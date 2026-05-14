# Architecture

## Vue D'Ensemble

Architecture cible :

```text
docs/*.json
  -> src/football_predictor/reference/
  -> seed DB local optionnel
  -> ingestion API-Football explicite
  -> stockage snapshots bruts
  -> construction features point-in-time
  -> modèles, stacking, calibration
  -> prédiction 1X2
  -> CLI et Discord
```

Le projet suit un layout `src/` :

```text
src/football_predictor/
├── cli.py
├── api/
├── backtesting/
├── config/
├── db/
├── discord/
├── features/
├── ingestion/
├── modeling/
├── prediction/
├── reference/
└── utils/
```

## Flux Cible

1. `reference/` lit les JSON locaux sous `docs/` et valide les IDs.
2. `seed DB` charge leagues, teams, venues, fixtures, players, squads, bookmakers et bets
   sans appel réseau.
3. `api/` appelle API-Football v3 seulement si un refresh explicite est demandé.
4. `db/` stocke entités et snapshots bruts avec horodatage.
5. `features/` construit les features à partir des données disponibles à `prediction_time`.
6. `modeling/` calcule les probabilités sportives, marché et API.
7. `prediction/` applique les fallbacks, le stacking, la confiance et les explications.
8. `discord/` formate et envoie le résultat via webhook.

## Modules

### `src/football_predictor/reference/`

Module obligatoire pour charger et interroger :

- `docs/api_football_reference.json` ;
- `docs/api_football_players_reference.json`.

Fonctions attendues :

- charger les référentiels locaux ;
- trouver une ligue, une équipe, une fixture, un bookmaker ou un bet ;
- trouver un joueur ou les joueurs d'une équipe ;
- valider qu'un ID existe ;
- ne jamais appeler l'API live ;
- retourner des erreurs explicites si un ID est absent.

Ce module est la première défense contre les IDs inventés.

### `config/`

Charge les settings :

- base URL API-Football ;
- chemin des référentiels docs ;
- `DATABASE_URL` ;
- timezone ;
- webhook Discord ;
- clé API depuis variable d'environnement.

Les secrets ne doivent jamais être affichés en clair.

### `api/`

Client API-Football centralisé :

- GET only ;
- header `x-apisports-key` depuis l'environnement ;
- timeout et retry raisonnables ;
- gestion des erreurs API ;
- payloads snapshotables sans secret.

### `db/`

Base SQLite au départ, compatible PostgreSQL ensuite.

Tables principales :

- `RawApiSnapshot` ;
- `League`, `Team`, `Venue`, `Fixture` ;
- `StandingSnapshot` ;
- `FixtureStatistics`, `FixtureEvent`, `FixtureLineup`, `FixturePlayerStats` ;
- `Player`, `PlayerSquad` ;
- `Injury`, `OddsSnapshot`, `ApiPredictionSnapshot` ;
- `FeatureSnapshot`, `ModelPrediction`, `DiscordMessage`.

Les ingestions doivent être idempotentes et conserver les snapshots temporels.

`football-predictor init-db` reste disponible pour créer rapidement les tables en local via
`Base.metadata.create_all()`. Pour une base durable ou partagée, le chemin recommandé est
Alembic :

```bash
alembic upgrade head
```

La première migration crée le schéma initial à partir des métadonnées SQLAlchemy. Les futures
évolutions de schéma devront être ajoutées comme migrations explicites, sans supprimer ni
recréer automatiquement une base existante.

### `ingestion/`

Responsabilités :

- seed local depuis les JSON docs sans réseau ;
- ingestion live explicite des référentiels API-Football (`leagues`, `teams`,
  `players/squads`, `odds/bookmakers`, `odds/bets`), des fixtures, standings et détails
  de match ;
- ingestion détaillée par fixture ou batch pour `fixtures/statistics`, `fixtures/events`,
  `fixtures/lineups`, `fixtures/players`, `injuries` et `predictions` ;
- ingestion `/odds` prematch par fixture, date ou ligue/saison, avec pagination et
  snapshots multiples pour mesurer le mouvement des cotes ;
- stockage de payloads bruts ;
- tolérance aux champs manquants ;
- logs compréhensibles sans secret.

Les commandes live refusent tout appel réseau sans option explicite `--refresh-api` ou
`--refresh-live`. Chaque réponse live est insérée en `RawApiSnapshot` avant normalisation.
La commande `seed-reference-from-docs` reste le chemin sans réseau et sans quota API.
La commande agrégée `ingest-reference` peut d'abord charger les docs (`--prefer-docs`) puis,
si demandé, rafraîchir leagues, teams et squads en live (`--refresh-live`).
`ingest-fixtures --prefer-docs` peut charger les fixtures et standings du référentiel local
en les marquant `ingestion_source=docs/reference`; les ingestions live insèrent aussi un
`RawApiSnapshot`.

