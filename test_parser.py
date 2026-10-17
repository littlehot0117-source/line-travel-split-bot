import re
import difflib

class FakeMember:
    def __init__(self, id, name):
        self.id = id
        self.display_name = name
    def __repr__(self):
        return f"Member({self.id}, {self.display_name})"

members = [
    FakeMember(1, '佳欣'),
    FakeMember(2, '小磅'),
    FakeMember(3, '江小'),
    FakeMember(4, '驊鏞'),
    FakeMember(5, '苡瑄'),
    FakeMember(6, '南廷'),
    FakeMember(8, '團子'),
    FakeMember(9, '玟璇'),
]

from app.currency import normalize_currency

def find_member(name, member_list):
    name = name.strip()
    if not name:
        return None
    for m in member_list:
        if m.display_name == name:
            return m
    names = [m.display_name for m in member_list]
    matches = difflib.get_close_matches(name, names, n=1, cutoff=0.5)
    if matches:
        for m in member_list:
            if m.display_name == matches[0]:
                return m
    return None

def parse_full_expense(text, member_list, default_curr="TWD"):
    # Clean up delimiters
    # Examples:
    # 泰奶 200 佳欣付 佳欣 南廷 園子 玫璇
    # 泰奶 200 佳欣付 佳欣、南廷、園子、玫璇 均分
    # 泰奶 200 佳欣付 全員
    # 泰奶 200 佳欣付 4人
    # 泰奶 200 THB 佳欣付 佳欣 南廷 園子 玫璇
    # 泰奶 200 佳欣 4人
    # 泰奶 200 佳欣 佳欣 南廷 團子 玟璇
    
    # 1. 抽取 項目 與 金額
    # Format: [項目] [金額] [選填幣別] [其餘字串...]
    m = re.match(r"^([^\d:：\s]+.*?)\s*[:：\s]\s*(\d+(?:\.\d+)?)(.*)$", text.strip())
    if not m:
        return None
    
    item = m.group(1).strip()
    amount = float(m.group(2))
    rest = m.group(3).strip()
    
    if not rest:
        # 只有項目和金額，例如「泰奶 200」
        return {
            "mode": "SIMPLE",
            "item": item,
            "amount": amount,
            "currency": default_curr
        }
    
    # 2. 檢查 rest 開頭是否為幣別
    currency = default_curr
    tokens = [t for t in re.split(r"[,，、/|\s]+", rest) if t]
    
    if tokens:
        first_token = tokens[0]
        # Check if first_token is a known currency
        norm_c = normalize_currency(first_token)
        if norm_c != "TWD" or first_token.upper() in ["TWD", "NTD", "NT$", "台幣", "新台幣", "NT"]:
            currency = norm_c
            tokens = tokens[1:]
        elif first_token.upper() in ["THB", "JPY", "USD", "EUR", "KRW", "CNY", "HKD", "SGD"]:
            currency = norm_c
            tokens = tokens[1:]

    if not tokens:
        return {
            "mode": "SIMPLE",
            "item": item,
            "amount": amount,
            "currency": currency
        }
    
    # 3. 尋找付款人 Payer
    # Tokens may contain "佳欣付", "佳欣先付", "由佳欣付", or just "佳欣"
    payer = None
    payer_token_idx = -1
    
    for i, tok in enumerate(tokens):
        clean_tok = re.sub(r"^(由|誰|請)?", "", tok)
        clean_tok = re.sub(r"(付|先付|出|買單|請客|墊|代墊)$", "", clean_tok).strip()
        matched = find_member(clean_tok, member_list)
        if matched and (tok.endswith("付") or tok.endswith("先付") or tok.endswith("出") or tok.endswith("墊") or tok.startswith("由") or i == 0):
            payer = matched
            payer_token_idx = i
            break
            
    if not payer and tokens:
        # Check if first token matches a member name
        clean_tok = tokens[0].strip()
        matched = find_member(clean_tok, member_list)
        if matched:
            payer = matched
            payer_token_idx = 0

    if not payer:
        return None
        
    # Remainder tokens after removing payer
    remaining_tokens = tokens[:payer_token_idx] + tokens[payer_token_idx+1:]
    
    # 4. 解析分攤對象 Split
    # Case A: 全員 / 全體 / 大家 / 全部 / 均分 (with no other tokens)
    clean_remaining = [re.sub(r"(均分|分攤|分帳|分)$", "", t).strip() for t in remaining_tokens]
    clean_remaining = [t for t in clean_remaining if t]
    
    if not clean_remaining:
        # 例如「泰奶 200 佳欣付」
        return {
            "mode": "PAYER_ONLY",
            "item": item,
            "amount": amount,
            "currency": currency,
            "payer": payer
        }
        
    full_remaining_str = " ".join(clean_remaining)
    if any(k in full_remaining_str for k in ["全員", "全體", "大家", "全部", "每人", "所有人"]):
        return {
            "mode": "FULL",
            "item": item,
            "amount": amount,
            "currency": currency,
            "payer": payer,
            "split_type": "ALL",
            "split_members": member_list
        }
        
    # Case B: 人數均分 (例如：「4人」、「4人均分」、「4」)
    cnt_match = re.match(r"^(\d+)\s*(?:人|位)?$", full_remaining_str)
    if cnt_match:
        count = int(cnt_match.group(1))
        return {
            "mode": "COUNT",
            "item": item,
            "amount": amount,
            "currency": currency,
            "payer": payer,
            "target_count": count
        }
        
    # Case C: 指定名單
    split_members = []
    for tok in clean_remaining:
        m_matched = find_member(tok, member_list)
        if m_matched and m_matched not in split_members:
            split_members.append(m_matched)
            
    if split_members:
        return {
            "mode": "FULL",
            "item": item,
            "amount": amount,
            "currency": currency,
            "payer": payer,
            "split_type": "CUSTOM",
            "split_members": split_members
        }
        
    return None

test_cases = [
    "泰奶 200 佳欣付 佳欣 南廷 園子 玫璇",
    "泰奶 200 佳欣付 佳欣、南廷、園子、玫璇 均分",
    "泰奶 200 佳欣 佳欣 南廷 園子 玫璇",
    "泰奶 200 佳欣付 全員",
    "泰奶 200 佳欣 4人",
    "泰奶 200 THB 佳欣付 佳欣 南廷",
    "拉麵 3000 JPY 佳欣付 全體",
    "晚餐 1200 佳欣付",
    "泰奶 200",
]

for tc in test_cases:
    res = parse_full_expense(tc, members, "THB")
    print(f"INPUT: {tc}")
    print(f"  OUTPUT: {res}\n")
