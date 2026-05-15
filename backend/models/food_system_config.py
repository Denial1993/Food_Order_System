"""
Food_SystemConfig — 全站環境變數表。

設計範本來自 Pet_Dev_PI.dbo.tblsysCode:
  CodeID (PK) / CodeNo / CodeType / CodeStr / CodeValue
  RoleID (權限分流,預設 0 = 不限)
  CodeDesc / CodeSeq / StatusCode
  + AuditMixin (AddUser/AddDate/AddIpAddr/UpdUser/UpdDate/UpdIpAddr)

範例資料 (對應規格書):
  CodeType='系統參數', CodeStr='SERVICE_FEE_RATE', CodeValue='0.10'  → 10% 服務費
  CodeType='系統參數', CodeStr='BUSINESS_STATUS', CodeValue='OPEN'   → 營業中
  CodeType='餐點分類', CodeStr='FAQ_TYPE', CodeValue='早餐', CodeSeq='001'
"""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from ._mixins import AuditMixin


class FoodSystemConfig(Base, AuditMixin):
    __tablename__ = "Food_SystemConfig"

    CodeID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="代碼識別子")
    CodeNo: Mapped[str | None] = mapped_column(String(5), nullable=True, comment="類型代碼")
    CodeType: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="類型")
    CodeStr: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="系統參數鍵")
    CodeValue: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="系統代碼/值")
    RoleID: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="使用角色權限,0=不限")
    CodeDesc: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="簡易說明")
    CodeSeq: Mapped[str | None] = mapped_column(String(3), nullable=True, comment="排序")
