import unittest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import GroupTrip, Member, Expense, ExpenseSplit
from app.line_handlers import handle_text_message
from tests.test_flow import MockMessageEvent


class TestMemberManagement(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.mock_api_client = MagicMock()

    def tearDown(self):
        self.db.close()

    def test_rename_member(self):
        # 1. 新增小明、小美
        handle_text_message(MockMessageEvent("新增成員 小明 小美"), self.db, self.mock_api_client)

        # 2. 改名 小明 -> 明哥
        handle_text_message(MockMessageEvent("改名 小明 明哥"), self.db, self.mock_api_client)

        members = self.db.query(Member).all()
        names = [m.display_name for m in members]
        self.assertIn("明哥", names)
        self.assertNotIn("小明", names)

    def test_delete_member_without_expenses(self):
        # 1. 新增小明、小美、阿豪
        handle_text_message(MockMessageEvent("新增成員 小明 小美 阿豪"), self.db, self.mock_api_client)

        # 2. 刪除阿豪
        handle_text_message(MockMessageEvent("刪除成員 阿豪"), self.db, self.mock_api_client)

        members = self.db.query(Member).all()
        names = [m.display_name for m in members]
        self.assertNotIn("阿豪", names)
        self.assertEqual(len(names), 2)

    def test_delete_member_with_expenses_blocked(self):
        # 1. 新增小明、小美
        handle_text_message(MockMessageEvent("新增成員 小明 小美"), self.db, self.mock_api_client)
        group = self.db.query(GroupTrip).first()
        ming = self.db.query(Member).filter(Member.display_name == "小明").first()

        # 2. 小明有記帳紀錄
        exp = Expense(group_id=group.id, item_name="午餐", amount=200, payer_id=ming.id)
        self.db.add(exp)
        self.db.commit()

        # 3. 嘗試刪除小明（應被保護阻止）
        handle_text_message(MockMessageEvent("刪除成員 小明"), self.db, self.mock_api_client)

        # 小明仍應存在
        members = self.db.query(Member).all()
        names = [m.display_name for m in members]
        self.assertIn("小明", names)


if __name__ == "__main__":
    unittest.main()
