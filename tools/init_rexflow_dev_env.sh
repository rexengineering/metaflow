#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

export PYTHONPATH=$SCRIPT_DIR/..:$PYTHONPATH
export FLOWD_HOST=localhost
export FLOWD_PORT=80

alias flowctl='python -m flowctl'
