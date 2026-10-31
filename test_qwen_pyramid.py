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

with Image.open(img_path) as im:
    im.thumbnail((800, 800))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="JPEG", quality=80)
    b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

prompt = """أنت المستشار البيطري الذكي في منصة VetMind AI.
انظر إلى الصورة المرفقة بعناية فائقة:
1. هل تحتوي هذه الصورة على حالة بيطرية سريرية أو حيوان أو آفة إكلينيكية؟
2. إذا كانت الصورة لا تخص الطب البيطري (مثلاً: صورة هرم، مبنى، سيارة، منظر طبيعي، شخص، أو أي شيء غير بيطري)، فأجب بوضوح وصراحة: '❌ الصورة المرفقة غير صالحة للتشخيص البيطري' واذكر بالتفصيل ما تراه في الصورة (مثلاً: أهرامات الجيزة)، واطلب من الطبيب رفع صورة لآفة أو حالة حيوانية حقيقية.
3. أما إذا كانت حالة بيطرية حقيقية، فقدم التوصيف الدقيق والتشخيص التفريقي."""

url = "https://api.groq.com/openai/v1/chat/completions"
payload = {
    "model": "qwen/qwen3.8-27b",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_img}"
                    }
                }
            ]
        }
    ],
    "max_tokens": 600,
    "temperature": 0.2
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("=== RESPONSE FROM QWEN VISION ===")
        print(res["choices"][0]["message"]["content"])
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read().decode("utf-8"))
except Exception as e:
    print("Error:", e)
