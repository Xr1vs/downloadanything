from http.server import BaseHTTPRequestHandler
import json
import subprocess
import sys
import urllib.parse

def install_ytdlp():
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

    def do_GET(self):
        install_ytdlp()
        import yt_dlp

        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        url = params.get('url', [''])[0].strip()

        if not url:
            return self._json({'error': 'missing url'}, 400)

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': 'in_playlist',  # fast for playlists
                'noplaylist': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if info.get('_type') == 'playlist':
                entries = info.get('entries', [])
                return self._json({
                    'type': 'playlist',
                    'title': info.get('title', 'Playlist'),
                    'count': len(entries),
                    'thumbnail': entries[0].get('thumbnail', '') if entries else '',
                    'entries': [
                        {'title': e.get('title', ''), 'id': e.get('id', ''), 'url': e.get('url') or f"https://youtube.com/watch?v={e.get('id', '')}"}
                        for e in entries[:50]  # cap at 50
                    ],
                }, 200)
            else:
                return self._json({
                    'type': 'video',
                    'title': info.get('title', 'Unknown'),
                    'author': info.get('uploader', info.get('channel', '')),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'videoId': info.get('id', ''),
                    'url': url,
                }, 200)

        except Exception as e:
            return self._json({'error': str(e)[:200]}, 500)

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
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, *args):
        pass
