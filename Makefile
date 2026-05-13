.PHONY: dev build start

dev:
	nix-shell backend/shell.nix --run "cd $(CURDIR)/backend && uv run uvicorn main:app --reload --port 8000" &
	cd frontend && yarn dev

build:
	cd frontend && yarn build
	cp -r frontend/out backend/static

start:
	nix-shell backend/shell.nix --run "cd $(CURDIR)/backend && uv run uvicorn main:app --port 8000"
