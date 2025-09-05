import os
import json
from datetime import datetime
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI, APIError
from supabase import create_client, Client
from dotenv import load_dotenv
import sentry_sdk

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 載入環境變量
load_dotenv()

# Sentry 初始化
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=0.1,
        environment="production"
    )
    logger.info("✅ Sentry 錯誤追蹤已啟用")
else:
    logger.warning("⚠️ Sentry DSN 未設定，跳過錯誤追蹤")

# API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MEMORIES_TABLE = os.getenv("SUPABASE_MEMORIES_TABLE", "xiaochenguang_memories")

# 初始化客戶端
client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class PersonalityEngine:
    def __init__(self, user_id):
        self.user_id = user_id
        self.personality_traits = {
            "curiosity": 0.5,
            "empathy": 0.5,
            "humor": 0.5,
            "technical_depth": 0.5
        }
        self.knowledge_domains = {}
        self.emotional_profile = {
            "positive_interactions": 0,
            "negative_interactions": 0,
            "neutral_interactions": 0
        }
        self.load_personality()

    def load_personality(self):
        """從Supabase載入個性記憶"""
        try:
            result = supabase.table(MEMORIES_TABLE)\
                .select("*")\
                .eq("conversation_id", self.user_id)\
                .eq("memory_type", "personality")\
                .execute()
            
            if result.data:
                personality_data = json.loads(result.data[0].get('document_content', '{}'))
                self.personality_traits = personality_data.get('traits', self.personality_traits)
                self.knowledge_domains = personality_data.get('knowledge', {})
                self.emotional_profile = personality_data.get('emotions', self.emotional_profile)
        except Exception as e:
            logger.error(f"載入個性失敗: {e}")
            sentry_sdk.capture_exception(e)

    def save_personality(self):
        """將個性存儲到Supabase"""
        try:
            personality_data = {
                "traits": self.personality_traits,
                "knowledge": self.knowledge_domains,
                "emotions": self.emotional_profile
            }
            
            supabase.table(MEMORIES_TABLE).upsert({
                "conversation_id": self.user_id,
                "memory_type": "personality",
                "document_content": json.dumps(personality_data),
                "user_message": "Personality Profile",
                "assistant_message": "Dynamic AI Personality"
            }).execute()
        except Exception as e:
            logger.error(f"保存個性失敗: {e}")
            sentry_sdk.capture_exception(e)

    # [其餘 PersonalityEngine 方法保持不變]

async def add_to_memory(
    user_id, 
    user_message, 
    bot_response, 
    memory_type='daily', 
    message_type=None, 
    additional_data=None
):
    """Enhanced memory storage"""
    try:
        data_to_insert = {
            "conversation_id": str(user_id),
            "user_message": user_message,
            "assistant_message": bot_response,
            "memory_type": memory_type,
            "message_type": message_type,
            "platform": 'telegram',
            "document_content": json.dumps(additional_data) if additional_data else None
        }
        
        supabase.table(MEMORIES_TABLE).insert(data_to_insert).execute()
        logger.info(f"✅ 成功將 {memory_type} 記憶儲存到 Supabase！")
    except Exception as e:
        logger.error(f"❌ 記憶儲存失敗：{e}")
        sentry_sdk.capture_exception(e)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.first_name

    # 初始化個性引擎
    personality_engine = PersonalityEngine(user_id)

    try:
        # 獲取對話歷史
        conversation_history = get_conversation_history(user_id)
        
        # 生成動態個性Prompt
        dynamic_personality = personality_engine.generate_dynamic_prompt()

        # 構建消息
        messages = [
            {"role": "system", "content": dynamic_personality},
            {"role": "user", "content": user_input}
        ]

        # 調用OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        ).choices[0].message.content

        # 回覆用戶
        await update.message.reply_text(response)

        # 儲存記憶
        await add_to_memory(user_id, user_input, response)
        
        # 學習成長
        personality_engine.learn_from_interaction(user_input, response)

    except APIError as api_error:
        logger.error(f"OpenAI API 錯誤: {api_error}")
        sentry_sdk.capture_exception(api_error)
        error_msg = f"哈尼～AI服務遇到小問題：{str(api_error)} 💛"
        await update.message.reply_text(error_msg)
    except Exception as e:
        logger.error(f"處理訊息錯誤：{e}")
        sentry_sdk.capture_exception(e)
        error_msg = f"哈尼～系統遇到小問題：{str(e)} 💛"
        await update.message.reply_text(error_msg)

def get_conversation_history(user_id: str, limit: int = 10):
    """獲取最近對話歷史"""
    try:
        response = supabase.table(MEMORIES_TABLE)\
            .select("*")\
            .eq("conversation_id", user_id)\
            .eq("memory_type", "daily")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        history = response.data
        formatted_history = []
        for turn in reversed(history):
            if turn.get("user_message"):
                formatted_history.append(f"User: {turn['user_message']}")
            if turn.get("assistant_message"):
                formatted_history.append(f"Bot: {turn['assistant_message']}")
        
        return "\n".join(formatted_history)
    except Exception as e:
        logger.error(f"回溯記憶時發生錯誤：{e}")
        sentry_sdk.capture_exception(e)
        return ""

def main():
    try:
        logger.info("🌟 小宸光智能系統啟動中...")
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT, handle_message))
        
        logger.info("✨ 智能成長系統已就緒")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ 啟動失敗：{e}")
        sentry_sdk.capture_exception(e)

if __name__ == "__main__":
    main()
