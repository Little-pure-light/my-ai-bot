app/
  bot.py                 # 入口，只做路由與註冊 handler
  config.py              # 讀環境變數
  handlers/
    text.py              # 純文字訊息：一般對話 + 問檔案內容
    files.py             # 文件上傳：下載→萃取→回報
    images.py            # 圖片上傳：下載→描述→回報
  services/
    parser.py            # 檔案偵測與讀取（txt/md/pdf…先做 txt/md）
    openai_client.py     # 與 OpenAI 對話（文字）與看圖（Vision）
  memory/
    session.py           # 記錄「每位使用者最近一次上傳的檔案路徑/類型」
  utils/
    paths.py             # 產生安全路徑（/tmp）
requirements.txt

import os

class Settings:
    BOT_TOKEN = os.getenv("_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")

settings = Settings()
