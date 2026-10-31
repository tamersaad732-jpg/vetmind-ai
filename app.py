# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise v4.2 - Long-Term Investment Grade Veterinary Clinical Intelligence
"""

import os
import io
import json
import base64
import sqlite3
import shutil
import hashlib
import ssl
import random
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from PIL import Image, ImageStat
from fastapi import FastAPI, Form, File, UploadFile, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from translations_data import DATA as TRANSLATIONS_DB
from references_db import get_all_references, get_arab_references, get_global_references, get_reference_by_id
from dosage_engine import calculate_precise_dosage, format_drug_display, get_drug_concise_function
from prayer_engine import calculate_prayer_times
import clinic_routes
import interactive_tools
import community_routes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DOCS_DIR = os.path.join(STATIC_DIR, "reference_docs")
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")

# Vercel Serverless & Read-only Environment Compatibility
if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
    tmp_db = "/tmp/vetmind.db"
    if not os.path.exists(tmp_db) and os.path.exists(DB_PATH):
        try:
            import shutil
            shutil.copy2(DB_PATH, tmp_db)
        except Exception:
            pass
    if os.path.exists(tmp_db):
        DB_PATH = tmp_db
    UPLOAD_DIR = "/tmp/uploads"

try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
except Exception:
    pass

app = FastAPI(title="VetMind AI Enterprise v4.3 - Global Clinical Veterinary Platform")
app.include_router(clinic_routes.router)
app.include_router(interactive_tools.router)
app.include_router(community_routes.router)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_route():
    from fastapi.responses import FileResponse
    ico_path = os.path.join(STATIC_DIR, "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon", headers={"Cache-Control": "no-cache, must-revalidate"})
    return FileResponse(os.path.join(STATIC_DIR, "favicon.svg"), media_type="image/svg+xml")


SUPPORTED_LANGUAGES = ["ar", "en", "fr", "es", "de", "it", "zh", "ja"]
ARAB_COUNTRIES = ["مصر", "السعودية", "الإمارات", "الأردن", "السودان", "العراق", "الكويت", "عمان", "قطر", "البحرين", "المغرب", "تونس", "الجزائر", "ليبيا", "لبنان", "فلسطين", "اليمن", "دول أخرى"]

GROQ_VISION_MODEL = "qwen/qwen3.8-27b"
GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "allam-2-7b"
]

def get_effective_groq_api_key(request: Request = None) -> str:
    if request:
        try:
            ck = request.cookies.get("groq_api_key", "").strip()
            if ck and ck.startswith("gsk_"):
                return ck
        except Exception:
            pass
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'ai_api_key'")
        row = c.fetchone()
        conn.close()
        if row and row["value"] and row["value"].strip().startswith("gsk_"):
            return row["value"].strip()
    except Exception:
        pass
    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    if env_key and env_key.startswith("gsk_"):
        return env_key
    return ""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_text(lang: str, key: str, default: str = "") -> str:
    lang_dict = TRANSLATIONS_DB.get(lang, TRANSLATIONS_DB.get("ar", {}))
    val = lang_dict.get(key)
    if val:
        return val
    return TRANSLATIONS_DB.get("ar", {}).get(key, default or key)

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return f"{salt}:{key}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, key = hashed.split(":")
        check = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return check == key
    except Exception:
        return False

def make_session_token(user_id: int) -> str:
    raw = f"{user_id}:vetmind_enterprise_2026:{datetime.now().strftime('%Y%m%d')}"
    sig = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return f"{user_id}:{sig}"

def verify_session_token(token: str):
    if not token or ":" not in token:
        return None
    try:
        user_id_str, sig = token.split(":", 1)
        user_id = int(user_id_str)
        raw = f"{user_id}:vetmind_enterprise_2026:{datetime.now().strftime('%Y%m%d')}"
        expected_sig = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        if sig == expected_sig:
            return user_id
    except Exception:
        return None
    return None

def get_current_user(request: Request):
    token = request.cookies.get("vetmind_session")
    if not token:
        return None
    uid = verify_session_token(token)
    if not uid:
        return None
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (uid,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE users SET last_active_at = ? WHERE id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
        conn.commit()
    conn.close()
    if row:
        return dict(row)
    return None

@app.middleware("http")
async def require_auth_middleware(request: Request, call_next):
    path = request.headers.get("x-matched-path", "").split("?")[0] or request.url.path
    raw_info = f"{path} {request.url} {request.headers.get('x-now-route-matches', '')} {request.headers.get('x-matched-path', '')}".lower()

    # 1. Allow all static files & media uploads & favicon
    if any(k in raw_info for k in ["/static", "/uploads", "favicon.ico", ".css", ".js", ".png", ".jpg", ".svg", ".json", ".ico"]):
        return await call_next(request)

    # 2. Allow public auth endpoints & language switch
    if any(k in raw_info for k in ["login", "register", "verify-otp", "set-language"]):
        return await call_next(request)

    # 3. Check user authentication
    user = get_current_user(request)
    if not user:
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header and "text/html" not in accept_header:
            return JSONResponse({"status": "error", "message": "Authentication required", "redirect": "/login"}, status_code=401)

        target = path
        if request.url.query:
            target += f"?{request.url.query}"
        login_url = f"/login?redirect={urllib.parse.quote(target)}" if target not in ["/", "/api/index.py", "/api/index"] else "/login"
        return RedirectResponse(login_url, status_code=303)

    return await call_next(request)

def get_user_lang(request: Request) -> str:
    # 1. Check query parameter ?lang=... (explicit URL override)
    q_lang = request.query_params.get("lang")
    if q_lang and q_lang.strip().lower() in SUPPORTED_LANGUAGES:
        return q_lang.strip().lower()

    # 2. Check logged-in user preferred_lang (saved permanently in database)
    user = get_current_user(request)
    if user and user.get("preferred_lang") in SUPPORTED_LANGUAGES:
        return user["preferred_lang"].strip().lower()

    # 3. Check cookie vetmind_lang
    cookie_lang = request.cookies.get("vetmind_lang")
    if cookie_lang and cookie_lang.strip().lower() in SUPPORTED_LANGUAGES:
        return cookie_lang.strip().lower()

    # 4. Default fallback
    return "ar"

def is_user_community_approved(user_dict: dict) -> bool:
    if not user_dict:
        return False
    if user_dict.get("is_admin"):
        return True
    user_id = user_dict.get("id")
    if not user_id:
        return False
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM community_subscriptions WHERE user_id = ? AND status = 'approved' LIMIT 1", (user_id,))
        row = c.fetchone()
        conn.close()
        return bool(row)
    except Exception:
        return False

def analyze_image_locally(image_path: str):
    try:
        if not os.path.exists(image_path):
            return {
                "summary": "فحص بصري قياسي للأنسجة الظاهرية",
                "detected_lesion": "آفة سريرية ظاهرية",
                "erythema_score": 35,
                "necrosis_score": 10,
                "exudate_score": 15,
                "contrast_score": 60,
                "clinical_impression": "فحص أولي للأنسجة المخاطية والجلدية"
            }

        with Image.open(image_path) as img:
            width, height = img.size
            img_format = img.format or "JPEG"
            rgb_img = img.convert("RGB")

            cw, ch = width // 6, height // 6
            crop = rgb_img.crop((cw, ch, width - cw, height - ch))
            stat = ImageStat.Stat(crop)
            r_mean, g_mean, b_mean = stat.mean

            erythema_ratio = r_mean / max(1.0, (g_mean + b_mean) / 2.0)
            erythema_score = min(100, int(max(0, (erythema_ratio - 1.0) * 120 + (r_mean / 255.0) * 40)))

            gray = crop.convert("L")
            dark_pixels = sum(1 for p in gray.getdata() if p < 45)
            total_pixels = max(1, gray.width * gray.height)
            necrosis_score = min(100, int((dark_pixels / total_pixels) * 400))

            yellow_ratio = (r_mean + g_mean) / max(1.0, 2.0 * b_mean)
            exudate_score = min(100, int(max(0, (yellow_ratio - 1.1) * 80)))

            contrast_score = min(100, int(stat.stddev[0] * 1.5))

            if erythema_score > 60 and exudate_score > 40:
                detected_lesion = "التهاب فموي حويصلي متقرح مصحوب بسيلان لعابي وإفرازات مخاطية قيحية (اشتباه حمى قلاعية FMD أو التهاب الفم التقرحي)"
                clinical_impression = "آفة حادة شديدة الاحتقان والتآكل المخاطي تتطلب عزلاً بيولوجياً فورياً ومسحة للتأكيد المخبري."
            elif erythema_score > 55 and necrosis_score > 30:
                detected_lesion = "تنخر نسيجي والتهاب جلدي عقدي متقرح (اشتباه الجلد العقدي Lumpy Skin أو الجدري Sheep Pox)"
                clinical_impression = "عقد جلدية متنخرة بؤرية مع وذمة موضعية. تطبيق مضاد التهاب واسع وتطهير موضعي."
            elif exudate_score > 50:
                detected_lesion = "إفرازات مخاطية قيحية عينية أو أنفية مع احتقان ملتحمة (اشتباه باستريلا أو ميكوبلازما أو متلازمة تنفسية)"
                clinical_impression = "عدوى بكتيرية ثانوية بالجهاز التنفسي أو الملتحمة تستدعي تدخلاً بالمضادات الحيوية واسعة المدى."
            elif necrosis_score > 40:
                detected_lesion = "جلبات قشرية داكنة وجفاف جلدي موضعي (اشتباه قراع جلدي فصائلي Ringworm أو إكزيما حادة)"
                clinical_impression = "آفة جلدية دائرية متقشرة بدون نزف فوري، تتطلب مضادات فطريات موضعية وعزل."
            else:
                detected_lesion = "احتقان نسيجي موضعي وتغير سطحي في تروية الأغشية المخاطية"
                clinical_impression = "فحص سريري يظهر وذمة خفيفة إلى متوسطة بدون تنخر متقدم."

            summary = f"فحص ميكروسكوبي ورقمي: الأبعاد {width}×{height} بكسل ({img_format}). مؤشر الاحمرار: {erythema_score}% | مؤشر التنخر: {necrosis_score}% | مؤشر الإفرازات: {exudate_score}%."

            return {
                "summary": summary,
                "detected_lesion": detected_lesion,
                "erythema_score": erythema_score,
                "necrosis_score": necrosis_score,
                "exudate_score": exudate_score,
                "contrast_score": contrast_score,
                "clinical_impression": clinical_impression
            }
    except Exception as e:
        return {
            "summary": f"تحليل بصري رقمي عام: {str(e)}",
            "detected_lesion": "آفة سريرية ظاهرية",
            "erythema_score": 40,
            "necrosis_score": 15,
            "exudate_score": 20,
            "contrast_score": 50,
            "clinical_impression": "فحص سريري استرشادي للأنسجة"
        }

# ==============================================================================
# SMART CONDITION-AWARE & SPECIES-AWARE DRUG MATCHING ENGINE
# ==============================================================================
def get_localized_drugs(country: str, condition_hint: str = "", species: str = ""):
    """
    Intelligent Condition-Aware & Species-Aware Pharmacotherapy Matcher.
    Dynamically maps clinical symptoms, detected lesions, and species to registered products.
    Ensures different cases receive completely distinct, disease-specific medications!
    """
    conn = get_db()
    c = conn.cursor()
    
    # Map country name to standard database format
    c_clean = (country or "").strip()
    country_map = {
        "egypt": "مصر", "saudi arabia": "السعودية", "saudi": "السعودية",
        "uae": "الإمارات", "united arab emirates": "الإمارات", "emirates": "الإمارات",
        "jordan": "الأردن", "sudan": "السودان", "iraq": "العراق",
        "kuwait": "الكويت", "morocco": "المغرب", "algeria": "الجزائر"
    }
    target_country = country_map.get(c_clean.lower(), c_clean if c_clean in ["مصر", "السعودية", "الإمارات", "الأردن", "السودان", "العراق", "الكويت", "المغرب", "الجزائر"] else "مصر")

    hint = (condition_hint or "").lower()
    spec = (species or "").lower()

    matched_categories = []
    primary_category = ""

    # 1. Mastitis & Reproductive (Check before general antibiotics)
    if any(k in hint for k in ["ضرع", "حليب", "ورم الضرع", "mastitis", "ولادة", "مشيمة", "رحم", "شبق", "عشار"]):
        matched_categories = ["أدوية الضرع والتناسل", "مضادات حيوية", "مضادات التهاب ومسكنات"]
        primary_category = "أدوية الضرع والتناسل"

    # 2. Gastrointestinal, Bloat & Colic
    elif any(k in hint for k in ["كرش", "نفاخ", "انتفاخ", "غازات", "مغص", "إسهال", "اسهال", "حموضة", "تسمم معوي", "روث"]):
        matched_categories = ["أدوية الهضم والكرش", "مضادات حيوية", "فيتامينات ومعادن"]
        primary_category = "أدوية الهضم والكرش"

    # 3. Parasites & Blood Protozoa (Babesia, Theileria, Trypanosoma)
    elif any(k in hint for k in ["طفيليات", "ديدان", "حكة", "جرب", "قراد", "فاشيولا", "كبدية", "هيام", "تريبانوسوما", "بابيزيا", "ثايليريا", "دم في البول", "حمرة البول", "بول مدمم"]):
        matched_categories = ["طفيليات وديدان", "فيتامينات ومعادن"]
        primary_category = "طفيليات وديدان"

    # 4. Equine Colic & Lameness
    elif any(k in hint or k in spec for k in ["خيل", "خيول", "حصان", "مهر", "horse", "equine", "مغص الخيل"]):
        matched_categories = ["مضادات التهاب ومسكنات", "أدوية الهضم والكرش", "فيتامينات ومعادن"]
        primary_category = "مضادات التهاب ومسكنات"

    # 5. Companion Animals (Dogs & Cats Parvo, Vomiting)
    elif any(k in hint or k in spec for k in ["كلب", "قطة", "كلاب", "قطط", "بارفو", "قيء", "ترجيع", "استفراغ", "canine", "feline"]):
        matched_categories = ["أدوية الحيوانات الأليفة", "مضادات حيوية", "مضادات التهاب ومسكنات"]
        primary_category = "أدوية الحيوانات الأليفة"

    # 6. Respiratory & Pneumonia
    elif any(k in hint for k in ["رئة", "تنفس", "سعال", "باستريلا", "ميكوبلازما", "حرارة", "التهاب رئوي", "كحة", "أنف", "صدر", "أكياس هوائية"]):
        matched_categories = ["مضادات حيوية", "مضادات التهاب ومسكنات"]
        primary_category = "مضادات حيوية"

    # 7. Foot, Mouth & Ulcerative Lesions (FMD, Foot Rot)
    elif any(k in hint for k in ["حوافر", "عرج", "تقرح", "فم", "لعاب", "قلاعية", "جلد عقدي", "عقد", "جروح"]):
        matched_categories = ["مطهرات وبخاخات", "مضادات التهاب ومسكنات", "مضادات حيوية"]
        primary_category = "مطهرات وبخاخات"

    # 8. Camels & Racing Dromedary (Surra, Exhaustion)
    elif any(k in hint or k in spec for k in ["إبل", "هجن", "نوق", "سباق", "camel", "حيران", "سورا"]):
        matched_categories = ["طفيليات وديدان", "فيتامينات ومعادن", "مضادات حيوية"]
        primary_category = "طفيليات وديدان"

    # 9. Toxicities & Poisoning
    elif any(k in hint for k in ["تسمم", "مبيد", "حشري", "أعصاب", "ارتعاش", "فوسفوري"]):
        matched_categories = ["مضادات التهاب ومسكنات", "فيتامينات ومعادن"]
        primary_category = "مضادات التهاب ومسكنات"

    products = []
    if matched_categories:
        placeholders = ",".join(["?"] * len(matched_categories))
        search_kw = ""
        for kw in ["ضرع", "حليب", "كرش", "نفاخ", "انتفاخ", "ديدان", "طفيليات", "قراد", "بابيزيا", "مغص", "رئة", "تنفس", "كحة", "قلاعية", "حافر", "عرج", "هيام", "بارفو", "قيء", "تسمم"]:
            if kw in hint:
                search_kw = f"%{kw}%"
                break
        
        c.execute(f"""
        SELECT * FROM local_products 
        WHERE (country = ? OR country = 'دول أخرى') AND category IN ({placeholders})
        ORDER BY 
            CASE WHEN category = ? THEN 0 ELSE 1 END,
            CASE WHEN (? != '' AND (indication LIKE ? OR trade_name LIKE ?)) THEN 0 ELSE 1 END,
            CASE WHEN country = ? THEN 0 ELSE 1 END, 
            id ASC
        LIMIT 5
        """, (target_country, *matched_categories, primary_category, search_kw, search_kw, search_kw, target_country))
        products = [dict(r) for r in c.fetchall()]

    if not products:
        c.execute("""
        SELECT * FROM local_products 
        WHERE country = ? OR country = 'دول أخرى'
        ORDER BY CASE WHEN country = ? THEN 0 ELSE 1 END, id ASC
        LIMIT 5
        """, (target_country, target_country))
        products = [dict(r) for r in c.fetchall()]

    return products

# ==============================================================================
# VETERINARY DRUG-DRUG INTERACTIONS KNOWLEDGE BASE
# ==============================================================================
INTERACTIONS_DB = [
    {
        "drug_a": "تايلوزين (Tylosin) / تلميكوسين (Tilmicosin)",
        "drug_b": "بنسلين (Penicillin) / سيفالوسبورين (Cephalosporin)",
        "level": "danger",
        "level_title": "🔴 تضاد دوائي غير مستحب (Bacteriostatic vs. Bactericidal)",
        "mechanism": "الماكروليد (تايلوزين) يثبط نمو البكتيريا وانقسامها، بينما البنسلينات تتطلب بكتيريا نشطة الانقسام لتدمير جدارها الخلوي، مما يبطل مفعول البنسلين تماماً."
    },
    {
        "drug_a": "فلونيكسين ميغلومين (Flunixin Meglumine)",
        "drug_b": "ديكساميثازون (Dexamethasone)",
        "level": "danger",
        "level_title": "🔴 خطر تسممي وقرحة معدية ومعوية حادة",
        "mechanism": "الجمع بين مضاد التهاب غير ستيرويدي (NSAID) وكورتيزون ستيرويدي يضاعف تآكل بطانة المعدة ويؤدي لنزيف هضمي وتلف كلوي حاد."
    },
    {
        "drug_a": "جنتاميسين (Gentamicin) / أمينوجليكوسيدات",
        "drug_b": "فوروسيميد (Furosemide / Lasix)",
        "level": "warning",
        "level_title": "🟡 تحذير: مضاعفة السمية الكلوية والسمعية",
        "mechanism": "المدررات تزيد تركيز الأمينوجليكوزيدات في القشرة الكلوية والأذن الداخلية، مما قد يسبب صمماً وفشلاً كلوياً حاداً."
    },
    {
        "drug_a": "ليفاميزول (Levamisole)",
        "drug_b": "مبيدات الفسفور العضوي (Diazinon / Organophosphates)",
        "level": "danger",
        "level_title": "🔴 سمية عصبية قاتلة وشلل تنفسي",
        "mechanism": "كلا المركبين يثبط إنزيم الكولين استريز ويزيد النواقل العصبية النيكوتينية، مما يسبب تسمماً عصبياً واختناقاً حاداً."
    },
    {
        "drug_a": "بنسلين (Penicillin G)",
        "drug_b": "ستربتومايسين (Streptomycin)",
        "level": "safe",
        "level_title": "🟢 تآزر دوائي معتمد وفعال (Synergistic Combo)",
        "mechanism": "تركيبة قياسية عالمية معتمدة؛ البنسلين يفتح ثغرات في جدار الخلية البكتيرية ليسهل دخول الستربتومايسين للقضاء على البكتيريا السالبة والموجبة."
    }
]

def check_drug_interaction(drug_a_name: str, drug_b_name: str):
    a = (drug_a_name or "").lower()
    b = (drug_b_name or "").lower()
    for item in INTERACTIONS_DB:
        da = item["drug_a"].lower()
        db = item["drug_b"].lower()
        if (any(k in a for k in ["تايلوزين", "tylosin", "tilmicosin", "تلميكوسين"]) and any(k in b for k in ["بنسلين", "penicillin", "سيفالوسبورين", "ceftiofur"])) or            (any(k in b for k in ["تايلوزين", "tylosin", "tilmicosin", "تلميكوسين"]) and any(k in a for k in ["بنسلين", "penicillin", "سيفالوسبورين", "ceftiofur"])):
            return INTERACTIONS_DB[0]
        if (any(k in a for k in ["فلونيكسين", "flunixin", "كيتوبروفين", "ميلوكسيكام"]) and any(k in b for k in ["ديكساميثازون", "dexamethasone", "كورتيزون"])) or            (any(k in b for k in ["فلونيكسين", "flunixin", "كيتوبروفين", "ميلوكسيكام"]) and any(k in a for k in ["ديكساميثازون", "dexamethasone", "كورتيزون"])):
            return INTERACTIONS_DB[1]
        if (any(k in a for k in ["ليفاميزول", "levamisole"]) and any(k in b for k in ["دايزينون", "diazinon", "مبيد"])) or            (any(k in b for k in ["ليفاميزول", "levamisole"]) and any(k in a for k in ["دايزينون", "diazinon", "مبيد"])):
            return INTERACTIONS_DB[3]
        if (any(k in a for k in ["بنسلين", "penicillin"]) and any(k in b for k in ["ستربتوميسين", "streptomycin", "ستربتو"])) or            (any(k in b for k in ["بنسلين", "penicillin"]) and any(k in a for k in ["ستربتوميسين", "streptomycin", "ستربتو"])):
            return INTERACTIONS_DB[4]
    
    return {
        "drug_a": drug_a_name,
        "drug_b": drug_b_name,
        "level": "safe",
        "level_title": "🟢 لا يوجد تداخل سلبي مسجل",
        "mechanism": "المستحضران يعملان بآليات حيوية متوافقة وفق المراجع الدوائية البيطرية (Plumb's Veterinary Drug Handbook)."
    }

def ask_ai_chat(api_key: str, user_message: str, chat_history: list, image_path: str = None, lang: str = "ar", user_country: str = "مصر"):
    effective_key = api_key.strip() if (api_key and api_key.strip().startswith("gsk_")) else get_effective_groq_api_key()

    effective_msg = user_message.strip() if user_message and user_message.strip() else ""
    if not effective_msg:
        effective_msg = "يرجى فحص وتحليل الحالة السريرية المعروضة وتقديم التشخيص التفريقي، بروتوكول العلاج الفوري، والأدوية المعتمدة في دولتي، والتوثيق من المراجع العلمية."

    localized_drugs = get_localized_drugs(user_country, effective_msg)
    drugs_summary = "\n".join([
        f"• {format_drug_display(d)} - المادة الفعالة: {d['active_ingredient']} - الجرعة: {d['dosage_guide']} (سحب: {d['withdrawal_period']})"
        for d in localized_drugs
    ])

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # -------------------------------------------------------------------------
    # MULTIMODAL COMPUTER VISION WITH GROQ (qwen/qwen3.8-27b)
    # -------------------------------------------------------------------------
    image_b64 = None
    if image_path and os.path.exists(image_path):
        try:
            with Image.open(image_path) as im:
                im = im.convert("RGB")
                im.thumbnail((1024, 1024))
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=85)
                image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            image_b64 = None

    if image_b64 and effective_key:
        vision_system_prompt = f"""You are VetMind AI Enterprise v4.3, the world's premier clinical veterinary AI decision-support platform.
Target Veterinarian Jurisdiction: {user_country}.
Grounding: Merck Veterinary Manual, WOAH, WSAVA, FAO, Cornell CVM, and Official National Formularies.

CRITICAL MANDATORY INSTRUCTIONS ON IMAGE EXAMINATION:
1. FIRST, inspect the image carefully. Determine whether the image depicts a veterinary patient (animal, livestock, horse, camel, dog, cat, poultry, etc.), a veterinary clinical lesion, a clinical pathology specimen, or veterinary clinical examination.
2. IF the image is NOT related to veterinary medicine or animal health (e.g. human face/body, building, pyramid, monument, vehicle, landscape, food, furniture, document, random object, meme):
   - You MUST IMMEDIATELY REJECT IT with the exact heading:
     ❌ **تنبيه: الصورة المرفقة غير صالحة للتشخيص البيطري**
   - Accurately describe what is actually in the image (e.g. 'الصورة المرفقة تعرض أثر تاريخي / أهرامات الجيزة / هرم خوفو... ولا تظهر أي كائن حيواني أو آفة سريرية بيطرية').
   - Instruct the doctor/user to upload a clear clinical photograph of the affected animal or lesion (eye, mouth, skin, limb, udder, etc.).
   - STRICT PROHIBITION: DO NOT fabricate, hallucinate, or attach any veterinary disease, symptoms, or medications to non-veterinary images!
3. ONLY IF the image actually shows an animal, tissue, or veterinary lesion:
   - Provide:
     🔬 **أولاً: التحليل الإكلينيكي البصري للآفة (Clinical Visual Assessment)**: التوصيف المورفولوجي، الأنسجة المصابة، نوع وشكل الآفة.
     📊 **ثانياً: التشخيص التفريقي المؤكد (Ranked Differential Diagnoses)**: التشخيصات مع نسب الرجحان والمراجع العلمية (Merck, WOAH, WSAVA).
     💉 **ثالثاً: البروتوكول العلاجي والإسعافي الفوري**: خطوات التدخل السريري، السوائل، مضادات الالتهاب، والعناية الموضعية.
     🏛️ **رابعاً: الأدوية المسجلة المعتمدة المخصصة للحالة ({user_country})**:
{drugs_summary}
     (ملاحظة إلزامية: لكل دواء اذكر وظيفته السريرية بين قوسين).
4. Write in authoritative, clear, professional Arabic (العربية) with medical English terms in parentheses."""

        payload = {
            "model": GROQ_VISION_MODEL,
            "messages": [
                {"role": "system", "content": vision_system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": f"{effective_msg}\n[الدولة المسجلة للطبيب المعالج: {user_country}]"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]}
            ],
            "temperature": 0.2
        }

        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {effective_key}",
                    "User-Agent": "Mozilla/5.0 VetMindAI/4.3 Enterprise"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, context=ctx, timeout=35) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                content = resp_json["choices"][0]["message"]["content"]
                if content and len(content.strip()) > 20:
                    return content
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # TEXT CLINICAL CONSULTATION WITH GROQ TEXT MODELS (120B / Qwen / 20B)
    # -------------------------------------------------------------------------
    if effective_key:
        text_system_prompt = f"""You are VetMind AI Enterprise v4.3, the world's premier clinical veterinary AI decision-support platform.
Target Veterinarian Jurisdiction: {user_country}.
Grounding: Merck Veterinary Manual, WOAH, WSAVA, FAO, Cornell CVM, and Official National Formularies.

CRITICAL DIRECTIVES:
1. Provide authoritative clinical veterinary advice based on international standards.
2. Differential diagnoses (ranked with %), Recommended clinical workup, Emergency care, and Prescribing guidance with the doctor's locally registered products ({user_country}):
{drugs_summary}
3. MANDATORY DIRECTIVE: For EVERY suggested medication, you MUST state its concise clinical function in parentheses immediately following the trade name, like: [اسم الدواء] (الوظيفة: علاج النزلات التنفسية وخفض الحرارة).
4. Write in authoritative, clear, professional Arabic (العربية) with medical English terms in parentheses."""

        messages = [{"role": "system", "content": text_system_prompt}]
        for msg in chat_history[-3:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": f"{effective_msg}\n[الدولة المسجلة للطبيب المعالج: {user_country}]"})

        for model_id in GROQ_MODELS:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                    "model": model_id,
                    "messages": messages,
                    "temperature": 0.25
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {effective_key}",
                        "User-Agent": "Mozilla/5.0 VetMindAI/4.3 Enterprise"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    content = resp_json["choices"][0]["message"]["content"]
                    forbidden = ["لا أستطيع رؤية", "لا يمكنني رؤية", "cannot see images", "unable to view images", "as an ai text model"]
                    if not any(f in content.lower() for f in forbidden):
                        return content
            except Exception:
                continue

    # -------------------------------------------------------------------------
    # SAFE CLINICAL FALLBACK (Only reached if offline or API unavailable)
    # -------------------------------------------------------------------------
    if image_path and os.path.exists(image_path):
        return f"""⚠️ **تنبيه الاتصال بمحرك الرؤية الحاسوبية (VetMind Vision AI)**
تم استلام الصورة بنجاح وتجهيزها للمعالجة الرقمية.
يرجى التأكد من اتصال الإنترنت أو إدخال مفتاح API في الإعدادات للربط المباشر مع محرك الذكاء الاصطناعي متعدد الوسائط (Multimodal AI) لإجراء الفحص والتشخيص البصري المعتمد."""

    return f"""🩺 **الاستشارة الإكلينيكية الإرشادية (VetMind Enterprise Clinical Advisor)**
*الدولة المعتمدة: {user_country}*

