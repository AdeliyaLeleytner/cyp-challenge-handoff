#!/bin/bash
set -euo pipefail
if ! command -v rsync >/dev/null 2>&1; then apt-get update -qq; apt-get install -y -qq rsync; fi
exec python -u -m night.admetlab_web
