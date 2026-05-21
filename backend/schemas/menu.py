from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    CategoryID:   int
    CategoryName: str
    CategoryDesc: str | None
    Sort:         int


class CategoryBrief(BaseModel):
    """嵌在 FoodOut 裡的分類簡短格式"""
    model_config = ConfigDict(from_attributes=True)

    CategoryID:   int
    CategoryName: str


class PictureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    PictureID:   int
    PicturePath: str
    AltText:     str | None


class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    FoodID:      int
    FoodName:    str
    FoodDesc:    str | None
    Price:       Decimal
    categories:  list[CategoryBrief]   # ← 多對多，一道菜可有多個分類
    IsAvailable: str
    picture:     PictureOut | None
