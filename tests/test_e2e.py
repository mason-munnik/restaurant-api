"""End-to-end tests against a live uvicorn server running the real BERT model.

Excluded from the default suite (see `addopts` in pyproject.toml) because these
boot a real process, download/load real model weights, and take minutes. CI runs
them via `pytest -m e2e` in a main-branch-only job.

Everything else in the suite stubs the model, so this is the only place that
proves real inference actually works end to end over HTTP.
"""

import os
import pathlib
import subprocess
import sys
import time

import httpx
import pytest
from conftest import requires_torch

API_KEY = "e2e-test-key"
# High enough that the functional tests below never trip it, low enough that
# the rate-limit test can exceed it in one fast burst.
RATE_LIMIT = "5/minute"
BURST = 8
PORT = 8399
BASE_URL = f"http://127.0.0.1:{PORT}"
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

pytestmark = [pytest.mark.e2e, requires_torch]


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    """Boot uvicorn in a temp cwd so its ./reviews.db doesn't touch the repo."""
    workdir = tmp_path_factory.mktemp("e2e")
    env = {
        **os.environ,
        "API_KEY": API_KEY,
        "ANALYZE_RATE_LIMIT": RATE_LIMIT,
        # the app package lives in the repo, but cwd is the temp dir
        "PYTHONPATH": str(REPO_ROOT),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
        cwd=workdir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # first boot loads BERT weights (downloading them if uncached), so allow
    # a generous window before declaring failure
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pytest.fail(f"server exited early:\n{proc.stdout.read()}")
        try:
            if httpx.get(f"{BASE_URL}/reviews", timeout=2).status_code == 200:
                break
        except httpx.TransportError:
            time.sleep(1)
    else:
        proc.kill()
        pytest.fail("server did not become ready within 300s")

    yield BASE_URL

    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def auth():
    return {"X-API-Key": API_KEY}


def test_positive_review_scored_by_real_model(live_server, auth):
    response = httpx.post(
        f"{live_server}/analyze",
        json={
            "restaurant_id": 1,
            "review_text": "Absolutely wonderful food and outstanding service!",
        },
        headers=auth,
        timeout=60,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "Positive"
    # a real model should be confident about text this clearly positive
    assert body["score"] > 0.9
    assert body["id"] >= 1


def test_negative_review_scored_by_real_model(live_server, auth):
    response = httpx.post(
        f"{live_server}/analyze",
        json={
            "restaurant_id": 2,
            "review_text": "The food was cold, bland and genuinely awful.",
        },
        headers=auth,
        timeout=60,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "Negative"
    assert body["score"] < -0.9


def test_write_endpoints_require_api_key(live_server):
    unauthenticated = httpx.post(
        f"{live_server}/analyze",
        json={"restaurant_id": 1, "review_text": "food was great here"},
        timeout=30,
    )
    assert unauthenticated.status_code == 401

    wrong_key = httpx.post(
        f"{live_server}/analyze",
        json={"restaurant_id": 1, "review_text": "food was great here"},
        headers={"X-API-Key": "wrong"},
        timeout=30,
    )
    assert wrong_key.status_code == 403


def test_reviews_are_listed_and_deletable(live_server, auth):
    created = httpx.post(
        f"{live_server}/analyze",
        json={"restaurant_id": 3, "review_text": "a perfectly fine meal today"},
        headers=auth,
        timeout=60,
    )
    assert created.status_code == 200
    review_id = created.json()["id"]

    listed = httpx.get(f"{live_server}/reviews", timeout=30)
    assert listed.status_code == 200
    assert any(r["id"] == review_id for r in listed.json())

    deleted = httpx.delete(
        f"{live_server}/reviews/{review_id}", headers=auth, timeout=30
    )
    assert deleted.status_code == 200

    remaining = httpx.get(f"{live_server}/reviews", timeout=30).json()
    assert all(r["id"] != review_id for r in remaining)


def test_invalid_params_rejected(live_server, auth):
    assert httpx.get(f"{live_server}/reviews?limit=0", timeout=30).status_code == 422
    assert httpx.get(f"{live_server}/reviews?limit=101", timeout=30).status_code == 422
    assert (
        httpx.delete(f"{live_server}/reviews/0", headers=auth, timeout=30).status_code
        == 422
    )


def test_rate_limit_enforced_on_live_server(live_server, auth):
    # Runs last: it deliberately exhausts the limiter's window. Bursting more
    # than the limit in one go means this holds regardless of how much quota
    # earlier tests used, and regardless of where the 60s window happens to
    # have rolled over.
    payload = {"restaurant_id": 4, "review_text": "another decent meal here"}
    codes = [
        httpx.post(
            f"{live_server}/analyze", json=payload, headers=auth, timeout=60
        ).status_code
        for _ in range(BURST)
    ]
    assert 429 in codes, f"expected a 429 within {RATE_LIMIT}, got {codes}"
