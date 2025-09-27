# EXACTLY WORKING BACKEND - RESTORED FROM SUCCESSFUL VERSION
# This version was successfully downloading 37MB, 69MB files as shown in logs

import os
import subprocess
import json
import uuid
import threading
import time
import logging
from flask import Flask, request, jsonify, send_file, after_this_request, make_response
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'working-restore-yt-downloader'

# CORS Configuration - keeping exactly as working
CORS(app,
     origins=[
         "https://yt-downloader-pro-v011.netlify.app",
         "http://localhost:3000",
         "http://localhost:8000", 
         "*"
     ],
     methods=['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'],
     allow_headers=['Content-Type', 'Accept', 'Origin', 'Authorization', 'X-Requested-With'],
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

@app.before_request
def before_request():
    """Handle preflight requests"""
    if request.method == 'OPTIONS':
        response = make_response('', 200)
        origin = request.headers.get('Origin')

        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'

        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin, Authorization'
        response.headers['Access-Control-Max-Age'] = '86400'

        return response

@app.after_request
def after_request(response):
    """Add CORS headers"""
    origin = request.headers.get('Origin')

    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'

    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin, Authorization'

    return response

def install_ffmpeg():
    """Install FFmpeg - keeping exactly as working"""
    try:
        logger.info("🔧 Installing FFmpeg...")

        # Try apt-get first
        try:
            subprocess.run(["apt-get", "update"], check=True, capture_output=True)
            result = subprocess.run(["apt-get", "install", "-y", "ffmpeg"], 
                                  check=True, capture_output=True, text=True)
            logger.info("✅ FFmpeg installed via apt-get")
            return True
        except:
            pass

        # Try static binary fallback
        try:
            os.makedirs('/tmp/ffmpeg', exist_ok=True)

            download_cmd = [
                "wget", "-O", "/tmp/ffmpeg.tar.xz",
                "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            ]
            subprocess.run(download_cmd, check=True, capture_output=True)

            extract_cmd = ["tar", "-xf", "/tmp/ffmpeg.tar.xz", "-C", "/tmp/ffmpeg", "--strip-components=1"]
            subprocess.run(extract_cmd, check=True, capture_output=True)

            os.chmod("/tmp/ffmpeg/ffmpeg", 0o755)
            os.environ['PATH'] = f"/tmp/ffmpeg:{os.environ.get('PATH', '')}"

            logger.info("✅ FFmpeg static binary installed")
            return True

        except Exception as e:
            logger.error(f"❌ Static binary install failed: {e}")

        return False

    except Exception as e:
        logger.error(f"❌ FFmpeg installation failed: {e}")
        return False

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            logger.info(f"✅ FFmpeg available: {version_line}")
            return True
        return False
    except:
        return False

def update_ytdlp():
    """Update yt-dlp - keeping exactly as working"""
    try:
        logger.info("🔄 Updating yt-dlp...")
        result = subprocess.run([
            "python", "-m", "pip", "install", "--upgrade", "yt-dlp"
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            logger.info("✅ yt-dlp updated successfully")
        else:
            logger.warning(f"⚠️ yt-dlp update failed: {result.stderr}")

    except Exception as e:
        logger.error(f"❌ yt-dlp update error: {e}")

def check_yt_dlp():
    """Check yt-dlp availability"""
    try:
        result = subprocess.run(["yt-dlp", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.info(f"✅ yt-dlp version: {version}")
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

def is_problematic_video(url):
    """Check if video has known extraction issues"""
    # List of known problematic videos
    problematic_ids = [
        'kJQP7kiw5Fk',  # Despacito - known extraction issues
        'V8zXLMIjlcw',  # From railway logs
        'udgrClXV26Y'   # From railway logs  
    ]

    for video_id in problematic_ids:
        if video_id in url:
            logger.warning(f"⚠️ Known problematic video detected: {video_id}")
            return True
    return False

def get_video_info_working(url):
    """Get video info using the exact method that was working before"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            return None

        clean_url = clean_youtube_url(url)
        logger.info(f"🔍 Processing with working extraction: {clean_url}")

        # Check for problematic videos first
        if is_problematic_video(clean_url):
            logger.warning("⚠️ Problematic video detected, using alternative method")
            return get_alternative_video_info(clean_url)

        # Use the exact command that was working before
        cmd = [
            ytdlp_exe, 
            "--dump-json",
            "--no-download",
            "--no-warnings",
            "--no-playlist",
            "--ignore-errors",
            "--extractor-retries", "3",
            "--sleep-interval", "1",
            clean_url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('{'):
                    try:
                        info = json.loads(line)
                        formats = info.get('formats', [])
                        logger.info(f"✅ Working extraction: {len(formats)} formats found")

                        return {
                            'title': info.get('title', 'Unknown')[:80],
                            'uploader': info.get('uploader', 'Unknown'),
                            'duration': info.get('duration', 0),
                            'view_count': info.get('view_count', 0),
                            'thumbnail': info.get('thumbnail', ''),
                            'formats': formats
                        }
                    except Exception as e:
                        logger.error(f"JSON parse error: {e}")
                        continue

        logger.error("❌ Working extraction failed")
        return None

    except Exception as e:
        logger.error(f"Working extraction error: {e}")
        return None

def get_alternative_video_info(url):
    """Alternative method for problematic videos"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            return None

        logger.info("🔄 Using alternative extraction method")

        # Use basic extraction with different options
        cmd = [
            ytdlp_exe,
            "--dump-json",
            "--no-download",
            "--ignore-errors",
            "--no-cache-dir",
            "--format", "worst",  # Get basic info only
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            try:
                info = json.loads(result.stdout.strip().split('\n')[0])

                # Create basic formats if none available
                basic_formats = [
                    {
                        'format_id': 'best',
                        'ext': 'mp4',
                        'height': 720,
                        'width': 1280,
                        'fps': 30,
                        'vcodec': 'avc1',
                        'acodec': 'mp4a'
                    },
                    {
                        'format_id': 'best[height<=480]',
                        'ext': 'mp4',
                        'height': 480,
                        'width': 854,
                        'fps': 30,
                        'vcodec': 'avc1',
                        'acodec': 'mp4a'
                    }
                ]

                logger.info("✅ Alternative extraction success")
                return {
                    'title': info.get('title', 'Unknown')[:80],
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': info.get('formats', basic_formats)
                }

            except:
                pass

    except Exception as e:
        logger.error(f"❌ Alternative extraction error: {e}")

    return None

def extract_working_formats(formats_data):
    """Extract formats using the exact method that was working"""

    video_formats = {}
    audio_formats = {}

    logger.info(f"🔍 Working format processing: {len(formats_data)} raw formats")

    # Quality mapping - keeping exactly as working
    quality_heights = {
        2160: '2160p', 1440: '1440p', 1080: '1080p', 720: '720p',
        480: '480p', 360: '360p', 240: '240p', 144: '144p'
    }

    try:
        # Process formats exactly as was working before
        for fmt in formats_data:
            try:
                format_id = fmt.get('format_id', '')
                ext = fmt.get('ext', '').lower()
                height = fmt.get('height')
                width = fmt.get('width')
                fps = fmt.get('fps', 30)
                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                filesize = fmt.get('filesize', 0)
                tbr = fmt.get('tbr', 0)
                abr = fmt.get('abr', 0)
                protocol = fmt.get('protocol', '')

                # Video formats with audio (standalone - no FFmpeg needed)
                if (height and vcodec != 'none' and acodec != 'none' and
                    ext in ['mp4', 'webm'] and protocol in ['https', 'http', '']):

                    quality = quality_heights.get(height, f"{height}p")

                    if quality not in video_formats:
                        video_formats[quality] = {}

                    if ext not in video_formats[quality]:
                        video_formats[quality][ext] = {
                            'format_id': format_id,
                            'ext': ext,
                            'quality': quality,
                            'height': height,
                            'width': width or (height * 16 // 9),
                            'fps': fps,
                            'has_audio': True,
                            'filesize': filesize,
                            'tbr': tbr,
                            'standalone': True
                        }

                        logger.info(f"✅ Standalone format: {quality} {ext.upper()}")

                # Video-only formats (need FFmpeg)
                elif (height and vcodec != 'none' and acodec == 'none' and
                      ext in ['mp4', 'webm'] and protocol in ['https', 'http', '']):

                    quality = quality_heights.get(height, f"{height}p")

                    if quality not in video_formats:
                        video_formats[quality] = {}

                    if ext not in video_formats[quality]:
                        video_formats[quality][ext] = {
                            'format_id': f"{format_id}+bestaudio",
                            'ext': ext,
                            'quality': quality,
                            'height': height,
                            'width': width or (height * 16 // 9),
                            'fps': fps,
                            'has_audio': True,  # Will have after merging
                            'filesize': filesize,
                            'tbr': tbr,
                            'standalone': False
                        }

                        logger.info(f"✅ Merge format: {quality} {ext.upper()}")

                # Audio formats
                elif (acodec != 'none' and vcodec == 'none' and
                      protocol in ['https', 'http', '']):

                    quality_label = f"{abr}kbps" if abr else "Unknown Quality"

                    if ext not in audio_formats:
                        audio_formats[ext] = {}

                    if quality_label not in audio_formats[ext]:
                        audio_formats[ext][quality_label] = {
                            'format_id': format_id,
                            'ext': ext,
                            'quality': quality_label,
                            'abr': abr,
                            'filesize': filesize
                        }

                        logger.info(f"✅ Audio format: {ext.upper()} {quality_label}")

            except Exception as e:
                logger.warning(f"⚠️ Format processing error: {e}")
                continue

    except Exception as e:
        logger.error(f"❌ Format extraction error: {e}")

    # Add working fallbacks exactly as before
    if len(video_formats) < 3:
        logger.warning("⚠️ Adding working fallbacks")

        working_fallbacks = {
            '1080p': {
                'mp4': {
                    'format_id': 'best[height<=1080]',
                    'ext': 'mp4',
                    'quality': '1080p',
                    'height': 1080,
                    'width': 1920,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'standalone': True
                }
            },
            '720p': {
                'mp4': {
                    'format_id': 'best[height<=720]',
                    'ext': 'mp4',
                    'quality': '720p',
                    'height': 720,
                    'width': 1280,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'standalone': True
                }
            },
            '480p': {
                'mp4': {
                    'format_id': 'best[height<=480]',
                    'ext': 'mp4',
                    'quality': '480p',
                    'height': 480,
                    'width': 854,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'standalone': True
                }
            },
            '360p': {
                'mp4': {
                    'format_id': 'best[height<=360]',
                    'ext': 'mp4',
                    'quality': '360p',
                    'height': 360,
                    'width': 640,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'standalone': True
                }
            }
        }

        for quality, formats in working_fallbacks.items():
            if quality not in video_formats:
                video_formats[quality] = formats

    # Add audio fallbacks
    if len(audio_formats) < 2:
        logger.warning("⚠️ Adding audio fallbacks")

        audio_fallbacks = {
            'mp3': {
                'High Quality': {
                    'format_id': 'bestaudio',
                    'ext': 'mp3',
                    'quality': 'High Quality',
                    'convert': True,
                    'abr': 320
                }
            },
            'm4a': {
                'Best Quality': {
                    'format_id': 'bestaudio[ext=m4a]',
                    'ext': 'm4a',
                    'quality': 'Best Quality',
                    'abr': 256
                }
            }
        }

        for ext, qualities in audio_fallbacks.items():
            if ext not in audio_formats:
                audio_formats[ext] = qualities

    # Final counts
    video_count = sum(len(quality_formats) for quality_formats in video_formats.values())
    audio_count = sum(len(format_formats) for format_formats in audio_formats.values())

    logger.info(f"✅ Working format extraction complete:")
    logger.info(f"📹 Video formats: {video_count} total across {len(video_formats)} qualities")
    logger.info(f"🎵 Audio formats: {audio_count} total")

    return video_formats, audio_formats

# Routes - keeping exactly as working
@app.route('/', methods=['GET', 'OPTIONS'])
def home():
    """Root endpoint"""
    return jsonify({
        'status': '🎬 YT Downloader Pro - Working Restore Edition',
        'version': '8.0.0 - Exactly As Working',
        'timestamp': time.time(),
        'features': ['Restored working extraction', 'Problematic video handling', 'Stable performance']
    })

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    """Health check"""
    ytdlp_status = check_yt_dlp() is not None
    ffmpeg_status = check_ffmpeg()

    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'yt_dlp_available': ytdlp_status,
        'ffmpeg_available': ffmpeg_status,
        'active_downloads': active_downloads,
        'extraction_method': 'working_restored'
    })

@app.route('/get_video_info', methods=['POST', 'OPTIONS'])
def get_video_info():
    """Working video info extraction exactly as before"""

    try:
        data = request.json

        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url'].strip()

        if not url:
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'}), 400

        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'success': False, 'error': 'Please enter a valid YouTube URL'}), 400

        logger.info(f"🔍 Working video info processing: {url}")

        # Use working extraction method
        info = get_video_info_working(url)

        if not info:
            logger.error(f"❌ Working video info extraction failed for: {url}")
            return jsonify({
                'success': False, 
                'error': 'Unable to process this video. It may be private, region-restricted, or temporarily unavailable. Please try a different video or try again later.'
            }), 200

        # Extract formats using working method
        video_formats, audio_formats = extract_working_formats(info['formats'])

        # Ensure we have formats
        if not video_formats and not audio_formats:
            logger.error("❌ No formats extracted using working method")
            return jsonify({
                'success': False,
                'error': 'No downloadable formats found for this video. The video may be protected or have unusual encoding.'
            }), 200

        response_data = {
            'success': True,
            'title': info['title'],
            'thumbnail': info['thumbnail'],
            'uploader': info['uploader'],
            'duration': info['duration'],
            'view_count': info['view_count'],
            'video_formats': video_formats,
            'audio_formats': audio_formats,
            'extraction_method': 'working_restored',
            'format_stats': {
                'total_video_formats': sum(len(q) for q in video_formats.values()),
                'total_audio_formats': sum(len(t) for t in audio_formats.values()),
                'video_qualities': list(video_formats.keys()),
                'audio_types': list(audio_formats.keys())
            },
            'timestamp': time.time()
        }

        logger.info(f"✅ Working extraction success: {info['title']}")
        logger.info(f"📊 Working formats: {response_data['format_stats']['total_video_formats']} video, {response_data['format_stats']['total_audio_formats']} audio")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"💥 Working video info error: {e}")
        return jsonify({
            'success': False, 
            'error': 'Server error while processing video. Please try again in a few moments.'
        }), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    """Start download with working method"""
    global active_downloads

    if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
        return jsonify({'success': False, 'error': 'Server busy. Please try again later.'}), 429

    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        download_id = str(uuid.uuid4())[:8]
        logger.info(f"🚀 Starting working download {download_id}")

        download_progress[download_id] = {
            'progress': 0,
            'status': 'starting',
            'message': 'Starting download...',
            'timestamp': time.time()
        }

        thread = threading.Thread(
            target=process_working_download,
            args=(download_id, data),
            daemon=True
        )
        thread.start()
        active_downloads += 1

        return jsonify({'success': True, 'download_id': download_id})

    except Exception as e:
        logger.error(f"Download start error: {e}")
        return jsonify({'success': False, 'error': 'Failed to start download'}), 500

def process_working_download(download_id, data):
    """Working download processing exactly as successful before"""
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

        # Check FFmpeg exactly as working
        ffmpeg_available = check_ffmpeg()
        if not ffmpeg_available and download_type == 'video' and '+' in format_id:
            ffmpeg_available = install_ffmpeg()

        # Safe filename exactly as working
        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        filename = f"{download_id}_{safe_title}.{output_format}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        logger.info(f"📥 Working download: {filename}")
        logger.info(f"🎯 Format: {format_id}")
        logger.info(f"🔧 FFmpeg available: {ffmpeg_available}")

        download_progress[download_id].update({
            'progress': 25,
            'status': 'downloading',
            'message': f'Downloading {download_type}...'
        })

        # Build command exactly as working
        if download_type == 'audio':
            if 'mp3' in output_format.lower() and ffmpeg_available:
                cmd = [ytdlp_exe, "-f", "bestaudio", "--extract-audio", 
                       "--audio-format", "mp3", "--audio-quality", "0",
                       "--no-warnings", "-o", filepath, url]
            else:
                cmd = [ytdlp_exe, "-f", "bestaudio", "--no-warnings", "-o", filepath, url]
        else:
            # Video download exactly as working
            if ffmpeg_available and '+' in format_id:
                cmd = [ytdlp_exe, 
                       "-f", format_id,
                       "--merge-output-format", output_format,
                       "--no-warnings",
                       "--retries", "3",
                       "-o", filepath, url]
            else:
                # Fallback exactly as working
                cmd = [ytdlp_exe,
                       "-f", "best",
                       "--no-warnings",
                       "--retries", "3",
                       "-o", filepath, url]

        logger.info(f"🔧 Working command: {' '.join(cmd[:6])}...")

        # Execute exactly as working
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

        if result.returncode == 0:
            # Find downloaded file exactly as working
            actual_files = [f for f in os.listdir(DOWNLOAD_FOLDER) 
                          if f.startswith(download_id)]

            if actual_files:
                actual_file = actual_files[0]
                actual_path = os.path.join(DOWNLOAD_FOLDER, actual_file)

                if os.path.exists(actual_path):
                    file_size = os.path.getsize(actual_path)

                    if file_size > 1000:
                        download_progress[download_id].update({
                            'progress': 100,
                            'status': 'completed',
                            'message': f'Download completed! ({file_size} bytes)',
                            'filename': actual_file,
                            'filepath': actual_path,
                            'filesize': file_size
                        })

                        logger.info(f"✅ Working download completed: {actual_file} ({file_size} bytes)")
                    else:
                        raise Exception("Downloaded file too small")
                else:
                    raise Exception("File not found after download")
            else:
                raise Exception("No files found after download")
        else:
            error_msg = result.stderr[:200] if result.stderr else result.stdout[:200]
            raise Exception(f"Download failed: {error_msg}")

    except Exception as e:
        logger.error(f"❌ Working download {download_id} failed: {e}")
        download_progress[download_id].update({
            'progress': 0,
            'status': 'error',
            'message': f'Download failed: {str(e)[:100]}'
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
            time.sleep(5)
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"🗑️ Cleaned up: {filename}")
                if download_id in download_progress:
                    del download_progress[download_id]
            except:
                pass
        threading.Thread(target=delayed_cleanup, daemon=True).start()
        return response

    clean_name = filename[9:] if filename.startswith(download_id) else filename
    return send_file(filepath, as_attachment=True, download_name=clean_name)

# Background cleanup exactly as working
def cleanup_old_files():
    """Background cleanup"""
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

    logger.info("🚀 YT Downloader Pro - WORKING RESTORE EDITION")
    logger.info(f"🌍 Port: {port}")
    logger.info(f"⚡ Max Downloads: {MAX_CONCURRENT_DOWNLOADS}")

    # Setup exactly as working
    update_ytdlp()

    ffmpeg_installed = install_ffmpeg()
    if ffmpeg_installed:
        logger.info("✅ FFmpeg ready")
    else:
        logger.warning("⚠️ FFmpeg installation failed - using fallbacks")

    if not check_yt_dlp():
        logger.error("❌ yt-dlp not available!")
    else:
        logger.info("✅ yt-dlp ready with working extraction")

    logger.info("🎬 Backend ready with working restoration!")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
