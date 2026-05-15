from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodRoleMenu(Base, AuditMixin):
    """角色 ↔ 選單關聯,控制不同角色登入後台可見的頁面"""

    __tablename__ = "Food_RoleMenu"

    ID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    RoleID: Mapped[int] = mapped_column(ForeignKey("Food_Role.RoleID"), nullable=False)
    MenuID: Mapped[int] = mapped_column(ForeignKey("Food_Menu.MenuID"), nullable=False)

    role = relationship("FoodRole", back_populates="role_menus")
    menu = relationship("FoodMenu", back_populates="role_menus")
