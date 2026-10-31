# -*- coding: utf-8 -*-
import base64
import json
import ssl
import sys
import urllib.request
import urllib.error
from PIL import Image
import io

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

import os
api_key = os.environ.get("GROQ_API_KEY", "")
img_path = r"C:\Users\tamersaad\Desktop\vetmind-ai\uploads\chat_1793405099_صورة_هرم_خوفو.png"

# Resize image to reasonable dimensions for vision model (e.g. max 1024x1024) and save as JPEG
with Image.open(img_path) as im:
    im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="JPEG", quality=85)
    b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

print(f"Base64 image size: {len(b64_img)/1024:.1f} KB")

# Check available models on Groq
req_models = urllib.request.Request(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)
with urllib.request.urlopen(req_models, context=ctx) as r:
    models_data = json.loads(r.read().decode("utf-8"))
    vision_available = [m["id"] for m in models_data["data"] if "vision" in m["id"].lower()]
    print("Available vision models:", vision_available)

for model in vision_available:
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "ماذا يظهر في هذه الصورة؟ هل هي حالة بيطرية؟"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_img}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"SUCCESS with {model}:")
            print(data["choices"][0]["message"]["content"])
            break
    except urllib.error.HTTPError as e:
        print(f"HTTPError {model}: {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Error {model}: {e}")
