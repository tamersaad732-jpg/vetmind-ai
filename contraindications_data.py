# -*- coding: utf-8 -*-
"""
VetMind AI - Comprehensive Veterinary Contraindications & Toxicities Knowledge Base
(قاعدة بيانات الممنوعات والسميات البيطرية الشاملة حسب نوع الحيوان والحالة الإكلينيكية)
"""

SPECIES_METADATA = {
    "cats": {"name": "القطط (Feline)", "icon": "🐱", "code": "cats"},
    "dogs": {"name": "الكلاب (Canine)", "icon": "🐶", "code": "dogs"},
    "cattle": {"name": "الأبقار والجاموس (Bovine)", "icon": "🐄", "code": "cattle"},
    "horses": {"name": "الخيول والمهور (Equine)", "icon": "🐎", "code": "horses"},
    "sheep": {"name": "الأغنام والماعز (Ovine/Caprine)", "icon": "🐑", "code": "sheep"},
    "camels": {"name": "الإبل والجمال (Camelids)", "icon": "🐪", "code": "camels"},
    "poultry": {"name": "الدواجن والطيور (Poultry/Avian)", "icon": "🐔", "code": "poultry"},
    "rabbits": {"name": "الأرانب والقوارض (Lagomorphs/Rodents)", "icon": "🐰", "code": "rabbits"},
}

