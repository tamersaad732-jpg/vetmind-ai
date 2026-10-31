import os
import re
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

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
        c.execute("""
        SELECT id FROM community_subscriptions 
        WHERE user_id = ? AND status = 'approved'
        ORDER BY id DESC LIMIT 1
        """, (user_id,))
        row = c.fetchone()
        conn.close()
        return bool(row)
    except Exception:
        return False

def get_user_community_sub(user_id: int):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
        SELECT * FROM community_subscriptions 
        WHERE user_id = ? 
        ORDER BY id DESC LIMIT 1
        """, (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None

def extract_youtube_embed(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    m = re.search(r'(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})', url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}"
    return ""

# ==============================================================================
# ALGORITHM ENGINE: CLINICAL CONTENT QUALITY & ENGAGEMENT VIRALITY
# ==============================================================================
def evaluate_clinical_content(title: str, content: str, has_media: bool) -> dict:
    """
    Algorithmic Content Quality & Veterinary Clinical Authenticity Scorer.
    Evaluates clinical vocabulary depth, species identification, diagnostic rigor,
    treatment protocol, and media evidence.
    """
    text = (title + " " + content).lower()
    score = 40  # Base entry score
    reasons = []

    # 1. Veterinary & Clinical Medical Terms
    clinical_terms = [
        "أعراض", "فحص", "تشخيص", "علاج", "جرعة", "حرارة", "التهاب", "ورم", "كسر", "جراحة",
        "تخدير", "سونار", "أشعة", "ميكروسكوب", "بكتيريا", "فيروس", "دم", "عينة", "صديد",
        "تقرح", "نزف", "مضاد حيوي", "خياطة", "أمعاء", "معدة", "رئة", "كبد", "كلية", "ضرع",
        "حافر", "عضل", "وريد", "مفصل", "تنفس", "نبض", "سحب", "تحصين", "مناعة", "مسكن",
        "symptoms", "diagnosis", "treatment", "dose", "surgery", "anesthesia", "ultrasound", "infection"
    ]
    matched_clinical = [t for t in clinical_terms if t in text]
    if len(matched_clinical) >= 6:
        score += 25
        reasons.append("عمق سريري ومصطلحات طبية متخصصة (+25%)")
    elif len(matched_clinical) >= 3:
        score += 15
        reasons.append("مصطلحات بيطرية إكلينيكية أساسية (+15%)")

    # 2. Species Identification
    species_terms = [
        "بقر", "أبقار", "عجل", "عجول", "خيل", "خيول", "فرس", "مهر", "حمار", "غنم", "أغنام",
        "خروف", "نعجة", "ماعز", "جدي", "إبل", "هجن", "ناقة", "جمل", "كلب", "كلاب", "قطط",
        "قطة", "دواجن", "فراخ", "دجاج", "طيور", "أرانب", "أسماك", "bovine", "equine", "canine", "feline"
    ]
    matched_species = [s for s in species_terms if s in text]
    if matched_species:
        score += 15
        reasons.append(f"تحديد الفصيلة الحيوانية ({matched_species[0]}) (+15%)")

    # 3. Content Length & Explanation Depth
    words_count = len(text.split())
    if words_count >= 80:
        score += 15
        reasons.append("شرح سريري وافٍ ومفصل (+15%)")
    elif words_count >= 30:
        score += 10
        reasons.append("وصف سريري موجز (+10%)")

    # 4. Clinical Evidence (Media Photo/Video)
    if has_media:
        score += 20
        reasons.append("توثيق مرئي ومجهري (+20%)")

    score = min(100, score)

    if score >= 85:
        badge = f"🌟 توثيق سريري فائق ({score}%)"
        badge_style = "background: #ecfdf5; color: #047857; border: 1px solid #6ee7b7;"
    elif score >= 70:
        badge = f"✅ معتمد إكلينيكياً ({score}%)"
        badge_style = "background: #eff6ff; color: #1d4ed8; border: 1px solid #93c5fd;"
    else:
        badge = f"📄 منشور عام ({score}%)"
        badge_style = "background: #f8fafc; color: #475569; border: 1px solid #cbd5e1;"

    return {
        "score": score,
        "badge": badge,
        "badge_style": badge_style,
        "reasons": reasons
    }

def compute_virality_score(post_dict: dict) -> float:
    """
    Algorithmic Engagement & Reach Expansion Formula.
    Ranks posts based on Likes, Comments, Saves, Views, Quality, and Time Decay.
    Posts with high virality get promoted to more doctors across the network.
    """
    likes = post_dict.get("likes_count", 0)
    comments = post_dict.get("comments_count", 0)
    views = post_dict.get("views_count", 0)
    shares = post_dict.get("shares_count", 0)
    quality = post_dict.get("quality_score", 70)
    is_boosted = post_dict.get("is_boosted", 0)
    is_pinned = post_dict.get("is_pinned", 0)

    # Engagement numerator
    raw_engagement = (likes * 4.0) + (comments * 6.0) + (shares * 5.0) + (views * 0.15)
    
    # Boost / Pin bonus
    if is_pinned:
        return 10000.0 + raw_engagement
    if is_boosted:
        raw_engagement += 300.0  # Reach expansion boost

    # Quality factor (80% to 120%)
    quality_factor = (quality / 100.0) * 0.4 + 0.8
    total_score = raw_engagement * quality_factor

    # Time decay (hours since creation)
    created_at_str = post_dict.get("created_at", "")
    age_hours = 1.0
    try:
        post_time = datetime.strptime(created_at_str[:19], "%Y-%m-%d %H:%M:%S")
        age_hours = max(0.5, (datetime.now() - post_time).total_seconds() / 3600.0)
    except Exception:
        pass

    # Gravity formula: score / (hours + 2)^1.25
    rank = total_score / ((age_hours + 2.0) ** 1.25)
    return round(rank, 4)

CATEGORIES = {
    "all": {"name": "كافة الأخبار والحالات", "color": "#0f766e", "icon": "📰"},
    "videos": {"name": "Vet Watch (فيديوهات وجراحات)", "color": "#dc2626", "icon": "🎥"},
    "photos": {"name": "معرض الآفات المجهرية", "color": "#e11d48", "icon": "📸"},
    "case_study": {"name": "حالات سريرية نادرة", "color": "#ea580c", "icon": "🔬"},
    "surgery": {"name": "جراحة وتخدير حيواني", "color": "#0891b2", "icon": "🩺"},
    "clinical_article": {"name": "مقالات وأبحاث موثقة", "color": "#059669", "icon": "📚"},
    "drug_experience": {"name": "تجارب دوائية وحقلية", "color": "#7c3aed", "icon": "💊"},
    "consultation": {"name": "استشارات عاجلة للزملاء", "color": "#d97706", "icon": "❓"},
    "bookmarks": {"name": "الحالات المحفوظة (Saved)", "color": "#b45309", "icon": "🔖"},
    "my_posts": {"name": "منشوراتي وحالاتي", "color": "#0f766e", "icon": "📝"},
}

PLANS = {
    "monthly": {
        "name": "الباقة الشهرية (Monthly Plan)",
        "price": "150 ج.م",
        "amount": 150.0,
        "period": "شهرياً",
        "badge": "مرنة",
        "features": ["وصول كامل لشبكة فيتبوك السريرية", "مشاركة مقاطع الفيديو والصور المجهرية", "التعليق والمناقشة المتبادلة مع الاستشاريين"]
    },
    "semi_annual": {
        "name": "الباقة نصف السنوية (Semi-Annual)",
        "price": "750 ج.م",
        "amount": 750.0,
        "period": "كل 6 أشهر (وفر 150 ج.م)",
        "badge": "توفير مميز",
        "features": ["كافة مزايا الباقة الشهرية", "أولوية الرد في الاستشارات الإكلينيكية", "رفع مقاطع فيديو العمليات الجراحية بدقة عالية"]
    },
    "annual": {
        "name": "الباقة السنوية الذهبية (Annual VIP)",
        "price": "1,200 ج.م",
        "amount": 1200.0,
        "period": "سنوياً (وفر 600 ج.م)",
        "badge": "⭐ الأكثر طلباً",
        "features": ["وصول غير محدود لجميع الحالات ومقاطع الفيديو", "شارة [طبيب معتمد VIP ⭐] موثقة بجانب اسمك", "إمكانية تثبيت الحالات السريرية الهامة", "استشارات حصرية ومباشرة مع كبار الخبراء"]
    },
    "lifetime": {
        "name": "العضوية الدائمة (Lifetime Access)",
        "price": "2,500 ج.م",
        "amount": 2500.0,
        "period": "دفعة واحدة مدى الحياة",
        "badge": "مدى الحياة Pro",
        "features": ["وصول دائم وشامل لملتقى فيتبوك مدى الحياة", "كافة التحديثات والميزات المستقبلية مجاناً", "شارة [عضو مؤسس مدى الحياة 🏆]"]
    }
}

# ==============================================================================
# ROUTE: GET /community (VetBook - Facebook with Smart Reach Algorithm)
# ==============================================================================
@router.get("/community", response_class=HTMLResponse)
async def community_hub(request: Request, category: str = "all", q: str = "", sort: str = "algorithmic", status_msg: str = ""):
    from app import get_current_user, get_user_lang, get_text, get_base_html

    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    if not user:
        login_prompt = f"""
        <div class="card" style="max-width: 620px; width: 100%; box-sizing: border-box; margin: 30px auto; text-align: center; border-top: 5px solid #0f766e; padding: clamp(24px, 5vw, 40px) clamp(16px, 4vw, 24px); border-radius: 16px; box-shadow: 0 8px 24px rgba(15,118,110,0.12); word-break: break-word;">
            <div style="width: 80px; height: 80px; border-radius: 20px; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-size: 2.8rem; font-weight: 800; margin: 0 auto 16px auto; box-shadow: 0 4px 14px rgba(15,118,110,0.3);">
                V
            </div>
            <h2 style="color: #0f766e; font-size: 1.8rem; margin-bottom: 8px;">VetBook الأطباء البيطريين</h2>
            <p style="color: var(--text-muted); font-size: 1.05rem; line-height: 1.8; margin-bottom: 26px;">
                المنصة الاجتماعية والسريرية الأولى المخصصة حصرياً للأطباء البيطريين لنشر الحالات، الفيديوهات الجراحية، والصور المجهرية، مع خوارزميات ذكية لتوسيع انتشار المحتوى عالي التفاعل.
            </p>
            <div style="display: flex; justify-content: center; gap: 14px; flex-wrap: wrap;">
                <a href="/login?redirect=/community" class="btn btn-primary" style="padding: 12px 28px; font-size: 1rem; border-radius: 25px;">🔑 تسجيل الدخول للطبيب</a>
                <a href="/register?redirect=/community" class="btn btn-accent" style="padding: 12px 28px; font-size: 1rem; border-radius: 25px;">📝 تسجيل حساب طبيب جديد</a>
            </div>
        </div>
        """
        return HTMLResponse(content=get_base_html("VetBook | ملتقى الأطباء", login_prompt, None, lang), media_type="text/html; charset=utf-8")

    approved = is_user_community_approved(user)

    # If NOT approved -> Paywall Hub
    if not approved:
        sub = get_user_community_sub(user["id"])
        
        status_banner = ""
        if status_msg == "submitted":
            status_banner = """
            <div style="background: #ecfdf5; border: 2px solid #6ee7b7; color: #065f46; border-radius: 12px; padding: 16px 20px; margin-bottom: 24px; font-weight: 700; display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.6rem;">✅</span>
                <div>
                    <div>تم استلام إيصال السداد وبيانات الاشتراك في شبكة VetBook الأطباء البيطريين!</div>
                    <div style="font-size: 0.88rem; font-weight: normal; margin-top: 3px;">الطلب قيد المراجعة الفورية من قبل إدارة المنصة (تامر سعد (Admin))، وسيتم تفعيل حسابك فور مطابقة التحويل.</div>
                </div>
            </div>
            """

        pending_box = ""
        if sub and sub.get("status") == "pending":
            receipt_preview = f'<a href="/uploads/{sub["receipt_image"]}" target="_blank" style="display: inline-block; margin-top: 8px; font-weight: 700; color: var(--primary);">📄 معاينة إيصال السداد المرفوع</a>' if sub.get("receipt_image") else ""
            pending_box = f"""
            <div class="card" style="background: #fffbeb; border: 2px solid #fde68a; border-radius: 14px; padding: 22px; margin-bottom: 28px;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <span style="font-size: 2rem;">⏳</span>
                    <div>
                        <h3 style="margin: 0; color: #92400e; font-size: 1.25rem;">طلب اشتراكك في VetBook الأطباء البيطريين قيد المراجعة والاعتماد</h3>
                        <div style="font-size: 0.85rem; color: #b45309;">تاريخ التقديم: {sub.get('created_at')} | رقم الطلب: #{sub.get('id')}</div>
                    </div>
                </div>
                <div style="font-size: 0.95rem; color: #78350f; line-height: 1.8;">
                    <strong>الباقة المختارة:</strong> {sub.get('plan_name')} ({sub.get('amount')} ج.م)<br>
                    <strong>وسيلة الدفع:</strong> {sub.get('payment_method')} | <strong>المرجع / المحفظة:</strong> {sub.get('transaction_ref')}<br>
                    {receipt_preview}
                </div>
                <div style="margin-top: 14px; padding: 10px; background: rgba(217, 119, 6, 0.1); border-radius: 8px; font-size: 0.85rem; color: #92400e;">
                    💡 بياناتك وإيصالك معروضان الآن في لوحة تحكم إدارة المنصة (تامر سعد (Admin)). يتم تفعيل الوصول فور التحقق من العملية.
                </div>
            </div>
            """
        elif sub and sub.get("status") == "rejected":
            pending_box = f"""
            <div class="card" style="background: #fef2f2; border: 2px solid #fca5a5; border-radius: 14px; padding: 22px; margin-bottom: 28px;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                    <span style="font-size: 2rem;">❌</span>
                    <h3 style="margin: 0; color: #991b1b; font-size: 1.2rem;">تنبيه: تم رفض إيصال السداد السابق</h3>
                </div>
                <div style="font-size: 0.92rem; color: #7f1d1d; line-height: 1.7;">
                    <strong>ملاحظات الإدارة:</strong> {sub.get('admin_notes') or 'الإيصال المرفق غير واضح أو لم يتم العثور على العملية في الحساب البنكي / المحفظة.'}<br>
                    يرجى إعادة التأكد من رقم العملية ورفع صورة واضحة لإشعار التحويل أدناه.
                </div>
            </div>
            """

        plans_html = ""
        for pid, pdata in PLANS.items():
            badge_style = "background: #ea580c; color: white;" if pid == "annual" else "background: #e0f2fe; color: #0369a1;"
            features_li = "".join([f"<li style='margin-bottom: 6px;'>✓ {f}</li>" for f in pdata["features"]])
            plans_html += f"""
            <div class="card" style="display: flex; flex-direction: column; justify-content: space-between; border-top: 4px solid {'#ea580c' if pid == 'annual' else 'var(--primary)'}; position: relative;">
                <div>
                    <span style="position: absolute; top: 12px; left: 12px; font-size: 0.72rem; font-weight: 800; padding: 3px 8px; border-radius: 12px; {badge_style}">{pdata['badge']}</span>
                    <h3 style="margin-top: 10px; font-size: 1.15rem; color: var(--primary);">{pdata['name']}</h3>
                    <div style="font-size: 1.8rem; font-weight: 800; color: var(--accent); margin: 8px 0;">{pdata['price']}</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 14px;">{pdata['period']}</div>
                    <ul style="padding-right: 18px; font-size: 0.85rem; color: var(--text-main); line-height: 1.6;">
                        {features_li}
                    </ul>
                </div>
                <button type="button" onclick="selectPlan('{pid}', '{pdata['name']}', '{pdata['amount']}')" class="btn btn-primary" style="width: 100%; justify-content: center; margin-top: 16px;">اختيار هذه الباقة 💳</button>
            </div>
            """

        body = f"""
        <div style="max-width: 1100px; width: 100%; margin: 0 auto; box-sizing: border-box; overflow-x: hidden; word-break: break-word;">
            {status_banner}
            {pending_box}

            <div style="text-align: center; margin-bottom: 30px;">
                <div style="width: 72px; height: 72px; border-radius: 18px; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-size: 2.4rem; font-weight: 800; margin: 0 auto 12px auto; box-shadow: 0 4px 14px rgba(15,118,110,0.3);">
                    V
                </div>
                <h1 style="margin: 6px 0 10px 0; font-size: 2.1rem; color: #0f766e;">VetBook الأطباء البيطريين</h1>
                <p style="max-width: 760px; margin: 0 auto; color: var(--text-muted); font-size: 1.05rem; line-height: 1.7;">
                    مجتمع إكلينيكي مغلق ومدفوع مصمم بنمط شبكة اجتماعية سريرية تفاعلية متطورة لنشر الحالات، الفيديوهات الجراحية، والصور المجهرية، مع خوارزميات ذكية لتوسيع رواج المنشورات الإكلينيكية الأكثر تفاعلاً وجودة.
                </p>
            </div>

            <div class="grid-3" style="margin-bottom: 32px;">
                <div class="card" style="text-align: center; background: #f8fafc;">
                    <div style="font-size: 2.2rem; margin-bottom: 8px;">🎥</div>
                    <h4 style="margin: 0 0 6px 0; color: #0f766e;">Vet Watch (فيديوهات الجراحة)</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin: 0;">بث وتشغيل مقاطع فيديو العمليات الجراحية، الفحص بالسونار، والمناظير البيطرية مع عداد المشاهدات.</p>
                </div>
                <div class="card" style="text-align: center; background: #f8fafc;">
                    <div style="font-size: 2.2rem; margin-bottom: 8px;">🧠</div>
                    <h4 style="margin: 0 0 6px 0; color: #0f766e;">خوارزميات الانتشار الذكي</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin: 0;">خوارزميات مخصصة ترقي الحالات المتميزة وتوسع وصولها للأطباء بناءً على عمق التفاعل العلمي.</p>
                </div>
                <div class="card" style="text-align: center; background: #f8fafc;">
                    <div style="font-size: 2.2rem; margin-bottom: 8px;">💬</div>
                    <h4 style="margin: 0 0 6px 0; color: #0f766e;">ردود متسلسلة وتفاعل مباشر</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin: 0;">نظام تعليقات وردود شجري يتيح للأطباء التعليق ولصاحب الحالة الرد الفوري والتوجيه الإكلينيكي.</p>
                </div>
            </div>

            <h2 style="text-align: center; color: var(--primary); margin-bottom: 20px;">💎 باقات الاشتراك في مجتمع فيتبوك</h2>
            <div class="grid-4" style="margin-bottom: 36px;">
                {plans_html}
            </div>

            <div class="card" id="checkout-section" style="border-top: 5px solid var(--accent); background: #ffffff;">
                <h3 style="margin-top: 0; color: var(--accent); font-size: 1.3rem;">💳 خطوات السداد ورفع إيصال التحويل للاعتماد</h3>
                
                <div class="grid-3" style="margin-bottom: 24px;">
                    <div style="background: #fdf2f8; border: 1px solid #fbcfe8; padding: 14px; border-radius: 10px;">
                        <strong style="color: #be185d;">📱 فودافون كاش (Vodafone Cash):</strong>
                        <div style="font-size: 1.25rem; font-weight: 800; color: #9d174d; margin: 6px 0; letter-spacing: 1px;">01026042468</div>
                        <div style="font-size: 0.8rem; color: #be185d;">التحويل متاح من أي محفظة إلكترونية (فودافون، أورانج، وي، اتصالات، فوري).</div>
                    </div>
                    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 14px; border-radius: 10px;">
                        <strong style="color: #15803d;">⚡ إنستاباي (InstaPay IPA):</strong>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #166534; margin: 6px 0; word-break: break-all;">vetmind.admin@instapay</div>
                        <div style="font-size: 0.8rem; color: #15803d;">التحويل اللحظي المباشر عبر تطبيق إنستاباي من كافة البنوك المصرية.</div>
                    </div>
                    <div style="background: #f0f9ff; border: 1px solid #bae6fd; padding: 14px; border-radius: 10px;">
                        <strong style="color: #0369a1;">🏦 التحويل البنكي (Bank Transfer):</strong>
                        <div style="font-size: 1.05rem; font-weight: 800; color: #075985; margin: 6px 0;">البنك التجاري الدولي (CIB)</div>
                        <div style="font-size: 0.8rem; color: #0369a1;">الحساب: VetMind Enterprise Medical | اطلب الآيبان عند الحاجة.</div>
                    </div>
                </div>

                <form action="/community/subscribe" method="POST" enctype="multipart/form-data" style="margin-top: 20px;">
                    <div class="grid-2" style="margin-bottom: 14px;">
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 6px;">الباقة المختارة *</label>
                            <select id="selected-plan-id" name="plan_id" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px; font-weight: 700;">
                                <option value="annual" selected>الباقة السنوية الذهبية (Annual VIP) - 1,200 ج.م</option>
                                <option value="monthly">الباقة الشهرية (Monthly Plan) - 150 ج.م</option>
                                <option value="semi_annual">الباقة نصف السنوية (Semi-Annual) - 750 ج.م</option>
                                <option value="lifetime">العضوية الدائمة (Lifetime Access) - 2,500 ج.م</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 6px;">طريقة الدفع المستخدمة *</label>
                            <select name="payment_method" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                                <option value="فودافون كاش (Vodafone Cash)">📱 فودافون كاش (Vodafone Cash)</option>
                                <option value="إنستاباي (InstaPay)">⚡ تطبيق إنستاباي (InstaPay)</option>
                                <option value="تحويل بنكي (Bank Wire)">🏦 تحويل بنكي (CIB / NBE)</option>
                                <option value="محفظة إلكترونية أخرى">💼 محفظة إلكترونية أخرى (أورانج / اتصالات / وي)</option>
                            </select>
                        </div>
                    </div>

                    <div class="grid-2" style="margin-bottom: 14px;">
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 6px;">رقم المحفظة المحول منها أو رقم العملية / الحوالة *</label>
                            <input type="text" name="transaction_ref" required placeholder="مثال: 010xxxxxxxx أو رقم الحوالة 892341..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                        </div>
                        <div>
                            <label style="display: block; font-weight: 700; margin-bottom: 6px;">رقم هاتف الطبيب للتواصل *</label>
                            <input type="tel" name="doctor_phone" required value="{user.get('phone', '')}" placeholder="01xxxxxxxxx" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                        </div>
                    </div>

                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-weight: 700; margin-bottom: 6px;">📸 رفع صورة إيصال السداد أو لقطة شاشة التحويل (Screenshot) *</label>
                        <input type="file" name="receipt_file" accept="image/*" required style="width: 100%; padding: 8px; border: 1px dashed var(--accent); border-radius: 8px; background: #fff7ed;">
                        <span style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-top: 4px;">يقبل صور JPG, PNG, WEBP (بحد أقصى 10 ميجابايت).</span>
                    </div>

                    <button type="submit" class="btn btn-accent" style="padding: 12px 30px; font-size: 1.05rem; font-weight: 800; width: 100%; justify-content: center;">
                        📤 إرسال بيانات السداد للاعتماد الفوري
                    </button>
                </form>
            </div>
        </div>

        <script>
        function selectPlan(planId, planName, planAmount) {{
            const sel = document.getElementById('selected-plan-id');
            if (sel) {{
                sel.value = planId;
            }}
            document.getElementById('checkout-section').scrollIntoView({{ behavior: 'smooth' }});
        }}
        </script>
        """
        return HTMLResponse(content=get_base_html("VetBook | الاشتراك", body, user, lang), media_type="text/html; charset=utf-8")

    # --------------------------------------------------------------------------
    # APPROVED USER / ADMIN -> ALGORITHMIC VETBOOK PLATFORM
    # --------------------------------------------------------------------------
    conn = get_db()
    c = conn.cursor()

    # Base Query
    sql = "SELECT * FROM community_posts WHERE 1=1"
    params = []

    if q and q.strip():
        sql += " AND (title LIKE ? OR content LIKE ? OR author_name LIKE ?)"
        q_term = f"%{q.strip()}%"
        params.extend([q_term, q_term, q_term])

    if category == "videos":
        sql += " AND (media_type = 'video' OR media_type = 'youtube' OR video_path IS NOT NULL)"
    elif category == "photos":
        sql += " AND (media_type = 'image' OR image_path IS NOT NULL)"
    elif category == "bookmarks":
        sql += " AND id IN (SELECT post_id FROM community_bookmarks WHERE user_id = ?)"
        params.append(user["id"])
    elif category == "my_posts":
        sql += " AND user_id = ?"
        params.append(user["id"])
    elif category != "all" and category in CATEGORIES:
        sql += " AND category = ?"
        params.append(category)

    c.execute(sql, tuple(params))
    raw_posts = [dict(r) for r in c.fetchall()]

    # Execute Algorithmic Scoring for each post
    for p in raw_posts:
        v_score = compute_virality_score(p)
        p["calculated_virality"] = v_score
        
        # Determine if Viral / Trending (Interactions >= 2 or virality > 1.5)
        is_trending_now = 1 if (p.get("likes_count", 0) + p.get("comments_count", 0) >= 2 or v_score >= 1.5) else 0
        p["is_trending"] = is_trending_now

        # Update in DB asynchronously
        c.execute("UPDATE community_posts SET virality_score = ?, is_trending = ? WHERE id = ?", (v_score, is_trending_now, p["id"]))

    # Sort Posts according to selected Sort Engine
    if sort == "recent":
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x["id"]), reverse=True)
    elif sort == "most_discussed":
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x.get("comments_count", 0), x["id"]), reverse=True)
    elif sort == "most_viewed":
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x.get("views_count", 0), x["id"]), reverse=True)
    else:
        # ALGORITHMIC (Default): Ranks by Virality Score (EdgeRank + Gravity Decay + Boost)
        raw_posts.sort(key=lambda x: (x.get("is_pinned", 0), x.get("calculated_virality", 0.0), x["id"]), reverse=True)

    posts = raw_posts

    # User Bookmarked Posts IDs
    c.execute("SELECT post_id FROM community_bookmarks WHERE user_id = ?", (user["id"],))
    user_bookmarks = set(r[0] for r in c.fetchall())

    # Trending viral posts for Right Sidebar & Algorithm Strip
    c.execute("""
    SELECT id, title, author_name, likes_count, comments_count, views_count, media_type, image_path, video_path
    FROM community_posts 
    ORDER BY virality_score DESC, likes_count + comments_count DESC 
    LIMIT 4
    """)
    trending_cases = [dict(r) for r in c.fetchall()]

    # Active verified colleagues
    c.execute("""
    SELECT u.id, u.name, u.clinic_name, u.country, u.last_active_at, u.is_admin
    FROM users u
    WHERE u.id != ?
    ORDER BY u.last_active_at DESC LIMIT 8
    """, (user["id"],))
    active_doctors = [dict(r) for r in c.fetchall()]

    # Community Stats
    c.execute("SELECT COUNT(*) FROM community_posts")
    total_posts = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM community_subscriptions WHERE status = 'approved'")
    approved_doctors_count = c.fetchone()[0] + 1
    c.execute("SELECT COUNT(*) FROM community_posts WHERE media_type = 'video' OR media_type = 'youtube'")
    total_videos = c.fetchone()[0]

    # Left Sidebar Navigation
    left_nav_items = ""
    for cid, cinfo in CATEGORIES.items():
        is_active = "active-fb-nav" if category == cid else ""
        left_nav_items += f"""
        <a href="/community?category={cid}&sort={sort}{f"&q={q}" if q else ""}" class="fb-nav-link {is_active}">
            <span style="font-size: 1.25rem;">{cinfo['icon']}</span>
            <span style="font-weight: 600; font-size: 0.92rem;">{cinfo['name']}</span>
        </a>
        """

    left_sidebar_html = f"""
    <div class="fb-left-sidebar">
        <!-- User Profile Card -->
        <a href="/profile" style="display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 10px; text-decoration: none; color: var(--text-main); transition: background 0.2s; margin-bottom: 8px;" class="fb-nav-link">
            <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.15rem; flex-shrink: 0; box-shadow: 0 2px 6px rgba(15,118,110,0.25);">
                {user.get('name', 'طبيب')[0]}
            </div>
            <div style="overflow: hidden;">
                <div style="font-weight: 700; font-size: 0.95rem; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">د. {user.get('name')}</div>
                <div style="font-size: 0.75rem; color: #059669; font-weight: 700;">طبيب بيطري معتمد 🩺</div>
            </div>
        </a>

        <div style="border-bottom: 1px solid var(--border); margin: 6px 0 10px 0;"></div>

        <!-- Navigation Links -->
        <div style="display: flex; flex-direction: column; gap: 3px;">
            {left_nav_items}
        </div>

        <div style="border-bottom: 1px solid var(--border); margin: 12px 0;"></div>

        <!-- Algorithm Reach Status -->
        <div style="background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%); border: 1px solid #bbf7d0; border-radius: 12px; padding: 14px; font-size: 0.82rem;">
            <div style="display: flex; align-items: center; gap: 6px; font-weight: 800; color: #047857; margin-bottom: 6px;">
                <span>🧠</span> خوارزمية الانتشار الذكي:
            </div>
            <div style="color: var(--text-muted); line-height: 1.6;">
                يتم تقييم كل منشور بنقاط الجودة السريرية (+85%) وتوسيع نشره تلقائياً عند تفاعل الزملاء معه بالتعليقات والمشاركات.
            </div>
        </div>
    </div>
    """

    # Trending cases for Right Sidebar
    trending_cases_html = ""
    for tc in trending_cases:
        media_ico = "🎥" if tc.get("media_type") in ("video", "youtube") else "🔬"
        trending_cases_html += f"""
        <a href="/community#post-{tc['id']}" style="display: block; padding: 10px 12px; border-radius: 8px; text-decoration: none; color: var(--text-main); background: var(--bg); margin-bottom: 8px; border-right: 3px solid #ef4444; transition: background 0.2s;">
            <div style="font-weight: 700; font-size: 0.85rem; color: #991b1b; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {media_ico} {tc['title']}
            </div>
            <div style="font-size: 0.72rem; color: var(--text-muted); display: flex; justify-content: space-between;">
                <span>د. {tc['author_name']}</span>
                <span>🔥 {tc.get('likes_count',0)} تفاعل • {tc.get('comments_count',0)} رد</span>
            </div>
        </a>
        """

    # Active doctors for Right Sidebar
    active_doctors_html = ""
    for ad in active_doctors:
        active_doctors_html += f"""
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 7px 10px; border-radius: 8px; transition: background 0.2s;" class="fb-contact-row">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="position: relative;">
                    <div style="width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #0284c7, #0f766e); color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.88rem;">
                        {ad['name'][0]}
                    </div>
                    <span style="position: absolute; bottom: 0; left: 0; width: 10px; height: 10px; background: #16a34a; border: 2px solid white; border-radius: 50%;"></span>
                </div>
                <div>
                    <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-main);">د. {ad['name']}</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">{ad.get('clinic_name') or 'طبيب بيطري'} • {ad.get('country') or 'مصر'}</div>
                </div>
            </div>
            <span style="font-size: 0.7rem; color: #15803d; font-weight: 700;">متصل الآن</span>
        </div>
        """

    right_sidebar_html = f"""
    <div class="fb-right-sidebar">
        <!-- Live Community Stats Box -->
        <div class="fb-card" style="margin-bottom: 18px; padding: 16px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #ecfdf5; color: #047857; display: flex; align-items: center; justify-content: center; font-size: 1.1rem;">📊</div>
                <h4 style="margin: 0; font-size: 0.95rem; color: var(--primary);">إحصائيات فيتبوك البيطري</h4>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                <div style="background: var(--bg); padding: 8px 10px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 1.35rem; font-weight: 800; color: #0f766e;">{approved_doctors_count}</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">طبيباً معتمداً</div>
                </div>
                <div style="background: var(--bg); padding: 8px 10px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 1.35rem; font-weight: 800; color: #ea580c;">{total_posts}</div>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">حالة سريرية</div>
                </div>
            </div>
        </div>

        <!-- Trending Viral Cases (Algorithm Picks) -->
        <div class="fb-card" style="margin-bottom: 18px; padding: 16px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <h4 style="margin: 0; font-size: 0.92rem; color: #dc2626; display: flex; align-items: center; gap: 6px;">
                    <span>🔥</span> الأعلى تفاعلاً بالخوارزمية
                </h4>
                <span style="font-size: 0.72rem; background: #fee2e2; color: #991b1b; padding: 2px 7px; border-radius: 12px; font-weight: 800;">رائج Viral</span>
            </div>
            {trending_cases_html if trending_cases_html else "<div style='color: var(--text-muted); font-size: 0.8rem;'>لا توجد حالات شائعة بعد.</div>"}
        </div>

        <!-- Online Veterinary Colleagues -->
        <div class="fb-card" style="padding: 16px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <h4 style="margin: 0; font-size: 0.92rem; color: var(--text-main); display: flex; align-items: center; gap: 6px;">
                    <span>👥</span> زملاء الشبكة المتاحون
                </h4>
                <span style="font-size: 0.72rem; background: #dcfce7; color: #166534; padding: 2px 7px; border-radius: 12px; font-weight: 700;">{len(active_doctors)} متاح</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 2px;">
                {active_doctors_html}
            </div>
        </div>
    </div>
    """

        # Mobile Categories Strip (Horizontal Scroll for Phones & Tablets)
    mobile_cat_items = ""
    for cid, cinfo in CATEGORIES.items():
        is_active = "active-fb-pill" if category == cid else ""
        mobile_cat_items += f"""
        <a href="/community?category={cid}&sort={sort}{f"&q={q}" if q else ""}" class="fb-mobile-cat-pill {is_active}">
            <span>{cinfo['icon']}</span>
            <span>{cinfo['name']}</span>
        </a>
        """
    mobile_categories_html = f"""
    <div class="fb-mobile-categories-bar">
        <div class="fb-mobile-categories-strip">
            {mobile_cat_items}
        </div>
    </div>
    """

    # Stories Strip (Facebook/Instagram Stories with Trending Cases)
    trending_stories_cards = ""
    for tc in trending_cases:
        m_icon = "🎥" if tc.get("media_type") in ("video", "youtube") else "🔬"
        bg_style = "linear-gradient(180deg, #fef2f2 0%, #fee2e2 100%)" if tc.get("media_type") in ("video", "youtube") else "linear-gradient(180deg, #ecfdf5 0%, #d1fae5 100%)"
        trending_stories_cards += f"""
        <a href="/community#post-{tc['id']}" class="fb-story-card" style="background: {bg_style}; text-decoration: none; position: relative;">
            <div style="position: absolute; top: 8px; right: 8px; width: 34px; height: 34px; border-radius: 50%; border: 2px solid #ef4444; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.82rem; font-weight: 800; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">
                {tc['author_name'][0]}
            </div>
            <div style="margin-top: 36px; text-align: center;">
                <span style="font-size: 1.1rem;">{m_icon}</span>
                <div style="font-size: 0.74rem; font-weight: 700; color: #0f766e; margin-top: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3;">
                    {tc['title'][:32]}
                </div>
                <div style="font-size: 0.68rem; color: #dc2626; font-weight: 800; margin-top: 3px;">
                    🔥 {tc.get('likes_count',0) + tc.get('comments_count',0)} تفاعل
                </div>
            </div>
        </a>
        """

    stories_html = f"""
    <div class="fb-stories-strip">
        <div class="fb-story-card" style="background: linear-gradient(180deg, rgba(15,118,110,0.05) 0%, rgba(15,118,110,0.15) 100%); border: 1px dashed #0f766e;" onclick="document.getElementById('new-post-modal').style.display='flex'">
            <div style="width: 42px; height: 42px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; box-shadow: 0 4px 10px rgba(15,118,110,0.3);">
                ➕
            </div>
            <span style="font-size: 0.8rem; font-weight: 700; color: #0f766e; margin-top: 8px;">نشر حالة جديدة</span>
        </div>

        {trending_stories_cards}

        <a href="/community?category=videos" class="fb-story-card" style="background: linear-gradient(180deg, #fee2e2 0%, #fecaca 100%); text-decoration: none;">
            <div style="width: 42px; height: 42px; border-radius: 50%; background: #dc2626; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;">
                🎥
            </div>
            <span style="font-size: 0.8rem; font-weight: 700; color: #991b1b; margin-top: 8px;">Vet Watch ({total_videos})</span>
        </a>

        <a href="/community?category=case_study" class="fb-story-card" style="background: linear-gradient(180deg, #ffedd5 0%, #fed7aa 100%); text-decoration: none;">
            <div style="width: 42px; height: 42px; border-radius: 50%; background: #ea580c; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;">
                🔬
            </div>
            <span style="font-size: 0.8rem; font-weight: 700; color: #9a3412; margin-top: 8px;">حالات نادرة</span>
        </a>

        <a href="/community?category=surgery" class="fb-story-card" style="background: linear-gradient(180deg, #cffafe 0%, #a5f3fc 100%); text-decoration: none;">
            <div style="width: 42px; height: 42px; border-radius: 50%; background: #0891b2; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;">
                🩺
            </div>
            <span style="font-size: 0.8rem; font-weight: 700; color: #155e75; margin-top: 8px;">جراحة وتخدير</span>
        </a>

        <a href="/community?category=drug_experience" class="fb-story-card" style="background: linear-gradient(180deg, #ede9fe 0%, #ddd6fe 100%); text-decoration: none;">
            <div style="width: 42px; height: 42px; border-radius: 50%; background: #7c3aed; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;">
                💊
            </div>
            <span style="font-size: 0.8rem; font-weight: 700; color: #5b21b6; margin-top: 8px;">تجارب دوائية</span>
        </a>
    </div>
    """

    # Create Post Box
    create_post_box = f"""
    <div class="fb-card" style="margin-bottom: 16px; padding: 14px 18px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div style="width: 42px; height: 42px; border-radius: 50%; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.15rem; flex-shrink: 0;">
                {user.get('name', 'طبيب')[0]}
            </div>
            <button type="button" onclick="document.getElementById('new-post-modal').style.display='flex'" class="fb-create-post-input">
                بم تفكر يا دكتور {user.get('name', '')}؟ شارك حالة، صورة، أو فيديو عملية...
            </button>
        </div>
        
        <div style="border-top: 1px solid var(--border); padding-top: 10px; display: flex; justify-content: space-around; align-items: center;">
            <button type="button" onclick="openNewPostModalWithMedia('video')" class="fb-quick-action-btn" style="color: #dc2626;">
                <span style="font-size: 1.3rem;">🎥</span>
                <span>فيديو مباشر / جراحة</span>
            </button>
            <button type="button" onclick="openNewPostModalWithMedia('image')" class="fb-quick-action-btn" style="color: #16a34a;">
                <span style="font-size: 1.3rem;">🖼️</span>
                <span>صورة سريرية</span>
            </button>
            <button type="button" onclick="openNewPostModalWithMedia('consultation')" class="fb-quick-action-btn" style="color: #d97706;">
                <span style="font-size: 1.3rem;">❓</span>
                <span>استشارة عاجلة</span>
            </button>
        </div>
    </div>
    """

    # Algorithm Sorting & Filter Bar (Facebook Feed Controls)
    sort_algorithmic_active = "active-sort" if sort == "algorithmic" else ""
    sort_recent_active = "active-sort" if sort == "recent" else ""
    sort_discussed_active = "active-sort" if sort == "most_discussed" else ""
    sort_viewed_active = "active-sort" if sort == "most_viewed" else ""

    sorting_bar = f"""
    <div class="fb-card" style="padding: 10px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
        <div style="display: flex; align-items: center; gap: 8px; font-size: 0.88rem; font-weight: 700; color: #0f766e;">
            <span>🧠</span> خوارزمية ترتيب الـ Feed:
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <a href="/community?category={category}&sort=algorithmic{f'&q={q}' if q else ''}" class="fb-sort-pill {sort_algorithmic_active}" title="الخوارزمية الذكية ترقي المنشورات الأعلى تفاعلاً وجودة سريرية">
                🔥 الأكثر رواجاً وتفاعلاً
            </a>
            <a href="/community?category={category}&sort=recent{f'&q={q}' if q else ''}" class="fb-sort-pill {sort_recent_active}">
                ✨ الأحدث نشراً
            </a>
            <a href="/community?category={category}&sort=most_discussed{f'&q={q}' if q else ''}" class="fb-sort-pill {sort_discussed_active}">
                💬 الأكثر نقاشاً
            </a>
            <a href="/community?category={category}&sort=most_viewed{f'&q={q}' if q else ''}" class="fb-sort-pill {sort_viewed_active}">
                👁️ الأكثر مشاهدة
            </a>
        </div>
    </div>
    """

    # Render Posts (Facebook Post Component with Algorithmic Telemetry)
    posts_html = ""
    for p in posts:
        post_id = p["id"]

        # Increment views
        c.execute("UPDATE community_posts SET views_count = views_count + 1 WHERE id = ?", (post_id,))

        # Reaction state
        c.execute("SELECT id, reaction_type FROM community_likes WHERE post_id = ? AND user_id = ?", (post_id, user["id"]))
        like_row = c.fetchone()
        user_liked = bool(like_row)
        reaction_val = like_row["reaction_type"] if like_row else "like"

        like_btn_style = "color: #0f766e; font-weight: 800;" if user_liked else "color: var(--text-muted);"
        like_icon = "👍" if not user_liked or reaction_val == "like" else ("❤️" if reaction_val == "love" else "💡")
        like_label = "أعجبني" if not user_liked else ("أعجبني 👍" if reaction_val == "like" else ("أحببته ❤️" if reaction_val == "love" else "مفيد 💡"))

        # Bookmark state
        is_bookmarked = post_id in user_bookmarks
        bookmark_btn_style = "color: #d97706; font-weight: 800;" if is_bookmarked else "color: var(--text-muted);"
        bookmark_text = "محفوظ 🔖" if is_bookmarked else "حفظ 🔖"

        # Comments & replies
        c.execute("SELECT * FROM community_comments WHERE post_id = ? ORDER BY id ASC", (post_id,))
        raw_comments = [dict(r) for r in c.fetchall()]

        top_comments = [cm for cm in raw_comments if not cm.get("parent_comment_id") or cm.get("parent_comment_id") == 0]
        replies_map = {}
        for cm in raw_comments:
            pid = cm.get("parent_comment_id")
            if pid and pid > 0:
                replies_map.setdefault(pid, []).append(cm)

        # Comments bubbles HTML
        comments_list_html = ""
        for cm in top_comments:
            cm_id = cm["id"]
            cm_is_post_author = (cm.get("user_id") == p["user_id"])
            author_badge = '<span style="background: #e0e7ff; color: #3730a3; padding: 1px 6px; border-radius: 8px; font-size: 0.72rem; font-weight: 700; margin-right: 4px;">👑 صاحب الحالة</span>' if cm_is_post_author else ""
            
            nested_replies_html = ""
            for rep in replies_map.get(cm_id, []):
                rep_is_author = (rep.get("user_id") == p["user_id"])
                rep_badge = '<span style="background: #e0e7ff; color: #3730a3; padding: 1px 5px; border-radius: 8px; font-size: 0.7rem; font-weight: 700;">👑 صاحب الحالة</span>' if rep_is_author else ""
                nested_replies_html += f"""
                <div style="margin-top: 8px; display: flex; gap: 8px; align-items: flex-start;">
                    <div style="width: 28px; height: 28px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; flex-shrink: 0;">
                        {rep['author_name'][0]}
                    </div>
                    <div style="flex: 1;">
                        <div class="fb-comment-bubble">
                            <div style="font-weight: 700; font-size: 0.82rem; color: #0f766e; word-break: break-word;">د. {rep['author_name']} {rep_badge}</div>
                            <div class="fb-comment-content">{rep['content']}</div>
                        </div>
                        <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px; margin-right: 10px;">
                            <span>{rep['created_at']}</span>
                        </div>
                    </div>
                </div>
                """

            comments_list_html += f"""
            <div style="margin-bottom: 12px; display: flex; gap: 10px; align-items: flex-start;">
                <div style="width: 34px; height: 34px; border-radius: 50%; background: #0284c7; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 700; flex-shrink: 0;">
                    {cm['author_name'][0]}
                </div>
                <div style="flex: 1;">
                    <div class="fb-comment-bubble">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px;">
                            <div style="word-break: break-word;">
                                <strong style="font-size: 0.88rem; color: #0f766e;">د. {cm['author_name']}</strong> {author_badge}
                                <span style="font-size: 0.75rem; color: var(--text-muted); margin-right: 4px;">({cm.get('author_specialty') or 'طبيب بيطري'})</span>
                            </div>
                        </div>
                        <div class="fb-comment-content">{cm['content']}</div>
                    </div>

                    <div style="display: flex; gap: 14px; font-size: 0.75rem; color: var(--text-muted); margin-top: 3px; margin-right: 12px;">
                        <button type="button" onclick="toggleReplyBox({cm_id})" style="background: none; border: none; font-weight: 700; color: #0f766e; cursor: pointer; padding: 0;">
                            رد ↩️
                        </button>
                        <span>{cm['created_at']}</span>
                    </div>

                    <div class="fb-replies-container">
                        {nested_replies_html}
                    </div>

                    <div id="reply-box-{cm_id}" style="display: none; margin-top: 8px; margin-right: 20px;">
                        <form action="/community/comment/{post_id}" method="POST" style="display: flex; gap: 8px; align-items: center;">
                            <input type="hidden" name="parent_comment_id" value="{cm_id}">
                            <input type="text" name="content" required placeholder="اكتب ردك على د. {cm['author_name']}..." style="flex: 1; padding: 8px 14px; border: 1px solid var(--border); border-radius: 20px; font-size: 0.82rem; background: var(--bg);">
                            <button type="submit" class="btn btn-primary" style="padding: 7px 16px; font-size: 0.8rem; border-radius: 20px;">رد ↩️</button>
                        </form>
                    </div>
                </div>
            </div>
            """

        # Media Player / Image Display (100% Responsive, Zero Card Overflow)
        media_html = ""
        if p.get("video_path"):
            vpath = p["video_path"]
            if vpath.startswith("http://") or vpath.startswith("https://"):
                media_html = f"""
                <div style="margin: 10px 0; background: #000; border-radius: 10px; overflow: hidden; width: 100%; max-width: 100%;">
                    <iframe src="{vpath}" style="width: 100%; aspect-ratio: 16/9; border: none; display: block;" allowfullscreen></iframe>
                </div>
                """
            else:
                media_html = f"""
                <div style="margin: 10px 0; background: #000; border-radius: 10px; overflow: hidden; width: 100%; max-width: 100%; text-align: center;">
                    <video controls playsinline preload="metadata" style="width: 100%; max-height: 520px; display: block; outline: none; background: #0f172a;">
                        <source src="/uploads/{vpath}">
                    </video>
                </div>
                """
        elif p.get("image_path"):
            media_html = f"""
            <div style="margin: 10px 0; text-align: center; background: #000; border-radius: 10px; overflow: hidden; width: 100%; max-width: 100%;">
                <img src="/uploads/{p['image_path']}" alt="{p['title']}" onclick="openImageModal('/uploads/{p['image_path']}')" style="max-width: 100%; width: 100%; height: auto; max-height: 520px; object-fit: contain; display: block; margin: 0 auto; cursor: zoom-in; transition: transform 0.2s;">
            </div>
            """

        # Algorithmic Badges & Reach Telemetry
        q_score = p.get("quality_score", 75)
        v_score = p.get("calculated_virality", 0.0)
        is_trending = p.get("is_trending", 0)
        is_boosted = p.get("is_boosted", 0)
        is_pinned = p.get("is_pinned", 0)

        algorithmic_badges = ""
        if is_pinned:
            algorithmic_badges += '<span style="background: #fef08a; color: #854d0e; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; margin-left: 4px;">📌 مثبت بالصدارة</span>'
        if is_boosted:
            algorithmic_badges += '<span style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; margin-left: 4px;">🚀 وصول موسع ومروج</span>'
        if is_trending:
            algorithmic_badges += '<span style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; margin-left: 4px; box-shadow: 0 2px 6px rgba(239,68,68,0.25);">🔥 رائج بالخوارزمية</span>'
        if q_score >= 85:
            algorithmic_badges += f'<span style="background: #ecfdf5; color: #047857; border: 1px solid #6ee7b7; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; margin-left: 4px;">🌟 توثيق سريري فائق ({q_score}%)</span>'

        cat_badge = CATEGORIES.get(p["category"], {"name": p["category"], "color": "#0f766e", "icon": "📄"})

        # Admin Controls (Pin, Boost & Delete)
        admin_boost_btn = ""
        if user.get("is_admin"):
            boost_label = "إلغاء الترويج" if is_boosted else "🚀 ترويج المنشور (Boost)"
            boost_style = "color: #ea580c; border-color: #f97316; font-weight: 700;" if is_boosted else "color: #0284c7;"
            pin_label = "إلغاء التثبيت" if is_pinned else "📌 تثبيت"
            pin_style = "color: #854d0e; border-color: #ca8a04; font-weight: 700;" if is_pinned else "color: #475569;"
            admin_boost_btn = f"""
            <a href="/admin/community/pin/{post_id}" class="btn btn-outline" style="font-size: 0.72rem; padding: 2px 7px; {pin_style}">{pin_label}</a>
            <a href="/admin/community/boost/{post_id}" class="btn btn-outline" style="font-size: 0.72rem; padding: 2px 7px; {boost_style}">{boost_label}</a>
            """

        delete_btn = ""
        if user.get("is_admin") or user["id"] == p["user_id"]:
            delete_btn = f"""
            <form action="/community/post/delete/{post_id}" method="POST" style="margin: 0;" onsubmit="return confirm('هل تريد بالتأكيد حذف هذا المنشور السريري؟');">
                <button type="submit" style="background: none; border: none; color: var(--danger); cursor: pointer; font-size: 0.8rem; padding: 4px;" title="حذف المنشور">🗑️</button>
            </form>
            """

        # Card Border Highlight if Trending/Viral
        card_border_style = "border-top: 4px solid #ef4444; box-shadow: 0 4px 14px rgba(239,68,68,0.12);" if is_trending else "border-top: 4px solid #0f766e;"

        posts_html += f"""
        <div class="fb-card" id="post-{post_id}" style="{card_border_style}">
            <!-- Facebook Post Header -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; flex-wrap: wrap; margin-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1 1 200px;">
                    <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.15rem; flex-shrink: 0;">
                        {p['author_name'][0] if p['author_name'] else 'V'}
                    </div>
                    <div style="min-width: 0; flex: 1 1 auto;">
                        <div style="font-weight: 700; font-size: clamp(0.9rem, 2.6vw, 1rem); color: var(--text-main); display: flex; align-items: center; gap: 5px; flex-wrap: wrap; word-break: break-word;">
                            <span>د. {p['author_name']}</span>
                            <span style="color: #059669; font-size: 0.85rem;" title="طبيب بيطري معتمد">🩺</span>
                            {algorithmic_badges}
                        </div>
                        <div style="font-size: clamp(0.7rem, 2vw, 0.76rem); color: var(--text-muted); display: flex; align-items: center; gap: 4px; flex-wrap: wrap; margin-top: 2px;">
                            <span>{p.get('author_specialty') or 'طب وجراحة الحيوان'}</span> •
                            <span>{p.get('author_country') or 'مصر'}</span> •
                            <span>{p['created_at']}</span> •
                            <span title="مرئي لجميع الأطباء المعتمدين">🌐</span>
                        </div>
                    </div>
                </div>
                
                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; flex-shrink: 0;">
                    {admin_boost_btn}
                    <span style="background: {cat_badge['color']}15; color: {cat_badge['color']}; padding: 3px 10px; border-radius: 12px; font-size: clamp(0.7rem, 2vw, 0.76rem); font-weight: 700; white-space: nowrap;">
                        {cat_badge['icon']} {cat_badge['name']}
                    </span>
                    {delete_btn}
                </div>
            </div>

            <!-- Post Title & Content (Word-Break & Overflow Wrap) -->
            <h3 class="fb-post-title">{p['title']}</h3>
            <div class="fb-post-content">{p['content']}</div>

            {media_html}

            <!-- Facebook Reactions & Counters Summary Bar -->
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; padding: 8px 2px; font-size: clamp(0.72rem, 2.2vw, 0.82rem); color: var(--text-muted); border-bottom: 1px solid var(--border); margin-top: 8px;">
                <div style="display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
                    <span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: #0f766e; color: white; font-size: 0.65rem;">👍</span>
                    <span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: #dc2626; color: white; font-size: 0.65rem;">❤️</span>
                    <span style="margin-right: 4px; font-weight: 700;">{p['likes_count']} تفاعلاً</span>
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
                    <span>{p['comments_count']} تعليقاً</span>
                    <span>•</span>
                    <span>{p.get('shares_count', 0)} مشاركة</span>
                    <span>•</span>
                    <span>{p.get('views_count', 1)} مشاهدة</span>
                    <span>•</span>
                    <span title="مؤشر الخوارزمية لانتشار الحالة">⚡ انتشار: {v_score}</span>
                </div>
            </div>

            <!-- Facebook Post Actions (Like, Comment, Share, Save) -->
            <div class="fb-post-action-bar">
                <form action="/community/like/{post_id}" method="POST" style="margin: 0; flex: 1;">
                    <button type="submit" class="fb-post-action-btn" style="{like_btn_style}">
                        <span>{like_icon}</span>
                        <span>{like_label}</span>
                    </button>
                </form>
                <button type="button" onclick="focusCommentBox({post_id})" class="fb-post-action-btn" style="flex: 1;">
                    <span>💬</span>
                    <span>تعليق</span>
                </button>
                <button type="button" onclick="copyPostLink({post_id})" class="fb-post-action-btn" style="flex: 1;">
                    <span>↪️</span>
                    <span>مشاركة</span>
                </button>
                <form action="/community/bookmark/{post_id}" method="POST" style="margin: 0; flex: 1;">
                    <button type="submit" class="fb-post-action-btn" style="{bookmark_btn_style}">
                        <span>{bookmark_text}</span>
                    </button>
                </form>
            </div>

            <!-- Comments Section -->
            <div id="comments-section-{post_id}" style="padding-top: 8px;">
                <div style="margin-bottom: 12px;">
                    {comments_list_html if comments_list_html else "<div style='color: var(--text-muted); font-size: 0.82rem; padding: 4px;'>لا توجد تعليقات بعد. كن أول طبيب يعلق على هذه الحالة!</div>"}
                </div>

                <!-- Comment Input Box -->
                <form action="/community/comment/{post_id}" method="POST" style="display: flex; gap: 8px; align-items: center; margin-top: 10px; width: 100%; box-sizing: border-box;">
                    <input type="hidden" name="parent_comment_id" value="0">
                    <div style="width: 34px; height: 34px; border-radius: 50%; background: #0f766e; color: white; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: 700; flex-shrink: 0;">
                        {user.get('name', 'طبيب')[0]}
                    </div>
                    <input type="text" id="main-comment-input-{post_id}" name="content" required placeholder="اكتب تعليقاً أو استشارة سريرية د. {user.get('name', '')}..." style="flex: 1 1 auto; min-width: 0; padding: 9px 14px; border: 1px solid var(--border); border-radius: 20px; font-size: clamp(0.78rem, 2.4vw, 0.88rem); background: var(--bg); box-sizing: border-box;">
                    <button type="submit" class="btn btn-primary" style="padding: 8px 16px; font-size: 0.85rem; border-radius: 20px;">نشر</button>
                </form>
            </div>
        </div>
        """

    conn.commit()
    conn.close()

    # --------------------------------------------------------------------------
    # FULL FACEBOOK THREE-COLUMN PAGE ASSEMBLY
    # --------------------------------------------------------------------------
    body = f"""
    <style>
    /* ==========================================================================
       VETBOOK UNIVERSAL RESPONSIVE ENGINE (MOBILE, TABLET, LAPTOP & 4K DESKTOP)
       ========================================================================== */
    .fb-wrapper {{
        background: var(--bg);
        width: 100%;
        max-width: 100%;
        margin: 0 auto;
        padding: 0;
        box-sizing: border-box;
        overflow-x: hidden;
    }}
    .fb-container {{
        width: 100%;
        max-width: 1360px;
        margin: 0 auto;
        display: grid;
        grid-template-columns: 260px minmax(0, 1fr) 300px;
        gap: 18px;
        align-items: start;
        box-sizing: border-box;
    }}
    .fb-left-sidebar {{
        position: sticky;
        top: 20px;
        min-width: 0;
        box-sizing: border-box;
    }}
    .fb-center-feed {{
        min-width: 0;
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
    }}
    .fb-right-sidebar {{
        position: sticky;
        top: 20px;
        min-width: 0;
        box-sizing: border-box;
    }}
    .fb-card {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 16px;
        padding: 16px;
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
        overflow-x: hidden;
        word-break: break-word;
        overflow-wrap: anywhere;
    }}
    .fb-nav-link {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 12px;
        border-radius: 10px;
        text-decoration: none;
        color: var(--text-main);
        transition: all 0.2s;
        min-width: 0;
        box-sizing: border-box;
    }}
    .fb-nav-link:hover {{
        background: rgba(15,118,110,0.08);
        color: #0f766e;
    }}
    .fb-nav-link.active-fb-nav {{
        background: #0f766e;
        color: #ffffff !important;
        font-weight: 700;
    }}

    /* Mobile / Tablet Horizontal Category Scroll Bar */
    .fb-mobile-categories-bar {{
        display: none;
        margin-bottom: 14px;
        width: 100%;
        overflow: hidden;
        box-sizing: border-box;
    }}
    .fb-mobile-categories-strip {{
        display: flex;
        gap: 8px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        padding: 4px 2px 8px 2px;
        white-space: nowrap;
        scrollbar-width: none;
    }}
    .fb-mobile-categories-strip::-webkit-scrollbar {{
        display: none;
    }}
    .fb-mobile-cat-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: var(--card-bg);
        border: 1px solid var(--border);
        color: var(--text-main);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 700;
        text-decoration: none;
        flex-shrink: 0;
        transition: all 0.2s ease;
        box-sizing: border-box;
    }}
    .fb-mobile-cat-pill:hover, .fb-mobile-cat-pill.active-fb-pill {{
        background: #0f766e;
        color: #ffffff !important;
        border-color: #0f766e;
    }}

    /* Stories & Reels Highlights */
    .fb-stories-strip {{
        display: flex;
        gap: 10px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 8px;
        margin-bottom: 16px;
        scrollbar-width: none;
        width: 100%;
        box-sizing: border-box;
    }}
    .fb-stories-strip::-webkit-scrollbar {{
        display: none;
    }}
    .fb-story-card {{
        min-width: 105px;
        width: 105px;
        height: 142px;
        border-radius: 12px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 10px;
        cursor: pointer;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s;
        border: 1px solid var(--border);
        flex-shrink: 0;
        box-sizing: border-box;
    }}
    .fb-story-card:hover {{
        transform: translateY(-2px);
    }}

    /* Create Post Input */
    .fb-create-post-input {{
        flex: 1 1 auto;
        min-width: 0;
        text-align: right;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 25px;
        padding: 10px 16px;
        color: var(--text-muted);
        font-size: clamp(0.78rem, 2.5vw, 0.92rem);
        cursor: pointer;
        transition: all 0.2s;
        box-sizing: border-box;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .fb-create-post-input:hover {{
        background: rgba(0,0,0,0.05);
    }}
    .fb-quick-action-btn {{
        background: none;
        border: none;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-weight: 700;
        font-size: clamp(0.75rem, 2.2vw, 0.88rem);
        padding: 6px 10px;
        border-radius: 8px;
        transition: background 0.2s;
        white-space: nowrap;
        box-sizing: border-box;
    }}
    .fb-quick-action-btn:hover {{
        background: rgba(0,0,0,0.05);
    }}

    /* Feed Filter Sorting */
    .fb-sort-strip {{
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        width: 100%;
        box-sizing: border-box;
    }}
    .fb-sort-pill {{
        background: var(--bg);
        border: 1px solid var(--border);
        color: var(--text-muted);
        padding: 5px 12px;
        border-radius: 20px;
        font-size: clamp(0.72rem, 2.2vw, 0.8rem);
        font-weight: 700;
        text-decoration: none;
        transition: all 0.2s;
        white-space: nowrap;
        flex-shrink: 0;
        box-sizing: border-box;
    }}
    .fb-sort-pill:hover {{
        background: rgba(15,118,110,0.1);
        color: #0f766e;
    }}
    .fb-sort-pill.active-sort {{
        background: #0f766e;
        color: white !important;
        border-color: #0f766e;
    }}

    /* Post Typography & Content */
    .fb-post-title {{
        margin: 8px 0 6px 0;
        font-size: clamp(1.05rem, 3.2vw, 1.22rem);
        color: #0f766e;
        line-height: 1.4;
        word-break: break-word;
        overflow-wrap: anywhere;
    }}
    .fb-post-content {{
        font-size: clamp(0.88rem, 2.6vw, 0.98rem);
        line-height: 1.7;
        color: var(--text-main);
        white-space: pre-wrap;
        word-break: break-word;
        overflow-wrap: anywhere;
        margin-bottom: 10px;
        max-width: 100%;
        box-sizing: border-box;
    }}

    /* Post Actions */
    .fb-post-action-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 12px;
        width: 100%;
        box-sizing: border-box;
        gap: 4px;
    }}
    .fb-post-action-btn {{
        width: 100%;
        background: none;
        border: none;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        padding: 8px 4px;
        border-radius: 6px;
        font-weight: 700;
        font-size: clamp(0.72rem, 2.3vw, 0.88rem);
        color: var(--text-muted);
        transition: background 0.2s;
        white-space: nowrap;
        box-sizing: border-box;
    }}
    .fb-post-action-btn:hover {{
        background: rgba(0,0,0,0.05);
    }}

    /* Comments & Nested Replies */
    .fb-comment-bubble {{
        background: #f0f2f5;
        border-radius: 16px;
        padding: 8px 12px;
        display: inline-block;
        max-width: 100%;
        box-sizing: border-box;
        word-break: break-word;
        overflow-wrap: anywhere;
    }}
    body.dark-theme .fb-comment-bubble {{
        background: #1e293b;
    }}
    .fb-comment-content {{
        color: var(--text-main);
        font-size: clamp(0.82rem, 2.3vw, 0.88rem);
        line-height: 1.5;
        margin-top: 4px;
        white-space: pre-wrap;
        word-break: break-word;
        overflow-wrap: anywhere;
    }}
    .fb-replies-container {{
        margin-right: 16px;
        border-right: 2px solid var(--border);
        padding-right: 10px;
        box-sizing: border-box;
    }}

    /* Contact Row */
    .fb-contact-row:hover {{
        background: rgba(0,0,0,0.04);
        cursor: pointer;
    }}

    /* Responsive Breakpoints Across All Devices in the World */
    @media (max-width: 1180px) {{
        .fb-container {{
            grid-template-columns: 240px minmax(0, 1fr) !important;
            gap: 14px;
        }}
        .fb-right-sidebar {{
            display: none !important;
        }}
    }}
    @media (max-width: 860px) {{
        .fb-container {{
            grid-template-columns: minmax(0, 1fr) !important;
            gap: 12px;
        }}
        .fb-left-sidebar {{
            display: none !important;
        }}
        .fb-mobile-categories-bar {{
            display: block !important;
        }}
    }}
    @media (max-width: 600px) {{
        .fb-card {{
            padding: 12px 10px !important;
            border-radius: 12px !important;
            margin-bottom: 12px !important;
        }}
        .fb-stories-strip {{
            gap: 8px !important;
        }}
        .fb-story-card {{
            min-width: 95px !important;
            width: 95px !important;
            height: 135px !important;
            padding: 8px !important;
        }}
        .fb-post-action-btn {{
            padding: 6px 2px !important;
            font-size: 0.74rem !important;
            gap: 2px !important;
        }}
        .fb-replies-container {{
            margin-right: 8px !important;
            padding-right: 6px !important;
        }}
        .fb-quick-action-btn {{
            padding: 5px 6px !important;
            font-size: 0.76rem !important;
        }}
    }}
