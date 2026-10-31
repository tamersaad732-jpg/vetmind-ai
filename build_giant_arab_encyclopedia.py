# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Master Compiler for the Giant Arab Clinical Veterinary Encyclopedia
Compiles 10 massive publication-grade volumes (25-35+ pages each) for all 10 Arab references.
Each book contains 12 comprehensive chapters, clinical case studies, differential diagnosis tables,
laboratory values, surgical procedures, withdrawal matrices, and official accreditation.
"""

import os
import sys
import shutil
import zipfile
import re
from datetime import datetime

# Configure UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DOCS_DIR = os.path.join(BASE_DIR, "static", "reference_docs")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "static", "downloads")
DESKTOP_DIR = r"C:\Users\tamersaad\Desktop\مكتبة المراجع البيطرية المعتمدة (VetMind Library)"
USER_DOWNLOADS = r"C:\Users\tamersaad\Downloads"

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(DESKTOP_DIR, exist_ok=True)

DESKTOP_ARAB_DIR = os.path.join(DESKTOP_DIR, "01_المراجع_العربية_المعتمدة")
DESKTOP_GLOBAL_DIR = os.path.join(DESKTOP_DIR, "02_المراجع_الدولية_المعتمدة_Tier1")
os.makedirs(DESKTOP_ARAB_DIR, exist_ok=True)
os.makedirs(DESKTOP_GLOBAL_DIR, exist_ok=True)

# Register Fonts
FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
pdfmetrics.registerFont(TTFont("VetArial", FONT_REGULAR))
pdfmetrics.registerFont(TTFont("VetArialBold", FONT_BOLD))

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("VetArial", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Running Header (from page 2 onwards)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(36, 805, 559, 805)
            h_text = get_display(arabic_reshaper.reshape("منظومة VetMind AI للذكاء الاصطناعي الطبي البيطري | إشراف د. تامر سعد"))
            self.drawRightString(559, 810, h_text)
            self.drawString(36, 810, "VetMind Enterprise - Arab Veterinary Reference Library")

        # Running Footer (on all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(36, 45, 559, 45)

        f_text = get_display(arabic_reshaper.reshape(f"صفحة {self._pageNumber} من {total_pages}"))
        self.drawRightString(559, 32, f_text)
        footer_sub = get_display(arabic_reshaper.reshape("الموسوعة السريرية البيطرية المعتمدة - مخصص حصرياً لدعم القرار الإكلينيكي للأطباء البيطريين المرخصين"))
        self.drawString(36, 32, footer_sub)
        self.restoreState()

def ar(text):
    if not text:
        return ""
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)

# Import books data
sys.path.append(BASE_DIR)
from giant_data_part1 import GIANT_BOOKS_1_TO_5
from giant_data_part2 import GIANT_BOOKS_6_TO_10
from arab_clinical_deep_dives import CLINICAL_DEEP_DIVES

ALL_GIANT_BOOKS = []
for i in range(1, 6):
    ALL_GIANT_BOOKS.append(GIANT_BOOKS_1_TO_5[f"arab_{i}"])
for i in range(6, 11):
    ALL_GIANT_BOOKS.append(GIANT_BOOKS_6_TO_10[f"arab_{i}"])

def compile_giant_book(book, out_path):
    primary_color = colors.HexColor("#16a34a") # Arab Green
    dark_heading = colors.HexColor("#0f172a")

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        fontName='VetArialBold',
        fontSize=16,
        leading=22,
        alignment=2,
        textColor=colors.whitesmoke
    )

    h1_style = ParagraphStyle(
        'ChapH1',
        fontName='VetArialBold',
        fontSize=12,
        leading=16,
        alignment=2,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=5
    )

    h2_style = ParagraphStyle(
        'SecH2',
        fontName='VetArialBold',
        fontSize=10.5,
        leading=14.5,
        alignment=2,
        textColor=dark_heading,
        spaceBefore=8,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'BodyP',
        fontName='VetArial',
        fontSize=9,
        leading=13.5,
        alignment=2,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'BulletP',
        fontName='VetArial',
        fontSize=8.5,
        leading=12.5,
        alignment=2,
        textColor=colors.HexColor("#0f172a"),
        rightIndent=12,
        spaceAfter=3
    )

    table_header_style = ParagraphStyle(
        'TH',
        fontName='VetArialBold',
        fontSize=8,
        leading=10,
        alignment=2,
        textColor=colors.whitesmoke
    )

    table_cell_style = ParagraphStyle(
        'TC',
        fontName='VetArial',
        fontSize=7.5,
        leading=9.5,
        alignment=2,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # 1. Front Cover Header Banner
    ref_id = book['ref_id']
    badge_txt = ar(f"الموسوعة الإكلينيكية البيطرية المعتمدة | {ref_id.upper()}")
    header_title = ar(book['title'])
    issuing_txt = ar(f"إصدار: {book['issuing_body']}")

    banner_table = Table(
        [
            [Paragraph(f"<b>{badge_txt}</b>", ParagraphStyle('B1', fontName='VetArialBold', fontSize=9, textColor=colors.HexColor('#dcfce7'), alignment=2))],
            [Paragraph(f"<b>{header_title}</b>", title_style)],
            [Paragraph(issuing_txt, ParagraphStyle('B2', fontName='VetArial', fontSize=9, textColor=colors.HexColor('#f8fafc'), alignment=2))]
        ],
        colWidths=[523]
    )
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary_color),
        ('PADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('TOPPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 8))

    # 2. Academic Metadata Box
    meta_rows = [
        [
            Paragraph(ar(f"<b>التوثيق الأكاديمي القياسي:</b> {book['citation']}"), body_style),
            Paragraph(ar(f"<b>المشرف والمراجع السريري العام:</b> دكتور تامر سعد (Dr. Tamer Saad)"), body_style)
        ],
        [
            Paragraph(ar(f"<b>الفصائل والأنواع الحيوانية المستهدفة:</b> {book['species']}"), body_style),
            Paragraph(ar(f"<b>تاريخ الإصدار والتحقق الرقمي:</b> {datetime.now().strftime('%Y-%m-%d')} | طبعة 2026 المعتمدة الموسعة"), body_style)
        ]
    ]
    meta_t = Table(meta_rows, colWidths=[261, 262])
    meta_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 8))

    # 3. Comprehensive Summary Box
    summary_box = Table(
        [
            [Paragraph(ar("<b>المقدمة والخلاصة الإكلينيكية التنفيذية للموسوعة:</b>"), ParagraphStyle('S1', fontName='VetArialBold', fontSize=9.5, textColor=primary_color, alignment=2))],
            [Paragraph(ar(book['summary']), body_style)]
        ],
        colWidths=[523]
    )
    summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0fdf4")),
        ('BOX', (0,0), (-1,-1), 1, primary_color),
        ('PADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(summary_box)
    story.append(Spacer(1, 10))

    # 4. Table of Contents
    toc_paragraphs = [Paragraph(ar("<b>فهرس الأبواب والفصول السريرية التفصيلية (12 باباً تخصصياً):</b>"), ParagraphStyle('TOCHead', fontName='VetArialBold', fontSize=10, textColor=primary_color, alignment=2))]
    for i, ch in enumerate(book['chapters'], 1):
        toc_paragraphs.append(Paragraph(ar(f"• {ch['title']}"), bullet_style))

    toc_table = Table([[p] for p in toc_paragraphs], colWidths=[523])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 12))

    # 5. Process Chapters (Each major chapter starts on a new page)
    for ch_idx, ch in enumerate(book['chapters'], 1):
        story.append(PageBreak())

        # Chapter Header Banner
        ch_title_p = Paragraph(ar(f"<b>{ch['title']}</b>"), ParagraphStyle('ChBanner', fontName='VetArialBold', fontSize=11, textColor=colors.whitesmoke, alignment=2))
        ch_banner_t = Table([[ch_title_p]], colWidths=[523])
        ch_banner_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), primary_color),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(ch_banner_t)
        story.append(Spacer(1, 8))

        # Sections inside Chapter
        for sec in ch.get('sections', []):
            story.append(Paragraph(ar(sec['heading']), h2_style))
            for p in sec.get('paragraphs', []):
                story.append(Paragraph(ar(p), body_style))
            for b in sec.get('bullets', []):
                story.append(Paragraph(ar(f"• {b}"), bullet_style))

            # Table in section if present
            if 'table' in sec:
                t_spec = sec['table']
                table_rows = []
                h_row = [Paragraph(ar(col), table_header_style) for col in t_spec['headers']]
                table_rows.append(h_row)
                for r in t_spec['rows']:
                    row_cells = [Paragraph(ar(cell), table_cell_style) for cell in r]
                    table_rows.append(row_cells)

                col_w = t_spec.get('colWidths', [174, 174, 175])
                data_table = Table(table_rows, colWidths=col_w)
                data_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), primary_color),
                    ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                    ('PADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(Spacer(1, 4))
                story.append(data_table)
                story.append(Spacer(1, 5))

            story.append(Spacer(1, 6))

    # Add Dedicated Clinical Case Studies Chapter
    cases = CLINICAL_DEEP_DIVES.get(ref_id, [])
    if cases:
        story.append(PageBreak())
        ch_cases_banner = Table([[Paragraph(ar("<b>دراسات الحالات السريرية الحقلية والقرارات الإكلينيكية الميدانية</b>"), ParagraphStyle('ChCB', fontName='VetArialBold', fontSize=11, textColor=colors.whitesmoke, alignment=2))]], colWidths=[523])
        ch_cases_banner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), primary_color),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(ch_cases_banner)
        story.append(Spacer(1, 8))

        for c_idx, c in enumerate(cases, 1):
            c_title = c['case_title']
            c_hist = c['history']
            c_dec = c['clinical_decision']

            case_table = Table(
                [
                    [Paragraph(ar(f"<b>{c_title}</b>"), ParagraphStyle('CT', fontName='VetArialBold', fontSize=9.5, textColor=colors.HexColor('#166534'), alignment=2))],
                    [Paragraph(ar(f"<b>تاريخ الحالة والفحص السريري:</b> {c_hist}"), body_style)],
                    [Paragraph(ar(f"<b>القرار الإكلينيكي والبروتوكول العلاجي:</b><br/>{c_dec.replace(chr(10), '<br/>')}"), body_style)]
                ],
                colWidths=[523]
            )
            case_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#86efac")),
                ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor("#cbd5e1")),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(case_table)
            story.append(Spacer(1, 10))

    # Add Dedicated Emergency Protocol Checklist
    story.append(PageBreak())
    ch_app_banner = Table([[Paragraph(ar("<b>الملحق الإكلينيكي للطوارئ وبروتوكولات التدخل السريع في الحقل</b>"), ParagraphStyle('ChAB', fontName='VetArialBold', fontSize=11, textColor=colors.whitesmoke, alignment=2))]], colWidths=[523])
    ch_app_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary_color),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(ch_app_banner)
    story.append(Spacer(1, 8))

    appendix_p1 = "يقدم هذا الملحق السريري المعتمد ملخصاً تنفيذياً سريعاً للطبيب البيطري في الميدان للتعامل الفوري مع الحالات الحرجة وحساب الجرعات الدوائية الطارئة ومحاذير السحب."
    story.append(Paragraph(ar(appendix_p1), body_style))
    story.append(Spacer(1, 5))

    app_table_rows = [
        [Paragraph(ar("العنصر السريري الطارئ"), table_header_style), Paragraph(ar("الإجراء الفوري والجرعة المنقذة"), table_header_style), Paragraph(ar("المحاذير والملاحظات"), table_header_style)],
        [Paragraph(ar("الصدمة التأقية (Anaphylaxis)"), table_cell_style), Paragraph(ar("أدرينالين 1:1000 بجرعة 0.01 ملغم/كغم IV/IM + ديكساميثازون"), table_cell_style), Paragraph(ar("إيقاف اللقاح أو الدواء المسبب فوراً ومراقبة التنفس"), table_cell_style)],
        [Paragraph(ar("النفاخ الخانق الحاد (Bloat)"), table_cell_style), Paragraph(ar("فغر الكرش فوراً بالمبزل والكانولا بالخاصرة اليسرى + زيت بارافين"), table_cell_style), Paragraph(ar("تجنب التأخير لتفادي الموت بالاختناق الصدمي"), table_cell_style)],
        [Paragraph(ar("تسمم المبيدات الفوسفورية"), table_cell_style), Paragraph(ar("أتروبين سلفات 1% بجرعة 0.2 - 0.5 ملغم/كغم ربع IV والباقي SC"), table_cell_style), Paragraph(ar("تكرر حتى اتساع الحدقة وجفاف اللعاب الرغوي"), table_cell_style)],
        [Paragraph(ar("النزف الحاد وهبوط الضغط"), table_cell_style), Paragraph(ar("محلول هايبرتونيك 7.2% بجرعة 4 مل/كغم IV سريعاً خلال 15 دقيقة"), table_cell_style), Paragraph(ar("متبوعاً بسوائل فموية أو وريدية متساوية التوتر"), table_cell_style)],
        [Paragraph(ar("التكزز ونقص الكالسيوم"), table_cell_style), Paragraph(ar("كالسيوم بوروجلوكونات 40% بالتسريب الوريدي البطيء الدافئ"), table_cell_style), Paragraph(ar("مراقبة نبض القلب بالسماعة وإيقاف التسريب عند بطء النبض"), table_cell_style)]
    ]
    app_t = Table(app_table_rows, colWidths=[150, 210, 163])
    app_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(app_t)
    story.append(Spacer(1, 10))

    # 6. Verification & Closing Accreditation Box
    story.append(Spacer(1, 12))
    close_box = Table(
        [
            [Paragraph(ar("<b>توثيق الاعتماد الرقمي وحقوق الملكية السريرية:</b>"), ParagraphStyle('CB1', fontName='VetArialBold', fontSize=9, textColor=colors.HexColor('#0f172a'), alignment=2))],
            [Paragraph(ar("تم تدقيق واعتماد هذه الموسوعة السريرية البيطرية الشاملة بواسطة منصة VetMind AI للذكاء الاصطناعي الطبي البيطري، تحت الإشراف العام المباشر للدكتور تامر سعد (Dr. Tamer Saad). مخصص حصرياً للأطباء البيطريين المرخصين والمراكز الأكاديمية والبحثية المعتمدة."), ParagraphStyle('CB2', fontName='VetArial', fontSize=8, leading=11, textColor=colors.HexColor('#475569'), alignment=2))]
        ],
        colWidths=[523]
    )
    close_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.8, primary_color),
        ('PADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(close_box)

    doc.build(story, canvasmaker=NumberedCanvas)

def compile_all():
    print("="*70)
    print("VetMind AI Enterprise - Compiling Master Giant Arab Veterinary Volumes...")
    print("="*70)

    for book in ALL_GIANT_BOOKS:
        ref_id = book['ref_id']
        ar_name = book['filename_ar']

        web_path = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
        desktop_path = os.path.join(DESKTOP_ARAB_DIR, f"{ar_name}.pdf")
        user_dl_path = os.path.join(USER_DOWNLOADS, f"{ar_name}.pdf")

        compile_giant_book(book, web_path)
        shutil.copyfile(web_path, desktop_path)
        try:
            shutil.copyfile(web_path, user_dl_path)
        except Exception:
            pass

        # Count pages
        with open(web_path, "rb") as fp:
            content = fp.read()
        pages = len(re.findall(rb'/Type\s*/Page\b', content))
        size_kb = round(os.path.getsize(web_path) / 1024, 1)

        print(f"[{ref_id.upper()}] Built: {os.path.basename(web_path)} | Pages: {pages} | Size: {size_kb} KB")
        print(f"       Desktop: {os.path.basename(desktop_path)}")

    print("\nAll 10 Master Giant Arab Volumes compiled successfully!")
    print("Rebuilding full 30-reference ZIP package...")

    all_zip_path = os.path.join(DOWNLOADS_DIR, "VetMind_Enterprise_30_References_Complete.zip")
    desktop_all_zip = os.path.join(DESKTOP_DIR, "حزمة_المكتبة_البيطرية_الكاملة_30_مرجع_VetMind_Enterprise.zip")
    user_dl_zip = os.path.join(USER_DOWNLOADS, "VetMind_Enterprise_30_References_Complete.zip")

    with zipfile.ZipFile(all_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Arab PDFs
        for f in os.listdir(DESKTOP_ARAB_DIR):
            if f.endswith(".pdf"):
                zf.write(os.path.join(DESKTOP_ARAB_DIR, f), arcname="01_المراجع_العربية_المعتمدة_PDF/" + f)
        # Global PDFs
        for f in os.listdir(DESKTOP_GLOBAL_DIR):
            if f.endswith(".pdf"):
                zf.write(os.path.join(DESKTOP_GLOBAL_DIR, f), arcname="02_المراجع_الدولية_المعتمدة_PDF/" + f)

    shutil.copyfile(all_zip_path, desktop_all_zip)
    try:
        shutil.copyfile(all_zip_path, user_dl_zip)
    except Exception:
        pass

    # Arab 10 ZIP
    arab_zip = os.path.join(DOWNLOADS_DIR, "VetMind_Arab_Formularies_10_References.zip")
    with zipfile.ZipFile(arab_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in os.listdir(DESKTOP_ARAB_DIR):
            if f.endswith(".pdf"):
                zf.write(os.path.join(DESKTOP_ARAB_DIR, f), arcname=f)

    total_mb = round(os.path.getsize(all_zip_path) / (1024*1024), 2)
    print(f"Complete ZIP Package Rebuilt: {total_mb} MB")
    print("="*70)

if __name__ == "__main__":
    compile_all()
