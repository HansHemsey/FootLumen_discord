# Operations Guide

Ce guide decrit l'exploitation locale quotidienne, les diagnostics et les procedures de reprise.

## Sources Et Secrets

Les secrets restent hors Git :

- `.env` local ;
- variables d'environnement du systeme ;
- `config/discord_webhooks.local.yaml` pour les URLs Discord.

Ne jamais afficher une cle API, une URL webhook complete ou un bot token. Les logs peuvent afficher
un statut configure/non configure et un hash court.

## Fichiers De Reference

Les cinq fichiers suivants doivent etre presents sur la machine d'exploitation :

```text
docs/api_football_reference.md
docs/api_football_reference.json
docs/api_football_players_reference.md
docs/api_football_players_reference.json
docs/api_football_players_cache.json
```

`api_football_players_cache.json` est un cache technique de collecte. Le seed metier joueurs doit
utiliser `api_football_players_reference.json`.

## Routine D'Exploitation

- Lundi matin : `scripts/weekly_ingestion.sh` prépare les fixtures des 7 prochains jours.
- Chaque matin : `scripts/daily_morning.sh` rafraîchit la DB et publie classement,
  calendrier, matchs du jour et score-pronos-semaine.
- H-6 : `scripts/publish_match_analyses.sh` publie seulement les analyses pré-match assez
  riches pour être utiles.
- M-30 : `scripts/daily_late.sh` génère V3 1X2 et `scripts/daily_ou.sh` génère O/U 2.5.
- Après match : `scripts/publish_match_results.sh` publie les résultats `FT/AET/PEN`.

Les vrais envois Discord exigent toujours `SEND_DISCORD=true DRY_RUN=false`. Les pronostics
faibles ou insuffisamment fiables restent internes et ne sont pas comptés dans le score
hebdomadaire.

## Checklist Quotidienne

```bash
scripts/football_predictor_cli.sh doctor --strict
scripts/football_predictor_cli.sh data-quality
scripts/smoke_test_local.sh
```

Rapports qualité sans réseau :

```bash
scripts/football_predictor_cli.sh data-quality --date YYYY-MM-DD --model-family all --json
scripts/football_predictor_cli.sh data-quality \
  --week-of YYYY-MM-DD \
  --model-family v3 \
  --json-output reports/data_quality_week.json \
  --markdown-output reports/data_quality_week.md
```

Le smoke test local n'appelle ni API-Football ni Discord. Il valide les fichiers de reference, la
DB, le seed local et une execution `predict-today` en dry-run.

Si l'entrypoint `football-predictor` installé dans `.venv` semble en retard sur le code
local, utiliser `scripts/football_predictor_cli.sh`. Ce wrapper injecte `PYTHONPATH=src`.
`make install` répare aussi l'installation editable Python 3.13 avec un `.pth` non caché.
Une erreur `Unknown competition key='global'` dans `doctor` indique souvent un paquet
installé obsolète : `global` est une route Discord volontaire pour les channels globaux
comme `score_pronos_semaine`, pas une compétition API-Football.

## Routine De Prediction

### T-24h

Objectif : prediction early avec fixtures connues, standings et odds deja disponibles.

```bash
WINDOW=early REFRESH_DATA=false DRY_RUN=true scripts/run_predict_today.sh
```

### H-6h

Objectif : refresh odds et donnees match si la cle API est disponible.

```bash
REFRESH_DATA=true WINDOW=mid DRY_RUN=true scripts/run_predict_today.sh
```

### M-30min

Objectif : tenter lineups, blessures et mouvements de cotes avant kickoff.

```bash
REFRESH_DATA=true WINDOW=late DRY_RUN=true scripts/run_predict_today.sh
```

Passe `SEND_DISCORD=true` seulement apres validation des webhooks et des routes.

### Production V3 Discord

Depuis Sprint 10, `scripts/daily_late.sh` utilise la V3 par defaut pour le channel
`predictions`. Les appels manuels de `predict-today-v3` restent en shadow mode par defaut ;
ajouter `--production-mode` pour autoriser le chemin production. Le répertoire modèle doit
contenir `confidence_thresholds.json` avec `production_approved=true`, sinon le runner
refuse le mode production avant prédiction.

