import re
import difflib
import urllib.parse
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    JoinEvent,
)

from app.models import GroupTrip, Member, Expense, ExpenseSplit, DraftExpense, CurrencyRate
from app.currency import normalize_currency, format_amount, DEFAULT_RATES_TO_TWD, CURRENCY_SYMBOLS, CURRENCY_ALIASES
from app.settlement import calculate_group_settlement
from app.flex_templates import (
    create_main_menu_flex,
    create_command_guide_flex,
    create_currency_selection_flex,
    create_payer_selection_flex,
    create_split_selection_flex,
    create_custom_split_flex,
    create_member_picker_flex,
    create_receipt_flex,
    create_repayment_flex,
    create_repayment_guide_flex,
    create_settlement_flex,
    create_expense_list_flex,
    create_edit_expense_flex,
    create_edit_payer_selection_flex,
    create_edit_split_selection_flex,
)


def get_exchange_rate(db: Session, group_id: int, currency: str) -> float:
    """取得群組自訂匯率，若未自訂則使用系統預設參考匯率"""
    if currency == "TWD":
        return 1.0
    custom = db.query(CurrencyRate).filter(
        CurrencyRate.group_id == group_id,
        CurrencyRate.currency == currency
    ).first()
    if custom:
        return custom.rate_to_base
    return DEFAULT_RATES_TO_TWD.get(currency, 1.0)


def get_group_id_from_event(event) -> str:
    """從 LINE 事件中取得群組 ID（若是一對一聊天則為 user_id）"""
    source = event.source
    if hasattr(source, "group_id") and source.group_id:
        return source.group_id
    if hasattr(source, "room_id") and source.room_id:
        return source.room_id
    if hasattr(source, "user_id") and source.user_id:
        return source.user_id
    return "default_group"


def get_or_create_group(db: Session, line_group_id: str) -> GroupTrip:
    """取得或建立旅程群組"""
    group = db.query(GroupTrip).filter(GroupTrip.line_group_id == line_group_id).first()
    if not group:
        group = GroupTrip(line_group_id=line_group_id, trip_name="本次旅行")
        db.add(group)
        db.commit()
        db.refresh(group)
    return group


WAITING_STATES: Dict[str, Dict[str, Any]] = {}
WAITING_STATE_TIMEOUT = 300  # 5 分鐘逾期防護


def set_waiting_state(line_group_id: str, user_id: str, action: str, data: Dict[str, Any]):
    """設定使用者的暫存等待輸入狀態（例如等待輸入新項目名稱或新金額）"""
    key = f"{line_group_id}:{user_id}" if (line_group_id and user_id) else (line_group_id or user_id or "default")
    data_copy = dict(data)
    data_copy["action"] = action
    data_copy["timestamp"] = time.time()
    WAITING_STATES[key] = data_copy


def get_waiting_state(line_group_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """取得使用者的暫存等待狀態，逾期則自動清除"""
    now = time.time()
    key = f"{line_group_id}:{user_id}" if (line_group_id and user_id) else (line_group_id or user_id or "default")
    state = WAITING_STATES.get(key)
    if not state and line_group_id:
        state = WAITING_STATES.get(line_group_id)
        if state:
            key = line_group_id

    if not state:
        return None

    if now - state.get("timestamp", 0) > WAITING_STATE_TIMEOUT:
        WAITING_STATES.pop(key, None)
        return None

    return state


def clear_waiting_state(line_group_id: str, user_id: str):
    """清除等待輸入狀態"""
    if line_group_id and user_id:
        WAITING_STATES.pop(f"{line_group_id}:{user_id}", None)
    if line_group_id:
        WAITING_STATES.pop(line_group_id, None)
    if user_id:
        WAITING_STATES.pop(user_id, None)


def get_sender_display_name(api_client: ApiClient, event) -> str:
    """嘗試從 LINE API 取得發話者的暱稱，若失敗則回傳預設名稱"""
    user_id = getattr(event.source, "user_id", None)
    if not user_id:
        return "夥伴"

    try:
        messaging_api = MessagingApi(api_client)
        group_id = getattr(event.source, "group_id", None)
        room_id = getattr(event.source, "room_id", None)

        if group_id:
            profile = messaging_api.get_group_member_profile(group_id, user_id)
            name = getattr(profile, "display_name", None)
            return str(name) if isinstance(name, str) else "夥伴"
        elif room_id:
            profile = messaging_api.get_room_member_profile(room_id, user_id)
            name = getattr(profile, "display_name", None)
            return str(name) if isinstance(name, str) else "夥伴"
        else:
            profile = messaging_api.get_profile(user_id)
            name = getattr(profile, "display_name", None)
            return str(name) if isinstance(name, str) else "夥伴"
    except Exception:
        # 在開發測試、未授權或未加好友環境下降級保護
        return "我"


def reply_flex(messaging_api: MessagingApi, reply_token: str, alt_text: str, flex_dict: Dict[str, Any]):
    """輔助函式：發送 Flex Message"""
    container = FlexContainer.from_dict(flex_dict)
    message = FlexMessage(alt_text=alt_text, contents=container)
    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[message]
        )
    )


def reply_text(messaging_api: MessagingApi, reply_token: str, text: str, quick_reply: Optional[QuickReply] = None):
    """輔助函式：發送純文字訊息"""
    message = TextMessage(text=text, quick_reply=quick_reply)
    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[message]
        )
    )


def find_member_fuzzy(name: str, member_list: List[Member]) -> Optional[Member]:
    """模糊比對群組成員（支援錯別字、同音字如 園子/團子, 玫璇/玟璇, 孜璇/玟璇, 驊鋪/驊鏞，並去除付/墊等動詞）"""
    name = name.strip()
    if not name:
        return None
    # 1. 精確比對
    for m in member_list:
        if m.display_name == name:
            return m
    # 2. 去除前後綴比對
    clean = re.sub(r"^(由|請)?", "", name)
    clean = re.sub(r"(哥|姐|付|先付|出|買單|請客|墊|代墊)$", "", clean).strip()
    for m in member_list:
        if m.display_name == clean:
            return m
    # 3. 近似比對（difflib cutoff=0.5）
    names = [m.display_name for m in member_list]
    matches = difflib.get_close_matches(clean, names, n=1, cutoff=0.5)
    if matches:
        for m in member_list:
            if m.display_name == matches[0]:
                return m
    return None


def is_known_currency(token: str) -> bool:
    """判斷文字是否為已知貨幣代碼或中文別名"""
    if not token:
        return False
    t = token.strip().upper()
    return t in CURRENCY_ALIASES or token.strip() in CURRENCY_ALIASES


def parse_split_names(text: str, member_list: List[Member]) -> List[Member]:
    """解析使用者傳送的均分名單（支援前後綴『均分』、『分攤』，與逗號頓號空格分隔）"""
    clean = re.sub(r"^(?:分攤|均分|分帳|分|請)\s*[:：\s]?", "", text.strip())
    clean = re.sub(r"[:：\s]?(?:均分|分攤|分帳|分|等|共|人|位)+$", "", clean).strip()
    tokens = [t.strip() for t in re.split(r"[,，、/|\s]+", clean) if t.strip()]
    if not tokens:
        return []
    matched = []
    for tok in tokens:
        m = find_member_fuzzy(tok, member_list)
        if m and m not in matched:
            matched.append(m)
    return matched


def parse_repayment(text: str, member_list: List[Member], default_curr: str = "TWD") -> Optional[Dict[str, Any]]:
    """
    解析小額還款指令，例如：
    - 「江小 還 佳欣 40」
    - 「江小 還 佳欣 40 THB」或「江小 還 佳欣 40 泰銖」
    - 「江小 還給 佳欣 40」
    - 「江小 還款給 佳欣 40」
    - 「江小 轉帳給 佳欣 200」或「江小 轉 佳欣 100」
    - 「江小 付給 佳欣 50」
    - 「還款 江小 佳欣 40」或「小額還款 江小 佳欣 40 THB」
    - 「登記還款 江小 佳欣 40」
    """
    raw_text = text.strip()
    if not raw_text:
        return None

    # 去除常見的前綴詞（如：還款、小額還款、登記還款）
    clean_text = raw_text
    prefix_matched = False
    prefix_match = re.match(r"^(?:小額還款|登記還款|還款|轉帳)\s*[:：\s]?\s*(.+)$", raw_text)
    if prefix_match:
        clean_text = prefix_match.group(1).strip()
        prefix_matched = True

    # Pattern A: Infix 還款語法
    # 例如：「江小 還 佳欣 40」、「江小 還給 佳欣 40 THB」、「江小 轉帳 佳欣 50」
    infix_pattern = re.compile(
        r"^([^\d:：\s]+?)\s*(?:還款給|還給|還款|還|轉帳給|轉帳|轉|付給|給)\s*([^\d:：\s]+?)\s*[:：\s]?\s*(\d+(?:\.\d+)?)(?:\s*([a-zA-Z\u4e00-\u9fa5]+))?$"
    )
    m = infix_pattern.match(clean_text)

    # Pattern B: 若有還款前綴，支援無 infix 語法，例如：「還款 江小 佳欣 40」、「還款 江小 佳欣 40 THB」
    if not m and prefix_matched:
        prefix_pattern = re.compile(
            r"^([^\d:：\s]+?)\s+(?:給\s+)?([^\d:：\s]+?)\s*[:：\s]?\s*(\d+(?:\.\d+)?)(?:\s*([a-zA-Z\u4e00-\u9fa5]+))?$"
        )
        m = prefix_pattern.match(clean_text)

    if not m:
        return None

    from_str = m.group(1).strip()
    to_str = m.group(2).strip()
    try:
        amount = float(m.group(3))
    except (ValueError, TypeError):
        return None

    if amount <= 0:
        return None

    curr_str = m.group(4)
    currency = default_curr
    if curr_str:
        curr_candidate = curr_str.strip()
        if is_known_currency(curr_candidate):
            currency = normalize_currency(curr_candidate)

    # 比對付款人 (from) 與收款人 (to)
    from_member = find_member_fuzzy(from_str, member_list)
    to_member = find_member_fuzzy(to_str, member_list)

    if not from_member or not to_member:
        return None

    if from_member.id == to_member.id:
        return None

    return {
        "from_member": from_member,
        "to_member": to_member,
        "amount": amount,
        "currency": currency
    }


