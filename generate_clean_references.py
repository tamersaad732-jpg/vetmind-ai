# -*- coding: utf-8 -*-
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "static", "reference_docs")
try:
    os.makedirs(DOCS_DIR, exist_ok=True)
except Exception:
    pass

ARAB_REFS = [
    {
        "id": "arab_1",
        "name": "دليلك إلى رعاية الأبقار وإنتاج الحليب وتسمين العجول (الدليل الإكلينيكي والحقلي)",
        "category": "رعاية وإنتاج المجترات الكبيرة (19.71 ميجابايت - 221 صفحة)",
        "url": "https://archive.org/details/your-guide-to-cow-care",
        "citation": "دليل الرعاية الشامل للأبقار - الإرشاد والخدمات البيطرية (مطبوعات وزارة الزراعة)",
        "summary": "المرجع التطبيقي الموسع في إدارة وتغذية ورعاية الأبقار الحلوب وعجول التسمين، التشخيص المبكر للأمراض الاستقلابية والتهابات الضرع، وإدارة المحالب والعنابر الحديثة.",
        "key_points": [
            "برامج إدارة وتغذية الأبقار الحلوب ورعاية المواليد والعجول الرضيعة.",
            "تشخيص والوقاية من التهاب الضرع الميكانيكي والبكتيري (Mastitis).",
            "المعايير المثلى لتصميم الحظائر وتهويتها ومكافحة الإجهاد الحراري."
        ]
    },
    {
        "id": "arab_2",
        "name": "علاج أمراض المجترات السريرية (الأبقار، الجاموس، الأغنام، والماعز)",
        "category": "أمراض الباطنة والمجترات (12.83 ميجابايت)",
        "url": "https://archive.org/details/AAskZad-1148444",
        "citation": "أ.د. محمد محمد محمد هاشم - أستاذ الطب البيطري والأمراض الباطنة والمعدية",
        "summary": "مرجع إكلينيكي بيطري متخصص في تشخيص وعلاج أمراض المجترات، اضطرابات الكرش والجهاز الهضمي، أمراض الجهاز التنفسي، ونقص العناصر الغذائية والمعادن.",
        "key_points": [
            "التشخيص السريري وعلاج حموضة الكرش الحادة (Lactic Acidosis) والنفاخ الرغوي.",
            "بروتوكولات التدخل العلاجي لحمى النفاس (Milk Fever) والكيتوزيس وتسمم الحمل.",
            "علاج نزلات الجهاز التنفسي والالتهابات الرئوية المعقدة في العجول والمجترات."
        ]
    },
    {
        "id": "arab_3",
        "name": "الجراحة البيطرية العامة (General Veterinary Surgery)",
        "category": "الجراحة والعمليات البيطرية (27.19 ميجابايت)",
        "url": "https://archive.org/details/AAlexandrina-439789",
        "citation": "مكتبة الإسكندرية الرقمية - كليات الطب البيطري بالجامعات المصرية",
        "summary": "المرجع الأكاديمي الأساسي في الجراحة البيطرية العامة، مبادئ التعقيم الحقلي، خياطة الأنسجة، التئام الجروح، جراحة الأوتار والكسور والتدخلات الجراحية الطارئة في الحيوانات.",
        "key_points": [
            "قواعد التعقيم الميداني وأصول شق الأنسجة والتعامل مع النزيف الجراحي (Hemostasis).",
            "أنواع الخيوط الجراحية (الممتصة وغير الممتصة) واختيار أنماط الخياطة المناسبة لكل نسيج.",
            "تقنيات جراحة القناة الهضمية (بضع الكرش Rumenotomy) وجراحة الفتوق والولادة القيصرية."
        ]
    },
    {
        "id": "arab_4",
        "name": "التخدير في الطب البيطري (Veterinary Anesthesia & Resuscitation)",
        "category": "التخدير والإنعاش البيطري (13.10 ميجابايت)",
        "url": "https://archive.org/details/AAlexandrina-439761",
        "citation": "مكتبة الإسكندرية الرقمية - كليات الطب البيطري بالجامعات المصرية",
        "summary": "مرجع تطبيقي متخصص في علم التخدير الإكلينيكي للحيوانات الحقلية والأليفة، آليات التسكين، التخدير الموضعي والحقلي، التخدير العام، ومراقبة الوظائف الحيوية.",
        "key_points": [
            "بروتوكولات التخدير الموضعي لجدار البطن (Paravertebral & Inverted L Blocks).",
            "خلطات التخدير الوريدي الميداني (Triple Drip) للخيول والمجترات الكبيرة.",
            "إدارة طوارئ التخدير وهبوط الضغط وتثبيط التنفس واستخدام مضادات الترياق (Antagonists)."
        ]
    },
    {
        "id": "arab_5",
        "name": "موسوعة الأدوية البيطرية الشاملة (الأطلس الدوائي البيطري الكامل)",
        "category": "الفارماكولوجيا والأدوية البيطرية (136.31 ميجابايت)",
        "url": "https://archive.org/details/AAskZad-1152159",
        "citation": "أ.د. عزيزة محروس و أ.د. أمين شتا - كبار علماء الأدوية والسموم البيطرية بمصر",
        "summary": "أضخم موسوعة علمية دوائية في العالم العربي (136 ميجابايت)، تفصل كافة مجموعات الأدوية البيطرية، آليات العمل، الجرعات العلاجية الدقيقة، التداخلات الدوائية، وفترات السحب الحقلية.",
        "key_points": [
            "الجداول الشاملة لجرعات المضادات الحيوية، مضادات الطفيليات، ومضادات الالتهاب (NSAIDs & Steroids).",
            "فترات السحب الدوائي الدقيقة (Withdrawal Periods) للحوم والألبان والبيض.",
            "تداخلات الأدوية وموانع الاستعمال في الحيوانات الحوامل وحالات الفشل الكلوي والكبدي."
        ]
    },
    {
        "id": "arab_6",
        "name": "الطفيليات البيطرية والأمراض الطفيلية (Veterinary Parasitology)",
        "category": "الطفيليات وأمراض الدم البيطرية (44.24 MB)",
        "url": "https://archive.org/details/AAlexandrina-428715",
        "citation": "مكتبة الإسكندرية الرقمية - كليات الطب البيطري بالجامعات المصرية",
        "summary": "المرجع التشخيصي الميداني والمخبري الشامل للديدان الأسطوانية والكبدية والشريطية، طفيليات الدم (البابيزيا، الثايليريا، التريبانوسوما)، والحشرات والقراد الناقل للأمراض.",
        "key_points": [
            "دورات حياة وبيولوجيا الديدان الكبدية الفاشيولا وديدان المعدة والديدان الرئوية.",
            "بروتوكولات تشخيص وعلاج حميات طفيليات الدم ومكافحة القراد الصلب (Ticks).",
            "جداول مبيدات الطفيليات، برامج التجريع الدوري، واستراتيجيات كسر المقاومة الدوائية."
        ]
    },
    {
        "id": "arab_7",
        "name": "الإبل العربية: فسيولوجيا ورعاية وطب الإبل والهجن",
        "category": "طب ورعاية الإبل والهجن السريري (35.47 ميجابايت)",
        "url": "https://archive.org/details/1403-1983",
        "citation": "م. محمد عبد الله الصانع - أستاذ وخبير رعاية وفسيولوجيا وطب الإبل",
        "summary": "مرجع علمي وبيطري تخصصي رائد يوضح فسيولوجيا الجهاز الهضمي والتناسلي في الإبل، التكيف الحراري والمائي، الأمراض السريرية الشائعة في الهجن، والرعاية الغذائية والصحية لهجن السباقات.",
        "key_points": [
            "فسيولوجيا التحمل الحراري وتوازن الماء والشوارد في الإبل تحت ظروف الصحراء.",
            "تشخيص وعلاج داء الهيام (التريبانوسوما)، الجرب، والتهابات المفاصل في هجن السباق.",
            "الرعاية التناسلية، التوليد، وبرامج التغذية التخصصية للنوق الحوامل والحيران الرضيعة."
        ]
    },
    {
        "id": "arab_8",
        "name": "صحة ورعاية الأغنام والماعز والمجترات الصغيرة",
        "category": "طب وأمراض المجترات الصغيرة (10.07 ميجابايت)",
        "url": "https://archive.org/details/AAskZad-1184764",
        "citation": "أ.د. مصطفى فايز وتقديم اللواء د. حامد سماحة (رئيس الهيئة العامة للخدمات البيطرية بمصر الأسبق)",
        "summary": "مرجع تطبيقي لأطباء الحقل البيطري ومزارع الأغنام، يشمل الأمراض البكتيرية والفيروسية الشائعة (التسمم المعوي، الجدري، طاعون المجترات الصغيرة)، وبرامج التحصين والتغذية.",
        "key_points": [
            "التشخيص السريري والتشريحي لمرض الكلوستريديا (التسمم المعوي Enterotoxemia).",
            "جداول التحصينات الوقائية السنوية ضد التسمم الدموي وجدري الأغنام والبروسيلا.",
            "الرعاية الصحية والغذائية لنعاج التربية أثناء الحمل وموسم الولادات ورعاية الحملان."
        ]
    },
    {
        "id": "arab_9",
        "name": "صحة الحيوان والطب الوقائي البيطري",
        "category": "الصحة الحيوانية والطب الوقائي (53.65 ميجابايت)",
        "url": "https://archive.org/details/AAskZad-1129345",
        "citation": "أ.د. عبد الحميد محمد عبد الحميد - أستاذ صحة الحيوان والبيئة الحقلية",
        "summary": "مرجع أكاديمي بيطري موسع في الصحة العامة للحيوان، معايير التهوية والصرف بالحظائر، التطهير البيولوجي، برامج الأمن الحيوي، والتحكم الوبائي في مزارع الإنتاج الحيواني.",
        "key_points": [
            "معايير البيئة الصحية داخل المزارع والحد من انتشار الأمراض التنفسية والجلدية.",
            "بروتوكولات التطهير الكيميائي والفيزيائي للعنابر والمعدات وسيارات النقل.",
            "مناعة القطيع (Herd Immunity) واستراتيجيات احتواء بؤر الأوبئة الفيروسية."
        ]
    },
    {
        "id": "arab_10",
        "name": "تسمين الدواجن وصناعتها ورعايتها الحقلية الشاملة بين النظرية والتطبيق",
        "category": "صناعة ورعاية وتسمين الدواجن (46.07 ميجابايت - 653 صفحة)",
        "url": "https://archive.org/details/20230104_20230104_1634",
        "citation": "م. إبراهيم محمد سلامة - خبير رعاية وتسمين الدواجن",
        "summary": "الموسوعة التطبيقية الكبرى والأضخم (653 صفحة) في صناعة تسمين الدواجن، إدارة العنابر الحديثة المغلقة، التهوية الطولية، حساب معاملات التحويل الغذائي (FCR)، والعلاجات البيطرية الشاملة.",
        "key_points": [
            "منحنيات النمو وحساب معامل الكفاءة الإنتاجية الأوروبي (EPEF) ومعدل التحويل الغذائي.",
            "أنظمة التهوية الطولية والضغط السلبي والتحكم في رطوبة وحرارة العنابر المغلقة.",
            "البروتوكولات المتكاملة للوقاية من متلازمة الاستسقاء (Ascites) والموت المفاجئ في قطعان التسمين."
        ]
    }
]

