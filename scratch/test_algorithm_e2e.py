import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import sqlite3
import hashlib
from datetime import datetime
import urllib.request
import urllib.parse
import http.cookiejar

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")

def make_session_token(user_id: int) -> str:
    raw = f"{user_id}:vetmind_enterprise_2026:{datetime.now().strftime('%Y%m%d')}"
    sig = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return f"{user_id}:{sig}"

def test_full_community_algorithm():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Find admin user
    c.execute("SELECT * FROM users WHERE is_admin = 1 LIMIT 1")
    admin = dict(c.fetchone())
    print(f"[OK] Admin User: {admin['name']} (ID: {admin['id']})")
    conn.close()

    session_token = make_session_token(admin["id"])
    print(f"[OK] Generated Admin Session Token: {session_token}")

    # Setup urllib opener with CookieJar
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    # Set the cookie
    cookie = http.cookiejar.Cookie(
        version=0, name="vetmind_session", value=session_token, port=None, port_specified=False,
        domain="127.0.0.1", domain_specified=True, domain_initial_dot=False, path="/", path_specified=True,
        secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={}, rfc2109=False
    )
    cj.set_cookie(cookie)

    # 1. Test GET /community
    req = urllib.request.Request("http://127.0.0.1:8000/community")
    with opener.open(req) as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        print(f"[PASS] GET /community returned 200 OK (Content length: {len(html)})")
        assert "fb-stories-strip" in html, "Stories strip not found!"
        assert "الأكثر رواجاً وتفاعلاً" in html, "Algorithmic sorting pill not found!"

    # 2. Test Content Scorer via creating a High-Quality Clinical Post
    fields = {
        "title": "استئصال ورم خبيث في ضرع أبقار فريزيان مع بروتوكول تخدير وجراحة متقدم",
        "category": "surgery",
        "content": "تم استقبال حالة بقرة فريزيان تعاني من أعراض التهاب ضرع حاد مع وجود ورم متقيح ونزف مستمر. قمنا بإجراء فحص سريري وسونار وتحليل عينة صديد بالصبغة المجهرية لتحديد نوع البكتيريا، ثم إعطاء جرعة تخدير موضعي وبدء عملية جراحية دقيقة مع استئصال كامل للنسيج المتنكرز، وإعطاء مضاد حيوي واسع المجال ومسكن للحرارة مع خياطة تجميلية.",
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
    
    post_data = urllib.parse.urlencode(fields).encode("utf-8")
    req_post = urllib.request.Request(
        "http://127.0.0.1:8000/community/post",
        data=post_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with opener.open(req_post) as resp:
        print(f"[PASS] POST /community/post response: {resp.status} (Final URL: {resp.url})")

    # Verify post in DB & its Quality Score
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM community_posts WHERE title LIKE '%استئصال ورم خبيث%' ORDER BY id DESC LIMIT 1")
    new_post = dict(c.fetchone())
    post_id = new_post["id"]
    print(f"[PASS] New Post Created! ID: {post_id}")
    print(f"      - Title: {new_post['title']}")
    print(f"      - Quality Score: {new_post['quality_score']}% (Expected >= 85%)")
    print(f"      - Media Type: {new_post['media_type']}")
    print(f"      - Initial Virality Score: {new_post['virality_score']}")
    assert new_post['quality_score'] >= 85, "Quality score should be >= 85 for detailed clinical post!"

    # 3. Simulate Interactions to Boost Virality & Expand Reach
    # A) Add Like
    like_data = urllib.parse.urlencode({"reaction": "like"}).encode("utf-8")
    req_like = urllib.request.Request(f"http://127.0.0.1:8000/community/like/{post_id}", data=like_data)
    opener.open(req_like)

    # B) Add Top-Level Comment
    comment_data = urllib.parse.urlencode({
        "content": "حالة ممتازة وموفقة يا دكتور! ما هو نوع المضاد الحيوي المستخدم وفترة السحب (Withdrawal period)؟",
        "parent_comment_id": 0
    }).encode("utf-8")
    req_cm = urllib.request.Request(f"http://127.0.0.1:8000/community/comment/{post_id}", data=comment_data)
    opener.open(req_cm)

    # Get the comment ID
    c.execute("SELECT id FROM community_comments WHERE post_id = ? ORDER BY id DESC LIMIT 1", (post_id,))
    parent_comment_id = c.fetchone()[0]

    # C) Add Nested Reply from Post Author
    reply_data = urllib.parse.urlencode({
        "content": "أهلاً دكتور، تم استخدام Ceftiofur Sodium وريدياً مع فترة سحب 4 أيام للحليب.",
        "parent_comment_id": parent_comment_id
    }).encode("utf-8")
    req_rep = urllib.request.Request(f"http://127.0.0.1:8000/community/comment/{post_id}", data=reply_data)
    opener.open(req_rep)

    # D) Bookmark
    req_bm = urllib.request.Request(f"http://127.0.0.1:8000/community/bookmark/{post_id}", data=b"")
    opener.open(req_bm)

    # Trigger community page fetch to let algorithm update virality
    req_feed = urllib.request.Request("http://127.0.0.1:8000/community?sort=algorithmic")
    with opener.open(req_feed) as resp:
        feed_html = resp.read().decode('utf-8')

    c.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,))
    updated_post = dict(c.fetchone())
    print(f"\n[PASS] Post after Engagements:")
    print(f"      - Likes: {updated_post['likes_count']}")
    print(f"      - Comments: {updated_post['comments_count']}")
    print(f"      - Views: {updated_post['views_count']}")
    print(f"      - Virality Score: {updated_post['virality_score']}")
    print(f"      - Is Trending (Viral): {updated_post['is_trending']}")
    assert updated_post['is_trending'] == 1, "Post should be marked trending after likes and comments!"
    assert updated_post['virality_score'] > 2.0, "Virality score should increase significantly!"

    # 4. Test Admin Boost & Pin Routes
    req_boost = urllib.request.Request(f"http://127.0.0.1:8000/admin/community/boost/{post_id}")
    opener.open(req_boost)
    print(f"\n[PASS] Admin Boost Post executed")

    c.execute("SELECT is_boosted, virality_score FROM community_posts WHERE id = ?", (post_id,))
    boosted_post = dict(c.fetchone())
    print(f"      - Is Boosted: {boosted_post['is_boosted']}")
    print(f"      - Boosted Virality Score: {boosted_post['virality_score']}")
    assert boosted_post['is_boosted'] == 1, "is_boosted should be 1"
    assert boosted_post['virality_score'] > 50.0, "Boosted virality score should explode (+300 boost)"

    req_pin = urllib.request.Request(f"http://127.0.0.1:8000/admin/community/pin/{post_id}")
    opener.open(req_pin)
    print(f"[PASS] Admin Pin Post executed")
    c.execute("SELECT is_pinned FROM community_posts WHERE id = ?", (post_id,))
    pinned_post = dict(c.fetchone())
    print(f"      - Is Pinned: {pinned_post['is_pinned']}")
    assert pinned_post['is_pinned'] == 1, "is_pinned should be 1"

    # 5. Check Algorithmic Feed HTML Elements
    req_final = urllib.request.Request("http://127.0.0.1:8000/community?sort=algorithmic")
    with opener.open(req_final) as resp:
        final_feed = resp.read().decode('utf-8')
    assert f"post-{post_id}" in final_feed, "Post card not in feed!"
    assert "رائج بالخوارزمية" in final_feed, "Trending badge not rendered!"
    assert "توثيق سريري فائق" in final_feed, "Quality badge not rendered!"
    assert "صاحب الحالة" in final_feed, "Author nested badge not rendered!"
    assert "الأعلى تفاعلاً بالخوارزمية" in final_feed, "Right sidebar trending section not found!"
    assert "خوارزمية الانتشار الذكي" in final_feed, "Left sidebar reach status not found!"

    print("\n=======================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! ALGORITHM VERIFIED 100%")
    print("=======================================================")

    conn.close()

if __name__ == "__main__":
    test_full_community_algorithm()
