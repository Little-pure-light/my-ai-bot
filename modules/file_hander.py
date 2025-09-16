import os
import io
import json
import tempfile
import mimetypes
from telegram import Update
from telegram.ext import ContextTypes

class XiaoChenGuangFileHandler:
    def __init__(self):
        self.max_file_size = 20 * 1024 * 1024  # 20MB 限制
        self.allowed_file_types = [
            'text/plain', 
            'application/pdf', 
            'image/jpeg', 
            'image/png'
        ]

    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
        """
        處理用戶上傳的文件
        1. 檢查文件大小
        2. 檢查文件類型
        3. 保存文件
        4. 返回處理結果
        """
        document = update.message.document
        
        # 檢查文件大小
        if document.file_size > self.max_file_size:
            return f"檔案超過 {self.max_file_size / (1024*1024)}MB 的限制"
        
        # 檢查文件類型
        file_mime_type = document.mime_type
        if file_mime_type not in self.allowed_file_types:
            return f"不支援的檔案類型：{file_mime_type}"
        
        try:
            # 下載文件
            file = await context.bot.get_file(document.file_id)
            
            # 創建臨時文件夾
            user_folder = f"uploads/{user_id}"
            os.makedirs(user_folder, exist_ok=True)
            
            # 保存文件
            file_path = os.path.join(user_folder, document.file_name)
            await file.download_to_drive(file_path)
            
            return f"成功上傳文件：{document.file_name}"
        
        except Exception as e:
            return f"文件處理失敗：{str(e)}"
