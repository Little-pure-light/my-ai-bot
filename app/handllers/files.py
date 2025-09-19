from aiogram import types, Dispatcher
import os

# 設定上傳的資料夾
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 處理文件上傳
async def handle_file(message: types.Message):
    file_info = await message.bot.get_file(message.document.file_id)
    file_path = file_info.file_path

    # 下載檔案
    downloaded_file = await message.bot.download_file(file_path)

    # 存到 uploads 資料夾
    save_path = os.path.join(UPLOAD_DIR, message.document.file_name)
    with open(save_path, "wb") as f:
        f.write(downloaded_file.read())

    await message.answer(f"📂 檔案 **{message.document.file_name}** 已儲存到 `{save_path}`")

# 處理圖片上傳
async def handle_image(message: types.Message):
    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)
    file_path = file_info.file_path

    downloaded_file = await message.bot.download_file(file_path)

    save_path = os.path.join(UPLOAD_DIR, f"{photo.file_id}.jpg")
    with open(save_path, "wb") as f:
        f.write(downloaded_file.read())

    await message.answer(f"🖼️ 圖片已儲存到 `{save_path}`")

# 註冊
def register(dp: Dispatcher):
    dp.register_message_handler(handle_file, content_types=['document'])
    dp.register_message_handler(handle_image, content_types=['photo'])
