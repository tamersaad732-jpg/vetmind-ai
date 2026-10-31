@echo off
chcp 65001 > nul
title VetMind AI - رفع المشروع إلى GitHub
color 0A
echo ========================================================
echo   VetMind AI Enterprise v4.3 - رفع المشروع إلى GitHub
echo ========================================================
echo.
echo جاري رفع أحدث نسخة من المشروع وقاعدة البيانات إلى:
echo https://github.com/tamersaad732-jpg/vetmind-ai.git
echo.
cd /d "C:\Users\tamersaad\Desktop\vetmind-ai"
"bin\git\cmd\git.exe" push -u origin main
echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo   [نجاح] تم رفع المشروع بالكامل إلى GitHub بنجاح!
    echo   الآن يمكنك الذهاب إلى Render.com وربط المستودع.
    echo ========================================================
) else (
    echo ========================================================
    echo   إذا طلب منك كلمة المرور، يرجى إدخال Personal Access Token
    echo   أو نسخ الرمز وإرساله لي لأقوم بالرفع بدلا منك.
    echo ========================================================
)
echo.
pause
