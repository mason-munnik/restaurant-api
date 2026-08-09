import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.db import models
from app.db.session import get_db
from app.schemas.restaurant import RestaurantCreate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/restaurants", dependencies=[Depends(require_api_key)])
def create_restaurant(restaurant: RestaurantCreate, db: Session = Depends(get_db)):
    new_restaurant = models.RestaurantModel(
        name=restaurant.name,
        cuisine=restaurant.cuisine,
        location=restaurant.location,
    )
    db.add(new_restaurant)
    db.commit()
    db.refresh(new_restaurant)
    return new_restaurant


@router.get("/restaurants")
def list_restaurants(
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
):
    return db.query(models.RestaurantModel).offset(offset).limit(limit).all()


@router.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = (
        db.query(models.RestaurantModel)
        .filter(models.RestaurantModel.id == restaurant_id)
        .first()
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.delete("/restaurants/{restaurant_id}", dependencies=[Depends(require_api_key)])
def delete_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = (
        db.query(models.RestaurantModel)
        .filter(models.RestaurantModel.id == restaurant_id)
        .first()
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    has_reviews = (
        db.query(models.ReviewModel)
        .filter(models.ReviewModel.restaurant_id == restaurant_id)
        .first()
        is not None
    )
    if has_reviews:
        logger.warning("Delete blocked: restaurant %s still has reviews", restaurant_id)
        raise HTTPException(
            status_code=409, detail="Cannot delete restaurant with existing reviews"
        )

    db.delete(restaurant)
    db.commit()
    return {"detail": f"Restaurant {restaurant_id} deleted"}
