from telegram.ext import Updater, MessageHandler, Filters
from app.config import settings
from handlers.files import handle_file
from handlers.text import handle_text
from .handllers import files
dp.add_handler(MessageHandler(filters.Document.ALL, files.handle_file))

def register_handlers(dp):
    # 文件上傳
    dp.add_handler(MessageHandler(Filters.document, handle_file))
    # 圖片上傳
    dp.add_handler(MessageHandler(Filters.photo, handle_file))
    # 文字訊息
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))



