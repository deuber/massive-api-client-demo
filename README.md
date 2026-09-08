# massive-api-client-demo

A small, original script exercising [`massive-com/client-python`](https://github.com/massive-com/client-python)
(`pip install massive`) — the official Python client for the Massive
(formerly Polygon.io) market data REST API — against the **live** API,
using a real free-tier API key.

## Live demo

**[deuber.github.io/massive-api-client-demo](https://deuber.github.io/massive-api-client-demo/)**
has an interactive toggle over whatever the last actual run captured — real
prices, an auto-paginating call, and several failure/edge-case shapes (403,
429, 401, and a silent empty-result "200"). Nothing on that page is
fabricated. See **How it works** below for the mechanics.

## How it works

1. **Capture.** `scripts/run_demo.py` makes six real calls against
   `api.massive.com` and writes whatever actually happens — success or
   failure — to `results.json`.
2. **Render, don't template.** `docs/index.html` has almost no hardcoded
   numbers. On load it does one `fetch('./results.json')` and builds the
   stat tile, chart, evidence cards, and flow-diagram states entirely from
   that response. A card (or a flow-toggle button) only exists if the
   matching field exists in the JSON — so a run where the news call
   succeeds instead of getting rate-limited renders a different card
   automatically, with no code change. There's no template to drift out of
   sync with the data, because there's no template — just real data
   driving real DOM.
3. **Interact, safely.** The flow-toggle buttons animate between those
   captured outcomes; they never call the live API from your browser,
   since that would mean shipping a real API key in public client-side JS.
   A caption under the buttons says this explicitly.
4. **Refresh automatically.** A scheduled [GitHub Action](.github/workflows/refresh.yml)
   re-runs the script weekly (and on manual dispatch) using the key as an
   encrypted repo secret, and commits the refreshed results only if
   something actually changed.
5. **Trust it.** Every number traces back to an actual HTTP response —
   nothing in the rendering logic invents data. The one simulated part
   (replaying past outcomes on button click, rather than calling the API
   live) is the part explicitly labeled as such on the page.

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

Writes real captured output to `results.json` **and** `docs/results.json`
(GitHub Pages only serves the `docs/` folder, and the page fetches its data
with a relative path, so both need the same file). The free tier
rate-limits aggressively (a handful of requests per minute), so the script
paces its own calls — you may still see a 429 on the news query if you run
it more than once in quick succession, which is the real behavior this
demo is partly about.

Open `docs/index.html` in a browser after running it — but not via a bare
`file://` URL, since `fetch()` for a local JSON file is blocked there by
browsers. Serve it locally instead, e.g. `python3 -m http.server` from
inside `docs/`.

## About the API key

`MASSIVE_API_KEY` is stored as an
[encrypted repo secret](https://docs.github.com/actions/security-guides/using-secrets-in-github-actions),
never committed and never visible in workflow logs. Cloning or forking this
repo gets you the code, not the secret — running the workflow yourself (or
`scripts/run_demo.py` locally) requires your own Massive API key, never
mine.

## Project structure

```
scripts/run_demo.py         The actual script — loads the key, makes the calls, writes both results.json files
results.json                  Real output from an actual run (checked in, not a mock)
docs/index.html              Thin renderer: fetches docs/results.json and builds the whole page from it
docs/results.json              Same content as the root copy, served by GitHub Pages
.github/workflows/refresh.yml   Scheduled re-run + auto-commit, using a repo secret for the key
```
