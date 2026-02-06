from sqlalchemy import Column, Integer, String, Float
from database import Base

class ReviewModel(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer)
    review_text = Column(String)
    score = Column(Float)
    verdict = Column(String)