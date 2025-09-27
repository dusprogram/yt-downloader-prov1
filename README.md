# ⚡ YT Downloader Pro - Backend API

Fast, secure backend API for YouTube video and audio downloading.

## 🌐 Live API

**Backend**: https://yt-downloader-pro-v1-dus.railway.app

## 🛠️ Technology Stack

- **Python 3.9+**: Modern Python with type hints
- **Flask**: Lightweight web framework
- **yt-dlp**: Latest YouTube processing engine
- **FFmpeg**: Professional media processing
- **Flask-CORS**: Cross-origin resource sharing
- **Gunicorn**: Production WSGI server

## 🔥 Features

- 📹 **Video Processing**: All formats up to 1080p
- 🎵 **Audio Extraction**: MP3, M4A with high quality
- 🔊 **Audio Merging**: Guaranteed audio in video downloads
- 🚀 **Fast Processing**: Optimized download pipelines
- 🔒 **Secure**: Auto-cleanup, no data persistence
- 📊 **Health Monitoring**: Built-in health checks

## 🏗️ File Structure

```
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── Procfile           # Railway deployment
├── README.md          # This file
└── .gitignore         # Python ignores
```

## 📋 API Endpoints

### Health Check

```http
GET /health
```

### Get Video Information

```http
POST /get_video_info
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=VIDEO_ID"
}
```

### Start Download

```http
POST /download
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=VIDEO_ID",
  "format_id": "best",
  "output_format": "mp4",
  "type": "video",
  "title": "Video Title"
}
```

### Check Progress

```http
GET /progress/{download_id}
```

### Download File

```http
GET /download_file/{download_id}
```

## ⚙️ Configuration

### Environment Variables

```bash
PORT=5000                    # Server port
MAX_DOWNLOADS=3              # Concurrent download limit
CLEANUP_SECONDS=120          # File cleanup interval
```

### CORS Settings

```python
CORS(app, origins=[
    "https://yt-downloader-pro-v011.netlify.app",
    "http://localhost:3000",
    "http://localhost:8000"
])
```

## 🚀 Local Development

```bash
# Clone repository
git clone https://github.com/dusprogram/yt-downloader-prov1.git
cd yt-downloader-prov1

# Install dependencies
pip install -r requirements.txt

# Install yt-dlp
pip install yt-dlp

# Run development server
python app.py

# API available at:
http://localhost:5000
```

## 📦 Deployment

### Railway Deployment

1. Push changes to GitHub
2. Railway automatically deploys
3. API live at: https://yt-downloader-pro-v1-dus.railway.app

### Manual Deployment

```bash
# Build
pip install -r requirements.txt

# Run production
gunicorn --bind 0.0.0.0:5000 app:app
```

## 🔧 Dependencies

```txt
Flask==3.0.0
Flask-CORS==4.0.0
yt-dlp==2023.12.30
Werkzeug==3.0.1
gunicorn==21.2.0
```

## 📊 Performance

- **Response Time**: <500ms average
- **Concurrent Downloads**: 3 simultaneous
- **File Cleanup**: Automatic after 2 minutes
- **Memory Usage**: Optimized for Railway limits

## 🔗 Related Repositories

- **Frontend**: https://github.com/dusprogram/yt-downloader-pro

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-api-feature`
3. Commit changes: `git commit -m 'Add new API feature'`
4. Push branch: `git push origin feature/new-api-feature`
5. Open Pull Request

## 📄 License

MIT License - see LICENSE file for details.

---

**Backend API for YT Downloader Pro - Powered by Railway**
