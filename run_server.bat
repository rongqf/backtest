@echo off

REM 启动 uvicorn 服务器 (后台运行)
start "uvicorn server" /min uvicorn server:app --host 0.0.0.0 --port 8000 --reload > server.log 2>&1