from typing import List, Dict, Any


def create_main_menu_flex() -> Dict[str, Any]:
    """主功能選單 Flex Message"""
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0284C7",
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "text",
                    "text": "🧳 旅行分帳小幫手",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "lg"
                },
                {
                    "type": "text",
                    "text": "輕鬆點選．誰付款幾人均分一目了然",
                    "color": "#E0F2FE",
                    "size": "xs",
                    "margin": "sm"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "action": {
                        "type": "message",
                        "label": "➕ 記帳（新增支出）",
                        "text": "記帳"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "📊 結算帳務與還款指南",
                        "data": "action=view_settlement",
                        "displayText": "查看結算"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "📋 帳務明細清單",
                        "data": "action=view_expenses",
                        "displayText": "查看明細"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "message",
                        "label": "💸 小額還款指南",
                        "text": "小額還款"
                    }
                },
                {
                    "type": "button",
                    "style": "link",
                    "color": "#64748B",
                    "action": {
                        "type": "postback",
                        "label": "👥 成員管理 / 新增旅伴",
                        "data": "action=manage_members",
                        "displayText": "成員名單"
                    }
                },
                {
                    "type": "button",
                    "style": "link",
                    "color": "#0284C7",
                    "action": {
                        "type": "message",
                        "label": "📖 完整指令大全與教學",
                        "text": "指令"
                    }
                }
            ]
        }
    }


def create_currency_selection_flex(current_currency: str = "TWD") -> Dict[str, Any]:
    """設定當下預設幣別卡片（按鈕點選）"""
    currencies = [
        ("🇯🇵 日幣 (JPY)", "JPY"),
        ("🇹🇼 台幣 (TWD)", "TWD"),
        ("🇰🇷 韓元 (KRW)", "KRW"),
        ("🇺🇸 美金 (USD)", "USD"),
        ("🇪🇺 歐元 (EUR)", "EUR"),
        ("🇹🇭 泰銖 (THB)", "THB"),
    ]

    buttons = []
    for label, code in currencies:
        is_current = (code == current_currency)
        buttons.append({
            "type": "button",
            "style": "primary" if is_current else "secondary",
            "color": "#0284C7" if is_current else None,
            "height": "sm",
            "action": {
                "type": "postback",
                "label": f"{label} {'(目前)' if is_current else ''}",
                "data": f"action=set_base_currency&currency={code}",
                "displayText": f"設定幣別 {code}"
            }
        })

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0284C7",
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "text",
                    "text": "💱 設定當下記帳幣別",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "md"
                },
                {
                    "type": "text",
                    "text": f"目前預設幣別：{current_currency}",
                    "color": "#E0F2FE",
                    "size": "xs",
                    "margin": "xs"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "text",
                    "text": "請點選旅程當下主要使用的貨幣：",
                    "size": "xs",
                    "color": "#64748B"
                },
                {
                    "type": "text",
                    "text": "💡 設定後，之後輸入「晚餐 1200」就會直接以此幣別記錄，不需每次輸入幣別代碼！",
                    "size": "xs",
                    "color": "#0284C7",
                    "wrap": True,
                    "margin": "xs"
                },
                {"type": "separator", "margin": "sm"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "margin": "sm",
                    "contents": buttons
                }
            ]
        }
    }


def create_command_guide_flex() -> Dict[str, Any]:
    """完整指令指南 Flex Message"""
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F172A",
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "text",
                    "text": "📖 旅行分帳指令大全",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "lg"
                },
                {
                    "type": "text",
                    "text": "直接傳送以下指令即可發動功能",
                    "color": "#94A3B8",
                    "size": "xs",
                    "margin": "xs"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "⚡ 1. 一則訊息直接記帳（最快！免按按鈕）：", "weight": "bold", "size": "xs", "color": "#16A34A"},
                        {"type": "text", "text": "• 泰奶 200 佳欣付 佳欣 南廷 園子 玫璇", "size": "xs", "color": "#0F172A", "margin": "xs"},
                        {"type": "text", "text": "• 泰奶 200 佳欣付 全員（全體均分）", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "• 泰奶 200 佳欣付 4人（直接挑選4人）", "size": "xs", "color": "#0F172A"}
                    ]
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "💳 2. 逐步按鈕引導記帳：", "weight": "bold", "size": "xs", "color": "#0284C7"},
                        {"type": "text", "text": "• 晚餐 1200（台幣記帳）", "size": "xs", "color": "#0F172A", "margin": "xs"},
                        {"type": "text", "text": "• 拉麵 3000 JPY 或 門票 50 USD", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "👉 點【📱 X人均分】可在同一個畫面勾選零洗版！", "size": "xxs", "color": "#0284C7"}
                    ]
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "👥 2. 旅伴成員管理：", "weight": "bold", "size": "xs", "color": "#0284C7"},
                        {"type": "text", "text": "• 新增成員 小明 小美 阿豪", "size": "xs", "color": "#0F172A", "margin": "xs"},
                        {"type": "text", "text": "• 改名 小磅 磅哥", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "• 刪除成員 團子", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "• 成員名單（查看目前夥伴）", "size": "xs", "color": "#0F172A"}
                    ]
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "💱 3. 匯率管理：", "weight": "bold", "size": "xs", "color": "#0284C7"},
                        {"type": "text", "text": "• 查看匯率（查看各國參考匯率）", "size": "xs", "color": "#0F172A", "margin": "xs"},
                        {"type": "text", "text": "• 設定匯率 JPY 0.22", "size": "xs", "color": "#0F172A"}
                    ]
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "📊 4. 結算與明細修改：", "weight": "bold", "size": "xs", "color": "#0284C7"},
                        {"type": "text", "text": "• 明細（查看紀錄，點【✏️修改】編輯項目）", "size": "xs", "color": "#0F172A", "margin": "xs"},
                        {"type": "text", "text": "• 修改 泰奶 金額 300 或 改金額 500", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "• 改付款人 佳欣 / 改分攤 全員", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "• 結算（最少轉帳次數還款指南）", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "• 新旅程（歸零重新開始）", "size": "xs", "color": "#0F172A"}
                    ]
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "💸 5. 旅途小額還款（隨時轉帳沖銷）：", "weight": "bold", "size": "xs", "color": "#059669"},
                        {"type": "text", "text": "• 江小 還 佳欣 40（以旅程當下幣別還款）", "size": "xs", "color": "#0F172A", "margin": "xs"},
                        {"type": "text", "text": "• 江小 還 佳欣 40 THB（指定幣別）", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "• 江小 轉帳給 佳欣 500 TWD", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "👉 查看結算中亦有【✅ 一鍵登記已還】按鈕！", "size": "xxs", "color": "#059669"}
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "➕ 記帳",
                        "text": "記帳"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📊 結算",
                        "data": "action=view_settlement",
                        "displayText": "查看結算"
                    }
                }
            ]
        }
    }


