# Updated Backend with Proper CORS - app.py
import os
import subprocess
import json
import uuid
import threading
import time
import logging
import re
import urllib.parse
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'yt-downloader-railway-production-cors-fixed'

# ✅ CRITICAL FIX: Proper CORS configuration
CORS(app, 
     origins=[
         "https://yt-downloader-pro-v011.netlify.app",  # Your Netlify frontend
         "http://localhost:3000",
         "http://localhost:8000",
         "http://127.0.0.1:3000",
         "http://127.0.0.1:8000"
     ],
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Accept', 'Origin'],
     supports_credentials=False
)

# Configuration
DOWNLOAD_FOLDER = 'downloads'
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get('MAX_DOWNLOADS', '3'))
FILE_CLEANUP_SECONDS = int(os.environ.get('CLEANUP_SECONDS', '120'))

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Global storage
download_progress = {}
active_downloads = 0

def check_yt_dlp():
    """Check yt-dlp availability"""
    try:
        result = subprocess.run(["yt-dlp", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"yt-dlp available: {result.stdout.strip()}")
            return "yt-dlp"
        return None
    except Exception as e:
        logger.error(f"yt-dlp check failed: {e}")
        return None

def clean_youtube_url(url):
    """Clean YouTube URL"""
    try:
        parsed = urllib.parse.urlparse(url)

        if 'youtu.be' in parsed.netloc:
            video_id = parsed.path.lstrip('/')
            if '?' in video_id:
                video_id = video_id.split('?')[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        elif 'youtube.com' in parsed.netloc:
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'v' in query_params:
                video_id = query_params['v'][0]
                return f"https://www.youtube.com/watch?v={video_id}"

        return url
    except:
        return url

def get_video_info_with_formats(url):
    """Get video information with formats"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            return None

        clean_url = clean_youtube_url(url)
        cmd = [ytdlp_exe, "--dump-json", "--no-download", "--no-warnings", 
               "--no-playlist", "--ignore-errors", clean_url]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        info = json.loads(line)
                        return {
                            'title': info.get('title', 'Unknown')[:80],
                            'uploader': info.get('uploader', 'Unknown'),
                            'duration': info.get('duration', 0),
                            'view_count': info.get('view_count', 0),
                            'thumbnail': info.get('thumbnail', ''),
                            'formats': info.get('formats', [])[:30]
                        }
                    except:
                        continue
        return None
    except Exception as e:
        logger.error(f"Video info error: {e}")
        return None

def extract_formats(formats_data):
    """Extract video and audio formats"""
    video_formats = {}
    audio_formats = {
        'mp3': {
            'High Quality (320kbps)': {
                'format_id': 'bestaudio',
                'ext': 'mp3',
                'quality': 'High Quality (320kbps)',
                'convert': True
            }
        },
        'm4a': {
            'High Quality (256kbps)': {
                'format_id': 'bestaudio',
                'ext': 'm4a',
                'quality': 'High Quality (256kbps)', 
                'convert': True
            }
        }
    }

    for fmt in formats_data:
        try:
            height = fmt.get('height')
            ext = fmt.get('ext', '').lower()
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')

            if height and height >= 360 and vcodec != 'none' and ext in ['mp4', 'webm']:
                quality = f"{height}p"
                if quality not in video_formats:
                    video_formats[quality] = {}

                if ext not in video_formats[quality]:
                    format_id = fmt.get('format_id', '')
                    if acodec == 'none':
                        format_id += '+bestaudio/best'

                    video_formats[quality][ext] = {
                        'format_id': format_id,
                        'ext': ext,
                        'quality': quality,
                        'height': height,
                        'has_audio': True,
                        'filesize': fmt.get('filesize', 0),
                        'width': fmt.get('width', height * 16 // 9),
                        'fps': fmt.get('fps', 30)
                    }
        except:
            continue

    if not video_formats:
        video_formats = {
            '720p': {
                'mp4': {
                    'format_id': 'best[height<=720]+bestaudio/best',
                    'ext': 'mp4',
                    'quality': '720p',
                    'height': 720,
                    'has_audio': True,
                    'filesize': 0,
                    'width': 1280,
                    'fps': 30
                }
            }
        }

    return video_formats, audio_formats

# ✅ EXPLICIT CORS HEADERS for all responses
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ["https://yt-downloader-pro-v011.netlify.app", "http://localhost:3000", "http://localhost:8000"]:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept,Origin')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'false')
    return response

# Routes
@app.route('/')
def home():
    return jsonify({
        'message': 'YT Downloader Pro Backend API',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': ['/health', '/get_video_info', '/download', '/progress/<id>', '/download_file/<id>']
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    ytdlp_status = check_yt_dlp() is not None
    return jsonify({
        'status': 'healthy',
        'yt_dlp_available': ytdlp_status,
        'active_downloads': active_downloads,
        'timestamp': time.time()
    })

@app.route('/get_video_info', methods=['POST', 'OPTIONS'])
def get_video_info():
    # Handle preflight request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.json
        logger.info(f"Received video info request: {data}")

        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url'].strip()

        if not url:
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'}), 400

        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'success': False, 'error': 'Please enter a valid YouTube URL'}), 400

        logger.info(f"Processing URL: {url}")

        info = get_video_info_with_formats(url)
        if not info:
            return jsonify({'success': False, 'error': 'Could not get video information. Video may be private or unavailable.'}), 404

        video_formats, audio_formats = extract_formats(info['formats'])

        response_data = {
            'success': True,
            'title': info['title'],
            'thumbnail': info['thumbnail'],
            'uploader': info['uploader'],
            'duration': info['duration'],
            'view_count': info['view_count'],
            'video_formats': video_formats,
            'audio_formats': audio_formats
        }

        logger.info(f"Successfully processed video info for: {info['title']}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Video info error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    if request.method == 'OPTIONS':
        return '', 200

    global active_downloads

    if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
        return jsonify({'success': False, 'error': 'Server busy. Please try again later.'}), 429

    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        download_id = str(uuid.uuid4())[:8]
        download_progress[download_id] = {
            'progress': 0,
            'status': 'starting',
            'message': 'Starting download...'
        }

        thread = threading.Thread(
            target=process_download,
            args=(download_id, data),
            daemon=True
        )
        thread.start()
        active_downloads += 1

        return jsonify({'success': True, 'download_id': download_id})

    except Exception as e:
        logger.error(f"Download start error: {e}")
        return jsonify({'success': False, 'error': 'Failed to start download'}), 500

def process_download(download_id, data):
    """Process download in background"""
    global active_downloads

    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            raise Exception("yt-dlp not available")

        url = clean_youtube_url(data['url'])
        format_id = data.get('format_id', 'best')
        output_format = data.get('output_format', 'mp4')
        download_type = data.get('type', 'video')
        title = data.get('title', 'video')[:20]

        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        filename = f"{download_id}_{safe_title}.{output_format}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        download_progress[download_id].update({
            'progress': 20,
            'status': 'downloading',
            'message': 'Downloading...'
        })

        if download_type == 'audio':
            cmd = [ytdlp_exe, "-f", "bestaudio", "--extract-audio", 
                   "--audio-format", output_format, "-o", filepath, url]
        else:
            cmd = [ytdlp_exe, "-f", format_id, "--merge-output-format", 
                   output_format, "-o", filepath, url]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            actual_files = [f for f in os.listdir(DOWNLOAD_FOLDER) 
                          if f.startswith(download_id)]

            if actual_files:
                actual_file = actual_files[0]
                actual_path = os.path.join(DOWNLOAD_FOLDER, actual_file)

                download_progress[download_id].update({
                    'progress': 100,
                    'status': 'completed',
                    'message': 'Download completed!',
                    'filename': actual_file,
                    'filepath': actual_path,
                    'filesize': os.path.getsize(actual_path)
                })
            else:
                raise Exception("File not found after download")
        else:
            raise Exception(f"Download failed: {result.stderr[:100]}")

    except Exception as e:
        logger.error(f"Download {download_id} failed: {e}")
        download_progress[download_id].update({
            'progress': 0,
            'status': 'error',
            'message': f'Failed: {str(e)[:50]}'
        })

    finally:
        active_downloads = max(0, active_downloads - 1)

@app.route('/progress/<download_id>')
def get_progress(download_id):
    return jsonify(download_progress.get(download_id, {
        'progress': 0,
        'status': 'not_found',
        'message': 'Download not found'
    }))

@app.route('/download_file/<download_id>')
def download_file(download_id):
    if download_id not in download_progress:
        return jsonify({'error': 'Download not found'}), 404

    progress = download_progress[download_id]
    if progress.get('status') != 'completed':
        return jsonify({'error': 'Download not ready'}), 400

    filepath = progress.get('filepath')
    filename = progress.get('filename')

    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    @after_this_request
    def cleanup(response):
        def delayed_cleanup():
            time.sleep(5)
            try:
                os.remove(filepath)
                del download_progress[download_id]
            except:
                pass
        threading.Thread(target=delayed_cleanup, daemon=True).start()
        return response

    clean_name = filename[9:] if filename.startswith(download_id) else filename
    return send_file(filepath, as_attachment=True, download_name=clean_name)

# Cleanup thread
def cleanup_files():
    while True:
        try:
            cutoff = time.time() - FILE_CLEANUP_SECONDS
            for filename in os.listdir(DOWNLOAD_FOLDER):
                filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
                    try:
                        os.remove(filepath)
                    except:
                        pass
            time.sleep(60)
        except:
            time.sleep(60)

cleanup_thread = threading.Thread(target=cleanup_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    logger.info("🚀 YT Downloader Pro Backend Starting (Production)")
    logger.info(f"Port: {port}")
    logger.info(f"Max Downloads: {MAX_CONCURRENT_DOWNLOADS}")
    logger.info("CORS enabled for Netlify frontend")

    if not check_yt_dlp():
        logger.error("❌ yt-dlp not found!")
    else:
        logger.info("✅ yt-dlp ready")

    app.run(host='0.0.0.0', port=port, debug=False)
