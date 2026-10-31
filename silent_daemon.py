"""
VetMind AI - High-Reliability Silent Background Daemon & Cloudflare Tunnel
Runs silently behind the screen with NO console window (via pythonw.exe).
Auto-starts on Windows boot/logon, serves on 0.0.0.0:8000, and provides
instant trusted HTTPS for 1-Click Android WebAPK & iOS PWA installation.
"""

import os
import sys
import time
import socket
import json
import re
import subprocess
import threading

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

LOG_FILE = os.path.join(BASE_DIR, "daemon.log")
TUNNEL_FILE = os.path.join(BASE_DIR, "tunnel_info.json")
CLOUDFLARED = os.path.join(BASE_DIR, "cloudflared.exe")

# Crucial for pythonw.exe: redirect stdout/stderr to real file before importing uvicorn
try:
    log_fp = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
    sys.stdout = log_fp
    sys.stderr = log_fp
except Exception:
    pass

def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [Daemon] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted)
    except Exception:
        pass

def is_port_in_use(port: int = 8000) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False

def run_cloudflared_tunnel():
    """Runs Cloudflare quick tunnel to give a trusted globally-valid HTTPS URL for WebAPK Android install."""
    if not os.path.exists(CLOUDFLARED):
        log("cloudflared.exe not found. Skipping HTTPS tunnel.")
        return

    while True:
        try:
            log("Starting Cloudflare Tunnel for secure HTTPS mobile access...")
            cmd = [CLOUDFLARED, "tunnel", "--url", "http://127.0.0.1:8000"]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in proc.stdout:
                m = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                if m:
                    tunnel_url = m.group(1)
                    log(f"Cloudflare HTTPS Tunnel established: {tunnel_url}")
                    try:
                        with open(TUNNEL_FILE, "w", encoding="utf-8") as f:
                            json.dump({"url": tunnel_url, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f)
                    except Exception as ex:
                        log(f"Failed to write tunnel_info.json: {ex}")
            proc.wait()
            log("Cloudflare Tunnel exited. Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            log(f"Tunnel error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)

def run_server():
    log("Checking port 8000 status...")
    if is_port_in_use(8000):
        log("Port 8000 is already active and serving. Exiting duplicate daemon process.")
        sys.exit(0)

    log("Port 8000 is free. Starting VetMind AI Uvicorn on 0.0.0.0:8000 (PC + Mobile Wi-Fi Access)...")

    # Start Cloudflare Tunnel in background thread
    t = threading.Thread(target=run_cloudflared_tunnel, daemon=True)
    t.start()
    
    import uvicorn
    
    # Restart loop: if server ever stops unexpectedly, auto-restart it
    while True:
        try:
            log("Launching uvicorn app:app on 0.0.0.0:8000...")
            uvicorn.run(
                "app:app",
                host="0.0.0.0",
                port=8000,
                log_config=None,  # Crucial for pythonw.exe: disables StreamHandler with None streams
                app_dir=BASE_DIR
            )
            log("Uvicorn terminated normally.")
            break
        except Exception as e:
            log(f"Uvicorn encountered an error: {e}. Restarting in 3 seconds...")
            time.sleep(3)

if __name__ == "__main__":
    run_server()
