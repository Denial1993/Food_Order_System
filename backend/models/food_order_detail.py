from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodOrderDetail(Base, AuditMixin):
    """
    訂單明細。
    UnitPrice 寫入下單當下的價格,避免日後改價影響歷史訂單。
    """

    __tablename__ = "Food_OrderDetail"

    DetailID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    OrderID: Mapped[int] = mapped_column(ForeignKey("Food_Order.OrderID"), nullable=False)
    FoodID: Mapped[int] = mapped_column(ForeignKey("Food_FoodData.FoodID"), nullable=False)
    Quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    UnitPrice: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="下單時單價")
    Subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="小計 = qty * price")
    Nickname: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="點餐人暱稱")
    Note: Mapped[str | None] = mapped_column(String(200), nullable=True)

    order = relationship("FoodOrder", back_populates="details")
    food = relationship("FoodData")
