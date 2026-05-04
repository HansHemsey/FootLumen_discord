# User Guide

Ce guide decrit l'utilisation quotidienne de Football Predictor en local, avec ou sans Docker.
Les commandes ne font pas d'appel API-Football sauf lorsqu'une option `--refresh-*` ou `--live`
est explicitement utilisee.

## Objectif

Football Predictor aide a construire une prediction 1X2 d'un match :

- victoire domicile ;
- match nul ;
- victoire exterieur.

La sortie reste probabiliste : probabilites, resultat predit, confiance, explications et qualite
des donnees. Une prediction n'est jamais une certitude.

## Prerequis

- Python 3.11+.
- Les cinq fichiers de reference sous `docs/`.
- Un fichier `.env` local cree depuis `.env.example`.
- Optionnel : une cle `API_FOOTBALL_KEY` pour les refresh live.
- Optionnel : une configuration Discord locale pour l'envoi webhook.

Les valeurs sensibles restent vides dans `.env.example` et ne doivent jamais etre commitees.

## Role De `AGENTS.md` Et `blueprint.md`

- `AGENTS.md` fixe les regles de travail : secrets, tests, IDs, data leakage, documentation.
- `blueprint.md` donne le contexte metier central : sources de verite, architecture, features,
  odds, modele, prediction et Discord.

Lis ces deux fichiers avant toute modification ou exploitation avancee.

## Configuration `.env`

Demarrage minimal :

```bash
cp .env.example .env
```

Variables principales :

```env
API_FOOTBALL_KEY=
DATABASE_URL=sqlite:///./data/football_predictor.db
APP_TIMEZONE=Europe/Paris
COMPETITIONS_CONFIG_PATH=config/competitions.example.yaml
API_FOOTBALL_REFERENCE_PATH=docs/api_football_reference.json
API_FOOTBALL_PLAYERS_REFERENCE_PATH=docs/api_football_players_reference.json
API_FOOTBALL_PLAYERS_CACHE_PATH=docs/api_football_players_cache.json
DISCORD_WEBHOOK_URL=
DISCORD_WEBHOOKS_CONFIG_PATH=config/discord_webhooks.local.yaml
DISCORD_CHANNELS_CONFIG_PATH=config/discord_channels.yaml
```

Les secrets restent vides dans `.env.example`.

## Role Des Fichiers `docs/`

Les referentiels locaux evitent de consommer le quota API et d'inventer des IDs.

- `docs/api_football_reference.md` : lecture humaine des competitions, equipes, venues,
  fixtures, bookmakers et bets.
- `docs/api_football_reference.json` : source structuree pour le code, les validations et le
  seed DB des competitions, equipes, venues, fixtures, standings, bookmakers et bets.
- `docs/api_football_players_reference.md` : lecture humaine des joueurs et effectifs.
- `docs/api_football_players_reference.json` : source structuree principale pour les joueurs,
  postes, numeros et liens equipe/saison.
- `docs/api_football_players_cache.json` : cache technique de collecte `/players/squads`.
  Il n'est pas la source metier principale.

Les donnees dynamiques de prediction viennent de la base locale et des snapshots dates :
fixtures recentes/futures, standings, odds, blessures, lineups, stats joueurs et predictions API.

## Installation Locale

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Verifie ensuite la configuration locale :

```bash
football-predictor doctor --strict
```

## Config Competitions

La configuration des ligues suivies se trouve dans `config/competitions.example.yaml` ou dans un
fichier local equivalent. Les `league_id` doivent etre verifies avec
`docs/api_football_reference.json`.

Exemple d'utilisation :

```bash
football-predictor ingest-reference --config config/competitions.example.yaml --prefer-docs --dry-run
```

## Initialisation Sans Quota API

Le seed local lit uniquement les JSON sous `docs/`.

```bash
football-predictor init-db
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json
football-predictor data-quality
```

Ce flux est le demarrage recommande avant tout refresh live.

## Ingestion

Seed local sans reseau :

```bash
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json
```

Refresh live explicite :

```bash
football-predictor ingest-fixtures --league 39 --season 2025 --refresh-api --save-raw
football-predictor ingest-standings --league 39 --season 2025 --refresh-api
football-predictor ingest-fixture-details --fixture <fixture_id> --refresh-api --save-raw
football-predictor ingest-odds --fixture <fixture_id> --refresh-api --save-raw
```

