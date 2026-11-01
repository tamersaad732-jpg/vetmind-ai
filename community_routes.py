import os
import re
import json
import shutil
import sqlite3
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from vetbook_algorithms import (
    calculate_edgerank_score,
    get_people_you_may_know,
    get_trending_topics,
    get_recommended_groups,
    get_similar_cases
)

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")
if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
    tmp_db = "/tmp/vetmind.db"
    if not os.path.exists(tmp_db):
        if os.path.exists(DB_PATH):
            try:
                shutil.copy2(DB_PATH, tmp_db)
            except Exception:
                pass
    if os.path.exists(tmp_db):
        DB_PATH = tmp_db
    UPLOAD_DIR = "/tmp/uploads"

try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except Exception:
    pass

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn

# ==============================================================================
# MULTI-LAYER COMMUNITY POSTS PERSISTENCE & GLOBAL SYNC ENGINE
# ==============================================================================
COMMUNITY_SYNC_FILE = os.path.join(UPLOAD_DIR, "community_posts_sync.json")
COMMUNITY_BACKUP_ALT = os.path.join(BASE_DIR, "static", "community_posts_sync.json")

def get_sync_file_path():
    try:
        if os.path.exists(COMMUNITY_SYNC_FILE):
            return COMMUNITY_SYNC_FILE
        if os.path.exists(COMMUNITY_BACKUP_ALT):
            return COMMUNITY_BACKUP_ALT
        return COMMUNITY_SYNC_FILE
    except Exception:
        return "/tmp/community_posts_sync.json"

def save_post_to_backup_sync(post_dict: dict):
    """Permanently backs up a post to JSON to survive serverless container lifecycles."""
    try:
        fpath = get_sync_file_path()
        existing = []
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                existing = json.load(f)
        # Avoid duplicates by title + created_at
        exists = any(
            (p.get("title") == post_dict.get("title") and p.get("created_at") == post_dict.get("created_at"))
            for p in existing
        )
        if not exists:
            existing.insert(0, post_dict)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(existing[:200], f, ensure_ascii=False, indent=2)
            if fpath != COMMUNITY_BACKUP_ALT:
                try:
                    os.makedirs(os.path.dirname(COMMUNITY_BACKUP_ALT), exist_ok=True)
                    with open(COMMUNITY_BACKUP_ALT, "w", encoding="utf-8") as f2:
                        json.dump(existing[:200], f2, ensure_ascii=False, indent=2)
                except Exception:
                    pass
    except Exception as e:
        print("save_post_to_backup_sync error:", e)

def sync_posts_from_backup_sync(conn):
    """Restores any backed up posts into SQLite community_posts table."""
    try:
        fpath = get_sync_file_path()
        if not os.path.exists(fpath) and os.path.exists(COMMUNITY_BACKUP_ALT):
            fpath = COMMUNITY_BACKUP_ALT
        if not os.path.exists(fpath):
            return
        with open(fpath, "r", encoding="utf-8") as f:
            backup_posts = json.load(f)
        if not backup_posts:
            return
        c = conn.cursor()
        c.execute("SELECT title, created_at FROM community_posts")
        existing_keys = set((r[0], r[1]) for r in c.fetchall())

        for p in backup_posts:
            key = (p.get("title"), p.get("created_at"))
            if key not in existing_keys and p.get("title") and p.get("content"):
                c.execute("""
                INSERT INTO community_posts (
                    user_id, author_name, author_specialty, author_country,
                    category, title, content, is_urgent, species, breed, age, weight,
                    gender, symptoms, medications, group_id, image_path, video_path,
                    media_type, quality_score, virality_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p.get("user_id", 4),
                    p.get("author_name", "طبيب بيطري"),
                    p.get("author_specialty", "طب وجراحة الحيوان"),
                    p.get("author_country", "مصر"),
                    p.get("category", "case_study"),
                    p.get("title", "حالة سريرية"),
                    p.get("content", ""),
                    p.get("is_urgent", 0),
                    p.get("species", ""),
                    p.get("breed", ""),
                    p.get("age", ""),
                    p.get("weight", ""),
                    p.get("gender", ""),
                    p.get("symptoms", ""),
                    p.get("medications", ""),
                    p.get("group_id", 0),
                    p.get("image_path"),
                    p.get("video_path"),
                    p.get("media_type", "text"),
                    p.get("quality_score", 10),
                    p.get("virality_score", 5.0),
                    p.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                ))
                existing_keys.add(key)
        conn.commit()
    except Exception as e:
        print("sync_posts_from_backup_sync error:", e)

def is_user_community_approved(user_dict: dict) -> bool:
    """100% Free Community: Any logged-in registered veterinarian has complete access."""
    return bool(user_dict)

def init_community_schema():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 1. Connection table for colleagues & followers (Replaces private DMs with public social networking)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            colleague_id INTEGER NOT NULL,
            status TEXT DEFAULT 'connected',
            created_at TEXT NOT NULL,
            UNIQUE(user_id, colleague_id)
        )
        """)

        # 2. Check community_posts columns
        c.execute("PRAGMA table_info(community_posts)")
        post_cols = [r["name"] for r in c.fetchall()]
        cols_to_add = [
            ("is_urgent", "INTEGER DEFAULT 0"),
            ("species", "TEXT DEFAULT ''"),
            ("breed", "TEXT DEFAULT ''"),
            ("age", "TEXT DEFAULT ''"),
            ("weight", "TEXT DEFAULT ''"),
            ("gender", "TEXT DEFAULT ''"),
            ("symptoms", "TEXT DEFAULT ''"),
            ("history", "TEXT DEFAULT ''"),
            ("diagnosis", "TEXT DEFAULT ''"),
            ("medications", "TEXT DEFAULT ''"),
            ("lab_files", "TEXT DEFAULT ''"),
            ("extra_images", "TEXT DEFAULT ''"),
            ("group_id", "INTEGER DEFAULT 0"),
            ("poll_data", "TEXT DEFAULT ''"),
            ("ai_analysis", "TEXT DEFAULT ''"),
            ("shares_count", "INTEGER DEFAULT 0"),
            ("bookmarks_count", "INTEGER DEFAULT 0"),
            ("specialized_reactions_count", "INTEGER DEFAULT 0"),
            ("detailed_comments_count", "INTEGER DEFAULT 0"),
            ("has_best_answer", "INTEGER DEFAULT 0")
        ]
        for col, ctype in cols_to_add:
            if col not in post_cols:
                try:
                    c.execute(f"ALTER TABLE community_posts ADD COLUMN {col} {ctype}")
                except Exception:
                    pass

        # 3. Check community_comments columns
        c.execute("PRAGMA table_info(community_comments)")
        cm_cols = [r["name"] for r in c.fetchall()]
        for col, ctype in [
            ("image_url", "TEXT DEFAULT ''"),
            ("is_best_answer", "INTEGER DEFAULT 0"),
            ("is_ai_comment", "INTEGER DEFAULT 0")
        ]:
            if col not in cm_cols:
                try:
                    c.execute(f"ALTER TABLE community_comments ADD COLUMN {col} {ctype}")
                except Exception:
                    pass

        # 4. Check users columns
        c.execute("PRAGMA table_info(users)")
        u_cols = [r["name"] for r in c.fetchall()]
        for col, ctype in [
            ("bio", "TEXT DEFAULT ''"),
            ("cover_photo", "TEXT DEFAULT ''"),
            ("reputation_score", "INTEGER DEFAULT 100"),
            ("verified_vet", "INTEGER DEFAULT 1")
        ]:
            if col not in u_cols:
                try:
                    c.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
                except Exception:
                    pass

        # 5. Specialized Groups
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT DEFAULT '🩺',
            category TEXT DEFAULT 'general',
            members_count INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS community_group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at TEXT NOT NULL,
            UNIQUE(group_id, user_id)
        )
        """)

        # 6. Events / Webinars
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date_time TEXT NOT NULL,
            location TEXT NOT NULL,
            interested_count INTEGER DEFAULT 0
        )
        """)

        # Seed groups if empty
        c.execute("SELECT count(*) FROM community_groups")
        if c.fetchone()[0] == 0:
            demo_groups = [
                ("نادي جراحة الحيوانات الأليفة", "مناقشة أحدث تقنيات جراحة العظام والأنسجة الرخوة في الكلاب والقطط", "🐕", "pets", 142),
                ("رابطة طب وتناسل المجترات", "بروتوكولات التلقيح الاصطناعي، علاج العقم، ومشاكل الضرع والولادة في الأبقار", "🐄", "bovine", 118),
                ("ملتقى طب وجراحة الخيول العربي", "تشخيص المغص الحاد، أمراض العرج، والمناظير البيطرية المتقدمة", "🐎", "equine", 95),
                ("مجلس أمراض الدواجن والأوبئة", "تشخيص الأمراض الفيروسية (نيوكاسل، جامبورو) وتصميم جداول اللقاحات", "🐔", "poultry", 84),
                ("الجمعية البيطرية للأشعة والسونار", "قراءة السونار، الأشعة السينية، والرنين المغناطيسي الإكلينيكي", "📡", "diagnostics", 163)
            ]
            for g_name, g_desc, g_icon, g_cat, g_mem in demo_groups:
                c.execute("""
                INSERT INTO community_groups (name, description, icon, category, members_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (g_name, g_desc, g_icon, g_cat, g_mem, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        # Seed events if empty
        c.execute("SELECT count(*) FROM community_events")
        if c.fetchone()[0] == 0:
            demo_events = [
                ("مؤتمر الطب البيطري العربي للحيوانات الأليفة 2026", "الخميس 12 نوفمبر • 10:00 ص", "مركز المؤتمرات - القاهرة & بث مباشر", 87),
                ("ويبينار: التحديثات العالمية في علاج مغص الخيول الحاد", "الإثنين 16 نوفمبر • 08:00 م", "Zoom Webinar Online", 134),
                ("ورشة عمل: قراءة وفحص السونار البطني للحوامل في الأبقار", "السبت 21 نوفمبر • 02:00 م", "مستشفى الطب البيطري التعليمي", 62)
            ]
            for e_title, e_dt, e_loc, e_int in demo_events:
                c.execute("INSERT INTO community_events (title, date_time, location, interested_count) VALUES (?, ?, ?, ?)",
                          (e_title, e_dt, e_loc, e_int))

        conn.commit()
        conn.close()
    except Exception as e:
        print("Schema init notice:", e)

init_community_schema()

CATEGORIES = {
    "all": {"name": "جميع الأقسام", "icon": "🌐", "color": "#0f766e"},
    "case_study": {"name": "استشارة سريرية", "icon": "🩺", "color": "#0f766e"},
    "urgent": {"name": "حالة طارئة حرجة", "icon": "🚨", "color": "#dc2626"},
    "videos": {"name": "فيديوهات الجراحة", "icon": "🎥", "color": "#0284c7"},
    "poll": {"name": "استطلاع رأي طبي", "icon": "📊", "color": "#7c3aed"},
    "bookmarks": {"name": "حالاتي المحفوظة", "icon": "🔖", "color": "#d97706"}
}

SPECIES_MAP = {
    "all": "🐾 كافة الفصائل",
    "pets": "🐕 حيوانات أليفة (كلاب وقطط)",
    "bovine": "🐄 مجترات (أبقار وجاموس)",
    "equine": "🐎 خيول وبغال",
    "ovine": "🐑 أغنام وماعز",
    "poultry": "🐔 دواجن وطيور",
    "wild": "🦅 حياة برية وغريبة"
}

REACTIONS = {
    "like": {"label": "إعجاب", "icon": "👍", "color": "#0f766e"},
    "vital": {"label": "حالة مهمة", "icon": "❤️", "color": "#dc2626"},
    "insight": {"label": "تشخيص دقيق", "icon": "💡", "color": "#d97706"},
    "followup": {"label": "متابعة", "icon": "🤔", "color": "#7c3aed"},
    "healing": {"label": "شفاء ودعم", "icon": "🐾", "color": "#059669"}
}

def extract_youtube_embed(url: str) -> str:
    if not url:
        return ""
    if "youtu.be/" in url:
        vid_id = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
        return f"https://www.youtube.com/embed/{vid_id}"
    if "watch?v=" in url:
        vid_id = url.split("watch?v=")[1].split("&")[0]
        return f"https://www.youtube.com/embed/{vid_id}"
    if "embed/" in url:
        return url
    return ""

def evaluate_clinical_content(title: str, content: str, has_media: bool, is_urgent: bool, has_details: bool) -> dict:
    score = 50
    words = len(content.split())
    if words >= 30:
        score += 15
    if words >= 80:
        score += 10
    if has_media:
        score += 15
    if has_details:
        score += 10
    if is_urgent:
        score += 5
    score = min(100, score)
    return {"score": score}

def compute_virality_score(post_dict: dict) -> float:
    likes = post_dict.get("likes_count", 0)
    comments = post_dict.get("comments_count", 0)
    views = max(1, post_dict.get("views_count", 1))
    shares = post_dict.get("shares_count", 0)
    bookmarks = post_dict.get("bookmarks_count", 0)
    engagement = (likes * 1.5) + (comments * 3.0) + (shares * 5.0) + (bookmarks * 4.0)
    virality = (engagement / views) * 10.0
    return round(virality, 2)



COMMUNITY_CSS = """
<style>
/* ==============================================================================
   VETBOOK - FACEBOOK-SCALE VETERINARY SOCIAL NETWORK DESIGN SYSTEM
   ============================================================================== */
:root {
    --fb-bg: #f0f2f5;
    --fb-card: #ffffff;
    --fb-primary: #0f766e;
    --fb-primary-hover: #115e59;
    --fb-accent: #ea580c;
    --fb-urgent: #dc2626;
    --fb-text: #0f172a;
    --fb-text-muted: #64748b;
    --fb-border: #e2e8f0;
    --fb-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --fb-shadow-hover: 0 6px 16px rgba(0,0,0,0.09);
    --fb-font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

body.dark-theme, html.dark-theme, [data-theme="dark"] {
    --fb-bg: #0b1120;
    --fb-card: #1e293b;
    --fb-text: #f1f5f9;
    --fb-text-muted: #94a3b8;
    --fb-border: #334155;
    --fb-shadow: 0 2px 8px rgba(0,0,0,0.3);
    --fb-shadow-hover: 0 8px 24px rgba(0,0,0,0.4);
}

*, *::before, *::after {
    box-sizing: border-box;
}

/* Strict Anti-Overlap Typography Rules */
body {
    letter-spacing: 0 !important;
}

.fb-app-wrapper {
    background-color: var(--fb-bg);
    min-height: 100vh;
    padding-bottom: 85px;
    max-width: 100vw;
    width: 100%;
    overflow-x: hidden;
    box-sizing: border-box;
}

/* VetBook Sub-Navigation Strip (Facebook Style Header Pills) */
.vetbook-subnav-strip {
    background: var(--fb-card);
    border-bottom: 1px solid var(--fb-border);
    position: sticky;
    top: 56px;
    z-index: 100;
    padding: 6px 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    overflow-x: auto;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}
.vetbook-subnav-strip::-webkit-scrollbar { display: none; }

.vetbook-nav-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 24px;
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--fb-text-muted);
    text-decoration: none;
    white-space: nowrap;
    transition: all 0.18s ease;
    border: 1px solid transparent;
}
.vetbook-nav-pill:hover {
    background: rgba(15, 118, 110, 0.08);
    color: var(--fb-primary);
}
.vetbook-nav-pill.active {
    background: #0f766e;
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(15, 118, 110, 0.25);
}