def create_payer_selection_flex(
    draft_id: int,
    item_name: str,
    amount: float,
    members: List[Dict[str, Any]],
    currency: str = "TWD",
    original_amount: float = None,
    rate: float = 1.0
) -> Dict[str, Any]:
    """選定誰付錢卡片（支援多幣別按鈕點選）"""
    from app.currency import format_amount
    orig_amt = original_amount if original_amount else amount
    amount_str = format_amount(orig_amt, currency)
    sub_amount_str = f"≈ NT$ {int(round(amount)):,} (匯率 {rate})" if currency != "TWD" else ""

    member_buttons = []
    for m in members:
        member_buttons.append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "postback",
                "label": f"👤 {m['name']}",
                "data": f"action=select_payer&draft_id={draft_id}&payer_id={m['id']}"
            }
        })

    member_buttons.append({
        "type": "button",
        "style": "link",
        "height": "sm",
        "color": "#0284C7",
        "action": {
            "type": "postback",
            "label": "➕ 旅伴不在選單中？新增成員",
            "data": f"action=prompt_add_member&draft_id={draft_id}",
            "displayText": "新增成員"
        }
    })

    amount_box_contents = [
        {"type": "text", "text": "💰 金額", "color": "#64748B", "size": "sm", "flex": 2},
        {"type": "text", "text": amount_str, "weight": "bold", "color": "#16A34A", "size": "lg", "flex": 5}
    ]

    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "📝 項目", "color": "#64748B", "size": "sm", "flex": 2},
                {"type": "text", "text": item_name, "weight": "bold", "color": "#0F172A", "size": "sm", "flex": 5}
            ]
        },
        {
            "type": "box",
            "layout": "horizontal",
            "contents": amount_box_contents
        }
    ]

    if sub_amount_str:
        body_contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "折合", "color": "#94A3B8", "size": "xs", "flex": 2},
                {"type": "text", "text": sub_amount_str, "color": "#64748B", "size": "xs", "flex": 5}
            ]
        })

    body_contents.extend([
        {"type": "separator", "margin": "md"},
        {
            "type": "text",
            "text": "請點選代墊付款的人：",
            "size": "xs",
            "color": "#94A3B8",
            "margin": "md"
        },
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "margin": "sm",
            "contents": member_buttons
        }
    ])

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#F8FAFC",
            "contents": [
                {
                    "type": "text",
                    "text": "💳 步驟 1/2：請選定誰付錢？",
                    "weight": "bold",
                    "size": "md",
                    "color": "#0F172A"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": body_contents
        }
    }


def create_split_selection_flex(
    draft_id: int,
    item_name: str,
    amount: float,
    payer_name: str,
    payer_id: int,
    members: List[Dict[str, Any]],
    currency: str = "TWD",
    original_amount: float = None,
    rate: float = 1.0
) -> Dict[str, Any]:
    """選定幾人均分卡片（支援多幣別按鈕點選）"""
    from app.currency import format_amount
    orig_amt = original_amount if original_amount else amount
    amount_str = format_amount(orig_amt, currency)
    member_count = len(members)

    per_person_orig = orig_amt / member_count if member_count > 0 else orig_amt
    per_person_orig_str = format_amount(per_person_orig, currency)

    buttons = []

    from app.config import get_base_url
    base_url = get_base_url()

    # 1. 全員均分按鈕（一鍵完成）
    buttons.append({
        "type": "button",
        "style": "primary",
        "color": "#0284C7",
        "action": {
            "type": "postback",
            "label": f"👥 全體均分 ({member_count}人，每人 {per_person_orig_str})",
            "data": f"action=confirm_split&draft_id={draft_id}&payer_id={payer_id}&split_mode=ALL"
        }
    })

    # 2. 人數均分按鈕 (2人、3人、4人...) -> 點擊直接開啟同頁勾選畫面（零洗版）
    for count in range(2, min(member_count, 6)):
        per_person = orig_amt / count
        per_str = format_amount(per_person, currency)
        buttons.append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "uri",
                "label": f"📱 {count} 人均分（同頁勾選・每人 {per_str}）",
                "uri": f"{base_url}/picker?draft_id={draft_id}&payer_id={payer_id}&target_count={count}"
            }
        })

    # 3. 指定特定成員均分 (自由勾選) -> 同樣直接開啟同頁勾選畫面
    buttons.append({
        "type": "button",
        "style": "link",
        "color": "#0284C7",
        "height": "sm",
        "action": {
            "type": "uri",
            "label": "🎯 自由勾選分攤夥伴（同頁選人）",
            "uri": f"{base_url}/picker?draft_id={draft_id}&payer_id={payer_id}&target_count=0"
        }
    })

    split_body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "📝 項目", "color": "#64748B", "size": "sm", "flex": 2},
                {"type": "text", "text": item_name, "weight": "bold", "color": "#0F172A", "size": "sm", "flex": 5}
            ]
        },
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "💰 金額", "color": "#64748B", "size": "sm", "flex": 2},
                {"type": "text", "text": amount_str, "weight": "bold", "color": "#16A34A", "size": "md", "flex": 5}
            ]
        }
    ]

    if currency != "TWD":
        split_body_contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "折合", "color": "#94A3B8", "size": "xs", "flex": 2},
                {"type": "text", "text": f"≈ NT$ {int(round(amount)):,} (匯率 {rate})", "color": "#64748B", "size": "xs", "flex": 5}
            ]
        })

    split_body_contents.extend([
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "👤 付款人", "color": "#64748B", "size": "sm", "flex": 2},
                {"type": "text", "text": payer_name, "weight": "bold", "color": "#0284C7", "size": "sm", "flex": 5}
            ]
        },
        {"type": "separator", "margin": "md"},
        {
            "type": "text",
            "text": "請選擇分攤方式：",
            "size": "xs",
            "color": "#94A3B8",
            "margin": "md"
        },
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "margin": "sm",
            "contents": buttons
        }
    ])

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#F8FAFC",
            "contents": [
                {
                    "type": "text",
                    "text": "🤝 步驟 2/2：有幾人均分？",
                    "weight": "bold",
                    "size": "md",
                    "color": "#0F172A"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": split_body_contents
        }
    }


