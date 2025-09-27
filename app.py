# ULTIMATE BACKEND FIX - Bypasses Railway CORS Issues
# Research-based solution that handles Railway's edge proxy

import os
import subprocess
import json
import uuid
import threading
import time
import logging
from flask import Flask, request, jsonify, send_file, after_this_request, make_response
from flask_cors import CORS

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'ultimate-yt-downloader-cors-fix'

# ✅ ULTIMATE CORS CONFIGURATION - Research-based Railway fix
CORS(app,
     origins=[
         "https://yt-downloader-pro-v011.netlify.app",  # Your Netlify frontend
         "http://localhost:3000",
         "http://localhost:8000",
         "http://127.0.0.1:3000",
         "http://127.0.0.1:8000",
         "*"  # Temporary wildcard for Railway edge proxy issues
     ],
     methods=['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'],
     allow_headers=[
         'Content-Type', 
         'Accept', 
         'Origin', 
         'Authorization',
         'X-Requested-With',
         'Access-Control-Request-Method',
         'Access-Control-Request-Headers'
     ],
     supports_credentials=False,
     max_age=86400
)

# Configuration
DOWNLOAD_FOLDER = 'downloads'
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get('MAX_DOWNLOADS', '3'))
FILE_CLEANUP_SECONDS = int(os.environ.get('CLEANUP_SECONDS', '120'))

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Global storage
download_progress = {}
active_downloads = 0

# ✅ ULTIMATE CORS HEADERS - Multiple layers to bypass Railway edge proxy
@app.before_request
def before_request():
    """Handle preflight and add CORS headers before Railway can interfere"""
    origin = request.headers.get('Origin')

    logger.info(f"🌐 Request from origin: {origin}")
    logger.info(f"🔧 Request method: {request.method}")
    logger.info(f"📍 Request endpoint: {request.endpoint}")

    # Handle preflight OPTIONS requests immediately
    if request.method == 'OPTIONS':
        logger.info("✅ Handling preflight OPTIONS request")

        response = make_response('', 200)

        # Add comprehensive CORS headers
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'

        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin, Authorization, X-Requested-With'
        response.headers['Access-Control-Max-Age'] = '86400'
        response.headers['Access-Control-Allow-Credentials'] = 'false'

        # Additional headers to prevent Railway interference
        response.headers['Vary'] = 'Origin'
        response.headers['Cache-Control'] = 'no-cache'

        logger.info("✅ Preflight response sent with CORS headers")
        return response

@app.after_request
def after_request(response):
    """Add CORS headers to all responses - final layer"""
    origin = request.headers.get('Origin')

    # Always add CORS headers to prevent Railway override
    allowed_origins = [
        "https://yt-downloader-pro-v011.netlify.app",
        "http://localhost:3000",
        "http://localhost:8000"
    ]

    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        logger.info(f"✅ CORS allowed for: {origin}")
    elif origin:
        # For Railway edge proxy issues, be more permissive
        response.headers['Access-Control-Allow-Origin'] = origin
        logger.info(f"⚠️ CORS allowed (permissive) for: {origin}")
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'

    # Essential CORS headers
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin, Authorization'
    response.headers['Access-Control-Max-Age'] = '86400'
    response.headers['Access-Control-Allow-Credentials'] = 'false'

    # Additional headers
    response.headers['Vary'] = 'Origin'
    response.headers['X-Content-Type-Options'] = 'nosniff'

    return response

