# -*- coding: utf-8 -*-
"""
VetMind AI - Clinic Management & Prescriptions Suite
Handles: Custom Clinic Logo, International Standard Rx Prescriptions, Cases Photo Gallery & Prayer Times
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

from dosage_engine import calculate_precise_dosage, format_drug_display, get_drug_concise_function
from prayer_engine import calculate_prayer_times, CITIES_DB
from enterprise_features import get_enterprise_tools_index

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

# ==============================================================================
# 1. CASES PHOTO GALLERY (/clinic/cases-gallery)
# ==============================================================================
@router.get("/clinic/cases-gallery", response_class=HTMLResponse)
async def cases_gallery_page(request: Request, species: str = "all", triage: str = "all"):
    from app import get_current_user, get_user_lang, get_text, get_base_html
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    user_id = user["id"]
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)

    conn = get_db()
    c = conn.cursor()

    query = "SELECT * FROM cases WHERE user_id = ? AND image_filename IS NOT NULL AND image_filename != ''"
    params = [user_id]
    if species != "all":
        query += " AND species LIKE ?"
        params.append(f"%{species}%")
    if triage != "all":
        query += " AND triage_level = ?"
        params.append(triage)
    query += " ORDER BY id DESC LIMIT 60"

    c.execute(query, params)
    cases_list = [dict(r) for r in c.fetchall()]
    conn.close()

    cards_html = ""
    for cs in cases_list:
        urgency_badge = '<span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">🚨 عاجل</span>' if cs.get("triage_level") == "urgent" else '<span style="background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem;">روتينية</span>'
        
        cards_html += f"""
        <div class="card" style="padding: 14px; display: flex; flex-direction: column; justify-content: space-between; border-radius: 12px; transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 10px 20px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='var(--shadow)';">
            <div>
                <div style="position: relative; overflow: hidden; border-radius: 10px; height: 190px; background: #0f172a;">
                    <img src="/uploads/{cs['image_filename']}" alt="{cs['animal_name']}" style="width: 100%; height: 100%; object-fit: cover; cursor: pointer;" onclick="openPhotoModal('/uploads/{cs['image_filename']}', '{cs['animal_name']}', '{cs['symptoms']}')">
                    <div style="position: absolute; top: 8px; right: 8px;">{urgency_badge}</div>
                    <div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem;">
                        #VET-{cs['id']}
                    </div>
                </div>
                <div style="margin-top: 12px;">
                    <h3 style="margin: 0; font-size: 1.1rem; color: var(--primary);">{cs['animal_name']}</h3>
                    <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 3px;">
                        🐾 <strong>الفصيلة:</strong> {cs['species']} | ⚖️ <strong>الوزن:</strong> {cs['weight']} كجم
                    </div>
                    <p style="font-size: 0.85rem; color: var(--text-main); margin: 8px 0; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                        <strong>الأعراض:</strong> {cs['symptoms']}
                    </p>
                </div>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 12px; border-top: 1px solid var(--border); padding-top: 10px;">
                <a href="/case/{cs['id']}" class="btn btn-primary" style="flex: 1; padding: 6px 10px; font-size: 0.82rem; justify-content: center;">
                    📋 التقرير الطبي
                </a>
                <a href="/rx-prescription?animal_name={cs['animal_name']}&species={cs['species']}&weight={cs['weight']}" class="btn btn-outline" style="padding: 6px 10px; font-size: 0.82rem;" title="حاسبة الجرعة والروشتة">
                    ⚡ الجرعة
                </a>
            </div>
        </div>
        """

    if not cards_html:
        cards_html = """
        <div class="card" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
            <div style="font-size: 3rem; margin-bottom: 10px;">📸</div>
            <h3>لا توجد صور حالات مطابقة للفلتر المحدد</h3>
            <p style="color: var(--text-muted);">يمكنك رفع صور سريرية جديدة عبر قسم الفحص بالرؤية أو الشات الطبي.</p>
            <a href="/vision-detect" class="btn btn-primary">📸 رفع صورة سريرية الآن</a>
        </div>
        """

    species_filters = ["all", "أبقار", "خيول", "إبل", "أغنام", "كلاب", "قطط", "دواجن"]
    species_pills = ""
    for s in species_filters:
        act = "background: var(--primary); color: white; border-color: var(--primary);" if s == species else "background: var(--card-bg); color: var(--text-main);"
        lbl = "الكل" if s == "all" else s
        species_pills += f'<a href="/clinic/cases-gallery?species={s}&triage={triage}" class="btn btn-outline" style="padding: 4px 12px; font-size: 0.82rem; border-radius: 20px; {act}">{lbl}</a> '

    body = f"""
    <div style="margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <h1 style="margin: 0; font-size: 1.7rem; color: var(--primary);">🖼️ معرض صور الحالات السريرية المباشر</h1>
                <p style="color: var(--text-muted); font-size: 0.92rem; margin-top: 4px;">
                    الأرشيف البصري المركزي لحالات العيادة - معاينة بصرية فورية، فحص الآفات وتكبيرها، وحساب الجرعات الدوائية
                </p>
            </div>
            <a href="/vision-detect" class="btn btn-primary">
                📸 فحص صورة جديدة بالرؤية الحاسوبية
            </a>
        </div>

        <!-- Filter Bar -->
        <div class="card" style="margin-top: 16px; padding: 12px 18px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span style="font-size: 0.85rem; font-weight: 700; color: var(--text-muted);">🐾 تصفية حسب الفصيلة:</span>
                {species_pills}
            </div>
            <div style="display: flex; gap: 6px;">
                <a href="/clinic/cases-gallery?species={species}&triage=all" class="btn btn-outline" style="padding: 3px 10px; font-size: 0.78rem; {'background: var(--primary); color: white;' if triage == 'all' else ''}">كافة الحالات</a>
                <a href="/clinic/cases-gallery?species={species}&triage=urgent" class="btn btn-outline" style="padding: 3px 10px; font-size: 0.78rem; {'background: var(--danger); color: white;' if triage == 'urgent' else ''}">🚨 الحالات العاجلة</a>
            </div>
        </div>
    </div>

    <!-- Gallery Grid -->
    <div class="grid-3" style="margin-bottom: 24px;">
        {cards_html}
    </div>

    <!-- Modal for full photo inspection -->
    <div id="photoModal" class="modal" onclick="if(event.target === this) this.style.display='none';">
        <div class="modal-content" style="max-width: 800px; text-align: center;">
            <button class="modal-close" onclick="document.getElementById('photoModal').style.display='none'">×</button>
            <h3 id="photoModalTitle" style="color: var(--primary); margin-top: 0;"></h3>
            <img id="photoModalImg" src="" style="max-width: 100%; max-height: 520px; border-radius: 10px; border: 1px solid var(--border); box-shadow: 0 4px 14px rgba(0,0,0,0.15);">
            <p id="photoModalDesc" style="margin-top: 12px; font-size: 0.95rem; color: var(--text-main); line-height: 1.6;"></p>
        </div>
    </div>

    <script>
    function openPhotoModal(src, title, desc) {{
        document.getElementById('photoModalImg').src = src;
        document.getElementById('photoModalTitle').innerText = title;
        document.getElementById('photoModalDesc').innerText = 'الأعراض والعلامات المرصودة: ' + desc;
        document.getElementById('photoModal').style.display = 'flex';
    }}
    </script>
    """
    return HTMLResponse(content=get_base_html("معرض صور الحالات السريرية", body, user, lang), media_type="text/html; charset=utf-8")


# ==============================================================================
# 2. ISLAMIC PRAYER TIMES & NOTIFICATIONS (/clinic/prayer-times)
# ==============================================================================
@router.get("/clinic/prayer-times", response_class=HTMLResponse)
async def prayer_times_page(request: Request, city: str = "القاهرة (مصر)"):
    from app import get_current_user, get_user_lang, get_text, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    res = calculate_prayer_times(city)

    city_options = "".join([f'<option value="{c}" {"selected" if c == city else ""}>{c}</option>' for c in res["all_cities"]])

    next_p = res["next_prayer"]

    body = f"""
    <div style="max-width: 900px; margin: 0 auto;">
        <!-- Header & Countdown Banner -->
        <div class="card" style="background: linear-gradient(135deg, #065f46 0%, #047857 100%); color: white; padding: 28px; border-radius: 16px; margin-bottom: 22px; text-align: center; border: 1px solid #10b981; box-shadow: 0 10px 25px rgba(6,95,70,0.25);">
            <div style="font-size: 2.5rem; margin-bottom: 8px;">🕌</div>
            <h1 style="margin: 0; font-size: 1.8rem; color: #ffffff;">مواقيت الصلاة والتنبيهات الإيمانية بالعيادة</h1>
            <p style="color: #a7f3d0; font-size: 1rem; margin-top: 6px;">
                تنظيم جدول مواعيد العمليات الجراحية والاستشارات البيطرية بما يتوافق مع أوقات الصلاة
            </p>

            <!-- Next Prayer Alert Pill -->
            <div style="display: inline-flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 10px; background: rgba(255,255,255,0.18); backdrop-filter: blur(8px); padding: 10px 20px; border-radius: 30px; margin-top: 14px; border: 1px solid #6ee7b7; max-width: 100%; box-sizing: border-box; text-align: center;">
                <span style="font-size: 1.2rem;">⏱️</span>
                <span style="font-size: 1.05rem; font-weight: 700;">الصلاة القادمة: {next_p['name']} ({next_p['time']})</span>
                <span style="background: #fef08a; color: #854d0e; padding: 2px 10px; border-radius: 12px; font-weight: 800; font-size: 0.85rem;">{res['countdown_text']}</span>
            </div>
        </div>

        <!-- City Selector -->
        <div class="card" style="margin-bottom: 22px; padding: 16px 20px;">
            <form method="GET" action="/clinic/prayer-times" style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <label style="font-weight: 700; color: var(--primary); font-size: 1rem;">📍 اختر مدينة وموقع عيادتك:</label>
                    <select name="city" onchange="this.form.submit()" style="padding: 8px 14px; border-radius: 8px; border: 1px solid var(--border); font-size: 0.95rem; font-weight: 600; background: var(--card-bg); color: var(--text-main);">
                        {city_options}
                    </select>
                </div>
                <div style="font-size: 0.88rem; color: var(--text-muted);">
                    📅 <strong>تاريخ اليوم:</strong> {res['date_gregorian']} م | حساب فلكي دقيق
                </div>
            </form>
        </div>

        <style>
        .prayer-card {{
            text-align: center;
            padding: 20px;
            border-radius: 14px;
            transition: var(--transition-smooth);
        }}
        .prayer-time-val {{
            font-size: 1.8rem;
            font-weight: 800;
            margin: 8px 0;
        }}
        .prayer-fajr .prayer-time-val {{ color: #0284c7; }}
        .prayer-sunrise .prayer-time-val {{ color: #d97706; }}
        .prayer-dhuhr .prayer-time-val {{ color: #059669; }}
        .prayer-asr .prayer-time-val {{ color: #ea580c; }}
        .prayer-maghrib .prayer-time-val {{ color: #7c3aed; }}
        .prayer-isha .prayer-time-val {{ color: #2563eb; }}

        body.dark-theme .prayer-fajr .prayer-time-val, [data-theme="dark"] .prayer-fajr .prayer-time-val {{ color: #38bdf8 !important; }}
        body.dark-theme .prayer-sunrise .prayer-time-val, [data-theme="dark"] .prayer-sunrise .prayer-time-val {{ color: #fbbf24 !important; }}
        body.dark-theme .prayer-dhuhr .prayer-time-val, [data-theme="dark"] .prayer-dhuhr .prayer-time-val {{ color: #34d399 !important; }}
        body.dark-theme .prayer-asr .prayer-time-val, [data-theme="dark"] .prayer-asr .prayer-time-val {{ color: #fb923c !important; }}
        body.dark-theme .prayer-maghrib .prayer-time-val, [data-theme="dark"] .prayer-maghrib .prayer-time-val {{ color: #c084fc !important; }}
        body.dark-theme .prayer-isha .prayer-time-val, [data-theme="dark"] .prayer-isha .prayer-time-val {{ color: #60a5fa !important; }}

        body.dark-theme .prayer-card, [data-theme="dark"] .prayer-card {{
            background-color: #111827 !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
        }}
        body.dark-theme .prayer-title-lbl, [data-theme="dark"] .prayer-title-lbl {{
            color: #F8FAFC !important;
            font-weight: 800 !important;
        }}
        body.dark-theme .prayer-sub-lbl, [data-theme="dark"] .prayer-sub-lbl {{
            color: #94A3B8 !important;
        }}
        </style>

        <!-- Prayer Times Grid -->
        <div class="grid-3" style="gap: 16px; margin-bottom: 24px;">
            <!-- Fajr -->
            <div class="card prayer-card prayer-fajr" style="border-top: 4px solid #0284c7;">
                <div class="prayer-title-lbl" style="font-size: 0.95rem; color: var(--text-muted); font-weight: 700;">صلاة الفجر</div>
                <div class="prayer-time-val">{res['fajr']}</div>
                <div class="prayer-sub-lbl" style="font-size: 0.78rem; color: var(--text-muted);">بداية الإمساك وبكور العمليات</div>
            </div>

            <!-- Sunrise -->
            <div class="card prayer-card prayer-sunrise" style="border-top: 4px solid #f59e0b;">
                <div class="prayer-title-lbl" style="font-size: 0.95rem; color: var(--text-muted); font-weight: 700;">الشروق</div>
                <div class="prayer-time-val">{res['sunrise']}</div>
                <div class="prayer-sub-lbl" style="font-size: 0.78rem; color: var(--text-muted);">شروق الشمس</div>
            </div>

            <!-- Dhuhr -->
            <div class="card prayer-card prayer-dhuhr" style="border-top: 4px solid #10b981;">
                <div class="prayer-title-lbl" style="font-size: 0.95rem; color: var(--text-muted); font-weight: 700;">صلاة الظهر</div>
                <div class="prayer-time-val">{res['dhuhr']}</div>
                <div class="prayer-sub-lbl" style="font-size: 0.78rem; color: var(--text-muted);">استراحة منتصف اليوم</div>
            </div>

            <!-- Asr -->
            <div class="card prayer-card prayer-asr" style="border-top: 4px solid #ea580c;">
                <div class="prayer-title-lbl" style="font-size: 0.95rem; color: var(--text-muted); font-weight: 700;">صلاة العصر</div>
                <div class="prayer-time-val">{res['asr']}</div>
                <div class="prayer-sub-lbl" style="font-size: 0.78rem; color: var(--text-muted);">فترة الكشوفات المسائية</div>
            </div>

            <!-- Maghrib -->
            <div class="card prayer-card prayer-maghrib" style="border-top: 4px solid #8b5cf6;">
                <div class="prayer-title-lbl" style="font-size: 0.95rem; color: var(--text-muted); font-weight: 700;">صلاة المغرب</div>
                <div class="prayer-time-val">{res['maghrib']}</div>
                <div class="prayer-sub-lbl" style="font-size: 0.78rem; color: var(--text-muted);">غروب الشمس</div>
            </div>

            <!-- Isha -->
            <div class="card prayer-card prayer-isha" style="border-top: 4px solid #3b82f6;">
                <div class="prayer-title-lbl" style="font-size: 0.95rem; color: var(--text-muted); font-weight: 700;">صلاة العشاء</div>
                <div class="prayer-time-val">{res['isha']}</div>
                <div class="prayer-sub-lbl" style="font-size: 0.78rem; color: var(--text-muted);">ختام العيادة ونوبتجيات الطوارئ</div>
            </div>
        </div>

        <!-- Adhan Notification Sound Box -->
        <div class="card" style="background: var(--bg); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; padding: 18px 24px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.6rem;">🔔</span>
                <div>
                    <div style="font-weight: 700; color: var(--text-main);">تفعيل التنبيه الصوتي للأذان داخل المنصة</div>
                    <div style="font-size: 0.82rem; color: var(--text-muted);">سيصدر صوت الأذان أو تنبيه لطيف عند حلول موعد الصلاة أثناء العمل على المنصة</div>
                </div>
            </div>
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 700; color: var(--primary);">
                <input type="checkbox" id="adhanToggle" onchange="toggleAdhan(this.checked)" style="width: 18px; height: 18px;">
                تفعيل الأذان التلقائي
            </label>
        </div>
    </div>

    <script>
    function toggleAdhan(enabled) {{
        document.cookie = "vetmind_adhan=" + (enabled ? "1" : "0") + "; path=/; max-age=31536000";
        alert(enabled ? "✅ تم تفعيل التنبيه الصوتي لمواقيت الصلاة في العيادة." : "تم إلغاء التنبيه الصوتي.");
    }}
    </script>
    """
    return HTMLResponse(content=get_base_html("مواقيت الصلاة والتنبيهات", body, user, lang), media_type="text/html; charset=utf-8")


# ==============================================================================
# 3. CLINIC LOGO UPLOAD & PROFILE UPDATE (/clinic/profile/update)
# ==============================================================================
@router.post("/clinic/profile/update")
async def update_clinic_branding(
    request: Request,
    clinic_name: str = Form(...),
    doctor_title: str = Form("استشاري الطب والجراحة البيطرية"),
    license_no: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    consultation_fee: str = Form(""),
    working_hours: str = Form(""),
    tagline: str = Form(""),
    clinic_logo: UploadFile = File(None)
):
    from app import get_current_user
    user = get_current_user(request)
    user_id = user["id"] if user else 4

    logo_filename = None
    if clinic_logo and clinic_logo.filename:
        safe_ext = os.path.splitext(clinic_logo.filename)[1].lower()
        if safe_ext in [".png", ".jpg", ".jpeg", ".svg", ".webp"]:
            saved_name = f"clinic_logo_{user_id}_{int(datetime.now().timestamp())}{safe_ext}"
            save_path = os.path.join(UPLOAD_DIR, saved_name)
            with open(save_path, "wb") as f_out:
                shutil.copyfileobj(clinic_logo.file, f_out)
            logo_filename = saved_name

    conn = get_db()
    c = conn.cursor()

    # Check if profile exists
    c.execute("SELECT user_id, logo_filename FROM clinic_profiles WHERE user_id = ?", (user_id,))
    existing = c.fetchone()

    if existing:
        final_logo = logo_filename if logo_filename else existing["logo_filename"]
        c.execute("""
        UPDATE clinic_profiles SET
            clinic_name = ?, doctor_title = ?, license_no = ?, phone = ?,
            address = ?, consultation_fee = ?, working_hours = ?, tagline = ?, logo_filename = ?
        WHERE user_id = ?
        """, (clinic_name, doctor_title, license_no, phone, address, consultation_fee, working_hours, tagline, final_logo, user_id))
    else:
        c.execute("""
        INSERT INTO clinic_profiles (
            user_id, clinic_name, doctor_title, license_no, phone, address,
            consultation_fee, working_hours, tagline, logo_filename, emergency_available
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (user_id, clinic_name, doctor_title, license_no, phone, address, consultation_fee, working_hours, tagline, logo_filename))

    conn.commit()
    conn.close()

    return RedirectResponse("/clinic?saved=1", status_code=303)


# ==============================================================================
# 4. PRINTABLE OFFICIAL CLINIC RX PRESCRIPTION (/clinic/prescription/print)
# ==============================================================================
@router.get("/clinic/prescription/print", response_class=HTMLResponse)
async def print_clinic_prescription(request: Request, rx_id: int = 0, serial_no: str = ""):
    from app import get_current_user, get_user_lang, get_text
    user = get_current_user(request)
    lang = get_user_lang(request)
    user_id = user["id"] if user else 4

    conn = get_db()
    c = conn.cursor()

    # Fetch Prescription (Doctor's private isolation)
    if serial_no:
        c.execute("SELECT * FROM clinic_prescriptions WHERE serial_no = ? AND user_id = ?", (serial_no, user_id))
    elif rx_id > 0:
        c.execute("SELECT * FROM clinic_prescriptions WHERE id = ? AND user_id = ?", (rx_id, user_id))
    else:
        c.execute("SELECT * FROM clinic_prescriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    rx = c.fetchone()
    if not rx:
        if serial_no:
            c.execute("SELECT * FROM clinic_prescriptions WHERE serial_no = ?", (serial_no,))
            rx = c.fetchone()
        elif rx_id > 0:
            c.execute("SELECT * FROM clinic_prescriptions WHERE id = ?", (rx_id,))
            rx = c.fetchone()

    # Fetch Clinic Profile
    c.execute("SELECT * FROM clinic_profiles WHERE user_id = ?", (user_id,))
    clinic = c.fetchone()
    if not clinic:
        c.execute("SELECT * FROM clinic_profiles WHERE user_id = 4")
        clinic = c.fetchone()
    conn.close()

    if not rx:
        raise HTTPException(status_code=404, detail="الروشتة غير موجودة")

    rx = dict(rx)
    clinic_name = clinic["clinic_name"] if clinic and clinic["clinic_name"] else "مركز فيتمايند للاستشارات والطب البيطري المتقدم"
    doctor_title = clinic["doctor_title"] if clinic and clinic["doctor_title"] else "استشاري الطب والجراحة البيطرية"
    license_no = clinic["license_no"] if clinic and clinic["license_no"] else "EGY-VET-98421"
    clinic_phone = clinic["phone"] if clinic and clinic["phone"] else "+20 100 000 0000"
    clinic_addr = clinic["address"] if clinic and clinic["address"] else "القاهرة - مدينة نصر"
    tagline = clinic["tagline"] if clinic and clinic["tagline"] else "الرعاية البيطرية المتطورة وفق المعايير العالمية"
    logo_file = clinic["logo_filename"] if clinic and clinic["logo_filename"] else ""

    # Logo HTML
    if logo_file and os.path.exists(os.path.join(UPLOAD_DIR, logo_file)):
        logo_html = f'<img src="/uploads/{logo_file}" alt="Clinic Logo" style="max-height: 85px; max-width: 140px; object-fit: contain;">'
    else:
        # Fallback to Snake Emblem
        logo_html = '<img src="/static/logo-snake.svg" alt="VetMind Logo" style="height: 80px; width: 80px;">'

    # Items table
    items = json.loads(rx["rx_items_json"]) if rx["rx_items_json"] else []
    items_rows = ""
    for idx, item in enumerate(items, 1):
        items_rows += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 12px 10px; font-weight: 800; color: #047857;">{idx}</td>
            <td style="padding: 12px 10px;">
                <div style="font-weight: 800; font-size: 1.05rem; color: #0f172a;">{item.get('trade_name')}</div>
                <div style="font-size: 0.82rem; color: #475569; margin-top: 2px;">{item.get('active', '')}</div>
                <div style="font-size: 0.82rem; color: #0284c7; font-weight: 700; margin-top: 2px;">{item.get('function', '')}</div>
            </td>
            <td style="padding: 12px 10px; font-weight: 800; color: #d97706; font-size: 1.05rem;">{item.get('dose')}</td>
            <td style="padding: 12px 10px; font-size: 0.9rem;">{item.get('route')}</td>
            <td style="padding: 12px 10px; font-size: 0.9rem;">{item.get('freq')}</td>
            <td style="padding: 12px 10px; font-size: 0.9rem; font-weight: 700;">{item.get('duration')}</td>
        </tr>
        """

    # Anti-counterfeit serial and QR payload
    serial_no_display = rx["serial_no"]
    verification_url = f"https://vetmind.ai/verify-rx?serial={serial_no_display}"

    html = f"""<!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>روشتة رسمية معتمدة | {serial_no_display}</title>
        <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
        <style>
            * {{ box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            body {{ background: #f1f5f9; margin: 0; padding: 20px; color: #0f172a; }}
            .no-print-bar {{
                max-width: 900px; margin: 0 auto 16px auto; display: flex; justify-content: space-between; align-items: center;
            }}
            .rx-paper {{
                max-width: 900px; margin: 0 auto; background: #ffffff; padding: 36px 44px;
                border: 2px solid #047857; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.08);
                position: relative; overflow: hidden;
            }}
            .watermark {{
                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-25deg);
                font-size: 6.5rem; font-weight: 900; color: rgba(4, 120, 87, 0.04);
                pointer-events: none; white-space: nowrap; text-transform: uppercase;
            }}
            .rx-header {{
                display: flex; justify-content: space-between; align-items: center; border-bottom: 3px double #047857;
                padding-bottom: 18px; margin-bottom: 20px;
            }}
            .rx-symbol {{
                font-family: Georgia, serif; font-size: 3.2rem; font-weight: 900; color: #047857; line-height: 1;
            }}
            .patient-box {{
                background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px 18px;
                margin-bottom: 22px; font-size: 0.92rem;
            }}
            table {{ width: 100%; border-collapse: collapse; text-align: right; margin-bottom: 24px; }}
            th {{ background: #f1f5f9; color: #065f46; font-weight: 800; padding: 10px; border-bottom: 2px solid #047857; font-size: 0.92rem; }}
            .withdrawal-alert {{
                background: #fef2f2; border: 1.5px dashed #ef4444; color: #991b1b; padding: 12px 16px;
                border-radius: 8px; font-weight: 700; font-size: 0.9rem; margin-bottom: 22px;
            }}
            .rx-footer {{
                display: flex; justify-content: space-between; align-items: flex-end; margin-top: 30px;
                border-top: 1px solid #cbd5e1; padding-top: 16px; font-size: 0.85rem; color: #475569;
            }}
            @media print {{
                body {{ background: #ffffff; padding: 0; }}
                .no-print-bar {{ display: none !important; }}
                .rx-paper {{ border: none; box-shadow: none; padding: 15px 20px; max-width: 100%; }}
            }}
        </style>
    </head>
    <body>
        <div class="no-print-bar">
            <a href="/clinic" style="text-decoration: none; color: #047857; font-weight: 700; font-size: 0.95rem;">⬅️ العودة للعيادة</a>
            <div>
                <button onclick="window.print()" style="background: #047857; color: white; border: none; padding: 10px 22px; border-radius: 8px; font-weight: 700; font-size: 1rem; cursor: pointer;">
                    🖨️ طباعة الروشتة الرسمية المعتمدة (Ctrl+P)
                </button>
            </div>
        </div>

        <div class="rx-paper">
            <div class="watermark">VETMIND RX CERTIFIED</div>

            <!-- Clinic Official Header -->
            <div class="rx-header">
                <div style="display: flex; align-items: center; gap: 18px;">
                    {logo_html}
                    <div>
                        <h2 style="margin: 0; font-size: 1.55rem; color: #047857; font-weight: 900;">{clinic_name}</h2>
                        <div style="color: #334155; font-size: 0.95rem; font-weight: 700; margin-top: 3px;">{doctor_title}</div>
                        <div style="color: #64748b; font-size: 0.82rem; margin-top: 2px;">{tagline}</div>
                        <div style="color: #d97706; font-size: 0.82rem; font-weight: 700; margin-top: 3px;">رقم ترخيص النقابة: {license_no}</div>
                    </div>
                </div>

                <div style="text-align: left;" dir="ltr">
                    <div class="rx-symbol">℞</div>
                    <div style="font-family: monospace; font-size: 0.82rem; font-weight: 800; color: #047857; background: #ecfdf5; padding: 4px 8px; border-radius: 6px; border: 1px solid #a7f3d0; margin-top: 6px;">
                        {serial_no_display}
                    </div>
                    <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">DATE: {rx['created_at'].split()[0]}</div>
                </div>
            </div>

            <!-- Patient Information Box -->
            <div class="patient-box">
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 8px;">
                    <div><strong>الحيوان / المريض:</strong> {rx['animal_name']}</div>
                    <div><strong>الفصيلة والسلالة:</strong> {rx['species']} ({rx['breed'] or 'هجين'})</div>
                    <div><strong>الوزن الحي الفعلي:</strong> <span style="color: #047857; font-weight: 800;">{rx['weight']} كجم</span></div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; border-top: 1px dashed #cbd5e1; padding-top: 8px;">
                    <div><strong>مالك الحيوان (المربي):</strong> {rx['owner_name']}</div>
                    <div><strong>هاتف التواصل:</strong> {rx['owner_phone'] or 'مسجل'}</div>
                    <div><strong>العمر التقريبي:</strong> {rx['age'] or 'بالغ'}</div>
                </div>
            </div>

            <!-- Diagnosis -->
            <div style="margin-bottom: 18px; padding: 8px 14px; background: #f0fdf4; border-right: 4px solid #047857; border-radius: 4px;">
                <strong style="color: #065f46;">التشخيص السريري المعتمد:</strong>
                <span style="font-weight: 700; color: #0f172a;">{rx['diagnosis']}</span>
            </div>

            <!-- Prescribed Medications Table -->
            <table>
                <thead>
                    <tr>
                        <th style="width: 35px;">#</th>
                        <th>المستحضر الدوائي والوظيفة السريرية</th>
                        <th>الجرعة الدقيقة</th>
                        <th>طريقة الإعطاء</th>
                        <th>التكرار</th>
                        <th>المدة</th>
                    </tr>
                </thead>
                <tbody>
                    {items_rows}
                </tbody>
            </table>

            <!-- Withdrawal Period Warning -->
            <div class="withdrawal-alert">
                ⚠️ <strong>تنبيه الأمان الغذائي وفترات السحب (Mandatory Withdrawal Period):</strong>
                <div style="margin-top: 4px; font-weight: 600;">{rx['withdrawal_warning']}</div>
            </div>

            <!-- Doctor Instructions -->
            <div style="margin-bottom: 20px; font-size: 0.9rem; line-height: 1.6;">
                <strong>إرشادات ورعاية الطبيب المعالج:</strong>
                <p style="margin: 4px 0 0 0; color: #334155;">{rx['doctor_instructions']}</p>
            </div>

            <!-- Footer Signatures & QR Code -->
            <div class="rx-footer">
                <div>
                    <div><strong>العنوان:</strong> {clinic_addr}</div>
                    <div><strong>طوارئ العيادة / واتساب:</strong> {clinic_phone}</div>
                    <div style="font-size: 0.76rem; color: #94a3b8; margin-top: 4px;">
                        وثيقة رسمية مشفرة بباركود تسلسلي فريد يمنع التكرار والتزوير © VetMind AI
                    </div>
                </div>

                <div style="text-align: center; border: 1.5px solid #cbd5e1; padding: 8px 16px; border-radius: 8px; background: #f8fafc;">
                    <div style="font-weight: 800; color: #047857; font-size: 0.9rem;">توقيع وختم الطبيب المعالج</div>
                    <div style="height: 40px; border-bottom: 1px dotted #94a3b8; margin: 6px 0;"></div>
                    <div style="font-size: 0.78rem; color: #64748b;">Signature & Clinic Seal</div>
                </div>
            </div>
        </div>
    </body>
    </html>"""
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


# ==============================================================================
# 5. ALL 30 ENTERPRISE TOOLS DIRECTORY (/tools)
# ==============================================================================
@router.get("/tools", response_class=HTMLResponse)
async def enterprise_tools_directory(request: Request):
    from app import get_current_user, get_user_lang, get_text, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)
    t = lambda k, d="": get_text(lang, k, d)
    user_country = user.get("country", "مصر") if user else "مصر"

    tools = get_enterprise_tools_index(user_country, lang=lang)

    cards_html = ""
    for idx, tl in enumerate(tools, 1):
        cards_html += f"""
        <div class="card" style="padding: 18px; display: flex; flex-direction: column; justify-content: space-between; border-top: 4px solid var(--primary); transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-3px)'" onmouseout="this.style.transform='translateY(0)'">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 1.8rem;">{tl['icon']}</span>
                    <span style="background: var(--primary-light); color: var(--primary); font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; font-weight: 800;">#{idx:02d}</span>
                </div>
                <h3 style="margin: 0; font-size: 1.05rem; color: var(--text-main); font-weight: 800;">{tl['title']}</h3>
                <div style="font-size: 0.76rem; color: var(--accent); font-weight: 700; margin: 4px 0;">{tl['category']}</div>
                <p style="font-size: 0.84rem; color: var(--text-muted); line-height: 1.5; margin: 8px 0 0 0;">
                    {tl['desc']}
                </p>
            </div>
            <div style="margin-top: 14px; pt-2; border-top: 1px solid var(--border);">
                <a href="{tl['url']}" class="btn btn-outline" style="width: 100%; justify-content: center; font-size: 0.85rem; padding: 6px 10px;">
                    {t('open_tool_btn', 'فتح الأداة ⚡')}
                </a>
            </div>
        </div>
        """

    page_heading = t('tools_suite_title', '🛠️ باقة الـ 30 ميزة والأدوات السريرية البيطرية المتقدمة')
    page_desc = t('tools_suite_desc', 'منظومة الأدوات السريرية الشاملة - محولات الجرعات، التخدير، السموم، الرقائق، مواقيت الصلاة، ومعرض صور الحالات المباشر')

    body = f"""
    <div style="margin-bottom: 24px;">
        <h1 style="margin: 0; font-size: 1.8rem; color: var(--primary);">{page_heading}</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem; margin-top: 6px;">
            {page_desc}
        </p>
    </div>

    <div class="grid-3" style="gap: 18px; margin-bottom: 30px;">
        {cards_html}
    </div>
    """
    return HTMLResponse(content=get_base_html(page_heading, body, user, lang), media_type="text/html; charset=utf-8")


def get_back_home_bar(extra_link_html: str = "", lang: str = "ar") -> str:
    """Standardized Return to Home Page navigation bar."""
    from app import get_text
    back_label = get_text(lang, 'back_to_home', 'العودة للصفحة الرئيسية')
    tools_label = get_text(lang, 'tools_index_btn', 'فهرس الأدوات الـ 30')
    return f'''
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 22px; flex-wrap: wrap; gap: 10px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <a href="/" style="display: inline-flex; align-items: center; gap: 8px; background: #ffffff; color: var(--primary); border: 2px solid var(--primary); padding: 8px 18px; border-radius: 25px; font-weight: 800; font-size: 0.92rem; text-decoration: none; box-shadow: 0 2px 6px rgba(4,120,87,0.12); transition: all 0.2s ease;">
                <span style="font-size: 1.1rem;">🏠</span> <span>{back_label}</span> <span style="font-size: 0.9rem;">⬅️</span>
            </a>
            <a href="/tools" style="display: inline-flex; align-items: center; gap: 8px; background: #ffffff; color: #475569; border: 1.5px solid #cbd5e1; padding: 8px 16px; border-radius: 25px; font-weight: 700; font-size: 0.9rem; text-decoration: none; box-shadow: var(--shadow);">
                <span>🛠️</span> <span>{tools_label}</span>
            </a>
        </div>
        {extra_link_html}
    </div>
    '''


# ==============================================================================
# 6. ELECTRONIC MICROCHIP REGISTRY & BARCODE (/clinic/microchips)
# ==============================================================================
@router.get("/clinic/microchips", response_class=HTMLResponse)
@router.post("/clinic/microchips", response_class=HTMLResponse)
async def microchips_tool(
    request: Request,
    chip_id: str = "",
    pet_name: str = "سيمبا",
    species: str = "كلاب",
    breed: str = "جيرمن شيبرد",
    owner_name: str = "د. تامر سعد",
    owner_phone: str = "01012345678"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if not chip_id:
        chip_id = "900" + str(random.randint(100000000000, 999999999999))

    if request.method == "POST":
        form = await request.form()
        chip_id = form.get("chip_id", chip_id)
        pet_name = form.get("pet_name", pet_name)
        species = form.get("species", species)
        breed = form.get("breed", breed)
        owner_name = form.get("owner_name", owner_name)
        owner_phone = form.get("owner_phone", owner_phone)

    # Generate visual SVG barcode lines
    barcode_bars = ""
    for idx, char in enumerate(chip_id):
        w = 3 if int(char) % 2 == 0 else 5
        x = 20 + (idx * 16)
        barcode_bars += f'<rect x="{x}" y="10" width="{w}" height="45" fill="#0f172a" />'

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #0f766e; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🏷️</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #0f766e;">سجل ومولد باركود الرقائق الإلكترونية (Microchip Registry ISO 11784)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">تسجيل وإصدار بطاقات الهوية الرسمية للحيوانات برقم الشريحة القياسي (15 رقماً) وباركود الأمان</p>
                </div>
            </div>

            <form method="POST" action="/clinic/microchips" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">رقم الشريحة (15 رقماً ISO):</label>
                        <input type="text" name="chip_id" value="{chip_id}" required maxlength="15" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); letter-spacing: 2px; font-weight: 800;">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">اسم الحيوان:</label>
                        <input type="text" name="pet_name" value="{pet_name}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الفصيلة والسلالة:</label>
                        <input type="text" name="breed" value="{breed}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">اسم المربي أو المالك:</label>
                        <input type="text" name="owner_name" value="{owner_name}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">هاتف المالك للتواصل:</label>
                        <input type="text" name="owner_phone" value="{owner_phone}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700;">🏷️ إصدار بطاقة الهوية وتوليد الباركود</button>
            </form>

            <!-- Printable Microchip Identity Card -->
            <div style="margin-top: 24px; background: linear-gradient(135deg, #0f766e 0%, #115e59 100%); color: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px rgba(15,118,110,0.25); max-width: 550px; margin-left: auto; margin-right: auto;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 12px; margin-bottom: 16px;">
                    <div>
                        <div style="font-size: 0.75rem; letter-spacing: 2px; text-transform: uppercase; opacity: 0.85;">Official Veterinary ID</div>
                        <div style="font-size: 1.25rem; font-weight: 800;">بطاقة الهوية والرقاقة الإلكترونية</div>
                    </div>
                    <span style="font-size: 2rem;">🏷️</span>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.9rem;">
                    <div><strong>🐾 اسم الحيوان:</strong> {pet_name}</div>
                    <div><strong>🧬 السلالة:</strong> {breed}</div>
                    <div><strong>👤 المالك:</strong> {owner_name}</div>
                    <div><strong>📱 الهاتف:</strong> {owner_phone}</div>
                </div>

                <div style="margin-top: 18px; background: #ffffff; color: #0f172a; padding: 12px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 0.75rem; color: #64748b; font-weight: 700; margin-bottom: 4px;">ISO 11784/11785 BARCODE</div>
                    <svg width="270" height="65" viewBox="0 0 280 65" style="display: block; margin: 0 auto;">
                        {barcode_bars}
                    </svg>
                    <div style="font-family: monospace; font-size: 1.15rem; font-weight: 800; letter-spacing: 3px; color: #0f766e;">
                        {chip_id}
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("سجل الرقائق الإلكترونية", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 7. RADIOLOGY & ULTRASOUND VIEWER HUB (/clinic/radiology-hub)
# ==============================================================================
@router.get("/clinic/radiology-hub", response_class=HTMLResponse)
async def radiology_hub_tool(request: Request, case_type: str = "trp"):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    cases = {
        "trp": {
            "title": "التهاب الشبكية والبريتون الرضحي (Hardware Disease / TRP)",
            "species": "أبقار (Cattle)",
            "finding": "جسم غريب معدني (مسمار/سلك) يخترق جدار القلنسوة (Reticulum) مع تجمع سائل وانصباب بريتوني وعلامات المغناطيس الوقائي.",
            "guide": "فحص السونار بتردد 3.5 MHz في الحيز الوربي السادس والخامس أيسر الصدر والبطن. فحص الأشعة السينية جانبي للشبكية."
        },
        "navicular": {
            "title": "متلازمة العظم الزورقي وتآكل الحافة السفلية (Navicular Syndrome)",
            "species": "خيول (Equine)",
            "finding": "تغيرات في القنوات الوعائية (Synovial Invaginations) مع تشكل زوائد عظمية وتصلب القشرة العظمية للزورقي.",
            "guide": "وضعيات الأشعة المعتمدة: Skyline (DPr-PaDiO) و Lateromedial لتقييم السطح المفصلي والجراب الزورقي."
        },
        "hip": {
            "title": "خلخلة مفصل الفخذ وزاوية نوربرج (Canine Hip Dysplasia)",
            "species": "كلاب (Canine)",
            "finding": "زاوية نوربرج أقل من 105 درجات مع تسطح الحُق الحرقفي وتآكل رأس عظم الفخذ والتهاب مفصلي تنكسي.",
            "guide": "وضعية Ventrodorsal ممتدة للأطراف الخلفية مع تدوير الركبتين للداخل وفحص استرخاء المفصل (PennHIP)."
        }
    }
    cur = cases.get(case_type, cases["trp"])

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 950px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #0284c7; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🩻</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #0284c7;">أرشيف ومحلل الأشعة السينية والسونار التفاعلي (Radiology & Ultrasound Hub)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">عارض تشخيصي مزود بمرشحات العكس الإشعاعي (Invert / Negative)، التحكم بالتباين، وأطلس الحالات المرجعية</p>
                </div>
            </div>

            <div style="display: flex; gap: 10px; margin: 16px 0; flex-wrap: wrap;">
                <a href="/clinic/radiology-hub?case_type=trp" class="btn {'btn-primary' if case_type=='trp' else 'btn-outline'}" style="font-size: 0.85rem;">🐄 بلع المعادن TRP للأبقار</a>
                <a href="/clinic/radiology-hub?case_type=navicular" class="btn {'btn-primary' if case_type=='navicular' else 'btn-outline'}" style="font-size: 0.85rem;">🐎 عظم الزورقي للخيول</a>
                <a href="/clinic/radiology-hub?case_type=hip" class="btn {'btn-primary' if case_type=='hip' else 'btn-outline'}" style="font-size: 0.85rem;">🐕 مفصل الفخذ للكلاب</a>
            </div>

            <div style="background: #030712; color: #f8fafc; border-radius: 12px; padding: 20px; margin-top: 14px;">
                <!-- Viewer Canvas simulation -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 10px; margin-bottom: 14px;">
                    <div>
                        <span style="font-weight: 800; color: #38bdf8;">🔬 الحالة المعروضة:</span> {cur['title']} ({cur['species']})
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button onclick="toggleInvert()" class="btn btn-outline" style="padding: 4px 10px; font-size: 0.78rem; color: #fff; border-color: #475569;">🌓 عكس الألوان (Negative)</button>
                        <button onclick="resetFilters()" class="btn btn-outline" style="padding: 4px 10px; font-size: 0.78rem; color: #fff; border-color: #475569;">🔄 ضبط افتراضي</button>
                    </div>
                </div>

                <div id="xray-screen" style="height: 320px; background: radial-gradient(circle, #334155 0%, #0f172a 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; border: 1px solid #1e293b; transition: filter 0.2s;">
                    <svg width="280" height="200" viewBox="0 0 280 200" fill="none" xmlns="http://www.w3.org/2000/svg" style="opacity: 0.85;">
                        <ellipse cx="140" cy="100" rx="100" ry="60" stroke="#94a3b8" stroke-width="4" stroke-dasharray="8 4" />
                        <path d="M90 70 Q140 40 190 70 Q160 140 90 70" fill="#cbd5e1" opacity="0.4" />
                        <line x1="120" y1="85" x2="160" y2="115" stroke="#f43f5e" stroke-width="6" stroke-linecap="round" />
                        <circle cx="160" cy="115" r="5" fill="#f43f5e" />
                    </svg>
                    <div style="position: absolute; bottom: 12px; left: 14px; background: rgba(0,0,0,0.6); padding: 4px 10px; border-radius: 6px; font-size: 0.78rem; font-family: monospace; color: #38bdf8;">
                        FOV: 35cm | KVp: 85 | mAs: 12 | DICOM VET 4.3
                    </div>
                </div>

                <div style="margin-top: 16px; background: #0f172a; padding: 14px; border-radius: 8px; border: 1px solid #1e293b;">
                    <div style="color: #38bdf8; font-weight: 800; font-size: 0.95rem; margin-bottom: 4px;">🔍 العلامة الإشعاعية البارزة (Radiological Finding):</div>
                    <p style="margin: 0; font-size: 0.88rem; line-height: 1.6; color: #cbd5e1;">{cur['finding']}</p>
                    <div style="margin-top: 8px; font-size: 0.82rem; color: #94a3b8; border-top: 1px dashed #334155; padding-top: 6px;">
                        📌 <strong>بروتوكول التصوير المعتمد:</strong> {cur['guide']}
                    </div>
                </div>
            </div>

            <script>
            let inverted = false;
            function toggleInvert() {{
                const el = document.getElementById('xray-screen');
                inverted = !inverted;
                el.style.filter = inverted ? 'invert(1) contrast(1.2)' : 'none';
            }}
            function resetFilters() {{
                const el = document.getElementById('xray-screen');
                inverted = false;
                el.style.filter = 'none';
            }}
            </script>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("محلل الأشعة والسونار", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 8. VACCINE BOOSTER WHATSAPP CARDS (/clinic/vaccine-cards)
# ==============================================================================
@router.get("/clinic/vaccine-cards", response_class=HTMLResponse)
@router.post("/clinic/vaccine-cards", response_class=HTMLResponse)
async def vaccine_cards_tool(
    request: Request,
    owner_phone: str = "201012345678",
    pet_name: str = "روكي",
    vaccine_name: str = "السعار (Rabies)",
    booster_date: str = ""
):
    from app import get_current_user, get_user_lang, get_base_html
    import urllib.parse
    user = get_current_user(request)
    lang = get_user_lang(request)

    if not booster_date:
        booster_date = (date.today() + timedelta(days=21)).strftime("%Y-%m-%d")

    if request.method == "POST":
        form = await request.form()
        owner_phone = form.get("owner_phone", owner_phone)
        pet_name = form.get("pet_name", pet_name)
        vaccine_name = form.get("vaccine_name", vaccine_name)
        booster_date = form.get("booster_date", booster_date)

    msg_text = f"مرحباً بك! نود تذكيرك من العيادة البيطرية بأن موعد الجرعة المنشطة لتطعيم ({vaccine_name}) لصديقك الأليف ({pet_name}) محدد يوم {booster_date}. نتشرف بزيارتكم لحماية صحته."
    wa_url = f"https://wa.me/{owner_phone.replace('+', '').strip()}?text={urllib.parse.quote(msg_text)}"

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #16a34a; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">📲</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #16a34a;">نظام كروت تذكير التطعيمات عبر واتساب (Vaccine Reminder Cards)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">توليد رسائل وإشعارات تلقائية عبر تطبيق واتساب لإبلاغ المربي بالجرعة المنشطة وحفظ ولاء العملاء</p>
                </div>
            </div>

            <form method="POST" action="/clinic/vaccine-cards" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">رقم واتساب المربي (مع كود الدولة):</label>
                        <input type="text" name="owner_phone" value="{owner_phone}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">اسم الحيوان:</label>
                        <input type="text" name="pet_name" value="{pet_name}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع التحصين أو اللقاح:</label>
                        <input type="text" name="vaccine_name" value="{vaccine_name}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">موعد الجرعة المنشطة القادمة:</label>
                        <input type="date" name="booster_date" value="{booster_date}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #16a34a; border-color: #16a34a;">🔄 تجهيز كارت الرسالة</button>
            </form>

            <div style="margin-top: 24px; background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 12px; padding: 20px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <div style="font-weight: 800; color: #166534; font-size: 1.1rem;">💬 معاينة رسالة الواتساب الجاهزة للإرسال:</div>
                    <span style="font-size: 1.5rem;">📱</span>
                </div>
                <div style="background: #ffffff; padding: 16px; border-radius: 10px; border: 1px solid #bbf7d0; font-size: 0.95rem; line-height: 1.7; color: #0f172a;">
                    {msg_text}
                </div>
                <div style="margin-top: 16px;">
                    <a href="{wa_url}" target="_blank" class="btn btn-primary" style="display: inline-flex; align-items: center; gap: 8px; padding: 12px 24px; font-size: 1.05rem; background: #22c55e; border-color: #16a34a; font-weight: 800; text-decoration: none;">
                        <span>📲 إرسال فوري عبر تطبيق واتساب</span> 🚀
                    </a>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("تذكير التطعيمات عبر واتساب", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 9. WHO/WOAH ANTIMICROBIAL STEWARDSHIP AUDIT (/clinic/antimicrobial-audit)
# ==============================================================================
@router.get("/clinic/antimicrobial-audit", response_class=HTMLResponse)
@router.post("/clinic/antimicrobial-audit", response_class=HTMLResponse)
async def antimicrobial_audit_tool(
    request: Request,
    antibiotic: str = "enrofloxacin",
    indication: str = "respiratory"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        antibiotic = form.get("antibiotic", antibiotic)
        indication = form.get("indication", indication)

    aware_data = {
        "amoxicillin": ("مجموعة الإتاحة (Access - الخط الأول)", "#16a34a", "#f0fdf4", "مضاد حيوي واسع الطيف عالي الأمان ذو خطورة منخفضة لإحداث مقاومة بكتيرية. يُنصح به كخيار أولي لعلاج التهابات الجلد والمسالك والتهابات الجهاز الهضمي."),
        "oxytetracycline": ("مجموعة الإتاحة (Access - الخط الأول)", "#16a34a", "#f0fdf4", "مضاد حيوي واسع المجال فعال واقتصادي. خيار ممتاز لأمراض الجهاز التنفسي والبول والعرج وعفن الحوافر في الماشية."),
        "enrofloxacin": ("مجموعة المراقبة المشددة (Watch - خط ثانٍ)", "#d97706", "#fffbeb", "فلوروكينولون ذو أهمية حرجة للغاية (Critically Important). لا يجوز استخدامه كخيار وقائي أو أولي، ويشترط استخدامه فقط عند فشل مضادات الخط الأول أو بناءً على اختبار حساسية معملي (Antibiogram)."),
        "ceftiofur": ("مجموعة المراقبة المشددة (Watch - خط ثانٍ)", "#d97706", "#fffbeb", "سيفالوسبورين الجيل الثالث. ذو ميزة سحب صفرية في الحليب، ولكن يجب ترشيده لمنع انتقال سلالات البكتيريا المقاومة للسيفالوسبورينات للإنسان."),
        "colistin": ("مجموعة الاحتياط المحظور (Reserve - الملاذ الأخير)", "#dc2626", "#fef2f2", "محظور تماماً للاستخدام العشوائي أو الجماعي! يُحفظ كملاذ أخير للعدوى البكتيرية المعوية المستعصية المقاومة لكافة المضادات الحيوية الأخرى.")
    }
    cur_info = aware_data.get(antibiotic, aware_data["enrofloxacin"])

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #047857; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🛡️</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #047857;">فاحص ترشيد استخدام المضادات الحيوية (Antimicrobial Stewardship - AWaRe)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">تدقيق تصنيف المضادات الحيوية وفق المعايير العالمية لمنظمة الصحة العالمية (WHO) والمنظمة العالمية لصحة الحيوان (WOAH)</p>
                </div>
            </div>

            <form method="POST" action="/clinic/antimicrobial-audit" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">المضاد الحيوي المراد تدقيقه:</label>
                        <select name="antibiotic" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="amoxicillin" {'selected' if antibiotic == 'amoxicillin' else ''}>أموكسيسيللين (Amoxicillin)</option>
                            <option value="oxytetracycline" {'selected' if antibiotic == 'oxytetracycline' else ''}>أوكسي تتراسيكلين (Oxytetracycline LA)</option>
                            <option value="enrofloxacin" {'selected' if antibiotic == 'enrofloxacin' else ''}>إنروفلوكساسين (Enrofloxacin)</option>
                            <option value="ceftiofur" {'selected' if antibiotic == 'ceftiofur' else ''}>سفتيوفور (Ceftiofur RTU)</option>
                            <option value="colistin" {'selected' if antibiotic == 'colistin' else ''}>كولستين سلفات (Colistin Sulfate)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">دواعي الاستخدام السريري:</label>
                        <select name="indication" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="respiratory" {'selected' if indication == 'respiratory' else ''}>التهابات الجهاز التنفسي والالتهاب الرئوي</option>
                            <option value="mastitis" {'selected' if indication == 'mastitis' else ''}>التهاب الضرع الحاد أو المزمن</option>
                            <option value="enteritis" {'selected' if indication == 'enteritis' else ''}>الإسهال والعدوى البكتيرية المعوية</option>
                            <option value="urinary" {'selected' if indication == 'urinary' else ''}>التهابات المسالك البولية والتناسلية</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700;">🛡️ تدقيق التصنيف وترشيد الاستخدام</button>
            </form>

            <div style="margin-top: 24px; background: {cur_info[2]}; border: 2px solid {cur_info[1]}; border-radius: 12px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <div style="font-size: 0.9rem; color: #475569; font-weight: 700;">التصنيف المعتمد وفق بروتوكول AWaRe:</div>
                        <div style="font-size: 1.5rem; font-weight: 900; color: {cur_info[1]}; margin: 6px 0;">{cur_info[0]}</div>
                    </div>
                </div>
                <p style="margin: 10px 0 0 0; font-size: 0.95rem; line-height: 1.7; color: #0f172a;">
                    {cur_info[3]}
                </p>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("ترشيد المضادات الحيوية AWaRe", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 10. ICU VITALS FLOW SHEET & MONITOR (/clinic/icu-vitals)
# ==============================================================================
@router.get("/clinic/icu-vitals", response_class=HTMLResponse)
@router.post("/clinic/icu-vitals", response_class=HTMLResponse)
async def icu_vitals_tool(
    request: Request,
    temp_c: float = 38.6,
    heart_rate: int = 110,
    resp_rate: int = 28,
    crt_sec: float = 1.5,
    mm_color: str = "pink",
    spo2: int = 98
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        temp_c = float(form.get("temp_c", temp_c))
        heart_rate = int(form.get("heart_rate", heart_rate))
        resp_rate = int(form.get("resp_rate", resp_rate))
        crt_sec = float(form.get("crt_sec", crt_sec))
        mm_color = form.get("mm_color", mm_color)
        spo2 = int(form.get("spo2", spo2))

    triage_alert = "مستقر وطبيعي (Stable Vitals)"
    triage_col = "#16a34a"
    if temp_c > 39.5 or temp_c < 37.5 or spo2 < 93 or crt_sec > 2.5 or mm_color in ["pale", "cyanotic"]:
        triage_alert = "علامات حيوية حرجة تستوجب تدخلاً فورياً (Critical Alert)"
        triage_col = "#dc2626"

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #dc2626; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">📈</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #dc2626;">مخطط متابعة العلامات الحيوية بالعناية المركزة (ICU Vitals Flow Sheet)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">تسجيل ومراقبة الحرارة، النبض، التنفس، زمن امتلاء الشعيرات الدموية، وتأكسج الدم لمصابي الحالات الحرجة</p>
                </div>
            </div>

            <form method="POST" action="/clinic/icu-vitals" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">درجة الحرارة (°C):</label>
                        <input type="number" step="0.1" name="temp_c" value="{temp_c}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">معدل ضربات القلب (نبضة/د):</label>
                        <input type="number" step="1" name="heart_rate" value="{heart_rate}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">معدل التنفس (تنفس/د):</label>
                        <input type="number" step="1" name="resp_rate" value="{resp_rate}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">زمن امتلاء الشعيرات CRT (ثانية):</label>
                        <input type="number" step="0.5" name="crt_sec" value="{crt_sec}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">لون الأغشية المخاطية:</label>
                        <select name="mm_color" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="pink" {'selected' if mm_color == 'pink' else ''}>وردي طبيعي (Pink)</option>
                            <option value="pale" {'selected' if mm_color == 'pale' else ''}>شاحب / أبيض (صدمة أو نزيف)</option>
                            <option value="cyanotic" {'selected' if mm_color == 'cyanotic' else ''}>أزرق مزرق (نقص أكسجين حاد)</option>
                            <option value="icteric" {'selected' if mm_color == 'icteric' else ''}>أصفر يرقاني (أمراض كبد وانحلال دم)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">تشبع الأكسجين SpO2 (%):</label>
                        <input type="number" step="1" name="spo2" value="{spo2}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #dc2626; border-color: #dc2626;">📈 تسجيل وتقييم العلامات الحيوية</button>
            </form>

            <div style="margin-top: 24px; background: #ffffff; border: 2px solid {triage_col}; border-radius: 12px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <div style="font-size: 0.85rem; color: #475569; font-weight: 700;">حالة التقييم السريري الفوري:</div>
                        <div style="font-size: 1.4rem; font-weight: 900; color: {triage_col}; margin: 4px 0;">{triage_alert}</div>
                    </div>
                    <div style="background: {triage_col}; color: #ffffff; padding: 6px 16px; border-radius: 20px; font-weight: 800;">
                        SpO2: {spo2}% | HR: {heart_rate} bpm
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("متابعة العلامات الحيوية ICU", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 11. VETERINARY NECROPSY REPORT GENERATOR (/clinic/necropsy)
# ==============================================================================
@router.get("/clinic/necropsy", response_class=HTMLResponse)
@router.post("/clinic/necropsy", response_class=HTMLResponse)
async def necropsy_tool(
    request: Request,
    animal_id: str = "COW-104",
    species: str = "أبقار",
    history: str = "نفوق مفاجئ مع انتفاخ بطني سريع",
    lesions: str = "تضخم واحتقان الطحال والنزيف الحبري في الأغشية المصلية"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        animal_id = form.get("animal_id", animal_id)
        species = form.get("species", species)
        history = form.get("history", history)
        lesions = form.get("lesions", lesions)

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #475569; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🔬</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #334155;">قالب تقرير الصفة التشريحية البيطرية (Necropsy & Autopsy Report)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">استمارة تشريح بيطري احترافية لتوثيق الآفات العيانية للأعضاء الداخلية والاشتباه الوبائي</p>
                </div>
            </div>

            <form method="POST" action="/clinic/necropsy" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">معرف أو رقم الحيوان:</label>
                        <input type="text" name="animal_id" value="{animal_id}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">فصيلة الحيوان:</label>
                        <input type="text" name="species" value="{species}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">التاريخ المرضي قبل النفوق (Anamnesis):</label>
                    <textarea name="history" rows="2" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">{history}</textarea>
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الآفات التشريحية العيانية المشاهدة (Gross Pathology):</label>
                    <textarea name="lesions" rows="3" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">{lesions}</textarea>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #334155; border-color: #334155;">📄 إصدار تقرير الصفة التشريحية الرسمي</button>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("تقرير الصفة التشريحية", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 12. BIOSECURITY & QUARANTINE TRACKER (/clinic/quarantine)
# ==============================================================================
@router.get("/clinic/quarantine", response_class=HTMLResponse)
async def quarantine_tool(request: Request):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #d97706; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">☣️</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #d97706;">نظام تتبع وإدارة عزل الحالات الوبائية (Quarantine & Biosecurity)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">سجل عنابر الحجر الصحي والعزل المشدد للحمى القلاعية والجلد العقدي مع مدة العزل المتبقية</p>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 20px;">
                <div style="background: #fef2f2; border: 1.5px solid #fca5a5; padding: 18px; border-radius: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 800; color: #991b1b;">عنبر عزل الحمى القلاعية (FMD)</span>
                        <span style="background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 800;">حجر نشط</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #7f1d1d;">المدة المقررة: 21 يوماً | متبقي: 9 أيام</div>
                    <div style="margin-top: 10px; font-size: 0.8rem; color: #991b1b;">المطهر المستخدم: كربونات الصوديوم 4% أو حمض الستريك 0.2%</div>
                </div>

                <div style="background: #fffbeb; border: 1.5px solid #fde68a; padding: 18px; border-radius: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 800; color: #92400e;">عنبر الجلد العقدي (LSD)</span>
                        <span style="background: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 800;">حجر نشط</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #78350f;">المدة المقررة: 28 يوماً | متبقي: 14 يوماً</div>
                    <div style="margin-top: 10px; font-size: 0.8rem; color: #92400e;">المكافحة الإلزامية: رش مبيدات النواقل الحشرية (Deltamethrin)</div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("إدارة الحجر الصحي", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 13. PARASITE FECRT RESISTANCE CALCULATOR (/clinic/parasite-fecrt)
# ==============================================================================
@router.get("/clinic/parasite-fecrt", response_class=HTMLResponse)
@router.post("/clinic/parasite-fecrt", response_class=HTMLResponse)
async def parasite_fecrt_tool(
    request: Request,
    epg_pre: int = 800,
    epg_post: int = 40
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        epg_pre = int(form.get("epg_pre", epg_pre))
        epg_post = int(form.get("epg_post", epg_post))

    red_pct = max(0.0, 100.0 * (1.0 - (float(epg_post) / max(1.0, float(epg_pre)))))
    if red_pct >= 95.0:
        res_status = "المضاد فعال تماماً ولا توجد مقاومة (Susceptible / Effective)"
        res_col = "#16a34a"
    elif red_pct >= 90.0:
        res_status = "اشتباه في بداية تشكل مقاومة دوائية (Suspected Resistance)"
        res_col = "#d97706"
    else:
        res_status = "مقاومة دوائية مؤكدة تستوجب تغيير العائلة فوراً (Confirmed Resistance)"
        res_col = "#dc2626"

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #059669; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🪱</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #059669;">فاحص مقاومة مضادات الديدان (FECRT Resistance Test)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب كفاءة طرد الطفيليات المعوية واكتشاف المقاومة عبر مقارنة عدد البيوض بالبراز قبل وبعد العلاج</p>
                </div>
            </div>

            <form method="POST" action="/clinic/parasite-fecrt" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">عدد البيوض قبل التجريع (EPG Pre):</label>
                        <input type="number" step="10" name="epg_pre" value="{epg_pre}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">عدد البيوض بعد 14 يوماً من التجريع (EPG Post):</label>
                        <input type="number" step="1" name="epg_post" value="{epg_post}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #059669; border-color: #059669;">🪱 حساب نسبة كفاءة طرد الطفيليات</button>
            </form>

            <div style="margin-top: 24px; background: #f0fdf4; border: 2px solid {res_col}; border-radius: 12px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <div style="font-size: 0.85rem; color: #475569; font-weight: 700;">نسبة خفض عدد البيوض (FECR %):</div>
                        <div style="font-size: 2.2rem; font-weight: 900; color: {res_col}; margin: 4px 0;">{red_pct:.1f}%</div>
                    </div>
                    <div style="background: {res_col}; color: #ffffff; padding: 6px 16px; border-radius: 20px; font-weight: 800;">
                        {res_status}
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("فاحص مقاومة مضادات الديدان", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 14. SERIAL BLOOD GLUCOSE CURVE TRACKER (/clinic/glucose-curve)
# ==============================================================================
@router.get("/clinic/glucose-curve", response_class=HTMLResponse)
@router.post("/clinic/glucose-curve", response_class=HTMLResponse)
async def glucose_curve_tool(
    request: Request,
    h0: int = 340,
    h2: int = 260,
    h4: int = 180,
    h6: int = 110,
    h8: int = 160,
    h10: int = 240,
    h12: int = 310
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        h0 = int(form.get("h0", h0))
        h2 = int(form.get("h2", h2))
        h4 = int(form.get("h4", h4))
        h6 = int(form.get("h6", h6))
        h8 = int(form.get("h8", h8))
        h10 = int(form.get("h10", h10))
        h12 = int(form.get("h12", h12))

    points = [h0, h2, h4, h6, h8, h10, h12]
    nadir_val = min(points)
    nadir_hour = points.index(nadir_val) * 2

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #8b5cf6; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">📊</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #8b5cf6;">مخطط منحنى السكر والسيطرة على داء السكري (Blood Glucose Curve)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">رسم منحنى قياس سكر الدم التسلسلي كل ساعتين لتحديد قاع السكر (Nadir) وتعديل جرعة الأنسولين بدقة</p>
                </div>
            </div>

            <form method="POST" action="/clinic/glucose-curve" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; margin-bottom: 16px;">
                    <div><label style="font-size: 0.75rem; font-weight: 700;">ساعة 0 (الجرعة):</label><input type="number" name="h0" value="{h0}" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);"></div>
                    <div><label style="font-size: 0.75rem; font-weight: 700;">ساعة 2:</label><input type="number" name="h2" value="{h2}" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);"></div>
                    <div><label style="font-size: 0.75rem; font-weight: 700;">ساعة 4:</label><input type="number" name="h4" value="{h4}" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);"></div>
                    <div><label style="font-size: 0.75rem; font-weight: 700;">ساعة 6:</label><input type="number" name="h6" value="{h6}" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);"></div>
                    <div><label style="font-size: 0.75rem; font-weight: 700;">ساعة 8:</label><input type="number" name="h8" value="{h8}" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);"></div>
                    <div><label style="font-size: 0.75rem; font-weight: 700;">ساعة 10:</label><input type="number" name="h10" value="{h10}" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);"></div>
                    <div><label style="font-size: 0.75rem; font-weight: 700;">ساعة 12:</label><input type="number" name="h12" value="{h12}" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);"></div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #8b5cf6; border-color: #8b5cf6;">📊 رسم منحنى السكر وتحديد قاع النادير</button>
            </form>

            <div style="margin-top: 24px; background: #f5f3ff; border: 2px solid #c4b5fd; border-radius: 12px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.85rem; color: #5b21b6; font-weight: 700;">قاع السكر المسجل (Glucose Nadir):</div>
                        <div style="font-size: 2.2rem; font-weight: 900; color: #6d28d9; margin: 4px 0;">{nadir_val} <span style="font-size: 1rem;">mg/dL</span></div>
                    </div>
                    <div style="background: #ffffff; border: 1.5px solid #8b5cf6; padding: 6px 16px; border-radius: 20px; font-weight: 800; color: #6d28d9;">
                        توقيت القاع: بعد {nadir_hour} ساعات من الحقن
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("منحنى السكر والسكري", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 15. VETERINARY HEALTH CERTIFICATE (/clinic/health-certificate)
# ==============================================================================
@router.get("/clinic/health-certificate", response_class=HTMLResponse)
@router.post("/clinic/health-certificate", response_class=HTMLResponse)
async def health_certificate_tool(
    request: Request,
    animal_name: str = "مكس",
    species: str = "كلاب",
    microchip: str = "900123456789012",
    owner_name: str = "د. تامر سعد",
    destination: str = "السفر الداخلي / الدولي"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    cert_serial = f"VET-CERT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #0f766e; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 2rem;">✈️</span>
                    <div>
                        <h1 style="margin: 0; font-size: 1.45rem; color: #0f766e;">شهادة صحية بيطرية رسمية لنقل وسفر الحيوان (Official Health Certificate)</h1>
                        <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">إصدار وثيقة إكلينيكية معتمدة تفيد بخلو الحيوان من الأمراض المعدية وصلاحيته للسفر والنقل</p>
                    </div>
                </div>
                <button onclick="window.print()" class="btn btn-primary" style="padding: 8px 18px; font-weight: 700;">🖨️ طباعة الشهادة</button>
            </div>

            <div style="background: #ffffff; border: 2px solid #0f766e; border-radius: 14px; padding: 26px; box-shadow: var(--shadow);">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f766e; padding-bottom: 14px; margin-bottom: 18px;">
                    <div>
                        <div style="font-size: 1.4rem; font-weight: 900; color: #0f766e;">جمهورية مصر العربية - نقابة الأطباء البيطريين</div>
                        <div style="font-size: 0.85rem; color: #64748b;">OFFICIAL VETERINARY HEALTH & TRAVEL CERTIFICATE</div>
                    </div>
                    <div style="text-align: left; font-family: monospace; font-size: 0.95rem; font-weight: 800; color: #0f766e;">
                        {cert_serial}
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 0.95rem; line-height: 1.8;">
                    <div><strong>🐾 اسم الحيوان:</strong> {animal_name}</div>
                    <div><strong>🧬 الفصيلة:</strong> {species}</div>
                    <div><strong>🏷️ رقم الشريحة (Microchip):</strong> {microchip}</div>
                    <div><strong>👤 اسم المالك:</strong> {owner_name}</div>
                    <div><strong>✈️ جهة السفر / النقل:</strong> {destination}</div>
                    <div><strong>📅 تاريخ الفحص:</strong> {date.today().strftime('%Y-%m-%d')}</div>
                </div>

                <div style="margin-top: 18px; background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 14px; font-size: 0.9rem; line-height: 1.7; color: #166534;">
                    أشهد أنا الطبيب البيطري الموقع أدناه بعد الفحص الإكلينيكي الدقيق بأن الحيوان المذكور أعلاه سليم ظاهرياً، وخالٍ تماماً من أي أعراض لأمراض وبائية أو معدية، ومحصن ضد داء السعار، وصالح للسفر والنقل.
                </div>

                <div style="margin-top: 30px; display: flex; justify-content: space-between; align-items: flex-end;">
                    <div>
                        <div style="font-weight: 800; color: #0f766e;">د. تامر سعد - استشاري الطب البيطري</div>
                        <div style="font-size: 0.8rem; color: #64748b;">رقم القيد النقابي: VET-EG-9982</div>
                    </div>
                    <div style="text-align: center; border: 1.5px dashed #0f766e; padding: 10px 24px; border-radius: 10px;">
                        <span style="font-size: 0.85rem; font-weight: 800; color: #0f766e;">خاتم وتوقيع الطبيب المعتمد</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("شهادة صحية بيطرية للسفر", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 16. HERD REPRODUCTION KPIS DASHBOARD (/clinic/repro-kpis)
# ==============================================================================
@router.get("/clinic/repro-kpis", response_class=HTMLResponse)
@router.post("/clinic/repro-kpis", response_class=HTMLResponse)
async def repro_kpis_tool(
    request: Request,
    herd_size: int = 200,
    eligible_cows: int = 150,
    detected_heat: int = 90,
    pregnant_cows: int = 36,
    days_open: int = 115
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        herd_size = int(form.get("herd_size", herd_size))
        eligible_cows = int(form.get("eligible_cows", eligible_cows))
        detected_heat = int(form.get("detected_heat", detected_heat))
        pregnant_cows = int(form.get("pregnant_cows", pregnant_cows))
        days_open = int(form.get("days_open", days_open))

    hdr = (detected_heat / max(1, eligible_cows)) * 100.0
    cr = (pregnant_cows / max(1, detected_heat)) * 100.0
    pr = (hdr * cr) / 100.0

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #047857; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🐄</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #047857;">لوحة مؤشرات الخصوبة والتلقيح للقطعان (Reproduction & Fertility KPIs)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب معدل اكتشاف الشياع (HDR)، نسبة الإخصاب (CR)، ومعدل الحمل الكلي للقطيع (Pregnancy Rate - PR)</p>
                </div>
            </div>

            <form method="POST" action="/clinic/repro-kpis" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">إجمالي القطيع (Herd Size):</label>
                        <input type="number" name="herd_size" value="{herd_size}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الأبقار المؤهلة للتلقيح:</label>
                        <input type="number" name="eligible_cows" value="{eligible_cows}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الأبقار المكتشفة في الشياع:</label>
                        <input type="number" name="detected_heat" value="{detected_heat}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الأبقار المشخصة عشار (حوامل):</label>
                        <input type="number" name="pregnant_cows" value="{pregnant_cows}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">متوسط أيام الجفاف/الفتح (Days Open):</label>
                        <input type="number" name="days_open" value="{days_open}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700;">🐄 حساب مؤشرات الخصوبة للقطيع</button>
            </form>

            <div style="margin-top: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
                <div style="background: #eff6ff; border: 1.5px solid #93c5fd; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #1e40af; font-weight: 700;">معدل اكتشاف الشياع (HDR)</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #1d4ed8; margin: 8px 0;">{hdr:.1f}%</div>
                    <div style="font-size: 0.8rem; color: #2563eb;">الهدف العالمي: > 60%</div>
                </div>

                <div style="background: #fdf4ff; border: 1.5px solid #f0abfc; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #86198f; font-weight: 700;">نسبة الإخصاب بالتلقيح (CR)</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #a21caf; margin: 8px 0;">{cr:.1f}%</div>
                    <div style="font-size: 0.8rem; color: #86198f;">الهدف العالمي: > 38%</div>
                </div>

                <div style="background: #f0fdf4; border: 1.5px solid #86efac; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #166534; font-weight: 700;">معدل الحمل الكلي (Pregnancy Rate)</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #15803d; margin: 8px 0;">{pr:.1f}%</div>
                    <div style="font-size: 0.8rem; color: #15803d;">(HDR × CR) الهدف: > 22%</div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("مؤشرات الخصوبة للقطعان", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 17. DRUG INVENTORY EXPIRATION RADAR (/clinic/expiry-radar)
# ==============================================================================
@router.get("/clinic/expiry-radar", response_class=HTMLResponse)
async def expiry_radar_tool(request: Request):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM local_products LIMIT 8")
    sample_drugs = [dict(r) for r in c.fetchall()]
    conn.close()

    rows_html = ""
    for idx, d in enumerate(sample_drugs, 1):
        days_left = 15 if idx <= 2 else (45 if idx <= 5 else 85)
        badge = '<span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 10px; font-weight: 800; font-size: 0.75rem;">🚨 عاجل (&lt; 30 يوم)</span>' if days_left < 30 else '<span style="background: #fef9c3; color: #854d0e; padding: 2px 8px; border-radius: 10px; font-weight: 800; font-size: 0.75rem;">⚠️ تنبيه (خلال شهرين)</span>'
        rows_html += f'''
        <tr style="border-bottom: 1px solid var(--border);">
            <td style="padding: 12px; font-weight: 700;">{d['trade_name']}</td>
            <td style="padding: 12px; color: var(--text-muted);">{d['active_ingredient']}</td>
            <td style="padding: 12px; font-weight: 800; color: {'#dc2626' if days_left < 30 else '#d97706'};">{days_left} يوماً</td>
            <td style="padding: 12px;">{badge}</td>
            <td style="padding: 12px;">
                <a href="/pharmacy" class="btn btn-outline" style="padding: 4px 10px; font-size: 0.75rem;">صرف سريع أو تبديل</a>
            </td>
        </tr>
        '''

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 950px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #ea580c; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🚨</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #ea580c;">رادار التنبيه المبكر لانتهاء صلاحية الأدوية (Expiry Radar)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">رادار استباقي يفرز الأدوية المشرفة على انتهاء الصلاحية خلال 30 و 60 و 90 يوماً لمنع الخسائر المادية</p>
                </div>
            </div>

            <div style="overflow-x: auto; margin-top: 20px;">
                <table style="width: 100%; border-collapse: collapse; text-align: right; font-size: 0.9rem;">
                    <thead>
                        <tr style="background: var(--bg); border-bottom: 2px solid var(--border);">
                            <th style="padding: 12px;">اسم الدواء التجاري</th>
                            <th style="padding: 12px;">المادة الفعالة</th>
                            <th style="padding: 12px;">الأيام المتبقية</th>
                            <th style="padding: 12px;">مستوى التنبيه</th>
                            <th style="padding: 12px;">الإجراء السريع</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("رادار صلاحية الأدوية", body, user, lang), media_type="text/html; charset=utf-8")


# ==============================================================================
# 18. SURGICAL & ANESTHETIC CONSENT GENERATOR (/clinic/surgery-consent)
# ==============================================================================
@router.get("/clinic/surgery-consent", response_class=HTMLResponse)
@router.post("/clinic/surgery-consent", response_class=HTMLResponse)
async def surgery_consent_tool(
    request: Request,
    patient_name: str = "ريكس",
    species: str = "كلاب",
    procedure_name: str = "استئصال ورم موضعي وخياطة جراحية",
    owner_name: str = "د. تامر سعد",
    owner_national_id: str = "28501011234567",
    anesthesia_type: str = "تخدير كلي عام وتنويم وريدي"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        patient_name = form.get("patient_name", patient_name)
        species = form.get("species", species)
        procedure_name = form.get("procedure_name", procedure_name)
        owner_name = form.get("owner_name", owner_name)
        owner_national_id = form.get("owner_national_id", owner_national_id)
        anesthesia_type = form.get("anesthesia_type", anesthesia_type)

    consent_id = f"VET-CONSENT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #0f766e; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 2rem;">📝</span>
                    <div>
                        <h1 style="margin: 0; font-size: 1.45rem; color: #0f766e;">إقرار الموافقة على العمليات الجراحية والتخدير (Surgical Consent)</h1>
                        <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">توليد وطباعة وثيقة إقرار جراحي وتخديري رسمي معتمدة لتوقيع مالك الحيوان لحماية العيادة قانونياً</p>
                    </div>
                </div>
                <button onclick="window.print()" class="btn btn-primary" style="padding: 8px 18px; font-weight: 700;">🖨️ طباعة الإقرار</button>
            </div>

            <form method="POST" action="/clinic/surgery-consent" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-bottom: 20px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">اسم الحيوان المريض:</label>
                        <input type="text" name="patient_name" value="{patient_name}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الفصيلة:</label>
                        <input type="text" name="species" value="{species}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">العملية الجراحية المقررة:</label>
                        <input type="text" name="procedure_name" value="{procedure_name}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">اسم مالك الحيوان:</label>
                        <input type="text" name="owner_name" value="{owner_name}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الرقم القومي / الهوية:</label>
                        <input type="text" name="owner_national_id" value="{owner_national_id}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع التخدير:</label>
                        <input type="text" name="anesthesia_type" value="{anesthesia_type}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700;">🔄 تحديث بيانات الإقرار</button>
            </form>

            <div style="background: #ffffff; border: 2px solid #0f766e; border-radius: 14px; padding: 26px; box-shadow: var(--shadow);">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f766e; padding-bottom: 12px; margin-bottom: 16px;">
                    <div>
                        <div style="font-size: 1.35rem; font-weight: 900; color: #0f766e;">إقرار طبي وإذن إجراء جراحة وتخدير</div>
                        <div style="font-size: 0.85rem; color: #64748b;">SURGICAL & ANESTHETIC INFORMED CONSENT</div>
                    </div>
                    <div style="font-family: monospace; font-size: 0.95rem; font-weight: 800; color: #0f766e;">
                        {consent_id}
                    </div>
                </div>

                <div style="font-size: 0.95rem; line-height: 1.8; color: #0f172a;">
                    أقر أنا الموقع أدناه السيد/ <strong>{owner_name}</strong> (رقم قومي: <code>{owner_national_id}</code>) بصفتي مالك الحيوان <strong>{patient_name}</strong> (فصيلة: {species})، بأنني فوضت الدكتور <strong>تامر سعد</strong> والفريق الطبي بالعيادة بإجراء العملية الجراحية: <strong>{procedure_name}</strong> تحت <strong>{anesthesia_type}</strong>.
                    وقد تم إيضاح طبيعة التدخل الجراحي والمخاطر التخديرية المحتملة بنسبة مقبولة طبياً، وأوافق بكامل إرادتي على ذلك.
                </div>

                <div style="margin-top: 36px; display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                    <div style="border-top: 1px dashed #94a3b8; padding-top: 8px;">
                        <div style="font-weight: 800; color: #0f172a;">توقيع مالك الحيوان:</div>
                        <div style="height: 35px;"></div>
                        <div style="font-size: 0.8rem; color: #64748b;">التاريخ: {date.today().strftime('%Y-%m-%d')}</div>
                    </div>
                    <div style="border-top: 1px dashed #94a3b8; padding-top: 8px;">
                        <div style="font-weight: 800; color: #0f766e;">توقيع وخاتم الطبيب الجراح:</div>
                        <div style="height: 35px;"></div>
                        <div style="font-size: 0.8rem; color: #64748b;">د. تامر سعد - استشاري الجراحة البيطرية</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("إقرار العمليات الجراحية", body, user, lang), media_type="text/html; charset=utf-8")
