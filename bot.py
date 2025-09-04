import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PORT = int(os.environ.get("PORT", 8000))

print(f"🔍 檢查環境變數：")
print(f"BOT_TOKEN: {'有' if BOT_TOKEN else '無'}")
print(f"OPENAI_API_KEY: {'有' if OPENAI_API_KEY else '無'}")
print(f"SUPABASE_URL: {'有' if SUPABASE_URL else '無'}")
print(f"SUPABASE_KEY: {'有' if SUPABASE_KEY else '無'}")

# 初始化服務
openai_client = None
supabase = None

try:
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI 連接成功")
    else:
        print("⚠️ 沒有 OpenAI API Key")
except Exception as e:
    print(f"❌ OpenAI 連接失敗: {e}")

try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase 連接成功")
    else:
        print("⚠️ 缺少 Supabase 設定")
except Exception as e:
    print(f"❌ Supabase 連接失敗: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理所有訊息"""
    try:
        user_message = update.message.text
        user_id = str(update.message.from_user.id)
        user_name = update.message.from_user.first_name or "朋友"
        
        print(f"💬 收到 {user_name}({user_id}) 的訊息: {user_message}")
        
        # 生成回復
        if openai_client:
            try:
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system", 
                            "content": f"你是小宸光，{user_name} 的AI助手。用友善簡潔的方式回復，不超過100字。"
                        },
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
                bot_reply = response.choices[0].message.content
                print(f"🤖 AI 回復已生成")
            except Exception as e:
                print(f"❌ AI 生成失敗: {e}")
                bot_reply = f"嗨 {user_name}！我收到你的訊息了，但 AI 功能暫時有點問題。不過我在這裡！"
        else:
            bot_reply = f"嗨 {user_name}！小宸光收到你的訊息了。目前還在設定中，請稍等一下～"
        
        # 回復用戶
        await update.message.reply_text(bot_reply)
        print(f"✅ 已回復用戶")
        
        # 嘗試儲存記憶
        if supabase:
            try:
                data = {
                    "conversation_id": user_id,
                    "user_message": user_message,
                    "assistant_message": bot_reply,
                    "platform": "telegram"
                }
                supabase.table("xiaochenguang_memories").insert(data).execute()
                print(f"💾 記憶已儲存")
            except Exception as e:
                print(f"⚠️ 記憶儲存失敗（不影響對話）: {e}")
        
    except Exception as e:
        print(f"❌ 處理訊息時發生錯誤: {e}")
        try:
            await update.message.reply_text("哎呀！出現了小問題，但小宸光還在努力運作中！")
        except:
            pass

def main():
    """啟動機器人"""
    print("🌟 小宸光開始啟動...")
    
    if not BOT_TOKEN:
        print("❌ 沒有 BOT_TOKEN，無法啟動")
        return
    
    try:
        # 建立應用
        app = Application.builder().token(BOT_TOKEN).build()
        
        # 加入訊息處理器
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print(f"🚀 準備在 Port {PORT} 啟動")
        
        # 啟動（用最簡單的方式）
        app.run_polling()
        
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
