import urllib.request
import urllib.parse
import json
import sqlite3
import os

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")

def test_algorithm_e2e():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get admin user
    c.execute("SELECT * FROM users WHERE is_admin = 1 LIMIT 1")
    admin = c.fetchone()
    print(f"Admin User: {admin['name']} (ID: {admin['id']})")

    # Check posts in DB
    c.execute("SELECT id, title, quality_score, virality_score, is_boosted, is_pinned, is_trending, likes_count, comments_count FROM community_posts ORDER BY id DESC LIMIT 5")
    posts = c.fetchall()
    print(f"\nFound {len(posts)} recent posts in community:")
    for p in posts:
        print(f"Post #{p['id']}: '{p['title'][:30]}' | Quality: {p['quality_score']}% | Virality: {p['virality_score']} | Likes: {p['likes_count']} | Comments: {p['comments_count']} | Boost: {p['is_boosted']} | Pin: {p['is_pinned']} | Trending: {p['is_trending']}")

    conn.close()

    # Test HTTP request to /community with admin session cookie
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # Login as admin to get session cookie
    login_data = urllib.parse.urlencode({
        "username": admin["username"],
        "password": "Password123!" # Check if login succeeds or set session directly
    }).encode("utf-8")

    # Let's inspect /community HTML directly by setting cookie
    # VetMind uses cookie 'vetmind_session' or similar. Let's check how session works in app.py
    
test_algorithm_e2e()