/* 3-Column Desktop Grid (RTL First: Right Column is Right Sidebar, Left is Left Sidebar) */
.fb-container {
    max-width: 1480px;
    width: 100%;
    margin: 0 auto;
    padding: 18px 12px;
    display: grid;
    grid-template-columns: 280px 1fr 310px;
    gap: 20px;
    align-items: start;
    box-sizing: border-box;
}

@media (max-width: 1140px) {
    .fb-container {
        grid-template-columns: 240px 1fr;
        gap: 16px;
    }
    .fb-left-col {
        display: none !important;
    }
}

@media (max-width: 768px) {
    .fb-container {
        grid-template-columns: 1fr !important;
        padding: 8px 4px !important;
        gap: 10px !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
    .fb-right-col {
        display: none !important;
    }
    .fb-main-feed {
        width: 100% !important;
        max-width: 100vw !important;
        min-width: 0 !important;
    }
}

.fb-card {
    background: var(--fb-card);
    border: 1px solid var(--fb-border);
    border-radius: 16px;
    box-shadow: var(--fb-shadow);
    transition: all 0.2s ease;
    box-sizing: border-box;
    overflow: hidden;
    max-width: 100%;
    width: 100%;
    overflow-wrap: break-word;
    word-break: normal;
}

.fb-sticky-sidebar {
    position: sticky;
    top: 115px;
    display: flex;
    flex-direction: column;
    gap: 14px;
}

/* Stories Bar */
.fb-stories-strip {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding: 4px 2px 10px 2px;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
}
.fb-stories-strip::-webkit-scrollbar { display: none; }

.fb-story-card {
    min-width: 112px;
    width: 112px;
    height: 180px;
    border-radius: 14px;
    overflow: hidden;
    position: relative;
    cursor: pointer;
    flex-shrink: 0;
    transition: transform 0.2s, box-shadow 0.2s;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    background-size: cover;
    background-position: center;
}
.fb-story-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 14px rgba(0,0,0,0.18);
}
.fb-story-create-card {
    background: linear-gradient(180deg, #ecfdf5 0%, #d1fae5 100%);
    border: 1.5px dashed #0f766e;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 10px;
}

/* Post Composer */
.fb-composer-box {
    padding: 14px 18px;
    margin-bottom: 16px;
}
.fb-composer-input {
    background: var(--fb-bg);
    border: 1px solid var(--fb-border);
    border-radius: 25px;
    padding: 12px 18px;
    width: 100%;
    color: var(--fb-text-muted);
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    text-align: right;
    transition: background 0.2s;
    outline: none;
    line-height: 1.45;
}
.fb-composer-input:hover {
    background: #e2e8f0;
}
body.dark-theme .fb-composer-input:hover {
    background: #334155;
}

/* Clinical Demographics Badge Box */
.case-demographics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 8px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 10px 14px;
    margin: 12px 0;
    font-size: 0.82rem;
    line-height: 1.6;
}
body.dark-theme .case-demographics-grid {
    background: #0f172a;
    border-color: #334155;
}

/* Urgent Case Glowing Border & Banner */
.urgent-post-card {
    border-top: 5px solid #dc2626 !important;
    border-right: 2px solid #ef4444 !important;
    box-shadow: 0 0 18px rgba(220, 38, 38, 0.15) !important;
}

.urgent-banner-row {
    background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
    border-bottom: 1.5px solid #f87171;
    padding: 8px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #991b1b;
    font-weight: 800;
    font-size: 0.84rem;
    flex-wrap: wrap;
    gap: 6px;
    box-sizing: border-box;
    width: 100%;
    line-height: 1.5;
}
.urgent-banner-left {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1 1 auto;
    min-width: 0;
    overflow-wrap: break-word;
    word-break: normal;
}
.urgent-badge {
    background: #dc2626;
    color: #ffffff;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.7rem;
    white-space: nowrap;
    flex-shrink: 0;
}

/* Facebook Smart Media Grid */
.fb-media-grid {
    margin: 12px 0;
    border-radius: 12px;
    overflow: hidden;
    background: #0f172a;
    width: 100%;
}
.fb-media-grid.grid-1 img {
    width: 100%;
    max-height: 520px;
    object-fit: contain;
    display: block;
    cursor: zoom-in;
}
.fb-media-grid.grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
}
.fb-media-grid.grid-2 img {
    width: 100%;
    height: 280px;
    object-fit: cover;
    cursor: zoom-in;
}
.fb-media-grid.grid-3 {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 4px;
    height: 320px;
}
.fb-media-grid.grid-3 .media-col-left img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    cursor: zoom-in;
}
.fb-media-grid.grid-3 .media-col-right {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.fb-media-grid.grid-3 .media-col-right img {
    width: 100%;
    height: calc(160px - 2px);
    object-fit: cover;
    cursor: zoom-in;
}
.fb-media-grid.grid-4 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
}
.fb-media-grid.grid-4 .media-slot {
    position: relative;
    height: 180px;
    overflow: hidden;
}
.fb-media-grid.grid-4 .media-slot img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    cursor: zoom-in;
}
.fb-media-grid .media-more-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.68);
    color: white;
    font-size: 1.4rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    backdrop-filter: blur(2px);
}

/* Reaction Bar Popup */
.reaction-wrapper {
    position: relative;
    display: inline-block;
}
.fb-reactions-popup {
    position: absolute;
    bottom: calc(100% + 6px);
    right: 0;
    background: var(--fb-card);
    border: 1px solid var(--fb-border);
    border-radius: 30px;
    padding: 6px 14px;
    display: none;
    gap: 10px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.18);
    z-index: 100;
    animation: popUpAnim 0.2s ease-out;
}
@keyframes popUpAnim {
    from { opacity: 0; transform: translateY(10px) scale(0.9); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}
.reaction-item-btn {
    background: none;
    border: none;
    font-size: 1.45rem;
    cursor: pointer;
    transition: transform 0.15s ease;
    padding: 2px;
    line-height: 1;
}
.reaction-item-btn:hover {
    transform: scale(1.4) translateY(-3px);
}

.fb-action-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid var(--fb-border);
    position: relative;
    flex-wrap: wrap;
    gap: 4px;
    box-sizing: border-box;
    width: 100%;
}
.fb-action-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.85rem;
    padding: 6px 10px;
    border-radius: 8px;
    transition: background 0.15s ease;
    white-space: nowrap;
    text-decoration: none;
}
.fb-action-btn:hover {
    background: rgba(0,0,0,0.04);
}

/* Threaded Comments & Bubbles */
.fb-comment-bubble {
    background: #f1f5f9;
    border-radius: 18px;
    padding: 10px 16px;
    color: var(--fb-text);
    font-size: 0.9rem;
    line-height: 1.75;
    word-break: normal;
    overflow-wrap: break-word;
}
body.dark-theme .fb-comment-bubble {
    background: #0f172a;
    border: 1px solid #334155;
}

.best-answer-bubble {
    background: #ecfdf5 !important;
    border: 1.5px solid #10b981 !important;
}
body.dark-theme .best-answer-bubble {
    background: #064e3b !important;
    border-color: #059669 !important;
}

/* Species & Sort Filter Strips */
.species-strip-container {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 10px;
    margin-bottom: 8px;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
}
.species-strip-container::-webkit-scrollbar { display: none; }

.sort-pills-scroll {
    display: flex;
    align-items: center;
    gap: 6px;
    overflow-x: auto;
    padding-bottom: 4px;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    max-width: 100%;
}
.sort-pills-scroll::-webkit-scrollbar { display: none; }

/* PYMK & Trending Widgets */
.pymk-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px;
    border-radius: 12px;
    background: var(--fb-bg);
    border: 1px solid var(--fb-border);
    margin-bottom: 8px;
    gap: 8px;
}
.trending-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 20px;
    background: var(--fb-bg);
    border: 1px solid var(--fb-border);
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--fb-text);
    text-decoration: none;
    transition: all 0.15s ease;
}
.trending-pill:hover {
    border-color: #0f766e;
    color: #0f766e;
}

/* Mobile & Universal Responsiveness */
@media (max-width: 768px) {
    .fb-container {
        padding: 6px 4px !important;
        gap: 10px !important;
        width: 100% !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
    .fb-card {
        border-radius: 12px !important;
    }
    .fb-card-content {
        padding: 12px 10px !important;
    }
    .fb-composer-box {
        padding: 10px 10px !important;
    }
    .fb-action-bar {
        gap: 2px !important;
        padding: 4px 0 !important;
    }
    .fb-action-btn {
        padding: 5px 6px !important;
        font-size: 0.74rem !important;
        gap: 3px !important;
        flex: 1 1 auto;
        min-width: fit-content;
        justify-content: center;
    }
    .urgent-banner-row {
        padding: 6px 10px !important;
        font-size: 0.78rem !important;
    }
    .case-demographics-grid {
        grid-template-columns: 1fr 1fr !important;
        padding: 8px 10px !important;
        gap: 6px !important;
        font-size: 0.76rem !important;
    }
}

@media (max-width: 480px) {
    .fb-action-btn {
        padding: 4px 4px !important;
        font-size: 0.70rem !important;
    }
    .case-demographics-grid {
        grid-template-columns: 1fr !important;
    }
    .fb-composer-input {
        font-size: 0.85rem !important;
        padding: 10px 12px !important;
    }
}

/* Doctor Profile Header Styles (Zero-Overflow Universal Scaling) */
.fb-profile-cover {
    height: clamp(120px, 25vw, 180px);
    border-radius: 16px 16px 0 0;
    position: relative;
}
.fb-profile-header-body {
    padding: 0 clamp(12px, 3.5vw, 24px) 20px clamp(12px, 3.5vw, 24px);
    position: relative;
}
.profile-header-avatar-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: clamp(-42px, -9vw, -55px);
    margin-bottom: 16px;
    width: 100%;
}
.profile-header-avatar {
    width: clamp(68px, 16vw, 105px) !important;
    height: clamp(68px, 16vw, 105px) !important;
    min-width: clamp(68px, 16vw, 105px) !important;
    max-width: clamp(68px, 16vw, 105px) !important;
    border-radius: 50% !important;
    border: 3.5px solid var(--fb-card) !important;
    background: linear-gradient(135deg, #0f766e, #0d9488) !important;
    color: #ffffff !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: clamp(1.9rem, 4.5vw, 2.8rem) !important;
    font-weight: 800 !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.15) !important;
    flex-shrink: 0 !important;
}
.profile-header-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
}
@media (max-width: 600px) {
    .profile-header-actions .btn {
        padding: 6px 12px !important;
        font-size: 0.78rem !important;
    }
}
</style>
"""

COMMUNITY_JS = """
<script>
function openComposerModal(mode) {
    const m = document.getElementById('new-post-modal');
    if (m) {
        m.style.display = 'flex';
        const urgCheck = document.getElementById('urgent-checkbox');
        const urgVal = document.getElementById('comp-is-urgent');
        const catVal = document.getElementById('comp-category');
        const titleElem = document.getElementById('modal-title');
        const demoBox = document.getElementById('clinical-fields-box');
        
        if (mode === 'urgent') {
            if (urgCheck) urgCheck.checked = true;
            if (urgVal) urgVal.value = '1';
            if (catVal) catVal.value = 'urgent';
            if (titleElem) titleElem.innerText = '🚨 نشر حالة طارئة ومستعجلة';
            if (demoBox) demoBox.style.display = 'block';
        } else if (mode === 'case') {
            if (urgCheck) urgCheck.checked = false;
            if (urgVal) urgVal.value = '0';
            if (catVal) catVal.value = 'case_study';
            if (titleElem) titleElem.innerText = '🩺 نشر حالة سريرية واستشارة';
            if (demoBox) demoBox.style.display = 'block';
        } else if (mode === 'video') {
            if (urgCheck) urgCheck.checked = false;
            if (urgVal) urgVal.value = '0';
            if (catVal) catVal.value = 'videos';
            if (titleElem) titleElem.innerText = '🎥 نشر فيديو جراحي وسريري';
            if (demoBox) demoBox.style.display = 'none';
        } else {
            if (urgCheck) urgCheck.checked = false;
            if (urgVal) urgVal.value = '0';
            if (catVal) catVal.value = 'case_study';
            if (titleElem) titleElem.innerText = '📝 إنشاء منشور عام في VetBook';
            if (demoBox) demoBox.style.display = 'none';
        }
    }
}

function closeComposerModal() {
    const m = document.getElementById('new-post-modal');
    if (m) m.style.display = 'none';
}

function openStoryModal() {
    const m = document.getElementById('story-upload-modal');
    if (m) m.style.display = 'flex';
}

let storyTimer = null;
function openStoryViewer(author, src, caption) {
    const m = document.getElementById('story-viewer-modal');
    if (m) {
        document.getElementById('story-author-tag').innerText = 'د. ' + author;
        document.getElementById('story-img-elem').src = src;
        document.getElementById('story-caption-elem').innerText = caption || '';
        m.style.display = 'flex';

        // Animated progress bar (5s duration)
        const prog = document.getElementById('story-progress-bar');
        if (prog) {
            prog.style.width = '0%';
            clearTimeout(storyTimer);
            setTimeout(() => { prog.style.width = '100%'; }, 50);
            storyTimer = setTimeout(() => { m.style.display = 'none'; }, 5100);
        }
    }
}

function sendStoryReaction(emoji) {
    alert('تم إرسال تفاعل ' + emoji + ' مع القصة السريرية للزميل بنجاح!');
}

function openImageModal(src) {
    const m = document.getElementById('image-modal');
    const img = document.getElementById('image-modal-src');
    if (m && img) {
        img.src = src;
        m.style.display = 'flex';
    }
}

