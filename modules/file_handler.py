import os
from telegram import Update
from telegram.ext import ContextTypes
from supabase import create_client, Client
from openai import OpenAI
from dotenv import load_dotenv
import PyPDF2
from docx import Document

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BUCKET_NAME = "xiaochenguang"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE, conversation_id: str = None):
    document = update.message.document
    if not document:
        await update.message.reply_text("❌ 沒有收到檔案")
        return "沒有收到檔案"

    file_path = os.path.join("temp", f"{conversation_id}_{document.file_name}")  # 改為 temp，避免 /tmp 權限問題
    os.makedirs("temp", exist_ok=True)

    try:
        # 下載文件
        file_obj = await context.bot.get_file(document.file_id)
        await file_obj.download_to_drive(file_path)
        await update.message.reply_text(f"✅ 檔案已下載: {document.file_name}")

        # 提取文件內容
        file_content = ""
        file_ext = os.path.splitext(document.file_name)[1].lower()
        if file_ext == '.pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    file_content += page.extract_text() or ""  # 處理空頁
        elif file_ext == '.docx':
            doc = Document(file_path)
            for para in doc.paragraphs:
                file_content += para.text + "\n"
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

        file_content = file_content[:10000]  # 限制長度

        # 上傳到 Supabase Storage
        with open(file_path, "rb") as f:
            supabase.storage.from_(BUCKET_NAME).upload(f"users/{conversation_id}/{document.file_name}", f)
        await update.message.reply_text(f"📤 檔案已上傳到 Supabase bucket: {BUCKET_NAME}")

        # OpenAI 摘要
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"請摘要此文件內容：\n\n{file_content}"}],
            max_tokens=600
        ).choices[0].message.content
        await update.message.reply_text(f"🧠 分析結果：\n{response}")

        # 儲存到資料表
        supabase.table("xiaochenguang_memories").insert({
            "conversation_id": conversation_id,
            "file_name": document.file_name,
            "document_content": file_content,
            "created_at": "now()",
            "platform": "telegram"
        }).execute()

        return "文件處理完成！"
    except Exception as e:
        await update.message.reply_text(f"❌ 處理失敗: {str(e)}")
        return f"錯誤: {str(e)}"
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def download_full_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("下載功能正在開發中...")


