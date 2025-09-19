from telegram.ext import MessageHandler, filters
from . import files
from app.config import settings
from handlers.files import handle_file
from handlers.text import handle_text
from .handllers import files
dp.add_handler(MessageHandler(filters.Document.ALL, files.handle_file))

def register_handlers(app):
    # 文件上傳
    app.add_handler(MessageHandler(filters.Document.ALL, files.handle_file))
    # 圖片上傳
    app.add_handler(MessageHandler(filters.PHOTO, files.handle_image))





