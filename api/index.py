import sys
import os
import traceback

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from app import app
except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI()
    err_msg = traceback.format_exc()

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    async def debug_error_handler(full_path: str = ""):
        return HTMLResponse(
            f"<html><body style='font-family:sans-serif;padding:30px;background:#fff5f5;color:#c53030;'>"
            f"<h2>VetMind AI Vercel Initialization Error</h2>"
            f"<pre style='background:#fff;padding:20px;border-radius:8px;border:1px solid #feb2b2;overflow:auto;'>"
            f"{err_msg}</pre></body></html>",
            status_code=500
        )
