from flask import Flask, request, jsonify, redirect, url_for, session
import yt_dlp
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRETS_FILE = "credentials.json"

logging.basicConfig(level=logging.INFO)

def upload_to_drive(filename, filepath, folder_id):
    logging.info(f"Uploading {filepath} to Google Drive...")
    creds = None
    try:
        if 'credentials' in session:
            creds = Credentials(**session['credentials'])
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
                flow.redirect_uri = url_for('oauth2callback', _external=True)
                authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
                session['state'] = state
                return redirect(authorization_url)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaFileUpload(filepath, mimetype='video/mp4')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"File uploaded to Google Drive with ID: {file.get('id')}")
        session['credentials'] = creds_to_dict(creds)
        return f"File ID: {file.get('id')}"
    except Exception as e:
        logging.error(f"Failed to upload file to Google Drive: {str(e)}")
        return None

def creds_to_dict(creds):
    return {'token': creds.token, 'refresh_token': creds.refresh_token, 'token_uri': creds.token_uri, 'client_id': creds.client_id, 'client_secret': creds.client_secret, 'scopes': creds.scopes}

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
            if file_id:
                return jsonify({'status': 'success', 'filePath': video_file, 'driveFileId': file_id})
            else:
                return jsonify({'status': 'error', 'message': 'Failed to upload to Google Drive'})
    except Exception as e:
        logging.error(f"Error during download and upload process: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials
    session['credentials'] = creds_to_dict(creds)
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
