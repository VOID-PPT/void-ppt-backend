.PHONY: dev test lint format migrate revision docker-up docker-down

# Local development with uv
dev:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run test suite
test:
	uv run pytest -v

# Lint with ruff
lint:
	uv run ruff check --fix

# Format code with ruff
format:
	uv run ruff format

# Generate migration revision (e.g., make revision msg="add_table")
revision:
	uv run alembic revision --autogenerate -m "$(msg)"

# Apply migrations to database
migrate:
	uv run alembic upgrade head

# Rollback one migration
rollback:
	uv run alembic downgrade -1

# Production Docker Compose commands
docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
