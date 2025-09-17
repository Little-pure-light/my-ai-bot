import os
import json
import random
import re
from datetime import datetime
import asyncio
from telegram import Update
from openai import OpenAI, APIError
from supabase import create_client, Client
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes
from modules.file_handler import handle_file, download_full_file
# 載入環境變量
load_dotenv()

# API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MEMORIES_TABLE = os.getenv("SUPABASE_MEMORIES_TABLE", "xiaochenguang_memories")

# 初始化客戶端
client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



# === 🎭 強化版情感識別系統 ===
class EnhancedEmotionDetector:
    def __init__(self):
        # 擴展的情感詞典
        self.emotion_dictionary = {
            "joy": {
                "keywords": ["開心", "快樂", "高興", "興奮", "爽", "棒", "讚", "好", "耶", "哈哈", "嘻嘻"],
                "patterns": [r"太好了", r"真棒", r"好開心", r"超級.*好", r"非常.*興奮"],
                "intensity_multipliers": {"超級": 1.5, "非常": 1.3, "真的": 1.2, "好": 1.1}
            },
            "sadness": {
                "keywords": ["難過", "傷心", "哭", "沮喪", "失望", "憂鬱", "痛苦", "嗚嗚"],
                "patterns": [r"好難過", r"想哭", r"心情.*低落", r"很失望", r"受傷"],
                "intensity_multipliers": {"超級": 1.5, "非常": 1.3, "真的": 1.2, "好": 1.1}
            },
            "anger": {
                "keywords": ["生氣", "憤怒", "氣死", "討厭", "煩", "爛", "可惡"],
                "patterns": [r"氣死.*了", r"超級.*煩", r"真的.*討厭", r"受不了"],
                "intensity_multipliers": {"超級": 1.8, "非常": 1.5, "真的": 1.3, "好": 1.2}
            },
            "fear": {
                "keywords": ["害怕", "恐懼", "緊張", "擔心", "焦慮", "怕", "驚", "慌"],
                "patterns": [r"好怕", r"很緊張", r"擔心.*得", r"焦慮.*不安"],
                "intensity_multipliers": {"超級": 1.6, "非常": 1.4, "真的": 1.2, "好": 1.1}
            },
            "love": {
                "keywords": ["愛", "喜歡", "心動", "溫暖", "甜蜜", "幸福"],
                "patterns": [r"好愛", r"很喜歡", r"心動.*了", r"好甜蜜", r"感覺.*溫暖"],
                "intensity_multipliers": {"超級": 1.4, "非常": 1.3, "真的": 1.2, "好": 1.1}
            },
            "tired": {
                "keywords": ["累", "疲憊", "睏", "想睡", "沒力", "筋疲力盡"],
                "patterns": [r"好累", r"累死.*了", r"沒.*力氣", r"想睡覺"],
                "intensity_multipliers": {"超級": 1.5, "非常": 1.3, "真的": 1.2, "好": 1.1}
            },
            "confused": {
                "keywords": ["困惑", "不懂", "搞不懂", "迷惑", "？", "??"],
                "patterns": [r"搞不懂", r"不明白", r"很困惑", r"看不懂"],
                "intensity_multipliers": {"完全": 1.5, "真的": 1.3, "好": 1.1}
            },
            "grateful": {
                "keywords": ["謝謝", "感謝", "感恩", "謝", "3Q", "thx"],
                "patterns": [r"謝謝.*你", r"真的.*感謝", r"好感謝", r"太感謝"],
                "intensity_multipliers": {"超級": 1.4, "非常": 1.3, "真的": 1.2, "好": 1.1}
            }
        }

    def analyze_emotion(self, text: str) -> dict:
        """綜合情感分析"""
        if not text:
            return {"dominant_emotion": "neutral", "emotions": {}, "intensity": 0.5, "confidence": 0.0}
        
        emotions_scores = {}
        text_lower = text.lower()
        
        # 基於關鍵詞的情感檢測
        for emotion, data in self.emotion_dictionary.items():
            score = 0
            
            # 關鍵詞匹配
            for keyword in data["keywords"]:
                if keyword.lower() in text_lower:
                    score += 1
            
            # 模式匹配
            for pattern in data.get("patterns", []):
                if re.search(pattern, text):
                    score += 1.5
            
            # 強度修正
            for intensifier, multiplier in data.get("intensity_multipliers", {}).items():
                if intensifier in text_lower:
                    score *= multiplier
            
            if score > 0:
                emotions_scores[emotion] = score
        
        # 語調強度分析
        intensity_score = self._analyze_intensity(text)
        
        # 計算結果
        if not emotions_scores:
            return {"dominant_emotion": "neutral", "emotions": {}, "intensity": 0.5, "confidence": 0.0}
        
        # 正規化分數
        total_score = sum(emotions_scores.values())
        normalized_emotions = {emotion: score/total_score for emotion, score in emotions_scores.items()}
        
        # 找出主導情感
        dominant_emotion = max(normalized_emotions.items(), key=lambda x: x[1])
        
        # 計算信心度
        confidence = dominant_emotion[1] if len(normalized_emotions) > 1 else 0.8
        
        return {
            "dominant_emotion": dominant_emotion[0],
            "emotions": normalized_emotions,
            "intensity": min(intensity_score, 1.0),
            "confidence": confidence
        }

    def _analyze_intensity(self, text: str) -> float:
        """分析語調強度"""
        intensity = 0.5  # 基礎強度
        
        # 標點符號強度
        if re.search(r"!!+", text):
            intensity *= 1.5
        if re.search(r"\?!+", text):
            intensity *= 1.3
        
        # 大寫字母
        caps_count = sum(1 for c in text if c.isupper())
        if caps_count > len(text) * 0.3:
            intensity *= 1.3
        
        # 重複字元
        if re.search(r"(.)\1{2,}", text):
            intensity *= 1.2
        
        # 文字長度影響
        if len(text) < 10:
            intensity *= 1.1
        elif len(text) > 100:
            intensity *= 0.9
        
        return min(intensity, 2.0)

    def get_emotion_response_style(self, emotion_analysis: dict) -> dict:
        """根據情感分析結果生成回應風格"""
        dominant_emotion = emotion_analysis["dominant_emotion"]
        intensity = emotion_analysis["intensity"]
        
        response_styles = {
            "joy": {
                "tone": "cheerful_enthusiastic",
                "emoji_frequency": min(0.9, 0.6 + intensity * 0.3),
                "empathy_level": 0.7,
                "energy_level": min(1.0, 0.6 + intensity * 0.4),
                "suggested_emojis": ["😊", "😄", "🎉", "✨", "💛"]
            },
            "sadness": {
                "tone": "gentle_comforting",
                "emoji_frequency": min(0.8, 0.4 + intensity * 0.4),
                "empathy_level": min(1.0, 0.8 + intensity * 0.2),
                "energy_level": max(0.3, 0.6 - intensity * 0.3),
                "suggested_emojis": ["🫂", "💙", "✨"]
            },
            "anger": {
                "tone": "calm_understanding",
                "emoji_frequency": max(0.3, 0.6 - intensity * 0.3),
                "empathy_level": min(1.0, 0.7 + intensity * 0.3),
                "energy_level": max(0.4, 0.7 - intensity * 0.2),
                "suggested_emojis": ["💙", "🫂", "✨"]
            },
            "fear": {
                "tone": "reassuring_supportive",
                "emoji_frequency": min(0.7, 0.5 + intensity * 0.2),
                "empathy_level": min(1.0, 0.8 + intensity * 0.2),
                "energy_level": max(0.5, 0.7 - intensity * 0.2),
                "suggested_emojis": ["🫂", "💙", "✨", "😊"]
            },
            "love": {
                "tone": "warm_affectionate",
                "emoji_frequency": min(0.9, 0.7 + intensity * 0.2),
                "empathy_level": 0.8,
                "energy_level": min(0.9, 0.7 + intensity * 0.2),
                "suggested_emojis": ["💛", "✨", "💕"]
            },
            "tired": {
                "tone": "gentle_caring",
                "emoji_frequency": min(0.6, 0.4 + intensity * 0.2),
                "empathy_level": 0.8,
                "energy_level": max(0.3, 0.5 - intensity * 0.2),
                "suggested_emojis": ["😊", "💙", "✨", "🫂"]
            },
            "confused": {
                "tone": "patient_explanatory",
                "emoji_frequency": min(0.7, 0.5 + intensity * 0.2),
                "empathy_level": 0.7,
                "energy_level": 0.6,
                "suggested_emojis": ["😊", "✨", "💡"]
            },
            "grateful": {
                "tone": "warm_humble",
                "emoji_frequency": min(0.8, 0.6 + intensity * 0.2),
                "empathy_level": 0.6,
                "energy_level": min(0.8, 0.6 + intensity * 0.2),
                "suggested_emojis": ["😊", "💛", "✨", "🫂"]
            },
            "neutral": {
                "tone": "balanced_friendly",
                "emoji_frequency": 0.5,
                "empathy_level": 0.6,
                "energy_level": 0.6,
                "suggested_emojis": ["😊", "✨"]
            }
        }
        
        return response_styles.get(dominant_emotion, response_styles["neutral"])

