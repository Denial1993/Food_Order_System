"""
系統參數 Pydantic Schema

對應 Food_SystemConfig (tblsysCode 風格)。
新增/編輯共用同一個 Schema，必填欄位是 CodeType / CodeStr / CodeValue。
"""
from pydantic import BaseModel, Field


class SystemConfigIn(BaseModel):
    CodeNo:    str | None = Field(None, max_length=5,  description="類型代碼，例 00=系統參數")
    CodeType:  str        = Field(..., min_length=1, max_length=10, description="分類，例 系統參數 / 付款方式")
    CodeStr:   str        = Field(..., min_length=1, max_length=30, description="參數鍵，例 SERVICE_FEE_RATE")
    CodeValue: str        = Field(..., max_length=100, description="參數值，例 0.10")
    RoleID:    int        = Field(0, ge=0, description="權限分流，0=不限")
    CodeDesc:  str | None = Field(None, max_length=50)
    CodeSeq:   str | None = Field(None, max_length=3, description="排序代碼，3 位字串")


class SystemConfigOut(BaseModel):
    CodeID:     int
    CodeNo:     str | None
    CodeType:   str | None
    CodeStr:    str | None
    CodeValue:  str | None
    RoleID:     int
    CodeDesc:   str | None
    CodeSeq:    str | None
    StatusCode: str | None

    model_config = {"from_attributes": True}
