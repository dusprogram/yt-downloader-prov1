# backend/app.py - Production backend with CORS support
# Updated for your Railway deployment

import os
import subprocess
import json
import uuid
import threading
import time
import logging
import re
import urllib.parse
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from flask_cors import CORS

# Setup logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'yt-downloader-pro-production'

# CORS configuration for your Netlify frontend
CORS(app, origins=[
    "https://yt-downloader-pro-v011.netlify.app",  # Your Netlify URL
    "http://localhost:3000",  # Local development
    "http://localhost:8000",  # Local development
    "http://127.0.0.1:3000",  # Local development
    "http://127.0.0.1:8000"   # Local development
])

# Configuration
DOWNLOAD_FOLDER = 'downloads'
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get('MAX_DOWNLOADS', '3'))
FILE_CLEANUP_SECONDS = int(os.environ.get('CLEANUP_SECONDS', '120'))

# Create directories
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Global storage
download_progress = {}
active_downloads = 0

def check_yt_dlp():
    """Check if yt-dlp is available with Railway compatibility"""
    try:
        executables = ['yt-dlp', 'yt-dlp.exe']

        for exe in executables:
            try:
                result = subprocess.run([exe, "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info(f"yt-dlp found: {exe} - {result.stdout.strip()}")
                    return exe
            except FileNotFoundError:
                continue

        logger.error("yt-dlp not found!")
        return None

    except Exception as e:
        logger.error(f"Error checking yt-dlp: {e}")
        return None

def clean_youtube_url(url):
    """Clean YouTube URL and remove tracking parameters"""
    try:
        parsed = urllib.parse.urlparse(url)

        if 'youtu.be' in parsed.netloc:
            video_id = parsed.path.lstrip('/')
            if '?' in video_id:
                video_id = video_id.split('?')[0]
            clean_url = f"https://www.youtube.com/watch?v={video_id}"
        elif 'youtube.com' in parsed.netloc:
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'v' in query_params:
                video_id = query_params['v'][0]
                clean_url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                clean_url = url
        else:
            clean_url = url

        logger.info(f"URL cleaned: {clean_url}")
        return clean_url

    except Exception as e:
        logger.warning(f"URL cleaning failed: {e}")
        return url

def get_video_info_with_formats(url):
    """Get video info with production error handling"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            return None

        clean_url = clean_youtube_url(url)

        cmd = [ytdlp_exe, "--dump-json", "--no-download", "--no-warnings", 
               "--no-playlist", "--ignore-errors", clean_url]

        logger.info(f"Getting video info...")

        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=30,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
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
                            'formats': info.get('formats', [])[:50]
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        continue

        logger.error("Info extraction failed")
        return None

    except Exception as e:
        logger.error(f"Info extraction error: {e}")
        return None

def extract_comprehensive_formats(formats_data):
    """Extract formats with production optimization"""
    video_formats = {}
    audio_formats = {}

    # Process video formats
    for fmt in formats_data:
        try:
            format_id = fmt.get('format_id', '')
            ext = fmt.get('ext', '').lower()
            height = fmt.get('height')
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')
            fps = fmt.get('fps', 30)
            filesize = fmt.get('filesize', 0)

            if not format_id:
                continue

            # Video formats (prioritize those with audio)
            if vcodec != 'none' and height and height >= 360 and ext in ['mp4', 'webm']:
                quality = f"{height}p"
                if fps and fps > 30:
                    quality += f"{int(fps)}"

                if quality not in video_formats:
                    video_formats[quality] = {}

                if ext not in video_formats[quality]:
                    has_audio = acodec != 'none'
                    enhanced_format_id = format_id

                    # Add audio merging for video-only formats
                    if not has_audio:
                        enhanced_format_id = f"{format_id}+bestaudio/best"
                        has_audio = True

                    video_formats[quality][ext] = {
                        'format_id': enhanced_format_id,
                        'ext': ext,
                        'quality': quality,
                        'height': height,
                        'fps': fps or 30,
                        'filesize': filesize,
                        'has_audio': has_audio,
                        'width': fmt.get('width', height * 16 // 9)
                    }

        except Exception as e:
            logger.warning(f"Format processing error: {e}")
            continue

    # Add fallback formats if none found
    if not video_formats:
        video_formats = {
            '720p': {
                'mp4': {
                    'format_id': 'best[height<=720]+bestaudio/best[height<=720]',
                    'ext': 'mp4',
                    'quality': '720p',
                    'height': 720,
                    'width': 1280,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0
                }
            },
            '480p': {
                'mp4': {
                    'format_id': 'best[height<=480]+bestaudio/best[height<=480]',
                    'ext': 'mp4',
                    'quality': '480p',
                    'height': 480,
                    'width': 854,
                    'fps': 30,
                    'has_audio': True,
                    'filesize': 0
                }
            }
        }

    # Audio formats with conversion options
    audio_formats = {
        'mp3': {
            'High Quality (320kbps)': {
                'format_id': 'bestaudio',
                'ext': 'mp3',
                'quality': 'High Quality (320kbps)',
                'convert': True,
                'target_abr': 320
            },
            'Good Quality (192kbps)': {
                'format_id': 'bestaudio',
                'ext': 'mp3',
                'quality': 'Good Quality (192kbps)',
                'convert': True,
                'target_abr': 192
            }
        },
        'm4a': {
            'High Quality (256kbps)': {
                'format_id': 'bestaudio',
                'ext': 'm4a',
                'quality': 'High Quality (256kbps)',
                'convert': True,
                'target_abr': 256
            }
        }
    }

    logger.info(f"Extracted formats - Video: {len(video_formats)} qualities, Audio: {len(audio_formats)} types")
    return video_formats, audio_formats

# Health check endpoint for Railway
@app.route('/health')
def health_check():
    """Health check for monitoring"""
    ytdlp_status = check_yt_dlp() is not None
    return jsonify({
        'status': 'healthy',
        'yt_dlp_available': ytdlp_status,
        'active_downloads': active_downloads,
        'timestamp': time.time()
    })

# Main API routes
@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url'].strip()

        if not url:
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'}), 400

        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'success': False, 'error': 'Please enter a valid YouTube URL'}), 400

        logger.info("Getting video info for request")

        info = get_video_info_with_formats(url)

        if not info:
            return jsonify({'success': False, 'error': 'Could not get video information'}), 404

        video_formats, audio_formats = extract_comprehensive_formats(info.get('formats', []))

        return jsonify({
            'success': True,
            'title': info['title'],
            'thumbnail': info['thumbnail'],
            'uploader': info['uploader'],
            'duration': info['duration'],
            'view_count': info['view_count'],
            'video_formats': video_formats,
            'audio_formats': audio_formats
        })

    except Exception as e:
        logger.error(f"Video info error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/download', methods=['POST'])
def start_download():
    global active_downloads

    if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
        return jsonify({'success': False, 'error': 'Server busy. Please try again.'}), 429

    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request'}), 400

        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        download_id = str(uuid.uuid4())[:8]

        download_progress[download_id] = {
            'progress': 0,
            'status': 'starting',
            'message': 'Initializing download...'
        }

        # Start download thread
        thread = threading.Thread(
            target=process_production_download,
            args=(download_id, data),
            daemon=True
        )
        thread.start()

        active_downloads += 1

        return jsonify({'success': True, 'download_id': download_id})

    except Exception as e:
        logger.error(f"Download start error: {e}")
        return jsonify({'success': False, 'error': 'Failed to start download'}), 500

def process_production_download(download_id, data):
    """Production download processing"""
    global active_downloads

    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            raise Exception("yt-dlp not available")

        url = clean_youtube_url(data['url'])
        format_id = data.get('format_id', 'best')
        output_format = data.get('output_format', 'mp4')
        download_type = data.get('type', 'video')
        title = data.get('title', 'video')[:30]

        # Safe filename
        safe_title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        filename = f"{download_id}_{safe_title}.{output_format}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        download_progress[download_id].update({
            'progress': 20,
            'status': 'downloading',
            'message': 'Downloading...'
        })

        # Build command with audio support
        if download_type == 'audio':
            cmd = [
                ytdlp_exe,
                "-f", "bestaudio/best",
                "--extract-audio",
                "--audio-format", output_format,
                "--audio-quality", "192",
                "--no-warnings",
                "--no-playlist",
                "-o", filepath,
                url
            ]
        else:
            cmd = [
                ytdlp_exe,
                "-f", f"{format_id}",
                "--merge-output-format", output_format,
                "--no-warnings", 
                "--no-playlist",
                "-o", filepath,
                url
            ]

        logger.info(f"Executing download command for {download_id}")

        # Execute download
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            # Find downloaded file
            actual_files = [f for f in os.listdir(DOWNLOAD_FOLDER) 
                          if f.startswith(download_id) and os.path.getsize(os.path.join(DOWNLOAD_FOLDER, f)) > 1024]

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

                logger.info(f"Download completed: {actual_file}")
            else:
                raise Exception("Download completed but file not found")
        else:
            raise Exception(f"Download failed: {result.stderr[:100]}")

    except Exception as e:
        logger.error(f"Download {download_id} failed: {e}")
        download_progress[download_id].update({
            'progress': 0,
            'status': 'error',
            'message': f'Download failed: {str(e)[:50]}'
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

    clean_name = filename[9:] if filename.startswith(download_id) else filename

    @after_this_request
    def cleanup(response):
        def delayed_cleanup():
            time.sleep(5)
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                if download_id in download_progress:
                    del download_progress[download_id]
            except:
                pass

        threading.Thread(target=delayed_cleanup, daemon=True).start()
        return response

    return send_file(filepath, as_attachment=True, download_name=clean_name)

# Cleanup thread
def cleanup_old_files():
    while True:
        try:
            cutoff_time = time.time() - FILE_CLEANUP_SECONDS
            if os.path.exists(DOWNLOAD_FOLDER):
                for filename in os.listdir(DOWNLOAD_FOLDER):
                    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                    try:
                        if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
                    except:
                        pass
            time.sleep(60)
        except:
            time.sleep(60)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    logger.info("🚀 YT Downloader Pro Backend Starting (Production)")
    logger.info(f"Port: {port}")
    logger.info(f"Max Downloads: {MAX_CONCURRENT_DOWNLOADS}")
    logger.info("CORS enabled for Netlify frontend")

    ytdlp_exe = check_yt_dlp()
    if not ytdlp_exe:
        logger.error("❌ yt-dlp not found!")
    else:
        logger.info(f"✅ yt-dlp available: {ytdlp_exe}")

    app.run(host='0.0.0.0', port=port, debug=False)
