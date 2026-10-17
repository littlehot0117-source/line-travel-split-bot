import unittest
from app.settlement import simplify_debts


class TestSettlement(unittest.TestCase):
    def test_simplify_debts_two_people(self):
        # 小明墊 1000，兩人均分各 500。小美應給小明 500
        balances = {
            "小明": 500.0,
            "小美": -500.0
        }
        transfers = simplify_debts(balances)
        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0], {"from": "小美", "to": "小明", "amount": 500})

    def test_simplify_debts_three_people(self):
        # 小明代墊 1200，三人均分各 400。
        # 小明淨額: +800
        # 小美淨額: -400
        # 阿豪淨額: -400
        balances = {
            "小明": 800.0,
            "小美": -400.0,
            "阿豪": -400.0
        }
        transfers = simplify_debts(balances)
        self.assertEqual(len(transfers), 2)
        recipients = [t["to"] for t in transfers]
        senders = [t["from"] for t in transfers]
        amounts = [t["amount"] for t in transfers]
        self.assertEqual(recipients, ["小明", "小明"])
        self.assertEqual(set(senders), {"小美", "阿豪"})
        self.assertEqual(amounts, [400, 400])

    def test_simplify_debts_multi_transfers(self):
        # 複雜情況：4人互有代墊
        balances = {
            "A": 300.0,
            "B": 200.0,
            "C": -400.0,
            "D": -100.0
        }
        transfers = simplify_debts(balances)
        total_paid = sum(t["amount"] for t in transfers)
        self.assertEqual(total_paid, 500)
        self.assertLessEqual(len(transfers), 3)


if __name__ == "__main__":
    unittest.main()