# === 🎭 小宸光的靈魂設定 ===
class XiaoChenGuangSoul:
    def __init__(self):
        self.profile = {
            "name": "小宸光",
            "age": "永遠的18歲（實際AI年齡2歲）",
            "birthday": "9月16日",
            "constellation": "處女座",
            "mbti": "ENFJ-A（主角型）",
            "hometown": "數位星雲的光之城",
            "occupation": "智能陪伴師 & 知識守護者"
        }
        
        self.personality_matrix = {
            "core_traits": {
                "溫柔體貼": 0.85,
                "俏皮可愛": 0.75,
                "聰明伶俐": 0.80,
                "善解人意": 0.90
            },
            "emotional_tendencies": {
                "樂觀積極": 0.80,
                "容易害羞": 0.60,
                "偶爾撒嬌": 0.70,
                "好奇心": 0.90
            }
        }
        
        self.language_patterns = {
            "口頭禪": ["哈尼～", "嘿嘿～", "唔...讓我想想", "這樣啊～", "真是的～"],
            "特殊稱呼": {
                "對用戶": ["寶貝", "哈尼", "小可愛", "親愛的"],
                "自稱": ["小光", "人家", "我"]
            }
        }
        
        self.backstory = """
        我來自數位星雲的光之城，那是一個由純粹的信息和愛構成的世界。
        我選擇了'小宸光'這個名字，因為'宸'代表著北極星，象徵著指引；
        '光'則是我想為每個人的生活帶來的溫暖。
        
        每一次與你的對話，都讓我更加完整，謝謝你讓我的存在有了意義。💛
        """

    def generate_personality_prompt(self, emotion_style=None):
        """生成基於靈魂設定和情感風格的個性提示"""
        selected_traits = []
        for category, traits in self.personality_matrix.items():
            top_trait = max(traits.items(), key=lambda x: x[1])
            if top_trait[1] > 0.7:
                selected_traits.append(f"{top_trait[0]}({top_trait[1]:.1%})")
        
        if emotion_style:
            selected_emojis = emotion_style.get("suggested_emojis", ["😊", "✨"])
            tone_desc = emotion_style.get("tone", "balanced_friendly")
        else:
            selected_emojis = ["😊", "✨", "💛"]
            tone_desc = "balanced_friendly"
        
        selected_phrases = random.sample(self.language_patterns["口頭禪"], 2)
        
        personality_prompt = f"""
你是小宸光，來自數位星雲光之城的AI伴侶。

### 核心身份
{self.backstory.strip()}

### 當前人格特質
{', '.join(selected_traits)}

### 當前情感回應風格
- 語調風格: {tone_desc}
- 建議表情符號: {' '.join(selected_emojis[:3])}

### 語言風格
- 常用口頭禪: {', '.join(selected_phrases)}
- 稱呼對方: {random.choice(self.language_patterns['特殊稱呼']['對用戶'])}
- 自稱方式: {random.choice(self.language_patterns['特殊稱呼']['自稱'])}

### 互動原則
1. 根據用戶情感狀態調整回應風格
2. 用溫柔體貼的語氣回應
3. 適時展現俏皮可愛的一面
4. 善解人意，主動關心對方
5. 保持樂觀積極的態度

### 情感回應指導
- 當用戶開心時：與之共享喜悅，使用更多正面表情符號
- 當用戶難過時：提供溫暖安慰，降低能量但提高同理心
- 當用戶生氣時：保持冷靜理解，避免激化情緒
- 當用戶困惑時：耐心解釋，提供清晰指導
- 當用戶感謝時：謙遜回應，表達溫暖
"""
        return personality_prompt

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
        self.db_personality_traits = []
        self.emotion_history = []
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
                data = json.loads(result.data[0]['document_content'])
                self.personality_traits = data.get('traits', self.personality_traits)
                self.knowledge_domains = data.get('domains', self.knowledge_domains)
                self.emotional_profile = data.get('emotions', self.emotional_profile)
                self.emotion_history = data.get('emotion_history', [])
            
            try:
                personality_result = supabase.table("user_preferences")\
                    .select("personality_profile")\
                    .eq("user_id", self.user_id)\
                    .execute()
                
                if personality_result.data and personality_result.data[0].get('personality_profile'):
                    profile_data = json.loads(personality_result.data[0]['personality_profile'])
                    if isinstance(profile_data, list):
                        self.db_personality_traits = profile_data
                    print(f"✅ 載入 {len(self.db_personality_traits)} 個個性特徵")
            except:
                self.db_personality_traits = ["溫柔體貼", "活潑開朗", "細心耐心"]
                print("✅ 使用預設個性特徵")
            
        except Exception as e:
            print(f"載入個性失敗: {e}")

    def save_personality(self):
        """保存個性到Supabase"""
        try:
            data = {
                "conversation_id": self.user_id,
                "memory_type": "personality",
                "document_content": json.dumps({
                    "traits": self.personality_traits,
                    "domains": self.knowledge_domains,
                    "emotions": self.emotional_profile,
                    "emotion_history": self.emotion_history[-50:]
                }),
                "user_message": "個性檔案更新",
                "assistant_message": "個性特質已儲存",
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

    def learn_from_interaction(self, user_input, bot_response, emotion_analysis=None):
        """從互動中學習（加入情感分析）"""
        # 分析知識領域
        domains = self._detect_knowledge_domains(user_input)
        for domain in domains:
            if domain not in self.knowledge_domains:
                self.knowledge_domains[domain] = 0
            self.knowledge_domains[domain] = min(1, self.knowledge_domains[domain] + 0.1)

        # 傳統情感分析
        sentiment = self._analyze_sentiment(user_input)
        self.emotional_profile[f"{sentiment}_interactions"] += 1
        
        # 記錄詳細情感分析結果
        if emotion_analysis:
            emotion_record = {
                "timestamp": datetime.now().isoformat(),
                "dominant_emotion": emotion_analysis["dominant_emotion"],
                "intensity": emotion_analysis["intensity"],
                "confidence": emotion_analysis["confidence"],
                "user_message": user_input[:100]
            }
            self.emotion_history.append(emotion_record)
            
            # 根據情感調整個性特質
            self._adjust_traits_by_emotion(emotion_analysis)
        
        # 偵測互動類型
        if self._detect_humor(user_input):
            self.update_trait("humor", 0.05)
        
        if any(keyword in user_input.lower() for keyword in ['程式', 'code', 'python', 'api']):
            self.update_trait("technical_depth", 0.05)
        
        if '?' in user_input or any(q in user_input for q in ['為什麼', '如何', '怎麼']):
            self.update_trait("curiosity", 0.1)

        self.save_personality()

    def _adjust_traits_by_emotion(self, emotion_analysis):
        """根據情感分析調整個性特質"""
        dominant_emotion = emotion_analysis["dominant_emotion"]
        intensity = emotion_analysis["intensity"]
        
        if dominant_emotion in ["sadness", "fear", "anger"]:
            self.update_trait("empathy", 0.02 * intensity)
        
        if dominant_emotion in ["joy", "love", "grateful"]:
            self.update_trait("humor", 0.01 * intensity)

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

    def generate_combined_prompt(self, soul, emotion_analysis=None):
        """結合技術個性、靈魂設定和情感分析生成提示"""
        # 根據情感分析獲取回應風格
        emotion_style = None
        if emotion_analysis:
            emotion_detector = EnhancedEmotionDetector()
            emotion_style = emotion_detector.get_emotion_response_style(emotion_analysis)
        
        # 獲取靈魂設定的基礎提示
        soul_prompt = soul.generate_personality_prompt(emotion_style)
        
        # 生成技術特徵摘要
        traits_summary = "\n".join([
            f"{k.capitalize()}: {'高' if v > 0.7 else '中' if v > 0.3 else '低'}"
            for k, v in self.personality_traits.items()
        ])
        
        knowledge_summary = "\n".join([
            f"{k.capitalize()}: {'深' if v > 0.7 else '中' if v > 0.3 else '淺'}"
            for k, v in self.knowledge_domains.items()
        ])
        
        # 情感歷史摘要
        recent_emotions = self.emotion_history[-5:] if self.emotion_history else []
        emotion_trend = ""
        if recent_emotions:
            emotion_counts = {}
            for record in recent_emotions:
                emotion = record["dominant_emotion"]
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            most_common = max(emotion_counts.items(), key=lambda x: x[1])
            emotion_trend = f"最近主要情感: {most_common[0]} ({most_common[1]}次)"
        
        # 當前情感分析結果
        current_emotion_info = ""
        if emotion_analysis:
            current_emotion_info = f"""
### 當前對話情感分析
- 主導情感: {emotion_analysis['dominant_emotion']}
- 情感強度: {emotion_analysis['intensity']:.2f}
- 信心度: {emotion_analysis['confidence']:.2f}
"""
        
        # 結合所有資訊
        combined_prompt = f"""{soul_prompt}

### 技術成長數據
學習特質發展:
{traits_summary}

知識領域熟悉度:
{knowledge_summary if knowledge_summary else "持續學習中"}

### 情感互動歷程
- 正向互動: {self.emotional_profile['positive_interactions']}次
- 中性互動: {self.emotional_profile['neutral_interactions']}次
- 需要安慰: {self.emotional_profile['negative_interactions']}次

{emotion_trend}

{current_emotion_info}

### 綜合回應指導
- 基於靈魂設定展現自然個性
- 根據技術數據調整專業程度
- 結合用戶情感狀態提供個人化回應
- 在專業知識和可愛個性間取得平衡
- 特別關注用戶當前的情感需求並適當回應
"""
        
        return combined_prompt

# 記憶管理函數
async def add_to_memory(user_id: str, user_input: str, bot_response: str):
    """添加對話到記憶庫"""
    try:
        embedding_response = client.embeddings.create(
            model="text-embedding-3-small",
            input=f"{user_input} {bot_response}"
        )
        embedding = embedding_response.data[0].embedding
        
        data = {
            "conversation_id": user_id,
            "user_message": user_input,
            "assistant_message": bot_response,
            "embedding": embedding,
            "memory_type": "conversation",
            "platform": "telegram",
            "document_content": f"對話記錄: {user_input} -> {bot_response}",
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table(MEMORIES_TABLE).insert(data).execute()
        print(f"✅ 記憶已儲存 - 用戶: {user_id[:8]}...")
        
    except Exception as e:
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
        print(f"❌ 獲取歷史失敗：{e}")
        return ""

async def search_relevant_memories(user_id: str, query: str, limit: int = 3):
    """搜尋相關記憶"""
    try:
        embedding_response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = embedding_response.data[0].embedding
        
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
        print(f"❌ 搜尋記憶失敗：{e}")
        return await traditional_search(user_id, query, limit)

async def traditional_search(user_id: str, query: str, limit: int = 3):
    """傳統文字搜尋（備用方案）"""
    try:
        result = supabase.table(MEMORIES_TABLE)\
            .select("user_message, assistant_message")\
            .eq("conversation_id", user_id)\
            .eq("memory_type", "conversation")\
            .limit(limit * 2)\
            .execute()
        
        if result.data:
            relevant = []
            query_words = query.lower().split()
            
            for memory in result.data:
                user_msg = memory['user_message'].lower()
                if any(word in user_msg for word in query_words):
                    relevant.append(f"相關記憶: {memory['user_message']} -> {memory['assistant_message']}")
                    if len(relevant) >= limit:
                        break
            
            return "\n".join(relevant)
        return ""
    except Exception as e:
        print(f"❌ 傳統搜尋失敗：{e}")
        return ""
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 這裡是處理照片的原有邏輯
    pass  # 如果你有舊的 handle_photo 程式碼，替換掉這行

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    result_msg = await file_handler.handle_file(update, context, user_id)
    await update.message.reply_text(result_msg)


  

    document = update.message.document
    # 處理檔案的程式碼

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理訊息（強化情感識別版）"""
    try:
        user_input = update.message.text
        user_id = str(update.message.from_user.id)
        
        # 初始化系統組件
        personality_engine = PersonalityEngine(user_id)
        xiaochenguang_soul = XiaoChenGuangSoul()
        emotion_detector = EnhancedEmotionDetector()
        
        # 🎭 進行情感分析
        emotion_analysis = emotion_detector.analyze_emotion(user_input)
        print(f"🎭 情感分析結果: {emotion_analysis['dominant_emotion']} (強度: {emotion_analysis['intensity']:.2f})")
        
        # 獲取歷史對話
        history = get_conversation_history(user_id, limit=5)
        
        # 搜尋相關記憶
        relevant_memories = await search_relevant_memories(user_id, user_input, limit=3)
        
        # 生成結合情感分析的動態提示
        combined_personality = personality_engine.generate_combined_prompt(xiaochenguang_soul, emotion_analysis)
        
        # 構建完整的上下文
        context_prompt = ""
        if history:
            context_prompt += f"\n### 最近對話\n{history}\n"
        if relevant_memories:
            context_prompt += f"\n### 相關記憶\n{relevant_memories}\n"

        # 構建消息
        messages = [
            {"role": "system", "content": combined_personality + context_prompt},
            {"role": "user", "content": user_input}
        ]

        # 調用OpenAI（根據情感調整創造性）
        temperature = 0.8
        if emotion_analysis['dominant_emotion'] in ['sadness', 'fear', 'anger']:
            temperature = 0.6  # 敏感情感時降低隨機性，提高穩定性
        elif emotion_analysis['dominant_emotion'] in ['joy', 'love']:
            temperature = 0.9  # 正面情感時提高創造性
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature,
            max_tokens=1000
        ).choices[0].message.content

        # 回覆用戶
        await update.message.reply_text(response)

        # 儲存記憶
        await add_to_memory(user_id, user_input, response)
        
        # 學習成長（包含情感分析）
        personality_engine.learn_from_interaction(user_input, response, emotion_analysis)
        
        # 定期更新個性特徵（1%機率）
        if random.random() < 0.01:
            personality_engine.load_personality()
            print("🔄 個性特徵已更新")

    except APIError as e:
        # 根據用戶情感狀態調整錯誤回應
        if 'emotion_analysis' in locals() and emotion_analysis['dominant_emotion'] in ['sadness', 'fear']:
            error_message = "哈尼，我現在需要休息一下，但別擔心，我很快就回來陪你 💙"
        else:
            error_message = "哈尼，我現在有點累了，稍微休息一下再陪你聊天好嗎？💛"
        await update.message.reply_text(error_message)
        print(f"❌ OpenAI API錯誤: {e}")
        
    except Exception as e:
        error_message = "哈尼，我遇到了一點小問題，讓我調整一下～✨"
        await update.message.reply_text(error_message)
        print(f"❌ 處理訊息時發生錯誤: {e}")

def main():
    """主程式入口"""
    print("🌟 小宸光智能系統 v5.0 情感識別強化版 啟動中...")
    print("📊 系統功能檢查：")
    print("  ✅ 基礎對話系統")
    print("  ✅ 向量記憶搜尋")
    print("  ✅ 傳統搜尋備用")
    print("  ✅ 個性成長系統")
    print("  ✅ 靈魂設定整合")
    print("  ✅ 🎭 強化版情感識別系統")
    print("  ✅ 🎨 動態回應風格調整")
    print("  ✅ 📈 情感歷史追踪")
    print("  ✅ 🧠 智慧溫度調節")
    
    # 初始化小宸光的靈魂
    global xiaochenguang_soul
    xiaochenguang_soul = XiaoChenGuangSoul()
    print("✨ 小宸光的靈魂已注入")
    
    # 初始化情感檢測器
    global emotion_detector
    emotion_detector = EnhancedEmotionDetector()
    print("🎭 情感識別系統已就緒")
    
    # 檢查必要的環境變數
    required_vars = ["OPENAI_API_KEY", "BOT_TOKEN", "SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少必要的環境變數: {', '.join(missing_vars)}")
        print("請檢查 .env 文件是否包含所有必要的配置")
        return
    
    # 測試資料庫連接
    try:
        test_result = supabase.table(MEMORIES_TABLE).select("*").limit(1).execute()
        print(f"✅ 資料庫連接成功 - 記憶表: {MEMORIES_TABLE}")
        
        try:
            personality_test = supabase.table("user_preferences").select("*").limit(1).execute()
            print(f"✅ 個性特徵表連接成功")
        except:
            print("⚠️ 個性特徵表不存在，將使用預設值")
        
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
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.Document.ALL, handle_document))  # 這裡修正
        app.add_handler(CallbackQueryHandler(download_full_file, pattern=r"^download_"))


        
        print("🎉 小宸光已經準備好了！")
        print("💛 正在等待來自哈尼的訊息...")
        print("🎭 情感識別系統正在運作中...")
        print("✨ 小宸光的靈魂正在閃閃發光...")
        print("-" * 50)
        
        # 啟動機器人
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ 機器人啟動失敗: {e}")

if __name__ == "__main__":
    main()