```bash
football-predictor predict-today-v3 \
  --window late \
  --model-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --production-mode \
  --no-refresh-data \
  --json
```

Envoi reel V3 via la routine late :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

Rollback V2 :

```bash
PREDICTION_ENGINE=v2 SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

En rollback, conserver les artefacts V3/O-U précédents mais les lancer en shadow/dry-run
jusqu'à ce qu'un nouveau rapport backtest approuvé soit disponible. Le modèle V2 late reste
dans `data/models/v2-late`; si ce répertoire manque, le pipeline retombe sur les fallbacks
documentés.

Le fichier d'approbation est généré par les backtests de calibration. Pour promouvoir un
nouveau modèle, copier l'artefact approuvé dans le répertoire modèle actif, par exemple
`data/models/v3/confidence_thresholds.json` ou
`data/models/ou-v1/confidence_thresholds.json`. Si l'artefact manque, est invalide ou n'est
pas approuvé, le log indique `Production mode refused` avec le modèle, le chemin attendu et
la raison, sans afficher de secret. Pour verifier le rendu Discord V3 sans publier :

Règle de publication publique : V2, V3 1X2 et O/U 2.5 ne publient dans Discord que les
pronostics `High` ou `Very High` avec une qualité de données suffisante
(`PUBLICATION_MIN_DATA_QUALITY_SCORE=60` par défaut). Les labels `Low`, `Medium`,
`Uncertain`, les scores qualité absents et les scores qualité sous le seuil sont persistés
en base mais retournent `confidence_skipped` avec une raison normalisée. Si
`data_quality_json.publication_blockers` est non vide, la publication réelle est aussi bloquée
avec `data_quality_blocker_present`.

```bash
football-predictor predict-today-v3 --window late --dry-run --print-only
```

## Automatisation Quotidienne Multi-Ligues

Les scripts quotidiens utilisent `config/competitions.yaml` et le binaire local `.venv` si
present. Ils ne contiennent aucun secret et n'affichent pas les valeurs de `.env`.

```bash
# Matin : doctor, init DB, seed docs, refresh standings/odds et publications operationnelles.
scripts/daily_morning.sh

# Avant match : window late, refresh odds/injuries/API predictions/lineups si disponibles.
scripts/daily_late.sh

# O/U 2.5 M-30 : pipeline séparé, même logique de publication sélective.
scripts/daily_ou.sh

# Lundi : préparation des fixtures des 7 prochains jours.
scripts/weekly_ingestion.sh

# Publication seule : classement, prochaine journee et matchs du jour.
scripts/publish_daily_discord.sh

# Backfill manuel plus lourd sur les saisons completes.
scripts/refresh_all_leagues.sh

# Dataset multi-ligues, entrainement et backtest.
scripts/train_backtest_all.sh
```

Variables utiles :

```bash
DATE=YYYY-MM-DD
WINDOW=now|early|mid|late|all
CONFIG=config/competitions.yaml
PREDICTION_ENGINE=v3
MODEL_DIR=data/models/v3
V2_MODEL_DIR=data/models/v2-late
OU_MODEL_DIR=data/models/ou-v1
SEND_DISCORD=false
DRY_RUN=true
FORCE=false
SAVE_RAW=true
LIMIT=
```

Par defaut, `daily_morning.sh` et `daily_late.sh` n'envoient rien dans Discord. Pour un
envoi reel, utiliser explicitement :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

`daily_morning.sh` appelle `publish_daily_discord.sh` apres le refresh standings/fixtures.
Il ne lance plus de prediction matinale. Les publications alimentent `classement`, `calendrier`,
`matchs_du_jour` et `score_pronos_semaine`. Le calendrier correspond a la prochaine
journee/round connue, pas a la saison complete. Les messages sont decoupes automatiquement
en plusieurs parties sous la limite Discord de 2000 caracteres.

`REPLACE_PREVIOUS=true` est le defaut pour ces publications operationnelles : l'outil
supprime les anciens messages Discord qu'il a envoyes et qui sont encore retrouves dans la
DB, puis publie la nouvelle version. Les predictions, analyses, resultats et discussions
ne sont pas nettoyes automatiquement. Pour conserver l'historique des messages
operationnels :

```bash
REPLACE_PREVIOUS=false scripts/publish_daily_discord.sh
```

Les channels `analyses` et `resultats` ont leurs propres scripts. Ils publient un seul
message par match et gardent l'historique :

Le score hebdomadaire compte uniquement les predictions réellement envoyées dans Discord
et dont le match est terminé : V2 legacy, V3 via `v3_model_prediction_id`, et O/U 2.5 via
`ou_model_prediction_id`. Les prédictions internes non publiées, `dry_run`, `print_only`
et `confidence_skipped` ne sont jamais incluses.
Le payload du message `weekly_prediction_score` conserve un audit local avec
`model_family_counts` et `counted_predictions` pour relier chaque ligne au message Discord
et a la prediction source réellement comptés. Ce bilan reflète l'état enregistré dans la
base locale : une suppression manuelle directement dans Discord n'est pas détectable sans
audit API explicite.
Il est remplace par `week_key` : une relance dans la même semaine met a jour le message
de cette semaine, mais ne supprime pas les autres semaines. Le lundi, `daily_morning.sh`
publie aussi une finalisation de la semaine précédente pour inclure les matchs du dimanche
dont les scores ont ete rafraîchis pendant la nuit.

```bash
# A lancer toutes les 15 minutes si tu veux capter la fenetre H-6 -> H-5h45.
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh

