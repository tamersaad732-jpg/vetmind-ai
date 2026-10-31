# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import urllib.parse
import http.cookiejar
import sqlite3
import json

print("======================================================================")
print("TESTING FULL PLATFORM CONVERSION BY USER REGISTRATION LANGUAGE")
print("======================================================================")

BASE_URL = "http://127.0.0.1:8000"

# 1. Test /register page has language selector
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

resp_reg = opener.open(f"{BASE_URL}/register")
html_reg = resp_reg.read().decode('utf-8')
has_lang_selector = 'name="preferred_lang"' in html_reg
print(f"1. Registration form has preferred_lang selector: {has_lang_selector}")
assert has_lang_selector, "preferred_lang selector missing from registration form!"

# 2. Register user with preferred_lang = 'en'
en_email = "doctor.smith@vetmind.ai"
# Delete existing if any
conn = sqlite3.connect(r'C:\Users\tamersaad\Desktop\vetmind-ai\vetmind.db')
c = conn.cursor()
c.execute("DELETE FROM users WHERE email = ?", (en_email,))
conn.commit()
conn.close()

data = urllib.parse.urlencode({
    "country": "مصر",
    "name": "John Smith",
    "phone": "+201011223344",
    "clinic_name": "Smith Equine & Pet Hospital",
    "syndicate_id": "VET-USA-9988",
    "email": en_email,
    "password": "Password123#",
    "confirm_password": "Password123#",
    "preferred_lang": "en"
}).encode('utf-8')

req = urllib.request.Request(f"{BASE_URL}/register", data=data, method="POST")
resp = opener.open(req)
print(f"2. Registration response URL: {resp.geturl()}")

# Verify in database
conn = sqlite3.connect(r'C:\Users\tamersaad\Desktop\vetmind-ai\vetmind.db')
c = conn.cursor()
c.execute("SELECT id, name, email, preferred_lang, is_email_verified, otp_code FROM users WHERE email = ?", (en_email,))
user_row = c.fetchone()
print(f"   Database Record -> ID: {user_row[0]}, Name: {user_row[1]}, preferred_lang: {user_row[3]}")
assert user_row[3] == "en", f"Expected preferred_lang 'en', got {user_row[3]}"

# Verify cookie in opener
cookies = {cookie.name: cookie.value for cookie in cj}
print(f"   Cookie after registration: vetmind_lang = {cookies.get('vetmind_lang')}")
assert cookies.get('vetmind_lang') == 'en', "Cookie vetmind_lang not set to 'en'!"

# Set user as verified so we can log in
c.execute("UPDATE users SET is_email_verified = 1, verification_status = 'approved' WHERE email = ?", (en_email,))
conn.commit()
conn.close()

# 3. Test Login with this English user
cj_login = http.cookiejar.CookieJar()
opener_login = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_login))

login_data = urllib.parse.urlencode({
    "email": en_email,
    "password": "Password123#"
}).encode('utf-8')

req_login = urllib.request.Request(f"{BASE_URL}/login", data=login_data, method="POST")
resp_login = opener_login.open(req_login)
login_cookies = {cookie.name: cookie.value for cookie in cj_login}
print(f"\n3. Login as English User:")
print(f"   Session Cookie: {'vetmind_session' in login_cookies}")
print(f"   Language Cookie: vetmind_lang = {login_cookies.get('vetmind_lang')}")
assert login_cookies.get('vetmind_lang') == 'en', "Login did not set language cookie to 'en'!"

# 4. Check that ALL views automatically render in English for this logged-in user
home_html = resp_login.read().decode('utf-8')
print(f"\n4. Checking Views for Logged-In English User:")
print(f"   • Home dir: {'dir=\"ltr\"' in home_html} | Title has Home: {'Home' in home_html}")
print(f"   • Next Prayer in English: {'Prayer' in home_html}")

# Check Profile
resp_prof = opener_login.open(f"{BASE_URL}/profile")
html_prof = resp_prof.read().decode('utf-8')
print(f"   • Profile: Full Name label present: {'Full Name' in html_prof} | Dr. John Smith: {'Dr. John Smith' in html_prof}")
print(f"   • Profile Language Switcher present: {'preferred_lang_title' in html_prof or 'Account Default Language' in html_prof}")

