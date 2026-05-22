"""
後台管理 API

【給新手的說明】
每個函式上方的 @router.get("/xxx") 稱為「路由裝飾器」，
意思是：「當瀏覽器 GET /api/admin/xxx 這個網址時，執行這個函式」。

FastAPI 會自動把 return 的 dict 轉成 JSON 回給前端。
"""
import uuid
from datetime import datetime
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import cast, Date, extract, func  # func = SQL 函式 (sum/count...)
from sqlalchemy.orm import Session, selectinload

from core.config import settings

from database import get_db  # 取得 DB 連線的函式
from models import (
    FoodCategory, FoodData, FoodOrder, FoodOrderDetail,
    FoodPicture, FoodSystemConfig, FoodTable,
)
from schemas.food_admin import FoodAdminIn
from schemas.system_config import SystemConfigIn

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
# POST /api/admin/upload-image  — 上傳圖片到 Supabase Storage
# ─────────────────────────────────────────────────────────────────
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_SIZE_MB   = 5

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)) -> dict:
    """
    接收前端上傳的圖片，存進 Supabase Storage，回傳公開 URL。

    【流程】
    1. 前端 FormData → FastAPI UploadFile
    2. 後端轉發到 Supabase Storage REST API（PUT /storage/v1/object/{bucket}/{path}）
    3. 回傳 { url, path }

    【設定方式】
    在後端 .env 填入：
      SUPABASE_URL=https://xxxx.supabase.co
      SUPABASE_SERVICE_KEY=eyJhbGciOi...  (service_role key)
      SUPABASE_STORAGE_BUCKET=menu-images  (預先在 Supabase 建好的 public bucket)

    【未設定 Supabase 時】
    直接回傳錯誤提示（不影響其他功能，URL 輸入仍可用）。
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise HTTPException(
            status_code=501,
            detail="圖片上傳尚未設定（後端未配置 SUPABASE_URL / SUPABASE_SERVICE_KEY）",
        )

    # ── 檔案類型與大小檢查 ───────────────────────────────────────
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="只允許 JPEG / PNG / WebP / GIF")

    content = await file.read()
    if len(content) > _MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"圖片大小不可超過 {_MAX_SIZE_MB} MB")

    # ── 產生唯一檔名，避免覆蓋 ──────────────────────────────────
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    unique_name = f"menu/{uuid.uuid4().hex}.{ext}"
    bucket = settings.SUPABASE_STORAGE_BUCKET

    # ── 上傳到 Supabase Storage ─────────────────────────────────
    upload_url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{unique_name}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "Content-Type": file.content_type or "image/jpeg",
        "x-upsert": "false",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.put(upload_url, content=content, headers=headers)

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"上傳到 Supabase 失敗: {resp.text[:200]}",
        )

    public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{unique_name}"
    return {"url": public_url, "path": unique_name}


# ─────────────────────────────────────────────────────────────────
# GET /api/admin/revenue  — 歷史營收分析
# ─────────────────────────────────────────────────────────────────
@router.get("/revenue")
def revenue_stats(
    mode:  str       = Query("annual",  description="annual | monthly | daily"),
    year:  int | None = Query(None,     description="年份，例 2026"),
    month: int | None = Query(None,     description="月份 1-12，僅 daily 模式使用"),
    db: Session = Depends(get_db),
) -> dict:
    """
    歷史營收分析（僅計算已結帳 PAID 訂單）。

    - mode=annual  → 近 3 年各年度總額（不傳 year）
    - mode=monthly → 指定年各月合計（需傳 year）
    - mode=daily   → 指定年+月各天合計（需傳 year + month）

    回傳格式: { "labels": [...], "values": [...], "total": float }
    """
    current_year = datetime.now().year

    base_q = db.query(FoodOrder).filter(FoodOrder.OrderStatus == "PAID")

    if mode == "annual":
        # 近 3 年（含今年）
        start_year = current_year - 2
        rows = (
            base_q
            .filter(extract("year", FoodOrder.AddDate) >= start_year)
            .with_entities(
                extract("year", FoodOrder.AddDate).label("label"),
                func.coalesce(func.sum(FoodOrder.TotalAmount), 0).label("revenue"),
            )
            .group_by(extract("year", FoodOrder.AddDate))
            .order_by(extract("year", FoodOrder.AddDate))
            .all()
        )
        # 補齊沒有資料的年份
        revenue_map: dict[int, float] = {int(r.label): float(r.revenue) for r in rows}
        labels = [str(y) for y in range(start_year, current_year + 1)]
        values = [revenue_map.get(y, 0.0) for y in range(start_year, current_year + 1)]

    elif mode == "monthly":
        if not year:
            year = current_year
        rows = (
            base_q
            .filter(extract("year", FoodOrder.AddDate) == year)
            .with_entities(
                extract("month", FoodOrder.AddDate).label("label"),
                func.coalesce(func.sum(FoodOrder.TotalAmount), 0).label("revenue"),
            )
            .group_by(extract("month", FoodOrder.AddDate))
            .order_by(extract("month", FoodOrder.AddDate))
            .all()
        )
        revenue_map = {int(r.label): float(r.revenue) for r in rows}
        labels = [f"{m}月" for m in range(1, 13)]
        values = [revenue_map.get(m, 0.0) for m in range(1, 13)]

    elif mode == "daily":
        if not year:
            year = current_year
        if not month:
            month = datetime.now().month
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        rows = (
            base_q
            .filter(
                extract("year",  FoodOrder.AddDate) == year,
                extract("month", FoodOrder.AddDate) == month,
            )
            .with_entities(
                extract("day", FoodOrder.AddDate).label("label"),
                func.coalesce(func.sum(FoodOrder.TotalAmount), 0).label("revenue"),
            )
            .group_by(extract("day", FoodOrder.AddDate))
            .order_by(extract("day", FoodOrder.AddDate))
            .all()
        )
        revenue_map = {int(r.label): float(r.revenue) for r in rows}
        labels = [f"{d}日" for d in range(1, days_in_month + 1)]
        values = [revenue_map.get(d, 0.0) for d in range(1, days_in_month + 1)]

    else:
        raise HTTPException(status_code=400, detail="mode 需為 annual / monthly / daily")

    return {
        "mode":   mode,
        "labels": labels,
        "values": values,
        "total":  sum(values),
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
    return [_config_to_dict(r) for r in rows]


def _config_to_dict(r: FoodSystemConfig) -> dict:
    return {
        "CodeID":     r.CodeID,
        "CodeNo":     r.CodeNo,
        "CodeType":   r.CodeType,
        "CodeStr":    r.CodeStr,
        "CodeValue":  r.CodeValue,
        "RoleID":     r.RoleID,
        "CodeDesc":   r.CodeDesc,
        "CodeSeq":    r.CodeSeq,
        "StatusCode": r.StatusCode,
    }


@router.post("/system-config", status_code=201)
def create_system_config(body: SystemConfigIn, db: Session = Depends(get_db)) -> dict:
    """
    新增一筆系統參數。
    若 (CodeType, CodeStr) 已存在且狀態為啟用，回 409 避免重複鍵。
    """
    dup = (
        db.query(FoodSystemConfig)
        .filter(
            FoodSystemConfig.CodeType == body.CodeType,
            FoodSystemConfig.CodeStr  == body.CodeStr,
            FoodSystemConfig.StatusCode == "111",
        )
        .first()
    )
    if dup:
        raise HTTPException(status_code=409, detail=f"{body.CodeType} / {body.CodeStr} 已存在")

    row = FoodSystemConfig(
        CodeNo     = body.CodeNo,
        CodeType   = body.CodeType,
        CodeStr    = body.CodeStr,
        CodeValue  = body.CodeValue,
        RoleID     = body.RoleID,
        CodeDesc   = body.CodeDesc,
        CodeSeq    = body.CodeSeq,
        StatusCode = "111",
        AddUser    = "admin",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _config_to_dict(row)


@router.put("/system-config/{code_id}")
def update_system_config(code_id: int, body: SystemConfigIn, db: Session = Depends(get_db)) -> dict:
    row: FoodSystemConfig | None = (
        db.query(FoodSystemConfig)
        .filter(FoodSystemConfig.CodeID == code_id, FoodSystemConfig.StatusCode == "111")
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="系統參數不存在")

    # 若鍵改了，檢查不可撞到其他啟用中的鍵
    if (row.CodeType, row.CodeStr) != (body.CodeType, body.CodeStr):
        dup = (
            db.query(FoodSystemConfig)
            .filter(
                FoodSystemConfig.CodeType == body.CodeType,
                FoodSystemConfig.CodeStr  == body.CodeStr,
                FoodSystemConfig.StatusCode == "111",
                FoodSystemConfig.CodeID  != code_id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=409, detail=f"{body.CodeType} / {body.CodeStr} 已存在")

    row.CodeNo    = body.CodeNo
    row.CodeType  = body.CodeType
    row.CodeStr   = body.CodeStr
    row.CodeValue = body.CodeValue
    row.RoleID    = body.RoleID
    row.CodeDesc  = body.CodeDesc
    row.CodeSeq   = body.CodeSeq
    row.UpdUser   = "admin"

    db.commit()
    db.refresh(row)
    return _config_to_dict(row)


@router.delete("/system-config/{code_id}", status_code=204)
def delete_system_config(code_id: int, db: Session = Depends(get_db)):
    """軟刪除：StatusCode → '000'，避免影響歷史稽核。"""
    row = (
        db.query(FoodSystemConfig)
        .filter(FoodSystemConfig.CodeID == code_id, FoodSystemConfig.StatusCode == "111")
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="系統參數不存在")
    row.StatusCode = "000"
    row.UpdUser    = "admin"
    db.commit()


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


# ═════════════════════════════════════════════════════════════════
# 訂單管理
# ═════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────
# GET /api/admin/orders
# ─────────────────────────────────────────────────────────────────
@router.get("/orders")
def list_orders_admin(
    status: str | None = Query(None, description="篩選狀態: OPEN / PAID / CANCELLED"),
    date:   str | None = Query(None, description="篩選日期 YYYY-MM-DD，不填代表今天"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    後台訂單列表，供廚房/收銀台使用。

    【查詢參數說明】
    - status: 不填 = 全部狀態；填 OPEN = 只看待備餐
    - date:   不填 = 今天；填 2026-05-21 = 看指定日期的訂單

    【為什麼加 selectinload？】
    orders 下面有 details（明細），details 下面有 food（餐點名稱），
    還有 table（桌位資訊）。
    用 selectinload 一次把三層關聯全部載入，
    避免每一筆訂單都多查一次 DB（N+1 問題）。
    """
    # ① 解析日期（預設今天）
    if date is None:
        filter_date = datetime.now().date()
    else:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式錯誤，請使用 YYYY-MM-DD")

    # ② 建立查詢
    q = (
        db.query(FoodOrder)
        .options(
            selectinload(FoodOrder.details).selectinload(FoodOrderDetail.food),
            selectinload(FoodOrder.table),
        )
        .filter(
            FoodOrder.StatusCode == "111",
            cast(FoodOrder.AddDate, Date) == filter_date,
        )
    )

    # ③ 狀態篩選（選填）
    if status:
        q = q.filter(FoodOrder.OrderStatus == status)

    orders = q.order_by(FoodOrder.AddDate.desc()).all()
    return [_order_to_dict(o) for o in orders]


