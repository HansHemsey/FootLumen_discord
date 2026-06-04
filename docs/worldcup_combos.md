# Combinés CDM 2026

## Objectif

Cette feature prépare un socle indépendant pour de futurs tickets combinés Coupe du Monde
2026.

Le sprint 1 ajoute la configuration, les objets métier et la persistance.
Le sprint 2 ajoute la lecture des fixtures CDM 2026, la création de sessions horaires et
la sélection de legs candidats à partir des prédictions déjà persistées.
Le sprint 3 ajoute la construction de tickets candidats, le scoring combiné, les pénalités
de risque et la décision `PUBLIC_PUBLISHED` / `STAFF_ONLY` / `NO_BET`.
Le sprint 4 ajoute refresh policy, revalidation pre-lock, lock final, formatage Discord,
publication contrôlée et settlement.
Le passage production ajoute une orchestration contrôlée `generate -> lock -> publish -> settle`
sans activer de cron par défaut.

La feature ne modifie pas les prédictions 1X2, V3 ou O/U existantes.

## Feature Flag

La configuration dédiée est `config/worldcup_combos.yaml`.

Par défaut :

```yaml
enabled: false
```

Le chemin peut être surchargé avec :

```env
WORLD_CUP_COMBOS_CONFIG_PATH=config/worldcup_combos.yaml
WORLD_CUP_COMBOS_ENABLED=false
```

## Tables Ajoutées

- `combo_tickets`
- `combo_ticket_legs`
- `combo_ticket_snapshots`

Les tables contiennent `created_at`, `updated_at`, `model_versions_json` et `warnings_json`.
Les snapshots JSON sont conservés pour permettre l'audit sans multiplier les migrations.

## Sprint 2

Services ajoutés :

- `worldcup_combo_sessions.py` : groupe les fixtures CDM 2026 par date Europe/Paris et
  fenêtres horaires.
- `adapters.py` : lit les fixtures, prédictions 1X2, décisions O/U V2, odds et lineups
  déjà stockées.
- `worldcup_combo_leg_selector.py` : filtre les legs candidats selon EV, edge, qualité
  data, confiance, statut fixture et fraîcheur.
- `scripts/dry_run_worldcup_combo_candidates.py` : affiche sessions, candidats et raisons
  d'exclusion sans écrire en DB.

Règles point-in-time :

- prédictions avec `prediction_time <= lock_time` uniquement ;
- odds avec `fetched_at <= lock_time` uniquement ;
- lineups avec `fetched_at <= lock_time` uniquement.

## Sprint 3

Services ajoutés :

- `worldcup_combo_builder.py` : construit au plus un ticket 2 legs safe et un ticket
  3 legs staff-only par session.
- `worldcup_combo_scoring.py` : calcule cotes combinées, probabilités, EV brute/ajustée,
  risques, fraîcheur et confiance combinée.
- `worldcup_combo_publication_policy.py` : applique la policy public/staff/no-bet sans
  envoyer de message Discord.
- `scripts/dry_run_worldcup_combo_builder.py` : affiche les meilleurs tickets par session
  sans écrire en DB ni publier.

Les snapshots de cycle supportés sont :

- `generated`
- `scored`
- `policy_decided`
- `pre_lock`
- `settled`

## Sprint 4

Services ajoutés :

- `worldcup_combo_refresh_policy.py` : décide si odds, prédictions ou lineups sont trop
  anciennes selon la proximité du kickoff.
- `worldcup_combo_lock_service.py` : revalide un ticket avant lock, recalcule scoring/policy,
  crée le snapshot `pre_lock`, puis passe `LOCKED`, `STAFF_ONLY` ou `NO_BET`.
- `worldcup_combo_formatter.py` : formate watchlist staff, ticket verrouillé staff et no bet.
- `worldcup_combo_publication_service.py` : publie uniquement dans le channel staff,
  avec idempotence par `ticket_key`.
- `worldcup_combo_settlement.py` : calcule `WON`, `LOST`, `VOID`, `PARTIAL_VOID` et
  `profit_unit` après résultats.

Règles staff/no bet :

- toutes les publications Discord partent vers `predictions_staff` ;
- un ticket théoriquement publiable reste staff-only pendant la CDM ;
- no bet si EV ajustée non positive, market scope inconnu, data insuffisante ou warning
  critique ;
- aucun message ne promet un gain ou une certitude.

## Commandes Contrôlées

Le fichier prod `config/worldcup_combos.yaml` est activé, mais staff-only.

Dry-run :

```bash
football-predictor worldcup-combos-run --dry-run
football-predictor worldcup-combos-publish --dry-run
PYTHONPATH=src .venv/bin/python scripts/dry_run_worldcup_combo_candidates.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/dry_run_worldcup_combo_builder.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/dry_run_worldcup_combo_publish.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/run_worldcup_combos.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/publish_worldcup_combos.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/lock_worldcup_combos.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/settle_worldcup_combos.py --config config/worldcup_combos.yaml
```

Execution explicite :

```bash
football-predictor worldcup-combos-run --execute
football-predictor worldcup-combos-publish --execute
PYTHONPATH=src .venv/bin/python scripts/run_worldcup_combos.py --config config/worldcup_combos.yaml --execute
PYTHONPATH=src .venv/bin/python scripts/publish_worldcup_combos.py --config config/worldcup_combos.yaml --execute
PYTHONPATH=src .venv/bin/python scripts/lock_worldcup_combos.py --config config/worldcup_combos.yaml --execute
PYTHONPATH=src .venv/bin/python scripts/settle_worldcup_combos.py --config config/worldcup_combos.yaml --execute
```

`worldcup-combos-run` génère et persiste les tickets, mais ne publie aucun message Discord.
`worldcup-combos-publish` publie uniquement des tickets déjà persistés, avec dry-run par défaut.

## Passage Production VPS

Avant toute activation :

```bash
alembic upgrade head
football-predictor worldcup-combos-run --dry-run
football-predictor worldcup-combos-publish --dry-run
```

Configuration de production :

```yaml
enabled: true
staff_only_shadow_mode: true
allow_public_matchday3: false
allow_public_knockout: false
```

Les cron combinés de `config/prod_worldcup.crontab` sont actifs. Ils génèrent, verrouillent,
publient en staff et settlent les tickets. Aucun channel public n'est nécessaire : la route
réelle à vérifier côté VPS est `predictions_staff`.

La feature reste CDM 2026 uniquement : `competition_key=fifa_world_cup_2026`,
`league_id=1`, `season=2026`.
