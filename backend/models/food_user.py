from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from ._mixins import AuditMixin


class FoodUser(Base, AuditMixin):
    """使用者:店家管理員 / 掃碼下單顧客 (臨時)"""

    __tablename__ = "Food_User"

    UserID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Account: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, comment="登入帳號 (店家用)")
    Password: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="bcrypt 雜湊密碼")
    UserName: Mapped[str] = mapped_column(String(50), nullable=False, comment="姓名 / 顧客暱稱")
    UserType: Mapped[str] = mapped_column(
        String(10), nullable=False, default="C", comment="使用者類型 S=店家 / C=顧客"
    )
    RoleID: Mapped[int | None] = mapped_column(ForeignKey("Food_Role.RoleID"), nullable=True)

    role = relationship("FoodRole", back_populates="users")