# A lancer toutes les 30-60 minutes apres les matchs.
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
```

`publish_match_analyses.sh` appelle `publish-match-analyses` et utilise strictement
`prediction_time = fixture.date - 6h`. La marge d'envoi est `ANALYSIS_GRACE_MINUTES=15`
par defaut. Le message contient le contexte, la forme recente, le classement, les odds, les
absences/XI si disponibles, les points forts/faibles et une conclusion prudente.
Une analyse trop pauvre est ignorée avec `reason=insufficient_analysis_data` afin d'éviter
les messages génériques remplis de champs non disponibles.
`publish_match_results.sh` appelle `publish-match-results` uniquement pour les fixtures
`FT/AET/PEN` avec score final, puis compare le resultat a la prediction pre-match publiee
si elle existe. Avec `REFRESH_DATA=true`, il rafraichit les fixtures du jour pour capter
les scores finaux. Ces deux flux ne remplacent jamais les anciens messages.

`daily_late.sh` peut appeler ces deux scripts sans les activer par defaut :

```bash
PUBLISH_ANALYSES=true PUBLISH_RESULTS=true SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

`refresh_all_leagues.sh` ne backfill pas les details de match par defaut, car les endpoints
`/fixtures/statistics`, `/fixtures/events` et `/fixtures/players` multiplient les appels par
fixture. Pour un backfill progressif :

```bash
REFRESH_DETAILS=true DETAILS_LIMIT=5 DETAILS_DELAY_SECONDS=2 scripts/refresh_all_leagues.sh
```

Convention d'exploitation :

- fixtures futures de la semaine courante : `scripts/weekly_ingestion.sh`, convention `J+7`
  incluant la date d'exécution locale puis les 6 dates suivantes ;
- détails récents de matchs terminés : `refresh_all_leagues.sh` avec `DETAILS_DAYS_BACK`,
  convention `J-7`.

Exemple lundi :

```bash
scripts/weekly_ingestion.sh
```

Routine hebdomadaire recommandee pour les details des matchs termines :

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

`DETAILS_DAYS_BACK=7` limite la selection a la periode recente et
`DETAILS_STATUSES="FT AET PEN"` est converti en filtres de statuts separes. Si
API-Football retourne `429`, le batch s'arrete au premier rate-limit. Attends le reset de
quota ou reduis `DETAILS_LIMIT` avant de relancer.
`DETAILS_SKIP_IF_COMPLETE=true` est le comportement recommande : le script saute les endpoints
detail deja stockes ou deja connus comme `no content`, endpoint par endpoint, pour ne pas
rappeler inutilement API-Football.

Les joueurs absents du referentiel statique sont collectes dans
`data/processed/unknown_players.jsonl`. Pour les resoudre progressivement dans la DB locale :

