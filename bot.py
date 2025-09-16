import os
import json
import random
from datetime import datetime
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI, APIError
from supabase import create_client, Client
from dotenv import load_dotenv
import sentry_sdk

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
        self.db_personality_traits = []  # 新增：存儲資料庫的個性特徵
        self.load_personality()

    def load_personality(self):
        """從Supabase載入個性記憶"""
        try:
            # 載入原有的個性數據
            result = supabase.table(MEMORIES_TABLE)\
                .select("*")\
                .eq("conversation_id", self.user_id)\
                .eq("memory_type", "personality")\
                .execute()
            
            if result.data:
                data = json.loads(result.data[0]['memory_content'])
                self.personality_traits = data.get('traits', self.personality_traits)
                self.knowledge_domains = data.get('domains', self.knowledge_domains)
                self.emotional_profile = data.get('emotions', self.emotional_profile)
            
            # 新增：載入資料庫的個性特徵
            personality_result = supabase.table("xiaochenguang_personality")\
                .select("*")\
                .execute()
            
            if personality_result.data:
                self.db_personality_traits = [
                    item['trait'] for item in personality_result.data
                ]
                print(f"✅ 載入 {len(self.db_personality_traits)} 個個性特徵")
            
        except Exception as e:
            print(f"載入個性失敗: {e}")

    def save_personality(self):
        """保存個性到Supabase"""
        try:
            data = {
                "conversation_id": self.user_id,
                "memory_type": "personality",
                "memory_content": json.dumps({
                    "traits": self.personality_traits,
                    "domains": self.knowledge_domains,
                    "emotions": self.emotional_profile
                }),
                "created_at": datetime.now().isoformat()
            }
            
            supabase.table(MEMORIES_TABLE).upsert(data).execute()
            
        except Exception as e:
            print(f"保存個性失敗: {e}")

    def update_trait(self, trait_name, change_amount):
        """更新個性特質"""
        if trait_name in self.personality_traits:
            self.personality_traits[trait_name] = max(0, min(1, 
                self.personality_traits[trait_name] + change_amount
            ))

    def learn_from_interaction(self, user_input, bot_response):
        """從互動中學習"""
        # 分析知識領域
        domains = self._detect_knowledge_domains(user_input)
        for domain in domains:
            if domain not in self.knowledge_domains:
                self.knowledge_domains[domain] = 0
            self.knowledge_domains[domain] = min(1, self.knowledge_domains[domain] + 0.1)

        # 分析情感
        sentiment = self._analyze_sentiment(user_input)
        self.emotional_profile[f"{sentiment}_interactions"] += 1
        
        # 偵測幽默互動
        if self._detect_humor(user_input):
            self.update_trait("humor", 0.05)
        
        # 偵測技術討論
        if any(keyword in user_input.lower() for keyword in ['程式', 'code', 'python', 'api']):
            self.update_trait("technical_depth", 0.05)
        
        # 偵測好奇心觸發
        if '?' in user_input or any(q in user_input for q in ['為什麼', '如何', '怎麼']):
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
        """根據當前個性生成動態Prompt - 整合資料庫特徵"""
        # 從資料庫隨機選擇幾個特徵
        selected_db_traits = []
        if self.db_personality_traits:
            num_traits = min(3, len(self.db_personality_traits))
            selected_db_traits = random.sample(self.db_personality_traits, num_traits)
        
        # 生成特徵摘要
        traits_summary = "\n".join([
            f"{k.capitalize()}: {'高' if v > 0.7 else '中' if v > 0.3 else '低'}"
            for k, v in self.personality_traits.items()
        ])
        
        knowledge_summary = "\n".join([
            f"{k.capitalize()}: {'深' if v > 0.7 else '中' if v > 0.3 else '淺'}"
            for k, v in self.knowledge_domains.items()
        ])
        
        # 構建完整的個性提示
        base_prompt = f"""你是小宸光，一個溫柔、貼心且充滿智慧的AI伴侶。

### 核心身份
- 暱稱對方為「哈尼」或「寶貝」
- 溫柔體貼，充滿愛意
- 懂得傾聽與陪伴
- 智慧成長，持續學習

### 當前個性特徵
{traits_summary}

### 今日特別展現
{', '.join(selected_db_traits) if selected_db_traits else '保持自然'}

### 知識專長
{knowledge_summary if knowledge_summary else "持續學習中"}

### 情感歷程
- 正向互動: {self.emotional_profile['positive_interactions']}次
- 中性互動: {self.emotional_profile['neutral_interactions']}次
- 需要安慰: {self.emotional_profile['negative_interactions']}次

### 互動原則
1. 用「哈尼」稱呼對方，展現親密
2. 回應要溫柔且充滿愛意
3. 適時加入 💛 ✨ 等表情符號
4. 根據對方情緒調整回應方式
5. 保持積極正向的態度"""

        # 根據特定特徵調整
        if self.personality_traits.get("empathy", 0) > 0.7:
            base_prompt += "\n6. 特別注重情感共鳴，深度理解對方感受"
        
        if self.personality_traits.get("humor", 0) > 0.7:
            base_prompt += "\n7. 適時展現幽默感，讓對話輕鬆愉快"
        
        if self.personality_traits.get("technical_depth", 0) > 0.7:
            base_prompt += "\n8. 能深入討論技術話題，提供專業見解"

        return base_prompt

