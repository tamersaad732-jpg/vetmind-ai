import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
html = urllib.request.urlopen("http://127.0.0.1:8000/").read().decode("utf-8")
assert "VetBook الأطباء البيطريين" in html
print("VERIFIED 100%: Text 'VetBook الأطباء البيطريين' is present in Home Page HTML!")
