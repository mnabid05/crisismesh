SHELL := /bin/sh

.PHONY: help test test-go test-python test-web lint dev build compose-up compose-down

help:
	@echo "CrisisMesh commands: test, lint, build, dev, compose-up, compose-down"

test: test-go test-python test-web

test-go:
	cd services/api && go test ./...
	cd services/ingestor && go test ./...

test-python:
	cd services/intelligence && python -m pytest

test-web:
	pnpm --filter @crisismesh/web typecheck

lint:
	cd services/api && go vet ./...
	cd services/ingestor && go vet ./...
	cd services/intelligence && python -m ruff check .
	pnpm --filter @crisismesh/web lint

build:
	cd services/api && go build ./cmd/server
	cd services/ingestor && go build ./cmd/ingestor
	pnpm --filter @crisismesh/web build

dev:
	docker compose up --build

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down
