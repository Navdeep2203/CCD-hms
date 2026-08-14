@echo off
cd /d "%~dp0"
start "Hotel API" cmd /k run-backend.bat
start "Hotel UI" cmd /k run-frontend.bat

