import unittest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import GroupTrip, Member, Expense, ExpenseSplit, DraftExpense
from app.settlement import calculate_group_settlement
from app.line_handlers import handle_text_message, handle_postback


class MockSource:
    def __init__(self, group_id="grp_japan_trip", user_id="user_ming"):
        self.group_id = group_id
        self.user_id = user_id


class MockTextMessage:
    def __init__(self, text):
        self.text = text


class MockMessageEvent:
    def __init__(self, text, group_id="grp_japan_trip", user_id="user_ming"):
        self.source = MockSource(group_id, user_id)
        self.message = MockTextMessage(text)
        self.reply_token = "reply_token_123"


class MockPostbackData:
    def __init__(self, data):
        self.data = data


class MockPostbackEvent:
    def __init__(self, data, group_id="grp_japan_trip", user_id="user_ming"):
        self.source = MockSource(group_id, user_id)
        self.postback = MockPostbackData(data)
        self.reply_token = "reply_token_456"


class TestFullFlow(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.mock_api_client = MagicMock()

    def tearDown(self):
        self.db.close()

    def test_complete_button_guided_flow(self):
        # 1. 新增夥伴名單
        evt_add_members = MockMessageEvent("新增成員 小明 小美 阿豪")
        handle_text_message(evt_add_members, self.db, self.mock_api_client)

        members = self.db.query(Member).all()
        member_names = [m.display_name for m in members]
        self.assertIn("小明", member_names)
        self.assertIn("小美", member_names)
        self.assertIn("阿豪", member_names)

        # 2. 使用者輸入項目與金額「晚餐 1200」
        evt_expense_input = MockMessageEvent("晚餐 1200")
        handle_text_message(evt_expense_input, self.db, self.mock_api_client)

        draft = self.db.query(DraftExpense).first()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.item_name, "晚餐")
        self.assertEqual(draft.amount, 1200.0)

        # 3. 使用者按鈕點選付款人（小明）
        ming = self.db.query(Member).filter(Member.display_name == "小明").first()
        evt_postback_payer = MockPostbackEvent(f"action=select_payer&draft_id={draft.id}&payer_id={ming.id}")
        handle_postback(evt_postback_payer, self.db, self.mock_api_client)

        # 檢查 draft 更新了付款人
        draft = self.db.query(DraftExpense).filter(DraftExpense.id == draft.id).first()
        self.assertEqual(draft.payer_member_id, ming.id)

        # 4. 使用者按鈕點選分攤方式（全體均分）
        evt_postback_split = MockPostbackEvent(f"action=confirm_split&draft_id={draft.id}&payer_id={ming.id}&split_mode=ALL")
        handle_postback(evt_postback_split, self.db, self.mock_api_client)

        # 檢查正式 Expense 建立，Draft 被清除
        self.assertIsNone(self.db.query(DraftExpense).first())
        expense = self.db.query(Expense).first()
        self.assertIsNotNone(expense)
        self.assertEqual(expense.item_name, "晚餐")
        self.assertEqual(expense.amount, 1200.0)
        self.assertEqual(expense.payer_id, ming.id)

        splits = self.db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == expense.id).all()
        self.assertEqual(len(splits), len(members))
        for sp in splits:
            self.assertAlmostEqual(sp.amount_owed, 1200.0 / len(members), delta=1.0)

        # 5. 結算驗證
        group = self.db.query(GroupTrip).first()
        settlement = calculate_group_settlement(self.db, group.id)
        self.assertEqual(settlement["total_spent"], 1200)

        # 小明墊 1200，三人均分各 400，小美與阿豪應各付 400 給小明
        transfers = settlement["transfers"]
        self.assertEqual(len(transfers), 2)
        for t in transfers:
            self.assertEqual(t["to"], "小明")
            self.assertIn(t["from"], ["小美", "阿豪"])


if __name__ == "__main__":
    unittest.main()
