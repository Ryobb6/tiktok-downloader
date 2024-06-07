from flask import Flask, request, jsonify
import yt_dlp
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import logging

app = Flask(__name__)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

logging.basicConfig(level=logging.INFO)

def upload_to_drive(filename, filepath, folder_id):
    logging.info(f"Uploading {filepath} to Google Drive...")
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(filepath, mimetype='video/mp4')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    logging.info(f"File uploaded to Google Drive with ID: {file.get('id')}")
    return f"File ID: {file.get('id')}"

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
    
    folder_id = '11wUCoalkVL-PBibU7mJIBtRhcI9Xvwd7'  # Your Google Drive folder ID
    ydl_opts = {'outtmpl': 'downloaded_video.%(ext)s',}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_ext = info_dict.get('ext', 'mp4')
            video_file = f'downloaded_video.{video_ext}'
            logging.info(f"Downloaded video file path: {video_file}")
            file_id = upload_to_drive(video_file, video_file, folder_id)
        return jsonify({'status': 'success', 'filePath': video_file, 'driveFileId': file_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
