# Shortcuts for running the stack. `make` alone lists the targets;
# `make setup` does everything the first time.

# compose reads .env on its own; including it here gives make the same values.
-include .env

export DOCKER_UID := $(shell id -u)
export DOCKER_GID := $(shell id -g)

MY_PROJECT ?= inspire-mcp-search
POSTGRES_USER ?= changeme
OLLAMA_EMBEDDING_MODEL ?= nomic-embed-text

COMPOSE := docker compose -p $(MY_PROJECT) -f compose.yml
ifneq ($(wildcard compose.dev.yml),)
COMPOSE += -f compose.dev.yml
endif
ifeq ($(USE_GPU),1)
COMPOSE += -f compose.gpu.yml
endif

# -T: no TTY, so the commands also work from scripts and MCP clients.
MANAGE := $(COMPOSE) exec -T web python manage.py

QUERY ?= dark matter detection
MAX_RECORDS ?= 2000
Q ?= an experiment that must be free of radioactive contamination
LIMIT ?= 3
WEB_PORT ?= 9001
BIND_HOST ?= 127.0.0.1

.DEFAULT_GOAL := help
.PHONY: help setup up down ps logs model migrate ingest search mcp test lint

help: ## List the targets
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-8s %s\n", $$1, $$2}'

# Created only when missing, so a hand-edited .env is never overwritten.
.env:
	@cp env_dist .env
	@echo "Created .env from env_dist: change POSTGRES_* and SECRET_KEY before exposing the stack." >&2

setup: up model migrate ingest ## First run: start, pull the model, migrate, ingest

up: .env ## Start ollama, db and web in the background
	$(COMPOSE) up -d

down: ## Stop the stack (volumes are kept)
	$(COMPOSE) down

ps: ## Show the containers
	$(COMPOSE) ps

logs: ## Follow the logs
	$(COMPOSE) logs -f

model: ## Pull the embedding model into Ollama
	@until $(COMPOSE) exec -T ollama ollama list >/dev/null 2>&1; do sleep 1; done
	$(COMPOSE) exec -T ollama ollama pull $(OLLAMA_EMBEDDING_MODEL)

migrate: ## Apply the database migrations
	@until $(COMPOSE) exec -T db pg_isready -U $(POSTGRES_USER) >/dev/null 2>&1; do sleep 1; done
	$(MANAGE) migrate

ingest: ## Fetch and embed papers (QUERY="..." MAX_RECORDS=N)
	$(MANAGE) ingest_inspire --query "$(QUERY)" --max-records $(MAX_RECORDS)

search: ## Search over REST (Q="..." LIMIT=N)
	@curl -sS -G "http://$(BIND_HOST):$(WEB_PORT)/api/search/" \
		--data-urlencode "q=$(Q)" --data-urlencode "limit=$(LIMIT)"; echo

# stdio carries the JSON-RPC stream: nothing else may reach stdout, hence the @.
# Use `make -s mcp` from an MCP client so make prints nothing either.
mcp: ## Start the MCP server on stdio (stack must be up)
	@$(MANAGE) mcp_server

test: ## Run the test suite
	$(COMPOSE) run --rm web pytest -q

lint: ## Run ruff
	$(COMPOSE) run --rm web ruff check .