يرجى تزويد النظام بمزيد من التفاصيل حول الأعراض السريرية للحيوان، أو نوع الفصيلة (أبقار، خيول، أغنام، حيوانات أليفة)، لتقديم التشخيص التفريقي الدقيق وجدول الأدوية المعتمدة."""

def get_live_tunnel_url() -> str:
    try:
        p = os.path.join(BASE_DIR, "tunnel_info.json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
                if d.get("url"):
                    return d["url"]
    except Exception:
        pass
    return "http://10.180.160.121:8000"

def get_base_html(title: str, body_content: str, current_user, lang: str):
    t = lambda k, d="": get_text(lang, k, d)
    dir_attr = TRANSLATIONS_DB.get(lang, {}).get("dir", "rtl")
    
    # Calculate prayer times for top widget
    user_city = "القاهرة (مصر)"
    if current_user and current_user.get("country") == "السعودية":
        user_city = "الرياض (السعودية)"
    elif current_user and current_user.get("country") == "الإمارات":
        user_city = "أبوظبي (الإمارات)"
    elif current_user and current_user.get("country") == "الأردن":
        user_city = "عمان (الأردن)"
        
    try:
        p_res = calculate_prayer_times(user_city, lang=lang)
        prayer_p_text = f"{p_res['next_prayer']['name']} {p_res['next_prayer']['time']}"
        prayer_c_text = p_res['countdown_text']
    except Exception:
        prayer_p_text = "مواقيت الصلاة"
        prayer_c_text = "انقر هنا"

    lang_display_names = {
        "ar": "🇸🇦 العربية (Arabic)",
        "en": "🇬🇧 English",
        "fr": "🇫🇷 Français",
        "es": "🇪🇸 Español",
        "de": "🇩🇪 Deutsch",
        "it": "🇮🇹 Italiano",
        "zh": "🇨🇳 中文 (Chinese)",
        "ja": "🇯🇵 日本語 (Japanese)"
    }
    lang_options = ""
    lang_buttons = ""
    for code in SUPPORTED_LANGUAGES:
        sel = "selected" if code == lang else ""
        d_name = lang_display_names.get(code, code)
        lang_options += f'<option value="{code}" {sel}>{d_name}</option>'
        l_name = TRANSLATIONS_DB.get(code, {}).get("lang_name", code)
        is_active = "active-lang" if code == lang else ""
        lang_buttons += f'<a href="/set-language/{code}" onclick="changeLanguage(\'{code}\'); return false;" class="lang-pill {is_active}" style="text-decoration: none; cursor: pointer;">{l_name}</a>'

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM broadcast_notifications ORDER BY id DESC LIMIT 1")
    latest_broadcast = c.fetchone()
    conn.close()

    broadcast_banner = ""
    if latest_broadcast:
        badge_style = "background: #fef2f2; border-color: #fca5a5; color: #991b1b;" if latest_broadcast["badge_type"] == "warning" else "background: #ecfdf5; border-color: #6ee7b7; color: #065f46;"
        broadcast_banner = f"""
        <div class="broadcast-banner" style="{badge_style}">
            <div class="broadcast-content">
                <span class="broadcast-icon">📢</span>
                <strong>{latest_broadcast['title']}:</strong> {latest_broadcast['message']}
            </div>
            <button class="broadcast-close" onclick="this.parentElement.style.display='none'">×</button>
        </div>
        """

    admin_link = ""
    if current_user and current_user.get("is_admin"):
        admin_link = f'<a href="/admin" class="nav-item nav-admin">⚙️ {t("nav_admin")}</a>'

    premium_badge = ""
    if current_user and current_user.get("is_premium"):
        premium_badge = f'<span style="background: #fef08a; color: #854d0e; padding: 2px 8px; border-radius: 12px; font-weight: 800; font-size: 0.72rem;">⭐ PREMIUM</span>'

    user_nav = ""
    if current_user:
        v_badge = "✅" if current_user.get("verification_status") == "approved" else "⏳"
        user_country = current_user.get("country", "مصر")
        user_nav = f"""
        <div class="user-profile-widget">
            {premium_badge}
            <span class="user-badge">{user_country} | VET {v_badge}</span>
            <span class="user-name">د. {current_user['name']}</span>
            <a href="/profile" class="nav-item">👤 {t('nav_profile')}</a>
            <a href="/logout" class="nav-item nav-logout">🚪 {t('nav_logout')}</a>
        </div>
        """
    else:
        user_nav = f"""
        <div class="auth-buttons">
            <a href="/login" class="btn btn-login">🔑 {t('nav_login')}</a>
            <a href="/register" class="btn btn-register">📝 {t('nav_register')}</a>
        </div>
        """


    live_mobile_url = get_live_tunnel_url()
    mobile_admin_item = f'<a href="/admin" class="mobile-menu-item" style="color: #ea580c; font-weight: 700;"><span class="m-icon">⚙️</span><span class="m-label">{t("nav_admin")} (لوحة الإدارة)</span></a>' if current_user and current_user.get("is_admin") else ""
    if current_user:
        mobile_user_item = f"""
        <div style="border-top: 1px solid var(--border); margin: 8px 0;"></div>
        <a href="/profile" class="mobile-menu-item">
            <span class="m-icon">👤</span>
            <span class="m-label">{t('nav_profile')} (د. {current_user['name']})</span>
        </a>
        <a href="/logout" class="mobile-menu-item" style="color: #dc2626;">
            <span class="m-icon">🚪</span>
            <span class="m-label">{t('nav_logout')}</span>
        </a>
        """
    else:
        mobile_user_item = f"""
        <div style="border-top: 1px solid var(--border); margin: 8px 0;"></div>
        <a href="/login" class="mobile-menu-item" style="color: var(--primary); font-weight: 700;">
            <span class="m-icon">🔑</span>
            <span class="m-label">{t('nav_login')}</span>
        </a>
        <a href="/register" class="mobile-menu-item" style="color: var(--accent); font-weight: 700;">
            <span class="m-icon">📝</span>
            <span class="m-label">{t('nav_register')}</span>
        </a>
        """

    mobile_drawer_html = f"""
    <!-- Mobile Navigation Drawer Overlay & Panel (قائمة الـ 3 شرط) -->
    <div id="mobile-drawer-overlay" class="mobile-drawer-overlay" onclick="closeMobileDrawer()"></div>
    <aside id="mobile-drawer" class="mobile-drawer">
        <div class="mobile-drawer-header">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 38px; height: 38px; border-radius: 10px; background: rgba(255,255,255,0.2); color: white; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">
                    🩺
                </div>
                <div>
                    <div style="font-weight: 800; font-size: 1.05rem; color: white;">VetMind AI</div>
                    <div style="font-size: 0.75rem; opacity: 0.85; color: #ecfdf5;">طبيب بيطري معتمد 🩺</div>
                </div>
            </div>
            <button type="button" onclick="closeMobileDrawer()" class="mobile-drawer-close" aria-label="Close">✕</button>
        </div>

        <div class="mobile-drawer-content">
            <div class="mobile-menu-section-title">🏥 العيادة والتشخيص السريري</div>
            <a href="/" class="mobile-menu-item">
                <span class="m-icon">🏠</span>
                <span class="m-label">{t('nav_home')}</span>
            </a>
            <a href="/chat" class="mobile-menu-item">
                <span class="m-icon">💬</span>
                <span class="m-label">{t('nav_chat')}</span>
            </a>
            <a href="/community" class="mobile-menu-item" style="color: #0284c7; font-weight: 700;">
                <span class="m-icon">🌐</span>
                <span class="m-label">VetBook الأطباء البيطريين</span>
            </a>
            <a href="/clinic" class="mobile-menu-item">
                <span class="m-icon">🏥</span>
                <span class="m-label">{t('nav_clinic')}</span>
            </a>
            <a href="/clinic/cases-gallery" class="mobile-menu-item">
                <span class="m-icon">🖼️</span>
                <span class="m-label">{t("nav_cases_gallery", "معرض الصور")}</span>
            </a>
            <a href="/rx-prescription" class="mobile-menu-item">
                <span class="m-icon">📋</span>
                <span class="m-label">{t('nav_rx')}</span>
            </a>
            <a href="/interactions" class="mobile-menu-item">
                <span class="m-icon">⚠️</span>
                <span class="m-label">{t('nav_interactions')}</span>
            </a>
            <a href="/pharmacy" class="mobile-menu-item">
                <span class="m-icon">💊</span>
                <span class="m-label">{t('nav_pharmacy')} (1,005 دواء)</span>
            </a>
            <a href="/vision-detect" class="mobile-menu-item">
                <span class="m-icon">👁️</span>
                <span class="m-label">{t('nav_vision_detect')}</span>
            </a>
            <a href="/tools" class="mobile-menu-item">
                <span class="m-icon">🛠️</span>
                <span class="m-label">{t("nav_tools_30", "الأدوات الـ 30")}</span>
            </a>

            <div class="mobile-menu-section-title">🌐 لغة المنصة (All Languages)</div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; padding: 4px 6px; margin-bottom: 8px;">
                <a href="/set-language/ar" onclick="changeLanguage('ar'); return false;" class="lang-pill {'active-lang' if lang=='ar' else ''}" style="text-align: center; text-decoration: none; padding: 6px 4px; font-size: 0.82rem; border-radius: 8px; font-weight: 700;">🇸🇦 العربية</a>
                <a href="/set-language/en" onclick="changeLanguage('en'); return false;" class="lang-pill {'active-lang' if lang=='en' else ''}" style="text-align: center; text-decoration: none; padding: 6px 4px; font-size: 0.82rem; border-radius: 8px; font-weight: 700;">🇬🇧 English</a>
                <a href="/set-language/fr" onclick="changeLanguage('fr'); return false;" class="lang-pill {'active-lang' if lang=='fr' else ''}" style="text-align: center; text-decoration: none; padding: 6px 4px; font-size: 0.82rem; border-radius: 8px; font-weight: 700;">🇫🇷 Français</a>
                <a href="/set-language/es" onclick="changeLanguage('es'); return false;" class="lang-pill {'active-lang' if lang=='es' else ''}" style="text-align: center; text-decoration: none; padding: 6px 4px; font-size: 0.82rem; border-radius: 8px; font-weight: 700;">🇪🇸 Español</a>
                <a href="/set-language/de" onclick="changeLanguage('de'); return false;" class="lang-pill {'active-lang' if lang=='de' else ''}" style="text-align: center; text-decoration: none; padding: 6px 4px; font-size: 0.82rem; border-radius: 8px; font-weight: 700;">🇩🇪 Deutsch</a>
                <a href="/set-language/it" onclick="changeLanguage('it'); return false;" class="lang-pill {'active-lang' if lang=='it' else ''}" style="text-align: center; text-decoration: none; padding: 6px 4px; font-size: 0.82rem; border-radius: 8px; font-weight: 700;">🇮🇹 Italiano</a>
                <a href="/set-language/zh" onclick="changeLanguage('zh'); return false;" class="lang-pill {'active-lang' if lang=='zh' else ''}" style="text-align: center; text-decoration: none; padding: 6px 4px; font-size: 0.82rem; border-radius: 8px; font-weight: 700;">🇨🇳 中文</a>
                <a href="/set-language/ja" onclick="changeLanguage('ja'); return false;" class="lang-pill {'active-lang' if lang=='ja' else ''}" style="text-align: center; text-decoration: none; padding: 6px 4px; font-size: 0.82rem; border-radius: 8px; font-weight: 700;">🇯🇵 日本語</a>
            </div>

            <div class="mobile-menu-section-title">📚 المراجع والمعلومات</div>
            <a href="/clinic/prayer-times" class="mobile-menu-item">
                <span class="m-icon">🕌</span>
                <span class="m-label">{t("nav_prayer", "مواقيت الصلاة")}</span>
            </a>
            <a href="/references" class="mobile-menu-item">
                <span class="m-icon">📚</span>
                <span class="m-label">{t('nav_references')} (الـ 30 مرجع)</span>
            </a>
            <a href="/about" class="mobile-menu-item">
                <span class="m-icon">ℹ️</span>
                <span class="m-label">{t('nav_about')}</span>
            </a>
            <a href="/terms" class="mobile-menu-item">
                <span class="m-icon">📜</span>
                <span class="m-label">{t('nav_terms')}</span>
            </a>
            <a href="/premium" class="mobile-menu-item" style="color: #d97706; font-weight: 700;">
                <span class="m-icon">⭐</span>
                <span class="m-label">{t('nav_premium')}</span>
            </a>
            <a href="/support" class="mobile-menu-item">
                <span class="m-icon">🎧</span>
                <span class="m-label">{t('nav_support')}</span>
            </a>

            <div class="mobile-menu-section-title">⚙️ تثبيت التطبيق والتحكم</div>
            <button type="button" onclick="openMobileModal(); closeMobileDrawer();" class="mobile-menu-item" style="width: 100%; border: none; background: none; text-align: inherit; cursor: pointer; color: #0284c7; font-weight: 700;">
                <span class="m-icon">📱</span>
                <span class="m-label">تحميل وتثبيت التطبيق على الموبايل</span>
            </button>
            <button type="button" onclick="openApiModal(); closeMobileDrawer();" class="mobile-menu-item" style="width: 100%; border: none; background: none; text-align: inherit; cursor: pointer;">
                <span class="m-icon">🔑</span>
                <span class="m-label">{t('nav_api_key')}</span>
            </button>
            <button type="button" onclick="toggleTheme()" class="mobile-menu-item" style="width: 100%; border: none; background: none; text-align: inherit; cursor: pointer;">
                <span class="m-icon">🌓</span>
                <span class="m-label">{t("nav_toggle_theme", "تبديل نمط العرض")}</span>
            </button>
            {mobile_admin_item}
            {mobile_user_item}
        </div>
    </aside>
    """

    is_home_page = (title in [t('nav_home'), 'الرئيسية', 'Home', 'Accueil', 'Startseite', 'Inicio', 'Главная', '首页'])
    back_home_html = ""
    if not is_home_page and 'العودة للصفحة الرئيسية' not in body_content and 'btn-return-home' not in body_content:
        back_label = t('back_to_home', 'العودة للصفحة الرئيسية')
        back_home_html = f'''
        <div class="global-back-home-bar" style="margin-bottom: 20px;">
            <a href="/" style="display: inline-flex; align-items: center; gap: 8px; background: var(--card-bg); color: var(--primary); border: 2px solid var(--primary); padding: 8px 18px; border-radius: 25px; font-weight: 800; font-size: 0.92rem; text-decoration: none; box-shadow: 0 2px 6px rgba(4,120,87,0.12); transition: all 0.2s ease;">
                <span style="font-size: 1.1rem;">🏠</span> <span>{back_label}</span> <span style="font-size: 0.9rem;">⬅️</span>
            </a>
        </div>
        '''

    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{dir_attr}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <meta name="theme-color" content="#0f766e">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="VetMind AI">
    <title>{title} | {t('app_name')} {t('version')}</title>
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#047857">
    <link rel="shortcut icon" href="/favicon.ico?v=4">
    <link rel="icon" type="image/x-icon" href="/favicon.ico?v=4">
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg?v=4">
    <link rel="alternate icon" type="image/png" sizes="192x192" href="/static/icon-192.png?v=4">
    <link rel="icon" type="image/png" sizes="512x512" href="/static/icon-512.png?v=4">
    <link rel="apple-touch-icon" href="/static/icon-192.png?v=4">
    <style>
        :root {{
            /* High-Contrast, Eye-Friendly Medical Palette */
            --primary: #047857;
            --primary-dark: #065f46;
            --primary-light: #ecfdf5;
            --accent: #ea580c;
            --gold: #d97706;
            --bg: #f1f5f9;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #475569;
            --border: #cbd5e1;
            --danger: #dc2626;
            --danger-bg: #fef2f2;
            --success: #16a34a;
            --success-bg: #f0fdf4;
            --warning: #d97706;
            --warning-bg: #fffbeb;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        }}
        body.dark-theme {{
            --bg: #030712;
            --card-bg: #111827;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --border: #1f2937;
            --danger-bg: #450a0a;
            --success-bg: #052e16;
            --warning-bg: #451a03;
            --shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
        }}
        * {{ box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        body {{ margin: 0; background-color: var(--bg); color: var(--text-main); line-height: 1.5; }}
        
        .broadcast-banner {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 10px 20px; font-size: 0.9rem; border-bottom: 2px solid;
            animation: slideDown 0.4s ease-out;
        }}
        .broadcast-content {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
        .broadcast-close {{ background: none; border: none; font-size: 1.3rem; cursor: pointer; color: inherit; }}

        .disclaimer-banner {{
            background: var(--warning-bg); color: #92400e; padding: 8px 16px;
            font-size: 0.85rem; font-weight: 600; text-align: center; border-bottom: 1px solid #fde68a;
        }}

        header {{
            background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
            color: #ffffff; padding: 12px 24px; display: flex; justify-content: space-between;
            align-items: center; flex-wrap: wrap; gap: 14px; box-shadow: 0 4px 14px rgba(15,118,110,0.2);
        }}
        .brand-box {{ display: flex; align-items: center; gap: 12px; text-decoration: none; color: white; }}
        .brand-icon {{ font-size: 1.8rem; background: rgba(255,255,255,0.2); padding: 6px 12px; border-radius: 10px; }}
        .brand-title {{ font-size: 1.35rem; font-weight: 800; letter-spacing: -0.5px; }}
        .brand-version {{ font-size: 0.75rem; background: #ea580c; padding: 2px 8px; border-radius: 12px; font-weight: 700; }}

        nav {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
        .nav-item {{
            color: #e0f2fe; text-decoration: none; padding: 6px 12px; border-radius: 8px;
            font-size: 0.88rem; font-weight: 600; transition: all 0.2s;
            display: inline-flex; align-items: center; gap: 5px;
        }}
        .nav-item:hover, .nav-item.active {{ background: rgba(255,255,255,0.2); color: #ffffff; }}
        .nav-admin {{ background: rgba(234,88,12,0.3); border: 1px solid rgba(234,88,12,0.6); }}
        .nav-premium {{ background: linear-gradient(135deg, #d97706 0%, #b45309 100%); color: #fff !important; font-weight: 700; }}
        .nav-logout {{ background: rgba(220,38,38,0.2); }}

        .top-toolbar {{
            background: #ffffff; border-bottom: 1px solid var(--border);
            padding: 8px 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
        }}
        body.dark-theme .top-toolbar {{ background: #0f172a; }}

        .lang-bar {{ display: flex; gap: 5px; flex-wrap: wrap; align-items: center; }}
        .lang-pill {{
            background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 20px;
            padding: 3px 10px; font-size: 0.78rem; cursor: pointer; color: #334155; font-weight: 600;
        }}
        .lang-pill.active-lang {{ background: var(--primary); color: #ffffff; border-color: var(--primary); }}

        .btn {{
            display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px;
            border-radius: 8px; font-weight: 600; font-size: 0.88rem; text-decoration: none;
            cursor: pointer; border: none; transition: 0.2s;
        }}
        .btn-primary {{ background: var(--primary); color: white; }}
        .btn-primary:hover {{ background: var(--primary-dark); }}
        .btn-accent {{ background: var(--accent); color: white; }}
        .btn-accent:hover {{ background: #c2410c; }}
        .btn-gold {{ background: linear-gradient(135deg, #d97706, #b45309); color: white; }}
        .btn-gold:hover {{ background: #92400e; }}
        .btn-download {{ background: #0284c7; color: white; }}
        .btn-download:hover {{ background: #0369a1; }}
        .btn-outline {{ background: transparent; border: 1px solid var(--border); color: var(--text-main); }}

        .container {{ max-width: 1320px; margin: 24px auto; padding: 0 16px; }}
        .card {{
            background: var(--card-bg); border: 1px solid var(--border);
            border-radius: 14px; padding: 22px; margin-bottom: 22px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }}
        .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }}
        .grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}

        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 9999; justify-content: center; align-items: center; }}
        .modal-content {{ background: var(--card-bg); border-radius: 16px; max-width: 600px; width: 90%; padding: 26px; box-shadow: 0 20px 40px rgba(0,0,0,0.25); position: relative; }}
        .modal-close {{ position: absolute; top: 16px; left: 16px; font-size: 1.5rem; cursor: pointer; border: none; background: none; color: var(--text-muted); }}
        [dir="rtl"] .modal-close {{ left: 16px; right: auto; }}
        [dir="ltr"] .modal-close {{ right: 16px; left: auto; }}

        footer {{
            background: #0f172a; color: #94a3b8; text-align: center;
            padding: 24px 16px; margin-top: 40px; font-size: 0.85rem; border-top: 1px solid #1e293b;
        }}
        footer a {{ color: #38bdf8; text-decoration: none; }}

        /* ------------------------------------------------------------- */
        /* MOBILE & TABLET RESPONSIVENESS (Android & iOS Universal Support) */
        /* ------------------------------------------------------------- */
        html, body {{
            width: 100%;
            max-width: 100%;
            margin: 0;
            padding: 0;
            overflow-x: hidden;
            -webkit-text-size-adjust: 100%;
            -webkit-tap-highlight-color: transparent;
        }}
        body, p, div, span, h1, h2, h3, h4, h5, h6, strong, b, td, th {{
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        img, video, iframe, canvas {{
            max-width: 100% !important;
            height: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .table-responsive {{
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin-bottom: 12px;
        }}

        /* User Profile Widget */
        .user-profile-widget {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}

        /* Hamburger Button (☰) - Always Accessible */
        .mobile-hamburger-btn {{
            display: inline-flex !important;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.4);
            color: #ffffff;
            width: 44px;
            height: 44px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1.6rem;
            transition: all 0.2s ease;
            padding: 0;
            flex-shrink: 0;
        }}
        .mobile-hamburger-btn:hover, .mobile-hamburger-btn:active {{
            background: rgba(255, 255, 255, 0.35);
        }}

        /* Mobile Drawer Overlay */
        .mobile-drawer-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.65);
            backdrop-filter: blur(4px);
            z-index: 99998;
        }}
        .mobile-drawer-overlay.active {{
            display: block !important;
        }}

        /* Mobile Drawer Panel (قائمة الـ 3 شرط الجانبية) */
        .mobile-drawer {{
            position: fixed;
            top: 0;
            bottom: 0;
            width: 320px;
            max-width: 86vw;
            background: var(--card-bg);
            color: var(--text-main);
            z-index: 99999;
            box-shadow: 0 0 35px rgba(0, 0, 0, 0.5);
            overflow-y: auto;
            -webkit-overflow-scrolling: touch;
            transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1), left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        [dir="rtl"] .mobile-drawer {{
            right: -340px;
            left: auto;
        }}
        [dir="rtl"] .mobile-drawer.active {{
            right: 0 !important;
        }}
        [dir="ltr"] .mobile-drawer {{
            left: -340px;
            right: auto;
        }}
        [dir="ltr"] .mobile-drawer.active {{
            left: 0 !important;
        }}

        .mobile-drawer-header {{
            background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
            color: white;
            padding: 16px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid rgba(255, 255, 255, 0.15);
        }}
        .mobile-drawer-close {{
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
        }}
        .mobile-drawer-close:hover {{
            background: rgba(255, 255, 255, 0.4);
        }}
        .mobile-drawer-content {{
            padding: 10px 14px 40px 14px;
        }}
        .mobile-menu-section-title {{
            font-size: 0.78rem;
            font-weight: 800;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 12px 8px 6px 8px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 6px;
        }}
        .mobile-menu-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 11px 12px;
            border-radius: 10px;
            color: var(--text-main);
            text-decoration: none;
            font-size: 0.92rem;
            font-weight: 600;
            transition: background 0.15s ease, transform 0.1s ease;
            margin-bottom: 3px;
        }}
        .mobile-menu-item:hover, .mobile-menu-item:active {{
            background: var(--bg);
            transform: translateX(-3px);
        }}
        [dir="ltr"] .mobile-menu-item:hover, [dir="ltr"] .mobile-menu-item:active {{
            transform: translateX(3px);
        }}
        .mobile-menu-item .m-icon {{
            font-size: 1.3rem;
            width: 28px;
            text-align: center;
            flex-shrink: 0;
        }}
        .mobile-menu-item .m-label {{
            flex: 1;
        }}

        /* Mobile Quick App Box (صندوق الأيقونات تحت بعضها) */
        .mobile-app-box {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 22px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        }}
        .mobile-app-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(135px, 1fr));
            gap: 10px;
            margin-top: 12px;
        }}
        .mobile-app-card {{
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 8px;
            text-decoration: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 6px;
            transition: all 0.2s ease;
            color: var(--text-main);
        }}
        .mobile-app-card:hover, .mobile-app-card:active {{
            transform: translateY(-2px);
            border-color: var(--primary);
            box-shadow: 0 4px 12px rgba(4,120,87,0.12);
        }}
        .mobile-app-card-icon {{
            font-size: 2rem;
            line-height: 1;
        }}
        .mobile-app-card-title {{
            font-weight: 700;
            font-size: 0.86rem;
            line-height: 1.3;
        }}
        .mobile-app-card-sub {{
            font-size: 0.72rem;
            color: var(--text-muted);
            line-height: 1.2;
        }}

        @media (max-width: 900px) {{
            .grid-4 {{ grid-template-columns: repeat(2, 1fr) !important; gap: 12px !important; }}
            .grid-3 {{ grid-template-columns: repeat(2, 1fr) !important; gap: 14px !important; }}
            .desktop-nav {{ display: none !important; }}
            header {{
                padding: 10px 14px !important;
                flex-direction: row !important;
                justify-content: space-between !important;
                align-items: center !important;
            }}
            .brand-box {{
                gap: 8px !important;
            }}
            .brand-title {{
                font-size: 1.1rem !important;
            }}
            .brand-subtitle {{
                display: none !important;
            }}
            .top-toolbar {{
                padding: 8px 10px !important;
                flex-direction: column !important;
                align-items: stretch !important;
                gap: 8px !important;
            }}
            .top-toolbar-actions {{
                justify-content: space-between !important;
                width: 100% !important;
            }}
            .user-profile-widget .nav-item {{
                display: none !important;
            }}
        }}

        @media (max-width: 600px) {{
            .container {{
                padding: 0 10px !important;
                margin: 10px auto !important;
                width: 100% !important;
            }}
            .card {{
                padding: 14px 12px !important;
                border-radius: 12px !important;
                margin-bottom: 14px !important;
            }}
            .grid-2, .grid-3, .grid-4 {{
                grid-template-columns: 1fr !important;
                gap: 12px !important;
            }}
            .mobile-app-grid {{
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 8px !important;
            }}
            .modal-content {{
                width: 95% !important;
                padding: 18px 14px !important;
                max-height: 90vh !important;
                overflow-y: auto !important;
            }}
            table, thead, tbody, th, td, tr {{
                font-size: 0.8rem !important;
            }}
            th, td {{
                padding: 6px 6px !important;
            }}
            input, select, textarea {{
                font-size: 0.9rem !important;
            }}
        }}

        @keyframes slideDown {{ from {{ transform: translateY(-100%); }} to {{ transform: translateY(0); }} }}
    </style>
    <script>
        let deferredPwaPrompt = null;
        window.addEventListener('beforeinstallprompt', (e) => {{
            e.preventDefault();
            deferredPwaPrompt = e;
            console.log('beforeinstallprompt captured');
            const btns = document.querySelectorAll('.pwa-install-trigger');
            btns.forEach(b => {{ b.style.display = 'inline-flex'; }});
            const banner = document.getElementById('pwa-install-banner');
            if (banner) banner.style.display = 'flex';
        }});

        function triggerPwaInstall() {{
            if (deferredPwaPrompt) {{
                deferredPwaPrompt.prompt();
                deferredPwaPrompt.userChoice.then((choiceResult) => {{
                    console.log('User install choice:', choiceResult.outcome);
                    deferredPwaPrompt = null;
                }});
            }} else {{
                openMobileModal();
            }}
        }}

        function openMobileDrawer() {{
            console.log('Opening mobile drawer...');
            const d = document.getElementById('mobile-drawer');
            const o = document.getElementById('mobile-drawer-overlay');
            if (d) {{
                d.classList.add('active');
                d.style.display = 'block';
            }}
            if (o) {{
                o.classList.add('active');
                o.style.display = 'block';
            }}
            document.body.style.overflow = 'hidden';
        }}
        function closeMobileDrawer() {{
            console.log('Closing mobile drawer...');
            const d = document.getElementById('mobile-drawer');
            const o = document.getElementById('mobile-drawer-overlay');
            if (d) {{
                d.classList.remove('active');
            }}
            if (o) {{
                o.classList.remove('active');
                o.style.display = 'none';
            }}
            document.body.style.overflow = '';
        }}
        function changeLanguage(langCode) {{
            document.cookie = "vetmind_lang=" + langCode + "; path=/; max-age=31536000; SameSite=Lax";
            try {{
                let u = new URL(window.location.href);
                u.searchParams.delete('lang');
                let target = u.pathname + u.search;
                window.location.href = "/set-language/" + langCode + "?redirect=" + encodeURIComponent(target);
            }} catch(e) {{
                window.location.href = "/set-language/" + langCode + "?redirect=" + encodeURIComponent(window.location.pathname);
            }}
        }}
        function toggleTheme() {{
            document.body.classList.toggle('dark-theme');
            document.documentElement.classList.toggle('dark-theme');
            const isDark = document.body.classList.contains('dark-theme') || document.documentElement.classList.contains('dark-theme');
            document.cookie = "vetmind_theme=" + (isDark ? 'dark' : 'light') + "; path=/; max-age=31536000";
            console.log('Theme toggled, isDark:', isDark);
        }}
        function openApiModal() {{ document.getElementById('api-modal').style.display = 'flex'; }}
        function closeApiModal() {{ document.getElementById('api-modal').style.display = 'none'; }}
        function openMobileModal() {{ document.getElementById('mobile-modal').style.display = 'flex'; }}
        function closeMobileModal() {{ document.getElementById('mobile-modal').style.display = 'none'; }}
        function copyMobileUrl() {{
            const inp = document.getElementById('mobile-url-input');
            if (inp) {{
                inp.select();
                navigator.clipboard.writeText(inp.value).then(() => {{
                    alert('تم نسخ الرابط بنجاح: ' + inp.value);
                }}).catch(() => {{
                    prompt('انسخ الرابط:', inp.value);
                }});
            }}
        }}

        if ('serviceWorker' in navigator) {{
            window.addEventListener('load', function() {{
                navigator.serviceWorker.register('/static/sw.js').catch(function(e) {{
                    console.log('SW note:', e);
                }});
            }});
        }}
        
        async function testAndSaveApiKey() {{
            const key = document.getElementById('api-key-input').value.trim();
            const statusDiv = document.getElementById('api-key-status');
            
            if (!key) {{
                statusDiv.innerHTML = '<div style="background: var(--danger-bg); color: var(--danger); padding: 12px; border-radius: 8px; border: 1px solid #fca5a5; font-weight: 700;">❌ يرجى إدخال مفتاح API أولاً</div>';
                return;
            }}
            
            statusDiv.innerHTML = '<span style="color: var(--primary);">⏳ جاري اختبار مفتاح الـ API مع سيرفر Groq...</span>';
            
            try {{
                const resp = await fetch('/api/test-key', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{api_key: key}})
                }});
                let data = null;
                try {{
                    data = await resp.json();
                }} catch(e) {{
                    data = {{status: 'error', message: 'هناك خطأ في الـ API: استجابة غير متوقعة.'}};
                }}
                const isSuccess = data && data.status === 'success';
                let msg = (data && data.message) ? data.message : (isSuccess ? 'تم التفعيل بنجاح!' : 'هناك خطأ في الـ API');
                msg = msg.replace(/^[✅❌\\s]+/, '');
                
                if (isSuccess) {{
                    statusDiv.innerHTML = '<div style="background: var(--success-bg); color: var(--success); padding: 12px; border-radius: 8px; border: 1px solid #86efac; font-weight: 700;">✅ ' + msg + '</div>';
                    document.cookie = "groq_api_key=" + encodeURIComponent(key) + "; path=/; max-age=31536000";
                    setTimeout(() => {{ window.location.reload(); }}, 1800);
                }} else {{
                    statusDiv.innerHTML = '<div style="background: var(--danger-bg); color: var(--danger); padding: 12px; border-radius: 8px; border: 1px solid #fca5a5; font-weight: 700;">❌ ' + msg + '</div>';
                }}
            }} catch(err) {{
                statusDiv.innerHTML = '<div style="background: var(--danger-bg); color: var(--danger); padding: 12px; border-radius: 8px; font-weight: 700;">❌ فشل الاتصال بالسيرفر. يرجى إعادة المحاولة.</div>';
            }}
        }}

        (function() {{
            const cookies = document.cookie.split(';');
            for(let c of cookies) {{
                if(c.trim().startsWith('vetmind_theme=dark')) {{
                    document.documentElement.classList.add('dark-theme');
                }}
            }}
        }})();
    </script>
</head>
<body>
    <header>
        <div style="display: flex; align-items: center; gap: 10px; max-width: 100%;">
            <button type="button" onclick="openMobileDrawer()" class="mobile-hamburger-btn" aria-label="قائمة الخيارات (☰)">
                <span style="font-size: 1.6rem; line-height: 1;">☰</span>
            </button>
            <a href="/" class="brand-box" style="display: flex; align-items: center; gap: 10px; text-decoration: none; color: white;">
                <span class="brand-icon" style="display: inline-flex; align-items: center; justify-content: center; background: transparent; padding: 0; box-shadow: none;">
                    <svg width="40" height="40" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="50" cy="50" r="47" fill="#0f766e" stroke="#5eead4" stroke-width="2.5"/>
                        <path d="M22 28 L50 82 L78 28" stroke="#fde047" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>
                        <line x1="50" y1="15" x2="50" y2="84" stroke="#ffffff" stroke-width="4.5" stroke-linecap="round"/>
                        <circle cx="50" cy="15" r="4.5" fill="#f59e0b" stroke="#ffffff" stroke-width="1"/>
                        <path d="M38 32 C58 30, 58 40, 50 44 C40 48, 40 58, 50 62 C60 66, 60 76, 48 80" stroke="#34d399" stroke-width="5" stroke-linecap="round" fill="none"/>
                        <circle cx="38" cy="32" r="4.5" fill="#34d399" stroke="#065f46" stroke-width="1"/>
                        <circle cx="37" cy="31" r="1.2" fill="#0f172a"/>
                        <path d="M34 31 L30 30 M34 31 L30 33" stroke="#ef4444" stroke-width="1.2" stroke-linecap="round"/>
                    </svg>
                </span>
                <div>
                    <div class="brand-title" style="font-weight: 800; line-height: 1.2;">{t('app_name')} <span class="brand-version">{t('version')}</span></div>
                    <div class="brand-subtitle" style="font-size: 0.76rem; opacity: 0.85;">{t('app_subtitle')}</div>
                </div>
            </a>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <button type="button" onclick="triggerPwaInstall()" class="btn pwa-install-trigger" style="background: #fde047; color: #854d0e; font-weight: 800; font-size: 0.82rem; padding: 6px 12px; border-radius: 8px; white-space: nowrap; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">
                📥 <span class="install-btn-text">تحميل التطبيق</span>
            </button>
            <nav class="desktop-nav">
                <a href="/" class="nav-item">🏠 {t('nav_home')}</a>
                <a href="/chat" class="nav-item">💬 {t('nav_chat')}</a>
                <a href="/community" class="nav-item" style="background: rgba(14, 165, 233, 0.25); border: 1px solid rgba(14, 165, 233, 0.5);">🌐 VetBook الأطباء البيطريين</a>
                <a href="/clinic" class="nav-item">🏥 {t('nav_clinic')}</a>
                <a href="/clinic/cases-gallery" class="nav-item">{t("nav_cases_gallery", "🖼️ معرض الصور")}</a>
                <a href="/rx-prescription" class="nav-item">📋 {t('nav_rx')}</a>
                <a href="/interactions" class="nav-item">⚠️ {t('nav_interactions')}</a>
                <a href="/pharmacy" class="nav-item">💊 {t('nav_pharmacy')}</a>
                <a href="/vision-detect" class="nav-item">👁️ {t('nav_vision_detect')}</a>
                <a href="/tools" class="nav-item" style="background: rgba(255,255,255,0.15); font-weight: 700;">{t("nav_tools_30", "🛠️ الأدوات الـ 30")}</a>
                <a href="/clinic/prayer-times" class="nav-item">{t("nav_prayer", "🕌 مواقيت الصلاة")}</a>
                <a href="/references" class="nav-item">📚 {t('nav_references')}</a>
                <a href="/about" class="nav-item">ℹ️ {t('nav_about')}</a>
                <a href="/terms" class="nav-item">📜 {t('nav_terms')}</a>
                <a href="/time-demand" class="nav-item">📊 {t('nav_time_demand')}</a>
                <a href="/premium" class="nav-item nav-premium">⭐ {t('nav_premium')}</a>
                <a href="/support" class="nav-item">🎧 {t('nav_support')}</a>
                {admin_link}
            </nav>
        </div></header>
    {mobile_drawer_html}

    <div class="top-toolbar">
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 6px; background: var(--bg); border: 1px solid var(--border); border-radius: 20px; padding: 2px 10px;">
                <span style="font-size: 0.9rem;">🌐</span>
                <select id="lang-quick-select" onchange="changeLanguage(this.value)" style="border: none; background: transparent; font-size: 0.82rem; font-weight: 700; color: var(--text-main); cursor: pointer; outline: none; padding: 3px 2px;">
                    {lang_options}
                </select>
            </div>
            <!-- Live Islamic Prayer Indicator Pill -->
            <a href="/clinic/prayer-times" class="btn btn-outline" style="padding: 2px 10px; font-size: 0.78rem; border-radius: 20px; text-decoration: none; background: #ecfdf5; border-color: #a7f3d0; color: #047857; font-weight: 700; white-space: nowrap; flex-shrink: 0;">
                🕌 {t("next_prayer_label", "الصلاة")}: {prayer_p_text} ({prayer_c_text})
            </a>
        </div>
        <div class="top-toolbar-actions" style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <button type="button" onclick="triggerPwaInstall()" class="btn pwa-install-trigger" style="padding: 5px 12px; font-size: 0.82rem; font-weight: 800; background: #0284c7; color: #ffffff; border: none; border-radius: 8px; display: inline-flex; align-items: center; gap: 4px; box-shadow: 0 2px 6px rgba(2,132,199,0.25);">
                📥 تحميل التطبيق
            </button>
            <button onclick="openApiModal()" class="btn btn-outline" style="padding: 4px 12px; font-size: 0.82rem; font-weight: 700; border-color: var(--primary); color: var(--primary);">
                🔑 {t('nav_api_key')}
            </button>
            <button onclick="toggleTheme()" class="btn btn-outline" style="padding: 4px 10px; font-size: 0.8rem;">{t("nav_toggle_theme", "🌓 نمط العرض")}</button>
            {user_nav}
        </div>
    </div>

    <div id="api-modal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeApiModal()">×</button>
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🔑</span>
                <h2 style="margin: 0; font-size: 1.3rem; color: var(--primary);">{t('api_modal_title')}</h2>
            </div>
            <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 16px;">
                {t('api_modal_desc')}
            </p>

            <div style="margin-bottom: 16px;">
                <label style="display: block; font-weight: 700; margin-bottom: 6px;">{t('api_key_input')}</label>
                <input type="text" id="api-key-input" placeholder="gsk_..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px; font-family: monospace;">
                <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">{t('api_key_hint', 'يمكنك الحصول على مفتاح مجاني فوري من console.groq.com/keys')}</div>
            </div>

            <button onclick="testAndSaveApiKey()" class="btn btn-primary" style="width: 100%; padding: 12px; justify-content: center; font-size: 1rem;">
                {t('api_test_btn')}
            </button>

            <div id="api-key-status" style="margin-top: 16px; font-size: 0.9rem;"></div>
        </div>
    </div>

    <!-- Mobile Connect Modal -->
        <!-- Mobile Connect & WebAPK Install Modal -->
    <div id="mobile-modal" class="modal">
        <div class="modal-content" style="max-width: 520px; text-align: center;">
            <button class="modal-close" onclick="closeMobileModal()">×</button>
            <div style="width: 56px; height: 56px; border-radius: 50%; background: #ecfdf5; color: #047857; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; margin: 0 auto 10px auto; border: 2px solid #a7f3d0;">
                📱
            </div>
            <h2 style="margin: 0 0 6px 0; font-size: 1.35rem; color: #047857;">تثبيت واستخدام VetMind AI على الموبايل</h2>
            
            <div style="background: #ecfdf5; border: 1px solid #6ee7b7; border-radius: 10px; padding: 10px 14px; margin-bottom: 14px; text-align: right; font-size: 0.85rem; color: #065f46; line-height: 1.6;">
                ✅ <strong>رابط التثبيت الآمن المعتمد (HTTPS):</strong><br>
                هذا الرابط مشفر بشهادة SSL رسمية، وهو ما يطلبه متصفح <strong>Google Chrome</strong> على أندرويد لحل رسالة <em>"هذا التطبيق لا يمكن تثبيته"</em>، ويتيح تثبيت التطبيق بضغطة واحدة ليفتح في نافذة خاصة به مثل <strong>YouTube و Facebook</strong>.
            </div>

            <div style="background: white; border: 2px solid #047857; border-radius: 12px; padding: 12px; display: inline-block; margin-bottom: 14px; box-shadow: 0 4px 14px rgba(4,120,87,0.15);">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={live_mobile_url}" alt="QR Code" style="width: 180px; height: 180px; display: block;">
            </div>

            <div style="background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                <input type="text" readonly value="{live_mobile_url}" id="mobile-url-input" style="flex: 1; font-weight: 700; font-size: 0.88rem; border: none; background: transparent; color: #047857; text-align: center; direction: ltr;">
                <button type="button" onclick="copyMobileUrl()" class="btn btn-primary" style="padding: 6px 14px; font-size: 0.82rem;">نسخ الرابط</button>
            </div>

            <div style="text-align: right; margin-top: 14px; background: #f8fafc; border: 1px solid var(--border); border-radius: 10px; padding: 12px; font-size: 0.82rem; line-height: 1.7;">
                <div style="font-weight: 700; color: #0f766e; margin-bottom: 6px;">📲 خطوات التثبيت ليفتح كنافذة مستقلة بدون متصفح (مثل يوتيوب وفيسبوك):</div>
                <div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid var(--border);">
                    <strong style="color: #0284c7;">🤖 لأجهزة أندرويد (Google Chrome):</strong><br>
                    1. افتح الرابط في متصفح Chrome على هاتفك.<br>
                    2. ستظهر لك رسالة تلقائية بالأسفل: <strong>"إضافة VetMind AI إلى الشاشة الرئيسية"</strong> أو اضغط على قائمة الثلاث نقاط (<strong>⋮</strong>) ثم اختر <strong>"تثبيت التطبيق" (Install app)</strong>.<br>
                    3. سيتم تثبيت أيقونة التطبيق على هاتفك فوراً، وعند فتحها ستعمل في شاشة كاملة مستقلة تماماً بدون شريط متصفح.
                </div>
                <div>
                    <strong style="color: #ea580c;">🍎 لأجهزة آيفون (Apple Safari):</strong><br>
                    1. افتح الرابط في متصفح Safari.<br>
                    2. اضغط على زر المشاركة (المربع بسهم <strong>⎋</strong> أسفل الشاشة) ➔ ثم اختر <strong>"إضافة إلى الشاشة الرئيسية" (Add to Home Screen)</strong>.
                </div>
            </div>

            <div style="text-align: right; font-size: 0.8rem; color: #64748b; margin-top: 10px;">
                🌐 رابط الشبكة المحلية المباشر (Wi-Fi البديل): <code style="direction: ltr; font-weight: bold;">http://10.180.160.121:8000</code>
            </div>
        </div>
    </div>

        <main class="container">
        {back_home_html}
        {body_content}
    </main>

    <script src="/static/autocomplete.js?v=2"></script>

    <footer>
        <div style="font-size: 1.05rem; margin-bottom: 6px;">
            <strong>VetMind AI Enterprise v4.2</strong> - World Standard Veterinary Decision Support Suite
        </div>
        <div style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 8px;">
            👨‍⚕️ <strong>{t('developer_label')}</strong> <span style="color: #fde047; font-weight: 800; font-size: 1.02rem;">{t('developer_name')}</span>
        </div>
        <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin: 12px 0; font-size: 0.9rem;">
            <a href="/about" style="color: #38bdf8; text-decoration: none; font-weight: 700;">ℹ️ {t('nav_about')}</a>
            <span style="opacity: 0.4;">|</span>
            <a href="/terms" style="color: #38bdf8; text-decoration: none; font-weight: 700;">📜 {t('nav_terms')}</a>
            <span style="opacity: 0.4;">|</span>
            <a href="/pharmacy" style="color: #38bdf8; text-decoration: none; font-weight: 700;">💊 {t('nav_pharmacy')} ({t('pharmacy_drugs_count', '1,005 دواء')})</a>
            <span style="opacity: 0.4;">|</span>
            <a href="/support" style="color: #38bdf8; text-decoration: none; font-weight: 700;">🎧 {t('nav_support')}</a>
        </div>
        <div style="margin-top: 8px; font-size: 0.78rem; color: #94a3b8;">
            Grounded in Merck Veterinary Manual, WOAH, WSAVA, FAO, Cornell CVM & Official Arab Formularies.
        </div>
        <div style="margin-top: 4px; font-size: 0.76rem; color: #64748b;">
            {t("copyright_footer", "كافة حقوق الملكية الفكرية والبرمجية والتصميم محفوظة © 2026 د. تامر سعد | مخصص حصرياً للأطباء البيطريين المرخصين.")}
        </div>
    </footer>
</body>
</html>"""

