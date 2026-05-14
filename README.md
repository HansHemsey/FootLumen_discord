# Football Predictor

Football Predictor est un outil Python de prédiction de matchs de football basé sur
API-Football v3.

L'objectif produit est de prédire le résultat 1X2 d'un match :

- `HOME` : victoire de l'équipe à domicile ;
- `DRAW` : match nul ;
- `AWAY` : victoire de l'équipe extérieure.

La sortie attendue est probabiliste : `P(Home)`, `P(Draw)`, `P(Away)`, résultat prédit,
score de confiance, explications principales et qualité des données.

> Une prédiction est probabiliste. Elle n'est jamais une garantie de résultat.

## Documents De Contexte

Avant tout développement, lire :

- `AGENTS.md` : règles de travail, sécurité, tests, data leakage, sources de vérité ;
- `blueprint.md` : contexte métier central et orientations du projet ;
- les fichiers `docs/` pertinents, surtout les référentiels API-Football.

Règle non négociable : aucun `league_id`, `team_id`, `fixture_id`, `player_id`,
`venue_id`, `bookmaker_id` ou `bet_id` ne doit être inventé. Les IDs doivent venir des
fichiers `docs/*.json` ou de la base locale initialisée depuis ces fichiers.

## Installation Et Bootstrap Sprint 1

Le Sprint 1 fournit une base Python installable avec Python 3.11+, `pyproject.toml`,
un layout `src/`, `typer`, `pydantic-settings`, `pytest`, `ruff` et `mypy`.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Les commandes CLI bootstrap sont :

```bash
football-predictor version
football-predictor healthcheck
football-predictor doctor
```

`healthcheck` affiche la version, les chemins configurés et l'état des secrets sous forme
masquée. `doctor` est conservée comme alias.

Les secrets resteront dans `.env` local ou dans l'environnement d'exécution :

```env
API_FOOTBALL_KEY=
DISCORD_WEBHOOK_URL=
API_FOOTBALL_TIMEOUT_SECONDS=20
API_FOOTBALL_MAX_RETRIES=2
API_FOOTBALL_RAW_SNAPSHOT_DIR=data/raw/api_football
COMPETITIONS_CONFIG_PATH=config/competitions.example.yaml
```

Les valeurs sensibles ne doivent jamais être committées, affichées ou loggées en clair.

## Exécution Locale, Makefile Et Docker

Pour travailler dans VSCode avec Codex, garder le flux local simple :

```bash
make install
scripts/init_local.sh
make doctor
make init-db
make seed-reference
make data-quality
make smoke
make check
```

`make check` exécute `ruff check .`, `mypy src` et `pytest`. Les commandes `doctor` et
`data-quality` ne font aucun appel réseau.

Le Makefile expose aussi les commandes quotidiennes principales :

```bash
make format
make predict-fixture FIXTURE_ID=<fixture_id>
make predict-today
make daily-morning
make daily-late
make publish-daily-discord
make refresh-all-leagues
make backfill-season SEASON=2024
make train-backtest-all
make train-backtest-ou
make train DATASET=data/processed/training_v2_late.parquet MODEL_DIR=data/models/v2-late
make backtest DATASET=data/processed/training_v2_late.parquet MODEL_DIR=data/models/v2-late
```

`scripts/init_local.sh` crée les dossiers `data/`, vérifie `.env`, vérifie les cinq
fichiers référentiels `docs/`, initialise la DB puis lance `doctor --strict`.
`scripts/run_predict_today.sh` lance `predict-today` avec variables optionnelles :
`DATE`, `WINDOW`, `LEAGUE_ID`, `SEASON`, `MODEL_DIR`, `CONFIG`, `LIMIT`,
`REFRESH_DATA`, `SEND_DISCORD`, `DRY_RUN`, `PRINT_ONLY` et `FORCE`.
Les scripts d'automatisation quotidiens utilisent `scripts/football_predictor_cli.sh`
quand il est disponible. Ce wrapper force l'import depuis `src/` et évite d'utiliser une
ancienne copie installée dans `.venv/site-packages`.

```bash
# Matin : diagnostics, seed idempotent, refresh du jour et publications operationnelles.
make daily-morning

# Publier seulement classement, calendrier et matchs du jour, dry-run par defaut.
make publish-daily-discord

# Avant match : fenetre late, lineups si disponibles, Discord en dry-run par defaut.
make daily-late

# O/U 2.5 M-30, Discord en dry-run par defaut.
scripts/daily_ou.sh

# Lundi : préparation des fixtures des 7 prochains jours.
scripts/weekly_ingestion.sh

# Backfill manuel plus lourd sur toutes les competitions enabled.
make refresh-all-leagues

# Dataset multi-ligues, entrainement et backtest.
make train-backtest-all

# Dataset multi-ligues, entrainement et backtest O/U 2.5.
make train-backtest-ou
```

`config/competitions.yaml` reste la config de production quotidienne : elle contient les
ligues et saisons courantes que les scripts du matin et d'avant-match rafraichissent.
`config/competitions_history.yaml` est la config d'entrainement/backtest : elle contient
les cinq championnats suivis sur les saisons `2022`, `2023`, `2024` et `2025`. Les scripts
`train_backtest_all.sh` et `train_backtest_ou.sh` l'utilisent par defaut si elle existe.
Ainsi, les fixtures hebdomadaires ingerees via la config production enrichissent la DB une
seule fois, puis deviennent automatiquement exploitables par les modeles car la saison
courante est aussi incluse dans la config historique.

