#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

DEST_DIR="$1" ./docker_run.sh /bin/bash