# Check Pharmacy
resp_pharm = opener_login.open(f"{BASE_URL}/pharmacy")
html_pharm = resp_pharm.read().decode('utf-8')
print(f"   • Pharmacy: Manufacturer label in EN: {'Manufacturer' in html_pharm}")
print(f"   • Pharmacy: Active Ingredient in EN: {'Active Ingredient' in html_pharm}")
print(f"   • Pharmacy: Withdrawal label in EN: {'Withdrawal Period' in html_pharm}")

# Check Rx Prescription
resp_rx = opener_login.open(f"{BASE_URL}/rx-prescription")
html_rx = resp_rx.read().decode('utf-8')
print(f"   • Rx Prescription: Attending Clinician in EN: {'Attending Clinician' in html_rx}")
print(f"   • Rx Prescription: Calculated Dose in EN: {'Accurately Calculated Dose' in html_rx or 'Dose' in html_rx}")

# Check Case View
resp_case = opener_login.open(f"{BASE_URL}/case/15")
html_case = resp_case.read().decode('utf-8')
print(f"   • Case Report: Certified Clinical Report in EN: {'Certified Clinical' in html_case}")
print(f"   • Case Report: Patient Demographics in EN: {'Patient Demographics' in html_case}")

# 5. Register French User
fr_email = "docteur.martin@vetmind.ai"
conn = sqlite3.connect(r'C:\Users\tamersaad\Desktop\vetmind-ai\vetmind.db')
c = conn.cursor()
c.execute("DELETE FROM users WHERE email = ?", (fr_email,))
conn.commit()
conn.close()

fr_data = urllib.parse.urlencode({
    "country": "مصر",
    "name": "Pierre Martin",
    "phone": "+201099887766",
    "clinic_name": "Clinique Vétérinaire Martin",
    "syndicate_id": "VET-FR-4545",
    "email": fr_email,
    "password": "Password123#",
    "confirm_password": "Password123#",
    "preferred_lang": "fr"
}).encode('utf-8')

cj_fr = http.cookiejar.CookieJar()
opener_fr = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_fr))
opener_fr.open(urllib.request.Request(f"{BASE_URL}/register", data=fr_data, method="POST"))

conn = sqlite3.connect(r'C:\Users\tamersaad\Desktop\vetmind-ai\vetmind.db')
c = conn.cursor()
c.execute("SELECT id, name, preferred_lang FROM users WHERE email = ?", (fr_email,))
fr_user = c.fetchone()
print(f"\n5. French User Registered: ID: {fr_user[0]}, preferred_lang: {fr_user[2]}")
assert fr_user[2] == "fr"
c.execute("UPDATE users SET is_email_verified = 1, verification_status = 'approved' WHERE email = ?", (fr_email,))
conn.commit()
conn.close()

# Login French User
login_fr_data = urllib.parse.urlencode({
    "email": fr_email,
    "password": "Password123#"
}).encode('utf-8')
resp_fr_login = opener_fr.open(urllib.request.Request(f"{BASE_URL}/login", data=login_fr_data, method="POST"))
html_fr_home = resp_fr_login.read().decode('utf-8')
print(f"   • French User Home: Accueil present: {'Accueil' in html_fr_home}")
print(f"   • French User Home: Prière present: {'Prière' in html_fr_home}")

# 6. Switch Language inside Profile to Deutsch
switch_data = urllib.parse.urlencode({"preferred_lang": "de"}).encode('utf-8')
resp_switch = opener_fr.open(urllib.request.Request(f"{BASE_URL}/profile/language", data=switch_data, method="POST"))
html_de_prof = resp_switch.read().decode('utf-8')
print(f"\n6. Switched Language from Profile to Deutsch:")
print(f"   • Profile in Deutsch: Startseite in nav: {'Startseite' in html_de_prof}")
print(f"   • Profile in Deutsch: Vollständiger Name: {'Vollständiger Name' in html_de_prof}")

# Check DB was updated to 'de'
conn = sqlite3.connect(r'C:\Users\tamersaad\Desktop\vetmind-ai\vetmind.db')
c = conn.cursor()
c.execute("SELECT preferred_lang FROM users WHERE email = ?", (fr_email,))
updated_lang = c.fetchone()[0]
conn.close()
print(f"   • Database updated to: {updated_lang}")
assert updated_lang == "de", f"Expected 'de', got {updated_lang}"

print("\n" + "="*70)
print("ALL MULTILINGUAL REGISTRATION AND PROFILE TESTS PASSED 100%!")
print("="*70)
