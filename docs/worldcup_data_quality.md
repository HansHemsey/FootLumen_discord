# Qualité Des Données CDM 2026

La couche de monitoring CDM 2026 mesure la couverture réellement disponible en base locale.
Elle ne déclenche aucun appel API par défaut et ne remplace pas les règles point-in-time des
prédictions.

## Sources Suivies

- `fixtures`
- `standings`
- `odds_1x2`
- `odds_ou`
- `odds_btts`
- `predictions`
- `lineups`
- `injuries`
- `fixture_statistics`
- `events`
- `player_statistics`

Les observations optionnelles sont stockées dans `api_coverage_observations` avec le endpoint,
la fixture ou équipe concernée, le timestamp de contrôle, le statut, le nombre de résultats et
un flag `useful_payload_flag`.

## Feature Matrix

Chaque fixture CDM peut produire une matrice de qualité :

- historique international ;
- Elo ;
- classement FIFA ;
- odds 1X2 ;
- odds O/U ;
- odds BTTS ;
- prédiction API-Football ;
- lineups ;
- blessures ;
- état de groupe ;
- force d'effectif ;
- `data_quality_score`.

Les lineups ne sont pénalisantes fortement que lorsqu'elles sont attendues, typiquement à moins
de 90 minutes du kickoff ou si le match n'est plus en statut pre-match.

## Impact Production

Le score de couverture CDM est ajouté à `data_quality_json` sous :

- `worldcup_fixture_quality_score`
- `worldcup_fixture_quality`

Les prédictions World Cup peuvent plafonner la confiance si une source critique manque. Une
qualité trop basse route la publication en staff plutôt qu'en public.

Les combinés CDM lisent aussi ces warnings depuis les prédictions persistées afin d'éviter de
construire un ticket public sur une fixture dont la couverture s'est dégradée.

## Commande

Dry-run par défaut :

```bash
PYTHONPATH=src .venv/bin/python scripts/worldcup_coverage_report.py
```

Persist observations et écrit les rapports :

```bash
PYTHONPATH=src .venv/bin/python scripts/worldcup_coverage_report.py --write --league-id 1 --season 2026
```

Rapports générés :

- `reports/worldcup_2026/data_coverage_summary.json`
- `reports/worldcup_2026/data_coverage_report.md`

Les warnings sont sanitizés avant écriture afin d'éviter l'exposition de clés API ou webhooks.

## Enrichissement Point-In-Time

Les sources statiques utiles à la précision CDM sont maintenant persistées sous forme de
snapshots datés :

- `national_team_matches` pour l'historique international ;
- `national_elo_snapshots` pour les Elo calculés ou importés ;
- `fifa_ranking_snapshots` pour les rankings FIFA ;
- `worldcup_group_state_snapshots` pour les enjeux de groupe ;
- `squad_strength_features` pour la force d'effectif.

Commandes dry-run :

```bash
PYTHONPATH=src .venv/bin/python scripts/ingest_national_results.py
PYTHONPATH=src .venv/bin/python scripts/compute_national_elo.py
PYTHONPATH=src .venv/bin/python scripts/ingest_fifa_rankings.py --snapshot-date 2026-05-01
PYTHONPATH=src .venv/bin/python scripts/build_group_incentive_features.py
PYTHONPATH=src .venv/bin/python scripts/build_squad_strength_features.py
PYTHONPATH=src .venv/bin/python scripts/build_worldcup_feature_matrix.py
PYTHONPATH=src .venv/bin/python scripts/sync_worldcup_odds_snapshots.py
```

Écriture explicite :

```bash
PYTHONPATH=src .venv/bin/python scripts/ingest_national_results.py --write
PYTHONPATH=src .venv/bin/python scripts/compute_national_elo.py --write
PYTHONPATH=src .venv/bin/python scripts/ingest_fifa_rankings.py --snapshot-date 2026-05-01 --write
PYTHONPATH=src .venv/bin/python scripts/build_group_incentive_features.py --write
PYTHONPATH=src .venv/bin/python scripts/build_squad_strength_features.py --write
PYTHONPATH=src .venv/bin/python scripts/build_worldcup_feature_matrix.py --write
```

La synchronisation des odds appelle API-Football uniquement avec deux options explicites :

```bash
PYTHONPATH=src .venv/bin/python scripts/sync_worldcup_odds_snapshots.py --write --refresh-api
```

Chaque commande applique `cutoff <= prediction_time` ou exige une date de snapshot. Un ranking
FIFA sans date explicite est refusé pour éviter d'utiliser une information courante dans une
simulation passée.
