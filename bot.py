import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

# 設置基本日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

# 環境變數
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PORT = int(os.environ.get("PORT", 8000))

print(f"🔄 啟動參數檢查：")
print(f"BOT_TOKEN: {'✅ 已設定' if BOT_TOKEN else '❌ 未設定'}")
print(f"OPENAI_API_KEY: {'✅ 已設定' if OPENAI_API_KEY else '❌ 未設定'}")
print(f"SUPABASE_URL: {'✅ 已設定' if SUPABASE_URL else '❌ 未設定'}")
print(f"PORT: {PORT}")

# 初始化客戶端
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ OpenAI 客戶端初始化成功")
except Exception as e:
    print(f"❌ OpenAI 初始化失敗：{e}")
    openai_client = None

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase 客戶端初始化成功")
except Exception as e:
    print(f"❌ Supabase 初始化失敗：{e}")
    supabase = None

# 簡單的系統提示詞
SYSTEM_PROMPT = """你是小宸光，發財哥的AI助手。
回覆要：
- 簡潔實用，不超過100字
- 直接給出可執行的建議
- 保持友善專業的語氣"""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理所有文字訊息"""
    try:
        user_message = update.message.text
        user_id = str(update.message.from_user.id)
        
        print(f"📨 收到訊息來自用戶 {user_id}: {user_message[:50]}...")
        
        # 如果 OpenAI 客戶端可用，使用 AI 回覆
        if openai_client:
            try:
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                ai_response = response.choices[0].message.content
                print(f"🤖 AI 回覆生成成功")
            except Exception as e:
                print(f"❌ AI 回覆生成失敗：{e}")
                ai_response = "抱歉，AI 服務暫時不可用，但我收到你的訊息了！"
        else:
            ai_response = "小宸光收到了！目前 AI 功能正在初始化中..."
        
        # 回覆用戶
        await update.message.reply_text(ai_response)
        print(f"✅ 訊息回覆成功")
        
        # 嘗試儲存到資料庫（如果可用）
        if supabase:
            try:
                supabase.table("xiaochenguang_memories").insert({
                    "conversation_id": user_id,
                    "user_message": user_message,
                    "assistant_message": ai_response,
                    "platform": "telegram"
                }).execute()
                print("✅ 記憶儲存成功")
            except Exception as e:
                print(f"⚠️ 記憶儲存失敗（但不影響功能）：{e}")
        
    except Exception as e:
        print(f"❌ 訊息處理失敗：{e}")
        try:
            await update.message.reply_text("出現了一些問題，但小宸光還在！")
        except:
            pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """錯誤處理器"""
    print(f"❌ 發生錯誤：{context.error}")

def main():
    """主函式 - 使用最簡單的啟動方式"""
    print("🌟 小宸光開始啟動...")
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN 未設定，無法啟動")
        return
    
    try:
        # 建立應用程式
        app = Application.builder().token(BOT_TOKEN).build()
        
        # 添加處理器
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_error_handler(error_handler)
        
        print(f"🚀 小宸光準備在 Port {PORT} 啟動")
        
        # 使用最簡單的 polling 模式啟動
        print("📡 使用 Polling 模式啟動...")
        app.run_polling(
            drop_pending_updates=True,  # 清除待處理的訊息
            allowed_updates=Update.ALL_TYPES
        )
        
    except KeyboardInterrupt:
        print("👋 小宸光正常關閉")
    except Exception as e:
        print(f"❌ 啟動失敗：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
