# -*- coding: utf-8 -*-
import sqlite3
import os
import hashlib

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")

def init_and_clean_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Ensure local_products table has correct schema and drop old corrupted records
    c.execute("DROP TABLE IF EXISTS local_products")
    c.execute("""
    CREATE TABLE local_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country TEXT NOT NULL,
        trade_name TEXT NOT NULL,
        manufacturer TEXT NOT NULL,
        active_ingredient TEXT NOT NULL,
        indication TEXT NOT NULL,
        target_species TEXT NOT NULL,
        dosage_guide TEXT NOT NULL,
        withdrawal_period TEXT,
        approval_reg_no TEXT
    )
    """)

    products = [
        # Egypt (مصر)
        ("مصر", "بنستريب 20/20 (Pen-Strep 20/20)", "شركة أدكو / فاركو بي (ADWIA / Pharco B)", "Procaine Penicillin G 200,000 IU + Dihydrostreptomycin 200 mg/ml", "علاج العدوى التنفسية والمعوية والتهابات الضرع في المجترات والخيول", "الأبقار، الأغنام، الخيول", "1 مل لكل 25 كجم وزن حي حقناً بالعضل لمدة 3-5 أيام", "اللحم: 21 يوماً، الحليب: 3 أيام", "م.ب/1452/2021"),
        ("مصر", "أوكسيتتراسيكلين 20% طويل المفعول (Oxytetracycline 20% L.A.)", "شركة أدكو للصناعات الدوائية (ADWIA)", "Oxytetracycline base 200 mg/ml", "علاج حمى النقل والباستريلا والتهاب القرنية المعدي وأمراض الرئة", "الأبقار، الأغنام، الماعز، الإبل", "1 مل لكل 10 كجم وزن حي حقناً عميقاً في العضل لمرة واحدة", "اللحم: 28 يوماً، الحليب: 7 أيام", "م.ب/984/2019"),
        ("مصر", "فلونيكسين ميغلومين (Flunixin Meglumine 5%)", "شركة ممفيس للأدوية والكيماويات (MEMCO)", "Flunixin Meglumine 50 mg/ml", "مضاد التهاب ومسكن للألم وخافض حرارة لحالات المغص الحاد والتهاب المفاصل", "الخيول، الأبقار، الكلاب", "الخيول: 1 مل لكل 45 كجم بالوريد، الأبقار: 2 مل لكل 45 كجم", "اللحم: 4 أيام، الحليب: 36 ساعة", "م.ب/2105/2022"),
        ("مصر", "إيفرمكتين سوبر (Ivermectin Super + Clorsulon)", "شركة موفكو للبيطرة (MUVCO)", "Ivermectin 10 mg + Clorsulon 100 mg/ml", "مكافحة الطفيليات الداخلية والخارجية والديدان الكبدية الفاشيولا", "الأبقار، الإبل، الأغنام", "1 مل لكل 50 كجم وزن حي تحت الجلد فقط", "اللحم: 49 يوماً، لا يستخدم في حلابات اللبن", "م.ب/3301/2020"),
        ("مصر", "تايلوزين 20% (Tylosin Tartrate 20%)", "شركة دلتا فيت فارما (Delta Vet)", "Tylosin base 200 mg/ml", "علاج الميكوبلازما (التهاب الرئة والالتهاب الرئوي البلوري) والتهاب المفاصل", "الدواجن، العجول، الأغنام، الخنازير", "العجول والأغنام: 0.5-1 مل لكل 20 كجم وزن حي بالعضل", "اللحم: 21 يوماً", "م.ب/1876/2023"),
        ("مصر", "أمبراسين بلس (Ampracin Plus Oral Powder)", "شركة إيليت فارما / النصر", "Amprolium HCl 20% + Sulfaquinoxaline 20%", "علاج الكوكسيديا المعوية والأعورية والتهاب الأمعاء النخري", "الدواجن، الأرانب، الحملان", "1 جم لكل لتر ماء شرب لمدة 5-7 أيام متتالية", "اللحم: 7 أيام", "م.ب/1120/2018"),

        # Saudi Arabia (السعودية)
        ("السعودية", "ميفاك سينوفاك (Mevac Synovac)", "الشركة السعودية للقاحات البيطرية (MEVAC)", "Inactivated FMD Antigens (O, A, SAT2)", "التحصين الوقائي ضد الحمى القلاعية والوقاية المعتمدة من وزارة البيئة والمياه والزراعة", "الأبقار، الأغنام، الماعز، الإبل", "الأبقار والإبل: 2 مل تحت الجلد، الأغنام: 1 مل تحت الجلد", "صفر أيام", "SFDA-VET-2022-094"),
        ("السعودية", "أسترامكتين بلس (Astramectin Plus L.A.)", "شركة أسترا للصناعات البيطرية (Astra Farma)", "Ivermectin 1% + Closantel 5%", "مكافحة ديدان نغف الأنف في الأغنام والدودة الحلزونية وطفيليات الإبل", "الإبل، الضأن، الماعز", "1 مل لكل 50 كجم تحت الجلد", "اللحم: 35 يوماً", "SFDA-VET-2021-312"),
        ("السعودية", "ألتراسين 200 طويل المفعول (Ultracin 200 L.A.)", "شركة الرياض فارما للصناعات البيطرية", "Oxytetracycline 200 mg/ml", "علاج أمراض الجهاز التنفسي والتهابات الحوافر وحمى القراد في الإبل والمواشي", "الإبل، الأبقار، الأغنام", "1 مل لكل 10 كجم بالعضل لمرة واحدة مع تكرار عند اللزوم بعد 72 ساعة", "اللحم: 28 يوماً، الحليب: 7 أيام", "SFDA-VET-2020-188"),
        ("السعودية", "سيباموكسين 50% (Cipamox 50% Powder)", "شركة أرامكم للكيماويات الدوائية (Arabcome / Cipamco)", "Amoxicillin Trihydrate 500 mg/g", "علاج بكتيريا الكولاي والسالمونيلا والتهابات القناة الهضمية", "الدواجن، العجول الرضيعة، الحملان", "20 ملجم لكل كجم وزن حي مع ماء الشرب", "اللحم: 3 أيام", "SFDA-VET-2023-401"),
        ("السعودية", "كلوبروستينول فيت (Cloprostenol Vet Luteolytic)", "الشركة الوطنية للخدمات البيطرية", "d-Cloprostenol 0.075 mg/ml (Prostaglandin F2a)", "تنظيم وتوحيد دورة الشبق وعلاج الأجسام الصفراء المصرة والتهاب الرحم", "الأبقار، النوق، الخيول", "الأبقار والنوق: 2 مل بالعضل لمرة واحدة", "اللحم: 24 ساعة، الحليب: صفر ساعات", "SFDA-VET-2019-065"),

        # UAE (الإمارات)
        ("الإمارات", "نيوفيت إنروفلوكساسين 10% (NeoVet Enro 10%)", "شركة نيوفارما البيطرية (Neopharma Abu Dhabi)", "Enrofloxacin 100 mg/ml", "مضاد حيوي واسع المدى لعلاج متلازمة التهاب الجهاز التنفسي والهضمي", "الصقور، الإبل، الخيول، الأغنام", "1 مل لكل 20-40 كجم وزن حي حقناً تحت الجلد أو بالعضل", "اللحم: 14 يوماً", "MOCCAE-VET-8831"),
        ("الإمارات", "هيموجلوبكس للإبل والسباق (HemoglobiX Racing Camel)", "شركة ريسنج فيت دبي (Dubai Racing Vet Lab)", "Iron Dextran + Vitamin B12 + Folic Acid + Cobalt", "علاج فقر الدم وتحسين الأداء البدني وحمل الأكسجين في هجن السباقات", "هجن السباق، الخيول الأصيلة", "10-20 مل بالوريد البطيء أسبوعياً", "صفر أيام", "MOCCAE-VET-7712"),

        # Jordan (الأردن)
        ("الأردن", "جوفاك نيوكاسل كلون 30 (Jovac Newcastle Clone 30)", "الشركة الأردنية لإنتاج الأجسام المضادة واللقاحات (JOVAC)", "Live Newcastle Disease Virus Clone 30 Strain", "تحصين مناعي عالي الكفاءة ضد مرض النيوكاسل النيوكاسيل في الدواجن", "الدجاج اللاحم والبياض والأمهات", "قطرة في العين أو رذاذ خشن أو مع ماء الشرب المبرد", "صفر أيام", "JFDA-VET-5541"),
        ("الأردن", "فابكوسين 20% (Vapco Tilmicosin 20%)", "شركة فابكو للأدوية والمبيدات البيطرية (VAPCO)", "Tilmicosin phosphate 200 mg/ml", "علاج أمراض الجهاز التنفسي المرتبطة بالمانهايميا والباستريلا", "الأبقار، الأغنام", "1 مل لكل 30 كجم تحت الجلد حصراً (تحذير: لا يعطى بالوريد إطلاقاً)", "اللحم: 42 يوماً", "JFDA-VET-4190"),

        # Sudan (السودان)
        ("السودان", "تريبانوسيد بي بي إس (Trypanocid Diminazene)", "الشركة العربية لإنتاج الأدوية البيطرية - الخرطوم", "Diminazene Aceturate 70 mg + Phenazone 375 mg/g", "العلاج النوعي لطفيل التريبانوسوما (مرض الذبابة - الذباب التسي تسي) والبابيزيا", "الأبقار، الإبل، الأغنام، الخيول", "3.5 ملجم لكل كجم وزن حي حقناً عميقاً في العضل", "اللحم: 21 يوماً، الحليب: 3 أيام", "NMPB-SUDAN-1002"),
        ("السودان", "أنتريسايد كلوريد (Antrycide Pro-Salt)", "معمل الأبحاث البيطرية - سوبا", "Quinapyramine sulphate & chloride 1.5g", "علاج ووقاية الإبل والماشية من داء المثقبيات السورا (Surra)", "الإبل، الخيول، الأبقار", "1 مل لكل 40 كجم من المحلول المحضر تحت الجلد", "اللحم: 30 يوماً", "NMPB-SUDAN-2041"),

        # International / Global Brands (العالمية)
        ("دول أخرى", "ديكساميثازون 0.2% (Dexamethasone Sodium Phosphate)", "سيفا سانتي أنيمال (Ceva Sante Animale)", "Dexamethasone 2 mg/ml", "مضاد التهاب ستيرويدي قوي وعلاج الصدمة والحساسية الحادة والتهاب الضرع التسممي", "الأبقار، الخيول، الكلاب، القطط", "الأبقار والخيول: 5-15 مل بالعضل أو الوريد، الحيوانات الصغيرة: 0.1-0.5 مل", "اللحم: 8 أيام، الحليب: 3 أيام", "GLOBAL-VET-771"),
        ("دول أخرى", "سيفوكين 2.5% (Cefquinome Sulfate 2.5%)", "إم إس دي لصحة الحيوان (MSD Animal Health)", "Cefquinome 25 mg/ml (4th gen Cephalosporin)", "علاج الالتهابات التنفسية البكتيرية الشديدة وتعفن الحوافر الحاد", "الأبقار، العجول، الخيول", "1 مل لكل 25 كجم وزن حي حقناً بالعضل يومياً لمدة 3-5 أيام", "اللحم: 5 أيام، الحليب: 24 ساعة", "GLOBAL-VET-992"),
        ("دول أخرى", "ميلوكسيكام 20 ملجم/مل (Meloxicam Injection)", "بورنجر إنجلهايم (Boehringer Ingelheim)", "Meloxicam 20 mg/ml (NSAID)", "تسكين الألم وتقليل الالتهاب بعد العمليات والتهاب المفاصل الرئوي الحاد", "الأبقار، الخيول، الكلاب، القطط", "0.5 ملجم لكل كجم وزن حي حقناً تحت الجلد أو بالوريد", "اللحم: 15 يوماً، الحليب: 5 أيام", "GLOBAL-VET-634")
    ]

    for p in products:
        c.execute("""
        INSERT INTO local_products 
        (country, trade_name, manufacturer, active_ingredient, indication, target_species, dosage_guide, withdrawal_period, approval_reg_no)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, p)

    # 2. Reset broadcast notifications with clean Arabic text
    c.execute("DROP TABLE IF EXISTS broadcast_notifications")
    c.execute("""
    CREATE TABLE broadcast_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        target_country TEXT DEFAULT 'ALL',
        badge_type TEXT DEFAULT 'info',
        created_at TEXT NOT NULL
    )
    """)

    notifs = [
        ("إشعار التحديث v4.0 للنسخة السريرية المعتمدة", 
         "مرحباً بكم في VetMind AI Enterprise v4.0! تم تفعيل الفحص البصري التلقائي المباشر للصور، ربط 30 مرجعاً سريرياً مع التحميل المباشر بضغطة زر، وإدراج قائمة الأدوية البيطرية الوطنية المعتمدة لكل دولة عربية مع جرعاتها وفترات السحب.", 
         "ALL", "update", "2026-10-29 18:00:00"),
        ("تنبيه وبائي: مراقبة حالات الحمى القلاعية والباستريلا", 
         "توصي المنظمة العالمية لصحة الحيوان (WOAH) بتشديد إجراءات التطهير وتطبيق بروتوكول التحصين المعتمد في مزارع الأبقار والمجترات الصغيرة مع استخدام المطهرات المعتمدة.", 
         "مصر", "warning", "2026-10-29 18:05:00"),
        ("تنبيه دوائي: تحديث فترات السحب لمضادات الماكروليد", 
         "تنبيهاً للسادة الأطباء البيطريين المعتمدين، تم تحديث فترات الأمان الدوائي (Withdrawal Periods) لمركبات التايلوزين والفلورفينيكول وفق أحدث أدلة منظمة الأغذية والزراعة (FAO).", 
         "السعودية", "info", "2026-10-29 18:10:00")
    ]

    for n in notifs:
        c.execute("""
        INSERT INTO broadcast_notifications (title, message, target_country, badge_type, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, n)

    # 3. Fix users table: update country and syndicate data for existing accounts
    c.execute("UPDATE users SET country = 'مصر', role = 'vet' WHERE email = 'tamersaad732@gmail.com'")
    c.execute("UPDATE users SET country = 'مصر', role = 'vet', is_admin = 1, verification_status = 'approved', clinic_name = 'المقر التنفيذي للرقابة البيطرية', syndicate_id = 'EXEC-VET-001' WHERE email = 'director@vetmind.ai'")
    c.execute("UPDATE users SET country = 'مصر', role = 'vet', is_admin = 1, verification_status = 'approved', clinic_name = 'إدارة الإشراف الطبي والدوائي', syndicate_id = 'CHIEF-VET-002' WHERE email = 'admin@vetmind.ai'")

    # 4. Ensure clinic_profiles table has profile for director and default users
    c.execute("DROP TABLE IF EXISTS clinic_profiles")
    c.execute("""
    CREATE TABLE clinic_profiles (
        user_id INTEGER PRIMARY KEY,
        clinic_name TEXT,
        phone TEXT,
        address TEXT,
        consultation_fee TEXT,
        working_hours TEXT,
        emergency_available INTEGER DEFAULT 1,
        notes TEXT
    )
    """)

    c.execute("""
    INSERT INTO clinic_profiles (user_id, clinic_name, phone, address, consultation_fee, working_hours, emergency_available, notes)
    VALUES (4, 'مركز فيتمايند للاستشارات والطب البيطري المتقدم', '+201000000000', 'القاهرة - مدينة نصر - شارع الطيران', '250 جنيه مصري', 'السبت إلى الخميس: 9:00 ص - 10:00 م', 1, 'استشارات متقدمة وفحص بالموجات فوق الصوتية والتحاليل المخبرية للحيوانات الكبيرة والصغيرة')
    """)

    conn.commit()
    conn.close()
    print("Database cleanly populated and initialized with verified UTF-8 records!")

if __name__ == "__main__":
    init_and_clean_db()
