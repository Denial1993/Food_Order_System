from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # pydantic-settings 讀取順序：左邊先讀，右邊蓋掉左邊
    # .env             = 開發預設值（本機 Docker）
    # .env.production  = 正式環境覆蓋（Supabase）；不存在時自動忽略
    # OS 環境變數       = 最高優先（Render Dashboard 設的值）
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.production"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Food Order System"
    APP_ENV: str = "dev"
    DEBUG: bool = True

    # ── 資料庫 ────────────────────────────────────────────────────
    # 優先用 DATABASE_URL（Render / Supabase 會直接提供這個）
    # 如果沒設，用下面的分項設定（本機 Docker 開發用）
    DATABASE_URL: str | None = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "yourpassword"
    DB_NAME: str = "food_order_db"

    # ── JWT ───────────────────────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # ── CORS ──────────────────────────────────────────────────────
    # 逗號分隔字串，方便在 Render 環境變數只填一行
    # 範例: https://food-order.onrender.com,http://localhost:5173
    CORS_ORIGINS_STR: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Supabase Storage（圖片上傳用）────────────────────────────
    # Supabase Dashboard → Settings → API → Project URL / service_role key
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "menu-images"

    # ── 計算屬性 ──────────────────────────────────────────────────

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS_STR.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Supabase / Render 給的是 postgresql:// 格式
            # psycopg3 (psycopg) 需要 postgresql+psycopg://
            if url.startswith("postgresql://"):
                url = "postgresql+psycopg://" + url[len("postgresql://"):]
            elif url.startswith("postgres://"):
                # Heroku / 舊格式也支援
                url = "postgresql+psycopg://" + url[len("postgres://"):]
            return url
        # 本機 Docker 分項設定（直連，不過 pooler，不需要 prepare_threshold）
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
