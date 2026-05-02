@echo off
REM start_ggapi.bat — auto-start by Windows Task Scheduler at server boot
REM Scheduled task: run as highest privileges, run whether user logged in or not

cd /d C:\ai\ggapi

REM Activate venv if one exists, otherwise use system python
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Run uvicorn bound to localhost only (IIS reverse proxies from IIS -> 127.0.0.1:8001)
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --workers 1 --log-file C:\ai\ggapi\ggapi.log
