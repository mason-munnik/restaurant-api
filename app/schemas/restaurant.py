from pydantic import BaseModel, field_validator


class RestaurantCreate(BaseModel):
    name: str
    cuisine: str | None = None
    location: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str):
        v = v.strip()
        if not v:
            raise ValueError("Restaurant name cannot be empty or only whitespace.")
        return v
