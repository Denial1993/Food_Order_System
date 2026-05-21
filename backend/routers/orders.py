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
from schemas.order import OrderOut, OrderSubmitIn


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
            detail="訂單已送出或此桌不在點餐狀態，請勿重複送單",
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


@router.post("/checkout/{order_id}")
def checkout(order_id: int, db: Session = Depends(get_db)) -> dict:
    order = db.query(FoodOrder).filter(FoodOrder.OrderID == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    if order.OrderStatus != "OPEN":
        raise HTTPException(status_code=409, detail="此訂單已結帳")

    order.OrderStatus = "PAID"

    # 桌況回 IDLE
    table = db.query(FoodTable).filter(FoodTable.TableID == order.TableID).first()
    if table:
        table.TableStatus = "IDLE"

    db.commit()
    return {"detail": "結帳成功", "OrderNo": order.OrderNo}
