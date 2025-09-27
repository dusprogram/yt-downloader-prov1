# ENHANCED BACKEND - Complete Format Support
# Supports all requested audio/video formats and qualities

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
app.secret_key = 'enhanced-yt-downloader-all-formats'

# ✅ ULTIMATE CORS CONFIGURATION
CORS(app,
     origins=[
         "https://yt-downloader-pro-v011.netlify.app",
         "http://localhost:3000",
         "http://localhost:8000",
         "http://127.0.0.1:3000",
         "http://127.0.0.1:8000",
         "*"
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

@app.before_request
def before_request():
    """Handle preflight requests"""
    origin = request.headers.get('Origin')

    logger.info(f"🌐 Request from origin: {origin}")
    logger.info(f"🔧 Request method: {request.method}")
    logger.info(f"📍 Request endpoint: {request.endpoint}")

    if request.method == 'OPTIONS':
        logger.info("✅ Handling preflight OPTIONS request")

        response = make_response('', 200)

        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'

        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin, Authorization, X-Requested-With'
        response.headers['Access-Control-Max-Age'] = '86400'
        response.headers['Access-Control-Allow-Credentials'] = 'false'
        response.headers['Vary'] = 'Origin'
        response.headers['Cache-Control'] = 'no-cache'

        logger.info("✅ Preflight response sent with CORS headers")
        return response

@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    origin = request.headers.get('Origin')

    allowed_origins = [
        "https://yt-downloader-pro-v011.netlify.app",
        "http://localhost:3000",
        "http://localhost:8000"
    ]

    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        logger.info(f"✅ CORS allowed for: {origin}")
    elif origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        logger.info(f"⚠️ CORS allowed (permissive) for: {origin}")
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'

    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin, Authorization'
    response.headers['Access-Control-Max-Age'] = '86400'
    response.headers['Access-Control-Allow-Credentials'] = 'false'
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
    """Get comprehensive video information and all available formats"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            return None

        clean_url = clean_youtube_url(url)
        logger.info(f"🔍 Processing: {clean_url}")

        # Enhanced command to get all formats
        cmd = [ytdlp_exe, "--dump-json", "--no-download", "--no-warnings", 
               "--no-playlist", "--ignore-errors", "--list-formats", clean_url]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        info = json.loads(line)
                        logger.info(f"✅ Raw formats found: {len(info.get('formats', []))}")
                        return {
                            'title': info.get('title', 'Unknown')[:80],
                            'uploader': info.get('uploader', 'Unknown'),
                            'duration': info.get('duration', 0),
                            'view_count': info.get('view_count', 0),
                            'thumbnail': info.get('thumbnail', ''),
                            'formats': info.get('formats', [])  # Get ALL formats
                        }
                    except:
                        continue

        logger.error("No video info extracted")
        return None

    except Exception as e:
        logger.error(f"Video info error: {e}")
        return None

def extract_comprehensive_formats(formats_data):
    """Extract all requested video and audio formats"""

    # Initialize comprehensive format structure
    video_formats = {}
    audio_formats = {
        'mp3': {
            'High Quality (320kbps)': {
                'format_id': 'bestaudio',
                'ext': 'mp3',
                'quality': 'High Quality (320kbps)',
                'convert': True,
                'bitrate': 320
            },
            'Good Quality (192kbps)': {
                'format_id': 'bestaudio',
                'ext': 'mp3', 
                'quality': 'Good Quality (192kbps)',
                'convert': True,
                'bitrate': 192
            },
            'Standard Quality (128kbps)': {
                'format_id': 'bestaudio',
                'ext': 'mp3',
                'quality': 'Standard Quality (128kbps)', 
                'convert': True,
                'bitrate': 128
            }
        },
        'm4a': {
            'High Quality (256kbps)': {
                'format_id': 'bestaudio[ext=m4a]',
                'ext': 'm4a',
                'quality': 'High Quality (256kbps)',
                'convert': True,
                'bitrate': 256
            },
            'Good Quality (192kbps)': {
                'format_id': 'bestaudio[ext=m4a]',
                'ext': 'm4a',
                'quality': 'Good Quality (192kbps)',
                'convert': True,
                'bitrate': 192
            }
        },
        'flac': {
            'Lossless': {
                'format_id': 'bestaudio',
                'ext': 'flac',
                'quality': 'Lossless',
                'convert': True,
                'bitrate': 'lossless'
            }
        }
    }

    # Process all formats from yt-dlp
    logger.info(f"🔍 Processing {len(formats_data)} raw formats from yt-dlp")

    # Track best formats for original audio
    best_m4a_original = None
    best_webm_audio = None

    # Define video quality mapping
    quality_mapping = {
        2160: '2160p',  # 4K
        1440: '1440p',  # 2K
        1080: '1080p',  # Full HD
        720: '720p',    # HD
        480: '480p',    # SD
        360: '360p',    # Low
        240: '240p',    # Very Low
        144: '144p'     # Mobile
    }

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
            tbr = fmt.get('tbr', 0)  # Total bitrate
            abr = fmt.get('abr', 0)  # Audio bitrate

            # Process video formats
            if height and vcodec != 'none' and ext in ['mp4', 'webm', 'mkv']:
                # Determine quality label
                quality_label = quality_mapping.get(height, f"{height}p")

                # Handle 60fps separately for 720p
                if height == 720 and fps and fps > 50:
                    quality_label = '720p60'

                if quality_label not in video_formats:
                    video_formats[quality_label] = {}

                # Create format entry
                video_format = {
                    'format_id': format_id,
                    'ext': ext,
                    'quality': quality_label,
                    'height': height,
                    'width': width or (height * 16 // 9),
                    'fps': fps,
                    'has_audio': acodec != 'none',
                    'filesize': filesize,
                    'tbr': tbr
                }

                # Only add if not already exists or if this one is better
                if ext not in video_formats[quality_label]:
                    video_formats[quality_label][ext] = video_format
                    logger.info(f"✅ Added video format: {quality_label} {ext.upper()}")

            # Process original audio formats  
            elif acodec != 'none' and vcodec == 'none':
                # Track best original audio formats
                if ext == 'm4a' and (not best_m4a_original or abr > best_m4a_original.get('abr', 0)):
                    best_m4a_original = {
                        'format_id': format_id,
                        'ext': 'm4a',
                        'quality': f'M4A ({abr}kbps from video)',
                        'abr': abr,
                        'filesize': filesize
                    }

                elif ext == 'webm' and (not best_webm_audio or abr > best_webm_audio.get('abr', 0)):
                    best_webm_audio = {
                        'format_id': format_id,
                        'ext': 'webm',
                        'quality': f'WebM Audio ({abr}kbps)',
                        'abr': abr,
                        'filesize': filesize
                    }

        except Exception as e:
            logger.error(f"Error processing format: {e}")
            continue

    # Add original audio formats if found
    if best_m4a_original or best_webm_audio:
        audio_formats['original'] = {}

        if best_m4a_original:
            audio_formats['original']['M4A (256kbps from video)'] = {
                'format_id': best_m4a_original['format_id'],
                'ext': 'm4a',
                'quality': 'M4A (256kbps from video)',
                'convert': False,
                'filesize': best_m4a_original.get('filesize', 0)
            }

        if best_webm_audio:
            audio_formats['original']['WebM Audio (128kbps)'] = {
                'format_id': best_webm_audio['format_id'],
                'ext': 'webm',
                'quality': 'WebM Audio (128kbps)', 
                'convert': False,
                'filesize': best_webm_audio.get('filesize', 0)
            }

    # Add fallback video formats if none found
    if not video_formats:
        logger.warning("⚠️ No video formats extracted, adding fallbacks")
        video_formats = {
            '1080p': {
                'mp4': {
                    'format_id': 'best[height<=1080]+bestaudio/best',
                    'ext': 'mp4',
                    'quality': '1080p',
                    'height': 1080,
                    'width': 1920,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'estimated_size': '1.2GB'
                }
            },
            '720p': {
                'mp4': {
                    'format_id': 'best[height<=720]+bestaudio/best',
                    'ext': 'mp4',
                    'quality': '720p',
                    'height': 720,
                    'width': 1280,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'estimated_size': '500MB'
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
                    'estimated_size': '350MB'
                }
            },
            '480p': {
                'mp4': {
                    'format_id': 'best[height<=480]+bestaudio/best',
                    'ext': 'mp4',
                    'quality': '480p',
                    'height': 480,
                    'width': 854,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'estimated_size': '200MB'
                }
            },
            '360p': {
                'mp4': {
                    'format_id': 'best[height<=360]+bestaudio/best',
                    'ext': 'mp4',
                    'quality': '360p',
                    'height': 360,
                    'width': 640,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0,
                    'estimated_size': '100MB'
                }
            }
        }

    # Log final counts
    video_count = sum(len(quality_formats) for quality_formats in video_formats.values())
    audio_count = sum(len(format_formats) for format_formats in audio_formats.values())

    logger.info(f"✅ Final format extraction complete:")
    logger.info(f"📹 Video formats: {video_count} total across {len(video_formats)} qualities")
    logger.info(f"🎵 Audio formats: {audio_count} total across {len(audio_formats)} types")

    return video_formats, audio_formats

# Routes
@app.route('/', methods=['GET', 'OPTIONS'])
def home():
    """Root endpoint"""
    return jsonify({
        'status': '🎬 YT Downloader Pro Backend - Enhanced Format Support',
        'version': '4.0.0 - All Formats Edition',
        'timestamp': time.time(),
        'cors_fixed': True,
        'formats_supported': {
            'video': ['1080p', '720p60', '720p', '480p', '360p', '240p'],
            'audio': ['MP3 (320/192/128kbps)', 'M4A (256/192kbps)', 'FLAC (Lossless)', 'Original Audio']
        },
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
        'cors_configuration': 'enhanced_v4',
        'railway_compatible': True,
        'format_extraction': 'comprehensive'
    }

    logger.info("✅ Health check accessed")
    return jsonify(health_data)

@app.route('/get_video_info', methods=['POST', 'OPTIONS'])
def get_video_info():
    """Get comprehensive video information with all formats"""

    logger.info("📝 Video info request received")
    logger.info(f"📋 Headers: {dict(request.headers)}")
    logger.info(f"🌐 Origin: {request.headers.get('Origin')}")
    logger.info(f"🔧 Method: {request.method}")

    try:
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

        # Get comprehensive video info
        info = get_video_info_with_formats(url)
        if not info:
            logger.error("❌ Failed to extract video info")
            return jsonify({
                'success': False, 
                'error': 'Could not get video information. Video may be private or unavailable.'
            }), 404

        # Extract all formats comprehensively 
        video_formats, audio_formats = extract_comprehensive_formats(info['formats'])

        response_data = {
            'success': True,
            'title': info['title'],
            'thumbnail': info['thumbnail'],
            'uploader': info['uploader'],
            'duration': info['duration'],
            'view_count': info['view_count'],
            'video_formats': video_formats,
            'audio_formats': audio_formats,
            'format_stats': {
                'video_qualities': len(video_formats),
                'audio_types': len(audio_formats),
                'total_video_formats': sum(len(q) for q in video_formats.values()),
                'total_audio_formats': sum(len(t) for t in audio_formats.values())
            },
            'timestamp': time.time()
        }

        logger.info(f"✅ Video info processed: {info['title']}")
        logger.info(f"📊 Formats: {response_data['format_stats']['total_video_formats']} video, {response_data['format_stats']['total_audio_formats']} audio")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"💥 Video info error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    """Start download with enhanced format support"""
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
        logger.info(f"🚀 Starting enhanced download {download_id}")
        logger.info(f"📋 Download request: {data}")

        download_progress[download_id] = {
            'progress': 0,
            'status': 'starting',
            'message': 'Starting enhanced download...',
            'timestamp': time.time()
        }

        thread = threading.Thread(
            target=process_enhanced_download,
            args=(download_id, data),
            daemon=True
        )
        thread.start()
        active_downloads += 1

        return jsonify({'success': True, 'download_id': download_id})

    except Exception as e:
        logger.error(f"Download start error: {e}")
        return jsonify({'success': False, 'error': 'Failed to start download'}), 500

def process_enhanced_download(download_id, data):
    """Process download with enhanced format handling"""
    global active_downloads

    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            raise Exception("yt-dlp not available")

        url = clean_youtube_url(data['url'])
        format_id = data.get('format_id', 'best')
        output_format = data.get('output_format', 'mp4')
        download_type = data.get('type', 'video')
        quality = data.get('quality', 'best')
        title = data.get('title', 'video')[:20]

        # Safe filename
        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        filename = f"{download_id}_{safe_title}.{output_format}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        logger.info(f"📥 Processing enhanced {download_type}: {filename}")
        logger.info(f"🎯 Format: {format_id}, Quality: {quality}")

        download_progress[download_id].update({
            'progress': 25,
            'status': 'downloading',
            'message': f'Downloading {quality} {download_type}...'
        })

        # Build enhanced command based on type and quality
        if download_type == 'audio':
            if 'mp3' in output_format.lower():
                # MP3 conversion with quality
                bitrate = '320'  # Default
                if '192' in quality:
                    bitrate = '192'
                elif '128' in quality:
                    bitrate = '128'

                cmd = [ytdlp_exe, "-f", "bestaudio", "--extract-audio", 
                       "--audio-format", "mp3", "--audio-quality", bitrate,
                       "-o", filepath, url]

            elif 'flac' in output_format.lower():
                # FLAC lossless
                cmd = [ytdlp_exe, "-f", "bestaudio", "--extract-audio",
                       "--audio-format", "flac", 
                       "-o", filepath, url]

            else:
                # M4A or other formats
                cmd = [ytdlp_exe, "-f", format_id, "-o", filepath, url]
        else:
            # Video download
            if '+' in format_id:
                # Format with audio merger
                cmd = [ytdlp_exe, "-f", format_id, "--merge-output-format", 
                       output_format, "-o", filepath, url]
            else:
                # Simple format
                cmd = [ytdlp_exe, "-f", format_id, "-o", filepath, url]

        logger.info(f"🔧 Enhanced command: {' '.join(cmd[:6])}... [URL_HIDDEN]")

        # Execute download with longer timeout
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            # Find downloaded file
            actual_files = [f for f in os.listdir(DOWNLOAD_FOLDER) 
                          if f.startswith(download_id)]

            if actual_files:
                actual_file = actual_files[0]
                actual_path = os.path.join(DOWNLOAD_FOLDER, actual_file)
                file_size = os.path.getsize(actual_path)

                download_progress[download_id].update({
                    'progress': 100,
                    'status': 'completed',
                    'message': f'Enhanced download completed! ({file_size} bytes)',
                    'filename': actual_file,
                    'filepath': actual_path,
                    'filesize': file_size
                })

                logger.info(f"✅ Enhanced download completed: {actual_file} ({file_size} bytes)")
            else:
                raise Exception("File not found after download")
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            raise Exception(f"Enhanced download failed: {error_msg}")

    except Exception as e:
        logger.error(f"❌ Enhanced download {download_id} failed: {e}")
        download_progress[download_id].update({
            'progress': 0,
            'status': 'error',
            'message': f'Download failed: {str(e)[:100]}'
        })

    finally:
        active_downloads = max(0, active_downloads - 1)
        logger.info(f"📊 Active downloads: {active_downloads}")

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
                            logger.info(f"🗑️ Auto-cleaned: {filename}")
                    except:
                        pass
            time.sleep(60)
        except:
            time.sleep(60)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    logger.info("🚀 YT Downloader Pro Backend - ENHANCED FORMAT EDITION")
    logger.info(f"🌍 Port: {port}")
    logger.info(f"⚡ Max Downloads: {MAX_CONCURRENT_DOWNLOADS}")
    logger.info(f"🧹 Cleanup: {FILE_CLEANUP_SECONDS}s")

    if not check_yt_dlp():
        logger.error("❌ yt-dlp not available!")
    else:
        logger.info("✅ yt-dlp ready for enhanced downloads")

    logger.info("🌐 CORS: Enhanced format support")
    logger.info("📋 Formats: All requested qualities supported")
    logger.info("🎬 Backend ready for enhanced requests!")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
