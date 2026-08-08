import pytest
from conftest import RATE_LIMIT_ENV_VAR

from app.core import security

PAYLOAD = {"restaurant_id": 1, "review_text": "food was great"}


@pytest.fixture
def rl_client(make_client, monkeypatch):
    """Opt in to the limiter, which conftest's autouse fixture keeps off.

    A tiny limit keeps these tests fast; it works because slowapi evaluates a
    callable limit provider on every request.
    """
    monkeypatch.setenv(RATE_LIMIT_ENV_VAR, "2/minute")
    security.limiter.reset()
    security.limiter.enabled = True
    return make_client()


def test_requests_under_limit_succeed(rl_client):
    assert rl_client.post("/analyze", json=PAYLOAD).status_code == 200
    assert rl_client.post("/analyze", json=PAYLOAD).status_code == 200


def test_request_over_limit_returns_429(rl_client):
    rl_client.post("/analyze", json=PAYLOAD)
    rl_client.post("/analyze", json=PAYLOAD)

    response = rl_client.post("/analyze", json=PAYLOAD)
    assert response.status_code == 429
    # substring, not the full body: the exact string embeds limits' repr
    assert "Rate limit exceeded" in response.json()["error"]


def test_limiter_state_does_not_leak_between_tests(rl_client):
    # deliberately placed right after the test that exhausts the limit --
    # this is the regression guard on the isolation strategy itself
    assert rl_client.post("/analyze", json=PAYLOAD).status_code == 200
    assert rl_client.post("/analyze", json=PAYLOAD).status_code == 200


def test_get_reviews_is_not_rate_limited(rl_client):
    for _ in range(3):
        rl_client.post("/analyze", json=PAYLOAD)

    for _ in range(5):
        assert rl_client.get("/reviews").status_code == 200


def test_rate_limit_value_comes_from_env(make_client, monkeypatch):
    monkeypatch.setenv(RATE_LIMIT_ENV_VAR, "1/minute")
    security.limiter.reset()
    security.limiter.enabled = True
    client = make_client()

    assert client.post("/analyze", json=PAYLOAD).status_code == 200
    assert client.post("/analyze", json=PAYLOAD).status_code == 429


def test_rate_limit_is_per_client_ip(make_client, monkeypatch):
    monkeypatch.setenv(RATE_LIMIT_ENV_VAR, "1/minute")
    security.limiter.reset()
    security.limiter.enabled = True

    first = make_client(ip="1.1.1.1")
    second = make_client(ip="2.2.2.2")

    assert first.post("/analyze", json=PAYLOAD).status_code == 200
    assert first.post("/analyze", json=PAYLOAD).status_code == 429
    # a different client IP has its own budget
    assert second.post("/analyze", json=PAYLOAD).status_code == 200


def test_rate_limit_disabled_flag_bypasses_limiter(rl_client):
    # pins the escape hatch the whole test suite depends on
    security.limiter.enabled = False
    for _ in range(5):
        assert rl_client.post("/analyze", json=PAYLOAD).status_code == 200


def test_rate_limited_response_has_retry_after_header(rl_client):
    for _ in range(3):
        response = rl_client.post("/analyze", json=PAYLOAD)

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_successful_response_has_rate_limit_headers(rl_client):
    response = rl_client.post("/analyze", json=PAYLOAD)
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "2"


def test_invalid_requests_do_not_consume_quota(rl_client):
    # the limiter runs after dependency + body validation, so rejected
    # requests never reach it
    for _ in range(5):
        bad = rl_client.post("/analyze", json={"restaurant_id": 1, "review_text": ""})
        assert bad.status_code == 422

    assert rl_client.post("/analyze", json=PAYLOAD).status_code == 200
    assert rl_client.post("/analyze", json=PAYLOAD).status_code == 200
