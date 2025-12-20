import os
import uuid
import random
import time
from flask import Flask, render_template, request, send_from_directory, flash, redirect
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 設定：檔案上傳的資料夾
UPLOAD_FOLDER = 'uploads'
# 設定：檔案保留時間 (秒)，這裡設為 600 秒 = 10 分鐘
FILE_TTL = 600 
# 設定：允許的檔案類型
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'zip'}

# 確保 uploads 資料夾存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# 限制上傳檔案大小 (例如最大 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 這是一個簡單的「資料庫」，用來記錄 代碼: 檔名
# 結構範例: {'1234': {'filename': 'note.pdf', 'upload_time': 1700000000}}
files_db = {}

def cleanup_expired_files():
    """清理過期檔案的輔助函式"""
    current_time = time.time()
    expired_codes = []
    
    # 檢查哪些代碼過期了
    for code, info in files_db.items():
        if current_time - info['upload_time'] > FILE_TTL:
            expired_codes.append(code)
            
    # 刪除過期檔案和紀錄
    for code in expired_codes:
        filename = files_db[code]['filename']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 嘗試從硬碟刪除檔案
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"刪除失敗: {e}")
            
        # 從字典中移除
        del files_db[code]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    """首頁：上傳檔案 OR 輸入代碼"""
    cleanup_expired_files() # 每次有人訪問首頁時，順便清理過期檔案
    
    new_code = None
    
    if request.method == 'POST':
        # 這是使用者上傳檔案
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return "沒有選擇檔案", 400
            
            if file:
                # 產生一個 4 位數隨機代碼 (1000-9999)
                # 為了避免重複，可以寫個迴圈檢查，但這裡先簡單做
                code = str(random.randint(1000, 9999))
                
                # 為了防止檔名重複或危險，這裡可以改名，但為了方便辨識我們先保留原檔名
                # (進階做法是使用 uuid 改名)

                # 1. 先淨化原檔名 (預防路徑攻擊)
                original_name = secure_filename(file.filename)

                # 2. 重新命名為 UUID (徹底防重複、防惡意字元)
                ext = os.path.splitext(original_name)[1]
                random_name = f"{uuid.uuid4()}{ext}"

                save_path = os.path.join(app.config['UPLOAD_FOLDER'], random_name)
                file.save(save_path)
                
                # 記錄到我們的「資料庫」
                # 同時保存使用者上傳的原始檔名（淨化後）以便讓下載時還原檔名
                files_db[code] = {
                    'filename': random_name,
                    'display_name': original_name,
                    'upload_time': time.time()
                }
                
                new_code = code

    return render_template('index.html', new_code=new_code)

@app.route('/download', methods=['POST'])
def download():
    """處理下載請求"""
    cleanup_expired_files()
    
    code = request.form.get('code')
    
    if code in files_db:
        filename = files_db[code]['filename']
        display_name = files_db[code].get('display_name')
        # 嘗試在不同 Flask 版本中傳回下載檔名（Flask>=2.0: download_name, 舊版: attachment_filename）
        try:
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True, download_name=display_name)
        except TypeError:
            # fallback for older Flask versions
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True, attachment_filename=display_name)
    else:
        return "找不到檔案或代碼已過期！", 404

if __name__ == '__main__':
    app.run(debug=True)