Convention d'exploitation : `scripts/weekly_ingestion.sh` prépare les fixtures futures en
`J+7` (date locale d'exécution incluse plus 6 jours). `DETAILS_DAYS_BACK=7` dans
`refresh_all_leagues.sh` reste réservé aux détails récents de matchs terminés en `J-7`.

Par defaut `SEND_DISCORD=false` et `DRY_RUN=true`. Un envoi Discord reel demande donc
explicitement `SEND_DISCORD=true DRY_RUN=false`. Les publications quotidiennes alimentent
les channels `classement`, `calendrier` et `matchs_du_jour` avec des blocs de code
Markdown decoupes automatiquement sous 2000 caracteres.

`refresh-all-leagues` reste volontairement prudent : il rafraichit fixtures, standings et
odds, mais ne backfill pas les details de match par defaut pour eviter les erreurs API
`429`. Pour enrichir progressivement les statistiques historiques :

```bash
REFRESH_DETAILS=true DETAILS_LIMIT=5 DETAILS_DELAY_SECONDS=2 scripts/refresh_all_leagues.sh
```

Pour une collecte hebdomadaire des matchs termines de la semaine ecoulee :

```bash
REFRESH_DETAILS=true \
DETAILS_ONLY="statistics events players" \
DETAILS_DAYS_BACK=7 \
DETAILS_STATUSES="FT AET PEN" \
DETAILS_LIMIT=100 \
DETAILS_DELAY_SECONDS=3 \
DETAILS_SKIP_IF_COMPLETE=true \
scripts/refresh_all_leagues.sh
```

`DETAILS_STATUSES` est transforme en statuts separes, et `DETAILS_LIMIT` reste un garde-fou
par competition. Si un `429` apparait, le batch details s'arrete au premier rate-limit au
lieu de continuer a consommer des appels.
`DETAILS_SKIP_IF_COMPLETE=true` est actif par defaut dans le script : les endpoints deja
presents en DB, ou deja connus comme sans contenu, sont ignores pour economiser le quota API.
Les joueurs live absents de `docs/api_football_players_reference.json` sont ajoutes dans
`data/processed/unknown_players.jsonl` sans bloquer l'ingestion. Pour les enrichir ensuite
dans la DB locale, active la resolution batch :

```bash
RESOLVE_UNKNOWN_PLAYERS=true UNKNOWN_PLAYERS_LIMIT=50 UNKNOWN_PLAYERS_DELAY_SECONDS=2 \
  scripts/refresh_all_leagues.sh
```

La resolution appelle explicitement API-Football, upsert `Player` / `PlayerSquad`, et ne
modifie jamais les fichiers referentiels `docs/`.

Pour backfiller une saison entiere sur toutes les ligues activees, utilise le script dedie.
Il part de `config/competitions_history.yaml` quand ce fichier existe, filtre la saison
demandee, puis genere une config temporaire sous `data/processed/backfill/` avec la bonne
`season` API-Football pour chaque ligue. Il rafraichit les equipes de cette saison pour
gerer montees/descentes, puis ingere fixtures et details :

```bash
SEASON=2024 scripts/backfill_season.sh
```

Par defaut, `SEASON=2024` couvre `2024-08-01` a `2025-07-31`, avec
`DETAILS_LIMIT=400` par ligue, `DETAILS_DELAY_SECONDS=3`,
`DETAILS_STATUSES="FT AET PEN"` et `DETAILS_SKIP_IF_COMPLETE=true`. Les odds historiques
sont desactivees par defaut, car un snapshot recupere aujourd'hui ne doit pas etre utilise
comme odds point-in-time d'un ancien match.
Les competitions de coupe/globales comme la CDM sont desactivees par defaut dans ce
backfill de championnats; utilise `BACKFILL_INCLUDE_CUPS=true` seulement pour un cas dedie.
Ne copie pas ces lignes historiques dans `config/competitions.yaml` : la config production
reste centree sur la saison courante, tandis que training/backtest lit l'historique.

Le packaging Docker exécute uniquement la CLI, sans serveur web :

```bash
make docker-build
make docker-doctor
make docker-init-db
make docker-seed-reference
make docker-data-quality
```

Le `Dockerfile` copie le package, Alembic, les fichiers `config/*.example.yaml` et les cinq
référentiels `docs/` nécessaires au fonctionnement local. Il ne copie jamais `.env`,
`data/`, `config/*.local.yaml`, `*.secrets.yaml`, `.venv` ni les caches.

`docker-compose.yml` utilise `.env` au runtime et monte :

```text
./data   -> /app/data       écriture, DB SQLite, raw snapshots, modèles
./docs   -> /app/docs:ro    lecture seule, référentiels API-Football
./config -> /app/config:ro  lecture seule, configs locales et examples
```

Les vraies clés API, URLs webhook et tokens restent dans `.env` ou dans
`config/discord_webhooks.local.yaml`, jamais dans l'image. Le montage `docs:ro` permet de
mettre à jour les référentiels locaux sans reconstruire l'image ; l'image garde aussi une
copie des mêmes référentiels pour les diagnostics autonomes.

La crontab prod autonome est prête dans `config/prod.crontab` :

```bash
scripts/install_prod_cron.sh
crontab -l
```

Elle publie réellement dans Discord avec `SEND_DISCORD=true DRY_RUN=false`, utilise les
scripts prod, verrouille chaque routine avec `lockf` et écrit les logs dans `logs/cron/`.

Résumé des crons installés :

```cron
15 5 * * 1        weekly_ingestion.sh
30 6 * * *        daily_morning.sh
*/15 6-23 * * *   publish_match_analyses.sh
1,11,21,31,41,51 7-23 * * * daily_late.sh
3,13,23,33,43,53 7-23 * * * daily_ou.sh
20,50 12-23 * * * publish_match_results.sh
10 8,12,18 * * *  publish_weekly_score.sh
55 23 * * *       publish_weekly_score.sh
```

Pour une exécution Docker personnalisée :

```bash
make docker-predict-today-dry-run \
  PREDICT_TODAY_ARGS="--date YYYY-MM-DD --window late --no-refresh-data --dry-run"

make compose-run ARGS="doctor --strict"
make compose-run ARGS="predict-today --date YYYY-MM-DD --window now --no-refresh-data --dry-run"
```

Ne pas supprimer, ignorer ou déplacer les cinq fichiers référentiels :

```text
docs/api_football_reference.md
docs/api_football_reference.json
docs/api_football_players_reference.md
docs/api_football_players_reference.json
docs/api_football_players_cache.json
```

## Documentation Finale Et Smoke End-To-End

Les guides finaux sont :

- `docs/user_guide.md` : installation, `.env`, seed local, prediction fixture, predictions du
  jour, Discord, Docker et Makefile.
- `docs/developer_guide.md` : workflow VSCode/Codex, tests, conventions, anti data leakage et
  usage des references locales.
- `docs/operations_guide.md` : cron, Docker, diagnostics, refresh live, quotas, sauvegardes et
  runbooks.
- `docs/codex_workflow.md` : Plan mode, Agent/Edit automatically, prompts types et checklist
  avant commit.

## Quickstart End-To-End

Flux recommande sans consommer de quota API :

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
football-predictor init-db
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json
football-predictor doctor --strict
football-predictor data-quality
scripts/smoke_test_local.sh
```

Puis, avec une fixture verifiee dans `docs/api_football_reference.json` ou en DB :

```bash
football-predictor predict --fixture <fixture_id> --no-refresh
football-predictor predict-and-send --fixture <fixture_id> --no-refresh --dry-run --print-only
```

Scenario local de bout en bout, sans appel API-Football ni Discord :

```bash
make smoke
# equivalent direct :
scripts/smoke_test_local.sh
```

Ce smoke test utilise une DB SQLite dediee dans `data/smoke/`, verifie les cinq fichiers
referentiels, initialise les tables, seed les references depuis `docs/`, lance `doctor --strict`,
`data-quality`, puis `predict-today --no-refresh-data --dry-run --json`.

Mode live explicite :

```bash
API_FOOTBALL_KEY=<secret_local> make smoke-live
# ou :
API_FOOTBALL_KEY=<secret_local> scripts/smoke_test_live.sh --date YYYY-MM-DD --league 39 --season 2025
```

Le mode live exige une cle API locale, active `--refresh-data` et garde Discord en dry-run sauf
option explicite via les variables du script. Aucune commande smoke executee par les tests ne fait
d'appel reseau.

Variables utiles du smoke :

```text
SMOKE_DATE=YYYY-MM-DD
SMOKE_WINDOW=now|early|mid|late
SMOKE_LEAGUE_ID=<league_id verifie dans docs/api_football_reference.json>
SMOKE_SEASON=2025
SMOKE_FIXTURE_ID=<fixture_id verifie>
SMOKE_LIMIT=5
SMOKE_LIVE=false
SMOKE_SEND_DISCORD=false
SEND_DISCORD=false
```

Limites connues :

- le smoke local valide le pipeline CLI/DB, mais ne garantit pas qu'une fixture du jour soit deja
  presente en DB ;
- les donnees optionnelles peuvent manquer selon la couverture API : odds, blessures, lineups,
  player stats et predictions API ;
- `docs/api_football_players_cache.json` reste un cache technique, pas la source principale joueurs ;
- une prediction est probabiliste et doit toujours etre lue avec son score de qualite des donnees.

## Sprints Complétés

- Sprint 1 : bootstrap Python, CLI minimale, settings, structure `src/`.
- Sprint 2 : client API-Football, retries, pagination, snapshots bruts.
- Sprint 3 : DB SQLAlchemy, repositories, Alembic, seed idempotent.
- Sprint 4 : ingestion referentiels et config competitions.
- Sprint 5 : ingestion fixtures et standings.
- Sprint 6 : ingestion details match, injuries et predictions API.
- Sprint 7 : ingestion odds et probabilites marche.
- Sprint 8 : features equipe point-in-time.
- Sprint 9 : features joueurs, XI probable et absences.
- Sprint 10 : feature builder global et dataset historique.
- Sprint 11 : modeles de prediction, baselines, stacking, artefacts.
- Sprint 12 : backtesting, metriques et rapports.
- Sprint 13 : pipeline `predict_fixture`.
- Sprint 14 : formatter Discord markdown.
- Sprint 15 : routage Discord multi-webhooks.
- Sprint 16 : automatisation des predictions du jour.
- Sprint 17 : diagnostics, data-quality et robustesse.
- Sprint 18 : packaging Docker, compose, Makefile.
- Sprint 19 : documentation finale et smoke tests local/live.

## Commandes Prévues

Les commandes CLI prévues sont :

```bash
football-predictor doctor
football-predictor doctor --strict
football-predictor doctor --json
football-predictor data-quality --league 39 --season 2025
football-predictor data-quality --fixture <fixture_id> --json
football-predictor data-quality --week-of YYYY-MM-DD --model-family v3 --markdown-output reports/data_quality_week.md
football-predictor version
football-predictor healthcheck
football-predictor init-db
alembic upgrade head
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json \
  --dry-run
football-predictor ingest-reference \
  --config config/competitions.example.yaml \
  --prefer-docs \
  --dry-run
football-predictor ingest-reference \
  --config config/competitions.example.yaml \
  --prefer-docs \
  --refresh-live \
  --save-raw
football-predictor ingest-leagues --config config/competitions.example.yaml --refresh-api
football-predictor ingest-teams --config config/competitions.example.yaml --refresh-api
football-predictor ingest-player-squads --config config/competitions.example.yaml --refresh-api
football-predictor ingest-bookmakers --refresh-api
football-predictor ingest-bets --refresh-api
football-predictor ingest-fixtures --league 39 --season 2025
football-predictor ingest-fixtures --league 39 --season 2025 --refresh-api
football-predictor ingest-fixtures --date 2026-05-02
football-predictor ingest-fixtures --team-id <team_id> --last <n> --refresh-api
football-predictor ingest-fixtures --team-id <team_id> --next <n> --refresh-api
football-predictor ingest-standings --league 39 --season 2025
football-predictor ingest-fixture-details --fixture <fixture_id> --refresh-api
football-predictor ingest-fixture-details \
  --fixture <fixture_id> \
  --refresh-api \
  --only statistics \
  --only lineups
football-predictor ingest-fixture-details \
  --league 39 \
  --season 2025 \
  --status FT \
  --limit 10 \
  --refresh-api
football-predictor ingest-fixture-details \
  --league 39 \
  --season 2025 \
  --include-upcoming \
  --refresh-api \
  --save-raw
football-predictor ingest-odds --fixture <fixture_id> --refresh-api
football-predictor ingest-odds --date YYYY-MM-DD --refresh-api
football-predictor ingest-odds --league 39 --season 2025 --refresh-api
football-predictor ingest-odds \
  --fixture <fixture_id> \
  --bookmaker <bookmaker_id> \
  --refresh-api \
  --save-raw
football-predictor odds-features --fixture <fixture_id> --as-of YYYY-MM-DDTHH:MM:SS+00:00
football-predictor build-dataset \
  --league <league_id> \
  --season <season> \
  --prediction-window 30m \
  --output data/processed/training_v2_late.parquet \
  --format parquet
football-predictor train \
  --dataset data/processed/training_v2_late.parquet \
  --output-dir data/models/v2-late \
  --model-version v2-late \
  --calibration sigmoid
football-predictor backtest \
  --dataset data/processed/training_v2_late.parquet \
  --model-dir data/models/v2-late \
  --output-dir reports/backtest_v2_late \
  --retrain-v2-model-version v2-late \
  --format both
football-predictor predict \
  --fixture <fixture_id> \
  --model-dir data/models/v2-late \
  --no-refresh \
  --json-output reports/prediction.json
football-predictor predict-and-send \
  --fixture <fixture_id> \
  --model-dir data/models/v2-late \
  --competition-key ligue1 \
  --channel predictions \
  --dry-run
football-predictor discord-check-config
football-predictor discord-test-route --competition-key ligue1 --channel predictions
football-predictor discord-send --prediction-id <model_prediction_id> --dry-run
football-predictor discord-send-message \
  --competition ligue1 \
  --channel analyses \
  --message-type analysis \
  --content-file reports/message.md \
  --dry-run
football-predictor discord-provision-webhooks \
  --channels-config config/discord_channels.yaml \
  --output config/discord_webhooks.local.yaml \
  --dry-run
football-predictor predict-today \
  --date YYYY-MM-DD \
  --window late \
  --league 61 \
  --season 2025 \
  --no-refresh-data \
  --dry-run
football-predictor predict-today \
  --date 2026-05-02 \
  --league 39 \
  --send-discord \
  --refresh-data
football-predictor predict-today \
  --date YYYY-MM-DD \
  --window now \
  --config config/competitions.yaml \
  --refresh-data \
  --send-discord \
  --dry-run
football-predictor predict-today-v3 \
  --date YYYY-MM-DD \
  --window late \
  --model-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --production-mode \
  --no-refresh-data \
  --json
```

Les placeholders `<league_id>` et `<fixture_id>` doivent être remplacés uniquement par des
valeurs vérifiées dans les référentiels JSON ou dans la base locale.
L'exemple `league 39` correspond à la Premier League 2025 et existe dans
`docs/api_football_reference.json`; il reste à adapter selon les compétitions suivies.
`predict-today-v3` reste en shadow mode par défaut pour les appels manuels. Ajouter
`--production-mode` autorise le chemin production V3 ; un envoi Discord réel exige aussi
`--send-discord` et l'absence de `--dry-run` / `--print-only`. Utiliser
`--dry-run --print-only` pour vérifier le rendu Discord V3 sans publication.

Les commandes `ingest-fixtures --league/--season`, `ingest-fixtures --date` et
`ingest-standings --league/--season` utilisent les docs locaux par défaut. Les variantes
live refusent de faire un appel réseau sans option explicite (`--refresh-api` ou
`--refresh-live`).

`ingest-fixture-details` appelle uniquement l'API live après `--refresh-api`. La commande
accepte soit `--fixture <fixture_id>`, soit un lot filtré par `--league/--season`, `--date`
ou `--status`. Sans `--include-upcoming`, un lot sans `--status` se limite aux fixtures
terminées (`FT`). Elle enrichit des fixtures déjà présentes en DB avec
`fixtures/statistics`, `fixtures/events`, `fixtures/lineups`, `fixtures/players`,
`injuries` et `predictions`, puis crée un `RawApiSnapshot` pour chaque réponse. Les
lineups, stats joueurs, blessures et prédictions peuvent manquer selon la couverture :
l'ingestion le signale sans bloquer tout le batch.

`ingest-odds` appelle `/odds` uniquement après `--refresh-api`. La V1 ne stocke que les
odds prematch 1X2 résolues depuis le bet configurable `MARKET_1X2_BET_NAME=Match Winner`
ou `MARKET_1X2_BET_ID`. Les snapshots multiples sont conservés avec `fetched_at` pour le
mouvement de cotes et les futurs calculs point-in-time.

`odds-features` ne fait aucun appel réseau : la commande lit les snapshots `OddsSnapshot`
déjà présents en DB, prend le dernier snapshot par bookmaker avant `--as-of`, retire la
marge bookmaker, calcule le consensus 1X2, la dispersion et le mouvement des cotes.

`doctor` est le diagnostic local principal. Il ne fait aucun appel API-Football ni Discord :
il vérifie la version, Python, la DB, les chemins configurés, les trois JSON de référence,
leur validité, les compteurs des référentiels, la config compétitions, la config Discord et
l'état des secrets sous forme masquée. `doctor --json` sert à la CI ; `doctor --strict`
sort avec un code non zéro seulement sur erreur critique.

`data-quality` observe la couverture locale déjà stockée en DB, sans ingestion ni recalcul
de features. Le rapport peut être global, filtré par fixture, par date, ou par
`--week-of`, `--league/--season` et `--model-family all|v3|ou25`. Il résume fixtures
futures/terminées, odds, standings, injuries, lineups, stats joueurs, prédictions API,
derniers `fetched_at`, nombre de snapshots, fraîcheur par source et readiness de
publication basée sur `publication_data_quality_score`. Les sorties locales sont
disponibles via `--json-output` et `--markdown-output`.

## Base De Données

Le stockage local utilise SQLAlchemy 2.x. SQLite est le moteur par défaut pour le
développement local, avec un schéma conçu pour rester compatible PostgreSQL.

Pour les tests rapides ou un bootstrap local jetable :

```bash
football-predictor init-db
```

Pour une base durable, utiliser Alembic :

```bash
alembic upgrade head
```

Le schéma conserve les entités normalisées seedées depuis `docs/*.json` et les snapshots
dynamiques avec `fetched_at` pour les futurs calculs point-in-time. Les payloads bruts
utiles sont conservés en JSON pour audit.

Avant d'ingérer les détails d'une fixture, charger les fixtures de base avec
`ingest-fixtures` ou `seed-reference-from-docs`. Les tables détaillées référencent
`fixture_id`, et les futurs builders de features devront filtrer ces snapshots avec
`fetched_at <= prediction_time`.

## Vue D'Architecture

Flux cible :

```text
docs reference JSON
  -> seed DB local optionnel
  -> ingestion API live explicite
  -> snapshots bruts horodatés
  -> features point-in-time
  -> modèles et stacking
  -> prédiction fixture unique ou batch
  -> sortie CLI et Discord
```

Modules cibles sous `src/football_predictor/` :

- `reference/` : loaders et lookups des JSON locaux, sans appel réseau ;
- `config/` : settings, chemins, timezone, variables d'environnement ;
- `api/` : client API-Football centralisé et secret-safe ;
- `db/` : modèles SQLAlchemy, session, repositories, snapshots ;
- `ingestion/` : seed local et collecte API explicite ;
- `features/` : features équipes, joueurs, XI, absences, odds et qualité des données ;
- `modeling/` : baselines, modèle sportif, stacking, calibration ;
- `backtesting/` : datasets historiques point-in-time et métriques ;
- `prediction/` : pipeline de prédiction et explications ;
- `discord/` : format markdown français et webhook ;
- `utils/` : logging, dates, secrets, diagnostics.

Le moteur `features.team_features` construit les premières features sportives équipe sans
appel réseau. Il prend `fixture_id` et `prediction_time`, exclut toujours la fixture cible,
lit uniquement les fixtures terminées avant `prediction_time`, puis filtre les snapshots
dynamiques avec `fetched_at <= prediction_time`. Les sorties sont des dicts plats
sérialisables, prêts à être stockés dans `FeatureSnapshot`.

Le moteur `features.xi_features` ajoute les features joueurs, XI probable et absences. Il
utilise les lineups, stats joueurs et injuries déjà stockées en DB, toujours filtrées par
`prediction_time`, puis complète l'identité et le poste des joueurs avec
`docs/api_football_players_reference.json` quand la DB est incomplète. Il expose
`home_team_expected_xi_json`, `away_team_expected_xi_json`, les formations probables,
l'impact des absences, la stabilité du XI, la profondeur du banc et des flags de qualité.
Sprint 9 ne crée pas de commande CLI dédiée : cette API Python sera utilisée par les
pipelines dataset et prédiction.

Le builder global `features.feature_builder` fusionne les features équipe, joueurs/XI,
odds et prédiction API-Football dans un `FeatureSnapshot` `v1`. Il prend toujours
`fixture_id` et `prediction_time`, puis ignore les odds, injuries, lineups, stats joueurs,
standings et prédictions API postérieures au cutoff. Il expose aussi un score
`overall_data_quality_score` borné de 0 à 100.

La commande `build-dataset` et le module `backtesting.dataset_builder` construisent un
dataset historique point-in-time depuis la DB locale. Ils sélectionnent les fixtures
terminées avec score, simulent par défaut `prediction_time = fixture.date - 24h`,
calculent un snapshot global, puis ajoutent la cible `HOME/DRAW/AWAY` hors
`features_json`. La fenêtre `30m` est disponible pour entraîner un modèle aligné sur
`daily_late`. Les exports CSV et Parquet sont supportés.

Le module `modeling/` entraîne les modèles sportifs. La V1 scikit-learn reste disponible,
la V2 `late` M-30 reste le rollback et un signal de la V3, et la production Discord
`daily_late` utilise la V3 depuis Sprint 10. La V2 combine marché calibré, Poisson
amélioré, Elo dynamique, modèle tabulaire LightGBM optionnel/fallback sklearn, puis
stacking appris sur validation temporelle. La commande `train` exclut les colonnes de
fuite (`target`, scores finaux, IDs naïfs, dates, statuts post-match et JSON bruts), puis
écrit `model.joblib`, `metadata.json`, `feature_names.json`, `metrics.json` et, pour V2,
`feature_coverage.json` dans `data/models/<version>/`.

Workflow V2 recommandé :

```bash
football-predictor build-dataset \
  --league 39 \
  --season 2025 \
  --prediction-window 30m \
  --output data/processed/training_v2_late.parquet

football-predictor train \
  --dataset data/processed/training_v2_late.parquet \
  --output-dir data/models/v2-late \
  --model-version v2-late

football-predictor backtest \
  --dataset data/processed/training_v2_late.parquet \
  --model-dir data/models/v2-late \
  --output-dir reports/backtest_v2_late \
  --retrain-v2-model-version v2-late \
  --format both
```

`scripts/train_backtest_all.sh` utilise ce workflow V2 par défaut, avec
`config/competitions_history.yaml` si le fichier existe. Le modèle V2 late reste écrit
dans `data/models/v2-late` pour servir de signal V3 et de rollback
`PREDICTION_ENGINE=v2`.

Pour le modèle Over/Under 2.5, la commande dédiée utilise la même config historique et écrit
l'artefact dans `data/models/ou-v1` :

```bash
scripts/train_backtest_ou.sh
```

Les scripts de production quotidienne, eux, restent sur `config/competitions.yaml` par
défaut pour éviter de parcourir les anciennes saisons.

La commande `backtest` lit le même dataset historique, impose un split temporel sans
shuffle, évalue le modèle sauvegardé et les baselines `odds_only`, `poisson` et
`api_prediction_only`, puis exporte `backtest_report.json` et/ou `backtest_report.md`.
Le rapport inclut les périodes train/validation/test, accuracy, log loss, Brier,
calibration, seuils de confiance, performances par ligue/saison, buckets de confiance,
buckets de qualité des données et deltas face au modèle final. Les probabilités évaluées
doivent provenir de snapshots construits point-in-time.

La commande `predict` prédit une fixture unique depuis la DB locale par défaut
(`--no-refresh`). Elle construit un `FeatureSnapshot` point-in-time, charge le modèle depuis
`--model-dir` si disponible, puis combine les sources autorisées. Le rollback
`PREDICTION_ENGINE=v2` de `daily_late` utilise `data/models/v2-late` s'il existe, sinon
revient à `data/models/v1`, puis aux fallbacks. Avec V2, les probabilités par expert sont
persistées dans `ModelPrediction.payload_json.expert_probabilities`. Les appels API live ne
sont faits qu'avec `--refresh-data`, jamais implicitement.

Depuis Sprint 10, `scripts/daily_late.sh` publie les prédictions M-30 avec la V3 par
défaut (`MODEL_DIR=data/models/v3`, `V2_MODEL_DIR=data/models/v2-late`). La promotion est
volontaire malgré un backtest V3 non validé ; surveiller les premiers runs réels et la
couverture odds/API/lineups rafraîchie à M-30. Le rollback officiel est :

```bash
PREDICTION_ENGINE=v2 SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

La publication publique applique le même filtre pour V3 1X2 et O/U 2.5 : seuls les labels
`High` et `Very High` sont envoyés dans Discord avec un
`publication_data_quality_score >= PUBLICATION_MIN_DATA_QUALITY_SCORE`. Les prédictions
`Low`, `Medium`, `Uncertain`, les scores qualité insuffisants ou les
`publication_blockers` sont persistés pour suivi interne avec le statut
`confidence_skipped`.

La commande `predict-today` automatise les prédictions d'une date sans serveur web. Elle
peut être appelée par cron ou par une tâche planifiée. Les fenêtres filtrent les fixtures
futures du jour et déterminent le `prediction_time` simulé pour chaque fixture :

- `early` : kickoff dans plus de 6h, avec `prediction_time = fixture.date - 24h` ;
- `mid` : kickoff entre 60min et 6h, avec `prediction_time = fixture.date - 6h` ;
- `late` : kickoff entre maintenant et 30min, avec `prediction_time = maintenant` ;
- `now` : toutes les fixtures futures du jour, avec `prediction_time = maintenant` ;
- `all` : toutes les fixtures futures du jour, avec `prediction_time = maintenant`.

Les fixtures déjà commencées ou terminées sont ignorées par défaut. Sans
`--refresh-data`, la commande lit uniquement la DB locale et ne découvre aucune fixture via
l'API. Avec `--refresh-data`, elle exige `API_FOOTBALL_KEY`, ingère les fixtures par date
et compétition, puis laisse le pipeline fixture unique rafraîchir détails, odds, injuries,
prédictions API et standings. Les ligues explicites doivent être vérifiées dans
`docs/api_football_reference.json`; les exemples valides connus sont `61` Ligue 1 2025,
`39` Premier League 2025, `140` La Liga 2025, `78` Bundesliga 2025, `135` Serie A 2025 et
`1` World Cup 2026.

Pour un cron local, utiliser par exemple des commandes séparées :

```bash
# Routine matin : refresh live explicite sur les competitions enabled, sans prediction.
scripts/daily_morning.sh

# Update avant match : V3 par defaut, refresh explicite, Discord reel seulement si dry-run desactive.
SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

La déduplication Discord est faite par `fixture_id + window` pour les vrais messages
`predictions`. En V3, elle n'empêche pas de créer une nouvelle `V3ModelPrediction`, mais
évite un second envoi réel pour la même fenêtre. `--force` contourne cette protection ;
`--dry-run` et `--print-only` ne bloquent jamais un futur envoi réel.

Le formatter Discord produit un bloc `md` ferme, en français, limite à 2000 caractères. Il
inclut le match, la compétition, la date, les probabilités, la confiance, les facteurs clés,
les absences clés disponibles, la qualité des données et la note : prédiction probabiliste,
pas une certitude. Si les odds ou les absences sont absentes, le message l'indique au lieu
d'inventer ou de substituer des valeurs.

Le routage Discord V1 supporte plusieurs webhooks par compétition et par channel. Les
fichiers `config/discord_channels.example.yaml` et `config/discord_webhooks.example.yaml`
décrivent la structure attendue avec des valeurs fictives uniquement. Les vraies URLs
webhook doivent venir de variables d'environnement ou de
`config/discord_webhooks.local.yaml`, qui est ignoré par Git. `DISCORD_WEBHOOK_URL` reste
un fallback legacy limité aux prédictions, mais la cible est le routage par
`competition_key`, `league_id`, `season`, `channel_key` et `message_type`.

Les `channel_key` supportés sont `classement`, `calendrier`, `matchs_du_jour`,
`analyses`, `predictions`, `resultats`, `score_pronos_semaine` et `discussions`. Les `message_type` standards sont
résolus ainsi : `standings -> classement`, `schedule -> calendrier`,
`daily_matches -> matchs_du_jour`, `analysis -> analyses`, `prediction -> predictions`,
`result -> resultats` et `weekly_prediction_score -> score_pronos_semaine`.
Les messages automatiques vers `discussions` sont refusés par
défaut.

La commande `publish-daily-discord` alimente les channels operationnels depuis la DB
locale, sans appel API direct :

```bash
football-predictor publish-daily-discord --date YYYY-MM-DD --dry-run
SEND_DISCORD=true DRY_RUN=false scripts/publish_daily_discord.sh
```

Elle publie, pour chaque competition enabled, le dernier classement vers `classement`, la
prochaine journee/round vers `calendrier`, et les matchs de la date cible vers
`matchs_du_jour`. Chaque message est un bloc `md` aligne ; si un tableau depasse la limite
Discord, il est decoupe en plusieurs parties, chacune sous 2000 caracteres.

Par defaut, ces trois channels operationnels remplacent les anciens messages envoyes par
l'outil afin de ne garder que l'etat le plus recent :

```bash
REPLACE_PREVIOUS=true scripts/publish_daily_discord.sh
football-predictor publish-daily-discord --no-replace-previous
```

Les anciennes predictions ne sont jamais supprimees par ce mecanisme.

Le score hebdomadaire global se publie avec :

```bash
football-predictor publish-weekly-score --date YYYY-MM-DD --dry-run
SEND_DISCORD=true DRY_RUN=false scripts/publish_weekly_score.sh
```

Il compte uniquement les pronostics réellement publiés dans Discord et dont le match est
terminé : V2 legacy, V3 via `payload_json["v3_model_prediction_id"]`, et O/U 2.5 via
`payload_json["ou_model_prediction_id"]`. Les prédictions internes non publiées pour
confiance insuffisante, `dry_run` ou `print_only` ne sont pas affichées. Le bilan est
calculé sur la semaine ISO lundi-dimanche en Europe/Paris, puis remplace seulement le
message du même `week_key`. Le lundi matin, il met aussi à jour la semaine précédente
afin de capter les résultats du dimanche arrivés dans la nuit, puis crée le message de la
nouvelle semaine. Le webhook de ce channel doit être renseigné dans la config locale ou
en variable d'environnement, jamais dans le repo.

Deux publications par match gardent volontairement l'historique :

```bash
# Analyse unique H-6, envoyee dans la fenetre H-6 -> H-5h45.
football-predictor publish-match-analyses --date YYYY-MM-DD --dry-run
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh

# Bilan apres match termine FT/AET/PEN.
football-predictor publish-match-results --date YYYY-MM-DD --dry-run
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
```

`publish-match-analyses` publie dans `analyses` un bloc `md` unique par fixture : contexte,
forme recente, classement, odds/mouvement, absences ou XI si disponibles, points
forts/faibles, fiabilite des donnees et conclusion prudente. La prediction est construite
avec `prediction_time = fixture.date - 6h` pour rester point-in-time. La marge d'envoi est
configurable avec `ANALYSIS_GRACE_MINUTES`, 15 minutes par defaut. Une analyse sans
signaux suffisants est ignorée avec `insufficient_analysis_data`.

`publish-match-results` publie dans `resultats` uniquement quand la DB contient un statut
termine et un score final. Le message compare le score et le resultat 1X2 avec la derniere
prediction pre-match envoyee sur Discord. Les prédictions internes jamais publiées ne sont
pas affichées après match. Avec `REFRESH_DATA=true`, le script rafraichit les fixtures du
jour pour capter les scores finaux. Les deux commandes verrouillent un seul envoi reel par
fixture ; `--force` renvoie volontairement.

Tous les envois Discord utilisent `allowed_mentions={"parse":[]}` pour éviter les
mentions non voulues. Les commandes `--dry-run` et `--print-only` ne font aucun appel
Discord et persistent quand même une trace `DiscordMessage` avec hash du webhook et hash
du message si disponibles. Le provisioning via API Discord est optionnel, nécessite
`DISCORD_BOT_TOKEN` et des `channel_id`, puis écrit les URLs générées uniquement dans
`config/discord_webhooks.local.yaml` avec `--yes`. Les logs et sorties CLI affichent des
hashes courts, jamais les URLs complètes.

Pour configurer manuellement Discord :

1. Copier `config/discord_channels.example.yaml` vers `config/discord_channels.yaml`.
2. Remplacer les `channel_id` par les IDs de channels du serveur Discord local.
3. Créer les webhooks dans chaque channel Discord.
4. Créer `config/discord_webhooks.local.yaml` avec les URLs réelles ou utiliser des
   variables d'environnement référencées par `webhook_url_env`.
5. Vérifier avec `football-predictor discord-check-config`.

Si un webhook est compromis, le révoquer dans Discord, remplacer la valeur locale et ne
jamais committer le fichier local.

## Qualité Et Diagnostics

Commandes de vérification attendues :

```bash
pytest
ruff check .
mypy src
football-predictor doctor --strict
football-predictor data-quality --json
```

Le projet fournit aussi une configuration pre-commit locale :

```bash
pre-commit install
pre-commit run --all-files
```

Les hooks sont volontairement non destructifs : `ruff check`, `ruff format --check`,
`mypy src` et un sous-ensemble de tests smoke. Ils ne font aucun appel réseau.

### Troubleshooting Local

Avant un lancement quotidien, exécuter :

```bash
scripts/football_predictor_cli.sh doctor --strict
scripts/football_predictor_cli.sh data-quality --date YYYY-MM-DD
```

`doctor` doit confirmer que les settings sont chargés, que la DB est accessible, que les
tables attendues existent, que `data/models` est présent ou signalé, que la config
compétitions est lisible et que les secrets sont seulement indiqués comme présents/absents
avec un hash court. Une clé API, un webhook Discord ou un bot token ne doivent jamais
apparaître en clair.

Le diagnostic vérifie aussi explicitement les références locales :

- `docs/api_football_reference.md` existe ;
- `docs/api_football_reference.json` existe et est un JSON métier valide ;
- `docs/api_football_players_reference.md` existe ;
- `docs/api_football_players_reference.json` existe et est un JSON métier valide ;
- `docs/api_football_players_cache.json` existe et est un JSON technique valide.

Le cache joueurs est seulement un cache de reprise de collecte. Il ne remplace pas
`docs/api_football_players_reference.json` comme source métier.

Si `football-predictor doctor --strict` affiche `Unknown competition key='global'` alors
que `scripts/football_predictor_cli.sh doctor --strict` passe, l'entrypoint installé est
obsolète. Réinstaller le paquet local avec `make install` ou continuer à utiliser le
wrapper `scripts/football_predictor_cli.sh`. Sur Python 3.13, `make install` ajoute aussi
un fichier `.pth` non caché pour que `.venv/bin/football-predictor` importe bien le
dossier `src/`. Dans la configuration Discord, `global` est réservé aux routes non liées
à une compétition, par exemple `score_pronos_semaine`; les compétitions API-Football
restent sous `competitions`.

Checklist avant automatisation :

- DB initialisée et alimentée pour les fixtures du jour.
- `doctor --strict` sans erreur critique.
- `data-quality` montre historique home/away, odds, standings, blessures, lineups, stats
  joueurs et prédiction API selon la fenêtre visée.
- `--no-refresh-data` utilisé si aucun appel API ne doit partir.
- `--dry-run` utilisé pour valider Discord sans envoyer.
- Les fichiers `config/discord_webhooks.local.yaml` et `.env` restent non versionnés.

## Référentiels Locaux

Le dossier `docs/` contient les sources locales déjà générées :

- `docs/api_football_reference.md` : lecture humaine des compétitions, équipes, fixtures,
  venues, bookmakers et bets ;
- `docs/api_football_reference.json` : source machine pour les IDs de compétitions,
  équipes, fixtures, venues, bookmakers et bets ;
- `docs/api_football_players_reference.md` : lecture humaine des joueurs et effectifs ;
- `docs/api_football_players_reference.json` : source machine pour joueurs et squads ;
- `docs/api_football_players_cache.json` : cache technique de collecte `/players/squads`,
  utile seulement pour reprendre ou éviter des appels API.

Les fichiers JSON servent au code et aux tests. Les fichiers Markdown servent à comprendre
et documenter. Le cache joueurs ne remplace pas le référentiel joueurs structuré.

Le fichier `config/competitions.example.yaml` liste les compétitions suivies. Ses IDs sont
résolus et validés contre `docs/api_football_reference.json`; une entrée absente du
référentiel est rejetée au lieu d'être devinée.

## Client API-Football

Tous les appels live doivent passer par `ApiFootballClient`. Le client utilise uniquement
des requêtes GET, envoie la clé via le header `x-apisports-key`, supporte les query params,
les retries et la pagination `paging.current` / `paging.total`.

L'écriture des réponses brutes est optionnelle avec `save_raw=True`. Les snapshots sont
enregistrés sous `data/raw/api_football/` par défaut et contiennent `endpoint`, `params`,
`payload`, `fetched_at`, `status_code` et `source`, jamais la clé API.

Exemple d'utilisation sans ID inventé :

```python
import os

from football_predictor.api import ApiFootballClient
from football_predictor.api.endpoints import FIXTURES

client = ApiFootballClient(
    base_url="https://v3.football.api-sports.io",
    api_key=os.environ["API_FOOTBALL_KEY"],
)

# Remplacer les paramètres par des valeurs validées depuis docs/*.json ou la base locale.
payload = client.get(FIXTURES, params={"league": "<league_id_verifie>", "season": "<season>"})
```

La clé réelle doit venir de `API_FOOTBALL_KEY` dans l'environnement ou un `.env` local non
versionné. Elle ne doit jamais être écrite dans le code, les tests, les logs ou les snapshots.

## Qualité Attendue

Commandes de vérification Sprint 1 :

```bash
pytest
ruff check .
mypy src
```

Les tests unitaires ne doivent pas faire d'appel réseau. Les tests réalistes doivent
s'appuyer sur des échantillons issus des JSON locaux, ou déclarer explicitement leurs
données comme synthétiques.

## Sprint 0 Completed

Sprint 0 établit la documentation de base du projet :

- objectif produit et avertissement probabiliste ;
- workflow Codex autour de `AGENTS.md` et `blueprint.md` ;
- rôle des cinq fichiers de référence existants sous `docs/` ;
- architecture cible `src/football_predictor` ;
- stratégie de modélisation, backtesting et calibration ;
- contrat de données, snapshots temporels et règles anti data leakage ;
- rappel explicite : ne jamais inventer d'ID API-Football.

## Sprint 1 Bootstrap

Sprint 1 établit la base technique :

- package importable `football_predictor` ;
- configuration `pyproject.toml` pour build, CLI, pytest, ruff et mypy ;
- CLI minimale `football-predictor doctor` ;
- settings typés avec `pydantic-settings` ;
- chemins configurables vers les référentiels `docs/` dans `.env.example` ;
- module `src/football_predictor/reference/` présent pour les futurs loaders locaux ;
- tests smoke sans ID API-Football inventé ;
- préservation des cinq fichiers référentiels sous `docs/`.

## Sprint 3 Storage

Sprint 3 ajoute :

- schéma SQLAlchemy complet pour référentiels, snapshots, features, prédictions et Discord ;
- première migration Alembic ;
- liaison `ModelPrediction -> FeatureSnapshot` ;
- champs normalisés utiles aux odds, lineups et player stats ;
- tests SQLite temporaires et seed idempotent depuis les JSON docs.

## Sprint 4 Reference Ingestion

Sprint 4 ajoute :

- services de seed séparés pour référentiels compétitions et joueurs ;
- lookups locaux enrichis dans `reference/`, toujours sans appel API ;
- chargement YAML/JSON des compétitions suivies avec validation des IDs ;
- ingestion live explicite pour leagues, teams, player squads, bookmakers et bets ;
- sauvegarde de chaque réponse API live en `RawApiSnapshot` avant upsert ;
- sécurité CLI : aucun appel live sans `--refresh-api`.

## Sprint 2 API Client

Sprint 2 ajoute :

- configuration timeout, retries et répertoire de snapshots API ;
- client `httpx` injectable pour tests sans réseau réel ;
- exceptions explicites pour `204`, `499`, `4xx` et `5xx` ;
- pagination API-Football agrégée ;
- snapshots bruts JSON optionnels sans secret ;
- tests unitaires avec `httpx.MockTransport`.
