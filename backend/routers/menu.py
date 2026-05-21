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
        .options(
            selectinload(FoodData.categories),   # 多對多，一次載入所有分類
            selectinload(FoodData.picture),
        )
        .filter(FoodData.IsAvailable == "Y", FoodData.StatusCode == "111")
    )

    if category_id is not None:
        # 多對多過濾：.any() 會產生 EXISTS 子查詢
        # 等同於 SQL: WHERE EXISTS (
        #   SELECT 1 FROM Food_FoodCategory fc
        #   WHERE fc.FoodID = Food_FoodData.FoodID AND fc.CategoryID = :category_id
        # )
        q = q.filter(FoodData.categories.any(FoodCategory.CategoryID == category_id))

    return q.order_by(FoodData.Sort).all()
