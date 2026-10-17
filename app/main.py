import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, Configuration
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    JoinEvent,
)

from app.config import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, PORT, HOST
from app.database import init_db, get_db, SessionLocal
from app.line_handlers import (
    handle_text_message,
    handle_postback,
    handle_join_event,
)
from app.settlement import calculate_group_settlement
from app.models import GroupTrip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LINE Bot 初始化
line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時自動建立資料庫表格
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully.")
    yield


app = FastAPI(
    title="LINE Travel Expense Split Bot",
    description="旅行夥伴記帳 LINE 機器人（按鈕引導、付款人選擇、均分計算、債務最小化結算）",
    version="1.0.0",
    lifespan=lifespan
)


@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {
        "status": "online",
        "service": "LINE Travel Split Bot",
        "docs": "/docs"
    }


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


from typing import List, Optional
from pydantic import BaseModel
from fastapi.responses import JSONResponse, HTMLResponse
from app.models import GroupTrip, Member, Expense, ExpenseSplit, DraftExpense
from app.config import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, PORT, HOST, set_base_url
from app.currency import format_amount


class ConfirmPickerRequest(BaseModel):
    draft_id: Optional[int] = None
    expense_id: Optional[int] = None
    payer_id: Optional[int] = None
    selected_ids: List[int]