`league_id=39` est verifie dans le referentiel local. Remplace-le seulement par un ID present dans
`docs/api_football_reference.json`.

## Entrainement Et Backtest

Construire un dataset historique :

```bash
football-predictor build-dataset \
  --league 39 \
  --season 2025 \
  --prediction-window 24h \
  --output data/processed/training.parquet
```

Entrainer :

```bash
football-predictor train \
  --dataset data/processed/training.parquet \
  --output-dir data/models/v1 \
  --model-version v1
```

Evaluer :

```bash
football-predictor backtest \
  --dataset data/processed/training.parquet \
  --model-dir data/models/v1 \
  --output-dir reports/backtest_v1 \
  --format both
```

## Prediction Fixture

La fixture doit exister dans la base locale ou dans le referentiel local. Ne devine jamais un
`fixture_id`; cherche-le dans `docs/api_football_reference.json` ou dans la DB initialisee.

```bash
football-predictor predict --fixture <fixture_id> --no-refresh
```

Avec refresh explicite :

```bash
football-predictor predict --fixture <fixture_id> --refresh-data --save-raw
```

Si aucun modele entraine n'est disponible, le pipeline utilise les fallbacks odds, API prediction,
Poisson et prior conservateur selon les donnees disponibles.

## Predictions Du Jour

Les fenetres disponibles sont :

- `early` : prediction simulee 24h avant kickoff ;
- `mid` : prediction simulee 6h avant kickoff ;
- `late` : prediction simulee 40 min avant kickoff ;
- `now` : prediction a l'heure courante.

Sans appel API :

```bash
football-predictor predict-today \
  --date YYYY-MM-DD \
  --window now \
  --league 39 \
  --season 2025 \
  --no-refresh-data \
  --dry-run
```

`league_id=39` est la Premier League 2025 dans le referentiel local. Pour une autre competition,
verifie d'abord `docs/api_football_reference.json`.

Avec refresh live explicite :

```bash
football-predictor predict-today \
  --date YYYY-MM-DD \
  --window late \
  --league 39 \
  --season 2025 \
  --refresh-data \
  --save-raw \
  --dry-run
```

## Discord

Le format Discord est en francais, dans un bloc markdown, et reste probabiliste. Les vraies URLs
webhook restent dans `.env` ou `config/discord_webhooks.local.yaml`.

Verifier la configuration :

```bash
football-predictor discord-check-config
```

Predire puis preparer l'envoi sans envoyer :

```bash
football-predictor predict-and-send \
  --fixture <fixture_id> \
  --no-refresh \
  --dry-run \
  --print-only
```

L'envoi reel doit etre volontaire, avec une route webhook configuree localement.

## Makefile Et Docker

Commandes locales utiles :

```bash
make install
make doctor
make init-db
make seed-reference
make data-quality
make smoke
make predict-fixture FIXTURE_ID=<fixture_id>
make predict-today
make check
```

Docker :

```bash
make docker-build
make docker-doctor
make docker-seed-reference
make docker-predict-today-dry-run
```

`docker-compose.yml` monte `./data` en ecriture et `./docs` en lecture seule. L'image ne contient
pas `.env`, `data/`, `config/*.local.yaml` ni secrets.

## Smoke Test End-To-End Local

Le smoke test par defaut ne contacte ni API-Football ni Discord :

```bash
scripts/smoke_test_local.sh
```

Il cree une DB SQLite dans `data/smoke/`, verifie les references, initialise les tables, seed les
references, lance `doctor --strict`, `data-quality`, puis `predict-today --no-refresh-data --dry-run`.

Prediction fixture optionnelle :

```bash
SMOKE_FIXTURE_ID=<fixture_id> scripts/smoke_test_local.sh
```

Mode live explicite :

```bash
API_FOOTBALL_KEY=<local_secret> scripts/smoke_test_live.sh --date YYYY-MM-DD --league 39 --season 2025
```

Le mode live exige une cle API locale et garde Discord en dry-run sauf option explicite.

## Limites Connues

- La qualite depend de la couverture locale : odds, lineups, blessures et stats joueurs peuvent
  manquer selon competition et timing.
- SQLite est le mode local V1 ; PostgreSQL reste une cible de compatibilite.
- Le smoke local valide le pipeline CLI/DB, pas la presence de fixtures live du jour.
- Les predictions sont probabilistes, jamais des certitudes.
- Le cache joueurs est technique et ne remplace pas `api_football_players_reference.json`.
