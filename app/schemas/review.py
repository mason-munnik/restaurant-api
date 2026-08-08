from pydantic import BaseModel, field_validator


class Review(BaseModel):
    restaurant_id: int
    review_text: str

    @field_validator("review_text")
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

    @field_validator("restaurant_id")
    @classmethod
    def validate_restaurant_id(cls, v: int):
        # wanted to set an upper bound for restaurant id that seems realistic
        if v > 10000:
            raise ValueError("Restaurant ID seems invalid, too large")
        return v
