#!/usr/bin/env bash
set -eo pipefail

cd streamlit
docker build -f Dockerfile -t "$1" .