function showReactionsPopup(postId) {
    const p = document.getElementById('reactions-popup-' + postId);
    if (p) p.style.display = 'flex';
}

function hideReactionsPopup(postId) {
    const p = document.getElementById('reactions-popup-' + postId);
    if (p) p.style.display = 'none';
}

async function setPostReaction(postId, rType) {
    hideReactionsPopup(postId);
    const rMeta = {
        like: { label: 'إعجاب', icon: '👍', color: '#0f766e' },
        vital: { label: 'حالة مهمة', icon: '❤️', color: '#dc2626' },
        insight: { label: 'تشخيص دقيق', icon: '💡', color: '#d97706' },
        followup: { label: 'متابعة', icon: '🤔', color: '#7c3aed' },
        healing: { label: 'شفاء ودعم', icon: '🐾', color: '#059669' }
    };
    const target = rMeta[rType] || rMeta.like;
    const btn = document.getElementById('react-btn-' + postId);
    const iconSpan = document.getElementById('react-icon-' + postId);
    const labelSpan = document.getElementById('react-label-' + postId);
    if (iconSpan) iconSpan.innerText = target.icon;
    if (labelSpan) labelSpan.innerText = target.label;
    if (btn) { btn.style.color = target.color; btn.style.fontWeight = '800'; }

    try {
        const formData = new FormData();
        formData.append('reaction', rType);
        const res = await fetch('/community/like/' + postId, {
            method: 'POST',
            body: formData,
            headers: { 'Accept': 'application/json' }
        });
        const data = await res.json();
        if (data.success) {
            const countElem = document.getElementById('likes-count-' + postId);
            if (countElem) countElem.innerText = data.likes_count;
        }
    } catch (e) {
        console.log(e);
    }
}

async function askVetMindAI(postId) {
    const btn = event.currentTarget;
    btn.disabled = true;
    btn.innerText = '🤖 جاري التحليل...';
    try {
        const res = await fetch('/community/ai-consult/' + postId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            location.reload();
        } else {
            alert('التحليل السريري: ' + (data.error || 'يرجى المحاولة لاحقاً'));
            btn.disabled = false;
            btn.innerText = '🤖 اسأل AI';
        }
    } catch (e) {
        console.log(e);
        btn.disabled = false;
        btn.innerText = '🤖 اسأل AI';
    }
}

async function togglePostBookmark(postId) {
    const btn = document.getElementById('bookmark-btn-' + postId);
    const textSpan = document.getElementById('bookmark-text-' + postId);
    try {
        const res = await fetch('/community/bookmark/' + postId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            if (data.is_bookmarked) {
                if (textSpan) textSpan.innerText = 'محفوظة 🔖';
                if (btn) { btn.style.color = '#d97706'; btn.style.fontWeight = '800'; }
            } else {
                if (textSpan) textSpan.innerText = 'حفظ 🔖';
                if (btn) { btn.style.color = 'var(--fb-text-muted)'; btn.style.fontWeight = '500'; }
            }
        }
    } catch (e) {
        console.log(e);
    }
}

async function submitCommentForm(e, postId) {
    e.preventDefault();
    const input = document.getElementById('comment-input-' + postId);
    const content = input.value.trim();
    if (!content) return;

    input.value = '';
    try {
        const formData = new FormData();
        formData.append('content', content);
        const res = await fetch('/community/comment/' + postId, {
            method: 'POST',
            body: formData,
            headers: { 'Accept': 'application/json' }
        });
        const data = await res.json();
        if (data.success) {
            location.reload();
        }
    } catch (err) {
        console.log(err);
    }
}

function toggleReplyBox(cmId) {
    const box = document.getElementById('reply-box-' + cmId);
    if (box) {
        box.style.display = (box.style.display === 'none' || box.style.display === '') ? 'block' : 'none';
        if (box.style.display === 'block') {
            const inp = document.getElementById('reply-input-' + cmId);
            if (inp) inp.focus();
        }
    }
}

async function submitReply(e, postId, parentId) {
    e.preventDefault();
    const input = document.getElementById('reply-input-' + parentId);
    const content = input.value.trim();
    if (!content) return;

    try {
        const formData = new FormData();
        formData.append('content', content);
        formData.append('parent_id', parentId);
        const res = await fetch('/community/comment/' + postId, {
            method: 'POST',
            body: formData,
            headers: { 'Accept': 'application/json' }
        });
        const data = await res.json();
        if (data.success) {
            location.reload();
        }
    } catch (err) {
        console.log(err);
    }
}

async function markBestDiagnosis(commentId, postId) {
    if (!confirm('هل تريد بالتأكيد اعتماد هذا التشخيص كأفضل رأي سريري؟ سيتم منح الزميل +50 نقطة سمعة.')) return;
    try {
        const res = await fetch('/community/comment/best/' + commentId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            location.reload();
        }
    } catch (e) {
        console.log(e);
    }
}

