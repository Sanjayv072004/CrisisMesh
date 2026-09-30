.PHONY: run test verify lint build docker-build e2e

# -----------------------------------------------------------------------
# Development
# -----------------------------------------------------------------------
run:
	python -m uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000

run-demo:
	CRISISMESH_DEMO_MODE=true python -m uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000

# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------
test:
	python -m pytest backend/tests/ -v

# -----------------------------------------------------------------------
# Quality Gate — runs ALL checks required for submission
# -----------------------------------------------------------------------
verify:
	python scripts/verify.py

# -----------------------------------------------------------------------
# Individual lint targets
# -----------------------------------------------------------------------
lint-backend:
	python -m ruff check backend/

lint-frontend:
	cd frontend && npm run lint

lint-types-backend:
	python -m mypy backend/app --ignore-missing-imports --no-strict-optional --explicit-package-bases

lint-types-frontend:
	cd frontend && npx tsc --noEmit

# -----------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------
build-frontend:
	cd frontend && npm run build

# -----------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-up-with-postgres:
	docker compose --profile postgres up -d

docker-down:
	docker compose down

# -----------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------
scan-secrets:
	python scripts/scan_secrets.py

# -----------------------------------------------------------------------
# E2E
# -----------------------------------------------------------------------
e2e:
	python tests/e2e/test_demo_e2e.py
