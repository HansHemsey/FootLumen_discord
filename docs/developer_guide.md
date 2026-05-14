# Developer Guide

Ce guide resume le flux de developpement pour VSCode, Codex et les contributions manuelles.

## Lecture Obligatoire

Avant toute modification importante :

1. Lire `AGENTS.md`.
2. Lire `blueprint.md`.
3. Lire les docs pertinentes dans `docs/`.
4. Verifier les IDs via les JSON de reference si un test, exemple ou mapping en utilise.

Les fichiers JSON sous `docs/` sont les sources machine-readable. Les fichiers Markdown associes
servent a la lecture humaine. Ne modifie pas les cinq referentiels sauf demande explicite de
regeneration.

## Architecture Et Modules

Le projet suit un layout `src/football_predictor/` :

- `api/` : client API-Football, erreurs, pagination et snapshots bruts.
- `config/` : settings, chemins et competitions suivies.
- `db/` : modeles SQLAlchemy, sessions, init DB et repositories.
- `reference/` : loaders/lookups locaux pour `docs/*.json`, sans appel API.
- `ingestion/` : seed docs, fixtures, standings, details match, odds et squads.
- `features/` : features equipe, joueurs, XI, odds, contexte et qualite.
- `modeling/` : baselines, Poisson, modele multiclass, stacking, calibration, training.
- `backtesting/` : dataset historique, metriques et rapports.
- `prediction/` : prediction fixture unique et automatisation quotidienne.
- `discord/` : formatter, router, webhooks et provisioning optionnel.
- `utils/` : secrets, logging, dates et diagnostics.

La CLI doit rester une couche d'orchestration mince.

## Hierarchie Des Sources De Verite

Pour competitions, equipes, fixtures, venues, bookmakers et bets :

1. `docs/api_football_reference.json` ;
2. `docs/api_football_reference.md` pour la lecture humaine ;
3. DB locale ;
4. API live seulement si refresh explicite.

Pour joueurs et effectifs :

1. `docs/api_football_players_reference.json` ;
2. `docs/api_football_players_reference.md` ;
3. DB locale ;
4. `docs/api_football_players_cache.json` uniquement pour reprise technique ;
5. API live seulement si refresh explicite.

## Module `reference/`

Utilise `reference/` pour charger et valider :

- `find_league_by_id` ;
- `find_team_by_id` / `find_team_by_name` ;
- `find_player_by_id` / `find_players_by_team` ;
- `find_bookmaker_by_id` ;
- `find_bet_by_id` ;
- `validate_fixture_reference`.

Ces fonctions lisent uniquement les fichiers locaux et ne doivent jamais appeler API-Football.

## Environnement VSCode/Codex

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
scripts/init_local.sh
```

Dans VSCode, utilise l'interpreteur `.venv/bin/python`. Les commandes de travail principales sont :

```bash
make test
make lint
make typecheck
make check
make smoke
```

`make smoke` doit rester sans reseau. Les commandes live doivent etre opt-in.

## Regles Anti Data Leakage

Toute feature dynamique doit respecter `fixture_id` et `prediction_time`.

- Exclure la fixture cible des historiques.
- Utiliser uniquement `Fixture.date < prediction_time`.
- Utiliser uniquement odds, blessures, standings, lineups et player stats avec timestamp
  disponible avant `prediction_time`.
- Ne jamais injecter `target`, score final ou statut post-match dans les features.
- Ajouter ou maintenir un test anti-fuite pour tout changement de features.

## Tests Et Fixtures

```bash
pytest
ruff check .
mypy src
```

Les tests unitaires ne doivent jamais faire d'appel reseau. Utilise :

- `httpx.MockTransport` pour API-Football ou Discord ;
- SQLite temporaire ;
- payloads sous `tests/fixtures/` ;
- IDs issus de `docs/api_football_reference.json` ou `docs/api_football_players_reference.json` ;
- IDs negatifs uniquement pour les cas synthetiques clairement marques.

Ne hardcode pas un ID positif absent des referentiels.

## Ajout De Fonctionnalite

- Garde la logique metier hors CLI quand c'est possible.
- Stocke les payloads bruts utiles pour audit.
- Continue quand une source optionnelle manque, avec flags de qualite.
- Masque tous les secrets dans logs, exceptions, snapshots et docs.
- Mets a jour `docs/data_contract.md` si une nouvelle feature ou structure de donnees apparait.
- Mets a jour `README.md`, `docs/operations_guide.md`, `docs/modeling_strategy.md`,
  `docs/data_contract.md` et `.env.example` si une commande, variable d'environnement,
  format de rapport ou workflow production change.

## Ajout De Nouvelles Features

- Exposer une API Python testable.
- Retourner des dictionnaires plats JSON-serializables.
- Prefixer clairement `home_team_*`, `away_team_*`, `p_market_*`, `api_pred_*`.
- Ajouter des `data_quality` flags.
- Filtrer toutes les tables dynamiques avec `prediction_time`.
- Ajouter un test anti-fuite.

## Ajout De Nouveaux Modeles

- Exclure `target`, scores finaux, dates, IDs naifs et JSON bruts de `X`.
- Retourner les classes fixes `HOME`, `DRAW`, `AWAY`.
- Normaliser les probabilites.
- Sauvegarder artefacts et metadata dans `data/models/`.
- Comparer au minimum odds-only, Poisson et API-only dans les backtests.
- Pour un modèle publié en production, fournir un rapport `published-only` et un
  `confidence_thresholds.json` approuvé ; shadow/dry-run restent autorisés sans approbation.

## Smoke Et Validation Finale

Avant de considerer un sprint termine :

```bash
make smoke
make check
```

Pour un changement touchant V3, O/U, publication ou backtesting production-like, ajouter les
tests ciblés pertinents, par exemple :

```bash
pytest tests/test_model_approval.py tests/test_production_like_backtest.py
```

Controle aussi :

- aucun secret dans le diff ;
- aucun ID API-Football invente ;
- les cinq fichiers `docs/api_football_*` sont toujours presents ;
- les changements de documentation ne recommandent pas d'appel live implicite.
