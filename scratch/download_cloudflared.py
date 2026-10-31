import urllib.request
import os

dest = r"C:\Users\tamersaad\Desktop\vetmind-ai\cloudflared.exe"
url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

print(f"Downloading cloudflared.exe from {url}...")
urllib.request.urlretrieve(url, dest)
size_mb = os.path.getsize(dest) / (1024 * 1024)
print(f"Downloaded cloudflared.exe successfully! Size: {size_mb:.2f} MB")
