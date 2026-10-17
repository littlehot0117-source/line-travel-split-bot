from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 依賴注入取得 DB Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化資料庫表格並確保新欄位自動遷移"""
    from sqlalchemy import text
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # 針對既有 SQLite / PostgreSQL 資料庫自動補齊多幣別欄位
    with engine.connect() as conn:
        migrations = [
            ("group_trips", [
                ("base_currency", "VARCHAR(10) DEFAULT 'TWD'"),
                ("last_active_expense_id", "INTEGER DEFAULT NULL")
            ]),
            ("expenses", [
                ("currency", "VARCHAR(10) DEFAULT 'TWD'"),
                ("original_amount", "FLOAT DEFAULT 0"),
                ("exchange_rate", "FLOAT DEFAULT 1.0")
            ]),
            ("draft_expenses", [
                ("currency", "VARCHAR(10) DEFAULT 'TWD'"),
                ("original_amount", "FLOAT DEFAULT 0"),
                ("exchange_rate", "FLOAT DEFAULT 1.0")
            ])
        ]
        for tbl, cols in migrations:
            for col_name, col_type in cols:
                try:
                    conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                except Exception:
                    pass
