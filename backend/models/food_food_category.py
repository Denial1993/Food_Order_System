"""
Food_FoodCategory — 餐點與分類的「多對多中間表」

【給新手的說明：什麼是多對多？】

  一對一：一個人只有一個身分證
  一對多：一個分類有很多道餐點（FoodCategory → FoodData）
  多對多：一道餐點屬於多個分類，同一個分類下也有多道餐點

  多對多的解法：在兩張表之間插入一張「中間表」，每一行代表一條關聯。
  例如：
    FoodID=1, CategoryID=1  ← 招牌雞腿飯 屬於 熱門推薦
    FoodID=1, CategoryID=2  ← 招牌雞腿飯 屬於 主食

【SQLAlchemy 中間表的寫法】
  不用 class，改用 Table() 物件。
  SQLAlchemy 會自動讀這個 Table 來做 JOIN，你不需要自己操作它。
"""
from sqlalchemy import Column, ForeignKey, Integer, Table

from database import Base

# Table() 物件：定義中間表的欄位結構
# ondelete="CASCADE"：如果刪掉餐點或分類，相關的中間表列自動刪除，不用手動清
food_category_association = Table(
    "Food_FoodCategory",        # PostgreSQL 裡的表名
    Base.metadata,              # 讓 SQLAlchemy 知道這張表的存在
    Column(
        "FoodID",
        Integer,
        ForeignKey("Food_FoodData.FoodID", ondelete="CASCADE"),
        primary_key=True,       # 複合主鍵：(FoodID, CategoryID) 不能重複
    ),
    Column(
        "CategoryID",
        Integer,
        ForeignKey("Food_Category.CategoryID", ondelete="CASCADE"),
        primary_key=True,
    ),
)
