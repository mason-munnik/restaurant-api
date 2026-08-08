# Restaurant Review Analysis API

An API that processes restaurant reviews and uses Natural Language Processing (NLP) to automatically assign a positive or negative sentiment score.

# Tech Stack
* Python 3.10+
* FastAPI 
* DistilBERT (`distilbert-base-uncased-finetuned-sst-2-english`, via Hugging Face `transformers`) for sentiment analysis
* SQLAlchemy (SQLite)
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
    # torch is CPU-only here to avoid pulling multi-GB CUDA wheels
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    pip install -r requirements.txt
    ```

4.  **Start the server:**
    ```bash
    uvicorn main:app --reload
    ```
    The first run downloads the DistilBERT sentiment model (~260MB) from
    Hugging Face and caches it under `~/.cache/huggingface`, so it will pause
    and needs internet access. Subsequent runs start immediately from cache.

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
# `GET /reviews`
Lists all reviews in database

# `DELETE /reviews/{review_id}`
Deletes a review by its ID