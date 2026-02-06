from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from nlp import SentimentAnalyzer
from sqlalchemy.orm import Session

import models
from database import engine, SessionLocal

# creates a reviews.db file
models.Base.metadata.create_all(bind=engine)

# initialize the analzyer and the API
analyzer = SentimentAnalyzer()
app = FastAPI()

# helper that opens the db before the request and closes it after
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Review(BaseModel):
    restaurant_id: int
    review_text: str

@app.post("/analyze")   
def analyze(review: Review, db: Session = Depends(get_db)):
    """
    Analyzes a restaurant review and returns a sentiment score

    - **restaurant_id**: the ID of the restaurant being reviewed
    - **review_text**: the text of the review

    Returns a score between -1.0(Negative) and 1.0(Positive)
    """
    # using TextBlob for now for simplicity, but planning to swap to 
    # a BERT model for more accuracy later on
    score = analyzer.get_score(review.review_text)
    verdict = "Positive" if score > 0 else "Negative"

    new_review = models.ReviewModel(
        restaurant_id=review.restaurant_id,
        input_text=review.review_text,
        sentiment_score=score,
        verdict=verdict
    )

    db.add(new_review)

    return new_review