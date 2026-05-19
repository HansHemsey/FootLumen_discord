# Mode VPS temporaire Coupe du Monde only

Ce document decrit la bascule temporaire du VPS vers un mode centre sur la Coupe du Monde 2026,
puis la marche arriere pour revenir aux championnats a la reprise de la saison 2026.

## Objectif

- Reduire les appels API inutiles sur les championnats termines.
- Concentrer l'ingestion sur `fifa_world_cup_2026`.
- Publier les predictions CDM M-30 avec le modele `worldcup-1x2`.
- Continuer a enrichir la base avec fixtures, standings, odds, squads, details post-match,
  lineups, stats joueurs, injuries et predictions API.
- Garder un retour championnat simple en aout 2026.

## Fichiers ajoutes

- `config/competitions_worldcup.yaml` : config CDM only.
- `config/prod_worldcup.crontab` : crontab VPS Ubuntu CDM only.
- `config/competitions_2026.example.yaml` : base de reprise pour les championnats 2026.

## Crontab avant modification

Le mode championnat faisait tourner toutes les routines domestiques :

```cron
SHELL=/bin/bash
PATH=/opt/football-predictor/app/.venv/bin:/usr/local/bin:/usr/bin:/bin
APP_TIMEZONE=Europe/Paris
PROJECT=/opt/football-predictor/app
LOGDIR=/opt/football-predictor/app/logs/cron
MPLCONFIGDIR=/opt/football-predictor/app/.cache/matplotlib
LOKY_MAX_CPU_COUNT=2

# Fixtures semaine J+7, chaque lundi matin.
15 5 * * 1 cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_ingestion.lock env SAVE_RAW=true DRY_RUN=false scripts/weekly_ingestion.sh >> "$LOGDIR/weekly_ingestion.log" 2>&1

# Routine matin championnats + CDM selon config courante.
30 6 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_daily_morning.lock env REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false PUBLISH_DISCORD=true SAVE_RAW=true scripts/daily_morning.sh >> "$LOGDIR/daily_morning.log" 2>&1

# Analyses H-6 championnats.
*/15 6-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_match_analyses.lock env MODEL_DIR=data/models/v2-late REFRESH_DATA=false SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh >> "$LOGDIR/match_analyses.log" 2>&1

# V3 1X2 championnats M-30.
1,11,21,31,41,51 7-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_daily_late.lock env PREDICTION_ENGINE=v3 WINDOW=late REFRESH_DATA=true SEND_DISCORD=false DRY_RUN=true SAVE_RAW=true scripts/daily_late.sh >> "$LOGDIR/daily_late_v3.log" 2>&1

# O/U 2.5 championnats M-30.
3,13,23,33,43,53 7-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_daily_ou.lock env WINDOW=late REFRESH_DATA=true SEND_DISCORD=false DRY_RUN=true SAVE_RAW=true scripts/daily_ou.sh >> "$LOGDIR/daily_ou.log" 2>&1

# Resultats post-match.
20,50 12-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_match_results.lock env REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false SAVE_RAW=true scripts/publish_match_results.sh >> "$LOGDIR/match_results.log" 2>&1

# Score public hebdo.
10 8,12,18 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_score.lock env DRY_RUN=false scripts/publish_weekly_score.sh >> "$LOGDIR/weekly_score.log" 2>&1
55 23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_score.lock env DRY_RUN=false scripts/publish_weekly_score.sh >> "$LOGDIR/weekly_score.log" 2>&1
```

## Crontab apres modification

Le mode CDM only est versionne dans `config/prod_worldcup.crontab`.

Il garde uniquement :

- fixtures CDM J+7 ;
- refresh quotidien fixtures + standings CDM ;
- daily morning CDM ;
- squads/effectifs CDM deux fois par semaine ;
- backfill post-match CDM ;
- predictions CDM M-30 ;
- resultats CDM ;
- score hebdo.

Les routines championnats suivantes sont desactivees dans ce profil :

- `scripts/daily_late.sh` ;
- `scripts/daily_ou.sh` ;
- `scripts/publish_match_analyses.sh` ;
- `PREDICTION_ENGINE=v3`.

Crontab CDM only :