CONTRAINDICATIONS_DB = [
    # =========================================================================
    # 1. CATS (القطط)
    # =========================================================================
    {
        "id": "cat_paracetamol",
        "species_code": "cats",
        "species_name": "القطط",
        "substance_name": "الباراسيتامول / الأسيتامينوفين (Paracetamol / Panadol / Tylenol)",
        "substance_category": "أدوية بشرية ومسكنات",
        "danger_level": "fatal",
        "danger_level_title": "🔴 قاتل فوراً (حبة واحدة تقتل قطة بالغة)",
        "clinical_condition": "عامة وفي جميع الحالات",
        "reason": "القطط تفتقر جينياً لإنزيم (Glucuronyl Transferase) اللازم لأيض الباراسيتامول في الكبد، مما يؤدي إلى تراكم مستقلب سام جداً (NAPQI). يرتبط هذا المستقلب بهيموغلوبين الدم ويحوله إلى ميثيموغلوبين عاجز عن حمل الأكسجين، مسبباً اختناقاً خلوياً وتلفاً كبدياً نخرياً حاداً وتكسراً هيموليتياً لكريات الدم (Heinz bodies).",
        "clinical_signs": "زرقة أو لون بني شيكولاتي للأغشية المخاطية واللسان، وذمة وجهية وتحت الفك، صعوبة تنفس حادة، خمول شديد وانخفاض حرارة الجسم، يرقان، ونفوق سريع خلال ساعات.",
        "emergency_antidote": "الترياق النوعي الفوري: إن-أسيتيل سيستئين (N-Acetylcysteine - NAC) بجرعة تحميلية 140 ملغم/كغم وريدياً أو فموياً، ثم 70 ملغم/كغم كل 4 ساعات لمدة 3-5 أيام، مع فيتامين C (حمض الأسكوربيك) 30 ملغم/كغم، والعلاج بالأكسجين والمحاليل الوريدية.",
        "references": "Plumb's Veterinary Drug Handbook 9th Ed • BSAVA Small Animal Formulary"
    },
    {
        "id": "cat_permethrin",
        "species_code": "cats",
        "species_name": "القطط",
        "substance_name": "مركبات البيرمثرين والبيريثرويد (Permethrin & Spot-on Dog Flea Treatments)",
        "substance_category": "مضادات حشرات وقراد الكلاب",
        "danger_level": "fatal",
        "danger_level_title": "🔴 سمية عصبية قاتلة",
        "clinical_condition": "العلاج الموضعي للحشرات أو ملامسة كلاب معالجة حديثاً",
        "reason": "عجز كبد القطط عن التخلص السريع من البيرمثرين عن طريق الجلوكورونيد؛ يؤدي ذلك لإبقاء قنوات الصوديوم العصبية مفتوحة باستمرار، مسبباً فرط إثارة عصبية مستمرة واختلاجات عضلية وتشنجات حادة تؤدي لفرط الحرارة وفشل تنفسي.",
        "clinical_signs": "رعشة مستمرة في الرأس والأذنين، لعاب رغوي كثيف، عدم اتزان ورنح، تشنجات عضلية واهتزازية تشبه الصرع، ارتفاع حرارة مفرط (> 41 مئوية).",
        "emergency_antidote": "غسيل فوري للجسم بماء فاتر وسائل تنظيف أطباق مخفف لإزالة المادة من الفراء، ضبط التشنجات بالميثوكاربامول (Methocarbamol) وريدياً 55-220 ملغم/كغم أو ديازيبام، ودعم بالسوائل الوريدية ومستحلبات الدهون الوريدية (Intralipid 20%).",
        "references": "ASPCA Animal Poison Control Center Guidelines"
    },
    {
        "id": "cat_lilies",
        "species_code": "cats",
        "species_name": "القطط",
        "substance_name": "نباتات الزنبق والزنابق (Lilies - Lilium & Hemerocallis spp.)",
        "substance_category": "نباتات زينة منزلية سامة",
        "danger_level": "fatal",
        "danger_level_title": "🔴 فشل كلوي حاد قاتل (حتى غبار الطلع أو ماء المزهرية)",
        "clinical_condition": "أي ابتلاع أو لعق لغبار الطلع من الفراء",
        "reason": "تحتوي نباتات الزنبق الحقيقي على ذيفانات مجهولة شديدة السمية للنبيبات الكلوية في القطط فقط، مسببة نخراً حاداً ومفاجئاً في خلايا الأنابيب الكلوية (Acute Tubular Necrosis).",
        "clinical_signs": "قيء وغثيان وخمول خلال ساعتين من التعرض، يليه انقطاع إدرار البول (Anuria)، وارتفاع هائل في اليوريا والكرياتينين، وفشل كلوي مميت خلال 48-72 ساعة.",
        "emergency_antidote": "إحداث قيء فوري وإعطاء فحم نشط خلال 4 ساعات الأولى، محاليل وريدية مكثفة بضعف الاحتياج اليومي لمدة 48 ساعة على الأقل لمنع ترسب الحطام الكلوي، وفي الحالات المتقدمة غسيل كلوي بريتوني.",
        "references": "Merck Veterinary Manual - Small Animal Nephrology"
    },
    {
        "id": "cat_aspirin",
        "species_code": "cats",
        "species_name": "القطط",
        "substance_name": "الأسبرين وحمض الساليسيليك (Aspirin / Salicylates)",
        "substance_category": "مضادات التهاب غير ستيرويدية",
        "danger_level": "severe",
        "danger_level_title": "🟠 سمية شديدة وتثبيط نقي العظم",
        "clinical_condition": "تكرار الجرعات يومياً (الجرعة المعتمدة طبياً تتطلب فاصل 48-72 ساعة بجرعات دقيقة جداً)",
        "reason": "فترة نصف العمر للأسبرين في القطط تتراوح بين 38 إلى 45 ساعة مقارنة بـ 8 ساعات في الكلاب وساعتين في الإنسان، مما يجعل إعطاءه بجرعات يومية اعتيادية يسبب تراكماً ساماً يؤدي لنزيف وقرحة معدية وحماض استقلابي وفشل كلوي.",
        "clinical_signs": "قيء مدمم، فقدان شهية، سرعة تنفس، اختلال التوازن، تقرحات هضمية، غيبوبة.",
        "emergency_antidote": "إيقاف الدواء فوراً، إعطاء حاميات المعدة (أوميبرازول 1 ملغم/كغم، سكرالفات)، محاليل وريدية بيكربوناتية لتصحيح الحموضة وتسريع الإطراح الكلوي للساليسيلات.",
        "references": "Plumb's Veterinary Drug Handbook"
    },
    {
        "id": "cat_enrofloxacin_high",
        "species_code": "cats",
        "species_name": "القطط",
        "substance_name": "إنروفلوكساسين بجرعات عالية (Enrofloxacin / Baytril > 5 mg/kg)",
        "substance_category": "مضادات حيوية فلوروكينولون",
        "danger_level": "severe",
        "danger_level_title": "🟠 عمى دائم وتلف شبكية العين (Retinal Toxicity)",
        "clinical_condition": "الجرعات التي تزيد عن 5 ملغم/كغم/يوم أو القطط المصابة بقصور كلوي",
        "reason": "القطط تمتلك طفرة في ناقل بروتيني (ABCG2) في الحاجز الشبكي الدموي تسمح بتراكم الإنروفلوكساسين وتفاعله الضوئي مع شبكية العين، مسبباً تدميراً نخرياً كاملاً لمستقبلات الضوء وعمى لا رجعة فيه.",
        "clinical_signs": "اتساع دائم لحدقة العين (Mydriasis)، عدم استجابة الحدقة للضوء، الاصطدام بالحوائط، فقدان البصر التام والمفاجئ.",
        "emergency_antidote": "إيقاف الدواء فوراً، إبعاد القطة عن الضوء الساطع، الاستعاضة ببدائل آمنة مثل الأموكسيسيلين كلافولانات أو السيفوفيسين (Convenia).",
        "references": "Gelatt's Veterinary Ophthalmology"
    },

    # =========================================================================
    # 2. DOGS (الكلاب)
    # =========================================================================
    {
        "id": "dog_chocolate",
        "species_code": "dogs",
        "species_name": "الكلاب",
        "substance_name": "الشوكولاتة والكاكاو (Theobromine & Caffeine / Methylxanthines)",
        "substance_category": "أطعمة بشرية سامة",
        "danger_level": "fatal",
        "danger_level_title": "🔴 تسارع قلبي وتشنجات مميتة",
        "clinical_condition": "تناول الشوكولاتة الداكنة أو بودرة الكاكاو الخام",
        "reason": "الكلاب تعاني من بطء شديد في استقلاب الثيوبرومين (فترة نصف العمر 17.5 ساعة). يثبط الثيوبرومين مستقبلات الأدينوزين ويزيد الكالسيوم داخل الخلايا مسبباً فرط إثارة عضلية وقلبية حادة وعدم انتظام ضربات القلب وتقلصات وعائية دماغية.",
        "clinical_signs": "لهاث شديد، عطش وتبول مفرط، تقيؤ وإسهال، تسرع ضربات القلب، تشنجات واهتزازات عضلية، انهيار قلبي ونفوق.",
        "emergency_antidote": "إحداث القيء الفوري بمحلول الأبومورفين (Apomorphine) أو ماء الأكسجين 3%، إعطاء فحم نشط مكرر كل 4-6 ساعات، حاصرات بيتا (بروبرانولول) أو ليدوكائين لضبط التسارع القلبي، وقسطرة بولية لمنع إعادة امتصاص الثيوبرومين من المثانة.",
        "references": "Small Animal Critical Care Medicine"
    },
    {
        "id": "dog_grapes",
        "species_code": "dogs",
        "species_name": "الكلاب",
        "substance_name": "العنب والزبيب (Grapes & Raisins / Tartaric Acid)",
        "substance_category": "أطعمة وفاكهة سامة",
        "danger_level": "fatal",
        "danger_level_title": "🔴 فشل كلوي حاد غير قابل للتنبؤ",
        "clinical_condition": "أي كمية حتى لو كانت حبة واحدة لبعض السلالات",
        "reason": "أثبتت الأبحاث الحديثة أن حمض التارتاريك (Tartaric acid) والأملاح المشتقة منه في العنب تسبب تنكساً نخرياً حاداً ومفاجئاً في الخلايا الأنبوبية لقشرة الكلية بالكلاب، ولا ترتبط السمية بالجرعة بل باستجابة الحيوان الفردية.",
        "clinical_signs": "قيء وإسهال خلال 6-12 ساعة، فقدان شهية، عطش وتبول غزير يليه انقطاع تام للبول (Oliguria/Anuria) مع فشل كلوي حاد ومميت خلال 24-72 ساعة.",
        "emergency_antidote": "إحداث قيء هجومي فوري خلال أول ساعتين، إعطاء فحم نشط، غسيل كلوي وتكثيف السوائل الوريدية المحتوية على الشوارد لمدة 48-72 ساعة متواصلة ومراقبة الكرياتينين.",
        "references": "Journal of Veterinary Emergency and Critical Care"
    },
    {
        "id": "dog_xylitol",
        "species_code": "dogs",
        "species_name": "الكلاب",
        "substance_name": "المحلي الصناعي إكسيليتول (Xylitol / Birch Sugar in sugar-free gum)",
        "substance_category": "محليات صناعية في العلك والحلويات والزبادي",
        "danger_level": "fatal",
        "danger_level_title": "🔴 هبوط سكر دم صاعق ونخر كبدي حاد",
        "clinical_condition": "ابتلاع العلك الخالي من السكر أو المخبوزات المصنعة",
        "reason": "في الكلاب، يُمتص الإكسيليتول بسرعة البرق ويحفز البنكرياس لإفراز كميات هائلة من الإنسولين تصل إلى 6 أضعاف الطبيعي، مسبباً هبوطاً سكرياً كارثياً خلال 30 دقيقة، وبجرعات أعلى يسبب نخراً كبدياً نخرياً شاملاً ونزيفاً داخلياً حاداً.",
        "clinical_signs": "ترنح، فقدان توازن، انهيار مفاجئ، تشنجات صرعية بسبب نقص سكر الدم (< 30 mg/dL)، قيء، يرقان، نزيف تحت الجلد (DIC)، وفاة مفاجئة.",
        "emergency_antidote": "تسريب وريدي فوري لمحلول الجلوكوز/الدكستروز 25% ثم الاستمرار على محاليل 5% دكستروز، حاميات الكبد (SAMe، سيليمارين)، وفحوصات دورية لإنزيمات الكبد وعوامل التخثر.",
        "references": "Veterinary Clinical Toxicology"
    },
    {
        "id": "dog_ivermectin_mdr1",
        "species_code": "dogs",
        "species_name": "الكلاب",
        "substance_name": "الإيفرمكتين بجرعات علاج الجرب في سلالات الكولي (Ivermectin in MDR1 Breeds)",
        "substance_category": "مضادات طفيليات",
        "danger_level": "fatal",
        "danger_level_title": "🔴 شلل تنفسي وغيبوبة عصبية في سلالات الكولي والشيبرد",
        "clinical_condition": "سلالات Collie, Australian Shepherd, Shetland, Whippet التي تحمل طفرة ABCB1 / MDR1",
        "reason": "طفرة جين MDR1 تؤدي لغياب بروتين (P-glycoprotein) الذي يحمي الدماغ ويضخ الأدوية خارج الحاجز الدموي الدماغي. بدون هذا البروتين، يتراكم الإيفرمكتين في الجهاز العصبي المركزي ويحفز مستقبلات GABA بشكل مفرط مسبباً شللاً عصبياً كاملاً.",
        "clinical_signs": "سيلان لعاب، ترنح وضعف القوائم الخلفية، اتساع حدقة العين والعمى المؤقت، غيبوبة عميقة تستمر لأيام أو أسابيع، توقف التنفس.",
        "emergency_antidote": "رعاية داعمة مكثفة في العناية المركزة، محاليل وريدية، تنفس صناعي، مستحلب الدهون الوريدي (Intralipid 20%) لالتقاط الإيفرمكتين المحب للدهون من مجرى الدم والدماغ.",
        "references": "Washington State University Veterinary Clinical Pharmacology"
    },
    {
        "id": "dog_onions_garlic",
        "species_code": "dogs",
        "species_name": "الكلاب",
        "substance_name": "البصل والثوم والكراث (Onions & Garlic / Allium species)",
        "substance_category": "أطعمة وخضار منزلية",
        "danger_level": "severe",
        "danger_level_title": "🟠 فقر دم انحلالي حاد (Hemolytic Anemia)",
        "clinical_condition": "تناول البصل أو الثوم مطبوخاً أو طازجاً أو مسحوقاً (بودرة)",
        "reason": "تحتوي مركبات الآليوم على ثنائي الكبريتيد العضوي (N-propyl disulfide) الذي يسبب أكسدة بروتينات كريات الدم الحمراء واستنزاف الجلوتاثيون، مسبباً تمزق الغشاء الخلوي للكبريت وتكون أجسام هاينز وتكسر الدم داخل الأوعية وخارجها.",
        "clinical_signs": "شحوب أو اصفرار اللثة، بول بني داكن كلون الشاي، خمول وضعف شديد، سرعة تنفس، انهيار بعد 2-4 أيام من الأكل.",
        "emergency_antidote": "إحداث قيء إن كان الابتلاع حديثاً، نقل دم كامل في الحالات الشديدة (PCV < 15%)، أكسجين، ومضادات أكسدة داعمة.",
        "references": "Veterinary Medicine: A textbook of the diseases of cattle, horses, sheep, pigs and dogs"
    },

    # =========================================================================
    # 3. HORSES (الخيول والمهور)
    # =========================================================================
    {
        "id": "horse_tilmicosin",
        "species_code": "horses",
        "species_name": "الخيول والمهور",
        "substance_name": "التلميكوسين (Tilmicosin / Micotil)",
        "substance_category": "مضادات حيوية ماكروليد للماشية",
        "danger_level": "fatal",
        "danger_level_title": "🔴 موت قلبي مفاجئ وفوري (حتى بالجرعات المتدنية)",
        "clinical_condition": "الحقن للخيول بأي طريق (عضلي أو وريدي أو تحت الجلد)",
        "reason": "التلميكوسين يرتبط بشكل غير عكوس بمستقبلات الكالسيوم في خلايا عضلة القلب في الفصيلة الخيلية، مسبباً تثبيطاً كلياً لانقباض عضلة القلب (Negative Inotropy)، وهبوطاً حاداً وغير قابل للعكس في النتاج القلبي والضغط، يتبعه سكتة قلبية ونفوق خلال دقائق.",
        "clinical_signs": "تسارع ضربات القلب وضعف النبض، ترنح وانهيار مفاجئ للأرض، صعوبة تنفس حادة، وتوقف القلب خلال 5-15 دقيقة من الحقن.",
        "emergency_antidote": "لا يوجد ترياق نوعي فعال. محاولات دعم القلب بالدوبامين أو الكالسيوم نادراً ما تنجح؛ الدواء ممنوع قطعياً وتاماً في الخيول ومحرم استخدامه.",
        "references": "Adams and Adams' Pharmacology and Therapeutics for Veterinary Medicine"
    },
    {
        "id": "horse_monensin",
        "species_code": "horses",
        "species_name": "الخيول والمهور",
        "substance_name": "الموننسين والأيونوفورات (Monensin / Rumensin Feed Additives)",
        "substance_category": "محسنات نمو وأعلاف الماشية",
        "danger_level": "fatal",
        "danger_level_title": "🔴 اعتلال عضلة القلب القاتل والتنكيس العضلي",
        "clinical_condition": "تغذية الخيول على أعلاف مخصصة للأبقار أو الدواجن تحتوي على الموننسين",
        "reason": "الخيول أكثر حساسية للموننسين بـ 200 ضعف مقارنة بالأبقار (الجرعة القاتلة 2-3 ملغم/كغم فقط). ينقل الموننسين شوارد الصوديوم والكالسيوم داخل خلايا القلب والعضلات الهيكلية بشكل مفرط، مسبباً انفجار الميتوكوندريا وتليف عضلة القلب وفشلها الاحتقاني.",
        "clinical_signs": "مغص، عرق بارد، ارتعاشات عضلية، عدم انتظام ضربات القلب، ضعف القوائم ورفض الحركة، صعوبة تنفس، ونفوق حاد أو موت مفاجئ عند أي إجهاد لاحق.",
        "emergency_antidote": "إيقاف العلف فوراً وتفريغ المعدة بالأنبوب الأنفي المعوي وإعطاء زيت برافين وفحم نشط، محاليل وريدية داعمة ومضادات أكسدة (فيتامين E وسيلينيوم)؛ الخيول الناجية تعاني من عجز دائم في أداء القلب.",
        "references": "Equine Internal Medicine 4th Edition"
    },
    {
        "id": "horse_lincomycin",
        "species_code": "horses",
        "species_name": "الخيول والمهور",
        "substance_name": "اللينكوميسين والكليندامايسين (Lincomycin & Clindamycin / Lincosamides)",
        "substance_category": "مضادات حيوية لينكوزامايد",
        "danger_level": "fatal",
        "danger_level_title": "🔴 التهاب معوي نخرى قاتل (Fatal Clostridial Typhlocolitis)",
        "clinical_condition": "أي استخدام فموي أو حقني في الخيول البالغة",
        "reason": "اللغة الميكروبية في الأعور والقولون لدى الخيول تعتمد على بكتيريا لاهوائية دقيقة لهضم الألياف. اللينكوسامايدات تقضي تماماً على الفلورا الطبيعية مما يسمح بتكاثر متفجر لبكتيريا (Clostridium difficile) و(Clostridium perfringens) التي تفرز ذيفانات معوية مميتة.",
        "clinical_signs": "إسهال مائي غزير وكريه الرائحة، مغص عنيف، صدمة تسممية معوية (Endotoxic Shock)، جفاف صاعق، ونفوق بنسبة تتجاوز 90% خلال 24-48 ساعة.",
        "emergency_antidote": "رعاية طبية فائقة بالمحاليل الوريدية الهجومية، مضادات السموم المعوية (بولي ميكسين B بجرعات متدنية لربط الإندوتوكسين)، ميترونيدازول لمقاومة الكلوستريديا، ومكملات الفلورا الحية (Transfaunation).",
        "references": "Kahn's Equine Veterinary Practice Guidelines"
    },
    {
        "id": "horse_procaine_pen_iv",
        "species_code": "horses",
        "species_name": "الخيول والمهور",
        "substance_name": "بنسلين بروكايين بالحقن الوريدي (Procaine Penicillin G - IV Injection)",
        "substance_category": "مضادات حيوية بنسلينية",
        "danger_level": "fatal",
        "danger_level_title": "🔴 نوبة جنون وتشنجات صرعية صاعقة ووفاة فورية",
        "clinical_condition": "دخول أي قطرة من بنسلين البروكايين في الوريد بدلاً من العضل",
        "reason": "البروكايين مخدر موضعي يتحرر فوراً في مجرى الدم عند الحقن الوريدي، ليعبر الحاجز الدماغي بتركيز فائق مسبباً سمية عصبية حادة وفرط إثارة قشرية وتشنجات جنونية عنيفة تؤدي إلى صدمة قلبية وكسور ورضوض مميتة.",
        "clinical_signs": "فزع وصرع عنيف، ركض عشوائي والاصطدام بالحوائط، تشنجات عضلية مستمرة، هبوط ووفاة خلال ثوانٍ إلى دقائق معدودة.",
        "emergency_antidote": "الوقاية بالغة الأهمية (سحب المكبس دائماً للتأكد من عدم خروج دم وحقنه عضلياً عميقاً فقط). في حال وقوع الحادثة: تأمين محيط الحصان، وتثبيط التشنجات بالديازيبام 25-50 ملغم وريدياً فوراً مع الرعاية الداعمة.",
        "references": "Adams and Adams' Veterinary Pharmacology"
    },

    # =========================================================================
    # 4. RUMINANTS - CATTLE, SHEEP, GOATS (الأبقار، الأغنام، الماعز)
    # =========================================================================
    {
        "id": "rum_copper_sheep",
        "species_code": "sheep",
        "species_name": "الأغنام والماعز",
        "substance_name": "النحاس وأملاح النحاس الزائدة (Copper Supplements & Cattle Feed in Sheep)",
        "substance_category": "معادن وإضافات علفية",
        "danger_level": "fatal",
        "danger_level_title": "🔴 انفجار انحلالي ونفوق جماعي للأغنام (Copper Storage Toxicity)",
        "clinical_condition": "تغذية الأغنام على أعلاف أبقار أو خلطات دواجن تحتوي على نحاس عالي",
        "reason": "كبد الأغنام يتميز بقدرة إطراحية ضعيفة جداً للنحاس في الصفراء مقارنة بباقي الحيوانات. يتراكم النحاس بصمت في خلايا الكبد لأشهر حتى يتشبع، ثم ينطلق فجأة وبكميات هائلة إلى مجرى الدم إثر أي إجهاد، مسبباً تكسراً هائلاً وشاملاً لكريات الدم الحمراء وفشلاً كلوياً وكبدياً صاعقاً.",
        "clinical_signs": "يرقان شديد واصفرار اللثة والعينين، بول مدمم داكن كلون القهوة (Gun-metal kidney)، انخفاض حاد في الشهية، ونفوق سريع خلال 24-48 ساعة من الأزمة الانحلالية.",
        "emergency_antidote": "الترياق النوعي: إعطاء موليبدات الأمونيوم (Ammonium molybdate) 100 ملغم مع ثيوكبريتات الصوديوم 1 غرام فموياً يومياً لمدة 3 أسابيع لسحب النحاس من الأنسجة، ودعم بالسوائل ونقل الدم للحيوانات المصابة.",
        "references": "Veterinary Medicine: Blood, Radostits et al. - Diseases of Sheep"
    },
    {
        "id": "rum_urea",
        "species_code": "cattle",
        "species_name": "الأبقار والجاموس",
        "substance_name": "اليوريا غير المتدرجة والأمونيا (Excessive Urea / NPN in Cattle)",
        "substance_category": "إضافات علفية نيتروجينية غير بروتينية",
        "danger_level": "fatal",
        "danger_level_title": "🔴 تسمم أمونيا حاد وانتفاخ كرش مميت",
        "clinical_condition": "خلط غير متجانس لليوريا أو زيادتها عن 1-2% من العليقة أو تناولها بدون تدرج",
        "reason": "إنزيم اليورييز في ميكروبات الكرش يفكك اليوريا بسرعة فائقة إلى غاز الأمونيا. عندما يتجاوز معدل الأمونيا قدرة الكرش على الاستفادة، يرتفع أس الكرش القلوي (pH > 8.0) وتُمتص الأمونيا الحرة غير المتأينة إلى الدم، مسببة تثبيط دورة كريبس وحماضاً دماغياً وتشنجات عضلية واختناقاً.",
        "clinical_signs": "ألم بطني وركل في البطن، انتفاخ كرش سريع، سيلان لعاب غزير ورغوي، ارتعاشات عضلية شديدة وتشنجات كزازية، صعوبة تنفس، ونفوق خلال 1-4 ساعات.",
        "emergency_antidote": "الترياق الكلاسيكي الفوري: تجريع الحيوان بالأنبوب المعدي 2-4 لترات من الخل الأبيض التجاري (حمض الأسيتيك 5%) المخلوط بـ 20-30 لتراً من الماء البارد جداً لخفض قلوية الكرش وإبطاء نشاط إنزيم اليورييز، وحقن كالسيوم وماغنسيوم وريدياً.",
        "references": "Merck Veterinary Manual - Ruminant Metabolic Emergencies"
    },
    {
        "id": "rum_dexamethasone_pregnancy",
        "species_code": "cattle",
        "species_name": "الأبقار والأغنام والجمال",
        "substance_name": "الديكساميثازون والستيرويدات في الثلث الأخير من العشار (Dexamethasone in Late Pregnancy)",
        "substance_category": "كورتيكوستيرويدات ومضادات التهاب",
        "danger_level": "severe",
        "danger_level_title": "🟠 إجهاض فوري وإسقاط الجنين واحتباس المشيمة",
        "clinical_condition": "استخدام الستيرويدات في الشهور الأخيرة من الحمل (بعد الشهر السادس في الأبقار)",
        "reason": "الكورتيكوستيرويدات تحاكي إشارة إفراز الكورتيزول الجنيني الطبيعية التي تحفز بدء الولادة؛ تؤدي إلى هبوط البروجسترون وزيادة الإستروجين وإفراز البروستاجلاندين (PGF2a) مما يسبب انقباضات رحمية قوية وإجهاض الجنين غير مكتمل النمو، مع شيوع احتباس المشيمة والتهاب الرحم الحاد.",
        "clinical_signs": "نزول السوائل الجنينية، انقباضات رحمية، خروج الجنين ميتاً أو خديجاً غير قادر على الحياة، احتباس أغشية الجنين والتهاب بطانة الرحم.",
        "emergency_antidote": "المنع الصارم: استخدام مضادات الالتهاب غير الستيرويدية الآمنة مثل الفلونيكسين ميغلومين أو الكيتوبروفين كبدائل للكورتيزون في الحوامل. في حال حدوث الإجهاض: علاج احتباس المشيمة بالمضادات الحيوية الرحمية وموسعات عنق الرحم.",
        "references": "Veterinary Reproduction and Obstetrics (Noakes et al.)"
    },

    # =========================================================================
    # 5. RABBITS & SMALL HERBIVORES (الأرانب والقوارض)
    # =========================================================================
    {
        "id": "rabbit_penicillins_oral",
        "species_code": "rabbits",
        "species_name": "الأرانب والقوارض",
        "substance_name": "البنسلينات الفموية ومشتقات البيتالكتام (Oral Penicillins / Amoxicillin / Ampicillin - PLACE)",
        "substance_category": "مضادات حيوية فموية",
        "danger_level": "fatal",
        "danger_level_title": "🔴 نخر وتسمم معوي معوي قاتل بنسبة 100% (Fatal Dysbiosis)",
        "clinical_condition": "إعطاء البنسلين، الأمبيسيلين، الأموكسيسيلين، السيفالوسبورين، اللينكومايسين، أو الإريثرومايسين فموياً",
        "reason": "قاعدة (PLACE Rule: Penicillins, Lincosamides, Ampicillin/Amoxicillin, Cephalosporins, Erythromycin). الجهاز الهضمي للأرانب يعتمد على فلورا موجبة الغرام تخمر الألياف بالأعور. تناول هذه الأدوية فموياً يبيد الفلورا النافعة، مما يفسح المجال لتكاثر كلوستريديا (Clostridium spiroforme) التي تفرز ذيفاناً معوياً إيوتوكسين (Iota-toxin) القاتل.",
        "clinical_signs": "إسهال مائي مخاطي، نزف معوي، انتفاخ هائل في الأعور، انخفاض شديد في درجة الحرارة، ونفوق محتم خلال 24-72 ساعة.",
        "emergency_antidote": "إيقاف الدواء فوراً، محاليل تحت الجلد أو وريدياً، كوليستيرامين (Cholestyramine) فموياً لربط الذيفان الإيوتوكسيني، إطعام قسري بألياف حرجة (Critical Care)، وإعطاء ميترونيدازول لمهاجمة الكلوستريديا.",
        "references": "Ferrets, Rabbits, and Rodents: Clinical Medicine and Surgery (Carpenter & Quesenberry)"
    },
    {
        "id": "rabbit_fipronil",
        "species_code": "rabbits",
        "species_name": "الأرانب",
        "substance_name": "الفيبرونيل (Fipronil / Frontline Spot-on)",
        "substance_category": "مضادات براغيث وقراد الكلاب والقطط",
        "danger_level": "fatal",
        "danger_level_title": "🔴 تشنجات صرعية صاعقة ووفاة مفاجئة",
        "clinical_condition": "وضع قطرات الفيبرونيل على جلد الأرنب لعلاج البراغيث أو الجرب",
        "reason": "الفيبرونيل يخترق جلد الأرانب بمعدل فائق جداً ويصل إلى الجهاز العصبي المركزي بتركيزات سامة، حيث يغلق قنوات الكلور المرتبطة بحمض GABA مسبباً اختلاجات عصبية مستمرة وانهياراً عصبياً وتوقفاً تنفسياً مميتاً.",
        "clinical_signs": "فقدان الشهية والخمول خلال ساعات، يليه تشنجات عضلية عنيفة واهتزازات صرعية، ونفوق سريع.",
        "emergency_antidote": "غسل الجلد فوراً بالماء والصابون اللطيف لإزالة ما تبقى من المادة، حقن المهدئات (ديازيبام أو ميدازولام) للسيطرة على التشنجات، وتوفير العناية الداعمة والسوائل.",
        "references": "BSAVA Small Animal Formulary Part B: Exotic Pets"
    },

    # =========================================================================
    # 6. POULTRY & BIRDS (الدواجن والطيور)
    # =========================================================================
    {
        "id": "poultry_avocado",
        "species_code": "poultry",
        "species_name": "الدواجن والطيور والكناري والبابغاوات",
        "substance_name": "الأفوكادو (Avocado / Persin)",
        "substance_category": "أطعمة وفاكهة نباتية",
        "danger_level": "fatal",
        "danger_level_title": "🔴 فشل عضلات القلب واختناق مميت خلال ساعات",
        "clinical_condition": "تناول أوراق أو قشور أو ثمار الأفوكادو",
        "reason": "تحتوي جميع أجزاء نبات الأفوكادو على مادة البيرسين (Persin)، وهي مركب سام للدهون يسبب تلفاً نخرياً لا رجعة فيه في ألياف عضلة القلب والنسيج الرئوي في جميع فصائل الطيور، يتبعه تجمع مائي حول القلب (Hydropericardium) ووذمة رئوية خانقة.",
        "clinical_signs": "نفش الريش، صعوبة شديدة في التنفس وفتح المنقار، عدم القدرة على الوقوف، ازرقاق العرف، ونفوق صاعق خلال 12-24 ساعة.",
        "emergency_antidote": "إعطاء فحم نشط فوري إن كان الابتلاع في الدقائق الأولى، دعم بالأكسجين ووضع الطائر في حاضنة دافئة وهادئة، ولا يوجد ترياق نوعي للبيرسين.",
        "references": "Avian Medicine: Principles and Application (Ritchie et al.)"
    },
    {
        "id": "poultry_teflon",
        "species_code": "poultry",
        "species_name": "الدواجن والطيور والبابغاوات المنزلية",
        "substance_name": "أبخرة أواني التيفلون المحروقة (PTFE / Polytetrafluoroethylene Fumes)",
        "substance_category": "أبخرة وأواني طهي منزلية",
        "danger_level": "fatal",
        "danger_level_title": "🔴 نزيف رئوي واختناق فوري في ثوانٍ",
        "clinical_condition": "تسخين أواني التيفلون المانعة للالتصاق بالقرب من أماكن تربية الطيور",
        "reason": "رئات الطيور تحتوي على أكياس هوائية دقيقة وشعيرات دموية فائقة الرقة. عند تسخين التيفلون فوق 280 مئوية تنطلق جزيئات متناهية الصغر من غاز التيترافلوروإيثيلين تسبب تدميراً نخرياً فورياً للحويصلات الهوائية ونزيفاً داخلياً في الرئة بالكامل.",
        "clinical_signs": "سقوط مفاجئ عن المجثم، صعوبة بالغة في التنفس واختناق، خروج سائل مدمم من المنقار، ونفوق فوري في دقائق معدودة.",
        "emergency_antidote": "نقل الطائر فوراً وبأقصى سرعة إلى هواء نقي وجيد التهوية، إعطاء أكسجين رطب 100%، ديوريتيك خفيف (فوروسيميد) لتقليل ارتشاح الرئة، ومضادات التهاب ستيرويدية طارئة.",
        "references": "Current Veterinary Therapy: Avian Practice"
    }
]

