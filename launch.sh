#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Living Journal needs Python3.10+. Install python3 using your Linux software manager.' >&2
  exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$HERE/app/launcher.py" "$@"
