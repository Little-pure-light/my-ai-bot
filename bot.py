from openai import OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
import os, psycopg
from pgvector.psycopg import register_vector
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
DB_DSN   = os.environ["DB_DSN"]
client   = OpenAI(api_key=os.environ["OPENAI_API_KEY"])  # 沒有 proxies

OPENAI_MODEL = os.getenv("OPENAI_MODEL","gpt-4o-mini")
EMBED_MODEL  = os.getenv("EMBED_MODEL","text-embedding-3-small")

# ...其餘程式照之前版本，不用改...
