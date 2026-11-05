# -*- coding: utf-8 -*-
"""
VetMind AI - Comprehensive Veterinary Symptom-Based Diagnostician Engine
(المشخص البيطري الذكي بناءً على الأعراض والخصائص السريرية)

Provides differential diagnoses, calculated dosages by weight, contraindication filters,
and confirmatory laboratory markers based on species, age, temperature, weight, and clinical signs.
Works 100% offline via local rule-based diagnostic matrix, with AI enhancement when online.
"""

from typing import Dict, List, Any, Optional

# Standard Physiological Body Temperatures for Domestic & Farm Species
SPECIES_PHYSIOLOGY = {
    "أبقار": {"temp_min": 38.0, "temp_max": 39.3, "fever_mild": 39.5, "fever_high": 40.5, "pulse": "60-80", "resp": "15-30"},
    "أغنام وماعز": {"temp_min": 38.5, "temp_max": 40.0, "fever_mild": 40.2, "fever_high": 41.0, "pulse": "70-90", "resp": "15-30"},
    "إبل وهجن": {"temp_min": 36.5, "temp_max": 38.5, "fever_mild": 38.8, "fever_high": 39.5, "pulse": "35-50", "resp": "8-18"},
    "خيول": {"temp_min": 37.5, "temp_max": 38.5, "fever_mild": 38.8, "fever_high": 39.8, "pulse": "28-44", "resp": "8-16"},
    "دواجن وطيور": {"temp_min": 40.5, "temp_max": 42.0, "fever_mild": 42.5, "fever_high": 43.5, "pulse": "250-300", "resp": "20-40"},
    "كلاب": {"temp_min": 38.0, "temp_max": 39.2, "fever_mild": 39.4, "fever_high": 40.2, "pulse": "70-120", "resp": "18-34"},
    "قطط": {"temp_min": 38.0, "temp_max": 39.2, "fever_mild": 39.4, "fever_high": 40.5, "pulse": "120-140", "resp": "20-40"},
    "أرانب": {"temp_min": 38.5, "temp_max": 40.0, "fever_mild": 40.3, "fever_high": 41.0, "pulse": "130-325", "resp": "30-60"}
}

def evaluate_temperature_status(species: str, temp_c: float) -> Dict[str, Any]:
    """Evaluate body temperature relative to species physiological norms."""
    phys = SPECIES_PHYSIOLOGY.get(species, {"temp_min": 38.0, "temp_max": 39.5, "fever_mild": 39.8, "fever_high": 40.8})
    
    if temp_c < (phys["temp_min"] - 0.5):
        return {
            "status": "hypothermia",
            "label": "هبوط حرارة خطير (Hypothermia) ❄️",
            "color": "#0284c7",
            "alert": "الحيوان في حالة صدمة أو تسمم داخلي متقدم أو نزف داخلي أو استلقاء طويل. يتطلب تدفئة ومحاليل دافئة فوراً.",
            "norm_text": f"المعدل الطبيعي لفصيلة {species}: {phys['temp_min']} - {phys['temp_max']} °C"
        }
    elif temp_c <= phys["temp_max"]:
        return {
            "status": "normal",
            "label": "حرارة طبيعية فسيولوجية ✅",
            "color": "#16a34a",
            "alert": "درجة الحرارة تقع ضمن النطاق الفسيولوجي المعتدل للحيوان.",
            "norm_text": f"المعدل الطبيعي: {phys['temp_min']} - {phys['temp_max']} °C"
        }
    elif temp_c < phys["fever_high"]:
        return {
            "status": "mild_fever",
            "label": "حمى متوسطة / ارتفاع حرارة (Mild Fever) 🌡️",
            "color": "#ea580c",
            "alert": "وجود رد فعل مناعي والتهاب نشط أو عدوى بكتيرية / فيروسية في بدايتها.",
            "norm_text": f"المعدل الطبيعي: {phys['temp_min']} - {phys['temp_max']} °C"
        }
    else:
        return {
            "status": "high_fever",
            "label": "حمى حادة وشديدة الخطورة (High Fever / Hyperthermia) 🔥",
            "color": "#dc2626",
            "alert": "ارتفاع حرارة خطير يهدد حياة الحيوان ويشير لتسمم دموي حاد، طفيليات دم ميكروبية، أو عدوى فيروسية حادة.",
            "norm_text": f"المعدل الطبيعي: {phys['temp_min']} - {phys['temp_max']} °C"
        }