</style>

    <div class="fb-wrapper">
        <div class="fb-container">
            <!-- Column 1: Left Navigation Sidebar -->
            {left_sidebar_html}

            <!-- Column 2: Center Main Facebook Feed -->
            <div class="fb-center-feed">
                <!-- Search Bar -->
                <div style="margin-bottom: 14px;">
                    <form action="/community" method="GET" style="display: flex; gap: 8px;">
                        <input type="hidden" name="category" value="{category}">
                        <input type="hidden" name="sort" value="{sort}">
                        <input type="text" name="q" value="{q}" placeholder="🔍 ابحث في منشورات فيتبوك، الحالات السريرية، أو أسماء الزملاء..." style="flex: 1 1 auto; min-width: 0; padding: 10px 16px; border: 1px solid var(--border); border-radius: 25px; font-size: clamp(0.8rem, 2.4vw, 0.9rem); background: var(--card-bg); box-sizing: border-box;">
                        <button type="submit" class="btn btn-primary" style="padding: 9px 20px; border-radius: 25px;">بحث</button>
                        {f'<a href="/community?category={category}&sort={sort}" class="btn btn-outline" style="border-radius: 25px;">إلغاء</a>' if q else ''}
                    </form>
                </div>

                <!-- Mobile Category Switcher -->
                {mobile_categories_html}

                <!-- Stories & Reels Highlights -->
                {stories_html}

                <!-- Create Post Box -->
                {create_post_box}

                <!-- Algorithm Feed Sorting Controls -->
                {sorting_bar}

                <!-- Posts Stream -->
                <div>
                    {posts_html if posts_html else f'''
                    <div class="fb-card" style="text-align: center; padding: 48px 20px; color: var(--text-muted);">
                        <div style="font-size: 3rem; margin-bottom: 10px;">🔍</div>
                        <h3 style="margin: 0; color: var(--text-main);">لم يتم العثور على منشورات مطابقة</h3>
                        <p style="margin-top: 6px;">لا توجد منشورات حالياً في هذا القسم. كن أول من يشارك حالة سريرية!</p>
                        <button onclick="document.getElementById('new-post-modal').style.display='flex'" class="btn btn-accent" style="margin-top: 14px; border-radius: 20px;">➕ نشر أول حالة الآن</button>
                    </div>
                    '''}
                </div>
            </div>

            <!-- Column 3: Right Sidebar -->
            {right_sidebar_html}
        </div>
    </div>

    <!-- Create Post Modal -->
    <div id="new-post-modal" class="modal">
        <div class="modal-content" style="max-width: 680px; max-height: 90vh; overflow-y: auto;">
            <button class="modal-close" onclick="document.getElementById('new-post-modal').style.display='none'">×</button>
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #0f766e, #0d9488); color: white; display: flex; align-items: center; justify-content: center; font-weight: 800;">
                    {user.get('name', 'طبيب')[0]}
                </div>
                <div>
                    <h3 style="margin: 0; color: #0f766e; font-size: 1.15rem;">إنشاء منشور سريري جديد في فيتبوك</h3>
                    <div style="display: flex; align-items: center; gap: 6px; margin-top: 2px;">
                        <span style="font-size: 0.75rem; background: var(--bg); border: 1px solid var(--border); padding: 1px 7px; border-radius: 12px; font-weight: 600;">🌐 خوارزمية النشر التلقائي والانتشار مفعلة</span>
                    </div>
                </div>
            </div>

            <form action="/community/post" method="POST" enctype="multipart/form-data">
                <div class="grid-2" style="margin-bottom: 12px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">تصنيف المنشور *</label>
                        <select id="modal-category-select" name="category" required style="width: 100%; padding: 9px; border: 1px solid var(--border); border-radius: 8px;">
                            <option value="case_study">🔬 حالة سريرية نادرة ومميزة</option>
                            <option value="surgery">🩺 فيديو / حالة جراحة وتخدير</option>
                            <option value="clinical_article">📚 مقال أو بحث بيطري سريري</option>
                            <option value="drug_experience">💊 تجربة دوائية وحقلية</option>
                            <option value="consultation">❓ استشارة طبية عاجلة للزملاء</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">عنوان الحالة أو الموضوع *</label>
                        <input type="text" name="title" required placeholder="مثال: استئصال ورم خبيث من جفن خيل / التهاب ضرع حاد" style="width: 100%; padding: 9px; border: 1px solid var(--border); border-radius: 8px;">
                    </div>
                </div>

                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 4px; font-size: 0.85rem;">التفاصيل السريرية والأعراض والبروتوكول المستخدم *</label>
                    <textarea name="content" rows="5" required placeholder="ما الذي يجري في عيادتك اليوم يا دكتور؟ اشرح الأعراض، الفحص العيني والميكروسكوبي، التدخل الجراحي أو الدوائي..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px; line-height: 1.6;"></textarea>
                </div>

                <!-- Add to your post Bar -->
                <div style="background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px 16px; margin-bottom: 16px;">
                    <div style="font-weight: 700; color: #0f766e; margin-bottom: 8px; font-size: 0.88rem;">
                        📁 أضف إلى منشورك (صور أو مقطع فيديو):
                    </div>
                    
                    <div style="margin-bottom: 8px;">
                        <label style="display: block; font-weight: 600; margin-bottom: 4px; font-size: 0.8rem;">
                            📸 / 🎥 رفع ملف من جهازك (صورة JPG/PNG أو فيديو MP4/WebM/MOV):
                        </label>
                        <input type="file" name="media_file" accept="image/*,video/*" style="width: 100%; padding: 7px; border: 1px dashed #0f766e; border-radius: 8px; background: var(--card-bg);">
                    </div>

                    <div>
                        <label style="display: block; font-weight: 600; margin-bottom: 4px; font-size: 0.8rem;">
                            🔗 أو رابط مقطع فيديو خارجي (YouTube / Shorts Embed):
                        </label>
                        <input type="url" name="youtube_url" placeholder="https://www.youtube.com/watch?v=... أو https://youtu.be/..." style="width: 100%; padding: 7px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.82rem; background: var(--card-bg);">
                    </div>
                </div>

                <div style="display: flex; justify-content: flex-end; gap: 10px;">
                    <button type="button" onclick="document.getElementById('new-post-modal').style.display='none'" class="btn btn-outline" style="border-radius: 20px;">إلغاء</button>
                    <button type="submit" class="btn btn-primary" style="padding: 10px 32px; font-weight: 800; border-radius: 20px; background: #0f766e;">🚀 نشر في فيتبوك</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Image Lightbox Modal -->
    <div id="image-modal" class="modal" onclick="closeImageModal()">
        <div style="max-width: 90vw; max-height: 90vh; position: relative;">
            <img id="image-modal-src" src="" style="max-width: 90vw; max-height: 90vh; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <button onclick="closeImageModal()" style="position: absolute; top: -14px; left: -14px; background: white; border: 2px solid #333; border-radius: 50%; width: 34px; height: 34px; font-size: 1.2rem; cursor: pointer;">✕</button>
        </div>
    </div>

    <!-- Share Toast Notification -->
    <div id="share-toast" style="display: none; position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: #065f46; color: white; padding: 12px 24px; border-radius: 30px; box-shadow: 0 4px 16px rgba(0,0,0,0.25); z-index: 10000; font-weight: 700; font-size: 0.95rem; align-items: center; gap: 8px;">
        <span>✅</span> تم نسخ رابط الحالة السريرية بنجاح! يمكنك مشاركته الآن مع الزملاء.
    </div>

    <script>
    function toggleReplyBox(cmId) {{
        const b = document.getElementById('reply-box-' + cmId);
        if (b) {{
            b.style.display = (b.style.display === 'none' ? 'block' : 'none');
            if (b.style.display === 'block') {{
                const inp = b.querySelector('input[type="text"]');
                if (inp) inp.focus();
            }}
        }}
    }}

    function focusCommentBox(postId) {{
        const inp = document.getElementById('main-comment-input-' + postId);
        if (inp) {{
            inp.focus();
            inp.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
    }}

    function copyPostLink(postId) {{
        const url = window.location.origin + '/community#post-' + postId;
        navigator.clipboard.writeText(url).then(() => {{
            const t = document.getElementById('share-toast');
            if (t) {{
                t.style.display = 'flex';
                setTimeout(() => {{ t.style.display = 'none'; }}, 3500);
            }}
        }}).catch(() => {{
            prompt('انسخ رابط الحالة السريرية:', url);
        }});
    }}

    function openNewPostModalWithMedia(type) {{
        const m = document.getElementById('new-post-modal');
        const sel = document.getElementById('modal-category-select');
        if (sel) {{
            if (type === 'video') sel.value = 'surgery';
            else if (type === 'consultation') sel.value = 'consultation';
            else sel.value = 'case_study';
        }}
        if (m) m.style.display = 'flex';
    }}

    function openImageModal(src) {{
        const m = document.getElementById('image-modal');
        const img = document.getElementById('image-modal-src');
        if (m && img) {{
            img.src = src;
            m.style.display = 'flex';
        }}
    }}

    function closeImageModal() {{
        const m = document.getElementById('image-modal');
        if (m) m.style.display = 'none';
    }}
    </script>
    """
    return HTMLResponse(content=get_base_html("VetBook | ملتقى الأطباء", body, user, lang), media_type="text/html; charset=utf-8")


# ==============================================================================
# ROUTE: POST /community/subscribe (Submit proof of payment)
# ==============================================================================
@router.post("/community/subscribe")
async def community_submit_subscription(
    request: Request,
    plan_id: str = Form(...),
    payment_method: str = Form(...),
    transaction_ref: str = Form(...),
    doctor_phone: str = Form(...),
    receipt_file: UploadFile = File(...)
):
    from app import get_current_user

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?redirect=/community", status_code=303)

    plan_info = PLANS.get(plan_id, PLANS["annual"])

    saved_receipt_name = ""
    try:
        ext = os.path.splitext(receipt_file.filename)[1] or ".jpg"
        saved_receipt_name = f"receipt_{int(datetime.now().timestamp())}_{user['id']}{ext}"
        full_dest = os.path.join(UPLOAD_DIR, saved_receipt_name)
        with open(full_dest, "wb") as buf:
            shutil.copyfileobj(receipt_file.file, buf)
    except Exception:
        saved_receipt_name = "error_receipt.jpg"

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_subscriptions (
        user_id, doctor_name, doctor_email, doctor_phone, syndicate_id, 
        clinic_name, country, plan_id, plan_name, amount, payment_method, 
        transaction_ref, receipt_image, status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (
        user["id"],
        user.get("name", "غير محدد"),
        user.get("email", ""),
        doctor_phone.strip(),
        user.get("syndicate_id", ""),
        user.get("clinic_name", ""),
        user.get("country", "مصر"),
        plan_id,
        plan_info["name"],
        plan_info["amount"],
        payment_method.strip(),
        transaction_ref.strip(),
        saved_receipt_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

    return RedirectResponse("/community?status_msg=submitted", status_code=303)


# ==============================================================================
# ROUTE: POST /community/post (Create Post with Algorithmic Content Scorer)
# ==============================================================================
@router.post("/community/post")
async def community_create_post(
    request: Request,
    title: str = Form(...),
    category: str = Form("case_study"),
    content: str = Form(...),
    media_file: UploadFile = File(None),
    youtube_url: str = Form("")
):
    from app import get_current_user

    user = get_current_user(request)
    if not user or not is_user_community_approved(user):
        return RedirectResponse("/community", status_code=303)

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

    # Run Algorithm Scorer on Clinical Content
    eval_res = evaluate_clinical_content(title, content, has_media)
    quality_score = eval_res["score"]

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_posts (
        user_id, author_name, author_specialty, author_country,
        category, title, content, image_path, video_path, media_type,
        quality_score, virality_score, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0, ?)
    """, (
        user["id"],
        user.get("name", "طبيب بيطري"),
        user.get("clinic_name", "طب وجراحة الحيوان"),
        user.get("country", "مصر"),
        category,
        title.strip(),
        content.strip(),
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
# ROUTE: POST /community/like/{post_id} (Reactions with Virality Recalculation)
# ==============================================================================
@router.post("/community/like/{post_id}")
async def community_toggle_like(request: Request, post_id: int, reaction: str = Form("like")):
    from app import get_current_user

    user = get_current_user(request)
    if not user or not is_user_community_approved(user):
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_likes WHERE post_id = ? AND user_id = ?", (post_id, user["id"]))
    existing = c.fetchone()

    if existing:
        c.execute("DELETE FROM community_likes WHERE id = ?", (existing["id"],))
        c.execute("UPDATE community_posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (post_id,))
    else:
        c.execute("INSERT INTO community_likes (post_id, user_id, reaction_type, created_at) VALUES (?, ?, ?, ?)",
                  (post_id, user["id"], reaction, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("UPDATE community_posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))

    # Trigger virality recalculation
    c.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,))
    p = c.fetchone()
    if p:
        v_score = compute_virality_score(dict(p))
        c.execute("UPDATE community_posts SET virality_score = ? WHERE id = ?", (v_score, post_id))

    conn.commit()
    conn.close()

    return RedirectResponse(f"/community#post-{post_id}", status_code=303)


# ==============================================================================
# ROUTE: POST /community/bookmark/{post_id} (Save Case)
# ==============================================================================
@router.post("/community/bookmark/{post_id}")
async def community_toggle_bookmark(request: Request, post_id: int):
    from app import get_current_user

    user = get_current_user(request)
    if not user or not is_user_community_approved(user):
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM community_bookmarks WHERE post_id = ? AND user_id = ?", (post_id, user["id"]))
    existing = c.fetchone()

    if existing:
        c.execute("DELETE FROM community_bookmarks WHERE id = ?", (existing["id"],))
    else:
        c.execute("INSERT INTO community_bookmarks (post_id, user_id, created_at) VALUES (?, ?, ?)",
                  (post_id, user["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return RedirectResponse(f"/community#post-{post_id}", status_code=303)


# ==============================================================================
# ROUTE: POST /community/comment/{post_id} (Comments & Direct Replies)
# ==============================================================================
@router.post("/community/comment/{post_id}")
async def community_add_comment(
    request: Request,
    post_id: int,
    content: str = Form(...),
    parent_comment_id: int = Form(0)
):
    from app import get_current_user

    user = get_current_user(request)
    if not user or not is_user_community_approved(user):
        return RedirectResponse("/community", status_code=303)

    if not content or not content.strip():
        return RedirectResponse(f"/community#post-{post_id}", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    INSERT INTO community_comments (post_id, user_id, author_name, author_specialty, author_country, content, parent_comment_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_id,
        user["id"],
        user.get("name", "طبيب بيطري"),
        user.get("clinic_name", "طب بيطري"),
        user.get("country", "مصر"),
        content.strip(),
        parent_comment_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    c.execute("UPDATE community_posts SET comments_count = comments_count + 1 WHERE id = ?", (post_id,))

    # Trigger virality recalculation
    c.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,))
    p = c.fetchone()
    if p:
        v_score = compute_virality_score(dict(p))
        c.execute("UPDATE community_posts SET virality_score = ? WHERE id = ?", (v_score, post_id))

    conn.commit()
    conn.close()

    return RedirectResponse(f"/community#post-{post_id}", status_code=303)


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
    c.execute("SELECT user_id, image_path, video_path FROM community_posts WHERE id = ?", (post_id,))
    row = c.fetchone()
    if row:
        if user.get("is_admin") or row["user_id"] == user["id"]:
            if row["image_path"]:
                try: os.remove(os.path.join(UPLOAD_DIR, row["image_path"]))
                except Exception: pass
            if row["video_path"] and not row["video_path"].startswith("http"):
                try: os.remove(os.path.join(UPLOAD_DIR, row["video_path"]))
                except Exception: pass

            c.execute("DELETE FROM community_comments WHERE post_id = ?", (post_id,))
            c.execute("DELETE FROM community_likes WHERE post_id = ?", (post_id,))
            c.execute("DELETE FROM community_bookmarks WHERE post_id = ?", (post_id,))
            c.execute("DELETE FROM community_posts WHERE id = ?", (post_id,))
            conn.commit()
    conn.close()

    return RedirectResponse("/community", status_code=303)


# ==============================================================================
# ROUTE: GET /admin/community/boost/{post_id} (Admin Boost / Reach Expansion)
# ==============================================================================
@router.get("/admin/community/boost/{post_id}")
async def admin_toggle_post_boost(request: Request, post_id: int):
    from app import get_current_user

    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM community_posts WHERE id = ?", (post_id,))
    row = c.fetchone()
    if row:
        p = dict(row)
        new_boost = 0 if p.get("is_boosted", 0) else 1
        p["is_boosted"] = new_boost
        v_score = compute_virality_score(p)
        c.execute("UPDATE community_posts SET is_boosted = ?, virality_score = ? WHERE id = ?", (new_boost, v_score, post_id))
        conn.commit()
    conn.close()

    referer = request.headers.get("referer") or f"/community#post-{post_id}"
    return RedirectResponse(referer, status_code=303)


# ==============================================================================
# ROUTE: GET /admin/community/pin/{post_id} (Admin Pin to Top)
# ==============================================================================
@router.get("/admin/community/pin/{post_id}")
async def admin_toggle_post_pin(request: Request, post_id: int):
    from app import get_current_user

    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/community", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_pinned FROM community_posts WHERE id = ?", (post_id,))
    row = c.fetchone()
    if row:
        new_pin = 0 if row["is_pinned"] else 1
        c.execute("UPDATE community_posts SET is_pinned = ? WHERE id = ?", (new_pin, post_id))
        conn.commit()
    conn.close()

    referer = request.headers.get("referer") or f"/community#post-{post_id}"
    return RedirectResponse(referer, status_code=303)

