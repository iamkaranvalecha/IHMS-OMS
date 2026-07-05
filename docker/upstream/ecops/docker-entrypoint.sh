#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

echo "==> EC-OPS: waiting for PostgreSQL"
until uv run python -c "
import asyncio, os, sys
import asyncpg

async def main():
    url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url, timeout=2)
    await conn.close()

asyncio.run(main())
" 2>/dev/null; do
  sleep 2
done

# migrate.py reads DATABASE_URL from .env on disk
printf 'DATABASE_URL=%s\n' "$DATABASE_URL" > /app/.env

echo "==> EC-OPS: applying migrations"
uv run python scripts/migrate.py

echo "==> EC-OPS: starting API on port ${PORT:-8002}"
exec uv run python -m src.main
