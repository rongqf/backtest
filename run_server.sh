#!/bin/bash

# 启动 uvicorn 服务器 (后台运行)
/home/clive/miniconda/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --reload > server.log 2>&1 &