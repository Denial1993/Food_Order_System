"""
餐點管理 Pydantic Schema

【給新手的說明】
Schema 的用途：定義「前端傳來的 JSON 長什麼樣子」以及「後端回傳的 JSON 長什麼樣子」。
FastAPI 會自動用這個做驗證，如果前端沒傳必填欄位，就會自動回 422 錯誤。
"""
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────
# 前端送來的表單資料（新增 / 編輯 共用同一個格式）
# ─────────────────────────────────────────────────────────────────
class FoodAdminIn(BaseModel):
    FoodName:    str            = Field(..., min_length=1, max_length=100, description="餐點名稱")
    FoodDesc:    str | None     = Field(None, description="餐點描述")
    Price:       float          = Field(..., ge=0, description="售價（不可為負數）")
    CategoryID:  int | None     = Field(None, description="分類 ID（可為空）")
    IsAvailable: str            = Field("Y", pattern="^[YN]$", description="是否供應 Y/N")
    Sort:        int            = Field(0, description="排序數字，越小越前面")
    # 圖片相關（選填）—— 如果有填 PicturePath，就會建立或更新圖片記錄
    PicturePath: str | None     = Field(None, description="圖片 URL 或相對路徑")
    PictureName: str | None     = Field(None, description="圖片名稱（留空自動用餐點名稱）")
    AltText:     str | None     = Field(None, description="圖片替代文字（SEO 用）")


# ─────────────────────────────────────────────────────────────────
# 後端回傳的餐點資料（單筆或列表）
# ─────────────────────────────────────────────────────────────────
class FoodAdminOut(BaseModel):
    FoodID:      int
    FoodName:    str
    FoodDesc:    str | None
    Price:       float
    CategoryID:  int | None
    CategoryName: str | None    # 關聯查來的分類名稱
    IsAvailable: str
    Sort:        int
    StatusCode:  str
    # 圖片
    PictureID:   int | None
    PicturePath: str | None
    PictureName: str | None
    AltText:     str | None

    model_config = {"from_attributes": True}
