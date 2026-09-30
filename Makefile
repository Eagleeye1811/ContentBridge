.PHONY: up down logs migrate revision seed demo api web test fmt

up:            ## Start the whole stack
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api

migrate:       ## Apply migrations (inside the api container)
	docker compose exec api alembic upgrade head

revision:      ## make revision m="add widgets"
	docker compose exec api alembic revision --autogenerate -m "$(m)"

demo:          ## Run the end-to-end walkthrough against a running API
	cd backend && .venv/bin/python ../scripts/demo.py

seed:          ## Create demo editor + approver accounts
	docker compose exec api python -m app.seed

api:           ## Run the API on the host (needs postgres+qdrant up)
	cd backend && uv run uvicorn app.main:app --reload

web:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest -q

fmt:
	cd backend && uv run ruff format . && uv run ruff check --fix .
