"""
訂單 API。

核心: POST /orders/submit  使用 SELECT ... FOR UPDATE 對該桌悲觀鎖,
      避免兩位顧客同毫秒按下送單時產生重複訂單。

骨架版本只保留鎖的範例,實際扣庫存 / 計算服務費 / 清空購物車待補。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import FoodTable

router = APIRouter()


@router.post("/submit/{table_id}")
def submit_order(table_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    """
    悲觀鎖示範:
        SELECT ... FROM Food_Table WHERE TableID = :id FOR UPDATE
    第二個請求會被排隊,讀到的桌況已是 PAID/CLEANING → 直接拒絕。
    """
    stmt = select(FoodTable).where(FoodTable.TableID == table_id).with_for_update()
    table = db.execute(stmt).scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    if table.TableStatus != "ORDERING":
        raise HTTPException(status_code=409, detail=f"Table is {table.TableStatus},無法送單")

    # TODO:
    #   1. 讀 Food_Cart (該桌全部)
    #   2. 建立 Food_Order + Food_OrderDetail (UnitPrice 寫入當下價格)
    #   3. 套用 Food_SystemConfig 的 SERVICE_FEE_RATE 計算總額
    #   4. 清空 Food_Cart
    #   5. 透過 ConnectionManager.broadcast 通知該桌
    db.commit()
    return {"detail": "TODO: implement order submit (lock acquired ok)"}


@router.post("/checkout/{order_id}")
def checkout(order_id: int) -> dict[str, str]:
    return {"detail": "TODO: PAID → 桌況 CLEANING/IDLE,WS 連線失效"}
