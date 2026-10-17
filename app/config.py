import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

# 資料庫連線：預設本地 SQLite，若有設定 PostgreSQL (如 Supabase) 則直接連線
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./travel_split.db")

# 如果 PostgreSQL URL 是 postgres:// 開頭（常見於舊版 Heroku 或某些託管平台），SQLAlchemy 要求 postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

APP_BASE_URL = os.getenv("APP_BASE_URL", "https://mention-enlarge-borders-network.trycloudflare.com")

def set_base_url(url: str):
    global APP_BASE_URL
    if url and url.startswith("http"):
        APP_BASE_URL = url.rstrip("/")

def get_base_url() -> str:
    return APP_BASE_URL
