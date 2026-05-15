from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodMenu(Base, AuditMixin):
    """系統選單 (後台左側導覽列)"""

    __tablename__ = "Food_Menu"

    MenuID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    MenuName: Mapped[str] = mapped_column(String(50), nullable=False, comment="選單名稱")
    MenuPath: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="前端路由")
    MenuIcon: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="圖示")
    ParentID: Mapped[int | None] = mapped_column(ForeignKey("Food_Menu.MenuID"), nullable=True, comment="父選單")
    Sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序")

    children = relationship("FoodMenu", remote_side=[MenuID])
    role_menus = relationship("FoodRoleMenu", back_populates="menu", cascade="all, delete-orphan")
