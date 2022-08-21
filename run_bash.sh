#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

declare -a DEST_DIR="$1"
. ./docker_run.sh /bin/bash
