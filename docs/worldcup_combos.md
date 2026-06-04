# Combinés CDM 2026

## Objectif

Cette feature prépare un socle indépendant pour de futurs tickets combinés Coupe du Monde
2026. Le sprint 1 ajoute uniquement la configuration, les objets métier et la persistance.

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

## Non Branché Dans Ce Sprint

- pas de commande CLI ;
- pas de cron ;
- pas de publication Discord ;
- pas de modification des channels Discord ;
- pas de construction automatique de tickets ;
- pas de settlement.

Les prochains sprints pourront brancher la lecture des prédictions existantes, la décision,
puis la publication, en gardant ce socle inactif par défaut.