def get_all_species_list() -> list:
    """Returns list of supported animal species with icons and codes."""
    return list(SPECIES_METADATA.values())

def get_contraindications_by_species(species_code: str = "all", category: str = "all", query: str = "") -> list:
    """
    Returns filtered list of contraindications based on species code, category, and search text.
    """
    results = []
    clean_q = (query or "").strip().lower()

    for item in CONTRAINDICATIONS_DB:
        # 1. Match Species
        if species_code and species_code != "all":
            if item["species_code"] != species_code and species_code not in item["species_code"]:
                continue

        # 2. Match Category
        if category and category != "all":
            if category not in item["substance_category"]:
                continue

        # 3. Match Search Query
        if clean_q:
            match_name = clean_q in item["substance_name"].lower()
            match_reason = clean_q in item["reason"].lower()
            match_signs = clean_q in item["clinical_signs"].lower()
            match_antidote = clean_q in item["emergency_antidote"].lower()
            match_species = clean_q in item["species_name"].lower()
            match_condition = clean_q in item.get("clinical_condition", "").lower()
            if not (match_name or match_reason or match_signs or match_antidote or match_species or match_condition):
                continue

        results.append(item)

    return results

def search_contraindications(query: str, limit: int = 15) -> list:
    """Fast search for universal search integration."""
    return get_contraindications_by_species(species_code="all", query=query)[:limit]
