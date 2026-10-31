# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Master Compiler for the 10 Massive Arab Veterinary Reference Compendiums
Compiles publication-grade, multi-page textbooks for all 10 Arab references.
Each book includes cover banner, academic metadata, executive summary, table of contents,
8 comprehensive chapters (each on a fresh page), clinical tables, running headers/footers,
and official accreditation by Dr. Tamer Saad.
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

# Import all 10 books
sys.path.append(BASE_DIR)
from data_arab_1 import ARAB_BOOK_1
from data_arab_2 import ARAB_BOOK_2
from data_arab_3 import ARAB_BOOK_3
from data_arab_4 import ARAB_BOOK_4
from data_arab_5 import ARAB_BOOK_5
from data_arab_6 import ARAB_BOOK_6
from data_arab_7 import ARAB_BOOK_7
from data_arab_8 import ARAB_BOOK_8
from data_arab_9 import ARAB_BOOK_9
from data_arab_10 import ARAB_BOOK_10
from arab_clinical_deep_dives import CLINICAL_DEEP_DIVES

ALL_BOOKS = [
    ARAB_BOOK_1, ARAB_BOOK_2, ARAB_BOOK_3, ARAB_BOOK_4, ARAB_BOOK_5,
    ARAB_BOOK_6, ARAB_BOOK_7, ARAB_BOOK_8, ARAB_BOOK_9, ARAB_BOOK_10
]

def compile_book_pdf(book, out_path):
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
        fontSize=17,
        leading=23,
        alignment=2,
        textColor=colors.whitesmoke
    )

    h1_style = ParagraphStyle(
        'ChapH1',
        fontName='VetArialBold',
        fontSize=13,
        leading=18,
        alignment=2,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SecH2',
        fontName='VetArialBold',
        fontSize=11,
        leading=15,
        alignment=2,
        textColor=dark_heading,
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyP',
        fontName='VetArial',
        fontSize=9.5,
        leading=14.5,
        alignment=2,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletP',
        fontName='VetArial',
        fontSize=9,
        leading=13.5,
        alignment=2,
        textColor=colors.HexColor("#0f172a"),
        rightIndent=12,
        spaceAfter=4
    )

    table_header_style = ParagraphStyle(
        'TH',
        fontName='VetArialBold',
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=colors.whitesmoke
    )

    table_cell_style = ParagraphStyle(
        'TC',
        fontName='VetArial',
        fontSize=8,
        leading=10.5,
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
            [Paragraph(issuing_txt, ParagraphStyle('B2', fontName='VetArial', fontSize=9.5, textColor=colors.HexColor('#f8fafc'), alignment=2))]
        ],
        colWidths=[523]
    )
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary_color),
        ('PADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 10))

    # 2. Academic Metadata Box
    meta_rows = [
        [
            Paragraph(ar(f"<b>التوثيق الأكاديمي القياسي:</b> {book['citation']}"), body_style),
            Paragraph(ar(f"<b>المشرف والمراجع السريري العام:</b> دكتور تامر سعد (Dr. Tamer Saad)"), body_style)
        ],
        [
            Paragraph(ar(f"<b>الفصائل والأنواع الحيوانية المستهدفة:</b> {book['species']}"), body_style),
            Paragraph(ar(f"<b>تاريخ الإصدار والتحقق الرقمي:</b> {datetime.now().strftime('%Y-%m-%d')} | طبعة 2026 المعتمدة"), body_style)
        ]
    ]
    meta_t = Table(meta_rows, colWidths=[261, 262])
    meta_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 10))

    # 3. Comprehensive Summary Box
    summary_box = Table(
        [
            [Paragraph(ar("<b>المقدمة والخلاصة الإكلينيكية التنفيذية للموسوعة:</b>"), ParagraphStyle('S1', fontName='VetArialBold', fontSize=10, textColor=primary_color, alignment=2))],
            [Paragraph(ar(book['summary']), body_style)]
        ],
        colWidths=[523]
    )
    summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0fdf4")),
        ('BOX', (0,0), (-1,-1), 1, primary_color),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(summary_box)
    story.append(Spacer(1, 12))

    # 4. Table of Contents
    toc_paragraphs = [Paragraph(ar("<b>فهرس الأبواب والفصول السريرية التفصيلية:</b>"), ParagraphStyle('TOCHead', fontName='VetArialBold', fontSize=11, textColor=primary_color, alignment=2))]
    for i, ch in enumerate(book['chapters'], 1):
        toc_paragraphs.append(Paragraph(ar(f"• {ch['title']}"), bullet_style))

    toc_table = Table([[p] for p in toc_paragraphs], colWidths=[523])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 14))

    # 5. Process Chapters (Each major chapter starts on a new page)
    for ch_idx, ch in enumerate(book['chapters'], 1):
        story.append(PageBreak())

        # Chapter Header Banner
        ch_title_p = Paragraph(ar(f"<b>{ch['title']}</b>"), ParagraphStyle('ChBanner', fontName='VetArialBold', fontSize=12, textColor=colors.whitesmoke, alignment=2))
        ch_banner_t = Table([[ch_title_p]], colWidths=[523])
        ch_banner_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), primary_color),
            ('PADDING', (0,0), (-1,-1), 7),
        ]))
        story.append(ch_banner_t)
        story.append(Spacer(1, 10))

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
                    ('PADDING', (0,0), (-1,-1), 5),
                ]))
                story.append(Spacer(1, 4))
                story.append(data_table)
                story.append(Spacer(1, 6))

            story.append(Spacer(1, 8))

    # Add Chapter 9: Applied Clinical Case Studies & Decision-Making
    cases = CLINICAL_DEEP_DIVES.get(ref_id, [])
    if cases:
        story.append(PageBreak())
        ch9_banner = Table([[Paragraph(ar("<b>الباب التاسع: الحالات السريرية التطبيقية والقرارات الإكلينيكية الميدانية</b>"), ParagraphStyle('Ch9B', fontName='VetArialBold', fontSize=12, textColor=colors.whitesmoke, alignment=2))]], colWidths=[523])
        ch9_banner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), primary_color),
            ('PADDING', (0,0), (-1,-1), 7),
        ]))
        story.append(ch9_banner)
        story.append(Spacer(1, 10))

        for c_idx, c in enumerate(cases, 1):
            c_title = c['case_title']
            c_hist = c['history']
            c_dec = c['clinical_decision']

            case_table = Table(
                [
                    [Paragraph(ar(f"<b>{c_title}</b>"), ParagraphStyle('CT', fontName='VetArialBold', fontSize=10, textColor=colors.HexColor('#166534'), alignment=2))],
                    [Paragraph(ar(f"<b>تاريخ الحالة والفحص السريري:</b> {c_hist}"), body_style)],
                    [Paragraph(ar(f"<b>القرار الإكلينيكي والبروتوكول العلاجي:</b><br/>{c_dec.replace(chr(10), '<br/>')}"), body_style)]
                ],
                colWidths=[523]
            )
            case_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#86efac")),
                ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor("#cbd5e1")),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(case_table)
            story.append(Spacer(1, 12))

    # Add Chapter 10: Clinical Appendix & Emergency Field Checklist
    story.append(PageBreak())
    ch10_banner = Table([[Paragraph(ar("<b>الباب العاشر: الملحق السريري المتقدم ودليل الطوارئ الحقلية المعتمد</b>"), ParagraphStyle('Ch10B', fontName='VetArialBold', fontSize=12, textColor=colors.whitesmoke, alignment=2))]], colWidths=[523])
    ch10_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary_color),
        ('PADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(ch10_banner)
    story.append(Spacer(1, 10))

    appendix_p1 = "يقدم هذا الملحق السريري المعتمد ملخصاً تنفيذياً سريعاً للطبيب البيطري في الميدان للتعامل الفوري مع الحالات الحرجة وحساب الجرعات الدوائية الطارئة ومحاذير السحب."
    story.append(Paragraph(ar(appendix_p1), body_style))
    story.append(Spacer(1, 6))

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
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(app_t)
    story.append(Spacer(1, 10))

    # 6. Verification & Closing Accreditation Box
    story.append(Spacer(1, 14))
    close_box = Table(
        [
            [Paragraph(ar("<b>توثيق الاعتماد الرقمي وحقوق الملكية السريرية:</b>"), ParagraphStyle('CB1', fontName='VetArialBold', fontSize=9.5, textColor=colors.HexColor('#0f172a'), alignment=2))],
            [Paragraph(ar("تم تدقيق واعتماد هذه الموسوعة السريرية البيطرية الشاملة بواسطة منصة VetMind AI للذكاء الاصطناعي الطبي البيطري، تحت الإشراف العام المباشر للدكتور تامر سعد (Dr. Tamer Saad). مخصص حصرياً للأطباء البيطريين المرخصين والمراكز الأكاديمية والبحثية المعتمدة."), ParagraphStyle('CB2', fontName='VetArial', fontSize=8.5, leading=12, textColor=colors.HexColor('#475569'), alignment=2))]
        ],
        colWidths=[523]
    )
    close_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.8, primary_color),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(close_box)

    doc.build(story, canvasmaker=NumberedCanvas)