```cron
SHELL=/bin/bash
PATH=/opt/football-predictor/app/.venv/bin:/usr/local/bin:/usr/bin:/bin
APP_TIMEZONE=Europe/Paris
PROJECT=/opt/football-predictor/app
LOGDIR=/opt/football-predictor/app/logs/cron
MPLCONFIGDIR=/opt/football-predictor/app/.cache/matplotlib
LOKY_MAX_CPU_COUNT=2
CONFIG_WC=config/competitions_worldcup.yaml

# MODE TEMPORAIRE COUPE DU MONDE ONLY.
# DISABLED UNTIL AUGUST 2026: routines championnats V3, O/U et analyses H-6 domestic.

15 5 * * 1 cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_wc_weekly_ingestion.lock env CONFIG="$CONFIG_WC" SAVE_RAW=true DRY_RUN=false scripts/weekly_ingestion.sh >> "$LOGDIR/worldcup_weekly_ingestion.log" 2>&1
50 5 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_wc_fixtures.lock env CONFIG="$CONFIG_WC" REFRESH_FIXTURES=true REFRESH_STANDINGS=true REFRESH_ODDS=false REFRESH_DETAILS=false SAVE_RAW=true scripts/refresh_all_leagues.sh >> "$LOGDIR/worldcup_fixtures.log" 2>&1
30 6 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_wc_daily_morning.lock env CONFIG="$CONFIG_WC" REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false PUBLISH_DISCORD=true SAVE_RAW=true scripts/daily_morning.sh >> "$LOGDIR/worldcup_daily_morning.log" 2>&1
40 4 * * 1,4 cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_wc_player_squads.lock football-predictor ingest-player-squads --config "$CONFIG_WC" --refresh-api >> "$LOGDIR/worldcup_player_squads.log" 2>&1
45 3 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_wc_details.lock env CONFIG="$CONFIG_WC" REFRESH_FIXTURES=false REFRESH_STANDINGS=false REFRESH_ODDS=false REFRESH_DETAILS=true DETAILS_ONLY="statistics events lineups players injuries predictions" DETAILS_DAYS_BACK=3 DETAILS_STATUSES="FT AET PEN" DETAILS_LIMIT=80 DETAILS_DELAY_SECONDS=2 DETAILS_SKIP_IF_COMPLETE=true SAVE_RAW=true scripts/refresh_all_leagues.sh >> "$LOGDIR/worldcup_details.log" 2>&1
1,11,21,31,41,51 7-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_wc_late.lock football-predictor worldcup-run-daily --window late --model-dir data/models/worldcup-1x2 --refresh-data --save-raw --send-discord --no-dry-run --json-output reports/daily/worldcup_late_summary.json >> "$LOGDIR/worldcup_late.log" 2>&1
20,50 12-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_wc_match_results.lock env CONFIG="$CONFIG_WC" REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false SAVE_RAW=true scripts/publish_match_results.sh >> "$LOGDIR/worldcup_match_results.log" 2>&1
10 8,12,18 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_wc_weekly_score.lock env DRY_RUN=false scripts/publish_weekly_score.sh >> "$LOGDIR/worldcup_weekly_score.log" 2>&1
55 23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_wc_weekly_score.lock env DRY_RUN=false scripts/publish_weekly_score.sh >> "$LOGDIR/worldcup_weekly_score.log" 2>&1
```

## Mise en place sur le VPS

Depuis le VPS :

```bash
cd /opt/football-predictor/app
source .venv/bin/activate

git status --short
crontab -l > ~/crontab.backup.before-worldcup-only.$(date +%F-%H%M%S)

git fetch origin
git pull --ff-only origin main

football-predictor doctor --strict
football-predictor worldcup-audit-reference
```

Verifier ou generer le modele CDM :

```bash
football-predictor worldcup-build-dataset --output data/processed/worldcup_1x2_training.parquet
football-predictor worldcup-train-1x2 --dataset data/processed/worldcup_1x2_training.parquet --output-dir data/models/worldcup-1x2
football-predictor worldcup-optimize-blend --dataset data/processed/worldcup_1x2_training.parquet --model-dir data/models/worldcup-1x2 --output-dir reports/worldcup_blend --write-best-config
ls -lah data/models/worldcup-1x2
```

Smoke test sans publication Discord :

```bash
football-predictor worldcup-run-daily \
  --window late \
  --model-dir data/models/worldcup-1x2 \
  --refresh-data \
  --save-raw \
  --dry-run
```

