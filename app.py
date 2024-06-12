from flask import Flask, request, jsonify
import yt_dlp
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import logging
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# Flaskアプリケーションの初期化
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # 環境変数からシークレットキーを取得

# Google Drive APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# ロギングの設定
logging.basicConfig(level=logging.INFO)

# シークレットファイルからサービスアカウントのJSON情報を読み込む
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'
with open(SERVICE_ACCOUNT_FILE) as f:
    service_account_info = json.load(f)

# サービスアカウントの認証情報を設定
credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

def upload_to_drive(filename, filepath, folder_id):
    """
    Google Driveにファイルをアップロードする関数
    """
    logging.info(f"Uploading {filepath} to Google Drive...")
    try:
        service = build('drive', 'v3', credentials=credentials)
        file_metadata = {
            'name': filename,
            'parents': [folder_id]  # アップロード先のフォルダIDを指定
        }
        media = MediaFileUpload(filepath, mimetype='video/mp4')  # アップロードするファイルのメタデータを設定
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"File uploaded to Google Drive with ID: {file.get('id')}")
        return f"File ID: {file.get('id')}"
    except Exception as e:
        logging.error(f"Failed to upload file to Google Drive: {str(e)}", exc_info=True)
        return None

@app.route('/')
def index():
    """
    ルートエンドポイント
    """
    return "Welcome to the TikTok Downloader!"

@app.route('/download', methods=['POST'])
def download_and_upload():
    """
    TikTok動画をダウンロードし、Google Driveにアップロードするエンドポイント
    """
    logging.info(f"Headers: {request.headers}")
    logging.info(f"Request data: {request.data}")

    # リクエストからURLとファイル名を取得
    if 'url' in request.form and 'name' in request.form:
        url = request.form['url']
        name = request.form['name']
        logging.info(f"URL: {url}")
        logging.info(f"File Name: {name}")
    else:
        return jsonify({'status': 'error', 'message': 'URL or name is missing'}), 400
    
    # Google DriveのフォルダIDを環境変数から取得
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    
    # ダウンロード用のディレクトリを設定
    download_dir = '/mnt/data'
    os.makedirs(download_dir, exist_ok=True)
    
    # yt-dlpのオプションを設定
    ydl_opts = {'outtmpl': os.path.join(download_dir, 'downloaded_video.%(ext)s')}
    
    try:
        # TikTok動画をダウンロード
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_ext = info_dict.get('ext', 'mp4')
            video_file = os.path.join(download_dir, f'downloaded_video.{video_ext}')
            logging.info(f"Downloaded video file path: {video_file}")
            
            # Google Driveにアップロード
            result = upload_to_drive(f'{name}.{video_ext}', video_file, folder_id)
            if isinstance(result, str):
                return jsonify({'status': 'success', 'filePath': video_file, 'driveFileId': result})
            else:
                return jsonify({'status': 'error', 'message': 'Failed to upload to Google Drive'})
    except Exception as e:
        logging.error(f"Error during download and upload process: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # アプリケーションのエントリーポイント
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
