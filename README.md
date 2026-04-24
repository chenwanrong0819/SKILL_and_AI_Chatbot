# 作業：設計 Skill + 打造 AI 聊天機器人

> **繳交方式**：將你的 GitHub repo 網址貼到作業繳交區
> **作業性質**：個人作業

---

## 作業目標

使用 Antigravity Skill 引導 AI，完成一個具備前後端的 AI 聊天機器人。
重點不只是「讓程式跑起來」，而是透過設計 Skill，學會用結構化的方式與 AI 協作開發。

---

## 繳交項目

你的 GitHub repo 需要包含以下內容：

### 1. Skill 設計（`.agents/skills/`）

為以下五個開發階段＋提交方式各設計一個 SKILL.md：

| 資料夾名稱        | 對應指令          | 說明                                                                           |
| ----------------- | ----------------- | ------------------------------------------------------------------------------ |
| `prd/`          | `/prd`          | 產出 `docs/PRD.md`                                                           |
| `architecture/` | `/architecture` | 產出 `docs/ARCHITECTURE.md`                                                  |
| `models/`       | `/models`       | 產出 `docs/MODELS.md`                                                        |
| `implement/`    | `/implement`    | 產出程式碼（**需指定**：HTML 前端 + FastAPI + SQLite 後端）              |
| `test/`         | `/test`         | 產出手動測試清單                                                               |
| `commit/`       | `/commit`       | 自動 commit + push（**需指定**：使用者與 email 使用 Antigravity 預設值） |

### 2. 開發文件（`docs/`）

用你設計的 Skill 產出的文件，需包含：

- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/MODELS.md`

### 3. 程式碼

一個可執行的 AI 聊天機器人，需支援以下功能：

| 功能           | 說明                                       | 是否完成 |
| -------------- | ------------------------------------------ | -------- |
| 對話狀態管理   | 支援多聊天室（session），維持上下文        | O        |
| 訊息系統       | 訊息結構包含 role、content、timestamp      | O        |
| 對話歷史管理   | 可顯示並切換過去的對話紀錄                 | O        |
| 上傳圖片或文件 | 支援使用者上傳檔案作為對話內容             | O        |
| 回答控制       | 提供重新生成（regenerate）或中止回應的功能 | O        |
| 記憶機制       | 儲存使用者偏好，實現跨對話持續性           | O        |
| 工具整合       | 串接外部 API，使聊天機器人具備實際操作能力 | O        |

### 4. 系統截圖（`screenshots/`）

在 `screenshots/` 資料夾放入以下截圖：

- `chat.png`：聊天機器人主畫面，**需包含至少一輪完整的對話**
- `history.png`：對話歷史或多 session 切換的畫面

### 5. 心得報告（本 README.md 下方）

在本 README 的**心得報告**區填寫。

---

## 專案結構範例

```
your-repo/
├── .agents/
│   └── skills/
│       ├── prd/SKILL.md
│       ├── architecture/SKILL.md
│       ├── models/SKILL.md
│       ├── implement/SKILL.md
│       ├── test/SKILL.md
│       └── commit/SKILL.md
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   └── MODELS.md
├── templates/
│   └── index.html
├── screenshots/
│   ├── chat.png
│   ├── history.png
│   └── skill.png
├── app.py
├── requirements.txt
├── .env.example
└── README.md          ← 本檔案（含心得報告）
```

---

## 啟動方式

```bash
# 1. 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. 安裝套件
pip install -r requirements.txt

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env，填入 GEMINI_API_KEY

# 4. 啟動伺服器
uvicorn app:app --reload
# 開啟瀏覽器：http://localhost:8000
```

---

## 心得報告

**姓名**：
**學號**：

### 問題與反思

**Q1. 你設計的哪一個 Skill 效果最好？為什麼？哪一個效果最差？你認為原因是什麼？**

> **效果最好的是 `implement/`。**因為我將技術棧（HTML 前端 + FastAPI + SQLite 後端）以及需要實作的功能定義得非常明確，AI 可以很容易地根據這些明確的條件與結構，產生完整且連貫的程式碼，並自動處理資料庫的初始化與 API 路由設定，大幅減少了手動串接的時間。
> 
> **效果相對最差的是 `test/`（或是 `commit/` 相關流程）。**因為測試通常需要實際去點擊畫面、觀察 UI 變化或是驗證外部 API 的報錯（例如 Quota 限制），這些偏向實務操作與本地環境相依的行為，很難單純用語法讓 AI 自行驗證，仍然需要大量的人工介入與判斷。

---

**Q2. 在用 AI 產生程式碼的過程中，你遇到什麼問題是 AI 沒辦法自己解決、需要你介入處理的？**

> 1. **API 模型版本與額度限制 (Quota Exceeded)**：AI 一開始產生的程式碼使用了 `gemini-1.5-pro`，但在實際執行時遇到了 404 與 429 的額度錯誤。這是因為我的 API 金鑰對應的模型可用版本不同，且免費版的請求頻率有嚴格限制（如每分鐘 5 次）。這種帳號專屬的環境限制，AI 無法事先得知，必須由我實際執行伺服器、看到報錯訊息後，將終端機的 log 貼給 AI，再由它幫忙把模型改為有額度的 `gemini-2.5-flash`。
> 2. **本機環境權限問題**：在 Windows 啟動虛擬環境 `.venv\Scripts\activate` 時，遇到了 PowerShell 停用指令碼執行的安全性錯誤 (Execution Policy)。這種涉及本機作業系統安全設定的問題，也需要我手動下達 `Set-ExecutionPolicy` 才有辦法排除障礙並繼續開發。