INVALID_EXPENSE_UNIT_PATTERN = r'^(?:分鐘|分鍾|秒鐘|秒|小時|個小時|點鐘|點半|點|次|下|遍|回|趟|場|天|日|號|週|周|月|個月|年|個|隻|支|張|條|本|把|杯|碗|盤|瓶|罐|盒|包|袋|道|段|期|集|節|課|劑|顆|粒|朵|部|首|台|輛|棟|戶|間|歲|樓|度|公分|公尺|公里|公斤|公克|毫升|cm|km|kg|ml)'


def parse_full_expense(text: str, member_list: List[Member], default_curr: str = "TWD") -> Optional[Dict[str, Any]]:
    """解析單一訊息記帳（支援 FULL, COUNT, PAYER_ONLY, SIMPLE 四種模式）"""
    text_clean = text.strip()
    candidates = list(re.finditer(r'(\d+(?:\.\d+)?)', text_clean))
    if not candidates:
        return None

    matched_candidate = None
    for cand in reversed(candidates):
        amt_str = cand.group(1)
        start, end = cand.start(), cand.end()
        item = text_clean[:start].rstrip(':： ')
        rest = text_clean[end:].strip()

        if not item:
            continue

        # 排除日期格式中的數字（例如 10/23、2024/10/23、10-23 或帶空格 10 / 23）
        # 1. 前方以 '/' 或 '-' 結尾且前有數字（如 10/23 中的 23）
        prefix_part = text_clean[:start].rstrip()
        if prefix_part.endswith(('/', '-')) and re.search(r'\d\s*[/\\-]$', prefix_part):
            continue
        # 2. 後方以 '/' 或 '-' 開頭且後有數字（如 10/23 中的 10）
        suffix_part = text_clean[end:].lstrip()
        if re.match(r'^[/\\-]\s*\d', suffix_part):
            continue
        # 3. item 結尾為 '/' 或 '-'（如 "10/"）
        if item.endswith(('/', '-')):
            continue

        # 若 item 以「每」、「第」、「前」、「後」、「隔」結尾，非記帳項目（如「每5分鐘」、「第1次」）
        if re.search(r'[每第前後隔]$', item):
            continue
        # 若緊接在數字後方為時間、次數、計量單位（如「5分鐘」、「3點」），非記帳金額
        if re.match(INVALID_EXPENSE_UNIT_PATTERN, rest, re.I):
            continue

        # 排除以常見指令開頭的品項（避免指令文字被誤判為記帳）
        if re.match(r'^(?:取消|修改|改名稱|改金額|改付款人|改分攤|刪除|結算|明細|成員|新增成員|設定|查看)', item):
            continue

        try:
            val = float(amt_str)
            if val <= 0:
                continue
            matched_candidate = (item, val, rest)
            break
        except ValueError:
            continue

    if not matched_candidate:
        return None

    item, amount, rest = matched_candidate

    if not rest:
        return {
            "mode": "SIMPLE",
            "item": item,
            "amount": amount,
            "currency": default_curr
        }

    tokens = [t for t in re.split(r"[,，、/|\s]+", rest) if t]
    currency = default_curr
    if tokens and is_known_currency(tokens[0]):
        currency = normalize_currency(tokens[0])
        tokens = tokens[1:]

    if not tokens:
        return {
            "mode": "SIMPLE",
            "item": item,
            "amount": amount,
            "currency": currency
        }

    # 尋找付款人 Payer
    payer = None
    payer_idx = -1
    for i, tok in enumerate(tokens):
        if tok.endswith("付") or tok.endswith("先付") or tok.endswith("出") or tok.endswith("墊") or tok.startswith("由"):
            m_found = find_member_fuzzy(tok, member_list)
            if m_found:
                payer = m_found
                payer_idx = i
                break
    if not payer and tokens:
        m_found = find_member_fuzzy(tokens[0], member_list)
        if m_found:
            payer = m_found
            payer_idx = 0

    if not payer:
        return {
            "mode": "SIMPLE",
            "item": item,
            "amount": amount,
            "currency": currency
        }

    rem_tokens = tokens[:payer_idx] + tokens[payer_idx+1:]
    clean_rem = [re.sub(r"(均分|分攤|分帳|分)$", "", t).strip() for t in rem_tokens]
    clean_rem = [t for t in clean_rem if t]

    if not clean_rem:
        return {
            "mode": "PAYER_ONLY",
            "item": item,
            "amount": amount,
            "currency": currency,
            "payer": payer
        }

    rem_str = " ".join(clean_rem)
    if any(k in rem_str for k in ["全員", "全體", "大家", "全部", "每人", "所有人"]):
        return {
            "mode": "FULL",
            "item": item,
            "amount": amount,
            "currency": currency,
            "payer": payer,
            "split_type": "ALL",
            "split_members": member_list
        }

    cnt_match = re.match(r"^(\d+)\s*(?:人|位)?$", rem_str)
    if cnt_match:
        cnt = int(cnt_match.group(1))
        return {
            "mode": "COUNT",
            "item": item,
            "amount": amount,
            "currency": currency,
            "payer": payer,
            "target_count": cnt
        }

    split_members = []
    for tok in clean_rem:
        m_m = find_member_fuzzy(tok, member_list)
        if m_m and m_m not in split_members:
            split_members.append(m_m)

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

    return {
        "mode": "PAYER_ONLY",
        "item": item,
        "amount": amount,
        "currency": currency,
        "payer": payer
    }


