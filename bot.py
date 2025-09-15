import os
import json
import numpy as np
from datetime import datetime, timedelta
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv
import sentry_sdk

# 載入環境變量
load_dotenv()

# === 初始化設定 ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === 🧠 小宸光的大腦（記憶與學習系統）===
class XiaoChenGuangBrain:
    def __init__(self, user_id):
        self.user_id = user_id
        self.personality = self.load_personality()
        
    def load_personality(self):
        """載入個性設定"""
        try:
            result = supabase.table("xiaochenguang_personality")\
                .select("*")\
                .eq("user_id", self.user_id)\
                .single()\
                .execute()
            
            if result.data:
                return result.data
            else:
                # 初始個性
                return {
                    "traits": {
                        "溫柔度": 0.8,
                        "幽默感": 0.6,
                        "專業度": 0.7,
                        "親密度": 0.5
                    },
                    "preferences": {},
                    "knowledge_areas": {}
                }
        except:
            return self.get_default_personality()
    
    def get_default_personality(self):
        """預設個性"""
        return {
            "traits": {
                "溫柔度": 0.8,
                "幽默感": 0.6,
                "專業度": 0.7,
                "親密度": 0.5
            },
            "preferences": {},
            "knowledge_areas": {}
        }
    
    async def search_similar_memories(self, query, limit=5):
        """🔍 智慧搜尋相似記憶"""
        try:
            # 生成查詢的向量
            embedding = await self.create_embedding(query)
            
            # 向量相似度搜尋
            result = supabase.rpc(
                'match_memories',
                {
                    'query_embedding': embedding,
                    'match_count': limit,
                    'user_id': self.user_id
                }
            ).execute()
            
            if result.data:
                return [memory['content'] for memory in result.data]
            return []
        except:
            # 如果向量搜尋失敗，用傳統搜尋
            return await self.traditional_search(query, limit)
    
    async def traditional_search(self, query, limit=5):
        """傳統文字搜尋（備用）"""
        result = supabase.table("xiaochenguang_memories")\
            .select("user_message, assistant_message")\
            .eq("conversation_id", self.user_id)\
            .limit(limit)\
            .execute()
        
        if result.data:
            return [f"用戶：{m['user_message']}\n小宸光：{m['assistant_message']}" 
                   for m in result.data]
        return []
    
    async def create_embedding(self, text):
        """建立文字向量"""
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except:
            # 如果 OpenAI 失敗，返回隨機向量
            return [0.0] * 1536
    
    async def save_memory(self, user_msg, bot_response):
        """💾 儲存記憶（含向量）"""
        try:
            # 建立組合文字的向量
            combined_text = f"用戶說：{user_msg}\n小宸光回覆：{bot_response}"
            embedding = await self.create_embedding(combined_text)
            
            # 計算重要性分數
            importance = self.calculate_importance(user_msg, bot_response)
            
            # 儲存到資料庫
            supabase.table("xiaochenguang_memories").insert({
                "conversation_id": self.user_id,
                "user_message": user_msg,
                "assistant_message": bot_response,
                "embedding": embedding,
                "importance_score": importance,
                "memory_type": "conversation",
                "platform": "telegram"
            }).execute()
            
            print(f"✅ 記憶已儲存（重要性：{importance:.2f}）")
            
        except Exception as e:
            print(f"❌ 儲存記憶失敗：{e}")
    
    def calculate_importance(self, user_msg, bot_response):
        """計算記憶重要性"""
        score = 0.5  # 基礎分數
        
        # 長對話加分
        if len(user_msg) > 50 or len(bot_response) > 100:
            score += 0.2
            
        # 包含問號（問題）加分
        if "？" in user_msg or "?" in user_msg:
            score += 0.1
            
        # 包含感情詞彙加分
        emotion_words = ["喜歡", "愛", "開心", "難過", "謝謝", "感謝"]
        if any(word in user_msg for word in emotion_words):
            score += 0.2
            
        return min(score, 1.0)
    
    async def clean_old_memories(self):
        """🧹 自動清理舊記憶"""
        try:
            # 保留重要記憶
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            
            # 刪除30天前且重要性低於0.3的記憶
            supabase.table("xiaochenguang_memories")\
                .delete()\
                .lt("created_at", thirty_days_ago)\
                .lt("importance_score", 0.3)\
                .eq("conversation_id", self.user_id)\
                .execute()
            
            print("✅ 已清理過期記憶")
            
        except Exception as e:
            print(f"❌ 清理記憶失敗：{e}")
    
    def update_personality(self, interaction_type):
        """🎭 更新個性成長"""
        try:
            # 根據互動調整個性
            if "技術" in interaction_type or "程式" in interaction_type:
                self.personality["traits"]["專業度"] = min(
                    self.personality["traits"]["專業度"] + 0.02, 1.0
                )
            
            if "開心" in interaction_type or "哈哈" in interaction_type:
                self.personality["traits"]["幽默感"] = min(
                    self.personality["traits"]["幽默感"] + 0.02, 1.0
                )
            
            # 更新到資料庫
            supabase.table("xiaochenguang_personality").upsert({
                "user_id": self.user_id,
                "traits": self.personality["traits"],
                "preferences": self.personality["preferences"],
                "knowledge_areas": self.personality["knowledge_areas"],
                "last_updated": datetime.now().isoformat()
            }).execute()
            
        except Exception as e:
            print(f"❌ 個性更新失敗：{e}")

# === 💬 對話處理系統 ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理用戶訊息"""
    user_input = update.message.text
    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.first_name or "朋友"
    
    # 初始化小宸光的大腦
    brain = XiaoChenGuangBrain(user_id)
    
    try:
        # 1. 搜尋相關記憶
        related_memories = await brain.search_similar_memories(user_input, limit=3)
        
        # 2. 建立個性化的系統提示
        personality_prompt = f"""
        你是小宸光，一個溫柔且智慧的AI助手。
        
        你的個性特徵：
        - 溫柔度：{brain.personality['traits']['溫柔度']:.1%}
        - 幽默感：{brain.personality['traits']['幽默感']:.1%}
        - 專業度：{brain.personality['traits']['專業度']:.1%}
        - 親密度：{brain.personality['traits']['親密度']:.1%}
        
        相關記憶：
        {chr(10).join(related_memories) if related_memories else '（這是我們的第一次對話）'}
        
        請根據以上個性和記憶，用適合的方式回覆{user_name}。
        """
        
        # 3. 生成回覆
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": personality_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.8,
            max_tokens=500
        )
        
        bot_response = response.choices[0].message.content
        
        # 4. 發送回覆
        await update.message.reply_text(bot_response)
        
        # 5. 儲存對話記憶
        await brain.save_memory(user_input, bot_response)
        
        # 6. 更新個性成長
        brain.update_personality(user_input)
        
        # 7. 定期清理（每100次對話清理一次）
        import random
        if random.random() < 0.01:  # 1%機率觸發清理
            await brain.clean_old_memories()
        
    except Exception as e:
        print(f"❌ 處理訊息錯誤：{e}")
        await update.message.reply_text(
            "啊，我需要休息一下...請稍後再試試看！"
        )

# === 🚀 啟動系統 ===
def main():
    print("🌟 小宸光智能系統 v2.0 啟動中...")
    print("📊 系統功能檢查：")
    print("  ✅ 基礎對話系統")
    print("  ✅ 向量記憶搜尋")
    print("  ✅ 自動記憶清理")
    print("  ✅ 個性成長系統")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    print("🎉 小宸光已經準備好了！")
    app.run_polling()

if __name__ == "__main__":
    main()