# Comprehensive Diagnostic Database by Species and Clinical Syndromes
DIAGNOSTIC_KNOWLEDGE_BASE = [
    # ------------------ CATTLE / BOVINE ------------------
    {
        "id": "bov_fmd",
        "species": ["أبقار", "أغنام وماعز"],
        "name_ar": "مرض الحمى القلاعية (Foot and Mouth Disease - FMD)",
        "name_en": "Foot and Mouth Disease (FMD)",
        "etiology": "Aphtovirus (Picornaviridae) - فيروسي حاد شديد السراية",
        "key_signs": ["حويصلات فموية", "لعاب غزير", "تقرحات حوافر", "عرج", "حمى"],
        "symptoms_keywords": ["لعاب", "فم", "حوافر", "عرج", "حمى", "حرارة", "حويصلات", "تقرحات", "ريالة"],
        "temp_criteria": "high_fever",
        "age_groups": ["رضيع", "مفطوم", "بالغ", "مسن"],
        "mortality_young": "مرتفعة في العجول الرضيعة (التهاب عضلة القلب النمري Tiger Heart)",
        "differential_diagnoses": ["التهاب الفم الحويصلي (VS)", "طاعون المجترات الصغيرة (PPR)", "التهاب الأنف والحنجرة البقري المعدي (IBR)"],
        "confirmatory_tests": "مسحة من سائل الحويصلات غير المنفجرة، فحص RT-PCR وفحص الأليزا ELISA للتنميط المصلي (O, A, SAT).",
        "treatment_protocol": [
            {"drug": "مضاد حيوي واسع: أموكسيسيلين + كلافولانيك أو أوكسيتتراسيكلين طويل المفعول", "dose_formula": "1 ml / 10 kg IM", "target": "منع العدوى البكتيرية الثانوية ومضاعفات تقرحات الحوافر"},
            {"drug": "مضاد التهاب وخافض حرارة: فلونيكسين ميغلومين (Flunixin Meglumine)", "dose_formula": "2.2 mg/kg (2 ml / 45 kg IV/IM)", "target": "خفض الحرارة وتسكين آلام الحوافر والفم الحادة"},
            {"drug": "مطهر فموي موضعي: محلول حمض البوريك 2% أو جلسرين مع يود خفيف", "dose_formula": "غسيل فموي موضعي مرتين يومياً", "target": "تسريع التئام تقرحات اللسان واللثة"},
            {"drug": "بخاخ موضعي للحوافر: سلفا وأوكسيتتراسيكلين سبراي (CTC spray)", "dose_formula": "رش موضعي على شق الحوافر بعد التنظيف الجاف", "target": "حماية الحوافر من التعفن البكتيري"}
        ],
        "warnings": "عزل الحيوان فوراً وإبلاغ السلطات البيطرية الرسمية. منع حركة المزرعة. إعطاء غذاء طري ناعم (دريس ناعم مسلوق أو علف رطب).",
        "pregnancy_safe": True
    },
    {
        "id": "bov_pasteurellosis",
        "species": ["أبقار", "أغنام وماعز", "إبل وهجن"],
        "name_ar": "التسمم الدموي النزفي والتهاب الرئة الباستريلي (Pasteurellosis / Hemorrhagic Septicemia)",
        "name_en": "Hemorrhagic Septicemia / Bovine Respiratory Disease",
        "etiology": "Pasteurella multocida / Mannheimia haemolytica (بكتيريا سلبية الغرام)",
        "key_signs": ["صعوبة تنفس", "وذمة حلقية", "إفرازات أنفية", "حمى حادة", "نهجان"],
        "symptoms_keywords": ["تنفس", "سعال", "نهجان", "صدر", "إفرازات", "حلق", "ورم", "حمى", "حرارة", "خمول", "أنين"],
        "temp_criteria": "high_fever",
        "age_groups": ["رضيع", "مفطوم", "بالغ", "مسن"],
        "mortality_young": "شديدة السرعة في غضون 24-48 ساعة إذا لم يُعالج مبكراً",
        "differential_diagnoses": ["الالتهاب الرئوي البلوري المعدي (CBPP)", "حمى النقل (Shipping Fever)", "داء الجمرة الخبيثة (Anthrax)"],
        "confirmatory_tests": "أخذ دم وريدي أو رشافة نسيجية من الوذمة لفحص المسحات بصبغة غرام، وزرع معزول Pasteurella.",
        "treatment_protocol": [
            {"drug": "المضاد النوعي: فلورفينيكول 300 مجم/مل (Florfenicol)", "dose_formula": "20 مجم/كجم (1 مل لكل 15 كجم عضل كل 48 ساعة) أو 40 مجم/كجم تحت الجلد جرعة واحدة", "target": "القضاء الفوري على الباستريلا الحادة"},
            {"drug": "أو تولاثروميسين (Tulathromycin) أو سيفينوكول / سفتيوفور (Ceftiofur)", "dose_formula": "1 مل لكل 50 كجم تحت الجلد أو عضل", "target": "بديل ممتاز آمن وخاصة في الحيوانات الحلوبة"},
            {"drug": "مضاد التهاب ومسكن: كيتوبروفين (Ketoprofen) أو ميلوكسيكام (Meloxicam)", "dose_formula": "3 مجم/كجم (3 مل / 100 كجم)", "target": "تخفيف الوذمة الحلقية والالتهاب الرئوي الصدري"},
            {"drug": "محلول ملحي وريدي + دكستروز 5% + فيتامين C", "dose_formula": "10-20 مل/كجم وريدياً ببطء", "target": "علاج التسمم الدموي والجفاف"}
        ],
        "warnings": "العلاج فوري قبل حدوث الاختناق التنفسي. تحذير: عدم إجهاد الحيوان أو تحريكه لمسافات طويلة.",
        "pregnancy_safe": True
    },
    {
        "id": "bov_theileriosis",
        "species": ["أبقار"],
        "name_ar": "داء الثايليريا وحمى الساحل الشرقي (Bovine Theileriosis / East Coast Fever)",
        "name_en": "Bovine Theileriosis (Theileria annulata / parva)",
        "etiology": "Theileria annulata / Theileria parva (طفيليات دم منقولة بالقراد)",
        "key_signs": ["تضخم الغدد الليمفاوية", "حمى شديدة", "شحوب", "اصفرار", "إفرازات دمعية"],
        "symptoms_keywords": ["غدد", "ليمفاوية", "حمى", "حرارة", "دم", "شحوب", "اصفرار", "يرقان", "قراد", "دمع", "عيون"],
        "temp_criteria": "high_fever",
        "age_groups": ["مفطوم", "بالغ", "مسن"],
        "mortality_young": "عالية في السلالات المستوردة والهجينة",
        "differential_diagnoses": ["البابيزيا (Babesiosis)", "الأنابلازما (Anaplasmosis)", "التريبانوسوما (Trypanosomiasis)"],
        "confirmatory_tests": "فحص شريحة دم رقيقة أو لطخة من سائل العقد الليمفاوية المرتشحة بصبغة غيمزا (أجسام كوخ الزرقاء Koch's Blue Bodies).",
        "treatment_protocol": [
            {"drug": "العقار النوعي الأول: بوبارفكون (Buparvaquone)", "dose_formula": "2.5 مجم/كجم (1 مل لكل 20 كجم في عضلات الرقبة عميقاً)", "target": "القضاء على طفيليات الثايليريا وانقسامها داخل الخلايا"},
            {"drug": "أوكسيتتراسيكلين طويل المفعول 20% (Oxytetracycline LA)", "dose_formula": "20 مجم/كجم (1 مل / 10 كجم عضل)", "target": "تثبيط العدوى المتزامنة والمضاعفات"},
            {"drug": "مضاد التهاب ومسكن: فلونيكسين ميغلومين", "dose_formula": "2.2 مجم/كجم وريدياً أو عضل", "target": "خفض الحمى الشديدة وتخفيف الاحتقان"},
            {"drug": "منشط كبد وحديد وفيتامين B12 + فوسفور (Catosal / Butaphosphan)", "dose_formula": "10-20 مل عضل أو وريد", "target": "تسريع تعويض كرات الدم الحمراء ومكافحة الأنيميا"}
        ],
        "warnings": "مكافحة حشرة القراد بمضادات الطفيليات الخارجية (Deltamethrin pour-on). تكرار البوبارفكون بعد 48 ساعة للحالات الشديدة.",
        "pregnancy_safe": True
    },
    {
        "id": "bov_babesiosis",
        "species": ["أبقار", "خيول", "أغنام وماعز", "كلاب"],
        "name_ar": "داء البابيزيا / حمى المياه الحمراء (Babesiosis / Red Water Disease)",
        "name_en": "Babesiosis (Tick Fever / Redwater)",
        "etiology": "Babesia bovis / Babesia bigemina (طفيليات دم أولية بداخل كرات الدم الحمراء)",
        "key_signs": ["بول مدمم أحمر داكن", "حمى شديدة", "شحوب حاد", "يرقان واصفرار", "تسارع قلب"],
        "symptoms_keywords": ["بول", "أحمر", "مدمم", "دم", "حمى", "حرارة", "شحوب", "اصفرار", "يرقان", "نهجان", "قلب"],
        "temp_criteria": "high_fever",
        "age_groups": ["مفطوم", "بالغ", "مسن"],
        "mortality_young": "الحيوانات البالغة أكثر حساسية وخطورة من العجول الصغيرة",
        "differential_diagnoses": ["البيلة الهيموغلوبينية النفاسية", "تسمم نحاس", "داء اللولبيات النحيفة (Leptospirosis)"],
        "confirmatory_tests": "فحص مسحة دم محيطية ملونة بغيمزا Giemsa لمشاهدة الميروزويتات المزدوجة الكمثرية داخل كرات الدم.",
        "treatment_protocol": [
            {"drug": "العقار النوعي الأول: إيميدوكارب ديبروبيونات (Imidocarb dipropionate)", "dose_formula": "1.2 مجم/كجم (1 مل لكل 100 كجم تحت الجلد أو عضل)", "target": "تدمير طفيل البابيزيا النوعي"},
            {"drug": "أو ديمينازين أستورات (Diminazene aceturate / Beneril)", "dose_formula": "3.5 مجم/كجم (1 قمع مذاب لكل 200-300 كجم عضل عميق)", "target": "العلاج الكلاسيكي الفعال المضاد للبابيزيا والتريبانوسوما"},
            {"drug": "خافض حرارة: دايبيرون (Analgin) أو كيتوبروفين", "dose_formula": "1 مل لكل 20 كجم عضل", "target": "السيطرة الفورية على نوبة الحمى الشديدة"},
            {"drug": "فيتامين B12 وحديد وسوائل وريدية بطيئة", "dose_formula": "10-25 مل", "target": "إنقاذ الكلى من ترسب الهيموغلوبين وتعويض فقر الدم"}
        ],
        "warnings": "تحذير: لا تكرر الإيميدوكارب قبل 14 يوماً لتجنب السمية الكبدية. تجنب نقل الدم السريع للحيوان دون توافق.",
        "pregnancy_safe": False
    },
    {
        "id": "bov_lumpy_skin",
        "species": ["أبقار"],
        "name_ar": "مرض التهاب الجلد العقدي (Lumpy Skin Disease - LSD)",
        "name_en": "Lumpy Skin Disease (LSD)",
        "etiology": "Capripoxvirus (Poxviridae) - ينقله البعوض والذباب الماص للدماء",
        "key_signs": ["عقد جلدية صلبة بارزة", "حمى", "وذمة القوائم واللبب", "انخفاض الحليب", "إفرازات عينية وأنفية"],
        "symptoms_keywords": ["عقد", "جلد", "حبيبات", "ورم", "حمى", "حرارة", "قوائم", "حليب", "دمامل", "قرص"],
        "temp_criteria": "high_fever",
        "age_groups": ["رضيع", "مفطوم", "بالغ", "مسن"],
        "mortality_young": "قد تسبب تلفاً للجلد وهزالاً شديداً ونفوق العجول",
        "differential_diagnoses": ["الجدري الكاذب (Pseudocowpox)", "التهاب الجلد والتحسس الحشري", "السل الجلدي (Cutaneous TB)"],
        "confirmatory_tests": "خزعة نسيجية من العقدة الجلدية أو مسحة PCR للتأكد من فيروس الكابريبوكس.",
        "treatment_protocol": [
            {"drug": "مضاد حيوي واسع: أوكسيتتراسيكلين طويل المفعول 20% أو بنسلين-ستربتومايسين", "dose_formula": "1 مل / 10 كجم عضل كل 48-72 ساعة", "target": "منع العدوى البكتيرية الصديدية الثانوية بالعقد والجلد"},
            {"drug": "مضاد التهاب غير ستيرويدي: فلونيكسين ميغلومين أو كيتوبروفين", "dose_formula": "2.2 مجم/كجم عضل لمدة 3 أيام متتالية", "target": "علاج وذمة القوائم واللبب وخفض الحرارة"},
            {"drug": "مضاد حساسية ومضاد هيستامين (Chlorpheniramine maleate)", "dose_formula": "10-15 مل عضل", "target": "تخفيف الحكة والوذمة النسيجية"},
            {"drug": "رش مطهر موضعي + طارد حشرات على العقد المتقرحة", "dose_formula": "مرتين يومياً", "target": "منع هجوم يرقات الذباب (التدويد Myiasis)"}
        ],
        "warnings": "عزل الحيوان واستخدام الناموسيات ورش الحظائر بمبيدات الدلتامثرين. التطعيم بلقاح الجدري في المواسم الوقائية.",
        "pregnancy_safe": True
    },
    {
        "id": "bov_ketosis",
        "species": ["أبقار", "أغنام وماعز"],
        "name_ar": "خلون الدم وحمى الأسيتون / تسمم الحمل (Bovine Ketosis / Pregnancy Toxemia)",
        "name_en": "Bovine Ketosis / Ovine Pregnancy Toxemia",
        "etiology": "اضطراب أيضي ناتج عن نقص توازن الطاقة السلبي (Negative Energy Balance)",
        "key_signs": ["رائحة أسيتون بالزفير والحليب", "انخفاض حاد في الحليب والشهية", "لعق الجدران وترنح", "فقدان وزن سريع"],
        "symptoms_keywords": ["أسيتون", "حليب", "شهية", "هزال", "ترنح", "عشار", "حمل", "ولادة", "طاقة", "كرش"],
        "temp_criteria": "normal",
        "age_groups": ["بالغ"],
        "mortality_young": "لا ينطبق (يصيب الإناث البالغات بعد الولادة أو في أواخر الحمل)",
        "differential_diagnoses": ["حمى اللبن (نقص كالسيوم)", "انزياح المنفحة (LDA)", "التهاب الشبكية والصفاق الوخزي (TRP)"],
        "confirmatory_tests": "اختبار شرائط فحص الكيتون في البول أو الحليب (Rothera's Test)، أو قياس بيتا-هيدروكسي بيوتيرات BHBA في الدم.",
        "treatment_protocol": [
            {"drug": "محلول جلوكوز دكستروز 50% عالي التركيز (Dextrose 50%)", "dose_formula": "500 مل وريدياً ببطء شديد", "target": "إمداد فوري سريع بالجلوكوز لسد العجز الكبدي"},
            {"drug": "بروبيلين جليكول (Propylene Glycol) عن طريق الفم", "dose_formula": "250-400 مل بالفم مرتين يومياً لمدة 3-5 أيام", "target": "توليد الجلوكوز الطبيعي عبر الكبد"},
            {"drug": "كورتيكوستيرويد: ديكساميثازون (لغير الحوامل فقط) أو إيزوفلوبيدون", "dose_formula": "10-20 مجم عضل جرعة واحدة", "target": "تحفيز تكوين السكر بالجسم وتحسين التمثيل الغذائي"},
            {"drug": "فيتامين B12 مع فوسفور ومحفزات الكبد (Catosal)", "dose_formula": "20-25 مل وريد أو عضل", "target": "تنشيط خلايا الكبد والتخلص من الدهون"}
        ],
        "warnings": "تحذير حرج: يُمنع إعطاء الديكساميثازون للحيوانات الحامل لأنه يسبب الإجهاض الفوري! يُستبدل بفيتامينات وكالسيوم.",
        "pregnancy_safe": False
    },
    {
        "id": "bov_milk_fever",
        "species": ["أبقار", "أغنام وماعز"],
        "name_ar": "حمى اللبن ونقص كالسيوم الدم الحاد (Milk Fever / Hypocalcemia)",
        "name_en": "Parturient Paresis (Milk Fever)",
        "etiology": "نقص حاد في مستوى الكالسيوم المتأين في الدم عقب بدء إنتاج الحليب واللبأ",
        "key_signs": ["عدم القدرة على الوقوف (Downer cow)", "برودة الأطراف والأذنين", "التواء الرقبة على الخاصرة في وضع S", "توقف حركة الكرش والإخراج"],
        "symptoms_keywords": ["استلقاء", "ربوض", "شلل", "وقوف", "برودة", "أذن", "رقبة", "ولادة", "حليب", "كالسيوم"],
        "temp_criteria": "hypothermia",
        "age_groups": ["بالغ"],
        "mortality_young": "لا ينطبق (يصيب الأبقار عالية الإدرار في الولادة الثالثة فأكثر)",
        "differential_diagnoses": ["تسمم بكتيري حاد من التهاب ضرع غنغريني", "كسر في عظام الحوض", "نقص ماغنسيوم الدم (الكزاز Grass Tetany)"],
        "confirmatory_tests": "استجابة دراماتيكية فورية للحقن الوريدي بمحلول الكالسيوم بوروجلوكونات خلال دقائق معدودة.",
        "treatment_protocol": [
            {"drug": "محلول كالسيوم بوروجلوكونات 23-40% مع ماغنسيوم وفوسفور (Cal-Borogluconate)", "dose_formula": "500 مل (يُعطى نصفها وريدياً ببطء شديد مع مراقبة ضربات القلب والنصف الآخر تحت الجلد)", "target": "إعادة مستوى الكالسيوم المصل فسيولوجياً"},
            {"drug": "جيل كالسيوم فموي (Calcium Bolus / Oral Gel)", "dose_formula": "جرعة واحدة بعد استعادة البقرة لوقوفها، وجرعة ثانية بعد 12 ساعة", "target": "منع انتكاس هبوط الكالسيوم"},
            {"drug": "مضاد التهاب ومسكن: ميلوكسيكام أو فلونيكسين", "dose_formula": "الجرعة القياسية", "target": "تخفيف تلف العضلات الناتج عن الربوض الطويل"}
        ],
        "warnings": "خطر داهم: يجب حقن الكالسيوم وريدياً ببطء شديد (على مدار 15-20 دقيقة) مع الاستماع لضربات القلب؛ الحقن السريع يسبب توقف القلب الانقباضي والموت الفوري!",
        "pregnancy_safe": True
    },

    # ------------------ SHEEP & GOATS ------------------
    {
        "id": "ovi_enterotoxemia",
        "species": ["أغنام وماعز", "أبقار"],
        "name_ar": "التسمم المعوي / الكلوة الرخوة (Enterotoxemia / Pulpy Kidney Disease)",
        "name_en": "Clostridial Enterotoxemia (Pulpy Kidney)",
        "etiology": "Clostridium perfringens type D (سموم بكتيرية لا هوائية تفرز إبسيلون توكسين)",
        "key_signs": ["موت مفاجئ لأفضل الأوزان", "تشنجات ورجوع الرأس للخلف", "إسهال داكن", "طحن الأسنان وغيبوبة"],
        "symptoms_keywords": ["موت", "مفاجئ", "تشنج", "صرع", "رقبة", "كلوة", "تسمم", "معوي", "علف", "إسهال", "طحن"],
        "temp_criteria": "normal",
        "age_groups": ["رضيع", "مفطوم", "بالغ"],
        "mortality_young": "فائقة الارتفاع ومباغتة خلال ساعات قليلة",
        "differential_diagnoses": ["التسمم باليوريا", "نقص فيتامين ب1 (CCN)", "التهاب الدماغ والتسمم الرصاصي"],
        "confirmatory_tests": "تشريح جثة حديثة: كليتان طريتان متحللتان (كلوة رخوة Pulpy kidney)، سائل مدمم في كيس التامور والبطن، وفحص السم بالبكتيريا.",
        "treatment_protocol": [
            {"drug": "مصل التسمم المعوي المناعي المضاد (Antitoxin Type D)", "dose_formula": "20-50 مل تحت الجلد فوراً", "target": "معادلة السموم الحرة قبل التصاقها بالمخ"},
            {"drug": "بنسلين بروكايين عالي التركيز (Procaine Penicillin G)", "dose_formula": "20,000 وحدة دولية / كجم عضل", "target": "القضاء على ميكروبات الكلوستريديا النشطة بالأمعاء"},
            {"drug": "محلول جفاف وإلكترولايت وبيكربونات الصوديوم بالفم", "dose_formula": "1-2 لتر", "target": "مكافحة الحموضة المعوية والجفاف"},
            {"drug": "فيتامين B1 (ثيامين Thiamine)", "dose_formula": "10-20 مجم/كجم عضل أو وريد", "target": "حماية أنسجة الجهاز العصبي"}
        ],
        "warnings": "خفض المركزات العلفية فوراً وزيادة نسبة الألياف (الدريس). تحصين كامل القطيع بلقاح الجامع للكلوستريديا (8-way / 10-way vaccine).",
        "pregnancy_safe": True
    },
    {
        "id": "ovi_ppr",
        "species": ["أغنام وماعز"],
        "name_ar": "طاعون المجترات الصغيرة (Peste des Petits Ruminants - PPR)",
        "name_en": "Peste des Petits Ruminants (PPR)",
        "etiology": "Morbillivirus (Paramyxoviridae) - فيروس الطاعون الصغير",
        "key_signs": ["حمى شديدة مفاجئة", "إسهال مائي كريه الرائحة", "تقرحات فموية ولعاب صديدي", "إفرازات أنفية وعينية صديدية جافة", "صعوبة تنفس حادة"],
        "symptoms_keywords": ["طاعون", "إسهال", "كريه", "فم", "تقرحات", "أنف", "صديد", "عيون", "تنفس", "حمى", "حرارة"],
        "temp_criteria": "high_fever",
        "age_groups": ["رضيع", "مفطوم", "بالغ", "مسن"],
        "mortality_young": "قد تصل إلى 80-90% في الماعز والحملان الصغيرة",
        "differential_diagnoses": ["الحمى القلاعية (FMD)", "الجدري (Pox)", "داء الرئة والبلورا الساري (CCPP)"],
        "confirmatory_tests": "مسحات فموية وأنفية لفحص الأنتيجين أو RT-PCR مع فحص مصل الأليزا التنافسي (c-ELISA).",
        "treatment_protocol": [
            {"drug": "مضاد حيوي واسع: أوكسيتتراسيكلين طويل المفعول 20% أو فلورفينيكول", "dose_formula": "1 مل / 10 كجم عضل", "target": "منع الالتهاب الرئوي البكتيري الثانوي الفتاك"},
            {"drug": "مضاد التهاب ومسكن: فلونيكسين ميغلومين أو كيتوبروفين", "dose_formula": "2.2 مجم/كجم عضل لمدة 3 أيام", "target": "خفض الحمى وتسكين آلام الأمعاء والفم"},
            {"drug": "محلول معالجة الجفاف وسوائل وريدية أو تحت الجلد (Ringers lactate)", "dose_formula": "50-100 مل/كجم يومياً", "target": "تعويض السوائل المفقودة في الإسهال المائي الغزير"},
            {"drug": "فيتامين A و E مع مطهرات فموية ملطفة", "dose_formula": "الجرعة الوقائية", "target": "تسريع ترميم الغشاء المخاطي المتقرح"}
        ],
        "warnings": "المرض وبائي خاضع للإبلاغ الدولي. عزل المشتبه به ومنع البيع والشراء. التطعيم الوقائي للقطيع بلقاح PPR النيجيري الحي المضعف.",
        "pregnancy_safe": True
    },

    # ------------------ EQUINE / HORSES ------------------
    {
        "id": "equ_colic",
        "species": ["خيول"],
        "name_ar": "متلازمة المغص المعوي في الخيل (Equine Colic Syndrome)",
        "name_en": "Equine Colic Syndrome",
        "etiology": "انحشار علفي، نفاخ تشنجي، التواء أمعاء، أو التهاب صفاق معوي",
        "key_signs": ["تقليب الرأس نحو الخاصرة", "الرقاد والتدحرج العنيف", "حك الأرض بالقوائم الأمامية", "التعرق الغزير وتسارع النبض", "انعدام أصوات حركة الأمعاء"],
        "symptoms_keywords": ["مغص", "تدحرج", "خاصرة", "تعرق", "أرض", "كرش", "أمعاء", "بطن", "روث", "إمساك", "نبض"],
        "temp_criteria": "normal",
        "age_groups": ["مفطوم", "بالغ", "مسن"],
        "mortality_young": "حالة طارئة مهددة للحياة إذا حدث التواء (Volvulus) أو انحباس معوي",
        "differential_diagnoses": ["التهاب الأمعاء الحاد (Enteritis)", "التهاب الصفاق (Peritonitis)", "تمزق الرحم أو المثانة"],
        "confirmatory_tests": "تمرير أنبوب معدي أنفي (Nasogastric tube) لارتجاع السوائل، والفحص المستقيمي لموقع الانحشار أو التمدد.",
        "treatment_protocol": [
            {"drug": "المسكن التشنجي الأول: فلونيكسين ميغلومين (Flunixin Meglumine / Banamine)", "dose_formula": "1.1 مجم/كجم وريدياً فقط (1 مل / 45 كجم)", "target": "تسكين آلام المغص الحشوي الشديدة ومكافحة السمية الداخلية"},
            {"drug": "مهدئ ومسكن عالي الفاعلية: كسيلازين (Xylazine 10%) أو ديتوميدين (Detomidine)", "dose_formula": "0.5-1.0 مجم/كجم وريدياً ببطء", "target": "تثبيت الخيل وتسكين التشنجات الشديدة للفحص الآمن"},
            {"drug": "ملين ومزلّق عبر الأنبوب الأنفي المعدي: زيت البارافين المعدني (Liquid Paraffin)", "dose_formula": "2-4 لتر ممزوجة بماء دافئ وأملاح إلكترولايت", "target": "تليين كتلة الانحشار العلفي وتسهيل خروجها"},
            {"drug": "محلول ملحي معادل متوازن وريدياً (Lactated Ringer's)", "dose_formula": "10-20 لتر وريدياً في حالات الجفاف الشديد", "target": "دعم الدورة الدموية ومكافحة الصدمة"}
        ],
        "warnings": "تحذير: لا تعطِ الفلونيكسين بالعضل في الخيل لتجنب خراجات كلوستريديا العضلات القاتلة (Clostridial Myositis). إذا استمر الألم بعد المسكنات، يجب التحويل الجراحي الفوري (Colic Surgery).",
        "pregnancy_safe": True
    },

    # ------------------ CAMELS / DROMEDARY ------------------
    {
        "id": "cam_trypanosomiasis",
        "species": ["إبل وهجن"],
        "name_ar": "مرض الجفار / الهيام في الإبل (Surra / Trypanosomiasis)",
        "name_en": "Camel Trypanosomiasis (Surra)",
        "etiology": "Trypanosoma evansi (طفيلي أولي سوطي في بلازما الدم ينقله ذباب التابانس)",
        "key_signs": ["حمى متموجة متقطعة", "ضمور شديد في السنام", "أنيميا وشحوب حاد", "وذمة أسفل البطن والقوائم", "إجهاض الحوامل"],
        "symptoms_keywords": ["سنام", "هزال", "حمى", "متقطعة", "ذباب", "جفار", "هيام", "بطن", "ورم", "دم", "إجهاض"],
        "temp_criteria": "mild_fever",
        "age_groups": ["مفطوم", "بالغ", "مسن"],
        "mortality_young": "مرتفع في الحيران والحوامل",
        "differential_diagnoses": ["التسمم الدموي في الإبل", "السل الكاذب (Pseudotuberculosis)", "ديدان البطن الشديدة"],
        "confirmatory_tests": "فحص قطرة دم طازجة معلقة مجهرياً لمشاهدة حركة التريبانوسوما السريعة، أو اختبار التلازن الكارتي (CATT).",
        "treatment_protocol": [
            {"drug": "العقار النوعي الأول للهجن: ميلارسامين (Melarsomine / Cymelarsan)", "dose_formula": "0.25 مجم/كجم عضل عميقاً (1 مل لكل 200 كجم)", "target": "القضاء التام على سلالات التريبانوسوما المقاومة"},
            {"drug": "أو كينابيرامين كبريتات وكلوريد (Quinapyramine sulphate/chloride)", "dose_formula": "3-5 مجم/كجم تحت الجلد", "target": "علاج وقائي وعلاجي واسع الاستخدام"},
            {"drug": "منشط كبد وحديد ومركبات الفوسفور (Butaphosphan + B12)", "dose_formula": "25-30 مل عضل أو وريد", "target": "إعادة بناء كرات الدم الحمراء وترميم عضلات السنام"},
            {"drug": "مضاد طفيليات داخلية وخارجية: إيفرمكتين سوبر (Ivermectin super)", "dose_formula": "1 مل / 50 كجم تحت الجلد", "target": "مكافحة ديدان الأنف والقراد والديدان المعوية"}
        ],
        "warnings": "التأكد من وزن الجمل بدقة؛ الجرعات الزائدة من مركبات الزرنيخ أو الكينابيرامين قد تسبب سمية كلوية وعصبية.",
        "pregnancy_safe": True
    },

    # ------------------ POULTRY / BIRDS ------------------
    {
        "id": "plk_newcastle",
        "species": ["دواجن وطيور"],
        "name_ar": "مرض النيوكاسل الوبائي (Newcastle Disease - ND / شبه طاعون الدجاج)",
        "name_en": "Newcastle Disease (ND)",
        "etiology": "Avian Paramyxovirus serotype 1 (APMV-1)",
        "key_signs": ["التواء الرقبة وشلل أجنحة", "إسهال أخضر فاقع", "صعوبة تنفس وحشرجة", "انتفاخ الرأس والعيون", "هبوط حاد في إنتاج البيض"],
        "symptoms_keywords": ["رقبة", "دوران", "شلل", "إسهال", "أخضر", "حشرجة", "بيض", "نيوكاسل", "موت", "طير"],
        "temp_criteria": "high_fever",
        "age_groups": ["رضيع", "مفطوم", "بالغ"],
        "mortality_young": "تصل إلى 90-100% في السلالات الحشوية الفتاكة (Velogenic)",
        "differential_diagnoses": ["إنفلونزا الطيور (Avian Influenza)", "التهاب الحنجرة والقصبة (ILT)", "مرض الجمبورو (IBD)"],
        "confirmatory_tests": "تشريح طيور نافقة: نزف صديدي على حلمات المعدة الغدية (Proventriculus)، وفحص تثبيط التلازن الدموي (HI) و RT-PCR.",
        "treatment_protocol": [
            {"drug": "مضاد فيروسي ورافع مناعة: مستخلص الأعشاب مع فيتامين C + أحماض أمينية", "dose_formula": "1-2 جم / لتر ماء شرب لمدة 5 أيام", "target": "دعم مناعة القطيع والتخفيف من وطأة الفيروس"},
            {"drug": "مضاد حيوي واسع: كولستين + تيلوزين أو دوكسي سيكلين", "dose_formula": "1 جم / لتر ماء شرب", "target": "منع وتطويق العدوى البكتيرية المعوية والتنفسية الثانوية (E. coli)"},
            {"drug": "محلول إلكترولايت وأملاح وسوربيتول ومنشط كلى", "dose_formula": "1 مل / لتر ماء شرب", "target": "غسيل الكلى وتخفيف ترسبات اليورات"}
        ],
        "warnings": "عزل العنبر وتطهيره التام بفورمالين أو فيركون إس (Virkon S). التخلص الصحي من الطيور النافقة بالحرق أو الدفن العميق.",
        "pregnancy_safe": True
    },

    # ------------------ DOGS & CATS ------------------
    {
        "id": "can_parvovirus",
        "species": ["كلاب"],
        "name_ar": "فيروس البارفو القاتل في الكلاب (Canine Parvovirus - CPV)",
        "name_en": "Canine Parvovirus (CPV-2)",
        "etiology": "Canine Parvovirus type 2b/2c (فيروس معوي شديد الضراوة والمقاومة)",
        "key_signs": ["إسهال دموي ذو رائحة عفنة مميزة", "قيء مستمر حاد", "جفاف شديد وانغوار العيون", "حمى ثم هبوط حرارة", "خمول ورفض تام للأكل والماء"],
        "symptoms_keywords": ["إسهال", "دم", "قيء", "ترجيع", "رائحة", "خمول", "جفاف", "كلب", "جرو", "بارفو"],
        "temp_criteria": "high_fever",
        "age_groups": ["رضيع", "مفطوم"],
        "mortality_young": "تصل إلى 80-90% في الجراء دون 6 أشهر إذا أهمل المحاليل",
        "differential_diagnoses": ["فيروس كورونا الكلاب (CCV)", "التهاب المعدة والأمعاء البكتيري (Salmonella)", "انسداد الأمعاء بجسم غريب"],
        "confirmatory_tests": "اختبار الكارت السريع لمسحة البراز (CPV Antigen Rapid Test Kit) تظهر النتيجة خلال 5 دقائق.",
        "treatment_protocol": [
            {"drug": "السوائل الوريدية المكثفة: محلول رينجر لاكتات (Ringer's Lactate)", "dose_formula": "60-90 مل/كجم يومياً تسريب وريدي مستمر مع 5% دكستروز وكلوريد بوتاسيوم", "target": "إنقاذ الجرو من الصدمة الوعائية والجفاف الحاد"},
            {"drug": "مضاد قيء مركزي: ماروبيتانت (Maropitant / Cerenia) أو أوندانسيترون", "dose_formula": "1 مجم/كجم تحت الجلد أو وريد مرة يومياً", "target": "وقف القيء لتمكين الأمعاء من الشفاء"},
            {"drug": "مضاد حيوي واسع: أموكسيسيلين كلافولانيك (Synulox) + ميترونيدازول", "dose_formula": "8.75 مجم/كجم تحت الجلد مرتين يومياً", "target": "منع التسمم الدموي البكتيري الناتج عن تهتك بطانة الأمعاء"},
            {"drug": "حامي المعدة: فاموتيدين (Famotidine) أو أوميبرازول", "dose_formula": "0.5-1 مجم/كجم وريدياً", "target": "حماية بطانة المعدة من القرح النزفية"}
        ],
        "warnings": "المنع التام للأكل والشرب بالفم (NPO) طوال فترة القيء النشط. عزل الجرو تطهير المكان بالكلور المركز (محلول 1:30).",
        "pregnancy_safe": True
    }
]


