#!/bin/bash

# Wait until database is ready
RETRIES=5

until PGPASSWORD=postgresql psql -h "db" -p "5432" -U "postgresql" -d "aplazame" -c "select 1" || [ $RETRIES -eq 0 ]; do
  echo "Waiting for postgres server, $((RETRIES--)) remaining attempts..."
  sleep 1
done

if [ $RETRIES -eq 0 ]
then
    exit 1
fi

# Run migrations

# Load fixtures

# Call entrypoint with args
exec $@