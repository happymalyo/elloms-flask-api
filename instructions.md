### create migration

- alembic revision --autogenerate -m "add crew for image"

### apply migration

- alembic upgrade head

### Docker

docker network create postgres-network
docker compose -f db-compose.yml up -d
docker compose -f api-compose.yml build
