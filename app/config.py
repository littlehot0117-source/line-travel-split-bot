import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

# 資料庫連線：預設本地 SQLite，若有設定 PostgreSQL (如 Supabase) 則直接連線
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./travel_split.db")

# 如果 PostgreSQL URL 未指定 driver，SQLAlchemy 預設可能尋找 psycopg3，此處明確指定 psycopg2
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

APP_BASE_URL = os.getenv("APP_BASE_URL", "https://mention-enlarge-borders-network.trycloudflare.com")

def set_base_url(url: str):
    global APP_BASE_URL
    if url and url.startswith("http"):
        APP_BASE_URL = url.rstrip("/")

def get_base_url() -> str:
    return APP_BASE_URL
