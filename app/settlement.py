from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from app.models import Expense, ExpenseSplit, Member, GroupTrip


def simplify_debts(balances: Dict[str, float], precision: int = 0) -> List[Dict[str, any]]:
    """
    債務最小化簡化演算法（貪婪法）
    將各成員的淨餘額 (代墊款 - 應分攤款) 轉換為最少筆數的還款轉帳指示。

    :param balances: 字典，key 為成員名稱/ID，value 為淨餘額（正數代表應收回，負數代表應支付）
    :param precision: 小數位數，預設 0（四捨五入至整數元，適合台幣/日幣等無小數場景）
    :return: 轉帳建議列表，例如 [{"from": "小美", "to": "小明", "amount": 300}]
    """
    # 建立債權人清單 (應收錢, balance > 0) 與 債務人清單 (應付錢, balance < 0)
    creditors: List[List[any]] = []  # [[name, amount]]
    debtors: List[List[any]] = []    # [[name, amount]]

    for person, bal in balances.items():
        rounded_bal = round(bal, precision) if precision > 0 else round(bal)
        if rounded_bal > 0:
            creditors.append([person, float(rounded_bal)])
        elif rounded_bal < 0:
            debtors.append([person, float(-rounded_bal)])

    # 排序：由大到小優先配對
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    transfers = []
    i, j = 0, 0

    while i < len(debtors) and j < len(creditors):
        debtor_name, debt_amt = debtors[i]
        creditor_name, cred_amt = creditors[j]

        # 轉帳金額為兩者之較小值
        settle_amt = min(debt_amt, cred_amt)

        if settle_amt > 0:
            transfers.append({
                "from": debtor_name,
                "to": creditor_name,
                "amount": int(settle_amt) if precision == 0 else round(settle_amt, precision)
            })

        debtors[i][1] -= settle_amt
        creditors[j][1] -= settle_amt

        # 檢查債務人是否已結清
        if abs(debtors[i][1]) < (10 ** (-max(precision, 1))):
            i += 1
        # 檢查債權人是否已收齊
        if abs(creditors[j][1]) < (10 ** (-max(precision, 1))):
            j += 1

    return transfers