Installer le crontab CDM only :

```bash
crontab config/prod_worldcup.crontab
crontab -l
```

Surveiller les premiers logs :

```bash
tail -n 100 logs/cron/worldcup_daily_morning.log
tail -n 100 logs/cron/worldcup_late.log
tail -n 100 logs/cron/worldcup_details.log
tail -n 100 logs/cron/worldcup_weekly_score.log
```

## Commandes manuelles utiles pendant la CDM

Refresh fixtures/standings CDM :

```bash
env CONFIG=config/competitions_worldcup.yaml REFRESH_FIXTURES=true REFRESH_STANDINGS=true REFRESH_ODDS=false REFRESH_DETAILS=false SAVE_RAW=true scripts/refresh_all_leagues.sh
```

Refresh squads/effectifs CDM :

```bash
football-predictor ingest-player-squads --config config/competitions_worldcup.yaml --refresh-api
```

Backfill post-match CDM recent :

```bash
env CONFIG=config/competitions_worldcup.yaml \
  REFRESH_FIXTURES=false \
  REFRESH_STANDINGS=false \
  REFRESH_ODDS=false \
  REFRESH_DETAILS=true \
  DETAILS_ONLY="statistics events lineups players injuries predictions" \
  DETAILS_DAYS_BACK=3 \
  DETAILS_STATUSES="FT AET PEN" \
  DETAILS_LIMIT=80 \
  DETAILS_DELAY_SECONDS=2 \
  DETAILS_SKIP_IF_COMPLETE=true \
  SAVE_RAW=true \
  scripts/refresh_all_leagues.sh
```

Prediction CDM M-30 en dry-run :

```bash
football-predictor worldcup-run-daily --window late --model-dir data/models/worldcup-1x2 --refresh-data --save-raw --dry-run
```

## Retour en mode championnat en aout 2026

1. Sauvegarder le crontab CDM :

```bash
crontab -l > ~/crontab.backup.before-championship-return.$(date +%F-%H%M%S)
```

2. Creer la config championnats 2026 :

```bash
cd /opt/football-predictor/app
cp config/competitions_2026.example.yaml config/competitions_2026.yaml
```

Verifier le fichier avant usage. Ne pas inventer d'ID ; les IDs doivent rester ceux du referentiel
API-Football local.

3. Faire une grosse ingestion de reprise :

```bash
env CONFIG=config/competitions_2026.yaml REFRESH_TEAMS=true REFRESH_FIXTURES=true REFRESH_STANDINGS=true REFRESH_ODDS=true REFRESH_DETAILS=false SAVE_RAW=true scripts/refresh_all_leagues.sh

football-predictor ingest-player-squads --config config/competitions_2026.yaml --refresh-api
```

4. Backfill details recents si les fixtures sont disponibles :

```bash
env CONFIG=config/competitions_2026.yaml \
  REFRESH_FIXTURES=false \
  REFRESH_STANDINGS=false \
  REFRESH_ODDS=false \
  REFRESH_DETAILS=true \
  DETAILS_ONLY="statistics events lineups players injuries predictions" \
  DETAILS_DAYS_BACK=14 \
  DETAILS_STATUSES="FT AET PEN" \
  DETAILS_LIMIT=150 \
  DETAILS_DELAY_SECONDS=2 \
  DETAILS_SKIP_IF_COMPLETE=true \
  SAVE_RAW=true \
  scripts/refresh_all_leagues.sh
```

5. Reinstaller le crontab championnats :

```bash
crontab config/prod.crontab
crontab -l
```

Sur le VPS Ubuntu, utilise plutot le crontab championnat propre ci-dessous. Il remet les routines
domestiques et ajoute l'entretien regulier qui manquait avant la CDM : squads/effectifs et details
historiques recents.

Crontab championnat 2026 recommande :

