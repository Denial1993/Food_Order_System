"""
DB seed -- run:
    cd backend
    python -X utf8 seed.py           ← 已有資料則略過
    python -X utf8 seed.py --reset   ← 清空所有表後重新建立（改了 schema 時用這個）
"""
import sys
import io

# 強制 stdout 使用 utf-8，避免 Windows cp950 無法輸出 emoji
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from database import Base, SessionLocal, engine
import models  # noqa: 確保所有 ORM 模型已註冊

from models import (
    FoodRole,
    FoodUser,
    FoodMenu,
    FoodRoleMenu,
    FoodTable,
    FoodCategory,
    FoodPicture,
    FoodData,
    FoodSystemConfig,
)
from decimal import Decimal


def seed() -> None:
    # ── --reset 旗標：清空全部表後重建 ─────────────────────────────
    if "--reset" in sys.argv:
        print("⚠️  --reset 模式：清空所有表，重新建立...")
        Base.metadata.drop_all(bind=engine)
        print("   ✓ 所有表已清除")

    Base.metadata.create_all(bind=engine)
    print("   ✓ 所有表已建立（含 Food_FoodCategory 多對多中間表）")

    db = SessionLocal()

    try:
        # ── 0. 如果已有資料就跳過 ─────────────────────────────────
        if db.query(FoodCategory).count() > 0:
            print("⚠️  資料庫已有資料，略過 seed。")
            print("   若要重置，請執行: python -X utf8 seed.py --reset")
            return

        # ── 1. 角色 ──────────────────────────────────────────────
        roles = [
            FoodRole(RoleName="店長",   RoleDesc="最高管理權限", StatusCode="111", AddUser="seed"),
            FoodRole(RoleName="工讀生", RoleDesc="基本操作權限", StatusCode="111", AddUser="seed"),
            FoodRole(RoleName="顧客",   RoleDesc="掃碼點餐",     StatusCode="111", AddUser="seed"),
        ]
        db.add_all(roles)
        db.flush()
        admin_role = roles[0]
        print(f"✅ 角色建立: {[r.RoleName for r in roles]}")

        # ── 2. 系統管理員帳號 ─────────────────────────────────────
        admin = FoodUser(
            Account="admin",
            Password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TiGniHZ9.W3bMGP9jI26fZALm5nG",  # admin123
            UserName="系統管理員",
            UserType="S",
            RoleID=admin_role.RoleID,
            StatusCode="111",
            AddUser="seed",
        )
        db.add(admin)
        db.flush()
        print("✅ 管理員帳號: admin / admin123")

        # ── 3. 後台選單 ───────────────────────────────────────────
        menus = [
            FoodMenu(MenuName="儀表板",   MenuPath="/admin/dashboard", MenuIcon="📊", Sort=1, StatusCode="111", AddUser="seed"),
            FoodMenu(MenuName="桌位管理", MenuPath="/admin/tables",    MenuIcon="🪑", Sort=2, StatusCode="111", AddUser="seed"),
            FoodMenu(MenuName="餐點管理", MenuPath="/admin/foods",     MenuIcon="🍱", Sort=3, StatusCode="111", AddUser="seed"),
            FoodMenu(MenuName="訂單列表", MenuPath="/admin/orders",    MenuIcon="📋", Sort=4, StatusCode="111", AddUser="seed"),
            FoodMenu(MenuName="系統參數", MenuPath="/admin/config",    MenuIcon="⚙️", Sort=5, StatusCode="111", AddUser="seed"),
        ]
        db.add_all(menus)
        db.flush()
        for m in menus:
            db.add(FoodRoleMenu(RoleID=admin_role.RoleID, MenuID=m.MenuID, StatusCode="111", AddUser="seed"))
        print(f"✅ 選單建立: {[m.MenuName for m in menus]}")

        # ── 4. 桌位 (10 桌) ───────────────────────────────────────
        tables = [
            FoodTable(TableNo="1",  TableName="靠窗A區", Seats=4, TableStatus="ORDERING", StatusCode="111", AddUser="seed"),
            FoodTable(TableNo="2",  TableName="靠窗A區", Seats=4, TableStatus="IDLE",     StatusCode="111", AddUser="seed"),
            FoodTable(TableNo="3",  TableName="靠窗A區", Seats=2, TableStatus="IDLE",     StatusCode="111", AddUser="seed"),
            FoodTable(TableNo="4",  TableName="中央B區", Seats=6, TableStatus="IDLE",     StatusCode="111", AddUser="seed"),
            FoodTable(TableNo="5",  TableName="中央B區", Seats=6, TableStatus="IDLE",     StatusCode="111", AddUser="seed"),
            FoodTable(TableNo="6",  TableName="中央B區", Seats=4, TableStatus="IDLE",     StatusCode="111", AddUser="seed"),
            FoodTable(TableNo="7",  TableName="包廂C區", Seats=8, TableStatus="IDLE",     StatusCode="111", AddUser="seed"),
            FoodTable(TableNo="8",  TableName="包廂C區", Seats=8, TableStatus="IDLE",     StatusCode="111", AddUser="seed"),
            FoodTable(TableNo="9",  TableName="吧台D區", Seats=2, TableStatus="IDLE",     StatusCode="111", AddUser="seed"),
            FoodTable(TableNo="10", TableName="吧台D區", Seats=2, TableStatus="IDLE",     StatusCode="111", AddUser="seed"),
        ]
        db.add_all(tables)
        db.flush()
        print("✅ 桌位建立: 桌號 1~10（桌號 1 預設開桌 ORDERING）")

        # ── 5. 餐點分類 ───────────────────────────────────────────
        categories = [
            FoodCategory(CategoryName="熱門推薦", CategoryDesc="本週最夯",   Sort=1, StatusCode="111", AddUser="seed"),
            FoodCategory(CategoryName="主食",     CategoryDesc="飯麵主餐",   Sort=2, StatusCode="111", AddUser="seed"),
            FoodCategory(CategoryName="小食",     CategoryDesc="輕食點心",   Sort=3, StatusCode="111", AddUser="seed"),
            FoodCategory(CategoryName="湯品",     CategoryDesc="暖胃湯品",   Sort=4, StatusCode="111", AddUser="seed"),
            FoodCategory(CategoryName="飲料",     CategoryDesc="冷熱飲品",   Sort=5, StatusCode="111", AddUser="seed"),
            FoodCategory(CategoryName="甜點",     CategoryDesc="甜蜜收尾",   Sort=6, StatusCode="111", AddUser="seed"),
        ]
        db.add_all(categories)
        db.flush()
        # 建立 name → object 的查找字典，後面方便用
        cat = {c.CategoryName: c for c in categories}
        print(f"✅ 分類建立: {[c.CategoryName for c in categories]}")

        # ── 6. 圖片（使用 picsum.photos 隨機圖）──────────────────
        pics = {
            "雞腿飯":   FoodPicture(PictureName="雞腿飯",   PicturePath="https://picsum.photos/seed/chickenrice/400/300",  AltText="香煎雞腿飯",     StatusCode="111", AddUser="seed"),
            "牛肉麵":   FoodPicture(PictureName="牛肉麵",   PicturePath="https://picsum.photos/seed/beefnoodle/400/300",   AltText="紅燒牛肉麵",     StatusCode="111", AddUser="seed"),
            "炒飯":     FoodPicture(PictureName="炒飯",     PicturePath="https://picsum.photos/seed/friedrice/400/300",    AltText="蛋炒飯",         StatusCode="111", AddUser="seed"),
            "排骨飯":   FoodPicture(PictureName="排骨飯",   PicturePath="https://picsum.photos/seed/porkrib/400/300",      AltText="炸排骨飯",       StatusCode="111", AddUser="seed"),
            "餃子":     FoodPicture(PictureName="餃子",     PicturePath="https://picsum.photos/seed/dumpling/400/300",     AltText="鍋貼水餃",       StatusCode="111", AddUser="seed"),
            "薯條":     FoodPicture(PictureName="薯條",     PicturePath="https://picsum.photos/seed/fries/400/300",        AltText="酥脆薯條",       StatusCode="111", AddUser="seed"),
            "玉米濃湯": FoodPicture(PictureName="玉米濃湯", PicturePath="https://picsum.photos/seed/cornsoup/400/300",     AltText="奶油玉米濃湯",   StatusCode="111", AddUser="seed"),
            "味噌湯":   FoodPicture(PictureName="味噌湯",   PicturePath="https://picsum.photos/seed/misosoup/400/300",     AltText="日式味噌湯",     StatusCode="111", AddUser="seed"),
            "珍珠奶茶": FoodPicture(PictureName="珍珠奶茶", PicturePath="https://picsum.photos/seed/bubbletea/400/300",    AltText="珍珠奶茶",       StatusCode="111", AddUser="seed"),
            "紅茶":     FoodPicture(PictureName="紅茶",     PicturePath="https://picsum.photos/seed/blacktea/400/300",     AltText="冰紅茶",         StatusCode="111", AddUser="seed"),
            "果汁":     FoodPicture(PictureName="果汁",     PicturePath="https://picsum.photos/seed/juice/400/300",        AltText="新鮮果汁",       StatusCode="111", AddUser="seed"),
            "布丁":     FoodPicture(PictureName="布丁",     PicturePath="https://picsum.photos/seed/pudding/400/300",      AltText="焦糖布丁",       StatusCode="111", AddUser="seed"),
            "蛋糕":     FoodPicture(PictureName="蛋糕",     PicturePath="https://picsum.photos/seed/cake/400/300",         AltText="古典巧克力蛋糕", StatusCode="111", AddUser="seed"),
        }
        db.add_all(pics.values())
        db.flush()

        # ── 7. 餐點（多對多分類）─────────────────────────────────
        #
        # 【重點】Cats 改成 list，可同時屬於多個分類：
        #   "招牌雞腿飯" Cats=["熱門推薦", "主食"]
        #   → 在 Food_FoodCategory 中會有兩筆記錄
        #
        foods_data = [
            # ── 跨兩個分類（熱門推薦 + 各自本分類）
            dict(FoodName="招牌雞腿飯",     FoodDesc="嚴選去骨雞腿，香煎至金黃，附湯品沙拉",           Price="150", Cats=["熱門推薦", "主食"], Pic="雞腿飯",   Sort=1),
            dict(FoodName="紅燒牛肉麵",     FoodDesc="澳洲牛腱慢燉4小時，湯頭濃郁醇厚",               Price="180", Cats=["熱門推薦", "主食"], Pic="牛肉麵",   Sort=2),
            dict(FoodName="珍珠奶茶",       FoodDesc="鮮奶+大葉紅茶，粉圓自製每日新鮮",               Price="65",  Cats=["熱門推薦", "飲料"], Pic="珍珠奶茶", Sort=3),
            dict(FoodName="焦糖布丁",       FoodDesc="每日現烤，入口即化的法式焦糖風味",               Price="55",  Cats=["熱門推薦", "甜點"], Pic="布丁",     Sort=4),
            # ── 主食（單一分類）
            dict(FoodName="蛋炒飯",         FoodDesc="三顆雞蛋、白飯、蔥花、醬油提香",                 Price="100", Cats=["主食"],             Pic="炒飯",     Sort=5),
            dict(FoodName="炸排骨飯",       FoodDesc="酥炸豬里肌，附飯、燙青菜、酸黃瓜",               Price="130", Cats=["主食"],             Pic="排骨飯",   Sort=6),
            # ── 小食
            dict(FoodName="鍋貼 (6入)",     FoodDesc="豬肉高麗菜內餡，煎至底部金黃酥脆",               Price="70",  Cats=["小食"],             Pic="餃子",     Sort=1),
            dict(FoodName="水餃 (10入)",    FoodDesc="韭黃豬肉水餃，皮薄Q彈，附辣椒醬",               Price="80",  Cats=["小食"],             Pic="餃子",     Sort=2),
            dict(FoodName="黃金薯條",       FoodDesc="比利時品種馬鈴薯，外酥內軟，附番茄醬",           Price="60",  Cats=["小食"],             Pic="薯條",     Sort=3),
            # ── 湯品
            dict(FoodName="奶油玉米濃湯",   FoodDesc="香甜玉米粒、奶油、鮮奶油，附麵包丁",             Price="50",  Cats=["湯品"],             Pic="玉米濃湯", Sort=1),
            dict(FoodName="日式味噌湯",     FoodDesc="白味噌、豆腐、海帶芽、蔥花",                     Price="35",  Cats=["湯品"],             Pic="味噌湯",   Sort=2),
            # ── 飲料（珍珠奶茶已在熱門推薦，這裡加其他飲料）
            dict(FoodName="冰紅茶",         FoodDesc="阿薩姆紅茶，微糖冰塊，清爽不甜膩",               Price="30",  Cats=["飲料"],             Pic="紅茶",     Sort=2),
            dict(FoodName="現打果汁",       FoodDesc="時令水果現榨，每日品項不同請洽店員",             Price="80",  Cats=["飲料"],             Pic="果汁",     Sort=3),
            # ── 甜點（焦糖布丁已在熱門推薦，這裡加其他甜點）
            dict(FoodName="古典巧克力蛋糕", FoodDesc="比利時黑巧克力，入口即化，附香草冰淇淋",         Price="90",  Cats=["甜點"],             Pic="蛋糕",     Sort=2),
        ]

        # ── 第一步：建立餐點物件，先不指定分類 ─────────────────────
        # 原因：多對多中間表 (Food_FoodCategory) 的 INSERT 需要知道 FoodID，
        # 但 FoodID 是資料庫 autoincrement 的，flush() 之後才會有值。
        # 所以必須先 add + flush 拿到 ID，再賦值 categories。
        food_objs    = []
        food_cats    = []   # 對應的分類名稱 list，暫存等 flush 後再用
        for f in foods_data:
            food_obj = FoodData(
                FoodName    = f["FoodName"],
                FoodDesc    = f["FoodDesc"],
                Price       = Decimal(f["Price"]),
                PictureID   = pics[f["Pic"]].PictureID,
                IsAvailable = "Y",
                Sort        = f["Sort"],
                StatusCode  = "111",
                AddUser     = "seed",
            )
            food_objs.append(food_obj)
            food_cats.append(f["Cats"])

        db.add_all(food_objs)
        db.flush()   # ← 這裡讓 DB 分配好所有 FoodID

        # ── 第二步：flush 後才指定分類（SQLAlchemy 才能正確寫中間表）───
        for food_obj, cats in zip(food_objs, food_cats):
            food_obj.categories = [cat[name] for name in cats]

        db.flush()   # ← 把 Food_FoodCategory 中間表的記錄寫入
        print(f"✅ 餐點建立: {len(food_objs)} 道（部分餐點跨多分類）")

        # ── 8. 系統參數 ───────────────────────────────────────────
        configs = [
            FoodSystemConfig(CodeNo="00", CodeType="系統參數", CodeStr="SERVICE_FEE_RATE",  CodeValue="0.10",     RoleID=0, CodeDesc="服務費率 10%",      CodeSeq="001", StatusCode="111", AddUser="seed"),
            FoodSystemConfig(CodeNo="00", CodeType="系統參數", CodeStr="BUSINESS_STATUS",   CodeValue="OPEN",     RoleID=0, CodeDesc="營業狀態",           CodeSeq="002", StatusCode="111", AddUser="seed"),
            FoodSystemConfig(CodeNo="00", CodeType="系統參數", CodeStr="ALLOW_TAKEOUT",     CodeValue="N",        RoleID=0, CodeDesc="是否開放外帶",        CodeSeq="003", StatusCode="111", AddUser="seed"),
            FoodSystemConfig(CodeNo="00", CodeType="系統參數", CodeStr="LAST_ORDER_NOTICE", CodeValue="30",       RoleID=0, CodeDesc="最後點餐提示(分鐘)",  CodeSeq="004", StatusCode="111", AddUser="seed"),
            FoodSystemConfig(CodeNo="01", CodeType="付款方式", CodeStr="PAY_CASH",          CodeValue="現金",     RoleID=0, CodeDesc="現金付款",            CodeSeq="001", StatusCode="111", AddUser="seed"),
            FoodSystemConfig(CodeNo="01", CodeType="付款方式", CodeStr="PAY_CARD",          CodeValue="信用卡",   RoleID=0, CodeDesc="信用卡",              CodeSeq="002", StatusCode="111", AddUser="seed"),
            FoodSystemConfig(CodeNo="01", CodeType="付款方式", CodeStr="PAY_LINEPAY",       CodeValue="LINE Pay", RoleID=0, CodeDesc="行動支付",            CodeSeq="003", StatusCode="111", AddUser="seed"),
        ]
        db.add_all(configs)
        db.flush()
        print(f"✅ 系統參數建立: {len(configs)} 筆")

        db.commit()
        print("\n🎉 Seed 完成！")
        print("   前台測試: http://localhost:5173/order?table=1")
        print("   後台測試: http://localhost:5173/admin")
        print("   API Docs: http://localhost:8000/docs")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed()
