# 🧳 旅行夥伴分帳 LINE 機器人 (LINE Travel Split Bot)

專為旅行團體設計的 LINE 記帳與分帳機器人。支援**純按鈕引導式互動**，讓大家在旅途中點選即可完成「誰付錢」、「幾人均分」，並內建**債務最小化最佳化算法**，一鍵計算出最少轉帳次數的還款指南！

---

## ✨ 核心特色

1. **純按鈕引導記帳**：
   - 輸入「晚餐 1200」後，機器人自動彈出互動卡片。
   - **步驟一**：點選按鈕選定「誰付款」（小明、小美、阿豪...）。
   - **步驟二**：點選按鈕選定「幾人均分」（全體均分、2人分、3人分...）。
   - 自動生成精緻明細收據卡片（Flex Receipt）。
2. **債務最小化結算算法 (Debt Minimization Algorithm)**：
   - 拒絕複雜的互相轉帳！系統自動根據每人墊付與應分擔金額，利用貪婪算法算出最精簡的還款路徑（例如只需 2 筆轉帳即可全部結清）。
3. **雲端與本機雙支援**：
   - 支援 **Supabase / PostgreSQL** 雲端資料庫，旅伴資料安全保存。
   - 本機未設定 `DATABASE_URL` 時自動 fallback 至 SQLite，開箱即測。
4. **完整帳務管理**：
   - 隨時查看總花費、成員墊付收支、明細清單與一鍵撤銷誤記的項目。

---

## 🛠️ 互動流程圖

```mermaid
flowchart TD
    A["使用者傳送「晚餐 1200」"] --> B["建立暫存紀錄 (DraftExpense)"]
    B --> C["彈出 Flex 卡片：💳 步驟 1 選定誰付錢？"]
    C --> D{"點選付款人按鈕<br/>(例如：小明)"}
    D --> E["彈出 Flex 卡片：🤝 步驟 2 有幾人均分？"]
    E --> F{"點選均分方式<br/>(例如：全體 3 人均分)"}
    F --> G["寫入資料庫 (Expense & ExpenseSplit)"]
    G --> H["發送 ✅ 記帳成功收據卡片<br/>(附帶查看結算與撤銷按鈕)"]
    
    I["點選「📊 查看結算」"] --> J["計算每人淨餘額 (代墊 - 應付)"]
    J --> K["執行債務最小化演算法"]
    K --> L["發送 📊 最佳化還款指南卡片"]
```

---

## 🚀 快速開始

### 1. 複製專案與安裝依賴

```bash
cd line-travel-split-bot
pip install -r requirements.txt
```

### 2. 設定環境變數

複製 `.env.example` 並更名為 `.env`：

```bash
cp .env.example .env
```

編輯 `.env` 填入您的設定：
```env
# LINE Messaging API 憑證 (由 LINE Developers 取得)
LINE_CHANNEL_ACCESS_TOKEN=你的Channel_Access_Token
LINE_CHANNEL_SECRET=你的Channel_Secret

# 資料庫連線字串
# 本機測試可直接留空使用 SQLite，或填入 Supabase / PostgreSQL 連線字串
DATABASE_URL=sqlite:///./travel_split.db
PORT=8000
```

### 3. 執行測試確認一切正常

```bash
python -m unittest discover tests
```

### 4. 啟動伺服器

```bash
uvicorn app.main:app --reload --port 8000
```
瀏覽器打開 `http://localhost:8000/docs` 即可查看 Swagger API 文件。

---

## 📲 LINE Developers 設定與 Webhook 串接

### 步驟 1：建立 LINE Messaging API Channel
1. 前往 [LINE Developers Console](https://developers.line.biz/) 並登入。
2. 建立一個 Provider（或選擇現有的），並在其中建立一個 **Messaging API** Channel。
3. 在 **Basic settings** 頁面找到 **Channel secret**，複製並填入 `.env` 的 `LINE_CHANNEL_SECRET`。
4. 在 **Messaging API** 頁面找到 **Channel access token**（點擊 Issue 產生），複製並填入 `.env` 的 `LINE_CHANNEL_ACCESS_TOKEN`。

### 步驟 2：本機測試（使用 ngrok 開啟對外通道）
在終端機執行：
```bash
ngrok http 8000
```
你會獲得一組 HTTPS 網址，例如：`https://abc1234.ngrok-free.app`。

### 步驟 3：設定 Webhook URL
1. 回到 LINE Developers 的 **Messaging API** 設定分頁。
2. 在 **Webhook settings**：
   - **Webhook URL** 填入：`https://你的ngrok網址/callback`
   - 開啟 **Use webhook** 開關。
   - 點選 **Verify**，確認回傳 `Success`。
3. 在 **LINE Official Account features**：
   - 關閉 **Auto-reply messages**（自動回覆訊息），避免官方預設罐頭訊息干擾。
   - 允許機器人加入群組（**Allow bot to join group chats**）。

---

## 💬 LINE 群組常用操作指令

| 指令 | 說明 |
| :--- | :--- |
| `選單` / `功能` | 開啟主功能卡片（包含記帳、結算、明細、旅伴管理按鈕） |
| `新增成員 小明 小美 阿豪` | 快速設定或加入旅伴名單（以逗號或空格分隔） |
| `成員名單` | 查看目前這趟旅行的所有夥伴 |
| `晚餐 1200` | **發動記帳**：立即跳出步驟卡片選擇「誰付錢」與「幾人均分」 |
| `結算` / `算帳` | 查看總支出、各人墊付餘額與**最佳化還款指南** |
| `明細` | 查看最近的所有支出清單與刪除按鈕 |
| `清空紀錄` | 結清旅程並歸零所有帳務，開啟新旅程 |

---

## 🗄️ 雲端資料庫設定 (Supabase / PostgreSQL)

1. 在 [Supabase](https://supabase.com/) 建立免費專案。
2. 進入 **Project Settings** -> **Database**。
3. 找到 **Connection string** (URI)，格式如下：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
4. 將該字串貼入 `.env` 中的 `DATABASE_URL` 即可。系統啟動時會自動建立所有必要資料表（無需手動建表）。

---

## 🚢 雲端部署 (Render / Fly.io / Docker)

本專案已包含 `Dockerfile`，可一鍵部署至 Render、Fly.io、Railway 或 GCP Cloud Run：

```bash
docker build -t line-travel-split-bot .
docker run -p 8000:8000 --env-file .env line-travel-split-bot
```

在雲端平台設定環境變數：
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_CHANNEL_SECRET`
- `DATABASE_URL`
- `PORT` = `8000`
部署完成後將該平台提供的公開 HTTPS 網址 + `/callback` 設定到 LINE Developers 的 Webhook URL 即可！
