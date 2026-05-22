from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class CartItemIn(BaseModel):
    """前端送來的購物車單項"""
    food_id: int
    quantity: int = 1
    nickname: str | None = None
    note: str | None = None


class OrderSubmitIn(BaseModel):
    """POST /orders/submit/{table_id} 的 Request Body"""
    cart:          list[CartItemIn]
    nickname:      str | None = None    # 下單人暱稱
    session_token: str | None = None    # 開桌時拿到的 UUID，驗證是否為本次入座的客人


class CancelCustomerIn(BaseModel):
    """POST /orders/{order_id}/cancel-customer 的 Request Body"""
    session_token: str | None = None    # 必須符合桌位目前的 SessionToken


class OrderDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    FoodID: int
    FoodName: str = ""   # 由 router 動態注入 detail.FoodName = detail.food.FoodName
    Quantity: int
    UnitPrice: Decimal
    Subtotal: Decimal
    Nickname: str | None
    Note: str | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    OrderID: int
    OrderNo: str
    SubTotal: Decimal
    DiscountAmount: Decimal
    ServiceFee: Decimal
    TotalAmount: Decimal
    OrderStatus: str
    AddDate: str = ""          # 送單時間 (ISO 格式，由 router 注入)
    details: list[OrderDetailOut] = []
