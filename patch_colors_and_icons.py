# -*- coding: utf-8 -*-
with open(r'C:\Users\tamersaad\Desktop\vetmind-ai\app.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''    <meta name="theme-color" content="#0f766e">
    <link rel="icon" type="image/png" href="/static/icon-192.png">
    <style>
        :root {
            --primary: #0f766e;
            --primary-dark: #115e59;
            --primary-light: #ccfbf1;
            --accent: #ea580c;
            --gold: #d97706;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --danger: #dc2626;
            --danger-bg: #fef2f2;
            --success: #16a34a;
            --success-bg: #f0fdf4;
            --warning: #d97706;
            --warning-bg: #fffbeb;
        }
        body.dark-theme {
            --bg: #090d16;
            --card-bg: #131b2e;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #1e293b;
            --danger-bg: #450a0a;
            --success-bg: #052e16;
            --warning-bg: #451a03;
        }'''

# Replace with double-bracketed version
target_double = target.replace('{', '{{').replace('}', '}}')

replacement_double = '''    <meta name="theme-color" content="#047857">
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <link rel="alternate icon" type="image/png" href="/static/icon-192.png">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <style>
        :root {{
            /* High-Contrast, Eye-Friendly Medical Palette */
            --primary: #047857;
            --primary-dark: #065f46;
            --primary-light: #ecfdf5;
            --accent: #ea580c;
            --gold: #d97706;
            --bg: #f1f5f9;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #475569;
            --border: #cbd5e1;
            --danger: #dc2626;
            --danger-bg: #fef2f2;
            --success: #16a34a;
            --success-bg: #f0fdf4;
            --warning: #d97706;
            --warning-bg: #fffbeb;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        }}
        body.dark-theme {{
            --bg: #030712;
            --card-bg: #111827;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --border: #1f2937;
            --danger-bg: #450a0a;
            --success-bg: #052e16;
            --warning-bg: #451a03;
            --shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
        }}'''

if target_double in text:
    text = text.replace(target_double, replacement_double)
    with open(r'C:\Users\tamersaad\Desktop\vetmind-ai\app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Updated app.py Head with SVG snake icon & high-contrast colors!")
else:
    print("Error: target_double not found.")
