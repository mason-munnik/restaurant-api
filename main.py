from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, field_validator, Field
from nlp import SentimentAnalyzer
from sqlalchemy.orm import Session
from typing import List

import models
from database import engine, SessionLocal

# creates a reviews.db file
models.Base.metadata.create_all(bind=engine)

# initialize the analzyer and the API
analyzer = SentimentAnalyzer()
app = FastAPI()


@field_validator('review_text')
@classmethod
def validate_review_text(cls, v: str):
    # remove leading or trailing whitespace
    v = v.strip()
    # check if the review is empty or just whitespace
    if not v or v.isspace():
        raise ValueError("Review cannot be empty or only whitespace.")
    
    # Check if the review has real words, not just punctuation, and is long enough
    words = v.split()
    if len(words) < 3:
        raise ValueError("Review too short, must contain at least 3 words")
    
    return v


@field_validator('restaurant_id')
@classmethod
def validate_restaurant_id(cls, v: int):
    # wanted to set an upper bound for restaurant id that seems realistic
    if v > 10000:
        raise ValueError("Restaurant ID seems invalid, too large")
    return v


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
            verdict=verdict
        )

        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        return new_review
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the review: {str(e)}")

@app.get("/reviews")
def list_reviews(limit: int = 10, db: Session = Depends(get_db)):
    """
    Lists all reviews in database
    """
    return db.query(models.ReviewModel).all()

@app.delete("/reviews/{review_id}")
def delete_review(review_id: int, db = Depends(get_db)):
    """
    Deletes a review by ID
        
    -**review_id**: the ID of the review being deleted

    Returns a confirmation when the review is deleted
    """
    review = db.query(models.ReviewModel).filter(models.ReviewModel.id == review_id).first()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db.delete(review)
    db.commit()

    return {"deleted":True, "review_id": review_id}