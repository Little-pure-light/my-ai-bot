# modules/file_handler.py
import os
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes

class FileHandler:
    """小宸光檔案處理模組"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.supported_formats = {'.txt', '.pdf', '.docx', '.md'}
        
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str) -> str:
        """處理用戶上傳的文件"""
        try:
            document = update.message.document  # Telegram 自動回傳 Document 物件
            
            # 檢查檔案格式
            file_ext = Path(document.file_name).suffix.lower()
            if file_ext not in self.supported_formats:
                return f"不支援的檔案格式: {file_ext}\n支援格式: {', '.join(self.supported_formats)}"
            
            # 創建用戶專屬資料夾
            user_dir = self.upload_dir / user_id
            user_dir.mkdir(exist_ok=True)
            
            # 下載檔案
            file = await context.bot.get_file(document.file_id)
            file_path = user_dir / document.file_name
            await file.download_to_drive(str(file_path))
            
            # 讀取檔案內容
            content = await self._read_file_content(file_path)
            
            return f"檔案 {document.file_name} 上傳成功！\n內容預覽：\n{content[:200]}..."
            
        except Exception as e:
            print(f"檔案處理錯誤: {e}")
            return f"檔案處理失敗: {str(e)}"
    
    async def _read_file_content(self, file_path: Path) -> str:
        """讀取檔案內容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='big5') as f:
                    return f.read()
            except:
                return "無法讀取檔案內容"
