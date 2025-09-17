from telegram.ext import Updater, MessageHandler, Filters
from app.config import settings
from handlers.files import handle_file
from handlers.text import handle_text