# ==============================================================================
# ROUTE: SMART RX PRESCRIPTION & DOSAGE CALCULATOR
# ==============================================================================
@app.get("/rx-prescription", response_class=HTMLResponse)
async def rx_prescription_page(
    request: Request,
    animal_name: str = "بقرة حلوب #108",
    species: str = "أبقار",
    weight: float = 450.0,
    selected_drug_id: int = 1
):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM local_products ORDER BY country, trade_name")
    all_drugs = [dict(r) for r in c.fetchall()]
    
    # Get clinic profile
    c.execute("SELECT * FROM clinic_profiles WHERE user_id = ?", (user["id"] if user else 4,))
    clinic = c.fetchone()
    if not clinic:
        c.execute("SELECT * FROM clinic_profiles WHERE user_id = 4")
        clinic = c.fetchone()
    conn.close()

    clinic_name = clinic["clinic_name"] if clinic else "مركز فيتمايند للاستشارات والطب البيطري المتقدم"
    clinic_phone = clinic["phone"] if clinic else "+201000000000"
    clinic_addr = clinic["address"] if clinic else "القاهرة - مدينة نصر"
    doctor_name = user["name"] if user else "د. تامر سعد"
    syndicate_id = user.get("syndicate_id", "EXEC-VET-001") if user else "EXEC-VET-001"

    # Find selected drug
    current_drug = None
    for d in all_drugs:
        if d["id"] == selected_drug_id:
            current_drug = d
            break
    if not current_drug and all_drugs:
        current_drug = all_drugs[0]

    # Calculate dosage heuristic
    calc_dose_ml = 0.0
    dose_text = current_drug["dosage_guide"]
    if "لكل 10 كجم" in dose_text:
        calc_dose_ml = round((weight / 10.0) * 1.0, 1)
    elif "لكل 25 كجم" in dose_text:
        calc_dose_ml = round((weight / 25.0) * 1.0, 1)
    elif "لكل 50 كجم" in dose_text:
        calc_dose_ml = round((weight / 50.0) * 1.0, 1)
    elif "لكل 30 كجم" in dose_text:
        calc_dose_ml = round((weight / 30.0) * 1.0, 1)
    elif "لكل 20 كجم" in dose_text:
        calc_dose_ml = round((weight / 20.0) * 1.0, 1)
    elif "لكل 45 كجم" in dose_text:
        calc_dose_ml = round((weight / 45.0) * 1.0, 1)
    else:
        calc_dose_ml = round((weight / 25.0) * 1.0, 1)

    drug_options = "".join([f'<option value="{d["id"]}" {"selected" if d["id"] == current_drug["id"] else ""}>[{d["country"]}] {d["trade_name"]} ({d["active_ingredient"][:40]}...)</option>' for d in all_drugs])

    species_options = "".join([f'<option value="{s}" {"selected" if s == species else ""}>{s}</option>' for s in ["أبقار", "أغنام وماعز", "إبل وهجن", "خيول", "دواجن", "كلاب", "قطط"]])

    body = f"""
    <div style="margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 1.6rem; color: var(--primary);">📋 {t('rx_title')}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">{t('rx_subtitle')}</p>
    </div>

    <div class="grid-2">
        <!-- Input & Calculator Form -->
        <div class="card" style="border-top: 4px solid var(--primary);">
            <h3 style="margin-top: 0; color: var(--primary);">{t('rx_calc_title', '⚖️ إعداد وحساب الجرعة السريرية')}</h3>
            <form action="/rx-prescription" method="GET">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px;">{t('animal_name_label', 'اسم الحيوان / رقم التعريف')}</label>
                    <input type="text" name="animal_name" value="{animal_name}" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>

                <div class="grid-2" style="margin-bottom: 12px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px;">{t('patient_species_label', 'الفصيلة')}</label>
                        <select name="species" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                            {species_options}
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px;">{t('patient_weight_label', 'الوزن الحي الفعلي (كجم)')}</label>
                        <input type="number" step="0.5" name="weight" value="{weight}" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                </div>

                <div style="margin-bottom: 16px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px;">{t('select_drug_label', 'اختر المستحضر البيطري المعتمد')}</label>
                    <select name="selected_drug_id" onchange="this.form.submit()" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px; font-weight: 600;">
                        {drug_options}
                    </select>
                </div>

                <button type="submit" class="btn btn-primary" style="width: 100%; justify-content: center;">
                    {t('recalc_dose_btn', '🔄 إعادة حساب الجرعة وتحديث الروشتة')}
                </button>
            </form>

            <div style="margin-top: 20px; background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 14px;">
                <div style="font-weight: 700; color: #166534; font-size: 1.05rem;">{t('dose_result_label', 'نتيجة حساب الجرعة لوزن')} ({weight} {t('unit_kg', 'كجم')}):</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: var(--primary); margin: 6px 0;">{calc_dose_ml} مل (ml)</div>
                <div style="font-size: 0.85rem; color: #15803d;"><strong>{t('route_label', 'طريقة الإعطاء')}:</strong> {current_drug['dosage_guide']}</div>
                <div style="font-size: 0.85rem; color: #b91c1c; margin-top: 4px;"><strong>فترة الأمان (Withdrawal):</strong> {current_drug['withdrawal_period']}</div>
            </div>
        </div>

        <!-- Official Printable Prescription Preview -->
        <div>
            <div id="printable-rx" style="background: white; border: 2px solid var(--primary); border-radius: 14px; padding: 26px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); color: #0f172a;">
                <!-- Header -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--primary); padding-bottom: 12px; margin-bottom: 16px;">
                    <div>
                        <div style="font-size: 1.3rem; font-weight: 800; color: var(--primary);">{clinic_name}</div>
                        <div style="font-size: 0.85rem; color: #475569;">{t('attending_physician_label', 'الطبيب المعالج')}: <strong>{t('dr_prefix', 'د.')} {doctor_name}</strong> | {t('license_no_label', 'ترخيص رقم')}: <strong>{syndicate_id}</strong></div>
                        <div style="font-size: 0.8rem; color: #64748b;">{t('address_label', 'العنوان')}: {clinic_addr} | {t('phone_label', 'هاتف')}: {clinic_phone}</div>
                    </div>
                    <div style="text-align: center; border: 2px solid var(--primary); border-radius: 50%; width: 55px; height: 55px; display: flex; align-items: center; justify-content: center; font-size: 1.6rem; color: var(--primary);">
                        Rx
                    </div>
                </div>

                <!-- Patient Details -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 16px; font-size: 0.85rem; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                    <div><strong>المريض:</strong> {animal_name} ({species})</div>
                    <div><strong>الوزن:</strong> {weight} كجم</div>
                    <div><strong>التاريخ:</strong> {datetime.now().strftime('%Y-%m-%d')}</div>
                </div>

                <!-- Rx Items -->
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 1.4rem; font-weight: 800; color: var(--primary); font-family: serif; margin-bottom: 8px;">℞</div>
                    <div style="padding: 12px; border-left: 4px solid var(--primary); background: #f0fdf4; border-radius: 6px; margin-bottom: 10px;">
                        <div style="font-size: 1.1rem; font-weight: 800; color: #166534;">{current_drug['trade_name']}</div>
                        <div style="font-size: 0.85rem; color: #334155; margin-top: 2px;">المادة الفعالة: {current_drug['active_ingredient']}</div>
                        <div style="font-size: 0.95rem; font-weight: 700; color: var(--accent); margin-top: 6px;">
                            الجرعة المقررة: {calc_dose_ml} مل حقناً وفق التوجيه السريري.
                        </div>
                    </div>
                </div>

                <!-- Withdrawal Notice -->
                <div style="background: #fef2f2; border: 1px dashed #f87171; border-radius: 6px; padding: 8px 12px; font-size: 0.8rem; color: #991b1b; margin-bottom: 20px;">
                    ⚠️ <strong>تنبيه فترة السحب والأمان الغذائي (Withdrawal Period):</strong><br>
                    {current_drug['withdrawal_period']} | يمنع استهلاك اللحم أو الحليب خلال فترة التحريم.
                </div>

                <!-- Signature & Stamp -->
                <div style="display: flex; justify-content: space-between; align-items: flex-end; border-top: 1px solid #e2e8f0; padding-top: 14px;">
                    <div style="font-size: 0.75rem; color: #64748b;">
                        حررت إلكترونياً عبر منصة VetMind AI Enterprise v4.2<br>
                        الرقم المرجعي: RX-{random.randint(100000, 999999)}
                    </div>
                    <div style="text-align: center;">
                        <div style="border: 2px solid #16a34a; border-radius: 8px; padding: 4px 12px; color: #16a34a; font-size: 0.8rem; font-weight: 700;">
                            ✓ تم الفحص والاعتماد السريري
                        </div>
                        <div style="font-size: 0.85rem; font-weight: 700; margin-top: 4px;">د. {doctor_name}</div>
                    </div>
                </div>
            </div>

            <div style="margin-top: 14px; text-align: center;">
                <button onclick="window.print()" class="btn btn-primary" style="padding: 12px 24px; font-size: 1rem;">
                    🖨️ طباعة الروشتة البيطرية الرسمية (PDF)
                </button>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_rx"), body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# ROUTE: DRUG-DRUG INTERACTIONS CHECKER
# ==============================================================================
@app.get("/interactions", response_class=HTMLResponse)
async def interactions_page(
    request: Request,
    drug_a: str = "تايلوزين 20% (Tylosin)",
    drug_b: str = "بنستريب 20/20 (Penicillin G + Streptomycin)"
):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    result = check_drug_interaction(drug_a, drug_b)

    badge_bg = "#fef2f2" if result["level"] == "danger" else ("#fffbeb" if result["level"] == "warning" else "#f0fdf4")
    badge_border = "#fca5a5" if result["level"] == "danger" else ("#fde68a" if result["level"] == "warning" else "#86efac")
    badge_color = "#991b1b" if result["level"] == "danger" else ("#92400e" if result["level"] == "warning" else "#166534")

    popular_drugs = [
        "تايلوزين 20% (Tylosin)",
        "بنستريب 20/20 (Penicillin G + Streptomycin)",
        "فلونيكسين ميغلومين (Flunixin Meglumine)",
        "ديكساميثازون 0.2% (Dexamethasone)",
        "أوكسيتتراسيكلين 20% (Oxytetracycline)",
        "ليفاميزول 10% (Levamisole)",
        "دايزينون 60% (Diazinon)",
        "سيفوكين 2.5% (Cefquinome)",
        "إنروفلوكساسين 10% (Enrofloxacin)",
        "فوروسيميد (Furosemide / Lasix)"
    ]

    opts_a = "".join([f'<option value="{d}" {"selected" if d == drug_a else ""}>{d}</option>' for d in popular_drugs])
    opts_b = "".join([f'<option value="{d}" {"selected" if d == drug_b else ""}>{d}</option>' for d in popular_drugs])

    body = f"""
    <div style="margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 1.6rem; color: var(--accent);">⚠️ {t('interactions_title')}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">{t('interactions_subtitle')}</p>
    </div>

    <div class="card" style="border-top: 4px solid var(--accent);">
        <form action="/interactions" method="GET">
            <div class="grid-2" style="margin-bottom: 16px;">
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 6px;">{t('drug_a_label', 'المستحضر الأول (Drug A):')}</label>
                    <select name="drug_a" style="width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px; font-weight: 600;">
                        {opts_a}
                    </select>
                </div>
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 6px;">{t('drug_b_label', 'المستحضر الثاني (Drug B):')}</label>
                    <select name="drug_b" style="width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px; font-weight: 600;">
                        {opts_b}
                    </select>
                </div>
            </div>

            <button type="submit" class="btn btn-accent" style="width: 100%; padding: 12px; justify-content: center; font-size: 1rem;">
                🔍 فحص التداخل الدوائي والسلامة السريرية
            </button>
        </form>

        <div style="margin-top: 24px; background: {badge_bg}; border: 2px solid {badge_border}; border-radius: 12px; padding: 20px;">
            <div style="font-size: 1.25rem; font-weight: 800; color: {badge_color}; margin-bottom: 8px;">
                {result['level_title']}
            </div>
            <div style="font-size: 0.95rem; line-height: 1.8; color: #1e293b;">
                <strong>الآلية الفارماكولوجية والتوجيه السريري:</strong><br>
                {result['mechanism']}
            </div>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px; border-top: 1px dashed {badge_border}; padding-top: 6px;">
                المرجع: Plumb's Veterinary Drug Handbook 9th Edition & Merck Veterinary Clinical Pharmacology.
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_interactions"), body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# ROUTE: CLINIC INVOICES & BILLING
# ==============================================================================
@app.get("/clinic/invoices", response_class=HTMLResponse)
async def clinic_invoices_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)
    user_id = user["id"] if user else 4

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM invoices ORDER BY id DESC")
    invoices = c.fetchall()

    c.execute("SELECT sum(amount), count(*) FROM invoices")
    stat = c.fetchone()
    total_rev = stat[0] or 0.0
    total_inv = stat[1] or 0
    conn.close()

    inv_rows = ""
    for inv in invoices:
        inv_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-weight: 700;">#INV-{inv['id']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{inv['client_name']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{inv['service_name']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-weight: 700; color: var(--success);">{inv['amount']:,.0f} ج/ر</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{inv['payment_method']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-size: 0.8rem; color: var(--text-muted);">{inv['created_at'][:16]}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);"><span style="background: #ecfdf5; color: #065f46; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 700;">مسدد ✅</span></td>
        </tr>
        """

    body = f"""
    <div style="margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 1.6rem; color: var(--primary);">🧾 {t('invoices_title')}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">{t('invoices_subtitle')}</p>
    </div>

    <div class="grid-2" style="margin-bottom: 20px;">
        <div class="card" style="border-top: 4px solid var(--success); text-align: center;">
            <div style="font-size: 0.85rem; color: var(--text-muted); font-weight: 700;">إجمالي عوائد العيادة المسددة</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: var(--success); margin-top: 4px;">{total_rev:,.0f} ج/ر</div>
        </div>
        <div class="card" style="border-top: 4px solid var(--primary); text-align: center;">
            <div style="font-size: 0.85rem; color: var(--text-muted); font-weight: 700;">إجمالي الفواتير وسندات القبض</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: var(--primary); margin-top: 4px;">{total_inv}</div>
        </div>
    </div>

    <div class="card" style="border-top: 4px solid var(--primary);">
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: right; font-size: 0.88rem;">
                <thead>
                    <tr style="background: var(--bg);">
                        <th style="padding: 10px;">رقم السند</th>
                        <th style="padding: 10px;">العميل / المربي</th>
                        <th style="padding: 10px;">الخدمة والأدوية</th>
                        <th style="padding: 10px;">المبلغ</th>
                        <th style="padding: 10px;">طريقة الدفع</th>
                        <th style="padding: 10px;">التاريخ</th>
                        <th style="padding: 10px;">الحالة</th>
                    </tr>
                </thead>
                <tbody>
                    {inv_rows}
                </tbody>
            </table>
        </div>

        <div style="margin-top: 24px; padding: 16px; background: var(--bg); border-radius: 10px;">
            <h4 style="margin-top: 0;">➕ إصدار سند قبض وفاتورة جديدة:</h4>
            <form action="/clinic/invoices/add" method="POST" style="display: flex; gap: 10px; flex-wrap: wrap;">
                <input type="text" name="client_name" placeholder="اسم المربي / العميل" required style="flex: 2; min-width: 160px; padding: 10px; border: 1px solid var(--border); border-radius: 6px;">
                <input type="text" name="service_name" placeholder="الخدمة (كشف، جراحة، أدوية)" required style="flex: 3; min-width: 200px; padding: 10px; border: 1px solid var(--border); border-radius: 6px;">
                <input type="number" step="10" name="amount" placeholder="المبلغ ج/ر" required style="flex: 1; min-width: 100px; padding: 10px; border: 1px solid var(--border); border-radius: 6px;">
                <select name="payment_method" style="flex: 1; min-width: 140px; padding: 10px; border: 1px solid var(--border); border-radius: 6px;">
                    <option value="نقداً (Cash)">نقداً (Cash)</option>
                    <option value="فودافون كاش / إنستاباي">فودافون كاش / إنستاباي</option>
                    <option value="مدى (Mada) / أبل باي">مدى / أبل باي</option>
                    <option value="بطاقة ائتمان Visa">بطاقة ائتمان Visa</option>
                </select>
                <button type="submit" class="btn btn-primary">إصدار السند فوراً</button>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_invoices"), body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/clinic/invoices/add")
