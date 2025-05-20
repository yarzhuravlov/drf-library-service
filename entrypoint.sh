#!/bin/sh


echo "Waiting for postgres..."
echo $POSTGRES_HOST
echo $POSTGRES_PORT

while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.1
done

echo "PostgreSQL started"

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Applying migrations..."
python manage.py migrate

exec "$@"