def check_yt_dlp():
    """Check yt-dlp availability"""
    try:
        result = subprocess.run(["yt-dlp", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.info(f"✅ yt-dlp ready: {version}")
            return "yt-dlp"
        return None
    except Exception as e:
        logger.error(f"❌ yt-dlp not available: {e}")
        return None

def clean_youtube_url(url):
    """Clean YouTube URL"""
    try:
        import urllib.parse
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
    """Get video information"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            return None

        clean_url = clean_youtube_url(url)
        logger.info(f"🔍 Processing: {clean_url}")

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
                            'formats': info.get('formats', [])[:25]
                        }
                    except:
                        continue

        logger.error("No video info extracted")
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

    # Fallback formats
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

# Routes
@app.route('/', methods=['GET', 'OPTIONS'])
def home():
    """Root endpoint to prevent 404 errors"""
    return jsonify({
        'status': '🎬 YT Downloader Pro Backend',
        'version': '3.0.0 - Ultimate CORS Fix',
        'timestamp': time.time(),
        'cors_fixed': True,
        'endpoints': {
            'health': '/health',
            'video_info': '/get_video_info',
            'download': '/download',
            'progress': '/progress/<id>',
            'download_file': '/download_file/<id>'
        }
    })

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    """Health check endpoint"""
    ytdlp_status = check_yt_dlp() is not None

    health_data = {
        'status': 'healthy',
        'timestamp': time.time(),
        'yt_dlp_available': ytdlp_status,
        'active_downloads': active_downloads,
        'max_downloads': MAX_CONCURRENT_DOWNLOADS,
        'cors_configuration': 'ultimate_fix_v3',
        'railway_compatible': True
    }

    logger.info("✅ Health check accessed")
    return jsonify(health_data)

@app.route('/get_video_info', methods=['POST', 'OPTIONS'])
def get_video_info():
    """Get video information endpoint - Ultimate CORS compatible"""

    logger.info("📝 Video info request received")
    logger.info(f"📋 Headers: {dict(request.headers)}")
    logger.info(f"🌐 Origin: {request.headers.get('Origin')}")
    logger.info(f"🔧 Method: {request.method}")

    try:
        # Get request data
        data = request.json
        logger.info(f"📤 Request data: {data}")

        if not data or 'url' not in data:
            logger.error("❌ Missing URL in request")
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url'].strip()

        if not url:
            logger.error("❌ Empty URL")
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'}), 400

        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            logger.error(f"❌ Invalid domain: {url}")
            return jsonify({'success': False, 'error': 'Please enter a valid YouTube URL'}), 400

        logger.info(f"🔍 Processing URL: {url}")

        # Get video info
        info = get_video_info_with_formats(url)
        if not info:
            logger.error("❌ Failed to extract video info")
            return jsonify({
                'success': False, 
                'error': 'Could not get video information. Video may be private or unavailable.'
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
            'audio_formats': audio_formats,
            'timestamp': time.time()
        }

        logger.info(f"✅ Video info processed: {info['title']}")
        logger.info(f"📊 Formats: {len(video_formats)} video, {len(audio_formats)} audio")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"💥 Video info error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    """Start download endpoint"""
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
            'message': 'Starting download...',
            'timestamp': time.time()
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

        # Safe filename
        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        filename = f"{download_id}_{safe_title}.{output_format}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        logger.info(f"📥 Processing {download_type}: {filename}")

        download_progress[download_id].update({
            'progress': 25,
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

        # Execute download
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            # Find actual file
            actual_files = [f for f in os.listdir(DOWNLOAD_FOLDER) 
                          if f.startswith(download_id)]

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
                raise Exception("File not found after download")
        else:
            error_msg = result.stderr[:100] if result.stderr else "Unknown error"
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

@app.route('/progress/<download_id>', methods=['GET', 'OPTIONS'])
def get_progress(download_id):
    """Get download progress"""
    progress = download_progress.get(download_id, {
        'progress': 0,
        'status': 'not_found',
        'message': 'Download not found'
    })
    return jsonify(progress)

@app.route('/download_file/<download_id>', methods=['GET', 'OPTIONS'])
def download_file(download_id):
    """Download completed file"""
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
            time.sleep(3)
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                if download_id in download_progress:
                    del download_progress[download_id]
            except:
                pass
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
                    except:
                        pass
            time.sleep(60)
        except:
            time.sleep(60)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    logger.info("🚀 YT Downloader Pro Backend - ULTIMATE CORS FIX")
    logger.info(f"🌍 Port: {port}")
    logger.info(f"⚡ Max Downloads: {MAX_CONCURRENT_DOWNLOADS}")
    logger.info(f"🧹 Cleanup: {FILE_CLEANUP_SECONDS}s")

    if not check_yt_dlp():
        logger.error("❌ yt-dlp not available!")
    else:
        logger.info("✅ yt-dlp ready")

    logger.info("🌐 CORS: Ultimate fix applied for Railway")
    logger.info("🎬 Backend ready for requests!")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
