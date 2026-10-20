#!/bin/sh
set -eu

case "${1:-}" in
    "")
        python -m app.migrate
        exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
        ;;
    --seed)
        python -m app.migrate --seed
        exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
        ;;
    *)
        exec "$@"
        ;;
esac