def create_custom_split_flex(
    draft_id: int,
    item_name: str,
    amount: float,
    payer_name: str,
    payer_id: int,
    members: List[Dict[str, Any]],
    currency: str = "TWD",
    original_amount: float = None,
    rate: float = 1.0
) -> Dict[str, Any]:
    """指定成員分攤引導卡片"""
    from app.currency import format_amount
    orig_amt = original_amount if original_amount else amount
    amount_str = format_amount(orig_amt, currency)

    member_buttons = []
    for m in members:
        member_buttons.append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "postback",
                "label": f"👤 僅由 {m['name']} 承擔 (1人)",
                "data": f"action=confirm_single_split&draft_id={draft_id}&payer_id={payer_id}&target_member_id={m['id']}",
                "displayText": f"僅由 {m['name']} 承擔"
            }
        })

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0284C7",
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "text",
                    "text": "🎯 指定夥伴分攤",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "md"
                },
                {
                    "type": "text",
                    "text": f"{item_name}（{amount_str}）• {payer_name} 先代墊",
                    "color": "#E0F2FE",
                    "size": "xs",
                    "margin": "xs"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#F8FAFC",
                    "paddingAll": "10px",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "👉 若是多位特定成員均分：",
                            "weight": "bold",
                            "size": "sm",
                            "color": "#0F172A"
                        },
                        {
                            "type": "text",
                            "text": "請直接在聊天室傳送欲分攤的夥伴名字，例如：\n「分攤 佳欣 小磅」\n「分攤 佳欣 江小 驊鏞」",
                            "size": "xs",
                            "color": "#0284C7",
                            "wrap": True,
                            "margin": "xs"
                        }
                    ]
                },
                {"type": "separator"},
                {
                    "type": "text",
                    "text": "或是點選下方，由單一成員全額承擔：",
                    "size": "xs",
                    "color": "#64748B"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": member_buttons[:8]
                }
            ]
        }
    }


