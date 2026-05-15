"""
稽核欄位 Mixin
對應 tblsysCode (Pet_Dev_PI) 的設計風格:
  AddUser / AddDate / AddIpAddr  — 新增者 / 日期 / IP
  UpdUser / UpdDate / UpdIpAddr  — 更新者 / 日期 / IP
  StatusCode                     — 3 位狀態碼 (如 '111' 表示啟用)
"""
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    """與 tblsysCode 一致的稽核 / 狀態欄位。"""

    StatusCode: Mapped[str] = mapped_column(String(3), nullable=True, default="111", comment="狀態 111 啟用")

    AddUser: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="新增使用者")
    AddDate: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        comment="新增日期",
    )
    AddIpAddr: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="新增 IP")

    UpdUser: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="更新使用者")
    UpdDate: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        onupdate=func.now(),
        comment="更新日期",
    )
    UpdIpAddr: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="更新 IP")
