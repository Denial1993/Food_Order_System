"""
共用購物車 API — placeholder。
規劃配合 WebSocket: REST 寫入 DB 後,由路由主動 broadcast 該桌新狀態。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import FoodCart

router = APIRouter()


@router.get("/{table_id}")
def get_cart(table_id: int, db: Session = Depends(get_db)) -> list[dict]:
    items = (
        db.query(FoodCart)
        .options(selectinload(FoodCart.food))
        .filter(FoodCart.TableID == table_id, FoodCart.StatusCode == "111")
        .all()
    )
    return [
        {
            "CartID": i.CartID,
            "FoodID": i.FoodID,
            "FoodName": i.food.FoodName if i.food else None,
            "Price": float(i.food.Price) if i.food else 0,
            "Quantity": i.Quantity,
            "Nickname": i.Nickname,
            "Note": i.Note,
        }
        for i in items
    ]


@router.post("/{table_id}/items")
def add_item(table_id: int) -> dict[str, str]:
    return {"detail": "TODO: insert/upsert Food_Cart row + broadcast via WS"}


@router.delete("/{table_id}/items/{cart_id}")
def remove_item(table_id: int, cart_id: int) -> dict[str, str]:
    return {"detail": "TODO: delete row + broadcast"}
