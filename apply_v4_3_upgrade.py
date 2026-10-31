# -*- coding: utf-8 -*-
"""
Patch app.py for VetMind AI Enterprise v4.3 Upgrade:
1. High-Contrast, Eye-Friendly Color Palette
2. Razor-sharp Snake Favicon & Touch Icons
3. Live Islamic Prayer Widget in Topbar
4. Drug function in parentheses in AI Chat & Case Reports
5. Dedicated Exact Dosage Calculator next to each suggested drug
6. Clinic Custom Logo Upload & Printing Support
7. Mounting Clinic & Interactive Tools Routers (All 30 Features)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

app_path = r'C:\Users\tamersaad\Desktop\vetmind-ai\app.py'

with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add router mounts and helper imports at top of app.py
imports_marker = 'from references_db import get_all_references, get_arab_references, get_global_references, get_reference_by_id'
new_imports = '''from references_db import get_all_references, get_arab_references, get_global_references, get_reference_by_id
from dosage_engine import calculate_precise_dosage, format_drug_display, get_drug_concise_function
from prayer_engine import calculate_prayer_times
import clinic_routes
import interactive_tools'''

if imports_marker in content and 'import clinic_routes' not in content:
    content = content.replace(imports_marker, new_imports)
    print("1. Added router imports to top of app.py")

# Router inclusion
router_mount_marker = 'app = FastAPI(title="VetMind AI Enterprise v4.2 - Global Clinical Veterinary Platform")'
new_router_mount = '''app = FastAPI(title="VetMind AI Enterprise v4.3 - Global Clinical Veterinary Platform")
app.include_router(clinic_routes.router)
app.include_router(interactive_tools.router)'''

if router_mount_marker in content:
    content = content.replace(router_mount_marker, new_router_mount)
    print("2. Mounted clinic_routes and interactive_tools routers")

# 2. Update CSS & Head in get_base_html
old_head_tags = '''    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | {t('app_name')} {t('version')}</title>
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#0f766e">
    <link rel="icon" type="image/png" href="/static/icon-192.png">
    <style>
        :root {
            --primary: #0f766e;
            --primary-dark: #115e59;
            --primary-light: #ccfbf1;
            --accent: #ea580c;
            --gold: #d97706;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --danger: #dc2626;
            --danger-bg: #fef2f2;
            --success: #16a34a;
            --success-bg: #f0fdf4;
            --warning: #d97706;
            --warning-bg: #fffbeb;
        }
        body.dark-theme {
            --bg: #090d16;
            --card-bg: #131b2e;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #1e293b;
            --danger-bg: #450a0a;
            --success-bg: #052e16;
            --warning-bg: #451a03;
        }'''

new_head_tags = '''    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | {t('app_name')} {t('version')}</title>
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#047857">
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <link rel="alternate icon" type="image/png" href="/static/icon-192.png">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <style>
        :root {
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
        }
        body.dark-theme {
            --bg: #030712;
            --card-bg: #111827;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --border: #1f2937;
            --danger-bg: #450a0a;
            --success-bg: #052e16;
            --warning-bg: #451a03;
            --shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
        }'''

if old_head_tags in content:
    content = content.replace(old_head_tags, new_head_tags)
    print("3. Updated Head with SVG snake icons and high-contrast eye-friendly colors")
else:
    print("3. Warning: old_head_tags not matched exactly, checking lines...")

# 3. Update Header & Nav in get_base_html to include Prayer widget and Tools link
old_nav_items = '''            <a href="/clinic" class="nav-item">🏥 {t('nav_clinic')}</a>
            <a href="/rx-prescription" class="nav-item">📋 {t('nav_rx')}</a>
            <a href="/interactions" class="nav-item">⚠️ {t('nav_interactions')}</a>
            <a href="/pharmacy" class="nav-item">💊 {t('nav_pharmacy')}</a>
            <a href="/vision-detect" class="nav-item">👁️ {t('nav_vision_detect')}</a>
            <a href="/references" class="nav-item">📚 {t('nav_references')}</a>
            <a href="/about" class="nav-item">ℹ️ {t('nav_about')}</a>
            <a href="/terms" class="nav-item">📜 {t('nav_terms')}</a>
            <a href="/time-demand" class="nav-item">📊 {t('nav_time_demand')}</a>'''

new_nav_items = '''            <a href="/clinic" class="nav-item">🏥 {t('nav_clinic')}</a>
            <a href="/clinic/cases-gallery" class="nav-item">🖼️ معرض الصور</a>
            <a href="/rx-prescription" class="nav-item">📋 {t('nav_rx')}</a>
            <a href="/interactions" class="nav-item">⚠️ {t('nav_interactions')}</a>
            <a href="/pharmacy" class="nav-item">💊 {t('nav_pharmacy')}</a>
            <a href="/vision-detect" class="nav-item">👁️ {t('nav_vision_detect')}</a>
            <a href="/tools" class="nav-item" style="background: rgba(255,255,255,0.15); font-weight: 700;">🛠️ الأدوات الـ 30</a>
            <a href="/clinic/prayer-times" class="nav-item">🕌 مواقيت الصلاة</a>
            <a href="/references" class="nav-item">📚 {t('nav_references')}</a>
            <a href="/about" class="nav-item">ℹ️ {t('nav_about')}</a>
            <a href="/terms" class="nav-item">📜 {t('nav_terms')}</a>
            <a href="/time-demand" class="nav-item">📊 {t('nav_time_demand')}</a>'''

if old_nav_items in content:
    content = content.replace(old_nav_items, new_nav_items)
    print("4. Updated Header Nav with Cases Gallery, Prayer Times, and 30 Tools links")

# 4. Add Live Prayer Widget to top-toolbar in get_base_html
old_top_toolbar = '''    <div class="top-toolbar">
        <div class="lang-bar">
            <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted);">🌐 {t('nav_language')}:</span>
            {lang_buttons}
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">'''

new_top_toolbar = '''    <div class="top-toolbar">
        <div class="lang-bar" style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted);">🌐 {t('nav_language')}:</span>
                {lang_buttons}
            </div>
            <!-- Live Islamic Prayer Indicator Pill -->
            <a href="/clinic/prayer-times" class="btn btn-outline" style="padding: 2px 10px; font-size: 0.78rem; border-radius: 20px; text-decoration: none; background: #ecfdf5; border-color: #a7f3d0; color: #047857; font-weight: 700;">
                🕌 الصلاة القادمة: {prayer_p_text} ({prayer_c_text})
            </a>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">'''

if old_top_toolbar in content:
    content = content.replace(old_top_toolbar, new_top_toolbar)
    print("5. Added live Islamic prayer indicator pill to top toolbar")

# Calculate prayer in get_base_html
old_get_base_top = '''def get_base_html(title: str, body_content: str, current_user, lang: str):
    t = lambda k, d="": get_text(lang, k, d)
    dir_attr = TRANSLATIONS_DB.get(lang, {}).get("dir", "rtl")'''

new_get_base_top = '''def get_base_html(title: str, body_content: str, current_user, lang: str):
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
        p_res = calculate_prayer_times(user_city)
        prayer_p_text = f"{p_res['next_prayer']['name']} {p_res['next_prayer']['time']}"
        prayer_c_text = p_res['countdown_text']
    except Exception:
        prayer_p_text = "مواقيت الصلاة"
        prayer_c_text = "انقر هنا"'''

if old_get_base_top in content:
    content = content.replace(old_get_base_top, new_get_base_top)
    print("6. Added prayer calculation inside get_base_html")

# 5. Update ask_ai_chat drugs_summary and system prompt to include concise function in parentheses
old_ai_drugs = '''    localized_drugs = get_localized_drugs(user_country, effective_msg + (vision_data['detected_lesion'] if vision_data else ""))
    drugs_summary = "\\n".join([f"• {d['trade_name']} ({d['manufacturer']}): {d['active_ingredient']} - الجرعة: {d['dosage_guide']} (سحب: {d['withdrawal_period']})" for d in localized_drugs])'''

new_ai_drugs = '''    localized_drugs = get_localized_drugs(user_country, effective_msg + (vision_data['detected_lesion'] if vision_data else ""))
    drugs_summary = "\\n".join([
        f"• {format_drug_display(d)} - المادة الفعالة: {d['active_ingredient']} - الجرعة: {d['dosage_guide']} (سحب: {d['withdrawal_period']})"
        for d in localized_drugs
    ])'''

if old_ai_drugs in content:
    content = content.replace(old_ai_drugs, new_ai_drugs)
    print("7. Updated drugs_summary to format concise function in parentheses")

old_ai_directive = '''3. Provide: Differential diagnoses (ranked with %), Recommended clinical workup, Emergency care, and Prescribing guidance with the doctor's locally registered products ({user_country}):
{drugs_summary}
4. Write in authoritative, clear, professional Arabic (العربية) with medical English terms in parentheses.'''

new_ai_directive = '''3. Provide: Differential diagnoses (ranked with %), Recommended clinical workup, Emergency care, and Prescribing guidance with the doctor's locally registered products ({user_country}):
{drugs_summary}
4. MANDATORY DIRECTIVE: For EVERY suggested medication, you MUST state its concise clinical function in parentheses immediately following the trade name, like: [اسم الدواء] (الوظيفة: علاج النزلات التنفسية وخفض الحرارة).
5. Write in authoritative, clear, professional Arabic (العربية) with medical English terms in parentheses.'''

if old_ai_directive in content:
    content = content.replace(old_ai_directive, new_ai_directive)
    print("8. Updated Groq prompt directive for mandatory concise drug function in parentheses")

# 6. Update case view drugs_html to include concise function AND dedicated dosage calculator
old_case_drugs_loop = '''    drugs_html = ""
    for dg in drugs:
        drugs_html += f"""
        <div style="padding: 12px; border-bottom: 1px solid var(--border);">
            <div style="font-weight: 700; color: var(--primary);">{dg.get('trade_name')} <span style="font-size: 0.8rem; color: var(--text-muted);">({dg.get('manufacturer')})</span></div>
            <div style="font-size: 0.85rem; margin-top: 3px;"><strong>المادة الفعالة:</strong> {dg.get('active_ingredient')}</div>
            <div style="font-size: 0.85rem; margin-top: 3px;"><strong>الجرعة وطريقة الإعطاء:</strong> {dg.get('dosage_guide')}</div>
            <div style="font-size: 0.82rem; color: var(--danger); margin-top: 3px;"><strong>فترة السحب (Withdrawal):</strong> {dg.get('withdrawal_period')} | رقم التسجيل: {dg.get('approval_reg_no')}</div>
        </div>
        """'''

new_case_drugs_loop = '''    drugs_html = ""
    for dg in drugs:
        dosage_calc = calculate_precise_dosage(dg, case_row["weight"], case_row["species"])
        fn_text = get_drug_concise_function(dg)
        drugs_html += f"""
        <div style="padding: 16px; border: 1px solid var(--border); border-radius: 12px; margin-bottom: 14px; background: var(--card-bg); box-shadow: var(--shadow);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="font-weight: 800; font-size: 1.15rem; color: var(--primary);">{dg.get('trade_name')}</span>
                    <span style="background: #e0f2fe; color: #0369a1; padding: 3px 10px; border-radius: 6px; font-size: 0.82rem; font-weight: 700; margin-right: 6px;">({fn_text})</span>
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;"><strong>الشركة المصنعة:</strong> {dg.get('manufacturer')} | <strong>المادة الفعالة:</strong> {dg.get('active_ingredient')}</div>
                </div>
                <div style="background: #ecfdf5; border: 1px solid #a7f3d0; padding: 6px 14px; border-radius: 8px; text-align: left;" dir="ltr">
                    <div style="font-size: 0.72rem; color: #047857; font-weight: 700;">PRECISE CALCULATED DOSE:</div>
                    <div style="font-size: 1.25rem; font-weight: 900; color: #047857;">{dosage_calc['exact_dose_formatted']}</div>
                </div>
            </div>

            <!-- Dedicated Dosage Calculator Details Box -->
            <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 12px 16px; margin-top: 12px; font-size: 0.9rem;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
                    <div>💉 <strong>الجرعة الدقيقة لوزن {case_row['weight']} كجم:</strong> <span style="color: #ea580c; font-weight: 900;">{dosage_calc['exact_dose_formatted']}</span></div>
                    <div>⏱️ <strong>التكرار:</strong> {dosage_calc['frequency']}</div>
                    <div>📍 <strong>طريقة الإعطاء:</strong> {dosage_calc['route']}</div>
                    <div>⏳ <strong>المدة:</strong> {dosage_calc['duration']}</div>
                </div>
                {f'<div style="color: #b91c1c; font-weight: 700; margin-top: 8px; font-size: 0.85rem;">{dosage_calc["site_split_warning"]}</div>' if dosage_calc.get("site_split_warning") else ''}
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 12px; font-size: 0.85rem; border-top: 1px solid var(--border); padding-top: 8px;">
                <div style="color: var(--danger); font-weight: 600;">⚠️ <strong>فترة السحب (Withdrawal):</strong> {dg.get('withdrawal_period')} | رقم التسجيل: {dg.get('approval_reg_no')}</div>
                <a href="/rx-prescription?animal_name={case_row['animal_name']}&species={case_row['species']}&weight={case_row['weight']}&selected_drug_id={dg.get('id', 1)}" class="btn btn-primary" style="padding: 5px 14px; font-size: 0.84rem; font-weight: 700;">
                    📋 تحويل لروشتة العيادة وطباعتها
                </a>
            </div>
        </div>
        """'''

if old_case_drugs_loop in content:
    content = content.replace(old_case_drugs_loop, new_case_drugs_loop)
    print("9. Updated case view with drug function in parentheses + dedicated dosage calculator")

# 7. Update Clinic Hub Profile Form to support logo upload & quick actions
old_clinic_profile_form = '''    <div class="card" style="border-top: 4px solid var(--primary); margin-bottom: 24px;">
        <h2 style="margin-top: 0; font-size: 1.25rem; color: var(--primary);">🏢 {t('clinic_profile_tab')}</h2>
        <form action="/clinic/profile" method="POST">
            <div class="grid-2" style="margin-bottom: 14px;">
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">اسم العيادة أو المستشفى</label>
                    <input type="text" name="clinic_name" value="{p_name}" required style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">هاتف العيادة / واتساب الطوارئ</label>
                    <input type="text" name="phone" value="{p_phone}" placeholder="+201..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
            </div>

            <div class="grid-2" style="margin-bottom: 14px;">
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">عنوان وموقع العيادة</label>
                    <input type="text" name="address" value="{p_addr}" placeholder="المدينة، الحي" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 700; margin-bottom: 5px;">سعر الكشف الاستشاري</label>
                    <input type="text" name="consultation_fee" value="{p_fee}" placeholder="مثال: 200 جنيه" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
                </div>
            </div>

            <div style="margin-bottom: 14px;">
                <label style="display: block; font-weight: 700; margin-bottom: 5px;">مواعيد العمل</label>
                <input type="text" name="working_hours" value="{p_hours}" placeholder="مثال: يومياً 10ص - 10م" style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px;">
            </div>

            <button type="submit" class="btn btn-primary">💾 {t('clinic_save')}</button>
        </form>
    </div>'''

new_clinic_profile_form = '''    <!-- Quick Action Hub for 30 Features -->
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
    </div>'''

if old_clinic_profile_form in content:
    content = content.replace(old_clinic_profile_form, new_clinic_profile_form)
    print("10. Updated Clinic Profile Hub with custom logo upload & quick actions")

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nSUCCESS: VetMind AI Enterprise v4.3 upgrade patch applied successfully to app.py!")
