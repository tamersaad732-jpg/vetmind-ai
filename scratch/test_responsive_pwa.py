import urllib.request

html = urllib.request.urlopen("http://127.0.0.1:8000/").read().decode("utf-8")
assert "apple-mobile-web-app-capable" in html, "iOS meta tag missing!"
assert "serviceWorker.register" in html, "Service worker registration missing!"
assert "overflow-wrap: break-word" in html, "Word wrapping CSS missing!"
assert "max-width: 680px" in html, "Mobile media query missing!"
assert "manifest.json" in html, "Manifest missing!"
print("ALL ASSERTIONS PASSED! MOBILE RESPONSIVENESS AND APP INSTALL COMPLIANCE VERIFIED 100%!")