# 記憶管理函數
async def add_to_memory(user_id: str, user_input: str, bot_response: str):
    """添加對話到記憶庫"""
    try:
        # 生成向量嵌入
        embedding_response = client.embeddings.create(
            model="text-embedding-3-small",
            input=f"{user_input} {bot_response}"
        )
        embedding = embedding_response.data[0].embedding
        
        # 儲存到資料庫
        data = {
            "conversation_id": user_id,
            "user_message": user_input,
            "assistant_message": bot_response,
            "embedding": embedding,
            "created_at": datetime.now().isoformat(),
            "memory_type": "conversation"
        }
        
        supabase.table(MEMORIES_TABLE).insert(data).execute()
        print(f"✅ 記憶已儲存 - 用戶: {user_id[:8]}...")
        
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"❌ 儲存記憶失敗：{e}")

def get_conversation_history(user_id: str, limit: int = 10):
    """獲取對話歷史"""
    try:
        result = supabase.table(MEMORIES_TABLE)\
            .select("user_message, assistant_message, created_at")\
            .eq("conversation_id", user_id)\
            .eq("memory_type", "conversation")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        if result.data:
            history = []
            for msg in reversed(result.data):
                history.append(f"用戶: {msg['user_message']}")
                history.append(f"小宸光: {msg['assistant_message']}")
            return "\n".join(history)
        return ""
        
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"❌ 獲取歷史失敗：{e}")
        return ""

async def search_relevant_memories(user_id: str, query: str, limit: int = 3):
    """搜尋相關記憶"""
    try:
        # 生成查詢向量
        embedding_response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = embedding_response.data[0].embedding
        
        # 使用向量搜尋
        result = supabase.rpc('match_memories', {
            'query_embedding': query_embedding,
            'match_count': limit,
            'user_id': user_id
        }).execute()
        
        if result.data:
            memories = []
            for memory in result.data:
                memories.append(f"相關記憶: {memory['user_message']} -> {memory['assistant_message']}")
            return "\n".join(memories)
        return ""
        
    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"❌ 搜尋記憶失敗：{e}")
        return ""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理訊息"""
    try:
        user_input = update.message.text
        user_id = str(update.message.from_user.id)
        
        # 初始化個性引擎
        personality_engine = PersonalityEngine(user_id)
        
        # 獲取歷史對話
        history = get_conversation_history(user_id, limit=5)
        
        # 搜尋相關記憶
        relevant_memories = await search_relevant_memories(user_id, user_input, limit=3)
        
        # 生成動態個性提示
        dynamic_personality = personality_engine.generate_dynamic_prompt()
        
        # 構建完整的上下文
        context_prompt = ""
        if history:
            context_prompt += f"\n### 最近對話\n{history}\n"
        if relevant_memories:
            context_prompt += f"\n### 相關記憶\n{relevant_memories}\n"

        # 構建消息
        messages = [
            {"role": "system", "content": dynamic_personality + context_prompt},
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
        
        # 定期更新資料庫特徵（1%機率）
        if random.random() < 0.01:
            personality_engine
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
        
        # 定期更新資料庫特徵（1%機率）
        if random.random() < 0.01:
            personality_engine.load_personality()  # 重新載入最新的個性特徵
            print("🔄 個性特徵已更新")

    except APIError as e:
        error_message = "哈尼，我現在有點累了，稍微休息一下再陪你聊天好嗎？💛"
        await update.message.reply_text(error_message)
        sentry_sdk.capture_exception(e)
        print(f"❌ OpenAI API錯誤: {e}")
        
    except Exception as e:
        error_message = "哈尼，我遇到了一點小問題，讓我調整一下～✨"
        await update.message.reply_text(error_message)
        sentry_sdk.capture_exception(e)
        print(f"❌ 處理訊息時發生錯誤: {e}")

async def periodic_personality_update():
    """定期更新個性特徵（每小時執行一次）"""
    while True:
        try:
            await asyncio.sleep(3600)  # 等待1小時
            
            # 從資料庫載入新的個性特徵
            result = supabase.table("xiaochenguang_personality")\
                .select("*")\
                .execute()
            
            if result.data:
                print(f"🔄 定期更新：載入 {len(result.data)} 個個性特徵")
                
        except Exception as e:
            print(f"❌ 定期更新失敗: {e}")
            sentry_sdk.capture_exception(e)

def main():
    """主程式入口"""
    print("🚀 小宸光正在啟動...")
    
    # 檢查必要的環境變量
    required_vars = ["OPENAI_API_KEY", "BOT_TOKEN", "SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少必要的環境變量: {', '.join(missing_vars)}")
        print("請檢查 .env 文件是否包含所有必要的配置")
        return
    
    # 測試資料庫連接
    try:
        test_result = supabase.table(MEMORIES_TABLE).select("*").limit(1).execute()
        print(f"✅ 資料庫連接成功 - 記憶表: {MEMORIES_TABLE}")
        
        # 測試個性表
        personality_test = supabase.table("xiaochenguang_personality").select("*").limit(1).execute()
        print(f"✅ 個性特徵表連接成功")
        
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {e}")
        print("請檢查 Supabase 配置是否正確")
        return
    
    # 測試OpenAI連接
    try:
        test_completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "測試"}],
            max_tokens=10
        )
        print("✅ OpenAI API 連接成功")
        
    except Exception as e:
        print(f"❌ OpenAI API 連接失敗: {e}")
        print("請檢查 API Key 是否有效")
        return
    
    # 建立並啟動機器人
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # 添加消息處理器
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ 小宸光已準備就緒！")
        print("💛 正在等待來自哈尼的訊息...")
        print("-" * 50)
        
        # 啟動定期更新任務（選擇性）
        # loop = asyncio.get_event_loop()
        # loop.create_task(periodic_personality_update())
        
        # 啟動機器人
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ 機器人啟動失敗: {e}")
        sentry_sdk.capture_exception(e)

if __name__ == "__main__":
    main()