def create_member_picker_flex(
    draft_id: int,
    item_name: str,
    amount: float,
    payer_name: str,
    payer_id: int,
    members: List[Dict[str, Any]],
    selected_ids: List[int],
    target_count: int = 0,
    currency: str = "TWD",
    original_amount: float = None,
    rate: float = 1.0
) -> Dict[str, Any]:
    """挑選均分夥伴卡片（支援指定人數與自由勾選）"""
    from app.currency import format_amount
    orig_amt = original_amount if (original_amount and original_amount > 0) else amount
    amount_str = format_amount(orig_amt, currency)
    selected_count = len(selected_ids)
    selected_names = [m["name"] for m in members if m["id"] in selected_ids]
    names_str = "、".join(selected_names) if selected_names else "尚未選取"

    if target_count > 0:
        title = f"🎯 選擇均分夥伴（{target_count}人均分）"
        per_person = orig_amt / target_count
        per_str = format_amount(per_person, currency)
        if selected_count == target_count:
            status_bg = "#DCFCE7"
            status_title = f"🎉 已選好 {target_count} 位夥伴！"
            status_color = "#15803D"
            status_desc = f"名單：{names_str}（每人 {per_str}）"
            status_desc_color = "#166534"
        elif selected_count < target_count:
            status_bg = "#EFF6FF"
            status_title = f"👉 請點選 {target_count} 位夥伴（已選 {selected_count}/{target_count}）"
            status_color = "#1D4ED8"
            status_desc = f"目前已選：{names_str}，還差 {target_count - selected_count} 位"
            status_desc_color = "#1E40AF"
        else:
            status_bg = "#FEF2F2"
            status_title = f"⚠️ 已選 {selected_count} 位，超出目標 {target_count} 位！"
            status_color = "#B91C1C"
            status_desc = "請點擊綠色按鈕取消多選的夥伴"
            status_desc_color = "#991B1B"
    else:
        title = "🎯 自由勾選均分夥伴"
        if selected_count > 0:
            per_person = orig_amt / selected_count
            per_str = format_amount(per_person, currency)
            status_bg = "#DCFCE7"
            status_title = f"已選 {selected_count} 位夥伴（每人 {per_str}）"
            status_color = "#15803D"
            status_desc = f"名單：{names_str}"
            status_desc_color = "#166534"
        else:
            status_bg = "#EFF6FF"
            status_title = "👉 請勾選要一起分攤的夥伴"
            status_color = "#1D4ED8"
            status_desc = "點擊下方按鈕即可切換勾選狀態"
            status_desc_color = "#1E40AF"

    from app.config import get_base_url
    web_picker_url = f"{get_base_url()}/picker?draft_id={draft_id}&payer_id={payer_id}&target_count={target_count}"
    web_picker_label = f"📱 開啟勾選單（同頁選 {target_count} 人・不洗版）" if target_count > 0 else "📱 開啟勾選單（同頁多選・不洗版）"

    # 建立 2 欄按鈕網格
    member_button_rows = []
    current_row = []
    for m in members:
        is_sel = m["id"] in selected_ids
        name = m["name"]
        m_id = m["id"]
        if is_sel:
            new_sel = [x for x in selected_ids if x != m_id]
            sel_str = ",".join(map(str, new_sel))
            btn = {
                "type": "button",
                "style": "primary",
                "color": "#10B981",
                "height": "sm",
                "action": {
                    "type": "postback",
                    "label": f"✅ {name}",
                    "data": f"action=pick_split_members&draft_id={draft_id}&payer_id={payer_id}&target_count={target_count}&selected={sel_str}"
                }
            }
        else:
            new_sel = selected_ids + [m_id]
            sel_str = ",".join(map(str, new_sel))
            btn = {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "postback",
                    "label": f"⬜ {name}",
                    "data": f"action=pick_split_members&draft_id={draft_id}&payer_id={payer_id}&target_count={target_count}&selected={sel_str}"
                }
            }
        current_row.append(btn)
        if len(current_row) == 2:
            member_button_rows.append({
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": current_row
            })
            current_row = []

    if current_row:
        current_row.append({"type": "filler"})
        member_button_rows.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": current_row
        })

    footer_contents = []
    can_confirm = (target_count > 0 and selected_count == target_count) or (target_count == 0 and selected_count > 0)
    sel_final_str = ",".join(map(str, selected_ids))

    if can_confirm:
        footer_contents.append({
            "type": "button",
            "style": "primary",
            "color": "#16A34A",
            "height": "sm",
            "action": {
                "type": "postback",
                "label": f"🎉 確認送出（{selected_count}人均分）",
                "data": f"action=confirm_picked_split&draft_id={draft_id}&payer_id={payer_id}&selected={sel_final_str}"
            }
        })
    else:
        hint_text = f"⏳ 還差 {target_count - selected_count} 位夥伴" if (target_count > 0 and selected_count < target_count) else "👉 請勾選夥伴"
        footer_contents.append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "postback",
                "label": hint_text,
                "data": f"action=pick_split_members&draft_id={draft_id}&payer_id={payer_id}&target_count={target_count}&selected={sel_final_str}"
            }
        })

    footer_contents.append({
        "type": "button",
        "style": "link",
        "height": "sm",
        "color": "#64748B",
        "action": {
            "type": "postback",
            "label": "⬅️ 返回重新選擇人數",
            "data": f"action=select_payer&draft_id={draft_id}&payer_id={payer_id}"
        }
    })

    sub_header = f"{item_name}（{amount_str}）• {payer_name} 先代墊"
    if currency != "TWD":
        sub_header += f" (≈ NT$ {int(round(amount)):,})"

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0284C7",
            "paddingAll": "15px",
            "contents": [
                {"type": "text", "text": title, "weight": "bold", "color": "#FFFFFF", "size": "md"},
                {"type": "text", "text": sub_header, "color": "#E0F2FE", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "height": "sm",
                    "action": {
                        "type": "uri",
                        "label": web_picker_label,
                        "uri": web_picker_url
                    }
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": status_bg,
                    "paddingAll": "10px",
                    "cornerRadius": "8px",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": status_title, "weight": "bold", "size": "sm", "color": status_color},
                        {"type": "text", "text": status_desc, "size": "xs", "color": status_desc_color, "wrap": True, "margin": "xs"}
                    ]
                },
                {
                    "type": "text",
                    "text": "💬 或直接在群組傳送名單：「分攤 佳欣 江小 南廷 園子 玫璇」",
                    "size": "xxs",
                    "color": "#64748B",
                    "align": "center",
                    "wrap": True,
                    "margin": "xs"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "margin": "sm",
                    "contents": member_button_rows
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": footer_contents
        }
    }


def create_receipt_flex(
    expense_id: int,
    item_name: str,
    amount: float,
    payer_name: str,
    split_desc: str,
    date_str: str,
    currency: str = "TWD",
    original_amount: float = None,
    rate: float = 1.0
) -> Dict[str, Any]:
    """記帳完成收據卡片（支援多幣別）"""
    from app.currency import format_amount
    orig_amt = original_amount if original_amount else amount
    amount_str = format_amount(orig_amt, currency)

    amount_box_items = [
        {
            "type": "text",
            "text": item_name,
            "size": "md",
            "color": "#64748B"
        },
        {
            "type": "text",
            "text": amount_str,
            "weight": "bold",
            "size": "xxl",
            "color": "#0F172A",
            "margin": "xs"
        }
    ]

    if currency != "TWD":
        amount_box_items.append({
            "type": "text",
            "text": f"≈ NT$ {int(round(amount)):,} (匯率 {rate})",
            "size": "xs",
            "color": "#0284C7",
            "margin": "xs"
        })

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#10B981",
            "contents": [
                {
                    "type": "text",
                    "text": "✅ 記帳成功！",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "md"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "alignItems": "center",
                    "contents": amount_box_items
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "💳 付款人", "color": "#64748B", "size": "sm", "flex": 3},
                                {"type": "text", "text": payer_name, "weight": "bold", "color": "#0F172A", "size": "sm", "flex": 5}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "🤝 分攤方式", "color": "#64748B", "size": "sm", "flex": 3},
                                {"type": "text", "text": split_desc, "color": "#0F172A", "size": "sm", "flex": 5, "wrap": True}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "🕒 時間", "color": "#64748B", "size": "sm", "flex": 3},
                                {"type": "text", "text": date_str, "color": "#94A3B8", "size": "xs", "flex": 5}
                            ]
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "color": "#F0F9FF",
                    "action": {
                        "type": "postback",
                        "label": "✏️ 修改",
                        "data": f"action=edit_expense_menu&expense_id={expense_id}",
                        "displayText": f"修改 {item_name}"
                    }
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📊 結算",
                        "data": "action=view_settlement",
                        "displayText": "查看結算"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "color": "#FEF2F2",
                    "action": {
                        "type": "postback",
                        "label": "❌ 撤銷",
                        "data": f"action=delete_expense&expense_id={expense_id}",
                        "displayText": f"撤銷 {item_name}"
                    }
                }
            ]
        }
    }


