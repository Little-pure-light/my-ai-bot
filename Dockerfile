FROM python:3.11-slim

# 安裝 Tesseract（含繁中 chi_tra）與開發套件
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    tesseract-ocr-chi-tra \
  && rm -rf /var/lib/apt/lists/*

# 工作目錄
WORKDIR /app

# 先安裝 Python 套件（利用快取）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 直接啟動 bot（不用 tini）
CMD ["python", "bot.py"]
