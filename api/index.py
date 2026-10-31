import sys
import os

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
    """Restores the original client URL path from Vercel's x-matched-path header"""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            matched_path = headers.get(b"x-matched-path") or headers.get(b"x-forwarded-uri")
            if matched_path:
                try:
                    clean_path = matched_path.decode("utf-8").split("?")[0]
                    if clean_path and not clean_path.startswith("/api/index"):
                        scope["path"] = clean_path
                        scope["raw_path"] = clean_path.encode("utf-8")
                except Exception:
                    pass
            elif scope.get("path") in ("/api/index.py", "/api/index", "/api"):
                scope["path"] = "/"
                scope["raw_path"] = b"/"

        await self.app(scope, receive, send)

app = VercelPathMiddleware(fastapi_app)