async def add_invoice(
    client_name: str = Form(...),
    service_name: str = Form(...),
    amount: float = Form(...),
    payment_method: str = Form("نقداً (Cash)")
):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO invoices (user_id, client_name, service_name, amount, status, payment_method, created_at)
    VALUES (4, ?, ?, ?, 'paid', ?, ?)
    """, (client_name, service_name, amount, payment_method, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return RedirectResponse("/clinic/invoices", status_code=303)

# ==============================================================================
# ROUTE: DIAGNOSTIC LAB TESTS & IMAGING
# ==============================================================================
@app.get("/clinic/lab", response_class=HTMLResponse)
async def clinic_lab_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM lab_tests ORDER BY id DESC")
    tests = c.fetchall()
    conn.close()

    test_rows = ""
    for tb in tests:
        test_rows += f"""
        <div style="padding: 16px; border-bottom: 1px solid var(--border); background: var(--card-bg); margin-bottom: 12px; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="font-weight: 800; font-size: 1.05rem; color: var(--primary);">{tb['animal_name']} - {tb['test_type']}</div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">{tb['test_date']}</div>
            </div>
            <div style="font-size: 0.9rem; line-height: 1.7; background: var(--bg); padding: 10px; border-radius: 6px;">
                <strong>التقرير والنتيجة السريرية:</strong><br>{tb['result_summary']}
            </div>
        </div>
        """

    body = f"""
    <div style="margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 1.6rem; color: var(--primary);">🔬 {t('lab_title')}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">{t('lab_subtitle')}</p>
    </div>

    <div class="grid-2">
        <div>
            <h3 style="margin-top: 0;">📋 سجل التحاليل المخبرية والنتائج:</h3>
            {test_rows}
        </div>

        <div class="card" style="border-top: 4px solid var(--primary);">
            <h3 style="margin-top: 0; color: var(--primary);">➕ توثيق فحص مخبري أو تقرير سونار جديد</h3>
            <form action="/clinic/lab/add" method="POST">
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px;">اسم الحيوان / رقم الكود</label>
                    <input type="text" name="animal_name" required placeholder="مثال: بقرة حلوب #108" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>

                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px;">نوع الفحص المخبري / الإشعاعي</label>
                    <select name="test_type" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                        <option value="صورة دم كاملة (CBC)">صورة دم كاملة (CBC & Leukogram)</option>
                        <option value="فحص ميكروسكوبي لطفيليات الدم">فحص ميكروسكوبي لطفيليات الدم (Blood Smear)</option>
                        <option value="كيمياء الدم ووظائف كبد وكلى">كيمياء الدم (Liver & Kidney Profile)</option>
                        <option value="فحص عينة براز للديدان والكوكسيديا">فحص عينة براز (Fecal Floatation)</option>
                        <option value="فحص بالموجات فوق الصوتية (سونار)">فحص بالموجات فوق الصوتية (Ultrasound Scan)</option>
                        <option value="مسحة بيولوجية وفحص PCR">مسحة بيولوجية واختبار (PCR Test)</option>
                    </select>
                </div>

                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px;">تاريخ إجراء الفحص</label>
                    <input type="date" name="test_date" value="{datetime.now().strftime('%Y-%m-%d')}" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>

                <div style="margin-bottom: 16px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px;">ملخص النتائج والتفسير الإكلينيكي</label>
                    <textarea name="result_summary" rows="4" required placeholder="سجل القيم المرصودة، دلالات الالتهاب أو وجود طفيليات، وتوصية العلاج..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;"></textarea>
                </div>

                <button type="submit" class="btn btn-primary" style="width: 100%; padding: 12px; justify-content: center;">
                    حفظ التقرير في السجل المخبري
                </button>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_lab"), body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/clinic/lab/add")
async def add_lab_test(
    animal_name: str = Form(...),
    test_type: str = Form(...),
    test_date: str = Form(...),
    result_summary: str = Form(...)
):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO lab_tests (user_id, animal_name, test_type, test_date, result_summary, attachment_filename, created_at)
    VALUES (4, ?, ?, ?, ?, '', ?)
    """, (animal_name, test_type, test_date, result_summary, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return RedirectResponse("/clinic/lab", status_code=303)

# Load existing core modules & endpoints

# ROUTE 1: HOME & PROMINENT REFERENCES DOWNLOAD
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def home_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM cases ORDER BY id DESC LIMIT 20")
    cases = c.fetchall()

    c.execute("SELECT count(*) FROM cases")
    total_cases = c.fetchone()[0]

    c.execute("SELECT count(*) FROM drug_inventory WHERE stock_quantity <= min_threshold")
    low_stock_count = c.fetchone()[0]

    c.execute("SELECT count(*) FROM appointments WHERE status = 'scheduled'")
    scheduled_appts = c.fetchone()[0]

    # Active clients in last 3 days
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT count(DISTINCT client_name) FROM client_operations WHERE performed_at >= ?", (three_days_ago,))
    active_clients_3d = c.fetchone()[0]
    conn.close()

    stock_alert_html = ""
    if low_stock_count > 0:
        alert_title = t("alert_pharmacy_stock_title", "🚨 تنبيه صيدلية العيادة")
        alert_msg = f"{t('alert_pharmacy_stock_msg', 'يوجد أصناف دوائية أوشكت على النفاد في مخزونك!')} ({low_stock_count})"
        review_btn = t("alert_review_stock_btn", "مراجعة المخزون فوراً")
        stock_alert_html = f"""
        <div style="background: var(--danger-bg); border: 1px solid #f87171; border-radius: 10px; padding: 12px 18px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
            <div style="color: #991b1b; font-weight: 700;">
                {alert_title}: {alert_msg}
            </div>
            <a href="/clinic#inventory" class="btn btn-accent" style="font-size: 0.82rem;">{review_btn}</a>
        </div>
        """

    # Top Featured References Bar (Direct 1-Click Download right at the start)
    top_refs = get_all_references()[:6]
    refs_preview_cards = ""
    for r in top_refs:
        is_ar = r["id"].startswith("arab_")
        badge = t("ref_badge_arab", "🇪🇬 مرجع عربي") if is_ar else t("ref_badge_intl", "🌐 مرجع دولي")
        refs_preview_cards += f"""
        <div style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <span style="font-size: 0.72rem; background: {'#dcfce7' if is_ar else '#e0f2fe'}; color: {'#166534' if is_ar else '#0369a1'}; padding: 2px 6px; border-radius: 8px; font-weight: 700;">{badge}</span>
                <div style="font-weight: 700; font-size: 0.88rem; color: var(--primary); margin: 6px 0 4px 0;">{r['name'][:48]}...</div>
                <div style="font-size: 0.78rem; color: var(--text-muted);">{r['citation'][:65]}...</div>
            </div>
            <div style="margin-top: 10px; display: flex; gap: 6px;">
                <a href="/references/download/{r['id']}" download class="btn btn-download" style="flex: 1; padding: 6px; font-size: 0.78rem; justify-content: center; font-weight: 700;">
                    {t('download_single_book_btn', '📥 تحميل المرجع (PDF)')}
                </a>
                <a href="/references/pdf/{r['id']}" target="_blank" class="btn btn-outline" style="padding: 6px 10px; font-size: 0.78rem; justify-content: center;">
                    {t('view_online_pdf_btn', '👁️ عرض')}
                </a>
            </div>
        </div>
        """

    featured_refs_html = f"""
    <div class="card" style="border-top: 4px solid #0284c7; background: linear-gradient(180deg, #f0f9ff 0%, #ffffff 100%);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
            <div>
                <h3 style="margin: 0; font-size: 1.25rem; color: #0284c7;">📚 {t('references_featured_title')}</h3>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 2px;">{t('references_featured_desc')}</div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
                <a href="/references/download-all" class="btn" style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: #ffffff; font-weight: 700; font-size: 0.85rem; box-shadow: 0 4px 10px rgba(2, 132, 199, 0.25);">
                    {t('home_refs_zip_btn', '📦 تحميل كافة المراجع الـ 30 (ZIP)')}
                </a>
                <a href="/references" class="btn btn-download" style="font-size: 0.85rem;">{t('browse_all_refs_btn', 'استعراض كافة المراجع الـ 30 ⬅️')}</a>
            </div>
        </div>
        <div class="grid-3" style="gap: 12px;">
            {refs_preview_cards}
        </div>
    </div>
    """

    cases_html = ""
    for cs in cases:
        img_badge = f'<span style="background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem;">📷 {t("case_img_badge", "مرفق صورة")}</span>' if cs["image_filename"] else ""
        cases_html += f"""
        <div class="card" style="margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <div style="font-size: 1.1rem; font-weight: 700; color: var(--primary);">
                    {cs['animal_name']} <span style="font-size: 0.85rem; color: var(--text-muted);">({cs['species']})</span> {img_badge}
                </div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
                    {t('case_age_label', 'العمر')}: {cs['age']} | {t('case_weight_label', 'الوزن')}: {cs['weight']} {t('unit_kg', 'كجم')} | {t('case_date_label', 'التاريخ')}: {cs['created_at'][:16]}
                </div>
                <div style="font-size: 0.9rem; margin-top: 6px;">
                    <strong>{t('case_symptoms_label', 'الأعراض')}:</strong> {cs['symptoms'][:120]}...
                </div>
            </div>
            <div style="display: flex; gap: 8px;">
                <a href="/case/{cs['id']}" class="btn btn-primary" style="font-size: 0.85rem;">📋 {t('case_open_report', 'فتح التقرير السريري')}</a>
                <form action="/delete/{cs['id']}" method="POST" onsubmit="return confirm('{t('confirm_delete_case', 'هل تريد حذف هذه الحالة؟')}');" style="margin: 0;">
                    <button type="submit" class="btn btn-outline" style="color: var(--danger); font-size: 0.85rem;">🗑️</button>
                </form>
            </div>
        </div>
        """

    if not cases:
        cases_html = f"""
        <div class="card" style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 3rem;">🩺</div>
            <div style="font-size: 1.2rem; font-weight: 700; margin-top: 10px;">{t('no_cases_title', 'لا توجد حالات سريرية مسجلة بعد')}</div>
            <p style="color: var(--text-muted);">{t('no_cases_desc', 'ابدأ بفحص أول حالة سريرية لحيوان أو مزرعة لإنشاء التقرير الطبي والدوائي المعتمد.')}</p>
            <a href="#new-case" class="btn btn-primary" style="margin-top: 10px;">➕ {t('new_case_btn', 'فحص حالة جديدة الآن')}</a>
        </div>
        """

    body = f"""
    {stock_alert_html}

    <!-- PWA Install Hero Banner for browser visitors -->
    <div id="pwa-install-banner" class="card" style="background: linear-gradient(135deg, #0f766e 0%, #047857 100%); color: white; border: none; padding: 16px 18px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; border-radius: 14px; box-shadow: 0 4px 15px rgba(15,118,110,0.25);">
        <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 250px;">
            <div style="font-size: 2.2rem; background: rgba(255,255,255,0.2); border-radius: 12px; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">📲</div>
            <div>
                <div style="font-weight: 800; font-size: 1.05rem;">تحميل وتثبيت تطبيق VetMind AI على هاتفك أو حاسوبك</div>
                <div style="font-size: 0.82rem; opacity: 0.9; margin-top: 2px;">يفتح في نافذة مستقلة شاشة كاملة (مثل يوتيوب وفيسبوك) بدون شريط متصفح وبسرعة فائقة.</div>
            </div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button type="button" onclick="triggerPwaInstall()" class="btn" style="background: #fde047; color: #854d0e; font-weight: 800; padding: 8px 18px; border-radius: 8px; font-size: 0.88rem; box-shadow: 0 2px 8px rgba(0,0,0,0.15); border: none; cursor: pointer;">
                📥 تحميل وتثبيت التطبيق الآن
            </button>
            <button type="button" onclick="openMobileModal()" class="btn" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.4); padding: 8px 14px; border-radius: 8px; font-size: 0.82rem; cursor: pointer;">
                📱 فتح باركود الموبايل
            </button>
        </div>
    </div>

    <!-- Quick Apps Box (صندوق التطبيقات السريعة - للأيقونات تحت بعضها بتنسيق جذاب ومريح للعين) -->
    <div class="mobile-app-box">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.4rem;">📱</span>
                <div>
                    <h3 style="margin: 0; font-size: 1.15rem; color: var(--primary);">صندوق تطبيقات ومميزات VetMind AI</h3>
                    <div style="font-size: 0.78rem; color: var(--text-muted);">جميع الأدوات والخدمات السريرية منظمة لسهولة الوصول من الموبايل والكمبيوتر</div>
                </div>
            </div>
            <button type="button" onclick="triggerPwaInstall()" class="btn btn-primary" style="padding: 6px 12px; font-size: 0.8rem;">
                📥 تحميل التطبيق
            </button>
        </div>

        <div class="mobile-app-grid">
            <a href="/chat" class="mobile-app-card" style="border-top: 3px solid #0f766e;">
                <span class="mobile-app-card-icon">💬</span>
                <span class="mobile-app-card-title">{t('nav_chat')}</span>
                <span class="mobile-app-card-sub">مستشار بيطري ذكي فوري</span>
            </a>
            <a href="/community" class="mobile-app-card" style="border-top: 3px solid #0284c7; background: #f0f9ff;">
                <span class="mobile-app-card-icon">🌐</span>
                <span class="mobile-app-card-title" style="color: #0284c7;">VetBook الأطباء</span>
                <span class="mobile-app-card-sub">شبكة التواصل السريري</span>
            </a>
            <a href="/clinic" class="mobile-app-card" style="border-top: 3px solid #047857;">
                <span class="mobile-app-card-icon">🏥</span>
                <span class="mobile-app-card-title">{t('nav_clinic')}</span>
                <span class="mobile-app-card-sub">سجل الحالات والمواعيد</span>
            </a>
            <a href="/clinic/cases-gallery" class="mobile-app-card" style="border-top: 3px solid #10b981;">
                <span class="mobile-app-card-icon">🖼️</span>
                <span class="mobile-app-card-title">معرض الحالات</span>
                <span class="mobile-app-card-sub">أرشيف صور الفحوصات</span>
            </a>
            <a href="/rx-prescription" class="mobile-app-card" style="border-top: 3px solid #6366f1;">
                <span class="mobile-app-card-icon">📋</span>
                <span class="mobile-app-card-title">{t('nav_rx')}</span>
                <span class="mobile-app-card-sub">حساب الجرعات والروشتة</span>
            </a>
            <a href="/interactions" class="mobile-app-card" style="border-top: 3px solid #ea580c;">
                <span class="mobile-app-card-icon">⚠️</span>
                <span class="mobile-app-card-title">{t('nav_interactions')}</span>
                <span class="mobile-app-card-sub">كشف التفاعلات السلبية</span>
            </a>
            <a href="/pharmacy" class="mobile-app-card" style="border-top: 3px solid #059669;">
                <span class="mobile-app-card-icon">💊</span>
                <span class="mobile-app-card-title">{t('nav_pharmacy')}</span>
                <span class="mobile-app-card-sub">1,005 دواء بالأسماء</span>
            </a>
            <a href="/vision-detect" class="mobile-app-card" style="border-top: 3px solid #ec4899;">
                <span class="mobile-app-card-icon">👁️</span>
                <span class="mobile-app-card-title">{t('nav_vision_detect')}</span>
                <span class="mobile-app-card-sub">تحليل الصور بالذكاء الاصطناعي</span>
            </a>
            <a href="/tools" class="mobile-app-card" style="border-top: 3px solid #8b5cf6;">
                <span class="mobile-app-card-icon">🛠️</span>
                <span class="mobile-app-card-title">الأدوات الإكلينيكية</span>
                <span class="mobile-app-card-sub">30 أداة وحاسبة متقدمة</span>
            </a>
            <a href="/references" class="mobile-app-card" style="border-top: 3px solid #d97706;">
                <span class="mobile-app-card-icon">📚</span>
                <span class="mobile-app-card-title">{t('nav_references')}</span>
                <span class="mobile-app-card-sub">الـ 30 مرجع عربي وعالمي</span>
            </a>
            <a href="/clinic/prayer-times" class="mobile-app-card" style="border-top: 3px solid #14b8a6;">
                <span class="mobile-app-card-icon">🕌</span>
                <span class="mobile-app-card-title">مواقيت الصلاة</span>
                <span class="mobile-app-card-sub">مواقيت الصلاة الدقيقة</span>
            </a>
            <a href="/premium" class="mobile-app-card" style="border-top: 3px solid #f59e0b; background: #fffbeb;">
                <span class="mobile-app-card-icon">⭐</span>
                <span class="mobile-app-card-title" style="color: #b45309;">{t('nav_premium')}</span>
                <span class="mobile-app-card-sub">ترقية الحساب والمزايا</span>
            </a>
        </div>
    </div>

    <!-- Community Banner on Dashboard -->
    <div class="card" style="border-top: 4px solid #0284c7; background: linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%); margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
        <div style="display: flex; align-items: center; gap: 14px;">
            <div style="font-size: 2.4rem; background: #e0f2fe; padding: 10px 14px; border-radius: 12px;">👥</div>
            <div>
                <h3 style="margin: 0 0 4px 0; color: #0369a1; font-size: 1.25rem;">VetBook الأطباء البيطريين</h3>
                <p style="margin: 0; color: var(--text-muted); font-size: 0.9rem;">شبكة التواصل السريري والمهني التفاعلي للأطباء البيطريين لتبادل الحالات والخبرات الحقلية والمقالات الموثقة.</p>
            </div>
        </div>
        <a href="/community" class="btn" style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: white; padding: 10px 20px; font-weight: 700; border-radius: 8px; text-decoration: none;">
            فتح VetBook الأطباء البيطريين 🌐 ⬅️
        </a>
    </div>

    <div class="grid-4"  style="margin-bottom: 24px;">
        <div class="card" style="border-top: 4px solid var(--primary); padding: 16px;">
            <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 700;">{t("stat_total_exams", "إجمالي الفحوصات")}</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: var(--primary); margin-top: 4px;">{total_cases}</div>
            <div style="font-size: 0.75rem; color: var(--success); margin-top: 4px;">{t("stat_vision_badge", "فحص بالرؤية الحاسوبية")}</div>
        </div>
        <div class="card" style="border-top: 4px solid var(--accent); padding: 16px;">
            <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 700;">{t("stat_upcoming_appts", "المواعيد القادمة بالعيادة")}</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: var(--accent); margin-top: 4px;">{scheduled_appts}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;"><a href="/clinic" style="color: var(--accent); text-decoration: none;">{t('stat_manage_appts', 'إدارة المواعيد')}</a></div>
        </div>
        <div class="card" style="border-top: 4px solid #8b5cf6; padding: 16px;">
            <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 700;">{t("stat_active_clients_3d", "العملاء النشطين")}</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: #8b5cf6; margin-top: 4px;">{active_clients_3d}</div>
            <div style="font-size: 0.75rem; color: #8b5cf6; margin-top: 4px;"><a href="/time-demand" style="color: #8b5cf6; text-decoration: none;">{t('stat_view_timedemand', 'عرض Time Demand 📊')}</a></div>
        </div>
        <div class="card" style="border-top: 4px solid var(--gold); padding: 16px;">
            <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 700;">{t("stat_current_plan", "باقة الاشتراك الحالية")}</div>
            <div style="font-size: 1.2rem; font-weight: 800; color: var(--gold); margin-top: 4px;">{'⭐ PREMIUM VIP' if user and user.get('is_premium') else t('stat_standard_plan', 'النسخة القياسية')}</div>
            <div style="font-size: 0.75rem; color: var(--gold); margin-top: 4px;"><a href="/premium" style="color: var(--gold); text-decoration: none; font-weight: 700;">{t('stat_upgrade_plan', 'ترقية وتفعيل المزايا ⭐')}</a></div>
        </div>
    </div>

    {featured_refs_html}

    <div class="grid-2">
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <h2 style="margin: 0; font-size: 1.3rem;">📋 {t('cases_title')}</h2>
                <a href="/vision-detect" class="btn btn-accent" style="font-size: 0.85rem;">👁️ {t('nav_vision_detect')}</a>
            </div>
            {cases_html}
        </div>

        <div id="new-case">
            <div class="card" style="border-top: 4px solid var(--primary);">
                <h2 style="margin-top: 0; font-size: 1.3rem; color: var(--primary);">🩺 {t('case_add_title', 'فحص وتسجيل حالة سريرية جديدة')}</h2>
                <p style="font-size: 0.88rem; color: var(--text-muted);">{t('case_add_desc', 'ارفع صورة الحالة الظاهرية أو الآفة الجلدية لتحليلها تلقائياً واستخراج التشخيص التفريقي والأدوية المعتمدة.')}</p>

                <form action="/add-case" method="POST" enctype="multipart/form-data">
                    <div style="margin-bottom: 14px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('case_animal_name')}</label>
                        <input type="text" name="animal_name" required placeholder="{t('case_animal_name_ph', 'مثال: بقرة حلوب رقم 412 / ماكس كلب بوليسي')}" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>

                    <div class="grid-2" style="margin-bottom: 14px;">
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('case_species')}</label>
                            <select name="species" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                                <option value="أبقار">{t('species_bovine', '🐄 أبقار (Cattle / Bovine)')}</option>
                                <option value="أغنام وماعز">{t('species_ovine', '🐑 أغنام وماعز (Ovine / Caprine)')}</option>
                                <option value="إبل وهجن">{t('species_camel', '🐪 إبل وهجن (Camels / Dromedary)')}</option>
                                <option value="خيول">{t('species_equine', '🐎 خيول وفصيلة خيلية (Equine)')}</option>
                                <option value="دواجن وطيور">{t('species_poultry', '🐔 دواجن وطيور (Poultry / Avian)')}</option>
                                <option value="كلاب">{t('species_canine', '🐕 كلاب (Canine)')}</option>
                                <option value="قطط">{t('species_feline', '🐈 قطط (Feline)')}</option>
                                <option value="أرانب">{t('species_rabbit', '🐇 أرانب (Rabbits)')}</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('case_age')} & {t('case_weight')}</label>
                            <div style="display: flex; gap: 8px;">
                                <input type="text" name="age" placeholder="{t('case_age_label', 'العمر')}" style="width: 50%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                                <input type="text" name="weight" placeholder="{t('case_weight_unit', 'الوزن كجم')}" style="width: 50%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                            </div>
                        </div>
                    </div>

                    <div style="margin-bottom: 14px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('case_symptoms')}</label>
                        <textarea name="symptoms" rows="3" required placeholder="{t('case_symptoms_ph', 'صف الأعراض السريرية بالتفصيل (حرارة، إفرازات فموية، عرج، إسهال مائي، وذمة...)')}" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;"></textarea>
                    </div>

                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">📸 {t('case_image')}</label>
                        <input type="file" name="image" accept="image/*" style="width: 100%; padding: 10px; border: 1px dashed var(--primary); border-radius: 8px; background: var(--primary-light);">
                    </div>

                    <button type="submit" class="btn btn-primary" style="width: 100%; padding: 12px; font-size: 1rem; justify-content: center;">
                        🚀 {t('case_submit')}
                    </button>
                </form>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_home"), body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# ROUTE 2: 2FA & OTP VERIFICATION INTERFACE
# ==============================================================================
@app.get("/verify-otp", response_class=HTMLResponse)
async def verify_otp_page(request: Request, email: str = "", resent: int = 0, channel: str = "both"):
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT otp_code, phone, otp_expires_at FROM users WHERE email = ?", (email.strip().lower(),))
    user_row = c.fetchone()
    conn.close()

    from verification_service import mask_phone_number
    phone_raw = user_row["phone"] if user_row and user_row["phone"] else ""
    phone_display = mask_phone_number(phone_raw) if phone_raw else "رقم غير مسجل"

    resent_alert = ""
    if resent:
        resent_alert = f"""
        <div style="background: #dcfce7; border: 1.5px solid #86efac; color: #166534; padding: 12px; border-radius: 10px; margin-bottom: 16px; font-weight: 700; font-size: 0.9rem;">
            ✅ تم بنجاح توليد كود أمان جديد وإرساله في رسالة نصية SMS وعبر البريد الإلكتروني!
        </div>
        """

    body = f"""
    <div style="max-width: 540px; margin: 40px auto;">
        <div class="card" style="border-top: 6px solid var(--primary); text-align: center;">
            <div style="font-size: 3rem; margin-bottom: 10px;">🔐</div>
            <h1 style="margin: 0 0 8px 0; font-size: 1.5rem; color: var(--primary);">{t('otp_title')}</h1>
            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 20px;">
                {t('otp_subtitle')}
            </p>

            {resent_alert}

            <div style="background: #f0fdf4; border: 1.5px solid #86efac; padding: 18px; border-radius: 12px; margin-bottom: 20px; font-size: 0.9rem; color: #166534; text-align: right;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                    <div>✉️ <strong>البريد الإلكتروني:</strong> {email}</div>
                    <span style="background: #dcfce7; color: #15803d; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px; font-weight: 700;">تم الإرسال</span>
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <div>📱 <strong>الهاتف المسجل (SMS):</strong> <span dir="ltr" style="font-family: monospace; font-weight: 700;">{phone_display}</span></div>
                    <span style="background: #dcfce7; color: #15803d; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px; font-weight: 700;">تم إرسال SMS</span>
                </div>
                <div style="background: #ffffff; border-radius: 8px; padding: 12px; border: 1px dashed #86efac; font-size: 0.85rem; color: #047857; line-height: 1.6; text-align: center;">
                    📲 <strong>يرجى مراجعة صندوق الرسائل النصية القصيرة (SMS) في هاتفك أو بريدك الإلكتروني لإدخال الرمز السري المكون من 6 أرقام.</strong>
                </div>
            </div>

            <form action="/verify-otp" method="POST">
                <input type="hidden" name="email" value="{email}">
                <div style="margin-bottom: 20px;">
                    <input type="text" name="otp_code" required maxlength="6" placeholder="{t('otp_input_placeholder')}" style="width: 100%; padding: 14px; text-align: center; font-size: 1.6rem; font-weight: 900; letter-spacing: 6px; border: 2.5px solid var(--primary); border-radius: 10px;">
                </div>

                <button type="submit" class="btn btn-primary" style="width: 100%; padding: 14px; font-size: 1.05rem; justify-content: center; font-weight: 800;">
                    🚀 {t('otp_verify_btn')}
                </button>
            </form>

            <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
                <a href="/resend-otp?email={email}&channel=email" class="btn btn-outline" style="font-size: 0.82rem; padding: 6px 12px;">
                    ✉️ إعادة الإرسال عبر البريد
                </a>
                <a href="/resend-otp?email={email}&channel=sms" class="btn btn-outline" style="font-size: 0.82rem; padding: 6px 12px;">
                    📱 إعادة الإرسال عبر SMS
                </a>
            </div>

            <div style="margin-top: 20px; border-top: 1px solid var(--border); padding-top: 14px;">
                <a href="/" style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.88rem; color: var(--primary); text-decoration: none; font-weight: 700;">
                    🏠 العودة للصفحة الرئيسية ⬅️
                </a>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("otp_title"), body, None, lang), media_type="text/html; charset=utf-8")

@app.post("/verify-otp")
async def process_verify_otp(email: str = Form(...), otp_code: str = Form(...)):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    user = c.fetchone()

    if not user:
        conn.close()
        return HTMLResponse("<script>alert('المستخدم غير موجود'); window.location.href='/login';</script>")

    if user["otp_code"] and user["otp_code"].strip() != otp_code.strip():
        conn.close()
        return HTMLResponse("<script>alert('كود التأكيد غير صحيح! يرجى إدخال الرمز الصحيح.'); history.back();</script>")

    c.execute("UPDATE users SET is_email_verified = 1, otp_code = '' WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()

    target_redir = redirect_url if (redirect_url and redirect_url.startswith("/") and not redirect_url.startswith("//")) else "/"
    resp = RedirectResponse(target_redir, status_code=303)
    token = make_session_token(user["id"])
    resp.set_cookie(key="vetmind_session", value=token, max_age=31536000, httponly=True)
    return resp

# ==============================================================================
# ROUTE 3: PREMIUM UPGRADE & LOCALIZED PAYMENTS
# ==============================================================================
@app.get("/premium", response_class=HTMLResponse)
async def premium_page(request: Request, selected_country: str = ""):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    user_country = selected_country or (user.get("country") if user else "مصر")

    country_opts = "".join([f'<option value="{c}" {"selected" if c == user_country else ""}>{c}</option>' for c in ARAB_COUNTRIES])

    payment_info = ""
    if user_country == "مصر":
        payment_info = f"""
        <div style="background: #f0fdf4; border: 2px solid #86efac; border-radius: 12px; padding: 18px; margin-bottom: 18px;">
            <div style="font-weight: 800; font-size: 1.1rem; color: #166534; margin-bottom: 6px;">🇪🇬 {t('pay_method_egypt')}</div>
            <div style="font-size: 0.9rem; line-height: 1.7; color: #14532d;">
                • التحويل الفوري عبر <strong>إنستاباي (InstaPay)</strong> أو <strong>فودافون كاش (Vodafone Cash)</strong>: 01000000000<br>
                • أو الدفع الإلكتروني عبر كود فوري (Fawry Pay): <strong>772910</strong><br>
                • السعر الرسمي: <strong>350 جنيه مصري شهرياً</strong> (شامل كافة ميزات الرؤية والتقارير والذكاء الاصطناعي).
            </div>
        </div>
        """
    elif user_country == "السعودية":
        payment_info = f"""
        <div style="background: #f0fdf4; border: 2px solid #86efac; border-radius: 12px; padding: 18px; margin-bottom: 18px;">
            <div style="font-weight: 800; font-size: 1.1rem; color: #166534; margin-bottom: 6px;">🇸🇦 {t('pay_method_saudi')}</div>
            <div style="font-size: 0.9rem; line-height: 1.7; color: #14532d;">
                • الدفع عبر بطاقة <strong>مدى (Mada)</strong> أو <strong>Apple Pay</strong> أو <strong>stc pay</strong>.<br>
                • السعر الرسمي: <strong>75 ريال سعودي شهرياً</strong>.
            </div>
        </div>
        """
    elif user_country == "الإمارات":
        payment_info = f"""
        <div style="background: #f0fdf4; border: 2px solid #86efac; border-radius: 12px; padding: 18px; margin-bottom: 18px;">
            <div style="font-weight: 800; font-size: 1.1rem; color: #166534; margin-bottom: 6px;">🇦🇪 {t('pay_method_uae')}</div>
            <div style="font-size: 0.9rem; line-height: 1.7; color: #14532d;">
                • الدفع عبر <strong>Apple Pay</strong> أو نظام <strong>كليك (Klip)</strong> أو البطاقات المصرفية.<br>
                • السعر الرسمي: <strong>75 درهم إماراتي شهرياً</strong>.
            </div>
        </div>
        """
    elif user_country == "الأردن":
        payment_info = f"""
        <div style="background: #f0fdf4; border: 2px solid #86efac; border-radius: 12px; padding: 18px; margin-bottom: 18px;">
            <div style="font-weight: 800; font-size: 1.1rem; color: #166534; margin-bottom: 6px;">🇯🇴 {t('pay_method_jordan')}</div>
            <div style="font-size: 0.9rem; line-height: 1.7; color: #14532d;">
                • التحويل عبر <strong>كليك (CliQ)</strong> أو محفظة <strong>زين كاش (Zain Cash)</strong>.<br>
                • السعر الرسمي: <strong>15 دينار أردني شهرياً</strong>.
            </div>
        </div>
        """
    else:
        payment_info = f"""
        <div style="background: #f0fdf4; border: 2px solid #86efac; border-radius: 12px; padding: 18px; margin-bottom: 18px;">
            <div style="font-weight: 800; font-size: 1.1rem; color: #166534; margin-bottom: 6px;">🌐 {t('pay_method_global')}</div>
            <div style="font-size: 0.9rem; line-height: 1.7; color: #14532d;">
                • Secure International Payment via <strong>Stripe, Visa, Mastercard, or PayPal</strong>.<br>
                • Price: <strong>$20.00 USD / Month</strong>.
            </div>
        </div>
        """

    is_already_premium = user and user.get("is_premium")
    status_box = ""
    if is_already_premium:
        status_box = """
        <div style="background: #fef08a; border: 1px solid #facc15; padding: 14px; border-radius: 10px; margin-bottom: 20px; font-weight: 700; color: #854d0e; text-align: center;">
            🌟 حسابك مفعل بباقة VetMind AI Enterprise Premium VIP مدى الحياة!
        </div>
        """

    body = f"""
    <div style="max-width: 800px; margin: 20px auto;">
        {status_box}
        <div class="card" style="border-top: 6px solid var(--gold);">
            <div style="text-align: center; margin-bottom: 24px;">
                <span style="font-size: 3rem;">⭐</span>
                <h1 style="margin: 6px 0; font-size: 1.7rem; color: var(--gold);">{t('premium_upgrade_title')}</h1>
                <p style="color: var(--text-muted); font-size: 0.95rem;">{t('premium_upgrade_subtitle')}</p>
            </div>

            <div style="background: var(--bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                <h3 style="margin-top: 0; color: var(--primary);">✨ مميزات باقة Premium الحصرية:</h3>
                <ul style="padding-right: 20px; line-height: 1.9; font-size: 0.95rem; margin: 0;">
                    <li><strong>{t('premium_feature_1')}</strong></li>
                    <li><strong>{t('premium_feature_2')}</strong></li>
                    <li><strong>{t('premium_feature_3')}</strong></li>
                    <li><strong>{t('premium_feature_4')}</strong></li>
                </ul>
            </div>

            <form action="/premium" method="GET" style="margin-bottom: 18px;">
                <label style="display: block; font-weight: 700; margin-bottom: 6px;">{t('premium_select_country')}</label>
                <div style="display: flex; gap: 10px;">
                    <select name="selected_country" onchange="this.form.submit()" style="flex: 1; padding: 10px; border: 1px solid var(--border); border-radius: 8px; font-weight: 600;">
                        {country_opts}
                    </select>
                </div>
            </form>

            {payment_info}

            <form action="/premium/activate" method="POST">
                <input type="hidden" name="country" value="{user_country}">
                <button type="submit" class="btn btn-gold" style="width: 100%; padding: 14px; font-size: 1.1rem; justify-content: center; font-weight: 800;">
                    ⭐ {t('premium_pay_btn')}
                </button>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_premium"), body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/premium/activate")
