#!/bin/bash

. activate exclusive-gateway
export PYTHONPATH=${PYTHONPATH}:.

exec gunicorn -k gthread --threads 8 -b :5000 --reload --timeout 120 --forwarded-allow-ips="*" --log-level=debug --error-logfile - --access-logfile - 'code.routes:app'
