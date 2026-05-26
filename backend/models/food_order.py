from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodOrder(Base, AuditMixin):
    """
    訂單主檔。

    每桌單次消費 = 一筆 FoodOrder。
    顧客「加點」時新增 OrderDetail 並關聯至同一張未結帳的 OrderID。
    Status: OPEN=未結帳 / PAID=已結帳 / CANCELLED=取消
    """

    __tablename__ = "Food_Order"

    OrderID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    OrderNo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, comment="訂單編號")
    TableID: Mapped[int] = mapped_column(ForeignKey("Food_Table.TableID"), nullable=False)

    SubTotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="餐點小計")
    DiscountAmount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="折扣金額")
    ServiceFee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="服務費")
    TotalAmount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="應付總額")

    OrderStatus: Mapped[str] = mapped_column(
        String(10), nullable=False, default="OPEN",
        comment="OPEN / PAID / CANCELLED",
    )
    PaymentMethod: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="付款方式")

    # 下單當下的桌位 SessionToken，用來區隔同一桌不同入座批次。
    # 顧客「我的訂單」依此過濾，避免新客人看到上一組客人的訂單。
    SessionToken: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="下單當下的桌位 Session，用於區隔不同入座批次"
    )

    table = relationship("FoodTable", back_populates="orders")
    details = relationship("FoodOrderDetail", back_populates="order", cascade="all, delete-orphan")
