from telegram.ext import Updater, MessageHandler, Filters
from app.config import settings
from handlers.files import handle_file
from handlers.text import handle_text
from .handllers import files
dp.add_handler(MessageHandler(filters.Document.ALL, files.handle_file))

def register_handlers(application: Application):
    # 文件上傳
    application.add_handler(MessageHandler(filters.Document.ALL, files.handle_file))
    # 圖片上傳
    application.add_handler(MessageHandler(filters.PHOTO, files.handle_image))