```cron
SHELL=/bin/bash
PATH=/opt/football-predictor/app/.venv/bin:/usr/local/bin:/usr/bin:/bin
APP_TIMEZONE=Europe/Paris
PROJECT=/opt/football-predictor/app
LOGDIR=/opt/football-predictor/app/logs/cron
MPLCONFIGDIR=/opt/football-predictor/app/.cache/matplotlib
LOKY_MAX_CPU_COUNT=2
CONFIG_CHAMP=config/competitions_2026.yaml

# MODE CHAMPIONNATS 2026.
# Coupe du Monde desactivee par defaut : WORLD_CUP_1X2_ENABLED=false.

# Fixtures championnats J+7, chaque lundi matin.
15 5 * * 1 cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_ingestion.lock env CONFIG="$CONFIG_CHAMP" SAVE_RAW=true DRY_RUN=false scripts/weekly_ingestion.sh >> "$LOGDIR/weekly_ingestion.log" 2>&1

# Squads/effectifs championnats : refresh prudent hebdomadaire.
35 4 * * 1 cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_player_squads.lock football-predictor ingest-player-squads --config "$CONFIG_CHAMP" --refresh-api >> "$LOGDIR/player_squads.log" 2>&1

# Details historiques recents termines : lineups, stats joueurs, blessures, events, predictions API.
45 4 * * 2 cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_details.lock env CONFIG="$CONFIG_CHAMP" REFRESH_FIXTURES=false REFRESH_STANDINGS=false REFRESH_ODDS=false REFRESH_DETAILS=true DETAILS_ONLY="statistics events lineups players injuries predictions" DETAILS_DAYS_BACK=10 DETAILS_STATUSES="FT AET PEN" DETAILS_LIMIT=120 DETAILS_DELAY_SECONDS=2 DETAILS_SKIP_IF_COMPLETE=true SAVE_RAW=true scripts/refresh_all_leagues.sh >> "$LOGDIR/weekly_details.log" 2>&1

# Routine matin : init, refs, standings, odds du jour, classements, calendriers, matchs du jour, score hebdo.
30 6 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_daily_morning.lock env CONFIG="$CONFIG_CHAMP" REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false PUBLISH_DISCORD=true SAVE_RAW=true scripts/daily_morning.sh >> "$LOGDIR/daily_morning.log" 2>&1

# Analyses H-6 championnats : publication reelle.
*/15 6-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_match_analyses.lock env CONFIG="$CONFIG_CHAMP" MODEL_DIR=data/models/v2-late REFRESH_DATA=false SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh >> "$LOGDIR/match_analyses.log" 2>&1

# V3 1X2 championnats M-30 : shadow par defaut tant que l'artefact production V3 n'est pas valide.
# Pour publier apres validation, passer SEND_DISCORD=true DRY_RUN=false.
1,11,21,31,41,51 7-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_daily_late.lock env CONFIG="$CONFIG_CHAMP" PREDICTION_ENGINE=v3 WINDOW=late REFRESH_DATA=true SEND_DISCORD=false DRY_RUN=true SAVE_RAW=true WORLD_CUP_1X2_ENABLED=false scripts/daily_late.sh >> "$LOGDIR/daily_late_v3.log" 2>&1

# O/U 2.5 championnats M-30 : shadow par defaut tant que l'artefact production O/U n'est pas valide.
# Pour publier apres validation, passer SEND_DISCORD=true DRY_RUN=false.
3,13,23,33,43,53 7-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_daily_ou.lock env CONFIG="$CONFIG_CHAMP" WINDOW=late REFRESH_DATA=true SEND_DISCORD=false DRY_RUN=true SAVE_RAW=true scripts/daily_ou.sh >> "$LOGDIR/daily_ou.log" 2>&1

# Resultats post-match : refresh scores + publication.
20,50 12-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_match_results.lock env CONFIG="$CONFIG_CHAMP" REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false SAVE_RAW=true scripts/publish_match_results.sh >> "$LOGDIR/match_results.log" 2>&1

# Score public hebdo : mises a jour apres les resultats.
10 8,12,18 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_score.lock env DRY_RUN=false scripts/publish_weekly_score.sh >> "$LOGDIR/weekly_score.log" 2>&1
55 23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_score.lock env DRY_RUN=false scripts/publish_weekly_score.sh >> "$LOGDIR/weekly_score.log" 2>&1
```

Pour l'installer proprement :

