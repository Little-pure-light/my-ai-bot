import os
import json
import logging
import pandas as pd
import docx
import PyPDF2
import csv
import xml.etree.ElementTree as ET
import chardet

class FileHandler:
    def __init__(self, log_level=logging.INFO):
        logging.basicConfig(
            level=log_level, 
            format='%(asctime)s - %(levelname)s: %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def detect_encoding(self, file_path):
        """
        自動偵測文件編碼
        """
        with open(file_path, 'rb') as file:
            result = chardet.detect(file.read())
        return result['encoding']

    def read_file(self, file_path):
        """
        通用文件讀取方法
        """
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return None

        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext in ['.txt', '.log', '.md']:
                encoding = self.detect_encoding(file_path)
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            
            elif file_ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            elif file_ext == '.csv':
                return pd.read_csv(file_path).to_dict(orient='records')
            
            elif file_ext in ['.xls', '.xlsx']:
                return pd.read_excel(file_path).to_dict(orient='records')
            
            elif file_ext == '.docx':
                doc = docx.Document(file_path)
                return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            
            elif file_ext == '.pdf':
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ''
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    return text
            
            elif file_ext == '.xml':
                tree = ET.parse(file_path)
                root = tree.getroot()
                return ET.tostring(root, encoding='unicode')
            
            else:
                self.logger.warning(f"不支援的文件類型: {file_ext}")
                return None
        
        except Exception as e:
            self.logger.error(f"讀取文件 {file_path} 時發生錯誤: {e}")
            return None

    def save_file(self, data, file_path):
        """
        通用文件儲存方法
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.txt':
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(data))
            
            elif file_ext == '.json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            
            elif file_ext == '.csv':
                pd.DataFrame(data).to_csv(file_path, index=False)
            
            elif file_ext in ['.xls', '.xlsx']:
                pd.DataFrame(data).to_excel(file_path, index=False)
            
            else:
                self.logger.warning(f"不支援的儲存文件類型: {file_ext}")
                return False
            
            self.logger.info(f"成功儲存文件: {file_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"儲存文件 {file_path} 時發生錯誤: {e}")
            return False

    def list_files(self, directory, extensions=None):
        """
        列出目錄下符合條件的文件
        """
        try:
            if not os.path.isdir(directory):
                self.logger.error(f"無效的目錄: {directory}")
                return []

            all_files = os.listdir(directory)
            
            if extensions:
                return [
                    f for f in all_files 
                    if os.path.isfile(os.path.join(directory, f)) 
                    and os.path.splitext(f)[1].lower() in extensions
                ]
            
            return [f for f in all_files if os.path.isfile(os.path.join(directory, f))]
        
        except Exception as e:
            self.logger.error(f"列出文件時發生錯誤: {e}")
            return []

# 使用範例
if __name__ == "__main__":
    handler = FileHandler()
    
    # 讀取文件
    content = handler.read_file('example.txt')
    
    # 儲存文件
    handler.save_file(content, 'output.txt')
    
    # 列出特定類型文件
    files = handler.list_files('.', ['.txt', '.json'])
