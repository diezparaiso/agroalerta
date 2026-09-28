#!/usr/bin/env bash
set -euo pipefail

# Ejecuta un ciclo completo fuera del proceso HTTP.
# El scheduler del entorno debe proporcionar aislamiento de concurrencia.
cd "$(dirname "$0")/.."

exec python -m app.jobs.agroclimatic_cycle
