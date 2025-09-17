from telegram import Update
from telegram.ext import CallbackContext

def handle_text(update: Update, context: CallbackContext):
    user_text = update.message.text
    update.message.reply_text(f"你說了：{user_text}")
