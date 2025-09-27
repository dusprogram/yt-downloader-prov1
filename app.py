# COMPLETE FIXED BACKEND - Proper Error Handling & Extraction Stability
# Only fixing the exact error handling issues, everything else unchanged

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
app.secret_key = 'error-fixed-yt-downloader'

# CORS Configuration
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
    """Install FFmpeg - keeping existing working method"""
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

        # Try static binary
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
    """Update yt-dlp to latest version"""
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

def get_video_info_with_retries(url, max_retries=3):
    """Get video info with multiple retry strategies"""

    ytdlp_exe = check_yt_dlp()
    if not ytdlp_exe:
        logger.error("❌ yt-dlp not available")
        return None

    clean_url = clean_youtube_url(url)
    logger.info(f"🔍 Robust processing: {clean_url}")

    # Strategy 1: Standard extraction
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Attempt {attempt + 1}: Standard extraction")

            cmd = [
                ytdlp_exe, 
                "--dump-json",
                "--no-download",
                "--no-warnings",
                "--no-playlist",
                "--ignore-errors",
                "--extractor-retries", "2",
                "--sleep-interval", "1",
                clean_url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('{'):
                        try:
                            info = json.loads(line)
                            formats = info.get('formats', [])

                            if formats and len(formats) > 0:
                                logger.info(f"✅ Standard extraction success: {len(formats)} formats")
                                return {
                                    'title': info.get('title', 'Unknown')[:80],
                                    'uploader': info.get('uploader', 'Unknown'),
                                    'duration': info.get('duration', 0),
                                    'view_count': info.get('view_count', 0),
                                    'thumbnail': info.get('thumbnail', ''),
                                    'formats': formats
                                }
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ JSON decode error: {e}")
                            continue

            logger.warning(f"⚠️ Attempt {attempt + 1} failed, retrying...")
            time.sleep(1)  # Brief delay between retries

        except Exception as e:
            logger.warning(f"⚠️ Attempt {attempt + 1} error: {e}")
            time.sleep(1)

    # Strategy 2: Fallback with different options
    try:
        logger.info("🔄 Trying fallback extraction method...")

        fallback_cmd = [
            ytdlp_exe,
            "--dump-json", 
            "--no-download",
            "--ignore-config",
            "--ignore-errors",
            "--no-cache-dir",
            clean_url
        ]

        result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=45)

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('{'):
                    try:
                        info = json.loads(line)
                        formats = info.get('formats', [])

                        if formats:
                            logger.info(f"✅ Fallback extraction success: {len(formats)} formats")
                            return {
                                'title': info.get('title', 'Unknown')[:80],
                                'uploader': info.get('uploader', 'Unknown'),
                                'duration': info.get('duration', 0),
                                'view_count': info.get('view_count', 0),
                                'thumbnail': info.get('thumbnail', ''),
                                'formats': formats
                            }
                    except:
                        continue

    except Exception as e:
        logger.error(f"❌ Fallback extraction error: {e}")

    # Strategy 3: Basic info only
    try:
        logger.info("🔄 Trying basic info extraction...")

        basic_cmd = [ytdlp_exe, "--dump-json", "--no-download", "--format", "worst", clean_url]
        result = subprocess.run(basic_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            try:
                info = json.loads(result.stdout.strip().split('\n')[0])
                # Create basic format list if formats missing
                basic_formats = [
                    {
                        'format_id': 'best',
                        'ext': 'mp4',
                        'height': 720,
                        'width': 1280,
                        'fps': 30,
                        'vcodec': 'avc1',
                        'acodec': 'mp4a'
                    }
                ]

                logger.info("✅ Basic info extraction success")
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
        logger.error(f"❌ Basic extraction error: {e}")

    logger.error("❌ All extraction methods failed")
    return None

def extract_robust_formats(formats_data):
    """Extract formats with robust error handling"""

    video_formats = {}
    audio_formats = {}

    logger.info(f"🔍 Robust format processing: {len(formats_data)} raw formats")

    # Quality mapping
    quality_heights = {
        2160: '2160p', 1440: '1440p', 1080: '1080p', 720: '720p',
        480: '480p', 360: '360p', 240: '240p', 144: '144p'
    }

    try:
        # Process formats safely
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

                # Video formats (with audio - standalone)
                if (height and vcodec != 'none' and acodec != 'none' and
                    ext in ['mp4', 'webm'] and height >= 144):

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

                        logger.info(f"✅ Video format: {quality} {ext.upper()}")

                # Video-only formats 
                elif (height and vcodec != 'none' and acodec == 'none' and
                      ext in ['mp4', 'webm'] and height >= 144):

                    quality = quality_heights.get(height, f"{height}p")

                    if quality not in video_formats:
                        video_formats[quality] = {}

                    # Only add if no standalone version exists
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

                # Audio formats
                elif (acodec != 'none' and vcodec == 'none'):
                    quality_label = f"{abr}kbps" if abr else "Unknown Quality"

                    if ext not in audio_formats:
                        audio_formats[ext] = {}

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

    # Add comprehensive fallbacks if extraction yielded few formats
    if len(video_formats) < 3:
        logger.warning("⚠️ Adding robust fallbacks")

        fallback_formats = {
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

        for quality, formats in fallback_formats.items():
            if quality not in video_formats:
                video_formats[quality] = formats

    # Add basic audio formats if needed
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

    logger.info(f"✅ Robust format extraction complete:")
    logger.info(f"📹 Video formats: {video_count} total across {len(video_formats)} qualities")
    logger.info(f"🎵 Audio formats: {audio_count} total")

    return video_formats, audio_formats

# Routes
@app.route('/', methods=['GET', 'OPTIONS'])
def home():
    """Root endpoint"""
    return jsonify({
        'status': '🎬 YT Downloader Pro - Error Fixed Edition',
        'version': '7.0.0 - Robust Error Handling',
        'timestamp': time.time(),
        'features': ['Multi-retry extraction', 'Robust error handling', 'Fallback methods']
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
        'error_handling': 'robust'
    })

@app.route('/get_video_info', methods=['POST', 'OPTIONS'])
def get_video_info():
    """Robust video info extraction with proper error handling"""

    try:
        data = request.json

        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url'].strip()

        if not url:
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'}), 400

        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'success': False, 'error': 'Please enter a valid YouTube URL'}), 400

        logger.info(f"🔍 Robust video info processing: {url}")

        # Use robust extraction with retries
        info = get_video_info_with_retries(url)

        if not info:
            # Return proper error response (not 404)
            logger.error(f"❌ Video info extraction failed for: {url}")
            return jsonify({
                'success': False, 
                'error': 'Unable to process this video. It may be private, region-restricted, or temporarily unavailable. Please try a different video or try again later.'
            }), 200  # Return 200 with error message, not 404

        # Extract formats robustly
        video_formats, audio_formats = extract_robust_formats(info['formats'])

        # Always ensure we have some formats
        if not video_formats and not audio_formats:
            logger.error("❌ No formats extracted")
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
            'extraction_method': 'robust_multi_retry',
            'format_stats': {
                'total_video_formats': sum(len(q) for q in video_formats.values()),
                'total_audio_formats': sum(len(t) for t in audio_formats.values()),
                'video_qualities': list(video_formats.keys()),
                'audio_types': list(audio_formats.keys())
            },
            'timestamp': time.time()
        }

        logger.info(f"✅ Robust extraction success: {info['title']}")
        logger.info(f"📊 Final formats: {response_data['format_stats']['total_video_formats']} video, {response_data['format_stats']['total_audio_formats']} audio")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"💥 Robust video info error: {e}")
        return jsonify({
            'success': False, 
            'error': 'Server error while processing video. Please try again in a few moments.'
        }), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    """Start download with robust error handling"""
    global active_downloads

    if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
        return jsonify({'success': False, 'error': 'Server busy. Please try again later.'}), 429

    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        download_id = str(uuid.uuid4())[:8]
        logger.info(f"🚀 Starting robust download {download_id}")

        download_progress[download_id] = {
            'progress': 0,
            'status': 'starting',
            'message': 'Starting download...',
            'timestamp': time.time()
        }

        thread = threading.Thread(
            target=process_robust_download,
            args=(download_id, data),
            daemon=True
        )
        thread.start()
        active_downloads += 1

        return jsonify({'success': True, 'download_id': download_id})

    except Exception as e:
        logger.error(f"Download start error: {e}")
        return jsonify({'success': False, 'error': 'Failed to start download'}), 500

