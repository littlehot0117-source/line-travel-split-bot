from typing import Dict, Tuple

# 常用貨幣符號
CURRENCY_SYMBOLS: Dict[str, str] = {
    "TWD": "NT$",
    "JPY": "¥",
    "USD": "$",
    "EUR": "€",
    "KRW": "₩",
    "THB": "฿",
    "CNY": "¥",
    "HKD": "HK$",
    "GBP": "£",
    "SGD": "S$",
    "AUD": "A$",
}

# 預設對台幣 (TWD) 參考匯率
DEFAULT_RATES_TO_TWD: Dict[str, float] = {
    "TWD": 1.0,
    "JPY": 0.215,   # 日幣
    "USD": 32.2,    # 美金
    "EUR": 35.0,    # 歐元
    "KRW": 0.024,   # 韓元
    "THB": 0.92,    # 泰銖
    "CNY": 4.45,    # 人民幣
    "HKD": 4.12,    # 港幣
    "GBP": 41.5,    # 英鎊
    "SGD": 24.2,    # 新幣
    "AUD": 21.0,    # 澳幣
}

# 幣別別名對照表
CURRENCY_ALIASES: Dict[str, str] = {
    "新台幣": "TWD",
    "台幣": "TWD",
    "TWD": "TWD",
    "NTD": "TWD",
    "NT$": "TWD",
    "NT": "TWD",
    "元": "TWD",
    "塊": "TWD",
    "塊錢": "TWD",
    "日幣": "JPY",
    "日圓": "JPY",
    "JPY": "JPY",
    "円": "JPY",
    "YEN": "JPY",
    "美金": "USD",
    "美元": "USD",
    "USD": "USD",
    "韓元": "KRW",
    "韓幣": "KRW",
    "KRW": "KRW",
    "WON": "KRW",
    "歐元": "EUR",
    "EUR": "EUR",
    "泰銖": "THB",
    "THB": "THB",
    "人民幣": "CNY",
    "CNY": "CNY",
    "RMB": "CNY",
    "港幣": "HKD",
    "HKD": "HKD",
    "英鎊": "GBP",
    "GBP": "GBP",
    "新幣": "SGD",
    "SGD": "SGD",
}


def normalize_currency(raw_str: str) -> str:
    """將文字轉換為標準 ISO 貨幣代碼（預設 TWD）"""
    if not raw_str:
        return "TWD"
    cleaned = raw_str.strip().upper()
    return CURRENCY_ALIASES.get(cleaned, CURRENCY_ALIASES.get(raw_str.strip(), "TWD"))


def format_amount(amount: float, currency: str = "TWD") -> str:
    """格式化顯示金額（日幣/台幣/韓元無小數，美金歐元兩位小數）"""
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    if currency in ["JPY", "KRW", "TWD"]:
        return f"{symbol} {int(round(amount)):,}"
    else:
        return f"{symbol} {amount:,.2f}"
