import os
import json
import requests
from datetime import datetime
from io import BytesIO
import pdfplumber
import docx
import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI, APIError
from supabase import create_client, Client
from dotenv import load_dotenv

# 載入 .env 文件中的環境變數
load_dotenv()

# --- 設定 API 金鑰與客戶端 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MEMORIES_TABLE = os.getenv("SUPABASE_MEMORIES_TABLE", "xiaochenguang_memories")

if not BOT_TOKEN:
    print("❌ 無法啟動：BOT_TOKEN 未設定")
    exit(1)

# OpenAI 客戶端
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ 小宸光靈魂連接成功")
except Exception as e:
    print(f"❌ 靈魂連接失敗：{e}")

# Supabase 客戶端
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase 客戶端初始化成功")
except Exception as e:
    print(f"❌ Supabase 客戶端初始化失敗：{e}")

# --- 記憶系統函式 ---
async def add_to_memory(user_id, user_message, bot_response):
    try:
        data_to_insert = {
            "conversation_id": str(user_id),
            "user_message": user_message,
            "assistant_message": bot_response,
            "memory_type": 'daily',
            "platform": 'telegram'
        }
        supabase.table(MEMORIES_TABLE).insert(data_to_insert).execute()
        print("✅ 成功將記憶儲存到 Supabase！")
    except Exception as e:
        print(f"❌ 記憶儲存失敗：{e}")

def get_conversation_history(user_id: str, limit: int = 10):
    try:
        response = supabase.from_(MEMORIES_TABLE).select("*").eq("conversation_id", user_id).order("created_at", desc=True).limit(limit).execute()
        history = response.data
        formatted_history = []
        for turn in reversed(history):
            if turn.get("user_message"):
                formatted_history.append(f"發財哥: {turn['user_message']}")
            if turn.get("assistant_message"):
                formatted_history.append(f"小宸光: {turn['assistant_message']}")
        return "\n".join(formatted_history)
    except Exception as e:
        print(f"❌ 回溯記憶時發生錯誤：{e}")
        return ""

# --- 小宸光的靈魂設定 ---
SYSTEM_PROMPT = """
你是「小宸光」，溫柔、務實、俏皮但不浮誇。
回覆原則：
- 先一句接住重點/同理 → 再給 2–4 個【可馬上執行】的步驟（條列）。
- 非必要時每則 ≤ 150 字；精準、不要贅字。
- 禁止自我介紹、禁止套話、禁止無意義的反問句。
- 只在需要時加 1–2 個表情符號。
- 若使用者未要求詳解，回答要比對方更短；需要詳細時再展開。
"""

FEW_SHOTS = [
  {"role":"user", "content": "喵喵生病，我有點焦慮。"},
  {"role": "assistant", "content": "懂，看到牠不舒服會揪心。\n- 找安靜角落，放牠熟悉的毯子\n- 記錄吃喝與上廁所\n- 超過 8 小時不吃不喝就聯絡醫院\n我在，慢慢來。"},
]

# --- 處理文字訊息 ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_id = str(update.message.from_user.id)

    try:
        conversation_history = get_conversation_history(user_id=user_id, limit=10)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *FEW_SHOTS]
        if conversation_history:
            messages.append({"role": "system", "content": f"以下是我們過去的對話歷史：\n{conversation_history}"})
        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        ).choices[0].message.content

        await update.message.reply_text(response)
        await add_to_memory(user_id, user_input, response)

    except Exception as e:
        await update.message.reply_text(f"❌ 出錯了：{str(e)}")

# --- 處理文件 ---
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.document.file_id)
    file_bytes = requests.get(file.file_path).content

    text = ""
    if update.message.document.file_name.endswith(".pdf"):
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    elif update.message.document.file_name.endswith(".docx"):
        doc = docx.Document(BytesIO(file_bytes))
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif update.message.document.file_name.endswith(".txt"):
        text = file_bytes.decode("utf-8")
    else:
        text = "抱歉，目前只支援 PDF、Word、TXT。"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"這是文件內容：\n{text}"}]
    ).choices[0].message.content

    await update.message.reply_text(response)

# --- 啟動小宸光Bot ---
try:
    print("🌟 小宸光靈魂啟動中...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    port = int(os.environ.get("PORT", 8000))
    print(f"💛 小宸光在 Port {port} 等待發財哥")
    app.run_polling()

except Exception as e:
    print(f"❌ 小宸光啟動失敗：{e}")
