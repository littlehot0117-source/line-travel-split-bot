@echo off
cd /d "C:\Users\Username\.gemini\antigravity\scratch\line-travel-split-bot"
echo ========================================================
echo   Pushing code to GitHub...
echo ========================================================
"C:\Program Files\Git\cmd\git.exe" push -u origin main
echo.
if %errorlevel% equ 0 (
    echo ========================================================
    echo   [SUCCESS] Code pushed to GitHub successfully!
    echo   Please go to Render.com to check deployment.
    echo ========================================================
) else (
    echo ========================================================
    echo   [FAILED] Push failed. Please check GitHub login.
    echo ========================================================
)
pause
