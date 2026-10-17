import os
import sys
import io

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, GroupTrip, Member, Expense, ExpenseSplit, CurrencyRate, DraftExpense

def migrate(neon_url: str):
    if not neon_url:
        print("⚠️ 請提供 Neon PostgreSQL 連線網址！")
        return

    if neon_url.startswith("postgres://"):
        neon_url = neon_url.replace("postgres://", "postgresql://", 1)

    print(f"🔗 連線至本機 SQLite 資料庫...")
    sqlite_engine = create_engine("sqlite:///./travel_split.db")
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_db = SqliteSession()

    print(f"🔗 連線至 Neon PostgreSQL...")
    pg_engine = create_engine(neon_url, pool_pre_ping=True)
    PgSession = sessionmaker(bind=pg_engine)
    pg_db = PgSession()

    print("📦 正在 Neon 建立資料表結構...")
    Base.metadata.create_all(bind=pg_engine)

    # 1. 遷移 GroupTrip
    groups = sqlite_db.query(GroupTrip).all()
    print(f"🚚 正在遷移 {len(groups)} 個群組...")
    for g in groups:
        existing = pg_db.query(GroupTrip).filter(GroupTrip.id == g.id).first()
        if not existing:
            new_g = GroupTrip(
                id=g.id,
                line_group_id=g.line_group_id,
                trip_name=g.trip_name,
                base_currency=g.base_currency,
                last_active_expense_id=g.last_active_expense_id,
                is_active=g.is_active,
                created_at=g.created_at
            )
            pg_db.add(new_g)
    pg_db.commit()

    # 2. 遷移 Member
    members = sqlite_db.query(Member).all()
    print(f"🚚 正在遷移 {len(members)} 位成員...")
    for m in members:
        existing = pg_db.query(Member).filter(Member.id == m.id).first()
        if not existing:
            new_m = Member(
                id=m.id,
                group_id=m.group_id,
                line_user_id=m.line_user_id,
                display_name=m.display_name,
                created_at=m.created_at
            )
            pg_db.add(new_m)
    pg_db.commit()

    # 3. 遷移 CurrencyRate
    rates = sqlite_db.query(CurrencyRate).all()
    print(f"🚚 正在遷移 {len(rates)} 筆匯率設定...")
    for r in rates:
        existing = pg_db.query(CurrencyRate).filter(CurrencyRate.id == r.id).first()
        if not existing:
            new_r = CurrencyRate(
                id=r.id,
                group_id=r.group_id,
                currency=r.currency,
                rate_to_base=r.rate_to_base,
                created_at=r.created_at
            )
            pg_db.add(new_r)
    pg_db.commit()

    # 4. 遷移 Expense
    expenses = sqlite_db.query(Expense).all()
    print(f"🚚 正在遷移 {len(expenses)} 筆支出紀錄...")
    for e in expenses:
        existing = pg_db.query(Expense).filter(Expense.id == e.id).first()
        if not existing:
            new_e = Expense(
                id=e.id,
                group_id=e.group_id,
                item_name=e.item_name,
                currency=e.currency,
                original_amount=e.original_amount,
                exchange_rate=e.exchange_rate,
                amount=e.amount,
                payer_id=e.payer_id,
                split_count=e.split_count,
                split_type=e.split_type,
                note=e.note,
                is_deleted=e.is_deleted,
                created_at=e.created_at
            )
            pg_db.add(new_e)
    pg_db.commit()

    # 5. 遷移 ExpenseSplit
    splits = sqlite_db.query(ExpenseSplit).all()
    print(f"🚚 正在遷移 {len(splits)} 筆分攤明細...")
    for s in splits:
        existing = pg_db.query(ExpenseSplit).filter(ExpenseSplit.id == s.id).first()
        if not existing:
            new_s = ExpenseSplit(
                id=s.id,
                expense_id=s.expense_id,
                member_id=s.member_id,
                amount_owed=s.amount_owed
            )
            pg_db.add(new_s)
    pg_db.commit()

    # 更新 PostgreSQL sequence (避免 auto-increment id 衝突)
    from sqlalchemy import text
    with pg_engine.connect() as conn:
        for tbl in ["group_trips", "members", "currency_rates", "expenses", "expense_splits"]:
            try:
                conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), COALESCE(max(id), 1)) FROM {tbl};"))
                conn.commit()
            except Exception:
                pass

    print("🎉 資料遷移完成！Neon PostgreSQL 已同步所有資料！")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("DATABASE_URL")
    migrate(url)
