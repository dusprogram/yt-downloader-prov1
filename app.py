# FINAL BACKEND FIX - Proper CORS Configuration
# This fixes the specific CORS error you're experiencing

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

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'yt-downloader-cors-fixed-final'

# ✅ CRITICAL FIX: Specific CORS configuration for your domain
CORS(app,
     origins=[
         "https://yt-downloader-pro-v011.netlify.app",  # Your exact Netlify domain
         "http://localhost:3000",
         "http://localhost:8000",
         "http://127.0.0.1:3000",
         "http://127.0.0.1:8000"
     ],
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Accept', 'Origin', 'Authorization'],
     supports_credentials=False,
     max_age=3600
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
            version = result.stdout.strip()
            logger.info(f"✅ yt-dlp available: {version}")
            return "yt-dlp"
        logger.error("❌ yt-dlp not working")
        return None
    except Exception as e:
        logger.error(f"❌ yt-dlp check failed: {e}")
        return None

def clean_youtube_url(url):
    """Clean and standardize YouTube URL"""
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
    """Get video information and formats"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            logger.error("yt-dlp not available")
            return None

        clean_url = clean_youtube_url(url)
        logger.info(f"Processing URL: {clean_url}")

        cmd = [ytdlp_exe, "--dump-json", "--no-download", "--no-warnings", 
               "--no-playlist", "--ignore-errors", clean_url]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        info = json.loads(line)
                        logger.info(f"✅ Video info extracted: {info.get('title', 'Unknown')}")
                        return {
                            'title': info.get('title', 'Unknown')[:80],
                            'uploader': info.get('uploader', 'Unknown'),
                            'duration': info.get('duration', 0),
                            'view_count': info.get('view_count', 0),
                            'thumbnail': info.get('thumbnail', ''),
                            'formats': info.get('formats', [])[:30]
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        continue

        logger.error("No valid video info found")
        return None

    except subprocess.TimeoutExpired:
        logger.error("Video info extraction timeout")
        return None
    except Exception as e:
        logger.error(f"Video info error: {e}")
        return None

def extract_formats(formats_data):
    """Extract and organize video/audio formats"""
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

    # Process video formats
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

    # Add fallback formats
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
            },
            '480p': {
                'mp4': {
                    'format_id': 'best[height<=480]+bestaudio/best',
                    'ext': 'mp4',
                    'quality': '480p',
                    'height': 480,
                    'has_audio': True,
                    'filesize': 0,
                    'width': 854,
                    'fps': 30
                }
            }
        }

    return video_formats, audio_formats

# ✅ EXPLICIT CORS headers for ALL responses
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    logger.info(f"Request origin: {origin}")

    allowed_origins = [
        "https://yt-downloader-pro-v011.netlify.app",
        "http://localhost:3000",
        "http://localhost:8000"
    ]

    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        logger.info(f"✅ CORS allowed for origin: {origin}")
    else:
        logger.warning(f"⚠️ Origin not in allowed list: {origin}")

    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin'
    response.headers['Access-Control-Max-Age'] = '3600'

    return response

# Routes
@app.route('/', methods=['GET'])
def home():
    """Root route to prevent 404 errors"""
    return jsonify({
        'message': '🎬 YT Downloader Pro Backend API',
        'status': 'running',
        'version': '2.0.0',
        'timestamp': time.time(),
        'endpoints': {
            'health': '/health',
            'video_info': '/get_video_info',
            'download': '/download',
            'progress': '/progress/<id>',
            'download_file': '/download_file/<id>'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    ytdlp_status = check_yt_dlp() is not None
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'yt_dlp_available': ytdlp_status,
        'active_downloads': active_downloads,
        'max_concurrent_downloads': MAX_CONCURRENT_DOWNLOADS,
        'version': '2.0.0'
    })

@app.route('/get_video_info', methods=['POST', 'OPTIONS'])
def get_video_info():
    """Get video information endpoint"""

    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        logger.info("✅ Handling OPTIONS preflight request")
        return '', 200

    try:
        # Log request details
        logger.info(f"📝 POST request to /get_video_info")
        logger.info(f"📋 Headers: {dict(request.headers)}")

        data = request.json
        logger.info(f"📤 Request data: {data}")

        if not data or 'url' not in data:
            logger.error("❌ Missing URL in request")
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url'].strip()

        if not url:
            logger.error("❌ Empty URL provided")
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'}), 400

        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            logger.error(f"❌ Invalid URL domain: {url}")
            return jsonify({'success': False, 'error': 'Please enter a valid YouTube URL'}), 400

        logger.info(f"🔍 Processing video URL: {url}")

        # Get video info
        info = get_video_info_with_formats(url)
        if not info:
            logger.error("❌ Failed to extract video information")
            return jsonify({
                'success': False, 
                'error': 'Could not get video information. Video may be private, unavailable, or region-blocked.'
            }), 404

        # Extract formats
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

        logger.info(f"✅ Successfully processed: {info['title']}")
        logger.info(f"📊 Video formats: {len(video_formats)}, Audio formats: {len(audio_formats)}")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"💥 Video info error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    """Start download endpoint"""

    if request.method == 'OPTIONS':
        return '', 200

    global active_downloads

    if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
        logger.warning(f"⚠️ Server busy: {active_downloads}/{MAX_CONCURRENT_DOWNLOADS}")
        return jsonify({'success': False, 'error': 'Server busy. Please try again later.'}), 429

    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        download_id = str(uuid.uuid4())[:8]
        logger.info(f"🚀 Starting download {download_id}")

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
    """Process download in background thread"""
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

        # Safe filename
        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        filename = f"{download_id}_{safe_title}.{output_format}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        logger.info(f"📥 Processing {download_type} download: {filename}")

        download_progress[download_id].update({
            'progress': 20,
            'status': 'downloading',
            'message': f'Downloading {download_type}...'
        })

        # Build command
        if download_type == 'audio':
            cmd = [ytdlp_exe, "-f", "bestaudio", "--extract-audio", 
                   "--audio-format", output_format, "--audio-quality", "192",
                   "-o", filepath, url]
        else:
            cmd = [ytdlp_exe, "-f", format_id, "--merge-output-format", 
                   output_format, "-o", filepath, url]

        logger.info(f"🔧 Command: {' '.join(cmd[:5])}... [URL_HIDDEN]")

        # Execute download
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            # Find downloaded file
            actual_files = [f for f in os.listdir(DOWNLOAD_FOLDER) 
                          if f.startswith(download_id) and os.path.getsize(os.path.join(DOWNLOAD_FOLDER, f)) > 1024]

            if actual_files:
                actual_file = actual_files[0]
                actual_path = os.path.join(DOWNLOAD_FOLDER, actual_file)
                file_size = os.path.getsize(actual_path)

                download_progress[download_id].update({
                    'progress': 100,
                    'status': 'completed',
                    'message': 'Download completed!',
                    'filename': actual_file,
                    'filepath': actual_path,
                    'filesize': file_size
                })

                logger.info(f"✅ Download completed: {actual_file} ({file_size} bytes)")
            else:
                raise Exception("Download completed but file not found")
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            raise Exception(f"Download failed: {error_msg}")

    except Exception as e:
        logger.error(f"❌ Download {download_id} failed: {e}")
        download_progress[download_id].update({
            'progress': 0,
            'status': 'error',
            'message': f'Failed: {str(e)[:50]}'
        })

    finally:
        active_downloads = max(0, active_downloads - 1)
        logger.info(f"📊 Active downloads: {active_downloads}")

@app.route('/progress/<download_id>', methods=['GET'])
def get_progress(download_id):
    """Get download progress"""
    progress = download_progress.get(download_id, {
        'progress': 0,
        'status': 'not_found',
        'message': 'Download not found'
    })
    return jsonify(progress)

@app.route('/download_file/<download_id>', methods=['GET'])
def download_file(download_id):
    """Download completed file"""
    if download_id not in download_progress:
        logger.error(f"❌ Download {download_id} not found")
        return jsonify({'error': 'Download not found'}), 404

    progress = download_progress[download_id]

    if progress.get('status') != 'completed':
        logger.error(f"❌ Download {download_id} not ready: {progress.get('status')}")
        return jsonify({'error': 'Download not ready'}), 400

    filepath = progress.get('filepath')
    filename = progress.get('filename')

    if not filepath or not os.path.exists(filepath):
        logger.error(f"❌ File not found: {filepath}")
        return jsonify({'error': 'File not found'}), 404

    logger.info(f"📤 Serving file: {filename}")

    @after_this_request
    def cleanup(response):
        def delayed_cleanup():
            time.sleep(5)
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"🗑️ Cleaned up: {filename}")
                if download_id in download_progress:
                    del download_progress[download_id]
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

        threading.Thread(target=delayed_cleanup, daemon=True).start()
        return response

    clean_name = filename[9:] if filename.startswith(download_id) else filename
    return send_file(filepath, as_attachment=True, download_name=clean_name)

# Background cleanup
def cleanup_old_files():
    """Background file cleanup"""
    while True:
        try:
            cutoff_time = time.time() - FILE_CLEANUP_SECONDS
            if os.path.exists(DOWNLOAD_FOLDER):
                for filename in os.listdir(DOWNLOAD_FOLDER):
                    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                    try:
                        if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
                            os.remove(filepath)
                            logger.info(f"🗑️ Auto-cleaned old file: {filename}")
                    except:
                        pass
            time.sleep(60)  # Check every minute
        except:
            time.sleep(60)

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    logger.info("🚀 YT Downloader Pro Backend Starting")
    logger.info(f"📍 Port: {port}")
    logger.info(f"⚡ Max Downloads: {MAX_CONCURRENT_DOWNLOADS}")
    logger.info(f"🧹 File Cleanup: {FILE_CLEANUP_SECONDS}s")

    # Check yt-dlp availability
    if not check_yt_dlp():
        logger.error("❌ yt-dlp not available - downloads will fail!")
    else:
        logger.info("✅ yt-dlp ready for downloads")

    logger.info("🌐 CORS configured for: https://yt-downloader-pro-v011.netlify.app")
    logger.info("🎬 Backend ready for requests!")

    # Use production server
    app.run(host='0.0.0.0', port=port, debug=False)