def compile_all():
    print("="*70)
    print("VetMind AI Enterprise - Compiling All 10 Massive Arab Textbooks...")
    print("="*70)

    for book in ALL_BOOKS:
        ref_id = book['ref_id']
        ar_name = book['filename_ar']

        web_path = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
        desktop_path = os.path.join(DESKTOP_ARAB_DIR, f"{ar_name}.pdf")

        compile_book_pdf(book, web_path)
        shutil.copyfile(web_path, desktop_path)

        # Count pages
        with open(web_path, "rb") as fp:
            content = fp.read()
        pages = len(re.findall(rb'/Type\s*/Page\b', content))
        size_kb = round(os.path.getsize(web_path) / 1024, 1)

        print(f"[{ref_id.upper()}] Built: {os.path.basename(web_path)} | Pages: {pages} | Size: {size_kb} KB")
        print(f"       Desktop Copy: {os.path.basename(desktop_path)}")

    print("\nAll 10 Massive Arab Textbooks compiled successfully!")
    print("Rebuilding full 30-reference ZIP package...")

    all_zip_path = os.path.join(DOWNLOADS_DIR, "VetMind_Enterprise_30_References_Complete.zip")
    desktop_all_zip = os.path.join(DESKTOP_DIR, "حزمة_المكتبة_البيطرية_الكاملة_30_مرجع_VetMind_Enterprise.zip")

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
    total_mb = round(os.path.getsize(all_zip_path) / (1024*1024), 2)
    print(f"Complete ZIP Package Rebuilt: {total_mb} MB")
    print("="*70)

if __name__ == "__main__":
    compile_all()
