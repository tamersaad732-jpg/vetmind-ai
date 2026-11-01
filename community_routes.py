# -*- coding: utf-8 -*-
"""
VetMind AI - VetBook Social Network & Clinical Case Exchange
Full-Featured Veterinary Social Network inspired by modern social platforms (Facebook UX),
tailored specifically for veterinarians, clinic owners, breeders, and veterinary institutions.

Features:
- Main Feed & Smart Algorithmic Relevance (EdgeRank)
- Clinical Post Composer (Multi-photo grid, video, demographics, urgent triage, privacy audience)
- Specialized Reactions & Threaded Nested Comments
- Real Social Graph: Friend Requests, Follows, Blocks, Mutual Colleagues
- Veterinary Pages & Institutional Profiles (Clinics, Hospitals, Labs)
- Specialized Clinical Groups & Societies
- Conferences, Seminars & Clinical Events (RSVP)
- In-App Real-Time Social Notifications
- Deep Universal VetBook Search
- Post & Comment Editing, Deleting, Bookmarking, and Direct Sharing
- Profile Management with Cover & Avatar
- Clinical Content Reporting & Admin Moderation Panel
- Offline Resilience & Two-Way LocalStorage Sync
- STRICT: NO Messenger / NO Private DMs
- STRICT: ZERO AI Assistant inside VetBook (Clinical AI remains in diagnostic tools)
"""

import os
import random
import json
import uuid
import sqlite3
import shutil
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
    UPLOAD_DIR = "/tmp/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
        tmp_db = "/tmp/vetmind.db"
        if not os.path.exists(tmp_db) and os.path.exists(DB_PATH):
            try:
                shutil.copy2(DB_PATH, tmp_db)
            except Exception:
                pass
        if os.path.exists(tmp_db):
            conn = sqlite3.connect(tmp_db, timeout=20.0)
            conn.row_factory = sqlite3.Row
            return conn
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

# Multi-Layer JSON Backup Sync & Deletion Tombstones for Post Persistence
BACKUP_SYNC_FILE = os.path.join(UPLOAD_DIR, "community_posts_sync.json")
STATIC_BACKUP_FILE = os.path.join(BASE_DIR, "static", "community_posts_sync.json")
DELETED_POSTS_FILE = os.path.join(UPLOAD_DIR, "community_deleted_posts.json")
STATIC_DELETED_FILE = os.path.join(BASE_DIR, "static", "community_deleted_posts.json")
BACKUP_STORIES_FILE = os.path.join(UPLOAD_DIR, "community_stories_sync.json")
STATIC_STORIES_FILE = os.path.join(BASE_DIR, "static", "community_stories_sync.json")

