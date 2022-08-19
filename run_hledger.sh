#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

ARG_1="$1"
shift
DEST_DIR="$ARG_1" ./docker_run.sh hledger "$@"