function focusCommentInput(postId) {
    const inp = document.getElementById('comment-input-' + postId);
    if (inp) {
        inp.focus();
        inp.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function sharePost(postId) {
    const url = window.location.origin + '/community#post-' + postId;
    if (navigator.clipboard) {
        navigator.clipboard.writeText(url);
        alert('🔗 تم نسخ رابط الحالة بنجاح لمشاركتها مع الزملاء!');
    } else {
        prompt('انسخ رابط الحالة:', url);
    }
}

async function toggleColleagueConnect(colleagueId, btn) {
    try {
        const res = await fetch('/community/connect/' + colleagueId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            if (data.connected) {
                btn.innerHTML = '✔️ زميل مضاف';
                btn.style.background = '#059669';
                btn.style.color = '#ffffff';
            } else {
                btn.innerHTML = '➕ إضافة زميل';
                btn.style.background = 'none';
                btn.style.color = '#0f766e';
            }
        }
    } catch (e) {
        console.log(e);
    }
}

async function toggleColleagueFollow(colleagueId, btn) {
    try {
        const res = await fetch('/community/follow/' + colleagueId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            if (data.following) {
                btn.innerHTML = '🔕 إلغاء المتابعة';
            } else {
                btn.innerHTML = '🔔 متابعة';
            }
        }
    } catch (e) {
        console.log(e);
    }
}

async function toggleEventInterest(eventId, btnElem) {
    try {
        const res = await fetch('/community/events/interest/' + eventId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            btnElem.innerText = '⭐ سأحضر (' + data.interested_count + ')';
            btnElem.style.background = '#0f766e';
            btnElem.style.color = '#ffffff';
        }
    } catch (e) {
        console.log(e);
    }
}

async function votePoll(postId, optId) {
    try {
        const formData = new FormData();
        formData.append('opt_id', optId);
        const res = await fetch('/community/poll/vote/' + postId, { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
            location.reload();
        }
    } catch (e) {
        console.log(e);
    }
}

// Global Feed Broadcast & Local Storage Resilience
document.addEventListener('DOMContentLoaded', function() {
    // 1. Detect if post was successfully published and broadcasted
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('posted') === '1') {
        const toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#0f766e;color:#fff;padding:14px 24px;border-radius:12px;font-weight:700;box-shadow:0 10px 25px rgba(0,0,0,0.3);z-index:99999;display:flex;align-items:center;gap:10px;font-size:0.95rem;transition:all 0.4s ease;';
        toast.innerHTML = '<span>🎉</span><span>تم حفظ ونشر حالتك وتعميمها بنجاح على كافة الأطباء المسجلين في المنصة!</span>';
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translate(-50%, 20px)';
            setTimeout(() => toast.remove(), 500);
        }, 4500);

        urlParams.delete('posted');
        const newSearch = urlParams.toString() ? ('?' + urlParams.toString()) : '';
        window.history.replaceState({}, '', window.location.pathname + newSearch + window.location.hash);
    }

    // 2. Intercept composer submission to preserve in localStorage backup
    const compForm = document.getElementById('composer-form');
    if (compForm) {
        compForm.addEventListener('submit', function() {
            try {
                const formData = new FormData(compForm);
                const postObj = {
                    title: formData.get('title') || '',
                    content: formData.get('content') || '',
                    category: formData.get('category') || 'case_study',
                    is_urgent: formData.get('is_urgent') === '1' ? 1 : 0,
                    species: formData.get('species') || '',
                    breed: formData.get('breed') || '',
                    age: formData.get('age') || '',
                    weight: formData.get('weight') || '',
                    gender: formData.get('gender') || '',
                    symptoms: formData.get('symptoms') || '',
                    medications: formData.get('medications') || '',
                    created_at: new Date().toISOString().replace('T', ' ').substring(0, 19)
                };
                let saved = JSON.parse(localStorage.getItem('vetbook_my_posts') || '[]');
                // Filter duplicates by title
                saved = saved.filter(p => p.title !== postObj.title);
                saved.unshift(postObj);
                if (saved.length > 50) saved = saved.slice(0, 50);
                localStorage.setItem('vetbook_my_posts', JSON.stringify(saved));
            } catch (err) {
                console.warn('Local storage post backup error:', err);
            }
        });
    }

    // 3. Client-side resilience check & auto-sync to server
    try {
        const localPosts = JSON.parse(localStorage.getItem('vetbook_my_posts') || '[]');
        if (localPosts.length > 0) {
            fetch('/api/community/sync-posts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ posts: localPosts })
            }).then(r => r.json()).then(res => {
                if (res && res.synced > 0) {
                    console.log('Synchronized ' + res.synced + ' offline posts with VetMind community cloud.');
                }
            }).catch(e => console.warn('Sync error:', e));
        }
    } catch (err) {
        console.warn('Auto sync check error:', err);
    }
});
</script>
"""



def render_facebook_media_grid(img_list: list, video_path: str = None) -> str:
    if video_path:
        if video_path.startswith("http://") or video_path.startswith("https://"):
            return f"""
            <div style="margin: 12px 0; background: #000; border-radius: 12px; overflow: hidden; width: 100%;">
                <iframe src="{video_path}" style="width: 100%; aspect-ratio: 16/9; border: none; display: block;" allowfullscreen></iframe>
            </div>
            """
        else:
            return f"""
            <div style="margin: 12px 0; background: #000; border-radius: 12px; overflow: hidden; width: 100%;">
                <video controls playsinline preload="metadata" style="width: 100%; max-height: 520px; display: block; background: #0f172a;">
                    <source src="/uploads/{video_path}">
                </video>
            </div>
            """

    if not img_list:
        return ""

    cnt = len(img_list)
    if cnt == 1:
        return f"""
        <div class="fb-media-grid grid-1" onclick="openImageModal('/uploads/{img_list[0]}')">
            <img src="/uploads/{img_list[0]}" alt="Case photo" loading="lazy">
        </div>
        """
    elif cnt == 2:
        return f"""
        <div class="fb-media-grid grid-2">
            <img src="/uploads/{img_list[0]}" onclick="openImageModal('/uploads/{img_list[0]}')" loading="lazy">
            <img src="/uploads/{img_list[1]}" onclick="openImageModal('/uploads/{img_list[1]}')" loading="lazy">
        </div>
        """
    elif cnt == 3:
        return f"""
        <div class="fb-media-grid grid-3">
            <div class="media-col-left">
                <img src="/uploads/{img_list[0]}" onclick="openImageModal('/uploads/{img_list[0]}')" loading="lazy">
            </div>
            <div class="media-col-right">
                <img src="/uploads/{img_list[1]}" onclick="openImageModal('/uploads/{img_list[1]}')" loading="lazy">
                <img src="/uploads/{img_list[2]}" onclick="openImageModal('/uploads/{img_list[2]}')" loading="lazy">
            </div>
        </div>
        """
    else:
        extra = cnt - 3
        return f"""
        <div class="fb-media-grid grid-4">
            <div class="media-slot"><img src="/uploads/{img_list[0]}" onclick="openImageModal('/uploads/{img_list[0]}')" loading="lazy"></div>
            <div class="media-slot"><img src="/uploads/{img_list[1]}" onclick="openImageModal('/uploads/{img_list[1]}')" loading="lazy"></div>
            <div class="media-slot"><img src="/uploads/{img_list[2]}" onclick="openImageModal('/uploads/{img_list[2]}')" loading="lazy"></div>
            <div class="media-slot" onclick="openImageModal('/uploads/{img_list[3]}')">
                <img src="/uploads/{img_list[3]}" loading="lazy">
                <div class="media-more-overlay">+{extra} صور إضافية</div>
            </div>
        </div>
        """


@router.get("/community", response_class=HTMLResponse)
async def community_hub(
    request: Request,
    category: str = "all",
    species: str = "all",
    q: str = "",
    sort: str = "smart",
    tab: str = "feed",
    group_id: int = 0
):
    from app import get_current_user, get_user_lang, get_text, get_base_html

    curr_user = get_current_user(request)
    if not curr_user:
        return RedirectResponse("/login?redirect=/community", status_code=303)

    user = curr_user
    lang = get_user_lang(request)

    conn = get_db()
    c = conn.cursor()

    # User Connected Colleagues map
    user_connections = set()
    try:
        c.execute("SELECT colleague_id FROM community_connections WHERE user_id = ?", (user["id"],))
        for r in c.fetchall():
            user_connections.add(r[0])
    except Exception:
        pass

    # User Bookmarks
    user_bookmarks = set()
    try:
        c.execute("SELECT post_id FROM community_bookmarks WHERE user_id = ?", (user["id"],))
        for r in c.fetchall():
            user_bookmarks.add(r[0])
    except Exception:
        pass

    # User Reactions
    user_reactions = {}
    try:
        c.execute("SELECT post_id, reaction_type FROM community_likes WHERE user_id = ?", (user["id"],))
        for r in c.fetchall():
            user_reactions[r["post_id"]] = r["reaction_type"]
    except Exception:
        pass

    # Algorithmic Recommendation Engines
    pymk_colleagues = get_people_you_may_know(conn, user["id"], limit=5)
    trending_topics = get_trending_topics(conn, hours=48, limit=6)
    recommended_groups = get_recommended_groups(conn, user["id"], limit=5)

    # Urgent cases for left sidebar
    c.execute("SELECT id, title, species, author_name, created_at FROM community_posts WHERE is_urgent = 1 ORDER BY id DESC LIMIT 5")
    urgent_cases = [dict(r) for r in c.fetchall()]

    # Stories
    c.execute("SELECT * FROM community_stories ORDER BY id DESC LIMIT 12")
    raw_stories = [dict(r) for r in c.fetchall()]

    stories_cards = ""
    for st in raw_stories:
        stories_cards += f"""
        <div class="fb-story-card" style="background-image: linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.8) 100%), url('/uploads/{st['media_url']}');" onclick="openStoryViewer('{st['author_name']}', '/uploads/{st['media_url']}', '{st.get('caption','')}')">
            <div style="position: absolute; top: 8px; right: 8px; width: 34px; height: 34px; border-radius: 50%; border: 2.5px solid #0f766e; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.85rem; box-shadow: 0 2px 6px rgba(0,0,0,0.25);">
                {st['author_name'][0]}
            </div>
            <div style="position: absolute; bottom: 8px; right: 8px; left: 8px; color: white; font-size: 0.78rem; font-weight: 700; text-shadow: 0 1px 3px rgba(0,0,0,0.85); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                د. {st['author_name']}
            </div>
        </div>
        """

    if not stories_cards:
        demo_stories = [
            ("د. تامر سعد", "bovine_cesarean", "ولادة قيصرية بقرة حلوب", "linear-gradient(135deg, #0f766e, #0d9488)"),
            ("د. أحمد محمود", "equine_colic", "تشخيص مغص حاد بالحصان", "linear-gradient(135deg, #dc2626, #b91c1c)"),
            ("د. سارة عادل", "ultrasound_scan", "فحص بالسونار لحمل قطة", "linear-gradient(135deg, #7c3aed, #6d28d9)"),
            ("د. خالد إبراهيم", "orthopedic_fix", "تثبيت كسر عظم الفخذ", "linear-gradient(135deg, #ea580c, #c2410c)")
        ]
        for s_name, s_id, s_title, s_bg in demo_stories:
            stories_cards += f"""
            <div class="fb-story-card" style="background: {s_bg}; display: flex; flex-direction: column; justify-content: space-between; padding: 10px; color: white;" onclick="alert('قصة سريرية: {s_title}')">
                <div style="width: 32px; height: 32px; border-radius: 50%; border: 2px solid white; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.8rem;">
                    {s_name[0]}
                </div>
                <div>
                    <div style="font-size: 0.72rem; opacity: 0.9;">{s_name}</div>
                    <div style="font-size: 0.78rem; font-weight: 800; line-height: 1.4; margin-top: 2px;">{s_title}</div>
                </div>
            </div>
            """

    # Ensure all persistent posts are synced into SQLite
    sync_posts_from_backup_sync(conn)

    # Fetch and Score Posts
    sql = "SELECT * FROM community_posts WHERE 1=1"
    params = []
    if tab == "my_posts" or category == "my_posts":
        sql += " AND user_id = ?"
        params.append(user["id"])
    if group_id:
        sql += " AND group_id = ?"
        params.append(group_id)
    if category != "all" and category != "bookmarks" and category != "my_posts":
        if category == "urgent":
            sql += " AND is_urgent = 1"
        else:
            sql += " AND category = ?"
            params.append(category)
    if species != "all":
        sql += " AND species = ?"
        params.append(species)
    if q.strip():
        search_kw = f"%{q.strip()}%"
        sql += " AND (title LIKE ? OR content LIKE ? OR symptoms LIKE ? OR species LIKE ?)"
        params.extend([search_kw, search_kw, search_kw, search_kw])

    sql += " ORDER BY id DESC LIMIT 100"
    c.execute(sql, params)
    raw_posts = [dict(r) for r in c.fetchall()]

    if category == "bookmarks" or tab == "saved":
        raw_posts = [p for p in raw_posts if p["id"] in user_bookmarks]

    # Pre-fetch latest comment timestamps for comment-bump ranking
    post_latest_comments = {}
    try:
        c.execute("SELECT post_id, MAX(created_at) FROM community_comments GROUP BY post_id")
        for r in c.fetchall():
            post_latest_comments[r[0]] = r[1]
    except Exception:
        pass

    # Score posts with EdgeRank
    for p in raw_posts:
        p["is_author_connected"] = p["user_id"] in user_connections
        p["bookmarks_count"] = 1 if p["id"] in user_bookmarks else 0
        latest_c_time = post_latest_comments.get(p["id"])
        p["edgerank_score"] = calculate_edgerank_score(p, user, latest_c_time)

    # Sort based on selector (Guarantees doctor's newly created posts are prioritized at the top)
    if sort == "smart":
        raw_posts.sort(key=lambda x: (
            x.get("is_pinned", 0),
            1 if x.get("user_id") == user["id"] else 0,
            x.get("edgerank_score", 0),
            x["id"]
        ), reverse=True)
    elif sort == "recent":
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x["id"]), reverse=True)
    elif sort == "urgent":
        raw_posts.sort(key=lambda x: (x.get("is_urgent", 0), x["id"]), reverse=True)
    elif sort == "trending":
        raw_posts.sort(key=lambda x: (x.get("virality_score", 0), x.get("likes_count", 0)), reverse=True)

    # Fetch comments for posts
    post_ids = [p["id"] for p in raw_posts]
    comments_by_post = {}
    if post_ids:
        placeholders = ",".join("?" for _ in post_ids)
        c.execute(f"SELECT * FROM community_comments WHERE post_id IN ({placeholders}) ORDER BY is_best_answer DESC, id ASC", post_ids)
        for cm in c.fetchall():
            comments_by_post.setdefault(cm["post_id"], []).append(dict(cm))

    # Render Post Cards
    posts_cards_html = ""
    for p in raw_posts:
        post_id = p["id"]
        is_urgent = p.get("is_urgent", 0)
        post_reaction = user_reactions.get(post_id)
        is_bookmarked = post_id in user_bookmarks

        react_info = REACTIONS.get(post_reaction, {"label": "إعجاب", "icon": "👍", "color": "var(--fb-text-muted)"})
        react_active_style = f"color: {react_info['color']}; font-weight: 800;" if post_reaction else "color: var(--fb-text-muted);"
        bookmark_style = "color: #d97706; font-weight: 800;" if is_bookmarked else "color: var(--fb-text-muted);"
        bookmark_label = "محفوظة 🔖" if is_bookmarked else "حفظ 🔖"

        # Urgent Banner
        urgent_banner = ""
        card_class = "fb-card"
        if is_urgent:
            card_class += " urgent-post-card"
            urgent_banner = """
            <div class="urgent-banner-row">
                <div class="urgent-banner-left">
                    <span style="font-size: 1.15rem; animation: pulse 1s infinite;">🚨</span>
                    <span>حالة سريرية عاجلة بحاجة لاستشارة فورية (URGENT CASE)</span>
                </div>
                <span class="urgent-badge">أولوية قصوى</span>
            </div>
            """

        # Demographics
        demographics_html = ""
        if p.get("species") or p.get("symptoms") or p.get("breed"):
            spec_name = SPECIES_MAP.get(p.get("species"), p.get("species") or "فصيلة غير محددة")
            demographics_html = f"""
            <div class="case-demographics-grid">
                <div>🐾 <strong>الفصيلة:</strong> {spec_name}</div>
                {f"<div>🧬 <strong>السلالة:</strong> {p['breed']}</div>" if p.get('breed') else ""}
                {f"<div>⚖️ <strong>الوزن/العمر:</strong> {p.get('weight','')} كجم • {p.get('age','')}</div>" if (p.get('weight') or p.get('age')) else ""}
                {f"<div>⚧ <strong>الجنس:</strong> {p['gender']}</div>" if p.get('gender') else ""}
                {f"<div style='grid-column: 1 / -1;'>🌡️ <strong>الأعراض الحيوية:</strong> {p['symptoms']}</div>" if p.get('symptoms') else ""}
                {f"<div style='grid-column: 1 / -1; color: #7c2d12;'>💊 <strong>الأدوية المسبقة:</strong> {p['medications']}</div>" if p.get('medications') else ""}
            </div>
            """

        # Media Grid
        media_images = []
        if p.get("image_path"):
            media_images.append(p["image_path"])
        if p.get("extra_images"):
            for ex in p["extra_images"].split(","):
                if ex.strip():
                    media_images.append(ex.strip())
        media_html = render_facebook_media_grid(media_images, p.get("video_path"))

        # Poll Widget
        poll_html = ""
        if p.get("poll_data"):
            try:
                p_data = json.loads(p["poll_data"])
                q_text = p_data.get("question", "")
                options = p_data.get("options", [])
                total_votes = sum(opt.get("votes", 0) for opt in options)
                opts_html = ""
                for opt in options:
                    pct = int((opt.get("votes", 0) / max(1, total_votes)) * 100)
                    opts_html += f"""
                    <div class="poll-option-bar" onclick="votePoll({post_id}, {opt['id']})" style="background: var(--fb-bg); border: 1px solid var(--fb-border); border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; cursor: pointer; position: relative; overflow: hidden;">
                        <div class="poll-progress-fill" style="position: absolute; top: 0; right: 0; bottom: 0; width: {pct}%; background: rgba(15,118,110,0.15);"></div>
                        <div style="position: relative; z-index: 2; display: flex; justify-content: space-between; font-weight: 700; font-size: 0.85rem;">
                            <span>{opt['text']}</span>
                            <span>{pct}% ({opt.get('votes', 0)})</span>
                        </div>
                    </div>
                    """
                poll_html = f"""
                <div style="background: var(--fb-card); border: 1px solid var(--fb-border); border-radius: 12px; padding: 14px; margin: 12px 0;">
                    <div style="font-weight: 800; font-size: 0.95rem; color: #0f766e; margin-bottom: 10px;">📊 استطلاع رأي طبي: {q_text}</div>
                    {opts_html}
                    <div style="font-size: 0.74rem; color: var(--fb-text-muted); margin-top: 6px;">إجمالي الأصوات: {total_votes} طبيباً</div>
                </div>
                """
            except Exception:
                pass

        # AI Analysis Card
        ai_card_html = ""
        if p.get("ai_analysis"):
            ai_card_html = f"""
            <div class="ai-consult-card" style="background: linear-gradient(135deg, #f0fdf4 0%, #ecfeff 100%); border: 1.5px solid #6ee7b7; border-radius: 14px; padding: 14px 18px; margin: 12px 0;" id="ai-box-{post_id}">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px; font-weight: 800; color: #0f766e;">
                        <span style="font-size: 1.3rem;">🤖</span>
                        <span>التحليل السريري الذكي (VetMind AI Differential Diagnosis):</span>
                    </div>
                    <span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 700;">معتمد ذكياً</span>
                </div>
                <div style="font-size: 0.9rem; line-height: 1.75; color: var(--fb-text); white-space: pre-line;">
                    {p['ai_analysis']}
                </div>
            </div>
            """

        # Comments
        comments_raw = comments_by_post.get(post_id, [])
        top_comments = [cm for cm in comments_raw if not cm.get("parent_comment_id") or cm.get("parent_comment_id") == 0]
        replies_map = {}
        for cm in comments_raw:
            pid = cm.get("parent_comment_id")
            if pid and pid > 0:
                replies_map.setdefault(pid, []).append(cm)

        comments_html = ""
        for cm in top_comments:
            cm_id = cm["id"]
            is_best = cm.get("is_best_answer", 0)
            is_ai = cm.get("is_ai_comment", 0)
            bubble_class = "fb-comment-bubble" + (" best-answer-bubble" if is_best else "")

            best_badge = '<span style="background: #10b981; color: white; padding: 1px 6px; border-radius: 8px; font-size: 0.7rem; font-weight: 800;">🏆 أفضل تشخيص معتمد ✅</span>' if is_best else ""
            ai_badge = '<span style="background: #10b981; color: white; padding: 1px 6px; border-radius: 8px; font-size: 0.68rem; font-weight: 800;">🤖 AI مساعد</span>' if is_ai else ""
            author_badge = '<span style="background: #e0e7ff; color: #3730a3; padding: 1px 6px; border-radius: 8px; font-size: 0.7rem; font-weight: 700;">👑 صاحب الحالة</span>' if cm.get("user_id") == p["user_id"] else ""

            mark_best_btn = ""
            if user and user["id"] == p["user_id"] and not is_best and cm.get("user_id") != user["id"]:
                mark_best_btn = f"""
                <button type="button" onclick="markBestDiagnosis({cm_id}, {post_id})" style="background: none; border: none; color: #059669; font-weight: 800; cursor: pointer; font-size: 0.74rem;">
                    ✅ اعتماد كأفضل تشخيص (+50 سمعة)
                </button>
                """

            replies_html = ""
            for rep in replies_map.get(cm_id, []):
                rep_badge = '<span style="background: #e0e7ff; color: #3730a3; padding: 1px 5px; border-radius: 8px; font-size: 0.68rem; font-weight: 700;">👑 صاحب الحالة</span>' if rep.get("user_id") == p["user_id"] else ""
                replies_html += f"""
                <div style="margin-top: 8px; display: flex; gap: 8px; align-items: flex-start;">
                    <div style="width: 28px; height: 28px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; flex-shrink: 0;">
                        {rep['author_name'][0]}
                    </div>
                    <div style="flex: 1; min-width: 0;">
                        <div class="fb-comment-bubble">
                            <div style="font-weight: 700; font-size: 0.82rem; color: #0f766e;">د. {rep['author_name']} {rep_badge}</div>
                            <div style="margin-top: 3px; line-height: 1.6;">{rep['content']}</div>
                        </div>
                        <div style="font-size: 0.68rem; color: var(--fb-text-muted); margin-top: 2px; margin-right: 8px;">
                            {rep['created_at']}
                        </div>
                    </div>
                </div>
                """

            comments_html += f"""
            <div style="margin-bottom: 12px; display: flex; gap: 10px; align-items: flex-start;" id="comment-{cm_id}">
                <div style="width: 34px; height: 34px; border-radius: 50%; background: #0284c7; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 700; flex-shrink: 0;">
                    {cm['author_name'][0]}
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div class="{bubble_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px; margin-bottom: 4px;">
                            <div>
                                <strong style="font-size: 0.88rem; color: #0f766e;">د. {cm['author_name']}</strong> {author_badge} {ai_badge}
                                <span style="font-size: 0.72rem; color: var(--fb-text-muted); margin-right: 4px;">({cm.get('author_specialty') or 'طبيب بيطري'})</span>
                            </div>
                            {best_badge}
                        </div>
                        <div style="line-height: 1.6;">{cm['content']}</div>
                    </div>
                    <div style="display: flex; gap: 12px; font-size: 0.74rem; color: var(--fb-text-muted); margin-top: 3px; margin-right: 10px; align-items: center; flex-wrap: wrap;">
                        <button type="button" onclick="toggleReplyBox({cm_id})" style="background: none; border: none; font-weight: 700; color: #0f766e; cursor: pointer; padding: 0;">رد ↩️</button>
                        {mark_best_btn}
                        <span>{cm['created_at']}</span>
                    </div>

                    <div style="margin-right: 16px;">
                        {replies_html}
                    </div>

                    <div id="reply-box-{cm_id}" style="display: none; margin-top: 8px; margin-right: 16px;">
                        <form onsubmit="submitReply(event, {post_id}, {cm_id})" style="display: flex; gap: 8px; align-items: center;">
                            <input type="text" id="reply-input-{cm_id}" required placeholder="اكتب ردك على د. {cm['author_name']}..." style="flex: 1; padding: 8px 14px; border: 1px solid var(--fb-border); border-radius: 20px; font-size: 0.82rem; background: var(--fb-bg); color: var(--fb-text);">
                            <button type="submit" class="btn btn-primary" style="padding: 6px 14px; font-size: 0.78rem; border-radius: 20px;">رد ↩️</button>
                        </form>
                    </div>
                </div>
            </div>
            """

        post_badges = ""
        if p.get("is_pinned"):
            post_badges += '<span style="background: #fef08a; color: #854d0e; padding: 2px 7px; border-radius: 10px; font-size: 0.7rem; font-weight: 800;">📌 مثبت</span>'
        if p.get("is_boosted"):
            post_badges += '<span style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; padding: 2px 7px; border-radius: 10px; font-size: 0.7rem; font-weight: 800;">🚀 مروج</span>'
        if is_urgent:
            post_badges += '<span style="background: #fee2e2; color: #dc2626; padding: 2px 7px; border-radius: 10px; font-size: 0.7rem; font-weight: 800;">🚨 طارئ</span>'
        post_badges += '<span style="background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 800;">📢 منشور عام موجه لكافة الأطباء</span>'
        if user and p.get("user_id") == user["id"]:
            post_badges += '<span style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 800;">👑 منشوري</span>'

        cat_badge = CATEGORIES.get(p["category"], {"name": p["category"], "color": "#0f766e", "icon": "📄"})

        delete_btn = ""
        if user and (user.get("is_admin") or user["id"] == p["user_id"]):
            delete_btn = f"""
            <form action="/community/post/delete/{post_id}" method="POST" style="margin: 0;" onsubmit="return confirm('هل تريد بالتأكيد حذف هذا المنشور السريري؟');">
                <button type="submit" style="background: none; border: none; color: #dc2626; cursor: pointer; font-size: 0.85rem; padding: 2px;" title="حذف المنشور">🗑️</button>
            </form>
            """

        posts_cards_html += f"""
        <div class="{card_class}" id="post-{post_id}" style="margin-bottom: 16px;">
            {urgent_banner}
            <div class="fb-card-content" style="padding: 16px;">
                <!-- Post Header -->
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <a href="/community/profile/{p['user_id']}" style="text-decoration: none;">
                            <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.15rem; box-shadow: 0 2px 6px rgba(15,118,110,0.25);">
                                {p['author_name'][0] if p['author_name'] else 'V'}
                            </div>
                        </a>
                        <div>
                            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                                <a href="/community/profile/{p['user_id']}" style="font-weight: 700; font-size: 0.98rem; color: var(--fb-text); text-decoration: none;">د. {p['author_name']}</a>
                                <span title="طبيب بيطري موثق ومعتمد">🩺</span>
                                {post_badges}
                            </div>
                            <div style="font-size: 0.74rem; color: var(--fb-text-muted); display: flex; align-items: center; gap: 4px; flex-wrap: wrap; margin-top: 2px;">
                                <span>{p.get('author_specialty') or 'طب وجراحة الحيوان'}</span> •
                                <span>{p.get('author_country') or 'مصر'}</span> •
                                <span>{p['created_at']}</span> •
                                <span>🌐</span>
                            </div>
                        </div>
                    </div>
                    
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="background: {cat_badge['color']}15; color: {cat_badge['color']}; padding: 3px 10px; border-radius: 12px; font-size: 0.74rem; font-weight: 700;">
                            {cat_badge['icon']} {cat_badge['name']}
                        </span>
                        {delete_btn}
                    </div>
                </div>

                <!-- Post Title & Content -->
                <h3 style="margin: 0 0 8px 0; font-size: 1.15rem; color: var(--fb-text); line-height: 1.45; word-break: normal; overflow-wrap: break-word;">{p['title']}</h3>
                <div style="font-size: 0.95rem; color: var(--fb-text); line-height: 1.75; word-break: normal; overflow-wrap: break-word; white-space: pre-line;">{p['content']}</div>

                {demographics_html}
                {media_html}
                {poll_html}
                {ai_card_html}

                <!-- Post Reactions Summary -->
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 4px; border-bottom: 1px solid var(--fb-border); font-size: 0.8rem; color: var(--fb-text-muted); margin-top: 8px; flex-wrap: wrap; gap: 6px;">
                    <div style="display: flex; align-items: center; gap: 5px;" id="likes-count-box-{post_id}">
                        <span>👍❤️💡</span>
                        <strong style="margin-right: 4px;" id="likes-count-{post_id}">{p['likes_count']}</strong>
                        <span>تفاعلاً</span>
                    </div>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <span id="comments-count-{post_id}">{p['comments_count']} تعليقاً</span> •
                        <span>{p.get('shares_count', 0)} مشاركة</span> •
                        <span>{p.get('views_count', 1)} مشاهدة</span>
                    </div>
                </div>

                <!-- Facebook Action Bar -->
                <div class="fb-action-bar">
                    <!-- Reactions Trigger & Popup -->
                    <div class="reaction-wrapper" onmouseenter="showReactionsPopup({post_id})" onmouseleave="hideReactionsPopup({post_id})">
                        <div class="fb-reactions-popup" id="reactions-popup-{post_id}">
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'like')" title="إعجاب">👍</button>
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'vital')" title="حالة مهمة">❤️</button>
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'insight')" title="تشخيص دقيق">💡</button>
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'followup')" title="بحاجة لمتابعة">🤔</button>
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'healing')" title="شفاء ودعم">🐾</button>
                        </div>
                        <button type="button" onclick="setPostReaction({post_id}, '{post_reaction or 'like'}')" id="react-btn-{post_id}" class="btn fb-action-btn" style="background: none; border: none; {react_active_style}">
                            <span id="react-icon-{post_id}">{react_info['icon']}</span>
                            <span id="react-label-{post_id}">{react_info['label']}</span>
                        </button>
                    </div>

                    <!-- Comment Button -->
                    <button type="button" onclick="focusCommentInput({post_id})" class="btn fb-action-btn" style="background: none; border: none; color: var(--fb-text-muted);">
                        <span>💬</span>
                        <span>تعليق</span>
                    </button>

                    <!-- Ask VetMind AI -->
                    <button type="button" onclick="askVetMindAI({post_id})" class="btn fb-action-btn" style="background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1px solid #10b981; color: #065f46; font-weight: 800; border-radius: 20px;">
                        <span>🤖</span>
                        <span>اسأل AI</span>
                    </button>

                    <!-- Share -->
                    <button type="button" onclick="sharePost({post_id})" class="btn fb-action-btn" style="background: none; border: none; color: var(--fb-text-muted);">
                        <span>↪️</span>
                        <span>مشاركة</span>
                    </button>

                    <!-- Bookmark -->
                    <button type="button" onclick="togglePostBookmark({post_id})" id="bookmark-btn-{post_id}" class="btn fb-action-btn" style="background: none; border: none; {bookmark_style}">
                        <span id="bookmark-icon-{post_id}">🔖</span>
                        <span id="bookmark-text-{post_id}">{bookmark_label}</span>
                    </button>
                </div>

                <!-- Comments Container -->
                <div style="margin-top: 14px;" id="comments-section-{post_id}">
                    <form onsubmit="submitCommentForm(event, {post_id})" style="display: flex; gap: 10px; align-items: center; margin-bottom: 14px;">
                        <div style="width: 34px; height: 34px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.9rem; flex-shrink: 0;">
                            {user.get('name', 'طبيب')[0]}
                        </div>
                        <div style="flex: 1; display: flex; align-items: center; background: var(--fb-bg); border: 1px solid var(--fb-border); border-radius: 25px; padding: 4px 14px;">
                            <input type="text" id="comment-input-{post_id}" required placeholder="اكتب تشخيصك أو رأيك السريري في هذه الحالة..." style="flex: 1; border: none; background: transparent; padding: 8px 0; font-size: 0.88rem; color: var(--fb-text); outline: none;">
                            <button type="submit" style="background: #0f766e; border: none; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 0.85rem;">
                                ⬆️
                            </button>
                        </div>
                    </form>

                    <div id="comments-list-{post_id}">
                        {comments_html if comments_html else "<div style='color: var(--fb-text-muted); font-size: 0.82rem; text-align: center; padding: 8px;' id='no-comments-" + str(post_id) + "'>كن أول من يشارك بتشخيص أو رأي سريري في هذه الحالة 🩺</div>"}
                    </div>
                </div>
            </div>
        </div>
        """

    conn.close()

    # Build Right Column
    user_avatar = user.get('name', 'طبيب')[0]
    right_col_html = f"""
    <div class="fb-right-col fb-sticky-sidebar">
        <!-- Logged-in Doctor Quick Card -->
        <div class="fb-card" style="padding: 16px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.3rem; box-shadow: 0 4px 10px rgba(15,118,110,0.25);">
                    {user_avatar}
                </div>
                <div style="overflow: hidden;">
                    <div style="font-weight: 800; font-size: 0.98rem; color: var(--fb-text); white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">د. {user.get('name', 'طبيب')}</div>
                    <div style="font-size: 0.75rem; color: #059669; font-weight: 700;">طبيب بيطري معتمد 🩺</div>
                    <div style="font-size: 0.72rem; color: var(--fb-text-muted);">{user.get('clinic_name') or 'عيادة بيطرية'}</div>
                </div>
            </div>
            <a href="/community/profile/{user['id']}" class="btn btn-outline" style="width: 100%; justify-content: center; font-size: 0.82rem; border-radius: 20px; font-weight: 700; text-decoration: none;">👤 عرض ملفي الشخصي والسمعة</a>
        </div>

        <!-- Quick Sub-Navigation -->
        <div class="fb-card" style="padding: 12px;">
            <div style="font-weight: 800; font-size: 0.86rem; color: #0f766e; margin-bottom: 8px; padding-right: 6px;">🧭 تصفح سريع:</div>
            <a href="/community" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text); font-weight: 700; font-size: 0.88rem;"><span>📰</span> <span>آخر الأخبار والحالات</span></a>
            <a href="/community?sort=smart" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: #0f766e; font-weight: 800; font-size: 0.88rem;"><span>✨</span> <span>خوارزمية الأكثر صلة</span></a>
            <a href="/community?category=urgent" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: #dc2626; font-weight: 800; font-size: 0.88rem;"><span>🚨</span> <span>الحالات الطارئة الحرجة</span></a>
            <a href="/community?category=videos" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text); font-weight: 700; font-size: 0.88rem;"><span>🎥</span> <span>فيديوهات الجراحة</span></a>
            <a href="/community?category=bookmarks" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text); font-weight: 700; font-size: 0.88rem;"><span>🔖</span> <span>الحالات المحفوظة للرجوع إليها</span></a>
        </div>

        <!-- Groups Widget -->
        <div class="fb-card" style="padding: 14px;">
            <div style="font-weight: 800; font-size: 0.88rem; color: #0f766e; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
                <span>👥</span> <span>المجموعات التخصصية</span>
            </div>
            {"".join([f'<a href="/community?group_id={g["id"]}" style="display: flex; align-items: center; justify-content: space-between; padding: 7px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text);"><div style="display: flex; align-items: center; gap: 8px; overflow: hidden;"><span style="font-size: 1.2rem;">{g.get("icon", "🩺")}</span><div style="overflow: hidden;"><div style="font-weight: 700; font-size: 0.82rem; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">{g["name"]}</div><div style="font-size: 0.70rem; color: var(--fb-text-muted);">{g.get("members_count", 1)} طبيباً</div></div></div><span style="font-size: 0.72rem; color: #0f766e; font-weight: 800;">تصفح ⬅️</span></a>' for g in recommended_groups])}
        </div>
    </div>
    """

    # Build Left Column (Urgent Cases Radar + Trending Topics + People You May Know)
    urgent_items_html = "".join([f'<a href="/community#post-{uc["id"]}" style="display: block; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text); background: var(--fb-bg); border-right: 3px solid #dc2626; margin-bottom: 6px;"><div style="font-weight: 800; font-size: 0.82rem; color: #991b1b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">🚨 {uc["title"]}</div><div style="font-size: 0.7rem; color: var(--fb-text-muted); display: flex; justify-content: space-between; margin-top: 2px;"><span>د. {uc["author_name"]}</span><span>{uc.get("created_at","")[:10]}</span></div></a>' for uc in urgent_cases])

    trending_items_html = "".join([f'<a href="/community?q={t_item["query"]}" class="trending-pill"><span>🔥</span><span>{t_item["tag"]}</span><span style="font-size: 0.7rem; opacity: 0.7;">({t_item["posts_approx"]})</span></a>' for t_item in trending_topics])

    pymk_items_html = ""
    for cand in pymk_colleagues:
        is_conn = cand["id"] in user_connections
        btn_text = "✔️ زميل" if is_conn else "➕ إضافة زميل"
        btn_style = "background: #059669; color: white;" if is_conn else "background: none; color: #0f766e; border: 1px solid #0f766e;"
        pymk_items_html += f"""
        <div class="pymk-card">
            <div style="display: flex; align-items: center; gap: 8px; min-width: 0;">
                <div style="width: 36px; height: 36px; border-radius: 50%; background: #0284c7; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.85rem; flex-shrink: 0;">
                    {cand['name'][0]}
                </div>
                <div style="min-width: 0; overflow: hidden;">
                    <a href="/community/profile/{cand['id']}" style="font-weight: 700; font-size: 0.82rem; color: var(--fb-text); text-decoration: none; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">د. {cand['name']}</a>
                    <div style="font-size: 0.68rem; color: #059669; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{cand.get('pymk_reason', '')}</div>
                </div>
            </div>
            <button type="button" onclick="toggleColleagueConnect({cand['id']}, this)" style="padding: 4px 10px; border-radius: 14px; font-size: 0.72rem; font-weight: 700; cursor: pointer; white-space: nowrap; {btn_style}">
                {btn_text}
            </button>
        </div>
        """

    left_col_html = f"""
    <div class="fb-left-col fb-sticky-sidebar">
        <!-- Urgent Cases Radar -->
        <div class="fb-card" style="padding: 14px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <div style="font-weight: 800; font-size: 0.88rem; color: #dc2626; display: flex; align-items: center; gap: 6px;">
                    <span>🚨</span> <span>رادار الحالات الطارئة</span>
                </div>
                <span style="background: #fee2e2; color: #991b1b; padding: 1px 6px; border-radius: 8px; font-size: 0.68rem; font-weight: 800;">مباشر</span>
            </div>
            {urgent_items_html if urgent_items_html else "<div style='color: var(--fb-text-muted); font-size: 0.78rem;'>لا توجد حالات طارئة غير محلولة حالياً.</div>"}
        </div>

        <!-- Trending in VetBook -->
        <div class="fb-card" style="padding: 14px;">
            <div style="font-weight: 800; font-size: 0.88rem; color: #ea580c; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
                <span>🔥</span> <span>الرائج الآن في VetBook</span>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                {trending_items_html}
            </div>
        </div>

        <!-- People You May Know (PYMK) -->
        <div class="fb-card" style="padding: 14px;">
            <div style="font-weight: 800; font-size: 0.88rem; color: var(--fb-text); margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
                <span>🤝</span> <span>أطباء وزملاء قد تعرفهم</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                {pymk_items_html if pymk_items_html else "<div style='color: var(--fb-text-muted); font-size: 0.78rem;'>تم الاتصال بكافة الأطباء المقترحين.</div>"}
            </div>
        </div>
    </div>
    """

    # Sub-Navigation Strip (Facebook tabs)
    subnav_strip = f"""
    <div class="vetbook-subnav-strip">
        <a href="/community" class="vetbook-nav-pill {'active' if tab == 'feed' else ''}"><span>📰</span> <span>آخر الأخبار</span></a>
        <a href="/community?tab=my_posts" class="vetbook-nav-pill {'active' if tab == 'my_posts' else ''}"><span>📢</span> <span>منشوراتي وحالاتي</span></a>
        <a href="/community?tab=groups" class="vetbook-nav-pill {'active' if tab == 'groups' else ''}"><span>👥</span> <span>المجموعات التخصصية</span></a>
        <a href="/community?tab=network" class="vetbook-nav-pill {'active' if tab == 'network' else ''}"><span>🤝</span> <span>شبكة الزملاء (PYMK)</span></a>
        <a href="/community?tab=events" class="vetbook-nav-pill {'active' if tab == 'events' else ''}"><span>🎓</span> <span>الفعاليات والمؤتمرات</span></a>
        <a href="/community?category=bookmarks" class="vetbook-nav-pill {'active' if (category == 'bookmarks' or tab == 'saved') else ''}"><span>🔖</span> <span>الحالات المحفوظة</span></a>
        <a href="/community/profile/{user['id']}" class="vetbook-nav-pill"><span>👤</span> <span>ملفي الشخصي</span></a>
    </div>
    """

    # Species Filter Strip
    species_strip = "".join([f'<a href="/community?species={sp_k}&category={category}&sort={sort}" style="padding: 5px 14px; border-radius: 20px; font-size: 0.80rem; text-decoration: none; font-weight: 700; background: {"#0f766e" if species == sp_k else "var(--fb-card)"}; color: {"white" if species == sp_k else "var(--fb-text)"}; border: 1px solid var(--fb-border); white-space: nowrap;">{sp_name}</a>' for sp_k, sp_name in SPECIES_MAP.items()])

    # Feed Sort Pills
    sort_pills = f"""
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 14px;">
        <div class="sort-pills-scroll">
            <a href="/community?sort=smart&category={category}&species={species}" style="padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; text-decoration: none; font-weight: 800; background: {'#0f766e' if sort == 'smart' else 'var(--fb-card)'}; color: {'white' if sort == 'smart' else 'var(--fb-text)'}; border: 1px solid var(--fb-border);">✨ الأكثر صلة لك (الخوارزمية الذكية)</a>
            <a href="/community?sort=recent&category={category}&species={species}" style="padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; text-decoration: none; font-weight: 700; background: {'#0f766e' if sort == 'recent' else 'var(--fb-card)'}; color: {'white' if sort == 'recent' else 'var(--fb-text)'}; border: 1px solid var(--fb-border);">🕒 الأحدث نشراً</a>
            <a href="/community?category=urgent&species={species}" style="padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; text-decoration: none; font-weight: 700; background: {'#dc2626' if category == 'urgent' else 'var(--fb-card)'}; color: {'white' if category == 'urgent' else '#dc2626'}; border: 1px solid {'#dc2626' if category == 'urgent' else 'var(--fb-border)'};">🚨 الحالات الطارئة</a>
            <a href="/community?sort=trending&category={category}&species={species}" style="padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; text-decoration: none; font-weight: 700; background: {'#ea580c' if sort == 'trending' else 'var(--fb-card)'}; color: {'white' if sort == 'trending' else 'var(--fb-text)'}; border: 1px solid var(--fb-border);">🔥 الأكثر رواجاً</a>
        </div>
        <div style="font-size: 0.78rem; color: var(--fb-text-muted); font-weight: 700;">
            إجمالي: {len(raw_posts)} حالة
        </div>
    </div>
    """

    body = f"""
    {COMMUNITY_CSS}
    <div class="fb-app-wrapper">
        {subnav_strip}

        <div class="fb-container">
            <!-- RIGHT SIDEBAR (RTL: Right side) -->
            {right_col_html}

            <!-- CENTER MAIN FEED -->
            <div class="fb-main-feed" style="min-width: 0;">
                <!-- Stories Bar -->
                <div class="fb-card" style="padding: 12px; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                        <div style="font-weight: 800; font-size: 0.88rem; color: #0f766e; display: flex; align-items: center; gap: 6px;">
                            <span>📸</span> <span>القصص اليومية وحالات العيادة السريعة</span>
                        </div>
                    </div>
                    <div class="fb-stories-strip">
                        <div class="fb-story-card fb-story-create-card" onclick="openStoryModal()">
                            <div style="width: 40px; height: 40px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; box-shadow: 0 4px 10px rgba(15,118,110,0.3);">
                                ➕
                            </div>
                            <span style="font-size: 0.78rem; font-weight: 800; color: #0f766e; margin-top: 8px;">إضافة قصة عيادتك</span>
                        </div>
                        {stories_cards}
                    </div>
                </div>

                <!-- Rich Post Composer Box -->
                <div class="fb-card fb-composer-box">
                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                        <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.2rem; flex-shrink: 0;">
                            {user_avatar}
                        </div>
                        <button type="button" onclick="openComposerModal('case')" class="fb-composer-input">
                            بم تفكر يا دكتور {user.get('name','')}؟ شارك حالة سريرية، استشارة، أو تجربة دوائية...
                        </button>
                    </div>
                    <div style="border-top: 1px solid var(--fb-border); padding-top: 10px; display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 6px;">
                        <button type="button" onclick="openComposerModal('case')" class="btn" style="background: none; border: none; color: #0f766e; font-weight: 800; font-size: 0.86rem; display: inline-flex; align-items: center; gap: 6px;">
                            <span style="font-size: 1.25rem;">🩺</span>
                            <span>نشر حالة سريرية</span>
                        </button>
                        <button type="button" onclick="openComposerModal('urgent')" class="btn" style="background: none; border: none; color: #dc2626; font-weight: 800; font-size: 0.86rem; display: inline-flex; align-items: center; gap: 6px;">
                            <span style="font-size: 1.25rem;">🚨</span>
                            <span>حالة طارئة حرجة</span>
                        </button>
                        <button type="button" onclick="openComposerModal('video')" class="btn" style="background: none; border: none; color: #0284c7; font-weight: 800; font-size: 0.86rem; display: inline-flex; align-items: center; gap: 6px;">
                            <span style="font-size: 1.25rem;">🎥</span>
                            <span>فيديو جراحي</span>
                        </button>
                        <button type="button" onclick="openComposerModal('general')" class="btn" style="background: none; border: none; color: #7c3aed; font-weight: 800; font-size: 0.86rem; display: inline-flex; align-items: center; gap: 6px;">
                            <span style="font-size: 1.25rem;">📝</span>
                            <span>منشور عام</span>
                        </button>
                    </div>
                </div>

                <!-- Species Filter Strip -->
                <div class="species-strip-container">
                    {species_strip}
                </div>

                <!-- Feed Sort Control -->
                {sort_pills}

                <!-- Posts Stream -->
                <div id="posts-stream">
                    {posts_cards_html if posts_cards_html else "<div class='fb-card' style='padding: 40px 20px; text-align: center;'><div style='font-size: 3rem;'>🩺</div><h3>لا توجد منشورات مطابقة لهذا الفلتر</h3><p style='color: var(--fb-text-muted);'>كن أول من يشارك حالة سريرية أو استشارة مع الزملاء</p></div>"}
                </div>
            </div>

            <!-- LEFT SIDEBAR (Desktop: Left side) -->
            {left_col_html}
        </div>

        <!-- Rich Post Composer Modal -->
        <div id="new-post-modal" class="modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 1100; align-items: center; justify-content: center; padding: 14px;">
            <div style="background: var(--fb-card); border-radius: 18px; max-width: 640px; width: 100%; max-height: 90vh; overflow-y: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.3); border: 1px solid var(--fb-border); padding: 22px; position: relative;">
                <button type="button" onclick="closeComposerModal()" style="position: absolute; top: 16px; left: 16px; background: var(--fb-bg); border: none; border-radius: 50%; width: 32px; height: 32px; font-size: 1.1rem; cursor: pointer; color: var(--fb-text);">✕</button>
                <div style="text-align: center; margin-bottom: 16px; border-bottom: 1px solid var(--fb-border); padding-bottom: 12px;">
                    <h2 style="margin: 0; font-size: 1.3rem; color: #0f766e;" id="modal-title">🩺 إنشاء منشور / استشارة سريرية</h2>
                </div>

                <form action="/community/post" method="POST" enctype="multipart/form-data" id="composer-form">
                    <input type="hidden" name="is_urgent" id="comp-is-urgent" value="0">
                    <input type="hidden" name="category" id="comp-category" value="case_study">

                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.88rem;">📌 عنوان الحالة أو الاستشارة:</label>
                        <input type="text" name="title" required placeholder="مثال: اشتباه التهاب بريتون معدي في قط شيرازي عمره 8 شهور" style="width: 100%; padding: 10px 14px; border: 1px solid var(--fb-border); border-radius: 10px; font-size: 0.95rem; background: var(--fb-bg); color: var(--fb-text);">
                    </div>

                    <!-- Clinical Demographics Inputs -->
                    <div id="clinical-fields-box" style="background: var(--fb-bg); border: 1px solid var(--fb-border); border-radius: 12px; padding: 14px; margin-bottom: 14px;">
                        <div style="font-weight: 800; font-size: 0.88rem; color: #0f766e; margin-bottom: 10px;">📋 البيانات السريرية والديموغرافية للحالة:</div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                            <div>
                                <label style="display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 3px;">🐾 الفصيلة:</label>
                                <select name="species" id="comp-species" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                                    <option value="pets">🐕 حيوانات أليفة (كلاب وقطط)</option>
                                    <option value="bovine">🐄 مجترات (أبقار وجاموس)</option>
                                    <option value="equine">🐎 خيول وبغال</option>
                                    <option value="ovine">🐑 أغنام وماعز</option>
                                    <option value="poultry">🐔 دواجن وطيور</option>
                                    <option value="wild">🦅 برية وغريبة</option>
                                </select>
                            </div>
                            <div>
                                <label style="display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 3px;">🧬 السلالة (Breed):</label>
                                <input type="text" name="breed" placeholder="مثال: شيرازي، هولشتاين، عربي أصيل" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                            <div>
                                <label style="display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 3px;">⏳ العمر:</label>
                                <input type="text" name="age" placeholder="مثال: سنتان أو 6 شهور" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                            </div>
                            <div>
                                <label style="display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 3px;">⚖️ الوزن (كجم):</label>
                                <input type="text" name="weight" placeholder="مثال: 4.5 أو 450" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                            </div>
                            <div>
                                <label style="display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 3px;">⚧ الجنس:</label>
                                <select name="gender" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                                    <option value="ذكر">ذكر (Male)</option>
                                    <option value="أنثى">أنثى (Female)</option>
                                </select>
                            </div>
                        </div>

                        <div style="margin-bottom: 10px;">
                            <label style="display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 3px;">🌡️ الأعراض السريرية والعلامات الحيوية:</label>
                            <input type="text" name="symptoms" placeholder="مثال: حرارة 40.2، خمول حاد، استسقاء بطني" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                        </div>

                        <div>
                            <label style="display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 3px;">💊 الأدوية والبروتوكولات المعطاة سابقاً:</label>
                            <input type="text" name="medications" placeholder="مثال: أوكسيتتراسيكلين، فلونيكسين" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                        </div>
                    </div>

                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.88rem;">📝 الشرح والتقرير السريري وتفاصيل الاستشارة:</label>
                        <textarea name="content" required rows="4" placeholder="اكتب وصفاً وافياً للحالة السريرية، الفحص الموضعي، والتاريخ المرضي وموضوع استشارة الزملاء..." style="width: 100%; padding: 12px; border: 1px solid var(--fb-border); border-radius: 10px; font-size: 0.95rem; background: var(--fb-bg); color: var(--fb-text); line-height: 1.6;"></textarea>
                    </div>

                    <!-- Media Attachment -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px;">
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.82rem;">📷 إرفاق صور / أشعة / فيديو:</label>
                            <input type="file" name="media_file" accept="image/*,video/*" style="width: 100%; padding: 6px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.82rem; background: var(--fb-bg);">
                        </div>
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.82rem;">🎥 أو رابط فيديو يوتيوب:</label>
                            <input type="url" name="youtube_url" placeholder="https://youtube.com/watch?v=..." style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-bg); color: var(--fb-text);">
                        </div>
                    </div>

                    <!-- Urgent Toggle Button -->
                    <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 10px 14px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 1.3rem;">🚨</span>
                            <div>
                                <strong style="color: #991b1b; font-size: 0.88rem;">تحديد كـ "حالة طارئة وعاجلة"</strong>
                                <div style="font-size: 0.74rem; color: #b91c1c;">تظهر ببروز في صدارة الشبكة لتنبيه الزملاء بالمساعدة الفورية</div>
                            </div>
                        </div>
                        <input type="checkbox" id="urgent-checkbox" onchange="document.getElementById('comp-is-urgent').value = this.checked ? '1' : '0'" style="width: 20px; height: 20px; accent-color: #dc2626; cursor: pointer;">
                    </div>

                    <button type="submit" class="btn btn-primary" style="width: 100%; padding: 12px; font-size: 1.05rem; font-weight: 800; border-radius: 10px; justify-content: center;">
                        🚀 نشر ومشاركة الحالة مع مجتمع الأطباء
                    </button>
                </form>
            </div>
        </div>

        <!-- Story Upload Modal -->
        <div id="story-upload-modal" class="modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 1100; align-items: center; justify-content: center; padding: 14px;">
            <div style="background: var(--fb-card); border-radius: 18px; max-width: 440px; width: 100%; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); border: 1px solid var(--fb-border); position: relative;">
                <button type="button" onclick="document.getElementById('story-upload-modal').style.display='none'" style="position: absolute; top: 14px; left: 14px; background: none; border: none; font-size: 1.2rem; cursor: pointer;">✕</button>
                <h3 style="margin: 0 0 14px 0; color: #0f766e; text-align: center;">📸 إضافة قصة عيادة يومية (24 ساعة)</h3>
                <form action="/community/story/create" method="POST" enctype="multipart/form-data">
                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">اختر صورة أو لقطة فيديو قصيرة:</label>
                        <input type="file" name="story_media" required accept="image/*,video/*" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px;">
                    </div>
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">تعليق أو نصيحة سريعة:</label>
                        <input type="text" name="caption" placeholder="مثال: لقطة من استئصال ورم خبيث صباح اليوم بنجاح..." style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.9rem;">
                    </div>
                    <button type="submit" class="btn btn-primary" style="width: 100%; padding: 12px; font-size: 1rem; border-radius: 10px; justify-content: center; font-weight: 800;">
                        📤 نشر القصة للزملاء
                    </button>
                </form>
            </div>
        </div>

        <!-- Fullscreen Story Viewer Modal (Strict No-DM Policy) -->
        <div id="story-viewer-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.94); z-index: 1200; align-items: center; justify-content: center; flex-direction: column;">
            <div style="position: absolute; top: 12px; left: 12px; right: 12px; height: 3px; background: rgba(255,255,255,0.3); border-radius: 2px; overflow: hidden;">
                <div id="story-progress-bar" style="height: 100%; width: 0%; background: #ffffff; transition: width 5s linear;"></div>
            </div>
            <button type="button" onclick="document.getElementById('story-viewer-modal').style.display='none'" style="position: absolute; top: 22px; left: 20px; background: none; border: none; color: white; font-size: 2rem; cursor: pointer;">✕</button>
            <div style="position: relative; max-width: 420px; width: 100%; max-height: 80vh; text-align: center; padding: 0 10px;">
                <div id="story-author-tag" style="position: absolute; top: 14px; right: 24px; background: rgba(0,0,0,0.6); color: white; padding: 4px 14px; border-radius: 20px; font-weight: 800; font-size: 0.88rem;"></div>
                <img id="story-img-elem" src="" style="max-width: 100%; max-height: 65vh; border-radius: 14px; object-fit: contain; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
                <div id="story-caption-elem" style="color: white; font-size: 1rem; font-weight: 700; margin-top: 14px; text-shadow: 0 2px 4px rgba(0,0,0,0.85); line-height: 1.6;"></div>
                <!-- Public Quick Reactions Bar (Zero DM) -->
                <div style="display: flex; justify-content: center; gap: 14px; margin-top: 16px;">
                    <button type="button" onclick="sendStoryReaction('❤️')" style="background: rgba(255,255,255,0.2); border: none; font-size: 1.5rem; padding: 6px 12px; border-radius: 20px; cursor: pointer;">❤️</button>
                    <button type="button" onclick="sendStoryReaction('👏')" style="background: rgba(255,255,255,0.2); border: none; font-size: 1.5rem; padding: 6px 12px; border-radius: 20px; cursor: pointer;">👏</button>
                    <button type="button" onclick="sendStoryReaction('💡')" style="background: rgba(255,255,255,0.2); border: none; font-size: 1.5rem; padding: 6px 12px; border-radius: 20px; cursor: pointer;">💡</button>
                    <button type="button" onclick="sendStoryReaction('🔥')" style="background: rgba(255,255,255,0.2); border: none; font-size: 1.5rem; padding: 6px 12px; border-radius: 20px; cursor: pointer;">🔥</button>
                    <button type="button" onclick="sendStoryReaction('🐾')" style="background: rgba(255,255,255,0.2); border: none; font-size: 1.5rem; padding: 6px 12px; border-radius: 20px; cursor: pointer;">🐾</button>
                </div>
            </div>
        </div>

        <!-- Image Lightbox Modal -->
        <div id="image-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.92); z-index: 1200; align-items: center; justify-content: center;" onclick="this.style.display='none'">
            <img id="image-modal-src" src="" style="max-width: 95%; max-height: 90vh; border-radius: 10px; object-fit: contain;">
        </div>
    </div>

    {COMMUNITY_JS}
    """
    return HTMLResponse(content=get_base_html("VetBook | ملتقى الأطباء البيطريين", body, user, lang), media_type="text/html; charset=utf-8")


@router.post("/community/post")
async def community_create_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form("case_study"),
    is_urgent: int = Form(0),
    species: str = Form(""),
    breed: str = Form(""),
    age: str = Form(""),
    weight: str = Form(""),
    gender: str = Form(""),
    symptoms: str = Form(""),
    medications: str = Form(""),
    media_file: UploadFile = File(None),
    youtube_url: str = Form(""),
    group_id: int = Form(0)
):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?redirect=/community", status_code=303)

    saved_img_name = None
    saved_video_name = None
    media_type = "text"
    has_media = False

    if media_file and media_file.filename:
        filename_lower = media_file.filename.lower()
        ext = os.path.splitext(media_file.filename)[1] or ".jpg"
        ts = int(datetime.now().timestamp())
        
        video_exts = [".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"]
        if any(filename_lower.endswith(ve) for ve in video_exts):
            media_type = "video"
            saved_video_name = f"video_{ts}_{user['id']}{ext}"
            full_dest = os.path.join(UPLOAD_DIR, saved_video_name)
            try:
                with open(full_dest, "wb") as buf:
                    shutil.copyfileobj(media_file.file, buf)
                has_media = True
            except Exception:
                saved_video_name = None
                media_type = "text"
        else:
            media_type = "image"
            saved_img_name = f"post_{ts}_{user['id']}{ext}"
            full_dest = os.path.join(UPLOAD_DIR, saved_img_name)
            try:
                with open(full_dest, "wb") as buf:
                    shutil.copyfileobj(media_file.file, buf)
                has_media = True
            except Exception:
                saved_img_name = None
                media_type = "text"

    if not saved_video_name and not saved_img_name and youtube_url and youtube_url.strip():
        embed = extract_youtube_embed(youtube_url)
        if embed:
            media_type = "youtube"
            saved_video_name = embed
            has_media = True

    has_details = bool(species or symptoms or breed)
    eval_res = evaluate_clinical_content(title, content, has_media, bool(is_urgent), has_details)
    quality_score = eval_res["score"]

    conn = get_db()
    c = conn.cursor()
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
    INSERT INTO community_posts (
        user_id, author_name, author_specialty, author_country,
        category, title, content, is_urgent, species, breed, age, weight,
        gender, symptoms, medications, group_id, image_path, video_path,
        media_type, quality_score, virality_score, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 5.0, ?)
    """, (
        user["id"],
        user.get("name", "طبيب بيطري"),
        user.get("clinic_name", "طب وجراحة الحيوان"),
        user.get("country", "مصر"),
        category,
        title.strip(),
        content.strip(),
        is_urgent,
        species.strip(),
        breed.strip(),
        age.strip(),
        weight.strip(),
        gender.strip(),
        symptoms.strip(),
        medications.strip(),
        group_id,
        saved_img_name,
        saved_video_name,
        media_type,
        quality_score,
        now_ts
    ))
    post_id = c.lastrowid
    conn.commit()

    # 1. Platform-Wide Broadcast Notification to ALL registered doctors
    try:
        author_name = user.get("name", "طبيب بيطري")
        c.execute("""
        INSERT INTO broadcast_notifications (title, message, target_country, badge_type, created_at)
        VALUES (?, ?, 'all', 'community', ?)
        """, (
            f"📢 منشور وحالة جديدة من د. {author_name}",
            f"{title.strip()[:100]}",
            now_ts
        ))
        conn.commit()
    except Exception:
        pass
    conn.close()

    # 2. Multi-Layer JSON Persistence (Survives Serverless Container Recycles)
    post_record = {
        "id": post_id,
        "user_id": user["id"],
        "author_name": user.get("name", "طبيب بيطري"),
        "author_specialty": user.get("clinic_name", "طب وجراحة الحيوان"),
        "author_country": user.get("country", "مصر"),
        "category": category,
        "title": title.strip(),
        "content": content.strip(),
        "is_urgent": is_urgent,
        "species": species.strip(),
        "breed": breed.strip(),
        "age": age.strip(),
        "weight": weight.strip(),
        "gender": gender.strip(),
        "symptoms": symptoms.strip(),
        "medications": medications.strip(),
        "group_id": group_id,
        "image_path": saved_img_name,
        "video_path": saved_video_name,
        "media_type": media_type,
        "quality_score": quality_score,
        "virality_score": 5.0,
        "created_at": now_ts
    }
    save_post_to_backup_sync(post_record)

    return RedirectResponse(f"/community?posted=1#post-{post_id}", status_code=303)


