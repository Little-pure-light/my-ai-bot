from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os
import psycopg2

# 設定 API Keys（匹配你的環境變數名稱）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")  # 改成你設定的名稱
DB_DSN = os.getenv("DB_DSN")        # 改成你設定的名稱

# OpenAI 客戶端
client = OpenAI(api_key=OPENAI_API_KEY)

# 連接 Supabase 資料庫
try:
    conn = psycopg2.connect(DB_DSN)
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
    print("✅ Supabase 資料庫連接成功！")
except Exception as e:
    print(f"❌ 資料庫連接失敗：{e}")
    conn = None

# 處理訊息
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_id = str(update.message.from_user.id)
    
    try:
        # 使用你設定的模型
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": user_input}]
        ).choices[0].message.content
        
        # 存入資料庫
        if conn:
            try:
                cur.execute(
                    "INSERT INTO conversations (user_id, message, response) VALUES (%s, %s, %s)",
                    (user_id, user_input, response)
                )
                conn.commit()
            except Exception as db_error:
                print(f"資料庫儲存失敗：{db_error}")
        
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(f"抱歉，發生錯誤：{str(e)}")
        print(f"處理訊息錯誤：{e}")

# 啟動 Bot
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, handle_message))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # 確保使用正確的webhook URL
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"https://my-ai-bot-production.up.railway.app/{BOT_TOKEN}"
    )