def create_repayment_flex(
    expense_id: int,
    from_name: str,
    to_name: str,
    amount: float,
    currency: str = "TWD",
    base_amount: float = None,
    rate: float = 1.0,
    date_str: str = ""
) -> Dict[str, Any]:
    """小額還款登記成功收據卡片"""
    from app.currency import format_amount
    amount_str = format_amount(amount, currency)

    amount_box_items = [
        {
            "type": "text",
            "text": "💸 旅伴小額還款",
            "size": "sm",
            "color": "#64748B"
        },
        {
            "type": "text",
            "text": amount_str,
            "weight": "bold",
            "size": "xxl",
            "color": "#059669",
            "margin": "xs"
        }
    ]

    if currency != "TWD":
        base_twd = base_amount if base_amount is not None else (amount * rate)
        amount_box_items.append({
            "type": "text",
            "text": f"≈ NT$ {int(round(base_twd)):,} (匯率 {rate})",
            "size": "xs",
            "color": "#0284C7",
            "margin": "xs"
        })

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#059669",
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "text",
                    "text": "💸 還款登記成功！",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "md"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "alignItems": "center",
                    "contents": amount_box_items
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "alignItems": "center",
                            "contents": [
                                {"type": "text", "text": f"💸 {from_name}", "weight": "bold", "color": "#DC2626", "size": "sm", "flex": 4},
                                {"type": "text", "text": "➡️ 還給 ➡️", "size": "xs", "color": "#94A3B8", "align": "center", "flex": 3},
                                {"type": "text", "text": f"💰 {to_name}", "weight": "bold", "color": "#16A34A", "size": "sm", "align": "end", "flex": 4}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "backgroundColor": "#ECFDF5",
                            "paddingAll": "10px",
                            "cornerRadius": "6px",
                            "margin": "sm",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "✅ 帳務已更新：此筆還款已自雙方債務餘額中自動抵扣！",
                                    "size": "xs",
                                    "color": "#065F46",
                                    "wrap": True
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "margin": "xs",
                            "contents": [
                                {"type": "text", "text": "🕒 登記時間", "color": "#64748B", "size": "xs", "flex": 4},
                                {"type": "text", "text": date_str, "color": "#94A3B8", "size": "xs", "align": "end", "flex": 6}
                            ]
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📊 查看最新結算",
                        "data": "action=view_settlement",
                        "displayText": "查看結算"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "❌ 撤銷此筆",
                        "data": f"action=delete_expense&expense_id={expense_id}",
                        "displayText": "撤銷還款"
                    }
                }
            ]
        }
    }


def create_repayment_guide_flex() -> Dict[str, Any]:
    """小額還款功能指南 Flex 卡片"""
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#059669",
            "paddingAll": "15px",
            "contents": [
                {
                    "type": "text",
                    "text": "💸 旅伴小額還款功能指南",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "md"
                },
                {
                    "type": "text",
                    "text": "旅途隨時還錢、轉帳，帳務即時自動沖銷！",
                    "color": "#D1FAE5",
                    "size": "xs",
                    "margin": "xs"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🎯 方式一：在「查看結算」一鍵登記（最推薦）", "weight": "bold", "size": "sm", "color": "#059669"},
                        {"type": "text", "text": "點選「查看結算」，系統會列出目前各幣別的最佳還款建議。每一筆建議下方都有綠色按鈕：", "size": "xs", "color": "#64748B", "wrap": True, "margin": "xs"},
                        {"type": "text", "text": "👉 點擊【✅ 登記 江小 已還 佳欣】即可一鍵完成！", "size": "xs", "color": "#0F172A", "weight": "bold", "margin": "xs"}
                    ]
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "💬 方式二：在群組直接傳送文字訊息", "weight": "bold", "size": "sm", "color": "#0284C7"},
                        {"type": "text", "text": "直接在群組輸入以下任一種格式，機器人立刻登記：", "size": "xs", "color": "#64748B", "margin": "xs"},
                        {"type": "text", "text": "• 「江小 還 佳欣 40」（以此旅程當下幣別）", "size": "xs", "color": "#0F172A", "margin": "xs"},
                        {"type": "text", "text": "• 「江小 還 佳欣 40 THB」（指定泰銖）", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "• 「江小 轉帳給 佳欣 500 TWD」", "size": "xs", "color": "#0F172A"},
                        {"type": "text", "text": "• 「小額還款 江小 佳欣 50」", "size": "xs", "color": "#0F172A"}
                    ]
                },
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#F8FAFC",
                    "paddingAll": "10px",
                    "cornerRadius": "6px",
                    "contents": [
                        {"type": "text", "text": "💡 說明與防呆機制：", "weight": "bold", "size": "xs", "color": "#475569"},
                        {"type": "text", "text": "1. 還款只會沖銷還款人與收款人的債務，不影響其他成員！", "size": "xxs", "color": "#64748B", "wrap": True, "margin": "xs"},
                        {"type": "text", "text": "2. 若不小心按錯，收據卡片或「查看明細」隨時可按【❌ 撤銷】復原！", "size": "xxs", "color": "#64748B", "wrap": True, "margin": "xs"}
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#059669",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📊 查看結算並登記還款",
                        "data": "action=view_settlement",
                        "displayText": "查看結算"
                    }
                }
            ]
        }
    }


