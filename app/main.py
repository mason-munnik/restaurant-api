import logging
import os

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import health, restaurants, reviews
from app.core.security import limiter

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# Schema is managed by Alembic (`alembic upgrade head`), not created here.
app = FastAPI()

# slowapi wiring: the handler reads request.app.state.limiter to add the
# Retry-After / X-RateLimit-* headers to a 429.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(reviews.router)
app.include_router(restaurants.router)
app.include_router(health.router)
