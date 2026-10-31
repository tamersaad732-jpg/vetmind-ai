# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Official Veterinary PDF Reference Manuals Builder
Generates multi-page, publication-grade clinical PDFs for all 30 references
using ReportLab with Arabic & English typography and NumberedCanvas.
"""

import os
import sys
import shutil
import zipfile
from datetime import datetime

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "static", "reference_docs")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "static", "downloads")
DESKTOP_DIR = os.path.join(BASE_DIR, "static", "downloads")
DESKTOP_ARAB_DIR = os.path.join(DESKTOP_DIR, "01_المراجع_العربية_المعتمدة")
DESKTOP_GLOBAL_DIR = os.path.join(DESKTOP_DIR, "02_المراجع_الدولية_المعتمدة_Tier1")

try:
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(DESKTOP_DIR, exist_ok=True)
    os.makedirs(DESKTOP_ARAB_DIR, exist_ok=True)
    os.makedirs(DESKTOP_GLOBAL_DIR, exist_ok=True)
except Exception:
    pass

sys.path.insert(0, BASE_DIR)
from references_content_data import ARAB_FULL_BOOKS, GLOBAL_FULL_BOOKS

# Register Windows TrueType Fonts for Unicode/Arabic support
FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
pdfmetrics.registerFont(TTFont("VetArial", FONT_REGULAR))
pdfmetrics.registerFont(TTFont("VetArialBold", FONT_BOLD))

class NumberedCanvas(canvas.Canvas):
    """Adds running headers, footers, and dynamic page counts (Page X of Y)"""
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
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header (from page 2 onwards)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(36, 805, 559, 805)
            header_text = get_display(arabic_reshaper.reshape("منظومة VetMind AI للذكاء الاصطناعي الطبي البيطري - إشراف د. تامر سعد"))
            self.drawRightString(559, 810, header_text)
            self.drawString(36, 810, "VetMind AI Enterprise Clinical Reference Library")

        # Running Footer (on all pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 45, 559, 45)

        footer_text = get_display(arabic_reshaper.reshape(f"صفحة {self._pageNumber} من {total_pages}"))
        self.drawRightString(559, 32, footer_text)
        self.drawString(36, 32, "Confidential - For Licensed Veterinary Medical Practitioners Only")
        self.restoreState()

def reshape_ar(text):
    if not text:
        return ""
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)

def generate_pdf_for_book(book, pdf_path, is_arab=True, ref_code=""):
    primary_hex = "#16a34a" if is_arab else "#0284c7"
    primary_color = colors.HexColor(primary_hex)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    title_align = 2 if is_arab else 0
    body_align = 2 if is_arab else 0

    title_style = ParagraphStyle(
        'DocTitle',
        fontName='VetArialBold',
        fontSize=18,
        leading=24,
        alignment=title_align,
        textColor=colors.whitesmoke
    )

    meta_label_style = ParagraphStyle(
        'MetaLabel',
        fontName='VetArialBold',
        fontSize=10,
        leading=14,
        alignment=title_align,
        textColor=primary_color
    )

    meta_val_style = ParagraphStyle(
        'MetaVal',
        fontName='VetArial',
        fontSize=9.5,
        leading=14,
        alignment=title_align,
        textColor=colors.HexColor("#1e293b")
    )

    h1_style = ParagraphStyle(
        'ChapterH1',
        fontName='VetArialBold',
        fontSize=13,
        leading=18,
        alignment=title_align,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SubH2',
        fontName='VetArialBold',
        fontSize=11,
        leading=15,
        alignment=title_align,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'DocBody',
        fontName='VetArial',
        fontSize=9.5,
        leading=14.5,
        alignment=body_align,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        fontName='VetArial',
        fontSize=9,
        leading=13.5,
        alignment=body_align,
        textColor=colors.HexColor("#1e293b"),
        leftIndent=15 if not is_arab else 0,
        rightIndent=15 if is_arab else 0,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'Callout',
        fontName='VetArial',
        fontSize=9,
        leading=13.5,
        alignment=body_align,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # 1. Header Banner
    header_title_text = reshape_ar(book['title']) if is_arab else book['title']
    header_sub_text = reshape_ar("دليل سريري وتوثيق رسمي معتمد | منظومة VetMind AI") if is_arab else "Official Tier-1 Clinical Veterinary Monograph | VetMind AI Enterprise"
    badge_text = reshape_ar(f"كود المرجع: {ref_code.upper()} | معتمد رسمياً") if is_arab else f"REF ID: {ref_code.upper()} | VERIFIED OFFICIAL"

    banner_table = Table(
        [
            [Paragraph(f"<b>{badge_text}</b>", ParagraphStyle('B1', fontName='VetArialBold', fontSize=8.5, textColor=colors.HexColor('#dcfce7' if is_arab else '#e0f2fe'), alignment=title_align))],
            [Paragraph(f"<b>{header_title_text}</b>", title_style)],
            [Paragraph(header_sub_text, ParagraphStyle('B2', fontName='VetArial', fontSize=9, textColor=colors.HexColor('#f8fafc'), alignment=title_align))]
        ],
        colWidths=[523]
    )
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary_color),
        ('PADDING', (0,0), (-1,-1), 12),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 10))

    # 2. Metadata Information Block
    meta_rows = [
        [
            Paragraph(reshape_ar(f"<b>الجهة المصدرة:</b> {book['issuing_body']}" if is_arab else f"<b>Issuing Authority:</b> {book['issuing_body']}"), meta_val_style),
            Paragraph(reshape_ar(f"<b>التوثيق:</b> {book['citation']}" if is_arab else f"<b>Citation:</b> {book['citation']}"), meta_val_style)
        ],
        [
            Paragraph(reshape_ar(f"<b>الأنواع المستهدفة:</b> {book['species']}" if is_arab else f"<b>Target Species:</b> {book['species']}"), meta_val_style),
            Paragraph(reshape_ar(f"<b>المشرف والمراجع العام:</b> دكتور تامر سعد (Dr. Tamer Saad)"), meta_val_style)
        ]
    ]
    meta_table = Table(meta_rows, colWidths=[261, 262])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. Executive Clinical Summary Box
    summary_label = reshape_ar("الخلاصة الإكلينيكية والتنفيذية للمرجع:") if is_arab else "Executive Clinical Summary & Scope:"
    summary_text = reshape_ar(book['summary']) if is_arab else book['summary']
    summary_box = Table(
        [
            [Paragraph(f"<b>{summary_label}</b>", meta_label_style)],
            [Paragraph(summary_text, body_style)]
        ],
        colWidths=[523]
    )
    summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#eff6ff" if not is_arab else "#f0fdf4")),
        ('BOX', (0,0), (-1,-1), 1, primary_color),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(summary_box)
    story.append(Spacer(1, 12))

    # 4. Chapters & In-depth Content
    for idx, ch in enumerate(book['chapters'], 1):
        ch_title_raw = ch['title']
        ch_title_display = reshape_ar(ch_title_raw) if is_arab else ch_title_raw
        story.append(Paragraph(ch_title_display, h1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=8, spaceBefore=2))

        lines = ch['content'].strip().split("\n")
        table_mode = False
        table_buffer = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Detect lines
            if line_str.startswith("-") or line_str.startswith("*"):
                bullet_text = line_str[1:].strip()
                b_display = reshape_ar(f"• {bullet_text}") if is_arab else f"• {bullet_text}"
                story.append(Paragraph(b_display, bullet_style))
            elif line_str.startswith("1.") or line_str.startswith("2.") or line_str.startswith("3.") or line_str.startswith("4.") or line_str.startswith("5."):
                h_display = reshape_ar(line_str) if is_arab else line_str
                story.append(Paragraph(h_display, h2_style))
            else:
                p_display = reshape_ar(line_str) if is_arab else line_str
                story.append(Paragraph(p_display, body_style))

        story.append(Spacer(1, 8))

    # 5. Regulatory Notice & Verification Box
    story.append(Spacer(1, 10))
    disc_header = reshape_ar("تنبيه سريري وقانوني وتوثيق الاعتماد الرقمي:") if is_arab else "Regulatory & Clinical Safety Authentication Notice:"
    disc_body = reshape_ar(
        "هذا الدليل السريري المعتمد موجه حصرياً للأطباء البيطريين المرخصين لدعم اتخاذ القرار الطبي. "
        "تمت المراجعة والاعتماد بواسطة لجنة التدقيق الطبي في منصة VetMind AI - المشرف العام: دكتور تامر سعد. "
        f"تاريخ الإصدار والتحقق: {datetime.now().strftime('%Y-%m-%d')} | الرمز الرقمي: VETMIND-OFFICIAL-2026"
    ) if is_arab else (
        "This official clinical monograph is strictly curated for licensed veterinary surgeons to assist evidence-based decision making. "
        "Medical Architecture & Review by Dr. Tamer Saad. "
        f"Verification Date: {datetime.now().strftime('%Y-%m-%d')} | Hash: VETMIND-GLOBAL-OFFICIAL-2026"
    )

    disc_table = Table(
        [
            [Paragraph(f"<b>{disc_header}</b>", ParagraphStyle('D1', fontName='VetArialBold', fontSize=8.5, textColor=colors.HexColor('#0f172a'), alignment=title_align))],
            [Paragraph(disc_body, ParagraphStyle('D2', fontName='VetArial', fontSize=8, leading=11, textColor=colors.HexColor('#475569'), alignment=title_align))]
        ],
        colWidths=[523]
    )
    disc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(disc_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated PDF: {pdf_path} (Size: {os.path.getsize(pdf_path)} bytes)")

def generate_all_30_pdfs():
    print("Generating official multi-page PDFs for all 30 references...")

    # 1. Arab References (10 PDFs)
    for ref_id, book in ARAB_FULL_BOOKS.items():
        ar_name = book['filename_ar']
        web_pdf = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
        desktop_pdf = os.path.join(DESKTOP_ARAB_DIR, f"{ar_name}.pdf")

        generate_pdf_for_book(book, web_pdf, is_arab=True, ref_code=ref_id)
        shutil.copyfile(web_pdf, desktop_pdf)

    print("All 10 Arab PDFs generated and copied to Desktop.")

    # 2. Global References (20 PDFs)
    for ref_id, book in GLOBAL_FULL_BOOKS.items():
        en_name = book['filename_en']
        web_pdf = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
        desktop_pdf = os.path.join(DESKTOP_GLOBAL_DIR, f"{en_name}.pdf")

        generate_pdf_for_book(book, web_pdf, is_arab=False, ref_code=ref_id)
        shutil.copyfile(web_pdf, desktop_pdf)

    print("All 20 Global PDFs generated and copied to Desktop.")

    # 3. Create Clean PDF-Only ZIP Bundles
    create_pdf_zip_bundles()

def create_pdf_zip_bundles():
    print("Creating PDF-Only ZIP bundles...")

    # 1. Complete Bundle (All 30 PDFs)
    all_zip_path = os.path.join(DOWNLOADS_DIR, "VetMind_Enterprise_30_References_Complete.zip")
    desktop_all_zip = os.path.join(DESKTOP_DIR, "حزمة_المكتبة_البيطرية_الكاملة_30_مرجع_VetMind_Enterprise.zip")

    with zipfile.ZipFile(all_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add 10 Arab PDFs
        for ref_id, book in ARAB_FULL_BOOKS.items():
            ar_name = book['filename_ar']
            local_pdf = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
            zf.write(local_pdf, arcname=f"01_المراجع_العربية_المعتمدة_PDF/{ar_name}.pdf")

        # Add 20 Global PDFs
        for ref_id, book in GLOBAL_FULL_BOOKS.items():
            en_name = book['filename_en']
            local_pdf = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
            zf.write(local_pdf, arcname=f"02_المراجع_الدولية_المعتمدة_PDF/{en_name}.pdf")

    shutil.copyfile(all_zip_path, desktop_all_zip)
    print("Complete PDF ZIP bundle generated.")

    # 2. Arab Bundle (10 PDFs)
    arab_zip_path = os.path.join(DOWNLOADS_DIR, "VetMind_Arab_Formularies_10_References.zip")
    with zipfile.ZipFile(arab_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for ref_id, book in ARAB_FULL_BOOKS.items():
            ar_name = book['filename_ar']
            local_pdf = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
            zf.write(local_pdf, arcname=f"{ar_name}.pdf")
    print("Arab PDF ZIP bundle generated.")

    # 3. Global Bundle (20 PDFs)
    global_zip_path = os.path.join(DOWNLOADS_DIR, "VetMind_Global_Tier1_20_References.zip")
    with zipfile.ZipFile(global_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for ref_id, book in GLOBAL_FULL_BOOKS.items():
            en_name = book['filename_en']
            local_pdf = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
            zf.write(local_pdf, arcname=f"{en_name}.pdf")
    print("Global PDF ZIP bundle generated.")

if __name__ == "__main__":
    generate_all_30_pdfs()
    print("\nAll 30 multi-page veterinary clinical PDFs successfully generated and packaged!")
