PY := .venv/Scripts/python

.PHONY: help backend-venv backend-install backend-migrate backend-seed backend-test frontend-install dev

help:
	@echo "Targets:"
	@echo "  backend-venv      - create .venv (Python 3.11)"
	@echo "  backend-install   - install Python deps into .venv (creates venv if missing)"
	@echo "  backend-migrate   - run alembic upgrade head"
	@echo "  backend-seed      - seed the Imperial tenant and demo users"
	@echo "  backend-test      - run pytest"
	@echo "  frontend-install  - install pnpm deps"
	@echo "  dev               - start backend + frontend (requires postgres+redis up)"

backend-venv:
	cd backend && python -m venv .venv

backend-install:
	cd backend && [ -d .venv ] || python -m venv .venv
	cd backend && $(PY) -m pip install --upgrade pip
	cd backend && $(PY) -m pip install -e ".[dev]"

backend-migrate:
	cd backend && $(PY) -m alembic upgrade head

backend-seed:
	cd backend && $(PY) scripts/seed_users.py

backend-test:
	cd backend && $(PY) -m pytest -v

frontend-install:
	cd frontend && pnpm install

dev:
	@echo "Run these in two terminals (activate the backend venv first):"
	@echo "  cd backend && uvicorn app.main:app --reload --port 8000"
	@echo "  cd frontend && pnpm dev"
