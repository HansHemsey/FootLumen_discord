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

## Checklist Quotidienne

```bash
scripts/football_predictor_cli.sh doctor --strict
scripts/football_predictor_cli.sh data-quality
scripts/smoke_test_local.sh
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
ajouter `--production-mode` pour autoriser le chemin production.

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

La V3 est activee en production malgre un backtest non valide. Surveiller les premiers
runs reels, la calibration des probabilites et la couverture odds/API/lineups issue du
refresh live M-30. Pour verifier le rendu Discord V3 sans publier :

Règle de publication publique : V3 1X2 publie selon ses seuils de confiance dédiés.
O/U 2.5 utilise une policy séparée : public uniquement avec une décision
`ou_decision_version="ou_v2"`, un vrai `value_side`, `edge_pick >= 0.03`,
`ev_pick >= 0.03`, `confidence_score_v2 >= 65`, data quality suffisante et au moins deux
bookmakers. `bookmaker_count` absent vaut `0`. Les sorties legacy O/U, les forecasts sans
pick value et les décisions non publiques sont envoyés en staff ou marqués `no_bet`.

Les messages V3 1X2 et O/U 2.5 utilisent un rendu compact oriente parieur : pick,
probabilites modele/marche, ecart de value, facteurs traduits et qualite data. Ce rendu
ne modifie pas les modeles, les crons, le routage ni le filtre de publication.

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
Il est remplace par `week_key` : une relance dans la même semaine met a jour le message
de cette semaine, mais ne supprime pas les autres semaines. Le lundi, `daily_morning.sh`
publie aussi une finalisation de la semaine précédente pour inclure les matchs du dimanche
dont les scores ont ete rafraîchis pendant la nuit.

```bash
# A lancer toutes les 15 minutes si tu veux capter la fenetre H-6 -> H-5h15.
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh

# A lancer toutes les 30-60 minutes apres les matchs.
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
```

`publish_match_analyses.sh` appelle `publish-match-analyses` et utilise strictement
`prediction_time = fixture.date - 6h`. La marge d'envoi est `ANALYSIS_GRACE_MINUTES=45`
par defaut pour absorber les retards cron/flock. Le message contient le contexte, la forme
recente, le classement, les odds, les absences/XI si disponibles, les points forts/faibles
et une conclusion prudente. Les summaries H-6 sont horodates et les messages persistés
incluent `analysis_prediction_time`, `analysis_current_time`, `analysis_deadline`,
`analysis_grace_minutes` et `source=publish_match_analyses` pour l'audit.
Une analyse trop pauvre est ignorée avec `reason=insufficient_analysis_data` afin d'éviter
les messages génériques remplis de champs non disponibles.
Diagnostic rapide VPS si une analyse manque :

```bash
sqlite3 -header -column data/football_predictor.db "
with now_utc(value) as (select datetime('now'))
select f.fixture_id, f.home_team || ' vs ' || f.away_team as match,
       f.date as kickoff_utc, datetime(f.date, '-6 hours') as analysis_time,
       datetime(f.date, '-315 minutes') as deadline,
       now_utc.value as current_time,
       count(o.id) as odds_before_h6
from fixtures f, now_utc
left join odds_snapshots o
  on o.fixture_id = f.fixture_id
 and o.bet_id = 1
 and o.is_live = 0
 and o.fetched_at <= datetime(f.date, '-6 hours')
where f.status_short in ('NS', 'TBD', '')
  and date(f.date) = date('now')
group by f.fixture_id
order by f.date;"

sqlite3 -header -column data/football_predictor.db "
select dm.id, dm.fixture_id, dm.status, dm.created_at,
       json_extract(dm.payload_json, '$.analysis_prediction_time') as prediction_time,
       json_extract(dm.payload_json, '$.analysis_deadline') as deadline,
       json_extract(dm.payload_json, '$.analysis_grace_minutes') as grace
from discord_messages dm
where dm.message_type = 'analysis'
order by dm.created_at desc
limit 20;"
```
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
la meme passe, ajoute `RESOLVE_UNKNOWN_PLAYERS=true`, ou lance la resolution separement

### Entrainement Et Backtest Multi-Saisons

```bash
scripts/train_backtest_all.sh
scripts/train_backtest_ou.sh
```

Ces deux scripts utilisent `config/competitions_history.yaml` par defaut. Le premier
entraine/backteste le modele 1X2 `data/models/v2-late`; le second entraine/backteste le
modele Over/Under `data/models/ou-v1`. Les scripts quotidiens continuent d'utiliser
`config/competitions.yaml`, donc l'historique ne ralentit pas la production.
avec les refresh desactives si tu veux economiser le quota.

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

Exemple local sans refresh, uniquement pour test manuel :

```cron
15 7 * * * cd /path/to/footlumen && . .venv/bin/activate && football-predictor doctor --strict
30 8 * * * cd /path/to/footlumen && . .venv/bin/activate && scripts/run_predict_today.sh
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

