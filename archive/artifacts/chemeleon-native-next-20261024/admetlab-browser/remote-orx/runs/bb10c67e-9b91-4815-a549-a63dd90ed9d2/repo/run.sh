#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq xvfb xauth rsync
python -m pip install playwright==1.64.1
python -m playwright install --with-deps chromium
exec xvfb-run -a python -u -m night.admetlab_browser
