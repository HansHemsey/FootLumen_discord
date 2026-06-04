# Combinés CDM 2026

## Objectif

Cette feature prépare un socle indépendant pour de futurs tickets combinés Coupe du Monde
2026.

Le sprint 1 ajoute la configuration, les objets métier et la persistance.
Le sprint 2 ajoute la lecture des fixtures CDM 2026, la création de sessions horaires et
la sélection de legs candidats à partir des prédictions déjà persistées.

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

## Non Branché Dans Ce Sprint

- pas de commande CLI ;
- pas de cron ;
- pas de publication Discord ;
- pas de modification des channels Discord ;
- pas de construction automatique de tickets ;
- pas de settlement.

Les prochains sprints pourront construire les tickets, appliquer la décision de publication
puis brancher Discord, en gardant ce socle inactif par défaut.
