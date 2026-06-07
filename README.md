# FootLumen

FootLumen est une plateforme Python de prédiction football construite autour
d'API-Football. Elle estime des probabilités de match, automatise les publications Discord
et fournit un mode dédié Coupe du Monde 2026.

Tagline : **Éclaire le match par la data.**

Le projet travaille avec des sorties probabilistes, pas avec des certitudes :

- `1X2` : victoire domicile, match nul, victoire extérieur ;
- `O/U 2.5` : value betting Over/Under avec une décision de publication dédiée ;
- confiance, explications, qualité des données et raisons de non-publication ;
- messages Discord courts, lisibles et sans promesse de gain.

L'identité visuelle FootLumen est disponible dans `footlumen_identity_pack/` :
logos SVG/PNG, favicon, icône d'app, bannière Discord et mini-charte.

## Ce Que Fait Le Projet

- Prédictions `1X2` avec modèles historiques, features sportives, odds, signaux API et
  garde-fous de publication.
- Modèle `O/U V2` orienté value betting : edge, EV, confiance, bookmaker count, backtests
  et règles public/staff.
- Mode Coupe du Monde 2026 :
  - groupes A-L ;
  - calendrier et matchs du jour enrichis avec le groupe ;
  - classements de groupes et format de qualification ;
  - contexte d'enjeu avec simulation des points et rangs post-match ;
  - crons adaptés aux coups d'envoi de nuit en heure de Paris.
- Combinés CDM 2026 :
  - tickets courts, staff/shadow par défaut ;
  - revalidation pre-lock ;
  - lock, publication contrôlée, no bet et settlement.
- Rapports de backtest, calibration, ROI et suivi de data quality.

## Principes De Fiabilité

Le projet est conçu pour éviter les erreurs classiques d'un système prédictif sportif :

- données point-in-time uniquement ;
- aucune lecture d'odds, lineups, blessures ou résultats après l'heure de prédiction ;
- secrets masqués dans logs, snapshots et payloads Discord ;
- sources optionnelles tolérées avec warnings et baisse de qualité ;
- publication publique bloquée si la confiance, l'EV ou la qualité de données est
  insuffisante.

Les IDs API-Football ne doivent jamais être inventés. Ils viennent des référentiels locaux
dans `docs/api_football_reference.json`, `docs/api_football_players_reference.json` ou de
la base déjà initialisée.

Référentiels locaux attendus :

- `docs/api_football_reference.md`
- `docs/api_football_reference.json`
- `docs/api_football_players_reference.md`
- `docs/api_football_players_reference.json`
- `docs/api_football_players_cache.json` : cache technique, pas la source metier principale.

## Installation Rapide

Prérequis :

- Python `>=3.11,<3.13` ;
- SQLite par défaut ;
- API-Football pour les refresh live ;
- Discord webhooks uniquement si publication activée.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python scripts/repair_editable_install.py
cp .env.example .env
```

Les valeurs sensibles restent dans `.env` ou dans des fichiers locaux ignorés par Git.
Ne jamais remplir `.env.example` avec de vraies clés.

## Commandes Essentielles

Le nom public du projet est FootLumen. La commande technique reste
`football-predictor` pour préserver la compatibilité avec les crons, scripts et imports
existants.

Diagnostic :

```bash
football-predictor healthcheck
football-predictor doctor --strict
```

Qualité :

```bash
make check
make security
make smoke
```

Base et référentiels :

```bash
football-predictor init-db
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json
```

Prédictions et publications en dry-run :

```bash
football-predictor predict-today --date 2026-06-11 --window late --no-refresh-data --dry-run
football-predictor worldcup-run-daily --window late --dry-run
football-predictor worldcup-combos-run --config config/worldcup_combos.yaml --dry-run
football-predictor worldcup-combos-publish --config config/worldcup_combos.yaml --dry-run
PYTHONPATH=src .venv/bin/python scripts/audit_worldcup_fixture_times.py
```

## API V1 Read-Only

FootLumen expose aussi une API HTTP V1 read-only destinée au futur dashboard
`app.footlumen.com`. Elle lit uniquement les données déjà produites par les crons et
services existants : fixtures, prédictions, O/U, combinés, résultats et compteurs de
performance. Elle ne remplace pas Discord et ne déclenche aucune prédiction, ingestion,
publication ou écriture DB.

Elle est désactivée et protégée par token par défaut :

```env
FOOTLUMEN_API_ENABLED=false
FOOTLUMEN_API_REQUIRE_TOKEN=true
FOOTLUMEN_API_DOCS_ENABLED=false
```

Lancement local contrôlé :

```bash
FOOTLUMEN_API_ENABLED=true FOOTLUMEN_API_TOKEN=dev-token \
uvicorn football_predictor.web_api.app:app --reload --port 8000
```

Contrat et déploiement : `docs/web_api_contract.md`, `docs/web_api_security.md`,
`docs/web_api_deployment.md`.

## Coupe Du Monde 2026

Le mode CDM utilise `config/competitions_worldcup.yaml` et le modèle
`data/models/worldcup-1x2`.

Fonctionnalités spécifiques :

- affichage des classements par groupes A-L ;
- calendrier groupé par groupe ;
- matchs du jour avec groupe affiché ;
- audit des horaires en `Europe/Paris` ;
- crons CDM 24h/24 pour ne pas manquer les matchs de nuit ;
- publication des combinés en staff/shadow tant que `staff_only_shadow_mode: true`.

Exemple de vérification horaire :

```bash
PYTHONPATH=src .venv/bin/python scripts/audit_worldcup_fixture_times.py
```

## Combinés CDM

La feature combinés CDM est isolée dans `world_cup_combos` et reste contrôlée par :

```yaml
enabled: true
staff_only_shadow_mode: true
publish_no_bet_public: false
```

Avec ce réglage, les tickets techniquement publiables restent en staff. Le passage public
doit être fait manuellement après validation des dry-runs, de l'idempotence Discord et de
la qualité des données.

## Documentation Utile

- `docs/operations_guide.md` : exploitation quotidienne et automatisations.
- `docs/production_runbook.md` : déploiement VPS, crons, rollback, monitoring.
- `docs/brand.md` : identité FootLumen, palette et usage des assets.
- `docs/worldcup_only_vps_mode.md` : mode Coupe du Monde uniquement.
- `docs/worldcup_combos.md` : combinés CDM, cycle de vie et publication.
- `docs/modeling_strategy.md` : modèles, calibration, draw safety, O/U V2.
- `docs/data_contract.md` : schémas, snapshots, features et règles point-in-time.
- `docs/security.md` : secrets, sanitization, scan et rotation.

## Développement

Avant tout changement important :

```bash
git status --short
make check
make security
```

Les tests unitaires ne doivent pas faire d'appel réseau. Les scripts qui écrivent, publient
ou synchronisent massivement doivent rester en dry-run par défaut ou exiger `--execute`.

## Avertissement

FootLumen fournit une aide à l'analyse probabiliste. Une prédiction, même avec une
confiance élevée, ne garantit jamais le résultat d'un match.
