import unittest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import GroupTrip, Member, Expense, ExpenseSplit, DraftExpense
from app.line_handlers import (
    parse_full_expense,
    handle_text_message,
    handle_postback,
    WAITING_STATES,
    clear_waiting_state,
)


class MockSource:
    def __init__(self, group_id="grp_thai_trip", user_id="user_jiaxin"):
        self.group_id = group_id
        self.user_id = user_id


class MockTextMessage:
    def __init__(self, text):
        self.text = text


class MockMessageEvent:
    def __init__(self, text, group_id="grp_thai_trip", user_id="user_jiaxin"):
        self.source = MockSource(group_id, user_id)
        self.message = MockTextMessage(text)
        self.reply_token = "reply_token_msg"


class MockPostbackData:
    def __init__(self, data):
        self.data = data


class MockPostbackEvent:
    def __init__(self, data, group_id="grp_thai_trip", user_id="user_jiaxin"):
        self.source = MockSource(group_id, user_id)
        self.postback = MockPostbackData(data)
        self.reply_token = "reply_token_pb"


class TestEditAndDateParsing(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.mock_api_client = MagicMock()
        WAITING_STATES.clear()

        # 初始化群組與成員
        self.group = GroupTrip(line_group_id="grp_thai_trip", trip_name="泰國行", base_currency="TWD")
        self.db.add(self.group)
        self.db.commit()

        self.m1 = Member(group_id=self.group.id, display_name="佳欣", line_user_id="user_jiaxin")
        self.m2 = Member(group_id=self.group.id, display_name="南廷", line_user_id="user_nanting")
        self.m3 = Member(group_id=self.group.id, display_name="園子", line_user_id="user_yuanzi")
        self.db.add_all([self.m1, self.m2, self.m3])
        self.db.commit()
        self.members = [self.m1, self.m2, self.m3]

    def tearDown(self):
        self.db.close()
        WAITING_STATES.clear()

    def test_date_parsing_is_not_treated_as_expense(self):
        """日期字串（無金額）不可被誤判為記帳"""
        # 1. 10/23 泰國機場接送至飯店
        res = parse_full_expense("10/23 泰國機場接送至飯店", self.members)
        self.assertIsNone(res, "包含 MM/DD 的純名稱不應被判為記帳")

        # 2. 泰國 10/23 機場接送至飯店
        res = parse_full_expense("泰國 10/23 機場接送至飯店", self.members)
        self.assertIsNone(res)

        # 3. 10-23 機場接送
        res = parse_full_expense("10-23 機場接送", self.members)
        self.assertIsNone(res)

        # 4. 2024/10/23 機場接送
        res = parse_full_expense("2024/10/23 機場接送", self.members)
        self.assertIsNone(res)

        # 5. 10月23日 機場接送
        res = parse_full_expense("10月23日 機場接送", self.members)
        self.assertIsNone(res)

    def test_date_with_amount_is_parsed_correctly(self):
        """帶有日期的記帳項目，其金額應被正確識別"""
        # 1. 10/23 機場接送 1395
        res = parse_full_expense("10/23 機場接送 1395", self.members)
        self.assertIsNotNone(res)
        self.assertEqual(res["item"], "10/23 機場接送")
        self.assertEqual(res["amount"], 1395.0)

        # 2. 10/28 小港機場接送 500 佳欣付 全員
        res = parse_full_expense("10/28 小港機場接送 500 佳欣付 全員", self.members)
        self.assertIsNotNone(res)
        self.assertEqual(res["item"], "10/28 小港機場接送")
        self.assertEqual(res["amount"], 500.0)
        self.assertEqual(res["payer"].display_name, "佳欣")
        self.assertEqual(res["mode"], "FULL")

        # 3. 7-11 500
        res = parse_full_expense("7-11 500", self.members)
        self.assertIsNotNone(res)
        self.assertEqual(res["item"], "7-11")
        self.assertEqual(res["amount"], 500.0)

    def test_edit_name_waiting_state_flow(self):
        """測試點選 [修改項目名稱] 按鈕後，直接傳送新名稱即可完成改名"""
        # 建立一筆既有支出
        exp = Expense(
            group_id=self.group.id,
            item_name="10/23 機場接送",
            amount=1395.0,
            original_amount=1395.0,
            currency="TWD",
            payer_id=self.m1.id,
            split_count=3,
            split_type="EQUAL_ALL"
        )
        self.db.add(exp)
        self.db.commit()
        self.db.refresh(exp)

        # 1. 使用者在明細或卡片點選 [📝 修改項目名稱]
        evt_pb = MockPostbackEvent(f"action=edit_prompt_name&expense_id={exp.id}")
        handle_postback(evt_pb, self.db, self.mock_api_client)

        # 2. 使用者直接傳送新名稱：「10/23 泰國機場接送至飯店」
        evt_rename = MockMessageEvent("10/23 泰國機場接送至飯店")
        handle_text_message(evt_rename, self.db, self.mock_api_client)

        # 3. 驗證名稱已成功更新，且未產生錯誤的 Draft
        self.db.refresh(exp)
        self.assertEqual(exp.item_name, "10/23 泰國機場接送至飯店")
        drafts = self.db.query(DraftExpense).all()
        self.assertEqual(len(drafts), 0, "不應產生錯誤草稿")

    def test_edit_amount_waiting_state_flow(self):
        """測試點選 [修改金額] 按鈕後，直接傳送新金額即可完成金額修改"""
        exp = Expense(
            group_id=self.group.id,
            item_name="午餐",
            amount=600.0,
            original_amount=600.0,
            currency="TWD",
            payer_id=self.m1.id,
            split_count=3,
            split_type="EQUAL_ALL"
        )
        self.db.add(exp)
        self.db.commit()
        self.db.refresh(exp)

        for m in self.members:
            self.db.add(ExpenseSplit(expense_id=exp.id, member_id=m.id, amount_owed=200.0))
        self.db.commit()

        # 1. 使用者點選 [💵 修改金額]
        evt_pb = MockPostbackEvent(f"action=edit_prompt_amount&expense_id={exp.id}")
        handle_postback(evt_pb, self.db, self.mock_api_client)

        # 2. 使用者直接傳送「900」
        evt_amt = MockMessageEvent("900")
        handle_text_message(evt_amt, self.db, self.mock_api_client)

        # 3. 驗證金額已更新為 900，每人分攤為 300
        self.db.refresh(exp)
        self.assertEqual(exp.amount, 900.0)
        splits = self.db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == exp.id).all()
        for s in splits:
            self.assertEqual(s.amount_owed, 300.0)

    def test_cancel_command_clears_waiting_state_and_drafts(self):
        """測試輸入「取消」可清除等待狀態與未完成草稿"""
        # 建立草稿
        draft = DraftExpense(
            line_group_id="grp_thai_trip",
            initiator_user_id="user_jiaxin",
            item_name="假資料",
            amount=100.0,
            currency="TWD"
        )
        self.db.add(draft)
        self.db.commit()

        # 使用者傳送「取消」
        evt_cancel = MockMessageEvent("取消")
        handle_text_message(evt_cancel, self.db, self.mock_api_client)

        # 驗證草稿已被刪除
        self.assertIsNone(self.db.query(DraftExpense).first())

    def test_text_command_no_arg_rename(self):
        """測試直接輸入「改名稱」會引導輸入新名稱"""
        exp = Expense(
            group_id=self.group.id,
            item_name="舊名稱",
            amount=500.0,
            original_amount=500.0,
            currency="TWD",
            payer_id=self.m1.id,
            split_count=1,
            split_type="SINGLE_MEMBER"
        )
        self.db.add(exp)
        self.db.commit()

        # 1. 傳送「改名稱」
        evt_cmd = MockMessageEvent("改名稱")
        handle_text_message(evt_cmd, self.db, self.mock_api_client)

        # 2. 傳送新名稱
        evt_new_name = MockMessageEvent("新名稱品項")
        handle_text_message(evt_new_name, self.db, self.mock_api_client)

        self.db.refresh(exp)
        self.assertEqual(exp.item_name, "新名稱品項")


if __name__ == "__main__":
    unittest.main()
