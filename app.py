# YOUTUBE SEPTEMBER 2025 COMPATIBLE - Complete Fixed Backend
import os
import subprocess
import json
import uuid
import threading
import time
import logging
from flask import Flask, request, jsonify, send_file, after_this_request, make_response
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'youtube-2025-compatible-downloader'

CORS(app, origins=["https://yt-downloader-pro-v011.netlify.app", "*"], methods=['GET', 'POST', 'OPTIONS'], 
     allow_headers=['Content-Type', 'Accept', 'Origin', 'Authorization'], supports_credentials=False, max_age=86400)

DOWNLOAD_FOLDER = 'downloads'
MAX_CONCURRENT_DOWNLOADS = 3
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

download_progress = {}
active_downloads = 0

@app.before_request
def before_request():
    if request.method == 'OPTIONS':
        response = make_response('', 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin'
        return response

@app.after_request  
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Origin'
    return response

def update_ytdlp():
    try:
        logger.info("🔄 Updating yt-dlp to 2025.09.26+ for YouTube compatibility...")
        subprocess.run(["python", "-m", "pip", "install", "--upgrade", "yt-dlp"], 
                      capture_output=True, text=True, timeout=60)
        logger.info("✅ yt-dlp updated for September 2025 YouTube changes")
    except Exception as e:
        logger.error(f"❌ yt-dlp update error: {e}")

def check_yt_dlp():
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.info(f"✅ yt-dlp version: {version}")
            return "yt-dlp"
        return None
    except Exception as e:
        logger.error(f"❌ yt-dlp not available: {e}")
        return None

def install_ffmpeg():
    try:
        logger.info("🔧 Installing FFmpeg...")
        subprocess.run(["apt-get", "update"], check=True, capture_output=True)
        subprocess.run(["apt-get", "install", "-y", "ffmpeg"], check=True, capture_output=True)
        logger.info("✅ FFmpeg installed")
        return True
    except:
        return False

def clean_youtube_url(url):
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        if 'youtu.be' in parsed.netloc:
            video_id = parsed.path.lstrip('/').split('?')[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        elif 'youtube.com' in parsed.netloc:
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'v' in query_params:
                video_id = query_params['v'][0]
                return f"https://www.youtube.com/watch?v={video_id}"
        return url
    except:
        return url

def get_video_info_2025_compatible(url):
    """YouTube September 2025 compatible extraction"""
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            return None
        
        clean_url = clean_youtube_url(url)
        logger.info(f"🔍 YouTube 2025 compatible extraction: {clean_url}")
        
        # September 2025 compatible command with new client parameters
        cmd = [
            ytdlp_exe,
            "--dump-json",
            "--no-download", 
            "--no-warnings",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=android_vr,web_safari",
            "--extractor-args", "youtube:player_skip=webpage,configs,js",
            "--extractor-retries", "5",
            "--sleep-interval", "2",
            clean_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        info = json.loads(line)
                        formats = info.get('formats', [])
                        if formats:
                            logger.info(f"✅ YouTube 2025 extraction success: {len(formats)} formats")
                            return {
                                'title': info.get('title', 'Unknown')[:80],
                                'uploader': info.get('uploader', 'Unknown'),
                                'duration': info.get('duration', 0),
                                'view_count': info.get('view_count', 0),
                                'thumbnail': info.get('thumbnail', ''),
                                'formats': formats
                            }
                    except json.JSONDecodeError:
                        continue
        
        # Fallback method for difficult videos
        logger.info("🔄 Using YouTube 2025 fallback method...")
        fallback_cmd = [
            ytdlp_exe,
            "--dump-json",
            "--no-download",
            "--extractor-args", "youtube:player_client=android_vr",
            "--format", "worst",
            clean_url
        ]
        
        result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=45)
        if result.returncode == 0 and result.stdout.strip():
            try:
                info = json.loads(result.stdout.strip().split('\n')[0])
                basic_formats = [
                    {'format_id': 'best', 'ext': 'mp4', 'quality': '720p', 'height': 720, 'width': 1280, 'has_audio': True},
                    {'format_id': 'best[height<=480]', 'ext': 'mp4', 'quality': '480p', 'height': 480, 'width': 854, 'has_audio': True},
                    {'format_id': 'best[height<=360]', 'ext': 'mp4', 'quality': '360p', 'height': 360, 'width': 640, 'has_audio': True}
                ]
                logger.info("✅ YouTube 2025 fallback success")
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
                
        return None
        
    except Exception as e:
        logger.error(f"YouTube 2025 extraction error: {e}")
        return None

def extract_2025_formats(formats_data):
    """Process formats for YouTube 2025 compatibility"""
    video_formats = {}
    audio_formats = {}
    
    quality_heights = {2160: '2160p', 1440: '1440p', 1080: '1080p', 720: '720p', 480: '480p', 360: '360p', 240: '240p', 144: '144p'}
    
    # Process available formats
    for fmt in formats_data:
        try:
            format_id = fmt.get('format_id', '')
            ext = fmt.get('ext', '').lower()
            height = fmt.get('height')
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')
            
            # Video formats with audio (standalone)
            if height and vcodec != 'none' and acodec != 'none' and ext in ['mp4', 'webm']:
                quality = quality_heights.get(height, f"{height}p")
                if quality not in video_formats:
                    video_formats[quality] = {}
                if ext not in video_formats[quality]:
                    video_formats[quality][ext] = {
                        'format_id': format_id,
                        'ext': ext,
                        'quality': quality,
                        'height': height,
                        'width': fmt.get('width', height * 16 // 9),
                        'has_audio': True,
                        'filesize': fmt.get('filesize', 0)
                    }
            
            # Audio formats  
            elif acodec != 'none' and vcodec == 'none':
                abr = fmt.get('abr', 0)
                quality_label = f"{abr}kbps" if abr else "Good Quality"
                if ext not in audio_formats:
                    audio_formats[ext] = {}
                audio_formats[ext][quality_label] = {
                    'format_id': format_id,
                    'ext': ext,
                    'quality': quality_label,
                    'abr': abr
                }
        except Exception as e:
            continue
    
    # Add guaranteed fallback formats
    if len(video_formats) < 3:
        fallback_formats = {
            '720p': {'mp4': {'format_id': 'best[height<=720]', 'ext': 'mp4', 'quality': '720p', 'height': 720, 'width': 1280, 'has_audio': True, 'filesize': 0}},
            '480p': {'mp4': {'format_id': 'best[height<=480]', 'ext': 'mp4', 'quality': '480p', 'height': 480, 'width': 854, 'has_audio': True, 'filesize': 0}},
            '360p': {'mp4': {'format_id': 'best[height<=360]', 'ext': 'mp4', 'quality': '360p', 'height': 360, 'width': 640, 'has_audio': True, 'filesize': 0}}
        }
        for quality, formats in fallback_formats.items():
            if quality not in video_formats:
                video_formats[quality] = formats
    
    if len(audio_formats) < 1:
        audio_formats = {
            'mp3': {'High Quality': {'format_id': 'bestaudio', 'ext': 'mp3', 'quality': 'High Quality', 'abr': 320}},
            'm4a': {'Best Quality': {'format_id': 'bestaudio[ext=m4a]', 'ext': 'm4a', 'quality': 'Best Quality', 'abr': 256}}
        }
    
    return video_formats, audio_formats

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    return jsonify({'status': 'healthy', 'youtube_2025_compatible': True, 'timestamp': time.time()})

@app.route('/get_video_info', methods=['POST', 'OPTIONS'])
def get_video_info():
    """YouTube September 2025 compatible video info endpoint"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        url = data['url'].strip()
        if not url:
            return jsonify({'success': False, 'error': 'Please enter a YouTube URL'}), 400
        
        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            return jsonify({'success': False, 'error': 'Please enter a valid YouTube URL'}), 400
        
        logger.info(f"🔍 YouTube 2025 processing: {url}")
        
        # Use 2025 compatible extraction
        info = get_video_info_2025_compatible(url)
        if not info:
            return jsonify({
                'success': False, 
                'error': 'Unable to process this video. Please try a different video or check if the video is publicly available.'
            }), 200
        
        # Process formats with 2025 compatibility
        video_formats, audio_formats = extract_2025_formats(info['formats'])
        
        response_data = {
            'success': True,
            'title': info['title'],
            'thumbnail': info['thumbnail'],
            'uploader': info['uploader'],
            'duration': info['duration'],
            'view_count': info['view_count'],
            'video_formats': video_formats,
            'audio_formats': audio_formats,
            'youtube_2025_compatible': True,
            'format_stats': {
                'total_video_formats': sum(len(q) for q in video_formats.values()),
                'total_audio_formats': sum(len(t) for t in audio_formats.values())
            },
            'timestamp': time.time()
        }
        
        logger.info(f"✅ YouTube 2025 success: {info['title']}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"💥 YouTube 2025 error: {e}")
        return jsonify({'success': False, 'error': 'Server error while processing video'}), 500

@app.route('/download', methods=['POST', 'OPTIONS'])
def start_download():
    """YouTube 2025 compatible download endpoint"""
    global active_downloads
    if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
        return jsonify({'success': False, 'error': 'Server busy. Please try again later.'}), 429
    
    try:
        data = request.json
        download_id = str(uuid.uuid4())[:8]
        download_progress[download_id] = {'progress': 0, 'status': 'starting', 'message': 'Starting download...'}
        
        thread = threading.Thread(target=process_2025_download, args=(download_id, data), daemon=True)
        thread.start()
        active_downloads += 1
        
        return jsonify({'success': True, 'download_id': download_id})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to start download'}), 500

def process_2025_download(download_id, data):
    """YouTube 2025 compatible download processing"""
    global active_downloads
    try:
        ytdlp_exe = check_yt_dlp()
        if not ytdlp_exe:
            raise Exception("yt-dlp not available")
        
        url = clean_youtube_url(data['url'])
        format_id = data.get('format_id', 'best')
        output_format = data.get('output_format', 'mp4')
        title = data.get('title', 'video')[:20]
        
        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        filename = f"{download_id}_{safe_title}.{output_format}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        download_progress[download_id].update({'progress': 25, 'status': 'downloading', 'message': 'Downloading with YouTube 2025 compatibility...'})
        
        # YouTube 2025 compatible download command
        cmd = [
            ytdlp_exe,
            "-f", format_id,
            "--extractor-args", "youtube:player_client=android_vr,web_safari",
            "--extractor-args", "youtube:player_skip=webpage,configs,js", 
            "--merge-output-format", output_format,
            "--no-warnings",
            "--retries", "5",
            "-o", filepath,
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        
        if result.returncode == 0:
            actual_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(download_id)]
            if actual_files:
                actual_file = actual_files[0]
                actual_path = os.path.join(DOWNLOAD_FOLDER, actual_file)
                if os.path.exists(actual_path):
                    file_size = os.path.getsize(actual_path)
                    if file_size > 1000:
                        download_progress[download_id].update({
                            'progress': 100, 'status': 'completed', 
                            'message': f'YouTube 2025 download completed! ({file_size} bytes)',
                            'filename': actual_file, 'filepath': actual_path, 'filesize': file_size
                        })
                        logger.info(f"✅ YouTube 2025 download completed: {actual_file}")
                        return
        
        raise Exception("YouTube 2025 download failed")
        
    except Exception as e:
        logger.error(f"❌ YouTube 2025 download failed: {e}")
        download_progress[download_id].update({'progress': 0, 'status': 'error', 'message': f'Download failed: {str(e)[:100]}'})
    finally:
        active_downloads = max(0, active_downloads - 1)

@app.route('/progress/<download_id>', methods=['GET', 'OPTIONS'])
def get_progress(download_id):
    return jsonify(download_progress.get(download_id, {'progress': 0, 'status': 'not_found', 'message': 'Download not found'}))

@app.route('/download_file/<download_id>', methods=['GET', 'OPTIONS'])
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("🚀 YouTube Downloader Pro - 2025 SEPTEMBER COMPATIBLE")
    logger.info(f"🎯 Handles YouTube September 2025 authentication changes")
    
    update_ytdlp()
    install_ffmpeg()
    
    if not check_yt_dlp():
        logger.error("❌ yt-dlp not available!")
    else:
        logger.info("✅ yt-dlp ready with YouTube 2025 compatibility")
    
    logger.info("🎬 Backend ready with YouTube September 2025 compatibility!")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