```bash
cat > /tmp/prod_championship_2026.crontab <<'CRON'
SHELL=/bin/bash
PATH=/opt/football-predictor/app/.venv/bin:/usr/local/bin:/usr/bin:/bin
APP_TIMEZONE=Europe/Paris
PROJECT=/opt/football-predictor/app
LOGDIR=/opt/football-predictor/app/logs/cron
MPLCONFIGDIR=/opt/football-predictor/app/.cache/matplotlib
LOKY_MAX_CPU_COUNT=2
CONFIG_CHAMP=config/competitions_2026.yaml

15 5 * * 1 cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_ingestion.lock env CONFIG="$CONFIG_CHAMP" SAVE_RAW=true DRY_RUN=false scripts/weekly_ingestion.sh >> "$LOGDIR/weekly_ingestion.log" 2>&1
35 4 * * 1 cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_player_squads.lock football-predictor ingest-player-squads --config "$CONFIG_CHAMP" --refresh-api >> "$LOGDIR/player_squads.log" 2>&1
45 4 * * 2 cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_details.lock env CONFIG="$CONFIG_CHAMP" REFRESH_FIXTURES=false REFRESH_STANDINGS=false REFRESH_ODDS=false REFRESH_DETAILS=true DETAILS_ONLY="statistics events lineups players injuries predictions" DETAILS_DAYS_BACK=10 DETAILS_STATUSES="FT AET PEN" DETAILS_LIMIT=120 DETAILS_DELAY_SECONDS=2 DETAILS_SKIP_IF_COMPLETE=true SAVE_RAW=true scripts/refresh_all_leagues.sh >> "$LOGDIR/weekly_details.log" 2>&1
30 6 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_daily_morning.lock env CONFIG="$CONFIG_CHAMP" REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false PUBLISH_DISCORD=true SAVE_RAW=true scripts/daily_morning.sh >> "$LOGDIR/daily_morning.log" 2>&1
*/15 6-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_match_analyses.lock env CONFIG="$CONFIG_CHAMP" MODEL_DIR=data/models/v2-late REFRESH_DATA=false SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh >> "$LOGDIR/match_analyses.log" 2>&1
1,11,21,31,41,51 7-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_daily_late.lock env CONFIG="$CONFIG_CHAMP" PREDICTION_ENGINE=v3 WINDOW=late REFRESH_DATA=true SEND_DISCORD=false DRY_RUN=true SAVE_RAW=true WORLD_CUP_1X2_ENABLED=false scripts/daily_late.sh >> "$LOGDIR/daily_late_v3.log" 2>&1
3,13,23,33,43,53 7-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_daily_ou.lock env CONFIG="$CONFIG_CHAMP" WINDOW=late REFRESH_DATA=true SEND_DISCORD=false DRY_RUN=true SAVE_RAW=true scripts/daily_ou.sh >> "$LOGDIR/daily_ou.log" 2>&1
20,50 12-23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_match_results.lock env CONFIG="$CONFIG_CHAMP" REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false SAVE_RAW=true scripts/publish_match_results.sh >> "$LOGDIR/match_results.log" 2>&1
10 8,12,18 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_score.lock env DRY_RUN=false scripts/publish_weekly_score.sh >> "$LOGDIR/weekly_score.log" 2>&1
55 23 * * * cd "$PROJECT" && mkdir -p "$LOGDIR" "$MPLCONFIGDIR" && flock -n /tmp/probet_weekly_score.lock env DRY_RUN=false scripts/publish_weekly_score.sh >> "$LOGDIR/weekly_score.log" 2>&1
CRON

crontab /tmp/prod_championship_2026.crontab
crontab -l
```

Le point important est de remettre :

- `daily_late.sh` ;
- `daily_ou.sh` ;
- `publish_match_analyses.sh` ;
- `CONFIG=config/competitions_2026.yaml` ou une config championnats equivalente ;
- `WORLD_CUP_1X2_ENABLED=false`, sauf besoin explicite de garder la CDM active.

6. Validation retour championnat :

```bash
football-predictor doctor --strict
env CONFIG=config/competitions_2026.yaml REFRESH_DATA=false SEND_DISCORD=false DRY_RUN=true scripts/daily_morning.sh
env CONFIG=config/competitions_2026.yaml PREDICTION_ENGINE=v3 WINDOW=late REFRESH_DATA=false SEND_DISCORD=false DRY_RUN=true scripts/daily_late.sh
env CONFIG=config/competitions_2026.yaml WINDOW=late REFRESH_DATA=false SEND_DISCORD=false DRY_RUN=true scripts/daily_ou.sh
```
