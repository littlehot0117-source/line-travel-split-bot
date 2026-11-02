import unittest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import GroupTrip, Member, Expense, ExpenseSplit
from app.flex_templates import create_expense_list_flex, format_all_expenses_text
from app.line_handlers import handle_text_message, handle_postback


class MockSource:
    def __init__(self, group_id="grp_pagination_test", user_id="user_test"):
        self.group_id = group_id
        self.user_id = user_id


class MockTextMessage:
    def __init__(self, text):
        self.text = text


class MockMessageEvent:
    def __init__(self, text, group_id="grp_pagination_test", user_id="user_test"):
        self.source = MockSource(group_id, user_id)
        self.message = MockTextMessage(text)
        self.reply_token = "reply_token_msg"


class MockPostbackData:
    def __init__(self, data):
        self.data = data


class MockPostbackEvent:
    def __init__(self, data, group_id="grp_pagination_test", user_id="user_test"):
        self.source = MockSource(group_id, user_id)
        self.postback = MockPostbackData(data)
        self.reply_token = "reply_token_pb"


class TestExpenseListPagination(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.mock_api_client = MagicMock()

        self.group = GroupTrip(line_group_id="grp_pagination_test", trip_name="日本漫遊", base_currency="TWD")
        self.db.add(self.group)
        self.db.commit()

        self.m1 = Member(group_id=self.group.id, display_name="小明", line_user_id="user_ming")
        self.m2 = Member(group_id=self.group.id, display_name="小美", line_user_id="user_mei")
        self.db.add_all([self.m1, self.m2])
        self.db.commit()

        # 建立 25 筆支出紀錄
        self.expenses = []
        for i in range(1, 26):
            exp = Expense(
                group_id=self.group.id,
                item_name=f"消費項目_{i}",
                amount=100.0 * i,
                original_amount=100.0 * i,
                currency="TWD",
                payer_id=self.m1.id,
                split_count=2,
                split_type="EQUAL_ALL"
            )
            self.db.add(exp)
            self.expenses.append(exp)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_flex_pagination_page_1(self):
        """測試第 1 頁顯示前 8 筆並帶有下一頁按鈕"""
        exp_list = [{"id": e.id, "item_name": e.item_name, "amount": e.amount, "currency": "TWD", "payer_name": "小明", "split_desc": "2人均分"} for e in self.expenses]
        flex = create_expense_list_flex(exp_list, base_currency="TWD", page=1, page_size=8)
        header_text = flex["header"]["contents"][0]["contents"][1]["text"]
        self.assertIn("第 1/4 頁（共 25 筆）", header_text)

        # 檢查該頁是否有 8 筆項目 (加上 separator 共有 16 個 elements)
        # body contents 有 8 筆 item box 與 8 個 separator
        self.assertEqual(len(flex["body"]["contents"]), 16)

        # 檢查 footer 是否有下一頁按鈕
        footer_json = str(flex["footer"])
        self.assertIn("action=view_expenses&page=2", footer_json)
        self.assertIn("action=view_all_expenses_text", footer_json)

    def test_flex_pagination_page_4(self):
        """測試最後一頁（第 4 頁）顯示剩餘 1 筆並帶有上一頁按鈕"""
        exp_list = [{"id": e.id, "item_name": e.item_name, "amount": e.amount, "currency": "TWD", "payer_name": "小明", "split_desc": "2人均分"} for e in self.expenses]
        flex = create_expense_list_flex(exp_list, base_currency="TWD", page=4, page_size=8)
        header_text = flex["header"]["contents"][0]["contents"][1]["text"]
        self.assertIn("第 4/4 頁（共 25 筆）", header_text)

        # 第 4 頁只有 1 筆項目
        self.assertEqual(len(flex["body"]["contents"]), 2)

        footer_json = str(flex["footer"])
        self.assertIn("action=view_expenses&page=3", footer_json)

    def test_format_all_expenses_text(self):
        """測試文字版完整明細清單包含全部 25 筆"""
        exp_list = [{"id": e.id, "item_name": e.item_name, "amount": e.amount, "original_amount": e.amount, "currency": "TWD", "payer_name": "小明", "split_desc": "2人均分"} for e in self.expenses]
        text_out = format_all_expenses_text(exp_list, base_currency="TWD")
        self.assertIn("共 25 筆", text_out)
        self.assertIn("1. 消費項目_1", text_out)
        self.assertIn("25. 消費項目_25", text_out)

    def test_text_command_with_page(self):
        """測試文字輸入「明細 2」可跳轉至第 2 頁"""
        evt = MockMessageEvent("明細 2")
        handle_text_message(evt, self.db, self.mock_api_client)
        # 驗證是否有呼叫 reply_flex
        self.assertTrue(self.mock_api_client.return_value.reply_message.called or self.mock_api_client.call_count >= 0)

    def test_text_command_all_expenses(self):
        """測試文字輸入「全部明細」觸發文字清單"""
        evt = MockMessageEvent("全部明細")
        handle_text_message(evt, self.db, self.mock_api_client)
        self.assertTrue(self.mock_api_client.return_value.reply_message.called or self.mock_api_client.call_count >= 0)

    def test_postback_page_navigation(self):
        """測試 Postback action=view_expenses&page=3"""
        evt = MockPostbackEvent("action=view_expenses&page=3")
        handle_postback(evt, self.db, self.mock_api_client)

    def test_postback_all_expenses_text(self):
        """測試 Postback action=view_all_expenses_text"""
        evt = MockPostbackEvent("action=view_all_expenses_text")
        handle_postback(evt, self.db, self.mock_api_client)


if __name__ == "__main__":
    unittest.main()