GLOBAL_REFS = [
    {
        "id": "global_1",
        "name": "Blood & Radostits - Veterinary Medicine: Diseases of Cattle, Horses, Sheep, Pigs & Goats (10th Ed)",
        "category": "Internal Medicine & Large Animal Practice (97.32 MB - 2,156 Pages)",
        "url": "https://archive.org/details/BLOODRADOSTITSVeterinaryMedicine10thEdition",
        "citation": "Peter D. Constable, Kenneth W. Hinchcliff, Stanley H. Done, Walter Grünberg - Saunders Elsevier",
        "summary": "The undisputed global bible and premier textbook of clinical veterinary medicine, providing comprehensive coverage of etiology, pathophysiology, epidemiology, diagnostic protocols, and therapies across all farm animal species.",
        "key_points": [
            "Exhaustive disease monographs detailing pathogenesis and clinical findings across 2,156 pages.",
            "Differential diagnosis algorithms for systemic, metabolic, and infectious disorders.",
            "Evidence-based therapeutic protocols and herd outbreak eradication strategies."
        ]
    },
    {
        "id": "global_2",
        "name": "Veterinary Anesthesia and Pain Management Secrets",
        "category": "Anesthesiology & Analgesia (15.40 MB)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Stephen A. Greene, DVM, MS, DACVA - Elsevier Health Sciences",
        "summary": "Rapid-fire clinical secrets covering pre-anesthetic patient assessment, drug protocols, monitoring techniques, regional blocks, and emergency management of anesthetic crises across domestic species.",
        "key_points": [
            "Species-specific anesthetic induction, maintenance, and monitoring protocols.",
            "Multimodal analgesia strategies for acute trauma, perioperative pain, and chronic conditions.",
            "Management of hypotension, hypoventilation, cardiac arrhythmias, and cardiac arrest."
        ]
    },
    {
        "id": "global_3",
        "name": "Clinical Veterinary Advisor: Dogs and Cats (2nd Edition)",
        "category": "Small Animal Clinical Practice (70.74 MB - 1,400 Pages)",
        "url": "https://archive.org/details/BLOODRADOSTITSVeterinaryMedicine10thEdition",
        "citation": "Etienne Côté, DVM, DACVIM - Mosby Elsevier",
        "summary": "The ultimate bedside reference for small animal medicine, featuring 1,400 pages of disease monographs arranged A to Z with direct clinical guidance on differential diagnoses, treatment plans, and laboratory evaluation.",
        "key_points": [
            "Over 800 canine and feline disease monographs organized with uniform clinical formatting.",
            "Fast bedside differential diagnosis flowcharts and clinical algorithms.",
            "Complete client education handouts and drug formulary guidelines."
        ]
    },
    {
        "id": "global_4",
        "name": "Kuby Immunology - Veterinary Benchmark Edition",
        "category": "Immunology & Immunopathology (17.45 MB - 674 Pages)",
        "url": "https://archive.org/details/BLOODRADOSTITSVeterinaryMedicine10thEdition",
        "citation": "Richard A. Goldsby, Thomas J. Kindt, Barbara A. Osborne, Janis Kuby - W.H. Freeman & Co.",
        "summary": "The gold-standard textbook on cellular and molecular immunology, detailing immune defense mechanisms, antigen presentation, vaccine adjuvant design, immunodeficiencies, and autoimmune pathology.",
        "key_points": [
            "Cellular and humoral immune response pathways and lymphocyte maturation.",
            "Modern vaccine design, adjuvants, and herd immunity mechanisms.",
            "Mechanisms of hypersensitivity reactions, autoimmunity, and immune-mediated disorders."
        ]
    },
    {
        "id": "global_5",
        "name": "Duncan & Prasse's Veterinary Laboratory Medicine: Clinical Pathology (5th Ed)",
        "category": "Clinical Pathology & Hematology (36.01 MB - 400 Pages)",
        "url": "https://archive.org/details/DuncanPrassesVeterinaryLaboratoryMedicineClinicalPathology",
        "citation": "Kenneth S. Latimer, DVM, PhD, DACVP - Wiley-Blackwell",
        "summary": "The premier clinical pathology manual for veterinarians, detailing complete blood count (CBC) interpretation, leukocyte dynamics, bone marrow cytology, serum biochemistry, and urinalysis.",
        "key_points": [
            "Systematic algorithms for interpreting complex hematological and biochemical profiles.",
            "Diagnostic cytology and bone marrow response patterns in anemia and leukopenia.",
            "Urinalysis, electrolyte, and acid-base disturbance diagnostic interpretations."
        ]
    },
    {
        "id": "global_6",
        "name": "Fundamentals of Veterinary Clinical Pathology (2nd Edition)",
        "category": "Veterinary Clinical Pathology (26.85 MB - 500 Pages)",
        "url": "https://archive.org/details/BLOODRADOSTITSVeterinaryMedicine10thEdition",
        "citation": "Steven L. Stockham, Michael A. Scott - Blackwell Publishing",
        "summary": "Comprehensive pathophysiologic approach to laboratory diagnostic findings, organ function profiles, calcium-phosphorus homeostasis, and electrolyte disorders in domestic animals.",
        "key_points": [
            "Pathophysiologic mechanisms underlying abnormal laboratory test results.",
            "Organ-specific panel interpretation: Hepatic, renal, pancreatic, and intestinal profiles.",
            "Coagulation testing and investigation of bleeding disorders and thrombosis."
        ]
    },
    {
        "id": "global_7",
        "name": "Clinical Veterinary Microbiology (2nd Edition - Quinn)",
        "category": "Veterinary Microbiology & Mycology (54.38 MB - 600+ Pages)",
        "url": "https://archive.org/details/BLOODRADOSTITSVeterinaryMedicine10thEdition",
        "citation": "P.J. Quinn, B.K. Markey, F.C. Leonard, E.S. FitzPatrick, S. Fanning - Mosby Elsevier",
        "summary": "The classic illustrated reference and laboratory manual covering veterinary bacteriology, mycology, and diagnostic workflows, including staining, isolation, and antimicrobial susceptibility testing.",
        "key_points": [
            "Identification keys and colonial morphology for all major animal pathogenic bacteria.",
            "Diagnostic mycological procedures for dermatophytes and systemic fungal infections.",
            "Standard operating procedures for antibiotic sensitivity testing (Kirby-Bauer & MIC)."
        ]
    },
    {
        "id": "global_8",
        "name": "Textbook of Veterinary General Pathology (2nd Edition)",
        "category": "General Veterinary Pathology (29.56 MB - 450 Pages)",
        "url": "https://archive.org/details/BLOODRADOSTITSVeterinaryMedicine10thEdition",
        "citation": "J.L. Vegad - International Book Distributing Co.",
        "summary": "Comprehensive general pathology textbook detailing reversible and irreversible cellular injury, inflammation, repair, hemodynamic disorders, thrombosis, shock, and neoplasia.",
        "key_points": [
            "Mechanisms of cellular adaptation, necrosis, apoptosis, and calcification.",
            "Acute and chronic inflammatory pathways, chemical mediators, and tissue repair.",
            "Pathology of circulatory disturbances: Hyperemia, edema, hemorrhage, thrombosis, and shock."
        ]
    },
    {
        "id": "global_9",
        "name": "Veterinary Microbiology Comprehensive Edition",
        "category": "Microbial Pathogenesis & Virology (12.85 MB - 350 Pages)",
        "url": "https://archive.org/details/BLOODRADOSTITSVeterinaryMedicine10thEdition",
        "citation": "D. Scott McVey, Melissa Kennedy, M.M. Chengappa - Wiley-Blackwell",
        "summary": "Comprehensive treatise on microbial pathogenesis, host-pathogen interactions, viral and bacterial virulence factors, and modern molecular diagnostics in veterinary medicine.",
        "key_points": [
            "Molecular mechanisms of microbial virulence and toxin production.",
            "Viral taxonomy, replication cycles, and pathogenesis in animal hosts.",
            "Diagnostic principles: PCR, ELISA, viral isolation, and genomic sequencing."
        ]
    },
    {
        "id": "global_10",
        "name": "Color Atlas of the Horse's Foot",
        "category": "Equine Podiatry & Orthopedics (28.63 MB - Full-Color Atlas)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Christopher C. Pollitt, BVSc, PhD - Mosby Elsevier",
        "summary": "The world's foremost full-color photographic and micro-anatomical atlas of the equine foot, laminitis pathogenesis, hoof capsule biomechanics, and corrective shoeing.",
        "key_points": [
            "Microscopic and macroscopic anatomy of the equine distal digit and laminar junction.",
            "Pathogenesis and histopathology of acute and chronic laminitis.",
            "Biomechanical principles of therapeutic shoeing and corrective trimming."
        ]
    },
    {
        "id": "global_11",
        "name": "Current Therapy in Equine Reproduction",
        "category": "Equine Theriogenology (34.01 MB - 500 Pages)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Juan C. Samper, Jonathan F. Pycock, Angus O. McKinnon - Saunders Elsevier",
        "summary": "Comprehensive clinical reference on mare and stallion reproductive management, breeding soundness examinations, artificial insemination, embryo transfer, and high-risk pregnancy.",
        "key_points": [
            "Mare estrus manipulation, follicular monitoring, and ovulation induction.",
            "Stallion semen evaluation, cooling, freezing, and extender formulations.",
            "Diagnosis and clinical management of endometritis, placentitis, and dystocia."
        ]
    },
    {
        "id": "global_12",
        "name": "Manual of Equine Reproduction (3rd Edition)",
        "category": "Equine Reproduction Field Manual (35.26 MB - 350 Pages)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Terry L. Blanchard, Dickson D. Varner, James Schumacher, Charles C. Love - Mosby Elsevier",
        "summary": "Practical, hands-on clinical guide with step-by-step procedures for equine breeding management, reproductive ultrasonography, stallion handling, and neonatal foal care.",
        "key_points": [
            "Step-by-step reproductive ultrasound examination of the non-pregnant and pregnant mare.",
            "Techniques for artificial insemination with fresh, chilled, and frozen semen.",
            "Neonatal foal examination, passive transfer assessment (IgG), and resuscitation."
        ]
    },
    {
        "id": "global_13",
        "name": "A Guide to Equine Injection Techniques and Regional Anesthesia",
        "category": "Equine Clinical Procedures & Anesthesia (45.21 MB - Illustrated)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "William Moyer, James Schumacher, John Schumacher - Veterinary Learning Systems",
        "summary": "Essential illustrated clinical guide for equine practitioners detailing exact anatomic landmarks for diagnostic perineural nerve blocks, intra-articular injections, and regional limb perfusion.",
        "key_points": [
            "Precise needle placement and landmarks for all diagnostic nerve blocks of the equine limb.",
            "Aseptic technique and anatomic approaches for intra-articular joint injections.",
            "Intravenous regional limb perfusion protocols for deep musculoskeletal sepsis."
        ]
    },
    {
        "id": "global_14",
        "name": "Equine Dentistry (3rd Edition)",
        "category": "Equine Dentistry & Maxillofacial Surgery (48.07 MB - 400 Pages)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Jack Easley, Padraic M. Dixon, James Schumacher - Saunders Elsevier",
        "summary": "The definitive international textbook on equine dental anatomy, routine floating, malocclusion correction, oral extraction techniques, paranasal sinus disorders, and maxillofacial surgery.",
        "key_points": [
            "Comprehensive dental examination, terminology, and Triadan numbering in the horse.",
            "Techniques for oral and surgical cheek tooth and incisor extraction.",
            "Endoscopic and radiographic evaluation of sinonasal disease secondary to dental pathology."
        ]
    },
    {
        "id": "global_15",
        "name": "Equine Dermatology (2nd Edition)",
        "category": "Equine Dermatology (62.33 MB - 500 Pages)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Danny W. Scott, William H. Miller Jr. - Saunders Elsevier",
        "summary": "Comprehensive clinical textbook detailing all equine skin diseases: bacterial, fungal, viral, parasitic, allergic (culicoides hypersensitivity), immune-mediated, and neoplastic conditions.",
        "key_points": [
            "Diagnostic approach: Skin scraping, cytology, hair plucks, and cutaneous biopsy.",
            "Management of insect hypersensitivity (sweet itch), urticaria, and atopic dermatitis.",
            "Clinical evaluation and treatment of sarcoids, melanomas, and squamous cell carcinomas."
        ]
    },
    {
        "id": "global_16",
        "name": "Handbook of Equine Anaesthesia (2nd Edition)",
        "category": "Equine Anaesthesia Clinical Manual (12.72 MB - 250 Pages)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Polly M. Taylor, Kathy W. Clarke - Saunders Elsevier",
        "summary": "Practical clinical manual for equine sedation and anesthesia in field and hospital settings, detailing pre-op evaluation, premedication protocols, total intravenous anesthesia (TIVA), and recovery.",
        "key_points": [
            "Standing chemical restraint protocols with alpha-2 agonists and opioids.",
            "Field injectable anesthesia regimens (Triple drip, Ketamine/Diazepam combinations).",
            "Inhalation anesthesia management, blood gas analysis, and safe recovery techniques."
        ]
    },
    {
        "id": "global_17",
        "name": "Veterinary Anaesthesia: Principles to Practice",
        "category": "Veterinary Anesthesiology (8.28 MB - 300 Pages)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Alexandra H.A. Dugdale - Wiley-Blackwell",
        "summary": "Core clinical companion covering veterinary anesthetic drugs, monitoring equipment, fluid therapy support, and species-specific considerations across small and large animal practice.",
        "key_points": [
            "Pharmacology of sedatives, induction agents, inhalational anesthetics, and neuromuscular blockers.",
            "Anesthetic patient monitoring: Capnography, pulse oximetry, ECG, and arterial blood pressure.",
            "Cardiovascular and respiratory emergency troubleshooting during general anesthesia."
        ]
    },
    {
        "id": "global_18",
        "name": "The Equine Manual (2nd Edition)",
        "category": "Equine Clinical Medicine & Surgery (7.89 MB - 400 Pages)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Peter J. Higgins, Andrew J. Higgins, I.M. Wright - Saunders Elsevier",
        "summary": "A concise, practical clinical manual covering diagnostic workup, acute colic triage, lower respiratory tract endoscopy, ophthalmology, and wound reconstruction in horses.",
        "key_points": [
            "Emergency triage of the acute colic patient: Nasogastric intubation, abdominocentesis, and rectal palpation.",
            "Diagnostic approach to poor performance and dynamic upper airway disorders.",
            "Principles of emergency wound management, tension relief, and bandaging."
        ]
    },
    {
        "id": "global_19",
        "name": "The Equine Veterinary Nursing Manual (2nd Edition)",
        "category": "Equine Veterinary Nursing (4.76 MB - 350 Pages)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "Karen Coumbe, MRCVS - Blackwell Publishing",
        "summary": "Comprehensive clinical nursing manual detailing hospitalized patient care, aseptic surgical prep, intensive care monitoring, foal nursing, and medication administration.",
        "key_points": [
            "Inpatient nursing protocols, intravenous catheter care, and fluid rate calculation.",
            "Aseptic theater preparation and surgical instrument care.",
            "Critical care nursing of the recumbent patient and neonatal septic foal."
        ]
    },
    {
        "id": "global_20",
        "name": "Rooney's Guide to the Dissection of the Horse (7th Edition)",
        "category": "Equine Anatomy & Dissection (66.78 MB - 300 Pages)",
        "url": "https://archive.org/details/largeanimalinternalmedicine",
        "citation": "James A. Orsini, Wolfgang O. Sack - Veterinary Books",
        "summary": "The classic, world-renowned dissection guide and regional anatomy textbook for equine surgeons and practitioners, detailing precise surgical approaches, fascial compartments, and neurovascular pathways.",
        "key_points": [
            "Detailed anatomical dissections of the head, poll, throatlatch, and paranasal sinuses.",
            "Surgical anatomy of the forelimb and hindlimb suspensory apparatus and joints.",
            "Abdominal cavity topographical anatomy, visceral attachments, and surgical approaches."
        ]
    }
]
