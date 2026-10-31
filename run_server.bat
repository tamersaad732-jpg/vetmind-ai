@echo off
chcp 65001 >nul
title تشغيل VetMind AI محلياً (Development Server)
cd /d "C:\Users\tamersaad\Desktop\vetmind-ai"
echo ========================================================
echo   تشغيل سيرفر VetMind AI للتجربة المحلية على الكمبيوتر
echo   الرابط المحلي: http://localhost:8000
echo   الرابط السحابي الدائم 24/7: https://vetmind-ai.vercel.app/
echo ========================================================
".\venv\Scripts\uvicorn.exe" app:app --host 127.0.0.1 --port 8000 --reload
pause
