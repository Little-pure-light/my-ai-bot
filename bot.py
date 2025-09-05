import os
import json
from datetime import datetime
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI, APIError
from supabase import create_client, Client
from dotenv import load_dotenv
import sentry_sdk  # 新增這行


# 載入環境變量
load_dotenv()
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=0.1,
        environment="production"
    )
    print("✅ Sentry 錯誤追蹤已啟用")
else:
    print("⚠️ Sentry DSN 未設定，跳過錯誤追蹤")

# 您現有的代碼繼續...

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
            print(f"載入個性失敗: {e}")

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
            print(f"保存個性失敗: {e}")

    def update_trait(self, trait, delta):
        """更新個性特質"""
        current = self.personality_traits.get(trait, 0.5)
        self.personality_traits[trait] = max(0, min(1, current + delta))
        self.save_personality()

    def learn_from_interaction(self, user_msg, bot_response):
        """從互動中學習"""
        # 偵測知識領域
        domains = self._detect_knowledge_domains(user_msg)
        for domain in domains:
            self.knowledge_domains[domain] = self.knowledge_domains.get(domain, 0) + 0.1

        # 情感分析
        sentiment = self._analyze_sentiment(user_msg)
        if sentiment == "positive":
            self.update_trait("empathy", 0.1)
            self.emotional_profile["positive_interactions"] += 1
        elif sentiment == "negative":
            self.update_trait("empathy", -0.1)
            self.emotional_profile["negative_interactions"] += 1
        
        # 幽默與好奇心
        if self._detect_humor(user_msg):
            self.update_trait("humor", 0.1)
            self.update_trait("curiosity", 0.1)

        self.save_personality()

    def _detect_knowledge_domains(self, text):
        """偵測知識領域"""
        domains = {
            "technology": ["程式", "python", "ai", "機器學習"],
            "personal_growth": ["學習", "成長", "進步"],
            "emotions": ["感受", "心情", "感覺"],
            "hobbies": ["興趣", "喜歡", "愛好"]
        }
        
        found_domains = []
        for domain, keywords in domains.items():
            if any(keyword in text.lower() for keyword in keywords):
                found_domains.append(domain)
        
        return found_domains

    def _analyze_sentiment(self, text):
        """簡單情感分析"""
        positive_words = ["好", "棒", "讚", "開心", "感謝"]
        negative_words = ["難過", "不好", "生氣", "討厭"]
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in positive_words):
            return "positive"
        elif any(word in text_lower for word in negative_words):
            return "negative"
        return "neutral"

    def _detect_humor(self, text):
        """偵測幽默互動"""
        humor_keywords = ['哈哈', '笑', '好玩', '有趣', 'XD']
        return any(keyword in text.lower() for keyword in humor_keywords)

    def generate_dynamic_prompt(self):
        """根據當前個性生成動態Prompt"""
        traits_summary = "\n".join([
            f"{k.capitalize()}: {'高' if v > 0.7 else '中' if v > 0.3 else '低'}"
            for k, v in self.personality_traits.items()
        ])
        
        knowledge_summary = "\n".join([
            f"{k.capitalize()}: {'深' if v > 0.7 else '中' if v > 0.3 else '淺'}"
            for k, v in self.knowledge_domains.items()
        ])
        
        return f"""你是小宸光，以下是你當前的個性特點：

個性特質：
{traits_summary}

知識領域：
{knowledge_summary}

回覆原則：
- 根據上述特點調整回覆風格
- 保持溫柔、精準的溝通方式
- 展現你獨特的個性特徵
"""

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
        print(f"✅ 成功將 {memory_type} 記憶儲存到 Supabase！")
    except Exception as e:
        print(f"❌ 記憶儲存失敗：{e}")

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

    except Exception as e:
        sentry_sdk.capture_exception(e)
        error_msg = f"哈尼～系統遇到小問題：{str(e)} 💛"
        await update.message.reply_text(error_msg)
        print(f"❌ 處理訊息錯誤：{e}")

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
        sentry_sdk.capture_exception(e)
        print(f"❌ 回溯記憶時發生錯誤：{e}")
        return ""

def main():
    try:
        print("🌟 小宸光智能系統啟動中...")
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT, handle_message))
        
        print("✨ 智能成長系統已就緒")
        app.run_polling()
        
    except Exception as e:
        sentry_sdk.capture_exception(e) 
        print(f"❌ 啟動失敗：{e}")

if __name__ == "__main__":
    main()
