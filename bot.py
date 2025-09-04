import os
import logging
import requests
from io import BytesIO
import pdfplumber
import docx

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

# 系統提示詞
SYSTEM_PROMPT = """你是小宸光，發財哥的AI助手。
回復要：
- 簡潔實用，不超過200字
- 直接給出可執行的建議
- 保持友善專業的語氣
- 針對文件內容提供實用分析"""

# === 文件處理核心功能 ===
async def extract_text_from_file(file_bytes, file_name):
    """從文件中提取文字內容"""
    try:
        text = ""
        file_extension = file_name.lower().split('.')[-1]
        
        if file_extension == "pdf":
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        
        elif file_extension == "docx":
            doc = docx.Document(BytesIO(file_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"
        
        elif file_extension == "txt":
            text = file_bytes.decode("utf-8")
        
        else:
            return None, f"不支援的文件格式：{file_extension}"
        
        return text.strip(), None
        
    except Exception as e:
        return None, f"文件處理失敗：{str(e)}"

async def analyze_document_content(text, file_name):
    """使用AI分析文件內容"""
    if not openai_client:
        return "AI服務暫時不可用，但我收到了您的文件！"
    
    try:
        # 限制文字長度避免token超限
        max_chars = 3000
        if len(text) > max_chars:
            text = text[:max_chars] + "...(內容已截取)"
        
        analysis_prompt = f"""
請分析這個文件內容，並提供：
- 核心重點（2-3個要點）
- 實用建議（如果適用）
- 需要注意的地方

文件名：{file_name}
內容：
{text}
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": analysis_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"分析失敗：{str(e)}"

# === 處理器函數 ===
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理文件訊息"""
    user_id = str(update.message.from_user.id)
    
    try:
        print(f"📄 收到文件來自用戶 {user_id}")
        
        # 發送處理中訊息
        await update.message.reply_text("📄 小宸光正在讀取文件...")
        
        # 獲取文件
        file = await context.bot.get_file(update.message.document.file_id)
        file_name = update.message.document.file_name
        
        # 檢查文件大小（Telegram限制）
        if update.message.document.file_size > 20 * 1024 * 1024:  # 20MB
            await update.message.reply_text("❌ 文件太大了！請上傳小於20MB的文件。")
            return
        
        # 下載文件
        file_bytes = requests.get(file.file_path).content
        print(f"✅ 文件下載完成：{file_name}")
        
        # 提取文字
        text, error = await extract_text_from_file(file_bytes, file_name)
        
        if error:
            await update.message.reply_text(f"❌ {error}\n\n目前支援：PDF、Word(.docx)、TXT文件")
            return
        
        if not text or len(text.strip()) < 10:
            await update.message.reply_text("📄 文件內容為空或過短，請檢查文件是否正常。")
            return
        
        print(f"✅ 文字提取完成，共 {len(text)} 字符")
        
        # AI分析
        analysis = await analyze_document_content(text, file_name)
        
        # 回復分析結果
        response_message = f"📋 **{file_name}** 分析完成：\n\n{analysis}"
        await update.message.reply_text(response_message)
        
        # 儲存到記憶
        if supabase:
            try:
                supabase.table("xiaochenguang_memories").insert({
                    "conversation_id": user_id,
                    "user_message": f"[文件: {file_name}]",
                    "assistant_message": analysis,
                    "platform": "telegram"
                }).execute()
                print("✅ 文件記憶儲存成功")
            except Exception as e:
                print(f"⚠️ 記憶儲存失敗：{e}")
        
    except Exception as e:
        error_msg = f"❌ 文件處理失敗：{str(e)}"
        await update.message.reply_text(error_msg)
        print(f"文件處理錯誤：{e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理所有文字訊息"""
    try:
        user_message = update.message.text
        user_id = str(update.message.from_user.id)
        
        print(f"💬 收到訊息來自用戶 {user_id}: {user_message[:50]}...")
        
        # 如果 OpenAI 客戶端可用，使用 AI 回復
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
                print(f"🤖 AI 回復生成成功")
            except Exception as e:
                print(f"❌ AI 回復生成失敗：{e}")
                ai_response = "抱歉，AI 服務暫時不可用，但我收到你的訊息了！"
        else:
            ai_response = "小宸光收到了！目前 AI 功能正在初始化中..."
        
        # 回復用戶
        await update.message.reply_text(ai_response)
        print(f"✅ 訊息回復成功")
        
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
    """主函式"""
    print("🌟 小宸光開始啟動...")
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN 未設定，無法啟動")
        return
    
    try:
        # 建立應用程式
        app = Application.builder().token(BOT_TOKEN).build()
        
        # 添加處理器
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(filters.Document.ALL, handle_document))  # 🆕 文件處理器
        app.add_error_handler(error_handler)
        
        print(f"🚀 小宸光準備在 Port {PORT} 啟動")
        print("📄 現在支援文件讀取功能！")
        
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
