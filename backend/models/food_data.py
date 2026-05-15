from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodData(Base, AuditMixin):
    """餐點總表"""

    __tablename__ = "Food_FoodData"

    FoodID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    FoodName: Mapped[str] = mapped_column(String(100), nullable=False, comment="餐點名稱")
    FoodDesc: Mapped[str | None] = mapped_column(Text, nullable=True, comment="餐點描述")
    Price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="單價")
    CategoryID: Mapped[int | None] = mapped_column(ForeignKey("Food_Category.CategoryID"), nullable=True)
    PictureID: Mapped[int | None] = mapped_column(ForeignKey("Food_Picture.PictureID"), nullable=True)
    Stock: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="庫存 (NULL = 不管控)")
    IsAvailable: Mapped[str] = mapped_column(
        String(1), nullable=False, default="Y", comment="是否供應中 Y/N"
    )
    Sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序")

    category = relationship("FoodCategory", back_populates="foods")
    picture = relationship("FoodPicture", back_populates="foods")
