# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import urllib.parse
import http.cookiejar
import re

LANGUAGES = ['ar', 'en', 'fr', 'de', 'es', 'it', 'zh', 'ja']

EXPECTED_SNIPPETS = {
    'ar': {
        'dir': 'dir="rtl"',
        'html_lang': 'lang="ar"',
        'prayer_name': 'صلاة',
        'home_nav': 'الرئيسية',
        'tools_title': 'باقة الـ 30 ميزة والأدوات السريرية البيطرية المتقدمة',
        'about_founder': 'دكتور تامر سعد',
        'terms_notice': 'التنبيه الإكلينيكي والطبي العام'
    },
    'en': {
        'dir': 'dir="ltr"',
        'html_lang': 'lang="en"',
        'prayer_name': 'Prayer',
        'home_nav': 'Home',
        'tools_title': '30 Advanced Clinical Veterinary Tools',
        'about_founder': 'Dr. Tamer Saad',
        'terms_notice': 'General Clinical & Medical Scope'
    },
    'fr': {
        'dir': 'dir="ltr"',
        'html_lang': 'lang="fr"',
        'prayer_name': 'Prière',
        'home_nav': 'Accueil',
        'tools_title': 'Suite des 30 Outils Cliniques Vétérinaires Avancés',
        'about_founder': 'Dr. Tamer Saad',
        'terms_notice': 'General Clinical & Medical Scope'
    },
    'de': {
        'dir': 'dir="ltr"',
        'html_lang': 'lang="de"',
        'prayer_name': 'Gebet',
        'home_nav': 'Startseite',
        'tools_title': 'Suite der 30 fortschrittlichen klinischen Veterinärwerkzeuge',
        'about_founder': 'Dr. Tamer Saad',
        'terms_notice': 'General Clinical & Medical Scope'
    },
    'es': {
        'dir': 'dir="ltr"',
        'html_lang': 'lang="es"',
        'prayer_name': 'Oración',
        'home_nav': 'Inicio',
        'tools_title': 'Suite de 30 Herramientas Clínicas Veterinarias Avanzadas',
        'about_founder': 'Dr. Tamer Saad',
        'terms_notice': 'General Clinical & Medical Scope'
    },
    'it': {
        'dir': 'dir="ltr"',
        'html_lang': 'lang="it"',
        'prayer_name': 'Preghiera',
        'home_nav': 'Home',
        'tools_title': 'Suite dei 30 Strumenti Clinici Veterinari Avanzati',
        'about_founder': 'Dr. Tamer Saad',
        'terms_notice': 'General Clinical & Medical Scope'
    },
    'zh': {
        'dir': 'dir="ltr"',
        'html_lang': 'lang="zh"',
        'prayer_name': '礼',
        'home_nav': '首页',
        'tools_title': '30项高级兽医临床与企业级决策工具套件',
        'about_founder': 'Dr. Tamer Saad',
        'terms_notice': 'General Clinical & Medical Scope'
    },
    'ja': {
        'dir': 'dir="ltr"',
        'html_lang': 'lang="ja"',
        'prayer_name': '礼拝',
        'home_nav': 'ホーム',
        'tools_title': '30の高度獣医臨床ツール＆エンタープライズ統合スイート',
        'about_founder': 'Dr. Tamer Saad',
        'terms_notice': 'General Clinical & Medical Scope'
    }
}

all_passed = True
print("======================================================================")
print("VETMIND AI ENTERPRISE - MULTILINGUAL COMPREHENSIVE VERIFICATION SUITE")
print("======================================================================")

for lang in LANGUAGES:
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    exp = EXPECTED_SNIPPETS[lang]

    # 1. Switch language via /set-language/{lang}
    resp_home = opener.open(f"http://127.0.0.1:8000/set-language/{lang}")
    html_home = resp_home.read().decode('utf-8')

    has_dir = exp['dir'] in html_home
    has_html_lang = exp['html_lang'] in html_home
    has_prayer = exp['prayer_name'] in html_home
    has_home_nav = exp['home_nav'] in html_home

    # 2. Check /tools page
    resp_tools = opener.open("http://127.0.0.1:8000/tools")
    html_tools = resp_tools.read().decode('utf-8')
    has_tools_title = exp['tools_title'] in html_tools

    # 3. Check /about page
    resp_about = opener.open("http://127.0.0.1:8000/about")
    html_about = resp_about.read().decode('utf-8')
    has_about_founder = exp['about_founder'] in html_about

    # 4. Check /terms page
    resp_terms = opener.open("http://127.0.0.1:8000/terms")
    html_terms = resp_terms.read().decode('utf-8')
    has_terms_notice = exp['terms_notice'] in html_terms

    lang_pass = all([has_dir, has_html_lang, has_prayer, has_home_nav, has_tools_title, has_about_founder, has_terms_notice])
    if not lang_pass:
        all_passed = False

    status_symbol = "✅ PASS" if lang_pass else "❌ FAIL"
    print(f"\nLanguage: [{lang.upper()}] -> {status_symbol}")
    print(f"  • HTML dir ({exp['dir']}): {has_dir}")
    print(f"  • HTML lang ({exp['html_lang']}): {has_html_lang}")
    print(f"  • Prayer Widget ({exp['prayer_name']}): {has_prayer}")
    print(f"  • Navbar Item ({exp['home_nav']}): {has_home_nav}")
    print(f"  • Tools Suite Title ({exp['tools_title'][:30]}...): {has_tools_title}")
    print(f"  • About Founder ({exp['about_founder']}): {has_about_founder}")
    print(f"  • Terms Notice ({exp['terms_notice'][:30]}...): {has_terms_notice}")

print("\n" + "="*70)
print(f"ALL 8 LANGUAGES FULLY FUNCTIONAL AND VERIFIED: {all_passed}")
print("="*70)
