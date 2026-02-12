# Restaurant Review Analysis API

An API that processes restaurant reviews and uses Natural Language Processing (NLP) to automatically assign a positive or negative sentiment score.

# Tech Stack
* Python 3.10+
* FastAPI 
* TextBlob (NLP/Sentiment Analysis)
* Uvicorn (ASGI server)

# How to run

1.  **Clone the repository and enter the folder:**
    ```bash
    cd restaurant-api
    ```

2.  **Create and activate the virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install fastapi uvicorn textblob sqlalchemy
    ```

4.  **Start the server:**
    ```bash
    uvicorn main:app --reload
    ```

# API Endpoints

# `POST /analyze`
Analyzes the sentiment of a review.

**Request Body (JSON):**
```json
{
  "restaurant_id": 1,
  "review_text": "The food was fantastic!"
}
```
# 'GET /reviews'
Lists all reviews in database

# 'DELETE /reviews/{review_id}'
Deletes a review by restaurant ID