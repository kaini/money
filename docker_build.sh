#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

DOCKER_IMG_HASH="$(docker build -q ./docker)"
echo "$DOCKER_IMG_HASH"
