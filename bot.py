from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
# 變更：從 openai 換成 google.generativeai
import os
import google.generativeai as genai

# 診斷：印出環境變數狀態
print("=== 環境變數檢查 ===")
print(f"BOT_TOKEN: {'✅ 已設定' if os.getenv('BOT_TOKEN') else '❌ 未設定'}")
# 變更：檢查 GEMINI_API_KEY
print(f"GEMINI_API_KEY: {'✅ 已設定' if os.getenv('GEMINI_API_KEY') else '❌ 未設定'}")
print(f"DB_DSN: {'✅ 已設定' if os.getenv('DB_DSN') else '❌ 未設定'}")

# 檢查 BOT_TOKEN 格式
bot_token = os.getenv("BOT_TOKEN")
if bot_token:
    if ":" in bot_token and len(bot_token) > 20:
        print(f"BOT_TOKEN 格式: ✅ 看起來正確")
    else:
        print(f"BOT_TOKEN 格式: ❌ 格式可能有問題")
        print(f"當前長度: {len(bot_token)}")
else:
    print("❌ BOT_TOKEN 完全沒有讀取到")

# 變更：使用 GEMINI_API_KEY
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 如果沒有 BOT_TOKEN，直接退出
if not BOT_TOKEN:
    print("❌ 無法啟動：BOT_TOKEN 未設定")
    exit(1)

# 變更：初始化 Gemini 客戶端
try:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini 客戶端初始化成功")
except Exception as e:
    print(f"❌ Gemini 客戶端初始化失敗：{e}")

# 處理訊息
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    
    try:
        # 變更：使用 Gemini 的模型名稱與方法
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # 變更：呼叫 generate_content
        response = model.generate_content(user_input)
        
        # 變更：從 response 物件中提取文字內容
        await update.message.reply_text(response.text)
        print(f"✅ 成功回覆用戶: {update.message.from_user.first_name}")
        
    except Exception as e:
        error_msg = f"抱歉，發生錯誤：{str(e)}"
        await update.message.reply_text(error_msg)
        print(f"❌ 處理訊息錯誤：{e}")

# 啟動 Bot
try:
    print("🚀 嘗試啟動 Telegram Bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    port = int(os.environ.get("PORT", 8000))
    print(f"📡 使用 Port: {port}")
    
    # 使用 polling 模式測試
    print("🔄 使用 Polling 模式啟動...")
    app.run_polling()
    
except Exception as e:
    print(f"❌ Bot 啟動失敗：{e}")
