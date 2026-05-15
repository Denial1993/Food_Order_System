"""
桌位 — 狀態機 API。
- GET /tables/{table_no}        查詢桌況 (顧客掃碼後讀取)
- POST /tables/{table_no}/open  店員開桌 (IDLE → ORDERING)
- POST /tables/{table_no}/clean 結帳後清潔 (PAID → CLEANING → IDLE)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import FoodTable
from schemas.table import TableOut

router = APIRouter()


@router.get("/{table_no}", response_model=TableOut)
def get_table(table_no: str, db: Session = Depends(get_db)) -> FoodTable:
    table = db.query(FoodTable).filter(FoodTable.TableNo == table_no).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    return table


@router.post("/{table_no}/open", response_model=TableOut)
def open_table(table_no: str, db: Session = Depends(get_db)) -> FoodTable:
    table = db.query(FoodTable).filter(FoodTable.TableNo == table_no).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    if table.TableStatus != "IDLE":
        raise HTTPException(status_code=409, detail=f"Table is {table.TableStatus}")
    table.TableStatus = "ORDERING"
    db.commit()
    db.refresh(table)
    return table


@router.post("/{table_no}/clean", response_model=TableOut)
def clean_table(table_no: str, db: Session = Depends(get_db)) -> FoodTable:
    table = db.query(FoodTable).filter(FoodTable.TableNo == table_no).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    table.TableStatus = "IDLE"
    db.commit()
    db.refresh(table)
    return table
