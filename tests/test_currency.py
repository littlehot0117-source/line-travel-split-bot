import unittest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import GroupTrip, Member, Expense, DraftExpense, CurrencyRate
from app.settlement import calculate_group_settlement
from app.line_handlers import handle_text_message, handle_postback
from tests.test_flow import MockMessageEvent, MockPostbackEvent


class TestMultiCurrencyFlow(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.mock_api_client = MagicMock()

    def tearDown(self):
        self.db.close()

    def test_multi_currency_expense_and_custom_rate(self):
        # 1. 新增旅伴
        handle_text_message(MockMessageEvent("新增成員 小明 小美"), self.db, self.mock_api_client)

        # 2. 自訂 JPY 匯率為 0.22
        handle_text_message(MockMessageEvent("設定匯率 JPY 0.22"), self.db, self.mock_api_client)
        group = self.db.query(GroupTrip).first()
        rate_rec = self.db.query(CurrencyRate).filter(CurrencyRate.group_id == group.id).first()
        self.assertEqual(rate_rec.currency, "JPY")
        self.assertEqual(rate_rec.rate_to_base, 0.22)

        # 3. 輸入日幣支出「拉麵 3000 JPY」
        handle_text_message(MockMessageEvent("拉麵 3000 JPY"), self.db, self.mock_api_client)
        draft = self.db.query(DraftExpense).first()
        self.assertEqual(draft.item_name, "拉麵")
        self.assertEqual(draft.currency, "JPY")
        self.assertEqual(draft.original_amount, 3000.0)
        self.assertAlmostEqual(draft.amount, 660.0)  # 3000 * 0.22 = 660

        # 4. 點選小明付款
        ming = self.db.query(Member).filter(Member.display_name == "小明").first()
        handle_postback(MockPostbackEvent(f"action=select_payer&draft_id={draft.id}&payer_id={ming.id}"), self.db, self.mock_api_client)

        # 5. 全員均分
        handle_postback(MockPostbackEvent(f"action=confirm_split&draft_id={draft.id}&payer_id={ming.id}&split_mode=ALL"), self.db, self.mock_api_client)

        expense = self.db.query(Expense).first()
        self.assertEqual(expense.currency, "JPY")
        self.assertEqual(expense.original_amount, 3000.0)
        self.assertAlmostEqual(expense.amount, 660.0)

        # 6. 查看結算
        settlement = calculate_group_settlement(self.db, group.id)
        self.assertEqual(settlement["total_spent"], 660)
        self.assertEqual(len(settlement["transfers"]), 1)
        self.assertEqual(settlement["transfers"][0], {"from": "小美", "to": "小明", "amount": 330})


if __name__ == "__main__":
    unittest.main()
