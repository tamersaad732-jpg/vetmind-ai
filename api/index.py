import sys
import os
import urllib.parse

# Ensure project root is in sys.path
cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import app as fastapi_app

class VercelPathMiddleware:
    """Restores the original client URL path from Vercel's rewrite query parameter or headers"""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            qs = scope.get("query_string", b"").decode("utf-8")
            params = urllib.parse.parse_qs(qs)
            
            # Read original path forwarded from vercel.json
            orig_path = params.get("__orig_path", [None])[0]
            if not orig_path:
                headers = dict(scope.get("headers", []))
                matched = headers.get(b"x-matched-path") or headers.get(b"x-forwarded-uri")
                if matched:
                    try:
                        orig_path = matched.decode("utf-8").split("?")[0]
                    except Exception:
                        pass

            if orig_path:
                while "//" in orig_path:
                    orig_path = orig_path.replace("//", "/")
                scope["path"] = orig_path
                scope["raw_path"] = orig_path.encode("utf-8")
            elif scope.get("path") in ("/api/index.py", "/api/index", "/api"):
                scope["path"] = "/"
                scope["raw_path"] = b"/"

        await self.app(scope, receive, send)

app = VercelPathMiddleware(fastapi_app)
