# -*- coding: utf-8 -*-
"""
VetMind AI - Interactive Clinical Tools & Calculators Suite
Contains all interactive calculators and tools with dedicated formulas, rich UI,
and 'Return to Home Page' navigation on every page.
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from datetime import datetime, date, timedelta
import math
import uuid

router = APIRouter()

def get_back_home_bar(extra_link_html: str = "", lang: str = "ar") -> str:
    """Returns a standardized, prominent return to home page navigation bar."""
    from app import get_text
    back_label = get_text(lang, 'back_to_home', 'العودة للصفحة الرئيسية')
    tools_label = get_text(lang, 'tools_index_btn', 'فهرس الأدوات الـ 30')
    return f"""
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
    """

# ==============================================================================
# 1. FLUID THERAPY CALCULATOR (/tools/fluid-therapy)
# ==============================================================================
@router.get("/tools/fluid-therapy", response_class=HTMLResponse)
@router.post("/tools/fluid-therapy", response_class=HTMLResponse)
async def fluid_therapy_tool(
    request: Request,
    species: str = "أبقار",
    weight: float = 400.0,
    dehydration_pct: float = 8.0,
    ongoing_losses: float = 2000.0,
    drip_set: int = 15
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        weight = float(form.get("weight", weight))
        dehydration_pct = float(form.get("dehydration_pct", dehydration_pct))
        ongoing_losses = float(form.get("ongoing_losses", ongoing_losses))
        drip_set = int(form.get("drip_set", drip_set))

    maint_rate = 60.0 if weight < 35 else 50.0
    maintenance_ml = weight * maint_rate
    deficit_ml = weight * (dehydration_pct / 100.0) * 1000.0
    total_24h_ml = maintenance_ml + deficit_ml + ongoing_losses
    hourly_rate_ml = total_24h_ml / 24.0
    drips_per_min = (hourly_rate_ml * drip_set) / 60.0

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid var(--primary); margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">💧</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: var(--primary);">حاسبة المحاليل الوريدية ومعدل التنقيط الدقيق (Fluid Therapy)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب احتياج السوائل الثلاثي (الصيانة اليومية + تعويض الجفاف + الفاقد المستمر) وضبط جهاز المحلول</p>
                </div>
            </div>

            <form method="POST" action="/tools/fluid-therapy" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الحيوان:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="أبقار" {'selected' if species == 'أبقار' else ''}>أبقار (Cattle)</option>
                            <option value="خيول" {'selected' if species == 'خيول' else ''}>خيول (Equine)</option>
                            <option value="أغنام" {'selected' if species == 'أغنام' else ''}>أغنام وماعز (Sheep/Goat)</option>
                            <option value="كلاب" {'selected' if species == 'كلاب' else ''}>كلاب (Canine)</option>
                            <option value="قطط" {'selected' if species == 'قطط' else ''}>قطط (Feline)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">وزن الحيوان (كجم):</label>
                        <input type="number" step="0.5" name="weight" value="{weight}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نسبة الجفاف التقديرية (%):</label>
                        <select name="dehydration_pct" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="4" {'selected' if dehydration_pct == 4 else ''}>4% (جفاف خفيف جداً، غير ملحوظ)</option>
                            <option value="6" {'selected' if dehydration_pct == 6 else ''}>6% (جفاف خفيف، فقد طفيف لمرونة الجلد)</option>
                            <option value="8" {'selected' if dehydration_pct == 8 else ''}>8% (جفاف متوسط، جفاف الأغشية وتأخر ارتداد الجلد)</option>
                            <option value="10" {'selected' if dehydration_pct == 10 else ''}>10% (جفاف شديد، غور العينين وبرودة الأطراف)</option>
                            <option value="12" {'selected' if dehydration_pct == 12 else ''}>12% (صدمة جفاف حرجة تهدد الحياة)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الفاقد المستمر التقديري (إسهال/قيء) بالملل:</label>
                        <input type="number" step="100" name="ongoing_losses" value="{ongoing_losses}" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">معامل جهاز المحلول (Drip Set):</label>
                        <select name="drip_set" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="15" {'selected' if drip_set == 15 else ''}>15 قطرة/مل (جهاز محاليل بشري/كبير Macro-drip)</option>
                            <option value="10" {'selected' if drip_set == 10 else ''}>10 قطرة/مل (جهاز محاليل خيول وماشية سريع)</option>
                            <option value="60" {'selected' if drip_set == 60 else ''}>60 قطرة/مل (جهاز أطفال وحيوانات أليفة Micro-drip)</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700;">🔄 احسب خطة المحاليل الوريدية</button>
            </form>

            <div style="margin-top: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
                <div style="background: #f0fdf4; border: 1.5px solid #86efac; padding: 16px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #166534; font-weight: 700;">إجمالي حجم السوائل خلال 24 ساعة</div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: #047857; margin: 8px 0;">{total_24h_ml:,.0f} <span style="font-size: 1rem;">مل</span></div>
                    <div style="font-size: 0.8rem; color: #15803d;">({total_24h_ml/1000:,.2f} لتر)</div>
                </div>

                <div style="background: #eff6ff; border: 1.5px solid #93c5fd; padding: 16px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #1e40af; font-weight: 700;">معدل التسريب بالساعة (mL/hr)</div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: #1d4ed8; margin: 8px 0;">{hourly_rate_ml:,.1f} <span style="font-size: 1rem;">مل/ساعة</span></div>
                    <div style="font-size: 0.8rem; color: #2563eb;">يعادل {(total_24h_ml/500):,.1f} زجاجة محلول 500 مل</div>
                </div>

                <div style="background: #fefce8; border: 1.5px solid #fde047; padding: 16px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #854d0e; font-weight: 700;">سرعة التنقيط بجهاز المحلول</div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: #b45309; margin: 8px 0;">{drips_per_min:,.0f} <span style="font-size: 1rem;">قطرة/دقيقة</span></div>
                    <div style="font-size: 0.8rem; color: #a16207;">(قطرة كل {60.0/drips_per_min:,.1f} ثانية)</div>
                </div>
            </div>

            <div style="margin-top: 20px; background: #f8fafc; border: 1px solid var(--border); border-radius: 10px; padding: 16px;">
                <h4 style="margin: 0 0 10px 0; color: var(--primary);">📋 تفكيك مكونات الاحتياج الحسابي:</h4>
                <ul style="margin: 0; padding-right: 20px; font-size: 0.9rem; line-height: 1.8; color: var(--text-main);">
                    <li><strong>حجم الصيانة اليومي (Maintenance):</strong> {maintenance_ml:,.0f} مل ({maint_rate} مل/كجم).</li>
                    <li><strong>عجز الجفاف (Dehydration Deficit):</strong> {deficit_ml:,.0f} مل (يُفضل إعطاء نصفه في أول 4-6 ساعات والنصف الآخر على باقي اليوم).</li>
                    <li><strong>الفاقد المستمر (Ongoing Losses):</strong> {ongoing_losses:,.0f} مل (تعويض فقد الإسهال والنزيف).</li>
                    <li><strong>نوع المحلول الموصى به:</strong> محلول رينجر لاكتات (Ringer Lactate) أو سالين متساوي التوتر 0.9%، مع مراعاة بوتاسيوم الدم.</li>
                </ul>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("حاسبة المحاليل الوريدية", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 2. ANESTHESIA & SEDATION PROTOCOL (/tools/anesthesia-protocol)
# ==============================================================================
@router.get("/tools/anesthesia-protocol", response_class=HTMLResponse)
@router.post("/tools/anesthesia-protocol", response_class=HTMLResponse)
async def anesthesia_protocol_tool(
    request: Request,
    species: str = "خيول",
    weight: float = 450.0,
    procedure: str = "standing"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        weight = float(form.get("weight", weight))
        procedure = form.get("procedure", procedure)

    # Protocols
    if species == "خيول":
        pre_med = f"زيلازين 10% (Xylazine): {(weight * 1.1) / 100:.2f} مل وريدياً (IV)"
        induction = f"كيتامين 10% (Ketamine): {(weight * 2.2) / 100:.2f} مل + ديازيبام 0.5%: {(weight * 0.05) / 5:.2f} مل وريدياً دفعة واحدة"
        reversal = f"يوهيمبين (Yohimbine 2 mg/ml): {(weight * 0.12) / 2:.2f} مل وريدياً"
        tube_size = "22 - 26 مم قطر داخلي (ID)"
    elif species == "أبقار":
        pre_med = f"زيلازين 2% (Xylazine): {(weight * 0.05) / 20:.2f} مل عضلياً أو {(weight * 0.02) / 20:.2f} مل وريدياً (الأبقار حساسة جداً للزيلازين 1/10 جرعة الخيل)"
        induction = f"كيتامين 10%: {(weight * 2.0) / 100:.2f} مل وريدياً بعد التسكين التام"
        reversal = f"تولازولين (Tolazoline 100 mg/ml): {(weight * 2.0) / 100:.2f} مل وريدياً ببطء"
        tube_size = "20 - 24 مم قطر داخلي (ID)"
    elif species == "أغنام":
        pre_med = f"ميدازولام 0.5%: {(weight * 0.2) / 5:.2f} مل عضلياً أو ديازيبام"
        induction = f"كيتامين 10%: {(weight * 4.0) / 100:.2f} مل + بروبوفول 1%: {(weight * 2.0) / 10:.2f} مل"
        reversal = f"فلومازينيل (Flumazenil) في حال الحاجة لإلغاء الميدازولام"
        tube_size = "8 - 10 مم قطر داخلي (ID)"
    elif species == "كلاب":
        pre_med = f"ميديتوميدين (Medetomidine 1 mg/ml): {(weight * 0.01) / 1:.2f} مل عضلياً + بوتورفانول 10 مجم/مل: {(weight * 0.2) / 10:.2f} مل"
        induction = f"بروبوفول 1% (Propofol 10 mg/ml): {(weight * 4.0) / 10:.2f} مل وريدياً ببطء حتى الرخاوة"
        reversal = f"أتيباميزول (Atipamezole 5 mg/ml - Antisedan): {(weight * 0.05) / 5:.2f} مل عضلياً"
        tube_size = f"{max(5.0, min(12.0, 5.0 + (weight * 0.15))):.1f} مم قطر داخلي"
    else:  # قطط
        pre_med = f"ميديتوميدين 1 مجم/مل: {(weight * 0.02) / 1:.2f} مل عضل + كيتامين 10%: {(weight * 5.0) / 100:.2f} مل"
        induction = f"بروبوفول 1%: {(weight * 2.5) / 10:.2f} مل وريدياً ببطء"
        reversal = f"أتيباميزول 5 مجم/مل: {(weight * 0.1) / 5:.2f} مل عضلياً"
        tube_size = "3.5 - 4.5 مم قطر داخلي"

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #0284c7; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">💉</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #0284c7;">بروتوكول التخدير والمهدئات المخصص (Anesthesia Protocol)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب الجرعات الدقيقة للتهدئة، التنويم التخديري، أنبوبة القصبة الهوائية، ومضادات التخدير (Reversal)</p>
                </div>
            </div>

            <form method="POST" action="/tools/anesthesia-protocol" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الحيوان:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="خيول" {'selected' if species == 'خيول' else ''}>خيول (Equine)</option>
                            <option value="أبقار" {'selected' if species == 'أبقار' else ''}>أبقار (Bovine)</option>
                            <option value="أغنام" {'selected' if species == 'أغنام' else ''}>أغنام وماعز (Ovine/Caprine)</option>
                            <option value="كلاب" {'selected' if species == 'كلاب' else ''}>كلاب (Canine)</option>
                            <option value="قطط" {'selected' if species == 'قطط' else ''}>قطط (Feline)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الوزن الحي (كجم):</label>
                        <input type="number" step="0.5" name="weight" value="{weight}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الإجراء الجراحي:</label>
                        <select name="procedure" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="minor" {'selected' if procedure == 'minor' else ''}>تسكين بسيط / فحص هادئ (Minor Sedation)</option>
                            <option value="standing" {'selected' if procedure == 'standing' else ''}>جراحة وقوفية وتخدير موضعي (Standing Surgery)</option>
                            <option value="general" {'selected' if procedure == 'general' else ''}>تخدير كلي عام وتنويم تام (General Anesthesia)</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #0284c7; border-color: #0284c7;">⚡ توليد بروتوكول التخدير الدقيق</button>
            </form>

            <div style="margin-top: 24px;">
                <div style="background: #f0f9ff; border: 1.5px solid #7dd3fc; border-radius: 12px; padding: 18px; margin-bottom: 16px;">
                    <h3 style="margin: 0 0 12px 0; color: #0369a1; font-size: 1.15rem;">💉 1. مرحلة ما قبل التخدير والتسكين (Premedication / Sedation)</h3>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #0c4a6e;">{pre_med}</div>
                    <div style="font-size: 0.82rem; color: #0284c7; margin-top: 4px;">* انتظر من 5 إلى 10 دقائق حتى هبوط الرأس وارتخاء الشفة السفلية قبل المتابعة.</div>
                </div>

                <div style="background: #fdf2f8; border: 1.5px solid #f472b6; border-radius: 12px; padding: 18px; margin-bottom: 16px;">
                    <h3 style="margin: 0 0 12px 0; color: #9d174d; font-size: 1.15rem;">🛌 2. مرحلة الحث التخديري والتنويم (Induction)</h3>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #831843;">{induction}</div>
                    <div style="font-size: 0.82rem; color: #db2777; margin-top: 4px;">* حقن وريدي سريع للخيول والأبقار، وبطيء مع التدريج للحيوانات الأليفة مع مراقبة المنعكس القرني.</div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px;">
                    <div style="background: #fefce8; border: 1.5px solid #fde047; border-radius: 12px; padding: 16px;">
                        <h4 style="margin: 0 0 8px 0; color: #854d0e;">🔄 3. مضاد التخدير والإفاقة السريعة (Reversal)</h4>
                        <div style="font-size: 1rem; font-weight: 700; color: #713f12;">{reversal}</div>
                    </div>
                    <div style="background: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 12px; padding: 16px;">
                        <h4 style="margin: 0 0 8px 0; color: #334155;">🫁 4. مقاس أنبوبة القصبة الهوائية (ET Tube)</h4>
                        <div style="font-size: 1.1rem; font-weight: 800; color: #0f172a;">{tube_size}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("بروتوكول التخدير والمهدئات", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 3. TOXICOLOGY & ANTIDOTE CALCULATOR (/tools/toxicology-calc)
# ==============================================================================
@router.get("/tools/toxicology-calc", response_class=HTMLResponse)
@router.post("/tools/toxicology-calc", response_class=HTMLResponse)
async def toxicology_calc_tool(
    request: Request,
    species: str = "كلاب",
    weight: float = 20.0,
    toxin: str = "organophosphate"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        weight = float(form.get("weight", weight))
        toxin = form.get("toxin", toxin)

    if toxin == "organophosphate":
        t_name = "المبيدات الفوسفورية العضوية والكاربامات (Organophosphates)"
        antidote = f"أتروبين سلفات (Atropine 1 mg/ml): {(weight * 0.3):.2f} مل (يُعطى 1/4 الجرعة وريدياً والباقي عضلياً، تكرر كل 15 دقيقة حتى جفاف اللعاب وتوسع الحدقة)"
        adjunct = "براليدوكسيم (2-PAM): 20 مجم/كجم وريدياً ببطء خلال الساعات الأولى لفك ارتباط الإنزيم."
        urgency = "حالة طارئة حرجة جداً (SLUDDE Signs: سيلان لعاب، تضيق حدقة، إسهال، تشنجات)"
    elif toxin == "rodenticide":
        t_name = "سموم الفئران ومضادات التخثر (Warfarin / Brodifacoum)"
        antidote = f"فيتامين ك1 (Phytomenadione / Vitamin K1 10 mg/ml): {(weight * 3.0) / 10:.2f} مل تحت الجلد ثم أقراص فموية مع طعام دهني لمدة 28 يوماً."
        adjunct = "في حال النزيف الحاد الشديد: نقل دم كامل طازج (Fresh Whole Blood) فوراً لتعويض عوامل التخثر."
        urgency = "شديدة الخطورة (نزيف باطني، نزيف رئوي، شحوب شديد بالأغشية)"
    elif toxin == "paracetamol":
        t_name = "تسمم الباراسيتامول / الأسيتامينوفين (شديد السمية للقطط)"
        antidote = f"إن-أسيتيل سيستئين (N-Acetylcysteine 20%): {(weight * 140) / 200:.2f} مل وريدياً جرعة أولى، ثم {(weight * 70) / 200:.2f} مل كل 6 ساعات لمدة 7 جرعات."
        adjunct = "فيتامين C (حمض الأسكوربيك) 30 مجم/كجم وريدياً لتقليل ميتهيموغلوبين الدم."
        urgency = "قاتل وفوري في القطط حتى بنصف قرص (زرقة وأغشية بنية شوكولاتية وتورم بالوجه)"
    elif toxin == "chocolate":
        t_name = "تسمم الشوكولاتة والثيوبرومين (Theobromine)"
        antidote = f"الفحم النشط (Activated Charcoal): {(weight * 2.0):.1f} جرام فموياً مع محلول ملين (Sorbitol) لمنع الامتصاص."
        adjunct = "محاليل وريدية مضاعفة لغسيل الكلى (Diuresis) ومراقبة ضربات القلب وتجنب التشنجات عبر الديازيبام."
        urgency = "متوسطة إلى شديدة (فرط نشاط، تسرع قلبي شديد، عدم انتظام ضربات القلب)"
    else:  # ivermectin
        t_name = "سمية الجرعة الزائدة من الإيفرمكتين (خاصة سلالات الكولي MDR1)"
        antidote = "لا يوجد ترياق كيميائي نوعي مباشر (No specific antidote). العلاج المعتمد: مستحلب الدهون الوريدي (Intralipid 20% Infusion)."
        adjunct = f"مستحلب الدهون (Lipid Rescue 20%): {(weight * 1.5):.1f} مل وريدياً كجرعة حث، ثم {(weight * 0.25):.2f} مل/دقيقة لمدة ساعة."
        urgency = "حرجة عصبياً (ترنح، فقدان البصر، غيبوبة، تباطؤ ضربات القلب)"

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #dc2626; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🧪</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #dc2626;">حاسبة السموم والجرعات القاتلة والترياق (Toxicology & Antidotes)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">تقييم التسممات الحادة وحساب جرعة الترياق المنقذ للحياة (Antidote) وإرشادات الغسيل المعوي</p>
                </div>
            </div>

            <form method="POST" action="/tools/toxicology-calc" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع السم أو المادة المبتلعة:</label>
                        <select name="toxin" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="organophosphate" {'selected' if toxin == 'organophosphate' else ''}>مبيدات فوسفورية / كاربامات (Organophosphates)</option>
                            <option value="rodenticide" {'selected' if toxin == 'rodenticide' else ''}>سموم فئران مانعة للتجلط (Warfarin / Brodifacoum)</option>
                            <option value="paracetamol" {'selected' if toxin == 'paracetamol' else ''}>باراسيتامول / بنادول (Paracetamol Toxicity)</option>
                            <option value="chocolate" {'selected' if toxin == 'chocolate' else ''}>شوكولاتة وثيوبرومين (Chocolate / Theobromine)</option>
                            <option value="ivermectin" {'selected' if toxin == 'ivermectin' else ''}>إيفرمكتين جرعة زائدة (Ivermectin Overdose / MDR1)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">فصيلة الحيوان:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="كلاب" {'selected' if species == 'كلاب' else ''}>كلاب (Canine)</option>
                            <option value="قطط" {'selected' if species == 'قطط' else ''}>قطط (Feline)</option>
                            <option value="أبقار" {'selected' if species == 'أبقار' else ''}>أبقار وماشية (Bovine)</option>
                            <option value="خيول" {'selected' if species == 'خيول' else ''}>خيول (Equine)</option>
                            <option value="أغنام" {'selected' if species == 'أغنام' else ''}>أغنام وماعز (Small Ruminants)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">وزن الحيوان المصاب (كجم):</label>
                        <input type="number" step="0.5" name="weight" value="{weight}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #dc2626; border-color: #dc2626;">🚨 حساب الترياق وبروتوكول الإنقاذ</button>
            </form>

            <div style="margin-top: 24px;">
                <div style="background: #fef2f2; border: 1.5px solid #fca5a5; border-radius: 12px; padding: 18px; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <h3 style="margin: 0; color: #991b1b; font-size: 1.15rem;">🎯 الترياق المنقذ للحياة (Specific Antidote)</h3>
                        <span style="background: #fee2e2; color: #b91c1c; font-weight: 800; font-size: 0.78rem; padding: 3px 8px; border-radius: 12px;">{urgency}</span>
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #7f1d1d; margin: 12px 0;">{antidote}</div>
                    <div style="font-size: 0.9rem; color: #991b1b;"><strong>العلاج الداعم المساعد:</strong> {adjunct}</div>
                </div>

                <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 10px; padding: 16px;">
                    <h4 style="margin: 0 0 10px 0; color: var(--primary);">⚠️ قواعد التطهير السريع ومنع الامتصاص (Decontamination):</h4>
                    <ul style="margin: 0; padding-right: 20px; font-size: 0.88rem; line-height: 1.8; color: var(--text-main);">
                        <li><strong>التقيؤ الحثي (Induction of Emesis):</strong> مسموح فقط خلال أول 1-2 ساعة من الابتلاع، <em>وممنوع تماماً</em> إذا كان الحيوان فاقداً للوعي أو إذا كانت المادة كاوية (حمض أو قلوي أو هيدروكربونات نفطية).</li>
                        <li><strong>غسيل الجلد والشعر:</strong> في حالات التسمم عبر الجلد، يُغسل الحيوان فوراً بماء دافئ وصابون سائل معتدل (Dawn dish soap) مع ارتداء قفازات واقية للطبيب.</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("حاسبة السموم والترياق", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 4. BLOOD TRANSFUSION & CROSSMATCH (/tools/blood-transfusion)
# ==============================================================================
@router.get("/tools/blood-transfusion", response_class=HTMLResponse)
@router.post("/tools/blood-transfusion", response_class=HTMLResponse)
async def blood_transfusion_tool(
    request: Request,
    species: str = "كلاب",
    weight: float = 25.0,
    current_pcv: float = 12.0,
    target_pcv: float = 25.0,
    donor_pcv: float = 45.0
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        weight = float(form.get("weight", weight))
        current_pcv = float(form.get("current_pcv", current_pcv))
        target_pcv = float(form.get("target_pcv", target_pcv))
        donor_pcv = float(form.get("donor_pcv", donor_pcv))

    factor = 90.0 if species in ["كلاب", "خيول"] else (66.0 if species == "قطط" else 60.0)
    pcv_diff = max(0.0, target_pcv - current_pcv)
    vol_ml = weight * factor * (pcv_diff / max(1.0, donor_pcv))
    test_rate = weight * 0.5  # ml/hr for first 30 min
    main_rate = weight * 5.0  # ml/hr

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #b91c1c; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🩸</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #b91c1c;">حاسبة نقل الدم والتوافق الفصائلي (Blood Transfusion Calculator)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب حجم الدم الكامل المطلوب نقله، معدل التسريب الأولي، ودليل التوافق المناعي الفصائلي</p>
                </div>
            </div>

            <form method="POST" action="/tools/blood-transfusion" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الحيوان المتلقي:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="كلاب" {'selected' if species == 'كلاب' else ''}>كلاب (DEA 1.1 Factor 90)</option>
                            <option value="قطط" {'selected' if species == 'قطط' else ''}>قطط (AB System Factor 66)</option>
                            <option value="خيول" {'selected' if species == 'خيول' else ''}>خيول (Factor 90)</option>
                            <option value="أبقار" {'selected' if species == 'أبقار' else ''}>أبقار (Factor 60)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">وزن المتلقي (كجم):</label>
                        <input type="number" step="0.5" name="weight" value="{weight}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الهيماتوكريت الحالي PCV (%):</label>
                        <input type="number" step="1" name="current_pcv" value="{current_pcv}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الهيماتوكريت المستهدف (%):</label>
                        <input type="number" step="1" name="target_pcv" value="{target_pcv}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">هيماتوكريت المتبرع PCV (%):</label>
                        <input type="number" step="1" name="donor_pcv" value="{donor_pcv}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #b91c1c; border-color: #b91c1c;">🩸 حساب حجم الدم ومعدل التسريب</button>
            </form>

            <div style="margin-top: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
                <div style="background: #fef2f2; border: 1.5px solid #f87171; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #991b1b; font-weight: 700;">حجم الدم الكامل المطلوب نقله</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #b91c1c; margin: 8px 0;">{vol_ml:,.0f} <span style="font-size: 1rem;">مل</span></div>
                    <div style="font-size: 0.8rem; color: #7f1d1d;">يعادل {(vol_ml/450):,.1f} كيس دم قياسي (450 مل)</div>
                </div>
                <div style="background: #fff7ed; border: 1.5px solid #fdba74; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #9a3412; font-weight: 700;">سرعة التسريب الاختبارية (أول 30 دقيقة)</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #c2410c; margin: 8px 0;">{test_rate:,.1f} <span style="font-size: 1rem;">مل/ساعة</span></div>
                    <div style="font-size: 0.8rem; color: #7c2d12;">(0.5 مل/كجم/ساعة لمراقبة التحسس والحرارة)</div>
                </div>
                <div style="background: #f0fdf4; border: 1.5px solid #86efac; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #166534; font-weight: 700;">سرعة التسريب المستمرة بعد التأكد</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #15803d; margin: 8px 0;">{main_rate:,.0f} <span style="font-size: 1rem;">مل/ساعة</span></div>
                    <div style="font-size: 0.8rem; color: #14532d;">إتمام الكيس خلال 4 ساعات كحد أقصى</div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("حاسبة نقل الدم والتوافق", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 5. VETERINARY PAIN SCALE (Grimace & Glasgow) (/tools/pain-scale)
# ==============================================================================
@router.get("/tools/pain-scale", response_class=HTMLResponse)
@router.post("/tools/pain-scale", response_class=HTMLResponse)
async def pain_scale_tool(
    request: Request,
    species: str = "كلاب",
    posture: int = 1,
    vocalization: int = 1,
    mobility: int = 1,
    palpation: int = 2,
    grimace: int = 1
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        posture = int(form.get("posture", posture))
        vocalization = int(form.get("vocalization", vocalization))
        mobility = int(form.get("mobility", mobility))
        palpation = int(form.get("palpation", palpation))
        grimace = int(form.get("grimace", grimace))

    total_score = posture + vocalization + mobility + palpation + grimace
    # Max possible score = 15
    if total_score <= 3:
        level = "ألم خفيف أو غير ملحوظ (Mild Pain)"
        color = "#16a34a"
        bg_col = "#f0fdf4"
        action = "مراقبة مستمرة، مسكنات بسيطة غير ستيرويدية (Meloxicam أو Carprofen) عند اللزوم."
    elif total_score <= 7:
        level = "ألم متوسط يستوجب التدخل (Moderate Pain)"
        color = "#d97706"
        bg_col = "#fffbeb"
        action = "بروتوكول تسكين متعدد الوسائط: مضاد التهاب غير ستيرويدي (NSAID) + أفيوني خفيف (Tramadol / Butorphanol)."
    else:
        level = "ألم شديد إلى حرج يتطلب تدخلاً فورياً (Severe / Critical Pain)"
        color = "#dc2626"
        bg_col = "#fef2f2"
        action = "تدخل طارئ: تسريب وريدي مستمر (CRI) كيتامين + ليدوكايين + مورفين/فنتانيل، مع تدفئة المريض وتخفيف التوتر."

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #d97706; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">😣</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #d97706;">أداة تقييم الألم السريري المركب (Glasgow & Grimace Scale)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">مقياس كمي موضوعي لدرجات الألم الحركي والجسدي وتعبير الوجه لتحديد عتبة التدخل المسكن</p>
                </div>
            </div>

            <form method="POST" action="/tools/pain-scale" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">1. الوضعية والوقوف (Posture):</label>
                        <select name="posture" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if posture == 0 else ''}>0: مسترخٍ وطبيعي تماماً</option>
                            <option value="1" {'selected' if posture == 1 else ''}>1: متوتر قليلاً أو يتجنب وضع ثقله على طرف</option>
                            <option value="2" {'selected' if posture == 2 else ''}>2: وضعية الصلاة (انحناء الظهر) أو تقوس بطني</option>
                            <option value="3" {'selected' if posture == 3 else ''}>3: رقود تام مع تصلب ورفض الحركة نهائياً</option>
                        </select>
                    </div>

                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">2. الأصوات الصادرة (Vocalization):</label>
                        <select name="vocalization" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if vocalization == 0 else ''}>0: هادئ لا يصدر أي أنين</option>
                            <option value="1" {'selected' if vocalization == 1 else ''}>1: أنين خفيف عند الحركة فقط</option>
                            <option value="2" {'selected' if vocalization == 2 else ''}>2: عواء أو خوار أو صراخ مستمر حتى في السكون</option>
                            <option value="3" {'selected' if vocalization == 3 else ''}>3: صراخ حاد هستيري عند الاقتراب منه</option>
                        </select>
                    </div>

                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">3. الحركة والاستجابة (Mobility):</label>
                        <select name="mobility" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if mobility == 0 else ''}>0: يتحرك بحرية ونشاط طبيعي</option>
                            <option value="1" {'selected' if mobility == 1 else ''}>1: حركة بطيئة ومترددة مع عرج خفيف</option>
                            <option value="2" {'selected' if mobility == 2 else ''}>2: عرج شديد أو انعدام توازن</option>
                            <option value="3" {'selected' if mobility == 3 else ''}>3: عاجز عن الوقوف أو شلل حركي</option>
                        </select>
                    </div>

                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">4. استجابة اللمس الموضعي (Palpation):</label>
                        <select name="palpation" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if palpation == 0 else ''}>0: لا يمانع الفحص ولا يتألم</option>
                            <option value="1" {'selected' if palpation == 1 else ''}>1: يلتفت لموضع الألم أو يشد عضلاته</option>
                            <option value="2" {'selected' if palpation == 2 else ''}>2: يسحب الطرف أو يبتعد أو يتأوه بوضوح</option>
                            <option value="3" {'selected' if palpation == 3 else ''}>3: محاولة العض أو الركل الدفاعي الشرس</option>
                        </select>
                    </div>

                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">5. تعابير الوجه والعينين (Grimace Scale):</label>
                        <select name="grimace" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if grimace == 0 else ''}>0: نظرة يقظة، أذنان للأمام، خدود مسترخية</option>
                            <option value="1" {'selected' if grimace == 1 else ''}>1: تضيق محجر العين (Orbital tightening) وتسطح الآذان</option>
                            <option value="2" {'selected' if grimace == 2 else ''}>2: شد وانقباض شديد في عضلات الوجه وفتحات الأنف</option>
                            <option value="3" {'selected' if grimace == 3 else ''}>3: إغماض عينين كامل مع خفض الرأس والأذنين للخلف</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #d97706; border-color: #d97706;">📊 تقييم درجة الألم والبروتوكول العلاجي</button>
            </form>

            <div style="margin-top: 24px; background: {bg_col}; border: 2px solid {color}; border-radius: 12px; padding: 20px;">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
                    <div>
                        <div style="font-size: 0.9rem; color: #475569; font-weight: 700;">مجموع نقاط تقييم الألم السريري:</div>
                        <div style="font-size: 2.2rem; font-weight: 900; color: {color}; margin: 5px 0;">{total_score} <span style="font-size: 1.1rem; color: #64748b;">/ 15</span></div>
                    </div>
                    <div style="background: #ffffff; border: 1.5px solid {color}; padding: 8px 18px; border-radius: 20px; font-weight: 800; color: {color}; font-size: 1.05rem;">
                        {level}
                    </div>
                </div>
                <div style="margin-top: 14px; border-top: 1px dashed {color}; padding-top: 12px;">
                    <strong style="color: {color};">💊 خطة التسكين الموصى بها إكلينيكياً:</strong>
                    <p style="margin: 5px 0 0 0; font-size: 0.95rem; line-height: 1.6; color: #0f172a;">{action}</p>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("تقييم الألم السريري", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 6. GESTATION & PARTURITION CALCULATOR (/tools/gestation-calc)
# ==============================================================================
@router.get("/tools/gestation-calc", response_class=HTMLResponse)
@router.post("/tools/gestation-calc", response_class=HTMLResponse)
async def gestation_calc_tool(
    request: Request,
    species: str = "أبقار",
    breeding_date: str = ""
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if not breeding_date:
        breeding_date = date.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        breeding_date = form.get("breeding_date", breeding_date)

    try:
        b_dt = datetime.strptime(breeding_date, "%Y-%m-%d").date()
    except Exception:
        b_dt = date.today()

    gest_days = {
        "أبقار": 283,
        "إبل": 375,
        "خيول": 340,
        "أغنام": 150,
        "ماعز": 150,
        "جاموس": 310,
        "كلاب": 63,
        "قطط": 63
    }
    days = gest_days.get(species, 283)
    due_date = b_dt + timedelta(days=days)
    dry_off = due_date - timedelta(days=60) if days > 200 else due_date - timedelta(days=15)
    pre_vaccine = due_date - timedelta(days=30)
    current_days = (date.today() - b_dt).days
    remaining_days = max(0, (due_date - date.today()).days)
    pct = min(100.0, max(0.0, (current_days / days) * 100.0))

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #ec4899; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🤰</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #ec4899;">حاسبة الحمل ومواعيد الولادة والتجفيف والتحصين</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب دقيق لتواريخ الولادة المتوقعة، جدول التجفيف، وتطعيمات السرسوب للمواليد</p>
                </div>
            </div>

            <form method="POST" action="/tools/gestation-calc" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الحيوان:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="أبقار" {'selected' if species == 'أبقار' else ''}>أبقار (283 يوماً)</option>
                            <option value="جاموس" {'selected' if species == 'جاموس' else ''}>جاموس (310 يوماً)</option>
                            <option value="خيول" {'selected' if species == 'خيول' else ''}>خيول (340 يوماً)</option>
                            <option value="إبل" {'selected' if species == 'إبل' else ''}>إبل / نوق (375 يوماً)</option>
                            <option value="أغنام" {'selected' if species == 'أغنام' else ''}>أغنام (150 يوماً)</option>
                            <option value="ماعز" {'selected' if species == 'ماعز' else ''}>ماعز (150 يوماً)</option>
                            <option value="كلاب" {'selected' if species == 'كلاب' else ''}>كلاب (63 يوماً)</option>
                            <option value="قطط" {'selected' if species == 'قطط' else ''}>قطط (63 يوماً)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">تاريخ التلقيح أو الإخصاب:</label>
                        <input type="date" name="breeding_date" value="{breeding_date}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #ec4899; border-color: #ec4899;">📅 احسب المواعيد الفلكية والإكلينيكية</button>
            </form>

            <div style="margin-top: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                <div style="background: #fdf2f8; border: 1.5px solid #f472b6; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #9d174d; font-weight: 700;">موعد الولادة المتوقع (Due Date)</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: #be185d; margin: 8px 0;">{due_date.strftime('%Y-%m-%d')}</div>
                    <div style="font-size: 0.8rem; color: #9d174d;">متبقي {remaining_days} يوماً للولادة</div>
                </div>

                <div style="background: #fff7ed; border: 1.5px solid #fdba74; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #9a3412; font-weight: 700;">تاريخ بدء التجفيف (Dry-off)</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: #c2410c; margin: 8px 0;">{dry_off.strftime('%Y-%m-%d')}</div>
                    <div style="font-size: 0.8rem; color: #9a3412;">حقن محاقن الضرع الجاف وسدادة الحلمات</div>
                </div>

                <div style="background: #eff6ff; border: 1.5px solid #93c5fd; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #1e40af; font-weight: 700;">تطعيم تحصين السرسوب (Pre-partum)</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: #1d4ed8; margin: 8px 0;">{pre_vaccine.strftime('%Y-%m-%d')}</div>
                    <div style="font-size: 0.8rem; color: #1e40af;">(إيكولاي، كلوستريديا، كورونا السرسوب)</div>
                </div>
            </div>

            <div style="margin-top: 20px; background: #f8fafc; border: 1px solid var(--border); border-radius: 10px; padding: 16px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 6px;">
                    <span>تقدم فترة الحمل: {current_days} يوماً ممرورة</span>
                    <span>{pct:.1f}%</span>
                </div>
                <div style="width: 100%; height: 12px; background: #e2e8f0; border-radius: 6px; overflow: hidden;">
                    <div style="width: {pct}%; height: 100%; background: linear-gradient(90deg, #ec4899, #f43f5e);"></div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("حاسبة الحمل والولادة", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 7. NUTRITION & ENERGY REQUIREMENT (RER / MER) (/tools/nutrition-calc)
# ==============================================================================
@router.get("/tools/nutrition-calc", response_class=HTMLResponse)
@router.post("/tools/nutrition-calc", response_class=HTMLResponse)
async def nutrition_calc_tool(
    request: Request,
    species: str = "كلاب",
    weight: float = 20.0,
    stage: str = "maintenance"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        weight = float(form.get("weight", weight))
        stage = form.get("stage", stage)

    # RER = 70 * (weight ** 0.75)
    rer = 70.0 * (weight ** 0.75)
    factors = {
        "maintenance": 1.6 if species == "كلاب" else 1.2,
        "growth": 2.5 if species == "كلاب" else 2.0,
        "lactation": 3.5,
        "weight_loss": 1.0,
        "geriatric": 1.2
    }
    f_val = factors.get(stage, 1.6)
    mer = rer * f_val
    dry_matter_kg = (weight * 0.025) if species in ["أبقار", "خيول", "أغنام"] else (mer / 3800.0)

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #16a34a; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🥩</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #16a34a;">حاسبة الاحتياج الطاقي والغذائي اليومي (RER / MER)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب السعرات الحرارية الحيوية (Kcal/day) واحتياج المادة الجافة لحالات النقاهة، الإنتاج، والنمو</p>
                </div>
            </div>

            <form method="POST" action="/tools/nutrition-calc" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الحيوان:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="كلاب" {'selected' if species == 'كلاب' else ''}>كلاب (Canine)</option>
                            <option value="قطط" {'selected' if species == 'قطط' else ''}>قطط (Feline)</option>
                            <option value="أبقار" {'selected' if species == 'أبقار' else ''}>أبقار (Bovine)</option>
                            <option value="خيول" {'selected' if species == 'خيول' else ''}>خيول (Equine)</option>
                            <option value="أغنام" {'selected' if species == 'أغنام' else ''}>أغنام وماعز (Ovine/Caprine)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">وزن الحيوان (كجم):</label>
                        <input type="number" step="0.5" name="weight" value="{weight}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">المرحلة الفسيولوجية والنشاط:</label>
                        <select name="stage" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="maintenance" {'selected' if stage == 'maintenance' else ''}>صيانة للبالغين نشاط عادي (Adult Maintenance)</option>
                            <option value="growth" {'selected' if stage == 'growth' else ''}>نمو وجراء صغار (Growth / Puppies)</option>
                            <option value="lactation" {'selected' if stage == 'lactation' else ''}>رضاعة وإنتاج حليب (Peak Lactation)</option>
                            <option value="weight_loss" {'selected' if stage == 'weight_loss' else ''}>حمية تخسيس السمنة (Weight Loss / Hypocaloric)</option>
                            <option value="geriatric" {'selected' if stage == 'geriatric' else ''}>كبار السن ونشاط منخفض (Senior / Geriatric)</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #16a34a; border-color: #16a34a;">⚡ احسب الاحتياج الغذائي</button>
            </form>

            <div style="margin-top: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
                <div style="background: #f0fdf4; border: 1.5px solid #86efac; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #166534; font-weight: 700;">طاقة الراحة الأساسية (RER)</div>
                    <div style="font-size: 1.9rem; font-weight: 800; color: #15803d; margin: 8px 0;">{rer:,.0f} <span style="font-size: 1rem;">سعرة/يوم</span></div>
                    <div style="font-size: 0.8rem; color: #166534;">طاقة الأيض الأساسي في السكون التام</div>
                </div>

                <div style="background: #eff6ff; border: 1.5px solid #93c5fd; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #1e40af; font-weight: 700;">الطاقة اليومية المستهدفة (MER)</div>
                    <div style="font-size: 1.9rem; font-weight: 800; color: #1d4ed8; margin: 8px 0;">{mer:,.0f} <span style="font-size: 1rem;">سعرة/يوم</span></div>
                    <div style="font-size: 0.8rem; color: #1e40af;">(المعامل الفسيولوجي المطبق: ×{f_val})</div>
                </div>

                <div style="background: #fffbeb; border: 1.5px solid #fde68a; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #92400e; font-weight: 700;">المادة الجافة التقديرية (Dry Matter)</div>
                    <div style="font-size: 1.9rem; font-weight: 800; color: #b45309; margin: 8px 0;">{dry_matter_kg:,.2f} <span style="font-size: 1rem;">كجم/يوم</span></div>
                    <div style="font-size: 0.8rem; color: #92400e;">كمية العلف الجاف أو الطعام المتوازن</div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("حاسبة الاحتياج الغذائي", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 8. BODY CONDITION SCORING (BCS 1-9 & 1-5) (/tools/bcs-evaluator)
# ==============================================================================
@router.get("/tools/bcs-evaluator", response_class=HTMLResponse)
@router.post("/tools/bcs-evaluator", response_class=HTMLResponse)
async def bcs_evaluator_tool(
    request: Request,
    species: str = "أبقار",
    weight: float = 550.0,
    score: int = 3
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        weight = float(form.get("weight", weight))
        score = int(form.get("score", score))

    if score <= 2:
        status = "نحافة شديدة وهزال (Underconditioned / Thin)"
        corr_pct = "+15% إلى +25% طاقة إضافية للوصول للدرجة المثالية"
        color = "#dc2626"
    elif score == 3:
        status = "درجة مثالية ممتازة (Ideal Body Condition)"
        corr_pct = "الحفاظ على نفس المعدل العلفي المتوازن الحالي"
        color = "#16a34a"
    else:
        status = "سمنة مفرطة وخطر الكبد الدهني (Overconditioned / Fat)"
        corr_pct = "-15% إلى -20% طاقة وخفض المركزات لمنع حمى النفاس والكبد الدهني"
        color = "#d97706"

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #0891b2; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">⚖️</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #0891b2;">مقيم الحالة الجسدية للحيوان (Body Condition Scoring - BCS)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">تقييم طبقة الدهن والعضلات على الأضلاع والعمود الفقري وميزان تعديل العليقة الغذائية</p>
                </div>
            </div>

            <form method="POST" action="/tools/bcs-evaluator" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الحيوان:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="أبقار" {'selected' if species == 'أبقار' else ''}>أبقار حلوب وماشية (مقياس 1 إلى 5)</option>
                            <option value="خيول" {'selected' if species == 'خيول' else ''}>خيول (Henneke مقياس 1 إلى 9)</option>
                            <option value="أغنام" {'selected' if species == 'أغنام' else ''}>أغنام وماعز (مقياس 1 إلى 5)</option>
                            <option value="كلاب" {'selected' if species == 'كلاب' else ''}>كلاب وقطط (WSAVA مقياس 1 إلى 9)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الوزن الحالي المسجل (كجم):</label>
                        <input type="number" step="0.5" name="weight" value="{weight}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">درجة الحالة الجسدية (BCS Score):</label>
                        <select name="score" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="1" {'selected' if score == 1 else ''}>1: هزال شديد وعظام بارزة حادة</option>
                            <option value="2" {'selected' if score == 2 else ''}>2: نحيف والأضلاع مرئية بوضوح</option>
                            <option value="3" {'selected' if score == 3 else ''}>3: مثالي (العمود الفقري ممتلئ بحافة ناعمة)</option>
                            <option value="4" {'selected' if score == 4 else ''}>4: زيادة وزن، ترسب دهن خفيف حول العروق</option>
                            <option value="5" {'selected' if score == 5 else ''}>5: سمنة مفرطة، دهن سميك يغطي الأضلاع تماماً</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #0891b2; border-color: #0891b2;">⚖️ تقييم الحالة وتعديل التغذية</button>
            </form>

            <div style="margin-top: 24px; background: #f0fdfa; border: 2px solid #2dd4bf; border-radius: 12px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <h3 style="margin: 0; color: #0f766e; font-size: 1.25rem;">التشخيص السريري للحالة الجسدية:</h3>
                        <div style="font-size: 1.4rem; font-weight: 800; color: {color}; margin: 6px 0;">{status}</div>
                    </div>
                    <div style="background: #ffffff; border: 1.5px solid {color}; padding: 6px 16px; border-radius: 20px; font-weight: 800; color: {color};">
                        درجة BCS: {score}
                    </div>
                </div>
                <div style="margin-top: 12px; border-top: 1px dashed #99f6e4; padding-top: 12px; font-size: 0.95rem; color: #042f2e;">
                    <strong>🎯 التوصية الغذائية التصحيحية:</strong> {corr_pct}
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("تقييم الحالة الجسدية BCS", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 9. LAMENESS SCORING & HOOF GUIDE (/tools/lameness-scoring)
# ==============================================================================
@router.get("/tools/lameness-scoring", response_class=HTMLResponse)
@router.post("/tools/lameness-scoring", response_class=HTMLResponse)
async def lameness_scoring_tool(
    request: Request,
    species: str = "خيول",
    grade: int = 2,
    limb: str = "RF",
    hoof_lesion: str = "sole_ulcer"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        grade = int(form.get("grade", grade))
        limb = form.get("limb", limb)
        hoof_lesion = form.get("hoof_lesion", hoof_lesion)

    descriptions = {
        0: "سليم تماماً - حركة متناغمة ولا يوجد أي عرج (Sound)",
        1: "عرج خفيف جداً - غير متسق ويصعب ملاحظته إلا تحت ظروف خاصة (Grade 1)",
        2: "عرج متسق في الخبب والميل الدائري مع حركة خفيفة للرأس (Grade 2)",
        3: "عرج ملحوظ بوضوح عند المشي العادي وهبوط الرأس عند ارتكاز الطرف المقابل (Grade 3)",
        4: "عرج شديد - الحيوان يرفع قدمه سريعاً ويتحاشى ملامسة الأرض (Grade 4)",
        5: "انعدام ارتكاز تام - عجز عن تحميل أي وزن على القدم المصابة (Grade 5)"
    }
    desc = descriptions.get(grade, descriptions[2])

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #854d0e; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🐎</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #854d0e;">دليل ومقياس فحص العرج السريري (AAEP & Sprecher Lameness Scale)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">التصنيف المعتمد عالمياً لعرج الخيول والأبقار وخريطة تشخيص إصابات الحوافر والمفاصل</p>
                </div>
            </div>

            <form method="POST" action="/tools/lameness-scoring" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الحيوان:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="خيول" {'selected' if species == 'خيول' else ''}>خيول (AAEP Scale 0-5)</option>
                            <option value="أبقار" {'selected' if species == 'أبقار' else ''}>أبقار حلوب (Sprecher 1-5 Locomotion)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الطرف المصاب المشتبه به:</label>
                        <select name="limb" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="RF" {'selected' if limb == 'RF' else ''}>الطرف الأمامي الأيمن (Right Forelimb)</option>
                            <option value="LF" {'selected' if limb == 'LF' else ''}>الطرف الأمامي الأيسر (Left Forelimb)</option>
                            <option value="RH" {'selected' if limb == 'RH' else ''}>الطرف الخلفي الأيمن (Right Hindlimb)</option>
                            <option value="LH" {'selected' if limb == 'LH' else ''}>الطرف الخلفي الأيسر (Left Hindlimb)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">درجة العرج الحركي:</label>
                        <select name="grade" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if grade == 0 else ''}>درجة 0: سليم تماماً</option>
                            <option value="1" {'selected' if grade == 1 else ''}>درجة 1: عرج خفيف جداً غير متسق</option>
                            <option value="2" {'selected' if grade == 2 else ''}>درجة 2: عرج متسق في الدوائر والخبب</option>
                            <option value="3" {'selected' if grade == 3 else ''}>درجة 3: عرج ملحوظ بوضوح وهبوط الرأس</option>
                            <option value="4" {'selected' if grade == 4 else ''}>درجة 4: عرج شديد مع تجنب لمس الأرض</option>
                            <option value="5" {'selected' if grade == 5 else ''}>درجة 5: عدم ارتكاز تام (Non-weight bearing)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الآفة المشتبهة بالحافر أو العظام:</label>
                        <select name="hoof_lesion" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="sole_ulcer" {'selected' if hoof_lesion == 'sole_ulcer' else ''}>قرحة النعل (Sole Ulcer / Rusterholz)</option>
                            <option value="white_line" {'selected' if hoof_lesion == 'white_line' else ''}>مرض الخط الأبيض وتجمع الخراج (White Line Abscess)</option>
                            <option value="digital_dermatitis" {'selected' if hoof_lesion == 'digital_dermatitis' else ''}>عفن الحوافر والتهاب الجلد الأصبعي (Foot Rot / Mortellaro)</option>
                            <option value="navicular" {'selected' if hoof_lesion == 'navicular' else ''}>متلازمة العظم الزورقي في الخيول (Navicular Syndrome)</option>
                            <option value="laminitis" {'selected' if hoof_lesion == 'laminitis' else ''}>حمرة الحافر الحادة (Acute Laminitis / Founder)</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #854d0e; border-color: #854d0e;">🐎 تشخيص العرج وتحديد خطة العلاج</button>
            </form>

            <div style="margin-top: 24px; background: #fefce8; border: 2px solid #ca8a04; border-radius: 12px; padding: 20px;">
                <h3 style="margin: 0 0 10px 0; color: #713f12; font-size: 1.2rem;">📋 التقييم الإكلينيكي للعرج:</h3>
                <div style="font-size: 1.15rem; font-weight: 800; color: #854d0e; margin-bottom: 12px;">{desc}</div>
                <div style="border-top: 1px dashed #eab308; padding-top: 10px; font-size: 0.9rem; line-height: 1.7; color: #422006;">
                    <strong>🛠️ الخطة العلاجية والتقليم التصحيحي:</strong>
                    تركيب قالوب خشبي/بلاستيكي (Hoof Block) على الظلف السليم المقابل لرفع الحافر المصاب عن الأرض، تفريغ الخراج بحذر دون الإضرار بالنسيج الحساس، وتضميد الحافر بضمادة أوكسي تتراسيكلين أو بخاخ مع راحة تامة.
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("دليل فحص العرج", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 10. ELECTROLYTE DEFICIT CORRECTION (/tools/electrolyte-correction)
# ==============================================================================
@router.get("/tools/electrolyte-correction", response_class=HTMLResponse)
@router.post("/tools/electrolyte-correction", response_class=HTMLResponse)
async def electrolyte_correction_tool(
    request: Request,
    weight: float = 300.0,
    measured_na: float = 125.0,
    target_na: float = 140.0,
    measured_k: float = 2.8,
    target_k: float = 4.0
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        weight = float(form.get("weight", weight))
        measured_na = float(form.get("measured_na", measured_na))
        target_na = float(form.get("target_na", target_na))
        measured_k = float(form.get("measured_k", measured_k))
        target_k = float(form.get("target_k", target_k))

    # Sodium Deficit: 0.6 * weight * (target - measured)
    na_deficit_meq = 0.6 * weight * max(0.0, (target_na - measured_na))
    # Potassium Deficit: 0.4 * weight * (target - measured)
    k_deficit_meq = 0.4 * weight * max(0.0, (target_k - measured_k))
    max_k_rate_meq_hr = 0.5 * weight  # max 0.5 mEq/kg/hr to avoid cardiac arrest

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #6366f1; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">⚡</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #6366f1;">حاسبة تصحيح الشوارد ونقص الصوديوم والبوتاسيوم (Electrolyte Deficit)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب عجز الصوديوم والبوتاسيوم والسرعة القصوى الآمنة للتسريب الوريدي لتجنب السكتة القلبية</p>
                </div>
            </div>

            <form method="POST" action="/tools/electrolyte-correction" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">وزن الحيوان (كجم):</label>
                        <input type="number" step="0.5" name="weight" value="{weight}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">صوديوم الدم المقاس Na+ (mEq/L):</label>
                        <input type="number" step="0.5" name="measured_na" value="{measured_na}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">الصوديوم المستهدف Na+ (mEq/L):</label>
                        <input type="number" step="0.5" name="target_na" value="{target_na}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">بوتاسيوم الدم المقاس K+ (mEq/L):</label>
                        <input type="number" step="0.1" name="measured_k" value="{measured_k}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">البوتاسيوم المستهدف K+ (mEq/L):</label>
                        <input type="number" step="0.1" name="target_k" value="{target_k}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #6366f1; border-color: #6366f1;">⚡ احسب العجز والجرعات الآمنة</button>
            </form>

            <div style="margin-top: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
                <div style="background: #eef2ff; border: 1.5px solid #a5b4fc; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #3730a3; font-weight: 700;">إجمالي عجز الصوديوم (Na+ Deficit)</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #4338ca; margin: 8px 0;">{na_deficit_meq:,.0f} <span style="font-size: 1rem;">mEq</span></div>
                    <div style="font-size: 0.8rem; color: #3730a3;">الحد الأقصى لرفع الصوديوم: 0.5 mEq/L/ساعة</div>
                </div>

                <div style="background: #fdf4ff; border: 1.5px solid #f0abfc; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #86198f; font-weight: 700;">إجمالي عجز البوتاسيوم (K+ Deficit)</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #a21caf; margin: 8px 0;">{k_deficit_meq:,.0f} <span style="font-size: 1rem;">mEq</span></div>
                    <div style="font-size: 0.8rem; color: #86198f;">يحسب بنسبة التوزيع الخلوي 0.4</div>
                </div>

                <div style="background: #fef2f2; border: 1.5px solid #fca5a5; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #991b1b; font-weight: 700;">أقصى سرعة تسريب بوتاسيوم آمنة</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #dc2626; margin: 8px 0;">{max_k_rate_meq_hr:,.1f} <span style="font-size: 1rem;">mEq/ساعة</span></div>
                    <div style="font-size: 0.8rem; color: #991b1b;">⚠️ تجاوز هذا المعدل يسبب توقف القلب الانبساطي</div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("حاسبة تصحيح الشوارد", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 11. BODY SURFACE AREA (BSA m²) ONCOLOGY CALCULATOR (/tools/bsa-calculator)
# ==============================================================================
@router.get("/tools/bsa-calculator", response_class=HTMLResponse)
@router.post("/tools/bsa-calculator", response_class=HTMLResponse)
async def bsa_calculator_tool(
    request: Request,
    species: str = "كلاب",
    weight: float = 25.0
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        weight = float(form.get("weight", weight))

    # BSA = (K * (wt_grams ** (2/3))) / 10000
    k_val = 10.1 if species == "كلاب" else 10.0
    wt_grams = weight * 1000.0
    bsa = (k_val * (wt_grams ** (2.0 / 3.0))) / 10000.0

    # Common chemo doses
    vincristine_mg = bsa * 0.7  # 0.7 mg/m2
    doxorubicin_mg = bsa * 30.0 if weight > 10 else weight * 1.0  # 30 mg/m2 for >10kg
    carboplatin_mg = bsa * 300.0  # 300 mg/m2

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #7c3aed; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">📐</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #7c3aed;">حاسبة مساحة سطح الجسم لعلاج الأورام الدقيق (BSA Calculator)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب مساحة الجسم بالمتر المربع (m²) لضبط الجرعات الحرجة لأدوية العلاج الكيماوي والأورام</p>
                </div>
            </div>

            <form method="POST" action="/tools/bsa-calculator" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الحيوان:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="كلاب" {'selected' if species == 'كلاب' else ''}>كلاب (K = 10.1)</option>
                            <option value="قطط" {'selected' if species == 'قطط' else ''}>قطط (K = 10.0)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">وزن الحيوان (كجم):</label>
                        <input type="number" step="0.1" name="weight" value="{weight}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #7c3aed; border-color: #7c3aed;">📐 حساب مساحة سطح الجسم والجرعات الكيماوية</button>
            </form>

            <div style="margin-top: 24px; text-align: center; background: #f5f3ff; border: 2px solid #c4b5fd; padding: 22px; border-radius: 14px;">
                <div style="font-size: 0.95rem; color: #5b21b6; font-weight: 700;">مساحة سطح الجسم المحسوبة (Body Surface Area):</div>
                <div style="font-size: 2.8rem; font-weight: 900; color: #6d28d9; margin: 10px 0;">{bsa:.3f} <span style="font-size: 1.3rem;">m²</span></div>
                <div style="font-size: 0.85rem; color: #7c3aed;">(معادلة مساحة الجسم الدقيقة للوزن {weight} كجم)</div>
            </div>

            <div style="margin-top: 20px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
                <div style="background: #ffffff; border: 1.5px solid var(--border); padding: 16px; border-radius: 10px;">
                    <div style="font-size: 0.85rem; font-weight: 700; color: #334155;">فينكريستين (Vincristine - 0.7 mg/m²)</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: #7c3aed; margin: 6px 0;">{vincristine_mg:.2f} مجم</div>
                </div>
                <div style="background: #ffffff; border: 1.5px solid var(--border); padding: 16px; border-radius: 10px;">
                    <div style="font-size: 0.85rem; font-weight: 700; color: #334155;">دوكسوروبيسين (Doxorubicin - 30 mg/m²)</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: #7c3aed; margin: 6px 0;">{doxorubicin_mg:.1f} مجم</div>
                </div>
                <div style="background: #ffffff; border: 1.5px solid var(--border); padding: 16px; border-radius: 10px;">
                    <div style="font-size: 0.85rem; font-weight: 700; color: #334155;">كاربوبلاتين (Carboplatin - 300 mg/m²)</div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: #7c3aed; margin: 6px 0;">{carboplatin_mg:.1f} مجم</div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("حاسبة مساحة سطح الجسم للأورام", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 12. CALIFORNIA MASTITIS TEST EVALUATOR (/tools/cmt-mastitis)
# ==============================================================================
@router.get("/tools/cmt-mastitis", response_class=HTMLResponse)
@router.post("/tools/cmt-mastitis", response_class=HTMLResponse)
async def cmt_mastitis_tool(
    request: Request,
    rf: str = "0",
    lf: str = "2",
    rr: str = "1",
    lr: str = "0"
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        rf = form.get("rf", rf)
        lf = form.get("lf", lf)
        rr = form.get("rr", rr)
        lr = form.get("lr", lr)

    scc_map = {
        "0": ("سلبي تماماً (Negative)", "< 200,000 خلية/مل", "لا يوجد فقد بالحليب", "#16a34a"),
        "T": ("أثر تخثر طفيف (Trace)", "150,000 - 400,000 خلية/مل", "فقد 6% من الإنتاج", "#0284c7"),
        "1": ("إيجابي خفيف (Grade 1)", "400,000 - 1,200,000 خلية/مل", "فقد 10% من الإنتاج", "#d97706"),
        "2": ("إيجابي متوسط (Grade 2)", "1,200,000 - 5,000,000 خلية/مل", "فقد 16% من الإنتاج", "#ea580c"),
        "3": ("إيجابي شديد / تخثر هلامي (Grade 3)", "> 5,000,000 خلية/مل", "فقد > 25% من الإنتاج", "#dc2626")
    }

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #2563eb; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🥛</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #2563eb;">دليل فحص كاليفورنيا لالتهاب الضرع الخفي (CMT Evaluation)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">تقييم أرباع الضرع الأربعة، تقدير عدد الخلايا الجسدية (SCC)، ونسبة الفقد الإنتاجي في الحليب</p>
                </div>
            </div>

            <form method="POST" action="/tools/cmt-mastitis" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 16px;">
                    <div style="background: #ffffff; padding: 14px; border-radius: 10px; border: 1.5px solid var(--border);">
                        <label style="display: block; font-weight: 800; margin-bottom: 6px; color: #1e3a8a;">الربع الأمامي الأيمن (Right Fore):</label>
                        <select name="rf" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if rf == '0' else ''}>0: سلبي (سائل غير متخثر)</option>
                            <option value="T" {'selected' if rf == 'T' else ''}>T: أثر خفيف (Trace)</option>
                            <option value="1" {'selected' if rf == '1' else ''}>1: إيجابي خفيف (لزوجة طفيفة)</option>
                            <option value="2" {'selected' if rf == '2' else ''}>2: إيجابي متوسط (تجمع هلامي بالوسط)</option>
                            <option value="3" {'selected' if rf == '3' else ''}>3: إيجابي شديد (كتلة جيلاتينية متماسكة)</option>
                        </select>
                    </div>

                    <div style="background: #ffffff; padding: 14px; border-radius: 10px; border: 1.5px solid var(--border);">
                        <label style="display: block; font-weight: 800; margin-bottom: 6px; color: #1e3a8a;">الربع الأمامي الأيسر (Left Fore):</label>
                        <select name="lf" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if lf == '0' else ''}>0: سلبي</option>
                            <option value="T" {'selected' if lf == 'T' else ''}>T: أثر خفيف</option>
                            <option value="1" {'selected' if lf == '1' else ''}>1: إيجابي خفيف</option>
                            <option value="2" {'selected' if lf == '2' else ''}>2: إيجابي متوسط</option>
                            <option value="3" {'selected' if lf == '3' else ''}>3: إيجابي شديد</option>
                        </select>
                    </div>

                    <div style="background: #ffffff; padding: 14px; border-radius: 10px; border: 1.5px solid var(--border);">
                        <label style="display: block; font-weight: 800; margin-bottom: 6px; color: #1e3a8a;">الربع الخلفي الأيمن (Right Rear):</label>
                        <select name="rr" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if rr == '0' else ''}>0: سلبي</option>
                            <option value="T" {'selected' if rr == 'T' else ''}>T: أثر خفيف</option>
                            <option value="1" {'selected' if rr == '1' else ''}>1: إيجابي خفيف</option>
                            <option value="2" {'selected' if rr == '2' else ''}>2: إيجابي متوسط</option>
                            <option value="3" {'selected' if rr == '3' else ''}>3: إيجابي شديد</option>
                        </select>
                    </div>

                    <div style="background: #ffffff; padding: 14px; border-radius: 10px; border: 1.5px solid var(--border);">
                        <label style="display: block; font-weight: 800; margin-bottom: 6px; color: #1e3a8a;">الربع الخلفي الأيسر (Left Rear):</label>
                        <select name="lr" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border);">
                            <option value="0" {'selected' if lr == '0' else ''}>0: سلبي</option>
                            <option value="T" {'selected' if lr == 'T' else ''}>T: أثر خفيف</option>
                            <option value="1" {'selected' if lr == '1' else ''}>1: إيجابي خفيف</option>
                            <option value="2" {'selected' if lr == '2' else ''}>2: إيجابي متوسط</option>
                            <option value="3" {'selected' if lr == '3' else ''}>3: إيجابي شديد</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #2563eb; border-color: #2563eb;">🥛 تقييم نتائج الحلمات الأربعة</button>
            </form>

            <div style="margin-top: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
                <div style="background: #f8fafc; border: 2px solid {scc_map[rf][3]}; border-radius: 10px; padding: 14px; text-align: center;">
                    <div style="font-weight: 800; color: #1e293b; margin-bottom: 4px;">أمامي أيمن (RF)</div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: {scc_map[rf][3]};">{scc_map[rf][0]}</div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">SCC: {scc_map[rf][1]}</div>
                </div>

                <div style="background: #f8fafc; border: 2px solid {scc_map[lf][3]}; border-radius: 10px; padding: 14px; text-align: center;">
                    <div style="font-weight: 800; color: #1e293b; margin-bottom: 4px;">أمامي أيسر (LF)</div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: {scc_map[lf][3]};">{scc_map[lf][0]}</div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">SCC: {scc_map[lf][1]}</div>
                </div>

                <div style="background: #f8fafc; border: 2px solid {scc_map[rr][3]}; border-radius: 10px; padding: 14px; text-align: center;">
                    <div style="font-weight: 800; color: #1e293b; margin-bottom: 4px;">خلفي أيمن (RR)</div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: {scc_map[rr][3]};">{scc_map[rr][0]}</div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">SCC: {scc_map[rr][1]}</div>
                </div>

                <div style="background: #f8fafc; border: 2px solid {scc_map[lr][3]}; border-radius: 10px; padding: 14px; text-align: center;">
                    <div style="font-weight: 800; color: #1e293b; margin-bottom: 4px;">خلفي أيسر (LR)</div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: {scc_map[lr][3]};">{scc_map[lr][0]}</div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">SCC: {scc_map[lr][1]}</div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("فحص كاليفورنيا لالتهاب الضرع", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 13. IRIS RENAL FAILURE STAGING & DIET (/tools/renal-calc)
# ==============================================================================
@router.get("/tools/renal-calc", response_class=HTMLResponse)
@router.post("/tools/renal-calc", response_class=HTMLResponse)
async def renal_calc_tool(
    request: Request,
    species: str = "قطط",
    creatinine: float = 2.4,
    sdma: float = 18.0,
    upc: float = 0.3,
    systolic_bp: int = 145
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        species = form.get("species", species)
        creatinine = float(form.get("creatinine", creatinine))
        sdma = float(form.get("sdma", sdma))
        upc = float(form.get("upc", upc))
        systolic_bp = int(form.get("systolic_bp", systolic_bp))

    if species == "قطط":
        if creatinine < 1.6:
            stage = "المرحلة الأولى (IRIS Stage 1 - Non-azotemic)"
        elif creatinine <= 2.8:
            stage = "المرحلة الثانية (IRIS Stage 2 - Mild Azotemia)"
        elif creatinine <= 5.0:
            stage = "المرحلة الثالثة (IRIS Stage 3 - Moderate Azotemia)"
        else:
            stage = "المرحلة الرابعة (IRIS Stage 4 - Severe Azotemia)"
    else:  # كلاب
        if creatinine < 1.4:
            stage = "المرحلة الأولى (IRIS Stage 1)"
        elif creatinine <= 2.8:
            stage = "المرحلة الثانية (IRIS Stage 2)"
        elif creatinine <= 5.0:
            stage = "المرحلة الثالثة (IRIS Stage 3)"
        else:
            stage = "المرحلة الرابعة (IRIS Stage 4)"

    bp_status = "ضغط طبيعي (Normotensive)" if systolic_bp < 140 else ("ارتفاع ضغط متوسط" if systolic_bp < 160 else "ارتفاع ضغط دم حرج يستوجب أملوديبين (Hypertensive)")

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #059669; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🫘</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #059669;">حاسبة وظائف الكلى ومعدل الترشيح وتصنيف (IRIS CKD Staging)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">التصنيف المعتمد لجمعية أمراض الكلى البيطرية الدولية وضبط الفوسفور والبروتين الغذائي</p>
                </div>
            </div>

            <form method="POST" action="/tools/renal-calc" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نوع الحيوان:</label>
                        <select name="species" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                            <option value="قطط" {'selected' if species == 'قطط' else ''}>قطط (Feline CKD)</option>
                            <option value="كلاب" {'selected' if species == 'كلاب' else ''}>كلاب (Canine CKD)</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">كرياتينين الدم Creatinine (mg/dL):</label>
                        <input type="number" step="0.1" name="creatinine" value="{creatinine}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">المؤشر المبكر SDMA (µg/dL):</label>
                        <input type="number" step="1" name="sdma" value="{sdma}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">نسبة البروتين بالبول UPC:</label>
                        <input type="number" step="0.05" name="upc" value="{upc}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">ضغط الدم الانقباضي (mmHg):</label>
                        <input type="number" step="5" name="systolic_bp" value="{systolic_bp}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #059669; border-color: #059669;">🫘 تصنيف المرحلة والعلاج الكلوي</button>
            </form>

            <div style="margin-top: 24px; background: #ecfdf5; border: 2px solid #6ee7b7; border-radius: 12px; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <div style="font-size: 0.9rem; color: #065f46; font-weight: 700;">تصنيف القصور الكلوي المزمن:</div>
                        <div style="font-size: 1.5rem; font-weight: 900; color: #047857; margin: 6px 0;">{stage}</div>
                    </div>
                    <div style="background: #ffffff; border: 1.5px solid #059669; padding: 6px 16px; border-radius: 20px; font-weight: 700; color: #047857;">
                        {bp_status}
                    </div>
                </div>
                <div style="margin-top: 12px; border-top: 1px dashed #a7f3d0; padding-top: 12px; font-size: 0.9rem; line-height: 1.7; color: #064e3b;">
                    <strong>💊 البروتوكول العلاجي المقترح:</strong>
                    الانتقال فوراً لغذاء كلوي علاجي (Renal Diet) منخفض الفوسفور وعالي الجودة في البروتين، إضافة رابط فوسفور معوي (Aluminum hydroxide أو Lanthanum) إذا كان الفوسفور > 4.5 mg/dL، ومحاليل وريدية أو تحت الجلد منتظمة لدعم الترشيح الكبيبي.
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("حاسبة وظائف الكلى IRIS", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 14. POULTRY WATER & VACCINE CONSUMPTION (/tools/poultry-water-calc)
# ==============================================================================
@router.get("/tools/poultry-water-calc", response_class=HTMLResponse)
@router.post("/tools/poultry-water-calc", response_class=HTMLResponse)
async def poultry_water_calc_tool(
    request: Request,
    bird_count: int = 10000,
    age_days: int = 18,
    temp_c: float = 28.0
):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    if request.method == "POST":
        form = await request.form()
        bird_count = int(form.get("bird_count", bird_count))
        age_days = int(form.get("age_days", age_days))
        temp_c = float(form.get("temp_c", temp_c))

    # Daily water rule of thumb: ~ (age_days * 5.2 ml) per bird at 21C
    temp_factor = 1.0 + max(0.0, (temp_c - 21.0) * 0.04)  # +4% per 1C over 21C
    daily_per_bird_ml = (age_days * 5.5) * temp_factor
    total_daily_liters = (bird_count * daily_per_bird_ml) / 1000.0
    # 2-hour vaccine water consumption: roughly 30% of daily total or (total_daily_liters / 7)
    vaccine_water_2h_liters = total_daily_liters * 0.28
    skim_milk_grams = vaccine_water_2h_liters * 2.5  # 2.5 g/L

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #ea580c; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🐔</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #ea580c;">حاسبة مياه شرب وتحصينات قطعان الدواجن (Poultry Water & Vaccine)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">حساب الاستهلاك اليومي الدقيق وكمية مياه التحصين خلال ساعتين مع مثبت اللقاح (لبن الفرز)</p>
                </div>
            </div>

            <form method="POST" action="/tools/poultry-water-calc" style="background: var(--bg); padding: 18px; border-radius: 12px; margin-top: 16px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 16px;">
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">عدد طيور العنبر (Bird Count):</label>
                        <input type="number" step="500" name="bird_count" value="{bird_count}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">عمر الطيور بالأيام (Age in Days):</label>
                        <input type="number" step="1" name="age_days" value="{age_days}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div>
                        <label style="display: block; font-weight: 700; margin-bottom: 5px; font-size: 0.85rem;">درجة حرارة العنبر (°C):</label>
                        <input type="number" step="0.5" name="temp_c" value="{temp_c}" required style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="padding: 10px 24px; font-weight: 700; background: #ea580c; border-color: #ea580c;">🐔 حساب مياه العنبر والتحصين</button>
            </form>

            <div style="margin-top: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
                <div style="background: #fff7ed; border: 1.5px solid #fdba74; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #9a3412; font-weight: 700;">إجمالي استهلاك المياه اليومي (24 ساعة)</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #ea580c; margin: 8px 0;">{total_daily_liters:,.0f} <span style="font-size: 1rem;">لتر/يوم</span></div>
                    <div style="font-size: 0.8rem; color: #9a3412;">(بمعدل {daily_per_bird_ml:.1f} مل لكل طائر)</div>
                </div>

                <div style="background: #eff6ff; border: 1.5px solid #93c5fd; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #1e40af; font-weight: 700;">حجم مياه التحصين الدقيق (ساعتين)</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #2563eb; margin: 8px 0;">{vaccine_water_2h_liters:,.0f} <span style="font-size: 1rem;">لتر</span></div>
                    <div style="font-size: 0.8rem; color: #1e40af;">يستهلك بالكامل خلال ساعتين بعد التعطيش</div>
                </div>

                <div style="background: #f0fdf4; border: 1.5px solid #86efac; padding: 18px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 0.85rem; color: #166534; font-weight: 700;">كمية لبن الفرز المثبت للتحصين</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #16a34a; margin: 8px 0;">{skim_milk_grams:,.0f} <span style="font-size: 1rem;">جرام</span></div>
                    <div style="font-size: 0.8rem; color: #166534;">(2.5 جم/لتر لمعادلة الكلور وحماية الفيروس)</div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("حاسبة مياه الدواجن والتحصينات", body, user, lang), media_type="text/html; charset=utf-8")

# ==============================================================================
# 15. CARDIAC & RESPIRATORY AUSCULTATION GUIDE (/tools/auscultation-guide)
# ==============================================================================
@router.get("/tools/auscultation-guide", response_class=HTMLResponse)
async def auscultation_guide_tool(request: Request):
    from app import get_current_user, get_user_lang, get_base_html
    user = get_current_user(request)
    lang = get_user_lang(request)

    body = f"""
    {get_back_home_bar(lang=lang)}
    <div style="max-width: 900px; margin: 0 auto;">
        <div class="card" style="border-top: 5px solid #0f766e; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 2rem;">🩺</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.45rem; color: #0f766e;">مسرد الأصوات القلبية والتنفسية المرضية (Auscultation Sound Hub)</h1>
                    <p style="margin: 4px 0 0 0; color: var(--text-muted); font-size: 0.88rem;">دليل سريري صوتي وبصري تفاعلي للنفخات القلبية الروماتيزمية وأصوات الحشرجة التنفسية</p>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 20px;">
                <!-- Sound 1: Mitral Regurgitation -->
                <div style="background: #ffffff; border: 1.5px solid var(--border); border-radius: 12px; padding: 18px; box-shadow: var(--shadow);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                        <h3 style="margin: 0; color: #b91c1c; font-size: 1.1rem;">❤️ نفخة ارتجاع الصمام التاجي (Mitral Regurgitation)</h3>
                        <span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">قلبي انقباضي</span>
                    </div>
                    <p style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.6;">
                        نفخة انقباضية شاملة (Holosystolic Murmur) تزداد شدتها عند قمة القلب من الجانب الأيسر. شائعة جداً في الكلاب المسنة (Myxomatous Valve Disease).
                    </p>
                    <button onclick="playSynthesizedSound('heart_mitral')" class="btn btn-outline" style="width: 100%; border-color: #b91c1c; color: #b91c1c; font-weight: 700;">
                        ▶️ محاكاة الصوت السريري (Listen)
                    </button>
                </div>

                <!-- Sound 2: Wet Crackles -->
                <div style="background: #ffffff; border: 1.5px solid var(--border); border-radius: 12px; padding: 18px; box-shadow: var(--shadow);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                        <h3 style="margin: 0; color: #0284c7; font-size: 1.1rem;">🫁 صوت الحشرجة والكركرة الرئوية (Wet Crackles)</h3>
                        <span style="background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">تنفسي شهيقي</span>
                    </div>
                    <p style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.6;">
                        صوت يشبه طقطقة الملح على النار أو فرك خصلات الشعر قرب الأذن. يدل على وجود سوائل وإفرازات سنخية (التهاب رئوي بكتيري أو وذمة رئوية Pulmonary Edema).
                    </p>
                    <button onclick="playSynthesizedSound('lung_crackles')" class="btn btn-outline" style="width: 100%; border-color: #0284c7; color: #0284c7; font-weight: 700;">
                        ▶️ محاكاة الصوت السريري (Listen)
                    </button>
                </div>

                <!-- Sound 3: Wheezes -->
                <div style="background: #ffffff; border: 1.5px solid var(--border); border-radius: 12px; padding: 18px; box-shadow: var(--shadow);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                        <h3 style="margin: 0; color: #ea580c; font-size: 1.1rem;">🫁 التزييق والصفير الزفيري (Wheezes / Heaves)</h3>
                        <span style="background: #ffedd5; color: #c2410c; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">تضيق قصبي</span>
                    </div>
                    <p style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.6;">
                        نغمات موسيقية متصلة تنتج عن مرور الهواء في مجاري تنفسية متضيقة بشدة (ربو القطط Feline Asthma أو حساسية الخيول الشديدة RAO/Heaves).
                    </p>
                    <button onclick="playSynthesizedSound('lung_wheezes')" class="btn btn-outline" style="width: 100%; border-color: #ea580c; color: #ea580c; font-weight: 700;">
                        ▶️ محاكاة الصوت السريري (Listen)
                    </button>
                </div>
            </div>

            <script>
            function playSynthesizedSound(type) {{
                try {{
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    const ctx = new AudioContext();
                    const now = ctx.currentTime;

                    if (type === 'heart_mitral') {{
                        // Lub-whoosh-dub simulation
                        const osc = ctx.createOscillator();
                        const gain = ctx.createGain();
                        osc.frequency.setValueAtTime(65, now);
                        gain.gain.setValueAtTime(0.8, now);
                        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
                        osc.connect(gain);
                        gain.connect(ctx.destination);
                        osc.start(now);
                        osc.stop(now + 0.2);

                        // Whoosh noise
                        const osc2 = ctx.createOscillator();
                        const gain2 = ctx.createGain();
                        osc2.type = 'sawtooth';
                        osc2.frequency.setValueAtTime(140, now + 0.08);
                        gain2.gain.setValueAtTime(0.2, now + 0.08);
                        gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
                        osc2.connect(gain2);
                        gain2.connect(ctx.destination);
                        osc2.start(now + 0.08);
                        osc2.stop(now + 0.38);
                    }} else if (type === 'lung_crackles') {{
                        for (let i = 0; i < 6; i++) {{
                            const osc = ctx.createOscillator();
                            const gain = ctx.createGain();
                            osc.frequency.setValueAtTime(600 + (Math.random() * 400), now + (i * 0.06));
                            gain.gain.setValueAtTime(0.3, now + (i * 0.06));
                            gain.gain.exponentialRampToValueAtTime(0.01, now + (i * 0.06) + 0.02);
                            osc.connect(gain);
                            gain.connect(ctx.destination);
                            osc.start(now + (i * 0.06));
                            osc.stop(now + (i * 0.06) + 0.03);
                        }}
                    }} else if (type === 'lung_wheezes') {{
                        const osc = ctx.createOscillator();
                        const gain = ctx.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(480, now);
                        osc.frequency.exponentialRampToValueAtTime(560, now + 0.4);
                        gain.gain.setValueAtTime(0.25, now);
                        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.6);
                        osc.connect(gain);
                        gain.connect(ctx.destination);
                        osc.start(now);
                        osc.stop(now + 0.65);
                    }}
                }} catch (e) {{
                    alert('مشغل الصوت مدعوم في المتصفحات الحديثة');
                }}
            }}
            </script>
        </div>
    </div>
    """
    return HTMLResponse(content=get_base_html("مسرد الأصوات القلبية والتنفسية", body, user, lang), media_type="text/html; charset=utf-8")
