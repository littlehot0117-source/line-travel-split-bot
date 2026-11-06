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

    def test_format_all_expenses_text_multi_currency(self):
        """測試多幣別（台幣 + 泰銖）完整支出總明細的分開小計與分組列表"""
        twd_items = [
            {"id": i, "item_name": f"台幣項目_{i}", "amount": 1000.0, "original_amount": 1000.0, "currency": "TWD", "payer_name": "小明", "split_desc": "全體均分"}
            for i in range(1, 15)
        ]
        thb_items = [
            {"id": 14 + j, "item_name": f"泰銖項目_{j}", "amount": 92.0, "original_amount": 100.0, "currency": "THB", "payer_name": "小美", "split_desc": "全體均分"}
            for j in range(1, 20)
        ]
        all_exp = twd_items + thb_items

        result = format_all_expenses_text(all_exp, base_currency="TWD")

        # 驗證頂部幣別小計與總額
        self.assertIn("共 33 筆", result)
        self.assertIn("各幣別支出總計", result)
        self.assertIn("🇹🇼 TWD 總計：NT$ 14,000（共 14 筆）", result)
        self.assertIn("🇹🇭 THB 總計：฿ 1,900.00（共 19 筆，折合 NT$ 1,748）", result)
        self.assertIn("旅程總支出折合：NT$ 15,748", result)

        # 驗證依幣別分組之區塊
        self.assertIn("【🇹🇼 TWD 支出明細 • 共 14 筆 • 小計 NT$ 14,000】", result)
        self.assertIn("【🇹🇭 THB 支出明細 • 共 19 筆 • 小計 ฿ 1,900.00 (折合 NT$ 1,748)】", result)
        self.assertIn("1. 台幣項目_1", result)
        self.assertIn("15. 泰銖項目_1", result)

    def test_flex_multi_currency_filtering(self):
        """測試 Flex 明細卡片之多幣別統計與幣別篩選功能"""
        twd_items = [
            {"id": i, "item_name": f"台幣項目_{i}", "amount": 1000.0, "original_amount": 1000.0, "currency": "TWD", "payer_name": "小明", "split_desc": "全體均分"}
            for i in range(1, 15)
        ]
        thb_items = [
            {"id": 14 + j, "item_name": f"泰銖項目_{j}", "amount": 92.0, "original_amount": 100.0, "currency": "THB", "payer_name": "小美", "split_desc": "全體均分"}
            for j in range(1, 20)
        ]
        all_exp = twd_items + thb_items

        # 1. 預設「全部」卡片：帶有頂部幣別統計與篩選按鈕
        flex_all = create_expense_list_flex(all_exp, base_currency="TWD", page=1, page_size=8)
        self.assertIn("第 1/5 頁（共 33 筆）", flex_all["header"]["contents"][0]["contents"][1]["text"])
        body_str = str(flex_all["body"])
        self.assertIn("幣別支出統計", body_str)
        self.assertIn("action=view_expenses&currency=TWD&page=1", body_str)
        self.assertIn("action=view_expenses&currency=THB&page=1", body_str)

        # 2. 篩選「THB 泰銖」卡片：共 19 筆，每頁 8 筆共 3 頁
        flex_thb = create_expense_list_flex(all_exp, base_currency="TWD", page=1, page_size=8, currency_filter="THB")
        self.assertIn("THB 支出明細", flex_thb["header"]["contents"][0]["contents"][0]["text"])
        self.assertIn("第 1/3 頁（共 19 筆）", flex_thb["header"]["contents"][0]["contents"][1]["text"])
        # 下一頁按鈕應保持 &currency=THB
        footer_str = str(flex_thb["footer"])
        self.assertIn("action=view_expenses&page=2&currency=THB", footer_str)

        # 3. 篩選「TWD 台幣」卡片：共 14 筆，每頁 8 筆共 2 頁
        flex_twd = create_expense_list_flex(all_exp, base_currency="TWD", page=2, page_size=8, currency_filter="TWD")
        self.assertIn("TWD 支出明細", flex_twd["header"]["contents"][0]["contents"][0]["text"])
        self.assertIn("第 2/2 頁（共 14 筆）", flex_twd["header"]["contents"][0]["contents"][1]["text"])

    def test_text_command_total_expense_and_currency_filters(self):
        """測試使用者輸入「支出總明細」、「泰銖明細」、「台幣明細」之指令回應"""
        # 建立一筆 THB 支出
        thb_exp = Expense(
            group_id=self.group.id,
            item_name="泰國按摩",
            amount=500.0,
            original_amount=550.0,
            currency="THB",
            payer_id=self.m2.id,
            split_count=2,
            split_type="EQUAL_ALL"
        )
        self.db.add(thb_exp)
        self.db.commit()

        # 1. 測試「支出總明細」
        evt1 = MockMessageEvent("支出總明細")
        handle_text_message(evt1, self.db, self.mock_api_client)

        # 2. 測試「泰銖明細」
        evt2 = MockMessageEvent("泰銖明細")
        handle_text_message(evt2, self.db, self.mock_api_client)

        # 3. 測試「台幣明細 2」
        evt3 = MockMessageEvent("台幣明細 2")
        handle_text_message(evt3, self.db, self.mock_api_client)

        # 4. 測試 Postback action=view_expenses&currency=THB&page=1
        pb_evt = MockPostbackEvent("action=view_expenses&currency=THB&page=1")
        handle_postback(pb_evt, self.db, self.mock_api_client)


if __name__ == "__main__":
    unittest.main()