def process_robust_download(download_id, data):
    """Robust download processing"""
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

        # Check FFmpeg
        ffmpeg_available = check_ffmpeg()
        if not ffmpeg_available and download_type == 'video' and '+' in format_id:
            ffmpeg_available = install_ffmpeg()

        # Safe filename
        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        filename = f"{download_id}_{safe_title}.{output_format}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        logger.info(f"📥 Robust download: {filename}")
        logger.info(f"🎯 Format: {format_id}")
        logger.info(f"🔧 FFmpeg available: {ffmpeg_available}")

        download_progress[download_id].update({
            'progress': 25,
            'status': 'downloading',
            'message': f'Downloading {download_type}...'
        })

        # Build robust command
        if download_type == 'audio':
            if 'mp3' in output_format.lower() and ffmpeg_available:
                cmd = [ytdlp_exe, "-f", "bestaudio", "--extract-audio", 
                       "--audio-format", "mp3", "--audio-quality", "0",
                       "--no-warnings", "-o", filepath, url]
            else:
                cmd = [ytdlp_exe, "-f", "bestaudio", "--no-warnings", "-o", filepath, url]
        else:
            # Video download
            if ffmpeg_available and '+' in format_id:
                cmd = [ytdlp_exe, 
                       "-f", format_id,
                       "--merge-output-format", output_format,
                       "--no-warnings",
                       "--retries", "3",
                       "-o", filepath, url]
            else:
                # Fallback: use simpler format
                simple_format = format_id.split('+')[0] if '+' in format_id else format_id
                cmd = [ytdlp_exe,
                       "-f", f"best[height<={simple_format.replace('p', '') if 'p' in format_id else '720'}]/best",
                       "--no-warnings",
                       "--retries", "3",
                       "-o", filepath, url]

        logger.info(f"🔧 Robust command: {' '.join(cmd[:6])}...")

        # Execute with timeout
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

        if result.returncode == 0:
            # Find downloaded file
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

                        logger.info(f"✅ Robust download completed: {actual_file} ({file_size} bytes)")
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
        logger.error(f"❌ Robust download {download_id} failed: {e}")
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

# Background cleanup
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

    logger.info("🚀 YT Downloader Pro - ERROR FIXED EDITION")
    logger.info(f"🌍 Port: {port}")
    logger.info(f"⚡ Max Downloads: {MAX_CONCURRENT_DOWNLOADS}")

    # Setup on startup
    update_ytdlp()

    ffmpeg_installed = install_ffmpeg()
    if ffmpeg_installed:
        logger.info("✅ FFmpeg ready")
    else:
        logger.warning("⚠️ FFmpeg installation failed - using fallbacks")

    if not check_yt_dlp():
        logger.error("❌ yt-dlp not available!")
    else:
        logger.info("✅ yt-dlp ready with robust error handling")

    logger.info("🎬 Backend ready with robust error handling!")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
