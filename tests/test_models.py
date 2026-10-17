import unittest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import GroupTrip, Member, Expense, ExpenseSplit
from app.settlement import calculate_group_settlement


class TestModelsAndSettlement(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def test_group_expense_and_settlement(self):
        # 1. 建立群組
        group = GroupTrip(line_group_id="test_group_123", trip_name="京都五日遊")
        self.db.add(group)
        self.db.commit()

        # 2. 建立 3 位旅行夥伴
        m1 = Member(group_id=group.id, display_name="小明")
        m2 = Member(group_id=group.id, display_name="小美")
        m3 = Member(group_id=group.id, display_name="阿豪")
        self.db.add_all([m1, m2, m3])
        self.db.commit()

        # 3. 小明代墊晚餐 1200，3人均分各 400
        exp1 = Expense(
            group_id=group.id,
            item_name="拉麵晚餐",
            amount=1200.0,
            payer_id=m1.id,
            split_count=3,
            split_type="EQUAL_ALL"
        )
        self.db.add(exp1)
        self.db.commit()

        for m in [m1, m2, m3]:
            split = ExpenseSplit(expense_id=exp1.id, member_id=m.id, amount_owed=400.0)
            self.db.add(split)
        self.db.commit()

        # 4. 計算結算
        result = calculate_group_settlement(self.db, group.id)
        self.assertEqual(result["total_spent"], 1200)
        self.assertEqual(result["expense_count"], 1)

        # 檢查轉帳建議：小美、阿豪 各轉 400 給小明
        transfers = result["transfers"]
        self.assertEqual(len(transfers), 2)
        for t in transfers:
            self.assertEqual(t["to"], "小明")
            self.assertEqual(t["amount"], 400)


if __name__ == "__main__":
    unittest.main()
