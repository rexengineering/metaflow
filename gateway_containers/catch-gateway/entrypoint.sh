#!/bin/bash

. activate catch-gateway
export PYTHONPATH=${PYTHONPATH}:.

python code/catch_event.py