def diagnose_clinical_case(
    species: str,
    age_str: str,
    temp_c: float,
    weight_kg: float,
    pregnancy_status: str,
    duration: str,
    symptoms_list: List[str],
    notes: str = ""
) -> Dict[str, Any]:
    """
    Main clinical diagnostic reasoning function.
    Matches inputs against knowledge base and returns prioritized differential diagnoses,
    exact calculated dosages for the animal's weight, warnings, and lab recommendations.
    """
    temp_eval = evaluate_temperature_status(species, temp_c)
    
    # Combined search tokens & Arabic clinical synonym expansion
    combined_tokens = [s.lower() for s in symptoms_list]
    if notes:
        combined_tokens.extend(notes.lower().split())

    full_text = " ".join(combined_tokens)
    synonym_map = {
        "كحة": ["سعال", "صدر", "تنفس", "نهجان"],
        "سخونة": ["حمى", "حرارة", "سخونية"],
        "سخونية": ["حمى", "حرارة"],
        "ريالة": ["لعاب", "سيلان لعاب", "فم"],
        "تطويح": ["ترنح", "دوران", "عصبية"],
        "دم": ["مدمم", "نزف", "أحمر", "بول أحمر"],
        "انتفاخ": ["نفاخ", "كرش", "غازات"],
        "خراريج": ["خراج", "صديد", "دمامل"],
        "عرج": ["حوافر", "حافر", "قلاعية"],
        "قرف": ["فقدان شهية", "امتناع عن الأكل", "هزال"],
        "إسهال": ["اسهال", "روث مائي", "إسهال دموي"],
        "اسهال": ["إسهال", "روث مائي"],
        "تشنج": ["تشنجات", "صرع", "صمل"],
        "ورم": ["وذمة", "عقد", "تضخم"],
        "عين": ["عيون", "دمع", "ملتحمة"],
        "جلد": ["عقد جلدية", "جرب", "قراع", "حكة"],
        "ضرع": ["حليب", "التهاب ضرع", "حلمات"]
    }
    for trigger, added_kws in synonym_map.items():
        if trigger in full_text:
            combined_tokens.extend(added_kws)

    scored_candidates = []

    for disease in DIAGNOSTIC_KNOWLEDGE_BASE:
        score = 0
        
        # 1. Species match (+30 points)
        if species in disease["species"] or "all" in disease["species"]:
            score += 30
        else:
            continue  # Wrong species entirely

        # 2. Temperature correlation (+20 points)
        if disease.get("temp_criteria") == temp_eval["status"]:
            score += 20
        elif disease.get("temp_criteria") == "high_fever" and temp_eval["status"] in ["high_fever", "mild_fever"]:
            score += 15
        elif disease.get("temp_criteria") == "normal" and temp_eval["status"] == "normal":
            score += 15

        # 3. Symptoms matching (+10 points per matched keyword)
        match_count = 0
        for token in combined_tokens:
            for kw in disease["symptoms_keywords"]:
                if kw in token or token in kw:
                    match_count += 1
                    score += 12
                    break
        
        # 4. Age match (+10 points)
        for ag in disease.get("age_groups", []):
            if ag in age_str:
                score += 10
                break

        # Calculate confidence percentage (capped at 96%)
        confidence = min(96, max(35, int((score / 90.0) * 100)))

        # Format exact weight-based doses
        custom_rx = []
        for rx in disease["treatment_protocol"]:
            dose_desc = rx["dose_formula"]
            # If weight is provided and formula mentions kg, add calculated absolute quantity
            calc_note = ""
            if weight_kg and weight_kg > 0:
                if "/ 10 kg" in dose_desc or "/10kg" in dose_desc:
                    calc_ml = round(weight_kg / 10.0, 1)
                    calc_note = f" (الحجم الإجمالي المحسوب للحيوان: {calc_ml} مل)"
                elif "/ 20 kg" in dose_desc or "/20kg" in dose_desc:
                    calc_ml = round(weight_kg / 20.0, 1)
                    calc_note = f" (الحجم الإجمالي المحسوب للحيوان: {calc_ml} مل)"
                elif "/ 50 kg" in dose_desc or "/50kg" in dose_desc:
                    calc_ml = round(weight_kg / 50.0, 1)
                    calc_note = f" (الحجم الإجمالي المحسوب للحيوان: {calc_ml} مل)"
                elif "/ 45 kg" in dose_desc or "/45kg" in dose_desc:
                    calc_ml = round(weight_kg / 45.0, 1)
                    calc_note = f" (الحجم الإجمالي المحسوب للحيوان: {calc_ml} مل)"

            custom_rx.append({
                "drug": rx["drug"],
                "dosage": dose_desc + calc_note,
                "purpose": rx["target"]
            })

        # Pregnancy contraindication check
        preg_warning = ""
        is_safe_in_preg = disease.get("pregnancy_safe", True)
        if "حامل" in pregnancy_status or "عشار" in pregnancy_status:
            if not is_safe_in_preg:
                preg_warning = "⚠️ تنبيه حمل حرج: هذا المرض أو بروتوكوله العلاجي يحمل خطورة عالية على الجنين (خطر الإجهاض أو التشوه). تجنب إعطاء أدوية مثل (Dexamethasone, PGF2a, Imidocarb) واستبدلها ببدائل داعمة آمنة."

        scored_candidates.append({
            "name_ar": disease["name_ar"],
            "name_en": disease["name_en"],
            "etiology": disease["etiology"],
            "confidence": confidence,
            "key_signs": disease["key_signs"],
            "differential_diagnoses": disease["differential_diagnoses"],
            "confirmatory_tests": disease["confirmatory_tests"],
            "treatment_protocol": custom_rx,
            "warnings": disease["warnings"],
            "pregnancy_warning": preg_warning
        })

    # Sort descending by confidence score
    scored_candidates.sort(key=lambda x: x["confidence"], reverse=True)

    # If no specific disease matched strongly, provide a robust clinical syndrome fallback
    if not scored_candidates:
        scored_candidates.append({
            "name_ar": f"متلازمة سريرية عامة مشتبهة في {species}",
            "name_en": f"General Clinical Syndrome in {species}",
            "etiology": "عدوى بكتيرية أو فيروسية أو تسمم معوي غير محدد",
            "confidence": 55,
            "key_signs": symptoms_list[:4] if symptoms_list else ["حمى", "خمول"],
            "differential_diagnoses": ["التسمم الدموي الحاد", "التهاب الأمعاء الحاد", "الالتهاب الرئوي التنفسي"],
            "confirmatory_tests": "فحص صورة دم كاملة (CBC)، فحص وظائف الكبد والكلى، وأخذ مسحات ميكروبيولوجية للزرع والتحسس.",
            "treatment_protocol": [
                {"drug": "مضاد حيوي واسع الطيف (أموكسيسيلين + كلافولانيك أو أوكسيتتراسيكلين)", "dosage": f"الجرعة القياسية لوزن {weight_kg or 100} كجم", "purpose": "السيطرة على العدوى البكتيرية المحتملة"},
                {"drug": "خافض حرارة ومسكن: فلونيكسين ميغلومين أو كيتوبروفين", "dosage": "حسب الوزن", "purpose": "خفض الحرارة وتسكين الألم"},
                {"drug": "محاليل إلكترولايت وفيتامينات داعمة وريدياً", "dosage": "حسب درجة الجفاف", "purpose": "دعم الدورة الدموية ومكافحة الصدمة"}
            ],
            "warnings": "عزل الحيوان في مكان دافئ وجاف ومراقبة العلامات الحيوية كل 6 ساعات.",
            "pregnancy_warning": ""
        })

    return {
        "species": species,
        "age": age_str,
        "weight_kg": weight_kg,
        "temperature_c": temp_c,
        "temp_evaluation": temp_eval,
        "pregnancy_status": pregnancy_status,
        "duration": duration,
        "diagnoses": scored_candidates[:3]  # Return top 3 differential diagnoses
    }
