from fastapi import FastAPI
from pydantic import BaseModel
from nlp import SentimentAnalyzer

# initialize the analzyer and the API
analyzer = SentimentAnalyzer()
app = FastAPI()

class Review(BaseModel):
    restaurant_id: int
    review_text: str

@app.post("/analyze")   
def analyze(review: Review):
    """
    Analyzes a restaurant review and returns a sentiment score

    - **restaurant_id**: the ID of the restaurant being reviewed
    - **review_text**: the text of the review

    Returns a score between -1.0(Negative) and 1.0(Positive)
    """
    # using TextBlob for now for simplicity, but planning to swap to 
    # a BERT model for more accuracy later on
    score = analyzer.get_score(review.review_text)

    return {
        "restaurant_id": review.restaurant_id,
        "input_text": review.review_text,
        "score": score,
        "verdict": "Positive" if score > 0 else "Negative"
    }