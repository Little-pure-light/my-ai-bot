from aiogram import types, Dispatcher

# 處理一般文字訊息
async def handle_text(message: types.Message):
    await message.answer(f"收到文字訊息：{message.text}")

# 註冊
def register(dp: Dispatcher):
    dp.register_message_handler(handle_text, content_types=['text'])
