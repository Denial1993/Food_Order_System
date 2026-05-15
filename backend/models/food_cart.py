from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodCart(Base, AuditMixin):
    """
    共用購物車暫存。
    多位同桌顧客 (UserID 區分) 共享同一 TableID 的購物車。
    送出訂單後即清空該桌紀錄。
    """

    __tablename__ = "Food_Cart"
    __table_args__ = (
        UniqueConstraint("TableID", "FoodID", "UserID", name="uq_cart_table_food_user"),
    )

    CartID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    TableID: Mapped[int] = mapped_column(ForeignKey("Food_Table.TableID"), nullable=False)
    FoodID: Mapped[int] = mapped_column(ForeignKey("Food_FoodData.FoodID"), nullable=False)
    Quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    UserID: Mapped[int | None] = mapped_column(ForeignKey("Food_User.UserID"), nullable=True)
    Nickname: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="顧客暱稱 (前端 LocalStorage 帶入)")
    Note: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="備註 / 客製需求")

    table = relationship("FoodTable", back_populates="carts")
    food = relationship("FoodData")
    user = relationship("FoodUser")
