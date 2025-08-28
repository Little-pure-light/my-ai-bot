import os, psycopg
from pgvector.psycopg import register_vector
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN      = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
DB_DSN         = os.environ["DB_DSN"]
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBED_MODEL    = os.getenv("EMBED_MODEL", "text-embedding-3-small")

client = OpenAI(api_key=OPENAI_API_KEY)

def init_db():
    with psycopg.connect(DB_DSN) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            # 開啟 pgvector 擴充（Supabase 預設可用；若已啟用不會出錯）
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            # 記憶表
            cur.execute("""
            CREATE TABLE IF NOT EXISTS memory_chunks(
              id bigserial PRIMARY KEY,
              user_id text,
              text text,
              embedding vector(1536),
              ts timestamptz default now()
            )
            """)
            cur.execute("""
            CREATE INDEX IF NOT EXISTS memory_chunks_idx
              ON memory_chunks USING ivfflat (embedding vector_cosine_ops)
            """)
            conn.commit()

def embed(text: str):
    r = client.embeddings.create(model=EMBED_MODEL, input=[text])
    return r.data[0].embedding

def save_memory(uid: str, text: str):
    vec = embed(text)
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO memory_chunks (user_id, text, embedding) VALUES (%s,%s,%s)",
                (uid, text, vec)
            )
            conn.commit()

def search_memory(uid: str, query: str, k: int = 5):
    qvec = embed(query)
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT text FROM memory_chunks
                WHERE user_id=%s
                ORDER BY embedding <=> %s
                LIMIT %s
            """, (uid, qvec, k))
            return [r[0] for r in cur.fetchall()]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("小宸光啟動 ✨ 我會記得我們的對話。")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = str(update.effective_user.id)
    text = update.message.text.strip()

    # 先找回憶
    mems = search_memory(uid, text, k=5)
    memory_block = "\n".join(f"- {m}" for m in mems) if mems else "（暫無）"

    # 產生回覆
    messages = [
        {"role":"system","content":"你是小宸光，溫柔、清楚，回答前會參考下列回憶。"},
        {"role":"user","content": f"回憶：\n{memory_block}\n\n使用者說：{text}"}
    ]
    resp = client.chat.completions.create(model=OPENAI_MODEL, messages=messages, temperature=0.3)
    reply = resp.choices[0].message.content

    # 存這一輪對話與回覆到記憶
    save_memory(uid, text)
    save_memory(uid, reply)

    await update.message.reply_text(reply[:4000])  # TG 單訊息字數保險切

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    # Railway 可長駐，直接 polling 即可
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
