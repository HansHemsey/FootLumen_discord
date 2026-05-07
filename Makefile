PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
CLI ?= scripts/football_predictor_cli.sh
DOCKER ?= docker
COMPOSE ?= docker compose
DOCKER_IMAGE ?= football-predictor:local
DATE ?= $(shell date +%F)
WINDOW ?= early
FIXTURE_ID ?=
DATASET ?= data/processed/training_v2_late.parquet
MODEL_DIR ?= data/models/v2-late
BACKTEST_DIR ?= reports/backtest_v2_late
MODEL_VERSION ?= v2-late
PREDICT_TODAY_ARGS ?= --date $(DATE) --window $(WINDOW) --no-refresh-data --dry-run
SEASON ?=

.PHONY: install test lint format typecheck check doctor init-db seed-reference data-quality smoke smoke-live
.PHONY: predict-fixture predict-today publish-daily-discord daily-morning daily-late refresh-all-leagues backfill-season train train-backtest-all train-backtest-ou backtest
.PHONY: docker-build docker-doctor docker-init-db docker-seed-reference docker-data-quality
.PHONY: docker-predict-today-dry-run docker-shell compose-doctor compose-run compose-down

install:
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) scripts/repair_editable_install.py

test:
	$(PYTHON) -m pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src

check: lint typecheck test

doctor:
	$(CLI) doctor --strict

init-db:
	$(CLI) init-db

seed-reference:
	$(CLI) seed-reference-from-docs \
		--reference docs/api_football_reference.json \
		--players docs/api_football_players_reference.json

data-quality:
	$(CLI) data-quality

smoke:
	scripts/smoke_test_local.sh

smoke-live:
	scripts/smoke_test_live.sh

predict-fixture:
	test -n "$(FIXTURE_ID)"
	$(CLI) predict --fixture "$(FIXTURE_ID)" --model-dir "$(MODEL_DIR)" --no-refresh

predict-today:
	scripts/run_predict_today.sh

publish-daily-discord:
	scripts/publish_daily_discord.sh

daily-morning:
	scripts/daily_morning.sh

daily-late:
	scripts/daily_late.sh

refresh-all-leagues:
	scripts/refresh_all_leagues.sh

backfill-season:
	test -n "$(SEASON)"
	SEASON="$(SEASON)" scripts/backfill_season.sh

train:
	$(CLI) train --dataset "$(DATASET)" --output-dir "$(MODEL_DIR)" --model-version "$(MODEL_VERSION)"

train-backtest-all:
	scripts/train_backtest_all.sh

train-backtest-ou:
	scripts/train_backtest_ou.sh

backtest:
	$(CLI) backtest --dataset "$(DATASET)" --model-dir "$(MODEL_DIR)" --output-dir "$(BACKTEST_DIR)" --retrain-v2-model-version "$(MODEL_VERSION)" --format both

docker-build:
	$(DOCKER) build -t $(DOCKER_IMAGE) .

docker-doctor:
	$(DOCKER) run --rm --env-file .env \
		-v "$(CURDIR)/data:/app/data" \
		-v "$(CURDIR)/docs:/app/docs:ro" \
		-v "$(CURDIR)/config:/app/config:ro" \
		$(DOCKER_IMAGE) doctor --strict

docker-init-db:
	$(DOCKER) run --rm --env-file .env \
		-v "$(CURDIR)/data:/app/data" \
		-v "$(CURDIR)/docs:/app/docs:ro" \
		-v "$(CURDIR)/config:/app/config:ro" \
		$(DOCKER_IMAGE) init-db

docker-seed-reference:
	$(DOCKER) run --rm --env-file .env \
		-v "$(CURDIR)/data:/app/data" \
		-v "$(CURDIR)/docs:/app/docs:ro" \
		-v "$(CURDIR)/config:/app/config:ro" \
		$(DOCKER_IMAGE) seed-reference-from-docs \
		--reference docs/api_football_reference.json \
		--players docs/api_football_players_reference.json

docker-data-quality:
	$(DOCKER) run --rm --env-file .env \
		-v "$(CURDIR)/data:/app/data" \
		-v "$(CURDIR)/docs:/app/docs:ro" \
		-v "$(CURDIR)/config:/app/config:ro" \
		$(DOCKER_IMAGE) data-quality

docker-predict-today-dry-run:
	$(DOCKER) run --rm --env-file .env \
		-v "$(CURDIR)/data:/app/data" \
		-v "$(CURDIR)/docs:/app/docs:ro" \
		-v "$(CURDIR)/config:/app/config:ro" \
		$(DOCKER_IMAGE) predict-today $(PREDICT_TODAY_ARGS)

docker-shell:
	$(DOCKER) run --rm -it --env-file .env \
		-v "$(CURDIR)/data:/app/data" \
		-v "$(CURDIR)/docs:/app/docs:ro" \
		-v "$(CURDIR)/config:/app/config:ro" \
		$(DOCKER_IMAGE) sh

compose-doctor:
	$(COMPOSE) run --rm app doctor --strict

compose-run:
	$(COMPOSE) run --rm app $(ARGS)

compose-down:
	$(COMPOSE) down
