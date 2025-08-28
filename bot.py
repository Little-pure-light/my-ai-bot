import os, psycopg
from pgvector.psycopg import register_vector
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
DB_DSN   = os.environ["DB_DSN"]

# ✅ 這裡只保留一次，不要重複
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBED_MODEL  = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# …下面程式碼繼續（init_db, embed, save_memory, search_memory, handle_msg, main 等）
