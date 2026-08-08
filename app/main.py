from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import reviews
from app.core.security import limiter
from app.db import models
from app.db.session import engine

# creates a reviews.db file
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# slowapi wiring: the handler reads request.app.state.limiter to add the
# Retry-After / X-RateLimit-* headers to a 429.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(reviews.router)