```bash
RESOLVE_UNKNOWN_PLAYERS=true UNKNOWN_PLAYERS_LIMIT=50 UNKNOWN_PLAYERS_DELAY_SECONDS=2 \
  scripts/refresh_all_leagues.sh
```

Cette resolution est optionnelle, explicite et ne modifie jamais
`docs/api_football_players_reference.json`.

### Config Production Et Historique

`config/competitions.yaml` est la config de production quotidienne. Les scripts
`daily_morning.sh`, `daily_late.sh`, `daily_ou.sh` et `refresh_all_leagues.sh` l'utilisent
par defaut pour rafraichir uniquement les competitions suivies en saison courante.

`config/competitions_history.yaml` est la config d'entrainement/backtest. Elle liste Ligue
1, Premier League, La Liga, Bundesliga et Serie A sur les saisons `2022`, `2023`, `2024`
et `2025`, avec une cle unique par saison et un `reference_key` qui valide le vrai
`league_id` depuis `docs/api_football_reference.json`.

Les fixtures hebdomadaires ingerees via la config production sont stockees une seule fois
dans la DB avec leur `league_id` et leur `season`. Elles sont ensuite reprises par les
datasets d'entrainement car la saison courante existe aussi dans
`config/competitions_history.yaml`.

### Backfill Saison Complete

Pour enrichir une saison entiere sans modifier `config/competitions.yaml`, utilise :

```bash
SEASON=2024 scripts/backfill_season.sh
```

Le script cree `data/processed/backfill/competitions_2024.yaml` depuis
`config/competitions_history.yaml` quand il existe, en filtrant uniquement `season: 2024`.
S'il n'existe pas, il genere un fallback temporaire depuis la config de production avec des
`reference_key` historiques. Cela permet de gerer les montees/descentes via `ingest-teams`,
puis de stocker les fixtures et details avec le bon couple `league_id` / `season`.
Les competitions de coupe ou globales sont desactivees par defaut pour eviter d'appeler une
CDM avec une saison de championnat. `BACKFILL_INCLUDE_CUPS=true` est reserve aux backfills
specifiques de coupes.

Parametres par defaut :

```text
DETAILS_FROM=2024-08-01
DETAILS_TO=2025-07-31
DETAILS_ONLY="statistics events players"
DETAILS_STATUSES="FT AET PEN"
DETAILS_LIMIT=400
DETAILS_DELAY_SECONDS=3
DETAILS_SKIP_IF_COMPLETE=true
REFRESH_ODDS=false
```

`DETAILS_LIMIT` reste un plafond par ligue/saison. Pour resoudre les joueurs inconnus dans
la meme passe, ajoute `RESOLVE_UNKNOWN_PLAYERS=true`, ou lance la resolution separement.

### Entrainement Et Backtest Multi-Saisons

```bash
scripts/train_backtest_all.sh
scripts/train_backtest_ou.sh
football-predictor backtest-production-like --league-id 39 --season 2025 --format both
```

Ces deux scripts utilisent `config/competitions_history.yaml` par defaut. Le premier
entraine/backteste le modele 1X2 `data/models/v2-late`; le second entraine/backteste le
modele Over/Under `data/models/ou-v1`. Les scripts quotidiens continuent d'utiliser
`config/competitions.yaml`, donc l'historique ne ralentit pas la production. Garde les
refresh desactives si tu veux economiser le quota.

Contrôle mensuel recommandé :

```bash
football-predictor backtest-production-like \
  --league-id 39 \
  --season 2025 \
  --v3-model-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --output-dir reports/production_like \
  --format both
```

Promouvoir un modèle uniquement si le rapport published-only valide les critères et si
`confidence_thresholds.json` porte `production_approved=true`. Conserver l'artefact précédent
pour rollback.

## Refresh Live Et Quota API

Les appels live sont toujours explicites :

```bash
football-predictor ingest-fixtures --league 39 --season 2025 --refresh-api --save-raw
football-predictor predict-today --date YYYY-MM-DD --window late --league 39 --season 2025 --refresh-data --save-raw
```

`league_id=39` est verifie dans `docs/api_football_reference.json`. Pour une autre competition,
verifie le referentiel avant de lancer la commande.

Economise le quota avec :

```bash
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json
```

## Cron