`ingest-fixture-details` nécessite des fixtures déjà présentes en DB et un `--refresh-api`
explicite. La commande accepte une fixture unique ou un lot filtré par ligue/saison, date
ou statut; `--include-upcoming` permet d'inclure les fixtures non terminées dans un lot. Les
détails live sont toujours horodatés avec `fetched_at`; les endpoints optionnels vides ou
non couverts sont reportés dans le résumé sans arrêter tout le batch.
Les joueurs présents dans lineups, injuries, events ou player stats sont upsertés seulement
si l'API fournit un `player.id`; si l'ID n'existe pas dans le référentiel joueurs local, il
est conservé comme donnée live inconnue sans inventer son identité.

`ingest-odds` conserve uniquement les odds prematch 1X2 dans la V1. Le marché cible est
résolu via le référentiel local (`Match Winner` par défaut), jamais par supposition. Les
probabilités marché utilisent les derniers snapshots par bookmaker avec
`fetched_at <= prediction_time`. La commande locale `odds-features` lit ces snapshots sans
appel réseau pour calculer consensus sans marge, confiance marché, dispersion et mouvement
des cotes.

### `features/`

Construit les features :

- forme équipe ;
- domicile/extérieur ;
- standings ;
- calendrier et repos ;
- statistiques de match ;
- joueurs, XI, absences ;
- odds ;
- prédiction API-Football ;
- qualité des données.

Chaque builder doit respecter `fixture_id` et `prediction_time`.

### `modeling/`

Contient :

- baselines odds-only, API prediction, Poisson ;
- modèle sportif multiclass ;
- stacking ;
- calibration ;
- sauvegarde et chargement de modèles.

### `backtesting/`

Construit des datasets historiques point-in-time et produit les métriques de validation.

### `prediction/`

Orchestre une prédiction fixture unique :

- récupère la fixture ;
- charge ou refresh les données si demandé ;
- construit le snapshot de features ;
- calcule les probabilités ;
- applique le stacking ;
- calcule confiance et explications ;
- sauvegarde la prédiction.

`run_daily.py` et `scheduler.py` orchestrent les prédictions du jour sans serveur web. La
CLI `predict-today` sélectionne les fixtures futures d'une date en timezone applicative,
calcule un `prediction_time` par fixture (`early = fixture.date - 24h`,
`mid = fixture.date - 6h`, `late = heure courante pour les matchs qui commencent dans les
30 prochaines minutes`, `now = heure courante`), valide les ligues via le référentiel local,
rafraîchit l'API uniquement avec `--refresh-data`, continue fixture par fixture en cas
d'erreur, puis produit un résumé JSON. Le backtest production-like est le flux qui simule
strictement `prediction_time = fixture.date - 30 minutes` pour les fixtures historiques.
L'envoi Discord est optionnel et dédupliqué par `fixture_id + model_version + window` pour
les prédictions 1X2, avec une clé sémantique O/U dédiée.

### `discord/`

Produit le bloc markdown français, route les messages vers le bon channel Discord par
compétition et envoie via webhook sans exposer l'URL complète.

Sous-modules :

- `formatter.py` : rendu markdown français limité pour Discord ;
- `config.py` : chargement des YAML channels/webhooks, sans secret en clair dans les
  fichiers example ;
- `router.py` : résolution `message_type -> channel_key` puis compétition/channel/webhook ;
- `webhook.py` : client `httpx` avec `allowed_mentions={"parse":[]}` ;
- `provisioning.py` : création optionnelle de webhooks via bot token ;
- `service.py` : dry-run, print-only, déduplication et persistance `DiscordMessage`.

Les messages prédictifs V3 et O/U sont reliés à leur source par
`DiscordMessage.v3_model_prediction_id` ou `DiscordMessage.ou_model_prediction_id`, avec
fallback historique via `payload_json`. Les messages O/U peuvent porter
`dedupe_key="ou25:{fixture_id}:{window}:{model_version}:ou_prediction"` afin d'éviter un
second envoi réel si le rendu markdown change.

### `utils/`

Fonctions partagées : dates, secrets, logging, exceptions, diagnostics.

## Usage Des JSON `docs/`

Les JSON de référence servent à :

- éviter d'inventer des IDs ;
- seed la base locale sans quota API ;
- créer des fixtures de tests réalistes ;
- valider les mappings métier ;
- relier les données dynamiques à des entités connues.

Les fichiers Markdown de référence servent à comprendre et documenter. Ils ne doivent pas
être parsés par le code applicatif si un JSON structuré existe.

`docs/api_football_players_cache.json` est un cache technique ; il ne doit être utilisé que
pour reprendre ou optimiser une collecte de squads.
