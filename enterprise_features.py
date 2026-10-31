# -*- coding: utf-8 -*-
"""
VetMind AI - Multilingual 30 Cutting-Edge Enterprise Features Suite
Supports Arabic and Global Languages (English, French, German, Spanish, etc.)
"""
import json
import random
import uuid
from datetime import datetime, date, timedelta

EN_TRANSLATIONS = {
    "cases-gallery": {
        "title": "Live Clinical Cases Photo Gallery",
        "category": "Visual Diagnostics & Triage",
        "desc": "Digital visual archive of all patient cases with zoom, high-res inspection, and triage filtering."
    },
    "prayer-times": {
        "title": "Islamic Prayer Times & Alerts",
        "category": "Daily Clinic Services",
        "desc": "Astronomical solar calculation for 26 Arab cities with live countdown and adhan notification."
    },
    "fluid-therapy": {
        "title": "Fluid Therapy & Drip Rate Calculator",
        "category": "Emergency & Critical Care",
        "desc": "Tripartite fluid balance (Maintenance + Deficit + Ongoing Losses) with drops/min calculation."
    },
    "anesthesia-protocol": {
        "title": "Anesthesia & Sedation Protocol",
        "category": "Surgery & Anesthesia",
        "desc": "Species-specific premedication, induction, endotracheal tube size, and reversal antagonists."
    },
    "toxicology-calc": {
        "title": "Toxicology & Antidote Calculator",
        "category": "Emergency & Critical Care",
        "desc": "Toxicity evaluation for pesticides, rodenticides, paracetamol, and exact antidote dosing."
    },
    "blood-transfusion": {
        "title": "Blood Transfusion & Crossmatch",
        "category": "Emergency & Critical Care",
        "desc": "Required transfusion volume based on recipient PCV, donor PCV, and species crossmatch."
    },
    "microchips": {
        "title": "Electronic Microchip Registry (ISO 11784)",
        "category": "Patient ID & Registry",
        "desc": "Standard 15-digit microchip registration, verification, and barcode identity card generator."
    },
    "surgery-consent": {
        "title": "Surgical & Anesthetic Consent Form",
        "category": "Surgery & Anesthesia",
        "desc": "Printable official bilingual informed surgical consent form for pet owner signature."
    },
    "radiology-hub": {
        "title": "Radiology & Ultrasound Image Hub",
        "category": "Visual Diagnostics",
        "desc": "Interactive X-ray negative inverter, contrast enhancement, and comparative clinical atlas."
    },
    "pain-scale": {
        "title": "Veterinary Pain Scale (Grimace & Glasgow)",
        "category": "Clinical Diagnostics",
        "desc": "Objective pain scoring based on posture, vocalization, mobility, and facial grimace."
    },
    "vaccine-cards": {
        "title": "Vaccine Booster WhatsApp Reminder",
        "category": "Patient Communications",
        "desc": "Automated WhatsApp click-to-chat appointment reminders and printable vaccine passports."
    },
    "gestation-calc": {
        "title": "Gestation & Parturition Calculator",
        "category": "Theriogenology & Reproduction",
        "desc": "Estimated delivery date, dry-off schedule, and pre-partum colostrum vaccination dates."
    },
    "nutrition-calc": {
        "title": "Veterinary Energy Requirement (RER / MER)",
        "category": "Nutrition & Production",
        "desc": "Resting and maintenance energy calculations (kcal/day) and dry matter feeding portions."
    },
    "antimicrobial-audit": {
        "title": "Antimicrobial Stewardship (AWaRe)",
        "category": "Pharmacology & Pharmacy",
        "desc": "WHO & WOAH classification (Access / Watch / Reserve) to curb antimicrobial resistance."
    },
    "icu-vitals": {
        "title": "ICU Vitals Flow Sheet & Monitoring",
        "category": "Emergency & Critical Care",
        "desc": "Real-time tracking of temperature, pulse, respiration, CRT, mucous membrane, and SpO2."
    },
    "bcs-evaluator": {
        "title": "Body Condition Scoring (BCS 1-9 & 1-5)",
        "category": "Nutrition & Production",
        "desc": "Assessment of ribs and fat depots with percentage dietary caloric adjustment."
    },
    "lameness-scoring": {
        "title": "Lameness Locomotion Scorer (AAEP & Sprecher)",
        "category": "Orthopedics & Hoof Care",
        "desc": "Quantitative lameness grading for equines and dairy cattle with corrective hoof blocks."
    },
    "necropsy": {
        "title": "Post-Mortem Necropsy Examination Report",
        "category": "Pathology & Autopsy",
        "desc": "Standardized gross pathology documentation form with tissue sampling instructions."
    },
    "quarantine": {
        "title": "Biosecurity & Epidemic Quarantine Tracker",
        "category": "Biosecurity & Epidemiology",
        "desc": "Isolation unit tracker for FMD, Lumpy Skin, and Parvovirus with disinfection countdowns."
    },
    "electrolyte-correction": {
        "title": "Electrolyte & Potassium Deficit Correction",
        "category": "Emergency & Critical Care",
        "desc": "Sodium deficit calculation and safe maximal IV potassium infusion rate limiters."
    },
    "parasite-fecrt": {
        "title": "FECRT Anthelmintic Resistance Test",
        "category": "Parasitology & Pharmacology",
        "desc": "Fecal Egg Count Reduction Test calculator to detect antiparasitic drug resistance."
    },
    "glucose-curve": {
        "title": "Serial Blood Glucose Curve (Diabetic Care)",
        "category": "Endocrinology & Emergency",
        "desc": "12-hour glucose curve plotting, nadir calculation, and Somogyi rebound alert."
    },
    "bsa-calculator": {
        "title": "Body Surface Area (BSA m²) Oncology Calc",
        "category": "Chemotherapy & Oncology",
        "desc": "Exact BSA (m²) calculations for Vincristine, Doxorubicin, and Carboplatin dosing."
    },
    "cmt-mastitis": {
        "title": "California Mastitis Test (CMT) Evaluator",
        "category": "Milk Quality & Udder Health",
        "desc": "Quarter-by-quarter gel grading, Somatic Cell Count (SCC) estimation, and milk loss."
    },
    "health-certificate": {
        "title": "Official Veterinary Health Travel Certificate",
        "category": "Regulatory & Travel",
        "desc": "Official bilingual health clearance certificate for domestic and international pet travel."
    },
    "renal-calc": {
        "title": "IRIS Chronic Kidney Disease (CKD) Staging",
        "category": "Nephrology & Urology",
        "desc": "Creatinine, SDMA, and proteinuria staging with dietary phosphate binder adjustments."
    },
    "poultry-water-calc": {
        "title": "Poultry Water & Vaccine Consumption",
        "category": "Avian & Poultry",
        "desc": "24h water volume, 2-hour vaccine water consumption, and skim milk stabilizer dosage."
    },
    "auscultation-guide": {
        "title": "Cardiac & Respiratory Auscultation Hub",
        "category": "Cardiopulmonary Audio",
        "desc": "Interactive clinical audio/visual reference for murmurs, wet crackles, and wheezes."
    },
    "repro-kpis": {
        "title": "Herd Reproduction & Fertility KPIs Dashboard",
        "category": "Theriogenology & Dairy",
        "desc": "Heat Detection Rate (HDR), Conception Rate (CR), and Pregnancy Rate (PR) benchmarks."
    },
    "expiry-radar": {
        "title": "Drug Expiry Early Warning Radar",
        "category": "Pharmacy & Inventory",
        "desc": "Automated radar scanning stock expiring within 30, 60, and 90 days to prevent losses."
    }
}