def _order_to_dict(o: FoodOrder) -> dict:
    """把 FoodOrder ORM 物件轉成可序列化的 dict（含明細）"""
    return {
        "OrderID":     o.OrderID,
        "OrderNo":     o.OrderNo,
        "TableNo":     o.table.TableNo   if o.table else "?",
        "TableName":   o.table.TableName if o.table else None,
        "AddDate":     o.AddDate.strftime("%Y-%m-%d %H:%M:%S") if o.AddDate else "",
        "SubTotal":    float(o.SubTotal),
        "ServiceFee":  float(o.ServiceFee),
        "TotalAmount": float(o.TotalAmount),
        "OrderStatus": o.OrderStatus,
        # 方便前端顯示「共 N 道」
        "ItemCount":   sum(d.Quantity for d in o.details),
        "details": [
            {
                "FoodName":  d.food.FoodName if d.food else "（餐點已刪除）",
                "Quantity":  d.Quantity,
                "UnitPrice": float(d.UnitPrice),
                "Subtotal":  float(d.Subtotal),
                "Nickname":  d.Nickname,
                "Note":      d.Note,
            }
            for d in o.details
        ],
    }


# ─────────────────────────────────────────────────────────────────
# POST /api/admin/orders/{order_id}/cancel
# ─────────────────────────────────────────────────────────────────
@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, db: Session = Depends(get_db)) -> dict:
    """
    取消訂單：OPEN → CANCELLED。
    只有「待備餐」的訂單才能取消（已結帳的不能反悔）。

    注意：取消訂單不會自動讓桌位回到 IDLE，
    因為同一桌可能還有其他 OPEN 訂單。
    桌位清除請由「清桌」功能處理。
    """
    order = db.query(FoodOrder).filter(FoodOrder.OrderID == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    if order.OrderStatus != "OPEN":
        raise HTTPException(status_code=409, detail="只有待備餐的訂單可以取消")

    order.OrderStatus = "CANCELLED"
    db.commit()
    return {"detail": "訂單已取消", "OrderNo": order.OrderNo}