@router.post("/api/community/sync-posts")
async def api_community_sync_posts(request: Request):
    """
    Client-Server Two-Way Sync Endpoint:
    Guarantees that posts created by doctors in localStorage are permanently synced to the database.
    """
    from app import get_current_user
    user = get_current_user(request)
    try:
        body = await request.json()
        client_posts = body.get("posts", [])
        if not client_posts:
            return JSONResponse({"status": "empty", "synced": 0})

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT title, created_at FROM community_posts")
        existing_keys = set((r[0], r[1]) for r in c.fetchall())

        synced_count = 0
        for p in client_posts:
            key = (p.get("title"), p.get("created_at"))
            if key not in existing_keys and p.get("title") and p.get("content"):
                c.execute("""
                INSERT INTO community_posts (
                    user_id, author_name, author_specialty, author_country,
                    category, title, content, is_urgent, species, breed, age, weight,
                    gender, symptoms, medications, group_id, image_path, video_path,
                    media_type, quality_score, virality_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 5.0, ?)
                """, (
                    p.get("user_id", user["id"] if user else 4),
                    p.get("author_name", user.get("name", "طبيب بيطري") if user else "طبيب بيطري"),
                    p.get("author_specialty", "طب وجراحة الحيوان"),
                    p.get("author_country", "مصر"),
                    p.get("category", "case_study"),
                    p.get("title", ""),
                    p.get("content", ""),
                    p.get("is_urgent", 0),
                    p.get("species", ""),
                    p.get("breed", ""),
                    p.get("age", ""),
                    p.get("weight", ""),
                    p.get("gender", ""),
                    p.get("symptoms", ""),
                    p.get("medications", ""),
                    p.get("group_id", 0),
                    p.get("image_path"),
                    p.get("video_path"),
                    p.get("media_type", "text"),
                    p.get("quality_score", 10),
                    p.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                ))
                existing_keys.add(key)
                save_post_to_backup_sync(p)
                synced_count += 1

        conn.commit()
        conn.close()
        return JSONResponse({"status": "success", "synced": synced_count})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/community/like/{post_id}")
