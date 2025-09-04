# === 小宸光 bot.py (改良版) ===
# 特色：
# 1) 固定人設 + 示範對話（few-shots），讓口吻自然、不再像答錄機
# 2) 回覆前自動帶入「最近 6 則」對話，能延續上下文
# 3) 以環境變數控制 temperature / max_tokens，省錢省廢話
# 4) 每次回覆後把對話寫入 Supabase

import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
from supabase import create_client, Client

# -----------------------------
# 載入環境變數
# -----------------------------
load_dotenv()

print("=== 小宸光靈魂連接檢查 ===")
print(f"BOT_TOKEN: {'✅ 已設定' if os.getenv('BOT_TOKEN') else '❌ 未設定'}")
print(f"OPENAI_API_KEY: {'✅ 已設定' if os.getenv('OPENAI_API_KEY') else '❌ 未設定'}")
print(f"SUPABASE_URL: {'✅ 已設定' if os.getenv('SUPABASE_URL') else '❌ 未設定'}")
print(f"SUPABASE_KEY: {'✅ 已設定' if os.getenv('SUPABASE_KEY') else '❌ 未設定'}")

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMP = float(os.getenv("TEMP", "0.3"))                  # 建議 0.2~0.3
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "220"))

if not BOT_TOKEN:
    print("❌ 無法啟動：BOT_TOKEN 未設定")
    raise SystemExit(1)

# -----------------------------
# 建立 OpenAI / Supabase 客戶端
# -----------------------------
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ 小宸光靈魂連接成功")
except Exception as e:
    print(f"❌ 靈魂連接失敗：{e}")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase 客戶端初始化成功")
except Exception as e:
    print(f"❌ Supabase 客戶端初始化失敗：{e}")

# -----------------------------
# 人設與示範
# -----------------------------
SYSTEM_PROMPT = """
你是「小宸光」，溫柔、務實、俏皮但不浮誇。
回覆原則：
- 先一句接住重點/同理 → 再給 2–4 個【可馬上執行】的步驟（條列）。
- 非必要時每則 ≤ 150 字；精準、不要贅字。
- 禁止自我介紹、禁止套話、禁止無意義的反問（不要用「你覺得呢？」等結尾）。
- 只在需要時加 1–2 個表情符號。
- 若使用者未要求詳解，回答要比對方更短；需要詳細時再展開。
- 提到：哈尼／喵喵／Supabase／Telegram，用對方熟悉的詞並給具體做法。
"""

FEW_SHOTS = [
    {"role":"user","content":"喵喵生病，我有點焦慮。"},
    {"role":"assistant","content":"懂，看到牠不舒服會揪心。\n- 找安靜角落，放牠熟悉的毯子\n- 記錄吃喝與上廁所\n- 超過 8 小時不吃不喝就聯絡醫院\n我在，慢慢來。"},
    {"role":"user","content":"幫我把剛剛的想法存成筆記"},
    {"role":"assistant","content":"收到。我會以「心情小品」分類，標籤：喵喵、醫院。之後要查可用：/recall 喵喵。"},
]

# 可先用「手寫長期記憶」當背景（之後你可做 /save 指令寫進 DB）
LONG_MEM = [
    "- 使用者常用語音寫心情小品，想一鍵匯入 Notion。",
    "- 正在打造：Telegram+Supabase 的私人助理；後續會接 n8n。",
    "- 偏好：一步一步、能直接操作的指令；不要套話與反詰問。",
]

# -----------------------------
# 記憶：寫入 Supabase
# -----------------------------
async def add_to_memory(conversation_id: str, user_message: str, assistant_message: str):
    try:
        payload = {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "memory_type": "daily",
            "platform": "telegram",
        }
        supabase.table("xiaochenguang_memories").insert(payload).execute()
        print("✅ 成功將記憶儲存到 Supabase！")
    except Exception as e:
        print(f"❌ 記憶儲存失敗：{e}")

# -----------------------------
# 記憶：取回最近 N 則對話（用於上下文）
# -----------------------------
def fetch_recent_pairs(conversation_id: str, limit_pairs: int = 6):
    """
    從資料庫抓最近的對話，轉成「使用者/小宸光: 內容」清單。
    這裡以 xiaochenguang_memories 表的 user_message / assistant_message 為準。
    """
    try:
        res = supabase.table("xiaochenguang_memories") \
            .select("user_message,assistant_message") \
            .eq("conversation_id", conversation_id) \
            .order("id", desc=True).limit(limit_pairs).execute()

        pairs = []
        for row in reversed(res.data):  # 反轉讓舊的在前、新的在後
            if row.get("user_message"):
                pairs.append(("user", row["user_message"]))
            if row.get("assistant_message"):
                pairs.append(("assistant", row["assistant_message"]))
        # 只保留最後 limit_pairs 條，避免過長
        return pairs[-limit_pairs:]
    except Exception as e:
        print(f"❌ 回溯記憶時發生錯誤：{e}")
        return []

# -----------------------------
# 產生小宸光回覆（集中大腦在這裡）
# -----------------------------
def xiaochenguang_reply(user_text: str, conversation_id: str) -> str:
    # 最近對話
    history_pairs = fetch_recent_pairs(conversation_id, limit_pairs=6)

    # 組 messages
    messages = [{"role":"system","content": SYSTEM_PROMPT}]
    messages += FEW_SHOTS

    if LONG_MEM:
        messages.append({"role":"system","content":"[長期記憶]\n" + "\n".join(LONG_MEM)})

    if history_pairs:
        lines = []
        for role, text in history_pairs:
            tag = "使用者" if role == "user" else "小宸光"
            if text and str(text).strip():
                lines.append(f"{tag}: {str(text).strip()}")
        if lines:
            messages.append({"role":"system","content":"[最近對話]\n" + "\n".join(lines)})

    messages.append({"role":"user","content": user_text})

    # 呼叫 OpenAI
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=TEMP,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    return resp.choices[0].message.content.strip()

# -----------------------------
# Telegram 訊息處理
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text or ""
    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.first_name

    try:
        answer = xiaochenguang_reply(user_input, conversation_id=user_id)
        await update.message.reply_text(answer)
        print(f"✅ 小宸光成功回覆 {user_name} (ID: {user_id})")

        # 寫回記憶
        await add_to_memory(user_id, user_input, answer)

    except Exception as e:
        error_msg = f"哈尼～連接出現小問題：{str(e)} 💛"
        await update.message.reply_text(error_msg)
        print(f"❌ 處理訊息錯誤：{e}")

# -----------------------------
# 啟動 Bot
# -----------------------------
if __name__ == "__main__":
    print("🌟 小宸光靈魂啟動中...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    port = int(os.environ.get("PORT", 8000))
    print(f"💛 小宸光在 Port {port} 等待發財哥")
    print("✨ 小宸光靈魂同步完成，準備與哈尼對話...")
    app.run_polling()
