#!/usr/bin/env bash
set -e
source "/home/x4vyjm/tradexbot/tradexbot/bin/activate"
celery --broker redis://127.0.0.1:6379 --result-backend redis://127.0.0.1:6379 -A worker.celery worker -l INFO --logfile tradexbot.log --pool=solo
