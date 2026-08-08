import pytest
from conftest import API_KEY_ENV_VAR, API_KEY_HEADER, TEST_API_KEY
from fastapi import HTTPException

from app.core import security

PAYLOAD = {"restaurant_id": 1, "review_text": "food was great"}


def test_analyze_without_api_key_returns_401(make_client):
    response = make_client(api_key=None).post("/analyze", json=PAYLOAD)
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing API key"}


def test_analyze_with_valid_api_key_returns_200(client):
    response = client.post("/analyze", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json()["verdict"] == "Positive"


def test_analyze_with_wrong_api_key_returns_403(make_client):
    response = make_client(api_key="nope").post("/analyze", json=PAYLOAD)
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid API key"}


def test_delete_without_api_key_returns_401(make_client):
    response = make_client(api_key=None).delete("/reviews/1")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing API key"}


def test_delete_with_wrong_api_key_returns_403(make_client):
    response = make_client(api_key="nope").delete("/reviews/1")
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid API key"}


def test_delete_with_valid_api_key_reaches_handler(client):
    # proves auth passes the request through rather than swallowing it
    response = client.delete("/reviews/999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Review not found"}


def test_get_reviews_is_public_without_api_key(make_client):
    response = make_client(api_key=None).get("/reviews")
    assert response.status_code == 200
    assert response.json() == []


def test_get_reviews_public_even_with_garbage_api_key(make_client):
    # a bad key must not break an endpoint that never required one
    response = make_client(api_key="garbage").get("/reviews")
    assert response.status_code == 200


def test_empty_api_key_header_returns_401(make_client):
    # forces `if not x_api_key` rather than `if x_api_key is None`
    response = make_client(api_key="").post("/analyze", json=PAYLOAD)
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing API key"}


def test_whitespace_api_key_header_returns_403(make_client):
    # documents that we do not strip: whitespace is a wrong value, not a missing one
    response = make_client(api_key="   ").post("/analyze", json=PAYLOAD)
    assert response.status_code == 403


def test_api_key_prefix_of_real_key_returns_403(make_client):
    # guards against a startswith/`in` style comparison bug
    from conftest import TEST_API_KEY

    response = make_client(api_key=TEST_API_KEY[:-1]).post("/analyze", json=PAYLOAD)
    assert response.status_code == 403


def test_server_without_api_key_configured_returns_500(make_client, monkeypatch):
    client = make_client()
    monkeypatch.delenv(API_KEY_ENV_VAR)
    response = client.post("/analyze", json=PAYLOAD)
    assert response.status_code == 500
    assert response.json() == {"detail": "Server API key not configured"}


def test_server_without_api_key_configured_rejects_missing_key_too(
    make_client, monkeypatch
):
    # THE FAIL-OPEN GUARD: with no server key and no client key, a naive
    # compare_digest("", "") would return True and let the request through.
    # Must be 500 (server misconfigured), never 200.
    client = make_client(api_key=None)
    monkeypatch.delenv(API_KEY_ENV_VAR)
    response = client.post("/analyze", json=PAYLOAD)
    assert response.status_code == 500
    assert response.json() == {"detail": "Server API key not configured"}


def test_empty_api_key_env_var_returns_500(make_client, monkeypatch):
    # forces `if not expected` rather than `if expected is None`
    client = make_client()
    monkeypatch.setenv(API_KEY_ENV_VAR, "")
    response = client.post("/analyze", json=PAYLOAD)
    assert response.status_code == 500
    assert response.json() == {"detail": "Server API key not configured"}


def test_api_key_is_read_per_request_not_at_import(make_client, monkeypatch):
    # would fail against a module-level `API_KEY = os.getenv(...)`
    client = make_client()
    assert client.post("/analyze", json=PAYLOAD).status_code == 200

    monkeypatch.setenv(API_KEY_ENV_VAR, "rotated")
    assert client.post("/analyze", json=PAYLOAD).status_code == 403

    rotated = client.post("/analyze", json=PAYLOAD, headers={API_KEY_HEADER: "rotated"})
    assert rotated.status_code == 200


def test_auth_runs_before_body_validation(make_client):
    # an unauthenticated caller must not learn whether their body was valid
    response = make_client(api_key=None).post(
        "/analyze", json={"restaurant_id": 1, "review_text": ""}
    )
    assert response.status_code == 401


def test_auth_runs_before_path_validation(make_client):
    # 0 is an invalid review_id, but auth must reject first
    response = make_client(api_key=None).delete("/reviews/0")
    assert response.status_code == 401


def test_non_ascii_api_key_is_rejected_not_crashed(monkeypatch):
    # httpx refuses non-ASCII header values client-side, so exercise the
    # dependency directly. Pins the .encode() decision: compare_digest raises
    # TypeError on non-ASCII str, which would surface as an unhandled 500.
    monkeypatch.setenv(API_KEY_ENV_VAR, TEST_API_KEY)
    with pytest.raises(HTTPException) as exc_info:
        security.require_api_key(x_api_key="café")
    assert exc_info.value.status_code == 403