async def community_toggle_like(request: Request, post_id: int, reaction: str = Form("like")):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        if request.headers.get("Accept") == "application/json":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return RedirectResponse("/login?redirect=/community", status_code=303)

    clean_react = reaction.strip().lower()
    if clean_react not in REACTIONS:
        clean_react = "like"

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, reaction_type FROM community_likes WHERE post_id = ? AND user_id = ?", (post_id, user["id"]))
    existing = c.fetchone()

    is_liked = True
    if existing:
        if existing["reaction_type"] == clean_react:
            c.execute("DELETE FROM community_likes WHERE id = ?", (existing["id"],))
            c.execute("UPDATE community_posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (post_id,))
            is_liked = False
        else:
            c.execute("UPDATE community_likes SET reaction_type = ? WHERE id = ?", (clean_react, existing["id"]))
    else:
        c.execute("INSERT INTO community_likes (post_id, user_id, reaction_type, created_at) VALUES (?, ?, ?, ?)",
                  (post_id, user["id"], clean_react, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("UPDATE community_posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))

    # Update specialized reactions count
    c.execute("SELECT COUNT(*) FROM community_likes WHERE post_id = ? AND reaction_type != 'like'", (post_id,))
    spec_cnt = c.fetchone()[0]
    c.execute("UPDATE community_posts SET specialized_reactions_count = ? WHERE id = ?", (spec_cnt, post_id))

    c.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,))
    p = c.fetchone()
    v_score = 1.0
    likes_count = 0
    if p:
        v_score = compute_virality_score(dict(p))
        likes_count = p["likes_count"]
        c.execute("UPDATE community_posts SET virality_score = ? WHERE id = ?", (v_score, post_id))

    conn.commit()
    conn.close()

    if request.headers.get("Accept") == "application/json":
        return JSONResponse({
            "success": True,
            "is_liked": is_liked,
            "reaction": clean_react,
            "likes_count": likes_count,
            "virality_score": v_score
        })

    return RedirectResponse(f"/community#post-{post_id}", status_code=303)


@router.post("/community/comment/{post_id}")
async def community_add_comment(
    request: Request,
    post_id: int,
    content: str = Form(...),
    parent_id: int = Form(0)
):
    from app import get_current_user

    user = get_current_user(request)
    if not user or not content.strip():
        if request.headers.get("Accept") == "application/json":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return RedirectResponse("/login?redirect=/community", status_code=303)

    is_detailed = 1 if len(content.strip()) >= 40 else 0

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_comments (post_id, user_id, author_name, author_specialty, author_country, parent_comment_id, content, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_id,
        user["id"],
        user.get("name", "طبيب بيطري"),
        user.get("clinic_name", "طبيب بيطري"),
        user.get("country", "مصر"),
        parent_id,
        content.strip(),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    c.execute("UPDATE community_posts SET comments_count = comments_count + 1 WHERE id = ?", (post_id,))
    if is_detailed:
        c.execute("UPDATE community_posts SET detailed_comments_count = detailed_comments_count + 1 WHERE id = ?", (post_id,))

    conn.commit()
    conn.close()

    if request.headers.get("Accept") == "application/json":
        return JSONResponse({"success": True})

    return RedirectResponse(f"/community#post-{post_id}", status_code=303)


@router.post("/community/comment/best/{comment_id}")
async def community_mark_best_answer(request: Request, comment_id: int):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM community_comments WHERE id = ?", (comment_id,))
    cm = c.fetchone()
    if not cm:
        conn.close()
        return JSONResponse({"error": "not found"}, status_code=404)

    post_id = cm["post_id"]
    c.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,))
    p = c.fetchone()
    if not p or p["user_id"] != user["id"]:
        conn.close()
        return JSONResponse({"error": "forbidden"}, status_code=403)

    # Mark as best diagnosis
    c.execute("UPDATE community_comments SET is_best_answer = 0 WHERE post_id = ?", (post_id,))
    c.execute("UPDATE community_comments SET is_best_answer = 1 WHERE id = ?", (comment_id,))
    c.execute("UPDATE community_posts SET has_best_answer = 1 WHERE id = ?", (post_id,))

    # Award +50 reputation points to author of best answer
    commenter_id = cm["user_id"]
    if commenter_id and commenter_id > 0:
        c.execute("UPDATE users SET reputation_score = reputation_score + 50 WHERE id = ?", (commenter_id,))

    conn.commit()
    conn.close()

    return JSONResponse({"success": True})


@router.post("/community/ai-consult/{post_id}")
async def community_ai_consult(request: Request, post_id: int):
    from app import get_current_user, ask_ai_chat, get_effective_groq_api_key

    user = get_current_user(request)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,))
    post = c.fetchone()
    if not post:
        conn.close()
        return JSONResponse({"error": "not found"}, status_code=404)

    if post["ai_analysis"]:
        conn.close()
        return JSONResponse({"success": True, "analysis": post["ai_analysis"]})

    p_dict = dict(post)
    case_context = f"""
    عنوان الحالة: {p_dict.get('title')}
    الفصيلة: {p_dict.get('species')} | السلالة: {p_dict.get('breed')} | العمر: {p_dict.get('age')} | الوزن: {p_dict.get('weight')} كجم
    الأعراض السريرية: {p_dict.get('symptoms')}
    الأدوية المعطاة سابقاً: {p_dict.get('medications')}
    تفاصيل الفحص: {p_dict.get('content')}
    """

    prompt = f"""
    بصفتك الذكاء الاصطناعي السريري المتقدم لمنصة VetMind AI، قدم تحليلاً طبياً موجزاً واحترافياً للزملاء الأطباء:
    {case_context}

    التشخيصات التفريقية (Top Differential Diagnoses)
    الفحوصات المقترحة (Diagnostic Workup)
    البروتوكول العلاجي المقترح (Treatment Plan)
    """

    api_key = get_effective_groq_api_key(request)
    ai_response = ask_ai_chat(api_key, prompt, [], p_dict.get("image_path"), "ar", "مصر")

    c.execute("UPDATE community_posts SET ai_analysis = ? WHERE id = ?", (ai_response, post_id))
    c.execute("""
    INSERT INTO community_comments (post_id, user_id, author_name, author_specialty, author_country, content, is_ai_comment, created_at)
    VALUES (?, 0, 'VetMind AI المساعد السريري', 'ذكاء اصطناعي سريري معتمد', 'سحابي', ?, 1, ?)
    """, (post_id, ai_response, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return JSONResponse({"success": True, "analysis": ai_response})


@router.post("/community/bookmark/{post_id}")
async def community_toggle_bookmark(request: Request, post_id: int):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_bookmarks WHERE post_id = ? AND user_id = ?", (post_id, user["id"]))
    existing = c.fetchone()

    is_bookmarked = True
    if existing:
        c.execute("DELETE FROM community_bookmarks WHERE id = ?", (existing["id"],))
        c.execute("UPDATE community_posts SET bookmarks_count = MAX(0, bookmarks_count - 1) WHERE id = ?", (post_id,))
        is_bookmarked = False
    else:
        c.execute("INSERT INTO community_bookmarks (post_id, user_id, created_at) VALUES (?, ?, ?)",
                  (post_id, user["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("UPDATE community_posts SET bookmarks_count = bookmarks_count + 1 WHERE id = ?", (post_id,))

    conn.commit()
    conn.close()

    return JSONResponse({"success": True, "is_bookmarked": is_bookmarked})


@router.post("/community/poll/vote/{post_id}")
async def community_vote_poll(request: Request, post_id: int, opt_id: int = Form(...)):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT poll_data FROM community_posts WHERE id = ?", (post_id,))
    row = c.fetchone()
    if not row or not row["poll_data"]:
        conn.close()
        return JSONResponse({"error": "no poll"}, status_code=404)

    try:
        p_data = json.loads(row["poll_data"])
        for opt in p_data.get("options", []):
            if opt["id"] == opt_id:
                opt["votes"] = opt.get("votes", 0) + 1
                break
        c.execute("UPDATE community_posts SET poll_data = ? WHERE id = ?", (json.dumps(p_data, ensure_ascii=False), post_id))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()

    return JSONResponse({"success": True})


@router.post("/community/story/create")
async def community_create_story(
    request: Request,
    caption: str = Form(""),
    story_media: UploadFile = File(...)
):
    from app import get_current_user

    user = get_current_user(request)
    if not user or not story_media or not story_media.filename:
        return RedirectResponse("/community", status_code=303)

    ext = os.path.splitext(story_media.filename)[1] or ".jpg"
    saved_name = f"story_{int(datetime.now().timestamp())}_{user['id']}{ext}"
    try:
        with open(os.path.join(UPLOAD_DIR, saved_name), "wb") as buf:
            shutil.copyfileobj(story_media.file, buf)
    except Exception:
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_stories (user_id, author_name, media_url, caption, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        user["id"],
        user.get("name", "طبيب بيطري"),
        saved_name,
        caption.strip(),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

    return RedirectResponse("/community", status_code=303)


@router.post("/community/post/delete/{post_id}")
async def community_delete_post(request: Request, post_id: int):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM community_posts WHERE id = ?", (post_id,))
    p = c.fetchone()
    if p and (user.get("is_admin") or user["id"] == p["user_id"]):
        c.execute("DELETE FROM community_posts WHERE id = ?", (post_id,))
        c.execute("DELETE FROM community_comments WHERE post_id = ?", (post_id,))
        c.execute("DELETE FROM community_likes WHERE post_id = ?", (post_id,))
        c.execute("DELETE FROM community_bookmarks WHERE post_id = ?", (post_id,))
        conn.commit()

    conn.close()
    return RedirectResponse("/community", status_code=303)


@router.post("/community/connect/{colleague_id}")
async def community_toggle_connect(request: Request, colleague_id: int):
    """Adds or removes a colleague connection (Replaces private DM with public professional connections)."""
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_connections WHERE user_id = ? AND colleague_id = ?", (user["id"], colleague_id))
    existing = c.fetchone()

    connected = True
    if existing:
        c.execute("DELETE FROM community_connections WHERE id = ?", (existing["id"],))
        connected = False
    else:
        c.execute("INSERT INTO community_connections (user_id, colleague_id, status, created_at) VALUES (?, ?, 'connected', ?)",
                  (user["id"], colleague_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return JSONResponse({"success": True, "connected": connected})


@router.post("/community/follow/{colleague_id}")
async def community_toggle_follow(request: Request, colleague_id: int):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_connections WHERE user_id = ? AND colleague_id = ?", (user["id"], colleague_id))
    existing = c.fetchone()

    following = True
    if existing:
        c.execute("DELETE FROM community_connections WHERE id = ?", (existing["id"],))
        following = False
    else:
        c.execute("INSERT INTO community_connections (user_id, colleague_id, status, created_at) VALUES (?, ?, 'following', ?)",
                  (user["id"], colleague_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return JSONResponse({"success": True, "following": following})


@router.get("/community/profile/{user_id}", response_class=HTMLResponse)
async def community_doctor_profile(request: Request, user_id: int):
    from app import get_current_user, get_user_lang, get_text, get_base_html

    curr_user = get_current_user(request)
    lang = get_user_lang(request)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    target_user = c.fetchone()
    if not target_user:
        conn.close()
        return RedirectResponse("/community", status_code=303)

    t_dict = dict(target_user)

    # Doctor cases
    c.execute("SELECT * FROM community_posts WHERE user_id = ? ORDER BY id DESC", (user_id,))
    doctor_posts = [dict(r) for r in c.fetchall()]

    # Stats
    cases_count = len(doctor_posts)
    c.execute("SELECT COUNT(*) FROM community_comments WHERE user_id = ? AND is_best_answer = 1", (user_id,))
    best_answers_count = c.fetchone()[0]
    reputation = t_dict.get("reputation_score", 100) + (best_answers_count * 50)

    # Connection status
    is_connected = False
    if curr_user:
        c.execute("SELECT id FROM community_connections WHERE user_id = ? AND colleague_id = ?", (curr_user["id"], user_id))
        is_connected = bool(c.fetchone())

    conn.close()

    connect_btn_text = "✔️ زميل في الشبكة" if is_connected else "➕ إضافة كزميل"
    connect_btn_style = "background: #059669; color: white;" if is_connected else "background: #0f766e; color: white;"

    cover_bg = "linear-gradient(135deg, #0f766e 0%, #0d9488 100%)"
    body = f"""
    {COMMUNITY_CSS}
    <div class="fb-app-wrapper" style="padding-top: 14px;">
        <div style="max-width: 960px; margin: 0 auto; padding: 0 12px;">
            <!-- Facebook-style Profile Header Card (STRICT NO-MESSENGER) -->
            <div class="fb-card" style="margin-bottom: 20px;">
                <div class="fb-profile-cover" style="background: {cover_bg};"></div>
                
                <div class="fb-profile-header-body">
                    <div class="profile-header-avatar-row">
                        <div class="profile-header-avatar">
                            {t_dict['name'][0]}
                        </div>
                        <div class="profile-header-actions">
                            {f'<button type="button" onclick="toggleColleagueConnect({user_id}, this)" class="btn" style="padding: 8px 16px; border-radius: 20px; font-weight: 700; {connect_btn_style}">{connect_btn_text}</button>' if (curr_user and curr_user['id'] != user_id) else ''}
                            <button type="button" onclick="alert('تم نسخ رابط الملف الشخصي!')" class="btn btn-outline" style="padding: 8px 16px; border-radius: 20px; font-weight: 700;">🔗 مشاركة الملف</button>
                            <a href="/community" class="btn btn-outline" style="padding: 8px 16px; border-radius: 20px;">⬅️ العودة للشبكة</a>
                        </div>
                    </div>

                    <h1 style="margin: 0; font-size: 1.6rem; color: var(--fb-text); display: flex; align-items: center; gap: 8px; flex-wrap: wrap; line-height: 1.45;">
                        <span>د. {t_dict['name']}</span>
                        <span style="font-size: 1.1rem; color: #059669;" title="طبيب بيطري معتمد وموثق">🩺</span>
                        <span style="background: #ecfdf5; color: #047857; font-size: 0.72rem; padding: 3px 10px; border-radius: 12px; font-weight: 800; border: 1px solid #6ee7b7;">طبيب موثق</span>
                    </h1>

                    <div style="font-size: 0.95rem; color: var(--fb-text-muted); margin-top: 4px;">
                        {t_dict.get('clinic_name') or 'مركز طب وجراحة الحيوان المتقدم'} • {t_dict.get('country') or 'مصر'}
                    </div>

                    <p style="color: var(--fb-text); font-size: 0.92rem; margin: 12px 0; line-height: 1.75; overflow-wrap: break-word;">
                        {t_dict.get('bio') or 'طبيب بيطري ممارس متخصص في التشخيص الإكلينيكي والجراحة ورعاية الحيوانات، عضو شبكة VetMind AI للتبادل العلمي.'}
                    </p>

                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; border-top: 1px solid var(--fb-border); padding-top: 16px; margin-top: 12px;">
                        <div style="background: var(--fb-bg); padding: 10px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 1.4rem; font-weight: 800; color: #0f766e;">{cases_count}</div>
                            <div style="font-size: 0.75rem; color: var(--fb-text-muted);">حالة سريرية منشورة</div>
                        </div>
                        <div style="background: var(--fb-bg); padding: 10px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 1.4rem; font-weight: 800; color: #059669;">{best_answers_count}</div>
                            <div style="font-size: 0.75rem; color: var(--fb-text-muted);">تشخيصات معتمدة 🏆</div>
                        </div>
                        <div style="background: var(--fb-bg); padding: 10px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 1.4rem; font-weight: 800; color: #ea580c;">{reputation}</div>
                            <div style="font-size: 0.75rem; color: var(--fb-text-muted);">نقاط السمعة العلمية 🎖️</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Doctor Posts Stream -->
            <h3 style="color: var(--fb-text); margin-bottom: 14px; line-height: 1.45;">📋 الحالات والمنشورات السريرية للدكتور {t_dict['name']}:</h3>
            {"".join([f'<div class="fb-card" style="padding: 16px; margin-bottom: 14px;"><a href="/community#post-{dp["id"]}" style="text-decoration: none; color: inherit;"><h4 style="margin: 0 0 6px 0; color: #0f766e; font-size: 1.1rem; line-height: 1.45;">{dp["title"]}</h4><p style="margin: 0; font-size: 0.9rem; color: var(--fb-text); line-height: 1.75; overflow-wrap: break-word;">{dp["content"][:240]}...</p><div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-top: 8px;">⏱️ {dp["created_at"]} • 🔥 {dp.get("likes_count", 0)} تفاعل • 💬 {dp.get("comments_count", 0)} رد</div></a></div>' for dp in doctor_posts]) if doctor_posts else "<div class='fb-card' style='padding: 24px; text-align: center; color: var(--fb-text-muted);'>لم يقم هذا الطبيب بنشر حالات بعد.</div>"}
        </div>
    </div>
    {COMMUNITY_JS}
    """
    return HTMLResponse(content=get_base_html(f"د. {t_dict['name']} | VetBook", body, curr_user, lang), media_type="text/html; charset=utf-8")


@router.post("/community/events/interest/{event_id}")
async def community_toggle_event_interest(request: Request, event_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_events SET interested_count = interested_count + 1 WHERE id = ?", (event_id,))
    c.execute("SELECT interested_count FROM community_events WHERE id = ?", (event_id,))
    row = c.fetchone()
    cnt = row[0] if row else 1
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "interested_count": cnt})


@router.get("/admin/community/boost/{post_id}")
async def admin_boost_post(request: Request, post_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_posts SET is_boosted = CASE WHEN is_boosted = 1 THEN 0 ELSE 1 END WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/community#post-{post_id}", status_code=303)


@router.get("/admin/community/pin/{post_id}")
async def admin_pin_post(request: Request, post_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_posts SET is_pinned = CASE WHEN is_pinned = 1 THEN 0 ELSE 1 END WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/community#post-{post_id}", status_code=303)