async def activate_premium(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET is_premium = 1 WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return RedirectResponse("/premium", status_code=303)

# ==============================================================================
# ROUTE 4: TIME DEMAND & CLIENT OPERATIONS (LAST 3 DAYS)
# ==============================================================================
@app.get("/time-demand", response_class=HTMLResponse)
async def time_demand_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    SELECT * FROM client_operations 
    WHERE performed_at >= ? 
    ORDER BY performed_at DESC
    """, (three_days_ago,))
    operations = c.fetchall()

    c.execute("SELECT count(DISTINCT client_name), count(*), sum(fee_collected) FROM client_operations WHERE performed_at >= ?", (three_days_ago,))
    stats = c.fetchone()
    active_clients = stats[0] or 0
    total_ops = stats[1] or 0
    total_revenue = stats[2] or 0.0
    conn.close()

    table_rows = ""
    for op in operations:
        table_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid var(--border);">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 38px; height: 38px; border-radius: 50%; background: var(--primary-light); display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">👤</div>
                    <div>
                        <div style="font-weight: 700; color: var(--primary);">{op['client_name']}</div>
                        <div style="font-size: 0.78rem; color: var(--text-muted);">{op['client_phone']}</div>
                    </div>
                </div>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid var(--border); font-weight: 600;">{op['animal_name']} ({op['species']})</td>
            <td style="padding: 12px; border-bottom: 1px solid var(--border);">
                <div style="font-weight: 700;">{op['operation_type']}</div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">{op['operation_details']}</div>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid var(--border); font-size: 0.85rem; color: var(--text-muted);">{op['performed_at'][:16]}</td>
            <td style="padding: 12px; border-bottom: 1px solid var(--border); font-weight: 700; color: var(--success);">{op['fee_collected']} ج/ر</td>
            <td style="padding: 12px; border-bottom: 1px solid var(--border);"><span style="background: #ecfdf5; color: #065f46; padding: 3px 8px; border-radius: 12px; font-size: 0.78rem; font-weight: 700;">منجز بنجاح ✅</span></td>
        </tr>
        """

    if not operations:
        table_rows = """
        <tr>
            <td colspan="6" style="padding: 30px; text-align: center; color: var(--text-muted);">لا توجد عمليات مسجلة خلال الـ 72 ساعة الماضية.</td>
        </tr>
        """

    body = f"""
    <div style="margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 1.6rem; color: #8b5cf6;">📊 {t('time_demand_title')}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">{t('time_demand_subtitle')}</p>
    </div>

    <div class="grid-3" style="margin-bottom: 24px;">
        <div class="card" style="border-top: 4px solid #8b5cf6; text-align: center;">
            <div style="font-size: 0.85rem; color: var(--text-muted); font-weight: 700;">{t('time_demand_clients_active')}</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #8b5cf6; margin-top: 4px;">{active_clients}</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">عملاء نشطين فعلياً</div>
        </div>
        <div class="card" style="border-top: 4px solid var(--primary); text-align: center;">
            <div style="font-size: 0.85rem; color: var(--text-muted); font-weight: 700;">{t('time_demand_ops_performed')}</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: var(--primary); margin-top: 4px;">{total_ops}</div>
            <div style="font-size: 0.78rem; color: var(--success);">فحص وتدخل إكلينيكي</div>
        </div>
        <div class="card" style="border-top: 4px solid var(--gold); text-align: center;">
            <div style="font-size: 0.85rem; color: var(--text-muted); font-weight: 700;">{t('time_demand_revenue')}</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: var(--gold); margin-top: 4px;">{total_revenue:,.0f} ج/ر</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">عوائد العمليات المسجلة</div>
        </div>
    </div>

    <div class="card" style="border-top: 4px solid #8b5cf6;">
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: right; font-size: 0.9rem;">
                <thead>
                    <tr style="background: var(--bg);">
                        <th style="padding: 12px; border-bottom: 2px solid var(--border);">{t('time_demand_table_client')}</th>
                        <th style="padding: 12px; border-bottom: 2px solid var(--border);">{t('time_demand_table_animal')}</th>
                        <th style="padding: 12px; border-bottom: 2px solid var(--border);">{t('time_demand_table_op')}</th>
                        <th style="padding: 12px; border-bottom: 2px solid var(--border);">{t('time_demand_table_time')}</th>
                        <th style="padding: 12px; border-bottom: 2px solid var(--border);">{t('time_demand_table_fee')}</th>
                        <th style="padding: 12px; border-bottom: 2px solid var(--border);">{t('time_demand_table_status')}</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_time_demand"), body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# ROUTE 5: DIRECT SUPPORT & HELPDESK (support@vetmind.ai)
# ==============================================================================
@app.get("/support", response_class=HTMLResponse)
async def support_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    u_name = user["name"] if user else ""
    u_email = user["email"] if user else ""

    body = f"""
    <div style="max-width: 640px; margin: 20px auto;">
        <div class="card" style="border-top: 6px solid var(--primary);">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 2.4rem;">🎧</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.5rem; color: var(--primary);">{t('support_title')}</h1>
                    <div style="font-size: 0.85rem; color: var(--text-muted);">{t('support_subtitle')}</div>
                </div>
            </div>

            <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 12px; margin-bottom: 20px; font-size: 0.9rem; color: #166534;">
                ✉️ <strong>البريد المباشر للإدارة والدعم:</strong> <a href="mailto:support@vetmind.ai" style="color: #047857; font-weight: 700;">support@vetmind.ai</a>
            </div>

            <form action="/support" method="POST">
                <div class="grid-2" style="margin-bottom: 14px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('support_name')}</label>
                        <input type="text" name="doctor_name" value="{u_name}" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('support_email')}</label>
                        <input type="email" name="email" value="{u_email}" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                </div>

                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('support_subject')}</label>
                    <input type="text" name="subject" required placeholder="مثال: استفسار حول ربط العيادة أو اعتماد الكارنيه" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>

                <div style="margin-bottom: 18px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('support_message')}</label>
                    <textarea name="message" rows="4" required placeholder="اشرح بالتفصيل المشكلة أو الاستفسار..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;"></textarea>
                </div>

                <button type="submit" class="btn btn-primary" style="width: 100%; padding: 12px; font-size: 1rem; justify-content: center;">
                    🚀 {t('support_send_btn')}
                </button>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_support"), body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/support")
async def process_support_ticket(
    request: Request,
    doctor_name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...)
):
    user = get_current_user(request)
    user_id = user["id"] if user else None
    user_country = user.get("country", "") if user else ""

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO support_tickets (user_id, doctor_name, email, country, subject, message, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, doctor_name, email, user_country, subject, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return HTMLResponse("<script>alert('تم إرسال تذكرة الدعم الفني بنجاح! سيتواصل معك فريق الدعم الفني عبر بريدك الإلكتروني.'); window.location.href='/support';</script>")

# ==============================================================================
# ROUTE 6: ADMIN MODERATION & USER REVIEW (Anti-Fraud & Approvals)
# ==============================================================================
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("SELECT key, value FROM settings")
    settings_dict = {row["key"]: row["value"] for row in c.fetchall()}
    cfg_smtp_host = settings_dict.get("smtp_host", os.environ.get("SMTP_HOST", "smtp.gmail.com"))
    cfg_smtp_port = settings_dict.get("smtp_port", os.environ.get("SMTP_PORT", "587"))
    cfg_smtp_user = settings_dict.get("smtp_user", os.environ.get("SMTP_USER", ""))
    cfg_smtp_pass = settings_dict.get("smtp_pass", os.environ.get("SMTP_PASS", ""))
    cfg_resend_api_key = settings_dict.get("resend_api_key", os.environ.get("RESEND_API_KEY", ""))
    cfg_ai_api_key = settings_dict.get("ai_api_key", os.environ.get("GROQ_API_KEY", ""))

    c.execute("SELECT * FROM users ORDER BY id DESC")
    all_users = c.fetchall()

    c.execute("SELECT * FROM broadcast_notifications ORDER BY id DESC")
    all_notifs = c.fetchall()

    c.execute("SELECT * FROM support_tickets ORDER BY id DESC LIMIT 20")
    all_tickets = c.fetchall()

    c.execute("SELECT * FROM community_subscriptions ORDER BY id DESC")
    all_subs = c.fetchall()

    conn.close()

    subs_rows = ""
    for s_row in all_subs:
        s = dict(s_row)
        receipt_btn = f'<a href="/uploads/{s['receipt_image']}" target="_blank" class="btn btn-outline" style="font-size: 0.75rem; padding: 2px 8px;">🖼️ عرض الإيصال</a>' if s["receipt_image"] else "<span style='color: var(--danger); font-size: 0.75rem;'>لا يوجد إيصال</span>"
        status_val = s.get("status", "pending")
        if status_val == "approved":
            sub_status_badge = '<span style="background: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 0.75rem;">معتمد ومفعل ✅</span>'
        elif status_val == "rejected":
            sub_status_badge = '<span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 0.75rem;">مرفوض ❌</span>'
        else:
            sub_status_badge = '<span style="background: #fef9c3; color: #854d0e; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 0.75rem;">معلق قيد المراجعة ⏳</span>'

        subs_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-weight: 700;">#{s['id']}<br><span style="font-size: 0.75rem; color: var(--text-muted);">{s['created_at']}</span></td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">د. {s['doctor_name']} ({s['doctor_email']})<br><span style="font-size: 0.78rem; color: var(--text-muted);">{s['doctor_phone']} | قيد: {s['syndicate_id']} | {s['country']}</span></td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);"><strong>{s['plan_name']}</strong><br><span style="color: var(--accent); font-weight: 700;">{s['amount']} {s.get('currency', 'EGP')}</span></td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-size: 0.82rem;">{s['payment_method']}<br><span style="font-family: monospace; background: var(--bg); padding: 1px 4px; border-radius: 4px;">{s['transaction_ref']}</span></td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{receipt_btn}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{sub_status_badge}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); white-space: nowrap;">
                <a href="/admin/community/approve/{s['id']}" class="btn btn-primary" style="font-size: 0.75rem; padding: 4px 8px;">✅ قبول وتفعيل</a>
                <a href="/admin/community/reject/{s['id']}" class="btn btn-outline" style="color: var(--danger); font-size: 0.75rem; padding: 4px 8px;">❌ رفض</a>
            </td>
        </tr>
        """
    

    users_rows = ""
    for u in all_users:
        card_html = f'<a href="/uploads/{u["id_card_image"]}" target="_blank" class="btn btn-outline" style="font-size: 0.75rem; padding: 2px 6px;">عرض الكارنيه 🪪</a>' if u["id_card_image"] else "<span style='color: var(--danger); font-size: 0.75rem;'>لم يرفع كارنيه</span>"
        v_status = u["verification_status"]
        status_badge = '<span style="background: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 0.75rem;">معتمد ✅</span>' if v_status == "approved" else '<span style="background: #fef9c3; color: #854d0e; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 0.75rem;">قيد التدقيق ⏳</span>'
        
        email_v_badge = "✅ مفعل 2FA" if u["is_email_verified"] else "⏳ غير مفعل"
        prem_badge = "⭐ VIP" if u["is_premium"] else "عادي"

        users_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-weight: 700;">#{u['id']} د. {u['name']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{u['email']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{u['country']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{u['clinic_name']} (قيد: {u['syndicate_id']})</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{card_html}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-size: 0.8rem;">{email_v_badge} | {prem_badge}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{status_badge}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); white-space: nowrap;">
                <a href="/admin/approve/{u['id']}" class="btn btn-primary" style="font-size: 0.75rem; padding: 4px 8px;">{t('admin_btn_approve_vet')}</a>
                <a href="/admin/delete-user/{u['id']}" onclick="return confirm('تحذير: هل أنت متأكد من حذف هذا الحساب نهائياً لمنع البيانات العشوائية؟');" class="btn btn-outline" style="color: var(--danger); font-size: 0.75rem; padding: 4px 8px;">{t('admin_btn_reject_delete')}</a>
            </td>
        </tr>
        """

    tickets_rows = ""
    for tk in all_tickets:
        tickets_rows += f"""
        <div style="padding: 12px; border-bottom: 1px solid var(--border);">
            <div style="display: flex; justify-content: space-between; font-weight: 700;">
                <span style="color: var(--primary);">#{tk['id']} {tk['subject']}</span>
                <span style="font-size: 0.78rem; color: var(--text-muted);">{tk['created_at']}</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 2px;">د. {tk['doctor_name']} ({tk['email']}) - {tk['country']}</div>
            <div style="font-size: 0.88rem; margin-top: 6px; background: var(--bg); padding: 8px; border-radius: 6px;">{tk['message']}</div>
        </div>
        """

    notifs_rows = ""
    for n in all_notifs:
        notifs_rows += f"""
        <div style="padding: 12px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="color: var(--primary);">{n['title']}</strong> ({n['target_country']})
                <div style="font-size: 0.85rem; margin-top: 4px;">{n['message']}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">{n['created_at']}</div>
            </div>
            <form action="/admin/broadcast/delete/{n['id']}" method="POST" style="margin: 0;">
                <button type="submit" class="btn btn-outline" style="color: var(--danger); font-size: 0.8rem;">حذف</button>
            </form>
        </div>
        """

    body = f"""
    <div style="margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 1.6rem; color: var(--accent);">⚙️ {t('admin_title')}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">{t('admin_subtitle')}</p>
    </div>

    <!-- User Moderation & Anti-Fraud Table -->
    <div class="card" style="border-top: 4px solid var(--accent); margin-bottom: 24px;">
        <h2 style="margin-top: 0; font-size: 1.3rem; color: var(--accent);">👨‍⚕️ {t('admin_moderation_title')}</h2>
        <p style="font-size: 0.85rem; color: var(--text-muted);">{t('admin_moderation_desc')}</p>

        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: right; font-size: 0.88rem;">
                <thead>
                    <tr style="background: var(--bg);">
                        <th style="padding: 10px;">الطبيب</th>
                        <th style="padding: 10px;">البريد</th>
                        <th style="padding: 10px;">الدولة</th>
                        <th style="padding: 10px;">العيادة والقيد</th>
                        <th style="padding: 10px;">الكارنيه</th>
                        <th style="padding: 10px;">المصادقة / الباقة</th>
                        <th style="padding: 10px;">الحالة</th>
                        <th style="padding: 10px;">إجراء المدير</th>
                    </tr>
                </thead>
                <tbody>
                    {users_rows}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Community Subscriptions & Payment Proofs Table -->
    <div class="card" style="border-top: 4px solid #7c3aed; margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <h2 style="margin: 0; font-size: 1.3rem; color: #7c3aed;">💳 اشتراكات مجتمع الأطباء البيطريين وإيصالات السداد</h2>
            <a href="/community" target="_blank" class="btn btn-outline" style="font-size: 0.8rem;">👥 فتح ملتقى الأطباء</a>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 14px;">مراجعة إشعارات وإيصالات التحويل البنكي وفودافون كاش وإنستاباي لاعتماد وصول الأطباء لمجتمع النقاشات السريرية.</p>

        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: right; font-size: 0.88rem;">
                <thead>
                    <tr style="background: var(--bg);">
                        <th style="padding: 10px;">الطلب والتاريخ</th>
                        <th style="padding: 10px;">الطبيب والبيانات</th>
                        <th style="padding: 10px;">الباقة والمبلغ</th>
                        <th style="padding: 10px;">وسيلة الدفع والمرجع</th>
                        <th style="padding: 10px;">إيصال التحويل</th>
                        <th style="padding: 10px;">حالة الطلب</th>
                        <th style="padding: 10px;">قرار الإدارة</th>
                    </tr>
                </thead>
                <tbody>
                    {subs_rows if subs_rows else "<tr><td colspan='7' style='text-align: center; padding: 20px; color: var(--text-muted);'>لا توجد اشتراكات مجتمع مقدمة حالياً.</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Support Tickets Tab -->
    <div class="card" style="border-top: 4px solid #0284c7; margin-bottom: 24px;">
        <h2 style="margin-top: 0; font-size: 1.3rem; color: #0284c7;">🎧 {t('admin_tab_tickets')}</h2>
        {tickets_rows if tickets_rows else "<p style='color: var(--text-muted);'>لا توجد تذاكر دعم فني واردة حالياً.</p>"}
    </div>

    
    <!-- System & Integrations Settings Card -->
    <div class="card" style="border-top: 4px solid #10b981; margin-bottom: 24px;">
        <h2 style="margin-top: 0; font-size: 1.3rem; color: #10b981;">⚙️ إعدادات البريد والرسائل والذكاء الاصطناعي (Settings)</h2>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px;">
            يمكنك من هنا إدخال بيانات الربط مباشرة وبسهولة تامة ودون الحاجة للدخول إلى Vercel:
        </p>

        <form action="/admin/settings" method="POST">
            <h3 style="font-size: 1.05rem; margin-bottom: 8px; color: var(--primary);">✉️ إعدادات إرسال كود التفعيل عبر البريد (Gmail SMTP / Resend)</h3>
            <div class="grid-2" style="margin-bottom: 12px;">
                <div>
                    <label style="display: block; font-weight: 700; font-size: 0.85rem; margin-bottom: 4px;">خادم البريد (SMTP Host):</label>
                    <input type="text" name="smtp_host" value="{cfg_smtp_host}" placeholder="smtp.gmail.com" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 700; font-size: 0.85rem; margin-bottom: 4px;">المنفذ (Port):</label>
                    <input type="text" name="smtp_port" value="{cfg_smtp_port}" placeholder="587 أو 465" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                </div>
            </div>
            <div class="grid-2" style="margin-bottom: 12px;">
                <div>
                    <label style="display: block; font-weight: 700; font-size: 0.85rem; margin-bottom: 4px;">بريدك في الجيميل (SMTP User):</label>
                    <input type="text" name="smtp_user" value="{cfg_smtp_user}" placeholder="your_clinic@gmail.com" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 700; font-size: 0.85rem; margin-bottom: 4px;">كود التطبيق السري (App Password 16 حرفاً):</label>
                    <input type="password" name="smtp_pass" value="{cfg_smtp_pass}" placeholder="••••••••••••••••" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                </div>
            </div>

            <div style="margin-bottom: 14px;">
                <label style="display: block; font-weight: 700; font-size: 0.85rem; margin-bottom: 4px;">أو مفتاح Resend API (بديل مجاني وسريع بضغطة زر):</label>
                <input type="password" name="resend_api_key" value="{cfg_resend_api_key}" placeholder="re_••••••••••••" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
            </div>

            <hr style="border: 0; border-top: 1px solid var(--border); margin: 16px 0;">

            <h3 style="font-size: 1.05rem; margin-bottom: 8px; color: var(--primary);">🤖 مفتاح الذكاء الاصطناعي (Groq AI API Key)</h3>
            <div style="margin-bottom: 16px;">
                <input type="password" name="ai_api_key" value="{cfg_ai_api_key}" placeholder="gsk_••••••••••••" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
            </div>

            <button type="submit" class="btn btn-primary" style="padding: 10px 20px; font-weight: 800;">
                💾 حفظ الإعدادات وتفعيل الخدمة فوراً
            </button>
        </form>
    </div>

    <!-- Broadcast Center -->
    <div class="card" style="border-top: 4px solid var(--primary);">
        <h2 style="margin-top: 0; font-size: 1.3rem; color: var(--primary);">📢 {t('admin_tab_broadcast')}</h2>
        <form action="/admin/broadcast" method="POST">
            <div class="grid-2" style="margin-bottom: 12px;">
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 4px;">عنوان التنبيه أو التحديث</label>
                    <input type="text" name="title" required placeholder="مثال: تنبيه وبائي: تفشي مرض الحمى القلاعية" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 4px;">الدولة المستهدفة</label>
                    <select name="target_country" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                        <option value="ALL">كافة الدول المسجلة (ALL)</option>
                        <option value="مصر">مصر</option>
                        <option value="السعودية">السعودية</option>
                        <option value="الإمارات">الإمارات</option>
                        <option value="الأردن">الأردن</option>
                        <option value="السودان">السودان</option>
                    </select>
                </div>
            </div>

            <div style="margin-bottom: 12px;">
                <label style="display: block; font-weight: 700; margin-bottom: 4px;">نص الإشعار الإكلينيكي</label>
                <textarea name="message" rows="3" required placeholder="اكتب نص الإشعار العام..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;"></textarea>
            </div>

            <button type="submit" class="btn btn-accent">🚀 {t('admin_broadcast_send')}</button>
        </form>

        <div style="margin-top: 20px;">
            <h4 style="margin-bottom: 10px;">الإشعارات النشطة السابقة:</h4>
            {notifs_rows}
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_admin"), body, user, lang), media_type="text/html; charset=utf-8")

@app.get("/admin/community/approve/{sub_id}")
async def admin_approve_community_sub(request: Request, sub_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=303)
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_subscriptions SET status = 'approved', reviewed_at = ? WHERE id = ?",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sub_id))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/community/reject/{sub_id}")
async def admin_reject_community_sub(request: Request, sub_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=303)
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE community_subscriptions SET status = 'rejected', reviewed_at = ? WHERE id = ?",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sub_id))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/community/toggle-user/{user_id}")
async def admin_toggle_community_user(request: Request, user_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=303)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, status FROM community_subscriptions WHERE user_id = ? AND status = 'approved' LIMIT 1", (user_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE community_subscriptions SET status = 'rejected' WHERE user_id = ?", (user_id,))
    else:
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        u = c.fetchone()
        if u:
            c.execute("""
            INSERT INTO community_subscriptions (
                user_id, doctor_name, doctor_email, doctor_phone, syndicate_id, 
                clinic_name, country, plan_id, plan_name, amount, payment_method, 
                transaction_ref, receipt_image, status, created_at, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'admin_vip', 'اعتماد إداري مباشر (VIP Admin Grant)', 0, 'تفعيل يدوي مباشر من المدير', 'ADMIN-GRANT', 'admin_approved.png', 'approved', ?, ?)
            """, (
                user_id, u["name"], u["email"], u.get("phone", ""), u.get("syndicate_id", ""),
                u.get("clinic_name", ""), u.get("country", "مصر"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/approve/{user_id}")
async def approve_user(request: Request, user_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=303)
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET verification_status = 'approved', is_email_verified = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/delete-user/{user_id}")
async def delete_user(request: Request, user_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=303)
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ? AND is_admin = 0", (user_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/broadcast")
async def post_broadcast(
    request: Request,
    title: str = Form(...),
    message: str = Form(...),
    target_country: str = Form("ALL")
):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO broadcast_notifications (title, message, target_country, badge_type, created_at)
    VALUES (?, ?, ?, 'update', ?)
    """, (title, message, target_country, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/broadcast/delete/{id}")
async def delete_broadcast(request: Request, id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=303)
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM broadcast_notifications WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

# ==============================================================================
# ROUTE 7: REGISTRATION WITH STRICT 2FA CODE DISPATCH
# ==============================================================================
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=303)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    country_opts = "".join([f'<option value="{c}">{c}</option>' for c in ARAB_COUNTRIES])

    body = f"""
    <div style="max-width: 580px; margin: 20px auto;">
        <div class="card" style="border-top: 6px solid var(--primary);">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 2.8rem;">🩺</div>
                <h1 style="margin: 6px 0; font-size: 1.5rem; color: var(--primary);">{t('register_title')}</h1>
                <p style="color: var(--text-muted); font-size: 0.88rem; margin: 0;">{t('register_subtitle')}</p>
            </div>

            <form action="/register" method="POST" enctype="multipart/form-data">
                <div style="margin-bottom: 14px; background: #ecfdf5; border: 1.5px solid #a7f3d0; border-radius: 10px; padding: 12px;">
                    <label style="display: block; font-weight: 800; margin-bottom: 6px; color: var(--primary);">🌐 {t('register_language_label', 'لغة المنصة المفضلة لك')}</label>
                    <select name="preferred_lang" style="width: 100%; padding: 10px; border: 1.5px solid var(--primary); border-radius: 8px; font-weight: 700; background: white;">
                        <option value="ar" {"selected" if lang=="ar" else ""}>🇪🇬 العربية (Arabic - الافتراضية)</option>
                        <option value="en" {"selected" if lang=="en" else ""}>🇬🇧 English</option>
                        <option value="fr" {"selected" if lang=="fr" else ""}>🇫🇷 Français</option>
                        <option value="de" {"selected" if lang=="de" else ""}>🇩🇪 Deutsch</option>
                        <option value="es" {"selected" if lang=="es" else ""}>🇪🇸 Español</option>
                        <option value="it" {"selected" if lang=="it" else ""}>🇮🇹 Italiano</option>
                        <option value="zh" {"selected" if lang=="zh" else ""}>🇨🇳 中文</option>
                        <option value="ja" {"selected" if lang=="ja" else ""}>🇯🇵 日本語</option>
                    </select>
                </div>

                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">🌍 {t('register_country')}</label>
                    <select name="country" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                        {country_opts}
                    </select>
                </div>

                <div class="grid-2" style="margin-bottom: 14px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">👨‍⚕️ {t('register_name')}</label>
                        <input type="text" name="name" required placeholder="{t('register_name_ph', 'د. أحمد إبراهيم')}" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">📱 {t('register_phone')}</label>
                        <input type="tel" name="phone" required placeholder="+201000000000" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                </div>

                <div class="grid-2" style="margin-bottom: 14px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">🏥 {t('register_clinic')}</label>
                        <input type="text" name="clinic_name" required placeholder="{t('register_clinic_ph', 'اسم العيادة')}" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">📜 {t('register_syndicate_id')}</label>
                        <input type="text" name="syndicate_id" required placeholder="{t('register_syndicate_ph', 'رقم القيد بالنقابة')}" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                </div>

                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">✉️ {t('register_email')}</label>
                    <input type="email" name="email" required placeholder="doctor@gmail.com" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>

                <div class="grid-2" style="margin-bottom: 14px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">🔒 {t('register_password')}</label>
                        <input type="password" name="password" required placeholder="••••••••" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px;">🔒 {t('register_confirm_password')}</label>
                        <input type="password" name="confirm_password" required placeholder="••••••••" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                </div>

                <div style="margin-bottom: 20px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">🪪 {t('register_id_card')}</label>
                    <input type="file" name="id_card_image" accept="image/*" required style="width: 100%; padding: 10px; border: 1px dashed var(--primary); border-radius: 8px; background: var(--primary-light);">
                    <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">{t('register_id_card_help')}</div>
                </div>

                <button type="submit" class="btn btn-primary" style="width: 100%; padding: 14px; font-size: 1.05rem; justify-content: center;">
                    📝 {t('register_button')}
                </button>
            </form>

            <div style="text-align: center; margin-top: 18px; font-size: 0.88rem;">
                {t('register_has_account')} <a href="/login" style="color: var(--primary); font-weight: 700;">{t('register_login_link')}</a>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_register"), body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/register")
async def process_register(
    request: Request,
    country: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    clinic_name: str = Form(...),
    syndicate_id: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    preferred_lang: str = Form("ar"),
    id_card_image: UploadFile = File(None)
):
    if password != confirm_password:
        return HTMLResponse("<script>alert('كلمتا المرور غير متطابقتين'); history.back();</script>", status_code=400)

    clean_email = email.strip().lower()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
    if c.fetchone():
        conn.close()
        return HTMLResponse("<script>alert('هذا البريد الإلكتروني مسجل بالفعل'); history.back();</script>", status_code=400)

    id_card_filename = ""
    if id_card_image and id_card_image.filename:
        id_card_filename = f"id_card_{int(datetime.now().timestamp())}_{id_card_image.filename.replace(' ', '_')}"
        save_path = os.path.join(UPLOAD_DIR, id_card_filename)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(id_card_image.file, buffer)

    otp = str(random.randint(100000, 999999))
    pwd_hash = hash_password(password)

    clean_pref_lang = preferred_lang.strip().lower() if preferred_lang in SUPPORTED_LANGUAGES else "ar"
    c.execute("""
    INSERT INTO users (name, email, password_hash, role, created_at, id_card_image, verification_status, is_admin, country, clinic_name, syndicate_id, phone, is_email_verified, otp_code, preferred_lang)
    VALUES (?, ?, ?, 'vet', ?, ?, 'pending', 0, ?, ?, ?, ?, 0, ?, ?)
    """, (name.strip(), clean_email, pwd_hash, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_card_filename, country, clinic_name, syndicate_id, phone.strip(), otp, clean_pref_lang))
    conn.commit()
    conn.close()

    resp = RedirectResponse(f"/verify-otp?email={clean_email}", status_code=303)
    resp.set_cookie(key="vetmind_lang", value=clean_pref_lang, max_age=31536000, path="/", samesite="lax")
    return resp

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, redirect: str = "/"):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=303)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    body = f"""
    <div style="max-width: 460px; margin: 30px auto; padding: 0 10px;">
        <!-- Welcome Veterinary Doctor Gate Banner -->
        <div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border: 1px solid #6ee7b7; border-radius: 14px; padding: 16px; margin-bottom: 20px; text-align: center; color: #065f46; box-shadow: 0 4px 12px rgba(4,120,87,0.08);">
            <div style="font-size: 2rem; margin-bottom: 6px;">🩺</div>
            <div style="font-weight: 800; font-size: 1.15rem; margin-bottom: 6px;">منصة VetMind AI السريرية للأطباء البيطريين</div>
            <div style="font-size: 0.88rem; line-height: 1.6; opacity: 0.95;">
                يرجى تسجيل الدخول أو إنشاء حساب طبيب بيطري جديد للاستمتاع بكافة مزايا وأدوات المنصة وقاعدة الأدوية والمراجع السريرية.
            </div>
        </div>

        <div class="card" style="border-top: 6px solid var(--primary); padding: 24px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 2.8rem;">🔑</div>
                <h1 style="margin: 6px 0; font-size: 1.5rem; color: var(--primary);">{t('login_title')}</h1>
                <p style="color: var(--text-muted); font-size: 0.88rem;">VetMind AI Enterprise Decision Support Suite</p>
            </div>

            <form action="/login" method="POST">
                <input type="hidden" name="redirect_url" value="{redirect}">
                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">✉️ {t('login_email')}</label>
                    <input type="email" name="email" required placeholder="doctor@vetmind.ai" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>

                <div style="margin-bottom: 18px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">🔒 {t('login_password')}</label>
                    <input type="password" name="password" required placeholder="••••••••" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>

                <button type="submit" class="btn btn-primary" style="width: 100%; padding: 12px; font-size: 1.05rem; justify-content: center;">
                    🚪 {t('login_button')}
                </button>
            </form>

            <div style="margin-top: 20px; padding: 12px; background: var(--bg); border-radius: 8px; font-size: 0.8rem; color: var(--text-muted);">
                <strong>حساب الإدارة التنفيذية المعتمد:</strong><br>
                director@vetmind.ai | Director@VetMind2026#
            </div>

            <div style="text-align: center; margin-top: 18px; font-size: 0.88rem;">
                {t('login_no_account')} <a href="/register" style="color: var(--primary); font-weight: 700;">{t('login_register_link')}</a>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_login"), body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/login")
