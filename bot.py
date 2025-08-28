import os, psycopg
from pgvector.psycopg import register_vector
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
DB_DSN   = os.environ["DB_DSN"]

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])  # ✅ 保留這一個就好

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBED_MODEL  = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# …下面程式碼照舊
