#!/bin/sh
# Container entrypoint: bring the schema up to date via Alembic before the
# bot process starts. If migrations fail, the container exits non-zero and
# never starts polling against a schema it can't trust.
set -e

echo "Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo "Starting bot..."
exec python -m app.main
