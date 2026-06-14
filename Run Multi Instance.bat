@echo off
cd /d "%~dp0"
py -3.11-64 multi_instance_launcher.py
if errorlevel 1 pause
