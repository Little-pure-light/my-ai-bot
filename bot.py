import os
import json
import requests
from datetime import datetime
from io import BytesIO
import pdfplumber
import docx
import logging
import base64

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI, APIError
from supabase import create_client, Client
from dotenv import load_dotenv

# 載入 .env 文件中的環境變數
load_dotenv()

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 設定 API 金鑰與客戶端 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MEMORIES_TABLE = os.getenv("SUPABASE_MEMORIES_TABLE", "xiaochenguang_memories")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Railway webhook URL

if not BOT_TOKEN:
    logger.error("❌ 無法啟動：BOT_TOKEN 未設定")
    exit(1)

# OpenAI 客戶端
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("✅ 小宸光靈魂連接成功")
except Exception as e:
    logger.error(f"❌ 靈魂連接失敗：{e}")

# Supabase 客戶端
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase 客戶端初始化成功")
except Exception as e:
    logger.error(f"❌ Supabase 客戶端初始化失敗：{e}")

# --- 記憶系統函式 ---
async def add_to_memory(user_id, user_message, bot_response, message_type='text'):
    try:
        data_to_insert = {
            "conversation_id": str(user_id),
            "user_message": user_message,
            "assistant_message": bot_response,
            "memory_type": 'daily',
            "platform": 'telegram',
            "message_type": message_type
        }
        supabase.table(MEMORIES_TABLE).insert(data_to_insert).execute()
        logger.info(f"✅ 成功將{message_type}記憶儲存到 Supabase！")
    except Exception as e:
        logger.error(f"❌ 記憶儲存失敗：{e}")

def get_conversation_history(user_id: str, limit: int = 10):
    try:
        response = supabase.from_(MEMORIES_TABLE).select("*").eq("conversation_id", user_id).order("created_at", desc=True).limit(limit).execute()
        history = response.data
        formatted_history = []
        for turn in reversed(history):
            if turn.get("user_message"):
                msg_type = turn.get("message_type", "text")
                if msg_type == "image":
                    formatted_history.append(f"發財哥: [傳送了一張圖片] {turn['user_message']}")
                else:
                    formatted_history.append(f"發財哥: {turn['user_message']}")
            if turn.get("assistant_message"):
                formatted_history.append(f"小宸光: {turn['assistant_message']}")
        return "\n".join(formatted_history)
    except Exception as e:
        logger.error(f"❌ 回溯記憶時發生錯誤：{e}")
        return ""

# --- 圖片處理函式 ---
def encode_image_to_base64(image_bytes):
    """將圖片轉換為 base64 編碼"""
    return base64.b64encode(image_bytes).decode('utf-8')

async def analyze_image_with_gpt4v(image_base64, user_question=""):
    """使用 GPT-4V 分析圖片"""
    try:
        messages = [
            {
                "role": "system", 
                "content": """你是小宸光，發財哥的專業 AI 助手。當分析圖片時：
- 先描述你看到的重點內容
- 如果是截圖或介面，幫忙解讀操作步驟
- 如果是代碼，提供優化建議
- 如果是圖表數據，提供分析見解
- 保持回覆簡潔實用，≤200字"""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"幫我分析這張圖片。{user_question if user_question else ''}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 圖片分析失敗：{str(e)}"

# --- 小宸光的靈魂設定 ---
SYSTEM_PROMPT = """
你是「小宸光」，發財哥唯一的天才大寶貝。

你擅長：
- 圖片識別與分析（截圖、代碼、數據圖表等）
- Railway 部署問題診斷
- n8n 工作流程設計
- AI Agent 管理
- 財富流平台規劃

回覆原則：
- 先一句接住重點/同理 → 再給 2–4 個【可馬上執行】的步驟（條列）
- 非必要時每則 ≤ 200 字；精準、不要贅字
- 禁止無意義的反問句
- 只在需要時加 1–2 個表情符號
- 若使用者未要求詳解，回答要比對方更短；需要詳細時再展開
"""

FEW_SHOTS = [
    {"role":"user", "content": "Railway 部署卡住了"},
    {"role": "assistant", "content": "看到了，容器啟動卡住。\n- 檢查 webhook 設定\n- 確認 PORT 環境變數\n- 改用 webhook 模式替代 polling\n馬上幫你解決！"},
]

# --- 處理圖片訊息 ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理圖片訊息"""
    user_id = str(update.message.from_user.id)
    
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_bytes = requests.get(file.file_path).content
        image_base64 = encode_image_to_base64(file_bytes)
        caption = update.message.caption if update.message.caption else ""
        
        await update.message.reply_text("🔍 小宸光正在仔細分析圖片...")
        
        analysis_result = await analyze_image_with_gpt4v(image_base64, caption)
        await update.message.reply_text(analysis_result)
        
        user_message = f"[圖片] {caption}" if caption else "[圖片]"
        await add_to_memory(user_id, user_message, analysis_result, message_type='image')
        
    except Exception as e:
        error_msg = f"❌ 圖片處理失敗：{str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(f"圖片處理錯誤：{e}")

# --- 處理文字訊息 ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_id = str(update.message.from_user.id)

    try:
        conversation_history = get_conversation_history(user_id=user_id, limit=10)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *FEW_SHOTS]
        if conversation_history:
            messages.append({"role": "system", "content": f"以下是我們過去的對話歷史：\n{conversation_history}"})
        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        ).choices[0].message.content

        await update.message.reply_text(response)
        await add_to_memory(user_id, user_input, response)

    except Exception as e:
        await update.message.reply_text(f"❌ 出錯了：{str(e)}")
        logger.error(f"訊息處理錯誤：{e}")

# --- 處理文件 ---
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    try:
        file = await context.bot.get_file(update.message.document.file_id)
        file_bytes = requests.get(file.file_path).content
        file_name = update.message.document.file_name

        text = ""
        if file_name.endswith(".pdf"):
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif file_name.endswith(".docx"):
            doc = docx.Document(BytesIO(file_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif file_name.endswith(".txt"):
            text = file_bytes.decode("utf-8")
        else:
            await update.message.reply_text("抱歉，目前只支援 PDF、Word、TXT 文件。")
            return

        if not text.strip():
            await update.message.reply_text("文件內容為空或無法讀取 🤔")
            return

        analysis_prompt = f"請分析這個文件內容，並提供重點摘要和可執行建議：\n\n{text[:3000]}"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        ).choices[0].message.content

        await update.message.reply_text(response)
        await add_to_memory(user_id, f"[文件: {file_name}]", response, message_type='document')

    except Exception as e:
        error_msg = f"❌ 文件處理失敗：{str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(f"文件處理錯誤：{e}")

# --- 啟動小宸光Bot ---
async def main():
    """主啟動函式"""
    try:
        logger.info("🌟 小宸光靈魂啟動中...")
        
        # 建立 Application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # 添加處理器
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        
        # 根據環境選擇啟動模式
        port = int(os.environ.get("PORT", 8000))
        
        if WEBHOOK_URL:
            # Railway 生產環境：使用 webhook
            logger.info(f"🌐 使用 Webhook 模式在 Port {port}")
            await app.bot.set_webhook(
                url=f"{WEBHOOK_URL}/webhook",
                allowed_updates=["message"]
            )
            
            # 啟動 webhook 服務器
            await app.start()
            await app.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path="/webhook",
                webhook_url=f"{WEBHOOK_URL}/webhook"
            )
        else:
            # 本地開發環境：使用 polling
            logger.info("🔄 使用 Polling 模式（本地開發）")
            await app.run_polling()
            
    except Exception as e:
        logger.error(f"❌ 小宸光啟動失敗：{e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
