from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin
from .food_food_category import food_category_association   # 引入中間表定義


class FoodData(Base, AuditMixin):
    """
    餐點總表

    【分類設計說明】
    原先用單一 CategoryID 外鍵 → 一道餐點只能屬於一個分類。
    現在改用多對多 `categories` 關係 → 一道餐點可同時屬於「熱門推薦」和「主食」。
    中間表 Food_FoodCategory 負責儲存這些對應關係。
    """

    __tablename__ = "Food_FoodData"

    FoodID:      Mapped[int]       = mapped_column(Integer, primary_key=True, autoincrement=True)
    FoodName:    Mapped[str]       = mapped_column(String(100), nullable=False,  comment="餐點名稱")
    FoodDesc:    Mapped[str | None] = mapped_column(Text, nullable=True,          comment="餐點描述")
    Price:       Mapped[Decimal]   = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="單價")
    PictureID:   Mapped[int | None] = mapped_column(ForeignKey("Food_Picture.PictureID"), nullable=True)
    Stock:       Mapped[int | None] = mapped_column(Integer, nullable=True,       comment="庫存 (NULL = 不管控)")
    IsAvailable: Mapped[str]       = mapped_column(String(1), nullable=False, default="Y", comment="是否供應中 Y/N")
    Sort:        Mapped[int]       = mapped_column(Integer, nullable=False, default=0, comment="排序")

    # ── 多對多關係：透過 food_category_association 中間表連到 FoodCategory ──
    # secondary = 中間表
    # back_populates = FoodCategory 那邊對應的屬性名稱
    categories = relationship(
        "FoodCategory",
        secondary=food_category_association,
        back_populates="foods",
    )

    picture = relationship("FoodPicture", back_populates="foods")
