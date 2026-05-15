from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodRole(Base, AuditMixin):
    """角色 (店長、工讀生、顧客...)"""

    __tablename__ = "Food_Role"

    RoleID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    RoleName: Mapped[str] = mapped_column(String(30), nullable=False, comment="角色名稱")
    RoleDesc: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="角色說明")

    users = relationship("FoodUser", back_populates="role")
    role_menus = relationship("FoodRoleMenu", back_populates="role", cascade="all, delete-orphan")
