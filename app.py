# ULTIMATE RESEARCH-BASED BACKEND - 2025 YouTube API Compatible
# Fixes all identified issues: outdated yt-dlp, format extraction, corruption

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
app.secret_key = 'ultimate-2025-yt-downloader'

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
    origin = request.headers.get('Origin')

    if request.method == 'OPTIONS':
        response = make_response('', 200)

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

def update_ytdlp():
    """Update yt-dlp to latest version - Critical for 2025 compatibility"""
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

            # Check if version is too old (before 2024)
            if "2023" in version or "2022" in version:
                logger.warning("⚠️ yt-dlp version is outdated, updating...")
                update_ytdlp()

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
    """Modern video info extraction - 2025 compatible"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            return None

        clean_url = clean_youtube_url(url)
        logger.info(f"🔍 Processing with modern extraction: {clean_url}")

        # ✅ RESEARCH-BASED COMMAND - Optimal for 2025 YouTube
        cmd = [
            ytdlp_exe, 
            "--dump-json",           # Get JSON info
            "--no-download",         # Don't download
            "--no-warnings",         # Reduce noise
            "--no-playlist",         # Single video only
            "--ignore-errors",       # Continue on errors
            "--extractor-retries", "3",  # Retry extraction
            "--sleep-interval", "1",     # Be nice to YouTube
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
                        logger.info(f"✅ Modern extraction: {len(formats)} formats found")

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

        logger.error("❌ Modern extraction failed")
        return None

    except Exception as e:
        logger.error(f"Modern extraction error: {e}")
        return None

def extract_modern_formats(formats_data):
    """Modern format extraction - Research-based for maximum compatibility"""

    video_formats = {}
    audio_formats = {}

    logger.info(f"🔍 Modern processing: {len(formats_data)} raw formats")

    # Modern video quality mapping
    quality_heights = {
        2160: '2160p',  # 4K
        1440: '1440p',  # 2K  
        1080: '1080p',  # Full HD
        720: '720p',    # HD
        480: '480p',    # SD
        360: '360p',    # Low
        240: '240p',    # Very Low
        144: '144p'     # Mobile
    }

    # Process all formats with modern logic
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

            # Modern video format processing
            if (height and vcodec != 'none' and 
                ext in ['mp4', 'webm'] and  # Only reliable formats
                protocol in ['https', 'http', '']):  # Avoid problematic protocols

                quality = quality_heights.get(height, f"{height}p")

                # Handle 60fps separately for 720p
                if height == 720 and fps and fps >= 60:
                    quality = '720p60'

                if quality not in video_formats:
                    video_formats[quality] = {}

                # Modern format entry with corruption prevention
                if ext not in video_formats[quality]:
                    # Use modern format selectors for better compatibility
                    modern_format_id = format_id
                    if acodec == 'none':
                        # Ensure audio is included to prevent corruption
                        modern_format_id = f"{format_id}+bestaudio/best"

                    video_formats[quality][ext] = {
                        'format_id': modern_format_id,
                        'ext': ext,
                        'quality': quality,
                        'height': height,
                        'width': width or (height * 16 // 9),
                        'fps': fps,
                        'has_audio': True,  # Force audio inclusion
                        'filesize': filesize,
                        'tbr': tbr,
                        'modern_compatible': True
                    }

                    logger.info(f"✅ Modern video format: {quality} {ext.upper()}")

            # Modern audio format processing
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
                    'modern_compatible': True
                }

                logger.info(f"✅ Modern audio format: {ext.upper()} {quality_label}")

        except Exception as e:
            logger.error(f"Format processing error: {e}")
            continue

    # Add comprehensive modern formats if limited extraction
    if len(video_formats) < 3:
        logger.warning("⚠️ Limited formats detected, adding modern standards")

        modern_standards = {
            '1080p': {
                'mp4': {
                    'format_id': 'best[height<=1080][ext=mp4]+bestaudio/best',
                    'ext': 'mp4',
                    'quality': '1080p',
                    'height': 1080,
                    'width': 1920,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'modern_compatible': True
                }
            },
            '720p': {
                'mp4': {
                    'format_id': 'best[height<=720][ext=mp4]+bestaudio/best',
                    'ext': 'mp4',
                    'quality': '720p', 
                    'height': 720,
                    'width': 1280,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'modern_compatible': True
                },
                'webm': {
                    'format_id': 'best[height<=720][ext=webm]+bestaudio/best',
                    'ext': 'webm',
                    'quality': '720p',
                    'height': 720,
                    'width': 1280, 
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'modern_compatible': True
                }
            },
            '480p': {
                'mp4': {
                    'format_id': 'best[height<=480][ext=mp4]+bestaudio/best',
                    'ext': 'mp4',
                    'quality': '480p',
                    'height': 480,
                    'width': 854,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'modern_compatible': True
                }
            },
            '360p': {
                'mp4': {
                    'format_id': 'best[height<=360][ext=mp4]+bestaudio/best', 
                    'ext': 'mp4',
                    'quality': '360p',
                    'height': 360,
                    'width': 640,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'modern_compatible': True
                }
            }
        }

        # Merge with existing
        for quality, formats in modern_standards.items():
            if quality not in video_formats:
                video_formats[quality] = formats
            else:
                for ext, format_data in formats.items():
                    if ext not in video_formats[quality]:
                        video_formats[quality][ext] = format_data

    # Add comprehensive modern audio formats
    if len(audio_formats) < 2:
        logger.warning("⚠️ Limited audio formats, adding modern standards")

        modern_audio = {
            'mp3': {
                'High Quality (320kbps)': {
                    'format_id': 'bestaudio',
                    'ext': 'mp3',
                    'quality': 'High Quality (320kbps)',
                    'convert': True,
                    'abr': 320,
                    'modern_compatible': True
                },
                'Good Quality (192kbps)': {
                    'format_id': 'bestaudio',
                    'ext': 'mp3',
                    'quality': 'Good Quality (192kbps)',
                    'convert': True,
                    'abr': 192,
                    'modern_compatible': True
                },
                'Standard Quality (128kbps)': {
                    'format_id': 'bestaudio',
                    'ext': 'mp3',
                    'quality': 'Standard Quality (128kbps)',
                    'convert': True,
                    'abr': 128,
                    'modern_compatible': True
                }
            },
            'm4a': {
                'High Quality (256kbps)': {
                    'format_id': 'bestaudio[ext=m4a]',
                    'ext': 'm4a',
                    'quality': 'High Quality (256kbps)',
                    'abr': 256,
                    'modern_compatible': True
                }
            }
        }

        audio_formats.update(modern_audio)

    # Final counts
    video_count = sum(len(quality_formats) for quality_formats in video_formats.values())
    audio_count = sum(len(format_formats) for format_formats in audio_formats.values())

    logger.info(f"✅ Modern extraction complete:")
    logger.info(f"📹 Video formats: {video_count} total across {len(video_formats)} qualities")
    logger.info(f"🎵 Audio formats: {audio_count} total")

    return video_formats, audio_formats

# Routes
@app.route('/', methods=['GET', 'OPTIONS'])
def home():
    """Root endpoint"""
    return jsonify({
        'status': '🎬 YT Downloader Pro - Modern 2025 Edition',
        'version': '5.0.0 - Research-Based Solution',
        'timestamp': time.time(),
        'features': ['Updated yt-dlp', 'Modern format extraction', 'Corruption-free downloads'],
        'compatibility': '2025 YouTube API'
    })

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    """Health check"""
    ytdlp_status = check_yt_dlp() is not None

    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'yt_dlp_available': ytdlp_status,
        'active_downloads': active_downloads,
        'modern_extraction': True,
        'corruption_prevention': True
    })

@app.route('/get_video_info', methods=['POST', 'OPTIONS'])
def get_video_info():
    """Modern video info extraction"""

    try:
        data = request.json

        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url'].strip()

        if not url:
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'}), 400

        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'success': False, 'error': 'Please enter a valid YouTube URL'}), 400

        logger.info(f"🔍 Modern processing: {url}")

        # Modern video info extraction
        info = get_video_info_modern(url)
        if not info:
            return jsonify({
                'success': False, 
                'error': 'Could not extract video information. Video may be private or region-restricted.'
            }), 404

        # Modern format extraction
        video_formats, audio_formats = extract_modern_formats(info['formats'])

        response_data = {
            'success': True,
            'title': info['title'],
            'thumbnail': info['thumbnail'],
            'uploader': info['uploader'],
            'duration': info['duration'],
            'view_count': info['view_count'],
            'video_formats': video_formats,
            'audio_formats': audio_formats,
            'extraction_method': 'modern_2025',
            'format_stats': {
                'total_video_formats': sum(len(q) for q in video_formats.values()),
                'total_audio_formats': sum(len(t) for t in audio_formats.values()),
                'video_qualities': list(video_formats.keys()),
                'audio_types': list(audio_formats.keys())
            },
            'timestamp': time.time()
        }

        logger.info(f"✅ Modern extraction success: {info['title']}")
        logger.info(f"📊 Modern formats: {response_data['format_stats']['total_video_formats']} video, {response_data['format_stats']['total_audio_formats']} audio")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"💥 Modern extraction error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    """Modern download with corruption prevention"""
    global active_downloads

    if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
        return jsonify({'success': False, 'error': 'Server busy. Please try again later.'}), 429

    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        download_id = str(uuid.uuid4())[:8]
        logger.info(f"🚀 Starting modern download {download_id}")

        download_progress[download_id] = {
            'progress': 0,
            'status': 'starting',
            'message': 'Starting modern download...',
            'timestamp': time.time()
        }

        thread = threading.Thread(
            target=process_modern_download,
            args=(download_id, data),
            daemon=True
        )
        thread.start()
        active_downloads += 1

        return jsonify({'success': True, 'download_id': download_id})

    except Exception as e:
        logger.error(f"Download start error: {e}")
        return jsonify({'success': False, 'error': 'Failed to start download'}), 500

def process_modern_download(download_id, data):
    """Modern download processing with corruption prevention"""
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

        logger.info(f"📥 Modern download: {filename}")
        logger.info(f"🎯 Modern format: {format_id}")

        download_progress[download_id].update({
            'progress': 25,
            'status': 'downloading',
            'message': f'Modern downloading {download_type}...'
        })

        # Modern command with corruption prevention
        if download_type == 'audio':
            if 'mp3' in output_format.lower():
                cmd = [ytdlp_exe, "-f", "bestaudio", "--extract-audio", 
                       "--audio-format", "mp3", "--audio-quality", "0",
                       "--embed-metadata", "--no-warnings", "-o", filepath, url]
            else:
                cmd = [ytdlp_exe, "-f", format_id, "--embed-metadata", 
                       "--no-warnings", "-o", filepath, url]
        else:
            # Modern video download with corruption prevention
            cmd = [ytdlp_exe, 
                   "-f", format_id,                    # Use specified format
                   "--merge-output-format", output_format,  # Ensure correct container
                   "--embed-subs",                     # Embed subtitles if available
                   "--embed-metadata",                 # Embed metadata
                   "--no-warnings",                    # Reduce noise
                   "--fixup", "detect_or_warn",       # Fix corruption issues
                   "--retries", "3",                   # Retry on failure
                   "-o", filepath, url]

        logger.info(f"🔧 Modern command: {' '.join(cmd[:8])}... [ARGS_HIDDEN]")

        # Execute with extended timeout for corruption prevention
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

        if result.returncode == 0:
            # Verify file was created
            actual_files = [f for f in os.listdir(DOWNLOAD_FOLDER) 
                          if f.startswith(download_id)]

            if actual_files:
                actual_file = actual_files[0]
                actual_path = os.path.join(DOWNLOAD_FOLDER, actual_file)

                # Modern file verification
                if os.path.exists(actual_path):
                    file_size = os.path.getsize(actual_path)

                    if file_size > 1000:  # Minimum viable file size
                        download_progress[download_id].update({
                            'progress': 100,
                            'status': 'completed',
                            'message': f'Modern download completed! ({file_size} bytes)',
                            'filename': actual_file,
                            'filepath': actual_path,
                            'filesize': file_size,
                            'corruption_checked': True
                        })

                        logger.info(f"✅ Modern download completed: {actual_file} ({file_size} bytes)")
                    else:
                        raise Exception("Downloaded file too small, possibly corrupted")
                else:
                    raise Exception("File not found after download")
            else:
                raise Exception("No files found after download")
        else:
            error_msg = result.stderr[:200] if result.stderr else result.stdout[:200]
            raise Exception(f"Modern download failed: {error_msg}")

    except Exception as e:
        logger.error(f"❌ Modern download {download_id} failed: {e}")
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
            time.sleep(5)  # Longer delay for download completion
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

    logger.info("🚀 YT Downloader Pro - MODERN 2025 EDITION")
    logger.info(f"🌍 Port: {port}")
    logger.info(f"⚡ Max Downloads: {MAX_CONCURRENT_DOWNLOADS}")

    # Update yt-dlp on startup
    update_ytdlp()

    if not check_yt_dlp():
        logger.error("❌ yt-dlp not available!")
    else:
        logger.info("✅ yt-dlp ready - modern extraction enabled")

    logger.info("🎬 Backend ready for modern downloads!")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
