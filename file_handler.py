import os

async def handle_file(update, context, user_id):
    try:
        document = update.message.document

        # 1. 檔案基本資訊
        print("=" * 50)
        print(f"[DEBUG] 收到檔案事件 - from user: {user_id}")
        print(f"[DEBUG] File name: {document.file_name}")
        print(f"[DEBUG] MIME type: {document.mime_type}")
        print(f"[DEBUG] File size: {document.file_size} bytes")

        # 2. 下載檔案
        tg_file = await context.bot.get_file(document.file_id)
        file_path = f"/tmp/{document.file_name}"
        await tg_file.download_to_drive(file_path)
        print(f"[DEBUG] File saved to: {file_path}")

        # 3. 確認檔案存在
        if os.path.exists(file_path):
            print("[DEBUG] File confirmed on disk ✅")
        else:
            print("[ERROR] File not found after download ❌")
            return "📂 檔案下載失敗，請再試一次。"

        # 4. 讀取檔案內容（依副檔名決定解析方式）
        content = None
        if document.file_name.lower().endswith(".txt"):
            print("[DEBUG] Detected TXT file, opening...")
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            print(f"[DEBUG] TXT file content length: {len(content)}")
        elif document.file_name.lower().endswith(".pdf"):
            print("[DEBUG] Detected PDF file, parsing...")
            from modules.pdf_parser import parse_pdf  # 假設你有 PDF 解析器
            content = parse_pdf(file_path)
            print(f"[DEBUG] PDF parsed content length: {len(content) if content else 0}")
        else:
            print(f"[WARN] Unhandled file type: {document.file_name}")
            return f"⚠ 我暫時不支援 {document.file_name} 這種檔案類型喔～"

        # 5. AI 分析內容
        if not content or len(content.strip()) == 0:
            print("[ERROR] No content extracted from file ❌")
            return "⚠ 檔案裡似乎沒有可以讀取的內容，請檢查檔案格式。"

        print("[DEBUG] Sending content to AI for analysis...")
        from modules.ai_handler import analyze_content_with_ai  # 假設的 AI 處理模組
        ai_result = await analyze_content_with_ai(content, user_id)

        print("[DEBUG] AI analysis completed ✅")
        print("=" * 50)
        return ai_result

    except Exception as e:
        print(f"[ERROR] handle_file failed: {e}")
        return f"❌ 在處理檔案時發生錯誤：{e}"
