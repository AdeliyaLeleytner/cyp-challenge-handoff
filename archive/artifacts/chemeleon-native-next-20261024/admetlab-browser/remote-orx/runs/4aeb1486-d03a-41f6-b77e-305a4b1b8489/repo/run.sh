#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq xvfb xauth rsync chromium
python -m pip install playwright==1.64.1
dpkg-query -W chromium
exec xvfb-run -a python -u -m night.admetlab_browser