def get_enterprise_tools_index(user_country: str = "مصر", lang: str = "ar") -> list:
    """
    Returns metadata for all 30 enterprise features localized according to user language.
    """
    tools = [
        # Suite 1: Visual Diagnostics & Clinical Access
        {
            "id": "cases-gallery",
            "title": "معرض صور الحالات السريرية المباشر",
            "icon": "🖼️",
            "category": "الفحص البصري والتشخيص",
            "url": "/clinic/cases-gallery",
            "desc": "أرشيف بصري رقمي لكافة صور الحالات المسجلة مع إمكانية الفحص والتكبير والتصنيف حسب الفصيلة ودرجة الخطورة."
        },
        {
            "id": "prayer-times",
            "title": "مواقيت الصلاة والتنبيهات المباشرة",
            "icon": "🕌",
            "category": "الخدمات اليومية للعيادة",
            "url": "/clinic/prayer-times",
            "desc": "حساب فلكي دقيق لمواقيت الصلاة لكافة المدن العربية مع عداد تنازلي للصلاة القادمة وتنبيهات الأذان."
        },
        {
            "id": "fluid-therapy",
            "title": "حاسبة المحاليل الوريدية ومعدل التنقيط",
            "icon": "💧",
            "category": "العناية المركزة والطوارئ",
            "url": "/tools/fluid-therapy",
            "desc": "حساب احتياج السوائل (صيانة + جفاف + فاقد مستمر) ومعدل التنقيط بالقطرة/دقيقة للمحاليل الوريدية."
        },
        {
            "id": "anesthesia-protocol",
            "title": "بروتوكول التخدير والمهدئات المخصص",
            "icon": "💉",
            "category": "الجراحة والتخدير",
            "url": "/tools/anesthesia-protocol",
            "desc": "جرعات التسكين والتنويم والإنعاش التخديري المخصصة حسب وزن الحيوان وفصيلته (خيول، أبقار، كلاب، قطط)."
        },
        {
            "id": "toxicology-calc",
            "title": "حاسبة السموم والجرعات القاتلة ومضاداتها",
            "icon": "🧪",
            "category": "العناية المركزة والطوارئ",
            "url": "/tools/toxicology-calc",
            "desc": "تقييم درجة خطورة ابتلاع المبيدات، الشوكولاتة، السموم القاتلة، وحساب جرعات الترياق (Antidote)."
        },
        {
            "id": "blood-transfusion",
            "title": "حاسبة نقل الدم والتوافق الفصائلي",
            "icon": "🩸",
            "category": "العناية المركزة والطوارئ",
            "url": "/tools/blood-transfusion",
            "desc": "حجم الدم المطلوب نقله بناءً على الهيماتوكريت (PCV) ودليل التوافق المناعي للفصائل الحيوانية."
        },
        {
            "id": "microchips",
            "title": "سجل ومولد باركود الرقائق الإلكترونية (Microchip)",
            "icon": "🏷️",
            "category": "إدارة المرضى والهوية",
            "url": "/clinic/microchips",
            "desc": "تسجيل وفحص أرقام الميكروتشيب القياسية (15 رقماً) وإصدار بطاقة الهوية البيطرية الرسمية."
        },
        {
            "id": "surgery-consent",
            "title": "مولد إقرارات العمليات والموافقة المستنيرة",
            "icon": "📝",
            "category": "الجراحة والتخدير",
            "url": "/clinic/surgery-consent",
            "desc": "توليد وطباعة وثيقة إقرار جراحي وتخديري رسمي معتمدة لتوقيع مالك الحيوان لحماية العيادة قانونياً."
        },
        {
            "id": "radiology-hub",
            "title": "أرشيف ومقارنة السونار والأشعة السينية",
            "icon": "🩻",
            "category": "الفحص البصري والتشخيص",
            "url": "/clinic/radiology-hub",
            "desc": "حفظ ومقارنة صور الأشعة التشخيصية وتقارير السونار والـ X-Ray لكل مريض بيطري."
        },
        {
            "id": "pain-scale",
            "title": "أداة تقييم الألم السريري (Grimace & Glasgow)",
            "icon": "😣",
            "category": "الفحص البصري والتشخيص",
            "url": "/tools/pain-scale",
            "desc": "مقياس درجات الألم للخيول والحيوانات الأليفة عبر تعابير الوجه واقتراح البروتوكول المسكن المناسب."
        },
        {
            "id": "vaccine-cards",
            "title": "نظام كروت تذكير التطعيمات عبر واتساب",
            "icon": "📲",
            "category": "إدارة المرضى والهوية",
            "url": "/clinic/vaccine-cards",
            "desc": "توليد رسائل تذكير تلقائية بروابط واتساب مباشرة بضغطة زر لإبلاغ المربي بموعد الجرعة المنشطة."
        },
        {
            "id": "gestation-calc",
            "title": "حاسبة الحمل وموعد الولادة المتوقع",
            "icon": "🤰",
            "category": "التناسل والولادة",
            "url": "/tools/gestation-calc",
            "desc": "تحديد موعد الولادة المتوقع وتاريخ التجفيف والتطعيمات الإلزامية للأبقار، الإبل، الخيول، والأغنام."
        },
        {
            "id": "nutrition-calc",
            "title": "حاسبة الاحتياج الطاقي والتغذوي (RER / MER)",
            "icon": "🥩",
            "category": "التغذية والإنتاج",
            "url": "/tools/nutrition-calc",
            "desc": "حساب السعرات الحرارية والاحتياج الغذائي اليومي لحالات النقاهة، الرضاعة، والتسمين."
        },
        {
            "id": "antimicrobial-audit",
            "title": "فاحص ترشيد استخدام المضادات الحيوية (Stewardship)",
            "icon": "🛡️",
            "category": "الصيدلة والأدوية",
            "url": "/clinic/antimicrobial-audit",
            "desc": "تدقيق تصنيف المضادات الحيوية (Access / Watch / Reserve) وفق منظمة الصحة العالمية والـ WOAH."
        },
        {
            "id": "icu-vitals",
            "title": "مخطط متابعة العلامات الحيوية بالعناية المركزة",
            "icon": "📈",
            "category": "العناية المركزة والطوارئ",
            "url": "/clinic/icu-vitals",
            "desc": "تسجيل ورسم منحنى الحرارة، النبض، التنفس، زمن امتلاء الشعيرات (CRT)، ولون الأغشية المخاطية."
        },
        {
            "id": "bcs-evaluator",
            "title": "مقيم الحالة الجسدية للحيوان (BCS 1-9 & 1-5)",
            "icon": "⚖️",
            "category": "التغذية والإنتاج",
            "url": "/tools/bcs-evaluator",
            "desc": "تقييم امتلاء العضلات والدهن على الأضلاع والعمود الفقري مع نسبة التصحيح الغذائي المطلوبة."
        },
        {
            "id": "lameness-scoring",
            "title": "دليل فحص العرج الموضعي للخيول والأبقار",
            "icon": "🐎",
            "category": "الفحص البصري والتشخيص",
            "url": "/tools/lameness-scoring",
            "desc": "مقياس العرج الحركي المعتمد عالمياً (AAEP & Sprecher) مع خريطة تشريحية لحوافر الحيوان."
        },
        {
            "id": "necropsy",
            "title": "قالب تقرير الصفة التشريحية (Necropsy Report)",
            "icon": "🔬",
            "category": "الفحص البصري والتشخيص",
            "url": "/clinic/necropsy",
            "desc": "استمارة تشريح بيطري احترافية لتوثيق الآفات العيانية للأعضاء الداخلية والاشتباه الوبائي."
        },
        {
            "id": "quarantine",
            "title": "نظام تتبع وإدارة عزل الحالات الوبائية",
            "icon": "☣️",
            "category": "الأمن الحيوي والوبائيات",
            "url": "/clinic/quarantine",
            "desc": "سجل عنابر الحجر الصحي والعزل المشدد للحمى القلاعية والجلد العقدي مع مدة العزل المتبقية."
        },
        {
            "id": "electrolyte-correction",
            "title": "حاسبة تصحيح الشوارد ونقص الصوديوم والبوتاسيوم",
            "icon": "⚡",
            "category": "العناية المركزة والطوارئ",
            "url": "/tools/electrolyte-correction",
            "desc": "حساب نقص الصوديوم والحد الأقصى لسرعة تسريب البوتاسيوم لمنع التوقف القلبي الفجائي."
        },
        {
            "id": "parasite-fecrt",
            "title": "فاحص مقاومة مضادات الديدان (FECRT Test)",
            "icon": "🪱",
            "category": "الصيدلة والأدوية",
            "url": "/clinic/parasite-fecrt",
            "desc": "حساب كفاءة طرد الديدان واكتشاف المقاومة الدوائية عبر مقارنة عدد البيوض قبل وبعد التجريع."
        },
        {
            "id": "glucose-curve",
            "title": "مخطط منحنى السكر والسيطرة على داء السكري",
            "icon": "📊",
            "category": "العناية المركزة والطوارئ",
            "url": "/clinic/glucose-curve",
            "desc": "رسم منحنى قياس سكر الدم التسلسلي كل ساعتين لتحديد قاع السكر وتعديل جرعة الأنسولين."
        },
        {
            "id": "bsa-calculator",
            "title": "حاسبة مساحة سطح الجسم لعلاج الأورام (BSA)",
            "icon": "📐",
            "category": "الجراحة والتخدير",
            "url": "/tools/bsa-calculator",
            "desc": "حساب مساحة الجسم بالمتر المربع (m²) لضبط الجرعات الدقيقة لبروتوكولات أدوية الأورام."
        },
        {
            "id": "cmt-mastitis",
            "title": "دليل فحص كاليفورنيا لالتهاب الضرع الخفي (CMT)",
            "icon": "🥛",
            "category": "التناسل والولادة",
            "url": "/tools/cmt-mastitis",
            "desc": "تقييم تخثر عينات الحليب لأرباع الضرع الأربعة وتقدير عدد الخلايا الجسدية (SCC)."
        },
        {
            "id": "health-certificate",
            "title": "شهادة صحية بيطرية رسمية لنقل وسفر الحيوان",
            "icon": "✈️",
            "category": "إدارة المرضى والهوية",
            "url": "/clinic/health-certificate",
            "desc": "إصدار وطباعة شهادة خلو من الأمراض الوبائية صالحة للنقل الداخلي والسفر الدولي."
        },
        {
            "id": "renal-calc",
            "title": "حاسبة وظائف الكلى ومعدل الترشيح (IRIS Stage)",
            "icon": "🫘",
            "category": "العناية المركزة والطوارئ",
            "url": "/tools/renal-calc",
            "desc": "تصنيف القصور الكلوي المزمن (IRIS 1-4) وتحديد متطلبات تخفيض الفوسفور والبروتين."
        },
        {
            "id": "poultry-water-calc",
            "title": "حاسبة مياه شرب وتحصينات قطعان الدواجن",
            "icon": "🐔",
            "category": "التغذية والإنتاج",
            "url": "/tools/poultry-water-calc",
            "desc": "حساب كمية المياه الدقيقة اللازمة لاستهلاك اللقاح خلال ساعتين بناءً على العمر والحرارة."
        },
        {
            "id": "auscultation-guide",
            "title": "مسرد الأصوات القلبية والتنفسية المرضية",
            "icon": "🩺",
            "category": "الفحص البصري والتشخيص",
            "url": "/tools/auscultation-guide",
            "desc": "دليل إكلينيكي للنفخات القلبية الروماتيزمية وأصوات الحشرجة التنفسية (Crackles & Wheezes)."
        },
        {
            "id": "repro-kpis",
            "title": "لوحة مؤشرات الخصوبة والتلقيح للقطعان",
            "icon": "🐄",
            "category": "التناسل والولادة",
            "url": "/clinic/repro-kpis",
            "desc": "حساب معدل الحمل (Pregnancy Rate)، أيام الجفاف، وعدد التلقيحات اللازمة للإخصاب."
        },
        {
            "id": "expiry-radar",
            "title": "رادار التنبيه المبكر لانتهاء صلاحية الأدوية",
            "icon": "🚨",
            "category": "الصيدلة والأدوية",
            "url": "/clinic/expiry-radar",
            "desc": "رادار ذكي يفرز الأدوية المشرفة على انتهاء الصلاحية خلال 30 و 60 و 90 يوماً لمنع الخسائر."
        }
    ]

    clean_lang = (lang or "ar").strip().lower()
    if clean_lang != "ar" and clean_lang in ["en", "fr", "de", "es", "it", "zh", "ja"]:
        for t in tools:
            tid = t["id"]
            if tid in EN_TRANSLATIONS:
                t["title"] = EN_TRANSLATIONS[tid]["title"]
                t["category"] = EN_TRANSLATIONS[tid]["category"]
                t["desc"] = EN_TRANSLATIONS[tid]["desc"]

    return tools