La crontab de production autonome est versionnée dans `config/prod.crontab`.
Elle utilise les scripts prod avec publication réelle :

```bash
scripts/install_prod_cron.sh
crontab -l
```

Ce fichier active explicitement `SEND_DISCORD=true DRY_RUN=false` pour les publications
Discord, garde des verrous `lockf` par routine, et écrit les logs dans `logs/cron/`.
`lockf` est un verrou BSD/macOS : sur VPS Linux, ne pas installer cette crontab telle quelle
sans adaptation `flock` ou systemd timer.

Exemple local sans refresh, uniquement pour test manuel :

```cron
15 7 * * * cd /path/to/ProBet_discord && . .venv/bin/activate && football-predictor doctor --strict
30 8 * * * cd /path/to/ProBet_discord && . .venv/bin/activate && scripts/run_predict_today.sh
```

Résumé des routines prod autonomes installées :

```cron
15 5 * * 1     scripts/weekly_ingestion.sh
30 6 * * *     scripts/daily_morning.sh
*/15 6-23 * * * scripts/publish_match_analyses.sh
*/10 7-23 * * * scripts/daily_late.sh
*/10 7-23 * * * scripts/daily_ou.sh
20,50 12-23 * * * scripts/publish_match_results.sh
10 8,12,18 * * * scripts/publish_weekly_score.sh
55 23 * * *    scripts/publish_weekly_score.sh
```

Garde `DRY_RUN=true` seulement pour les tests manuels. La crontab prod est volontairement
configurée pour publier.

## Surveillance Logs

Surveille surtout :

- erreurs API-Football 499, 5xx ou timeouts ;
- warnings de sources optionnelles absentes ;
- data quality basse ;
- erreurs Discord 401/403/404/429 ;
- doublons Discord ignores par deduplication.

Les logs ne doivent jamais afficher de cle API, URL webhook complete ou token.

## Docker

```bash
make docker-build
make docker-doctor
make docker-seed-reference
make docker-predict-today-dry-run
```

`docker-compose.yml` monte :

- `./data:/app/data` pour DB, snapshots, datasets et modeles ;
- `./docs:/app/docs:ro` pour les referentiels ;
- `./config:/app/config:ro` pour les configs locales.

Ne place jamais `.env` ou `config/discord_webhooks.local.yaml` dans l'image.

## Sauvegardes

Sauvegarde regulierement :

- `data/football_predictor.db` ou la DB configuree ;
- `data/raw/api_football/` pour les snapshots bruts ;
- `data/processed/` pour datasets et backtests ;
- `data/models/` pour artefacts modeles ;
- les configs locales non commitees.

## Reset DB Local

Pour reconstruire une DB locale sans toucher aux referentiels :

```bash
mv data/football_predictor.db data/football_predictor.db.bak
football-predictor init-db
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json
```

Ne supprime pas les snapshots ou modeles sans sauvegarde si tu veux conserver l'historique.

## Refresh Des Referentiels `docs/`

Les referentiels `docs/api_football_*` ne sont pas regeneres par les commandes quotidiennes. Un
refresh de ces fichiers doit etre un workflow manuel explicite, relu, puis valide par tests.

Le cache joueurs economise les appels `/players/squads` lors d'une reprise technique, mais la source
metier principale reste `docs/api_football_players_reference.json`.

## Runbooks

- `doctor` signale un JSON absent ou invalide : restaure le fichier depuis la copie de reference
  avant toute ingestion live.
- API-Football rate limit ou timeout : relance plus tard, conserve les snapshots existants, ne
  contourne pas le client central.
- Odds ou lineups absentes : la prediction doit continuer avec qualite de donnees plus faible.
- Discord 401/403/404 : regenere le webhook ou corrige la route, sans logger l'URL complete.
- DB corrompue en local : restaure une sauvegarde ou cree une DB neuve puis relance le seed docs.

## Limites V1

- Pas de serveur web ; orchestration via CLI, cron ou Docker.
- Les predictions dependent fortement de la couverture des snapshots locaux.
- Les lineups officielles peuvent arriver seulement 20 a 40 minutes avant kickoff.
- Les modeles doivent etre reevalues par backtest avant usage operationnel confiant.