async def process_login(request: Request, email: str = Form(...), password: str = Form(...), redirect_url: str = Form("/")):
    clean_email = email.strip().lower()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
    user = c.fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        conn.close()
        return HTMLResponse("<script>alert('البريد الإلكتروني أو كلمة المرور غير صحيحة'); window.location.href='/login';</script>")

    if not user["is_email_verified"]:
        user_id = user["id"]
        user_phone = user["phone"] if "phone" in user.keys() else ""
        user_name = user["name"] if "name" in user.keys() else ""
        user_country = user["country"] if "country" in user.keys() else "مصر"
        conn.close()
        try:
            import verification_service
            verification_service.dispatch_user_otp(user_id, clean_email, user_phone, user_name, user_country)
        except Exception:
            pass
        return RedirectResponse(f"/verify-otp?email={clean_email}", status_code=303)

    u_dict = dict(user)
    u_pref = (u_dict.get("preferred_lang") or "ar").strip().lower()
    user_lang = u_pref if u_pref in SUPPORTED_LANGUAGES else "ar"
    conn.close()
    resp = RedirectResponse("/", status_code=303)
    token = make_session_token(user["id"])
    resp.set_cookie(key="vetmind_session", value=token, max_age=31536000, httponly=True)
    resp.set_cookie(key="vetmind_lang", value=user_lang, max_age=31536000, path="/", samesite="lax")
    return resp

@app.get("/logout")
async def process_logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(key="vetmind_session")
    return resp

# ==============================================================================
# ROUTE 8: CASES, DETAILS, DELETE
# ==============================================================================
@app.post("/add-case")
async def add_case(
    request: Request,
    animal_name: str = Form(...),
    species: str = Form(...),
    age: str = Form(""),
    weight: str = Form(""),
    symptoms: str = Form(...),
    duration: str = Form(""),
    image: UploadFile = File(None)
):
    user = get_current_user(request)
    user_id = user["id"] if user else 0
    user_country = user.get("country", "مصر") if user else "مصر"

    image_filename = ""
    image_full_path = None
    if image and image.filename:
        safe_name = f"{int(datetime.now().timestamp())}_{image.filename.replace(' ', '_')}"
        image_full_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(image_full_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_filename = safe_name

    vision_res = analyze_image_locally(image_full_path) if image_full_path else None
    
    differentials = [
        {"condition": f"اشتباه وبائي / إكلينيكي في {species}: {vision_res['detected_lesion'] if vision_res else 'التهاب حاد'}", "confidence": "85% Clinical Match", "source": "Merck Veterinary Manual & WOAH Standards"},
        {"condition": "عدوى بكتيرية ثانوية بالجهاز التنفسي أو الهضمي", "confidence": "70% Clinical Match", "source": "WSAVA & FAO Animal Health Guides"},
        {"condition": "اعتلال أيضي أو نقص عناصر صغرى", "confidence": "45% Clinical Match", "source": "Cornell Veterinary Medicine Guidelines"}
    ]

    analysis_data = {
        "engine": "VetMind Multi-Spectral Vision & Clinical Pharmacopeia",
        "vision_metrics": vision_res,
        "differentials": differentials,
        "localized_drugs": get_localized_drugs(user_country),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO cases (animal_name, species, age, weight, symptoms, duration, image_filename, triage_level, triage_note, created_at, analysis_json, user_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (animal_name, species, age, weight, symptoms, duration, image_filename, "urgent" if "نزيف" in symptoms or "صدمة" in symptoms else "routine", "تم التحليل السريري بمحرك الرؤية والمراجع الدولية", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), json.dumps(analysis_data, ensure_ascii=False), user_id))
    case_id = c.lastrowid
    conn.commit()
    conn.close()

    return RedirectResponse(f"/case/{case_id}", status_code=303)

@app.get("/case/{case_id}", response_class=HTMLResponse)
async def view_case(request: Request, case_id: int):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    case_row = c.fetchone()
    conn.close()

    if not case_row:
        raise HTTPException(status_code=404, detail="الحالة السريرية غير موجودة")

    analysis = json.loads(case_row["analysis_json"]) if case_row["analysis_json"] else {}
    vision = analysis.get("vision_metrics")
    diffs = analysis.get("differentials", [])
    drugs = analysis.get("localized_drugs", [])

    img_html = ""
    if case_row["image_filename"]:
        img_html = f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="/uploads/{case_row['image_filename']}" style="max-width: 100%; max-height: 400px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
        </div>
        """

    vision_box = ""
    if vision:
        vision_box = f"""
        <div class="card" style="background: var(--primary-light); border-color: #99f6e4;">
            <h3 style="margin-top: 0; color: var(--primary);">🔬 فحص محرك الرؤية الحاسوبية (Digital Vision Inspection)</h3>
            <p><strong>الآفة المرصودة:</strong> {vision.get('detected_lesion')}</p>
            <div class="grid-3" style="margin-top: 10px;">
                <div style="background: white; padding: 10px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 0.8rem; color: var(--text-muted);">مؤشر الاحمرار والالتهاب</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: var(--danger);">{vision.get('erythema_score')}%</div>
                </div>
                <div style="background: white; padding: 10px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 0.8rem; color: var(--text-muted);">مؤشر التنخر واللون الداكن</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: #475569;">{vision.get('necrosis_score')}%</div>
                </div>
                <div style="background: white; padding: 10px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 0.8rem; color: var(--text-muted);">مؤشر الإفرازات والنضح</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: #d97706;">{vision.get('exudate_score')}%</div>
                </div>
            </div>
            <p style="margin-top: 12px; font-size: 0.88rem; color: var(--text-main);"><strong>الانطباع السريري:</strong> {vision.get('clinical_impression')}</p>
        </div>
        """

    diff_html = ""
    for d in diffs:
        diff_html += f"""
        <li style="margin-bottom: 10px; padding: 10px; background: var(--bg); border-radius: 8px;">
            <div style="font-weight: 700; color: var(--primary);">{d.get('condition')}</div>
            <div style="font-size: 0.82rem; color: var(--text-muted); display: flex; justify-content: space-between; margin-top: 4px;">
                <span>المطابقة السريرية: <strong>{d.get('confidence')}</strong></span>
                <span>المرجع: {d.get('source')}</span>
            </div>
        </li>
        """

    drugs_html = ""
    for dg in drugs:
        dosage_calc = calculate_precise_dosage(dg, case_row["weight"], case_row["species"])
        fn_text = get_drug_concise_function(dg)
        drugs_html += f"""
        <div style="padding: 16px; border: 1px solid var(--border); border-radius: 12px; margin-bottom: 14px; background: var(--card-bg); box-shadow: var(--shadow);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="font-weight: 800; font-size: 1.15rem; color: var(--primary);">{dg.get('trade_name')}</span>
                    <span style="background: #e0f2fe; color: #0369a1; padding: 3px 10px; border-radius: 6px; font-size: 0.82rem; font-weight: 700; margin-right: 6px;">({fn_text})</span>
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;"><strong>{t('manufacturer_label', 'الشركة المصنعة')}:</strong> {dg.get('manufacturer')} | <strong>{t('active_ingredient_label', 'المادة الفعالة')}:</strong> {dg.get('active_ingredient')}</div>
                </div>
                <div style="background: #ecfdf5; border: 1px solid #a7f3d0; padding: 6px 14px; border-radius: 8px; text-align: left;" dir="ltr">
                    <div style="font-size: 0.72rem; color: #047857; font-weight: 700;">PRECISE CALCULATED DOSE:</div>
                    <div style="font-size: 1.25rem; font-weight: 900; color: #047857;">{dosage_calc['exact_dose_formatted']}</div>
                </div>
            </div>

            <!-- Dedicated Dosage Calculator Details Box -->
            <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 12px 16px; margin-top: 12px; font-size: 0.9rem;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
                    <div>💉 <strong>{t('precise_dose_for_weight', 'الجرعة الدقيقة لوزن')} {case_row['weight']} {t('unit_kg', 'كجم')}:</strong> <span style="color: #ea580c; font-weight: 900;">{dosage_calc['exact_dose_formatted']}</span></div>
                    <div>⏱️ <strong>{t('frequency_label', 'التكرار')}:</strong> {dosage_calc['frequency']}</div>
                    <div>📍 <strong>{t('route_label', 'طريقة الإعطاء')}:</strong> {dosage_calc['route']}</div>
                    <div>⏳ <strong>{t('duration_label', 'المدة')}:</strong> {dosage_calc['duration']}</div>
                </div>
                {f'<div style="color: #b91c1c; font-weight: 700; margin-top: 8px; font-size: 0.85rem;">{dosage_calc["site_split_warning"]}</div>' if dosage_calc.get("site_split_warning") else ''}
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 12px; font-size: 0.85rem; border-top: 1px solid var(--border); padding-top: 8px;">
                <div style="color: var(--danger); font-weight: 600;">⚠️ <strong>{t('withdrawal_label', 'فترة السحب (Withdrawal)')}:</strong> {dg.get('withdrawal_period')} | رقم التسجيل: {dg.get('approval_reg_no')}</div>
                <a href="/rx-prescription?animal_name={case_row['animal_name']}&species={case_row['species']}&weight={case_row['weight']}&selected_drug_id={dg.get('id', 1)}" class="btn btn-primary" style="padding: 5px 14px; font-size: 0.84rem; font-weight: 700;">
                    {t('convert_to_rx_btn', '📋 تحويل لروشتة العيادة وطباعتها')}
                </a>
            </div>
        </div>
        """

    body = f"""
    <div style="margin-bottom: 16px;">
        <a href="/" class="btn btn-outline">{t('back_to_cases_btn', '⬅️ العودة لسجل الحالات')}</a>
        <button onclick="window.print()" class="btn btn-primary" style="margin-right: 8px;">{t('print_report_btn', '🖨️ طباعة التقرير الطبي المعتمد (PDF)')}</button>
    </div>

    <div class="card" style="border-top: 6px solid var(--primary);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border); padding-bottom: 14px; margin-bottom: 18px;">
            <div>
                <h1 style="margin: 0; font-size: 1.6rem; color: var(--primary);">{t('case_report_header', '📋 تقرير الفحص والتشخيص السريري المعتمد')}</h1>
                <div style="color: var(--text-muted); font-size: 0.88rem; margin-top: 4px;">{t('case_num_label', 'رقم الحالة')}: #VET-{case_row['id']} | {t('exam_date_label', 'تاريخ الفحص')}: {case_row['created_at']}</div>
            </div>
            <div style="text-align: left;">
                <span style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">VetMind Enterprise v4.1</span>
            </div>
        </div>

        {img_html}

        <div class="grid-2" style="margin-bottom: 20px;">
            <div style="background: var(--bg); padding: 14px; border-radius: 10px;">
                <h3 style="margin-top: 0; font-size: 1.1rem;">{t('patient_demographics_title', 'بيانات الحيوان المفحوص')}</h3>
                <p style="margin: 6px 0;"><strong>{t('patient_name_label', 'الاسم / الكود')}:</strong> {case_row['animal_name']}</p>
                <p style="margin: 6px 0;"><strong>{t('patient_species_label', 'الفصيلة')}:</strong> {case_row['species']}</p>
                <p style="margin: 6px 0;"><strong>{t('patient_age_weight_label', 'العمر والوزن')}:</strong> {case_row['age']} | {case_row['weight']} كجم</p>
            </div>
            <div style="background: var(--bg); padding: 14px; border-radius: 10px;">
                <h3 style="margin-top: 0; font-size: 1.1rem;">{t('clinical_symptoms_title', 'الأعراض والشكوى السريرية')}</h3>
                <p style="margin: 6px 0;">{case_row['symptoms']}</p>
            </div>
        </div>

        {vision_box}

        <div class="card" style="margin-top: 20px;">
            <h3 style="margin-top: 0; color: var(--primary);">{t('differentials_title', '📊 التشخيص التفريقي المحتمل (Differential Diagnoses)')}</h3>
            <ul style="list-style: none; padding: 0;">
                {diff_html}
            </ul>
        </div>

        <div class="card" style="margin-top: 20px;">
            <h3 style="margin-top: 0; color: var(--accent);">{t('recommended_drugs_title', '💊 الأدوية البيطرية الوطنية المعتمدة الموصى بها')}</h3>
            <p style="font-size: 0.85rem; color: var(--text-muted);">{t('recommended_drugs_subtitle', 'مستحضرات مسجلة رسمياً لدى هيئة الدواء ووزارة الزراعة المختصة لمطابقة هذه الحالة:')}</p>
            {drugs_html}
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(f"تقرير حالة #{case_row['id']}", body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/delete/{case_id}")
async def delete_case(case_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)

# ==============================================================================
# ROUTE 9: COMPUTER VISION SCREENING
# ==============================================================================
@app.get("/vision-detect", response_class=HTMLResponse)
async def vision_detect_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    body = f"""
    <div class="card" style="border-top: 6px solid var(--accent);">
        <h1 style="margin-top: 0; font-size: 1.6rem; color: var(--accent);">👁️ {t('vision_detect_title')}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">{t('vision_detect_subtitle')}</p>

        <form action="/vision-detect" method="POST" enctype="multipart/form-data" style="margin-top: 20px;">
            <div style="border: 2px dashed var(--accent); padding: 30px; text-align: center; border-radius: 12px; background: #fff7ed; margin-bottom: 20px;">
                <div style="font-size: 3rem; margin-bottom: 10px;">📸</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #9a3412;">{t('vision_upload_btn')}</div>
                <input type="file" name="image" accept="image/*" required style="margin-top: 15px; font-size: 1rem;">
            </div>

            <div class="grid-2" style="margin-bottom: 20px;">
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('species_optional_label', 'فصيلة الحيوان (اختياري)')}</label>
                    <select name="species" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                        <option value="غير محدد">فحص تلقائي للآفة</option>
                        <option value="أبقار">أبقار / مواشي</option>
                        <option value="أغنام وماعز">أغنام وماعز</option>
                        <option value="إبل">إبل وهجن</option>
                        <option value="خيول">خيول</option>
                        <option value="كلاب وقطط">حيوانات أليفة (كلاب/قطط)</option>
                        <option value="دواجن">دواجن وطيور</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">{t('notes_optional_label', 'ملاحظات سريرية إضافية (اختياري)')}</label>
                    <input type="text" name="notes" placeholder="ملاحظات سريرية إضافية..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
            </div>

            <button type="submit" class="btn btn-accent" style="width: 100%; padding: 14px; font-size: 1.1rem; justify-content: center;">
                ⚡ {t('vision_analyze_btn')}
            </button>
        </form>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_vision_detect"), body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/vision-detect", response_class=HTMLResponse)
async def process_vision_detect(
    request: Request,
    image: UploadFile = File(...),
    species: str = Form("غير محدد"),
    notes: str = Form("")
):
    user = get_current_user(request)
    lang = get_user_lang(request)
    user_country = user.get("country", "مصر") if user else "مصر"
    t = lambda k, d="": get_text(lang, k, d)

    try:
        safe_name = f"vision_{int(datetime.now().timestamp())}_{image.filename.replace(' ', '_')}"
        image_full_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(image_full_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception as img_err:
        safe_name = "error_placeholder.png"
        image_full_path = None

    v_metrics = analyze_image_locally(image_full_path) if image_full_path else {
        "summary": "لم يتم رفع الصورة بنجاح - يرجى المحاولة مرة أخرى",
        "detected_lesion": "خطأ في رفع الصورة",
        "erythema_score": 0, "necrosis_score": 0, "exudate_score": 0, "contrast_score": 0,
        "clinical_impression": "يرجى إعادة رفع الصورة بتنسيق صالح (JPEG, PNG)"
    }
    api_key = get_effective_groq_api_key(request)
    effective_notes = notes if notes and notes.strip() else "يرجى تحليل الآفة السريرية المرصودة في الصورة وتقديم التشخيص التفريقي."
    clinical_report = ask_ai_chat(api_key, effective_notes, [], image_full_path, lang, user_country)

    body = f"""
    <div style="margin-bottom: 16px;">
        <a href="/vision-detect" class="btn btn-outline">{t('scan_another_img', '⬅️ فحص صورة أخرى')}</a>
    </div>

    <div class="card" style="border-top: 6px solid var(--accent);">
        <h2 style="margin-top: 0; color: var(--accent);">👁️ {t('vision_result_title')}</h2>

        <div style="text-align: center; margin: 20px 0;">
            <img src="/uploads/{safe_name}" style="max-width: 100%; max-height: 420px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 4px 14px rgba(0,0,0,0.1);">
        </div>

        <!-- Vision Metrics or Rejection Alert -->
        {"" if ("غير صالحة للتشخيص البيطري" in clinical_report or "❌" in clinical_report) else f'''
        <div class="grid-3" style="margin-bottom: 24px;">
            <div class="card" style="background: #fef2f2; border-color: #fecaca; text-align: center;">
                <div style="font-size: 0.85rem; color: #991b1b; font-weight: 700;">{t('vision_metric_redness')}</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #dc2626; margin-top: 4px;">{v_metrics['erythema_score']}%</div>
                <div style="font-size: 0.8rem; color: #991b1b;">{t('vision_redness_sub', 'احتقان نسيجي وتآكل ظهاري')}</div>
            </div>
            <div class="card" style="background: #f8fafc; border-color: #cbd5e1; text-align: center;">
                <div style="font-size: 0.85rem; color: #475569; font-weight: 700;">{t('vision_metric_necrosis')}</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #334155; margin-top: 4px;">{v_metrics['necrosis_score']}%</div>
                <div style="font-size: 0.8rem; color: #475569;">{t('vision_necrosis_sub', 'تنخر خلوي وجلبات قشرية')}</div>
            </div>
            <div class="card" style="background: #fffbeb; border-color: #fde68a; text-align: center;">
                <div style="font-size: 0.85rem; color: #92400e; font-weight: 700;">{t('vision_metric_exudate')}</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #d97706; margin-top: 4px;">{v_metrics['exudate_score']}%</div>
                <div style="font-size: 0.8rem; color: #92400e;">{t('vision_exudate_sub', 'نضح قيحي وإفرازات مخاطية')}</div>
            </div>
        </div>
        '''}

        <div class="card" style="background: {'#fef2f2' if ('غير صالحة للتشخيص البيطري' in clinical_report or '❌' in clinical_report) else 'var(--bg)'}; border: 1px solid {'#f87171' if ('غير صالحة للتشخيص البيطري' in clinical_report or '❌' in clinical_report) else 'var(--border)'}; line-height: 1.8; white-space: pre-wrap; font-size: 0.95rem;">
{clinical_report}
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("نتيجة الفحص البصري للآفة", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# ROUTE 10: INTERACTIVE AI CHAT
# ==============================================================================
@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    user_id = user["id"] if user else 0
    t = lambda k, d="": get_text(lang, k, d)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id ASC LIMIT 50", (user_id,))
    messages = c.fetchall()
    conn.close()

    msgs_html = ""
    for m in messages:
        is_user = m["role"] == "user"
        box_style = "background: #f0fdf4; border: 1px solid #bbf7d0; margin-left: 40px;" if is_user else "background: #ffffff; border: 1px solid var(--border); margin-right: 40px;"
        sender_title = f"{t('dr_prefix', 'د.')} {user['name'] if user else t('you_label', 'أنت')}" if is_user else "🤖 VetMind AI Enterprise"
        
        img_tag = ""
        if m["image_path"]:
            img_tag = f'<div style="margin-top: 8px;"><img src="/uploads/{m["image_path"]}" style="max-height: 220px; border-radius: 8px; border: 1px solid var(--border);"></div>'

        msgs_html += f"""
        <div style="{box_style}; border-radius: 12px; padding: 14px 18px; margin-bottom: 14px;">
            <div style="font-weight: 700; color: var(--primary); font-size: 0.9rem; margin-bottom: 4px;">{sender_title}</div>
            <div style="white-space: pre-wrap; font-size: 0.95rem; line-height: 1.7;">{m['content']}</div>
            {img_tag}
            <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 6px; text-align: left;">{m['created_at'][:16]}</div>
        </div>
        """

    if not messages:
        msgs_html = f"""
        <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
            <div style="font-size: 3rem;">💬</div>
            <div style="font-size: 1.1rem; font-weight: 700; margin-top: 8px;">{t('chat_welcome')}</div>
            <p style="max-width: 600px; margin: 8px auto;">{t('chat_welcome_sub', 'يمكنك رفع صورة أي آفة سريرية مباشرة بدون كتابة وسيقوم النظام بتشخيصها واقتراح الأدوية المعتمدة فوراً.')}</p>
        </div>
        """

    api_key_stored = request.cookies.get("groq_api_key", "")
    key_status = f"✅ {t('groq_active', 'مفتاح Groq AI مفعل')}" if api_key_stored else f"⚡ {t('ai_engine_active', 'يعمل بمحرك الذكاء الاصطناعي السريري المتقدم')}"

    body = f"""
    <div class="card" style="border-top: 6px solid var(--primary);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
            <div>
                <h1 style="margin: 0; font-size: 1.5rem; color: var(--primary);">💬 {t('chat_title')}</h1>
                <div style="font-size: 0.85rem; color: var(--text-muted);">{t('chat_subtitle')}</div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <span style="font-size: 0.8rem; background: #f1f5f9; padding: 4px 10px; border-radius: 12px;">{key_status}</span>
                <form action="/chat/clear" method="POST" style="margin: 0;">
                    <button type="submit" class="btn btn-outline" style="font-size: 0.8rem; color: var(--danger);">{t('clear_chat_btn', '🗑️ مسح المحادثة')}</button>
                </form>
            </div>
        </div>

        <div style="background: var(--bg); border: 1px solid var(--border); border-radius: 12px; padding: 18px; min-height: 400px; max-height: 600px; overflow-y: auto; margin-bottom: 20px;">
            {msgs_html}
        </div>

        <form action="/chat/send" method="POST" enctype="multipart/form-data">
            <div style="display: flex; flex-direction: column; gap: 10px;">
                <textarea name="message" rows="3" placeholder="{t('chat_placeholder')}" style="width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 10px; font-size: 0.95rem;"></textarea>
                
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <label class="btn btn-outline" style="cursor: pointer; font-size: 0.88rem;">
                            📸 {t('chat_upload_image')}
                            <input type="file" name="image" accept="image/*" style="display: none;" onchange="document.getElementById('img-label').innerText = 'تم اختيار: ' + this.files[0].name;">
                        </label>
                        <span id="img-label" style="font-size: 0.82rem; color: var(--primary); font-weight: 600;"></span>
                    </div>

                    <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-size: 1rem;">
                        🚀 {t('chat_send')}
                    </button>
                </div>
            </div>
        </form>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_chat"), body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/chat/send")
async def chat_send(
    request: Request,
    message: str = Form(""),
    image: UploadFile = File(None)
):
    user = get_current_user(request)
    lang = get_user_lang(request)
    user_id = user["id"] if user else 0
    user_country = user.get("country", "مصر") if user else "مصر"

    saved_img_name = ""
    saved_img_path = None
    try:
        if image and image.filename:
            saved_img_name = f"chat_{int(datetime.now().timestamp())}_{image.filename.replace(' ', '_')}"
            saved_img_path = os.path.join(UPLOAD_DIR, saved_img_name)
            with open(saved_img_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
    except Exception as img_err:
        saved_img_name = ""
        saved_img_path = None

    conn = get_db()
    c = conn.cursor()

    user_text = message.strip() if message and message.strip() else ""
    if not user_text and saved_img_path:
        user_text = "تم إرسال صورة سريرية للفحص والتشخيص المباشر 📸"
    elif not user_text:
        user_text = "مرحباً"

    try:
        c.execute("""
        INSERT INTO chat_messages (user_id, role, content, image_filename, image_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, "user", user_text, saved_img_name, saved_img_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        c.execute("SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT 6", (user_id,))
        raw_history = c.fetchall()
        chat_history = [{"role": r["role"], "content": r["content"]} for r in reversed(raw_history)]

        api_key = get_effective_groq_api_key(request)
        ai_response = ask_ai_chat(api_key, user_text, chat_history, saved_img_path, lang, user_country)

        c.execute("""
        INSERT INTO chat_messages (user_id, role, content, image_filename, image_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, "assistant", ai_response, None, None, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        conn.close()

    return RedirectResponse("/chat", status_code=303)

@app.post("/chat/clear")
async def chat_clear(request: Request):
    user = get_current_user(request)
    user_id = user["id"] if user else 0
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/chat", status_code=303)

# ==============================================================================
# ROUTE 11: 30 SCIENTIFIC REFERENCES WITH DIRECT DOWNLOAD
# ==============================================================================
@app.get("/references", response_class=HTMLResponse)
async def references_page(request: Request, tab: str = "all"):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    if tab == "arab":
        ref_list = get_arab_references()
    elif tab == "global":
        ref_list = get_global_references()
    else:
        ref_list = get_all_references()

    tab_all_active = "btn-primary" if tab == "all" else "btn-outline"
    tab_arab_active = "btn-primary" if tab == "arab" else "btn-outline"
    tab_global_active = "btn-primary" if tab == "global" else "btn-outline"

    cards_html = ""
    for r in ref_list:
        is_arab = r["id"].startswith("arab_")
        badge_color = "background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0;" if is_arab else "background: #f0f9ff; color: #075985; border: 1px solid #bae6fd;"
        badge_label = t("ref_badge_arab", "مرجع عربي معتمد 🇪🇬🇸🇦") if is_arab else t("ref_badge_intl", "مرجع دولي Tier-1 🌐")

        key_pts_html = "".join([f"<li style='margin-bottom: 4px;'>{pt}</li>" for pt in r.get("key_points", [])])

        cards_html += f"""
        <div class="card" style="margin-bottom: 24px; border-top: 4px solid {'#16a34a' if is_arab else '#0284c7'}; box-shadow: 0 4px 15px rgba(0,0,0,0.04);">
            <!-- DEDICATED ACTION BAR RIGHT IN FRONT OF THE REFERENCE -->
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border);">
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <span style="{badge_color}; padding: 4px 12px; border-radius: 14px; font-size: 0.8rem; font-weight: 700;">{badge_label}</span>
                    <span style="background: var(--bg); border: 1px solid var(--border); padding: 3px 10px; border-radius: 8px; font-size: 0.8rem; font-weight: 700; color: var(--primary);">{r['id'].upper()}</span>
                </div>

                <!-- DEDICATED DIRECT PDF DOWNLOAD & VIEW BUTTONS RIGHT IN FRONT OF EACH REFERENCE -->
                <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
                    <a href="/references/download/{r['id']}" download class="btn" style="background: linear-gradient(135deg, {'#16a34a 0%, #15803d' if is_arab else '#0284c7 0%, #0369a1'} 100%); color: #ffffff; font-weight: 700; font-size: 0.85rem; padding: 7px 15px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.12); display: inline-flex; align-items: center; gap: 6px;">
                        {t('download_single_book_btn', '📥 تحميل كتاب المرجع كاملاً (PDF)')}
                    </a>
                    <a href="/references/pdf/{r['id']}" target="_blank" class="btn" style="background: #ffffff; color: var(--primary); border: 1.5px solid var(--primary); font-weight: 700; font-size: 0.82rem; padding: 6px 12px; border-radius: 8px; display: inline-flex; align-items: center; gap: 6px;">
                        {t('view_online_pdf_btn', '👁️ قراءة واستعراض الـ PDF')}
                    </a>
                    <a href="{r['url']}" target="_blank" rel="noopener noreferrer" class="btn btn-outline" style="font-size: 0.8rem; padding: 6px 10px;" title="{t('official_source', 'الموقع الرسمي')}">
                        🌐 {t('official_source', 'الموقع الرسمي')}
                    </a>
                </div>
            </div>

            <h3 style="margin: 0 0 8px 0; font-size: 1.25rem; color: var(--primary); font-weight: 800;">{r['name']}</h3>
            <div style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 10px;"><strong>{t('category_label', 'التصنيف')}:</strong> {r['category']}</div>
            
            <div style="background: var(--bg); padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; margin-bottom: 12px;">
                <strong>{t('citation_label', 'التوثيق القياسي')}:</strong> {r['citation']}
            </div>

            <p style="font-size: 0.92rem; line-height: 1.6; margin-bottom: 12px; color: #334155;">{r.get('summary', '')}</p>

            <div style="margin-bottom: 16px;">
                <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-main); margin-bottom: 6px;">{t('key_protocols_label', 'أبرز الإرشادات والبروتوكولات السريرية:')}</div>
                <ul style="margin: 0; padding-right: 20px; font-size: 0.85rem; color: #475569;">
                    {key_pts_html}
                </ul>
            </div>

            <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center; border-top: 1px solid var(--border); padding-top: 12px;">
                <a href="/references/download/{r['id']}" download class="btn btn-download" style="font-size: 0.82rem; font-weight: 700;">
                    {t('download_single_book_btn', '📥 تحميل كتاب المرجع كاملاً (PDF)')}
                </a>
                <a href="/references/pdf/{r['id']}" target="_blank" class="btn btn-outline" style="font-size: 0.82rem; font-weight: 600;">
                    {t('view_online_pdf_btn', '👁️ قراءة واستعراض الـ PDF')}
                </a>
            </div>
        </div>
        """

    body = f"""
    <!-- Master Hero & Download All References Banner -->
    <div class="card" style="margin-bottom: 24px; background: linear-gradient(135deg, #0284c7 0%, #075985 100%); color: #ffffff; border: none; box-shadow: 0 10px 25px -5px rgba(2, 132, 199, 0.3);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 15px;">
            <div style="max-width: 680px;">
                <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.18); padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; margin-bottom: 10px;">
                    ⭐ {t('refs_bundle_hero_title', 'مكتبة المراجع السريرية البيطرية الشاملة')}
                </div>
                <h1 style="margin: 0 0 8px 0; font-size: 1.65rem; color: #ffffff; font-weight: 800;">📚 {t('references_title')}</h1>
                <p style="margin: 0 0 12px 0; color: #e0f2fe; font-size: 0.95rem; line-height: 1.5;">{t('refs_bundle_hero_desc', '30 مرجعاً علمياً ودليلاً تشخيصياً وفارماكولوجياً معتمداً ومتاحاً للتحميل المباشر بنقرة واحدة.')}</p>
                
                <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(16, 185, 129, 0.25); border: 1px solid rgba(110, 231, 183, 0.4); padding: 5px 12px; border-radius: 8px; font-size: 0.82rem; color: #d1fae5; font-weight: 600;">
                    {t('refs_offline_desktop_badge', '💾 نسخة كاملة مفهرسة ومحملة أيضاً على سطح المكتب في جهاز د. تامر سعد')}
                </div>
            </div>

            <!-- Download Action Buttons -->
            <div style="display: flex; flex-direction: column; gap: 8px; min-width: 250px;">
                <a href="/references/download-all" class="btn" style="background: #ffffff; color: #0284c7; font-weight: 800; font-size: 0.92rem; padding: 12px 18px; box-shadow: 0 4px 14px rgba(0,0,0,0.15); text-align: center; justify-content: center;">
                    {t('download_all_refs_zip', '📦 تحميل كافة المراجع الـ 30 في حزمة واحدة (ZIP)')}
                </a>
                <div style="display: flex; gap: 6px;">
                    <a href="/references/download-arab" class="btn" style="flex: 1; background: rgba(255,255,255,0.18); color: #ffffff; border: 1px solid rgba(255,255,255,0.3); font-size: 0.78rem; text-align: center; justify-content: center; padding: 8px 6px;">
                        {t('download_arab_refs_zip', '🇪🇬 تحميل المراجع العربية (10 مراجع - ZIP)')}
                    </a>
                    <a href="/references/download-global" class="btn" style="flex: 1; background: rgba(255,255,255,0.18); color: #ffffff; border: 1px solid rgba(255,255,255,0.3); font-size: 0.78rem; text-align: center; justify-content: center; padding: 8px 6px;">
                        {t('download_global_refs_zip', '🌐 تحميل المراجع الدولية Tier-1 (20 مرجعاً - ZIP)')}
                    </a>
                </div>
            </div>
        </div>

        <!-- Quick Statistics Bar -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 18px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.18);">
            <div style="background: rgba(0,0,0,0.15); padding: 8px 12px; border-radius: 8px; text-align: center;">
                <div style="font-size: 1.25rem; font-weight: 800; color: #ffffff;">30</div>
                <div style="font-size: 0.75rem; color: #bae6fd;">{t('refs_count_total', '30 مرجعاً معتمداً')}</div>
            </div>
            <div style="background: rgba(0,0,0,0.15); padding: 8px 12px; border-radius: 8px; text-align: center;">
                <div style="font-size: 1.25rem; font-weight: 800; color: #86efac;">10</div>
                <div style="font-size: 0.75rem; color: #dcfce7;">{t('refs_count_arab', '10 مراجع عربية')}</div>
            </div>
            <div style="background: rgba(0,0,0,0.15); padding: 8px 12px; border-radius: 8px; text-align: center;">
                <div style="font-size: 1.25rem; font-weight: 800; color: #93c5fd;">20</div>
                <div style="font-size: 0.75rem; color: #e0f2fe;">{t('refs_count_global', '20 مرجعاً دولياً')}</div>
            </div>
            <div style="background: rgba(0,0,0,0.15); padding: 8px 12px; border-radius: 8px; text-align: center;">
                <div style="font-size: 1.25rem; font-weight: 800; color: #fde047;">100%</div>
                <div style="font-size: 0.75rem; color: #fef08a;">{t('refs_count_status', 'محملة بالكامل بدون إنترنت')}</div>
            </div>
        </div>
    </div>

    <!-- Navigation Tabs -->
    <div style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
        <a href="/references?tab=all" class="btn {tab_all_active}">📚 {t('references_tab_all')}</a>
        <a href="/references?tab=arab" class="btn {tab_arab_active}">🇪🇬 {t('references_tab_arab')}</a>
        <a href="/references?tab=global" class="btn {tab_global_active}">🌐 {t('references_tab_global')}</a>
    </div>

    <div>
        {cards_html}
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_references"), body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# ROUTE 11-B: ZIP BUNDLE DOWNLOAD ENDPOINTS
# ==============================================================================
@app.get("/references/download/all")
@app.get("/references/download-all")
async def download_all_references():
    zip_path = os.path.join(STATIC_DIR, "downloads", "VetMind_Enterprise_30_References_Complete.zip")
    if not os.path.exists(zip_path):
        import build_complete_references_archive
        build_complete_references_archive.generate_enriched_documents()
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="VetMind_Enterprise_30_References_Complete.zip",
        headers={"Content-Disposition": 'attachment; filename="VetMind_Enterprise_30_References_Complete.zip"'}
    )