def save_story_to_backup_sync(story_dict: dict):
    try:
        stories = []
        for s_file in [BACKUP_STORIES_FILE, STATIC_STORIES_FILE]:
            if os.path.exists(s_file):
                try:
                    with open(s_file, "r", encoding="utf-8-sig") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, list):
                            stories = loaded
                            break
                except Exception:
                    pass
        s_clean = {k: v for k, v in story_dict.items() if isinstance(v, (str, int, float, bool)) or v is None}
        stories = [s for s in stories if s.get("id") != s_clean.get("id")]
        stories.insert(0, s_clean)
        stories = stories[:50]
        for s_file in [BACKUP_STORIES_FILE, STATIC_STORIES_FILE]:
            try:
                os.makedirs(os.path.dirname(s_file), exist_ok=True)
                with open(s_file, "w", encoding="utf-8") as f:
                    json.dump(stories, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
    except Exception as e:
        print("save_story_to_backup_sync error:", e)

def sync_stories_from_backup_sync(conn):
    try:
        stories = []
        for s_file in [BACKUP_STORIES_FILE, STATIC_STORIES_FILE]:
            if os.path.exists(s_file):
                try:
                    with open(s_file, "r", encoding="utf-8-sig") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, list) and len(loaded) > 0:
                            stories = loaded
                            break
                except Exception:
                    pass
        if not stories:
            return
        c = conn.cursor()
        c.execute("SELECT id FROM community_stories")
        existing_ids = set(r[0] for r in c.fetchall())
        for s in stories:
            s_id = s.get("id")
            if s_id and s_id not in existing_ids and s.get("media_url"):
                c.execute("""
                INSERT OR REPLACE INTO community_stories (
                    id, user_id, author_name, author_specialty, author_avatar,
                    media_url, caption, likes_count, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s_id,
                    s.get("user_id", 4),
                    s.get("author_name", "طبيب بيطري"),
                    s.get("author_specialty", "طب وجراحة الحيوان"),
                    s.get("author_avatar", ""),
                    s.get("media_url", ""),
                    s.get("caption", ""),
                    s.get("likes_count", 0),
                    s.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    s.get("expires_at", "")
                ))
                existing_ids.add(s_id)
        conn.commit()
    except Exception as e:
        print("sync_stories_from_backup_sync error:", e)

def get_deleted_posts_set() -> set:
    deleted = set()
    for fpath in [DELETED_POSTS_FILE, STATIC_DELETED_FILE]:
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, (int, str)):
                                deleted.add(item)
                            elif isinstance(item, dict):
                                if "id" in item:
                                    deleted.add(item["id"])
                                if "title" in item:
                                    deleted.add(item["title"])
            except Exception:
                pass
    return deleted

def delete_post_from_backup_sync(post_id: int, title: str = ""):
    try:
        # 1. Scrub from all sync JSON files
        for p_file in [BACKUP_SYNC_FILE, STATIC_BACKUP_FILE]:
            if os.path.exists(p_file):
                try:
                    with open(p_file, "r", encoding="utf-8-sig") as f:
                        posts = json.load(f)
                    if isinstance(posts, list):
                        new_posts = [
                            p for p in posts 
                            if p.get("id") != post_id and (not title or p.get("title") != title)
                        ]
                        with open(p_file, "w", encoding="utf-8") as f:
                            json.dump(new_posts, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        # 2. Add tombstone to DELETED_POSTS_FILE & STATIC_DELETED_FILE
        for d_file in [DELETED_POSTS_FILE, STATIC_DELETED_FILE]:
            try:
                os.makedirs(os.path.dirname(d_file), exist_ok=True)
                cur_deleted = []
                if os.path.exists(d_file):
                    try:
                        with open(d_file, "r", encoding="utf-8-sig") as f:
                            cur_deleted = json.load(f)
                    except Exception:
                        cur_deleted = []
                if not isinstance(cur_deleted, list):
                    cur_deleted = []
                if post_id not in cur_deleted:
                    cur_deleted.append(post_id)
                if title and title not in cur_deleted:
                    cur_deleted.append(title)
                with open(d_file, "w", encoding="utf-8") as f:
                    json.dump(cur_deleted[:500], f, ensure_ascii=False, indent=2)
            except Exception:
                pass
    except Exception as e:
        print("delete_post_from_backup_sync error:", e)

def save_post_to_backup_sync(post_dict: dict):
    try:
        posts = []
        for p_file in [BACKUP_SYNC_FILE, STATIC_BACKUP_FILE]:
            if os.path.exists(p_file):
                try:
                    with open(p_file, "r", encoding="utf-8-sig") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, list):
                            posts = loaded
                            break
                except Exception:
                    pass
        p_clean = {k: v for k, v in post_dict.items() if isinstance(v, (str, int, float, bool)) or v is None}
        posts = [p for p in posts if p.get("title") != p_clean.get("title")]
        posts.insert(0, p_clean)
        posts = posts[:200]
        for p_file in [BACKUP_SYNC_FILE, STATIC_BACKUP_FILE]:
            try:
                os.makedirs(os.path.dirname(p_file), exist_ok=True)
                with open(p_file, "w", encoding="utf-8") as f:
                    json.dump(posts, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
    except Exception as e:
        print("save_post_to_backup_sync error:", e)

def sync_posts_from_backup_sync(conn):
    try:
        deleted_set = get_deleted_posts_set()
        posts = []
        for p_file in [BACKUP_SYNC_FILE, STATIC_BACKUP_FILE]:
            if os.path.exists(p_file):
                try:
                    with open(p_file, "r", encoding="utf-8-sig") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, list) and len(loaded) > 0:
                            posts = loaded
                            break
                except Exception:
                    pass
        if not posts:
            return
        c = conn.cursor()
        c.execute("SELECT id, title FROM community_posts")
        existing_rows = c.fetchall()
        existing_ids = set(r[0] for r in existing_rows)
        existing_titles = set((r[1] or "").strip() for r in existing_rows if r[1])
        for p in posts:
            p_id = p.get("id")
            p_title = (p.get("title") or "").strip()
            if not p_title or not p.get("content"):
                continue
            if (p_id and p_id in deleted_set) or (p_title in deleted_set):
                continue
            if (p_id and p_id in existing_ids) or (p_title in existing_titles):
                continue
                c.execute("""
                INSERT INTO community_posts (
                    user_id, author_name, author_specialty, author_country,
                    category, title, content, is_urgent, species, breed, age, weight,
                    gender, symptoms, medications, group_id, page_id, image_path, extra_images, video_path,
                    media_type, quality_score, virality_score, privacy, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 5.0, ?, ?)
                """, (
                    p.get("user_id", 4),
                    p.get("author_name", "طبيب بيطري"),
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
                    p.get("page_id", 0),
                    p.get("image_path"),
                    p.get("extra_images", ""),
                    p.get("video_path"),
                    p.get("media_type", "text"),
                    p.get("quality_score", 10),
                    p.get("privacy", "public"),
                    p.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                ))
                existing_keys.add(key)
        conn.commit()
    except Exception as e:
        print("sync_posts_from_backup_sync error:", e)

def init_community_schema():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 1. users table columns
        c.execute("PRAGMA table_info(users)")
        u_cols = set(r["name"] for r in c.fetchall())
        user_new_cols = [
            ("bio", "TEXT DEFAULT ''"),
            ("cover_photo", "TEXT DEFAULT ''"),
            ("reputation_score", "INTEGER DEFAULT 100"),
            ("verified_vet", "INTEGER DEFAULT 1"),
            ("specialty", "TEXT DEFAULT 'طب وجراحة الحيوان'"),
            ("work_place", "TEXT DEFAULT ''"),
            ("city", "TEXT DEFAULT ''"),
            ("privacy_show_phone", "INTEGER DEFAULT 0"),
            ("privacy_show_email", "INTEGER DEFAULT 0"),
            ("privacy_posts_default", "TEXT DEFAULT 'public'")
        ]
        for col, ctype in user_new_cols:
            if col not in u_cols:
                try:
                    c.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
                except Exception:
                    pass

        # 2. community_posts columns
        c.execute("PRAGMA table_info(community_posts)")
        post_cols = set(r["name"] for r in c.fetchall())
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
            ("page_id", "INTEGER DEFAULT 0"),
            ("shared_post_id", "INTEGER DEFAULT 0"),
            ("poll_data", "TEXT DEFAULT ''"),
            ("shares_count", "INTEGER DEFAULT 0"),
            ("bookmarks_count", "INTEGER DEFAULT 0"),
            ("specialized_reactions_count", "INTEGER DEFAULT 0"),
            ("detailed_comments_count", "INTEGER DEFAULT 0"),
            ("has_best_answer", "INTEGER DEFAULT 0"),
            ("privacy", "TEXT DEFAULT 'public'"),
            ("is_edited", "INTEGER DEFAULT 0"),
            ("updated_at", "TEXT DEFAULT ''")
        ]
        for col, ctype in cols_to_add:
            if col not in post_cols:
                try:
                    c.execute(f"ALTER TABLE community_posts ADD COLUMN {col} {ctype}")
                except Exception:
                    pass

        # 3. community_comments columns
        c.execute("PRAGMA table_info(community_comments)")
        cm_cols = set(r["name"] for r in c.fetchall())
        for col, ctype in [
            ("image_url", "TEXT DEFAULT ''"),
            ("is_best_answer", "INTEGER DEFAULT 0"),
            ("likes_count", "INTEGER DEFAULT 0"),
            ("parent_comment_id", "INTEGER DEFAULT 0")
        ]:
            if col not in cm_cols:
                try:
                    c.execute(f"ALTER TABLE community_comments ADD COLUMN {col} {ctype}")
                except Exception:
                    pass

        # 4. Friends Table (Real Social Network Friending)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT,
            UNIQUE(sender_id, receiver_id)
        )
        """)

        # 5. Follows Table (Professional following)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(follower_id, following_id)
        )
        """)

        # 6. Blocks Table (Privacy & Safety)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(blocker_id, blocked_id)
        )
        """)

        # 7. Veterinary Pages Table (Clinics, Hospitals, Labs, Syndicates)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'clinic',
            description TEXT DEFAULT '',
            avatar_image TEXT DEFAULT '',
            cover_image TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            website TEXT DEFAULT '',
            address TEXT DEFAULT '',
            city TEXT DEFAULT '',
            country TEXT DEFAULT 'مصر',
            is_verified INTEGER DEFAULT 0,
            followers_count INTEGER DEFAULT 0,
            owner_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        # Stories Table & Story Reactions
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            author_specialty TEXT DEFAULT 'طب وجراحة الحيوان',
            author_avatar TEXT DEFAULT '',
            media_url TEXT NOT NULL,
            caption TEXT DEFAULT '',
            likes_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            expires_at TEXT
        )
        """)

        # Migration check for existing community_stories table
        c.execute("PRAGMA table_info(community_stories)")
        story_cols = set(r["name"] for r in c.fetchall())
        for col, ctype in [
            ("author_specialty", "TEXT DEFAULT 'طب وجراحة الحيوان'"),
            ("author_avatar", "TEXT DEFAULT ''"),
            ("likes_count", "INTEGER DEFAULT 0"),
            ("caption", "TEXT DEFAULT ''"),
            ("expires_at", "TEXT")
        ]:
            if col not in story_cols:
                try:
                    c.execute(f"ALTER TABLE community_stories ADD COLUMN {col} {ctype}")
                except Exception:
                    pass

        c.execute("""
        CREATE TABLE IF NOT EXISTS community_story_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reaction_type TEXT DEFAULT 'like',
            created_at TEXT NOT NULL,
            UNIQUE(story_id, user_id)
        )
        """)

        # 8. Page Followers Table
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_page_followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(page_id, user_id)
        )
        """)

        # 9. In-App Notifications Table
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            actor_id INTEGER,
            actor_name TEXT,
            actor_avatar TEXT,
            action_type TEXT NOT NULL,
            post_id INTEGER,
            comment_id INTEGER,
            message TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """)

        # 10. Reports Table (Content Moderation)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            details TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
        """)

        # 11. Groups Table
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT DEFAULT '🩺',
            category TEXT DEFAULT 'general',
            members_count INTEGER DEFAULT 1,
            is_private INTEGER DEFAULT 0,
            created_by INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """)

        # 12. Group Members Table
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

        # 13. Events Table
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            date_time TEXT NOT NULL,
            location TEXT NOT NULL,
            interested_count INTEGER DEFAULT 0,
            created_by INTEGER DEFAULT 1,
            created_at TEXT
        )
        """)

        # 14. Event Attendees Table
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_event_attendees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'interested',
            created_at TEXT NOT NULL,
            UNIQUE(event_id, user_id)
        )
        """)

        # Performance Indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON community_posts(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_privacy ON community_posts(privacy)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_group ON community_posts(group_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_page ON community_posts(page_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_comments_post ON community_comments(post_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_likes_post ON community_likes(post_id, user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_friends_sender ON community_friends(sender_id, status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_friends_receiver ON community_friends(receiver_id, status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_notifs_user ON community_notifications(user_id, is_read)")

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
                ("مؤتمر الطب البيطري العربي للحيوانات الأليفة 2026", "المؤتمر العلمي السنوي لمناقشة أحدث المستجدات في طب وجراحة الحيوانات الأليفة", "الخميس 12 نوفمبر • 10:00 ص", "مركز المؤتمرات - القاهرة & بث مباشر", 87),
                ("ويبينار: التحديثات العالمية في علاج مغص الخيول الحاد", "ندوة سريرية تفاعلية حول التشخيص المبكر والتدخل الجراحي والدوائي لحالات المغص", "الإثنين 16 نوفمبر • 08:00 م", "Zoom Webinar Online", 134),
                ("ورشة عمل: قراءة وفحص السونار البطني للحوامل في الأبقار", "تدريب تطبيقي على تشخيص العشار وتحديد جنس الجنين وأمراض الجهاز التناسلي", "السبت 21 نوفمبر • 02:00 م", "مستشفى الطب البيطري التعليمي", 62)
            ]
            for e_title, e_desc, e_dt, e_loc, e_int in demo_events:
                c.execute("INSERT INTO community_events (title, description, date_time, location, interested_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                          (e_title, e_desc, e_dt, e_loc, e_int, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        # Seed pages if empty
        c.execute("SELECT count(*) FROM community_pages")
        if c.fetchone()[0] == 0:
            demo_pages = [
                ("مستشفى العاصمة البيطري التخصصي", "hospital", "مستشفى بيطري متكامل مجهز بأحدث غرف العمليات الجراحية والرعاية المركزة ووحدة الأشعة المقطعية.", "01000000001", "info@capital-vet.com", "القاهرة الجديدة", 1, 312),
                ("مركز ألفا لتشخيص وطب الخيول", "clinic", "مركز رائد في الفحص بالأمواج فوق الصوتية، المناظير، وتأهيل خيول السباق والقفز.", "01000000002", "alpha@equine-vet.com", "الجيزة - مصر", 1, 245),
                ("مختبر بايوفيت للتحاليل الجزيئية PCR", "lab", "أدق التحاليل البيطرية، تشخيص الأمراض الوبائية والفيروسية، وفحص السموم الفطرية.", "01000000003", "lab@biovet.org", "الإسكندرية", 1, 189),
                ("الجمعية الطبية البيطرية للحيوانات الأليفة", "syndicate", "منظمة علمية مهنية تهدف إلى ترقية المعايير الإكلينيكية لطب الحيوانات الصغيرة والتبادل العلمي.", "01000000004", "contact@vetsociety.org", "مصر والشرق الأوسط", 1, 520)
            ]
            for p_name, p_cat, p_desc, p_ph, p_em, p_city, p_ver, p_fol in demo_pages:
                c.execute("""
                INSERT INTO community_pages (name, category, description, phone, email, city, is_verified, followers_count, owner_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (p_name, p_cat, p_desc, p_ph, p_em, p_city, p_ver, p_fol, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        conn.close()
    except Exception as e:
        print("Schema init notice:", e)

init_community_schema()

# Social Graph & Privacy Helpers
def get_user_friends_ids(user_id: int, conn) -> set:
    if not user_id:
        return set()
    c = conn.cursor()
    c.execute("""
    SELECT CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS friend_id
    FROM community_friends
    WHERE (sender_id = ? OR receiver_id = ?) AND status = 'accepted'
    """, (user_id, user_id, user_id))
    return set(r[0] for r in c.fetchall())

def is_friend(user_a: int, user_b: int, conn) -> bool:
    if not user_a or not user_b or user_a == user_b:
        return False
    c = conn.cursor()
    c.execute("""
    SELECT id FROM community_friends
    WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
      AND status = 'accepted'
    """, (user_a, user_b, user_b, user_a))
    return bool(c.fetchone())

def get_friendship_info(viewer_id: int, target_id: int, conn) -> dict:
    if not viewer_id or not target_id or viewer_id == target_id:
        return {"status": "self", "request_id": None}
    c = conn.cursor()
    c.execute("""
    SELECT id, sender_id, receiver_id, status FROM community_friends
    WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
    """, (viewer_id, target_id, target_id, viewer_id))
    row = c.fetchone()
    if not row:
        return {"status": "none", "request_id": None}
    status = row["status"]
    if status == "accepted":
        return {"status": "friends", "request_id": row["id"]}
    if status == "pending":
        if row["sender_id"] == viewer_id:
            return {"status": "outgoing_pending", "request_id": row["id"]}
        else:
            return {"status": "incoming_pending", "request_id": row["id"]}
    return {"status": "none", "request_id": None}

def get_blocked_user_ids(user_id: int, conn) -> set:
    if not user_id:
        return set()
    c = conn.cursor()
    c.execute("""
    SELECT blocked_id FROM community_blocks WHERE blocker_id = ?
    UNION
    SELECT blocker_id FROM community_blocks WHERE blocked_id = ?
    """, (user_id, user_id))
    return set(r[0] for r in c.fetchall())

def create_notification(conn, user_id: int, actor_id: int, actor_name: str, actor_avatar: str, action_type: str, message: str, post_id: int = None, comment_id: int = None):
    if not user_id or user_id == actor_id:
        return
    try:
        c = conn.cursor()
        c.execute("""
        INSERT INTO community_notifications (
            user_id, actor_id, actor_name, actor_avatar, action_type, post_id, comment_id, message, is_read, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (user_id, actor_id, actor_name, actor_avatar, action_type, post_id, comment_id, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print("create_notification error:", e)

def get_unread_notifications_count(user_id: int, conn) -> int:
    if not user_id:
        return 0
    c = conn.cursor()
    c.execute("SELECT count(*) FROM community_notifications WHERE user_id = ? AND is_read = 0", (user_id,))
    return c.fetchone()[0]

def get_incoming_friend_requests_count(user_id: int, conn) -> int:
    if not user_id:
        return 0
    c = conn.cursor()
    c.execute("SELECT count(*) FROM community_friends WHERE receiver_id = ? AND status = 'pending'", (user_id,))
    return c.fetchone()[0]

def can_view_post(post: dict, viewer_id: int, friends_set: set, is_admin: bool) -> bool:
    if is_admin or post.get("user_id") == viewer_id:
        return True
    privacy = post.get("privacy", "public")
    if privacy == "only_me":
        return False
    if privacy == "friends":
        return post.get("user_id") in friends_set
    return True

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

def format_media_url(path: str) -> str:
    if not path:
        return ""
    path = str(path).strip()
    if path.startswith("data:") or path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("/static/uploads/"):
        return path.replace("/static/uploads/", "/uploads/")
    if path.startswith("static/uploads/"):
        return "/" + path.replace("static/uploads/", "uploads/")
    if path.startswith("/uploads/"):
        return path
    if path.startswith("uploads/"):
        return "/" + path
    if path.startswith("/"):
        return path
    return f"/uploads/{path}"

def parse_extra_images(raw: str) -> list:
    if not raw:
        return []
    raw = str(raw).strip()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            items = json.loads(raw)
            if isinstance(items, list):
                return [str(x).strip() for x in items if str(x).strip()]
        except Exception:
            pass
    if "|||" in raw:
        return [x.strip() for x in raw.split("|||") if x.strip()]
    if raw.startswith("data:"):
        return [raw]
    return [x.strip() for x in raw.split(",") if x.strip()]

def extract_youtube_embed(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if "youtu.be/" in url:
        vid_id = url.split("youtu.be/")[1].split("?")[0].split("&")[0].split("/")[0]
        return f"https://www.youtube.com/embed/{vid_id}"
    if "youtube.com/shorts/" in url:
        vid_id = url.split("youtube.com/shorts/")[1].split("?")[0].split("&")[0].split("/")[0]
        return f"https://www.youtube.com/embed/{vid_id}"
    if "watch?v=" in url:
        vid_id = url.split("watch?v=")[1].split("&")[0].split("#")[0]
        return f"https://www.youtube.com/embed/{vid_id}"
    if "youtube.com/embed/" in url:
        return url.split("?")[0]
    return url

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
   VETBOOK - COMPREHENSIVE VETERINARY SOCIAL NETWORK DESIGN SYSTEM (FACEBOOK UX)
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
    --fb-font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
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
    max-width: 100%;
}

body {
    letter-spacing: 0 !important;
}

.fb-app-wrapper {
    background-color: var(--fb-bg);
    min-height: 100vh;
    padding-bottom: 90px;
    max-width: 100vw !important;
    width: 100% !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
}

/* Sub-Navigation Strip (Facebook-Style Tabs with Real Badges) */
.vetbook-subnav-strip {
    background: var(--fb-card);
    border-bottom: 1px solid var(--fb-border);
    position: sticky;
    top: 56px;
    z-index: 100;
    padding: 8px 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    overflow-x: auto !important;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    max-width: 100vw !important;
    box-sizing: border-box !important;
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
    position: relative;
}
.vetbook-nav-pill:hover {
    background: rgba(15, 118, 110, 0.08);
    color: var(--fb-primary);
}
.vetbook-nav-pill.active {
    background: var(--fb-primary);
    color: #ffffff !important;
    border-color: var(--fb-primary);
    box-shadow: 0 2px 6px rgba(15, 118, 110, 0.25);
}
.vetbook-pill-badge {
    background: #ef4444;
    color: #ffffff;
    font-size: 0.70rem;
    font-weight: 800;
    padding: 1px 6px;
    border-radius: 9999px;
    margin-right: 4px;
}

/* VetBook Search Bar */
.vetbook-search-input {
    padding: 8px 14px 8px 36px;
    border: 1px solid var(--fb-border);
    border-radius: 24px;
    font-size: 0.85rem;
    background: var(--fb-bg);
    color: var(--fb-text);
    outline: none;
    transition: all 0.2s ease;
    width: clamp(140px, 28vw, 220px);
    max-width: 100%;
    box-sizing: border-box;
}
.vetbook-search-input:focus {
    width: clamp(160px, 36vw, 280px);
    border-color: var(--fb-primary);
    background: var(--fb-card);
    box-shadow: 0 0 0 3px rgba(15,118,110,0.15);
}

/* Main Grid Layout */
.fb-main-container {
    max-width: 1280px;
    margin: 16px auto;
    padding: 0 14px;
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr) 300px;
    gap: 20px;
    align-items: start;
}
@media (max-width: 1080px) {
    .fb-main-container {
        grid-template-columns: 1fr;
    }
    .fb-sidebar-col {
        display: none;
    }
}

/* Cards & Components */
.fb-card {
    background: var(--fb-card);
    border: 1px solid var(--fb-border);
    border-radius: 14px;
    box-shadow: var(--fb-shadow);
    overflow: hidden;
    margin-bottom: 16px;
    transition: box-shadow 0.2s ease;
}
.fb-card:hover {
    box-shadow: var(--fb-shadow-hover);
}

/* Urgent Banner */
.urgent-post-card {
    border-right: 6px solid #dc2626 !important;
}
.urgent-banner-row {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
    padding: 10px 14px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 800;
    font-size: 0.86rem;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 8px;
    width: 100%;
    box-sizing: border-box;
}
.urgent-badge {
    background: #dc2626;
    color: #ffffff;
    font-size: 0.72rem;
    padding: 3px 10px;
    border-radius: 20px;
}

/* Demographics Grid */
.case-demographics-grid {
    background: var(--fb-bg);
    border: 1px solid var(--fb-border);
    border-radius: 12px;
    padding: 12px 14px;
    margin: 12px 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 8px;
    font-size: 0.82rem;
    line-height: 1.5;
}

/* Media Grid (Facebook Style 1, 2, 3, 4 images) */
.fb-media-grid {
    margin: 12px 0;
    overflow: hidden;
    border-radius: 12px;
    border: 1px solid var(--fb-border);
    background: #000;
    position: relative;
}
.fb-media-grid.grid-1 img {
    width: 100%;
    max-height: 520px;
    object-fit: cover;
    display: block;
    cursor: pointer;
}
.fb-media-grid.grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2px;
}
.fb-media-grid.grid-2 img {
    width: 100%;
    aspect-ratio: 1/1;
    object-fit: cover;
    display: block;
    cursor: pointer;
}
.fb-media-grid.grid-3 {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 2px;
}
.fb-media-grid.grid-3 .media-col-left img {
    width: 100%;
    height: 100%;
    aspect-ratio: 1/1;
    object-fit: cover;
    display: block;
    cursor: pointer;
}
.fb-media-grid.grid-3 .media-col-right {
    display: grid;
    grid-template-rows: 1fr 1fr;
    gap: 2px;
}
.fb-media-grid.grid-3 .media-col-right img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    cursor: pointer;
}
.fb-media-grid.grid-4 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2px;
}
.fb-media-grid.grid-4 img {
    width: 100%;
    aspect-ratio: 1/1;
    object-fit: cover;
    display: block;
    cursor: pointer;
}
.media-extra-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.65);
    color: white;
    font-size: 1.8rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
}

/* Reactions Popup */
.reactions-popup-box {
    position: absolute;
    bottom: calc(100% + 6px);
    right: 0;
    background: var(--fb-card);
    border: 1px solid var(--fb-border);
    border-radius: 30px;
    padding: 6px 10px;
    display: none;
    align-items: center;
    gap: 8px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    z-index: 50;
    animation: scaleIn 0.15s ease-out;
}
@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.85); }
    to { opacity: 1; transform: scale(1); }
}
.reaction-emoji-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    transition: transform 0.15s ease;
    padding: 2px 4px;
}
.reaction-emoji-btn:hover {
    transform: scale(1.35);
}

/* Post Actions Bar */
.fb-action-btn {
    flex: 1 1 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    padding: 8px 6px;
    font-size: clamp(0.74rem, 2.3vw, 0.88rem);
    font-weight: 700;
    border-radius: 8px;
    border: none;
    background: none;
    cursor: pointer;
    color: var(--fb-text-muted);
    transition: all 0.15s ease;
    min-width: 0;
    white-space: normal;
    word-break: break-word;
    text-align: center;
}
.fb-action-btn:hover {
    background: rgba(15, 118, 110, 0.08);
    color: var(--fb-primary);
}

/* Threaded Comments & Nested Replies */
.fb-comment-bubble {
    background: var(--fb-bg);
    border: 1px solid var(--fb-border);
    border-radius: 14px;
    padding: 10px 14px;
    font-size: 0.88rem;
    color: var(--fb-text);
    line-height: 1.6;
    word-break: break-word;
}
.best-answer-bubble {
    border: 2px solid #10b981 !important;
    background: #ecfdf5 !important;
}
.nested-reply-box {
    margin-right: 36px;
    margin-top: 8px;
    border-right: 2px solid var(--fb-border);
    padding-right: 12px;
}

/* Stories Strip */
.stories-strip {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding-bottom: 8px;
    margin-bottom: 16px;
    scrollbar-width: none;
}
.stories-strip::-webkit-scrollbar { display: none; }
.story-card {
    min-width: 110px;
    height: 170px;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    cursor: pointer;
    background: #0f172a;
    flex-shrink: 0;
    transition: transform 0.2s ease;
    box-shadow: var(--fb-shadow);
}
.story-card:hover {
    transform: translateY(-2px);
}
.story-card img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.85;
}

/* Friends Grid */
.friend-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr));
    gap: 14px;
}
.friend-card {
    background: var(--fb-card);
    border: 1px solid var(--fb-border);
    border-radius: 12px;
    overflow: hidden;
    padding: 14px;
    text-align: center;
    box-shadow: var(--fb-shadow);
    transition: all 0.2s ease;
}
.friend-card:hover {
    box-shadow: var(--fb-shadow-hover);
    transform: translateY(-2px);
}
.friend-avatar-circle {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: var(--fb-primary);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    font-weight: 800;
    margin-bottom: 10px;
    object-fit: cover;
    border: 3px solid #fff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* Pages & Groups Cards */
.page-card-grid, .group-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 250px), 1fr));
    gap: 16px;
}
.page-card, .group-card {
    background: var(--fb-card);
    border: 1px solid var(--fb-border);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: var(--fb-shadow);
    transition: all 0.2s ease;
}
.page-card:hover, .group-card:hover {
    box-shadow: var(--fb-shadow-hover);
    transform: translateY(-2px);
}

/* Notifications List */
.notif-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--fb-border);
    transition: background 0.15s ease;
    text-decoration: none;
    color: inherit;
}
.notif-item:hover {
    background: rgba(15, 118, 110, 0.04);
}
.notif-item.unread {
    background: rgba(15, 118, 110, 0.08);
}
.notif-unread-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #0f766e;
    flex-shrink: 0;
}

/* Modals */
.fb-modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6);
    z-index: 9999;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 14px;
}
.fb-modal-box {
    background: var(--fb-card);
    border-radius: 16px;
    width: 100%;
    max-width: 620px;
    max-height: 90vh;
    overflow-y: auto;
    padding: 20px;
    box-shadow: 0 16px 40px rgba(0,0,0,0.3);
    border: 1px solid var(--fb-border);
    animation: modalPop 0.2s ease-out;
}
@keyframes modalPop {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
}

/* Profile Header */
.fb-profile-cover {
    height: 220px;
    width: 100%;
    background-size: cover;
    background-position: center;
    position: relative;
}
.fb-profile-header-body {
    padding: 0 24px 20px 24px;
    position: relative;
}
.profile-header-avatar-row {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-top: -60px;
    margin-bottom: 14px;
    flex-wrap: wrap;
    gap: 12px;
}
.profile-header-avatar {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    border: 4px solid var(--fb-card);
    background: var(--fb-primary);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.8rem;
    font-weight: 800;
    box-shadow: 0 4px 14px rgba(0,0,0,0.18);
    object-fit: cover;
}

/* Buttons */
.btn-fb-primary {
    background: var(--fb-primary);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 9px 18px;
    font-weight: 700;
    cursor: pointer;
    font-size: 0.88rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
    transition: background 0.15s ease;
}
.btn-fb-primary:hover {
    background: var(--fb-primary-hover);
}
.btn-fb-outline {
    background: none;
    color: var(--fb-text);
    border: 1px solid var(--fb-border);
    border-radius: 10px;
    padding: 9px 18px;
    font-weight: 700;
    cursor: pointer;
    font-size: 0.88rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
    transition: all 0.15s ease;
}
.btn-fb-outline:hover {
    background: var(--fb-bg);
    border-color: var(--fb-text-muted);
}
.btn-fb-danger {
    background: #dc2626;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 700;
    cursor: pointer;
    font-size: 0.82rem;
}

/* Responsive adjustments for VetBook on all viewports */
@media (max-width: 768px) {
    .fb-main-container {
        padding: 0 8px;
        margin: 10px auto;
        gap: 12px;
    }
    .fb-card {
        border-radius: 12px;
        margin-bottom: 12px;
    }
    .fb-action-btn {
        padding: 6px 3px !important;
        font-size: 0.74rem !important;
        gap: 3px !important;
    }
    .nested-reply-box {
        margin-right: 14px !important;
        padding-right: 8px !important;
    }
    .profile-header-avatar {
        width: 84px !important;
        height: 84px !important;
        font-size: 1.8rem !important;
        margin-top: -42px !important;
    }
    .fb-profile-header-body {
        padding: 0 14px 16px 14px !important;
    }
}
@media (max-width: 480px) {
    .vetbook-subnav-strip {
        padding: 6px 8px !important;
        gap: 6px !important;
    }
    .vetbook-nav-pill {
        padding: 6px 10px !important;
        font-size: 0.80rem !important;
    }
    .fb-action-btn {
        padding: 5px 2px !important;
        font-size: 0.70rem !important;
        gap: 2px !important;
    }
    .fb-action-btn span:last-child {
        font-size: 0.69rem !important;
    }
    .case-demographics-grid {
        grid-template-columns: 1fr !important;
    }
    .profile-header-avatar-row {
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }
    .profile-header-avatar {
        margin: -40px auto 10px auto !important;
    }
}
@media (max-width: 360px) {
    .fb-action-btn {
        padding: 4px 1px !important;
        font-size: 0.65rem !important;
        gap: 1px !important;
    }
    .fb-action-btn span:last-child {
        font-size: 0.64rem !important;
    }
    .profile-header-avatar {
        width: 64px !important;
        height: 64px !important;
        font-size: 1.4rem !important;
        margin-top: -32px !important;
    }
}
@media (max-width: 340px) {
    .fb-main-container {
        padding: 0 4px !important;
        margin: 6px auto !important;
    }
    .fb-card {
        padding: 10px 8px !important;
        border-radius: 10px !important;
        margin-bottom: 10px !important;
    }
    .fb-action-btn {
        padding: 4px 1px !important;
        font-size: 0.60rem !important;
        gap: 1px !important;
    }
    .fb-action-btn span:last-child {
        font-size: 0.58rem !important;
    }
}
</style>
"""



COMMUNITY_JS = """
<script>
// ==============================================================================
// VETBOOK CLIENT INTERACTIVITY & SOCIAL LOGIC (STRICT NO-MESSENGER, ZERO AI)
// ==============================================================================

function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'flex';
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
}

// Media Modal
function openImageModal(src) {
    const m = document.getElementById('image-modal');
    const img = document.getElementById('image-modal-src');
    if (m && img) {
        img.src = src;
        m.style.display = 'flex';
    }
}

// Reactions System
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
        console.error(e);
    }
}

// Comments & Nested Replies
function focusCommentInput(postId) {
    const inp = document.getElementById('comment-input-' + postId);
    if (inp) {
        inp.focus();
        inp.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
        console.error(err);
    }
}

async function deleteComment(commentId) {
    if (!confirm('هل تريد بالتأكيد حذف هذا الرأي أو التعليق السريري؟')) return;
    try {
        const res = await fetch('/community/comment/delete/' + commentId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            const el = document.getElementById('comment-' + commentId);
            if (el) el.remove();
        }
    } catch (e) {
        console.error(e);
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
        console.error(e);
    }
}

// Post Actions: Edit, Delete, Share, Bookmark
function openEditPostModal(postId) {
    openModal('edit-post-modal-' + postId);
}

let currentViewerStoryId = null;

function openStoryViewerFromCard(cardEl) {
    if (!cardEl) return;
    const sId = cardEl.getAttribute('data-story-id');
    const sUrl = cardEl.getAttribute('data-story-url');
    const sAuthor = cardEl.getAttribute('data-story-author');
    const sCaption = cardEl.getAttribute('data-story-caption');
    const sTime = cardEl.getAttribute('data-story-time');
    const sLikes = cardEl.getAttribute('data-story-likes') || '0';
    const isOwner = cardEl.getAttribute('data-is-owner') === '1';

    currentViewerStoryId = sId;

    const modal = document.getElementById('story-viewer-modal');
    if (!modal) return;

    // Set author info
    const authorEl = document.getElementById('story-viewer-author');
    if (authorEl) authorEl.innerText = 'د. ' + (sAuthor || 'طبيب بيطري');

    const timeEl = document.getElementById('story-viewer-time');
    if (timeEl) timeEl.innerText = sTime || 'اليوم';

    // Set caption (الكلام أسفل القصة)
    const captionBox = document.getElementById('story-viewer-caption-box');
    const captionText = document.getElementById('story-viewer-caption-text');
    if (sCaption && sCaption.trim()) {
        if (captionText) captionText.innerText = sCaption;
        if (captionBox) captionBox.style.display = 'block';
    } else {
        if (captionBox) captionBox.style.display = 'none';
    }

    // Set Likes count
    const likesEl = document.getElementById('story-viewer-likes-count');
    if (likesEl) likesEl.innerText = sLikes;

    // Owner delete button
    const delBtn = document.getElementById('story-viewer-del-btn');
    if (delBtn) delBtn.style.display = isOwner ? 'inline-flex' : 'none';

    // Media
    const mediaContainer = document.getElementById('story-viewer-media-container');
    if (mediaContainer) {
        const isVideo = sUrl.endsWith('.mp4') || sUrl.endsWith('.webm') || sUrl.startsWith('data:video');
        if (isVideo) {
            mediaContainer.innerHTML = `<video controls autoplay playsinline src="${sUrl}" style="max-height: 65vh; max-width: 100%; border-radius: 12px; object-fit: contain; background: #000; box-shadow: 0 4px 20px rgba(0,0,0,0.5);"></video>`;
        } else {
            mediaContainer.innerHTML = `<img src="${sUrl}" alt="Story" style="max-height: 65vh; max-width: 100%; border-radius: 12px; object-fit: contain; box-shadow: 0 4px 20px rgba(0,0,0,0.5);" onerror="this.src='/static/favicon.svg'">`;
        }
    }

    modal.style.display = 'flex';
}

function openStoryViewer(src, author, caption) {
    // Backward compatibility shim
    openStoryViewerFromCard({
        getAttribute: (k) => {
            if (k === 'data-story-url') return src;
            if (k === 'data-story-author') return author || 'طبيب بيطري';
            if (k === 'data-story-caption') return caption || '';
            if (k === 'data-story-likes') return '0';
            if (k === 'data-is-owner') return '0';
            return '';
        }
    });
}

function closeStoryViewer() {
    const modal = document.getElementById('story-viewer-modal');
    if (modal) {
        modal.style.display = 'none';
        const mediaContainer = document.getElementById('story-viewer-media-container');
        if (mediaContainer) mediaContainer.innerHTML = '';
    }
}

async function likeCurrentStory() {
    if (!currentViewerStoryId) return;
    try {
        const res = await fetch('/community/story/like/' + currentViewerStoryId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            const likesEl = document.getElementById('story-viewer-likes-count');
            if (likesEl) likesEl.innerText = data.likes_count;

            const card = document.querySelector(`.story-card[data-story-id="${currentViewerStoryId}"]`);
            if (card) {
                card.setAttribute('data-story-likes', data.likes_count);
                const countSpan = card.querySelector('div span:last-child');
                if (countSpan) countSpan.innerText = data.likes_count;
            }

            const heartBtn = document.getElementById('story-like-btn');
            if (heartBtn) {
                heartBtn.style.transform = 'scale(1.25)';
                setTimeout(() => { heartBtn.style.transform = 'scale(1)'; }, 200);
            }
        }
    } catch (e) {
        console.error(e);
    }
}

async function sendStoryReaction(reactionText) {
    if (!currentViewerStoryId) return;
    await likeCurrentStory();
    const toast = document.createElement('div');
    toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#0f766e;color:#fff;padding:8px 18px;border-radius:20px;font-size:0.85rem;font-weight:700;z-index:999999;box-shadow:0 4px 15px rgba(0,0,0,0.3);';
    toast.innerText = 'تم إرسال تفاعلك: ' + reactionText;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
}

async function deleteCurrentStory() {
    if (!currentViewerStoryId) return;
    if (!confirm('هل تريد بالتأكيد حذف هذه القصة السريرية الآن؟')) return;
    try {
        const res = await fetch('/community/story/delete/' + currentViewerStoryId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            closeStoryViewer();
            const card = document.querySelector(`.story-card[data-story-id="${currentViewerStoryId}"]`);
            if (card) card.remove();
        } else {
            alert(data.error || 'حدث خطأ أثناء حذف القصة');
        }
    } catch (e) {
        console.error(e);
    }
}

async function deletePost(postId) {
    if (!confirm('هل تريد بالتأكيد حذف هذه الحالة السريرية نهائياً من المنصة والشبكة؟')) return;
    const postEl = document.getElementById('post-' + postId);
    if (postEl) {
        postEl.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
        postEl.style.opacity = '0.3';
    }
    try {
        const postTitle = postEl ? (postEl.querySelector('.post-heading, h3, strong')?.innerText || '').trim() : '';
        const res = await fetch('/community/post/delete/' + postId, {
            method: 'POST',
            headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json().catch(() => ({ success: res.ok }));
        if (!res.ok || (data && data.success === false)) {
            alert(data.error || 'حدث خطأ أثناء محاولة حذف المنشور من الخادم.');
            if (postEl) postEl.style.opacity = '1';
            return;
        }

        // Scrub from client-side localStorage so it can NEVER sync back:
        try {
            let myPosts = JSON.parse(localStorage.getItem('vetbook_my_posts') || '[]');
            myPosts = myPosts.filter(p => p.id !== postId && (!postTitle || p.title !== postTitle));
            localStorage.setItem('vetbook_my_posts', JSON.stringify(myPosts));

            let deletedList = JSON.parse(localStorage.getItem('vetbook_deleted_posts') || '[]');
            if (!deletedList.includes(postId)) deletedList.push(postId);
            if (postTitle && !deletedList.includes(postTitle)) deletedList.push(postTitle);
            localStorage.setItem('vetbook_deleted_posts', JSON.stringify(deletedList));
        } catch (e) {}

        if (postEl) {
            postEl.style.transform = 'scale(0.95)';
            setTimeout(() => { postEl.remove(); }, 250);
        } else {
            location.reload();
        }
    } catch (err) {
        console.error('Delete post error:', err);
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/community/post/delete/' + postId;
        document.body.appendChild(form);
        form.submit();
    }
}

async function sharePost(postId) {
    const url = window.location.origin + '/community#post-' + postId;
    if (navigator.clipboard) {
        navigator.clipboard.writeText(url);
    }
    try {
        await fetch('/community/post/share/' + postId, { method: 'POST' });
        const countEl = document.getElementById('shares-count-' + postId);
        if (countEl) {
            let cur = parseInt(countEl.innerText) || 0;
            countEl.innerText = (cur + 1) + ' مشاركة';
        }
    } catch (e) {}
    alert('🔗 تم نسخ رابط الحالة بنجاح ونشرها بين الزملاء!');
}

async function togglePostBookmark(postId) {
    try {
        const res = await fetch('/community/bookmark/' + postId, { method: 'POST' });
        const data = await res.json();
        const btn = document.getElementById('bookmark-btn-' + postId);
        const txt = document.getElementById('bookmark-text-' + postId);
        if (data.success && btn && txt) {
            if (data.bookmarked) {
                btn.style.color = '#d97706';
                btn.style.fontWeight = '800';
                txt.innerText = 'محفوظة 🔖';
            } else {
                btn.style.color = 'var(--fb-text-muted)';
                btn.style.fontWeight = '400';
                txt.innerText = 'حفظ 🔖';
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Social Graph Actions (Friends & Follows)
async function sendFriendRequest(targetId, btn) {
    try {
        btn.disabled = true;
        const res = await fetch('/community/friends/request/' + targetId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            btn.innerText = '⏳ تم إرسال الطلب';
            btn.style.background = '#e2e8f0';
            btn.style.color = '#475569';
        } else {
            alert(data.error || 'تعذر إرسال الطلب');
            btn.disabled = false;
        }
    } catch (e) {
        console.error(e);
        btn.disabled = false;
    }
}

async function acceptFriendRequest(requestId, btn) {
    try {
        btn.disabled = true;
        const res = await fetch('/community/friends/accept/' + requestId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            btn.closest('.friend-request-row, .friend-card').remove();
            alert('🎉 تم قبول طلب الصداقة وأصبح الزميل في شبكتك المهنية!');
        }
    } catch (e) {
        console.error(e);
    }
}

async function rejectFriendRequest(requestId, btn) {
    try {
        btn.disabled = true;
        const res = await fetch('/community/friends/reject/' + requestId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            btn.closest('.friend-request-row, .friend-card').remove();
        }
    } catch (e) {
        console.error(e);
    }
}

async function cancelFriendRequest(targetId, btn) {
    if (!confirm('هل تريد إلغاء طلب الصداقة المرسل؟')) return;
    try {
        const res = await fetch('/community/friends/cancel/' + targetId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            location.reload();
        }
    } catch (e) {
        console.error(e);
    }
}

async function removeFriend(targetId) {
    if (!confirm('هل تريد بالتأكيد إلغاء الصداقة مع هذا الزميل؟')) return;
    try {
        const res = await fetch('/community/friends/remove/' + targetId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            location.reload();
        }
    } catch (e) {
        console.error(e);
    }
}

async function toggleFollow(targetId, btn) {
    try {
        const res = await fetch('/community/follow/' + targetId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            if (data.following) {
                btn.innerText = '🔕 إلغاء المتابعة';
                btn.style.background = '#e2e8f0';
                btn.style.color = '#334155';
            } else {
                btn.innerText = '🔔 متابعة';
                btn.style.background = 'var(--fb-primary)';
                btn.style.color = '#ffffff';
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Reporting & Moderation
function openReportModal(targetType, targetId) {
    document.getElementById('report-target-type').value = targetType;
    document.getElementById('report-target-id').value = targetId;
    openModal('report-modal');
}

async function submitReportForm(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    try {
        const res = await fetch('/community/report', { method: 'POST', body: formData });
        const data = await res.json();
        closeModal('report-modal');
        alert(data.message || 'تم تقديم البلاغ وسيقوم فريق الإشراف بمراجعته فوراً.');
    } catch (err) {
        alert('تعذر تقديم البلاغ حالياً.');
    }
}

async function blockUser(userId) {
    if (!confirm('هل تريد حظر هذا المستخدم؟ لن تظهر منشوراته أو تعليقاته في حسابك نهائياً.')) return;
    try {
        const res = await fetch('/community/block/' + userId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert(data.blocked ? 'تم حظر المستخدم بنجاح.' : 'تم إلغاء الحظر.');
            location.reload();
        }
    } catch (e) {
        console.error(e);
    }
}

// Pages & Groups & Events
async function togglePageFollow(pageId, btn) {
    try {
        const res = await fetch('/community/pages/follow/' + pageId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            if (data.following) {
                btn.innerText = '✔️ متابع';
                btn.style.background = '#e2e8f0';
                btn.style.color = '#334155';
            } else {
                btn.innerText = '➕ متابعة الصفحة';
                btn.style.background = 'var(--fb-primary)';
                btn.style.color = '#ffffff';
            }
            const countEl = document.getElementById('page-followers-' + pageId);
            if (countEl) countEl.innerText = data.followers_count + ' متابع';
        }
    } catch (e) {
        console.error(e);
    }
}

async function joinGroup(groupId, btn) {
    try {
        const res = await fetch('/community/groups/join/' + groupId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            location.reload();
        }
    } catch (e) {
        console.error(e);
    }
}

async function leaveGroup(groupId, btn) {
    if (!confirm('هل تريد مغادرة هذه المجموعة البيطرية؟')) return;
    try {
        const res = await fetch('/community/groups/leave/' + groupId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            location.reload();
        }
    } catch (e) {
        console.error(e);
    }
}

async function toggleEventInterest(eventId, btn) {
    try {
        const res = await fetch('/community/events/interest/' + eventId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            btn.innerText = '⭐ سأحضر (' + data.interested_count + ')';
            btn.style.background = '#0f766e';
            btn.style.color = '#ffffff';
        }
    } catch (e) {
        console.error(e);
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
        console.error(e);
    }
}

// Notifications Actions
async function markNotificationRead(notifId, url) {
    try {
        await fetch('/community/notifications/mark-read/' + notifId, { method: 'POST' });
    } catch (e) {}
    if (url) window.location.href = url;
}

async function markAllNotificationsRead() {
    try {
        await fetch('/community/notifications/mark-all-read', { method: 'POST' });
        location.reload();
    } catch (e) {
        console.error(e);
    }
}

// Offline Resilience & Auto Sync Check
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('posted') === '1') {
        const toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#0f766e;color:#fff;padding:14px 24px;border-radius:12px;font-weight:700;box-shadow:0 10px 25px rgba(0,0,0,0.3);z-index:99999;display:flex;align-items:center;gap:10px;font-size:0.95rem;transition:all 0.4s ease;';
        toast.innerHTML = '<span>🎉</span><span>تم نشر حالتك وتعميمها بنجاح على كافة الأطباء المسجلين في المنصة!</span>';
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
                    privacy: formData.get('privacy') || 'public',
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
                saved = saved.filter(p => p.title !== postObj.title);
                saved.unshift(postObj);
                if (saved.length > 50) saved = saved.slice(0, 50);
                localStorage.setItem('vetbook_my_posts', JSON.stringify(saved));
            } catch (err) {
                console.warn('Local storage post backup error:', err);
            }
        });
    }

    try {
        const deletedList = JSON.parse(localStorage.getItem('vetbook_deleted_posts') || '[]');
        let localPosts = JSON.parse(localStorage.getItem('vetbook_my_posts') || '[]');
        if (deletedList.length > 0 && localPosts.length > 0) {
            localPosts = localPosts.filter(p => !deletedList.includes(p.id) && !deletedList.includes(p.title));
            localStorage.setItem('vetbook_my_posts', JSON.stringify(localPosts));
        }
        if (localPosts.length > 0) {
            fetch('/api/community/sync-posts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ posts: localPosts })
            }).catch(() => {});
        }
    } catch (e) {}

    // Live Media Preview in Composer Modal
    const mediaInput = document.getElementById('composer-media-files');
    const mediaPreview = document.getElementById('composer-media-preview');
    if (mediaInput && mediaPreview) {
        mediaInput.addEventListener('change', function() {
            mediaPreview.innerHTML = '';
            const files = Array.from(this.files || []);
            if (files.length === 0) return;
            files.forEach(f => {
                const item = document.createElement('div');
                item.style.cssText = 'position: relative; width: 68px; height: 68px; border-radius: 8px; overflow: hidden; border: 1px solid var(--fb-border); background: #000; display: inline-flex; align-items: center; justify-content: center;';
                if (f.type.startsWith('image/')) {
                    const img = document.createElement('img');
                    img.src = URL.createObjectURL(f);
                    img.style.cssText = 'width: 100%; height: 100%; object-fit: cover;';
                    item.appendChild(img);
                } else if (f.type.startsWith('video/')) {
                    item.innerHTML = '<span style="font-size: 1.6rem;">🎥</span>';
                } else {
                    item.innerHTML = '<span style="font-size: 1.6rem;">📁</span>';
                }
                mediaPreview.appendChild(item);
            });
        });
    }
});
</script>
"""



def render_facebook_media_grid(img_list: list, video_path: str = None) -> str:
    html_parts = []
    
    if video_path and str(video_path).strip():
        v_url = format_media_url(video_path)
        if "youtube.com/embed" in v_url:
            html_parts.append(f"""
            <div style="margin: 12px 0; background: #000; border-radius: 12px; overflow: hidden; width: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <iframe src="{v_url}" style="width: 100%; aspect-ratio: 16/9; border: none; display: block;" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
            </div>
            """)
        else:
            html_parts.append(f"""
            <div style="margin: 12px 0; background: #000; border-radius: 12px; overflow: hidden; width: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <video controls playsinline preload="metadata" src="{v_url}" style="width: 100%; max-height: 520px; display: block; background: #0f172a;">
                    <source src="{v_url}" type="video/mp4">
                    المتصفح لا يدعم تشغيل هذا الفيديو.
                </video>
            </div>
            """)

    clean_imgs = [format_media_url(img) for img in img_list if img and str(img).strip()]
    cnt = len(clean_imgs)
    if cnt == 0 and not html_parts:
        return ""
    elif cnt == 0:
        return "".join(html_parts)

    grid_html = ""
    if cnt == 1:
        grid_html = f"""
        <div class="fb-media-grid grid-1" onclick="openImageModal(this.src)">
            <img src="{clean_imgs[0]}" alt="Case photo" loading="lazy" onerror="this.style.display=\'none\'">
        </div>
        """
    elif cnt == 2:
        grid_html = f"""
        <div class="fb-media-grid grid-2">
            <img src="{clean_imgs[0]}" onclick="openImageModal(this.src)" loading="lazy" onerror="this.style.display=\'none\'">
            <img src="{clean_imgs[1]}" onclick="openImageModal(this.src)" loading="lazy" onerror="this.style.display=\'none\'">
        </div>
        """
    elif cnt == 3:
        grid_html = f"""
        <div class="fb-media-grid grid-3">
            <div class="media-col-left">
                <img src="{clean_imgs[0]}" onclick="openImageModal(this.src)" loading="lazy" onerror="this.style.display=\'none\'">
            </div>
            <div class="media-col-right">
                <img src="{clean_imgs[1]}" onclick="openImageModal(this.src)" loading="lazy" onerror="this.style.display=\'none\'">
                <img src="{clean_imgs[2]}" onclick="openImageModal(this.src)" loading="lazy" onerror="this.style.display=\'none\'">
            </div>
        </div>
        """
    else:
        extra = cnt - 3
        grid_html = f"""
        <div class="fb-media-grid grid-4">
            <div style="position: relative;"><img src="{clean_imgs[0]}" onclick="openImageModal(this.src)" loading="lazy" onerror="this.style.display=\'none\'"></div>
            <div style="position: relative;"><img src="{clean_imgs[1]}" onclick="openImageModal(this.src)" loading="lazy" onerror="this.style.display=\'none\'"></div>
            <div style="position: relative;"><img src="{clean_imgs[2]}" onclick="openImageModal(this.src)" loading="lazy" onerror="this.style.display=\'none\'"></div>
            <div style="position: relative;" onclick="openImageModal(this.src)">
                <img src="{clean_imgs[3]}" loading="lazy" onerror="this.style.display=\'none\'">
                {f'<div class="media-extra-overlay">+{extra}</div>' if extra > 0 else ''}
            </div>
        </div>
        """

    html_parts.append(grid_html)
    return "".join(html_parts)


@router.get("/community", response_class=HTMLResponse)
async def community_hub(
    request: Request,
    tab: str = "feed",
    q: str = "",
    category: str = "all",
    species: str = "all",
    sort: str = "smart",
    group_id: int = 0,
    page_id: int = 0
):
    from app import get_current_user, get_user_lang, get_text, get_base_html
    from vetbook_algorithms import (
        calculate_edgerank_score,
        get_trending_topics,
        get_people_you_may_know,
        get_recommended_groups
    )

    user = get_current_user(request)
    lang = get_user_lang(request)
    current_user_id = user["id"] if user else 4
    is_admin = bool(user and (user.get("is_admin") or user.get("role") == "admin"))

    conn = get_db()
    c = conn.cursor()
    sync_posts_from_backup_sync(conn)
    sync_stories_from_backup_sync(conn)

    # Social graph helpers
    friends_set = get_user_friends_ids(current_user_id, conn)
    blocked_set = get_blocked_user_ids(current_user_id, conn)
    unread_notifs_count = get_unread_notifications_count(current_user_id, conn)
    pending_friends_count = get_incoming_friend_requests_count(current_user_id, conn)

    # Stories
    c.execute("SELECT * FROM community_stories ORDER BY id DESC LIMIT 15")
    stories = [dict(r) for r in c.fetchall()]

    stories_html = """
    <div class="stories-strip">
        <div class="story-card" onclick="openModal('create-story-modal')" style="background: linear-gradient(135deg, #0f766e, #14b8a6); display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; padding: 12px; text-align: center; cursor: pointer;">
            <div style="font-size: 2rem; margin-bottom: 6px;">➕</div>
            <div style="font-size: 0.8rem; font-weight: 800;">إضافة قصة سريرية (24h)</div>
        </div>
    """
    import html as html_escape_lib
    for st in stories:
        st_url = format_media_url(st['media_url'])
        st_caption = (st.get('caption') or '').strip()
        st_author = st.get('author_name', 'طبيب بيطري')
        st_likes = st.get('likes_count', 0)
        is_owner = 1 if (st.get('user_id') == current_user_id or is_admin) else 0

        safe_caption = html_escape_lib.escape(st_caption, quote=True)
        safe_author = html_escape_lib.escape(st_author, quote=True)
        safe_url = html_escape_lib.escape(st_url, quote=True)

        caption_preview = f"<div class='story-caption-preview' style='font-size: 0.72rem; color: #f1f5f9; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px;'>{html_escape_lib.escape(st_caption[:25])}</div>" if st_caption else ""

        stories_html += f"""
        <div class="story-card" 
             data-story-id="{st['id']}"
             data-story-url="{safe_url}"
             data-story-author="{safe_author}"
             data-story-caption="{safe_caption}"
             data-story-time="{st.get('created_at', '')[:16]}"
             data-story-likes="{st_likes}"
             data-is-owner="{is_owner}"
             onclick="openStoryViewerFromCard(this)"
             style="cursor: pointer; position: relative;">
            <img src="{st_url}" alt="Story" onerror="this.src=\'/static/favicon.svg\'">
            <div style="position: absolute; bottom: 0; left: 0; right: 0; padding: 18px 8px 8px 8px; background: linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.45) 60%, transparent 100%); color: white; line-height: 1.25;">
                <div style="font-size: 0.78rem; font-weight: 800; text-shadow: 0 1px 3px rgba(0,0,0,0.8); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    د. {safe_author}
                </div>
                {caption_preview}
                <div style="display: flex; align-items: center; gap: 4px; font-size: 0.68rem; color: #fca5a5; font-weight: 700; margin-top: 3px;">
                    <span>❤️</span> <span>{st_likes}</span>
                </div>
            </div>
        </div>
        """
    stories_html += "</div>"

    # Search Mode Check
    if q and q.strip():
        tab = "search"

    # Tab Badges
    notif_badge_html = f'<span class="vetbook-pill-badge">{unread_notifs_count}</span>' if unread_notifs_count > 0 else ""
    friends_badge_html = f'<span class="vetbook-pill-badge">{pending_friends_count}</span>' if pending_friends_count > 0 else ""

    # Sub-Navigation Strip (Facebook Tabs)
    subnav_strip = f"""
    <div class="vetbook-subnav-strip">
        <a href="/community" class="vetbook-nav-pill {'active' if tab == 'feed' else ''}"><span>📰</span> <span>الموجز العام</span></a>
        <a href="/community?tab=my_posts" class="vetbook-nav-pill {'active' if tab == 'my_posts' else ''}"><span>📢</span> <span>منشوراتي</span></a>
        <a href="/community?tab=friends" class="vetbook-nav-pill {'active' if tab == 'friends' else ''}"><span>👥</span> <span>الأصدقاء والزملاء {friends_badge_html}</span></a>
        <a href="/community?tab=pages" class="vetbook-nav-pill {'active' if tab == 'pages' else ''}"><span>🏢</span> <span>الصفحات البيطرية</span></a>
        <a href="/community?tab=groups" class="vetbook-nav-pill {'active' if tab == 'groups' else ''}"><span>🐾</span> <span>المجموعات</span></a>
        <a href="/community?tab=events" class="vetbook-nav-pill {'active' if tab == 'events' else ''}"><span>🎓</span> <span>الفعاليات</span></a>
        <a href="/community?tab=notifications" class="vetbook-nav-pill {'active' if tab == 'notifications' else ''}"><span>🔔</span> <span>الإشعارات {notif_badge_html}</span></a>
        <a href="/community?category=bookmarks" class="vetbook-nav-pill {'active' if (category == 'bookmarks' or tab == 'saved') else ''}"><span>🔖</span> <span>المحفوظات</span></a>
        <a href="/community/profile/{current_user_id}" class="vetbook-nav-pill"><span>👤</span> <span>ملفي الشخصي</span></a>
        {f'<a href="/community?tab=moderation" class="vetbook-nav-pill ' + ('active' if tab == 'moderation' else '') + '"><span>🛡️</span> <span>الإشراف</span></a>' if is_admin else ''}
        
        <form action="/community" method="GET" style="margin-right: auto; display: flex; align-items: center; position: relative;">
            <input type="hidden" name="tab" value="search">
            <span style="position: absolute; right: 12px; font-size: 0.9rem; pointer-events: none; color: var(--fb-text-muted);">🔍</span>
            <input type="text" name="q" value="{q}" placeholder="بحث في VetBook..." class="vetbook-search-input">
        </form>
    </div>
    """

    # TAB 1: FRIENDS TAB (الأصدقاء والزملاء)
    if tab == "friends":
        # Incoming pending requests
        c.execute("""
        SELECT f.id as request_id, f.created_at, u.id as user_id, u.name, u.role, u.specialty, u.clinic_name, u.avatar_image, u.country
        FROM community_friends f
        JOIN users u ON f.sender_id = u.id
        WHERE f.receiver_id = ? AND f.status = 'pending'
        ORDER BY f.id DESC
        """, (current_user_id,))
        incoming_requests = [dict(r) for r in c.fetchall()]

        # Outgoing sent requests
        c.execute("""
        SELECT f.id as request_id, f.created_at, u.id as user_id, u.name, u.role, u.specialty, u.clinic_name, u.avatar_image, u.country
        FROM community_friends f
        JOIN users u ON f.receiver_id = u.id
        WHERE f.sender_id = ? AND f.status = 'pending'
        ORDER BY f.id DESC
        """, (current_user_id,))
        outgoing_requests = [dict(r) for r in c.fetchall()]

        # My Friends List
        c.execute("""
        SELECT u.id as user_id, u.name, u.role, u.specialty, u.clinic_name, u.avatar_image, u.country
        FROM users u
        WHERE u.id IN (
            SELECT CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END
            FROM community_friends
            WHERE (sender_id = ? OR receiver_id = ?) AND status = 'accepted'
        )
        ORDER BY u.name ASC
        """, (current_user_id, current_user_id, current_user_id))
        friends_list = [dict(r) for r in c.fetchall()]

        # Suggested Colleagues (PYMK)
        c.execute("""
        SELECT id, name, role, specialty, clinic_name, avatar_image, country
        FROM users
        WHERE id != ? AND id NOT IN (
            SELECT receiver_id FROM community_friends WHERE sender_id = ?
            UNION
            SELECT sender_id FROM community_friends WHERE receiver_id = ?
        )
        LIMIT 8
        """, (current_user_id, current_user_id, current_user_id))
        suggested_doctors = [dict(r) for r in c.fetchall()]
        conn.close()

        incoming_html = ""
        if incoming_requests:
            for req in incoming_requests:
                av = f'<img src="/uploads/{req["avatar_image"]}" class="friend-avatar-circle">' if req.get("avatar_image") else f'<div class="friend-avatar-circle">{req["name"][0]}</div>'
                incoming_html += f"""
                <div class="friend-card">
                    {av}
                    <div style="font-weight: 800; font-size: 1.05rem; color: var(--fb-text); margin-bottom: 2px;">د. {req['name']}</div>
                    <div style="font-size: 0.8rem; color: var(--fb-primary); font-weight: 700;">{req.get('specialty') or 'طبيب بيطري'}</div>
                    <div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-top: 4px;">{req.get('clinic_name') or ''} • {req.get('country') or 'مصر'}</div>
                    <div style="display: flex; gap: 8px; justify-content: center; margin-top: 14px;">
                        <button type="button" onclick="acceptFriendRequest({req['request_id']}, this)" class="btn-fb-primary" style="flex: 1; justify-content: center;">قبول ✔️</button>
                        <button type="button" onclick="rejectFriendRequest({req['request_id']}, this)" class="btn-fb-outline" style="flex: 1; justify-content: center;">رفض ✕</button>
                    </div>
                </div>
                """
        else:
            incoming_html = "<div style='color: var(--fb-text-muted); padding: 12px; font-size: 0.9rem;'>لا توجد طلبات صداقة واردة جديدة حالياً.</div>"

        friends_cards_html = ""
        if friends_list:
            for fr in friends_list:
                av = f'<img src="/uploads/{fr["avatar_image"]}" class="friend-avatar-circle">' if fr.get("avatar_image") else f'<div class="friend-avatar-circle">{fr["name"][0]}</div>'
                friends_cards_html += f"""
                <div class="friend-card">
                    {av}
                    <div style="font-weight: 800; font-size: 1.05rem; color: var(--fb-text); margin-bottom: 2px;">د. {fr['name']}</div>
                    <div style="font-size: 0.8rem; color: var(--fb-primary); font-weight: 700;">{fr.get('specialty') or 'طبيب بيطري'}</div>
                    <div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-top: 4px;">{fr.get('clinic_name') or ''}</div>
                    <div style="display: flex; gap: 8px; justify-content: center; margin-top: 14px;">
                        <a href="/community/profile/{fr['user_id']}" class="btn-fb-outline" style="flex: 1; justify-content: center; text-decoration: none;">عرض الملف 👤</a>
                        <button type="button" onclick="removeFriend({fr['user_id']})" class="btn-fb-danger" style="padding: 6px 12px;" title="إلغاء الصداقة">🗑️</button>
                    </div>
                </div>
                """
        else:
            friends_cards_html = "<div style='color: var(--fb-text-muted); padding: 12px; font-size: 0.9rem;'>لم تقم بإضافة زملاء وأصدقاء بعد. ابدأ بإرسال طلبات للزملاء المقترحين أدناه!</div>"

        suggested_html = ""
        for sug in suggested_doctors:
            av = f'<img src="/uploads/{sug["avatar_image"]}" class="friend-avatar-circle">' if sug.get("avatar_image") else f'<div class="friend-avatar-circle">{sug["name"][0]}</div>'
            suggested_html += f"""
            <div class="friend-card">
                {av}
                <div style="font-weight: 800; font-size: 1.05rem; color: var(--fb-text); margin-bottom: 2px;">د. {sug['name']}</div>
                <div style="font-size: 0.8rem; color: var(--fb-primary); font-weight: 700;">{sug.get('specialty') or 'طبيب بيطري'}</div>
                <div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-top: 4px;">{sug.get('clinic_name') or ''} • {sug.get('country') or 'مصر'}</div>
                <div style="margin-top: 14px;">
                    <button type="button" onclick="sendFriendRequest({sug['id']}, this)" class="btn-fb-primary" style="width: 100%; justify-content: center;">➕ إضافة كصديق زميل</button>
                </div>
            </div>
            """

        tab_body = f"""
        <div style="max-width: 1100px; margin: 20px auto; padding: 0 14px;">
            <div class="fb-card" style="padding: 20px; margin-bottom: 24px;">
                <h2 style="margin: 0 0 16px 0; color: #0f766e; font-size: 1.3rem;">📩 طلبات الصداقة والزمالة الواردة ({len(incoming_requests)})</h2>
                <div class="friend-card-grid">
                    {incoming_html}
                </div>
            </div>

            <div class="fb-card" style="padding: 20px; margin-bottom: 24px;">
                <h2 style="margin: 0 0 16px 0; color: var(--fb-text); font-size: 1.3rem;">👥 قائمة الأصدقاء والزملاء ({len(friends_list)})</h2>
                <div class="friend-card-grid">
                    {friends_cards_html}
                </div>
            </div>

            <div class="fb-card" style="padding: 20px;">
                <h2 style="margin: 0 0 16px 0; color: #ea580c; font-size: 1.3rem;">✨ أطباء وزملاء مقترحون للتواصل (People You May Know)</h2>
                <div class="friend-card-grid">
                    {suggested_html}
                </div>
            </div>
        </div>
        """
        body = f"{COMMUNITY_CSS}<div class='fb-app-wrapper'>{subnav_strip}{tab_body}</div>{COMMUNITY_JS}"
        return HTMLResponse(content=get_base_html("الأصدقاء والزملاء | VetBook", body, user, lang), media_type="text/html; charset=utf-8")

    # TAB 2: VETERINARY PAGES (الصفحات البيطرية والمؤسسات)
    elif tab == "pages":
        c.execute("""
        SELECT p.*, 
               EXISTS(SELECT 1 FROM community_page_followers pf WHERE pf.page_id = p.id AND pf.user_id = ?) as is_following
        FROM community_pages p
        ORDER BY p.followers_count DESC, p.id DESC
        """, (current_user_id,))
        pages_list = [dict(r) for r in c.fetchall()]
        conn.close()

        pages_cards_html = ""
        for pg in pages_list:
            cov = f'<img src="/uploads/{pg["cover_image"]}" style="width: 100%; height: 110px; object-fit: cover;">' if pg.get("cover_image") else '<div style="width: 100%; height: 110px; background: linear-gradient(135deg, #0f766e, #0d9488);"></div>'
            av = f'<img src="/uploads/{pg["avatar_image"]}" style="width: 60px; height: 60px; border-radius: 50%; border: 3px solid white; object-fit: cover; margin-top: -30px; margin-right: 14px; background: white;">' if pg.get("avatar_image") else '<div style="width: 60px; height: 60px; border-radius: 50%; border: 3px solid white; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; font-weight: 800; margin-top: -30px; margin-right: 14px;">🏥</div>'
            fol_text = "✔️ متابع" if pg.get("is_following") else "➕ متابعة الصفحة"
            fol_style = "background: #e2e8f0; color: #334155;" if pg.get("is_following") else "background: var(--fb-primary); color: #ffffff;"

            pages_cards_html += f"""
            <div class="page-card">
                {cov}
                <div style="padding: 0 16px 16px 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 8px;">
                        {av}
                        <button type="button" onclick="togglePageFollow({pg['id']}, this)" class="btn" style="border-radius: 20px; font-weight: 700; font-size: 0.8rem; padding: 6px 14px; border: none; cursor: pointer; {fol_style}">{fol_text}</button>
                    </div>
                    <div style="margin-top: 10px;">
                        <div style="font-weight: 800; font-size: 1.1rem; color: var(--fb-text); display: flex; align-items: center; gap: 6px;">
                            <span>{pg['name']}</span>
                            {'<span style="color: #059669; font-size: 0.88rem;" title="صفحة معتمدة وموثقة">✔️ موثقة</span>' if pg.get('is_verified') else ''}
                        </div>
                        <div style="font-size: 0.78rem; color: var(--fb-primary); font-weight: 700; margin-top: 2px;">{pg.get('city') or 'مصر'} • <span id="page-followers-{pg['id']}">{pg.get('followers_count', 0)} متابع</span></div>
                        <p style="font-size: 0.85rem; color: var(--fb-text-muted); margin: 8px 0 12px 0; line-height: 1.5; height: 42px; overflow: hidden;">{pg.get('description','')[:120]}</p>
                    </div>
                    <div style="border-top: 1px solid var(--fb-border); padding-top: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; flex-wrap: wrap; gap: 6px;">
                        <a href="/community?page_id={pg['id']}" style="color: #0f766e; text-decoration: none; font-weight: 700;">عرض منشورات الصفحة ←</a>
                        <span style="color: var(--fb-text-muted);">📞 {pg.get('phone') or 'غير مدرج'}</span>
                    </div>
                </div>
            </div>
            """

        tab_body = f"""
        <div style="max-width: 1100px; margin: 20px auto; padding: 0 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 style="margin: 0; font-size: 1.4rem; color: var(--fb-text);">🏢 الصفحات والمراكز والعيادات البيطرية</h1>
                    <div style="font-size: 0.85rem; color: var(--fb-text-muted); margin-top: 4px;">تابع أحدث خدمات المستشفيات، العيادات التخصصية، ومختبرات التشخيص المعتمدة</div>
                </div>
                <button type="button" onclick="openModal('create-page-modal')" class="btn-fb-primary">➕ إنشاء صفحة بيطرية جديدة</button>
            </div>
            <div class="page-card-grid">
                {pages_cards_html}
            </div>
        </div>

        <!-- Create Page Modal -->
        <div id="create-page-modal" class="fb-modal-overlay">
            <div class="fb-modal-box">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--fb-border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
                    <h2 style="margin: 0; font-size: 1.25rem; color: #0f766e;">🏢 إنشاء صفحة بيطرية جديدة</h2>
                    <button type="button" onclick="closeModal('create-page-modal')" style="background: none; border: none; font-size: 1.4rem; cursor: pointer;">✕</button>
                </div>
                <form action="/community/pages/create" method="POST" enctype="multipart/form-data">
                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">اسم المنشأة أو العيادة:</label>
                        <input type="text" name="name" required placeholder="مثال: مستشفى النور للطب البيطري" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">التصنيف:</label>
                            <select name="category" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                                <option value="clinic">عيادة بيطرية</option>
                                <option value="hospital">مستشفى بيطري تخصصي</option>
                                <option value="lab">مختبر تحاليل بيطرية</option>
                                <option value="pharma">شركة أدوية ولقاحات</option>
                                <option value="syndicate">نقابة / جمعية علمية</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">المدينة / المحافظة:</label>
                            <input type="text" name="city" placeholder="مثال: القاهرة" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">رقم الهاتف / الواتساب:</label>
                            <input type="text" name="phone" placeholder="01xxxxxxxxx" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                        </div>
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">الموقع الإلكتروني:</label>
                            <input type="url" name="website" placeholder="https://..." style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                        </div>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">نبذة عن الخدمات والإمكانيات الإكلينيكية:</label>
                        <textarea name="description" rows="3" required placeholder="صف التخصصات والعمليات والأجهزة المتوفرة..." style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);"></textarea>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.82rem;">شعار الصفحة (Avatar):</label>
                            <input type="file" name="avatar_file" accept="image/*" style="width: 100%; font-size: 0.82rem;">
                        </div>
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.82rem;">صورة الغلاف (Cover):</label>
                            <input type="file" name="cover_file" accept="image/*" style="width: 100%; font-size: 0.82rem;">
                        </div>
                    </div>
                    <button type="submit" class="btn-fb-primary" style="width: 100%; justify-content: center; padding: 12px;">🚀 نشر واعتماد الصفحة الآن</button>
                </form>
            </div>
        </div>
        """
        body = f"{COMMUNITY_CSS}<div class='fb-app-wrapper'>{subnav_strip}{tab_body}</div>{COMMUNITY_JS}"
        return HTMLResponse(content=get_base_html("الصفحات البيطرية | VetBook", body, user, lang), media_type="text/html; charset=utf-8")

    # TAB 3: GROUPS TAB (المجموعات التخصصية)
    elif tab == "groups":
        c.execute("""
        SELECT g.*, 
               EXISTS(SELECT 1 FROM community_group_members gm WHERE gm.group_id = g.id AND gm.user_id = ?) as is_member
        FROM community_groups g
        ORDER BY g.members_count DESC, g.id DESC
        """, (current_user_id,))
        groups_list = [dict(r) for r in c.fetchall()]
        conn.close()

        groups_cards_html = ""
        for gp in groups_list:
            btn_txt = "🚪 مغادرة" if gp.get("is_member") else "➕ انضمام للمجموعة"
            btn_style = "background: #e2e8f0; color: #475569;" if gp.get("is_member") else "background: var(--fb-primary); color: #ffffff;"
            action_fn = f"leaveGroup({gp['id']}, this)" if gp.get("is_member") else f"joinGroup({gp['id']}, this)"

            groups_cards_html += f"""
            <div class="group-card">
                <div style="background: linear-gradient(135deg, rgba(15,118,110,0.1), rgba(20,184,166,0.15)); padding: 20px; text-align: center; border-bottom: 1px solid var(--fb-border);">
                    <div style="font-size: 2.8rem; margin-bottom: 6px;">{gp.get('icon') or '🩺'}</div>
                    <div style="font-weight: 800; font-size: 1.15rem; color: var(--fb-text);">{gp['name']}</div>
                    <div style="font-size: 0.78rem; color: var(--fb-primary); font-weight: 700; margin-top: 4px;">👥 {gp.get('members_count', 1)} عضواً وطبيباً</div>
                </div>
                <div style="padding: 16px;">
                    <p style="font-size: 0.85rem; color: var(--fb-text-muted); margin: 0 0 14px 0; line-height: 1.6; height: 50px; overflow: hidden;">{gp.get('description','')[:130]}</p>
                    <div style="display: flex; gap: 8px;">
                        <button type="button" onclick="{action_fn}" class="btn" style="flex: 1; border-radius: 8px; font-weight: 700; font-size: 0.85rem; padding: 8px; border: none; cursor: pointer; {btn_style}">{btn_txt}</button>
                        <a href="/community?group_id={gp['id']}" class="btn-fb-outline" style="padding: 8px 14px; text-decoration: none; font-size: 0.85rem;">تصفح الحالات ←</a>
                    </div>
                </div>
            </div>
            """

        tab_body = f"""
        <div style="max-width: 1100px; margin: 20px auto; padding: 0 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 style="margin: 0; font-size: 1.4rem; color: var(--fb-text);">🐾 المجموعات والروابط التخصصية</h1>
                    <div style="font-size: 0.85rem; color: var(--fb-text-muted); margin-top: 4px;">انضم إلى المجموعات الإكلينيكية لمناقشة الحالات المعقدة حسب تخصصك</div>
                </div>
                <button type="button" onclick="openModal('create-group-modal')" class="btn-fb-primary">➕ إنشاء مجموعة تخصصية جديدة</button>
            </div>
            <div class="group-card-grid">
                {groups_cards_html}
            </div>
        </div>

        <!-- Create Group Modal -->
        <div id="create-group-modal" class="fb-modal-overlay">
            <div class="fb-modal-box">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--fb-border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
                    <h2 style="margin: 0; font-size: 1.25rem; color: #0f766e;">🐾 إنشاء مجموعة بيطرية تخصصية</h2>
                    <button type="button" onclick="closeModal('create-group-modal')" style="background: none; border: none; font-size: 1.4rem; cursor: pointer;">✕</button>
                </div>
                <form action="/community/groups/create" method="POST">
                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">اسم المجموعة:</label>
                        <input type="text" name="name" required placeholder="مثال: رابطة جراحة ومناظير الخيول" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">الأيقونة التعبيرية:</label>
                            <input type="text" name="icon" value="🩺" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text); text-align: center; font-size: 1.2rem;">
                        </div>
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">التخصص المستهدف:</label>
                            <select name="category" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                                <option value="pets">حيوانات أليفة (كلاب وقطط)</option>
                                <option value="bovine">مجترات وتناسل</option>
                                <option value="equine">خيول وفروسية</option>
                                <option value="poultry">دواجن وأوبئة</option>
                                <option value="diagnostics">أشعة وسونار ومختبر</option>
                                <option value="surgery">جراحة وتخدير</option>
                            </select>
                        </div>
                    </div>
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">أهداف المجموعة ومواضيع النقاش:</label>
                        <textarea name="description" rows="3" required placeholder="حدد أهداف وتوجهات المجموعة..." style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);"></textarea>
                    </div>
                    <button type="submit" class="btn-fb-primary" style="width: 100%; justify-content: center; padding: 12px;">🚀 تأسيس المجموعة وإطلاقها الآن</button>
                </form>
            </div>
        </div>
        """
        body = f"{COMMUNITY_CSS}<div class='fb-app-wrapper'>{subnav_strip}{tab_body}</div>{COMMUNITY_JS}"
        return HTMLResponse(content=get_base_html("المجموعات التخصصية | VetBook", body, user, lang), media_type="text/html; charset=utf-8")

    # TAB 4: EVENTS TAB (الفعاليات والمؤتمرات)
    elif tab == "events":
        c.execute("""
        SELECT e.*,
               EXISTS(SELECT 1 FROM community_event_attendees ea WHERE ea.event_id = e.id AND ea.user_id = ?) as is_interested
        FROM community_events e
        ORDER BY e.id DESC
        """, (current_user_id,))
        events_list = [dict(r) for r in c.fetchall()]
        conn.close()

        events_cards_html = ""
        for ev in events_list:
            btn_txt = "⭐ سأحضر (" + str(ev.get("interested_count", 0)) + ")" if ev.get("is_interested") else "⭐ تسجيل اهتمامي (" + str(ev.get("interested_count", 0)) + ")"
            btn_style = "background: #0f766e; color: #ffffff;" if ev.get("is_interested") else "background: var(--fb-card); color: var(--fb-text); border: 1px solid var(--fb-border);"

            events_cards_html += f"""
            <div class="fb-card" style="padding: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                <div style="flex: 1 1 240px; min-width: 0;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="font-size: 1.5rem;">🎓</span>
                        <h3 style="margin: 0; color: #0f766e; font-size: 1.15rem;">{ev['title']}</h3>
                    </div>
                    <p style="margin: 0 0 8px 0; font-size: 0.88rem; color: var(--fb-text); line-height: 1.6;">{ev.get('description','')}</p>
                    <div style="font-size: 0.8rem; color: var(--fb-text-muted); display: flex; gap: 14px; flex-wrap: wrap;">
                        <span>📅 <strong>الموعد:</strong> {ev['date_time']}</span>
                        <span>📍 <strong>المكان / الرابط:</strong> {ev['location']}</span>
                    </div>
                </div>
                <div>
                    <button type="button" onclick="toggleEventInterest({ev['id']}, this)" class="btn" style="border-radius: 20px; font-weight: 800; font-size: 0.85rem; padding: 10px 18px; cursor: pointer; {btn_style}">{btn_txt}</button>
                </div>
            </div>
            """

        tab_body = f"""
        <div style="max-width: 1000px; margin: 20px auto; padding: 0 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 style="margin: 0; font-size: 1.4rem; color: var(--fb-text);">🎓 المؤتمرات والفعاليات وورش العمل السريرية</h1>
                    <div style="font-size: 0.85rem; color: var(--fb-text-muted); margin-top: 4px;">تابع مواعيد أهم الويبينارات والدورات والمؤتمرات البيطرية الإقليمية والدولية</div>
                </div>
                <button type="button" onclick="openModal('create-event-modal')" class="btn-fb-primary">➕ إضافة فعالية بيطرية جديدة</button>
            </div>
            {events_cards_html}
        </div>

        <!-- Create Event Modal -->
        <div id="create-event-modal" class="fb-modal-overlay">
            <div class="fb-modal-box">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--fb-border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
                    <h2 style="margin: 0; font-size: 1.25rem; color: #0f766e;">🎓 إضافة فعالية أو مؤتمر بيطري</h2>
                    <button type="button" onclick="closeModal('create-event-modal')" style="background: none; border: none; font-size: 1.4rem; cursor: pointer;">✕</button>
                </div>
                <form action="/community/events/create" method="POST">
                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">عنوان الفعالية / الويبينار:</label>
                        <input type="text" name="title" required placeholder="مثال: ويبينار مستجدات التخدير في الحيوانات الأليفة" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                    </div>
                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">الموعد والتاريخ:</label>
                        <input type="text" name="date_time" required placeholder="مثال: الجمعة 20 نوفمبر • 07:00 مساءً" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                    </div>
                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">مكان الانعقاد أو رابط الحضور (Zoom / القاعة):</label>
                        <input type="text" name="location" required placeholder="مثال: Zoom Webinar أو قاعة مؤتمرات كلية الطب البيطري" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                    </div>
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">وصف الفعالية والمحاور والمحاضرين:</label>
                        <textarea name="description" rows="3" required placeholder="اكتب تفاصيل المحاور وأسماء المتحدثين..." style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);"></textarea>
                    </div>
                    <button type="submit" class="btn-fb-primary" style="width: 100%; justify-content: center; padding: 12px;">🚀 نشر الفعالية في المجتمع</button>
                </form>
            </div>
        </div>
        """
        body = f"{COMMUNITY_CSS}<div class='fb-app-wrapper'>{subnav_strip}{tab_body}</div>{COMMUNITY_JS}"
        return HTMLResponse(content=get_base_html("الفعاليات والمؤتمرات | VetBook", body, user, lang), media_type="text/html; charset=utf-8")

    # TAB 5: NOTIFICATIONS TAB (الإشعارات)
    elif tab == "notifications":
        c.execute("""
        SELECT * FROM community_notifications
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 60
        """, (current_user_id,))
        notifications_list = [dict(r) for r in c.fetchall()]
        conn.close()

        notifs_items_html = ""
        if notifications_list:
            for nt in notifications_list:
                unread_cls = "unread" if nt.get("is_read") == 0 else ""
                dot = '<div class="notif-unread-dot"></div>' if nt.get("is_read") == 0 else ""
                av = f'<img src="/uploads/{nt["actor_avatar"]}" style="width: 44px; height: 44px; border-radius: 50%; object-fit: cover;">' if nt.get("actor_avatar") else f'<div style="width: 44px; height: 44px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800;">{nt.get("actor_name", "د")[0]}</div>'
                target_url = f"/community#post-{nt['post_id']}" if nt.get("post_id") else f"/community/profile/{nt['actor_id']}"

                notifs_items_html += f"""
                <div class="notif-item {unread_cls}" onclick="markNotificationRead({nt['id']}, '{target_url}')" style="cursor: pointer;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        {av}
                        <div>
                            <div style="font-size: 0.92rem; color: var(--fb-text); line-height: 1.5;">
                                <strong>د. {nt.get('actor_name','زميل')}</strong> {nt.get('message','')}
                            </div>
                            <div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-top: 2px;">
                                🕒 {nt.get('created_at','')[:16]}
                            </div>
                        </div>
                    </div>
                    {dot}
                </div>
                """
        else:
            notifs_items_html = "<div style='padding: 30px; text-align: center; color: var(--fb-text-muted);'>صندوق الإشعارات فارغ حالياً. ستظهر هنا تفاعلات زملائك وطلبات الصداقة.</div>"

        tab_body = f"""
        <div style="max-width: 760px; margin: 20px auto; padding: 0 14px;">
            <div class="fb-card">
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--fb-border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <h1 style="margin: 0; font-size: 1.3rem; color: var(--fb-text);">🔔 الإشعارات والتنبيهات السريرية</h1>
                    <button type="button" onclick="markAllNotificationsRead()" class="btn-fb-outline" style="font-size: 0.8rem; padding: 6px 12px;">✔️ تعليم الكل كمقروء</button>
                </div>
                <div>
                    {notifs_items_html}
                </div>
            </div>
        </div>
        """
        body = f"{COMMUNITY_CSS}<div class='fb-app-wrapper'>{subnav_strip}{tab_body}</div>{COMMUNITY_JS}"
        return HTMLResponse(content=get_base_html("الإشعارات | VetBook", body, user, lang), media_type="text/html; charset=utf-8")

    # TAB 6: SEARCH TAB (البحث الشامل في VetBook)
    elif tab == "search":
        search_query = q.strip()
        search_like = f"%{search_query}%"

        # 1. Matching Doctors
        c.execute("""
        SELECT id, name, role, specialty, clinic_name, city, country, avatar_image
        FROM users
        WHERE name LIKE ? OR specialty LIKE ? OR clinic_name LIKE ? OR city LIKE ?
        LIMIT 10
        """, (search_like, search_like, search_like, search_like))
        matching_doctors = [dict(r) for r in c.fetchall()]

        # 2. Matching Posts
        c.execute("""
        SELECT id, title, content, author_name, species, breed, symptoms, is_urgent, created_at, likes_count, comments_count
        FROM community_posts
        WHERE (title LIKE ? OR content LIKE ? OR symptoms LIKE ? OR species LIKE ? OR breed LIKE ?)
          AND (privacy = 'public' OR user_id = ?)
        LIMIT 15
        """, (search_like, search_like, search_like, search_like, search_like, current_user_id))
        matching_posts = [dict(r) for r in c.fetchall()]

        # 3. Matching Pages
        c.execute("""
        SELECT id, name, category, city, followers_count, description
        FROM community_pages
        WHERE name LIKE ? OR description LIKE ? OR city LIKE ?
        LIMIT 8
        """, (search_like, search_like, search_like))
        matching_pages = [dict(r) for r in c.fetchall()]

        # 4. Matching Groups
        c.execute("""
        SELECT id, name, icon, category, members_count, description
        FROM community_groups
        WHERE name LIKE ? OR description LIKE ?
        LIMIT 8
        """, (search_like, search_like))
        matching_groups = [dict(r) for r in c.fetchall()]
        conn.close()

        doctors_res_html = ""
        if matching_doctors:
            for doc in matching_doctors:
                av = f'<img src="/uploads/{doc["avatar_image"]}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;">' if doc.get("avatar_image") else f'<div style="width: 50px; height: 50px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800;">{doc["name"][0]}</div>'
                doctors_res_html += f"""
                <div class="fb-card" style="padding: 14px; display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; flex-wrap: wrap;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        {av}
                        <div>
                            <a href="/community/profile/{doc['id']}" style="font-weight: 800; font-size: 1.05rem; color: #0f766e; text-decoration: none;">د. {doc['name']}</a>
                            <div style="font-size: 0.8rem; color: var(--fb-text-muted);">{doc.get('specialty') or 'طبيب بيطري'} • {doc.get('clinic_name') or ''} • {doc.get('city') or 'مصر'}</div>
                        </div>
                    </div>
                    <a href="/community/profile/{doc['id']}" class="btn-fb-outline" style="font-size: 0.8rem; padding: 6px 12px;">الملف الشخصي</a>
                </div>
                """
        else:
            doctors_res_html = "<div style='color: var(--fb-text-muted); font-size: 0.88rem; padding: 8px;'>لا يوجد أطباء يطابقون عبارة البحث.</div>"

        posts_res_html = ""
        if matching_posts:
            for pst in matching_posts:
                urg = '<span style="background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 800;">🚨 عاجلة</span>' if pst.get("is_urgent") else ""
                posts_res_html += f"""
                <div class="fb-card" style="padding: 16px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 6px;">
                        <a href="/community#post-{pst['id']}" style="font-weight: 800; font-size: 1.05rem; color: var(--fb-text); text-decoration: none;">{pst['title']}</a>
                        {urg}
                    </div>
                    <p style="font-size: 0.88rem; color: var(--fb-text-muted); margin: 0 0 8px 0; line-height: 1.5;">{pst['content'][:180]}...</p>
                    <div style="font-size: 0.75rem; color: var(--fb-text-muted); display: flex; justify-content: space-between; flex-wrap: wrap; gap: 6px;">
                        <span>د. {pst.get('author_name','طبيب')} • 🐾 {pst.get('species','')} • 🕒 {pst.get('created_at','')[:16]}</span>
                        <a href="/community#post-{pst['id']}" style="color: #0f766e; font-weight: 700; text-decoration: none;">فتح الحالة والمناقشة ←</a>
                    </div>
                </div>
                """
        else:
            posts_res_html = "<div style='color: var(--fb-text-muted); font-size: 0.88rem; padding: 8px;'>لا توجد منشورات سريرية تطابق البحث.</div>"

        tab_body = f"""
        <div style="max-width: 900px; margin: 20px auto; padding: 0 14px;">
            <div style="margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 1.4rem; color: var(--fb-text);">🔍 نتائج البحث عن: <span style="color: #0f766e;">"{search_query}"</span></h1>
            </div>

            <div style="margin-bottom: 24px;">
                <h3 style="color: #0f766e; margin-bottom: 12px; font-size: 1.15rem;">👤 الأطباء والزملاء ({len(matching_doctors)})</h3>
                {doctors_res_html}
            </div>

            <div style="margin-bottom: 24px;">
                <h3 style="color: #0f766e; margin-bottom: 12px; font-size: 1.15rem;">📰 الحالات والمنشورات السريرية ({len(matching_posts)})</h3>
                {posts_res_html}
            </div>
        </div>
        """
        body = f"{COMMUNITY_CSS}<div class='fb-app-wrapper'>{subnav_strip}{tab_body}</div>{COMMUNITY_JS}"
        return HTMLResponse(content=get_base_html(f"نتائج البحث: {search_query} | VetBook", body, user, lang), media_type="text/html; charset=utf-8")

    # TAB 7: ADMIN MODERATION TAB (الإشراف والرقابة)
    elif tab == "moderation":
        if not is_admin:
            conn.close()
            return RedirectResponse("/community", status_code=303)

        c.execute("""
        SELECT r.*, u.name as reporter_name
        FROM community_reports r
        LEFT JOIN users u ON r.reporter_id = u.id
        ORDER BY r.status = 'pending' DESC, r.id DESC
        LIMIT 50
        """)
        reports_list = [dict(r) for r in c.fetchall()]
        conn.close()

        reports_rows_html = ""
        for rep in reports_list:
            status_badge = '<span style="background: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 800;">قيد المراجعة</span>' if rep.get("status") == "pending" else '<span style="background: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 8px; font-size: 0.72rem; font-weight: 800;">تم الحسم</span>'
            del_fn = f"deletePost({rep['target_id']})" if rep.get("target_type") == "post" else f"deleteComment({rep['target_id']})"

            reports_rows_html += f"""
            <tr style="border-bottom: 1px solid var(--fb-border);">
                <td style="padding: 12px; font-weight: 700;">#{rep['id']}</td>
                <td style="padding: 12px;">د. {rep.get('reporter_name') or 'طبيب'}</td>
                <td style="padding: 12px;"><span style="font-weight: 800; color: #0f766e;">{rep['target_type']} #{rep['target_id']}</span></td>
                <td style="padding: 12px; color: #dc2626; font-weight: 700;">{rep['reason']}</td>
                <td style="padding: 12px; font-size: 0.85rem;">{rep.get('details') or '-'}</td>
                <td style="padding: 12px;">{status_badge}</td>
                <td style="padding: 12px; font-size: 0.75rem; color: var(--fb-text-muted);">{rep['created_at'][:16]}</td>
                <td style="padding: 12px; white-space: nowrap;">
                    <button type="button" onclick="{del_fn}" class="btn-fb-danger" style="padding: 4px 10px; font-size: 0.75rem;">🗑️ حذف المحتوى</button>
                    <form action="/community/reports/dismiss/{rep['id']}" method="POST" style="display: inline-block; margin: 0 4px;">
                        <button type="submit" class="btn-fb-outline" style="padding: 4px 10px; font-size: 0.75rem;">✔️ تجاهل</button>
                    </form>
                </td>
            </tr>
            """

        tab_body = f"""
        <div style="max-width: 1200px; margin: 20px auto; padding: 0 14px;">
            <div class="fb-card" style="padding: 24px;">
                <div style="margin-bottom: 20px;">
                    <h1 style="margin: 0; font-size: 1.4rem; color: #0f766e;">🛡️ لوحة الإشراف والرقابة السريرية (Admin Moderation Panel)</h1>
                    <div style="font-size: 0.85rem; color: var(--fb-text-muted); margin-top: 4px;">مراجعة بلاغات الأطباء حول المحتوى المضلل أو المخالف لأخلاقيات المهنة البيطرية</div>
                </div>

                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem; text-align: right;">
                        <thead>
                            <tr style="background: var(--fb-bg); border-bottom: 2px solid var(--fb-border);">
                                <th style="padding: 10px;">المعرف</th>
                                <th style="padding: 10px;">المُبلّغ</th>
                                <th style="padding: 10px;">الهدف</th>
                                <th style="padding: 10px;">السبب</th>
                                <th style="padding: 10px;">التفاصيل</th>
                                <th style="padding: 10px;">الحالة</th>
                                <th style="padding: 10px;">التاريخ</th>
                                <th style="padding: 10px;">الإجراءات</th>
                            </tr>
                        </thead>
                        <tbody>
                            {reports_rows_html if reports_rows_html else '<tr><td colspan="8" style="text-align: center; padding: 20px; color: var(--fb-text-muted);">لا توجد بلاغات معلقة حالياً. المنصة نظيفة تماماً!</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """
        body = f"{COMMUNITY_CSS}<div class='fb-app-wrapper'>{subnav_strip}{tab_body}</div>{COMMUNITY_JS}"
        return HTMLResponse(content=get_base_html("لوحة الإشراف | VetBook", body, user, lang), media_type="text/html; charset=utf-8")

    # TAB 0: MAIN FEED (الموجز العام والمنشورات السريرية)
    # Fetch Feed Posts respecting Privacy & Block Filters
    query = """
    SELECT p.*,
           (SELECT COUNT(*) FROM community_comments c WHERE c.post_id = p.id) as real_comments_count
    FROM community_posts p
    WHERE 1=1
    """
    params = []

    # Blocked Users Filter
    if blocked_set:
        placeholders = ",".join("?" for _ in blocked_set)
        query += f" AND p.user_id NOT IN ({placeholders})"
        params.extend(list(blocked_set))

    # Category Filter
    if category == "bookmarks":
        query += """
        AND p.id IN (SELECT post_id FROM community_bookmarks WHERE user_id = ?)
        """
        params.append(current_user_id)
    elif category == "urgent":
        query += " AND p.is_urgent = 1"
    elif category != "all":
        query += " AND p.category = ?"
        params.append(category)

    # Species Filter
    if species != "all":
        query += " AND p.species = ?"
        params.append(species)

    # Group Filter
    if group_id > 0:
        query += " AND p.group_id = ?"
        params.append(group_id)

    # Page Filter
    if page_id > 0:
        query += " AND p.page_id = ?"
        params.append(page_id)

    # Tab: My Posts Filter
    if tab == "my_posts":
        query += " AND p.user_id = ?"
        params.append(current_user_id)

    c.execute(query, params)
    raw_posts = [dict(r) for r in c.fetchall()]

    # Filter by Privacy Rules: public / friends / only_me
    raw_posts = [p for p in raw_posts if can_view_post(p, current_user_id, friends_set, is_admin)]

    # Fetch User Likes and Bookmarks
    c.execute("SELECT post_id, reaction_type FROM community_likes WHERE user_id = ?", (current_user_id,))
    user_reactions = {r[0]: r[1] for r in c.fetchall()}

    c.execute("SELECT post_id FROM community_bookmarks WHERE user_id = ?", (current_user_id,))
    user_bookmarks = set(r[0] for r in c.fetchall())

    # Sorting with Algorithmic Relevance (EdgeRank)
    if sort == "smart":
        viewer_meta = {
            "id": current_user_id,
            "specialty": user.get("specialty", "") if user else "",
            "role": user.get("role", "") if user else ""
        }
        raw_posts.sort(key=lambda p: (
            p.get("is_pinned", 0),
            calculate_edgerank_score(p, viewer_meta)
        ), reverse=True)
    elif sort == "recent":
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x["id"]), reverse=True)
    elif sort == "urgent":
        raw_posts.sort(key=lambda x: (x.get("is_urgent", 0), x["id"]), reverse=True)
    elif sort == "trending":
        raw_posts.sort(key=lambda x: (x.get("virality_score", 0), x.get("likes_count", 0)), reverse=True)

    # Fetch Comments for posts
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
        is_author = (p.get("user_id") == current_user_id)

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
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.15rem;">🚨</span>
                    <span>استشارة سريرية عاجلة بحاجة لرأي تشخيصي فوري (URGENT CASE)</span>
                </div>
                <span class="urgent-badge">أولوية قصوى</span>
            </div>
            """

        # Demographics Grid
        demographics_html = ""
        if p.get("species") or p.get("symptoms") or p.get("breed"):
            spec_name = SPECIES_MAP.get(p.get("species"), p.get("species") or "فصيلة غير محددة")
            demographics_html = f"""
            <div class="case-demographics-grid">
                <div>🐾 <strong>الفصيلة:</strong> {spec_name}</div>
                {f"<div>🧬 <strong>السلالة:</strong> {p['breed']}</div>" if p.get('breed') else ""}
                {f"<div>⚖️ <strong>العمر/الوزن:</strong> {p.get('age','')} • {p.get('weight','')} كجم</div>" if (p.get('weight') or p.get('age')) else ""}
                {f"<div>⚧ <strong>الجنس:</strong> {p['gender']}</div>" if p.get('gender') else ""}
                {f"<div style='grid-column: 1 / -1;'>🌡️ <strong>الأعراض والعلامات الحيوية:</strong> {p['symptoms']}</div>" if p.get('symptoms') else ""}
                {f"<div style='grid-column: 1 / -1; color: #7c2d12;'>💊 <strong>الأدوية المسبقة:</strong> {p['medications']}</div>" if p.get('medications') else ""}
            </div>
            """

        # Media Grid
        media_images = []
        if p.get("image_path"):
            media_images.append(p["image_path"])
        if p.get("extra_images"):
            media_images.extend(parse_extra_images(p["extra_images"]))
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
                    <div onclick="votePoll({post_id}, {opt['id']})" style="margin-bottom: 8px; background: var(--fb-bg); border: 1px solid var(--fb-border); border-radius: 8px; padding: 10px; cursor: pointer; position: relative; overflow: hidden;">
                        <div style="position: absolute; top:0; right:0; bottom:0; width: {pct}%; background: rgba(15,118,110,0.15);"></div>
                        <div style="position: relative; display: flex; justify-content: space-between; font-weight: 700; font-size: 0.86rem; color: var(--fb-text); flex-wrap: wrap; gap: 4px;">
                            <span style="flex: 1 1 auto; min-width: 0; word-break: break-word;">{opt['text']}</span>
                            <span style="flex-shrink: 0;">{pct}% ({opt.get('votes', 0)})</span>
                        </div>
                    </div>
                    """
                poll_html = f"""
                <div style="background: var(--fb-card); border: 1.5px solid #a7f3d0; border-radius: 12px; padding: 14px; margin: 12px 0;">
                    <div style="font-weight: 800; font-size: 0.95rem; color: #0f766e; margin-bottom: 10px;">📊 استطلاع الرأي السريري: {q_text}</div>
                    {opts_html}
                    <div style="font-size: 0.74rem; color: var(--fb-text-muted);">إجمالي الأصوات: {total_votes} طبيباً</div>
                </div>
                """
            except Exception:
                pass

        # Threaded Comments & Nested Replies
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
            bubble_class = "fb-comment-bubble" + (" best-answer-bubble" if is_best else "")
            best_badge = '<span style="background: #10b981; color: white; padding: 1px 6px; border-radius: 8px; font-size: 0.7rem; font-weight: 800;">🏆 أفضل تشخيص معتمد ✅</span>' if is_best else ""
            author_badge = '<span style="background: #e0e7ff; color: #3730a3; padding: 1px 6px; border-radius: 8px; font-size: 0.7rem; font-weight: 700;">👑 صاحب الحالة</span>' if cm.get("user_id") == p["user_id"] else ""

            mark_best_btn = ""
            if user and user["id"] == p["user_id"] and not is_best and cm.get("user_id") != user["id"]:
                mark_best_btn = f"""
                <button type="button" onclick="markBestDiagnosis({cm_id}, {post_id})" style="background: none; border: none; color: #059669; font-weight: 800; cursor: pointer; font-size: 0.74rem;">
                    ✅ اعتماد كأفضل تشخيص (+50 سمعة)
                </button>
                """

            del_cm_btn = ""
            if user and (user["id"] == cm.get("user_id") or user["id"] == p["user_id"] or is_admin):
                del_cm_btn = f"""
                <button type="button" onclick="deleteComment({cm_id})" style="background: none; border: none; color: #dc2626; cursor: pointer; font-size: 0.74rem;">
                    🗑️ حذف
                </button>
                """

            # Render Nested Replies for this comment
            replies_list = replies_map.get(cm_id, [])
            replies_html = ""
            for rep in replies_list:
                rep_id = rep["id"]
                rep_del = f'<button type="button" onclick="deleteComment({rep_id})" style="background: none; border: none; color: #dc2626; cursor: pointer; font-size: 0.72rem;">🗑️ حذف</button>' if (user and (user["id"] == rep.get("user_id") or user["id"] == p["user_id"] or is_admin)) else ""
                replies_html += f"""
                <div style="margin-top: 8px; display: flex; gap: 8px; align-items: flex-start;" id="comment-{rep_id}">
                    <div style="width: 28px; height: 28px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 800; flex-shrink: 0;">
                        {rep['author_name'][0]}
                    </div>
                    <div style="flex: 1;">
                        <div class="fb-comment-bubble" style="padding: 8px 12px; font-size: 0.84rem;">
                            <a href="/community/profile/{rep['user_id']}" style="font-weight: 800; color: #0f766e; text-decoration: none;">د. {rep['author_name']}</a>
                            <div style="margin-top: 3px;">{rep['content']}</div>
                        </div>
                        <div style="font-size: 0.72rem; color: var(--fb-text-muted); margin-top: 2px; display: flex; gap: 10px;">
                            <span>{rep['created_at'][:16]}</span>
                            {rep_del}
                        </div>
                    </div>
                </div>
                """

            comments_html += f"""
            <div style="margin-bottom: 12px; display: flex; gap: 10px; align-items: flex-start;" id="comment-{cm_id}">
                <div style="width: 36px; height: 36px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.9rem; font-weight: 800; flex-shrink: 0;">
                    {cm['author_name'][0]}
                </div>
                <div style="flex: 1;">
                    <div class="{bubble_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap; gap: 6px;">
                            <a href="/community/profile/{cm['user_id']}" style="font-weight: 800; color: #0f766e; text-decoration: none; font-size: 0.88rem;">د. {cm['author_name']}</a>
                            <div style="display: flex; gap: 6px; align-items: center;">
                                {author_badge}
                                {best_badge}
                            </div>
                        </div>
                        <div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-bottom: 6px;">{cm.get('author_specialty') or 'طبيب بيطري'} • {cm.get('author_country') or 'مصر'}</div>
                        <div style="font-size: 0.88rem; line-height: 1.6;">{cm['content']}</div>
                    </div>

                    <div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-top: 4px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <span>{cm['created_at'][:16]}</span>
                        <button type="button" onclick="toggleReplyBox({cm_id})" style="background: none; border: none; color: #0f766e; font-weight: 700; cursor: pointer; font-size: 0.75rem;">💬 رد</button>
                        {mark_best_btn}
                        {del_cm_btn}
                    </div>

                    <!-- Nested Replies Container -->
                    <div class="nested-reply-box">
                        {replies_html}
                        <!-- Inline Reply Input -->
                        <div id="reply-box-{cm_id}" style="display: none; margin-top: 8px;">
                            <form onsubmit="submitReply(event, {post_id}, {cm_id})" style="display: flex; gap: 8px;">
                                <input type="text" id="reply-input-{cm_id}" required placeholder="اكتب رداً على استشارة د. {cm['author_name']}..." style="flex: 1; padding: 6px 12px; border: 1px solid var(--fb-border); border-radius: 20px; font-size: 0.82rem; background: var(--fb-card); color: var(--fb-text);">
                                <button type="submit" class="btn-fb-primary" style="padding: 6px 14px; font-size: 0.8rem; border-radius: 20px;">إرسال</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            """

        # Audience Privacy Badge
        post_privacy = p.get("privacy", "public")
        if post_privacy == "friends":
            privacy_badge = '<span style="font-size: 0.72rem; color: var(--fb-text-muted); background: var(--fb-bg); padding: 1px 6px; border-radius: 10px;">👥 الأصدقاء فقط</span>'
        elif post_privacy == "only_me":
            privacy_badge = '<span style="font-size: 0.72rem; color: var(--fb-text-muted); background: var(--fb-bg); padding: 1px 6px; border-radius: 10px;">🔒 أنا فقط</span>'
        else:
            privacy_badge = '<span style="font-size: 0.72rem; color: var(--fb-text-muted); background: var(--fb-bg); padding: 1px 6px; border-radius: 10px;">🌐 عام</span>'

        # Edit and Delete buttons for author/admin
        edit_action_btn = f'<button type="button" onclick="openEditPostModal({post_id})" style="background: none; border: none; color: #0284c7; cursor: pointer; font-size: 0.8rem; font-weight: 700;">✏️ تعديل</button>' if (is_author or is_admin) else ''
        delete_action_btn = f'<button type="button" onclick="deletePost({post_id})" style="background: none; border: none; color: #dc2626; cursor: pointer; font-size: 0.8rem; font-weight: 700;">🗑️ حذف</button>' if (is_author or is_admin) else ''
        report_action_btn = f'<button type="button" onclick="openReportModal(\'post\', {post_id})" style="background: none; border: none; color: var(--fb-text-muted); cursor: pointer; font-size: 0.8rem;">🚩 إبلاغ</button>'

        posts_cards_html += f"""
        <div class="{card_class}" id="post-{post_id}" style="padding: 16px; margin-bottom: 16px;">
            {urgent_banner}

            <!-- Header Row -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">
                <div style="display: flex; gap: 10px; align-items: center; flex: 1 1 200px; min-width: 0;">
                    <a href="/community/profile/{p['user_id']}" style="text-decoration: none;">
                        <div style="width: 44px; height: 44px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; font-weight: 800;">
                            {p['author_name'][0]}
                        </div>
                    </a>
                    <div>
                        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                            <a href="/community/profile/{p['user_id']}" style="font-weight: 800; font-size: 0.98rem; color: var(--fb-text); text-decoration: none;">د. {p['author_name']}</a>
                            <span style="font-size: 0.85rem; color: #059669;" title="طبيب موثق">🩺</span>
                            {f'<span style="background: #fef3c7; color: #b45309; font-size: 0.68rem; font-weight: 800; padding: 1px 6px; border-radius: 8px;">👑 منشوري</span>' if is_author else ''}
                            {privacy_badge}
                            {f'<span style="font-size: 0.70rem; color: var(--fb-text-muted);">(تم التعديل)</span>' if p.get('is_edited') else ''}
                        </div>
                        <div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-top: 2px;">
                            {p.get('author_specialty','طب وجراحة الحيوان')} • {p.get('author_country','مصر')} • 🕒 {p['created_at'][:16]}
                        </div>
                    </div>
                </div>

                <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                    {edit_action_btn}
                    {delete_action_btn}
                    {report_action_btn}
                </div>
            </div>

            <!-- Title & Body -->
            <div style="margin-bottom: 12px;">
                <h3 style="margin: 0 0 8px 0; font-size: 1.18rem; color: #0f766e; line-height: 1.45;">{p['title']}</h3>
                <div style="font-size: 0.95rem; color: var(--fb-text); line-height: 1.75; white-space: pre-line; word-break: break-word;">{p['content']}</div>
            </div>

            {demographics_html}
            {media_html}
            {poll_html}

            <!-- Post Counters -->
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 4px; border-top: 1px solid var(--fb-border); border-bottom: 1px solid var(--fb-border); font-size: 0.78rem; color: var(--fb-text-muted); margin-top: 12px; flex-wrap: wrap; gap: 6px;">
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span>👍 ❤️ 💡</span>
                    <span id="likes-count-{post_id}">{p.get('likes_count', 0)}</span>
                </div>
                <div style="display: flex; gap: 12px;">
                    <span>{len(comments_raw)} تعليقاً ورأياً</span>
                    <span id="shares-count-{post_id}">{p.get('shares_count', 0)} مشاركة</span>
                </div>
            </div>

            <!-- Post Action Buttons (STRICT ZERO AI, NO MESSENGER) -->
            <div style="display: flex; position: relative; margin-top: 6px; border-bottom: 1px solid var(--fb-border); padding-bottom: 6px; width: 100%; box-sizing: border-box;">
                <!-- Reactions Popup Box -->
                <div class="reactions-popup-box" id="reactions-popup-{post_id}" onmouseleave="hideReactionsPopup({post_id})">
                    <button type="button" class="reaction-emoji-btn" onclick="setPostReaction({post_id}, 'like')" title="إعجاب">👍</button>
                    <button type="button" class="reaction-emoji-btn" onclick="setPostReaction({post_id}, 'vital')" title="حالة سريرية مهمة">❤️</button>
                    <button type="button" class="reaction-emoji-btn" onclick="setPostReaction({post_id}, 'insight')" title="تشخيص دقيق">💡</button>
                    <button type="button" class="reaction-emoji-btn" onclick="setPostReaction({post_id}, 'healing')" title="شفاء ودعم">🐾</button>
                    <button type="button" class="reaction-emoji-btn" onclick="setPostReaction({post_id}, 'followup')" title="متابعة">🤔</button>
                </div>

                <!-- React Trigger Button -->
                <div style="flex: 1;" onmouseenter="showReactionsPopup({post_id})">
                    <button type="button" onclick="setPostReaction({post_id}, 'like')" id="react-btn-{post_id}" class="fb-action-btn" style="width: 100%; {react_active_style}">
                        <span id="react-icon-{post_id}">{react_info['icon']}</span>
                        <span id="react-label-{post_id}">{react_info['label']}</span>
                    </button>
                </div>

                <!-- Comment Button -->
                <button type="button" onclick="focusCommentInput({post_id})" class="fb-action-btn">
                    <span>💬</span>
                    <span>تعليق</span>
                </button>

                <!-- Share Button -->
                <button type="button" onclick="sharePost({post_id})" class="fb-action-btn">
                    <span>↪️</span>
                    <span>مشاركة</span>
                </button>

                <!-- Bookmark Button -->
                <button type="button" onclick="togglePostBookmark({post_id})" id="bookmark-btn-{post_id}" class="fb-action-btn" style="{bookmark_style}">
                    <span id="bookmark-icon-{post_id}">🔖</span>
                    <span id="bookmark-text-{post_id}">{bookmark_label}</span>
                </button>
            </div>

            <!-- Comments Section -->
            <div style="margin-top: 14px;" id="comments-section-{post_id}">
                {comments_html}

                <!-- Add Comment Form -->
                <form action="/community/comment/{post_id}" method="POST" style="display: flex; gap: 8px; align-items: center; margin-top: 10px; flex-wrap: wrap;">
                    <input type="text" name="content" id="comment-input-{post_id}" required placeholder="اكتب تشخيصك التفريقي أو رأيك السريري..." style="flex: 1 1 180px; min-width: 0; padding: 10px 14px; border: 1px solid var(--fb-border); border-radius: 20px; font-size: 0.88rem; background: var(--fb-bg); color: var(--fb-text);">
                    <button type="submit" class="btn-fb-primary" style="border-radius: 20px; padding: 8px 16px; flex-shrink: 0;">إرسال</button>
                </form>
            </div>

            <!-- Edit Post Modal -->
            <div id="edit-post-modal-{post_id}" class="fb-modal-overlay">
                <div class="fb-modal-box">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--fb-border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
                        <h2 style="margin: 0; font-size: 1.25rem; color: #0f766e;">✏️ تعديل الحالة السريرية</h2>
                        <button type="button" onclick="closeModal('edit-post-modal-{post_id}')" style="background: none; border: none; font-size: 1.4rem; cursor: pointer;">✕</button>
                    </div>
                    <form action="/community/post/edit/{post_id}" method="POST">
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">عنوان الحالة:</label>
                            <input type="text" name="title" value="{p['title']}" required style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                        </div>
                        <div style="margin-bottom: 12px;">
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">جمهور المنشور (الخصوصية):</label>
                            <select name="privacy" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                                <option value="public" {'selected' if post_privacy == 'public' else ''}>🌐 عام (كافة الأطباء)</option>
                                <option value="friends" {'selected' if post_privacy == 'friends' else ''}>👥 الأصدقاء والزملاء فقط</option>
                                <option value="only_me" {'selected' if post_privacy == 'only_me' else ''}>🔒 أنا فقط (سجل خاص)</option>
                            </select>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                            <div>
                                <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">السلالة (Breed):</label>
                                <input type="text" name="breed" value="{p.get('breed','')}" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                            </div>
                            <div>
                                <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">العلامات والأعراض الحيوية:</label>
                                <input type="text" name="symptoms" value="{p.get('symptoms','')}" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                            </div>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">تفاصيل الحالة والفحص الإكلينيكي:</label>
                            <textarea name="content" rows="4" required style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text); line-height: 1.6;">{p['content']}</textarea>
                        </div>
                        <button type="submit" class="btn-fb-primary" style="width: 100%; justify-content: center; padding: 12px;">💾 حفظ التعديلات الآن</button>
                    </form>
                </div>
            </div>
        </div>
        """

    if not posts_cards_html:
        posts_cards_html = """
        <div class="fb-card" style="padding: 40px 20px; text-align: center;">
            <div style="font-size: 3rem; margin-bottom: 10px;">🩺</div>
            <h3 style="margin: 0; color: var(--fb-text); font-size: 1.2rem;">لا توجد منشورات سريرية في هذا القسم حالياً</h3>
            <p style="color: var(--fb-text-muted); font-size: 0.9rem; margin-top: 6px;">كن أول من يشارك حالة سريرية لتبادل الخبرة التشخيصية مع زملائك!</p>
            <button type="button" onclick="openModal('composer-modal')" class="btn-fb-primary" style="margin-top: 10px;">➕ نشر حالة سريرية جديدة</button>
        </div>
        """

    # Species Filter Strip
    species_strip = "".join([f'<a href="/community?species={sp_k}&category={category}&sort={sort}" style="padding: 5px 14px; border-radius: 20px; font-size: 0.80rem; text-decoration: none; font-weight: 700; background: {"#0f766e" if species == sp_k else "var(--fb-card)"}; color: {"white" if species == sp_k else "var(--fb-text)"}; border: 1px solid var(--fb-border); white-space: nowrap;">{sp_name}</a>' for sp_k, sp_name in SPECIES_MAP.items()])

    # Right Sidebar Widgets (Trending & Urgent & Groups)
    c.execute("SELECT id, title, is_urgent, created_at FROM community_posts WHERE is_urgent = 1 ORDER BY id DESC LIMIT 4")
    urgent_cases = [dict(r) for r in c.fetchall()]

    c.execute("SELECT id, name, category, members_count FROM community_groups ORDER BY members_count DESC LIMIT 4")
    sidebar_groups = [dict(r) for r in c.fetchall()]

    c.execute("SELECT id, name, category, followers_count FROM community_pages ORDER BY followers_count DESC LIMIT 4")
    sidebar_pages = [dict(r) for r in c.fetchall()]
    conn.close()

    urgent_sidebar_html = "".join([f'<a href="/community#post-{uc["id"]}" style="display: block; padding: 8px 10px; border-radius: 8px; margin-bottom: 6px; text-decoration: none; background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; font-size: 0.82rem; font-weight: 700; line-height: 1.4;">🚨 {uc["title"][:50]}...</a>' for uc in urgent_cases]) if urgent_cases else "<div style='font-size: 0.78rem; color: var(--fb-text-muted);'>لا توجد حالات طارئة حالياً.</div>"
    groups_sidebar_html = "".join([f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 0.82rem; flex-wrap: wrap; gap: 4px;"><a href="/community?group_id={sg["id"]}" style="font-weight: 700; color: #0f766e; text-decoration: none;">🐾 {sg["name"]}</a><span style="color: var(--fb-text-muted); font-size: 0.75rem;">{sg["members_count"]} عضواً</span></div>' for sg in sidebar_groups])
    pages_sidebar_html = "".join([f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 0.82rem; flex-wrap: wrap; gap: 4px;"><a href="/community?page_id={sp["id"]}" style="font-weight: 700; color: #0f766e; text-decoration: none;">🏥 {sp["name"]}</a><span style="color: var(--fb-text-muted); font-size: 0.75rem;">{sp["followers_count"]} متابع</span></div>' for sp in sidebar_pages])

    feed_layout = f"""
    <div class="fb-main-container">
        <!-- Left Sidebar (Shortcuts & Quick Filters) -->
        <div class="fb-sidebar-col">
            <div class="fb-card" style="padding: 16px;">
                <div style="font-weight: 800; font-size: 0.88rem; color: #0f766e; margin-bottom: 12px;">📁 تصنيفات الحالات</div>
                <div style="display: flex; flex-direction: column; gap: 6px;">
                    <a href="/community" style="padding: 8px 12px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 0.85rem; color: var(--fb-text); background: {'rgba(15,118,110,0.1)' if category == 'all' else 'none'};">🌐 كافة الحالات والمنشورات</a>
                    <a href="/community?category=urgent" style="padding: 8px 12px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 0.85rem; color: #dc2626; background: {'#fee2e2' if category == 'urgent' else 'none'};">🚨 حالات طارئة حرجة</a>
                    <a href="/community?category=case_study" style="padding: 8px 12px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 0.85rem; color: var(--fb-text); background: {'rgba(15,118,110,0.1)' if category == 'case_study' else 'none'};">🩺 استشارات إكلينيكية</a>
                    <a href="/community?category=poll" style="padding: 8px 12px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 0.85rem; color: var(--fb-text); background: {'rgba(15,118,110,0.1)' if category == 'poll' else 'none'};">📊 استطلاعات رأي تشخيصية</a>
                    <a href="/community?category=bookmarks" style="padding: 8px 12px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 0.85rem; color: #d97706; background: {'#fef3c7' if category == 'bookmarks' else 'none'};">🔖 الحالات المحفوظة</a>
                </div>
            </div>

            <div class="fb-card" style="padding: 16px;">
                <div style="font-weight: 800; font-size: 0.88rem; color: #0f766e; margin-bottom: 12px;">🐾 المجموعات النشطة</div>
                {groups_sidebar_html}
                <a href="/community?tab=groups" style="display: block; font-size: 0.8rem; color: #0f766e; font-weight: 700; text-decoration: none; margin-top: 10px;">عرض كافة المجموعات ←</a>
            </div>
        </div>

        <!-- Center Column (Composer & Feed Stream) -->
        <div style="min-width: 0;">
            <!-- Stories Strip -->
            {stories_html}

            <!-- Facebook-Style Quick Composer Box -->
            <div class="fb-card" style="padding: 14px; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <div style="width: 42px; height: 42px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; font-weight: 800; flex-shrink: 0;">
                        {user.get('name','ط')[0] if user else 'ط'}
                    </div>
                    <div onclick="openModal('composer-modal')" style="flex: 1; min-width: 0; background: var(--fb-bg); border: 1px solid var(--fb-border); border-radius: 24px; padding: 10px 16px; color: var(--fb-text-muted); cursor: pointer; font-size: 0.92rem; word-break: break-word;">
                        ما هي الحالة السريرية أو الاستشارة التي تريد طرحها اليوم يا دكتور؟
                    </div>
                </div>
                <div style="display: flex; border-top: 1px solid var(--fb-border); padding-top: 10px; gap: 8px;">
                    <button type="button" onclick="openModal('composer-modal')" class="fb-action-btn">
                        <span>📷</span> <span>صور وأشعة</span>
                    </button>
                    <button type="button" onclick="openModal('composer-modal')" class="fb-action-btn">
                        <span>🚨</span> <span>حالة طارئة</span>
                    </button>
                    <button type="button" onclick="openModal('composer-modal')" class="fb-action-btn">
                        <span>📊</span> <span>استطلاع رأي</span>
                    </button>
                </div>
            </div>

            <!-- Species Filter Strip -->
            <div style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 14px; scrollbar-width: none;">
                {species_strip}
            </div>

            <!-- Stream of Post Cards -->
            <div id="posts-stream">
                {posts_cards_html}
            </div>
        </div>

        <!-- Right Sidebar (Urgent & Pages) -->
        <div class="fb-sidebar-col">
            <div class="fb-card" style="padding: 16px;">
                <div style="font-weight: 800; font-size: 0.88rem; color: #dc2626; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
                    <span>🚨</span> <span>حالات سريرية عاجلة (Live Triage)</span>
                </div>
                {urgent_sidebar_html}
            </div>

            <div class="fb-card" style="padding: 16px;">
                <div style="font-weight: 800; font-size: 0.88rem; color: #0f766e; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
                    <span>🏢</span> <span>مراكز وعيادات موثقة</span>
                </div>
                {pages_sidebar_html}
                <a href="/community?tab=pages" style="display: block; font-size: 0.8rem; color: #0f766e; font-weight: 700; text-decoration: none; margin-top: 10px;">استكشاف كافة الصفحات ←</a>
            </div>
        </div>
    </div>

    <!-- Create Post Modal (Full Feature Composer) -->
    <div id="composer-modal" class="fb-modal-overlay">
        <div class="fb-modal-box">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--fb-border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
                <h2 style="margin: 0; font-size: 1.25rem; color: #0f766e;">🩺 نشر استشارة / حالة سريرية جديدة</h2>
                <button type="button" onclick="closeModal('composer-modal')" style="background: none; border: none; font-size: 1.4rem; cursor: pointer;">✕</button>
            </div>

            <form action="/community/post" method="POST" enctype="multipart/form-data" id="composer-form">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">عنوان الحالة أو الاستشارة:</label>
                    <input type="text" name="title" required placeholder="مثال: اشتباه التهاب صفاق معدي (FIP) في قط شيرازي عمره 8 شهور" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">جمهور المنشور (الخصوصية):</label>
                        <select name="privacy" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                            <option value="public">🌐 عام (كافة الأطباء والمستخدمين)</option>
                            <option value="friends">👥 الأصدقاء والزملاء المتصلين فقط</option>
                            <option value="only_me">🔒 أنا فقط (سجل سريري شخصي)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">أولوية الحالة:</label>
                        <select name="is_urgent" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                            <option value="0">استشارة عادية / تبادل خبرة</option>
                            <option value="1">🚨 حالة طارئة حرجة (Urgent Priority)</option>
                        </select>
                    </div>
                </div>

                <!-- Clinical Demographics -->
                <div style="background: var(--fb-bg); border: 1px solid var(--fb-border); border-radius: 12px; padding: 12px; margin-bottom: 12px;">
                    <div style="font-weight: 800; font-size: 0.85rem; color: #0f766e; margin-bottom: 8px;">📋 البيانات السريرية والديموغرافية:</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px;">
                        <div>
                            <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 2px;">الفصيلة:</label>
                            <select name="species" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                                <option value="pets">حيوانات أليفة (كلاب وقطط)</option>
                                <option value="bovine">مجترات (أبقار وجاموس)</option>
                                <option value="equine">خيول وبغال</option>
                                <option value="ovine">أغنام وماعز</option>
                                <option value="poultry">دواجن وطيور</option>
                                <option value="wild">برية وغريبة</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 2px;">السلالة (Breed):</label>
                            <input type="text" name="breed" placeholder="شيرازي، هولشتاين..." style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 8px;">
                        <div>
                            <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 2px;">العمر:</label>
                            <input type="text" name="age" placeholder="سنتان / 6 شهور" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                        </div>
                        <div>
                            <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 2px;">الوزن (كجم):</label>
                            <input type="text" name="weight" placeholder="4.5" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                        </div>
                        <div>
                            <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 2px;">الجنس:</label>
                            <select name="gender" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                                <option value="ذكر">ذكر</option>
                                <option value="أنثى">أنثى</option>
                            </select>
                        </div>
                    </div>
                    <div style="margin-bottom: 8px;">
                        <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 2px;">الأعراض والعلامات الحيوية:</label>
                        <input type="text" name="symptoms" placeholder="حرارة 40.2، خمول حاد، استسقاء بطني..." style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                    </div>
                    <div>
                        <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 2px;">الأدوية المعطاة مسبقاً:</label>
                        <input type="text" name="medications" placeholder="أوكسيتتراسيكلين، فلونيكسين..." style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                    </div>
                </div>

                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">تفاصيل الفحص السريري والاستشارة:</label>
                    <textarea name="content" required rows="4" placeholder="اكتب وصفاً وافياً للحالة والتاريخ المرضي والتشخيص المقترح..." style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text); line-height: 1.6;"></textarea>
                </div>

                <!-- Multiple Media Upload -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.82rem;">📷 إرفاق صور / أشعة / فيديو (يمكن اختيار عدة ملفات):</label>
                        <input type="file" name="media_files" id="composer-media-files" multiple accept="image/*,video/*" style="width: 100%; font-size: 0.82rem;">
                        <div id="composer-media-preview" style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px;"></div>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.82rem;">🎥 أو رابط فيديو يوتيوب:</label>
                        <input type="url" name="youtube_url" placeholder="https://youtube.com/watch?v=..." style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-bg); color: var(--fb-text);">
                    </div>
                </div>

                <button type="submit" class="btn-fb-primary" style="width: 100%; justify-content: center; padding: 12px; font-size: 1rem;">🚀 نشر الحالة السريرية وتعميمها الآن</button>
            </form>
        </div>
    </div>

    <!-- Dedicated Facebook-Grade Interactive Story Viewer Modal -->
    <div id="story-viewer-modal" class="fb-modal-overlay" style="display: none; align-items: center; justify-content: center; z-index: 999999; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px);">
        <div style="position: relative; width: 100%; max-width: 520px; margin: 0 auto; padding: 16px; box-sizing: border-box; display: flex; flex-direction: column; max-height: 96vh;">
            
            <!-- Top Bar inside story -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 42px; height: 42px; border-radius: 50%; background: #0f766e; border: 2px solid #14b8a6; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem;">
                        🩺
                    </div>
                    <div>
                        <div id="story-viewer-author" style="color: white; font-weight: 800; font-size: 0.95rem; text-shadow: 0 1px 3px rgba(0,0,0,0.8);">د. طبيب بيطري</div>
                        <div id="story-viewer-time" style="color: #94a3b8; font-size: 0.75rem;">الآن</div>
                    </div>
                </div>

                <div style="display: flex; align-items: center; gap: 8px;">
                    <button type="button" id="story-viewer-del-btn" onclick="deleteCurrentStory()" class="btn-fb-danger" style="display: none; padding: 4px 10px; font-size: 0.75rem; border-radius: 8px;">🗑️ حذف</button>
                    <button type="button" onclick="closeStoryViewer()" style="background: rgba(255,255,255,0.2); border: none; color: white; width: 34px; height: 34px; border-radius: 50%; font-size: 1.2rem; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;">✕</button>
                </div>
            </div>

            <!-- Media Container -->
            <div id="story-viewer-media-container" style="display: flex; align-items: center; justify-content: center; min-height: 280px; max-height: 65vh; overflow: hidden; margin-bottom: 12px;"></div>

            <!-- Full Caption Box (الكلام أسفل القصة) -->
            <div id="story-viewer-caption-box" style="display: none; background: rgba(15, 23, 42, 0.88); border: 1px solid rgba(255,255,255,0.18); border-radius: 12px; padding: 12px 16px; margin-bottom: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.4);">
                <div style="font-size: 0.75rem; color: #14b8a6; font-weight: 700; margin-bottom: 4px;">💬 تعليق وسؤال الحالة السريرية:</div>
                <div id="story-viewer-caption-text" style="color: #ffffff; font-size: 0.95rem; line-height: 1.6; word-break: break-word; font-weight: 600;"></div>
            </div>

            <!-- Interactive Reaction & Engagement Bar (التفاعل مع القصة) -->
            <div style="background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(255,255,255,0.15); border-radius: 30px; padding: 8px 14px; display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap;">
                <button type="button" id="story-like-btn" onclick="likeCurrentStory()" style="background: #e11d48; color: white; border: none; border-radius: 20px; padding: 6px 14px; font-weight: 800; font-size: 0.82rem; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: transform 0.2s ease;">
                    <span>❤️</span> <span>إعجاب ودعم</span> (<span id="story-viewer-likes-count">0</span>)
                </button>

                <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                    <button type="button" onclick="sendStoryReaction('💡 تشخيص دقيق')" style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); color: white; border-radius: 16px; padding: 5px 10px; font-size: 0.75rem; cursor: pointer; font-weight: 700;">💡 تشخيص</button>
                    <button type="button" onclick="sendStoryReaction('🩺 استشارة')" style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); color: white; border-radius: 16px; padding: 5px 10px; font-size: 0.75rem; cursor: pointer; font-weight: 700;">🩺 استشارة</button>
                    <button type="button" onclick="sendStoryReaction('👏 رائع')" style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); color: white; border-radius: 16px; padding: 5px 10px; font-size: 0.75rem; cursor: pointer; font-weight: 700;">👏 رائع</button>
                </div>
            </div>

        </div>
    </div>

    <!-- Create Story Modal -->
    <div id="create-story-modal" class="fb-modal-overlay">
        <div class="fb-modal-box">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--fb-border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
                <h2 style="margin: 0; font-size: 1.25rem; color: #0f766e;">📸 نشر قصة سريرية سريعة (Story)</h2>
                <button type="button" onclick="closeModal('create-story-modal')" style="background: none; border: none; font-size: 1.4rem; cursor: pointer;">✕</button>
            </div>
            <form action="/community/story/create" method="POST" enctype="multipart/form-data">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">اختر صورة أو فيديو الحالة:</label>
                    <input type="file" name="story_media" required accept="image/*,video/*" style="width: 100%; font-size: 0.85rem;">
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">تعليق أو سؤال سريع على القصة:</label>
                    <input type="text" name="caption" placeholder="مثال: من يتعرف على هذه الآفة في الأذن؟" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                </div>
                <button type="submit" class="btn-fb-primary" style="width: 100%; justify-content: center; padding: 12px;">نشر القصة السريرية (تختفي بعد 24 ساعة)</button>
            </form>
        </div>
    </div>

    <!-- Content Reporting Modal -->
    <div id="report-modal" class="fb-modal-overlay">
        <div class="fb-modal-box">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--fb-border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
                <h2 style="margin: 0; font-size: 1.25rem; color: #dc2626;">🚩 إبلاغ عن محتوى أو مخالفة مهنية</h2>
                <button type="button" onclick="closeModal('report-modal')" style="background: none; border: none; font-size: 1.4rem; cursor: pointer;">✕</button>
            </div>
            <form onsubmit="submitReportForm(event)">
                <input type="hidden" name="target_type" id="report-target-type" value="post">
                <input type="hidden" name="target_id" id="report-target-id" value="0">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">سبب البلاغ:</label>
                    <select name="reason" required style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                        <option value="معلومات طبية خاطئة أو بروتوكول دوائي خطير">معلومات طبية خاطئة أو بروتوكول دوائي خطير</option>
                        <option value="محتوى غير لائق أو مخالف لأخلاقيات المهنة البيطرية">محتوى غير لائق أو مخالف لأخلاقيات المهنة البيطرية</option>
                        <option value="إساءة أو تنمر أو مضايقة لزميل">إساءة أو تنمر أو مضايقة لزميل</option>
                        <option value="إعلانات تجارية مضللة أو سبام">إعلانات تجارية مضللة أو سبام</option>
                    </select>
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">تفاصيل إضافية لمساعدة المشرفين:</label>
                    <textarea name="details" rows="3" placeholder="وضح باختصار وجه المخالفة..." style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);"></textarea>
                </div>
                <button type="submit" class="btn-fb-danger" style="width: 100%; justify-content: center; padding: 12px;">إرسال البلاغ لفريق الإشراف</button>
            </form>
        </div>
    </div>

    <!-- Image Viewer Modal -->
    <div id="image-modal" class="fb-modal-overlay" onclick="closeModal('image-modal')">
        <div style="max-width: 90vw; max-height: 90vh;">
            <img src="" id="image-modal-src" style="max-width: 100%; max-height: 90vh; border-radius: 8px; object-fit: contain;">
        </div>
    </div>
    """

    body = f"{COMMUNITY_CSS}<div class='fb-app-wrapper'>{subnav_strip}{feed_layout}</div>{COMMUNITY_JS}"
    return HTMLResponse(content=get_base_html("VetBook - شبكة الأطباء البيطريين", body, user, lang), media_type="text/html; charset=utf-8")



# ==============================================================================
# ACTION ROUTES: POSTS, COMMENTS, REACTIONS, SHARING, REPORTING, SOCIAL GRAPH
# ==============================================================================

@router.post("/community/post")
@router.post("/community/post/create")
async def community_create_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form("case_study"),
    is_urgent: int = Form(0),
    privacy: str = Form("public"),
    species: str = Form(""),
    breed: str = Form(""),
    age: str = Form(""),
    weight: str = Form(""),
    gender: str = Form(""),
    symptoms: str = Form(""),
    medications: str = Form(""),
    group_id: int = Form(0),
    page_id: int = Form(0),
    youtube_url: str = Form(""),
    media_files: list[UploadFile] = File(None)
):
    from app import get_current_user

    import base64
    user = get_current_user(request)
    author_id = user["id"] if user else 4
    author_name = user.get("name", "طبيب بيطري") if user else "طبيب بيطري"
    author_spec = (user.get("specialty") or user.get("role") or "طب وجراحة الحيوان") if user else "طب وجراحة الحيوان"
    author_country = user.get("country", "مصر") if user else "مصر"

    primary_img = None
    extra_imgs = []
    saved_video = None
    media_type = "text"

    if youtube_url and youtube_url.strip():
        saved_video = extract_youtube_embed(youtube_url.strip())
        if saved_video:
            media_type = "video"

    if media_files:
        for mf in media_files:
            if not mf or not mf.filename:
                continue
            ext = os.path.splitext(mf.filename)[1].lower()
            content_type = (getattr(mf, "content_type", "") or "").lower()
            try:
                raw_bytes = await mf.read()
            except Exception:
                continue
            if not raw_bytes or len(raw_bytes) < 4:
                continue

            is_img = (
                content_type.startswith("image/") or 
                ext in [".jpg", ".jpeg", ".jfif", ".png", ".webp", ".gif", ".bmp", ".svg", ".heic", ".heif", ".avif"]
            )
            is_vid = (
                content_type.startswith("video/") or 
                ext in [".mp4", ".webm", ".mov", ".mkv", ".avi", ".3gp", ".m4v"]
            )

            if is_img:
                fname = f"post_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}{ext if ext else '.jpg'}"
                # Save to disk
                for d in [UPLOAD_DIR, os.path.join(BASE_DIR, "uploads")]:
                    if os.path.exists(d) and os.access(d, os.W_OK):
                        try:
                            with open(os.path.join(d, fname), "wb") as buf:
                                buf.write(raw_bytes)
                        except Exception:
                            pass

                # Build optimized Base64 Data URI for serverless durability (Vercel)
                img_data_uri = None
                try:
                    from PIL import Image, ImageOps
                    import io
                    im = Image.open(io.BytesIO(raw_bytes))
                    im = ImageOps.exif_transpose(im)
                    if im.mode in ("RGBA", "P"):
                        im = im.convert("RGB")
                    max_dim = 1200
                    if max(im.size) > max_dim:
                        im.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                    out = io.BytesIO()
                    im.save(out, format="JPEG", quality=82, optimize=True)
                    c_bytes = out.getvalue()
                    img_data_uri = f"data:image/jpeg;base64,{base64.b64encode(c_bytes).decode('ascii')}"
                except Exception:
                    if len(raw_bytes) <= 1.5 * 1024 * 1024:
                        mime = content_type if content_type.startswith("image/") else "image/jpeg"
                        img_data_uri = f"data:{mime};base64,{base64.b64encode(raw_bytes).decode('ascii')}"
                    else:
                        img_data_uri = fname

                final_img_ref = img_data_uri or fname
                if not primary_img:
                    primary_img = final_img_ref
                    media_type = "image"
                else:
                    extra_imgs.append(final_img_ref)

            elif is_vid and not saved_video:
                fname = f"vid_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}{ext if ext else '.mp4'}"
                for d in [UPLOAD_DIR, os.path.join(BASE_DIR, "uploads")]:
                    if os.path.exists(d) and os.access(d, os.W_OK):
                        try:
                            with open(os.path.join(d, fname), "wb") as buf:
                                buf.write(raw_bytes)
                        except Exception:
                            pass
                if len(raw_bytes) <= 3 * 1024 * 1024:
                    mime = content_type if content_type.startswith("video/") else "video/mp4"
                    saved_video = f"data:{mime};base64,{base64.b64encode(raw_bytes).decode('ascii')}"
                else:
                    saved_video = fname
                media_type = "video"

    eval_res = evaluate_clinical_content(title, content, bool(primary_img or saved_video), bool(is_urgent), bool(species or symptoms))
    quality_score = eval_res["score"]

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_posts (
        user_id, author_name, author_specialty, author_country,
        category, title, content, is_urgent, privacy, species, breed, age, weight,
        gender, symptoms, medications, group_id, page_id, image_path, extra_images, video_path,
        media_type, quality_score, virality_score, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 5.0, ?)
    """, (
        author_id, author_name, author_spec, author_country,
        category, title.strip(), content.strip(), is_urgent, privacy, species, breed, age, weight,
        gender, symptoms, medications, group_id, page_id, primary_img, (json.dumps(extra_imgs, ensure_ascii=False) if extra_imgs else ""), saved_video,
        media_type, quality_score, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    post_id = c.lastrowid

    # Broadcast notification to all colleagues
    try:
        c.execute("""
        INSERT INTO broadcast_notifications (title, message, target_country, badge_type, created_at)
        VALUES (?, ?, 'الكل', 'clinical_case', ?)
        """, (
            f"📢 حالة ومنشور سريري جديد من د. {author_name}",
            f"{title[:90]} - متاح الآن للمناقشة وتبادل الرأي في شبكة VetBook",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
    except Exception:
        pass

    conn.commit()
    conn.close()

    post_record = {
        "id": post_id,
        "user_id": author_id,
        "author_name": author_name,
        "author_specialty": author_spec,
        "author_country": author_country,
        "category": category,
        "title": title.strip(),
        "content": content.strip(),
        "is_urgent": is_urgent,
        "privacy": privacy,
        "species": species,
        "breed": breed,
        "age": age,
        "weight": weight,
        "gender": gender,
        "symptoms": symptoms,
        "medications": medications,
        "group_id": group_id,
        "page_id": page_id,
        "image_path": primary_img,
        "extra_images": (json.dumps(extra_imgs, ensure_ascii=False) if extra_imgs else ""),
        "video_path": saved_video,
        "media_type": media_type,
        "quality_score": quality_score,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_post_to_backup_sync(post_record)

    return RedirectResponse(f"/community?posted=1#post-{post_id}", status_code=303)


@router.post("/community/post/edit/{post_id}")
async def community_edit_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    content: str = Form(...),
    privacy: str = Form("public"),
    breed: str = Form(""),
    symptoms: str = Form("")
):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM community_posts WHERE id = ?", (post_id,))
    row = c.fetchone()
    if not row or (row["user_id"] != user["id"] and not user.get("is_admin") and user.get("role") != "admin"):
        conn.close()
        return RedirectResponse("/community", status_code=303)

    c.execute("""
    UPDATE community_posts
    SET title = ?, content = ?, privacy = ?, breed = ?, symptoms = ?, is_edited = 1, updated_at = ?
    WHERE id = ?
    """, (title.strip(), content.strip(), privacy, breed.strip(), symptoms.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), post_id))
    conn.commit()
    conn.close()

    return RedirectResponse(f"/community#post-{post_id}", status_code=303)


@router.post("/community/post/delete/{post_id}")
async def community_delete_post(request: Request, post_id: int):
    from app import get_current_user
    user = get_current_user(request)
    current_user_id = user["id"] if user else 4
    is_admin = bool(user and (user.get("is_admin") or user.get("role") == "admin"))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, user_id, title FROM community_posts WHERE id = ?", (post_id,))
    p = c.fetchone()
    if not p:
        conn.close()
        if request.headers.get("accept") == "application/json" or request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({"success": False, "error": "المنشور غير موجود"}, status_code=404)
        return RedirectResponse("/community", status_code=303)

    # Allow delete if admin, post author, or guest author
    if not (is_admin or p["user_id"] == current_user_id or not user):
        conn.close()
        if request.headers.get("accept") == "application/json" or request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({"success": False, "error": "غير مصرح لك بحذف هذا المنشور"}, status_code=403)
        return RedirectResponse("/community", status_code=303)

    post_title = p["title"]
    c.execute("DELETE FROM community_posts WHERE id = ?", (post_id,))
    c.execute("DELETE FROM community_comments WHERE post_id = ?", (post_id,))
    c.execute("DELETE FROM community_likes WHERE post_id = ?", (post_id,))
    c.execute("DELETE FROM community_bookmarks WHERE post_id = ?", (post_id,))
    try:
        c.execute("DELETE FROM community_reports WHERE target_type = 'post' AND target_id = ?", (post_id,))
    except Exception:
        pass
    conn.commit()
    conn.close()

    delete_post_from_backup_sync(post_id, post_title)

    if request.headers.get("accept") == "application/json" or request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({"success": True, "post_id": post_id, "message": "تم حذف المنشور نهائياً بنجاح"})
    return RedirectResponse("/community", status_code=303)


@router.post("/community/post/share/{post_id}")
async def community_share_post(request: Request, post_id: int):
    from app import get_current_user
    user = get_current_user(request)
    current_user_id = user["id"] if user else 4
    actor_name = user.get("name", "طبيب زميل") if user else "طبيب زميل"
    actor_avatar = user.get("avatar_image", "") if user else ""

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_posts SET shares_count = shares_count + 1 WHERE id = ?", (post_id,))
    c.execute("SELECT user_id, title FROM community_posts WHERE id = ?", (post_id,))
    p = c.fetchone()
    if p and p["user_id"] != current_user_id:
        create_notification(
            conn,
            user_id=p["user_id"],
            actor_id=current_user_id,
            actor_name=actor_name,
            actor_avatar=actor_avatar,
            action_type="post_share",
            message="قام بمشاركة حالتك السريرية مع زملائه في الشبكة",
            post_id=post_id
        )
    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/like/{post_id}")
async def community_toggle_like(request: Request, post_id: int, reaction: str = Form("like")):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4
    actor_name = user.get("name", "طبيب زميل") if user else "طبيب زميل"
    actor_avatar = user.get("avatar_image", "") if user else ""

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, reaction_type FROM community_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
    existing = c.fetchone()

    liked = True
    if existing:
        if existing["reaction_type"] == reaction:
            c.execute("DELETE FROM community_likes WHERE id = ?", (existing["id"],))
            liked = False
        else:
            c.execute("UPDATE community_likes SET reaction_type = ? WHERE id = ?", (reaction, existing["id"]))
    else:
        c.execute("INSERT INTO community_likes (post_id, user_id, reaction_type, created_at) VALUES (?, ?, ?, ?)",
                  (post_id, user_id, reaction, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    # Update counters
    c.execute("SELECT count(*) FROM community_likes WHERE post_id = ?", (post_id,))
    likes_count = c.fetchone()[0]
    c.execute("UPDATE community_posts SET likes_count = ? WHERE id = ?", (likes_count, post_id))

    # Send notification if new reaction
    if liked:
        c.execute("SELECT user_id, title FROM community_posts WHERE id = ?", (post_id,))
        p = c.fetchone()
        if p and p["user_id"] != user_id:
            r_label = REACTIONS.get(reaction, {}).get("label", "إعجاب")
            r_icon = REACTIONS.get(reaction, {}).get("icon", "👍")
            create_notification(
                conn,
                user_id=p["user_id"],
                actor_id=user_id,
                actor_name=actor_name,
                actor_avatar=actor_avatar,
                action_type="post_reaction",
                message=f"تفاعل ({r_icon} {r_label}) مع استشارتك السريرية",
                post_id=post_id
            )

    conn.commit()
    conn.close()

    return JSONResponse({"success": True, "liked": liked, "likes_count": likes_count, "reaction": reaction})


@router.post("/community/comment/{post_id}")
async def community_add_comment(
    request: Request,
    post_id: int,
    content: str = Form(...),
    parent_id: int = Form(0)
):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4
    author_name = user.get("name", "طبيب بيطري") if user else "طبيب بيطري"
    author_spec = user.get("specialty") or user.get("role") or "طب وجراحة الحيوان"
    author_country = user.get("country", "مصر") if user else "مصر"
    actor_avatar = user.get("avatar_image", "") if user else ""

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_comments (post_id, user_id, author_name, author_specialty, author_country, content, parent_comment_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (post_id, user_id, author_name, author_spec, author_country, content.strip(), parent_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    cm_id = c.lastrowid

    # Update comments counter on post
    c.execute("UPDATE community_posts SET comments_count = comments_count + 1 WHERE id = ?", (post_id,))

    # Notification handling
    if parent_id and parent_id > 0:
        c.execute("SELECT user_id FROM community_comments WHERE id = ?", (parent_id,))
        parent_cm = c.fetchone()
        if parent_cm and parent_cm["user_id"] != user_id:
            create_notification(
                conn,
                user_id=parent_cm["user_id"],
                actor_id=user_id,
                actor_name=author_name,
                actor_avatar=actor_avatar,
                action_type="comment_reply",
                message="رد على رأيك السريري في المناقشة",
                post_id=post_id,
                comment_id=cm_id
            )
    else:
        c.execute("SELECT user_id, title FROM community_posts WHERE id = ?", (post_id,))
        p = c.fetchone()
        if p and p["user_id"] != user_id:
            create_notification(
                conn,
                user_id=p["user_id"],
                actor_id=user_id,
                actor_name=author_name,
                actor_avatar=actor_avatar,
                action_type="post_comment",
                message="أضاف تشخيصاً ورأياً سريرياً على حالتك",
                post_id=post_id,
                comment_id=cm_id
            )

    conn.commit()
    conn.close()

    if request.headers.get("accept") == "application/json":
        return JSONResponse({"success": True, "comment_id": cm_id})
    return RedirectResponse(f"/community#post-{post_id}", status_code=303)


@router.post("/community/comment/delete/{comment_id}")
async def community_delete_comment(request: Request, comment_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    SELECT c.user_id, c.post_id, p.user_id as post_author_id
    FROM community_comments c
    JOIN community_posts p ON c.post_id = p.id
    WHERE c.id = ?
    """, (comment_id,))
    cm = c.fetchone()
    if not cm:
        conn.close()
        return JSONResponse({"error": "not found"}, status_code=404)

    if user["id"] == cm["user_id"] or user["id"] == cm["post_author_id"] or user.get("is_admin") or user.get("role") == "admin":
        c.execute("DELETE FROM community_comments WHERE id = ? OR parent_comment_id = ?", (comment_id, comment_id))
        c.execute("UPDATE community_posts SET comments_count = (SELECT count(*) FROM community_comments WHERE post_id = ?) WHERE id = ?", (cm["post_id"], cm["post_id"]))
        conn.commit()
        conn.close()
        return JSONResponse({"success": True})

    conn.close()
    return JSONResponse({"error": "forbidden"}, status_code=403)


@router.post("/community/comment/best/{comment_id}")
async def community_mark_best_comment(request: Request, comment_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    SELECT c.id, c.user_id, c.post_id, p.user_id as post_author_id
    FROM community_comments c
    JOIN community_posts p ON c.post_id = p.id
    WHERE c.id = ?
    """, (comment_id,))
    row = c.fetchone()
    if not row or row["post_author_id"] != user["id"]:
        conn.close()
        return JSONResponse({"error": "unauthorized"}, status_code=403)

    c.execute("UPDATE community_comments SET is_best_answer = 0 WHERE post_id = ?", (row["post_id"],))
    c.execute("UPDATE community_comments SET is_best_answer = 1 WHERE id = ?", (comment_id,))
    c.execute("UPDATE community_posts SET has_best_answer = 1 WHERE id = ?", (row["post_id"],))
    c.execute("UPDATE users SET reputation_score = reputation_score + 50 WHERE id = ?", (row["user_id"],))

    # Send Notification to Doctor
    create_notification(
        conn,
        user_id=row["user_id"],
        actor_id=user["id"],
        actor_name=user.get("name", "طبيب زميل"),
        actor_avatar=user.get("avatar_image", ""),
        action_type="best_diagnosis",
        message="اعتمد تشخيصك السريري كـ 'أفضل تشخيص معتمد' ومنحك +50 نقطة سمعة! 🏆",
        post_id=row["post_id"],
        comment_id=comment_id
    )

    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/bookmark/{post_id}")
async def community_toggle_bookmark(request: Request, post_id: int):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_bookmarks WHERE user_id = ? AND post_id = ?", (user_id, post_id))
    b = c.fetchone()

    bookmarked = True
    if b:
        c.execute("DELETE FROM community_bookmarks WHERE id = ?", (b["id"],))
        bookmarked = False
    else:
        c.execute("INSERT INTO community_bookmarks (user_id, post_id, created_at) VALUES (?, ?, ?)",
                  (user_id, post_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "bookmarked": bookmarked})


@router.post("/community/poll/vote/{post_id}")
async def community_vote_poll(request: Request, post_id: int, opt_id: int = Form(...)):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT poll_data FROM community_posts WHERE id = ?", (post_id,))
    row = c.fetchone()
    if not row or not row["poll_data"]:
        conn.close()
        return JSONResponse({"error": "poll not found"}, status_code=404)

    try:
        data = json.loads(row["poll_data"])
        options = data.get("options", [])
        for opt in options:
            if opt["id"] == opt_id:
                opt["votes"] = opt.get("votes", 0) + 1
        new_poll = json.dumps(data)
        c.execute("UPDATE community_posts SET poll_data = ? WHERE id = ?", (new_poll, post_id))
        conn.commit()
    except Exception as e:
        conn.close()
        return JSONResponse({"error": str(e)}, status_code=500)

    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/story/create")
async def community_create_story(
    request: Request,
    story_media: UploadFile = File(...),
    caption: str = Form("")
):
    import base64
    from app import get_current_user
    user = get_current_user(request)
    author_id = user["id"] if user else 4
    author_name = user.get("name", "طبيب بيطري") if user else "طبيب بيطري"
    if not story_media or not story_media.filename:
        return RedirectResponse("/community", status_code=303)

    ext = (os.path.splitext(story_media.filename)[1] or ".jpg").lower()
    content_type = (getattr(story_media, "content_type", "") or "").lower()
    saved_name = f"story_{int(datetime.now().timestamp())}_{author_id}{ext}"
    try:
        raw_bytes = await story_media.read()
    except Exception:
        return RedirectResponse("/community", status_code=303)

    # Save to disk
    for d in [UPLOAD_DIR, os.path.join(BASE_DIR, "uploads")]:
        if os.path.exists(d) and os.access(d, os.W_OK):
            try:
                with open(os.path.join(d, saved_name), "wb") as buf:
                    buf.write(raw_bytes)
            except Exception:
                pass

    media_ref = saved_name
    is_img = content_type.startswith("image/") or ext in [".jpg", ".jpeg", ".jfif", ".png", ".webp", ".gif", ".bmp"]
    if is_img:
        try:
            from PIL import Image, ImageOps
            import io
            im = Image.open(io.BytesIO(raw_bytes))
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            max_dim = 1000
            if max(im.size) > max_dim:
                im.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            im.save(out, format="JPEG", quality=80, optimize=True)
            media_ref = f"data:image/jpeg;base64,{base64.b64encode(out.getvalue()).decode('ascii')}"
        except Exception:
            if len(raw_bytes) <= 1.5 * 1024 * 1024:
                media_ref = f"data:image/jpeg;base64,{base64.b64encode(raw_bytes).decode('ascii')}"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    author_spec = (user.get("specialty") or user.get("role") or "طب وجراحة الحيوان") if user else "طب وجراحة الحيوان"
    author_avatar = user.get("avatar_image", "") if user else ""

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_stories (user_id, author_name, author_specialty, author_avatar, media_url, caption, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        author_id,
        author_name,
        author_spec,
        author_avatar,
        media_ref,
        caption.strip(),
        now_str
    ))
    story_id = c.lastrowid
    conn.commit()
    conn.close()

    story_record = {
        "id": story_id,
        "user_id": author_id,
        "author_name": author_name,
        "author_specialty": author_spec,
        "author_avatar": author_avatar,
        "media_url": media_ref,
        "caption": caption.strip(),
        "likes_count": 0,
        "created_at": now_str
    }
    save_story_to_backup_sync(story_record)

    return RedirectResponse("/community?story_posted=1", status_code=303)


@router.post("/community/story/like/{story_id}")
async def community_like_story(request: Request, story_id: int):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_stories WHERE id = ?", (story_id,))
    if not c.fetchone():
        conn.close()
        return JSONResponse({"success": False, "error": "القصة غير موجودة"}, status_code=404)
    
    c.execute("SELECT id FROM community_story_likes WHERE story_id = ? AND user_id = ?", (story_id, user_id))
    existing = c.fetchone()
    if existing:
        c.execute("DELETE FROM community_story_likes WHERE id = ?", (existing[0],))
        c.execute("UPDATE community_stories SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (story_id,))
        liked = False
    else:
        c.execute("INSERT OR REPLACE INTO community_story_likes (story_id, user_id, reaction_type, created_at) VALUES (?, ?, 'like', ?)",
                  (story_id, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("UPDATE community_stories SET likes_count = likes_count + 1 WHERE id = ?", (story_id,))
        liked = True
    
    c.execute("SELECT likes_count FROM community_stories WHERE id = ?", (story_id,))
    new_count = c.fetchone()[0]
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "liked": liked, "likes_count": new_count})


@router.post("/community/story/delete/{story_id}")
async def community_delete_story(request: Request, story_id: int):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4
    is_admin = bool(user and (user.get("is_admin") or user.get("role") == "admin"))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, user_id FROM community_stories WHERE id = ?", (story_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return JSONResponse({"success": False, "error": "القصة غير موجودة"}, status_code=404)
    if not (is_admin or row[1] == user_id or not user):
        conn.close()
        return JSONResponse({"success": False, "error": "غير مصرح لك بحذف هذه القصة"}, status_code=403)
    
    c.execute("DELETE FROM community_stories WHERE id = ?", (story_id,))
    c.execute("DELETE FROM community_story_likes WHERE story_id = ?", (story_id,))
    conn.commit()
    conn.close()

    for s_file in [BACKUP_STORIES_FILE, STATIC_STORIES_FILE]:
        if os.path.exists(s_file):
            try:
                with open(s_file, "r", encoding="utf-8-sig") as f:
                    stories = json.load(f)
                if isinstance(stories, list):
                    stories = [s for s in stories if s.get("id") != story_id]
                    with open(s_file, "w", encoding="utf-8") as f:
                        json.dump(stories, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    return JSONResponse({"success": True, "message": "تم حذف القصة بنجاح"})



# ==============================================================================
# SOCIAL GRAPH: FRIENDS, FOLLOWS, BLOCKS & REPORTS
# ==============================================================================

@router.post("/community/friends/request/{target_id}")
async def community_send_friend_request(request: Request, target_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    if user["id"] == target_id:
        return JSONResponse({"error": "cannot friend self"}, status_code=400)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    SELECT id, status FROM community_friends
    WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
    """, (user["id"], target_id, target_id, user["id"]))
    existing = c.fetchone()
    if existing:
        conn.close()
        return JSONResponse({"error": "طلب صداقة أو صلة موجودة مسبقاً"}, status_code=400)

    c.execute("""
    INSERT INTO community_friends (sender_id, receiver_id, status, created_at)
    VALUES (?, ?, 'pending', ?)
    """, (user["id"], target_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    # Notify target
    create_notification(
        conn,
        user_id=target_id,
        actor_id=user["id"],
        actor_name=user.get("name", "طبيب زميل"),
        actor_avatar=user.get("avatar_image", ""),
        action_type="friend_request",
        message="أرسل لك طلب صداقة وزمالة مهنية"
    )

    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/friends/accept/{request_id}")
async def community_accept_friend_request(request: Request, request_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, sender_id, receiver_id FROM community_friends WHERE id = ?", (request_id,))
    row = c.fetchone()
    if not row or row["receiver_id"] != user["id"]:
        conn.close()
        return JSONResponse({"error": "unauthorized or not found"}, status_code=403)

    c.execute("UPDATE community_friends SET status = 'accepted', updated_at = ? WHERE id = ?",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), request_id))

    # Notify sender
    create_notification(
        conn,
        user_id=row["sender_id"],
        actor_id=user["id"],
        actor_name=user.get("name", "طبيب زميل"),
        actor_avatar=user.get("avatar_image", ""),
        action_type="friend_accepted",
        message="قبل طلب صداقتك وأصبح زميلاً في شبكتك المهنية"
    )

    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/friends/reject/{request_id}")
async def community_reject_friend_request(request: Request, request_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM community_friends WHERE id = ? AND receiver_id = ?", (request_id, user["id"]))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/friends/cancel/{target_id}")
async def community_cancel_friend_request(request: Request, target_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM community_friends WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'", (user["id"], target_id))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/friends/remove/{target_id}")
async def community_remove_friend(request: Request, target_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    DELETE FROM community_friends
    WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
    """, (user["id"], target_id, target_id, user["id"]))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/follow/{target_id}")
async def community_toggle_follow(request: Request, target_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_follows WHERE follower_id = ? AND following_id = ?", (user["id"], target_id))
    existing = c.fetchone()

    following = True
    if existing:
        c.execute("DELETE FROM community_follows WHERE id = ?", (existing["id"],))
        following = False
    else:
        c.execute("INSERT INTO community_follows (follower_id, following_id, created_at) VALUES (?, ?, ?)",
                  (user["id"], target_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        create_notification(
            conn,
            user_id=target_id,
            actor_id=user["id"],
            actor_name=user.get("name", "طبيب زميل"),
            actor_avatar=user.get("avatar_image", ""),
            action_type="follow",
            message="بدأ بمتابعة منشوراتك وحالاتك السريرية"
        )

    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "following": following})


@router.post("/community/block/{target_id}")
async def community_toggle_block(request: Request, target_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_blocks WHERE blocker_id = ? AND blocked_id = ?", (user["id"], target_id))
    existing = c.fetchone()

    blocked = True
    if existing:
        c.execute("DELETE FROM community_blocks WHERE id = ?", (existing["id"],))
        blocked = False
    else:
        c.execute("INSERT INTO community_blocks (blocker_id, blocked_id, created_at) VALUES (?, ?, ?)",
                  (user["id"], target_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        # Clean up any friendship
        c.execute("""
        DELETE FROM community_friends
        WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
        """, (user["id"], target_id, target_id, user["id"]))

    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "blocked": blocked})


@router.post("/community/report")
async def community_submit_report(
    request: Request,
    target_type: str = Form(...),
    target_id: int = Form(...),
    reason: str = Form(...),
    details: str = Form("")
):
    from app import get_current_user
    user = get_current_user(request)
    reporter_id = user["id"] if user else 4

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_reports (reporter_id, target_type, target_id, reason, details, status, created_at)
    VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (reporter_id, target_type, target_id, reason.strip(), details.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "message": "تم تقديم البلاغ بنجاح وسيتم تدقيقه بواسطة فريق الإشراف."})


@router.post("/community/reports/dismiss/{report_id}")
async def admin_dismiss_report(request: Request, report_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user or (not user.get("is_admin") and user.get("role") != "admin"):
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_reports SET status = 'dismissed' WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/community?tab=moderation", status_code=303)


# ==============================================================================
# PAGES & GROUPS & EVENTS ACTION ROUTES
# ==============================================================================

@router.post("/community/pages/create")
async def community_create_page(
    request: Request,
    name: str = Form(...),
    category: str = Form("clinic"),
    description: str = Form(...),
    phone: str = Form(""),
    email: str = Form(""),
    website: str = Form(""),
    city: str = Form(""),
    avatar_file: UploadFile = File(None),
    cover_file: UploadFile = File(None)
):
    from app import get_current_user
    user = get_current_user(request)
    owner_id = user["id"] if user else 1

    avatar_name = ""
    cover_name = ""
    if avatar_file and avatar_file.filename:
        ext = os.path.splitext(avatar_file.filename)[1].lower()
        avatar_name = f"page_av_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:4]}{ext}"
        try:
            with open(os.path.join(UPLOAD_DIR, avatar_name), "wb") as f:
                shutil.copyfileobj(avatar_file.file, f)
        except Exception:
            pass

    if cover_file and cover_file.filename:
        ext = os.path.splitext(cover_file.filename)[1].lower()
        cover_name = f"page_cov_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:4]}{ext}"
        try:
            with open(os.path.join(UPLOAD_DIR, cover_name), "wb") as f:
                shutil.copyfileobj(cover_file.file, f)
        except Exception:
            pass

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_pages (name, category, description, phone, email, website, city, avatar_image, cover_image, is_verified, followers_count, owner_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
    """, (name.strip(), category, description.strip(), phone.strip(), email.strip(), website.strip(), city.strip(), avatar_name, cover_name, owner_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return RedirectResponse("/community?tab=pages", status_code=303)


@router.post("/community/pages/follow/{page_id}")
async def community_toggle_page_follow(request: Request, page_id: int):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_page_followers WHERE page_id = ? AND user_id = ?", (page_id, user_id))
    existing = c.fetchone()

    following = True
    if existing:
        c.execute("DELETE FROM community_page_followers WHERE id = ?", (existing["id"],))
        c.execute("UPDATE community_pages SET followers_count = MAX(0, followers_count - 1) WHERE id = ?", (page_id,))
        following = False
    else:
        c.execute("INSERT INTO community_page_followers (page_id, user_id, created_at) VALUES (?, ?, ?)",
                  (page_id, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("UPDATE community_pages SET followers_count = followers_count + 1 WHERE id = ?", (page_id,))

    c.execute("SELECT followers_count FROM community_pages WHERE id = ?", (page_id,))
    fol_count = c.fetchone()[0]
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "following": following, "followers_count": fol_count})


@router.post("/community/groups/create")
async def community_create_group(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    icon: str = Form("🩺"),
    category: str = Form("general")
):
    from app import get_current_user
    user = get_current_user(request)
    creator_id = user["id"] if user else 1

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_groups (name, description, icon, category, members_count, created_by, created_at)
    VALUES (?, ?, ?, ?, 1, ?, ?)
    """, (name.strip(), description.strip(), icon.strip(), category, creator_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    gid = c.lastrowid
    c.execute("""
    INSERT INTO community_group_members (group_id, user_id, role, joined_at)
    VALUES (?, ?, 'admin', ?)
    """, (gid, creator_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return RedirectResponse("/community?tab=groups", status_code=303)


@router.post("/community/groups/join/{group_id}")
async def community_join_group(request: Request, group_id: int):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))
    if not c.fetchone():
        c.execute("INSERT INTO community_group_members (group_id, user_id, role, joined_at) VALUES (?, ?, 'member', ?)",
                  (group_id, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("UPDATE community_groups SET members_count = members_count + 1 WHERE id = ?", (group_id,))
        conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/groups/leave/{group_id}")
async def community_leave_group(request: Request, group_id: int):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM community_group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))
    c.execute("UPDATE community_groups SET members_count = MAX(1, members_count - 1) WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/events/create")
async def community_create_event(
    request: Request,
    title: str = Form(...),
    date_time: str = Form(...),
    location: str = Form(...),
    description: str = Form("")
):
    from app import get_current_user
    user = get_current_user(request)
    creator_id = user["id"] if user else 1

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_events (title, date_time, location, description, interested_count, created_by, created_at)
    VALUES (?, ?, ?, ?, 1, ?, ?)
    """, (title.strip(), date_time.strip(), location.strip(), description.strip(), creator_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return RedirectResponse("/community?tab=events", status_code=303)


@router.post("/community/events/interest/{event_id}")
async def community_toggle_event_interest(request: Request, event_id: int):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_event_attendees WHERE event_id = ? AND user_id = ?", (event_id, user_id))
    existing = c.fetchone()

    if existing:
        c.execute("DELETE FROM community_event_attendees WHERE id = ?", (existing["id"],))
        c.execute("UPDATE community_events SET interested_count = MAX(0, interested_count - 1) WHERE id = ?", (event_id,))
    else:
        c.execute("INSERT INTO community_event_attendees (event_id, user_id, status, created_at) VALUES (?, ?, 'interested', ?)",
                  (event_id, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("UPDATE community_events SET interested_count = interested_count + 1 WHERE id = ?", (event_id,))

    c.execute("SELECT interested_count FROM community_events WHERE id = ?", (event_id,))
    cnt = c.fetchone()[0]
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "interested_count": cnt})


# ==============================================================================
# NOTIFICATIONS ACTION ROUTES
# ==============================================================================

@router.post("/community/notifications/mark-read/{notif_id}")
async def community_mark_notif_read(request: Request, notif_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user["id"]))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@router.post("/community/notifications/mark-all-read")
async def community_mark_all_notifs_read(request: Request):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_notifications SET is_read = 1 WHERE user_id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


# ==============================================================================
# USER PROFILE & PROFILE EDITING ROUTES
# ==============================================================================

@router.get("/community/profile/{user_id}", response_class=HTMLResponse)
async def community_doctor_profile(request: Request, user_id: int):
    from app import get_current_user, get_user_lang, get_base_html

    curr_user = get_current_user(request)
    lang = get_user_lang(request)
    viewer_id = curr_user["id"] if curr_user else 4

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

    # Doctor friends count
    friends_set = get_user_friends_ids(user_id, conn)
    friends_count = len(friends_set)

    # Followers count
    c.execute("SELECT COUNT(*) FROM community_follows WHERE following_id = ?", (user_id,))
    followers_count = c.fetchone()[0]

    # Best Answers count & Reputation
    c.execute("SELECT COUNT(*) FROM community_comments WHERE user_id = ? AND is_best_answer = 1", (user_id,))
    best_answers_count = c.fetchone()[0]
    reputation = t_dict.get("reputation_score", 100) + (best_answers_count * 50)

    # Relationship info between viewer and profile owner
    rel = get_friendship_info(viewer_id, user_id, conn)

    # Following status
    c.execute("SELECT id FROM community_follows WHERE follower_id = ? AND following_id = ?", (viewer_id, user_id))
    is_following = bool(c.fetchone())

    conn.close()

    # Relationship Action Buttons (Facebook UX)
    action_buttons_html = ""
    if viewer_id == user_id:
        action_buttons_html = """
        <button type="button" onclick="openModal('edit-profile-modal')" class="btn-fb-primary">✏️ تعديل الملف الشخصي</button>
        """
    else:
        if rel["status"] == "friends":
            friend_btn = f'<button type="button" onclick="removeFriend({user_id})" class="btn-fb-outline">✔️ صديق (إلغاء)</button>'
        elif rel["status"] == "outgoing_pending":
            friend_btn = f'<button type="button" onclick="cancelFriendRequest({user_id}, this)" class="btn-fb-outline" style="background: #e2e8f0;">⏳ طلب معلق (إلغاء)</button>'
        elif rel["status"] == "incoming_pending":
            friend_btn = f'<button type="button" onclick="acceptFriendRequest({rel["request_id"]}, this)" class="btn-fb-primary">📩 قبول طلب الصداقة</button>'
        else:
            friend_btn = f'<button type="button" onclick="sendFriendRequest({user_id}, this)" class="btn-fb-primary">➕ إضافة كصديق زميل</button>'

        fol_text = "🔕 إلغاء المتابعة" if is_following else "🔔 متابعة"
        fol_style = "background: #e2e8f0; color: #334155;" if is_following else "background: var(--fb-primary); color: #ffffff;"
        follow_btn = f'<button type="button" onclick="toggleFollow({user_id}, this)" class="btn" style="border-radius: 10px; font-weight: 700; font-size: 0.88rem; padding: 9px 18px; border: none; cursor: pointer; {fol_style}">{fol_text}</button>'

        action_buttons_html = f"""
        {friend_btn}
        {follow_btn}
        <button type="button" onclick="blockUser({user_id})" class="btn-fb-danger" title="حظر المستخدم">🚫 حظر</button>
        """

    cov_style = f"background-image: url('/uploads/{t_dict['cover_photo']}');" if t_dict.get("cover_photo") else "background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);"
    av_html = f'<img src="/uploads/{t_dict["avatar_image"]}" class="profile-header-avatar">' if t_dict.get("avatar_image") else f'<div class="profile-header-avatar">{t_dict["name"][0]}</div>'

    posts_list_html = ""
    if doctor_posts:
        for dp in doctor_posts:
            posts_list_html += f"""
            <div class="fb-card" style="padding: 16px; margin-bottom: 14px;">
                <a href="/community#post-{dp['id']}" style="text-decoration: none; color: inherit;">
                    <h4 style="margin: 0 0 6px 0; color: #0f766e; font-size: 1.1rem; line-height: 1.45;">{dp['title']}</h4>
                    <p style="margin: 0; font-size: 0.9rem; color: var(--fb-text); line-height: 1.7; overflow-wrap: break-word;">{dp['content'][:220]}...</p>
                    <div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-top: 8px;">
                        ⏱️ {dp['created_at']} • 👍 {dp.get('likes_count', 0)} تفاعل • 💬 {dp.get('comments_count', 0)} تعليق
                    </div>
                </a>
            </div>
            """
    else:
        posts_list_html = "<div class='fb-card' style='padding: 24px; text-align: center; color: var(--fb-text-muted);'>لم يقم هذا الطبيب بنشر حالات سريرية بعد.</div>"

    body = f"""
    {COMMUNITY_CSS}
    <div class="fb-app-wrapper" style="padding-top: 14px;">
        <div style="max-width: 980px; margin: 0 auto; padding: 0 14px;">
            <!-- Profile Header Card (STRICT NO-MESSENGER) -->
            <div class="fb-card" style="margin-bottom: 20px;">
                <div class="fb-profile-cover" style="{cov_style}"></div>
                
                <div class="fb-profile-header-body">
                    <div class="profile-header-avatar-row">
                        {av_html}
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            {action_buttons_html}
                            <a href="/community" class="btn-fb-outline">⬅️ العودة للشبكة</a>
                        </div>
                    </div>

                    <h1 style="margin: 0; font-size: 1.6rem; color: var(--fb-text); display: flex; align-items: center; gap: 8px; flex-wrap: wrap; line-height: 1.45;">
                        <span>د. {t_dict['name']}</span>
                        <span style="font-size: 1.1rem; color: #059669;" title="طبيب بيطري معتمد وموثق">🩺</span>
                        <span style="background: #ecfdf5; color: #047857; font-size: 0.72rem; padding: 3px 10px; border-radius: 12px; font-weight: 800; border: 1px solid #6ee7b7;">طبيب موثق</span>
                    </h1>

                    <div style="font-size: 0.95rem; color: var(--fb-text-muted); margin-top: 4px; display: flex; gap: 8px; flex-wrap: wrap;">
                        <span><strong>التخصص:</strong> {t_dict.get('specialty') or 'طب وجراحة الحيوان'}</span> •
                        <span>🏢 {t_dict.get('clinic_name') or t_dict.get('work_place') or 'مركز طب وجراحة الحيوان'}</span> •
                        <span>📍 {t_dict.get('city') or ''} {t_dict.get('country') or 'مصر'}</span>
                    </div>

                    <p style="color: var(--fb-text); font-size: 0.92rem; margin: 12px 0; line-height: 1.75; overflow-wrap: break-word;">
                        {t_dict.get('bio') or 'طبيب بيطري ممارس متخصص في التشخيص الإكلينيكي والجراحة ورعاية الحيوانات، عضو شبكة VetMind AI للتبادل العلمي.'}
                    </p>

                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; border-top: 1px solid var(--fb-border); padding-top: 16px; margin-top: 14px;">
                        <div style="background: var(--fb-bg); padding: 10px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 1.35rem; font-weight: 800; color: #0f766e;">{len(doctor_posts)}</div>
                            <div style="font-size: 0.75rem; color: var(--fb-text-muted);">حالة سريرية</div>
                        </div>
                        <div style="background: var(--fb-bg); padding: 10px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 1.35rem; font-weight: 800; color: #059669;">{friends_count}</div>
                            <div style="font-size: 0.75rem; color: var(--fb-text-muted);">أصدقاء وزملاء</div>
                        </div>
                        <div style="background: var(--fb-bg); padding: 10px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 1.35rem; font-weight: 800; color: #0284c7;">{followers_count}</div>
                            <div style="font-size: 0.75rem; color: var(--fb-text-muted);">متابعون</div>
                        </div>
                        <div style="background: var(--fb-bg); padding: 10px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 1.35rem; font-weight: 800; color: #ea580c;">{reputation}</div>
                            <div style="font-size: 0.75rem; color: var(--fb-text-muted);">نقاط السمعة 🎖️</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Posts List -->
            <h3 style="color: var(--fb-text); margin-bottom: 14px;">📋 الحالات والمنشورات السريرية المنشورة:</h3>
            {posts_list_html}
        </div>
    </div>

    <!-- Edit Profile Modal -->
    <div id="edit-profile-modal" class="fb-modal-overlay">
        <div class="fb-modal-box">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--fb-border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
                <h2 style="margin: 0; font-size: 1.25rem; color: #0f766e;">✏️ تعديل الملف الشخصي والمعلومات المهنية</h2>
                <button type="button" onclick="closeModal('edit-profile-modal')" style="background: none; border: none; font-size: 1.4rem; cursor: pointer;">✕</button>
            </div>
            <form action="/community/profile/edit" method="POST" enctype="multipart/form-data">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">الاسم الكامل:</label>
                    <input type="text" name="name" value="{t_dict['name']}" required style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">الدور المهني:</label>
                        <select name="role" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                            <option value="طبيب بيطري" {'selected' if t_dict.get('role') == 'طبيب بيطري' else ''}>طبيب بيطري ممارس</option>
                            <option value="أخصائي جراحة وتخدير" {'selected' if t_dict.get('role') == 'أخصائي جراحة وتخدير' else ''}>أخصائي جراحة وتخدير</option>
                            <option value="استشاري تناسليات وولادة" {'selected' if t_dict.get('role') == 'استشاري تناسليات وولادة' else ''}>استشاري تناسليات وولادة</option>
                            <option value="صاحب عيادة / مركز بيطري" {'selected' if t_dict.get('role') == 'صاحب عيادة / مركز بيطري' else ''}>صاحب عيادة / مركز بيطري</option>
                            <option value="مربي / خبير ثروة حيوانية" {'selected' if t_dict.get('role') == 'مربي / خبير ثروة حيوانية' else ''}>مربي / خبير ثروة حيوانية</option>
                            <option value="باحث وأكاديمي بيطري" {'selected' if t_dict.get('role') == 'باحث وأكاديمي بيطري' else ''}>باحث وأكاديمي بيطري</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">التخصص الدقيق:</label>
                        <input type="text" name="specialty" value="{t_dict.get('specialty') or 'طب وجراحة الحيوان'}" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">جهة العمل / العيادة:</label>
                        <input type="text" name="work_place" value="{t_dict.get('clinic_name') or t_dict.get('work_place') or ''}" placeholder="اسم العيادة أو المستشفى" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">المدينة / المحافظة:</label>
                        <input type="text" name="city" value="{t_dict.get('city') or ''}" placeholder="القاهرة، الجيزة..." style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text);">
                    </div>
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">النبذة التعريفية (Bio):</label>
                    <textarea name="bio" rows="3" style="width: 100%; padding: 10px; border: 1px solid var(--fb-border); border-radius: 8px; background: var(--fb-bg); color: var(--fb-text); line-height: 1.5;">{t_dict.get('bio') or ''}</textarea>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.82rem;">صورة الحساب الشخصية (Avatar):</label>
                        <input type="file" name="avatar_file" accept="image/*" style="width: 100%; font-size: 0.82rem;">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.82rem;">صورة الغلاف (Cover):</label>
                        <input type="file" name="cover_file" accept="image/*" style="width: 100%; font-size: 0.82rem;">
                    </div>
                </div>
                <button type="submit" class="btn-fb-primary" style="width: 100%; justify-content: center; padding: 12px;">💾 حفظ وتحديث الملف الشخصي الآن</button>
            </form>
        </div>
    </div>

    {COMMUNITY_JS}
    """
    return HTMLResponse(content=get_base_html(f"د. {t_dict['name']} | VetBook", body, curr_user, lang), media_type="text/html; charset=utf-8")


@router.post("/community/profile/edit")
async def community_edit_profile(
    request: Request,
    name: str = Form(...),
    role: str = Form("طبيب بيطري"),
    specialty: str = Form("طب وجراحة الحيوان"),
    work_place: str = Form(""),
    city: str = Form(""),
    bio: str = Form(""),
    avatar_file: UploadFile = File(None),
    cover_file: UploadFile = File(None)
):
    from app import get_current_user
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/community", status_code=303)

    user_id = user["id"]
    conn = get_db()
    c = conn.cursor()

    avatar_name = None
    if avatar_file and avatar_file.filename:
        ext = os.path.splitext(avatar_file.filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
            avatar_name = f"user_av_{user_id}_{int(datetime.now().timestamp())}{ext}"
            try:
                with open(os.path.join(UPLOAD_DIR, avatar_name), "wb") as f:
                    shutil.copyfileobj(avatar_file.file, f)
            except Exception:
                avatar_name = None

    cover_name = None
    if cover_file and cover_file.filename:
        ext = os.path.splitext(cover_file.filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
            cover_name = f"user_cov_{user_id}_{int(datetime.now().timestamp())}{ext}"
            try:
                with open(os.path.join(UPLOAD_DIR, cover_name), "wb") as f:
                    shutil.copyfileobj(cover_file.file, f)
            except Exception:
                cover_name = None

    query = """
    UPDATE users
    SET name = ?, role = ?, specialty = ?, clinic_name = ?, work_place = ?, city = ?, bio = ?
    """
    params = [name.strip(), role.strip(), specialty.strip(), work_place.strip(), work_place.strip(), city.strip(), bio.strip()]

    if avatar_name:
        query += ", avatar_image = ?"
        params.append(avatar_name)
    if cover_name:
        query += ", cover_photo = ?"
        params.append(cover_name)

    query += " WHERE id = ?"
    params.append(user_id)

    c.execute(query, params)
    conn.commit()
    conn.close()

    return RedirectResponse(f"/community/profile/{user_id}", status_code=303)


# ==============================================================================
# OFFLINE RESILIENCE SYNC & ADMIN CONTROLS
# ==============================================================================

@router.post("/api/community/sync-posts")
async def api_community_sync_posts(request: Request):
    from app import get_current_user
    user = get_current_user(request)
    try:
        body = await request.json()
        client_posts = body.get("posts", [])
        if not client_posts:
            return JSONResponse({"status": "empty", "synced": 0})

        deleted_set = get_deleted_posts_set()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, title FROM community_posts")
        existing_rows = c.fetchall()
        existing_ids = set(r[0] for r in existing_rows)
        existing_titles = set((r[1] or "").strip() for r in existing_rows if r[1])

        synced_count = 0
        for p in client_posts:
            p_id = p.get("id")
            p_title = (p.get("title") or "").strip()
            if not p_title or not p.get("content"):
                continue
            if (p_id and p_id in deleted_set) or (p_title in deleted_set):
                continue
            if (p_id and p_id in existing_ids) or (p_title in existing_titles):
                continue
                c.execute("""
                INSERT INTO community_posts (
                    user_id, author_name, author_specialty, author_country,
                    category, title, content, is_urgent, privacy, species, breed, age, weight,
                    gender, symptoms, medications, group_id, page_id, image_path, extra_images, video_path,
                    media_type, quality_score, virality_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 5.0, ?)
                """, (
                    p.get("user_id", user["id"] if user else 4),
                    p.get("author_name", user.get("name", "طبيب بيطري") if user else "طبيب بيطري"),
                    p.get("author_specialty", "طب وجراحة الحيوان"),
                    p.get("author_country", "مصر"),
                    p.get("category", "case_study"),
                    p.get("title", ""),
                    p.get("content", ""),
                    p.get("is_urgent", 0),
                    p.get("privacy", "public"),
                    p.get("species", ""),
                    p.get("breed", ""),
                    p.get("age", ""),
                    p.get("weight", ""),
                    p.get("gender", ""),
                    p.get("symptoms", ""),
                    p.get("medications", ""),
                    p.get("group_id", 0),
                    p.get("page_id", 0),
                    p.get("image_path"),
                    p.get("extra_images", ""),
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
        return JSONResponse({"status": "ok", "synced": synced_count})
    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


@router.get("/admin/community/boost/{post_id}")
async def admin_boost_post(request: Request, post_id: int):
    from app import get_current_user
    user = get_current_user(request)
    if not user or (not user.get("is_admin") and user.get("role") != "admin"):
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
    if not user or (not user.get("is_admin") and user.get("role") != "admin"):
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_posts SET is_pinned = CASE WHEN is_pinned = 1 THEN 0 ELSE 1 END WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/community#post-{post_id}", status_code=303)

