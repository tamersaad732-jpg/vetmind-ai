# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Generator for Exhaustive Clinical Veterinary Reference Books
Generates rich, multi-chapter textbooks in both TXT and HTML formats,
updates Desktop library folders, and packages comprehensive ZIP bundles.
"""

import os
import sys
import shutil
import zipfile
from datetime import datetime

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DOCS_DIR = os.path.join(BASE_DIR, "static", "reference_docs")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "static", "downloads")
DESKTOP_DIR = r"C:\Users\tamersaad\Desktop\مكتبة المراجع البيطرية المعتمدة (VetMind Library)"

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(DESKTOP_DIR, exist_ok=True)

DESKTOP_ARAB_DIR = os.path.join(DESKTOP_DIR, "01_المراجع_العربية_المعتمدة")
DESKTOP_GLOBAL_DIR = os.path.join(DESKTOP_DIR, "02_المراجع_الدولية_المعتمدة_Tier1")
os.makedirs(DESKTOP_ARAB_DIR, exist_ok=True)
os.makedirs(DESKTOP_GLOBAL_DIR, exist_ok=True)

sys.path.insert(0, BASE_DIR)
from references_content_data import ARAB_FULL_BOOKS, GLOBAL_FULL_BOOKS
from generate_clean_references import ARAB_REFS, GLOBAL_REFS

def build_txt_monograph(book, is_arab=True):
    now_str = datetime.now().strftime("%Y-%m-%d")
    sep_major = "=" * 80
    sep_minor = "-" * 80

    txt = f"""{sep_major}
   VetMind AI Enterprise - الدليل السريري البيطري المعتمد
   {book['title']}
   المشرف والمراجع العام: دكتور تامر سعد (Dr. Tamer Saad) | تاريخ التحديث: {now_str}
{sep_major}

اسم المرجع العلمي: {book['title']}
الجهة المصدرة والمعتمدة: {book['issuing_body']}
التوثيق الأكاديمي القياسي: {book['citation']}
الرابط الرسمي المعتمد: {book['url']}
الفصائل والأنواع الحيوانية المستهدفة: {book['species']}
المشرف الطبي العام: دكتور تامر سعد (Dr. Tamer Saad)

{sep_minor}
مقدمة وخلاصة المرجع السريري والتنفيذي:
{sep_minor}
{book['summary']}

{sep_minor}
فهرس الأبواب والفصول السريرية التفصيلية:
{sep_minor}
"""
    for i, ch in enumerate(book['chapters'], 1):
        txt += f"[{i:02d}] {ch['title']}\n"

    txt += f"\n{sep_major}\n"

    for i, ch in enumerate(book['chapters'], 1):
        txt += f"""
{sep_minor}
{ch['title']}
{sep_minor}
{ch['content'].strip()}

"""

    txt += f"""{sep_major}
التنبيه الإكلينيكي والتنظيمي وحقوق الاستخدام:
{sep_major}
هذا المرجع السريري المعتمد تم إعداده وتدقيقه خصيصاً لدعم القرار الطبي للأطباء البيطريين
والعيادات والمستشفيات البيطرية تحت إشراف د. تامر سعد.
جميع الجرعات الدوائية وفترات التحريم خاضعة للوائح والتشريعات الدوائية الوطنية.

تم التحقق والاعتماد الرقمي بواسطة:
لجنة التدقيق الإكلينيكي - منصة VetMind AI للذكاء الاصطناعي البيطري
كود التوثيق المشفر: VETMIND-REF-SECURE-{datetime.now().year}
{sep_major}
"""
    return txt

def build_html_book(book, is_arab=True, ref_id=""):
    direction = "rtl" if is_arab else "ltr"
    lang_code = "ar" if is_arab else "en"
    primary_color = "#16a34a" if is_arab else "#0284c7"
    badge_text = "مرجع عربي معتمد 🇪🇬🇸🇦" if is_arab else "Global Tier-1 Reference 🌐"
    now_str = datetime.now().strftime("%Y-%m-%d")

    chapters_html = ""
    toc_html = ""
    for i, ch in enumerate(book['chapters'], 1):
        ch_id = f"chapter_{i}"
        toc_html += f'<li><a href="#{ch_id}">{ch["title"]}</a></li>'
        # Format content paragraphs and bullet points
        raw_text = ch['content'].strip()
        formatted_content = ""
        for line in raw_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("-") or line.startswith("*"):
                formatted_content += f'<li style="margin-bottom: 6px;">{line[1:].strip()}</li>'
            elif line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or line.startswith("4."):
                formatted_content += f'<h4 style="margin: 16px 0 6px 0; color: #0f172a; font-size: 1.05rem;">{line}</h4>'
            else:
                formatted_content += f'<p style="margin-bottom: 8px; line-height: 1.7;">{line}</p>'

        chapters_html += f"""
        <section id="{ch_id}" class="chapter-card">
            <h3 class="chapter-title">{ch['title']}</h3>
            <div class="chapter-body">
                {formatted_content}
            </div>
        </section>
        """

    html = f"""<!DOCTYPE html>
