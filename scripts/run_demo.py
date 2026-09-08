#!/usr/bin/env python3
"""
A small, original script exercising the massive-com/client-python SDK
(pip install massive) against the live Massive REST API.

Demonstrates:
  - loading an API key from an env var (never hardcoded/committed)
  - a single-object REST call (get_previous_close_agg)
  - an auto-paginating generator call (list_aggs)
  - a filtered query (list_ticker_news, published_utc.gte operator)
  - error handling on a call the account's plan doesn't cover (get_last_trade)
  - a request trace, for the "what a support engineer looks at when a call
    fails" view
  - what an invalid API key actually returns (401, not a generic failure)
  - what an unknown ticker actually returns (a 200 with an empty result set,
    not a 404 - a real "silent failure" gotcha worth knowing before you ship
    code that only checks for a raised exception)

Writes its captured results to results.json so a static page can render
them without ever needing the API key itself.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from urllib3.exceptions import MaxRetryError
from massive import RESTClient
from massive.exceptions import BadResponse

TICKER = "AAPL"
# The free tier rate-limits aggressively; the client's own retry
# logic isn't enough to ride that out, so this script paces its own calls.
CALL_SPACING_SECONDS = 15


def load_api_key() -> str:
    key = os.environ.get("MASSIVE_API_KEY")
    if key:
        return key

    env_file = os.path.expanduser("~/.massive_env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith("MASSIVE_API_KEY="):
                    return line.strip().split("=", 1)[1]

    sys.exit("Set MASSIVE_API_KEY (env var or ~/.massive_env) before running this.")


def main() -> None:
    api_key = load_api_key()
    client = RESTClient(api_key, trace=True, verbose=False)
    today = datetime.now(timezone.utc).date()
    results: dict = {"ticker": TICKER, "generated_at": today.isoformat()}

    # 1. Single-object call: previous day's close.
    prev = client.get_previous_close_agg(TICKER)
    bar = prev[0] if isinstance(prev, list) else prev
    results["previous_close"] = {
        "close": bar.close,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "volume": bar.volume,
    }
    print(f"[get_previous_close_agg] {TICKER} close=${bar.close}")

    # 2. Auto-paginating generator call: last 7 calendar days of daily bars.
    from_date = today - timedelta(days=9)
    bars = list(
        client.list_aggs(TICKER, 1, "day", from_date.isoformat(), today.isoformat(), limit=5)
    )
    results["daily_bars"] = [
        {
            "date": datetime.fromtimestamp(b.timestamp / 1000, tz=timezone.utc).date().isoformat(),
            "close": b.close,
        }
        for b in bars
    ]
    print(f"[list_aggs] fetched {len(bars)} daily bars")
    time.sleep(CALL_SPACING_SECONDS)

    # 3. Filtered query: recent news, published_utc.gte operator from the README.
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        news = list(client.list_ticker_news(TICKER, published_utc_gte=week_ago, limit=3))
        results["news"] = [n.title for n in news]
        print(f"[list_ticker_news] fetched {len(news)} articles")
    except (BadResponse, MaxRetryError) as e:
        results["news"] = None
        results["news_error"] = "rate limited (free tier — 429 on every attempt across multiple retries and minutes of spacing)"
        print(f"[list_ticker_news] rate limited: {e}")
    time.sleep(CALL_SPACING_SECONDS)

    # 4. Error handling: last-trade real-time data isn't included on this plan.
    try:
        client.get_last_trade(TICKER)
        results["last_trade_error"] = None
    except BadResponse as e:
        # BadResponse carries only the raw response body (see massive/rest/base.py);
        # it's JSON text, so parse it back into structured fields when possible.
        raw_body = str(e)
        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError:
            parsed = {"raw": raw_body}
        results["last_trade_error"] = parsed
        print(f"[get_last_trade] failed as expected: {parsed}")
    except MaxRetryError as e:
        results["last_trade_error"] = {"raw": "rate limited (free tier — 429 on every attempt across multiple retries and minutes of spacing)"}
        print(f"[get_last_trade] rate limited: {e}")
    time.sleep(CALL_SPACING_SECONDS)

    # 5. An invalid key isn't a generic failure - it's a specific 401.
    # Doesn't touch rate-limit budget: auth is checked before that accounting.
    bad_client = RESTClient("bad_key_deliberately_invalid_12345")
    try:
        bad_client.get_previous_close_agg(TICKER)
        results["bad_key_error"] = None
    except BadResponse as e:
        try:
            results["bad_key_error"] = json.loads(str(e))
        except json.JSONDecodeError:
            results["bad_key_error"] = {"raw": str(e)}
        print(f"[bad api key] failed as expected: {results['bad_key_error']}")
    time.sleep(CALL_SPACING_SECONDS)

    # 6. An unknown ticker isn't a 404 - it's a 200 with an empty result set.
    # A caller who only catches exceptions will miss this silently. raw=True
    # returns the actual HTTP response instead of a parsed model, so the
    # real envelope (status, resultsCount, request_id) is captured as-is.
    raw_resp = client.get_previous_close_agg("ZZZZNOTAREALTICKER", raw=True)
    results["unknown_ticker_result"] = json.loads(raw_resp.data.decode("utf-8"))
    print(f"[unknown ticker] no error raised - got back: {results['unknown_ticker_result']}")

    results["generated_at_iso"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Written to both locations: root results.json is the canonical raw
    # output (what someone browsing the repo would look for), and the copy
    # inside docs/ is what GitHub Pages actually serves - docs/index.html
    # fetches it with a relative path, so it has to live alongside the page.
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    for rel_path in ("results.json", os.path.join("docs", "results.json")):
        out_path = os.path.join(repo_root, rel_path)
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
