#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

declare -a DEST_DIR="$1"
shift
. ./docker_run.sh hledger "$@"