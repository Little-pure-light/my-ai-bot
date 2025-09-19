import os
from telegram import Update
from telegram.ext import ContextTypes
from supabase import create_client, Client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # 載入環境變數

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BUCKET_NAME = "xiaochenguang"  # 替換為您創建的 bucket 名稱

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str = None):
    document = update.message.document
    if not document:
        await update.message.reply_text("❌ 沒有收到檔案")
        return "沒有收到檔案"

    file_path = os.path.join("/tmp", document.file_name)
    os.makedirs("/tmp", exist_ok=True)

    try:
        # 異步下載文件
        file_obj = await context.bot.get_file(document.file_id)
        await file_obj.download_to_drive(file_path)
        await update.message.reply_text(f"✅ 檔案已下載: {document.file_name}")

        # 上傳到 Supabase
        with open(file_path, "rb") as f:
            supabase.storage.from_(BUCKET_NAME).upload(f"users/{user_id}/{document.file_name}", f)
        await update.message.reply_text(f"📤 檔案已上傳到 Supabase bucket: {BUCKET_NAME}")

        # OpenAI 處理（範例：摘要文件）
        with open(file_path, "rb") as f:
            openai_file = openai_client.files.create(file=f, purpose="assistants")
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"請摘要此文件內容: {openai_file.id}"}],
            max_tokens=300
        ).choices[0].message.content
        await update.message.reply_text(f"🧠 分析結果：\n{response}")

        return "文件處理完成！"
    except Exception as e:
        await update.message.reply_text(f"❌ 處理失敗: {str(e)}")
        return f"錯誤: {str(e)}"
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# 保留 download_full_file（如果需要）
async def download_full_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("下載功能正在開發中...")
