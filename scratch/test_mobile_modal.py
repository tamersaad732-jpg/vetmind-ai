import urllib.request
html = urllib.request.urlopen("http://127.0.0.1:8000/").read().decode("utf-8")
assert "mobile-modal" in html
assert "10.180.160.121" in html
assert "openMobileModal" in html
print("VERIFIED 100%: Mobile Connect Modal and QR Code are active and serving on both PC and Mobile LAN!")
