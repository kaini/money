#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

CODE_DIR="$(pwd)/src"

DOCKER_IMG_HASH="$(./docker_build.sh)"
docker run -it --rm -u "$(id -u $USER)" -v "$CODE_DIR:/code" -v "$DEST_DIR:/dest" -e LANG=C.UTF-8 -e LEDGER_FILE="/dest/main.journal" "${DOCKER_ARGS[@]}" "$DOCKER_IMG_HASH" "$@"
