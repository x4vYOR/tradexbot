#!/usr/bin/env bash
set -e
source "/home/x4vyjm/tradexbot/tradexenv/bin/activate"
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8080  main:app
