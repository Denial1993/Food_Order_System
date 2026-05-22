"""
訂單 API。

POST /orders/submit/{table_id}
  - SELECT ... FOR UPDATE 悲觀鎖，防止同桌兩人同毫秒重複送單
  - 從 Food_SystemConfig 讀取 SERVICE_FEE_RATE
  - 建立 Food_Order + Food_OrderDetail
  - 回傳訂單資訊

POST /orders/checkout/{order_id}
  - 標記訂單 PAID，桌況回 IDLE
"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import FoodData, FoodOrder, FoodOrderDetail, FoodSystemConfig, FoodTable
from schemas.order import OrderOut, OrderSubmitIn, CancelCustomerIn


def _enrich_order(order: FoodOrder) -> FoodOrder:
    """把 detail.FoodName 和 AddDate 字串注入 ORM 物件，讓 Pydantic schema 能序列化"""
    for det in order.details:
        det.FoodName = det.food.FoodName if det.food else ""   # type: ignore[attr-defined]
    order.AddDate = (                                           # type: ignore[attr-defined]
        order.AddDate.strftime("%Y-%m-%d %H:%M:%S") if order.AddDate else ""
    )
    return order

router = APIRouter()


def _get_service_fee_rate(db: Session) -> Decimal:
    """從 Food_SystemConfig 讀取服務費率，找不到預設 0%"""
    cfg = (
        db.query(FoodSystemConfig)
        .filter(
            FoodSystemConfig.CodeStr == "SERVICE_FEE_RATE",
            FoodSystemConfig.StatusCode == "111",
        )
        .first()
    )
    if cfg and cfg.CodeValue:
        try:
            return Decimal(cfg.CodeValue)
        except Exception:
            pass
    return Decimal("0")


def _make_order_no(table_no: str) -> str:
    """產生訂單編號: ORD-YYYYMMDD-桌號-時間戳末4碼"""
    now = datetime.now()
    ts = str(int(now.timestamp()))[-4:]
    return f"ORD-{now.strftime('%Y%m%d')}-T{table_no}-{ts}"


@router.get("/table/{table_id}", response_model=list[OrderOut])
def get_table_orders(table_id: int, db: Session = Depends(get_db)) -> list[FoodOrder]:
    """查詢某桌的所有訂單（含明細），供顧客「我的訂單」頁使用"""
    orders = (
        db.query(FoodOrder)
        .options(selectinload(FoodOrder.details).selectinload(FoodOrderDetail.food))
        .filter(FoodOrder.TableID == table_id)
        .order_by(FoodOrder.AddDate.desc())
        .all()
    )
    return [_enrich_order(o) for o in orders]


@router.post("/submit/{table_id}", response_model=OrderOut)
def submit_order(
    table_id: int,
    body: OrderSubmitIn,
    db: Session = Depends(get_db),
) -> FoodOrder:
    # ── 1. 悲觀鎖：鎖定桌位，防止重複送單 ────────────────────────
    stmt = select(FoodTable).where(FoodTable.TableID == table_id).with_for_update()
    table = db.execute(stmt).scalar_one_or_none()

    if not table:
        raise HTTPException(status_code=404, detail="桌號不存在")
    if table.TableStatus != "ORDERING":
        raise HTTPException(
            status_code=409,
            detail="此桌不在點餐狀態，請重新掃描 QR Code",
        )

    # ── Session Token 驗證 ───────────────────────────────────────
    # 驗證顧客帶來的 Token 是否和桌位記錄的 Token 相同。
    # 如果有人把 QR Code 截圖帶回家，當桌位被新客人開桌後，
    # Token 已經更換，舊的 Token 就會在這裡被擋下來。
    #
    # table.SessionToken 為 None 時代表「舊資料沒有 Token，跳過驗證」
    # 這樣可以相容尚未升級的舊桌位記錄
    if table.SessionToken and body.session_token != table.SessionToken:
        raise HTTPException(
            status_code=403,
            detail="連線已過期，請重新掃描 QR Code 入座",
        )

    if not body.cart:
        raise HTTPException(status_code=400, detail="購物車是空的")

    # ── 2. 讀取餐點資料（一次查詢拿全部，避免 N+1）───────────────
    food_ids = [item.food_id for item in body.cart]
    foods: dict[int, FoodData] = {
        f.FoodID: f
        for f in db.query(FoodData).filter(FoodData.FoodID.in_(food_ids)).all()
    }

    # 檢查是否有不存在的餐點
    missing = [fid for fid in food_ids if fid not in foods]
    if missing:
        raise HTTPException(status_code=400, detail=f"餐點 ID {missing} 不存在")

    # ── 3. 計算金額 ───────────────────────────────────────────────
    fee_rate = _get_service_fee_rate(db)
    subtotal = Decimal("0")
    details_data = []

    for item in body.cart:
        food = foods[item.food_id]
        unit_price = food.Price
        item_subtotal = unit_price * item.quantity
        subtotal += item_subtotal
        details_data.append(
            dict(
                food=food,
                quantity=item.quantity,
                unit_price=unit_price,
                item_subtotal=item_subtotal,
                nickname=item.nickname or body.nickname,
                note=item.note,
            )
        )

    service_fee = (subtotal * fee_rate).quantize(Decimal("1"))
    total = subtotal + service_fee

    # ── 4. 建立 Food_Order ────────────────────────────────────────
    order = FoodOrder(
        OrderNo=_make_order_no(table.TableNo),
        TableID=table_id,
        SubTotal=subtotal,
        DiscountAmount=Decimal("0"),
        ServiceFee=service_fee,
        TotalAmount=total,
        OrderStatus="OPEN",
        AddUser=body.nickname or "guest",
        StatusCode="111",
    )
    db.add(order)
    db.flush()  # 取得 OrderID

    # ── 5. 建立 Food_OrderDetail ──────────────────────────────────
    for d in details_data:
        detail = FoodOrderDetail(
            OrderID=order.OrderID,
            FoodID=d["food"].FoodID,
            Quantity=d["quantity"],
            UnitPrice=d["unit_price"],
            Subtotal=d["item_subtotal"],
            Nickname=d["nickname"],
            Note=d["note"],
            AddUser=body.nickname or "guest",
            StatusCode="111",
        )
        db.add(detail)

    db.commit()

    # ── 6. 重新載入 + 組出回應 ────────────────────────────────────
    db.refresh(order)
    order_with_details = (
        db.query(FoodOrder)
        .options(selectinload(FoodOrder.details).selectinload(FoodOrderDetail.food))
        .filter(FoodOrder.OrderID == order.OrderID)
        .one()
    )

    return _enrich_order(order_with_details)


def _get_cancel_window(db: Session) -> int:
    """從 Food_SystemConfig 讀取顧客取消視窗（分鐘），找不到預設 5 分鐘"""
    cfg = (
        db.query(FoodSystemConfig)
        .filter(
            FoodSystemConfig.CodeStr == "CANCEL_WINDOW_MINUTES",
            FoodSystemConfig.StatusCode == "111",
        )
        .first()
    )
    if cfg and cfg.CodeValue:
        try:
            return int(cfg.CodeValue)
        except Exception:
            pass
    return 5


@router.post("/cancel-customer/{order_id}")
def cancel_order_by_customer(
    order_id: int,
    body: CancelCustomerIn,
    db: Session = Depends(get_db),
) -> dict:
    """
    顧客自助取消訂單。

    【業務規則】
    1. 只能取消狀態為 OPEN（尚未備餐完成）的訂單。
    2. 下單後超過 CANCEL_WINDOW_MINUTES（預設 5 分鐘）不可再取消。
       — 廚房可能已開始備餐，食材損耗不宜退單。
    3. 必須持有本次桌位的 SessionToken，防止陌生人取消別桌的訂單。
       — 結帳或重新開桌後 Token 更換，舊 Session 的顧客無法取消新訂單。
    4. 取消後桌位狀態維持 ORDERING，不影響同桌其他未結帳訂單。
    """
    order: FoodOrder | None = (
        db.query(FoodOrder)
        .filter(FoodOrder.OrderID == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    if order.OrderStatus != "OPEN":
        raise HTTPException(
            status_code=409,
            detail="只有「備餐中」的訂單可以取消",
        )

    # ── Token 驗證：確認是本次入座的客人 ─────────────────────────
    table: FoodTable | None = (
        db.query(FoodTable)
        .filter(FoodTable.TableID == order.TableID)
        .first()
    )
    if table and table.SessionToken:
        if body.session_token != table.SessionToken:
            raise HTTPException(
                status_code=403,
                detail="連線已過期，無法取消此訂單",
            )

    # ── 時間視窗：下單後 N 分鐘內才允許取消 ──────────────────────
    if order.AddDate:
        minutes_since = (datetime.now() - order.AddDate).total_seconds() / 60
        window = _get_cancel_window(db)
        if minutes_since > window:
            raise HTTPException(
                status_code=409,
                detail=f"下單後超過 {window} 分鐘，無法自行取消，請聯絡店員",
            )

    order.OrderStatus = "CANCELLED"
    order.UpdUser = "customer"
    db.commit()
    return {"detail": "訂單已取消", "OrderNo": order.OrderNo}


@router.post("/checkout/{order_id}")
def checkout(order_id: int, db: Session = Depends(get_db)) -> dict:
    """
    結帳：OPEN → PAID。

    【為什麼桌況改成 CLEANING 而不是 IDLE？】

    如果直接回 IDLE，桌子立刻變成「可點餐」狀態，
    任何人只要掃舊的 QR Code 截圖就能把桌子自動開起來並下單。

    改成 CLEANING 後：
      1. SessionToken 立刻清除 → 舊截圖永遠無效
      2. 桌子進入「清潔中」狀態 → 無法點餐，無法自動開桌
      3. 店員確認桌面清潔完畢後，手動點「清桌完成」→ 才回到 IDLE
      4. 下一組客人掃碼 → 自動開桌 → 產生全新 Token

    攻擊者的唯一成功條件：必須在「店員把桌子設回 IDLE 之後、
    下一組客人掃碼開桌之前」的短暫空窗內掃碼——
    但這段時間桌子是 IDLE 而非 ORDERING，
    攻擊者雖然能自動開桌，但等同於幫下一組開桌，
    下一組客人的新 Session 會立刻把攻擊者的 Token 覆蓋掉。
    實務上這個風險極低。
    """
    order = db.query(FoodOrder).filter(FoodOrder.OrderID == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    if order.OrderStatus != "OPEN":
        raise HTTPException(status_code=409, detail="此訂單已結帳")

    order.OrderStatus = "PAID"

    # ── 桌況 → CLEANING（而非直接回 IDLE）──────────────────────
    table = db.query(FoodTable).filter(FoodTable.TableID == order.TableID).first()
    if table:
        table.TableStatus  = "CLEANING"
        table.SessionToken = None   # ← Token 立刻清除，舊截圖即刻失效

    db.commit()
    return {"detail": "結帳成功", "OrderNo": order.OrderNo}
