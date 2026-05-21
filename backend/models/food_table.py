import uuid

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodTable(Base, AuditMixin):
    """
    桌位主檔 + 狀態機。

    【狀態機說明】
      IDLE     空閒中  → 新客人入座，確認暱稱時自動切換到 ORDERING
      ORDERING 點餐中  → 顧客可下單、加點
      CLEANING 清潔中  → 結帳後進入，清潔完成後手動切回 IDLE

    【SessionToken 說明】
    每次從 IDLE 切換到 ORDERING 時，產生一個全新的 UUID（隨機字串）。
    顧客點餐時必須帶著這個 Token，後端才接受下單。
    這樣一來，就算有人把 QR Code 截圖帶回家，
    下次新客人入座時 Token 已經換掉，舊截圖就沒辦法亂點餐了。
    """

    __tablename__ = "Food_Table"

    TableID:     Mapped[int]       = mapped_column(Integer, primary_key=True, autoincrement=True)
    TableNo:     Mapped[str]       = mapped_column(String(10), unique=True, nullable=False, comment="桌號")
    TableName:   Mapped[str | None] = mapped_column(String(30), nullable=True, comment="桌名/區域")
    Seats:       Mapped[int | None] = mapped_column(Integer, nullable=True, comment="座位數")
    TableStatus: Mapped[str]       = mapped_column(
        String(10), nullable=False, default="IDLE",
        comment="IDLE / ORDERING / CLEANING",
    )
    # 每次開桌產生新 UUID，用來驗證顧客是否為「本次入座」的客人
    # UUID 格式: "550e8400-e29b-41d4-a716-446655440000"（36 個字元）
    SessionToken: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="開桌 Session，每次開桌重新產生"
    )

    carts  = relationship("FoodCart",  back_populates="table", cascade="all, delete-orphan")
    orders = relationship("FoodOrder", back_populates="table")

    def new_session(self) -> str:
        """產生並儲存新的 Session Token，回傳 Token 字串"""
        self.SessionToken = str(uuid.uuid4())
        return self.SessionToken
