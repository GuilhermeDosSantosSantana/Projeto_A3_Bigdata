@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0INICIAR_MYSQL_GIRO.ps1"
if errorlevel 1 pause
