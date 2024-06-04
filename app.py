from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "TikTok Downloader is running!"

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data['url']

    ydl_opts = {
        'outtmpl': 'downloaded_video.%(ext)s',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_ext = info_dict.get('ext', 'mp4')
            video_file = f'downloaded_video.{video_ext}'
        
        return jsonify({'status': 'success', 'filePath': video_file})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
