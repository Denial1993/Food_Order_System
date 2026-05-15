from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import FoodCategory, FoodData
from schemas.menu import CategoryOut, FoodOut

router = APIRouter()


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[FoodCategory]:
    return (
        db.query(FoodCategory)
        .filter(FoodCategory.StatusCode == "111")
        .order_by(FoodCategory.Sort)
        .all()
    )


@router.get("/foods", response_model=list[FoodOut])
def list_foods(
    category_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[FoodData]:
    q = (
        db.query(FoodData)
        .options(selectinload(FoodData.picture), selectinload(FoodData.category))
        .filter(FoodData.IsAvailable == "Y", FoodData.StatusCode == "111")
    )
    if category_id is not None:
        q = q.filter(FoodData.CategoryID == category_id)
    return q.order_by(FoodData.Sort).all()