@app.get("/api/settlement/{line_group_id}")
def api_get_settlement(line_group_id: str, db: Session = Depends(get_db)):
    """API: 取得指定群組的結算資訊"""
    group = db.query(GroupTrip).filter(GroupTrip.line_group_id == line_group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    data = calculate_group_settlement(db, group.id)
    return data


@app.get("/picker", response_class=HTMLResponse)
def get_member_picker_page(
    request: Request,
    draft_id: Optional[int] = None,
    expense_id: Optional[int] = None,
    payer_id: Optional[int] = None,
    target_count: int = 0,
    db: Session = Depends(get_db)
):
    """LINE 內嵌網頁：停留在同一個頁面勾選所有分攤夥伴，零訊息洗版"""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    proto = request.headers.get("x-forwarded-proto") or "https"
    if host:
        set_base_url(f"{proto}://{host}")

    if expense_id:
        expense = db.query(Expense).filter(Expense.id == expense_id, Expense.is_deleted == False).first()
        if not expense:
            return HTMLResponse("""
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="font-family: sans-serif; text-align: center; padding: 40px; color: #475569;">
                <h2>⚠️ 該筆支出不存在或已被刪除</h2>
                <p style="margin-top: 10px;">請關閉此視窗，返回 LINE 群組重新操作。</p>
            </body></html>
            """, status_code=200)

        group = db.query(GroupTrip).filter(GroupTrip.id == expense.group_id).first()
        members = db.query(Member).filter(Member.group_id == group.id).all() if group else []
        curr = expense.currency or "TWD"
        orig_amt = expense.original_amount if (expense.original_amount and expense.original_amount > 0) else expense.amount
        amount_str = format_amount(orig_amt, curr)
        payer = expense.payer
        payer_display = payer.display_name if payer else "未知"
        eff_draft_id = 0
        eff_expense_id = expense.id
        eff_payer_id = expense.payer_id or 0
    else:
        draft = db.query(DraftExpense).filter(DraftExpense.id == draft_id).first()
        payer = db.query(Member).filter(Member.id == payer_id).first()
        if not draft or not payer:
            return HTMLResponse("""
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="font-family: sans-serif; text-align: center; padding: 40px; color: #475569;">
                <h2>⚠️ 該筆記帳作業已完成或過期</h2>
                <p style="margin-top: 10px;">請關閉此視窗，返回 LINE 群組查看收據或重新記帳。</p>
            </body></html>
            """, status_code=200)

        group = db.query(GroupTrip).filter(GroupTrip.line_group_id == draft.line_group_id).first()
        members = db.query(Member).filter(Member.group_id == group.id).all() if group else []
        curr = draft.currency or "TWD"
        orig_amt = draft.original_amount if (draft.original_amount and draft.original_amount > 0) else draft.amount
        amount_str = format_amount(orig_amt, curr)
        payer_display = payer.display_name
        eff_draft_id = draft.id or 0
        eff_expense_id = 0
        eff_payer_id = payer.id

    member_cards_html = ""
    for m in members:
        member_cards_html += f"""
        <div class="member-btn" id="mem-{m.id}" onclick="toggleMember({m.id})">
            <span class="icon">⬜</span>
            <span class="name">{m.display_name}</span>
        </div>
        """

    target_title = f"👉 請勾選 {target_count} 位夥伴" if target_count > 0 else "👉 請自由勾選分攤夥伴"
    btn_init_text = f"請選滿 {target_count} 位夥伴" if target_count > 0 else "請至少勾選 1 位夥伴"

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>選擇均分夥伴</title>
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
        body {{ background-color: #F1F5F9; color: #0F172A; padding: 14px; }}
        .card {{ background: #FFFFFF; border-radius: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07); padding: 20px; max-width: 480px; margin: 0 auto; }}
        .header {{ text-align: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 14px; margin-bottom: 14px; }}
        .title {{ font-size: 1.25rem; font-weight: 800; color: #0284C7; }}
        .item-info {{ font-size: 1rem; font-weight: 700; color: #0F172A; margin: 6px 0 2px; }}
        .payer-info {{ font-size: 0.82rem; color: #64748B; }}
        .status-box {{
            background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 14px;
            padding: 12px; text-align: center; margin-bottom: 16px;
        }}
        .status-title {{ font-size: 0.95rem; font-weight: 700; color: #1D4ED8; }}
        .status-desc {{ font-size: 0.82rem; color: #1E40AF; margin-top: 4px; }}
        .grid {{
            display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px;
        }}
        .member-btn {{
            display: flex; align-items: center; justify-content: flex-start;
            padding: 14px 12px; border-radius: 12px; border: 2px solid #E2E8F0;
            background: #FFFFFF; font-size: 0.95rem; font-weight: 600; color: #334155;
            cursor: pointer; transition: all 0.15s ease; user-select: none;
        }}
        .member-btn .icon {{ font-size: 1.1rem; margin-right: 8px; }}
        .member-btn.selected {{
            border-color: #10B981; background: #ECFDF5; color: #065F46;
        }}
        .btn-submit {{
            width: 100%; padding: 16px; border: none; border-radius: 12px;
            background: #CBD5E1; color: #94A3B8; font-size: 1.05rem; font-weight: bold;
            cursor: not-allowed; transition: all 0.2s;
        }}
        .btn-submit.ready {{
            background: #16A34A; color: #FFFFFF; cursor: pointer; box-shadow: 0 4px 6px -1px rgba(22, 163, 74, 0.35);
        }}
        .overlay {{
            display: none; position: fixed; inset: 0; background: #FFFFFF;
            flex-direction: column; align-items: center; justify-content: center;
            text-align: center; padding: 24px; z-index: 999;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div class="title">🎯 挑選均分夥伴</div>
            <div class="item-info">📝 {draft.item_name}（{amount_str}）</div>
            <div class="payer-info">👤 由 {payer.display_name} 先代墊</div>
        </div>

        <div class="status-box" id="status-box">
            <div class="status-title" id="status-title">{target_title}</div>
            <div class="status-desc" id="status-desc">
                已選 <span id="count-num" style="font-weight:bold;">0</span> / {target_count or len(members)} 位
            </div>
        </div>

        <div class="grid">
            {member_cards_html}
        </div>

        <button class="btn-submit" id="btn-submit" disabled onclick="submitSelection()">
            {btn_init_text}
        </button>
    </div>

    <div class="overlay" id="overlay">
        <div style="font-size: 3.5rem; margin-bottom: 12px;">🎉</div>
        <h2 style="color: #15803D; margin-bottom: 8px;">記帳成功！</h2>
        <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 24px;">收據已自動送出至 LINE 群組</p>
        <button onclick="closeApp()" style="padding: 12px 32px; border-radius: 9999px; border: none; background: #0284C7; color: #fff; font-size: 1rem; font-weight: bold; cursor: pointer;">
            返回 LINE 聊天室
        </button>
    </div>

    <script>
        const draftId = {eff_draft_id};
        const expenseId = {eff_expense_id};
        const payerId = {eff_payer_id};
        const targetCount = {target_count};
        const totalAmount = {orig_amt};
        const currency = "{curr}";
        let selectedIds = [];

        function toggleMember(id) {{
            const el = document.getElementById('mem-' + id);
            const idx = selectedIds.indexOf(id);
            if (idx > -1) {{
                selectedIds.splice(idx, 1);
                el.classList.remove('selected');
                el.querySelector('.icon').innerText = '⬜';
            }} else {{
                selectedIds.push(id);
                el.classList.add('selected');
                el.querySelector('.icon').innerText = '✅';
            }}
            updateUI();
        }}

        function updateUI() {{
            const count = selectedIds.length;
            const statusBox = document.getElementById('status-box');
            const statusTitle = document.getElementById('status-title');
            const statusDesc = document.getElementById('status-desc');
            const btn = document.getElementById('btn-submit');

            if (targetCount > 0) {{
                const perAmt = Math.round(totalAmount / targetCount);
                if (count === targetCount) {{
                    statusBox.style.background = '#DCFCE7';
                    statusBox.style.borderColor = '#86EFAC';
                    statusTitle.style.color = '#15803D';
                    statusDesc.style.color = '#166534';
                    statusTitle.innerText = '🎉 已選滿 ' + targetCount + ' 位夥伴！';
                    statusDesc.innerText = '每人分攤約 ' + perAmt + ' ' + currency;
                    btn.disabled = false;
                    btn.classList.add('ready');
                    btn.innerText = '🎉 確認送出（' + targetCount + ' 人均分）';
                }} else if (count < targetCount) {{
                    statusBox.style.background = '#EFF6FF';
                    statusBox.style.borderColor = '#BFDBFE';
                    statusTitle.style.color = '#1D4ED8';
                    statusDesc.style.color = '#1E40AF';
                    statusTitle.innerText = '👉 還差 ' + (targetCount - count) + ' 位夥伴';
                    statusDesc.innerText = '已選 ' + count + ' / ' + targetCount + ' 位';
                    btn.disabled = true;
                    btn.classList.remove('ready');
                    btn.innerText = '還差 ' + (targetCount - count) + ' 位尚未選取';
                }} else {{
                    statusBox.style.background = '#FEF2F2';
                    statusBox.style.borderColor = '#FECACA';
                    statusTitle.style.color = '#B91C1C';
                    statusDesc.style.color = '#991B1B';
                    statusTitle.innerText = '⚠️ 已選 ' + count + ' 位，超出目標 ' + targetCount + ' 位！';
                    statusDesc.innerText = '請取消勾選多選的夥伴';
                    btn.disabled = true;
                    btn.classList.remove('ready');
                    btn.innerText = '請取消多選夥伴';
                }}
            }} else {{
                if (count > 0) {{
                    const perAmt = Math.round(totalAmount / count);
                    statusBox.style.background = '#DCFCE7';
                    statusBox.style.borderColor = '#86EFAC';
                    statusTitle.style.color = '#15803D';
                    statusDesc.style.color = '#166534';
                    statusTitle.innerText = '已選 ' + count + ' 位夥伴';
                    statusDesc.innerText = '每人分攤約 ' + perAmt + ' ' + currency;
                    btn.disabled = false;
                    btn.classList.add('ready');
                    btn.innerText = '🎉 確認送出（' + count + ' 人均分）';
                }} else {{
                    statusBox.style.background = '#EFF6FF';
                    statusBox.style.borderColor = '#BFDBFE';
                    statusTitle.style.color = '#1D4ED8';
                    statusDesc.style.color = '#1E40AF';
                    statusTitle.innerText = '👉 請自由勾選分攤夥伴';
                    statusDesc.innerText = '已選 0 位';
                    btn.disabled = true;
                    btn.classList.remove('ready');
                    btn.innerText = '請至少勾選 1 位夥伴';
                }}
            }}
        }}

        async function submitSelection() {{
            const btn = document.getElementById('btn-submit');
            btn.disabled = true;
            btn.innerText = '⏳ 處理中...';

            try {{
                const res = await fetch('/api/confirm_picker', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        draft_id: draftId,
                        expense_id: expenseId,
                        payer_id: payerId,
                        selected_ids: selectedIds
                    }})
                }});
                const data = await res.json();
                if (res.ok) {{
                    document.getElementById('overlay').style.display = 'flex';
                    setTimeout(() => {{
                        closeApp();
                    }}, 1500);
                }} else {{
                    alert('⚠️ 記帳失敗：' + (data.detail || '請稍後再試'));
                    btn.disabled = false;
                    btn.innerText = '重試送出';
                }}
            }} catch (err) {{
                alert('網路錯誤，請重試！');
                btn.disabled = false;
                btn.innerText = '重試送出';
            }}
        }}

        function closeApp() {{
            try {{
                if (window.liff) {{
                    liff.closeWindow();
                }}
            }} catch(e) {{}}
            window.close();
        }}
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/confirm_picker")
def api_confirm_picker(req: ConfirmPickerRequest, db: Session = Depends(get_db)):
    """API: 內嵌網頁勾選完成後送出分攤"""
    if req.expense_id:
        expense = db.query(Expense).filter(Expense.id == req.expense_id, Expense.is_deleted == False).first()
        if not expense:
            raise HTTPException(status_code=404, detail="該筆支出紀錄不存在或已被刪除")
        group = db.query(GroupTrip).filter(GroupTrip.id == expense.group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="找不到對應群組")
        if not req.selected_ids:
            raise HTTPException(status_code=400, detail="尚未選取任何均分夥伴")

        target_members = db.query(Member).filter(Member.id.in_(req.selected_ids)).all()
        if not target_members:
            raise HTTPException(status_code=400, detail="選取的夥伴不存在")

        split_count = len(target_members)
        curr = expense.currency or "TWD"
        orig_amt = expense.original_amount if (expense.original_amount and expense.original_amount > 0) else expense.amount
        per_person_orig = orig_amt / split_count
        per_person_base = round(expense.amount / split_count, 2)
        names_str = "、".join(m.display_name for m in target_members)
        is_all = (split_count == len(group.members))
        split_desc = f"全體 {split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）" if is_all else f"{names_str} 共 {split_count} 人均分（每人 {format_amount(per_person_orig, curr)}）"

        db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == expense.id).delete()
        expense.split_count = split_count
        expense.split_type = "EQUAL_ALL" if is_all else f"CUSTOM_{split_count}"
        group.last_active_expense_id = expense.id
        db.commit()

        for m in target_members:
            db.add(ExpenseSplit(expense_id=expense.id, member_id=m.id, amount_owed=per_person_base))
        db.commit()

        # 發送更新後的收據到 LINE 群組
        try:
            from datetime import datetime, timezone
            from app.flex_templates import create_receipt_flex
            from linebot.v3.messaging import ApiClient, MessagingApi, PushMessageRequest, FlexMessage, FlexContainer

            now_str = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
            payer = expense.payer
            payer_name = payer.display_name if payer else "未知"
            receipt_card = create_receipt_flex(
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

            with ApiClient(line_config) as api_client:
                messaging_api = MessagingApi(api_client)
                messaging_api.push_message(
                    PushMessageRequest(
                        to=group.line_group_id,
                        messages=[
                            FlexMessage(
                                alt_text=f"✏️ 分攤修改成功：{expense.item_name} {display_cost}",
                                contents=FlexContainer.from_dict(receipt_card)
                            )
                        ]
                    )
                )
        except Exception as e:
            logger.error(f"Failed to push edit confirmation: {e}")

        return {"status": "success", "message": "已成功更新分攤夥伴！"}

    draft = db.query(DraftExpense).filter(DraftExpense.id == req.draft_id).first()
    payer = db.query(Member).filter(Member.id == req.payer_id).first()
    if not draft or not payer:
        raise HTTPException(status_code=404, detail="該筆記帳作業已過期或不存在")

    if not req.selected_ids:
        raise HTTPException(status_code=400, detail="尚未選取任何均分夥伴")

    target_members = db.query(Member).filter(Member.id.in_(req.selected_ids)).all()
    if not target_members:
        raise HTTPException(status_code=400, detail="選取的夥伴不存在")

    group = db.query(GroupTrip).filter(GroupTrip.line_group_id == draft.line_group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="找不到對應群組")

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
    group.last_active_expense_id = expense.id
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
    db.commit()

    # 發送收據到 LINE 群組 (Push Message)
    try:
        from datetime import datetime, timezone
        from app.flex_templates import create_receipt_flex
        from linebot.v3.messaging import ApiClient, MessagingApi, PushMessageRequest, FlexMessage, FlexContainer

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

        with ApiClient(line_config) as api_client:
            messaging_api = MessagingApi(api_client)
            messaging_api.push_message(
                PushMessageRequest(
                    to=group.line_group_id,
                    messages=[
                        FlexMessage(
                            alt_text=f"✅ 記帳成功：{expense.item_name} {display_cost}",
                            contents=FlexContainer.from_dict(receipt_card)
                        )
                    ]
                )
            )
    except Exception as e:
        logger.exception(f"Push message receipt failed: {e}")

    return {"status": "ok", "expense_id": expense.id}


@app.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(None)):
    """LINE Webhook 回呼接口"""
    # 自動更新當前伺服器對外 Base URL
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    proto = request.headers.get("x-forwarded-proto") or "https"
    if host:
        set_base_url(f"{proto}://{host}")

    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature")

    body = await request.body()
    body_text = body.decode("utf-8")

    try:
        handler.handle(body_text, x_line_signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Please check LINE_CHANNEL_SECRET.")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.exception(f"Error handling event: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

    return "OK"


# -------------------------------------------------------------
# 註冊 LINE Webhook 事件路由
# -------------------------------------------------------------
@handler.add(MessageEvent, message=TextMessageContent)
def on_message(event):
    with SessionLocal() as db:
        with ApiClient(line_config) as api_client:
            handle_text_message(event, db, api_client)


@handler.add(PostbackEvent)
def on_postback(event):
    with SessionLocal() as db:
        with ApiClient(line_config) as api_client:
            handle_postback(event, db, api_client)


@handler.add(JoinEvent)
def on_join(event):
    with SessionLocal() as db:
        with ApiClient(line_config) as api_client:
            handle_join_event(event, db, api_client)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
