# -*- coding: utf-8 -*-
import base64
import json
import ssl
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

import os
api_key = os.environ.get("GROQ_API_KEY", "")
img_path = r"C:\Users\tamersaad\Desktop\vetmind-ai\uploads\chat_1793405099_صورة_هرم_خوفو.png"

with open(img_path, "rb") as f:
    b64_img = base64.b64encode(f.read()).decode("utf-8")

# Let's test Groq Vision models
vision_models = [
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview"
]

prompt = "بصفتك مستشار بيطري ذكي، حلل هذه الصورة بدقة. إذا كانت الصورة لا تتعلق بحالة بيطرية أو حيوان أو آفة إكلينيكية (مثل صورة مبنى، هرم، سيارة، شخص، إلخ)، وضح ذلك صراحة واذكر ما يظهر في الصورة بالضبط وبين أنها غير صالحة للتشخيص البيطري. أما إذا كانت حالة بيطرية فقدم التشخيص والعلاج."

for model in vision_models:
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_img}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.2
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "VetMindAI/4.2"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ans = data["choices"][0]["message"]["content"]
            print(f"SUCCESS with {model}:")
            print(ans)
            break
    except Exception as e:
        print(f"FAILED with {model}: {e}")
