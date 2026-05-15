from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodCategory(Base, AuditMixin):
    """餐點分類 (早餐 / 午餐 / 熱門...)"""

    __tablename__ = "Food_Category"

    CategoryID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    CategoryName: Mapped[str] = mapped_column(String(30), nullable=False, comment="分類名稱")
    CategoryDesc: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="說明")
    Sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序")

    foods = relationship("FoodData", back_populates="category")
