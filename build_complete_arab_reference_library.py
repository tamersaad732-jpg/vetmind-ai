# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Comprehensive Clinical Arab Veterinary Textbooks Generator
Generates multi-page, publication-grade clinical reference volumes for all 10 Arab references.
Each book contains extensive clinical chapters, disease monographs, differential diagnosis matrices,
laboratory values, pharmacological regimens, surgical workflows, and withdrawal times.
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
        self.setFillColor(colors.HexColor("#475569"))

        # Running Header (from page 2 onwards)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(36, 805, 559, 805)
            h_text = get_display(arabic_reshaper.reshape("منظومة VetMind AI للذكاء الاصطناعي الطبي البيطري | إشراف د. تامر سعد"))
            self.drawRightString(559, 810, h_text)
            self.drawString(36, 810, "VetMind Enterprise - Arab Veterinary Reference Library")

        # Running Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(36, 45, 559, 45)

        f_text = get_display(arabic_reshaper.reshape(f"صفحة {self._pageNumber} من {total_pages}"))
        self.drawRightString(559, 32, f_text)
        footer_sub = get_display(arabic_reshaper.reshape("الموسوعة السريرية البيطرية المعتمدة - مخصص حصرياً للأطباء البيطريين المرخصين"))
        self.drawString(36, 32, footer_sub)
        self.restoreState()

def ar(text):
    if not text:
        return ""
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)

print("NumberedCanvas and Arab text reshaping configured.")
