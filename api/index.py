from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
def home():
    return HTMLResponse("<h1>VetMind AI Vercel is Working!</h1><p>System Online</p>")

@app.get("/test")
def test():
    return {"status": "ok"}