### Mode temporaire Coupe du Monde only

Pendant la treve des championnats, utilise `config/prod_worldcup.crontab` sur le VPS pour
concentrer les appels API et les publications sur `fifa_world_cup_2026` uniquement.
La procedure detaillee est disponible dans `docs/worldcup_only_vps_mode.md`.

Installation :

```bash
cd /opt/football-predictor/app
crontab config/prod_worldcup.crontab
crontab -l
```

Ce profil utilise `config/competitions_worldcup.yaml` et des verrous `flock`. Il desactive les
routines championnats V3, O/U et analyses H-6 domestic. Les routines actives sont :

```cron
15 5 * * 1         scripts/weekly_ingestion.sh avec CONFIG=config/competitions_worldcup.yaml
50 5 * * *         scripts/refresh_all_leagues.sh fixtures + standings CDM
30 6 * * *         scripts/daily_morning.sh avec CONFIG=config/competitions_worldcup.yaml
5 23 * * *         scripts/publish_daily_discord.sh avec DATE=demain Europe/Paris
40 4 * * 1,4       football-predictor ingest-player-squads --config config/competitions_worldcup.yaml
45 3 * * *         scripts/refresh_all_leagues.sh details CDM J-3 termines
*/10 * * * *       football-predictor worldcup-run-daily --window late --refresh-data
*/10 * * * *       worldcup-combos-run/lock/publish, staff-only via config
35 * * * *         scripts/settle_worldcup_combos.py --execute
20,50 * * * *      scripts/publish_match_results.sh avec CONFIG=config/competitions_worldcup.yaml
25,55 0-3 * * *    scripts/publish_match_results.sh avec DATE=hier Europe/Paris
10 2,6,8,12,18 * * * scripts/publish_weekly_score.sh
55 23 * * *        scripts/publish_weekly_score.sh
```

Les horaires Discord sont affiches en `Europe/Paris`. La prediction CDM `late`
fonctionne en fenetre glissante `now -> now+30min`, ce qui couvre les coups d'envoi
apres minuit. Auditer les horaires disponibles avec :

```bash
PYTHONPATH=src .venv/bin/python scripts/audit_worldcup_fixture_times.py
```

Validation avant activation :

```bash
football-predictor doctor --strict
football-predictor worldcup-audit-reference
PYTHONPATH=src .venv/bin/python scripts/audit_worldcup_fixture_times.py
football-predictor worldcup-build-dataset --output data/processed/worldcup_1x2_training.parquet
football-predictor worldcup-train-1x2 --dataset data/processed/worldcup_1x2_training.parquet --output-dir data/models/worldcup-1x2
football-predictor worldcup-optimize-blend --dataset data/processed/worldcup_1x2_training.parquet --model-dir data/models/worldcup-1x2 --output-dir reports/worldcup_blend --write-best-config
football-predictor worldcup-run-daily --window late --refresh-data --save-raw --dry-run
```

### Enrichissement data CDM point-in-time

Avant d'activer une publication publique CDM plus ambitieuse, initialiser les sources datées
dans cet ordre. Toutes les commandes sont dry-run sauf si `--write` est présent :

```bash
alembic upgrade head
PYTHONPATH=src .venv/bin/python scripts/ingest_national_results.py --write
PYTHONPATH=src .venv/bin/python scripts/compute_national_elo.py --write
PYTHONPATH=src .venv/bin/python scripts/ingest_fifa_rankings.py --snapshot-date YYYY-MM-DD --write
PYTHONPATH=src .venv/bin/python scripts/build_group_incentive_features.py --write
PYTHONPATH=src .venv/bin/python scripts/build_squad_strength_features.py --write
PYTHONPATH=src .venv/bin/python scripts/build_worldcup_feature_matrix.py --write
PYTHONPATH=src .venv/bin/python scripts/worldcup_coverage_report.py --write --league-id 1 --season 2026
```

Les odds CDM multi-marchés nécessitent une autorisation API explicite :

```bash
PYTHONPATH=src .venv/bin/python scripts/sync_worldcup_odds_snapshots.py --write --refresh-api --markets 1x2,ou25,btts
```

Ne jamais importer un ranking FIFA/Elo sans date de snapshot. En cas de doute, laisser la
source manquante : la coverage matrix baissera la qualité plutôt que d'introduire une fuite
temporelle.

Retour championnats en aout 2026 :

1. creer une vraie config locale depuis `config/competitions_2026.example.yaml` ;
2. relancer l'ingestion teams, fixtures, standings, squads, odds et details recents ;
3. reinstalller le crontab championnats avec `crontab config/prod.crontab` ou une version VPS
   equivalente ;
4. laisser `WORLD_CUP_1X2_ENABLED=false` sauf si la routine CDM doit rester active.

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