def calculate_group_settlement(db: Session, group_id: int) -> dict:
    """
    計算群組所有非刪除支出的結算資訊：
    1. 各原始幣別獨立分開折算（該幣別之債務最小化轉帳指南、每人收支）
    2. 全局折合主幣別支出總計與對照
    """
    group = db.query(GroupTrip).filter(GroupTrip.id == group_id).first()
    if not group:
        return None

    members = db.query(Member).filter(Member.group_id == group_id).all()
    member_names = {m.id: m.display_name for m in members}

    expenses = db.query(Expense).filter(
        Expense.group_id == group_id,
        Expense.is_deleted == False
    ).all()

    from app.currency import format_amount, CURRENCY_SYMBOLS

    # 1. 各幣別獨立折算（各幣別各算各的）
    currencies_used = sorted(list(set(e.currency or "TWD" for e in expenses))) if expenses else [group.base_currency or "TWD"]

    currency_settlements = []
    for curr in currencies_used:
        curr_expenses = [e for e in expenses if (e.currency or "TWD") == curr]
        curr_spendings = [e for e in curr_expenses if e.split_type != "REPAYMENT"]
        curr_repayments = [e for e in curr_expenses if e.split_type == "REPAYMENT"]
        curr_total = sum(e.original_amount if (e.original_amount and e.original_amount > 0) else e.amount for e in curr_spendings)

        # 統計每人在該幣別的消費代墊與應分攤，以及小額還款紀錄
        spent_paid_map = {m.id: 0.0 for m in members}
        spent_owed_map = {m.id: 0.0 for m in members}
        repay_sent_map = {m.id: 0.0 for m in members}
        repay_recv_map = {m.id: 0.0 for m in members}

        for exp in curr_spendings:
            orig_amt = exp.original_amount if (exp.original_amount and exp.original_amount > 0) else exp.amount
            if exp.payer_id in spent_paid_map:
                spent_paid_map[exp.payer_id] += orig_amt

            splits = db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == exp.id).all()
            if splits:
                per_split_orig = orig_amt / len(splits)
                for sp in splits:
                    if sp.member_id in spent_owed_map:
                        spent_owed_map[sp.member_id] += per_split_orig

        for rep in curr_repayments:
            orig_amt = rep.original_amount if (rep.original_amount and rep.original_amount > 0) else rep.amount
            if rep.payer_id in repay_sent_map:
                repay_sent_map[rep.payer_id] += orig_amt
            splits = db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == rep.id).all()
            for sp in splits:
                if sp.member_id in repay_recv_map:
                    repay_recv_map[sp.member_id] += orig_amt

        precision = 0 if curr in ["TWD", "JPY", "KRW", "THB"] else 2
        curr_balances = {}
        curr_member_summary = []

        for m in members:
            sp_p = spent_paid_map[m.id]
            sp_o = spent_owed_map[m.id]
            rp_s = repay_sent_map[m.id]
            rp_r = repay_recv_map[m.id]
            # 淨餘額 = (代墊公費 - 應分攤公費) + 已還給他人 - 已收他人還款
            net = (sp_p - sp_o) + (rp_s - rp_r)
            curr_balances[m.display_name] = net
            if sp_p > 0 or sp_o > 0 or rp_s > 0 or rp_r > 0:
                curr_member_summary.append({
                    "member_id": m.id,
                    "name": m.display_name,
                    "paid": round(sp_p, precision) if precision > 0 else round(sp_p),
                    "owed": round(sp_o, precision) if precision > 0 else round(sp_o),
                    "repay_sent": round(rp_s, precision) if precision > 0 else round(rp_s),
                    "repay_recv": round(rp_r, precision) if precision > 0 else round(rp_r),
                    "net": round(net, precision) if precision > 0 else round(net),
                    "formatted_paid": format_amount(sp_p, curr),
                    "formatted_owed": format_amount(sp_o, curr),
                    "formatted_repay_sent": format_amount(rp_s, curr) if rp_s > 0 else "",
                    "formatted_repay_recv": format_amount(rp_r, curr) if rp_r > 0 else "",
                    "formatted_net": ("+" if round(net, precision) > 0 else "") + format_amount(net, curr)
                })

        # 計算該幣別的獨立債務最小化轉帳指南
        curr_transfers = simplify_debts(curr_balances, precision=precision)
        for t in curr_transfers:
            t["currency"] = curr
            t["formatted_amount"] = format_amount(t["amount"], curr)

        currency_settlements.append({
            "currency": curr,
            "total_spent": curr_total,
            "formatted_total": format_amount(curr_total, curr),
            "symbol": CURRENCY_SYMBOLS.get(curr, curr),
            "expense_count": len(curr_spendings),
            "repayment_count": len(curr_repayments),
            "members": curr_member_summary,
            "transfers": curr_transfers
        })

    # 2. 合併計算（折合主幣別之傳統統計，保留相容性）
    spending_all = [e for e in expenses if e.split_type != "REPAYMENT"]
    repayments_all = [e for e in expenses if e.split_type == "REPAYMENT"]
    total_spent = sum(e.amount for e in spending_all)
    base_curr = group.base_currency or "TWD"

    combined_spent_paid = {m.id: 0.0 for m in members}
    combined_spent_owed = {m.id: 0.0 for m in members}
    combined_repay_sent = {m.id: 0.0 for m in members}
    combined_repay_recv = {m.id: 0.0 for m in members}

    for exp in spending_all:
        if exp.payer_id in combined_spent_paid:
            combined_spent_paid[exp.payer_id] += exp.amount
        splits = db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == exp.id).all()
        for sp in splits:
            if sp.member_id in combined_spent_owed:
                combined_spent_owed[sp.member_id] += sp.amount_owed

    for rep in repayments_all:
        if rep.payer_id in combined_repay_sent:
            combined_repay_sent[rep.payer_id] += rep.amount
        splits = db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == rep.id).all()
        for sp in splits:
            if sp.member_id in combined_repay_recv:
                combined_repay_recv[sp.member_id] += sp.amount_owed

    combined_balances = {}
    combined_members = []
    for m in members:
        sp_p = combined_spent_paid[m.id]
        sp_o = combined_spent_owed[m.id]
        rp_s = combined_repay_sent[m.id]
        rp_r = combined_repay_recv[m.id]
        net = (sp_p - sp_o) + (rp_s - rp_r)
        combined_balances[m.display_name] = net
        combined_members.append({
            "member_id": m.id,
            "name": m.display_name,
            "paid": round(sp_p),
            "owed": round(sp_o),
            "repay_sent": round(rp_s),
            "repay_recv": round(rp_r),
            "net": round(net)
        })
    combined_transfers = simplify_debts(combined_balances, precision=0)

    # 統計各原始幣別支出總計清單（排除還款）
    currency_totals: Dict[str, float] = {}
    for exp in spending_all:
        c = exp.currency or "TWD"
        orig_amt = exp.original_amount if (exp.original_amount and exp.original_amount > 0) else exp.amount
        currency_totals[c] = currency_totals.get(c, 0.0) + orig_amt

    currency_breakdown = [
        {
            "currency": c,
            "amount": round(amt, 2),
            "formatted": format_amount(amt, c),
            "symbol": CURRENCY_SYMBOLS.get(c, c)
        }
        for c, amt in sorted(currency_totals.items())
    ]

    return {
        "trip_name": group.trip_name,
        "base_currency": base_curr,
        "total_spent": round(total_spent),
        "expense_count": len(spending_all),
        "repayment_count": len(repayments_all),
        "currency_breakdown": currency_breakdown,
        "currency_settlements": currency_settlements,
        "is_multi_currency": len(currency_settlements) > 1,
        "members": combined_members,
        "transfers": combined_transfers
    }
