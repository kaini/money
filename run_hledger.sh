#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

DEST_DIR="$1" ./docker_run.sh --env LEDGER_FILE="/dest/main.journal" hledger