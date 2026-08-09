from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class RestaurantModel(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    cuisine = Column(String, nullable=True)
    location = Column(String, nullable=True)

    reviews = relationship("ReviewModel", back_populates="restaurant")


class ReviewModel(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(
        Integer, ForeignKey("restaurants.id"), nullable=False, index=True
    )
    review_text = Column(String)
    score = Column(Float)
    verdict = Column(String)

    restaurant = relationship("RestaurantModel", back_populates="reviews")
