from fastapi import APIRouter

router = APIRouter()


# Liveness-only (no DB round-trip) and deliberately excluded from the rate
# limiter: orchestrator/LB probes must never be gated or fail alongside a
# downstream dependency.
@router.get("/health")
def health():
    return {"status": "ok"}
