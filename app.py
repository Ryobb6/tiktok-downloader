from flask import Flask, request, jsonify
import yt_dlp
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request


app = Flask(__name__)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def upload_to_drive(filename, filepath):
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
    file_metadata = {'name': filename}
    media = MediaFileUpload(filepath, mimetype='video/mp4')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"File ID: {file.get('id')}"

#確認用
@app.route('/')
def index():
    return "Welcome to the TikTok Downloader!"


@app.route('/download', methods=['POST'])
def download_and_upload():
    data = request.json
    url = data['url']
    ydl_opts = {'outtmpl': 'downloaded_video.%(ext)s',}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_ext = info_dict.get('ext', 'mp4')
            video_file = f'downloaded_video.{video_ext}'
            file_id = upload_to_drive(video_file, video_file)
        return jsonify({'status': 'success', 'filePath': video_file, 'driveFileId': file_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
