import os
import json
import docx
import io
from PyPDF2 import PdfReader
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile

# 支援的副檔名
allowed_extensions = [".txt", ".md", ".json", ".py", ".docx", ".pdf"]

async def handle_file(update, context, user_id):
    document = update.message.document
    file_name = document.file_name
    file_ext = os.path.splitext(file_name)[-1].lower()

    # 副檔名檢查
    if file_ext not in allowed_extensions:
        return f"⚠ 檔案格式 `{file_ext}` 不支援，目前支援：{', '.join(allowed_extensions)}"

    try:
        # 下載檔案到本地 temp 資料夾
        os.makedirs("temp", exist_ok=True)
        file_path = os.path.join("temp", file_name)
        new_file = await document.get_file()
        await new_file.download_to_drive(file_path)
        
        # 根據副檔名處理文字
        if file_ext in [".txt", ".md", ".py", ".json"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # JSON 額外格式化
            if file_ext == ".json":
                try:
                    content_json = json.loads(content)
                    content = json.dumps(content_json, indent=4, ensure_ascii=False)
                except Exception:
                    pass  # 解析失敗就保持原文

        elif file_ext == ".docx":
            doc = docx.Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])

        elif file_ext == ".pdf":
            content = ""
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        content += page_text

        # 判斷是否需要預覽或完整檔案
        if len(content) > 2000:
            preview = content[:2000] + "...\n\n(內容過長，請使用按鈕下載完整文字)"
            # 按鈕生成
            keyboard = [
                [InlineKeyboardButton("📥 下載完整檔案", callback_data=f"download_{file_name}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # 存入 context.user_data，供回傳檔案用
            context.user_data[f"file_{file_name}"] = content

            await update.message.reply_text(
                f"📄 檔案 **{file_name}** 上傳成功！\n內容預覽：\n```\n{preview}\n```",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return None
        else:
            return f"📄 檔案 **{file_name}** 上傳成功！\n內容預覽：\n```\n{content}\n```"

    except Exception as e:
        return f"❌ 讀取檔案時發生錯誤: {e}"


async def download_full_file(update, context):
    """處理按下完整下載按鈕的回覆"""
    query = update.callback_query
    await query.answer()

    file_name = query.data.replace("download_", "", 1)
    content = context.user_data.get(f"file_{file_name}")

    if content:
        file_stream = io.BytesIO(content.encode("utf-8", errors="ignore"))
        file_stream.name = file_name + ".txt"
        await query.message.reply_document(
            document=InputFile(file_stream, filename=file_stream.name),
            caption=f"📎 這是檔案 **{file_name}** 的完整內容"
        )
    else:
        await query.message.reply_text("⚠ 找不到檔案內容，請重新上傳。")
