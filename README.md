# massive-api-client-demo

A small, original script exercising [`massive-com/client-python`](https://github.com/massive-com/client-python)
(`pip install massive`) — the official Python client for the Massive
(formerly Polygon.io) market data REST API — against the **live** API,
using a real free-tier API key.

## Live demo

**[deuber.github.io/massive-api-client-demo](https://deuber.github.io/massive-api-client-demo/)**
has an interactive toggle over six real, pre-recorded outcomes from an
actual run — real prices, an auto-paginating call, and four different
failure/edge-case shapes (403, 429, 401, and a silent empty-result "200").
Nothing on that page is fabricated; `results.json` in this repo is the raw
output the script wrote.

## What it demonstrates

- Loading an API key from an env var / local file, never hardcoded or committed
- A single-object REST call (`get_previous_close_agg`)
- An auto-paginating generator call (`list_aggs`)
- A filtered query using the `published_utc.gte` operator (`list_ticker_news`)
- Handling a **403** on an endpoint the account's plan doesn't cover
  (`get_last_trade` — real-time last-trade data isn't included on the free tier)
- Handling a **429** from the free tier's rate limit — the vendor's own
  README calls this out as expected free-tier behavior, and it's exactly
  what happened running this for real (see `results.json`)
- Handling a **401** from a deliberately invalid key — confirms it's a
  specific, self-explanatory error, not a generic connection failure
- The **silent empty-result gotcha**: an unknown ticker doesn't 404, it
  returns a normal `200` with an empty result set — code that only catches
  exceptions will miss this entirely
- Request tracing (`RESTClient(trace=True)`), which auto-redacts the API
  key in its own log output

## Running it yourself

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export MASSIVE_API_KEY=your_key_here   # free tier: https://massive.com/pricing
python3 scripts/run_demo.py
```

Writes real captured output to `results.json`. The free tier rate-limits
aggressively (a handful of requests per minute), so the script paces its
own calls — you may still see a 429 on the news query if you run it more
than once in quick succession, which is the real behavior this demo is
partly about.

## Project structure

```
scripts/run_demo.py   The actual script — loads the key, makes the 6 calls, writes results.json
results.json           Real output from an actual run (checked in, not a mock)
docs/index.html         Static page with an interactive toggle over the 6 outcomes
```
