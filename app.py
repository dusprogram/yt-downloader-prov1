# COMPLETE FFMPEG SOLUTION - Railway Compatible Backend
# Fixes FFmpeg missing issue + provides fallback options

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
app.secret_key = 'ffmpeg-fixed-yt-downloader'

# ✅ ULTIMATE CORS CONFIGURATION
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
    """Install FFmpeg on Railway - Multiple methods"""
    try:
        logger.info("🔧 Installing FFmpeg for Railway...")

        # Method 1: Try apt-get (Ubuntu/Debian based)
        try:
            subprocess.run(["apt-get", "update"], check=True, capture_output=True)
            result = subprocess.run(["apt-get", "install", "-y", "ffmpeg"], 
                                  check=True, capture_output=True, text=True)
            logger.info("✅ FFmpeg installed via apt-get")
            return True
        except:
            logger.info("⚠️ apt-get method failed, trying alternatives...")

        # Method 2: Try package manager alternatives
        package_managers = [
            ["yum", "install", "-y", "ffmpeg"],
            ["dnf", "install", "-y", "ffmpeg"], 
            ["pacman", "-S", "--noconfirm", "ffmpeg"]
        ]

        for cmd in package_managers:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"✅ FFmpeg installed via {cmd[0]}")
                return True
            except:
                continue

        # Method 3: Download static binary
        try:
            logger.info("🔧 Downloading static FFmpeg binary...")

            # Create ffmpeg directory
            os.makedirs('/tmp/ffmpeg', exist_ok=True)

            # Download static binary (Linux x64)
            download_cmd = [
                "wget", "-O", "/tmp/ffmpeg.tar.xz",
                "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            ]
            subprocess.run(download_cmd, check=True, capture_output=True)

            # Extract binary
            extract_cmd = ["tar", "-xf", "/tmp/ffmpeg.tar.xz", "-C", "/tmp/ffmpeg", "--strip-components=1"]
            subprocess.run(extract_cmd, check=True, capture_output=True)

            # Make executable and add to PATH
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
        logger.warning("⚠️ FFmpeg not found")
        return False

def update_ytdlp():
    """Update yt-dlp to latest version"""
    try:
        logger.info("🔄 Updating yt-dlp to latest version...")
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
    """Check and update yt-dlp"""
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

def get_video_info_modern(url):
    """Modern video info extraction - FFmpeg compatible"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            return None

        clean_url = clean_youtube_url(url)
        logger.info(f"🔍 Processing with FFmpeg support: {clean_url}")

        # Enhanced command for better format detection
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
                        logger.info(f"✅ Format extraction: {len(formats)} formats found")

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

        logger.error("❌ Format extraction failed")
        return None

    except Exception as e:
        logger.error(f"Format extraction error: {e}")
        return None

def extract_ffmpeg_compatible_formats(formats_data):
    """Extract formats with FFmpeg compatibility in mind"""

    video_formats = {}
    audio_formats = {}

    logger.info(f"🔍 FFmpeg-compatible processing: {len(formats_data)} raw formats")

    # Quality mapping
    quality_heights = {
        2160: '2160p', 1440: '1440p', 1080: '1080p', 720: '720p',
        480: '480p', 360: '360p', 240: '240p', 144: '144p'
    }

    # Track best standalone formats (no FFmpeg needed)
    standalone_video = {}
    standalone_audio = {}

    # Process all formats
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

            # Standalone video formats (video + audio, no merging needed)
            if (height and vcodec != 'none' and acodec != 'none' and
                ext in ['mp4', 'webm'] and protocol in ['https', 'http', '']):

                quality = quality_heights.get(height, f"{height}p")

                if quality not in standalone_video:
                    standalone_video[quality] = {}

                # Prefer these formats as they don't need FFmpeg
                standalone_video[quality][ext] = {
                    'format_id': format_id,
                    'ext': ext,
                    'quality': quality,
                    'height': height,
                    'width': width or (height * 16 // 9),
                    'fps': fps,
                    'has_audio': True,
                    'filesize': filesize,
                    'tbr': tbr,
                    'standalone': True,  # No FFmpeg needed
                    'ffmpeg_required': False
                }

                logger.info(f"✅ Standalone format (no FFmpeg): {quality} {ext.upper()}")

            # Video-only formats (will need audio merging if FFmpeg available)
            elif (height and vcodec != 'none' and acodec == 'none' and
                  ext in ['mp4', 'webm'] and protocol in ['https', 'http', '']):

                quality = quality_heights.get(height, f"{height}p")

                if quality not in video_formats:
                    video_formats[quality] = {}

                video_formats[quality][ext] = {
                    'format_id': format_id,
                    'ext': ext,
                    'quality': quality,
                    'height': height,
                    'width': width or (height * 16 // 9),
                    'fps': fps,
                    'has_audio': False,
                    'filesize': filesize,
                    'tbr': tbr,
                    'standalone': False,
                    'ffmpeg_required': True  # Needs FFmpeg for audio merging
                }

            # Audio-only formats
            elif (acodec != 'none' and vcodec == 'none' and
                  protocol in ['https', 'http', '']):

                quality_label = f"{abr}kbps" if abr else "Unknown Quality"

                if ext not in audio_formats:
                    audio_formats[ext] = {}

                audio_formats[ext][quality_label] = {
                    'format_id': format_id,
                    'ext': ext,
                    'quality': quality_label,
                    'abr': abr,
                    'filesize': filesize,
                    'standalone': True,
                    'ffmpeg_required': False
                }

                logger.info(f"✅ Audio format: {ext.upper()} {quality_label}")

        except Exception as e:
            logger.error(f"Format processing error: {e}")
            continue

    # Prioritize standalone formats, add FFmpeg-dependent as secondary
    final_video_formats = {}

    # Add standalone formats first (highest priority)
    for quality, formats in standalone_video.items():
        if quality not in final_video_formats:
            final_video_formats[quality] = {}
        final_video_formats[quality].update(formats)

    # Add FFmpeg-dependent formats as alternatives
    for quality, formats in video_formats.items():
        if quality not in final_video_formats:
            final_video_formats[quality] = {}

        for ext, format_data in formats.items():
            # Only add if we don't have a standalone version
            if ext not in final_video_formats[quality]:
                # Modify format_id to include audio merging
                format_data['format_id'] = f"{format_data['format_id']}+bestaudio"
                format_data['has_audio'] = True  # Will have after merging
                final_video_formats[quality][ext] = format_data

    # Add comprehensive fallbacks if limited formats
    if len(final_video_formats) < 3:
        logger.warning("⚠️ Adding comprehensive fallbacks")

        fallback_formats = {
            '1080p': {
                'mp4': {
                    'format_id': 'best[height<=1080]',  # Single stream, no merging
                    'ext': 'mp4',
                    'quality': '1080p',
                    'height': 1080,
                    'width': 1920,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'standalone': True,
                    'ffmpeg_required': False
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
                    'standalone': True,
                    'ffmpeg_required': False
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
                    'standalone': True,
                    'ffmpeg_required': False
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
                    'standalone': True,
                    'ffmpeg_required': False
                }
            }
        }

        for quality, formats in fallback_formats.items():
            if quality not in final_video_formats:
                final_video_formats[quality] = formats

    # Add comprehensive audio formats
    if len(audio_formats) < 2:
        logger.warning("⚠️ Adding audio fallbacks")

        audio_fallbacks = {
            'mp3': {
                'High Quality (320kbps)': {
                    'format_id': 'bestaudio',
                    'ext': 'mp3',
                    'quality': 'High Quality (320kbps)',
                    'convert': True,
                    'abr': 320,
                    'standalone': False,
                    'ffmpeg_required': True  # MP3 conversion needs FFmpeg
                },
                'Good Quality (192kbps)': {
                    'format_id': 'bestaudio',
                    'ext': 'mp3',
                    'quality': 'Good Quality (192kbps)', 
                    'convert': True,
                    'abr': 192,
                    'standalone': False,
                    'ffmpeg_required': True
                }
            },
            'm4a': {
                'Best Quality': {
                    'format_id': 'bestaudio[ext=m4a]',
                    'ext': 'm4a',
                    'quality': 'Best Quality',
                    'abr': 256,
                    'standalone': True,
                    'ffmpeg_required': False
                }
            }
        }

        for ext, qualities in audio_fallbacks.items():
            if ext not in audio_formats:
                audio_formats[ext] = qualities
            else:
                audio_formats[ext].update(qualities)

    # Final counts
    video_count = sum(len(quality_formats) for quality_formats in final_video_formats.values())
    audio_count = sum(len(format_formats) for format_formats in audio_formats.values())

    logger.info(f"✅ FFmpeg-compatible extraction complete:")
    logger.info(f"📹 Video formats: {video_count} total across {len(final_video_formats)} qualities")
    logger.info(f"🎵 Audio formats: {audio_count} total")

    return final_video_formats, audio_formats

# Routes
@app.route('/', methods=['GET', 'OPTIONS'])
def home():
    """Root endpoint"""
    ffmpeg_status = check_ffmpeg()

    return jsonify({
        'status': '🎬 YT Downloader Pro - FFmpeg Fixed Edition',
        'version': '6.0.0 - FFmpeg Solution',
        'timestamp': time.time(),
        'ffmpeg_available': ffmpeg_status,
        'features': ['FFmpeg auto-install', 'Standalone format priority', 'No-merge fallbacks']
    })

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    """Health check with FFmpeg status"""
    ytdlp_status = check_yt_dlp() is not None
    ffmpeg_status = check_ffmpeg()

    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'yt_dlp_available': ytdlp_status,
        'ffmpeg_available': ffmpeg_status,
        'active_downloads': active_downloads,
        'ffmpeg_solution': 'deployed'
    })

@app.route('/get_video_info', methods=['POST', 'OPTIONS'])
def get_video_info():
    """FFmpeg-compatible video info extraction"""

    try:
        data = request.json

        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url'].strip()

        if not url:
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'}), 400

        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'success': False, 'error': 'Please enter a valid YouTube URL'}), 400

        logger.info(f"🔍 FFmpeg-compatible processing: {url}")

        # Get video info with FFmpeg awareness
        info = get_video_info_modern(url)
        if not info:
            return jsonify({
                'success': False, 
                'error': 'Could not extract video information. Video may be private or region-restricted.'
            }), 404

        # Extract FFmpeg-compatible formats
        video_formats, audio_formats = extract_ffmpeg_compatible_formats(info['formats'])

        ffmpeg_status = check_ffmpeg()

        response_data = {
            'success': True,
            'title': info['title'],
            'thumbnail': info['thumbnail'],
            'uploader': info['uploader'],
            'duration': info['duration'],
            'view_count': info['view_count'],
            'video_formats': video_formats,
            'audio_formats': audio_formats,
            'extraction_method': 'ffmpeg_compatible',
            'ffmpeg_available': ffmpeg_status,
            'format_stats': {
                'total_video_formats': sum(len(q) for q in video_formats.values()),
                'total_audio_formats': sum(len(t) for t in audio_formats.values()),
                'video_qualities': list(video_formats.keys()),
                'audio_types': list(audio_formats.keys()),
                'standalone_priority': True
            },
            'timestamp': time.time()
        }

        logger.info(f"✅ FFmpeg-compatible extraction: {info['title']}")
        logger.info(f"📊 FFmpeg-aware formats: {response_data['format_stats']['total_video_formats']} video, {response_data['format_stats']['total_audio_formats']} audio")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"💥 FFmpeg-compatible extraction error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    """FFmpeg-compatible download start"""
    global active_downloads

    if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
        return jsonify({'success': False, 'error': 'Server busy. Please try again later.'}), 429

    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        download_id = str(uuid.uuid4())[:8]
        logger.info(f"🚀 Starting FFmpeg-compatible download {download_id}")

        download_progress[download_id] = {
            'progress': 0,
            'status': 'starting',
            'message': 'Starting download...',
            'timestamp': time.time()
        }

        thread = threading.Thread(
            target=process_ffmpeg_compatible_download,
            args=(download_id, data),
            daemon=True
        )
        thread.start()
        active_downloads += 1

        return jsonify({'success': True, 'download_id': download_id})

    except Exception as e:
        logger.error(f"Download start error: {e}")
        return jsonify({'success': False, 'error': 'Failed to start download'}), 500

def process_ffmpeg_compatible_download(download_id, data):
    """FFmpeg-compatible download processing with intelligent format selection"""
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

        # Check FFmpeg availability
        ffmpeg_available = check_ffmpeg()

        if not ffmpeg_available and download_type == 'video':
            logger.warning("⚠️ FFmpeg not available, installing...")
            ffmpeg_available = install_ffmpeg()

        # Safe filename
        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        filename = f"{download_id}_{safe_title}.{output_format}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        logger.info(f"📥 FFmpeg-aware download: {filename}")
        logger.info(f"🎯 Format: {format_id}")
        logger.info(f"🔧 FFmpeg available: {ffmpeg_available}")

        download_progress[download_id].update({
            'progress': 25,
            'status': 'downloading',
            'message': f'Downloading {download_type}...'
        })

        # Build command based on FFmpeg availability
        if download_type == 'audio':
            if 'mp3' in output_format.lower():
                if ffmpeg_available:
                    # MP3 conversion with FFmpeg
                    cmd = [ytdlp_exe, "-f", "bestaudio", "--extract-audio", 
                           "--audio-format", "mp3", "--audio-quality", "0",
                           "--no-warnings", "-o", filepath, url]
                else:
                    # Fallback: download best audio format without conversion
                    cmd = [ytdlp_exe, "-f", "bestaudio[ext=m4a]/bestaudio", 
                           "--no-warnings", "-o", filepath.replace('.mp3', '.%(ext)s'), url]
            else:
                # Direct audio download (no FFmpeg needed)
                cmd = [ytdlp_exe, "-f", format_id, "--no-warnings", "-o", filepath, url]
        else:
            # Video download with FFmpeg intelligence
            if ffmpeg_available and '+' in format_id:
                # FFmpeg available: can merge video+audio
                cmd = [ytdlp_exe, 
                       "-f", format_id,
                       "--merge-output-format", output_format,
                       "--no-warnings",
                       "-o", filepath, url]
            elif ffmpeg_available:
                # FFmpeg available: ensure best quality with audio
                cmd = [ytdlp_exe,
                       "-f", f"{format_id}+bestaudio/best",
                       "--merge-output-format", output_format, 
                       "--no-warnings",
                       "-o", filepath, url]
            else:
                # No FFmpeg: use standalone format (video+audio already combined)
                logger.info("⚠️ No FFmpeg: using standalone format")
                standalone_format = format_id.split('+')[0] if '+' in format_id else format_id

                # Try to get a format that already has audio
                cmd = [ytdlp_exe,
                       "-f", f"best[height<={format_id.split('p')[0] if 'p' in format_id else '720'}][acodec!=none]/best",
                       "--no-warnings",
                       "-o", filepath, url]

        logger.info(f"🔧 FFmpeg-aware command: {' '.join(cmd[:6])}... [URL_HIDDEN]")

        # Execute download with appropriate timeout
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

        if result.returncode == 0:
            # Find actual downloaded file
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
                            'filesize': file_size,
                            'ffmpeg_used': ffmpeg_available
                        })

                        logger.info(f"✅ FFmpeg-compatible download completed: {actual_file} ({file_size} bytes)")
                    else:
                        raise Exception("Downloaded file too small")
                else:
                    raise Exception("File not found after download")
            else:
                raise Exception("No files found after download")
        else:
            error_msg = result.stderr[:200] if result.stderr else result.stdout[:200]

            # Special handling for FFmpeg errors
            if "ffmpeg not found" in error_msg.lower():
                logger.error("❌ FFmpeg still missing, trying emergency install...")
                if install_ffmpeg():
                    # Retry download with FFmpeg
                    result_retry = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
                    if result_retry.returncode == 0:
                        logger.info("✅ Retry successful after FFmpeg install")
                        # Process successful download...
                        actual_files = [f for f in os.listdir(DOWNLOAD_FOLDER) 
                                      if f.startswith(download_id)]
                        if actual_files:
                            actual_file = actual_files[0]
                            actual_path = os.path.join(DOWNLOAD_FOLDER, actual_file)
                            if os.path.exists(actual_path):
                                file_size = os.path.getsize(actual_path)
                                download_progress[download_id].update({
                                    'progress': 100,
                                    'status': 'completed',
                                    'message': f'Download completed! ({file_size} bytes)',
                                    'filename': actual_file,
                                    'filepath': actual_path,
                                    'filesize': file_size,
                                    'ffmpeg_used': True
                                })
                                logger.info(f"✅ Retry download successful: {actual_file}")
                                return

                raise Exception("FFmpeg installation failed, try lower quality format")
            else:
                raise Exception(f"Download failed: {error_msg}")

    except Exception as e:
        logger.error(f"❌ FFmpeg-compatible download {download_id} failed: {e}")
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

    logger.info("🚀 YT Downloader Pro - FFMPEG SOLUTION EDITION")
    logger.info(f"🌍 Port: {port}")
    logger.info(f"⚡ Max Downloads: {MAX_CONCURRENT_DOWNLOADS}")

    # Update yt-dlp and install FFmpeg on startup
    update_ytdlp()

    ffmpeg_installed = install_ffmpeg()
    if ffmpeg_installed:
        logger.info("✅ FFmpeg installation successful")
    else:
        logger.warning("⚠️ FFmpeg installation failed - will use fallback methods")

    if not check_yt_dlp():
        logger.error("❌ yt-dlp not available!")
    else:
        logger.info("✅ yt-dlp ready with FFmpeg compatibility")

    logger.info("🎬 Backend ready with FFmpeg solution!")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