# -------------------------------------------------------------
# 訊息事件處理 (MessageEvent)
# -------------------------------------------------------------
def handle_text_message(event: MessageEvent, db: Session, api_client: ApiClient):
    messaging_api = MessagingApi(api_client)
    user_text = event.message.text.strip()
    reply_token = event.reply_token
    line_group_id = get_group_id_from_event(event)
    user_id = getattr(event.source, "user_id", "")

    group = get_or_create_group(db, line_group_id)

    def get_target_expense(item_query: str = "") -> Optional[Expense]:
        if item_query:
            clean_q = item_query.strip()
            exp = db.query(Expense).filter(
                Expense.group_id == group.id,
                Expense.is_deleted == False,
                Expense.item_name.ilike(f"%{clean_q}%")
            ).order_by(Expense.id.desc()).first()
            if exp:
                return exp
        if group.last_active_expense_id:
            exp = db.query(Expense).filter(
                Expense.group_id == group.id,
                Expense.id == group.last_active_expense_id,
                Expense.is_deleted == False
            ).first()
            if exp:
                return exp
        return db.query(Expense).filter(
            Expense.group_id == group.id,
            Expense.is_deleted == False
        ).order_by(Expense.id.desc()).first()

    # 0. 取消/放棄目前操作（包含清除等待輸入狀態與草稿記帳）
    if user_text.lower() in ["取消", "放棄", "算了", "cancel", "exit", "q", "關閉"]:
        had_waiting = get_waiting_state(line_group_id, user_id) is not None
        clear_waiting_state(line_group_id, user_id)

        drafts = db.query(DraftExpense).filter(DraftExpense.line_group_id == line_group_id).all()
        had_drafts = len(drafts) > 0
        if had_drafts:
            for d in drafts:
                db.delete(d)
            db.commit()

        if had_waiting or had_drafts:
            reply_text(messaging_api, reply_token, "👌 已為您取消目前的記帳或修改操作！")
        else:
            reply_text(messaging_api, reply_token, "👌 目前沒有正在進行中的記帳或修改操作喔。")
        return

    # 全域導覽或功能指令：若使用者輸入此類指令，自動清除等待修改狀態，避免使用者被困在等待輸入中
    global_commands = [
        "指令", "所有指令", "指令表", "指令大全", "說明", "使用說明", "教學", "怎麼用", "help", "commands",
        "選單", "功能", "主選單", "目錄", "menu",
        "結算", "查看結算", "算帳", "還款", "小額還款", "還款教學", "登記還款", "還款指南", "怎麼還款",
        "明細", "查看明細", "帳務明細", "成員名單", "查看成員", "旅伴",
        "清空紀錄", "重新開始", "新旅程", "歸零", "設定幣別", "幣別", "當下幣別", "切換幣別", "預設幣別", "換幣別",
        "匯率表", "查看匯率", "匯率清單"
    ]
    if user_text.lower() in global_commands or re.match(r"^(?:新增成員|新增夥伴|旅伴|設定匯率|匯率設定)\s*", user_text):
        clear_waiting_state(line_group_id, user_id)

    # 0.5 處理等待輸入狀態（WAITING_STATES，例如修改名稱、修改金額）
    waiting_state = get_waiting_state(line_group_id, user_id)
    if waiting_state:
        w_action = waiting_state.get("action")
        expense_id = waiting_state.get("expense_id")
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        if not expense:
            clear_waiting_state(line_group_id, user_id)
            reply_text(messaging_api, reply_token, "⚠️ 找不到該筆支出紀錄，可能已被刪除！")
            return

        if w_action == "edit_name":
            # 去除常見修改前綴
            new_name = re.sub(r"^(?:改名稱|修改名稱|更名|改名|修改)\s*[:：\s]?", "", user_text).strip()
            if not new_name:
                reply_text(messaging_api, reply_token, "⚠️ 請輸入有效的新名稱，或傳送「取消」放棄修改。")
                return

            old_name = expense.item_name
            expense.item_name = new_name
            group.last_active_expense_id = expense.id
            db.commit()
            clear_waiting_state(line_group_id, user_id)

            curr = expense.currency or (group.base_currency or "TWD")
            orig_amt = expense.original_amount if (expense.original_amount and expense.original_amount > 0) else expense.amount
            split_count = max(expense.split_count or 1, 1)
            per_person_orig = orig_amt / split_count
            split_desc = f"{split_count}人均分（每人 {format_amount(per_person_orig, curr)}）"
            payer_name = expense.payer.display_name if expense.payer else "未知"

            now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
            card = create_receipt_flex(
                expense.id,
                expense.item_name,
                expense.amount,
                payer_name,
                split_desc,
                now_str,
                currency=expense.currency,
                original_amount=expense.original_amount,
                rate=expense.exchange_rate
            )
            reply_flex(messaging_api, reply_token, f"✅ 已成功將【{old_name}】更名為【{new_name}】！", card)
            return

        elif w_action == "edit_amount":
            clean_amt = re.sub(r"^(?:改金額|修改金額|金額)\s*[:：\s]?", "", user_text).strip().replace(",", "")
            amt_match = re.search(r"(\d+(?:\.\d+)?)", clean_amt)
            if not amt_match or float(amt_match.group(1)) <= 0:
                reply_text(messaging_api, reply_token, "⚠️ 請輸入正確的數字金額（例如「500」），或傳送「取消」放棄修改。")
                return

            new_amt = float(amt_match.group(1))
            rate = expense.exchange_rate or 1.0
            expense.original_amount = new_amt
            expense.amount = round(new_amt * rate, 2)
            group.last_active_expense_id = expense.id

            split_count = max(expense.split_count or 1, 1)
            per_person_base = round(expense.amount / split_count, 2)
            for s in expense.splits:
                s.amount_owed = per_person_base
            db.commit()
            clear_waiting_state(line_group_id, user_id)

            curr = expense.currency or (group.base_currency or "TWD")
            per_person_orig = new_amt / split_count
            payer_name = expense.payer.display_name if expense.payer else "未知"
            split_desc = f"{split_count}人均分（每人 {format_amount(per_person_orig, curr)}）"

            now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
            card = create_receipt_flex(
                expense.id,
                expense.item_name,
                expense.amount,
                payer_name,
                split_desc,
                now_str,
                currency=expense.currency,
                original_amount=expense.original_amount,
                rate=expense.exchange_rate
            )
            display_cost = format_amount(expense.original_amount, expense.currency)
            reply_flex(messaging_api, reply_token, f"✅ 已成功將【{expense.item_name}】金額修改為 {display_cost}！", card)
            return

    # 1. 功能指令優先比對
    # (A) 完整指令大全
    if user_text.lower() in ["指令", "所有指令", "指令表", "指令大全", "說明", "使用說明", "教學", "怎麼用", "help", "commands"]:
        reply_flex(messaging_api, reply_token, "📖 旅行分帳指令大全", create_command_guide_flex())
        return

    # (B) 主選單
    if user_text.lower() in ["選單", "功能", "主選單", "目錄", "menu"]:
        reply_flex(messaging_api, reply_token, "🧳 旅行分帳小幫手選單", create_main_menu_flex())
        return

    # (B) 批次新增成員指令（如：「新增成員 小明 小美 阿豪」）
    add_member_match = re.match(r"^(?:新增成員|新增夥伴|旅伴)\s*[:：\s]\s*(.+)$", user_text)
    if add_member_match:
        current_members = db.query(Member).filter(Member.group_id == group.id).all()
        names_raw = add_member_match.group(1)
        names = [n.strip() for n in re.split(r"[,，\s]+", names_raw) if n.strip()]
        added = []
        for name in names:
            if not any(m.display_name == name for m in current_members):
                m = Member(group_id=group.id, display_name=name)
                db.add(m)
                added.append(name)
        db.commit()

        if added:
            reply_text(messaging_api, reply_token, f"✅ 已成功加入旅行夥伴：{'、'.join(added)}！\n現在可以直接輸入項目與金額（如「晚餐 1200」）開始記帳囉。")
        else:
            reply_text(messaging_api, reply_token, "ℹ️ 這些夥伴已經在名單中囉！")
        return

    # (C) 自動確保至少有發話者（若名單全空時）
    current_members = db.query(Member).filter(Member.group_id == group.id).all()
    user_name = get_sender_display_name(api_client, event)
    if not current_members:
        new_m = Member(group_id=group.id, line_user_id=user_id, display_name=user_name)
        db.add(new_m)
        db.commit()
        current_members = [new_m]

    # (B) 記帳提示引導
    if user_text in ["記帳", "新增支出", "我要記帳", "記一筆"]:
        qr = QuickReply(items=[
            QuickReplyItem(action=MessageAction(label="晚餐 1200", text="晚餐 1200")),
            QuickReplyItem(action=MessageAction(label="計程車 350", text="計程車 350")),
            QuickReplyItem(action=MessageAction(label="門票 600", text="門票 600")),
            QuickReplyItem(action=MessageAction(label="👥 查看成員", text="成員名單")),
        ])
        msg_text = (
            "💰 請輸入【消費項目 金額】\n"
            "例如輸入：\n"
            "👉 「晚餐 1200」\n"
            "👉 「計程車 350」\n\n"
            "送出後，我會立即彈出按鈕卡片讓您快速點選【誰付款】與【幾人均分】！"
        )
        reply_text(messaging_api, reply_token, msg_text, quick_reply=qr)
        return

    # (C) 查看結算與還款
    if user_text in ["結算", "查看結算", "算帳", "還款"]:
        settlement_data = calculate_group_settlement(db, group.id)
        reply_flex(messaging_api, reply_token, "📊 結算報表", create_settlement_flex(settlement_data))
        return

    # (C-2) 小額還款教學指南
    if user_text in ["小額還款", "還款教學", "登記還款", "還款指南", "怎麼還款"]:
        reply_flex(messaging_api, reply_token, "💸 旅伴小額還款指南", create_repayment_guide_flex())
        return

    # (D) 查看明細
    if user_text in ["明細", "查看明細", "帳務明細"]:
        expenses = db.query(Expense).filter(
            Expense.group_id == group.id,
            Expense.is_deleted == False
        ).order_by(Expense.id.desc()).all()

        base_curr = group.base_currency or "TWD"
        exp_list = []
        for e in expenses:
            exp_list.append({
                "id": e.id,
                "item_name": e.item_name,
                "amount": e.amount,
                "original_amount": e.original_amount if e.original_amount else e.amount,
                "currency": e.currency or base_curr,
                "payer_name": e.payer.display_name if e.payer else "未知",
                "split_desc": f"{e.split_count}人均分",
                "split_type": e.split_type
            })
        reply_flex(messaging_api, reply_token, "📋 支出明細", create_expense_list_flex(exp_list, base_curr))
        return

    # (E) 成員管理指令
    if user_text in ["成員名單", "查看成員", "旅伴"]:
        members_str = "、".join([m.display_name for m in current_members]) if current_members else "尚無"
        msg = (
            f"👥 目前旅行夥伴名單（共 {len(current_members)} 位）：\n"
            f"{members_str}\n\n"
            f"💡 成員管理功能：\n"
            f"➕ 新增夥伴：傳送「新增成員 [名字]」\n"
            f"✏️ 修改名字：傳送「改名 舊名字 新名字」（例如：改名 小磅 磅哥）\n"
            f"🗑️ 刪除成員：傳送「刪除成員 [名字]」（例如：刪除成員 團子）"
        )
        reply_text(messaging_api, reply_token, msg)
        return

    # 修改成員名稱（改名）
    rename_match = re.match(r"^(?:修改成員|改名|修改名字|更名)\s*[:：\s]?\s*(.+?)\s*(?:->|至|為|\s+)\s*(.+)$", user_text)
    if rename_match:
        old_name = rename_match.group(1).strip()
        new_name = rename_match.group(2).strip()

        target_m = db.query(Member).filter(
            Member.group_id == group.id,
            Member.display_name == old_name
        ).first()

        if not target_m:
            reply_text(messaging_api, reply_token, f"⚠️ 找不到名為【{old_name}】的成員，請先傳送「成員名單」確認！")
            return

        target_m.display_name = new_name
        db.commit()
        reply_text(messaging_api, reply_token, f"✅ 已成功將成員【{old_name}】更名為【{new_name}】！\n所有過去與未來的記帳與結算皆已同步更新。")
        return

    # 刪除成員
    delete_member_match = re.match(r"^(?:刪除成員|移除成員|刪除夥伴|移除夥伴)\s*[:：\s]?\s*(.+)$", user_text)
    if delete_member_match:
        raw_names = delete_member_match.group(1)
        names_to_del = [n.strip() for n in re.split(r"[,，\s]+", raw_names) if n.strip()]
        deleted = []
        blocked = []

        for name in names_to_del:
            target_m = db.query(Member).filter(
                Member.group_id == group.id,
                Member.display_name == name
            ).first()

            if not target_m:
                continue

            # 檢查是否有未刪除的支出關聯，避免破壞帳務完整性
            has_paid = db.query(Expense).filter(
                Expense.payer_id == target_m.id,
                Expense.is_deleted == False
            ).first()

            has_splits = db.query(ExpenseSplit).join(Expense).filter(
                ExpenseSplit.member_id == target_m.id,
                Expense.is_deleted == False
            ).first()

            if has_paid or has_splits:
                blocked.append(name)
            else:
                db.delete(target_m)
                deleted.append(name)

        db.commit()

        res_msg = []
        if deleted:
            res_msg.append(f"✅ 已成功從群組移除成員：{'、'.join(deleted)}")
        if blocked:
            res_msg.append(f"⚠️ 以下成員已有記帳或分攤紀錄，無法直接刪除：{'、'.join(blocked)}\n💡 提示：若只需更改名稱請使用「改名 舊名 新名」，或於結算後使用「新旅程」重置！")

        if not res_msg:
            res_msg.append("⚠️ 找不到欲刪除的成員，請先確認「成員名單」！")

        reply_text(messaging_api, reply_token, "\n\n".join(res_msg))
        return


    # (F) 清空/新旅程
    if user_text in ["清空紀錄", "重新開始", "新旅程", "歸零"]:
        db.query(Expense).filter(Expense.group_id == group.id).update({"is_deleted": True})
        db.commit()
        reply_text(messaging_api, reply_token, "✨ 舊有帳務已全數歸零，已為您開啟新的旅程記帳！")
        return

    # (G) 匯率設定與查詢指令（例如：「設定匯率 JPY 0.215」或「查看匯率」）
    rate_set_match = re.match(r"^(?:設定匯率|匯率設定|匯率)\s*([a-zA-Z\u4e00-\u9fa5]+)\s*[:：\s]?\s*(\d+(?:\.\d+)?)$", user_text)
    if rate_set_match:
        curr_name = rate_set_match.group(1).strip()
        curr = normalize_currency(curr_name)
        new_rate = float(rate_set_match.group(2))
        rate_rec = db.query(CurrencyRate).filter(
            CurrencyRate.group_id == group.id,
            CurrencyRate.currency == curr
        ).first()
        if not rate_rec:
            rate_rec = CurrencyRate(group_id=group.id, currency=curr, rate_to_base=new_rate)
            db.add(rate_rec)
        else:
            rate_rec.rate_to_base = new_rate
        db.commit()
        reply_text(messaging_api, reply_token, f"✅ 已成功設定 {curr} 對台幣匯率為：{new_rate}！\n之後記帳輸入 {curr}（例如「拉麵 3000 {curr}」）將自動以此匯率折算。")
        return

    # (G-2) 設定當下預設幣別（例如：「設定幣別 JPY」、「幣別 日幣」、「設定幣別」）
    if user_text in ["設定幣別", "幣別", "當下幣別", "切換幣別", "預設幣別", "換幣別"]:
        curr = group.base_currency or "TWD"
        reply_flex(messaging_api, reply_token, "💱 設定當下記帳幣別", create_currency_selection_flex(curr))
        return

    curr_set_match = re.match(r"^(?:設定幣別|設定當下幣別|當下幣別|切換幣別|預設幣別|幣別)\s*[:：\s]?\s*([a-zA-Z\u4e00-\u9fa5]+)$", user_text)
    if curr_set_match:
        curr_name = curr_set_match.group(1).strip()
        new_curr = normalize_currency(curr_name)
        group.base_currency = new_curr
        db.commit()
        reply_text(
            messaging_api,
            reply_token,
            f"✅ 已成功將群組當下預設幣別切換為：【{new_curr}】！\n"
            f"👉 之後記帳直接輸入「拉麵 1500」或「門票 800」就會自動視為 {new_curr} 囉！（若有其他幣別亦可加上尾碼，如「伴手禮 500 TWD」）"
        )
        return

    if user_text in ["匯率表", "查看匯率", "匯率清單"]:
        custom_rates = {r.currency: r.rate_to_base for r in db.query(CurrencyRate).filter(CurrencyRate.group_id == group.id).all()}
        lines = ["💱 目前參考匯率（折合台幣）："]
        for curr in ["JPY", "USD", "EUR", "KRW", "THB", "CNY", "HKD", "SGD"]:
            r = custom_rates.get(curr, DEFAULT_RATES_TO_TWD.get(curr, 1.0))
            tag = " (自訂)" if curr in custom_rates else ""
            lines.append(f"• 1 {curr} = {r} TWD{tag}")
        lines.append("\n💡 提示：傳送「設定匯率 JPY 0.215」可自訂群組匯率！")
        reply_text(messaging_api, reply_token, "\n".join(lines))
        return

    # (G-3) 支援直接文字修改支出內容（金額、名稱、付款人、分攤名單）
    # 0. 若僅傳送「修改金額」或「改金額」
    if user_text in ["修改金額", "改金額", "改價錢", "改費用"]:
        expense = get_target_expense()
        if not expense:
            reply_text(messaging_api, reply_token, "⚠️ 目前尚無可修改的支出紀錄！")
            return
        set_waiting_state(line_group_id, user_id, "edit_amount", {"expense_id": expense.id})
        curr = expense.currency or (group.base_currency or "TWD")
        cur_amt_str = format_amount(expense.original_amount or expense.amount, curr)
        reply_text(
            messaging_api,
            reply_token,
            f"✏️ 請輸入【{expense.item_name}】的新金額（目前為 {cur_amt_str}）：\n\n"
            f"💡 直接傳送新金額即可（例如「500」），或傳送「取消」放棄修改。"
        )
        return

    # 0-2. 若僅傳送「修改名稱」或「改名稱」
    if user_text in ["修改名稱", "改名稱", "改品項", "修改項目"]:
        expense = get_target_expense()
        if not expense:
            reply_text(messaging_api, reply_token, "⚠️ 目前尚無可修改的支出紀錄！")
            return
        set_waiting_state(line_group_id, user_id, "edit_name", {"expense_id": expense.id})
        reply_text(
            messaging_api,
            reply_token,
            f"✏️ 請輸入【{expense.item_name}】的新名稱：\n\n"
            f"💡 直接傳送新名稱即可，或傳送「取消」放棄修改。"
        )
        return

    # Pattern 1: 修改金額
    edit_amt_match = (
        re.match(r"^(?:修改|改)\s*(.+?)\s*(?:的)?\s*(?:金額|價錢|費用)\s*[:：\s]?\s*(\d+(?:\.\d+)?)$", user_text) or
        re.match(r"^(?:改金額|修改金額)\s*[:：\s]?\s*(\d+(?:\.\d+)?)$", user_text)
    )
    if edit_amt_match:
        if len(edit_amt_match.groups()) == 2:
            target_item = edit_amt_match.group(1).strip()
            new_amount_raw = float(edit_amt_match.group(2))
        else:
            target_item = ""
            new_amount_raw = float(edit_amt_match.group(1))

        expense = get_target_expense(target_item)
        if not expense:
            reply_text(messaging_api, reply_token, f"⚠️ 找不到欲修改的支出紀錄！" if target_item else "⚠️ 目前尚無可修改的支出紀錄！")
            return

        rate = expense.exchange_rate or 1.0
        expense.original_amount = new_amount_raw
        expense.amount = round(new_amount_raw * rate, 2)
        group.last_active_expense_id = expense.id

        split_count = max(expense.split_count or 1, 1)
        per_person_base = round(expense.amount / split_count, 2)
        for s in expense.splits:
            s.amount_owed = per_person_base
        db.commit()

        curr = expense.currency or (group.base_currency or "TWD")
        per_person_orig = new_amount_raw / split_count
        payer_name = expense.payer.display_name if expense.payer else "未知"
        split_desc = f"{split_count}人均分（每人 {format_amount(per_person_orig, curr)}）"

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            payer_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        display_cost = format_amount(expense.original_amount, expense.currency)
        reply_flex(messaging_api, reply_token, f"✅ 已成功將【{expense.item_name}】金額修改為 {display_cost}！", card)
        return

    # Pattern 2: 修改付款人
    edit_payer_match = (
        re.match(r"^(?:修改|改)\s*(.+?)\s*(?:的)?\s*(?:付款人|誰付|誰出的|先付|代墊)\s*[:：\s]?\s*(.+)$", user_text) or
        re.match(r"^(?:改付款人|修改付款人|更換付款人)\s*[:：\s]?\s*(.+)$", user_text)
    )
    if edit_payer_match:
        if len(edit_payer_match.groups()) == 2:
            target_item = edit_payer_match.group(1).strip()
            payer_str = edit_payer_match.group(2).strip()
        else:
            target_item = ""
            payer_str = edit_payer_match.group(1).strip()

        expense = get_target_expense(target_item)
        if not expense:
            reply_text(messaging_api, reply_token, f"⚠️ 找不到欲修改的支出紀錄！" if target_item else "⚠️ 目前尚無可修改的支出紀錄！")
            return

        new_payer = find_member_fuzzy(payer_str, current_members)
        if not new_payer:
            reply_text(messaging_api, reply_token, f"⚠️ 找不到名為【{payer_str}】的成員，請先確認成員名單！")
            return

        expense.payer_id = new_payer.id
        group.last_active_expense_id = expense.id
        db.commit()

        curr = expense.currency or (group.base_currency or "TWD")
        orig_amt = expense.original_amount if (expense.original_amount and expense.original_amount > 0) else expense.amount
        split_count = max(expense.split_count or 1, 1)
        per_person_orig = orig_amt / split_count
        split_desc = f"{split_count}人均分（每人 {format_amount(per_person_orig, curr)}）"

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            new_payer.display_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        reply_flex(messaging_api, reply_token, f"✅ 已成功將【{expense.item_name}】付款人修改為【{new_payer.display_name}】！", card)
        return

    # Pattern 3: 修改項目名稱
    edit_name_match = (
        re.match(r"^(?:修改|改)\s*(.+?)\s*(?:的)?\s*(?:名稱|項目|品項)\s*[:：\s]?\s*(.+)$", user_text) or
        re.match(r"^(?:改名稱|修改名稱)\s*[:：\s]?\s*(.+)$", user_text)
    )
    if edit_name_match:
        if len(edit_name_match.groups()) == 2:
            target_item = edit_name_match.group(1).strip()
            new_name = edit_name_match.group(2).strip()
        else:
            target_item = ""
            new_name = edit_name_match.group(1).strip()

        expense = get_target_expense(target_item)
        if not expense:
            reply_text(messaging_api, reply_token, f"⚠️ 找不到欲修改的支出紀錄！" if target_item else "⚠️ 目前尚無可修改的支出紀錄！")
            return

        old_name = expense.item_name
        expense.item_name = new_name
        group.last_active_expense_id = expense.id
        db.commit()

        curr = expense.currency or (group.base_currency or "TWD")
        orig_amt = expense.original_amount if (expense.original_amount and expense.original_amount > 0) else expense.amount
        split_count = max(expense.split_count or 1, 1)
        per_person_orig = orig_amt / split_count
        split_desc = f"{split_count}人均分（每人 {format_amount(per_person_orig, curr)}）"
        payer_name = expense.payer.display_name if expense.payer else "未知"

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            payer_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        reply_flex(messaging_api, reply_token, f"✅ 已成功將【{old_name}】更名為【{new_name}】！", card)
        return

    # Pattern 4: 修改分攤夥伴名單
    edit_split_match = (
        re.match(r"^(?:修改|改)\s*(.+?)\s*(?:的)?\s*(?:分攤|均分|分帳|夥伴)\s*[:：\s]?\s*(.+)$", user_text) or
        re.match(r"^(?:改分攤|修改分攤|重新分攤)\s*[:：\s]?\s*(.+)$", user_text)
    )
    if edit_split_match:
        if len(edit_split_match.groups()) == 2:
            target_item = edit_split_match.group(1).strip()
            splits_raw = edit_split_match.group(2).strip()
        else:
            target_item = ""
            splits_raw = edit_split_match.group(1).strip()

        expense = get_target_expense(target_item)
        if not expense:
            reply_text(messaging_api, reply_token, f"⚠️ 找不到欲修改的支出紀錄！" if target_item else "⚠️ 目前尚無可修改的支出紀錄！")
            return

        if any(k in splits_raw for k in ["全員", "全體", "大家", "全部", "每人", "所有人"]):
            target_members = current_members
            is_all = True
        else:
            target_members = parse_split_names(splits_raw, current_members)
            is_all = (len(target_members) == len(current_members))

        if not target_members:
            reply_text(messaging_api, reply_token, f"⚠️ 找不到符合的分攤夥伴【{splits_raw}】，請確認成員名單！")
            return

        split_count = len(target_members)
        db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == expense.id).delete()
        expense.split_count = split_count
        expense.split_type = "EQUAL_ALL" if is_all else f"CUSTOM_{split_count}"
        per_person_base = round(expense.amount / split_count, 2)
        group.last_active_expense_id = expense.id
        db.commit()

        for m in target_members:
            db.add(ExpenseSplit(expense_id=expense.id, member_id=m.id, amount_owed=per_person_base))
        db.commit()

        curr = expense.currency or (group.base_currency or "TWD")
        orig_amt = expense.original_amount if (expense.original_amount and expense.original_amount > 0) else expense.amount
        per_person_orig = orig_amt / split_count
        names_str = "、".join(m.display_name for m in target_members)
        split_desc = f"全體 {split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）" if is_all else f"{names_str} 共 {split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）"
        payer_name = expense.payer.display_name if expense.payer else "未知"

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            payer_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        reply_flex(messaging_api, reply_token, f"✅ 已成功更新【{expense.item_name}】分攤夥伴！", card)
        return

    # Pattern 5: 支援若剛在點選修改金額後直接傳送純數字（如「800」）
    if re.match(r"^\d+(?:\.\d+)?$", user_text) and group.last_active_expense_id:
        new_amt = float(user_text)
        expense = db.query(Expense).filter(
            Expense.group_id == group.id,
            Expense.id == group.last_active_expense_id,
            Expense.is_deleted == False
        ).first()
        if expense:
            rate = expense.exchange_rate or 1.0
            expense.original_amount = new_amt
            expense.amount = round(new_amt * rate, 2)
            split_count = max(expense.split_count or 1, 1)
            per_person_base = round(expense.amount / split_count, 2)
            for s in expense.splits:
                s.amount_owed = per_person_base
            db.commit()

            curr = expense.currency or (group.base_currency or "TWD")
            per_person_orig = new_amt / split_count
            payer_name = expense.payer.display_name if expense.payer else "未知"
            split_desc = f"{split_count}人均分（每人 {format_amount(per_person_orig, curr)}）"

            now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
            card = create_receipt_flex(
                expense.id,
                expense.item_name,
                expense.amount,
                payer_name,
                split_desc,
                now_str,
                currency=expense.currency,
                original_amount=expense.original_amount,
                rate=expense.exchange_rate
            )
            display_cost = format_amount(expense.original_amount, expense.currency)
            reply_flex(messaging_api, reply_token, f"✅ 已成功將【{expense.item_name}】金額修改為 {display_cost}！", card)
            return

    # (H) 指定成員均分文字指令（支援草稿等待時輸入「佳欣、南廷、園子、玫璇 均分」或「佳欣 南廷 園子 玫璇」）
    waiting_draft = db.query(DraftExpense).filter(
        DraftExpense.line_group_id == line_group_id
    ).order_by(DraftExpense.id.desc()).first()

    if waiting_draft and waiting_draft.payer_member_id:
        if user_text in ["全員", "全體", "大家", "全部", "每人", "所有人", "全員均分", "全體均分"]:
            matched_members = current_members
        else:
            matched_members = parse_split_names(user_text, current_members)

        if matched_members:
            payer = db.query(Member).filter(Member.id == waiting_draft.payer_member_id).first()
            if not payer:
                payer = current_members[0]

            split_count = len(matched_members)
            curr = waiting_draft.currency or (group.base_currency or "TWD")
            orig_amt = waiting_draft.original_amount if (waiting_draft.original_amount and waiting_draft.original_amount > 0) else waiting_draft.amount
            per_person_orig = orig_amt / split_count
            names_str = "、".join([m.display_name for m in matched_members])

            if split_count == len(current_members):
                split_desc = f"全體 {split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）"
                split_type = "EQUAL_ALL"
            else:
                split_desc = f"{names_str} 共 {split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）"
                split_type = f"CUSTOM_{split_count}"

            per_person_base_amount = round(waiting_draft.amount / split_count, 2)

            expense = Expense(
                group_id=group.id,
                item_name=waiting_draft.item_name,
                currency=curr,
                original_amount=orig_amt,
                exchange_rate=waiting_draft.exchange_rate or 1.0,
                amount=waiting_draft.amount,
                payer_id=payer.id,
                split_count=split_count,
                split_type=split_type
            )
            db.add(expense)
            db.commit()
            db.refresh(expense)

            for m in matched_members:
                split = ExpenseSplit(
                    expense_id=expense.id,
                    member_id=m.id,
                    amount_owed=per_person_base_amount
                )
                db.add(split)

            db.delete(waiting_draft)
            db.commit()

            now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
            receipt_card = create_receipt_flex(
                expense.id,
                expense.item_name,
                expense.amount,
                payer.display_name,
                split_desc,
                now_str,
                currency=expense.currency,
                original_amount=expense.original_amount,
                rate=expense.exchange_rate
            )
            display_cost = format_amount(expense.original_amount, expense.currency)
            reply_flex(messaging_api, reply_token, f"✅ 記帳成功：{expense.item_name} {display_cost}", receipt_card)
            return

    # (H-2) 解析小額還款文字指令（例如：「江小 還 佳欣 40 THB」、「江小 轉帳給 佳欣 500」）
    parsed_repay = parse_repayment(user_text, current_members, default_curr=group.base_currency or "TWD")
    if parsed_repay:
        from_m = parsed_repay["from_member"]
        to_m = parsed_repay["to_member"]
        repay_amt = parsed_repay["amount"]
        repay_curr = parsed_repay["currency"]

        rate = get_exchange_rate(db, group.id, repay_curr)
        base_amount = repay_amt * rate

        expense = Expense(
            group_id=group.id,
            item_name=f"小額還款：{from_m.display_name} ➜ {to_m.display_name}",
            currency=repay_curr,
            original_amount=repay_amt,
            exchange_rate=rate,
            amount=base_amount,
            payer_id=from_m.id,
            split_count=1,
            split_type="REPAYMENT"
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)

        split = ExpenseSplit(
            expense_id=expense.id,
            member_id=to_m.id,
            amount_owed=base_amount
        )
        db.add(split)
        db.commit()

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        card = create_repayment_flex(
            expense_id=expense.id,
            from_name=from_m.display_name,
            to_name=to_m.display_name,
            amount=repay_amt,
            currency=repay_curr,
            base_amount=base_amount,
            rate=rate,
            date_str=now_str
        )
        display_cost = format_amount(repay_amt, repay_curr)
        reply_flex(messaging_api, reply_token, f"✅ 還款登記成功：{from_m.display_name} ➜ {to_m.display_name} {display_cost}", card)
        return

    # (I) 解析記帳文字指令（支援單一訊息一次完成記帳、或引導式記帳）
    # 例如：
    # 「泰奶 200 佳欣付 佳欣 南廷 園子 玫璇」 -> 一則訊息直接完成！
    # 「泰奶 200 佳欣付 全員」 -> 一則訊息直接完成！
    # 「泰奶 200 佳欣 4人」 -> 直接跳出 4 人挑選單
    # 「泰奶 200 佳欣付」 -> 直接跳出分攤方式選單
    # 「泰奶 200」 -> 進入步驟一付款人選單
    parsed_exp = parse_full_expense(user_text, current_members, default_curr=group.base_currency or "TWD")
    if parsed_exp:
        mode = parsed_exp["mode"]
        item_name = parsed_exp["item"]
        raw_amount = parsed_exp["amount"]
        currency = parsed_exp["currency"]
        rate = get_exchange_rate(db, group.id, currency)
        base_amount = raw_amount * rate

        # Mode A: FULL (單一訊息直接完成記帳！)
        if mode == "FULL":
            payer = parsed_exp["payer"]
            split_members = parsed_exp["split_members"]
            split_count = len(split_members)
            per_person_orig = raw_amount / split_count
            names_str = "、".join([m.display_name for m in split_members])

            if parsed_exp.get("split_type") == "ALL" or split_count == len(current_members):
                split_desc = f"全體 {split_count} 人均分（每人 {format_amount(per_person_orig, currency)}）"
                split_type = "EQUAL_ALL"
            else:
                split_desc = f"{names_str} 共 {split_count} 人均分（每人 {format_amount(per_person_orig, currency)}）"
                split_type = f"CUSTOM_{split_count}"

            per_person_base_amount = round(base_amount / split_count, 2)

            expense = Expense(
                group_id=group.id,
                item_name=item_name,
                currency=currency,
                original_amount=raw_amount,
                exchange_rate=rate,
                amount=base_amount,
                payer_id=payer.id,
                split_count=split_count,
                split_type=split_type
            )
            db.add(expense)
            db.commit()
            db.refresh(expense)

            for m in split_members:
                split = ExpenseSplit(
                    expense_id=expense.id,
                    member_id=m.id,
                    amount_owed=per_person_base_amount
                )
                db.add(split)

            if waiting_draft:
                db.delete(waiting_draft)
            group.last_active_expense_id = expense.id
            db.commit()

            now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
            receipt_card = create_receipt_flex(
                expense.id,
                expense.item_name,
                expense.amount,
                payer.display_name,
                split_desc,
                now_str,
                currency=expense.currency,
                original_amount=expense.original_amount,
                rate=expense.exchange_rate
            )
            display_cost = format_amount(expense.original_amount, expense.currency)
            reply_flex(messaging_api, reply_token, f"✅ 記帳成功：{expense.item_name} {display_cost}", receipt_card)
            return

        # Mode B: COUNT (指定了付款人與特定目標人數，如「泰奶 200 佳欣 4人」)
        elif mode == "COUNT":
            payer = parsed_exp["payer"]
            target_count = parsed_exp["target_count"]
            if target_count == len(current_members):
                split_count = target_count
                per_person_orig = raw_amount / split_count
                split_desc = f"全體 {split_count} 人均分（每人 {format_amount(per_person_orig, currency)}）"
                per_person_base_amount = round(base_amount / split_count, 2)
                expense = Expense(
                    group_id=group.id,
                    item_name=item_name,
                    currency=currency,
                    original_amount=raw_amount,
                    exchange_rate=rate,
                    amount=base_amount,
                    payer_id=payer.id,
                    split_count=split_count,
                    split_type="EQUAL_ALL"
                )
                db.add(expense)
                db.commit()
                db.refresh(expense)
                for m in current_members:
                    db.add(ExpenseSplit(expense_id=expense.id, member_id=m.id, amount_owed=per_person_base_amount))
                if waiting_draft:
                    db.delete(waiting_draft)
                group.last_active_expense_id = expense.id
                db.commit()

                now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
                receipt_card = create_receipt_flex(
                    expense.id,
                    expense.item_name,
                    expense.amount,
                    payer.display_name,
                    split_desc,
                    now_str,
                    currency=expense.currency,
                    original_amount=expense.original_amount,
                    rate=expense.exchange_rate
                )
                display_cost = format_amount(expense.original_amount, expense.currency)
                reply_flex(messaging_api, reply_token, f"✅ 記帳成功：{expense.item_name} {display_cost}", receipt_card)
                return
            else:
                draft = DraftExpense(
                    line_group_id=line_group_id,
                    initiator_user_id=user_id or "user",
                    item_name=item_name,
                    currency=currency,
                    original_amount=raw_amount,
                    exchange_rate=rate,
                    amount=base_amount,
                    payer_member_id=payer.id
                )
                db.add(draft)
                db.commit()
                db.refresh(draft)

                member_dicts = [{"id": m.id, "name": m.display_name} for m in current_members]
                flex_card = create_member_picker_flex(
                    draft.id,
                    item_name,
                    base_amount,
                    payer.display_name,
                    payer.id,
                    member_dicts,
                    selected_ids=[],
                    target_count=target_count,
                    currency=currency,
                    original_amount=raw_amount,
                    rate=rate
                )
                reply_flex(messaging_api, reply_token, f"🎯 請挑選 {target_count} 位均分夥伴（{item_name}）", flex_card)
                return

        # Mode C: PAYER_ONLY (指定了付款人，但尚未指定均分，如「泰奶 200 佳欣付」)
        elif mode == "PAYER_ONLY":
            payer = parsed_exp["payer"]
            draft = DraftExpense(
                line_group_id=line_group_id,
                initiator_user_id=user_id or "user",
                item_name=item_name,
                currency=currency,
                original_amount=raw_amount,
                exchange_rate=rate,
                amount=base_amount,
                payer_member_id=payer.id
            )
            db.add(draft)
            db.commit()
            db.refresh(draft)

            member_dicts = [{"id": m.id, "name": m.display_name} for m in current_members]
            flex_card = create_split_selection_flex(
                draft.id,
                item_name,
                base_amount,
                payer.display_name,
                payer.id,
                member_dicts,
                currency=currency,
                original_amount=raw_amount,
                rate=rate
            )
            reply_flex(messaging_api, reply_token, f"請選定分攤方式（{item_name}）", flex_card)
            return

        # Mode D: SIMPLE (僅輸入「泰奶 200」)
        elif mode == "SIMPLE":
            draft = DraftExpense(
                line_group_id=line_group_id,
                initiator_user_id=user_id or "user",
                item_name=item_name,
                currency=currency,
                original_amount=raw_amount,
                exchange_rate=rate,
                amount=base_amount
            )
            db.add(draft)
            db.commit()
            db.refresh(draft)

            member_dicts = [{"id": m.id, "name": m.display_name} for m in current_members]
            flex_card = create_payer_selection_flex(
                draft.id,
                item_name,
                base_amount,
                member_dicts,
                currency=currency,
                original_amount=raw_amount,
                rate=rate
            )
            display_cost = format_amount(raw_amount, currency)
            reply_flex(messaging_api, reply_token, f"請選定由誰付款（{item_name} {display_cost}）", flex_card)
            return


