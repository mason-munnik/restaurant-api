import os

API_KEY_ENV_VAR = "API_KEY"
API_KEY_HEADER = "X-API-Key"


def api_key() -> str | None:
    """Read at request time so a rotated key is picked up without a restart
    (and so tests can monkeypatch it)."""
    return os.getenv(API_KEY_ENV_VAR)


def rate_limit(env_var: str, default: str):
    """Build a slowapi limit provider backed by an env var.

    slowapi calls a zero-arg provider on every request, so limits stay live.
    Each endpoint gets its own env var, so they are independently tunable as
    the API grows.
    """

    def provider() -> str:
        return os.getenv(env_var) or default

    return provider
