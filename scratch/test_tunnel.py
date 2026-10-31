import subprocess
import re
import time
import json
import os

CLOUDFLARED = r"C:\Users\tamersaad\Desktop\vetmind-ai\cloudflared.exe"
TUNNEL_FILE = r"C:\Users\tamersaad\Desktop\vetmind-ai\tunnel_info.json"

def get_tunnel():
    cmd = [CLOUDFLARED, "tunnel", "--url", "http://127.0.0.1:8000"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    
    url = None
    start = time.time()
    while time.time() - start < 20:
        line = proc.stdout.readline()
        if not line:
            break
        print("CF:", line.strip())
        m = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
        if m:
            url = m.group(1)
            print(f"\n===> FOUND HTTPS URL: {url} <===\n")
            with open(TUNNEL_FILE, "w", encoding="utf-8") as f:
                json.dump({"url": url, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f)
            break
            
    if url:
        print("Success! Tunnel URL is:", url)
        # Keep running
        time.sleep(5)
    else:
        print("Failed to get tunnel URL within timeout")
    
    proc.terminate()

if __name__ == "__main__":
    get_tunnel()
