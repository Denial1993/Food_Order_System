from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    CategoryID: int
    CategoryName: str
    CategoryDesc: str | None
    Sort: int


class PictureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    PictureID: int
    PicturePath: str
    AltText: str | None


class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    FoodID: int
    FoodName: str
    FoodDesc: str | None
    Price: Decimal
    CategoryID: int | None
    IsAvailable: str
    picture: PictureOut | None
