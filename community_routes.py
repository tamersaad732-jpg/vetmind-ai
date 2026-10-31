import os
import re
import json
import shutil
import sqlite3
from datetime import datetime
from fastapi import APIRouter, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")
if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
    tmp_db = "/tmp/vetmind.db"
    if os.path.exists(DB_PATH):
        try:
            import shutil
            if (not os.path.exists(tmp_db) or 
                os.path.getmtime(DB_PATH) > os.path.getmtime(tmp_db) or 
                os.path.getsize(DB_PATH) != os.path.getsize(tmp_db)):
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

def is_user_community_approved(user_dict: dict) -> bool:
    """100% Free Community: Any logged-in registered veterinarian has complete access."""
    return bool(user_dict)

def init_community_schema():
    try:
        conn = get_db()
        c = conn.cursor()
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
            ("group_id", "INTEGER DEFAULT 0"),
            ("poll_data", "TEXT DEFAULT ''"),
            ("ai_analysis", "TEXT DEFAULT ''")
        ]
        for col, ctype in cols_to_add:
            if col not in post_cols:
                try:
                    c.execute(f"ALTER TABLE community_posts ADD COLUMN {col} {ctype}")
                except Exception:
                    pass

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

        c.execute("""
        CREATE TABLE IF NOT EXISTS community_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT DEFAULT '🩺',
            category TEXT DEFAULT 'general',
            members_count INTEGER DEFAULT 1,
            is_private INTEGER DEFAULT 0,
            created_by INTEGER DEFAULT 4,
            created_at TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at TEXT,
            UNIQUE(group_id, user_id)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            date_time TEXT NOT NULL,
            location TEXT DEFAULT 'أونلاين (Webinar)',
            cover_image TEXT DEFAULT '',
            interested_count INTEGER DEFAULT 0,
            created_by INTEGER DEFAULT 4,
            created_at TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_event_attendees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'interested',
            created_at TEXT,
            UNIQUE(event_id, user_id)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            media_url TEXT NOT NULL,
            caption TEXT DEFAULT '',
            created_at TEXT,
            expires_at TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS community_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            attachment_url TEXT DEFAULT '',
            created_at TEXT,
            is_read INTEGER DEFAULT 0
        )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        pass

init_community_schema()

def extract_youtube_embed(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    m = re.search(r'(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})', url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}"
    return ""

def evaluate_clinical_content(title: str, content: str, has_media: bool, is_urgent: bool = False, has_case_details: bool = False) -> dict:
    score = 65
    reasons = []
    text_corpus = (title + " " + content).lower()
    
    if len(content.split()) >= 25:
        score += 15
        reasons.append("شرح سريري وافٍ (+15%)")
        
    v_keywords = [
        "تشخيص", "أعراض", "جرعة", "علاج", "جراحة", "سونار", "أشعة", "تخدير",
        "مضاد حيوي", "حرارة", "تنفس", "نبض", "دم", "كبد", "كلى", "ضرع", "ولادة",
        "قيصرية", "تسمم", "عدوى", "فيروس", "بكتيريا", "طفيليات", "مغص", "عرج", "كسر"
    ]
    matches = sum(1 for kw in v_keywords if kw in text_corpus)
    if matches >= 3:
        score += 15
        reasons.append(f"مصطلحات طبية دقيقة ({matches} كلمات +15%)")
        
    if has_media:
        score += 15
        reasons.append("توثيق مرئي / مجهري (+15%)")
        
    if has_case_details:
        score += 15
        reasons.append("بيانات الحالة الديموغرافية والجرعات مكتملة (+15%)")
        
    if is_urgent:
        score += 10
        reasons.append("حالة طارئة حرجة (+10%)")
        
    score = min(100, score)
    return {
        "score": score,
        "reasons": reasons
    }

def compute_virality_score(post_dict: dict) -> float:
    likes = post_dict.get("likes_count", 0)
    comments = post_dict.get("comments_count", 0)
    views = post_dict.get("views_count", 0)
    shares = post_dict.get("shares_count", 0)
    quality = post_dict.get("quality_score", 70)
    is_boosted = post_dict.get("is_boosted", 0)
    is_pinned = post_dict.get("is_pinned", 0)
    is_urgent = post_dict.get("is_urgent", 0)

    raw_engagement = (likes * 4.0) + (comments * 6.0) + (shares * 5.0) + (views * 0.15)
    if is_pinned:
        return 10000.0 + raw_engagement
    if is_boosted:
        raw_engagement += 300.0
    if is_urgent:
        raw_engagement += 500.0

    quality_factor = (quality / 100.0) * 0.4 + 0.8
    total_score = raw_engagement * quality_factor

    created_at_str = post_dict.get("created_at", "")
    age_hours = 1.0
    try:
        post_time = datetime.strptime(created_at_str[:19], "%Y-%m-%d %H:%M:%S")
        age_hours = max(0.5, (datetime.now() - post_time).total_seconds() / 3600.0)
    except Exception:
        pass

    rank = total_score / ((age_hours + 2.0) ** 1.2)
    return round(rank, 4)

CATEGORIES = {
    "all": {"name": "كافة الحالات والأخبار", "color": "#0f766e", "icon": "📰"},
    "urgent": {"name": "حالات طارئة 🚨", "color": "#dc2626", "icon": "🚨"},
    "case_study": {"name": "حالات سريرية واستشارات", "color": "#ea580c", "icon": "🩺"},
    "videos": {"name": "Vet Watch (فيديوهات وجراحات)", "color": "#dc2626", "icon": "🎥"},
    "photos": {"name": "أشعة وآفات مجهرية", "color": "#e11d48", "icon": "📸"},
    "surgery": {"name": "جراحة وتخدير حيواني", "color": "#0891b2", "icon": "🔬"},
    "drug_experience": {"name": "تجارب دوائية وعلاجية", "color": "#7c3aed", "icon": "💊"},
    "consultation": {"name": "استشارات عاجلة للزملاء", "color": "#d97706", "icon": "❓"},
    "bookmarks": {"name": "الحالات المحفوظة (Saved)", "color": "#b45309", "icon": "🔖"},
    "my_posts": {"name": "منشوراتي وحالاتي", "color": "#0f766e", "icon": "📝"},
}

REACTIONS = {
    "like": {"label": "إعجاب", "icon": "👍", "color": "#0f766e"},
    "vital": {"label": "حالة مهمة", "icon": "❤️", "color": "#dc2626"},
    "insight": {"label": "تشخيص دقيق", "icon": "💡", "color": "#d97706"},
    "followup": {"label": "متابعة", "icon": "🤔", "color": "#7c3aed"},
    "healing": {"label": "شفاء ودعم", "icon": "🐾", "color": "#059669"},
}

SPECIES_MAP = {
    "pets": "🐕 حيوانات أليفة (كلاب وقطط)",
    "bovine": "🐄 مجترات (أبقار وجاموس)",
    "equine": "🐎 خيول وبغال",
    "ovine": "🐑 أغنام وماعز",
    "poultry": "🐔 دواجن وطيور",
    "wild": "🦅 برية وغريبة",
    "other": "🐾 فصائل أخرى"
}



COMMUNITY_CSS = """
<style>
/* ==============================================================================
   FACEBOOK-STYLE VETERINARY COMMUNITY (VETBOOK) DESIGN SYSTEM
   ============================================================================== */
:root {
    --fb-bg: #f0f2f5;
    --fb-card: #ffffff;
    --fb-primary: #0f766e;
    --fb-primary-hover: #115e59;
    --fb-accent: #ea580c;
    --fb-urgent: #dc2626;
    --fb-text: #1e293b;
    --fb-text-muted: #64748b;
    --fb-border: #e2e8f0;
    --fb-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --fb-shadow-hover: 0 4px 12px rgba(0,0,0,0.08);
}

body.dark-theme {
    --fb-bg: #0b1120;
    --fb-card: #1e293b;
    --fb-text: #f1f5f9;
    --fb-text-muted: #94a3b8;
    --fb-border: #334155;
    --fb-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.fb-app-wrapper {
    background-color: var(--fb-bg);
    min-height: 100vh;
    padding-bottom: 70px;
}

/* 3-Column Desktop Grid (RTL First: Right Column is Right Sidebar, Left is Left Sidebar) */
.fb-container {
    max-width: 1360px;
    margin: 0 auto;
    padding: 16px 12px;
    display: grid;
    grid-template-columns: 280px 1fr 310px;
    gap: 20px;
    align-items: start;
    box-sizing: border-box;
}

@media (max-width: 1160px) {
    .fb-container {
        grid-template-columns: 240px 1fr;
    }
    .fb-left-col {
        display: none !important;
    }
}

@media (max-width: 860px) {
    .fb-container {
        grid-template-columns: 1fr;
        padding: 8px 6px;
        gap: 12px;
    }
    .fb-right-col {
        display: none !important;
    }
    .fb-mobile-nav {
        display: flex !important;
        position: static !important;
        height: auto !important;
        padding: 10px 12px !important;
        border-radius: 14px !important;
        margin-bottom: 12px !important;
        border: 1px solid var(--fb-border) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
    }
    .vet-messenger-box {
        bottom: calc(75px + env(safe-area-inset-bottom, 0px)) !important;
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
}

.fb-sticky-sidebar {
    position: sticky;
    top: 70px;
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
    min-width: 110px;
    width: 110px;
    height: 175px;
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
}
body.dark-theme .case-demographics-grid {
    background: #0f172a;
    border-color: #334155;
}

/* Urgent Case Glowing Border */
.urgent-post-card {
    border-top: 5px solid #dc2626 !important;
    border-right: 2px solid #ef4444 !important;
    box-shadow: 0 0 18px rgba(220, 38, 38, 0.15) !important;
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

/* Threaded Comments & Bubbles */
.fb-comment-bubble {
    background: #f1f5f9;
    border-radius: 18px;
    padding: 10px 16px;
    color: var(--fb-text);
    font-size: 0.9rem;
    line-height: 1.7;
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

/* VetMind AI Smart Consultation Card */
.ai-consult-card {
    background: linear-gradient(135deg, #f0fdf4 0%, #ecfeff 100%);
    border: 1.5px solid #6ee7b7;
    border-radius: 14px;
    padding: 14px 18px;
    margin: 12px 0;
    box-shadow: 0 4px 14px rgba(15,118,110,0.08);
}
body.dark-theme .ai-consult-card {
    background: linear-gradient(135deg, #064e3b 0%, #083344 100%);
    border-color: #047857;
}

/* Fixed Mobile Bottom Navigation Bar */
.fb-mobile-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: var(--fb-card);
    border-top: 1px solid var(--fb-border);
    display: none;
    justify-content: space-around;
    align-items: center;
    z-index: 999;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.06);
}
.fb-mobile-nav-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    text-decoration: none;
    color: var(--fb-text-muted);
    font-size: 0.72rem;
    font-weight: 700;
}
.fb-mobile-nav-btn.active {
    color: var(--fb-primary);
}

/* Vet Messenger Drawer */
.vet-messenger-box {
    position: fixed;
    bottom: 20px;
    left: 20px;
    width: 330px;
    background: var(--fb-card);
    border: 1px solid var(--fb-border);
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    z-index: 1050;
    display: none;
    flex-direction: column;
    overflow: hidden;
}
@media (max-width: 600px) {
    .vet-messenger-box {
        width: calc(100% - 20px);
        left: 10px;
        bottom: 65px;
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
        
        if (mode === 'urgent') {
            if (urgCheck) urgCheck.checked = true;
            if (urgVal) urgVal.value = '1';
            if (catVal) catVal.value = 'urgent';
            if (titleElem) titleElem.innerText = '🚨 نشر حالة طارئة ومستعجلة';
        } else if (mode === 'case') {
            if (urgCheck) urgCheck.checked = false;
            if (urgVal) urgVal.value = '0';
            if (catVal) catVal.value = 'case_study';
            if (titleElem) titleElem.innerText = '🩺 نشر حالة سريرية واستشارة';
        } else if (mode === 'video') {
            if (urgCheck) urgCheck.checked = false;
            if (urgVal) urgVal.value = '0';
            if (catVal) catVal.value = 'videos';
            if (titleElem) titleElem.innerText = '🎥 نشر فيديو جراحي وسريري';
        } else {
            if (urgCheck) urgCheck.checked = false;
            if (urgVal) urgVal.value = '0';
            if (catVal) catVal.value = 'case_study';
            if (titleElem) titleElem.innerText = '📝 إنشاء منشور / استشارة سريرية';
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

function openStoryViewer(author, src, caption) {
    const m = document.getElementById('story-viewer-modal');
    if (m) {
        document.getElementById('story-author-tag').innerText = 'د. ' + author;
        document.getElementById('story-img-elem').src = src;
        document.getElementById('story-caption-elem').innerText = caption || '';
        m.style.display = 'flex';
    }
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

// Optimistic UI for Reactions
async function setPostReaction(postId, rType) {
    hideReactionsPopup(postId);
    
    const rMeta = {
        like: { label: 'إعجاب', icon: '👍', color: '#0f766e' },
        vital: { label: 'حالة مهمة', icon: '❤️', color: '#dc2626' },
        insight: { label: 'تشخيص دقيق', icon: '💡', color: '#d97706' },
        followup: { label: 'متابعة', icon: '🤔', color: '#7c3aed' },
        healing: { label: 'شفاء ودعم', icon: '🐾', color: '#059669' }
    };

    const meta = rMeta[rType] || rMeta['like'];
    const btn = document.getElementById('react-btn-' + postId);
    const icon = document.getElementById('react-icon-' + postId);
    const label = document.getElementById('react-label-' + postId);
    const countBox = document.getElementById('likes-count-' + postId);

    if (icon && label && btn) {
        icon.innerText = meta.icon;
        label.innerText = meta.label;
        btn.style.color = meta.color;
        btn.style.fontWeight = '800';
    }

    try {
        const formData = new FormData();
        formData.append('reaction', rType);
        const res = await fetch('/community/like/' + postId, {
            method: 'POST',
            body: formData,
            headers: { 'Accept': 'application/json' }
        });
        const data = await res.json();
        if (data && data.likes_count !== undefined && countBox) {
            countBox.innerText = data.likes_count;
            if (!data.is_liked && btn) {
                btn.style.color = 'var(--fb-text-muted)';
                icon.innerText = '👍';
                label.innerText = 'إعجاب';
            }
        }
    } catch (e) {
        console.log('Reaction sync:', e);
    }
}

// Ask VetMind AI
async function askVetMindAI(postId) {
    const postCard = document.getElementById('post-' + postId);
    const existingBox = document.getElementById('ai-box-' + postId);
    
    if (existingBox) {
        existingBox.scrollIntoView({ behavior: 'smooth' });
        return;
    }

    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'ai-loading-' + postId;
    loadingDiv.className = 'ai-consult-card';
    loadingDiv.innerHTML = '<div style="display: flex; align-items: center; gap: 10px; font-weight: 700; color: #0f766e;"><span>⏳</span> جاري استدعاء محرك VetMind AI لتحليل الأعراض وصياغة التشخيص التفريقي...</div>';
    
    if (postCard) {
        postCard.appendChild(loadingDiv);
        loadingDiv.scrollIntoView({ behavior: 'smooth' });
    }

    try {
        const res = await fetch('/community/ai-consult/' + postId, { method: 'POST' });
        const data = await res.json();
        if (loadingDiv) loadingDiv.remove();

        if (data.success && data.analysis) {
            const aiBox = document.createElement('div');
            aiBox.id = 'ai-box-' + postId;
            aiBox.className = 'ai-consult-card';
            aiBox.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px; font-weight: 800; color: #0f766e;">
                    <span style="font-size: 1.3rem;">🤖</span>
                    <span>التحليل السريري المعتمد من VetMind AI:</span>
                </div>
                <span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 700;">فوري</span>
            </div>
            <div style="font-size: 0.9rem; line-height: 1.7; color: var(--fb-text); white-space: pre-line;">${data.analysis}</div>
            `;
            if (postCard) postCard.appendChild(aiBox);
        }
    } catch (e) {
        if (loadingDiv) loadingDiv.innerHTML = '<span style="color: red;">تعذر الاتصال بـ VetMind AI حالياً.</span>';
    }
}

// Bookmark Toggle
async function togglePostBookmark(postId) {
    const btn = document.getElementById('bookmark-btn-' + postId);
    const text = document.getElementById('bookmark-text-' + postId);
    try {
        const res = await fetch('/community/bookmark/' + postId, { method: 'POST', headers: { 'Accept': 'application/json' } });
        const data = await res.json();
        if (data && data.is_bookmarked !== undefined) {
            if (data.is_bookmarked) {
                btn.style.color = '#d97706';
                btn.style.fontWeight = '800';
                text.innerText = 'محفوظة 🔖';
            } else {
                btn.style.color = 'var(--fb-text-muted)';
                btn.style.fontWeight = 'normal';
                text.innerText = 'حفظ 🔖';
            }
        }
    } catch (e) {
        console.log('Bookmark error:', e);
    }
}

// Submit Comment (Optimistic UI)
async function submitCommentForm(e, postId) {
    e.preventDefault();
    const input = document.getElementById('comment-input-' + postId);
    const fileInput = document.getElementById('comment-file-' + postId);
    const text = input.value.trim();
    if (!text) return;

    const formData = new FormData();
    formData.append('content', text);
    formData.append('parent_comment_id', '0');
    if (fileInput && fileInput.files.length > 0) {
        formData.append('comment_image', fileInput.files[0]);
    }

    input.value = '';
    if (fileInput) fileInput.value = '';

    try {
        const res = await fetch('/community/comment/' + postId, {
            method: 'POST',
            body: formData,
            headers: { 'Accept': 'application/json' }
        });
        const data = await res.json();
        if (data.success && data.comment_html) {
            const list = document.getElementById('comments-list-' + postId);
            const noCm = document.getElementById('no-comments-' + postId);
            if (noCm) noCm.remove();
            if (list) {
                list.insertAdjacentHTML('beforeend', data.comment_html);
            }
            const cnt = document.getElementById('comments-count-' + postId);
            if (cnt && data.total_comments) {
                cnt.innerText = data.total_comments + ' تعليقاً';
            }
        }
    } catch (err) {
        console.log('Comment error:', err);
    }
}

// Submit Reply
async function submitReply(e, postId, parentId) {
    e.preventDefault();
    const input = document.getElementById('reply-input-' + parentId);
    const text = input.value.trim();
    if (!text) return;

    const formData = new FormData();
    formData.append('content', text);
    formData.append('parent_comment_id', parentId);

    input.value = '';
    const box = document.getElementById('reply-box-' + parentId);
    if (box) box.style.display = 'none';

    try {
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
        console.log('Reply error:', err);
    }
}

// Mark Best Diagnosis
async function markBestDiagnosis(commentId, postId) {
    if (!confirm('هل تريد بالتأكيد اعتماد هذا التشخيص كأفضل تشخيص رسمي للحالة ومنح الطبيب +50 نقطة سمعة علمية؟')) return;
    try {
        const res = await fetch('/community/comment/best/' + commentId, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert('🏆 تم اعتماد التشخيص بنجاح ومنح الزميل وسام التشخيص المعتمد!');
            location.reload();
        }
    } catch (e) {
        console.log(e);
    }
}

function toggleReplyBox(cmId) {
    const box = document.getElementById('reply-box-' + cmId);
    if (box) {
        box.style.display = (box.style.display === 'none' || box.style.display === '') ? 'block' : 'none';
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

// Event Interest Toggle
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

// Messenger
function openMessenger(colleagueId, colleagueName) {
    const win = document.getElementById('vet-messenger-window');
    document.getElementById('chat-colleague-name').innerText = 'د. ' + colleagueName;
    document.getElementById('chat-receiver-id').value = colleagueId;
    if (win) win.style.display = 'flex';
    loadChatMessages(colleagueId);
}

function closeMessenger() {
    const win = document.getElementById('vet-messenger-window');
    if (win) win.style.display = 'none';
}

function toggleMessengerDrawer() {
    const win = document.getElementById('vet-messenger-window');
    if (win) {
        win.style.display = (win.style.display === 'none' || win.style.display === '') ? 'flex' : 'none';
    }
}

async function loadChatMessages(colleagueId) {
    const container = document.getElementById('chat-messages-container');
    try {
        const res = await fetch('/community/messages/' + colleagueId);
        const data = await res.json();
        if (data.messages && container) {
            container.innerHTML = data.messages.map(m => {
                const isMe = m.sender_id !== colleagueId;
                const bStyle = isMe ? 'background: #0f766e; color: white; margin-left: 20px;' : 'background: white; border: 1px solid var(--fb-border); margin-right: 20px;';
                return `<div style="padding: 8px 12px; border-radius: 12px; ${bStyle}; font-size: 0.82rem; word-break: break-word;">${m.message}</div>`;
            }).join('') || '<div style="color: var(--fb-text-muted); font-size: 0.8rem; text-align: center; margin-top: 30px;">ابدأ استشارتك الطبية الخاصة الآن 🩺</div>';
            container.scrollTop = container.scrollHeight;
        }
    } catch (e) {
        console.log(e);
    }
}

async function sendDirectMessage(e) {
    e.preventDefault();
    const rId = document.getElementById('chat-receiver-id').value;
    const input = document.getElementById('chat-text-input');
    const text = input.value.trim();
    if (!text || rId === '0') return;

    input.value = '';
    try {
        const formData = new FormData();
        formData.append('receiver_id', rId);
        formData.append('message', text);
        await fetch('/community/messages/send', { method: 'POST', body: formData });
        loadChatMessages(parseInt(rId));
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
</script>
"""



@router.get("/community", response_class=HTMLResponse)
async def community_hub(
    request: Request,
    category: str = "all",
    species: str = "all",
    q: str = "",
    sort: str = "algorithmic",
    group_id: int = 0,
    tab: str = "feed"
):
    from app import get_current_user, get_user_lang, get_text, get_base_html

    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    conn = get_db()
    c = conn.cursor()

    # Query Posts
    sql = "SELECT * FROM community_posts WHERE 1=1"
    params = []

    if q and q.strip():
        sql += " AND (title LIKE ? OR content LIKE ? OR author_name LIKE ? OR symptoms LIKE ? OR diagnosis LIKE ?)"
        q_term = f"%{q.strip()}%"
        params.extend([q_term, q_term, q_term, q_term, q_term])

    if group_id > 0:
        sql += " AND group_id = ?"
        params.append(group_id)

    if species != "all":
        sql += " AND species = ?"
        params.append(species)

    if category == "urgent":
        sql += " AND is_urgent = 1"
    elif category == "videos":
        sql += " AND (media_type = 'video' OR media_type = 'youtube' OR video_path IS NOT NULL)"
    elif category == "photos":
        sql += " AND (media_type = 'image' OR image_path IS NOT NULL)"
    elif category == "bookmarks" and user:
        sql += " AND id IN (SELECT post_id FROM community_bookmarks WHERE user_id = ?)"
        params.append(user["id"])
    elif category == "my_posts" and user:
        sql += " AND user_id = ?"
        params.append(user["id"])
    elif category != "all" and category in CATEGORIES:
        sql += " AND category = ?"
        params.append(category)

    c.execute(sql, tuple(params))
    raw_posts = [dict(r) for r in c.fetchall()]

    # Calculate virality score & trending flag
    for p in raw_posts:
        v_score = compute_virality_score(p)
        p["calculated_virality"] = v_score
        is_trending_now = 1 if (p.get("likes_count", 0) + p.get("comments_count", 0) >= 2 or v_score >= 1.5) else 0
        p["is_trending"] = is_trending_now

    # Sort Posts
    if sort == "recent":
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x.get("is_urgent", 0), x["id"]), reverse=True)
    elif sort == "most_discussed":
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x.get("comments_count", 0), x["id"]), reverse=True)
    elif sort == "most_viewed":
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x.get("views_count", 0), x["id"]), reverse=True)
    else:
        # Algorithmic (Default)
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x.get("is_urgent", 0), x.get("calculated_virality", 0.0), x["id"]), reverse=True)

    posts = raw_posts

    # Bookmarks
    user_bookmarks = set()
    if user:
        c.execute("SELECT post_id FROM community_bookmarks WHERE user_id = ?", (user["id"],))
        user_bookmarks = set(r[0] for r in c.fetchall())

    # User Reactions map for current posts
    user_reactions = {}
    if user:
        c.execute("SELECT post_id, reaction_type FROM community_likes WHERE user_id = ?", (user["id"],))
        for r in c.fetchall():
            user_reactions[r["post_id"]] = r["reaction_type"]

    # Active Groups
    c.execute("SELECT * FROM community_groups ORDER BY members_count DESC LIMIT 6")
    active_groups = [dict(r) for r in c.fetchall()]

    # Upcoming Events
    c.execute("SELECT * FROM community_events ORDER BY id DESC LIMIT 3")
    upcoming_events = [dict(r) for r in c.fetchall()]

    # Urgent cases for sidebar
    c.execute("SELECT id, title, species, author_name, created_at FROM community_posts WHERE is_urgent = 1 ORDER BY id DESC LIMIT 5")
    urgent_cases = [dict(r) for r in c.fetchall()]

    # Online colleagues
    c.execute("SELECT id, name, clinic_name, country, last_active_at FROM users WHERE id != ? ORDER BY id DESC LIMIT 8", (user["id"] if user else 0,))
    colleagues = [dict(r) for r in c.fetchall()]

    # Stories
    c.execute("SELECT * FROM community_stories ORDER BY id DESC LIMIT 10")
    raw_stories = [dict(r) for r in c.fetchall()]

    # Stats
    c.execute("SELECT COUNT(*) FROM community_posts")
    total_posts = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users")
    total_vets = c.fetchone()[0]

    # Build Stories HTML
    stories_cards = ""
    for st in raw_stories:
        stories_cards += f"""
        <div class="fb-story-card" style="background-image: linear-gradient(180deg, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.7) 100%), url('/uploads/{st['media_url']}');" onclick="openStoryViewer('{st['author_name']}', '/uploads/{st['media_url']}', '{st.get('caption','')}')">
            <div style="position: absolute; top: 8px; right: 8px; width: 34px; height: 34px; border-radius: 50%; border: 2px solid #0f766e; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.85rem; box-shadow: 0 2px 6px rgba(0,0,0,0.2);">
                {st['author_name'][0]}
            </div>
            <div style="position: absolute; bottom: 8px; right: 8px; left: 8px; color: white; font-size: 0.76rem; font-weight: 700; text-shadow: 0 1px 3px rgba(0,0,0,0.8); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                د. {st['author_name']}
            </div>
        </div>
        """

    # If no stories, show demo surgical stories
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

    # Build Posts Stream
    posts_cards_html = ""
    for p in posts:
        post_id = p["id"]
        is_urgent = p.get("is_urgent", 0)
        post_reaction = user_reactions.get(post_id)
        is_bookmarked = post_id in user_bookmarks

        # Increment views count
        c.execute("UPDATE community_posts SET views_count = views_count + 1 WHERE id = ?", (post_id,))

        # Active Reaction info
        react_info = REACTIONS.get(post_reaction, {"label": "إعجاب", "icon": "👍", "color": "var(--fb-text-muted)"})
        react_active_style = f"color: {react_info['color']}; font-weight: 800;" if post_reaction else "color: var(--fb-text-muted);"

        # Bookmark styling
        bookmark_style = "color: #d97706; font-weight: 800;" if is_bookmarked else "color: var(--fb-text-muted);"
        bookmark_label = "محفوظة 🔖" if is_bookmarked else "حفظ 🔖"

        # Urgent Banner
        urgent_banner = ""
        card_class = "fb-card"
        if is_urgent:
            card_class += " urgent-post-card"
            urgent_banner = """
            <div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border-bottom: 1.5px solid #f87171; padding: 8px 14px; display: flex; align-items: center; justify-content: space-between; color: #991b1b; font-weight: 800; font-size: 0.84rem;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.15rem; animation: pulse 1s infinite;">🚨</span>
                    <span>حالة سريرية عاجلة بحاجة لاستشارة فورية (URGENT CASE)</span>
                </div>
                <span style="background: #dc2626; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem;">أولوية قصوى</span>
            </div>
            """

        # Clinical Demographics Box
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

        # Media Player / Image
        media_html = ""
        if p.get("video_path"):
            vpath = p["video_path"]
            if vpath.startswith("http://") or vpath.startswith("https://"):
                media_html = f"""
                <div style="margin: 12px 0; background: #000; border-radius: 12px; overflow: hidden; width: 100%;">
                    <iframe src="{vpath}" style="width: 100%; aspect-ratio: 16/9; border: none; display: block;" allowfullscreen></iframe>
                </div>
                """
            else:
                media_html = f"""
                <div style="margin: 12px 0; background: #000; border-radius: 12px; overflow: hidden; width: 100%;">
                    <video controls playsinline preload="metadata" style="width: 100%; max-height: 520px; display: block; background: #0f172a;">
                        <source src="/uploads/{vpath}">
                    </video>
                </div>
                """
        elif p.get("image_path"):
            media_html = f"""
            <div style="margin: 12px 0; border-radius: 12px; overflow: hidden; background: #0f172a; text-align: center;">
                <img src="/uploads/{p['image_path']}" alt="{p['title']}" onclick="openImageModal('/uploads/{p['image_path']}')" style="max-width: 100%; max-height: 520px; object-fit: contain; display: block; margin: 0 auto; cursor: zoom-in;">
            </div>
            """

        # Poll Widget (if poll_data exists)
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
                    <div class="poll-option-bar" onclick="votePoll({post_id}, {opt['id']})">
                        <div class="poll-progress-fill" style="width: {pct}%;"></div>
                        <div style="position: relative; z-index: 2; display: flex; justify-content: space-between; font-weight: 700; font-size: 0.88rem;">
                            <span>{opt['text']}</span>
                            <span>{pct}% ({opt.get('votes', 0)})</span>
                        </div>
                    </div>
                    """
                poll_html = f"""
                <div style="background: var(--fb-bg); border: 1px solid var(--fb-border); border-radius: 12px; padding: 14px; margin: 12px 0;">
                    <div style="font-weight: 800; font-size: 0.95rem; color: #0f766e; margin-bottom: 10px;">📊 استطلاع رأي سريري: {q_text}</div>
                    {opts_html}
                    <div style="font-size: 0.74rem; color: var(--fb-text-muted); margin-top: 6px; text-align: left;">إجمالي الأصوات: {total_votes} طبيباً</div>
                </div>
                """
            except Exception:
                pass

        # AI Analysis Card (if generated)
        ai_card_html = ""
        if p.get("ai_analysis"):
            ai_card_html = f"""
            <div class="ai-consult-card" id="ai-box-{post_id}">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px; font-weight: 800; color: #0f766e;">
                        <span style="font-size: 1.3rem;">🤖</span>
                        <span>التحليل السريري الذكي (VetMind AI Differential Diagnosis):</span>
                    </div>
                    <span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 700;">معتمد ذكياً</span>
                </div>
                <div style="font-size: 0.9rem; line-height: 1.7; color: var(--fb-text); white-space: pre-line;">
                    {p['ai_analysis']}
                </div>
            </div>
            """

        # Fetch Comments
        c.execute("SELECT * FROM community_comments WHERE post_id = ? ORDER BY is_best_answer DESC, id ASC", (post_id,))
        comments_raw = [dict(r) for r in c.fetchall()]
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

            best_badge = '<span class="best-answer-badge">🏆 أفضل تشخيص معتمد من صاحب الحالة ✅</span>' if is_best else ""
            ai_badge = '<span style="background: #10b981; color: white; padding: 1px 6px; border-radius: 8px; font-size: 0.68rem; font-weight: 800;">🤖 AI مساعد</span>' if is_ai else ""
            author_badge = '<span style="background: #e0e7ff; color: #3730a3; padding: 1px 6px; border-radius: 8px; font-size: 0.7rem; font-weight: 700;">👑 صاحب الحالة</span>' if cm.get("user_id") == p["user_id"] else ""

            mark_best_btn = ""
            if user and user["id"] == p["user_id"] and not is_best and cm.get("user_id") != user["id"]:
                mark_best_btn = f"""
                <button type="button" onclick="markBestDiagnosis({cm_id}, {post_id})" style="background: none; border: none; color: #059669; font-weight: 800; cursor: pointer; font-size: 0.74rem;">
                    ✅ اعتماد كأفضل تشخيص (+50 سمعة)
                </button>
                """

            # Replies
            replies_html = ""
            for rep in replies_map.get(cm_id, []):
                rep_is_author = rep.get("user_id") == p["user_id"]
                rep_badge = '<span style="background: #e0e7ff; color: #3730a3; padding: 1px 5px; border-radius: 8px; font-size: 0.68rem; font-weight: 700;">👑 صاحب الحالة</span>' if rep_is_author else ""
                replies_html += f"""
                <div style="margin-top: 8px; display: flex; gap: 8px; align-items: flex-start;">
                    <div style="width: 28px; height: 28px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; flex-shrink: 0;">
                        {rep['author_name'][0]}
                    </div>
                    <div style="flex: 1;">
                        <div class="fb-comment-bubble">
                            <div style="font-weight: 700; font-size: 0.82rem; color: #0f766e;">د. {rep['author_name']} {rep_badge}</div>
                            <div style="margin-top: 3px;">{rep['content']}</div>
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
                <div style="flex: 1;">
                    <div class="{bubble_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px; margin-bottom: 4px;">
                            <div>
                                <strong style="font-size: 0.88rem; color: #0f766e;">د. {cm['author_name']}</strong> {author_badge} {ai_badge}
                                <span style="font-size: 0.72rem; color: var(--fb-text-muted); margin-right: 4px;">({cm.get('author_specialty') or 'طبيب بيطري'})</span>
                            </div>
                            {best_badge}
                        </div>
                        <div style="line-height: 1.5;">{cm['content']}</div>
                        {f'<img src="/uploads/{cm["image_url"]}" style="max-width: 240px; border-radius: 8px; margin-top: 8px; display: block;" onclick="openImageModal(\'/uploads/{cm["image_url"]}\')">' if cm.get("image_url") else ""}
                    </div>
                    <div style="display: flex; gap: 12px; font-size: 0.74rem; color: var(--fb-text-muted); margin-top: 3px; margin-right: 10px; align-items: center;">
                        <button type="button" onclick="toggleReplyBox({cm_id})" style="background: none; border: none; font-weight: 700; color: #0f766e; cursor: pointer; padding: 0;">رد ↩️</button>
                        {mark_best_btn}
                        <span>{cm['created_at']}</span>
                    </div>

                    <div style="margin-right: 20px;">
                        {replies_html}
                    </div>

                    <div id="reply-box-{cm_id}" style="display: none; margin-top: 8px; margin-right: 20px;">
                        <form onsubmit="submitReply(event, {post_id}, {cm_id})" style="display: flex; gap: 8px; align-items: center;">
                            <input type="text" id="reply-input-{cm_id}" required placeholder="اكتب ردك على د. {cm['author_name']}..." style="flex: 1; padding: 8px 14px; border: 1px solid var(--fb-border); border-radius: 20px; font-size: 0.82rem; background: var(--fb-bg); color: var(--fb-text);">
                            <button type="submit" class="btn btn-primary" style="padding: 6px 14px; font-size: 0.78rem; border-radius: 20px;">رد ↩️</button>
                        </form>
                    </div>
                </div>
            </div>
            """

        # Algorithmic and author badges
        q_score = p.get("quality_score", 75)
        v_score = p.get("calculated_virality", 0.0)
        is_trending = p.get("is_trending", 0)
        is_boosted = p.get("is_boosted", 0)
        is_pinned = p.get("is_pinned", 0)

        post_badges = ""
        if is_pinned:
            post_badges += '<span style="background: #fef08a; color: #854d0e; padding: 2px 7px; border-radius: 10px; font-size: 0.7rem; font-weight: 800;">📌 مثبت</span>'
        if is_boosted:
            post_badges += '<span style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; padding: 2px 7px; border-radius: 10px; font-size: 0.7rem; font-weight: 800;">🚀 مروج</span>'
        if is_trending:
            post_badges += '<span style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 2px 7px; border-radius: 10px; font-size: 0.7rem; font-weight: 800;">🔥 رائج</span>'
        if q_score >= 85:
            post_badges += f'<span style="background: #ecfdf5; color: #047857; border: 1px solid #6ee7b7; padding: 2px 7px; border-radius: 10px; font-size: 0.7rem; font-weight: 700;">🌟 توثيق فائق ({q_score}%)</span>'

        cat_badge = CATEGORIES.get(p["category"], {"name": p["category"], "color": "#0f766e", "icon": "📄"})

        # Delete & Admin Controls
        delete_btn = ""
        if user and (user.get("is_admin") or user["id"] == p["user_id"]):
            delete_btn = f"""
            <form action="/community/post/delete/{post_id}" method="POST" style="margin: 0;" onsubmit="return confirm('هل تريد بالتأكيد حذف هذا المنشور السريري؟');">
                <button type="submit" style="background: none; border: none; color: #dc2626; cursor: pointer; font-size: 0.85rem; padding: 2px;" title="حذف المنشور">🗑️</button>
            </form>
            """

        admin_boost = ""
        if user and user.get("is_admin"):
            b_label = "إلغاء الترويج" if is_boosted else "🚀 ترويج"
            p_label = "إلغاء التثبيت" if is_pinned else "📌 تثبيت"
            admin_boost = f"""
            <a href="/admin/community/pin/{post_id}" style="font-size: 0.7rem; text-decoration: none; padding: 2px 6px; border-radius: 6px; background: #fef9c3; color: #854d0e; font-weight: 700;">{p_label}</a>
            <a href="/admin/community/boost/{post_id}" style="font-size: 0.7rem; text-decoration: none; padding: 2px 6px; border-radius: 6px; background: #ffedd5; color: #c2410c; font-weight: 700;">{b_label}</a>
            """

        posts_cards_html += f"""
        <div class="{card_class}" id="post-{post_id}" style="margin-bottom: 16px;">
            {urgent_banner}
            <div style="padding: 16px;">
                <!-- Post Header -->
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 12px;">
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
                        {admin_boost}
                        <span style="background: {cat_badge['color']}15; color: {cat_badge['color']}; padding: 3px 10px; border-radius: 12px; font-size: 0.74rem; font-weight: 700;">
                            {cat_badge['icon']} {cat_badge['name']}
                        </span>
                        {delete_btn}
                    </div>
                </div>

                <!-- Post Title & Content -->
                <h3 style="margin: 0 0 8px 0; font-size: 1.15rem; color: var(--fb-text); line-height: 1.5; word-break: normal; overflow-wrap: break-word;">{p['title']}</h3>
                <div style="font-size: 0.95rem; color: var(--fb-text); line-height: 1.75; word-break: normal; overflow-wrap: break-word; white-space: pre-line;">{p['content']}</div>

                {demographics_html}
                {media_html}
                {poll_html}
                {ai_card_html}

                <!-- Post Reactions Summary -->
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 4px; border-bottom: 1px solid var(--fb-border); font-size: 0.8rem; color: var(--fb-text-muted); margin-top: 8px;">
                    <div style="display: flex; align-items: center; gap: 5px;" id="likes-count-box-{post_id}">
                        <span>👍❤️💡</span>
                        <strong style="margin-right: 4px;" id="likes-count-{post_id}">{p['likes_count']}</strong>
                        <span>تفاعلاً</span>
                    </div>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <span id="comments-count-{post_id}">{p['comments_count']} تعليقاً</span> •
                        <span>{p.get('views_count', 1)} مشاهدة</span>
                    </div>
                </div>

                <!-- Facebook Action Bar -->
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--fb-border); position: relative;">
                    <!-- Reactions Trigger & Popup -->
                    <div class="reaction-wrapper" onmouseenter="showReactionsPopup({post_id})" onmouseleave="hideReactionsPopup({post_id})">
                        <div class="fb-reactions-popup" id="reactions-popup-{post_id}">
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'like')" title="إعجاب">👍</button>
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'vital')" title="حالة مهمة">❤️</button>
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'insight')" title="تشخيص دقيق">💡</button>
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'followup')" title="بحاجة لمتابعة">🤔</button>
                            <button type="button" class="reaction-item-btn" onclick="setPostReaction({post_id}, 'healing')" title="شفاء ودعم">🐾</button>
                        </div>
                        <button type="button" onclick="setPostReaction({post_id}, '{post_reaction or 'like'}')" id="react-btn-{post_id}" class="btn" style="background: none; border: none; {react_active_style} font-size: 0.88rem; padding: 6px 12px; display: inline-flex; align-items: center; gap: 6px;">
                            <span id="react-icon-{post_id}">{react_info['icon']}</span>
                            <span id="react-label-{post_id}">{react_info['label']}</span>
                        </button>
                    </div>

                    <!-- Comment Button -->
                    <button type="button" onclick="focusCommentInput({post_id})" class="btn" style="background: none; border: none; color: var(--fb-text-muted); font-size: 0.88rem; padding: 6px 12px; display: inline-flex; align-items: center; gap: 6px;">
                        <span>💬</span>
                        <span>تعليق</span>
                    </button>

                    <!-- Ask VetMind AI -->
                    <button type="button" onclick="askVetMindAI({post_id})" class="btn" style="background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1px solid #10b981; color: #065f46; font-size: 0.82rem; font-weight: 800; padding: 6px 12px; border-radius: 20px; display: inline-flex; align-items: center; gap: 5px;">
                        <span>🤖</span>
                        <span>اسأل VetMind AI</span>
                    </button>

                    <!-- Share -->
                    <button type="button" onclick="sharePost({post_id})" class="btn" style="background: none; border: none; color: var(--fb-text-muted); font-size: 0.88rem; padding: 6px 12px; display: inline-flex; align-items: center; gap: 6px;">
                        <span>↪️</span>
                        <span>مشاركة</span>
                    </button>

                    <!-- Bookmark -->
                    <button type="button" onclick="togglePostBookmark({post_id})" id="bookmark-btn-{post_id}" class="btn" style="background: none; border: none; {bookmark_style} font-size: 0.88rem; padding: 6px 12px; display: inline-flex; align-items: center; gap: 6px;">
                        <span id="bookmark-icon-{post_id}">🔖</span>
                        <span id="bookmark-text-{post_id}">{bookmark_label}</span>
                    </button>
                </div>

                <!-- Comments Container -->
                <div style="margin-top: 14px;" id="comments-section-{post_id}">
                    <!-- Add Comment Input Box -->
                    <form onsubmit="submitCommentForm(event, {post_id})" style="display: flex; gap: 10px; align-items: center; margin-bottom: 14px;">
                        <div style="width: 34px; height: 34px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.9rem; flex-shrink: 0;">
                            {user.get('name', 'طبيب')[0] if user else 'V'}
                        </div>
                        <div style="flex: 1; display: flex; align-items: center; background: var(--fb-bg); border: 1px solid var(--fb-border); border-radius: 25px; padding: 4px 14px;">
                            <input type="text" id="comment-input-{post_id}" required placeholder="اكتب تشخيصك أو تعليقك الطبي..." style="flex: 1; border: none; background: transparent; padding: 8px 0; font-size: 0.88rem; color: var(--fb-text); outline: none;">
                            <label style="cursor: pointer; padding: 4px 8px; font-size: 1.1rem; color: var(--fb-text-muted);" title="إرفاق صورة أو روشتة">
                                📷
                                <input type="file" id="comment-file-{post_id}" accept="image/*" style="display: none;" onchange="alert('تم اختيار صورة للتعليق: ' + this.files[0].name)">
                            </label>
                            <button type="submit" style="background: #0f766e; border: none; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 0.85rem;">
                                ⬆️
                            </button>
                        </div>
                    </form>

                    <!-- Comments List -->
                    <div id="comments-list-{post_id}">
                        {comments_html if comments_html else "<div style='color: var(--fb-text-muted); font-size: 0.82rem; text-align: center; padding: 8px;' id='no-comments-" + str(post_id) + "'>كن أول من يشارك بتشخيص أو رأي سريري في هذه الحالة 🩺</div>"}
                    </div>
                </div>
            </div>
        </div>
        """

    try:
        conn.commit()
        conn.close()
    except Exception:
        pass

    if not posts_cards_html:
        posts_cards_html = f"""
        <div class="fb-card" style="padding: 40px 20px; text-align: center;">
            <div style="font-size: 3rem; margin-bottom: 12px;">🩺</div>
            <h3 style="color: var(--fb-text); margin-bottom: 8px;">لا توجد منشورات سريرية مطابقة لهذا الفلتر حالياً</h3>
            <p style="color: var(--fb-text-muted); font-size: 0.95rem; margin-bottom: 20px;">كن أول من يشارك حالة سريرية، استشارة، أو تجربة دوائية مع الزملاء الأطباء</p>
            <button type="button" onclick="openComposerModal('case')" class="btn btn-primary" style="padding: 10px 24px; border-radius: 20px; font-weight: 700;">
                ➕ نشر أول حالة سريرية الآن
            </button>
        </div>
        """

    # Build Right Column (Doctor Profile, Groups, Saved Cases)
    user_avatar_letter = user.get('name', 'طبيب')[0] if user else 'V'
    user_name_disp = user.get('name', 'طبيب بيطري زائر') if user else 'طبيب بيطري زائر'
    user_clinic_disp = user.get('clinic_name', 'عيادة بيطرية') if user else 'سجل دخولك للمشاركة'

    groups_list_html = ""
    for g in active_groups:
        groups_list_html += f"""
        <a href="/community?group_id={g['id']}" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; border-radius: 10px; text-decoration: none; color: var(--fb-text); transition: background 0.2s;" class="fb-hover-row">
            <div style="display: flex; align-items: center; gap: 8px; overflow: hidden;">
                <span style="font-size: 1.3rem;">{g.get('icon', '🩺')}</span>
                <div style="overflow: hidden;">
                    <div style="font-weight: 700; font-size: 0.84rem; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">{g['name']}</div>
                    <div style="font-size: 0.72rem; color: var(--fb-text-muted);">{g.get('members_count', 1)} طبيباً</div>
                </div>
            </div>
            <span style="font-size: 0.72rem; color: #0f766e; font-weight: 800;">تصفح ⬅️</span>
        </a>
        """

    right_col_html = f"""
    <div class="fb-right-col fb-sticky-sidebar">
        <!-- Logged-in Doctor Card -->
        <div class="fb-card" style="padding: 16px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.3rem; box-shadow: 0 4px 10px rgba(15,118,110,0.25);">
                    {user_avatar_letter}
                </div>
                <div style="overflow: hidden;">
                    <div style="font-weight: 800; font-size: 0.98rem; color: var(--fb-text); white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">د. {user_name_disp}</div>
                    <div style="font-size: 0.75rem; color: #059669; font-weight: 700;">طبيب بيطري معتمد 🩺</div>
                    <div style="font-size: 0.72rem; color: var(--fb-text-muted);">{user_clinic_disp}</div>
                </div>
            </div>
            {f'<a href="/community/profile/{user["id"]}" class="btn btn-outline" style="width: 100%; justify-content: center; font-size: 0.82rem; border-radius: 20px; font-weight: 700;">👤 عرض ملفي الشخصي والسمعة</a>' if user else '<a href="/login?redirect=/community" class="btn btn-primary" style="width: 100%; justify-content: center; font-size: 0.82rem; border-radius: 20px; font-weight: 700;">🔑 تسجيل الدخول للطبيب</a>'}
        </div>

        <!-- Quick Navigation -->
        <div class="fb-card" style="padding: 12px;">
            <div style="font-weight: 800; font-size: 0.86rem; color: #0f766e; margin-bottom: 8px; padding-right: 6px;">
                🧭 تصفح سريع:
            </div>
            <a href="/community" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text); font-weight: 700; font-size: 0.88rem;">
                <span>📰</span> <span>آخر الأخبار والحالات</span>
            </a>
            <a href="/community?category=urgent" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: #dc2626; font-weight: 800; font-size: 0.88rem;">
                <span>🚨</span> <span>الحالات الطارئة المستعجلة</span>
            </a>
            <a href="/community?category=case_study" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text); font-weight: 700; font-size: 0.88rem;">
                <span>🩺</span> <span>الاستشارات السريرية</span>
            </a>
            <a href="/community?category=videos" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text); font-weight: 700; font-size: 0.88rem;">
                <span>🎥</span> <span>فيديوهات الجراحة (Vet Watch)</span>
            </a>
            <a href="/community?category=bookmarks" style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text); font-weight: 700; font-size: 0.88rem;">
                <span>🔖</span> <span>الحالات المحفوظة للرجوع إليها</span>
            </a>
        </div>

        <!-- Specialized Veterinary Groups -->
        <div class="fb-card" style="padding: 14px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <div style="font-weight: 800; font-size: 0.88rem; color: #0f766e; display: flex; align-items: center; gap: 6px;">
                    <span>👥</span> <span>المجموعات التخصصية</span>
                </div>
                <button type="button" onclick="openCreateGroupModal()" style="background: none; border: none; color: #0f766e; font-size: 0.75rem; font-weight: 800; cursor: pointer;">➕ إنشاء</button>
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
                {groups_list_html}
            </div>
        </div>
    </div>
    """

    # Build Left Column (Urgent Cases, Webinars/Events, Colleague Messenger)
    urgent_items_html = ""
    for uc in urgent_cases:
        urgent_items_html += f"""
        <a href="/community#post-{uc['id']}" style="display: block; padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--fb-text); background: var(--fb-bg); border-right: 3px solid #dc2626; margin-bottom: 6px;">
            <div style="font-weight: 800; font-size: 0.82rem; color: #991b1b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                🚨 {uc['title']}
            </div>
            <div style="font-size: 0.7rem; color: var(--fb-text-muted); display: flex; justify-content: space-between; margin-top: 2px;">
                <span>د. {uc['author_name']}</span>
                <span>{uc.get('created_at','')[:10]}</span>
            </div>
        </a>
        """

    events_items_html = ""
    for ev in upcoming_events:
        events_items_html += f"""
        <div style="padding: 10px; border-radius: 10px; background: var(--fb-bg); border: 1px solid var(--fb-border); margin-bottom: 8px;">
            <div style="font-weight: 800; font-size: 0.85rem; color: #0f766e; margin-bottom: 3px;">📅 {ev['title']}</div>
            <div style="font-size: 0.72rem; color: var(--fb-text-muted); margin-bottom: 6px;">⏱️ {ev['date_time']} • {ev.get('location', '')}</div>
            <button type="button" onclick="toggleEventInterest({ev['id']}, this)" class="btn btn-outline" style="padding: 3px 12px; font-size: 0.72rem; border-radius: 12px; font-weight: 700; width: 100%; justify-content: center;">
                ⭐ مهتم ({ev.get('interested_count', 0)})
            </button>
        </div>
        """

    colleagues_items_html = ""
    for col in colleagues:
        colleagues_items_html += f"""
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; border-radius: 8px;" class="fb-hover-row">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="position: relative;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background: #0284c7; color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.8rem;">
                        {col['name'][0]}
                    </div>
                    <span style="position: absolute; bottom: 0; left: 0; width: 8px; height: 8px; background: #16a34a; border: 1.5px solid white; border-radius: 50%;"></span>
                </div>
                <div>
                    <div style="font-weight: 700; font-size: 0.82rem; color: var(--fb-text);">د. {col['name']}</div>
                    <div style="font-size: 0.68rem; color: var(--fb-text-muted);">{col.get('clinic_name') or 'طبيب بيطري'}</div>
                </div>
            </div>
            <button type="button" onclick="openMessenger({col['id']}, '{col['name']}')" style="background: none; border: none; color: #0f766e; font-size: 1.1rem; cursor: pointer;" title="دردشة واستشارة خاصة">
                💬
            </button>
        </div>
        """

    left_col_html = f"""
    <div class="fb-left-col fb-sticky-sidebar">
        <!-- Urgent Cases Quick Box -->
        <div class="fb-card" style="padding: 14px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <div style="font-weight: 800; font-size: 0.88rem; color: #dc2626; display: flex; align-items: center; gap: 6px;">
                    <span>🚨</span> <span>حالات طارئة الآن</span>
                </div>
                <span style="background: #fee2e2; color: #991b1b; padding: 1px 6px; border-radius: 8px; font-size: 0.68rem; font-weight: 800;">مباشر</span>
            </div>
            {urgent_items_html if urgent_items_html else "<div style='color: var(--fb-text-muted); font-size: 0.78rem;'>لا توجد حالات طارئة غير محلولة حالياً.</div>"}
        </div>

        <!-- Upcoming Webinars & Events -->
        <div class="fb-card" style="padding: 14px;">
            <div style="font-weight: 800; font-size: 0.88rem; color: #0f766e; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
                <span>🎓</span> <span>ندوات وفعاليات بيطرية</span>
            </div>
            {events_items_html}
        </div>

        <!-- Active Colleagues & Instant Messenger -->
        <div class="fb-card" style="padding: 14px;">
            <div style="font-weight: 800; font-size: 0.88rem; color: var(--fb-text); margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
                <span>👥</span> <span>أطباء متاحون للتشاور</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 2px;">
                {colleagues_items_html}
            </div>
        </div>
    </div>
    """

    # Species Filter Strip
    species_strip = "".join([f'<a href="/community?species={sp_k}&category={category}&sort={sort}" style="padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; text-decoration: none; font-weight: 700; background: {"#0f766e" if species == sp_k else "var(--fb-card)"}; color: {"white" if species == sp_k else "var(--fb-text)"}; border: 1px solid var(--fb-border); white-space: nowrap;">{sp_name}</a>' for sp_k, sp_name in SPECIES_MAP.items()])

    # Feed Sorting Pills
    sort_pills = f"""
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 14px;">
        <div style="display: flex; align-items: center; gap: 6px; overflow-x: auto; padding-bottom: 4px; scrollbar-width: none;">
            <a href="/community?sort=algorithmic&category={category}&species={species}" style="padding: 5px 14px; border-radius: 20px; font-size: 0.82rem; text-decoration: none; font-weight: 800; background: {'#0f766e' if sort == 'algorithmic' else 'var(--fb-card)'}; color: {'white' if sort == 'algorithmic' else 'var(--fb-text)'}; border: 1px solid var(--fb-border);">🔥 الأكثر تفاعلاً بالخوارزمية</a>
            <a href="/community?sort=recent&category={category}&species={species}" style="padding: 5px 14px; border-radius: 20px; font-size: 0.82rem; text-decoration: none; font-weight: 700; background: {'#0f766e' if sort == 'recent' else 'var(--fb-card)'}; color: {'white' if sort == 'recent' else 'var(--fb-text)'}; border: 1px solid var(--fb-border);">✨ الأحدث نشراً</a>
            <a href="/community?sort=most_discussed&category={category}&species={species}" style="padding: 5px 14px; border-radius: 20px; font-size: 0.82rem; text-decoration: none; font-weight: 700; background: {'#0f766e' if sort == 'most_discussed' else 'var(--fb-card)'}; color: {'white' if sort == 'most_discussed' else 'var(--fb-text)'}; border: 1px solid var(--fb-border);">💬 الأكثر نقاشاً</a>
        </div>
        <div style="font-size: 0.78rem; color: var(--fb-text-muted); font-weight: 700;">
            إجمالي: {len(posts)} حالة معتمدة
        </div>
    </div>
    """

    body = f"""
    {COMMUNITY_CSS}
    <div class="fb-app-wrapper">
        <div class="fb-container">
            <!-- RIGHT SIDEBAR (RTL First: Right side) -->
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
                            {user_avatar_letter}
                        </div>
                        <button type="button" onclick="openComposerModal('general')" class="fb-composer-input">
                            بم تفكر يا دكتور {user_name_disp}؟ شارك حالة سريرية، استشارة، أو تجربة دوائية...
                        </button>
                    </div>
                    <div style="border-top: 1px solid var(--fb-border); padding-top: 10px; display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 6px;">
                        <button type="button" onclick="openComposerModal('case')" class="btn" style="background: none; border: none; color: #ea580c; font-weight: 800; font-size: 0.86rem; display: inline-flex; align-items: center; gap: 6px;">
                            <span style="font-size: 1.25rem;">🩺</span>
                            <span>نشر حالة سريرية / استشارة</span>
                        </button>
                        <button type="button" onclick="openComposerModal('urgent')" class="btn" style="background: none; border: none; color: #dc2626; font-weight: 800; font-size: 0.86rem; display: inline-flex; align-items: center; gap: 6px;">
                            <span style="font-size: 1.25rem;">🚨</span>
                            <span>حالة طارئة ومستعجلة</span>
                        </button>
                        <button type="button" onclick="openComposerModal('video')" class="btn" style="background: none; border: none; color: #0284c7; font-weight: 800; font-size: 0.86rem; display: inline-flex; align-items: center; gap: 6px;">
                            <span style="font-size: 1.25rem;">🎥</span>
                            <span>فيديو جراحي</span>
                        </button>
                        <button type="button" onclick="openComposerModal('poll')" class="btn" style="background: none; border: none; color: #7c3aed; font-weight: 800; font-size: 0.86rem; display: inline-flex; align-items: center; gap: 6px;">
                            <span style="font-size: 1.25rem;">📊</span>
                            <span>استطلاع رأي</span>
                        </button>
                    </div>
                </div>

                <!-- Species Filter Strip -->
                <div style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 8px; scrollbar-width: none;">
                    {species_strip}
                </div>

                <!-- Feed Sort Control -->
                {sort_pills}

                <!-- Posts Stream -->
                <div id="posts-stream">
                    {posts_cards_html}
                </div>
            </div>

            <!-- LEFT SIDEBAR (Desktop: Left side) -->
            {left_col_html}
        </div>

        <!-- Fixed Mobile Bottom Navigation Bar -->
        <div class="fb-mobile-nav">
            <a href="/community" class="fb-mobile-nav-btn {'active' if category == 'all' else ''}">
                <span style="font-size: 1.3rem;">📰</span>
                <span>الرئيسية</span>
            </a>
            <a href="/community?category=urgent" class="fb-mobile-nav-btn {'active' if category == 'urgent' else ''}">
                <span style="font-size: 1.3rem;">🚨</span>
                <span>طارئة</span>
            </a>
            <a href="javascript:void(0)" onclick="openComposerModal('case')" class="fb-mobile-nav-btn" style="color: #0f766e;">
                <div style="width: 38px; height: 38px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; box-shadow: 0 4px 10px rgba(15,118,110,0.3);">
                    ➕
                </div>
            </a>
            <a href="/community?category=case_study" class="fb-mobile-nav-btn {'active' if category == 'case_study' else ''}">
                <span style="font-size: 1.3rem;">🩺</span>
                <span>استشارات</span>
            </a>
            <a href="javascript:void(0)" onclick="toggleMessengerDrawer()" class="fb-mobile-nav-btn">
                <span style="font-size: 1.3rem;">💬</span>
                <span>المراسلة</span>
            </a>
        </div>

        <!-- Vet Messenger Floating Box -->
        <div class="vet-messenger-box" id="vet-messenger-window">
            <div style="background: linear-gradient(135deg, #0f766e, #0d9488); color: white; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>💬</span>
                    <strong style="font-size: 0.95rem;" id="chat-colleague-name">دردشة الأطباء</strong>
                </div>
                <button type="button" onclick="closeMessenger()" style="background: none; border: none; color: white; font-size: 1.2rem; cursor: pointer;">✕</button>
            </div>
            <div id="chat-messages-container" style="height: 280px; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; background: var(--fb-bg);">
                <div style="color: var(--fb-text-muted); font-size: 0.8rem; text-align: center; margin-top: 40px;">اختر زميلاً لبدء استشارة أو مناقشة حالة سريرية خاصة.</div>
            </div>
            <form onsubmit="sendDirectMessage(event)" style="display: flex; gap: 6px; padding: 10px; background: var(--fb-card); border-top: 1px solid var(--fb-border);">
                <input type="hidden" id="chat-receiver-id" value="0">
                <input type="text" id="chat-text-input" required placeholder="اكتب استشارتك الخاصة..." style="flex: 1; padding: 8px 12px; border: 1px solid var(--fb-border); border-radius: 20px; font-size: 0.84rem; background: var(--fb-bg); color: var(--fb-text); outline: none;">
                <button type="submit" style="background: #0f766e; border: none; color: white; border-radius: 50%; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                    🚀
                </button>
            </form>
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
                                    <option value="other">🐾 فصائل أخرى</option>
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
                                    <option value="مخصي">مخصي (Castrated)</option>
                                </select>
                            </div>
                        </div>

                        <div style="margin-bottom: 10px;">
                            <label style="display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 3px;">🌡️ الأعراض السريرية والعلامات الحيوية:</label>
                            <input type="text" name="symptoms" placeholder="مثال: حرارة 40.2، خمول حاد، استسقاء بطني، تضخم عقد لمفاوية" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                        </div>

                        <div>
                            <label style="display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 3px;">💊 الأدوية والبروتوكولات المعطاة سابقاً:</label>
                            <input type="text" name="medications" placeholder="مثال: أوكسيتتراسيكلين، فلونيكسين، ليزكس" style="width: 100%; padding: 8px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.85rem; background: var(--fb-card); color: var(--fb-text);">
                        </div>
                    </div>

                    <div style="margin-bottom: 12px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.88rem;">📝 الشرح والتقرير السريري وتفاصيل الاستشارة:</label>
                        <textarea name="content" required rows="4" placeholder="اكتب وصفاً وافياً للحالة السريرية، الفحص الموضعي، والتاريخ المرضي وموضوع استشارة الزملاء..." style="width: 100%; padding: 12px; border: 1px solid var(--fb-border); border-radius: 10px; font-size: 0.95rem; background: var(--fb-bg); color: var(--fb-text); line-height: 1.6;"></textarea>
                    </div>

                    <!-- Media Attachment -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px;">
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.82rem;">📷 إرفاق صور / أشعة / تحليل PDF:</label>
                            <input type="file" name="media_file" accept="image/*,video/*,application/pdf" style="width: 100%; padding: 6px; border: 1px solid var(--fb-border); border-radius: 8px; font-size: 0.82rem; background: var(--fb-bg);">
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

        <!-- Fullscreen Story Viewer Modal -->
        <div id="story-viewer-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.92); z-index: 1200; align-items: center; justify-content: center; flex-direction: column;">
            <button type="button" onclick="document.getElementById('story-viewer-modal').style.display='none'" style="position: absolute; top: 20px; left: 20px; background: none; border: none; color: white; font-size: 2rem; cursor: pointer;">✕</button>
            <div style="position: relative; max-width: 420px; width: 100%; max-height: 80vh; text-align: center;">
                <div id="story-author-tag" style="position: absolute; top: 14px; right: 14px; background: rgba(0,0,0,0.6); color: white; padding: 4px 12px; border-radius: 20px; font-weight: 800; font-size: 0.88rem;"></div>
                <img id="story-img-elem" src="" style="max-width: 100%; max-height: 70vh; border-radius: 14px; object-fit: contain; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
                <div id="story-caption-elem" style="color: white; font-size: 1rem; font-weight: 700; margin-top: 14px; text-shadow: 0 2px 4px rgba(0,0,0,0.8);"></div>
            </div>
        </div>

        <!-- Image Lightbox Modal -->
        <div id="image-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.9); z-index: 1200; align-items: center; justify-content: center;" onclick="this.style.display='none'">
            <img id="image-modal-src" src="" style="max-width: 95%; max-height: 90vh; border-radius: 10px; object-fit: contain;">
        </div>
    </div>

    {COMMUNITY_JS}
    """
    return HTMLResponse(content=get_base_html("VetBook | ملتقى الأطباء البيطريين", body, user, lang), media_type="text/html; charset=utf-8")



# ==============================================================================
# ROUTE: POST /community/post (Create Rich Post, Clinical Case, or Video)
# ==============================================================================
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
    c.execute("""
    INSERT INTO community_posts (
        user_id, author_name, author_specialty, author_country,
        category, title, content, is_urgent, species, breed, age, weight,
        gender, symptoms, medications, group_id, image_path, video_path,
        media_type, quality_score, virality_score, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0, ?)
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
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

    return RedirectResponse("/community", status_code=303)


# ==============================================================================
# ROUTE: POST /community/like/{post_id} (Multi-reactions with AJAX JSON)
# ==============================================================================
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

    # Trigger virality recalculation
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


# ==============================================================================
# ROUTE: POST /community/comment/{post_id} (Threaded Comments & AJAX)
# ==============================================================================
@router.post("/community/comment/{post_id}")
async def community_add_comment(
    request: Request,
    post_id: int,
    content: str = Form(...),
    parent_comment_id: int = Form(0),
    comment_image: UploadFile = File(None)
):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        if request.headers.get("Accept") == "application/json":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return RedirectResponse("/login?redirect=/community", status_code=303)

    if not content or not content.strip():
        return RedirectResponse(f"/community#post-{post_id}", status_code=303)

    saved_img_name = ""
    if comment_image and comment_image.filename:
        ext = os.path.splitext(comment_image.filename)[1] or ".jpg"
        saved_img_name = f"cm_{int(datetime.now().timestamp())}_{user['id']}{ext}"
        try:
            with open(os.path.join(UPLOAD_DIR, saved_img_name), "wb") as buf:
                shutil.copyfileobj(comment_image.file, buf)
        except Exception:
            saved_img_name = ""

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_comments (post_id, user_id, author_name, author_specialty, author_country, content, parent_comment_id, image_url, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_id,
        user["id"],
        user.get("name", "طبيب بيطري"),
        user.get("clinic_name", "طب بيطري"),
        user.get("country", "مصر"),
        content.strip(),
        parent_comment_id,
        saved_img_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    new_cm_id = c.lastrowid
    c.execute("UPDATE community_posts SET comments_count = comments_count + 1 WHERE id = ?", (post_id,))

    # Virality update
    c.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,))
    p = c.fetchone()
    total_comments = p["comments_count"] if p else 1
    if p:
        v_score = compute_virality_score(dict(p))
        c.execute("UPDATE community_posts SET virality_score = ? WHERE id = ?", (v_score, post_id))

    conn.commit()
    conn.close()

    if request.headers.get("Accept") == "application/json":
        author_name = user.get("name", "طبيب بيطري")
        cm_html = f"""
        <div style="margin-bottom: 12px; display: flex; gap: 10px; align-items: flex-start;" id="comment-{new_cm_id}">
            <div style="width: 34px; height: 34px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 700; flex-shrink: 0;">
                {author_name[0]}
            </div>
            <div style="flex: 1;">
                <div class="fb-comment-bubble">
                    <strong style="font-size: 0.88rem; color: #0f766e;">د. {author_name}</strong>
                    <div style="line-height: 1.5; margin-top: 3px;">{content.strip()}</div>
                    {f'<img src="/uploads/{saved_img_name}" style="max-width: 240px; border-radius: 8px; margin-top: 8px; display: block;">' if saved_img_name else ''}
                </div>
                <div style="font-size: 0.72rem; color: var(--fb-text-muted); margin-top: 2px; margin-right: 10px;">
                    الآن
                </div>
            </div>
        </div>
        """
        return JSONResponse({
            "success": True,
            "comment_id": new_cm_id,
            "comment_html": cm_html,
            "total_comments": total_comments
        })

    return RedirectResponse(f"/community#post-{post_id}", status_code=303)


# ==============================================================================
# ROUTE: POST /community/comment/best/{comment_id} (Mark Best Diagnosis)
# ==============================================================================
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

    # Check that current user is the author of the post
    c.execute("SELECT user_id FROM community_posts WHERE id = ?", (cm["post_id"],))
    post = c.fetchone()
    if not post or post["user_id"] != user["id"]:
        conn.close()
        return JSONResponse({"error": "forbidden"}, status_code=403)

    # Set best answer
    c.execute("UPDATE community_comments SET is_best_answer = 0 WHERE post_id = ?", (cm["post_id"],))
    c.execute("UPDATE community_comments SET is_best_answer = 1 WHERE id = ?", (comment_id,))
    
    # Award +50 reputation points to author of comment
    c.execute("UPDATE users SET reputation_score = reputation_score + 50 WHERE id = ?", (cm["user_id"],))

    conn.commit()
    conn.close()

    return JSONResponse({"success": True})


# ==============================================================================
# ROUTE: POST /community/ai-consult/{post_id} (Ask VetMind AI)
# ==============================================================================
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

    # Check if already generated
    if post["ai_analysis"]:
        conn.close()
        return JSONResponse({"success": True, "analysis": post["ai_analysis"]})

    # Prepare Clinical AI Prompt
    p_dict = dict(post)
    case_context = f"""
    عنوان الحالة: {p_dict.get('title')}
    الفصيلة: {p_dict.get('species')} | السلالة: {p_dict.get('breed')} | العمر: {p_dict.get('age')} | الوزن: {p_dict.get('weight')} كجم
    الأعراض السريرية: {p_dict.get('symptoms')}
    الأدوية المعطاة سابقاً: {p_dict.get('medications')}
    تفاصيل الفحص: {p_dict.get('content')}
    """

    prompt = f"""
    بصفتك الذكاء الاصطناعي السريري المتقدم لمنصة VetMind AI Enterprise، قم بتقديم استشارة طبية متخصصة وموجزة ومفيدة للزملاء الأطباء لهذه الحالة السريرية:
    {case_context}

    يرجى تنظيم الرد بالنقاط التالية:
    1. أبرز التشخيصات التفريقية المحتملة (Top Differential Diagnoses)
    2. الفحوصات المخبرية أو التأكيدية المقترحة (Diagnostic Tests)
    3. التوصيات العلاجية وبروتوكول الرعاية الموصى به (Clinical Recommendations)
    """

    api_key = get_effective_groq_api_key(request)
    ai_response = ask_ai_chat(api_key, prompt, [], p_dict.get("image_path"), "ar", "مصر")

    c.execute("UPDATE community_posts SET ai_analysis = ? WHERE id = ?", (ai_response, post_id))

    # Also insert as AI assistant comment
    c.execute("""
    INSERT INTO community_comments (post_id, user_id, author_name, author_specialty, author_country, content, is_ai_comment, created_at)
    VALUES (?, 0, 'VetMind AI المساعد السريري', 'ذكاء اصطناعي سريري معتمد', 'سحابي', ?, 1, ?)
    """, (post_id, ai_response, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return JSONResponse({"success": True, "analysis": ai_response})


# ==============================================================================
# ROUTE: POST /community/bookmark/{post_id} (Toggle Save Case)
# ==============================================================================
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
        is_bookmarked = False
    else:
        c.execute("INSERT INTO community_bookmarks (post_id, user_id, created_at) VALUES (?, ?, ?)",
                  (post_id, user["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return JSONResponse({"success": True, "is_bookmarked": is_bookmarked})


# ==============================================================================
# ROUTE: POST /community/poll/vote/{post_id}
# ==============================================================================
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
    except Exception as e:
        conn.rollback()
    finally:
        conn.close()

    return JSONResponse({"success": True})


# ==============================================================================
# ROUTE: POST /community/story/create
# ==============================================================================
@router.post("/community/story/create")
async def community_create_story(
    request: Request,
    caption: str = Form(""),
    story_media: UploadFile = File(...)
):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?redirect=/community", status_code=303)

    if not story_media or not story_media.filename:
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


# ==============================================================================
# ROUTE: POST /community/post/delete/{post_id}
# ==============================================================================
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


# ==============================================================================
# ROUTE: GET /community/profile/{user_id} (Doctor Profile & Reputation)
# ==============================================================================
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

    conn.close()

    # Profile Header HTML
    cover_bg = "linear-gradient(135deg, #0f766e 0%, #0d9488 100%)"
    body = f"""
    {COMMUNITY_CSS}
    <div class="fb-app-wrapper" style="padding-top: 14px;">
        <div style="max-width: 960px; margin: 0 auto; padding: 0 12px;">
            <!-- Facebook-style Profile Header Card -->
            <div class="fb-card" style="margin-bottom: 20px;">
                <!-- Cover Photo -->
                <div style="height: 180px; background: {cover_bg}; border-radius: 16px 16px 0 0; position: relative;">
                </div>
                
                <!-- Profile Avatar & Bio Row -->
                <div style="padding: 0 24px 20px 24px; position: relative;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 14px; margin-top: -55px; margin-bottom: 16px;">
                        <div style="width: 110px; height: 110px; border-radius: 50%; border: 4px solid var(--fb-card); background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 3rem; font-weight: 800; box-shadow: 0 4px 14px rgba(0,0,0,0.15);">
                            {t_dict['name'][0]}
                        </div>
                        <div style="display: flex; gap: 10px;">
                            {f'<button type="button" onclick="openMessenger({user_id}, \'{t_dict["name"]}\')" class="btn btn-primary" style="padding: 8px 20px; border-radius: 20px; font-weight: 700;">💬 إرسال استشارة خاصة</button>' if (curr_user and curr_user['id'] != user_id) else ''}
                            <a href="/community" class="btn btn-outline" style="padding: 8px 18px; border-radius: 20px;">⬅️ العودة للشبكة</a>
                        </div>
                    </div>

                    <h1 style="margin: 0; font-size: 1.6rem; color: var(--fb-text); display: flex; align-items: center; gap: 8px;">
                        <span>د. {t_dict['name']}</span>
                        <span style="font-size: 1.1rem; color: #059669;" title="طبيب بيطري معتمد وموثق">🩺</span>
                        <span style="background: #ecfdf5; color: #047857; font-size: 0.72rem; padding: 3px 10px; border-radius: 12px; font-weight: 800; border: 1px solid #6ee7b7;">طبيب معتمد</span>
                    </h1>

                    <div style="font-size: 0.95rem; color: var(--fb-text-muted); margin-top: 4px;">
                        {t_dict.get('clinic_name') or 'مركز طب وجراحة الحيوان المتقدم'} • {t_dict.get('country') or 'مصر'}
                    </div>

                    <p style="color: var(--fb-text); font-size: 0.92rem; margin: 12px 0; line-height: 1.6;">
                        {t_dict.get('bio') or 'طبيب بيطري ممارس متخصص في التشخيص الإكلينيكي والجراحة ورعاية الحيوانات، عضو شبكة VetMind AI للتبادل العلمي.'}
                    </p>

                    <!-- Stats Row -->
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
            <h3 style="color: var(--fb-text); margin-bottom: 14px;">📋 الحالات والمنشورات السريرية للدكتور {t_dict['name']}:</h3>
            {"".join([f'<div class="fb-card" style="padding: 16px; margin-bottom: 14px;"><a href="/community#post-{dp["id"]}" style="text-decoration: none; color: inherit;"><h4 style="margin: 0 0 6px 0; color: #0f766e; font-size: 1.1rem;">{dp["title"]}</h4><p style="margin: 0; font-size: 0.9rem; color: var(--fb-text); line-height: 1.6;">{dp["content"][:240]}...</p><div style="font-size: 0.75rem; color: var(--fb-text-muted); margin-top: 8px;">⏱️ {dp["created_at"]} • 🔥 {dp.get("likes_count", 0)} تفاعل • 💬 {dp.get("comments_count", 0)} رد</div></a></div>' for dp in doctor_posts]) if doctor_posts else "<div class='fb-card' style='padding: 24px; text-align: center; color: var(--fb-text-muted);'>لم يقم هذا الطبيب بنشر حالات بعد.</div>"}
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(f"د. {t_dict['name']} | VetBook", body, curr_user, lang), media_type="text/html; charset=utf-8")


# ==============================================================================
# ROUTE: POST /community/events/interest/{event_id}
# ==============================================================================
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


# ==============================================================================
# ROUTE: GET /community/messages/{colleague_id}
# ==============================================================================
@router.get("/community/messages/{colleague_id}")
async def community_get_chat(request: Request, colleague_id: int):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    SELECT * FROM community_messages 
    WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
    ORDER BY id ASC LIMIT 50
    """, (user["id"], colleague_id, colleague_id, user["id"]))
    msgs = [dict(r) for r in c.fetchall()]
    conn.close()

    return JSONResponse({"success": True, "messages": msgs})


# ==============================================================================
# ROUTE: POST /community/messages/send
# ==============================================================================
@router.post("/community/messages/send")
async def community_send_message(request: Request, receiver_id: int = Form(...), message: str = Form(...)):
    from app import get_current_user

    user = get_current_user(request)
    if not user or not message.strip():
        return JSONResponse({"error": "invalid"}, status_code=400)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_messages (sender_id, receiver_id, message, created_at)
    VALUES (?, ?, ?, ?)
    """, (user["id"], receiver_id, message.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return JSONResponse({"success": True})


# ==============================================================================
# ROUTE: GET /admin/community/boost/{post_id} & /admin/community/pin/{post_id}
# ==============================================================================
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

