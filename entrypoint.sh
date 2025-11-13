#!/bin/sh
set -e

# Настройки по умолчанию для PostgreSQL
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-itemuser}

echo "⏳ Waiting for PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" >/dev/null 2>&1; do
  sleep 2
done
echo "✅ PostgreSQL is ready!"

# Выполняем миграции и сбор статики только для web (gunicorn)
if echo "$@" | grep -q "gunicorn"; then
  echo "🧩 Applying migrations..."
  python manage.py migrate --noinput

  echo "🎨 Collecting static files..."
  python manage.py collectstatic --noinput
fi

# Запуск основной команды (gunicorn / celery)
exec "$@"
