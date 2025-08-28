from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os
import psycopg2

# 設定 API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# 修正：移除 proxies 參數
client = OpenAI(api_key=OPENAI_API_KEY)

# 資料庫連接
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255),
        message TEXT,
        response TEXT,
        timestamp TIMESTAMP DEFAULT NOW()
    )
""")
conn.commit()

# 處理訊息
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_id = update.message.from_user.id

    # 修正：使用新版 OpenAI API 語法
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_input}]
    ).choices[0].message.content

    # 存入資料庫
    cur.execute(
        "INSERT INTO conversations (user_id, message, response) VALUES (%s, %s, %s)",
        (user_id, user_input, response)
    )
    conn.commit()

    # 回覆用戶
    await update.message.reply_text(response)

# 啟動 Bot
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, handle_message))

if __name__ == "__main__":
    app.run_polling()
