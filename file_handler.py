import os
import requests  # 添加以支援 OpenAI 文件上傳（如果需要）
from telegram import Update
from telegram.ext import ContextTypes
from supabase import create_client, Client  # 如果在 bot.py 中已定義，可全局使用
from openai import OpenAI  # 同上

# 假設從環境變數載入（或從 bot.py 傳入）
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str = None):
    document = update.message.document
    if not document:
        await update.message.reply_text("❌ 沒有收到檔案")
        return "沒有收到檔案"

    file_path = os.path.join("/tmp", document.file_name)
    os.makedirs("/tmp", exist_ok=True)  # 確保暫存目錄存在

    try:
        # 異步獲取並下載文件
        file_obj = await context.bot.get_file(document.file_id)
        await file_obj.download_to_drive(file_path)
        await update.message.reply_text(f"✅ 檔案已下載到 {file_path}")

        # (可選) 上傳到 Supabase 儲存
        with open(file_path, "rb") as f:
            supabase.storage.from_("your-bucket-name").upload(f"users/{user_id}/{document.file_name}", f)  # 替換 your-bucket-name
        await update.message.reply_text("📤 檔案已上傳到 Supabase")

        # (可選) 使用 OpenAI 處理文件（例如上傳並分析內容）
        with open(file_path, "rb") as f:
            openai_file = openai_client.files.create(file=f, purpose="assistants")
        # 示例：使用模型分析文件內容
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"請摘要這個文件: {openai_file.id}"}],
            max_tokens=500
        ).choices[0].message.content
        await update.message.reply_text(f"🧠 OpenAI 分析結果：\n{response}")

        return "文件處理完成！"
    except Exception as e:
        await update.message.reply_text(f"❌ 檔案處理失敗: {str(e)}")
        return f"錯誤: {str(e)}"
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)  # 清理暫存文件

# 如果有 download_full_file，保留原樣
def download_full_file(...):  # 您的原有邏輯
    pass
