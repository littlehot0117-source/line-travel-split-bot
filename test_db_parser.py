import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.database import SessionLocal
from app.models import Member, GroupTrip
from app.line_handlers import parse_split_names, parse_full_expense

db = SessionLocal()
group = db.query(GroupTrip).first()
members = db.query(Member).filter(Member.group_id == group.id).all()
print("DB Members:", [m.display_name for m in members])

test_split = "佳欣、南廷、園子、玫璇 均分"
matched = parse_split_names(test_split, members)
print(f"parse_split_names('{test_split}') ->", [m.display_name for m in matched])

test_one_shot = "泰奶 200 佳欣付 佳欣、南廷、園子、玫璇 均分"
parsed = parse_full_expense(test_one_shot, members, "THB")
print(f"parse_full_expense('{test_one_shot}') ->", parsed["mode"], parsed["item"], parsed["amount"], parsed["payer"].display_name, [m.display_name for m in parsed["split_members"]])

test_one_shot_all = "泰奶 200 佳欣付 全員"
parsed_all = parse_full_expense(test_one_shot_all, members, "THB")
print(f"parse_full_expense('{test_one_shot_all}') ->", parsed_all["mode"], parsed_all["item"], parsed_all["amount"], parsed_all["payer"].display_name, [m.display_name for m in parsed_all["split_members"]])

test_count = "泰奶 200 佳欣付 4人"
parsed_count = parse_full_expense(test_count, members, "THB")
print(f"parse_full_expense('{test_count}') ->", parsed_count["mode"], parsed_count["item"], parsed_count["payer"].display_name, parsed_count["target_count"])