# -------------------------------------------------------------
# 按鈕 Postback 事件處理 (PostbackEvent)
# -------------------------------------------------------------
def handle_postback(event: PostbackEvent, db: Session, api_client: ApiClient):
    messaging_api = MessagingApi(api_client)
    reply_token = event.reply_token
    postback_data = event.postback.data
    params = dict(urllib.parse.parse_qsl(postback_data))
    action = params.get("action")
    line_group_id = get_group_id_from_event(event)
    user_id = getattr(event.source, "user_id", "")

    group = get_or_create_group(db, line_group_id)

    # 1. 步驟一選定付款人完成 -> 進入步驟二：選定幾人均分
    if action == "select_payer":
        draft_id = int(params.get("draft_id", 0))
        payer_id = int(params.get("payer_id", 0))

        draft = db.query(DraftExpense).filter(DraftExpense.id == draft_id).first()
        payer = db.query(Member).filter(Member.id == payer_id).first()

        if not draft or not payer:
            reply_text(messaging_api, reply_token, "⚠️ 該筆記帳作業已過期或不存在，請重新輸入項目與金額！")
            return

        draft.payer_member_id = payer.id
        db.commit()

        members = db.query(Member).filter(Member.group_id == group.id).all()
        member_dicts = [{"id": m.id, "name": m.display_name} for m in members]

        # 發送【步驟 2：選定幾人均分】按鈕卡片
        flex_card = create_split_selection_flex(
            draft.id,
            draft.item_name,
            draft.amount,
            payer.display_name,
            payer.id,
            member_dicts,
            currency=draft.currency or "TWD",
            original_amount=draft.original_amount,
            rate=draft.exchange_rate or 1.0
        )
        reply_flex(messaging_api, reply_token, f"請選定分攤方式（{draft.item_name}）", flex_card)
        return

    # 2. 步驟二選定分攤方式完成 -> 正式寫入支出與分攤明細，發送收據
    if action == "confirm_split":
        draft_id = int(params.get("draft_id", 0))
        payer_id = int(params.get("payer_id", 0))
        split_mode = params.get("split_mode", "ALL")

        draft = db.query(DraftExpense).filter(DraftExpense.id == draft_id).first()
        payer = db.query(Member).filter(Member.id == payer_id).first()

        if not draft or not payer:
            reply_text(messaging_api, reply_token, "⚠️ 該筆記帳作業已過期或不存在，請重新輸入！")
            return

        members = db.query(Member).filter(Member.group_id == group.id).all()
        total_members = len(members)

        curr = draft.currency or "TWD"
        orig_amt = draft.original_amount if (draft.original_amount and draft.original_amount > 0) else draft.amount

        if split_mode == "COUNT":
            split_count = int(params.get("count", total_members))
            split_type = f"EQUAL_{split_count}"
            per_person_orig = orig_amt / split_count
            split_desc = f"{split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）"
            target_members = members[:split_count] if split_count <= total_members else members
            per_person_base_amount = round(draft.amount / split_count, 2)
        else:
            split_count = max(total_members, 1)
            split_type = "EQUAL_ALL"
            per_person_orig = orig_amt / split_count
            split_desc = f"全體 {split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）"
            target_members = members
            per_person_base_amount = round(draft.amount / split_count, 2)

        # 建立正式 Expense
        expense = Expense(
            group_id=group.id,
            item_name=draft.item_name,
            currency=curr,
            original_amount=orig_amt,
            exchange_rate=draft.exchange_rate or 1.0,
            amount=draft.amount,
            payer_id=payer.id,
            split_count=split_count,
            split_type=split_type
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)

        # 建立 ExpenseSplit 明細
        for m in target_members:
            split = ExpenseSplit(
                expense_id=expense.id,
                member_id=m.id,
                amount_owed=per_person_base_amount
            )
            db.add(split)

        # 清除 Draft
        db.delete(draft)
        group.last_active_expense_id = expense.id
        db.commit()

        # 發送記帳成功收據卡片
        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        receipt_card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            payer.display_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        display_cost = format_amount(expense.original_amount, expense.currency)
        reply_flex(messaging_api, reply_token, f"✅ 記帳成功：{expense.item_name} {display_cost}", receipt_card)
        return

    # 2.5 挑選均分夥伴（指定人數或自由勾選切換）
    if action in ["pick_split_members", "pick_custom_members"]:
        draft_id = int(params.get("draft_id", 0))
        payer_id = int(params.get("payer_id", 0))
        target_count = int(params.get("target_count", 0))
        selected_raw = params.get("selected", "")
        selected_ids = [int(x) for x in selected_raw.split(",") if x.strip().isdigit()]

        draft = db.query(DraftExpense).filter(DraftExpense.id == draft_id).first()
        payer = db.query(Member).filter(Member.id == payer_id).first()

        if not draft or not payer:
            reply_text(messaging_api, reply_token, "⚠️ 該筆記帳作業已過期或不存在，請重新輸入！")
            return

        members = db.query(Member).filter(Member.group_id == group.id).all()
        member_dicts = [{"id": m.id, "name": m.display_name} for m in members]

        flex_card = create_member_picker_flex(
            draft.id,
            draft.item_name,
            draft.amount,
            payer.display_name,
            payer.id,
            member_dicts,
            selected_ids=selected_ids,
            target_count=target_count,
            currency=draft.currency or "TWD",
            original_amount=draft.original_amount,
            rate=draft.exchange_rate or 1.0
        )
        title_hint = f"🎯 選擇均分夥伴（{target_count}人均分）" if target_count > 0 else "🎯 自由勾選均分夥伴"
        reply_flex(messaging_api, reply_token, title_hint, flex_card)
        return

    # 2.5.1 確認送出已挑選的均分夥伴
    if action == "confirm_picked_split":
        draft_id = int(params.get("draft_id", 0))
        payer_id = int(params.get("payer_id", 0))
        selected_raw = params.get("selected", "")
        selected_ids = [int(x) for x in selected_raw.split(",") if x.strip().isdigit()]

        draft = db.query(DraftExpense).filter(DraftExpense.id == draft_id).first()
        payer = db.query(Member).filter(Member.id == payer_id).first()

        if not draft or not payer:
            reply_text(messaging_api, reply_token, "⚠️ 該筆記帳作業已過期或不存在，請重新輸入！")
            return

        if not selected_ids:
            reply_text(messaging_api, reply_token, "⚠️ 尚未選取任何均分夥伴，請重新選擇！")
            return

        target_members = db.query(Member).filter(Member.id.in_(selected_ids)).all()
        if not target_members:
            reply_text(messaging_api, reply_token, "⚠️ 選取的夥伴不存在，請重新操作！")
            return

        curr = draft.currency or "TWD"
        orig_amt = draft.original_amount if (draft.original_amount and draft.original_amount > 0) else draft.amount
        split_count = len(target_members)
        per_person_orig = orig_amt / split_count
        per_person_base = round(draft.amount / split_count, 2)
        names_str = "、".join(m.display_name for m in target_members)

        split_desc = f"{names_str} 共 {split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）"

        expense = Expense(
            group_id=group.id,
            item_name=draft.item_name,
            currency=curr,
            original_amount=orig_amt,
            exchange_rate=draft.exchange_rate or 1.0,
            amount=draft.amount,
            payer_id=payer.id,
            split_count=split_count,
            split_type=f"CUSTOM_{split_count}"
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)

        for m in target_members:
            split = ExpenseSplit(
                expense_id=expense.id,
                member_id=m.id,
                amount_owed=per_person_base
            )
            db.add(split)

        db.delete(draft)
        group.last_active_expense_id = expense.id
        db.commit()

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        receipt_card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            payer.display_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        display_cost = format_amount(expense.original_amount, expense.currency)
        reply_flex(messaging_api, reply_token, f"✅ 記帳成功：{expense.item_name} {display_cost}", receipt_card)
        return

    # 2.6 單一成員全額承擔
    if action == "confirm_single_split":
        draft_id = int(params.get("draft_id", 0))
        payer_id = int(params.get("payer_id", 0))
        target_id = int(params.get("target_member_id", 0))

        draft = db.query(DraftExpense).filter(DraftExpense.id == draft_id).first()
        payer = db.query(Member).filter(Member.id == payer_id).first()
        target_m = db.query(Member).filter(Member.id == target_id).first()

        if not draft or not payer or not target_m:
            reply_text(messaging_api, reply_token, "⚠️ 該筆記帳作業已過期或不存在，請重新輸入！")
            return

        curr = draft.currency or "TWD"
        orig_amt = draft.original_amount if (draft.original_amount and draft.original_amount > 0) else draft.amount
        split_desc = f"由 {target_m.display_name} 獨自全額承擔 ({format_amount(orig_amt, curr)})"

        expense = Expense(
            group_id=group.id,
            item_name=draft.item_name,
            currency=curr,
            original_amount=orig_amt,
            exchange_rate=draft.exchange_rate or 1.0,
            amount=draft.amount,
            payer_id=payer.id,
            split_count=1,
            split_type="SINGLE_MEMBER"
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)

        split = ExpenseSplit(
            expense_id=expense.id,
            member_id=target_m.id,
            amount_owed=draft.amount
        )
        db.add(split)

        db.delete(draft)
        group.last_active_expense_id = expense.id
        db.commit()

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        receipt_card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            payer.display_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        display_cost = format_amount(expense.original_amount, expense.currency)
        reply_flex(messaging_api, reply_token, f"✅ 記帳成功：{expense.item_name} {display_cost}", receipt_card)
        return

    # 2.7 切換當下預設幣別
    if action == "set_base_currency":
        new_curr = params.get("currency", "TWD")
        group.base_currency = new_curr
        db.commit()
        reply_text(
            messaging_api,
            reply_token,
            f"✅ 已成功將群組當下預設幣別切換為：【{new_curr}】！\n"
            f"👉 之後記帳直接輸入「拉麵 1500」或「門票 800」就會自動視為 {new_curr} 囉！"
        )
        return

    # 3. 點選「查看結算」
    if action == "view_settlement":
        settlement_data = calculate_group_settlement(db, group.id)
        reply_flex(messaging_api, reply_token, "📊 結算報表", create_settlement_flex(settlement_data))
        return

    # 4. 點選「查看明細」
    if action == "view_expenses":
        expenses = db.query(Expense).filter(
            Expense.group_id == group.id,
            Expense.is_deleted == False
        ).order_by(Expense.id.desc()).all()

        base_curr = group.base_currency or "TWD"
        exp_list = []
        for e in expenses:
            exp_list.append({
                "id": e.id,
                "item_name": e.item_name,
                "amount": e.amount,
                "original_amount": e.original_amount if e.original_amount else e.amount,
                "currency": e.currency or base_curr,
                "payer_name": e.payer.display_name if e.payer else "未知",
                "split_desc": f"{e.split_count}人均分",
                "split_type": e.split_type
            })
        reply_flex(messaging_api, reply_token, "📋 支出明細", create_expense_list_flex(exp_list, base_curr))
        return

    # 5. 點選「撤銷/刪除支出或還款」
    if action == "delete_expense":
        expense_id = int(params.get("expense_id", 0))
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if expense:
            expense.is_deleted = True
            db.commit()
            if expense.split_type == "REPAYMENT":
                reply_text(messaging_api, reply_token, f"🗑️ 已成功撤銷【{expense.item_name}】還款紀錄！債務已自動還原。")
            else:
                reply_text(messaging_api, reply_token, f"🗑️ 已成功撤銷【{expense.item_name}】（NT$ {int(expense.amount):,}）！")
        else:
            reply_text(messaging_api, reply_token, "⚠️ 找不到該筆支出紀錄。")
        return

    # 4.5 編輯支出功能（從查看明細點選「✏️ 修改」）
    if action == "edit_expense_menu":
        expense_id = int(params.get("expense_id", 0))
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        if not expense:
            reply_text(messaging_api, reply_token, "⚠️ 找不到該筆支出紀錄，可能已被刪除！")
            return

        group.last_active_expense_id = expense.id
        db.commit()

        base_curr = group.base_currency or "TWD"
        payer_name = expense.payer.display_name if expense.payer else "未知"
        split_desc = f"{expense.split_count}人均分"
        if expense.splits:
            names = [s.member.display_name for s in expense.splits if s.member]
            all_m_count = len(group.members)
            if len(names) == all_m_count and all_m_count > 0:
                split_desc = f"全體 {len(names)} 人均分"
            else:
                split_desc = f"{'、'.join(names)} ({len(names)}人)"

        exp_data = {
            "id": expense.id,
            "item_name": expense.item_name,
            "amount": expense.amount,
            "original_amount": expense.original_amount if expense.original_amount else expense.amount,
            "currency": expense.currency or base_curr,
            "exchange_rate": expense.exchange_rate or 1.0,
            "payer_name": payer_name,
            "payer_id": expense.payer_id,
            "split_desc": split_desc,
            "split_count": expense.split_count,
            "split_type": expense.split_type
        }
        reply_flex(messaging_api, reply_token, f"✏️ 編輯支出：{expense.item_name}", create_edit_expense_flex(exp_data, base_curr))
        return

    if action == "edit_prompt_amount":
        expense_id = int(params.get("expense_id", 0))
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        if not expense:
            reply_text(messaging_api, reply_token, "⚠️ 找不到該筆支出紀錄！")
            return
        group.last_active_expense_id = expense.id
        db.commit()
        set_waiting_state(line_group_id, user_id, "edit_amount", {"expense_id": expense.id})
        curr = expense.currency or (group.base_currency or "TWD")
        cur_amt_str = format_amount(expense.original_amount or expense.amount, curr)
        reply_text(
            messaging_api,
            reply_token,
            f"✏️ 請輸入【{expense.item_name}】的新金額（目前為 {cur_amt_str}）：\n\n"
            f"💡 直接傳送新金額即可（例如「500」），或傳送「取消」放棄修改。"
        )
        return

    if action == "edit_prompt_name":
        expense_id = int(params.get("expense_id", 0))
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        if not expense:
            reply_text(messaging_api, reply_token, "⚠️ 找不到該筆支出紀錄！")
            return
        group.last_active_expense_id = expense.id
        db.commit()
        set_waiting_state(line_group_id, user_id, "edit_name", {"expense_id": expense.id})
        reply_text(
            messaging_api,
            reply_token,
            f"✏️ 請輸入【{expense.item_name}】的新名稱：\n\n"
            f"💡 直接傳送新名稱即可（例如「泰國機場接送」），或傳送「取消」放棄修改。"
        )
        return

    if action == "edit_show_payer":
        expense_id = int(params.get("expense_id", 0))
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        if not expense:
            reply_text(messaging_api, reply_token, "⚠️ 找不到該筆支出紀錄！")
            return
        group.last_active_expense_id = expense.id
        db.commit()
        members = db.query(Member).filter(Member.group_id == group.id).all()
        member_dicts = [{"id": m.id, "name": m.display_name} for m in members]
        reply_flex(
            messaging_api,
            reply_token,
            f"👤 更換付款人（{expense.item_name}）",
            create_edit_payer_selection_flex(expense.id, expense.item_name, member_dicts, expense.payer_id)
        )
        return

    if action == "do_edit_payer":
        expense_id = int(params.get("expense_id", 0))
        payer_id = int(params.get("payer_id", 0))
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        new_payer = db.query(Member).filter(Member.id == payer_id).first()
        if not expense or not new_payer:
            reply_text(messaging_api, reply_token, "⚠️ 操作失敗，找不到該筆支出或成員！")
            return

        expense.payer_id = new_payer.id
        group.last_active_expense_id = expense.id
        db.commit()

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        split_desc = f"{expense.split_count}人均分"
        if expense.splits:
            names = [s.member.display_name for s in expense.splits if s.member]
            all_m_count = len(group.members)
            if len(names) == all_m_count and all_m_count > 0:
                split_desc = f"全體 {len(names)} 人均分"
            else:
                split_desc = f"{'、'.join(names)} ({len(names)}人)"

        card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            new_payer.display_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        reply_flex(messaging_api, reply_token, f"✅ 已將【{expense.item_name}】付款人更改為【{new_payer.display_name}】", card)
        return

    if action == "edit_show_splits":
        expense_id = int(params.get("expense_id", 0))
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        if not expense:
            reply_text(messaging_api, reply_token, "⚠️ 找不到該筆支出紀錄！")
            return
        group.last_active_expense_id = expense.id
        db.commit()

        members = db.query(Member).filter(Member.group_id == group.id).all()
        member_dicts = [{"id": m.id, "name": m.display_name} for m in members]
        current_split_member_ids = [s.member_id for s in expense.splits]
        curr = expense.currency or (group.base_currency or "TWD")
        orig_amt = expense.original_amount if (expense.original_amount and expense.original_amount > 0) else expense.amount
        amt_str = format_amount(orig_amt, curr)

        from app.config import get_base_url
        base_url = get_base_url()

        reply_flex(
            messaging_api,
            reply_token,
            f"🤝 重新設定分攤（{expense.item_name}）",
            create_edit_split_selection_flex(
                expense.id,
                expense.item_name,
                amt_str,
                member_dicts,
                current_split_member_ids,
                base_url=base_url
            )
        )
        return

    if action == "do_edit_split_all":
        expense_id = int(params.get("expense_id", 0))
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        if not expense:
            reply_text(messaging_api, reply_token, "⚠️ 找不到該筆支出紀錄！")
            return

        members = db.query(Member).filter(Member.group_id == group.id).all()
        split_count = len(members)
        if split_count == 0:
            reply_text(messaging_api, reply_token, "⚠️ 群組尚無任何成員！")
            return

        db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == expense.id).delete()
        expense.split_count = split_count
        expense.split_type = "EQUAL_ALL"
        per_person_base = round(expense.amount / split_count, 2)
        group.last_active_expense_id = expense.id
        db.commit()

        for m in members:
            db.add(ExpenseSplit(
                expense_id=expense.id,
                member_id=m.id,
                amount_owed=per_person_base
            ))
        db.commit()

        curr = expense.currency or (group.base_currency or "TWD")
        orig_amt = expense.original_amount if (expense.original_amount and expense.original_amount > 0) else expense.amount
        per_person_orig = orig_amt / split_count
        split_desc = f"全體 {split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）"

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        payer_name = expense.payer.display_name if expense.payer else "未知"
        card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            payer_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        reply_flex(messaging_api, reply_token, f"✅ 已將【{expense.item_name}】改為全體均分！", card)
        return

    if action == "do_edit_split_single":
        expense_id = int(params.get("expense_id", 0))
        member_id = int(params.get("member_id", 0))
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        target_m = db.query(Member).filter(Member.id == member_id).first()
        if not expense or not target_m:
            reply_text(messaging_api, reply_token, "⚠️ 找不到該筆支出或成員！")
            return

        db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == expense.id).delete()
        expense.split_count = 1
        expense.split_type = "SINGLE_MEMBER"
        group.last_active_expense_id = expense.id
        db.commit()

        db.add(ExpenseSplit(
            expense_id=expense.id,
            member_id=target_m.id,
            amount_owed=expense.amount
        ))
        db.commit()

        curr = expense.currency or (group.base_currency or "TWD")
        orig_amt = expense.original_amount if (expense.original_amount and expense.original_amount > 0) else expense.amount
        split_desc = f"由 {target_m.display_name} 獨自全額承擔 ({format_amount(orig_amt, curr)})"

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        payer_name = expense.payer.display_name if expense.payer else "未知"
        card = create_receipt_flex(
            expense.id,
            expense.item_name,
            expense.amount,
            payer_name,
            split_desc,
            now_str,
            currency=expense.currency,
            original_amount=expense.original_amount,
            rate=expense.exchange_rate
        )
        reply_flex(messaging_api, reply_token, f"✅ 已將【{expense.item_name}】改由 {target_m.display_name} 全額承擔！", card)
        return

    # 5.5 一鍵登記小額還款（從結算卡片點選）
    if action == "quick_repay":
        from_name = params.get("from", "").strip()
        to_name = params.get("to", "").strip()
        amount_raw = params.get("amount", "0")
        curr = params.get("currency", group.base_currency or "TWD")

        try:
            repay_amt = float(amount_raw)
        except ValueError:
            repay_amt = 0.0

        if repay_amt <= 0:
            reply_text(messaging_api, reply_token, "⚠️ 還款金額無效！")
            return

        members = db.query(Member).filter(Member.group_id == group.id).all()
        from_m = find_member_fuzzy(from_name, members)
        to_m = find_member_fuzzy(to_name, members)

        if not from_m or not to_m:
            reply_text(messaging_api, reply_token, f"⚠️ 找不到還款夥伴【{from_name}】或【{to_name}】，請先確認成員名單！")
            return

        rate = get_exchange_rate(db, group.id, curr)
        base_amount = repay_amt * rate

        expense = Expense(
            group_id=group.id,
            item_name=f"小額還款：{from_m.display_name} ➜ {to_m.display_name}",
            currency=curr,
            original_amount=repay_amt,
            exchange_rate=rate,
            amount=base_amount,
            payer_id=from_m.id,
            split_count=1,
            split_type="REPAYMENT"
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)

        split = ExpenseSplit(
            expense_id=expense.id,
            member_id=to_m.id,
            amount_owed=base_amount
        )
        db.add(split)
        db.commit()

        now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
        card = create_repayment_flex(
            expense_id=expense.id,
            from_name=from_m.display_name,
            to_name=to_m.display_name,
            amount=repay_amt,
            currency=curr,
            base_amount=base_amount,
            rate=rate,
            date_str=now_str
        )
        display_cost = format_amount(repay_amt, curr)
        reply_flex(messaging_api, reply_token, f"✅ 還款登記成功：{from_m.display_name} ➜ {to_m.display_name} {display_cost}", card)
        return

    # 6. 成員管理或新增引導
    if action in ["manage_members", "prompt_add_member"]:
        members = db.query(Member).filter(Member.group_id == group.id).all()
        members_str = "、".join([m.display_name for m in members]) if members else "尚無"
        msg = (
            f"👥 目前旅行夥伴（共 {len(members)} 位）：\n"
            f"{members_str}\n\n"
            f"💡 請直接傳送想加入的夥伴姓名：\n"
            f"「新增成員 小明 小美 阿豪」"
        )
        reply_text(messaging_api, reply_token, msg)
        return


# -------------------------------------------------------------
# 機器人加入群組事件處理 (JoinEvent)
# -------------------------------------------------------------
def handle_join_event(event: JoinEvent, db: Session, api_client: ApiClient):
    messaging_api = MessagingApi(api_client)
    reply_token = event.reply_token
    line_group_id = get_group_id_from_event(event)
    get_or_create_group(db, line_group_id)

    welcome_msg = (
        "👋 大家好！我是旅行分帳小幫手 🧳\n\n"
        "✨ 核心功能：\n"
        "1. 點選按鈕記帳：輸入「晚餐 1200」立即彈出卡片選付款人與均分人數\n"
        "2. 一鍵結算：自動計算每人收支，以最少轉帳次數搞定還款！\n\n"
        "💡 建議第一步：傳送「新增成員 小明 小美 阿豪」快速設定旅伴名單！"
    )
    reply_text(messaging_api, reply_token, welcome_msg)
