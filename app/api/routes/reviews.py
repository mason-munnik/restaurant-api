from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy.orm import Session

from app.core import config
from app.core.security import limiter, require_api_key
from app.db import models
from app.db.session import get_db
from app.schemas.review import Review
from app.services.nlp import SentimentAnalyzer

# Constructed here rather than in services/nlp.py on purpose: tests patch
# `pipeline` on that module before this one is imported, so the analyzer must
# not exist until after that patch has been applied.
analyzer = SentimentAnalyzer()

# Auth is applied per-endpoint rather than on the router, because GET /reviews
# is intentionally public while the write endpoints are not.
router = APIRouter()


@router.post("/analyze", dependencies=[Depends(require_api_key)])
@limiter.limit(config.rate_limit("ANALYZE_RATE_LIMIT", "10/minute"))
def analyze(
    request: Request,
    response: Response,
    review: Review,
    db: Session = Depends(get_db),
):
    """
    Analyzes a restaurant review and returns a sentiment score

    - **restaurant_id**: the ID of the restaurant being reviewed
    - **review_text**: the text of the review

    Returns a score between -1.0(Negative) and 1.0(Positive)
    """
    try:
        # get sentiment score
        score = analyzer.get_score(review.review_text)

        # validate that score is in expected range (defensive programming)
        if not -1.0 <= score <= 1.0:
            raise ValueError(f"Unexpected sentiment score: {score}")

        verdict = "Positive" if score > 0 else "Negative"

        new_review = models.ReviewModel(
            restaurant_id=review.restaurant_id,
            review_text=review.review_text,
            score=score,
            verdict=verdict,
        )

        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        return new_review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reviews")
def list_reviews(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    db: Session = Depends(get_db),
):
    return db.query(models.ReviewModel).limit(limit).all()


@router.delete("/reviews/{review_id}", dependencies=[Depends(require_api_key)])
def delete_review(
    review_id: Annotated[int, Path(ge=1)],
    db: Session = Depends(get_db),
):
    """
    Deletes a review by its ID
    """
    review = (
        db.query(models.ReviewModel).filter(models.ReviewModel.id == review_id).first()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    db.delete(review)
    db.commit()
    return {"detail": f"Review {review_id} deleted"}