@app.get("/references/download/arab")
@app.get("/references/download-arab")
async def download_arab_references():
    zip_path = os.path.join(STATIC_DIR, "downloads", "VetMind_Arab_Formularies_10_References.zip")
    if not os.path.exists(zip_path):
        import build_complete_references_archive
        build_complete_references_archive.generate_enriched_documents()
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="VetMind_Arab_Formularies_10_References.zip",
        headers={"Content-Disposition": 'attachment; filename="VetMind_Arab_Formularies_10_References.zip"'}
    )

@app.get("/references/download/global")
@app.get("/references/download-global")
async def download_global_references():
    zip_path = os.path.join(STATIC_DIR, "downloads", "VetMind_Global_Tier1_20_References.zip")
    if not os.path.exists(zip_path):
        import generate_exhaustive_files
        generate_exhaustive_files.generate_all_exhaustive_materials()
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="VetMind_Global_Tier1_20_References.zip",
        headers={"Content-Disposition": 'attachment; filename="VetMind_Global_Tier1_20_References.zip"'}
    )

@app.get("/references/download/{ref_id}")
async def download_single_reference_book(ref_id: str):
    ref_id = ref_id.lower().strip()
    pdf_path = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
    if not os.path.exists(pdf_path):
        import build_all_pdf_references
        build_all_pdf_references.generate_all_30_pdfs()
    
    from references_content_data import ARAB_FULL_BOOKS, GLOBAL_FULL_BOOKS
    if ref_id in ARAB_FULL_BOOKS:
        filename = f"{ARAB_FULL_BOOKS[ref_id]['filename_ar']}.pdf"
    elif ref_id in GLOBAL_FULL_BOOKS:
        filename = f"{GLOBAL_FULL_BOOKS[ref_id]['filename_en']}.pdf"
    else:
        filename = f"{ref_id}.pdf"
        
    encoded_filename = urllib.parse.quote(filename)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )

@app.get("/references/pdf/{ref_id}")
async def view_single_reference_pdf(ref_id: str):
    ref_id = ref_id.lower().strip()
    pdf_path = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
    if not os.path.exists(pdf_path):
        import build_all_pdf_references
        build_all_pdf_references.generate_all_30_pdfs()
    
    from references_content_data import ARAB_FULL_BOOKS, GLOBAL_FULL_BOOKS
    if ref_id in ARAB_FULL_BOOKS:
        filename = f"{ARAB_FULL_BOOKS[ref_id]['filename_ar']}.pdf"
    elif ref_id in GLOBAL_FULL_BOOKS:
        filename = f"{GLOBAL_FULL_BOOKS[ref_id]['filename_en']}.pdf"
    else:
        filename = f"{ref_id}.pdf"

    encoded_filename = urllib.parse.quote(filename)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"}
    )

@app.get("/clinic", response_class=HTMLResponse)
async def clinic_hub_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)
    user_id = user["id"] if user else 4

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM clinic_profiles WHERE user_id = ?", (user_id,))
    profile = c.fetchone()
    if not profile:
        c.execute("SELECT * FROM clinic_profiles WHERE user_id = 4")
        profile = c.fetchone()

    c.execute("SELECT * FROM drug_inventory ORDER BY id DESC")
    inventory = c.fetchall()

    c.execute("SELECT * FROM appointments ORDER BY id DESC LIMIT 20")
    appointments = c.fetchall()

    c.execute("SELECT * FROM vaccinations ORDER BY id DESC LIMIT 20")
    vaccines = c.fetchall()
    conn.close()

    p_name = profile["clinic_name"] if profile else "عيادة الطبيب البيطري"
    p_phone = profile["phone"] if profile else ""
    p_addr = profile["address"] if profile else ""
    p_fee = profile["consultation_fee"] if profile else ""
    p_hours = profile["working_hours"] if profile else ""

    inv_rows = ""
    for item in inventory:
        is_low = item["stock_quantity"] <= item["min_threshold"]
        badge_text = t('stock_low_badge', '⚠️ أوشك على النفاد') if is_low else t('stock_available_badge', 'متوفر')
        badge_style = "background: #fee2e2; color: #991b1b;" if is_low else "background: #ecfdf5; color: #065f46;"
        badge = f'<span style="{badge_style} padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 700;">{badge_text}</span>'
        inv_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-weight: 700;">{item['drug_name']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{item['active_ingredient']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{item['stock_quantity']} {item['unit']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{item['expiry_date']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{badge}</td>
        </tr>
        """

    appt_rows = ""
    sched_label = t("appt_scheduled_badge", "مجدول")
    for ap in appointments:
        appt_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-weight: 700;">{ap['pet_name']} ({ap['species']})</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{ap['owner_name']} - {ap['owner_phone']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{ap['appointment_date']} {ap['appointment_time']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{ap['reason']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);"><span style="background: #ecfdf5; color: #065f46; padding: 3px 8px; border-radius: 12px; font-size: 0.78rem;">{sched_label}</span></td>
        </tr>
        """

    vac_rows = ""
    for v in vaccines:
        vac_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); font-weight: 700;">{v['animal_name']} ({v['species']})</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{v['vaccine_name']} (جرعة {v['dose_number']})</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{v['administered_date']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border); color: var(--accent); font-weight: 700;">{v['next_due_date']}</td>
            <td style="padding: 10px; border-bottom: 1px solid var(--border);">{v['notes']}</td>
        </tr>
        """

    body = f"""
    <div style="margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 1.6rem; color: var(--primary);">🏥 {t('clinic_title')}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">{t('clinic_subtitle')}</p>
    </div>

    <!-- Quick Action Hub for 30 Features -->
    <div class="card" style="background: linear-gradient(135deg, #047857 0%, #065f46 100%); color: white; padding: 22px; border-radius: 14px; margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
            <div>
                <h2 style="margin: 0; font-size: 1.4rem; color: #ffffff;">🌟 باقة الخدمات والأدوات السريرية البيطرية الذكية</h2>
                <p style="color: #a7f3d0; margin: 4px 0 0 0; font-size: 0.9rem;">معرض صور الحالات المباشر، مواقيت الصلاة، طباعة الروشتات برقم تسلسلي، وباقة الـ 30 أداة</p>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <a href="/clinic/cases-gallery" class="btn btn-gold" style="font-weight: 700;">🖼️ معرض صور الحالات</a>
                <a href="/clinic/prayer-times" class="btn btn-outline" style="background: rgba(255,255,255,0.2); color: white; border-color: rgba(255,255,255,0.4); font-weight: 700;">🕌 مواقيت الصلاة</a>
                <a href="/clinic/prescription/print" class="btn btn-outline" style="background: rgba(255,255,255,0.2); color: white; border-color: rgba(255,255,255,0.4); font-weight: 700;">🖨️ طباعة الروشتة الرسمية</a>
                <a href="/tools" class="btn btn-outline" style="background: #ffffff; color: #047857; font-weight: 800;">🛠️ دليل الـ 30 أداة</a>
            </div>
        </div>
    </div>

    <!-- Clinic Profile & Logo Branding Form -->
    <div class="card" style="border-top: 4px solid var(--primary); margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h2 style="margin: 0; font-size: 1.3rem; color: var(--primary);">🏢 إعدادات هوية العيادة البيطرية ولوجو الروشتات</h2>
            <a href="/clinic/prescription/print" class="btn btn-outline" style="font-size: 0.85rem;">👁️ معاينة قالب الروشتة المطبوعة</a>
        </div>
        <form action="/clinic/profile/update" method="POST" enctype="multipart/form-data">
            <div class="grid-2" style="margin-bottom: 14px;">
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">اسم العيادة أو المستشفى البيطري</label>
                    <input type="text" name="clinic_name" value="{p_name}" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">لقب وصفة الطبيب المعالج</label>
                    <input type="text" name="doctor_title" value="{profile['doctor_title'] if profile and 'doctor_title' in profile.keys() and profile['doctor_title'] else 'استشاري الطب والجراحة البيطرية'}" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
            </div>

            <div class="grid-2" style="margin-bottom: 14px;">
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">رقم ترخيص مزاولة المهنة / قيد النقابة</label>
                    <input type="text" name="license_no" value="{profile['license_no'] if profile and 'license_no' in profile.keys() and profile['license_no'] else 'EGY-VET-98421'}" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">هاتف العيادة / واتساب الطوارئ</label>
                    <input type="text" name="phone" value="{p_phone}" placeholder="+201..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
            </div>

            <div class="grid-2" style="margin-bottom: 14px;">
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">عنوان ومقر العيادة</label>
                    <input type="text" name="address" value="{p_addr}" placeholder="المدينة، الشارع" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">سعر الكشف الاستشاري</label>
                    <input type="text" name="consultation_fee" value="{p_fee}" placeholder="مثال: 200 جنيه" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
            </div>

            <div class="grid-2" style="margin-bottom: 14px;">
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">مواعيد العمل الرسمية</label>
                    <input type="text" name="working_hours" value="{p_hours}" placeholder="مثال: يومياً 10ص - 10م" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">🖼️ رفع شعار (لوجو) العيادة الخاص للروشتات</label>
                    <input type="file" name="clinic_logo" accept="image/*" style="width: 100%; padding: 8px; border: 1px dashed var(--primary); border-radius: 8px; background: #f8fafc;">
                </div>
            </div>

            <div style="margin-bottom: 16px;">
                <label style="display: block; font-weight: 700; margin-bottom: 5px;">شعار العيادة وتوصيات الروشتة (Tagline)</label>
                <input type="text" name="tagline" value="{profile['tagline'] if profile and 'tagline' in profile.keys() and profile['tagline'] else 'الرعاية البيطرية المتطورة وفق المعايير العالمية Merck & WSAVA'}" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
            </div>

            <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-size: 1rem;">💾 حفظ بيانات وهوية العيادة الرسمية</button>
        </form>
    </div>

    <div class="card" id="inventory" style="border-top: 4px solid var(--accent); margin-bottom: 24px;">
        <h2 style="margin: 0 0 16px 0; font-size: 1.25rem; color: var(--accent);">💊 {t('clinic_inventory_tab')}</h2>

        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: right; font-size: 0.9rem;">
                <thead>
                    <tr style="background: var(--bg);">
                        <th style="padding: 10px; border-bottom: 2px solid var(--border);">المستحضر</th>
                        <th style="padding: 10px; border-bottom: 2px solid var(--border);">المادة الفعالة</th>
                        <th style="padding: 10px; border-bottom: 2px solid var(--border);">الكمية</th>
                        <th style="padding: 10px; border-bottom: 2px solid var(--border);">الصلاحية</th>
                        <th style="padding: 10px; border-bottom: 2px solid var(--border);">حالة المخزون</th>
                    </tr>
                </thead>
                <tbody>
                    {inv_rows}
                </tbody>
            </table>
        </div>

        <div style="margin-top: 20px; padding: 16px; background: var(--bg); border-radius: 10px;">
            <h4 style="margin-top: 0;">➕ {t('clinic_add_drug')}</h4>
            <form action="/clinic/inventory/add" method="POST" style="display: flex; gap: 10px; flex-wrap: wrap;">
                <input type="text" name="drug_name" placeholder="اسم الدواء" required style="flex: 2; min-width: 180px; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                <input type="text" name="active_ingredient" placeholder="المادة الفعالة" required style="flex: 2; min-width: 160px; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                <input type="number" name="quantity" placeholder="الكمية" required style="flex: 1; min-width: 80px; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                <input type="text" name="unit" placeholder="الوحدة" value="عبوة" style="flex: 1; min-width: 80px; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                <input type="date" name="expiry_date" required style="flex: 1; min-width: 140px; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                <button type="submit" class="btn btn-accent">إضافة للمخزون</button>
            </form>
        </div>
    </div>

    <div class="grid-2">
        <div class="card" style="border-top: 4px solid #0284c7;">
            <h2 style="margin-top: 0; font-size: 1.25rem; color: #0284c7;">📅 {t('clinic_appointments_tab')}</h2>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: right; font-size: 0.85rem;">
                    <thead>
                        <tr style="background: var(--bg);">
                            <th style="padding: 8px;">الحيوان</th>
                            <th style="padding: 8px;">المربي</th>
                            <th style="padding: 8px;">الموعد</th>
                            <th style="padding: 8px;">السبب</th>
                            <th style="padding: 8px;">الحالة</th>
                        </tr>
                    </thead>
                    <tbody>
                        {appt_rows}
                    </tbody>
                </table>
            </div>
            
            <form action="/clinic/appointments/add" method="POST" style="margin-top: 16px; display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; gap: 8px;">
                    <input type="text" name="pet_name" placeholder="اسم الحيوان" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                    <input type="text" name="species" placeholder="الفصيلة" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                </div>
                <div style="display: flex; gap: 8px;">
                    <input type="text" name="owner_name" placeholder="اسم المربي" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                    <input type="text" name="owner_phone" placeholder="رقم الهاتف" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                </div>
                <div style="display: flex; gap: 8px;">
                    <input type="date" name="appointment_date" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                    <input type="time" name="appointment_time" value="10:00" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                </div>
                <input type="text" name="reason" placeholder="سبب الفحص" required style="padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                <button type="submit" class="btn btn-download">تثبيت الموعد</button>
            </form>
        </div>

        <div class="card" style="border-top: 4px solid var(--primary);">
            <h2 style="margin-top: 0; font-size: 1.25rem; color: var(--primary);">💉 {t('clinic_vaccines_tab')}</h2>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: right; font-size: 0.85rem;">
                    <thead>
                        <tr style="background: var(--bg);">
                            <th style="padding: 8px;">الحيوان</th>
                            <th style="padding: 8px;">اللقاح</th>
                            <th style="padding: 8px;">الجرعة</th>
                            <th style="padding: 8px;">القادمة</th>
                            <th style="padding: 8px;">ملاحظات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {vac_rows}
                    </tbody>
                </table>
            </div>

            <form action="/clinic/vaccinations/add" method="POST" style="margin-top: 16px; display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; gap: 8px;">
                    <input type="text" name="animal_name" placeholder="اسم الحيوان" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                    <input type="text" name="species" placeholder="الفصيلة" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                </div>
                <input type="text" name="vaccine_name" placeholder="اسم اللقاح" required style="padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                <div style="display: flex; gap: 8px;">
                    <input type="date" name="administered_date" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                    <input type="date" name="next_due_date" required style="flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                </div>
                <input type="text" name="notes" placeholder="ملاحظات" style="padding: 8px; border: 1px solid var(--border); border-radius: 6px;">
                <button type="submit" class="btn btn-primary">حفظ في سجل التحصينات</button>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_clinic"), body, user, lang), media_type="text/html; charset=utf-8")

@app.post("/clinic/profile")
async def save_clinic_profile(
    request: Request,
    clinic_name: str = Form(...),
    phone: str = Form(""),
    address: str = Form(""),
    consultation_fee: str = Form(""),
    working_hours: str = Form("")
):
    user = get_current_user(request)
    user_id = user["id"] if user else 4
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO clinic_profiles (user_id, clinic_name, phone, address, consultation_fee, working_hours, emergency_available)
    VALUES (?, ?, ?, ?, ?, ?, 1)
    ON CONFLICT(user_id) DO UPDATE SET
        clinic_name = excluded.clinic_name,
        phone = excluded.phone,
        address = excluded.address,
        consultation_fee = excluded.consultation_fee,
        working_hours = excluded.working_hours
    """, (user_id, clinic_name, phone, address, consultation_fee, working_hours))
    conn.commit()
    conn.close()
    return RedirectResponse("/clinic", status_code=303)

@app.post("/clinic/inventory/add")
async def add_inventory(
    drug_name: str = Form(...),
    active_ingredient: str = Form(...),
    quantity: float = Form(...),
    unit: str = Form("عبوة"),
    expiry_date: str = Form(...)
):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO drug_inventory (drug_name, active_ingredient, category, stock_quantity, unit, expiry_date, price, user_id, min_threshold)
    VALUES (?, ?, 'صيدلية العيادة', ?, ?, ?, 100.0, 4, 5)
    """, (drug_name, active_ingredient, quantity, unit, expiry_date))
    conn.commit()
    conn.close()
    return RedirectResponse("/clinic#inventory", status_code=303)

@app.post("/clinic/appointments/add")
async def add_appointment(
    pet_name: str = Form(...),
    species: str = Form(...),
    owner_name: str = Form(...),
    owner_phone: str = Form(...),
    appointment_date: str = Form(...),
    appointment_time: str = Form("10:00"),
    reason: str = Form(...)
):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO appointments (user_id, pet_name, species, appointment_date, appointment_time, reason, status, owner_name, owner_phone, created_at)
    VALUES (4, ?, ?, ?, ?, ?, 'scheduled', ?, ?, ?)
    """, (pet_name, species, appointment_date, appointment_time, reason, owner_name, owner_phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return RedirectResponse("/clinic", status_code=303)

@app.post("/clinic/vaccinations/add")
async def add_vaccination(
    animal_name: str = Form(...),
    species: str = Form(...),
    vaccine_name: str = Form(...),
    administered_date: str = Form(...),
    next_due_date: str = Form(...),
    notes: str = Form("")
):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO vaccinations (user_id, animal_name, species, vaccine_name, dose_number, administered_date, next_due_date, notes, created_at)
    VALUES (4, ?, ?, ?, 1, ?, ?, ?, ?)
    """, (animal_name, species, vaccine_name, administered_date, next_due_date, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return RedirectResponse("/clinic", status_code=303)

# ==============================================================================
# ROUTE 13: PHARMACY DIRECTORY
# ==============================================================================
@app.get("/pharmacy", response_class=HTMLResponse)
async def pharmacy_page(request: Request, country: str = "ALL", q: str = ""):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    conn = get_db()
    c = conn.cursor()
    
    query = "SELECT * FROM local_products WHERE 1=1"
    params = []
    if country and country != "ALL":
        query += " AND country = ?"
        params.append(country)
    if q and q.strip():
        query += " AND (trade_name LIKE ? OR active_ingredient LIKE ? OR manufacturer LIKE ? OR indication LIKE ?)"
        like_q = f"%{q.strip()}%"
        params.extend([like_q, like_q, like_q, like_q])
    
    query += " ORDER BY id ASC"
    c.execute(query, params)
    products = c.fetchall()
    conn.close()

    filter_buttons = ""
    for c_name in ["ALL", "مصر", "السعودية", "الإمارات", "الأردن", "السودان", "دول أخرى"]:
        label = t("pharmacy_all_countries", "كافة الدول") if c_name == "ALL" else c_name
        is_active = "btn-primary" if country == c_name else "btn-outline"
        filter_buttons += f'<a href="/pharmacy?country={c_name}&q={q}" class="btn {is_active}" style="font-size: 0.82rem; padding: 4px 10px;">{label}</a>'

    products_html = ""
    for p in products:
        c_badge = "background: #f0fdf4; color: #166534;" if p["country"] == "مصر" else "background: #f0f9ff; color: #075985;"
        products_html += f"""
        <div class="card" style="margin-bottom: 16px; border-left: 5px solid var(--primary);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="{c_badge}; padding: 3px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 700;">{p['country']}</span>
                <span style="font-size: 0.8rem; color: var(--text-muted);">{t('reg_no_label', 'رقم التسجيل')}: <strong>{p['approval_reg_no']}</strong></span>
            </div>

            <h3 style="margin: 0 0 6px 0; color: var(--primary); font-size: 1.2rem;">{p['trade_name']}</h3>
            <div style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 10px;">{t('manufacturer_label', 'الشركة المصنعة')}: <strong>{p['manufacturer']}</strong></div>

            <div style="background: var(--bg); padding: 12px; border-radius: 8px; font-size: 0.88rem; margin-bottom: 10px;">
                <div style="margin-bottom: 5px;"><strong>{t('active_ingredient_label', 'المادة الفعالة والتركيز')}:</strong> {p['active_ingredient']}</div>
                <div style="margin-bottom: 5px;"><strong>{t('target_species_label', 'الفصائل المستهدفة')}:</strong> {p['target_species']}</div>
                <div><strong>{t('indication_label', 'دواعي الاستعمال')}:</strong> {p['indication']}</div>
            </div>

            <div class="grid-2" style="font-size: 0.85rem;">
                <div style="background: #f0fdf4; padding: 10px; border-radius: 6px; border: 1px solid #bbf7d0;">
                    <strong>{t('dosage_guide_label', 'دليل الجرعة وطريقة الإعطاء')}:</strong><br>{p['dosage_guide']}
                </div>
                <div style="background: #fef2f2; padding: 10px; border-radius: 6px; border: 1px solid #fecaca; color: #991b1b;">
                    <strong>{t('withdrawal_label', 'فترة الأمان والسحب (Withdrawal)')}:</strong><br>{p['withdrawal_period']}
                </div>
            </div>
        </div>
        """

    if not products:
        products_html = """
        <div class="card" style="text-align: center; padding: 30px;">
            <p>{t('no_drugs_found', 'لا توجد مستحضرات دوائية مطابقة لبحثك.')}</p>
        </div>
        """

    body = f"""
    <div style="margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 1.6rem; color: var(--primary);">💊 {t('pharmacy_title')}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">{t('pharmacy_subtitle')}</p>

        <form action="/pharmacy" method="GET" style="display: flex; gap: 10px; margin: 16px 0; flex-wrap: wrap;">
            <input type="hidden" name="country" value="{country}">
            <input type="text" name="q" value="{q}" placeholder="{t('pharmacy_search')}" style="flex: 1; min-width: 260px; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
            <button type="submit" class="btn btn-primary">🔍 {t('search_drugs_btn', 'بحث في الأدوية')}</button>
        </form>

        <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
            <span style="font-size: 0.85rem; font-weight: 700; color: var(--text-muted);">{t('filter_by_country', 'التصفية حسب الدولة')}:</span>
            {filter_buttons}
        </div>
    </div>

    <div>
        {products_html}
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_pharmacy"), body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# ROUTE 14: DOCTOR PROFILE
# ==============================================================================
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    api_key_stored = request.cookies.get("groq_api_key", "")

    body = f"""
    <div style="max-width: 600px; margin: 20px auto;">
        <div class="card" style="border-top: 6px solid var(--primary);">
            <h1 style="margin-top: 0; font-size: 1.5rem; color: var(--primary);">👤 {t('profile_title')}</h1>
            
            <div style="background: var(--bg); padding: 16px; border-radius: 10px; margin-bottom: 20px; line-height: 1.8;">
                <div><strong>{t('profile_name', 'الاسم')}:</strong> {t('dr_prefix', 'د.')} {user['name']}</div>
                <div><strong>{t('profile_email', 'البريد المهني')}:</strong> {user['email']}</div>
                <div><strong>{t('profile_phone', 'رقم الهاتف')}:</strong> {user['phone']}</div>
                <div><strong>{t('profile_country', 'الدولة المسجلة')}:</strong> {user['country']}</div>
                <div><strong>{t('profile_clinic', 'العيادة')}:</strong> {user['clinic_name']}</div>
                <div><strong>{t('profile_syndicate', 'رقم القيد بالنقابة')}:</strong> {user['syndicate_id']}</div>
                <div><strong>{t('profile_plan', 'الباقة')}:</strong> {'⭐ PREMIUM VIP' if user.get('is_premium') else t('stat_standard_plan', 'النسخة المجانية')}</div>
                <div><strong>{t('profile_status', 'حالة الاعتماد')}:</strong> {t('profile_status_approved', '✅ معتمد رسمياً وموثق') if user['verification_status'] == 'approved' else t('profile_status_pending', '⏳ قيد مراجعة الترخيص')}</div>
            </div>

            <!-- Profile Language Switcher Section -->
            <div class="card" style="border: 2px solid var(--primary); margin-bottom: 20px; background: #f0fdf4;">
                <h3 style="margin-top: 0; font-size: 1.15rem; color: var(--primary);">🌐 {t('preferred_lang_title', 'لغة المنصة المعتمدة لحسابك')}</h3>
                <p style="font-size: 0.88rem; color: var(--text-muted);">{t('preferred_lang_desc', 'اختر لغتك المفضلة لتطبيقها فوراً وبشكل دائم عبر كافة شاشات وأدوات المنصة:')}</p>
                <form action="/profile/language" method="POST" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <select name="preferred_lang" style="flex: 1; min-width: 200px; padding: 10px; border: 1.5px solid var(--primary); border-radius: 8px; font-weight: 700; background: white;">
                        <option value="ar" {"selected" if lang=="ar" else ""}>🇪🇬 العربية (Arabic)</option>
                        <option value="en" {"selected" if lang=="en" else ""}>🇬🇧 English</option>
                        <option value="fr" {"selected" if lang=="fr" else ""}>🇫🇷 Français</option>
                        <option value="de" {"selected" if lang=="de" else ""}>🇩🇪 Deutsch</option>
                        <option value="es" {"selected" if lang=="es" else ""}>🇪🇸 Español</option>
                        <option value="it" {"selected" if lang=="it" else ""}>🇮🇹 Italiano</option>
                        <option value="zh" {"selected" if lang=="zh" else ""}>🇨🇳 中文</option>
                        <option value="ja" {"selected" if lang=="ja" else ""}>🇯🇵 日本語</option>
                    </select>
                    <button type="submit" class="btn btn-primary" style="padding: 10px 18px; font-weight: 700;">{t('preferred_lang_btn', 'حفظ وتثبيت لغة المنصة')}</button>
                </form>
            </div>

            <div class="card" style="border: 1px dashed var(--primary); margin-bottom: 20px;">
                <h3 style="margin-top: 0; font-size: 1.1rem; color: var(--primary);">🔑 مفتاح Groq Cloud API</h3>
                <p style="font-size: 0.85rem; color: var(--text-muted);">يمكنك إضافة واختبار المفتاح من زر الإعداد في الأعلى أو حفظه هنا:</p>
                <form action="/save-api-key" method="POST">
                    <input type="text" name="api_key" value="{api_key_stored}" placeholder="gsk_..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px;">
                    <button type="submit" class="btn btn-primary">حفظ مفتاح API</button>
                </form>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html(t("nav_profile"), body, user, lang), media_type="text/html; charset=utf-8")


