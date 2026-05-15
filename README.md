# Food Order System

QR Code 手機點餐系統 — 依規格書建立的開發骨架。

## 技術棧

- **後端**:Python 3.11+ / FastAPI / SQLAlchemy 2 / PostgreSQL 15
- **前端**:Vue 3 / Vite / TypeScript / Tailwind CSS / Pinia / vue-router
- **即時同步**:WebSocket (FastAPI 內建)
- **容器化**:Docker Compose (PostgreSQL + pgAdmin)

## 目錄結構

```
Food_Order_System/
├── backend/
│   ├── main.py              FastAPI 入口
│   ├── database.py          SQLAlchemy engine / Session / Base
│   ├── core/config.py       pydantic-settings 環境設定
│   ├── models/              ORM (12 張表)
│   │   ├── _mixins.py       AuditMixin (對應 tblsysCode 稽核欄位)
│   │   ├── food_role.py     角色
│   │   ├── food_user.py     使用者
│   │   ├── food_menu.py     後台選單
│   │   ├── food_role_menu.py 角色 ↔ 選單
│   │   ├── food_table.py    桌位 + 狀態機 (IDLE/ORDERING/CLEANING)
│   │   ├── food_category.py 餐點分類
│   │   ├── food_picture.py  圖片庫
│   │   ├── food_data.py     餐點主檔
│   │   ├── food_cart.py     共用購物車暫存
│   │   ├── food_order.py    訂單主檔
│   │   ├── food_order_detail.py 訂單明細
│   │   └── food_system_config.py 全站環境變數 (參考 tblsysCode)
│   ├── routers/
│   │   ├── auth.py / tables.py / menu.py / cart.py / orders.py / admin.py
│   │   └── ws.py            WebSocket 同桌即時同步
│   └── schemas/             Pydantic I/O 模型
├── frontend/
│   ├── src/
│   │   ├── api/client.ts    axios 實例 (走 Vite proxy /api → 8000)
│   │   ├── router/          顧客端 /order、後台 /admin/*
│   │   ├── stores/customer.ts  LocalStorage 暱稱記憶 (規格書 3.4)
│   │   └── views/
│   │       ├── customer/OrderView.vue  Mobile 點餐頁
│   │       └── admin/                  Tablet/Desktop 後台
│   ├── tailwind.config.js
│   └── vite.config.ts       proxy /api 與 /ws 至 :8000
└── docker-compose.yml       PostgreSQL 15 + pgAdmin
```

## 規格書關鍵設計對應

| 規格章節 | 實作位置 |
|---------|---------|
| 3.1 QR Code + 狀態機 | `models/food_table.py` (TableStatus 欄位) + `routers/tables.py` (open/clean) |
| 3.2 WebSocket 同桌同步 | `routers/ws.py` ConnectionManager |
| 3.3 悲觀鎖防止重複結帳 | `routers/orders.py` `select(...).with_for_update()` |
| 3.4 跨店顧客暱稱記憶 | `frontend/src/stores/customer.ts` (LocalStorage) |
| 4.3 全站環境變數 | `models/food_system_config.py` (套用 tblsysCode 設計) |
| 全表稽核欄位 | `models/_mixins.py` AuditMixin |

## 本機啟動

### 1. 啟動 PostgreSQL

```powershell
cd Food_Order_System
docker-compose up -d
# pgAdmin: http://localhost:5050  (admin@food.local / admin)
```

### 2. 後端

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # 自行調整密碼
uvicorn main:app --reload
# http://localhost:8000/docs
```

第一次啟動會自動 `Base.metadata.create_all()` 建表 (正式環境改用 alembic)。

### 3. 前端

```powershell
cd frontend
npm install
npm run dev
# http://localhost:5173
```

## 路由

- 首頁 `/` — 入口導引
- 顧客點餐 `/order?table=1` — Mobile-First
- 店家後台 `/admin/dashboard|tables|foods|orders|config`

## 後續開發

骨架已建立。下一步建議:
1. 補 `routers/cart.py` 完整 CRUD + WS broadcast
2. 補 `routers/orders.py` 送單事務 (含服務費計算 / 清空 Cart / 改桌況)
3. 接 JWT 認證 (`routers/auth.py`)
4. 後台 CRUD UI 串 API
5. Alembic migrations + 預設 seed (角色、選單、SystemConfig 範本資料)
