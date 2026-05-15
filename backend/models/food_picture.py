from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodPicture(Base, AuditMixin):
    """圖片庫 — 集中管理餐點圖片路徑與屬性"""

    __tablename__ = "Food_Picture"

    PictureID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    PictureName: Mapped[str] = mapped_column(String(100), nullable=False, comment="圖片名稱")
    PicturePath: Mapped[str] = mapped_column(String(500), nullable=False, comment="檔案路徑 / URL")
    AltText: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="替代文字")

    foods = relationship("FoodData", back_populates="picture")