def create_settlement_flex(settlement_data: Dict[str, Any]) -> Dict[str, Any]:
    """結算報表與還款指南 Flex 卡片（支援多幣別分開折算與統一結算）"""
    trip_name = settlement_data.get("trip_name", "旅程記帳")
    total_spent = settlement_data.get("total_spent", 0)
    expense_count = settlement_data.get("expense_count", 0)
    base_curr = settlement_data.get("base_currency", "TWD")
    currency_settlements = settlement_data.get("currency_settlements", [])
    is_multi_currency = settlement_data.get("is_multi_currency", False)

    body_contents = []

    if expense_count == 0:
        body_contents.append({
            "type": "text",
            "text": "📋 目前尚無任何記帳支出！\n請直接輸入「項目 金額」（如「泰奶 200」）開始記帳。",
            "size": "sm",
            "color": "#64748B",
            "align": "center",
            "wrap": True
        })
    else:
        for idx, cs in enumerate(currency_settlements):
            curr = cs.get("currency", "TWD")
            c_total = cs.get("formatted_total", "")
            c_members = cs.get("members", [])
            c_transfers = cs.get("transfers", [])

            if is_multi_currency:
                body_contents.append({
                    "type": "box",
                    "layout": "horizontal",
                    "backgroundColor": "#F1F5F9",
                    "paddingAll": "8px",
                    "cornerRadius": "6px",
                    "contents": [
                        {"type": "text", "text": f"💱 【{curr}】結算", "size": "sm", "weight": "bold", "color": "#0369A1", "flex": 5},
                        {"type": "text", "text": f"支出 {c_total}", "size": "xs", "weight": "bold", "color": "#0F172A", "align": "end", "flex": 4}
                    ]
                })

            if c_members:
                body_contents.append({
                    "type": "text",
                    "text": f"👤 成員收支狀況（{curr}）：",
                    "size": "xs",
                    "color": "#64748B",
                    "margin": "sm",
                    "weight": "bold"
                })
                for m in c_members:
                    net_val = m["net"]
                    net_str = m.get("formatted_net", str(net_val))
                    net_color = "#16A34A" if net_val > 0 else ("#DC2626" if net_val < 0 else "#64748B")
                    paid_str = m.get("formatted_paid", "")
                    repay_sent = m.get("repay_sent", 0)
                    repay_recv = m.get("repay_recv", 0)
                    if m.get("paid", 0) > 0 and repay_recv > 0:
                        detail_label = f"墊 {paid_str}(收{m.get('formatted_repay_recv')})"
                    elif m.get("paid", 0) == 0 and repay_sent > 0:
                        detail_label = f"已還 {m.get('formatted_repay_sent')}"
                    else:
                        detail_label = f"墊付 {paid_str}"

                    if net_val == 0:
                        status_str = "已結清 ✅"
                        status_color = "#10B981"
                    else:
                        status_str = net_str
                        status_color = net_color

                    body_contents.append({
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": m["name"], "size": "sm", "weight": "bold", "color": "#0F172A", "flex": 3},
                            {"type": "text", "text": detail_label, "size": "xs", "color": "#64748B", "flex": 4},
                            {"type": "text", "text": status_str, "size": "sm", "weight": "bold", "color": status_color, "align": "end", "flex": 3}
                        ]
                    })
            else:
                body_contents.append({
                    "type": "text",
                    "text": f"（尚無 {curr} 支出紀錄）",
                    "size": "xs",
                    "color": "#94A3B8"
                })

            body_contents.append({
                "type": "text",
                "text": f"💡 最佳化還款指南（{curr} 最少轉帳）：",
                "size": "xs",
                "color": "#64748B",
                "margin": "md",
                "weight": "bold"
            })

            if c_transfers:
                for t in c_transfers:
                    body_contents.append({
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "sm",
                        "alignItems": "center",
                        "contents": [
                            {"type": "text", "text": f"💸 {t['from']}", "size": "sm", "weight": "bold", "color": "#DC2626", "flex": 3},
                            {"type": "text", "text": "➡️ 給 ➡️", "size": "xs", "color": "#94A3B8", "align": "center", "flex": 2},
                            {"type": "text", "text": t["to"], "size": "sm", "weight": "bold", "color": "#16A34A", "flex": 3},
                            {"type": "text", "text": t.get("formatted_amount", f"${t['amount']}"), "size": "sm", "weight": "bold", "color": "#0284C7", "align": "end", "flex": 4}
                        ]
                    })
                    # 1-Click 一鍵登記已還款按鈕
                    from_short = t['from'][:4]
                    to_short = t['to'][:4]
                    btn_label = f"✅ 登記 {from_short} 已還 {to_short}"
                    body_contents.append({
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xs",
                        "contents": [
                            {
                                "type": "button",
                                "style": "secondary",
                                "height": "sm",
                                "color": "#F0FDF4",
                                "action": {
                                    "type": "postback",
                                    "label": btn_label,
                                    "data": f"action=quick_repay&from={t['from']}&to={t['to']}&amount={t['amount']}&currency={curr}",
                                    "displayText": f"{t['from']} 還 {t['to']} {t['amount']} {curr}"
                                }
                            }
                        ]
                    })
                body_contents.append({
                    "type": "text",
                    "text": f"💡 旅途小額還款：亦可直接輸入「{c_transfers[0]['from']} 還 {c_transfers[0]['to']} [金額]」登記！",
                    "size": "xxs",
                    "color": "#64748B",
                    "margin": "xs",
                    "wrap": True
                })
            else:
                body_contents.append({
                    "type": "text",
                    "text": f"🎉 {curr} 帳務已結清！無須還款",
                    "size": "xs",
                    "color": "#10B981",
                    "margin": "xs"
                })

            if is_multi_currency and idx < len(currency_settlements) - 1:
                body_contents.append({"type": "separator", "margin": "lg"})

        if is_multi_currency:
            body_contents.append({"type": "separator", "margin": "md"})
            body_contents.append({
                "type": "text",
                "text": f"ℹ️ 各幣別分開折算，請依上述各幣別指南轉帳或付現（全部折合約 NT$ {total_spent:,}）",
                "size": "xxs",
                "color": "#94A3B8",
                "wrap": True,
                "margin": "sm"
            })

    header_sub = f"共 {expense_count} 筆 • 各幣別獨立折算" if is_multi_currency else f"折合支出：{base_curr} {total_spent:,}    共 {expense_count} 筆"

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F172A",
            "contents": [
                {
                    "type": "text",
                    "text": f"📊 {trip_name} 結算報表",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "md"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "sm",
                    "contents": [
                        {"type": "text", "text": header_sub, "size": "xs", "color": "#38BDF8"}
                    ]
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": body_contents
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📋 查看明細",
                        "data": "action=view_expenses",
                        "displayText": "查看明細"
                    }
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "➕ 繼續記帳",
                        "text": "記帳"
                    }
                }
            ]
        }
    }


