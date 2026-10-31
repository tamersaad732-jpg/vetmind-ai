# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def test_endpoints():
    with open(r"C:\Users\tamersaad\Desktop\vetmind-ai\tunnel_info.json", "r", encoding="utf-8") as f:
        t_data = json.load(f)
    tunnel_url = t_data.get("url")
    print(f"Active Tunnel URL: {tunnel_url}")

    # 1. Test local http://127.0.0.1:8000
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            html = res.read().decode("utf-8")
            print("Local 127.0.0.1:8000 Status:", res.status)
            print("Has Hamburger Button (☰):", "mobile-hamburger-btn" in html)
            print("Has Mobile Drawer Overlay:", "mobile-drawer-overlay" in html)
            print("Has Mobile Drawer Aside:", "id=\"mobile-drawer\"" in html)
            print("Has Quick Apps Box:", "mobile-app-box" in html)
            print("Has HTTPS Mobile Modal URL:", tunnel_url in html)
    except Exception as e:
        print("Local test error:", e)

    # 2. Test manifest
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/static/manifest.json")
        with urllib.request.urlopen(req, timeout=5) as res:
            m_json = json.loads(res.read().decode("utf-8"))
            print("Manifest status: 200, display:", m_json.get("display"), "display_override:", m_json.get("display_override"))
    except Exception as e:
        print("Manifest test error:", e)

    # 3. Test Service Worker
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/static/sw.js")
        with urllib.request.urlopen(req, timeout=5) as res:
            sw_code = res.read().decode("utf-8")
            print("Service Worker status: 200, length:", len(sw_code))
    except Exception as e:
        print("SW test error:", e)

    # 4. Test Cloudflare Live HTTPS Tunnel
    if tunnel_url:
        try:
            req = urllib.request.Request(tunnel_url + "/", headers={"User-Agent": "Mozilla/5.0 (Android; Mobile)"})
            with urllib.request.urlopen(req, timeout=12, context=ctx) as res:
                t_html = res.read().decode("utf-8")
                print("Cloudflare HTTPS Tunnel Status:", res.status)
                print("Tunnel HTML size:", len(t_html))
                print("Tunnel contains VetMind AI:", "VetMind AI" in t_html)
                print("Tunnel contains Quick Apps Box:", "mobile-app-box" in t_html)
        except Exception as e:
            print("Tunnel live test error:", e)

if __name__ == "__main__":
    test_endpoints()
