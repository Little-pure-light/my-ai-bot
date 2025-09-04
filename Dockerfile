FROM python:3.11-slim

# 安裝 Tesseract
RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev

# 設定工作目錄
WORKDIR /app

# 複製需求檔案
COPY requirements.txt .

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 啟動 bot
CMD ["python", "bot.py"]