def create_expense_list_flex(expenses: List[Dict[str, Any]], base_currency: str = "TWD") -> Dict[str, Any]:
    """查看最近支出明細清單"""
    if not expenses:
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📋 目前尚無任何記帳支出！", "size": "md", "color": "#64748B", "align": "center"}
                ]
            }
        }

    from app.currency import format_amount

    item_rows = []
    for exp in expenses[:10]:  # 最多顯示 10 筆
        curr = exp.get("currency") or "TWD"
        orig_amt = exp.get("original_amount") if exp.get("original_amount") is not None else exp.get("amount", 0)
        base_twd_amt = exp.get("amount", 0)

        is_repay = exp.get("split_type") == "REPAYMENT" or "小額還款" in exp.get("item_name", "")
        item_title = exp["item_name"]
        item_sub = "💸 還款抵扣 • 債務已沖銷" if is_repay else f"{exp['payer_name']} 墊付 • {exp['split_desc']}"
        amt_color = "#059669" if is_repay else "#16A34A"

        right_contents = [
            {
                "type": "text",
                "text": format_amount(orig_amt, curr),
                "weight": "bold",
                "size": "sm",
                "color": amt_color
            }
        ]
        if curr != "TWD":
            right_contents.append({
                "type": "text",
                "text": f"≈ NT$ {int(round(base_twd_amt)):,}",
                "size": "xxs",
                "color": "#64748B"
            })

        action_buttons = []
        if not is_repay:
            action_buttons.append({
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "color": "#F0F9FF",
                "action": {
                    "type": "postback",
                    "label": "✏️ 修改",
                    "data": f"action=edit_expense_menu&expense_id={exp['id']}",
                    "displayText": f"修改 {item_title}"
                }
            })
        action_buttons.append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "color": "#FEF2F2",
            "action": {
                "type": "postback",
                "label": "🗑️ 刪除",
                "data": f"action=delete_expense&expense_id={exp['id']}",
                "displayText": f"刪除 {item_title}"
            }
        })

        item_rows.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 7,
                            "contents": [
                                {"type": "text", "text": item_title, "weight": "bold", "size": "sm", "color": "#0F172A", "wrap": True},
                                {"type": "text", "text": item_sub, "size": "xs", "color": "#64748B", "wrap": True}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 4,
                            "alignItems": "flex-end",
                            "contents": right_contents
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "justifyContent": "flex-end",
                    "spacing": "sm",
                    "contents": action_buttons
                }
            ]
        })
        item_rows.append({"type": "separator", "margin": "xs"})

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0284C7",
            "contents": [
                {"type": "text", "text": "📋 最近支出紀錄", "weight": "bold", "color": "#FFFFFF", "size": "md"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": item_rows
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📊 查看總結算",
                        "data": "action=view_settlement",
                        "displayText": "查看結算"
                    }
                }
            ]
        }
    }


def create_edit_expense_flex(expense_data: Dict[str, Any], base_currency: str = "TWD") -> Dict[str, Any]:
    """修改單筆支出 Flex 卡片選單"""
    from app.currency import format_amount

    exp_id = expense_data["id"]
    item_name = expense_data["item_name"]
    curr = expense_data.get("currency") or "TWD"
    orig_amt = expense_data.get("original_amount") if expense_data.get("original_amount") is not None else expense_data.get("amount", 0)
    base_twd_amt = expense_data.get("amount", 0)
    payer_name = expense_data.get("payer_name", "未知")
    split_desc = expense_data.get("split_desc", "均分")

    amount_display = format_amount(orig_amt, curr)
    if curr != "TWD":
        amount_display += f" (≈ NT$ {int(round(base_twd_amt)):,})"

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0284C7",
            "paddingAll": "15px",
            "contents": [
                {"type": "text", "text": "✏️ 編輯支出內容", "weight": "bold", "color": "#FFFFFF", "size": "md"},
                {"type": "text", "text": f"正在修改：{item_name}", "color": "#E0F2FE", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#F8FAFC",
                    "cornerRadius": "md",
                    "paddingAll": "10px",
                    "spacing": "xs",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "項目", "color": "#64748B", "size": "xs", "flex": 2},
                                {"type": "text", "text": item_name, "weight": "bold", "color": "#0F172A", "size": "xs", "flex": 6}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "金額", "color": "#64748B", "size": "xs", "flex": 2},
                                {"type": "text", "text": amount_display, "weight": "bold", "color": "#16A34A", "size": "xs", "flex": 6}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "付款人", "color": "#64748B", "size": "xs", "flex": 2},
                                {"type": "text", "text": payer_name, "color": "#0F172A", "size": "xs", "flex": 6}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "分攤", "color": "#64748B", "size": "xs", "flex": 2},
                                {"type": "text", "text": split_desc, "color": "#0F172A", "size": "xs", "flex": 6}
                            ]
                        }
                    ]
                },
                {"type": "separator"},
                {
                    "type": "text",
                    "text": "請點選欲修改的欄位：",
                    "size": "xs",
                    "color": "#475569",
                    "weight": "bold"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#0284C7",
                            "height": "sm",
                            "action": {
                                "type": "postback",
                                "label": "💵 修改金額",
                                "data": f"action=edit_prompt_amount&expense_id={exp_id}",
                                "displayText": f"修改 {item_name} 金額"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "color": "#F0F9FF",
                            "height": "sm",
                            "action": {
                                "type": "postback",
                                "label": "👤 更換付款人",
                                "data": f"action=edit_show_payer&expense_id={exp_id}",
                                "displayText": f"更換 {item_name} 付款人"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "color": "#F0F9FF",
                            "height": "sm",
                            "action": {
                                "type": "postback",
                                "label": "🤝 重新設定分攤夥伴",
                                "data": f"action=edit_show_splits&expense_id={exp_id}",
                                "displayText": f"重新設定 {item_name} 分攤"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "color": "#F0F9FF",
                            "height": "sm",
                            "action": {
                                "type": "postback",
                                "label": "📝 修改項目名稱",
                                "data": f"action=edit_prompt_name&expense_id={exp_id}",
                                "displayText": f"修改 {item_name} 名稱"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "color": "#FEF2F2",
                            "height": "sm",
                            "action": {
                                "type": "postback",
                                "label": "🗑️ 刪除此筆支出",
                                "data": f"action=delete_expense&expense_id={exp_id}",
                                "displayText": f"刪除 {item_name}"
                            }
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📋 返回支出明細",
                        "data": "action=view_expenses",
                        "displayText": "查看明細"
                    }
                }
            ]
        }
    }


