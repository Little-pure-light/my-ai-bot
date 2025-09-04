FROM python:3.11-slim

# 安裝 Tesseract OCR
RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev

# 安裝 tini (解決容器啟動卡住的問題)
RUN apt-get install -y tini

# 設定工作目錄
WORKDIR /app

# 複製需求檔案
COPY requirements.txt .

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 使用 tini 作為 entrypoint，避免卡死
ENTRYPOINT ["/usr/bin/tini\", \"--\"]

# 啟動 bot
CMD [\"python\", \"bot.py\"]
