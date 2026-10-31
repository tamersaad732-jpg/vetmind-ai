# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Generator for Massive Multi-Page Arab Clinical Veterinary Books
Generates extensive, publication-grade clinical reference volumes for all 10 Arab references.
Each book contains extensive clinical chapters, disease profiles, differential diagnosis matrices,
normal/abnormal lab intervals, exact dosing formulations, surgical steps, and withdrawal tables.
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
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header (from page 2 onwards)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(36, 805, 559, 805)
            h_text = get_display(arabic_reshaper.reshape("منظومة VetMind AI للذكاء الاصطناعي الطبي البيطري | إشراف د. تامر سعد"))
            self.drawRightString(559, 810, h_text)
            self.drawString(36, 810, "VetMind Enterprise Arab Veterinary Compendium")

        # Running Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(36, 45, 559, 45)

        f_text = get_display(arabic_reshaper.reshape(f"صفحة {self._pageNumber} من {total_pages}"))
        self.drawRightString(559, 32, f_text)
        self.drawString(36, 32, "الموسوعة السريرية البيطرية المعتمدة - مخصص للأطباء البيطريين المرخصين")
        self.restoreState()

def ar(text):
    if not text:
        return ""
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)

# We will generate comprehensive massive monographs for each Arab reference
from massive_arab_data import MASSIVE_ARAB_BOOKS

def build_massive_pdf(ref_id, book_data, out_path):
    primary_color = colors.HexColor("#16a34a") # Arab Green

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
        fontSize=18,
        leading=24,
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
        spaceBefore=16,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SecH2',
        fontName='VetArialBold',
        fontSize=11,
        leading=15,
        alignment=2,
        textColor=colors.HexColor("#0f172a"),
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
        spaceAfter=3
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
    badge_txt = ar(f"الموسوعة الإكلينيكية البيطرية المعتمدة | {ref_id.upper()}")
    header_title = ar(book_data['title'])
    issuing_txt = ar(f"إصدار: {book_data['issuing_body']}")

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

    # 2. Metadata Box
    meta_rows = [
        [
            Paragraph(ar(f"<b>التوثيق الأكاديمي القياسي:</b> {book_data['citation']}"), body_style),
            Paragraph(ar(f"<b>المشرف والمراجع السريري العام:</b> دكتور تامر سعد (Dr. Tamer Saad)"), body_style)
        ],
        [
            Paragraph(ar(f"<b>الفصائل والأنواع الحيوانية المستهدفة:</b> {book_data['species']}"), body_style),
            Paragraph(ar(f"<b>تاريخ الإصدار والتحقق الرقمي:</b> {datetime.now().strftime('%Y-%m-%d')}"), body_style)
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
            [Paragraph(ar("<b>المقدمة والخلاصة التنفيذية للموسوعة:</b>"), ParagraphStyle('S1', fontName='VetArialBold', fontSize=10, textColor=primary_color, alignment=2))],
            [Paragraph(ar(book_data['summary']), body_style)]
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
    for i, ch in enumerate(book_data['chapters'], 1):
        toc_paragraphs.append(Paragraph(ar(f"• الباب {i}: {ch['title']}"), bullet_style))
    
    toc_table = Table([[p] for p in toc_paragraphs], colWidths=[523])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 14))

    # 5. Process Chapters
    for ch_idx, ch in enumerate(book_data['chapters'], 1):
        # Section Heading
        story.append(Paragraph(ar(f"الباب {ch_idx}: {ch['title']}"), h1_style))
        story.append(HRFlowable(width="100%", thickness=1.2, color=primary_color, spaceAfter=8, spaceBefore=2))

        # Check if chapter has structured sections
        if 'sections' in ch:
            for sec in ch['sections']:
                story.append(Paragraph(ar(sec['heading']), h2_style))
                for p in sec.get('paragraphs', []):
                    story.append(Paragraph(ar(p), body_style))
                for b in sec.get('bullets', []):
                    story.append(Paragraph(ar(f"• {b}"), bullet_style))
                
                # Check for tables inside section
                if 'table' in sec:
                    t_spec = sec['table']
                    table_rows = []
                    # Header
                    h_row = [Paragraph(ar(col), table_header_style) for col in t_spec['headers']]
                    table_rows.append(h_row)
                    # Rows
                    for r in t_spec['rows']:
                        row_cells = [Paragraph(ar(cell), table_cell_style) for cell in r]
                        table_rows.append(row_cells)
                    
                    data_table = Table(table_rows, colWidths=t_spec.get('colWidths', [174, 174, 175]))
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

        elif 'raw_content' in ch:
            for line in ch['raw_content'].split("\n"):
                line_str = line.strip()
                if not line_str:
                    continue
                if line_str.startswith("-") or line_str.startswith("*"):
                    story.append(Paragraph(ar(f"• {line_str[1:].strip()}"), bullet_style))
                elif line_str.startswith("1.") or line_str.startswith("2.") or line_str.startswith("3.") or line_str.startswith("4.") or line_str.startswith("5."):
                    story.append(Paragraph(ar(line_str), h2_style))
                else:
                    story.append(Paragraph(ar(line_str), body_style))

        story.append(Spacer(1, 10))

    # 6. Verification and Closing Box
    story.append(Spacer(1, 14))
    close_box = Table(
        [
            [Paragraph(ar("<b>توثيق الاعتماد الرقمي وحقوق الملكية:</b>"), ParagraphStyle('CB1', fontName='VetArialBold', fontSize=9, textColor=colors.HexColor('#0f172a'), alignment=2))],
            [Paragraph(ar("تم تدقيق واعتماد هذه الموسوعة السريرية البيطرية الشاملة بواسطة منصة VetMind AI للذكاء الاصطناعي الطبي البيطري، تحت الإشراف العام المباشر للدكتور تامر سعد (Dr. Tamer Saad). مخصص حصرياً لدعم القرار الإكلينيكي للأطباء البيطريين المرخصين."), ParagraphStyle('CB2', fontName='VetArial', fontSize=8, leading=11, textColor=colors.HexColor('#475569'), alignment=2))]
        ],
        colWidths=[523]
    )
    close_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(close_box)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Built massive PDF: {out_path} ({os.path.getsize(out_path)} bytes)")

def build_all_massive_arab_books():
    print("Building all 10 massive Arab veterinary clinical books...")
    for ref_id, book in MASSIVE_ARAB_BOOKS.items():
        ar_name = book['filename_ar']
        web_path = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
        desktop_path = os.path.join(DESKTOP_ARAB_DIR, f"{ar_name}.pdf")

        build_massive_pdf(ref_id, book, web_path)
        shutil.copyfile(web_path, desktop_path)

    print("Completed building and copying all 10 massive Arab PDFs.")

    # Re-bundle ZIP
    update_complete_zip()

def update_complete_zip():
    print("Rebuilding complete ZIP bundles...")
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
    print("Complete ZIP bundle rebuilt! Size:", round(os.path.getsize(all_zip_path)/1024/1024, 2), "MB")

if __name__ == "__main__":
    build_all_massive_arab_books()