def create_edit_payer_selection_flex(
    expense_id: int,
    item_name: str,
    members: List[Dict[str, Any]],
    current_payer_id: int
) -> Dict[str, Any]:
    """更換付款人選單 Flex"""
    buttons = []
    curr_row = []
    for m in members:
        is_current = (m["id"] == current_payer_id)
        if is_current:
            btn = {
                "type": "button",
                "style": "primary",
                "color": "#10B981",
                "height": "sm",
                "action": {
                    "type": "postback",
                    "label": f"✅ {m['name']} (目前)",
                    "data": f"action=edit_expense_menu&expense_id={expense_id}"
                }
            }
        else:
            btn = {
                "type": "button",
                "style": "secondary",
                "color": "#F1F5F9",
                "height": "sm",
                "action": {
                    "type": "postback",
                    "label": m["name"],
                    "data": f"action=do_edit_payer&expense_id={expense_id}&payer_id={m['id']}",
                    "displayText": f"更改付款人為 {m['name']}"
                }
            }
        curr_row.append(btn)
        if len(curr_row) == 2:
            buttons.append({
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": curr_row
            })
            curr_row = []
    if curr_row:
        buttons.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": curr_row
        })

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0284C7",
            "paddingAll": "15px",
            "contents": [
                {"type": "text", "text": "👤 更換付款人", "weight": "bold", "color": "#FFFFFF", "size": "md"},
                {"type": "text", "text": f"【{item_name}】由誰代墊？", "color": "#E0F2FE", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": "請點選新的代墊夥伴：", "size": "xs", "color": "#64748B"},
                {"type": "separator", "margin": "sm"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "margin": "sm",
                    "contents": buttons
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🔙 返回編輯選單",
                        "data": f"action=edit_expense_menu&expense_id={expense_id}"
                    }
                }
            ]
        }
    }


def create_edit_split_selection_flex(
    expense_id: int,
    item_name: str,
    amount_str: str,
    members: List[Dict[str, Any]],
    current_split_member_ids: List[int],
    base_url: str = ""
) -> Dict[str, Any]:
    """重新設定分攤方式選單 Flex"""
    member_count = len(members)
    buttons = []

    # 1. 全員均分
    buttons.append({
        "type": "button",
        "style": "primary",
        "color": "#0284C7",
        "height": "sm",
        "action": {
            "type": "postback",
            "label": f"👥 全體均分 ({member_count} 人平分)",
            "data": f"action=do_edit_split_all&expense_id={expense_id}",
            "displayText": f"全體均分 {item_name}"
        }
    })

    # 2. 同頁挑選（若有 base_url）
    if not base_url:
        from app.config import get_base_url
        base_url = get_base_url()

    if base_url:
        buttons.append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "uri",
                "label": "📱 同頁勾選分攤夥伴（零洗版）",
                "uri": f"{base_url}/picker?expense_id={expense_id}&target_count=0"
            }
        })

    # 3. 個別成員單獨全額承擔
    single_buttons = []
    curr_row = []
    for m in members:
        curr_row.append({
            "type": "button",
            "style": "secondary",
            "color": "#F8FAFC",
            "height": "sm",
            "action": {
                "type": "postback",
                "label": f"由 {m['name']} 承擔",
                "data": f"action=do_edit_split_single&expense_id={expense_id}&member_id={m['id']}",
                "displayText": f"由 {m['name']} 全額承擔 {item_name}"
            }
        })
        if len(curr_row) == 2:
            single_buttons.append({
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": curr_row
            })
            curr_row = []
    if curr_row:
        single_buttons.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": curr_row
        })

    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0284C7",
            "paddingAll": "15px",
            "contents": [
                {"type": "text", "text": "🤝 重新設定分攤方式", "weight": "bold", "color": "#FFFFFF", "size": "md"},
                {"type": "text", "text": f"【{item_name}】{amount_str}", "color": "#E0F2FE", "size": "xs", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": "請選擇分攤模式：", "size": "xs", "color": "#64748B"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": buttons
                },
                {"type": "separator", "margin": "md"},
                {"type": "text", "text": "或由特定夥伴全額承擔：", "size": "xs", "color": "#64748B", "margin": "sm"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": single_buttons
                },
                {"type": "separator", "margin": "md"},
                {
                    "type": "text",
                    "text": "💡 亦可直接輸入：「改分攤 小明 小美」或「改分攤 全員」",
                    "size": "xxs",
                    "color": "#0284C7",
                    "wrap": True,
                    "margin": "xs"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🔙 返回編輯選單",
                        "data": f"action=edit_expense_menu&expense_id={expense_id}"
                    }
                }
            ]
        }
    }
