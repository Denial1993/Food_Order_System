from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
    future=True,
)

# Supabase 使用 PgBouncer pooler，psycopg3 預設會在伺服器端快取 Prepared Statement。
# PgBouncer 換連線後舊的 statement 不存在，導致 "DuplicatePreparedStatement" 錯誤。
# 解法：每次新連線建立後，把 prepare_threshold 設為 None → 完全停用自動 prepare。
# （None = 永不 prepare；0 = 每次都 prepare，反而更糟）
if settings.DATABASE_URL:
    @event.listens_for(engine, "connect")
    def _disable_prepared_statements(dbapi_conn, _conn_record):
        dbapi_conn.prepare_threshold = None

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
