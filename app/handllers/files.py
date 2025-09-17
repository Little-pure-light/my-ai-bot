import os
from telegram import Update
from telegram.ext import CallbackContext

UPLOAD_DIR = "uploads"

def handle_file(update: Update, context: CallbackContext):
    file = update.message.document
    if not file:
        update.message.reply_text("❌ 沒有收到檔案")
        return

    # 下載檔案
    file_path = os.path.join(UPLOAD_DIR, file.file_name)
    file.get_file().download(file_path)

    # 回報
    update.message.reply_text(f"✅ 檔案已存到 {file_path}")