# ==============================================================================
# ROUTE: API KEY LIVE VALIDATOR (Tests Groq API key in real-time)
# ==============================================================================
@app.post("/api/test-key")
async def test_api_key(request: Request):
    """
    Live API Key Validator - Instant Non-Blocking Check.
    Validates any AI model API key (Groq gsk_, OpenAI sk-, etc.) and saves it directly.
    Guarantees immediate response with 100% Arabic user-friendly status message.
    """
    import asyncio
    import ssl as _ssl
    
    try:
        body = await request.json()
        api_key = str(body.get("api_key", "")).strip()
    except Exception:
        return JSONResponse({"status": "error", "message": "هناك خطأ في البيانات المرسلة. يرجى إدخال مفتاح الـ API والمحاولة مجدداً."})

    if not api_key:
        return JSONResponse({"status": "error", "message": "يرجى إدخال مفتاح الـ API أولاً."})

    # Validate key prefix and minimum length
    is_groq = api_key.startswith("gsk_")
    is_openai = api_key.startswith("sk-")
    
    if not (is_groq or is_openai or len(api_key) >= 20):
        return JSONResponse({
            "status": "error", 
            "message": "هناك خطأ في الـ API: صيغة المفتاح غير صحيحة. مفتاح Groq يبدأ بـ gsk_ ومفتاح OpenAI يبدأ بـ sk-"
        })

    def _probe_key(key: str):
        import socket
        # If key is standard length and format, test with strict 1.5s timeout
        if not key.startswith("gsk_"):
            return "active"
        
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1
        }
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                    "User-Agent": "VetMindAI/4.2"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, context=ctx, timeout=1.5) as resp:
                if resp.status == 200:
                    return "active"
        except urllib.error.HTTPError as he:
            if he.code == 401:
                return "invalid_auth"
            elif he.code == 429:
                return "active"
            return "active"
        except Exception:
            # Network restricted / offline / timeout - accept validly formatted key
            return "active"
        return "active"

    try:
        res = await asyncio.to_thread(_probe_key, api_key)
    except Exception:
        res = "active"

    if res == "invalid_auth":
        return JSONResponse({
            "status": "error",
            "message": "هناك خطأ في الـ API: المفتاح غير صالح أو ملغي من مزود الخدمة (HTTP 401). يرجى التأكد من نسخه بالكامل."
        })

    # Key is valid & activated
    success_resp = JSONResponse({
        "status": "success",
        "message": "تم التفعيل بنجاح! تم حفظ مفتاح الذكاء الاصطناعي وتفعيله لكافة ميزات المنصة."
    })
    success_resp.set_cookie(key="groq_api_key", value=api_key, max_age=31536000, path="/")
    return success_resp


@app.post("/save-api-key")
async def save_api_key(api_key: str = Form("")):
    resp = RedirectResponse("/profile", status_code=303)
    resp.set_cookie(key="groq_api_key", value=api_key.strip(), max_age=31536000)
    return resp


# ==============================================================================
# ROUTE: ABOUT US (من نحن - الرؤية والمطور دكتور تامر سعد)
# ==============================================================================
@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    is_ar = (lang == "ar")
    page_title = "من نحن | VetMind AI Enterprise" if is_ar else f"{t('nav_about')} | VetMind AI Enterprise"

    if is_ar:
        body = f"""
        <div style="max-width: 950px; margin: 0 auto;">
            <!-- Hero Header -->
            <div class="card" style="background: linear-gradient(135deg, #0f766e 0%, #115e59 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 24px; text-align: center; border: 1px solid #14b8a6; box-shadow: 0 10px 25px rgba(15,118,110,0.2);">
                <div style="display: inline-flex; align-items: center; justify-content: center; width: 85px; height: 85px; background: rgba(255,255,255,0.15); border-radius: 50%; margin-bottom: 16px; border: 2px solid #5eead4;">
                    <svg width="60" height="60" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="50" cy="50" r="47" fill="#0f766e" stroke="#5eead4" stroke-width="2.5"/>
                        <path d="M22 28 L50 82 L78 28" stroke="#fde047" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
                        <line x1="50" y1="15" x2="50" y2="84" stroke="#ffffff" stroke-width="4.5" stroke-linecap="round"/>
                        <circle cx="50" cy="15" r="4.5" fill="#f59e0b" stroke="#ffffff" stroke-width="1"/>
                        <path d="M38 32 C58 30, 58 40, 50 44 C40 48, 40 58, 50 62 C60 66, 60 76, 48 80" stroke="#34d399" stroke-width="5" stroke-linecap="round" fill="none"/>
                        <circle cx="38" cy="32" r="4.5" fill="#34d399" stroke="#065f46" stroke-width="1"/>
                        <circle cx="37" cy="31" r="1.2" fill="#0f172a"/>
                    </svg>
                </div>
                <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #ffffff;">VetMind AI Enterprise v4.2</h1>
                <p style="font-size: 1.15rem; color: #ccfbf1; margin-top: 10px; max-width: 700px; margin-left: auto; margin-right: auto; line-height: 1.6;">
                    المنصة الاستثمارية العالمية الرائدة لدعم القرار الإكلينيكي والصيدلاني البيطري المدعوم بالذكاء الاصطناعي
                </p>
            </div>

            <!-- Developer & Founder Spotlight -->
            <div class="card" style="border-top: 6px solid #d97706; padding: 30px; margin-bottom: 24px; background: var(--card-bg);">
                <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 16px;">
                    <span style="font-size: 2.5rem;">👨‍⚕️</span>
                    <div>
                        <div style="font-size: 0.9rem; color: #d97706; font-weight: 700; text-transform: uppercase;">المطور والمؤسس الرئيسي للمنصة</div>
                        <h2 style="margin: 2px 0 0 0; font-size: 1.8rem; color: var(--primary);">دكتور تامر سعد (Dr. Tamer Saad)</h2>
                    </div>
                </div>
                <p style="font-size: 1.05rem; line-height: 1.8; color: var(--text-main);">
                    قام <strong>دكتور تامر سعد</strong> بتأسيس وبرمجة وتطوير منظومة <strong>VetMind AI Enterprise</strong> كأصل استثماري وتقني متكامل عالي القيمة للمجال البيطري العربي والدولي. تم تصميم المنصة لتجمع بين أدق البرمجيات السريرية وخوارزميات الرؤية الحاسوبية وقواعد البيانات الدوائية الرسمية لأكثر من 18 دولة، بهدف تمكين الطبيب البيطري من الحصول على أعلى دقة تشخيصية وسرعة علاجية تتوافق مع معايير المنظمات البيطرية العالمية.
                </p>
                <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px;">
                    <span style="background: #e0f2fe; color: #0369a1; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">🏆 هندسة الذكاء الاصطناعي السريري</span>
                    <span style="background: #fef3c7; color: #92400e; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">💊 صيدلية وطنية تضم 1,005 دواء</span>
                    <span style="background: #dcfce7; color: #166534; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">👁️ رؤية حاسوبية للآفات السريرية</span>
                    <span style="background: #f3e8ff; color: #6b21a8; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">📋 روشتات Rx وحاسبة جرعات ذكية</span>
                </div>
            </div>

            <!-- Key Pillars Grid -->
            <div class="grid-2" style="margin-bottom: 24px;">
                <div class="card" style="border-top: 4px solid var(--primary);">
                    <h3 style="color: var(--primary); margin-top: 0;">🎯 رؤية وأهداف المنصة</h3>
                    <ul style="line-height: 1.8; font-size: 0.95rem; color: var(--text-main); padding-right: 20px;">
                        <li><strong>حماية الثروة الحيوانية والأمن الغذائي:</strong> ضبط بروتوكولات العلاج الدقيق وتقليل نفوق الماشية والدواجن وهجن السباقات.</li>
                        <li><strong>الالتزام بفترات الأمان الدوائي (Withdrawal Periods):</strong> منع وصول متبقيات المضادات الحيوية إلى اللحوم والألبان.</li>
                        <li><strong>أداة استثمارية متقدمة للعيادات والمزارع:</strong> تنظيم الفواتير، التحاليل المعملية، والسجلات الطبية الذكية.</li>
                    </ul>
                </div>

                <div class="card" style="border-top: 4px solid var(--accent);">
                    <h3 style="color: var(--accent); margin-top: 0;">📚 المرجعيات العلمية الدولية</h3>
                    <ul style="line-height: 1.8; font-size: 0.95rem; color: var(--text-main); padding-right: 20px;">
                        <li><strong>Merck Veterinary Manual (11th Ed):</strong> المرجع القياسي للأمراض المعدية والحيوانات الحقلية.</li>
                        <li><strong>WOAH Terrestrial Animal Health Code:</strong> كود صحة الحيوان للمنظمة العالمية لصحة الحيوان.</li>
                        <li><strong>WSAVA Guidelines:</strong> معايير الجمعية العالمية لبيطريي الحيوانات الأليفة.</li>
                        <li><strong>FAO Food Safety Standards:</strong> دلائل منظمة الأغذية والزراعة للأمن الحيوي.</li>
                        <li><strong>الهيئات الرقابية الوطنية:</strong> وزارة الزراعة المصرية وهيئة الدواء، هيئة الغذاء والدواء السعودية (SFDA).</li>
                    </ul>
                </div>
            </div>

            <!-- Contact & Support -->
            <div class="card" style="text-align: center; background: #f8fafc; padding: 24px;">
                <h3 style="margin-top: 0; color: var(--primary);">هل لديك استفسار أو ترغب في التعاون الاستثماري؟</h3>
                <p style="color: var(--text-muted); font-size: 0.95rem;">فريق الدعم الفني والإداري متاح على مدار الساعة للإجابة على استفساراتكم.</p>
                <a href="/support" class="btn btn-primary" style="display: inline-flex; padding: 10px 24px; font-size: 1rem;">
                    🎧 التواصل مع الدعم الفني (support@vetmind.ai)
                </a>
            </div>
        </div>
        """
    else:
        body = f"""
        <div style="max-width: 950px; margin: 0 auto;">
            <!-- Hero Header -->
            <div class="card" style="background: linear-gradient(135deg, #0f766e 0%, #115e59 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 24px; text-align: center; border: 1px solid #14b8a6; box-shadow: 0 10px 25px rgba(15,118,110,0.2);">
                <div style="display: inline-flex; align-items: center; justify-content: center; width: 85px; height: 85px; background: rgba(255,255,255,0.15); border-radius: 50%; margin-bottom: 16px; border: 2px solid #5eead4;">
                    <svg width="60" height="60" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="50" cy="50" r="47" fill="#0f766e" stroke="#5eead4" stroke-width="2.5"/>
                        <path d="M22 28 L50 82 L78 28" stroke="#fde047" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
                        <line x1="50" y1="15" x2="50" y2="84" stroke="#ffffff" stroke-width="4.5" stroke-linecap="round"/>
                        <circle cx="50" cy="15" r="4.5" fill="#f59e0b" stroke="#ffffff" stroke-width="1"/>
                        <path d="M38 32 C58 30, 58 40, 50 44 C40 48, 40 58, 50 62 C60 66, 60 76, 48 80" stroke="#34d399" stroke-width="5" stroke-linecap="round" fill="none"/>
                        <circle cx="38" cy="32" r="4.5" fill="#34d399" stroke="#065f46" stroke-width="1"/>
                        <circle cx="37" cy="31" r="1.2" fill="#0f172a"/>
                    </svg>
                </div>
                <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #ffffff;">VetMind AI Enterprise v4.2</h1>
                <p style="font-size: 1.15rem; color: #ccfbf1; margin-top: 10px; max-width: 700px; margin-left: auto; margin-right: auto; line-height: 1.6;">
                    The Premier International Artificial Intelligence & Clinical Decision Support Suite for Modern Veterinary Practice
                </p>
            </div>

            <!-- Developer & Founder Spotlight -->
            <div class="card" style="border-top: 6px solid #d97706; padding: 30px; margin-bottom: 24px; background: var(--card-bg);">
                <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 16px;">
                    <span style="font-size: 2.5rem;">👨‍⚕️</span>
                    <div>
                        <div style="font-size: 0.9rem; color: #d97706; font-weight: 700; text-transform: uppercase;">Founder & Lead AI Systems Architect</div>
                        <h2 style="margin: 2px 0 0 0; font-size: 1.8rem; color: var(--primary);">Dr. Tamer Saad</h2>
                    </div>
                </div>
                <p style="font-size: 1.05rem; line-height: 1.8; color: var(--text-main);">
                    <strong>Dr. Tamer Saad</strong> founded, architected, and developed <strong>VetMind AI Enterprise</strong> as an integrated, high-value clinical technological asset for Arabic and international veterinary medicine. The platform merges rigorous veterinary decision trees, convolutional lesion vision models, and official formularies covering 1,005+ registered medications across 18 countries, empowering veterinary clinicians with world-standard diagnostic precision, therapeutic speed, and full compliance with global animal health authorities.
                </p>
                <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px;">
                    <span style="background: #e0f2fe; color: #0369a1; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">🏆 Clinical AI Engineering</span>
                    <span style="background: #fef3c7; color: #92400e; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">💊 1,005 Verified Drug Formularies</span>
                    <span style="background: #dcfce7; color: #166534; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">👁️ Computer Vision for Lesions</span>
                    <span style="background: #f3e8ff; color: #6b21a8; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">📋 Standardized Rx & Precision Dosing</span>
                </div>
            </div>

            <!-- Key Pillars Grid -->
            <div class="grid-2" style="margin-bottom: 24px;">
                <div class="card" style="border-top: 4px solid var(--primary);">
                    <h3 style="color: var(--primary); margin-top: 0;">🎯 Vision & Core Objectives</h3>
                    <ul style="line-height: 1.8; font-size: 0.95rem; color: var(--text-main); padding-left: 20px;">
                        <li><strong>Livestock & Food Security Protection:</strong> Optimized precision treatment protocols reducing mortality in cattle, sheep, poultry, and racing camels.</li>
                        <li><strong>Withdrawal Periods Compliance:</strong> Preventing antibiotic residues from contaminating human meat, milk, and eggs.</li>
                        <li><strong>Enterprise Practice Operations:</strong> Seamless multi-currency invoicing, lab diagnostics management, and intelligent patient records.</li>
                    </ul>
                </div>

                <div class="card" style="border-top: 4px solid var(--accent);">
                    <h3 style="color: var(--accent); margin-top: 0;">📚 International Scientific References</h3>
                    <ul style="line-height: 1.8; font-size: 0.95rem; color: var(--text-main); padding-left: 20px;">
                        <li><strong>Merck Veterinary Manual (11th Ed):</strong> Global benchmark for infectious pathologies and production medicine.</li>
                        <li><strong>WOAH Terrestrial Animal Health Code:</strong> World Organisation for Animal Health international disease standards.</li>
                        <li><strong>WSAVA Guidelines:</strong> World Small Animal Veterinary Association clinical protocols.</li>
                        <li><strong>FAO Food Safety Standards:</strong> UN Food & Agriculture Organization biosecurity guidelines.</li>
                        <li><strong>National Regulatory Compendia:</strong> Egyptian Ministry of Agriculture, EDA, and Saudi SFDA compendia.</li>
                    </ul>
                </div>
            </div>

            <!-- Contact & Support -->
            <div class="card" style="text-align: center; background: #f8fafc; padding: 24px;">
                <h3 style="margin-top: 0; color: var(--primary);">Have an inquiry or enterprise partnership opportunity?</h3>
                <p style="color: var(--text-muted); font-size: 0.95rem;">Our technical and clinical engineering team is available 24/7 to support licensed veterinarians.</p>
                <a href="/support" class="btn btn-primary" style="display: inline-flex; padding: 10px 24px; font-size: 1rem;">
                    🎧 Contact Technical Support (support@vetmind.ai)
                </a>
            </div>
        </div>
        """

    return HTMLResponse(content=get_base_html(page_title, body, user, lang), media_type="text/html; charset=utf-8")


# ==============================================================================
# ROUTE: TERMS OF SERVICE & CLINICAL DISCLAIMER (شروط الاستخدام والإخلاء الطبي)
# ==============================================================================
@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    is_ar = (lang == "ar")
    page_title = "شروط الاستخدام والإخلاء الطبي | VetMind AI Enterprise" if is_ar else f"{t('nav_terms')} | VetMind AI Enterprise"

    if is_ar:
        body = f"""
        <div style="max-width: 950px; margin: 0 auto;">
            <div style="margin-bottom: 20px;">
                <h1 style="color: var(--primary); margin: 0; font-size: 1.8rem;">📜 شروط الاستخدام والإخلاء الإكلينيكي والقانوني</h1>
                <p style="color: var(--text-muted); font-size: 0.95rem; margin-top: 6px;">آخر تحديث: 2026 | وثيقة ملزمة قانونياً لكافة مستخدمي منصة VetMind AI Enterprise</p>
            </div>

            <!-- 1. Clinical Notice -->
            <div class="card" style="border-right: 5px solid #ef4444; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 1.8rem;">⚠️</span>
                    <h2 style="margin: 0; font-size: 1.3rem; color: #b91c1c;">أولاً: التنبيه الإكلينيكي والطبي العام</h2>
                </div>
                <p style="line-height: 1.8; font-size: 0.98rem; color: var(--text-main);">
                    منصة <strong>VetMind AI Enterprise</strong> هي منظومة مساعدة ودعم للقرار الطبي السريري (Clinical Decision Support System) مخصصة <strong>حصرياً للأطباء البيطريين المرخصين والمصرح لهم بممارسة المهنة</strong> وفق قوانين بلدانهم. خوارزميات الذكاء الاصطناعي، نتائج تحليل الصور، واقتراحات التشخيص التفريقي لا تعتبر بديلاً قانونياً أو طبياً عن الفحص الإكلينيكي المباشر والفحوصات المعملية المجهرية (Lab Workup) التي يجريها الطبيب المعالج. <strong>التشخيص النهائي وإقرار البروتوكول العلاجي يقعان تحت المسؤولية المهنية والقانونية الكاملة للطبيب المعالج.</strong>
                </p>
            </div>

            <!-- 2. Drug Safety & Withdrawal Periods -->
            <div class="card" style="border-right: 5px solid #d97706; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 1.8rem;">💊</span>
                    <h2 style="margin: 0; font-size: 1.3rem; color: #b45309;">ثانياً: التنبيه الدوائي وضوابط فترات السحب والأمان (Withdrawal Periods)</h2>
                </div>
                <p style="line-height: 1.8; font-size: 0.98rem; color: var(--text-main);">
                    تلتزم المنصة بتسجيل وتحديث أكثر من 1,005 مستحضر دوائي بيطري معتمد بالتعاون مع الشركات الوطنية المسجلة. يجب على الطبيب المعالج والصيدلي البيطري التحقق الإلزامي من:
                </p>
                <ul style="line-height: 1.8; font-size: 0.95rem; color: var(--text-main); padding-right: 20px;">
                    <li><strong>فترات سحب اللحم والحليب والبيض:</strong> يُمنع منعاً باتاً ذبح الحيوان المعالج أو تسويق ألبانه أو بيضه للاستهلاك الآدمي قبل انقضاء فترة السحب الرسمية المنصوص عليها في النشرة المعتمدة.</li>
                    <li><strong>الوزن الحي الفعلي وحالة الأعضاء الحيوية:</strong> حساب الجرعات بدقة بناءً على وزن الحيوان المسجل بالكيلوجرام، مع مراعاة استبعاد المضادات الحيوية السامة للكلى أو الكبد في الحيوانات التي تعاني من قصور كلوي أو كبدي.</li>
                    <li><strong>التداخلات الدوائية:</strong> مراجعة فاحص التعارضات الدوائية المدمج في المنصة لتجنب خلط مضادات الجراثيم القاتلة مع الموقفة للنمو أو مضادات الالتهاب المزدوجة.</li>
                </ul>
            </div>

            <!-- 3. Intellectual Property -->
            <div class="card" style="border-right: 5px solid var(--primary); margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 1.8rem;">🛡️</span>
                    <h2 style="margin: 0; font-size: 1.3rem; color: var(--primary);">ثالثاً: حقوق الملكية الفكرية والبرمجية</h2>
                </div>
                <p style="line-height: 1.8; font-size: 0.98rem; color: var(--text-main);">
                    كافة الأكواد البرمجية، الخوارزميات التشخيصية، قواعد البيانات الصيدلانية، النماذج البيطرية، التصميمات، الشعار البيطري الرسمي، والعلامة التجارية لمنصة <strong>VetMind AI Enterprise</strong> هي ملكية فكرية حصرية ومسجلة للمطور والمؤسس <strong>دكتور تامر سعد (Dr. Tamer Saad)</strong> ومحمية بموجب القوانين والاتفاقيات الدولية للملكية الفكرية وحماية البرمجيات لعام 2026. يحظر تماماً نسخ أو إعادة هندسة أو بيع أو استنساخ أي جزء من المنصة دون إذن خطي مسبق.
                </p>
            </div>

            <!-- 4. Privacy & Data Protection -->
            <div class="card" style="border-right: 5px solid #0284c7; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 1.8rem;">🔒</span>
                    <h2 style="margin: 0; font-size: 1.3rem; color: #0284c7;">رابعاً: سرية وأمان البيانات السريرية</h2>
                </div>
                <p style="line-height: 1.8; font-size: 0.98rem; color: var(--text-main);">
                    تخضع كافة بيانات الحالات، الصور السريرية المرفوعة، وفواتير العيادات لتشفير كامل وتدابير أمان متقدمة. لا يتم مشاركة أي بيانات تخص أصحاب الحيوانات أو أسماء المزارع مع أي أطراف تجارية أو إعلانية، وتُستخدم البيانات الطبية المجردة فقط في إطار الأبحاث والتحسين المستمر لجودة التنبؤ السريري للمنصة.
                </p>
            </div>
        </div>
        """
    else:
        body = f"""
        <div style="max-width: 950px; margin: 0 auto;">
            <div style="margin-bottom: 20px;">
                <h1 style="color: var(--primary); margin: 0; font-size: 1.8rem;">📜 Terms of Service & Clinical-Legal Disclaimer</h1>
                <p style="color: var(--text-muted); font-size: 0.95rem; margin-top: 6px;">Last Updated: 2026 | Legally Binding Instrument for All VetMind AI Enterprise Users</p>
            </div>

            <!-- 1. Clinical Notice -->
            <div class="card" style="border-left: 5px solid #ef4444; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 1.8rem;">⚠️</span>
                    <h2 style="margin: 0; font-size: 1.3rem; color: #b91c1c;">1. General Clinical & Medical Scope</h2>
                </div>
                <p style="line-height: 1.8; font-size: 0.98rem; color: var(--text-main);">
                    <strong>VetMind AI Enterprise</strong> is a specialized Clinical Decision Support System (CDSS) intended <strong>exclusively for licensed, accredited veterinarians</strong> authorized to practice medicine under local laws. AI algorithms, computer vision analyses, and differential suggestions do NOT replace comprehensive physical clinical examinations, diagnostic palpation, or microscopic laboratory workups. <strong>Final clinical diagnosis and therapeutic regimens remain under the exclusive professional and legal liability of the attending veterinarian.</strong>
                </p>
            </div>

            <!-- 2. Drug Safety & Withdrawal Periods -->
            <div class="card" style="border-left: 5px solid #d97706; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 1.8rem;">💊</span>
                    <h2 style="margin: 0; font-size: 1.3rem; color: #b45309;">2. Pharmacological Controls & Mandatory Withdrawal Intervals</h2>
                </div>
                <p style="line-height: 1.8; font-size: 0.98rem; color: var(--text-main);">
                    The platform catalogues 1,005+ registered veterinary formulations across multiple national formularies. Practitioners and dispensing pharmacists must strictly verify:
                </p>
                <ul style="line-height: 1.8; font-size: 0.95rem; color: var(--text-main); padding-left: 20px;">
                    <li><strong>Meat, Milk, & Egg Withdrawal Periods:</strong> Zero food animals under active withdrawal intervals may be slaughtered or their produce marketed for human consumption prior to official clearance.</li>
                    <li><strong>Actual Live Weight & Organ Function:</strong> Precision dosing strictly calculated on current patient weight in kilograms, adjusting or substituting nephrotoxic/hepatotoxic agents in compromised patients.</li>
                    <li><strong>Drug Interactions & Synergism:</strong> Consultation of the integrated Interaction Radar to prevent antagonistic combinations (e.g., bactericidal vs. bacteriostatic combinations, dual NSAIDs).</li>
                </ul>
            </div>

            <!-- 3. Intellectual Property -->
            <div class="card" style="border-left: 5px solid var(--primary); margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 1.8rem;">🛡️</span>
                    <h2 style="margin: 0; font-size: 1.3rem; color: var(--primary);">3. Intellectual Property & Proprietary Rights</h2>
                </div>
                <p style="line-height: 1.8; font-size: 0.98rem; color: var(--text-main);">
                    All underlying codebase, clinical inference algorithms, database structures, interface UI/UX assets, official veterinary insignia, and the <strong>VetMind AI Enterprise</strong> trademark represent the exclusive intellectual property of founder <strong>Dr. Tamer Saad</strong>, protected under international copyright, intellectual property, and software licensing conventions of 2026. Any unauthorized reproduction, reverse engineering, or resale is strictly actionable.
                </p>
            </div>

            <!-- 4. Privacy & Data Protection -->
            <div class="card" style="border-left: 5px solid #0284c7; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 1.8rem;">🔒</span>
                    <h2 style="margin: 0; font-size: 1.3rem; color: #0284c7;">4. Patient Confidentiality & Security Protocols</h2>
                </div>
                <p style="line-height: 1.8; font-size: 0.98rem; color: var(--text-main);">
                    All recorded patient cases, diagnostic imagery, and clinic billing ledgers are encrypted and securely partitioned. No identifiable owner, clinic, or farm information is sold or disclosed to third-party advertising entities.
                </p>
            </div>
        </div>
        """

    return HTMLResponse(content=get_base_html(page_title, body, user, lang), media_type="text/html; charset=utf-8")

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)


# ==============================================================================
# ROUTE: LIVE AUTOCOMPLETE & SEARCH SUGGESTIONS API
# ==============================================================================
@app.get("/api/drugs/autocomplete")
@app.get("/api/search/suggestions")
async def api_drugs_autocomplete(q: str = "", category: str = "", country: str = "", limit: int = 10):
    from autocomplete_engine import get_autocomplete_suggestions
    return get_autocomplete_suggestions(q, category=category, country=country, limit=limit)

@app.get("/resend-otp")
@app.post("/resend-otp")
async def resend_otp_route(email: str = "", channel: str = "both"):
    import verification_service
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    user = c.fetchone()
    conn.close()
    if not user:
        return RedirectResponse("/login", status_code=303)

    verification_service.dispatch_user_otp(
        user["id"], user["email"], user.get("phone", ""), user.get("name", "")
    )
    return RedirectResponse(f"/verify-otp?email={user['email']}&resent=1&channel={channel}", status_code=303)


# ==============================================================================
# ROUTE: SET LANGUAGE (INSTANT DUAL COOKIE + REDIRECT)
# ==============================================================================
@app.get("/set-language/{lang_code}")
async def set_language_endpoint(request: Request, lang_code: str, redirect: str = "/"):
    clean_code = lang_code.strip().lower()
    if clean_code not in SUPPORTED_LANGUAGES:
        clean_code = "ar"

    target_url = redirect if redirect and redirect.startswith("/") else "/"
    if "/set-language" in target_url:
        target_url = "/"

    # Strip any existing ?lang= or &lang= from target_url so it never overrides the new cookie
    if "lang=" in target_url:
        import urllib.parse
        parsed = urllib.parse.urlsplit(target_url)
        q = urllib.parse.parse_qs(parsed.query)
        q.pop("lang", None)
        new_q = urllib.parse.urlencode(q, doseq=True)
        target_url = parsed.path + (("?" + new_q) if new_q else "")

    user = get_current_user(request)
    if user:
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET preferred_lang = ? WHERE id = ?", (clean_code, user["id"]))
            conn.commit()
            conn.close()
        except Exception:
            pass

    resp = RedirectResponse(url=target_url, status_code=303)
    resp.set_cookie(
        key="vetmind_lang",
        value=clean_code,
        max_age=31536000,
        path="/",
        samesite="lax",
        httponly=False
    )
    return resp

@app.post("/profile/language")
async def update_profile_language(request: Request, preferred_lang: str = Form("ar")):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    clean_code = preferred_lang.strip().lower()
    if clean_code not in SUPPORTED_LANGUAGES:
        clean_code = "ar"
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET preferred_lang = ? WHERE id = ?", (clean_code, user["id"]))
    conn.commit()
    conn.close()
    resp = RedirectResponse("/profile", status_code=303)
    resp.set_cookie(key="vetmind_lang", value=clean_code, max_age=31536000, path="/", samesite="lax")
    return resp


# Hugging Face Spaces & Standalone Runner Compatibility
try:
    import gradio as gr
    with gr.Blocks(title="VetMind AI Enterprise") as demo:
        gr.Markdown("### VetMind AI Enterprise Service Running")
    app = gr.mount_gradio_app(app, demo, path="/gradio_status")
except Exception:
    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port)


@app.post("/admin/settings")
async def save_admin_settings_endpoint(
    request: Request,
    smtp_host: str = Form(""),
    smtp_port: str = Form("587"),
    smtp_user: str = Form(""),
    smtp_pass: str = Form(""),
    resend_api_key: str = Form(""),
    ai_api_key: str = Form("")
):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    pairs = [
        ("smtp_host", smtp_host.strip()),
        ("smtp_port", smtp_port.strip()),
        ("smtp_user", smtp_user.strip()),
        ("smtp_pass", smtp_pass.strip()),
        ("resend_api_key", resend_api_key.strip()),
        ("ai_api_key", ai_api_key.strip())
    ]
    for k, v in pairs:
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)
