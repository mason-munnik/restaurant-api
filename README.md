# Restaurant Review Analysis API

An API that processes restaurant reviews and uses Natural Language Processing (NLP) to automatically assign a positive or negative sentiment score.

# Tech Stack
* Python 3.10+
* FastAPI 
* DistilBERT (`distilbert-base-uncased-finetuned-sst-2-english`, via Hugging Face `transformers`) for sentiment analysis
* SQLAlchemy (SQLite)
* Uvicorn (ASGI server)

# How to run

1.  **Clone the repository and enter the folder:**
    ```bash
    cd restaurant-api
    ```

2.  **Create and activate the virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    # torch is CPU-only here to avoid pulling multi-GB CUDA wheels
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    pip install -r requirements.txt
    ```

4.  **Start the server:**
    ```bash
    export API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    uvicorn app.main:app --reload
    ```
    The first run downloads the DistilBERT sentiment model (~260MB) from
    Hugging Face and caches it under `~/.cache/huggingface`, so it will pause
    and needs internet access. Subsequent runs start immediately from cache.

# Running the tests

```bash
pytest -v
```

The suite never runs real BERT inference — `tests/conftest.py` replaces
`nlp.pipeline` before `main` is imported, so no model weights are downloaded
and tests finish in well under a second.

End-to-end tests live in `tests/test_e2e.py`. They boot a real uvicorn server
and run real BERT inference over HTTP, so they need `torch` and take minutes.
They're excluded from the default run and opt-in via their marker:

```bash
pytest -m e2e -v
```

CI runs them in a separate job on pushes to `main` only, keeping PR checks fast.

Because of that, CI installs `requirements-test.txt` for the fast suite, which omits `torch`
(~326MB plus its `sympy`/`networkx` deps) and cuts the install from ~676MB to
~220MB. If you add a test that needs the real model, decorate it with
`@requires_torch` (defined in `tests/conftest.py`) so it self-skips in CI instead of
failing, and run it locally against the full `requirements.txt`.

# Configuration

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `API_KEY` | yes | — | Shared secret for write endpoints. If unset, `POST /analyze` and `DELETE /reviews/{id}` return 500 rather than failing open. |
| `ANALYZE_RATE_LIMIT` | no | `10/minute` | Rate limit for `POST /analyze`. |

# Authentication

Write endpoints require an `X-API-Key` header. `GET /reviews` is intentionally public.

| Condition | Status | Body |
| --- | --- | --- |
| Valid key | 200 | endpoint payload |
| Header absent or empty | 401 | `{"detail": "Missing API key"}` |
| Header present, wrong value | 403 | `{"detail": "Invalid API key"}` |
| Server has no `API_KEY` set | 500 | `{"detail": "Server API key not configured"}` |

```bash
curl -X POST localhost:8000/analyze \
  -H "X-API-Key: $API_KEY" -H 'Content-Type: application/json' \
  -d '{"restaurant_id": 1, "review_text": "The food was fantastic!"}'
```

The key is compared with `secrets.compare_digest` over UTF-8 bytes, so the check
is constant-time and non-ASCII input cannot crash it. The key is read from the
environment on every request, so rotating it does not require a restart.

# Rate limiting

`POST /analyze` is limited per client IP (BERT inference is the expensive part).
Exceeding it returns `429` with `Retry-After` and `X-RateLimit-*` headers.

Counters are in-memory and per-process, so they reset on restart and are not
shared across uvicorn workers — a multi-worker deploy needs a shared
`storage_uri` (e.g. `redis://`). Requests rejected earlier in the chain (401
auth failures, 422 validation failures) do not consume quota, because the
limiter runs after dependency resolution and body validation.

Behind a proxy, the limiter sees the proxy's IP; switch the limiter's `key_func`
to `slowapi.util.get_ipaddr` only if the proxy is trusted, since the
`X-Forwarded-For` header it reads is client-spoofable.

# Request validation

- `GET /reviews?limit=` must be an integer in `[1, 100]` (default `10`); otherwise 422.
- `DELETE /reviews/{review_id}` requires `review_id >= 1`; otherwise 422.
- `review_text` must be non-empty and at least 3 words; `restaurant_id` must be <= 10000.

# Project layout

```
app/
  main.py               # creates the app, wires slowapi, includes routers
  api/routes/
    reviews.py          # all endpoints (APIRouter) + the analyzer singleton
  core/
    config.py           # env-driven settings, read at request time
    security.py         # require_api_key dependency + rate limiter
  db/
    session.py          # engine, SessionLocal, Base, get_db
    models.py           # ReviewModel (SQLAlchemy)
  schemas/
    review.py           # Review (Pydantic) + its validators
  services/
    nlp.py              # SentimentAnalyzer (DistilBERT)
tests/                  # conftest.py + the suite
```

Note: the `analyzer = SentimentAnalyzer()` singleton lives in
`app/api/routes/reviews.py`, **not** in `app/services/nlp.py`. That is
deliberate — `tests/conftest.py` patches `pipeline` on the nlp module before
importing anything that constructs an analyzer, which would be impossible if
importing the service itself created one.

# Adding a new endpoint

Auth and an independently-tunable rate limit are two lines:

```python
@router.post("/summarize", dependencies=[Depends(require_api_key)])
@limiter.limit(config.rate_limit("SUMMARIZE_RATE_LIMIT", "5/minute"))
def summarize(request: Request, response: Response, ...):
```

Config lives in `app/core/config.py`, the auth dependency and limiter in
`app/core/security.py`. Tests get DB/limiter/env isolation for free from the
`make_client` fixture in `tests/conftest.py`. Endpoints that should *all* be
protected can be grouped onto their own
`APIRouter(dependencies=[Depends(require_api_key)])` so auth is applied once
for the group — the current router applies it per-endpoint because
`GET /reviews` is intentionally public.

# API Endpoints

# `POST /analyze`
Analyzes the sentiment of a review.

**Request Body (JSON):**
```json
{
  "restaurant_id": 1,
  "review_text": "The food was fantastic!"
}
```
# `GET /reviews`
Lists all reviews in database

# `DELETE /reviews/{review_id}`
Deletes a review by its ID