from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodTable(Base, AuditMixin):
    """
    桌位主檔 + 狀態機。

    TableStatus 取代 GPS 定位,作為「開桌 / 點餐 / 清潔」的防呆控制:
      - IDLE     空閒中  (掃碼會跳通知店員開桌)
      - ORDERING 點餐中  (可下單 / 加點)
      - CLEANING 清潔中  (結帳後重置,連結失效)
    """

    __tablename__ = "Food_Table"

    TableID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    TableNo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, comment="桌號")
    TableName: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="桌名/區域")
    Seats: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="座位數")
    TableStatus: Mapped[str] = mapped_column(
        String(10), nullable=False, default="IDLE",
        comment="IDLE / ORDERING / CLEANING",
    )

    carts = relationship("FoodCart", back_populates="table", cascade="all, delete-orphan")
    orders = relationship("FoodOrder", back_populates="table")
