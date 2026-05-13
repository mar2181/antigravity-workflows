@echo off
echo ============================================ >> "C:\Users\mario\.gemini\antigravity\tools\execution\logs\nightly_intelligence.log"
echo %DATE% %TIME% — Starting nightly_intelligence >> "C:\Users\mario\.gemini\antigravity\tools\execution\logs\nightly_intelligence.log"
echo ============================================ >> "C:\Users\mario\.gemini\antigravity\tools\execution\logs\nightly_intelligence.log"
cd /d "C:\Users\mario\.gemini\antigravity\tools\execution"
"C:\Users\mario\AppData\Local\Programs\Python\Python310\python.exe" nightly_intelligence.py >> "C:\Users\mario\.gemini\antigravity\tools\execution\logs\nightly_intelligence.log" 2>&1
echo Exit code: %ERRORLEVEL% >> "C:\Users\mario\.gemini\antigravity\tools\execution\logs\nightly_intelligence.log"
