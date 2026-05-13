.PHONY: dev build start

dev:
	cd backend && nix-shell -p uv python311 --run "uv run uvicorn main:app --reload --port 8000" &
	cd frontend && yarn dev

build:
	cd frontend && yarn build
	cp -r frontend/out backend/static

start:
	cd backend && nix-shell -p uv python311 --run "uv run uvicorn main:app --port 8000"
