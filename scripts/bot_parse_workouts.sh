#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/semaine.pdf" >&2
  exit 1
fi

PDF_PATH="$1"

cd /home/aptsdae/garmin_parser_docker

python3 /home/aptsdae/garmin_parser_docker/scripts/clawdbot_workflow.py \
  --action parse_workouts \
  --file "$PDF_PATH"
