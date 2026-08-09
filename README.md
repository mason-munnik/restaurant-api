# Restaurant Review Analysis API

An API that processes restaurant reviews and uses Natural Language Processing (NLP) to automatically assign a positive or negative sentiment score.

# Tech Stack
* Python 3.10+
* FastAPI 
* DistilBERT (`distilbert-base-uncased-finetuned-sst-2-english`, via Hugging Face `transformers`) for sentiment analysis
* SQLAlchemy (SQLite) + Alembic for migrations
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

4.  **Apply database migrations:**
    ```bash
    alembic upgrade head
    ```

5.  **Start the server:**
    ```bash
    export API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    uvicorn app.main:app --reload
    ```
    The first run downloads the DistilBERT sentiment model (~260MB) from
    Hugging Face and caches it under `~/.cache/huggingface`, so it will pause
    and needs internet access. Subsequent runs start immediately from cache.

# Database migrations

Schema is managed by Alembic, not by the app at startup. After pulling changes
that touch `app/db/models.py`, run:
```bash
alembic upgrade head
```
To create a new migration after changing a model:
```bash
alembic revision --autogenerate -m "describe the change"
```
Always hand-check the generated script before running it — SQLite can't
`ALTER TABLE` most constraint changes in place, so autogenerate output for
those needs wrapping in `op.batch_alter_table(...)` (see
`alembic/versions/7409d3949ef4_add_restaurants_table_and_fk_on_reviews.py`
for an example).

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
| `API_KEY` | yes | — | Shared secret for write endpoints. If unset, write endpoints return 500 rather than failing open. |
| `ANALYZE_RATE_LIMIT` | no | `10/minute` | Rate limit for `POST /analyze`. |
| `DATABASE_URL` | no | `sqlite:///./reviews.db` | SQLAlchemy database URL. |
| `SQL_ECHO` | no | `false` | Set to `true` to log every SQL statement. |
| `LOG_LEVEL` | no | `INFO` | Python logging level. |

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

- `GET /reviews?limit=` and `GET /restaurants?limit=` must be an integer in
  `[1, 100]` (default `10`); otherwise 422. Both also accept `offset` (>= 0,
  default `0`).
- `DELETE /reviews/{review_id}` requires `review_id >= 1`; otherwise 422.
- `review_text` must be non-empty and at least 3 words; `restaurant_id` must
  be a positive int referencing an existing restaurant (`POST /analyze`
  returns 404 if it doesn't exist) — the old <= 10000 sanity-cap validator
  was replaced by this real foreign-key check.
- Restaurant `name` must be non-empty and non-whitespace.

# Project layout

```
alembic/                # migration environment + versions/ (see Database migrations)
app/
  main.py               # creates the app, wires slowapi, includes routers
  api/routes/
    reviews.py          # review endpoints (APIRouter) + the analyzer singleton
    restaurants.py      # restaurant endpoints (APIRouter)
    health.py           # GET /health (liveness only)
  core/
    config.py           # env-driven settings, read at request time
    security.py         # require_api_key dependency + rate limiter
  db/
    session.py          # engine, SessionLocal, Base, get_db
    models.py           # ReviewModel, RestaurantModel (SQLAlchemy)
  schemas/
    review.py           # Review (Pydantic) + its validators
    restaurant.py       # RestaurantCreate (Pydantic) + its validator
  services/
    nlp.py              # SentimentAnalyzer (DistilBERT)
tests/                  # conftest.py + the suite
Dockerfile              # multi-stage build, bakes the DistilBERT weights in
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

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/analyze` | required | Analyzes a review's sentiment and persists it. 404 if `restaurant_id` doesn't exist. |
| GET | `/reviews` | public | Lists reviews. Accepts `limit`, `offset`, `restaurant_id` (filter). |
| GET | `/reviews/{review_id}` | public | Fetches a single review. 404 if missing. |
| DELETE | `/reviews/{review_id}` | required | Deletes a review by its ID. |
| POST | `/restaurants` | required | Creates a restaurant. |
| GET | `/restaurants` | public | Lists restaurants. Accepts `limit`, `offset`. |
| GET | `/restaurants/{restaurant_id}` | public | Fetches a single restaurant. 404 if missing. |
| DELETE | `/restaurants/{restaurant_id}` | required | Deletes a restaurant. 409 if it still has reviews. |
| GET | `/health` | public | Liveness check. Not rate-limited. |

# `POST /analyze`
Analyzes the sentiment of a review.

**Request Body (JSON):**
```json
{
  "restaurant_id": 1,
  "review_text": "The food was fantastic!"
}
```

# `POST /restaurants`
Creates a restaurant.

**Request Body (JSON):**
```json
{
  "name": "Trattoria Roma",
  "cuisine": "Italian",
  "location": "Downtown"
}
```
`cuisine` and `location` are optional.

# `DELETE /restaurants/{restaurant_id}`
Deletes a restaurant by its ID. Restaurants with existing reviews cannot be
deleted (409) — delete or reassign their reviews first. This is enforced at
the application layer, not via a database-level cascade/restrict constraint.

# Future work

Deliberately out of scope for now, to keep each pass focused:
- `PATCH`/`PUT` endpoints to update a restaurant or review after creation.
- Menu items, orders, reservations, or user accounts — the API models
  restaurants and reviews only.

# Running with Docker

```bash
docker build -t restaurant-api .
docker run -p 8000:8000 -e API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" restaurant-api
```
The image bakes the DistilBERT weights in at build time (no first-request
download) and runs `alembic upgrade head` before starting uvicorn. Expect the
image to be 1GB+ — that's inherent to shipping CPU torch + transformers + a
baked model, not something multi-stage builds avoid; multi-staging here just
keeps build-only artifacts (pip cache, `requirements.txt`) out of the final
layer. There's no `docker-compose.yml`, since the app stays on SQLite; mount a
volume at `/app` (or set `DATABASE_URL` to a path under one) if you want the
SQLite file to persist across container restarts.

CI builds and pushes this image to GHCR (`ghcr.io/<owner>/<repo>`) on every
push to `main` — see `.github/workflows/docker.yml`. It does not deploy
anywhere.