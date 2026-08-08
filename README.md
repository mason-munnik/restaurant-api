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
    uvicorn main:app --reload
    ```
    The first run downloads the DistilBERT sentiment model (~260MB) from
    Hugging Face and caches it under `~/.cache/huggingface`, so it will pause
    and needs internet access. Subsequent runs start immediately from cache.

# Running the tests

```bash
pytest -v
```

The suite never runs real BERT inference — `conftest.py` replaces
`nlp.pipeline` before `main` is imported, so no model weights are downloaded
and tests finish in well under a second.

Because of that, CI installs `requirements-test.txt`, which omits `torch`
(~326MB plus its `sympy`/`networkx` deps) and cuts the install from ~676MB to
~220MB. If you add a test that needs the real model, decorate it with
`@requires_torch` (defined in `conftest.py`) so it self-skips in CI instead of
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

# Adding a new endpoint

Auth and an independently-tunable rate limit are two lines:

```python
@app.post("/summarize", dependencies=[Depends(require_api_key)])
@limiter.limit(config.rate_limit("SUMMARIZE_RATE_LIMIT", "5/minute"))
def summarize(request: Request, response: Response, ...):
```

Config lives in `config.py`, the auth dependency and limiter in `security.py`.
Tests get DB/limiter/env isolation for free from the `make_client` fixture in
`conftest.py`. Once endpoints outgrow a single file, move them onto an
`APIRouter(prefix=..., dependencies=[Depends(require_api_key)])` so a whole
group is protected once instead of per-endpoint.

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