# -*- coding: utf-8 -*-
"""
Generate crisp, professional Veterinary Snake Logo (SVG and high-res PNGs)
"""
import os
from PIL import Image, ImageDraw
import math

STATIC_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai\static"
os.makedirs(STATIC_DIR, exist_ok=True)

# 1. Pure SVG Logo (Scalable, razor-sharp on all screens, Retina & Chrome tabs)
svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#047857" />
      <stop offset="50%" stop-color="#065f46" />
      <stop offset="100%" stop-color="#022c22" />
    </linearGradient>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef08a" />
      <stop offset="50%" stop-color="#f59e0b" />
      <stop offset="100%" stop-color="#d97706" />
    </linearGradient>
    <linearGradient id="snakeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#34d399" />
      <stop offset="50%" stop-color="#10b981" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>
    <linearGradient id="staffGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f8fafc" />
      <stop offset="50%" stop-color="#e2e8f0" />
      <stop offset="100%" stop-color="#cbd5e1" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
  </defs>

  <!-- Outer Circle Badge -->
  <circle cx="256" cy="256" r="240" fill="url(#bgGrad)" stroke="#34d399" stroke-width="10" filter="url(#shadow)"/>
  <circle cx="256" cy="256" r="225" fill="none" stroke="#f59e0b" stroke-width="3" stroke-dasharray="10 8" opacity="0.6"/>

  <!-- Veterinary 'V' Emblem -->
  <path d="M 120 140 L 256 420 L 392 140" fill="none" stroke="url(#goldGrad)" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>

  <!-- Staff of Asclepius (Central Rod) -->
  <line x1="256" y1="80" x2="256" y2="435" stroke="url(#staffGrad)" stroke-width="20" stroke-linecap="round"/>
  <!-- Staff Top Golden Orb Knob -->
  <circle cx="256" cy="78" r="24" fill="url(#goldGrad)" stroke="#ffffff" stroke-width="4"/>

  <!-- The Coiled Serpent (Smooth Double Helix Wave) -->
  <path d="M 200 155 
           C 310 140, 315 195, 256 220 
           C 195 245, 190 300, 256 325 
           C 320 350, 310 405, 250 420" 
        fill="none" stroke="url(#snakeGrad)" stroke-width="26" stroke-linecap="round"/>

  <!-- Snake Head (Majestic & Medical) -->
  <g transform="translate(198, 155)">
    <ellipse cx="0" cy="0" rx="20" ry="16" fill="url(#snakeGrad)" stroke="#065f46" stroke-width="3" transform="rotate(-25)"/>
    <!-- Snake Eye -->
    <circle cx="4" cy="-3" r="4.5" fill="#fef08a"/>
    <circle cx="4" cy="-3" r="2.5" fill="#0f172a"/>
    <!-- Snake Forked Tongue -->
    <path d="M -16 2 L -28 6 M -16 2 L -26 -3" stroke="#ef4444" stroke-width="3.5" stroke-linecap="round"/>
  </g>
</svg>'''

with open(os.path.join(STATIC_DIR, "logo-snake.svg"), "w", encoding="utf-8") as f:
    f.write(svg_content)

with open(os.path.join(STATIC_DIR, "favicon.svg"), "w", encoding="utf-8") as f:
    f.write(svg_content)

print("SUCCESS: Created static/logo-snake.svg and static/favicon.svg")

# 2. Render High-Resolution PNG Icons (icon-192.png, icon-512.png)
def render_snake_png(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    pad = int(size * 0.04)
    cx, cy = size // 2, size // 2
    r = size // 2 - pad
    
    # Outer circle background
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(4, 120, 87, 255), outline=(52, 211, 153, 255), width=max(3, size // 35))
    
    # Inner border
    r_in = r - int(size * 0.04)
    draw.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], outline=(245, 158, 11, 200), width=max(1, size // 80))
    
    # Veterinary 'V'
    v_w = max(4, size // 15)
    lx, ty = int(size * 0.23), int(size * 0.27)
    rx = int(size * 0.77)
    bx, by = cx, int(size * 0.83)
    gold = (245, 158, 11, 245)
    draw.line([(lx, ty), (bx, by)], fill=gold, width=v_w)
    draw.line([(rx, ty), (bx, by)], fill=gold, width=v_w)
    
    # Central Staff
    staff_w = max(3, size // 24)
    s_top = int(size * 0.15)
    s_bot = int(size * 0.85)
    draw.line([(cx, s_top), (cx, s_bot)], fill=(248, 250, 252, 255), width=staff_w)
    
    # Staff top knob
    knob_r = max(4, size // 20)
    draw.ellipse([cx - knob_r, s_top - knob_r, cx + knob_r, s_top + knob_r], fill=(245, 158, 11, 255), outline=(255, 255, 255, 255), width=max(1, size // 70))
    
    # Snake Body
    snake_w = max(4, size // 17)
    snake_color = (52, 211, 153, 255)
    
    pts = []
    steps = 120
    for i in range(steps):
        t = i / (steps - 1)
        y = (s_top + int(size * 0.08)) + t * (s_bot - s_top - int(size * 0.12))
        amp = size * 0.13 * (1.0 - 0.22 * t)
        freq = 3.6 * math.pi
        x = cx + amp * math.sin(t * freq)
        pts.append((x, y))
        
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=snake_color, width=snake_w)
        
    # Snake Head
    hx, hy = pts[0]
    hr = max(5, size // 16)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=snake_color, outline=(6, 95, 70, 255), width=max(1, size // 70))
    
    # Eye
    er = max(1, size // 45)
    draw.ellipse([hx + int(hr*0.2) - er, hy - int(hr*0.2) - er, hx + int(hr*0.2) + er, hy - int(hr*0.2) + er], fill=(254, 240, 138, 255))
    draw.ellipse([hx + int(hr*0.2) - er//2, hy - int(hr*0.2) - er//2, hx + int(hr*0.2) + er//2, hy - int(hr*0.2) + er//2], fill=(15, 23, 42, 255))
    
    # Red tongue
    draw.line([(hx - hr, hy), (hx - hr - int(size*0.025), hy - int(size*0.015))], fill=(239, 68, 68, 255), width=max(1, size // 75))
    draw.line([(hx - hr, hy), (hx - hr - int(size*0.025), hy + int(size*0.015))], fill=(239, 68, 68, 255), width=max(1, size // 75))
    
    return img

img192 = render_snake_png(192)
img192.save(os.path.join(STATIC_DIR, "icon-192.png"))

img512 = render_snake_png(512)
img512.save(os.path.join(STATIC_DIR, "icon-512.png"))

print("SUCCESS: Rendered static/icon-192.png and static/icon-512.png")
