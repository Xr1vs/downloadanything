from http.server import BaseHTTPRequestHandler
import json
import subprocess
import sys
import os
import urllib.parse

def install_ytdlp():
    """Install yt-dlp if not present (Vercel serverless cold start)"""
    try:
        import yt_dlp
        return True
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'yt-dlp', '-q', '--target', '/tmp/deps'])
        sys.path.insert(0, '/tmp/deps')
        return True

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        install_ytdlp()
        import yt_dlp

        content_len = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_len) or b'{}')

        url       = body.get('url', '').strip()
        mode      = body.get('mode', 'audio')       # audio | video
        audio_fmt = body.get('audioFormat', 'mp3')
        quality   = body.get('videoQuality', '1080')

        if not url:
            return self._json({'error': 'missing url'}, 400)

        try:
            # Build yt-dlp options to extract info + direct URL
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'skip_download': True,
                # Don't actually download — just get the URL
            }

            if mode == 'audio':
                ydl_opts['format'] = 'bestaudio/best'
            elif mode == 'video':
                ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'
            else:  # mute
                ydl_opts['format'] = f'bestvideo[height<={quality}]/best[height<={quality}]'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Get the direct stream URL
            if 'requested_formats' in info:
                # Merged format (video+audio) — return both
                formats = info['requested_formats']
                result = {
                    'status': 'multi',
                    'title': info.get('title', 'download'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'urls': [f.get('url') for f in formats if f.get('url')],
                    'ext': info.get('ext', 'mp4'),
                }
            else:
                direct_url = info.get('url') or (info.get('formats', [{}])[-1].get('url'))
                ext = info.get('ext', 'mp3' if mode == 'audio' else 'mp4')
                result = {
                    'status': 'redirect',
                    'url': direct_url,
                    'title': info.get('title', 'download'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'ext': ext,
                    'filename': sanitize(info.get('title', 'download')) + '.' + ext,
                }

            return self._json(result, 200)

        except Exception as e:
            err = str(e)
            # Friendlier error messages
            if 'Sign in' in err or 'age' in err.lower():
                err = 'video is age-restricted or requires sign-in'
            elif 'not available' in err.lower():
                err = 'video is unavailable or private'
            elif 'copyright' in err.lower():
                err = 'video blocked due to copyright'
            return self._json({'error': err[:200]}, 500)

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, *args):
        pass

def sanitize(name):
    import re
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:60]