<html lang="{lang_code}" dir="{direction}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{book['title']} - VetMind AI Library</title>
    <style>
        :root {{
            --primary: {primary_color};
            --text: #0f172a;
            --muted: #475569;
            --bg: #f8fafc;
            --border: #e2e8f0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Cairo", Tahoma, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        .no-print {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
            padding: 12px 18px;
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.9rem;
            text-decoration: none;
            cursor: pointer;
            border: none;
            transition: all 0.2s ease;
        }}
        .btn-print {{ background: var(--primary); color: #ffffff; }}
        .btn-print:hover {{ opacity: 0.9; }}
        .btn-back {{ background: #f1f5f9; color: var(--text); border: 1px solid var(--border); }}
        .book-header {{
            background: linear-gradient(135deg, {primary_color} 0%, #0f172a 100%);
            color: #ffffff;
            padding: 35px 30px;
            border-radius: 16px;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.15);
        }}
        .badge {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 12px;
        }}
        .book-title {{
            margin: 0 0 10px 0;
            font-size: 1.85rem;
            font-weight: 800;
            line-height: 1.3;
        }}
        .book-meta {{
            font-size: 0.92rem;
            opacity: 0.92;
            margin-bottom: 6px;
        }}
        .toc-card {{
            background: #ffffff;
            border-radius: 12px;
            padding: 20px 25px;
            margin-bottom: 24px;
            border: 1px solid var(--border);
        }}
        .toc-title {{
            margin: 0 0 12px 0;
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--primary);
            border-bottom: 2px solid var(--border);
            padding-bottom: 8px;
        }}
        .toc-list {{
            margin: 0;
            padding-right: 25px;
        }}
        .toc-list li {{
            margin-bottom: 8px;
        }}
        .toc-list a {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
        }}
        .toc-list a:hover {{
            text-decoration: underline;
        }}
        .chapter-card {{
            background: #ffffff;
            border-radius: 12px;
            padding: 25px 30px;
            margin-bottom: 20px;
            border: 1px solid var(--border);
            border-right: 5px solid var(--primary);
        }}
        .chapter-title {{
            margin: 0 0 16px 0;
            font-size: 1.35rem;
            color: var(--primary);
            font-weight: 800;
            border-bottom: 1px solid var(--border);
            padding-bottom: 10px;
        }}
        .chapter-body {{
            font-size: 0.95rem;
            color: #1e293b;
        }}
        .footer-notice {{
            background: #f1f5f9;
            border-radius: 12px;
            padding: 16px 20px;
            margin-top: 30px;
            font-size: 0.85rem;
            color: var(--muted);
            text-align: center;
            border: 1px solid var(--border);
        }}
        @media print {{
            body {{ padding: 0; background: #ffffff; }}
            .no-print {{ display: none !important; }}
            .chapter-card {{ page-break-inside: avoid; border: 1px solid #ccc; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Floating Navigation & Print Toolbar -->
        <div class="no-print">
            <div style="font-weight: 700; font-size: 0.92rem; color: var(--primary);">
                📖 VetMind AI Clinical Library - Official Electronic Monograph
            </div>
            <div style="display: flex; gap: 10px;">
                <button onclick="window.print()" class="btn btn-print">
                    🖨️ طباعة المرجع / حفظ كـ PDF (Print / Save PDF)
                </button>
                <a href="/references" class="btn btn-back">
                    ⬅️ العودة لقائمة المراجع
                </a>
            </div>
        </div>

        <!-- Book Header -->
        <header class="book-header">
            <div class="badge">{badge_text}</div>
            <h1 class="book-title">{book['title']}</h1>
            <div class="book-meta"><strong>الجهة المعتمدة:</strong> {book['issuing_body']}</div>
            <div class="book-meta"><strong>التوثيق الأكاديمي القياسي:</strong> {book['citation']}</div>
            <div class="book-meta"><strong>الفصائل المستهدفة:</strong> {book['species']}</div>
            <div class="book-meta"><strong>المشرف والمراجع الطبي:</strong> دكتور تامر سعد (Dr. Tamer Saad)</div>
            <div style="margin-top: 15px; font-size: 0.88rem; opacity: 0.9; background: rgba(0,0,0,0.15); padding: 10px 14px; border-radius: 8px;">
                {book['summary']}
            </div>
        </header>

        <!-- Table of Contents -->
        <nav class="toc-card">
            <h2 class="toc-title">📋 فهرس الفصول السريرية</h2>
            <ul class="toc-list">
                {toc_html}
            </ul>
        </nav>

        <!-- Clinical Chapters -->
        <main>
            {chapters_html}
        </main>

        <!-- Official Footer Notice -->
        <footer class="footer-notice">
            جميع الحقوق محفوظة &copy; 2026 لمنظومة VetMind AI للذكاء الاصطناعي الطبي البيطري - تحت إشراف د. تامر سعد<br>
            هذا الدليل الطبي مخصص حصرياً للأطباء البيطريين المرخصين لدعم القرار السريري.
        </footer>
    </div>
</body>
</html>
"""
    return html

def generate_all_exhaustive_materials():
    print("Building full clinical reference books (TXT and HTML) for all 30 references...")

    # 1. Process 10 Arab References
    for ref_id, book in ARAB_FULL_BOOKS.items():
        txt_content = build_txt_monograph(book, is_arab=True)
        html_content = build_html_book(book, is_arab=True, ref_id=ref_id)
        ar_name = book['filename_ar']

        # Static web files
        with open(os.path.join(DOCS_DIR, f"{ref_id}.txt"), "w", encoding="utf-8") as f:
            f.write(txt_content)
        with open(os.path.join(DOCS_DIR, f"{ref_id}.html"), "w", encoding="utf-8") as f:
            f.write(html_content)

        # Desktop folder files
        with open(os.path.join(DESKTOP_ARAB_DIR, f"{ar_name}.txt"), "w", encoding="utf-8") as f:
            f.write(txt_content)
        with open(os.path.join(DESKTOP_ARAB_DIR, f"{ar_name}.html"), "w", encoding="utf-8") as f:
            f.write(html_content)

    print("Completed 10 Arab full books.")

    # 2. Process 20 Global References
    for ref_id, book in GLOBAL_FULL_BOOKS.items():
        txt_content = build_txt_monograph(book, is_arab=False)
        html_content = build_html_book(book, is_arab=False, ref_id=ref_id)
        en_name = book['filename_en']

        # Static web files
        with open(os.path.join(DOCS_DIR, f"{ref_id}.txt"), "w", encoding="utf-8") as f:
            f.write(txt_content)
        with open(os.path.join(DOCS_DIR, f"{ref_id}.html"), "w", encoding="utf-8") as f:
            f.write(html_content)

        # Desktop folder files
        with open(os.path.join(DESKTOP_GLOBAL_DIR, f"{en_name}.txt"), "w", encoding="utf-8") as f:
            f.write(txt_content)
        with open(os.path.join(DESKTOP_GLOBAL_DIR, f"{en_name}.html"), "w", encoding="utf-8") as f:
            f.write(html_content)

    print("Completed 20 Global full books.")

    # 3. Master Indexes
    generate_indexes()

    # 4. Packaging ZIPs
    package_zip_archives()

def generate_indexes():
    print("Generating comprehensive Master Indexes...")
    index_txt = f"""================================================================================
   VetMind AI Enterprise - فهرس مكتبة المراجع السريرية البيطرية الشاملة
   The Comprehensive Master Index of 30 Veterinary Clinical References
   المطور والمشرف العام: دكتور تامر سعد (Dr. Tamer Saad)
   التاريخ: {datetime.now().strftime('%Y-%m-%d')}
================================================================================

تحتوي هذه المكتبة على 30 مرجعاً سريرياً معتمداً ومحدثاً بالكامل:
- 10 مراجع ودلائل دوائية ووبائية عربية سيادية ومحكمة.
- 20 مرجعاً طبياً دولياً معتمداً من الدرجة الأولى (Tier-1 Global References).

================================================================================
القسم الأول: المراجع العربية المعتمدة (10 مراجع كاملة بكتبها وفصولها)
================================================================================
"""
    for idx, (ref_id, book) in enumerate(ARAB_FULL_BOOKS.items(), 1):
        index_txt += f"""
[{idx:02d}] {book['title']}
     - الكود: {ref_id.upper()}
     - الجهة المعتمدة: {book['issuing_body']}
     - التوثيق الأكاديمي: {book['citation']}
     - الرابط الرسمي: {book['url']}
     - الأنواع المستهدفة: {book['species']}
     - الملخص: {book['summary']}
"""

    index_txt += f"""
================================================================================
القسم الثاني: المراجع الدولية المعتمدة من الدرجة الأولى (20 مرجعاً Tier-1)
================================================================================
"""
    for idx, (ref_id, book) in enumerate(GLOBAL_FULL_BOOKS.items(), 1):
        index_txt += f"""
[{idx:02d}] {book['title']}
     - Reference ID: {ref_id.upper()}
     - Issuing Authority: {book['issuing_body']}
     - Standard Citation: {book['citation']}
     - Official URL: {book['url']}
     - Target Species: {book['species']}
     - Summary: {book['summary']}
"""

    index_txt += f"""
================================================================================
حقوق الإعداد والتطوير محفوظة c 2026 لمنظومة VetMind AI - د. تامر سعد
================================================================================
"""

    with open(os.path.join(DOCS_DIR, "00_فهرس_المكتبة_السريرية_الشامل.txt"), "w", encoding="utf-8") as f:
        f.write(index_txt)
    with open(os.path.join(DESKTOP_DIR, "00_فهرس_المكتبة_السريرية_الشامل.txt"), "w", encoding="utf-8") as f:
        f.write(index_txt)

def package_zip_archives():
    print("Packaging comprehensive ZIP archives...")
    all_zip_path = os.path.join(DOWNLOADS_DIR, "VetMind_Enterprise_30_References_Complete.zip")
    desktop_all_zip = os.path.join(DESKTOP_DIR, "حزمة_المكتبة_البيطرية_الكاملة_30_مرجع_VetMind_Enterprise.zip")

    with zipfile.ZipFile(all_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(DOCS_DIR, "00_فهرس_المكتبة_السريرية_الشامل.txt"), arcname="00_فهرس_المكتبة_السريرية_الشامل.txt")

        # 10 Arab full books (both TXT and HTML)
        for ref_id, book in ARAB_FULL_BOOKS.items():
            ar_name = book['filename_ar']
            zf.write(os.path.join(DOCS_DIR, f"{ref_id}.txt"), arcname=f"01_المراجع_العربية_المعتمدة/{ar_name}.txt")
            zf.write(os.path.join(DOCS_DIR, f"{ref_id}.html"), arcname=f"01_المراجع_العربية_المعتمدة/{ar_name}.html")

        # 20 Global full books (both TXT and HTML)
        for ref_id, book in GLOBAL_FULL_BOOKS.items():
            en_name = book['filename_en']
            zf.write(os.path.join(DOCS_DIR, f"{ref_id}.txt"), arcname=f"02_المراجع_الدولية_المعتمدة_Tier1/{en_name}.txt")
            zf.write(os.path.join(DOCS_DIR, f"{ref_id}.html"), arcname=f"02_المراجع_الدولية_المعتمدة_Tier1/{en_name}.html")

    shutil.copyfile(all_zip_path, desktop_all_zip)
    print("All-in-one complete ZIP created.")

    # Arab ZIP
    arab_zip_path = os.path.join(DOWNLOADS_DIR, "VetMind_Arab_Formularies_10_References.zip")
    with zipfile.ZipFile(arab_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(DOCS_DIR, "00_فهرس_المكتبة_السريرية_الشامل.txt"), arcname="00_فهرس_المكتبة_السريرية_الشامل.txt")
        for ref_id, book in ARAB_FULL_BOOKS.items():
            ar_name = book['filename_ar']
            zf.write(os.path.join(DOCS_DIR, f"{ref_id}.txt"), arcname=f"{ar_name}.txt")
            zf.write(os.path.join(DOCS_DIR, f"{ref_id}.html"), arcname=f"{ar_name}.html")
    print("Arab ZIP created.")

    # Global ZIP
    global_zip_path = os.path.join(DOWNLOADS_DIR, "VetMind_Global_Tier1_20_References.zip")
    with zipfile.ZipFile(global_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(DOCS_DIR, "00_فهرس_المكتبة_السريرية_الشامل.txt"), arcname="00_Clinical_Index.txt")
        for ref_id, book in GLOBAL_FULL_BOOKS.items():
            en_name = book['filename_en']
            zf.write(os.path.join(DOCS_DIR, f"{ref_id}.txt"), arcname=f"{en_name}.txt")
            zf.write(os.path.join(DOCS_DIR, f"{ref_id}.html"), arcname=f"{en_name}.html")
    print("Global ZIP created.")

if __name__ == "__main__":
    generate_all_exhaustive_materials()
    print("\nExhaustive clinical reference manuals generated successfully!")
