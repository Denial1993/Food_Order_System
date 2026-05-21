"""
餐點管理 Pydantic Schema（多對多分類版本）

【改動說明】
原本 FoodAdminIn 只有 CategoryID: int | None（單一分類）。
現在改成 CategoryIDs: list[int]（分類 ID 的陣列），支援多選。

例如：招牌雞腿飯 → CategoryIDs: [1, 2]  表示同時屬於「熱門推薦」和「主食」
"""
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────
# 前端送來的表單資料（新增 / 編輯 共用）
# ─────────────────────────────────────────────────────────────────
class FoodAdminIn(BaseModel):
    FoodName:    str        = Field(..., min_length=1, max_length=100)
    FoodDesc:    str | None = Field(None)
    Price:       float      = Field(..., ge=0)
    CategoryIDs: list[int]  = Field(default_factory=list, description="分類 ID 陣列，可多選")
    IsAvailable: str        = Field("Y", pattern="^[YN]$")
    Sort:        int        = Field(0)
    PicturePath: str | None = Field(None)
    PictureName: str | None = Field(None)
    AltText:     str | None = Field(None)


# ─────────────────────────────────────────────────────────────────
# 後端回傳的分類簡短格式（嵌在 FoodAdminOut 裡）
# ─────────────────────────────────────────────────────────────────
class CategoryBrief(BaseModel):
    CategoryID:   int
    CategoryName: str
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────
# 後端回傳的餐點資料
# ─────────────────────────────────────────────────────────────────
class FoodAdminOut(BaseModel):
    FoodID:      int
    FoodName:    str
    FoodDesc:    str | None
    Price:       float
    categories:  list[CategoryBrief]   # ← 改為 list，可能有多個分類
    IsAvailable: str
    Sort:        int
    StatusCode:  str
    PictureID:   int | None
    PicturePath: str | None
    PictureName: str | None
    AltText:     str | None

    model_config = {"from_attributes": True}
