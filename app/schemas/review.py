from pydantic import BaseModel, Field, field_validator


class Review(BaseModel):
    restaurant_id: int = Field(gt=0)
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
