from aiogram import types, Dispatcher

# 處理文件上傳
async def handle_file(message: types.Message):
    file_info = await message.bot.get_file(message.document.file_id)
    file_path = file_info.file_path
    await message.answer(f"收到檔案：{message.document.file_name}\n路徑：{file_path}")

# 處理圖片上傳
async def handle_image(message: types.Message):
    photo = message.photo[-1]  # 取最大尺寸
    file_info = await message.bot.get_file(photo.file_id)
    file_path = file_info.file_path
    await message.answer(f"收到圖片，路徑：{file_path}")

# 註冊
def register(dp: Dispatcher):
    dp.register_message_handler(handle_file, content_types=['document'])
    dp.register_message_handler(handle_image, content_types=['photo'])
