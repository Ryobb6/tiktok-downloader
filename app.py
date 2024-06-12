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

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

SCOPES = ['https://www.googleapis.com/auth/drive.file']

logging.basicConfig(level=logging.INFO)

# シークレットファイルからサービスアカウントのJSON情報を読み込む
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'
with open(SERVICE_ACCOUNT_FILE) as f:
    service_account_info = json.load(f)

credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

def upload_to_drive(filename, filepath, folder_id):
    logging.info(f"Uploading {filepath} to Google Drive...")
    try:
        service = build('drive', 'v3', credentials=credentials)
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaFileUpload(filepath, mimetype='video/mp4')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"File uploaded to Google Drive with ID: {file.get('id')}")
        return f"File ID: {file.get('id')}"
    except Exception as e:
        logging.error(f"Failed to upload file to Google Drive: {str(e)}", exc_info=True)
        return None

@app.route('/')
def index():
    return "Welcome to the TikTok Downloader!"

@app.route('/download', methods=['POST'])
def download_and_upload():
    logging.info(f"Headers: {request.headers}")
    logging.info(f"Request data: {request.data}")

    if 'url' in request.form:
        url = request.form['url']
        logging.info(f"URL: {url}")
    else:
        return jsonify({'status': 'error', 'message': 'URL is missing'}), 400
    
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    download_dir = '/mnt/data'
    os.makedirs(download_dir, exist_ok=True)
    ydl_opts = {'outtmpl': os.path.join(download_dir, 'downloaded_video.%(ext)s')}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_ext = info_dict.get('ext', 'mp4')
            video_file = os.path.join(download_dir, f'downloaded_video.{video_ext}')
            logging.info(f"Downloaded video file path: {video_file}")
            result = upload_to_drive(f'downloaded_video.{video_ext}', video_file, folder_id)
            if isinstance(result, str):
                return jsonify({'status': 'success', 'filePath': video_file, 'driveFileId': result})
            else:
                return jsonify({'status': 'error', 'message': 'Failed to upload to Google Drive'})
    except Exception as e:
        logging.error(f"Error during download and upload process: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
