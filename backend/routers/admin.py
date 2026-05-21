"""
後台管理 API

【給新手的說明】
每個函式上方的 @router.get("/xxx") 稱為「路由裝飾器」，
意思是：「當瀏覽器 GET /api/admin/xxx 這個網址時，執行這個函式」。

FastAPI 會自動把 return 的 dict 轉成 JSON 回給前端。
"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import cast, Date, func  # func = SQL 函式 (sum/count...)
from sqlalchemy.orm import Session, selectinload

from database import get_db  # 取得 DB 連線的函式
from models import (
    FoodCategory, FoodData, FoodOrder, FoodOrderDetail,
    FoodPicture, FoodSystemConfig, FoodTable,
)
from schemas.food_admin import FoodAdminIn

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
# GET /api/admin/dashboard
# ─────────────────────────────────────────────────────────────────
@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),  # ← FastAPI 自動幫你建立 DB 連線並在函式結束後關閉
) -> dict:
    """
    儀表板統計資料

    Depends(get_db) 是 FastAPI 的「依賴注入」:
    你不需要自己寫 db = SessionLocal() / db.close()，
    FastAPI 會在每次請求進來時自動給你一條新的 DB 連線。
    """

    today = datetime.now().date()   # 今天的日期（不含時間）

    # ── 1. 今日營收：把今天所有「已結帳」訂單的 TotalAmount 加總 ──
    #    SQL 等價: SELECT COALESCE(SUM(TotalAmount), 0)
    #              FROM Food_Order
    #              WHERE OrderStatus='PAID' AND DATE(AddDate)=today
    today_revenue: Decimal = (
        db.query(func.coalesce(func.sum(FoodOrder.TotalAmount), 0))
        .filter(
            FoodOrder.OrderStatus == "PAID",
            cast(FoodOrder.AddDate, Date) == today,   # cast 把 datetime 轉成 date 比較
        )
        .scalar()   # .scalar() = 只取第一行第一欄的值（這裡是那個數字）
        or Decimal("0")
    )

    # ── 2. 在線桌數：目前有幾桌狀態是 ORDERING ─────────────────
    active_tables: int = (
        db.query(func.count(FoodTable.TableID))
        .filter(FoodTable.TableStatus == "ORDERING")
        .scalar()
        or 0
    )

    # ── 3. 待處理訂單：顧客已送單但店家還沒結帳的訂單數 ─────────
    pending_orders: int = (
        db.query(func.count(FoodOrder.OrderID))
        .filter(FoodOrder.OrderStatus == "OPEN")
        .scalar()
        or 0
    )

    # ── 4. 今日訂單數：今天所有訂單（不管是否結帳）───────────────
    today_order_count: int = (
        db.query(func.count(FoodOrder.OrderID))
        .filter(cast(FoodOrder.AddDate, Date) == today)
        .scalar()
        or 0
    )

    # ── 5. 桌況統計：各狀態有幾桌（IDLE/ORDERING/CLEANING）──────
    #    SQL 等價: SELECT TableStatus, COUNT(*) FROM Food_Table GROUP BY TableStatus
    rows = (
        db.query(FoodTable.TableStatus, func.count(FoodTable.TableID).label("cnt"))
        .filter(FoodTable.StatusCode == "111")
        .group_by(FoodTable.TableStatus)
        .all()
    )
    # 轉成 {"IDLE": 8, "ORDERING": 1, "CLEANING": 0} 這種格式
    table_stats = {r.TableStatus: r.cnt for r in rows}
    table_stats.setdefault("IDLE",     0)
    table_stats.setdefault("ORDERING", 0)
    table_stats.setdefault("CLEANING", 0)

    # ── 6. 最新 5 筆訂單（給儀表板下方的列表）────────────────────
    #    selectinload = 一次把關聯資料（details、food、table）都載入
    #    避免 N+1 問題（不然每筆訂單都要再查一次 DB）
    recent = (
        db.query(FoodOrder)
        .options(
            selectinload(FoodOrder.details).selectinload(FoodOrderDetail.food),
            selectinload(FoodOrder.table),
        )
        .order_by(FoodOrder.AddDate.desc())
        .limit(5)
        .all()
    )

    recent_list = []
    for o in recent:
        # 把每道餐點組成 "招牌雞腿飯×1, 珍珠奶茶×2" 的字串
        items_str = "、".join(
            f"{d.food.FoodName}×{d.Quantity}"
            for d in o.details
            if d.food
        )
        recent_list.append({
            "OrderNo":     o.OrderNo,
            "TableNo":     o.table.TableNo if o.table else "?",
            "TotalAmount": float(o.TotalAmount),
            "OrderStatus": o.OrderStatus,
            "AddDate":     o.AddDate.strftime("%H:%M") if o.AddDate else "",
            "Items":       items_str or "（無明細）",
        })

    # ── 組合最終回傳資料 ──────────────────────────────────────────
    return {
        "today_revenue":     float(today_revenue),
        "active_tables":     active_tables,
        "pending_orders":    pending_orders,
        "today_order_count": today_order_count,
        "table_stats":       table_stats,
        "recent_orders":     recent_list,
    }


# ─────────────────────────────────────────────────────────────────
# GET /api/admin/system-config
# ─────────────────────────────────────────────────────────────────
@router.get("/system-config")
def list_system_config(db: Session = Depends(get_db)) -> list[dict]:
    """列出全部系統參數（參考 tblsysCode 設計）"""
    rows = (
        db.query(FoodSystemConfig)
        .filter(FoodSystemConfig.StatusCode == "111")
        .order_by(FoodSystemConfig.CodeType, FoodSystemConfig.CodeSeq)
        .all()
    )
    return [
        {
            "CodeID":    r.CodeID,
            "CodeType":  r.CodeType,
            "CodeStr":   r.CodeStr,
            "CodeValue": r.CodeValue,
            "CodeDesc":  r.CodeDesc,
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────
# 餐點分類列表（給新增/編輯餐點時的下拉選單用）
# GET /api/admin/categories
# ─────────────────────────────────────────────────────────────────
@router.get("/categories")
def list_categories(db: Session = Depends(get_db)) -> list[dict]:
    """回傳所有有效分類（StatusCode='111'）"""
    rows = (
        db.query(FoodCategory)
        .filter(FoodCategory.StatusCode == "111")
        .order_by(FoodCategory.Sort, FoodCategory.CategoryID)
        .all()
    )
    return [{"CategoryID": r.CategoryID, "CategoryName": r.CategoryName} for r in rows]


# ─────────────────────────────────────────────────────────────────
# 後台餐點列表（含下架商品，管理員要看到全部）
# GET /api/admin/foods
# ─────────────────────────────────────────────────────────────────
@router.get("/foods")
def list_foods_admin(db: Session = Depends(get_db)) -> list[dict]:
    """
    回傳所有餐點（StatusCode='111'，但 IsAvailable 不過濾）
    使用 selectinload 一次載入 categories（多對多）和 picture 關聯，避免 N+1 查詢。
    """
    rows = (
        db.query(FoodData)
        .options(
            selectinload(FoodData.categories),   # ← 多對多，載入所有分類
            selectinload(FoodData.picture),
        )
        .filter(FoodData.StatusCode == "111")
        .order_by(FoodData.Sort, FoodData.FoodID)
        .all()
    )
    return [_food_to_dict(r) for r in rows]


def _food_to_dict(r: FoodData) -> dict:
    """把 FoodData ORM 物件轉成可序列化的 dict"""
    return {
        "FoodID":      r.FoodID,
        "FoodName":    r.FoodName,
        "FoodDesc":    r.FoodDesc,
        "Price":       float(r.Price),
        # categories 是一個 list，每個元素含 CategoryID 和 CategoryName
        "categories":  [
            {"CategoryID": c.CategoryID, "CategoryName": c.CategoryName}
            for c in r.categories
        ],
        "IsAvailable": r.IsAvailable,
        "Sort":        r.Sort,
        "StatusCode":  r.StatusCode,
        "PictureID":   r.PictureID,
        "PicturePath": r.picture.PicturePath if r.picture else None,
        "PictureName": r.picture.PictureName if r.picture else None,
        "AltText":     r.picture.AltText     if r.picture else None,
    }


# ─────────────────────────────────────────────────────────────────
# 新增餐點
# POST /api/admin/foods
# ─────────────────────────────────────────────────────────────────
@router.post("/foods", status_code=201)
def create_food(body: FoodAdminIn, db: Session = Depends(get_db)) -> dict:
    """
    新增一道餐點。
    如果有傳 PicturePath，就順便建立一筆 Food_Picture 記錄並關聯。

    HTTP 201 = Created（新增成功的標準回應碼）
    """
    # ① 如果有圖片路徑，先建立圖片記錄
    picture_id: int | None = None
    if body.PicturePath:
        pic = FoodPicture(
            PictureName = body.PictureName or body.FoodName,
            PicturePath = body.PicturePath,
            AltText     = body.AltText,
            StatusCode  = "111",
        )
        db.add(pic)
        db.flush()          # flush 讓 DB 先分配 PictureID，但還沒 commit
        picture_id = pic.PictureID

    # ② 建立餐點（不再有 CategoryID 欄位，改用多對多）
    food = FoodData(
        FoodName    = body.FoodName,
        FoodDesc    = body.FoodDesc,
        Price       = body.Price,
        PictureID   = picture_id,
        IsAvailable = body.IsAvailable,
        Sort        = body.Sort,
        StatusCode  = "111",
    )
    db.add(food)
    db.flush()   # 先取得 FoodID，才能建立中間表關聯

    # ③ 設定多對多分類（SQLAlchemy 會自動處理中間表的 INSERT）
    if body.CategoryIDs:
        cat_objs = db.query(FoodCategory).filter(
            FoodCategory.CategoryID.in_(body.CategoryIDs)
        ).all()
        food.categories = cat_objs

    db.commit()
    db.refresh(food)
    # 觸發 lazy load，讓 _food_to_dict 可以讀到關聯資料
    _ = food.categories
    _ = food.picture

    return _food_to_dict(food)


# ─────────────────────────────────────────────────────────────────
# 修改餐點（含圖片）
# PUT /api/admin/foods/{food_id}
# ─────────────────────────────────────────────────────────────────
@router.put("/foods/{food_id}")
def update_food(food_id: int, body: FoodAdminIn, db: Session = Depends(get_db)) -> dict:
    """
    更新餐點資料。
    - 如果原本有圖片且傳入新 PicturePath → 更新同一筆圖片記錄
    - 如果原本沒圖片但傳入 PicturePath → 新建圖片記錄
    - 如果 PicturePath 為空 → 不動圖片（保留原來的）
    """
    # 用 options 一起撈關聯（categories + picture）
    food: FoodData | None = (
        db.query(FoodData)
        .options(
            selectinload(FoodData.categories),
            selectinload(FoodData.picture),
        )
        .filter(FoodData.FoodID == food_id, FoodData.StatusCode == "111")
        .first()
    )
    if not food:
        raise HTTPException(status_code=404, detail="餐點不存在")

    # ① 更新基本欄位
    food.FoodName    = body.FoodName
    food.FoodDesc    = body.FoodDesc
    food.Price       = body.Price
    food.IsAvailable = body.IsAvailable
    food.Sort        = body.Sort

    # ② 更新多對多分類（直接覆蓋整個 categories list，SQLAlchemy 自動處理中間表）
    cat_objs = db.query(FoodCategory).filter(
        FoodCategory.CategoryID.in_(body.CategoryIDs)
    ).all() if body.CategoryIDs else []
    food.categories = cat_objs

    # ③ 處理圖片
    if body.PicturePath:
        if food.picture:
            food.picture.PicturePath = body.PicturePath
            food.picture.PictureName = body.PictureName or body.FoodName
            food.picture.AltText     = body.AltText
        else:
            pic = FoodPicture(
                PictureName = body.PictureName or body.FoodName,
                PicturePath = body.PicturePath,
                AltText     = body.AltText,
                StatusCode  = "111",
            )
            db.add(pic)
            db.flush()
            food.PictureID = pic.PictureID

    db.commit()
    db.refresh(food)
    _ = food.categories
    _ = food.picture

    return _food_to_dict(food)


# ─────────────────────────────────────────────────────────────────
# 刪除餐點（軟刪除）
# DELETE /api/admin/foods/{food_id}
# ─────────────────────────────────────────────────────────────────
@router.delete("/foods/{food_id}", status_code=204)
def delete_food(food_id: int, db: Session = Depends(get_db)):
    """
    軟刪除：把 StatusCode 改成 '000'，不真的從 DB 刪掉資料。
    這樣可以保留歷史訂單的參照完整性。

    HTTP 204 = No Content（刪除成功但不回傳內容）
    """
    food = db.query(FoodData).filter(
        FoodData.FoodID == food_id,
        FoodData.StatusCode == "111",
    ).first()
    if not food:
        raise HTTPException(status_code=404, detail="餐點不存在")

    food.StatusCode = "000"
    db.commit()
