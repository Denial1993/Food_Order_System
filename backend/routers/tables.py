"""
桌位 — 狀態機 API。

- GET  /tables/                  列出全部桌位（後台用）
- GET  /tables/{table_no}        查詢單桌桌況（顧客掃碼後讀取）
- POST /tables/{table_no}/open   開桌：IDLE → ORDERING，同時產生新 SessionToken
- POST /tables/{table_no}/clean  清桌：任意狀態 → IDLE，同時清除 SessionToken
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import FoodTable
from schemas.table import TableOut

router = APIRouter()


@router.get("/", response_model=list[TableOut])
def list_tables(db: Session = Depends(get_db)) -> list[FoodTable]:
    """後台用：列出全部桌位"""
    return (
        db.query(FoodTable)
        .filter(FoodTable.StatusCode == "111")
        .order_by(FoodTable.TableNo)
        .all()
    )


@router.get("/{table_no}", response_model=TableOut)
def get_table(table_no: str, db: Session = Depends(get_db)) -> FoodTable:
    """顧客掃碼後讀取桌況，回應中含有 SessionToken（顧客要存起來）"""
    table = db.query(FoodTable).filter(FoodTable.TableNo == table_no).first()
    if not table:
        raise HTTPException(status_code=404, detail="桌號不存在")
    return table


@router.post("/{table_no}/open", response_model=TableOut)
def open_table(table_no: str, db: Session = Depends(get_db)) -> FoodTable:
    """
    開桌：IDLE → ORDERING。
    同時產生新的 SessionToken，舊的 QR Code 截圖從此失效。

    呼叫方：
    - 後台店員手動開桌
    - 顧客確認暱稱時若桌況為 IDLE，前端自動呼叫此 endpoint（自動開桌）
    """
    table = db.query(FoodTable).filter(FoodTable.TableNo == table_no).first()
    if not table:
        raise HTTPException(status_code=404, detail="桌號不存在")
    if table.TableStatus != "IDLE":
        raise HTTPException(status_code=409, detail=f"此桌目前是 {table.TableStatus}，無法重複開桌")

    table.TableStatus = "ORDERING"
    table.new_session()   # ← 產生新 UUID SessionToken
    db.commit()
    db.refresh(table)
    return table


@router.post("/{table_no}/clean", response_model=TableOut)
def clean_table(table_no: str, db: Session = Depends(get_db)) -> FoodTable:
    """
    清桌：任意狀態 → IDLE。
    同時清除 SessionToken，確保舊連線完全失效。
    """
    table = db.query(FoodTable).filter(FoodTable.TableNo == table_no).first()
    if not table:
        raise HTTPException(status_code=404, detail="桌號不存在")

    table.TableStatus  = "IDLE"
    table.SessionToken = None   # ← 清除 Token，此桌所有舊 session 全部失效
    db.commit()
    db.refresh(table)
    return table
