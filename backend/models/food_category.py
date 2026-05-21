from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin
from .food_food_category import food_category_association   # 引入同一個中間表


class FoodCategory(Base, AuditMixin):
    """
    餐點分類

    一個分類下有多道餐點，一道餐點也可屬於多個分類。
    透過 food_category_association 中間表實現多對多。
    """

    __tablename__ = "Food_Category"

    CategoryID:   Mapped[int]       = mapped_column(Integer, primary_key=True, autoincrement=True)
    CategoryName: Mapped[str]       = mapped_column(String(30), nullable=False, comment="分類名稱")
    CategoryDesc: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="說明")
    Sort:         Mapped[int]       = mapped_column(Integer, nullable=False, default=0, comment="排序")

    # 多對多：此分類下的所有餐點
    foods = relationship(
        "FoodData",
        secondary=food_category_association,
        back_populates="categories",
    )
