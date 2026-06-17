@echo off
echo Starting GitHub Sync...
git add .
git commit -m "Auto-sync: %date% %time%"
git push origin main
echo Sync completed successfully!
pause