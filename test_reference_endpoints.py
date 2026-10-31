import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')
base = 'http://127.0.0.1:8000'

urls_to_test = [
    ('/references', 'References page'),
    ('/references/download-all', 'ZIP all (hyphen)'),
    ('/references/download/all', 'ZIP all (slash)'),
    ('/references/download-arab', 'ZIP arab (hyphen)'),
    ('/references/download/arab', 'ZIP arab (slash)'),
    ('/references/download/arab_1', 'arab_1 attachment'),
    ('/references/pdf/arab_1', 'arab_1 inline PDF'),
    ('/references/download/arab_10', 'arab_10 attachment'),
    ('/references/pdf/arab_10', 'arab_10 inline PDF')
]

for endpoint, desc in urls_to_test:
    req = urllib.request.Request(base + endpoint, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read(100)
            ct = resp.headers.get('Content-Type')
            cd = resp.headers.get('Content-Disposition')
            print(f"PASS: {desc} ({endpoint}) -> Status: {resp.status}, Type: {ct}, Disp: {cd}")
    except Exception as e:
        print(f"FAIL: {desc} ({endpoint}) -> Error: {e}")
