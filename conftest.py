import importlib.util
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import nlp


def _fake_pipeline_factory(*args, **kwargs):
    def fake_pipeline(text, **kwargs):
        return [{"label": "POSITIVE", "score": 0.99}]

    return fake_pipeline


# main.py builds `analyzer = SentimentAnalyzer()` at import time, which would
# otherwise download/load real BERT weights the moment any test imports it.
# Everything below must be imported AFTER this line.
nlp.pipeline = _fake_pipeline_factory

import main  # noqa: E402
import security  # noqa: E402
from database import Base  # noqa: E402

TEST_API_KEY = "test-api-key"
API_KEY_ENV_VAR = "API_KEY"
API_KEY_HEADER = "X-API-Key"
RATE_LIMIT_ENV_VAR = "ANALYZE_RATE_LIMIT"

# CI installs requirements-test.txt, which omits torch (see that file for why),
# so anything exercising the real BERT model must self-skip rather than fail.
# Decorate such a test with @requires_torch.
requires_torch = pytest.mark.skipif(
    importlib.util.find_spec("torch") is None,
    reason="torch not installed (CI runs the torch-free requirements-test.txt)",
)


def _make_stub_pipeline(label="POSITIVE", score=0.95):
    def stub_pipeline(text, **kwargs):
        return [{"label": label, "score": score}]

    return stub_pipeline


@pytest.fixture(autouse=True)
def clean_security_env(monkeypatch):
    """Never inherit the developer's real API_KEY / rate limit from the shell."""
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    monkeypatch.delenv(RATE_LIMIT_ENV_VAR, raising=False)


@pytest.fixture(autouse=True)
def limiter_off():
    """slowapi's counters are process-global and TestClient presents the same
    client IP every time, so hits would accumulate across unrelated tests and
    cause spurious 429s. Default the limiter off and empty; test_rate_limit.py
    opts back in. Reset on both sides so a test failing mid-way can't leak.
    """
    security.limiter.reset()
    security.limiter.enabled = False
    yield
    security.limiter.enabled = False
    security.limiter.reset()


@pytest.fixture
def make_client(clean_security_env, monkeypatch):
    """Factory for TestClients sharing one isolated in-memory DB.

    api_key=None sends no X-API-Key header at all; pass a string to send a
    specific one. ip sets scope["client"], which is what the rate limiter
    keys on.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db
    main.analyzer._pipeline = _make_stub_pipeline()
    monkeypatch.setenv(API_KEY_ENV_VAR, TEST_API_KEY)

    with ExitStack() as stack:

        def _make(api_key=TEST_API_KEY, ip="testclient"):
            headers = {} if api_key is None else {API_KEY_HEADER: api_key}
            return stack.enter_context(
                TestClient(main.app, headers=headers, client=(ip, 50000))
            )

        yield _make

    main.app.dependency_overrides.clear()


@pytest.fixture
def client(make_client):
    return make_client()
