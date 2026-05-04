# Prompts de sprints consolidés — Football Predictor

Ce document remplace la première version des prompts de sprints. Il conserve les objectifs, contraintes, tâches et définitions de done des prompts originaux, tout en ajoutant le contexte obligatoire lié aux fichiers suivants déjà présents dans le projet :

```text
AGENTS.md
blueprint.md
docs/api_football_reference.md
docs/api_football_reference.json
docs/api_football_players_reference.md
docs/api_football_players_reference.json
docs/api_football_players_cache.json
```

Règle générale à appliquer dans tous les sprints : Codex doit lire `AGENTS.md` et `blueprint.md` avant toute modification, puis consulter les fichiers `docs/` pertinents. Aucun `league_id`, `team_id`, `fixture_id`, `player_id`, `venue_id`, `bookmaker_id` ou `bet_id` ne doit être inventé. Les JSON servent au code, aux tests et aux validateurs. Les Markdown servent à comprendre le contexte humain. Le cache joueurs sert uniquement à la reprise de collecte et à l’économie de quota.

---

# Préambule commun à coller au début de chaque sprint Codex

```text
Avant toute action, lis AGENTS.md et blueprint.md.
Ensuite, consulte les fichiers docs/ pertinents selon la tâche :
- docs/api_football_reference.md pour comprendre humainement les compétitions, équipes, venues, fixtures, standings, rounds, bookmakers et bets.
- docs/api_football_reference.json pour charger, valider ou rechercher par code les league_id, team_id, fixture_id, venue_id, bookmaker_id et bet_id.
- docs/api_football_players_reference.md pour comprendre humainement les joueurs, effectifs, postes, numéros et équipes.
- docs/api_football_players_reference.json pour charger, valider ou rechercher par code les player_id, team_id, postes, numéros, saisons et effectifs.
- docs/api_football_players_cache.json uniquement comme cache technique de collecte, pas comme source métier principale.

Règles obligatoires :
- Ne devine aucun ID API-Football.
- Ne supprime ni n’écrase aucun des 5 fichiers de référence sous docs/.
- Utilise les JSON pour le code, les tests, les validateurs et le seed local.
- Utilise les Markdown pour comprendre et documenter.
- Ne fais aucun appel API live sauf si le sprint le demande explicitement.
- Ne fais aucun appel réseau dans les tests unitaires.
- Ne loggue jamais API_FOOTBALL_KEY, DISCORD_WEBHOOK_URL, token ou secret.
- Toutes les features dynamiques doivent respecter fixture_id + prediction_time.
- Exclue toujours la fixture cible de ses propres historiques.
- Aucune feature ne doit utiliser une donnée postérieure à prediction_time.
- Si une donnée optionnelle manque, continue le pipeline avec flags de qualité et logs clairs.
- À la fin, exécute pytest et ruff check . si possible, puis relis le diff pour détecter bugs, data leakage, secrets exposés, IDs inventés, tests manquants et documentation obsolète.
```

---

# Sprint 0 — Cadrage produit, spécification et plan global

## Objectif

Créer les documents de référence du projet et les aligner avec `AGENTS.md`, `blueprint.md` et les 5 fichiers référentiels déjà présents sous `docs/`.

Le sprint doit produire ou mettre à jour :

```text
README.md
PLANS.md
docs/product_spec.md
docs/architecture.md
docs/modeling_strategy.md
docs/data_contract.md
```

Important : `AGENTS.md`, `blueprint.md` et les 5 fichiers de référence API-Football existent déjà. Ils ne doivent pas être supprimés, renommés, tronqués ou écrasés.

Aucun code métier complexe ici. On veut que Codex ait un cadre stable avant d’écrire.

## Mode Codex

```text
Plan mode d’abord
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis d’abord AGENTS.md et blueprint.md.
Consulte ensuite les fichiers de référence existants sous docs/ :
- docs/api_football_reference.md
- docs/api_football_reference.json
- docs/api_football_players_reference.md
- docs/api_football_players_reference.json
- docs/api_football_players_cache.json

Ne modifie aucun fichier pour l’instant.
Ne supprime, ne renomme et n’écrase aucun des fichiers ci-dessus.

Je veux construire un outil Python de prédiction de matchs de football basé sur API-Football.

Objectif produit :
- Prédire le résultat 1X2 d’un match : victoire domicile, nul, victoire extérieur.
- Produire des probabilités calibrées : P(Home), P(Draw), P(Away).
- Générer une prédiction claire et explicable.
- Publier le résultat dans Discord via webhook, sous forme de bloc markdown.
- Construire une V1 ultra robuste, pas une simple preuve de concept.

Contexte documentaire maintenant obligatoire :
- AGENTS.md définit les règles de travail, de sécurité, de tests, d’anti data leakage et de hiérarchie des sources.
- blueprint.md définit le contexte métier central du projet.
- docs/api_football_reference.md est la documentation lisible des compétitions : league_id, team_id, venue_id, standings, rounds, fixtures, bookmakers, bets.
- docs/api_football_reference.json contient le même contenu en version machine-readable pour le futur code.
- docs/api_football_players_reference.md est la documentation lisible des joueurs par compétition et par équipe.
- docs/api_football_players_reference.json contient la version structurée des 4645 joueurs reliés à team_id, compétition, saison et équipe.
- docs/api_football_players_cache.json est un cache technique de collecte pour éviter de refaire les appels /players/squads ; ce n’est pas la source métier principale.

Contraintes :
- Python 3.11+.
- Architecture modulaire.
- Stockage local SQLite au départ, mais compatible PostgreSQL ensuite.
- Utiliser API-Football v3.
- Éviter strictement toute fuite de données : les features historiques doivent être calculées comme si on était avant le coup d’envoi.
- Les données brutes API doivent être stockées en snapshots.
- Les odds doivent être converties en probabilités implicites sans marge bookmaker.
- Le modèle doit intégrer : forme équipe, domicile/extérieur, statistiques match, standings, joueurs, XI type, absences, blessures, odds, prédiction API-Football, contexte calendrier.
- Le livrable final doit être utilisable en CLI.
- Les prédictions doivent être envoyées dans Discord via webhook.
- Le projet doit être testable avec pytest et lintable avec ruff.
- Le projet doit prévoir un module reference/ pour charger et interroger les JSON locaux sous docs/.
- Aucun ID API-Football ne doit être inventé dans les exemples ou tests : utiliser les docs JSON ou marquer explicitement les données comme synthétiques.
- Les fichiers de référence docs/ doivent permettre de seed la base locale sans consommer de quota API.

Je veux que tu proposes un plan d’architecture complet avant toute modification de fichier.

À produire dans ton plan :
1. Arborescence cible du repo.
2. Liste des modules.
3. Liste des documents à créer ou mettre à jour.
4. Place de AGENTS.md et blueprint.md dans le workflow Codex.
5. Usage précis des 5 fichiers docs/ de référence.
6. Choix techniques.
7. Principes anti data leakage.
8. Stratégie de tests.
9. Stratégie de seed local depuis docs/.
10. Définition du “done” pour ce sprint.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 0.

Avant de modifier les fichiers, relis AGENTS.md et blueprint.md.
Consulte les fichiers docs/ existants pour intégrer leur rôle dans la documentation :
- docs/api_football_reference.md
- docs/api_football_reference.json
- docs/api_football_players_reference.md
- docs/api_football_players_reference.json
- docs/api_football_players_cache.json

Ne supprime, ne renomme et n’écrase aucun de ces 5 fichiers.
Ne réécris pas AGENTS.md ni blueprint.md sauf correction strictement nécessaire et explicitement justifiée.

Crée ou complète les fichiers de documentation suivants :
- README.md
- PLANS.md
- docs/product_spec.md
- docs/architecture.md
- docs/modeling_strategy.md
- docs/data_contract.md

Contenu attendu :
1. README.md :
   - Objectif du projet.
   - Installation future.
   - Commandes prévues.
   - Vue d’ensemble de l’architecture.
   - Avertissement : prédiction probabiliste, pas garantie de résultat.
   - Mention explicite que AGENTS.md et blueprint.md sont les documents de contexte à lire avant développement.
   - Mention explicite que les IDs API-Football doivent venir des fichiers docs/*.json ou de la base locale, jamais être inventés.

2. PLANS.md :
   - Format d’ExecPlan pour les gros changements.
   - Chaque sprint doit avoir objectif, contexte, contraintes, étapes, tests, risques, done.
   - Rappel que Codex doit commencer par Plan mode pour tout sprint ou changement important.
   - Rappel de consulter AGENTS.md, blueprint.md et les fichiers docs/ pertinents.

3. docs/product_spec.md :
   - Fonctionnalités finales attendues.
   - Sortie attendue de prédiction.
   - Format Discord attendu.
   - Données API-Football utilisées.
   - Rôle des 5 fichiers référentiels sous docs/.
   - Différence entre référentiels statiques, snapshots dynamiques et API live.

4. docs/architecture.md :
   - Architecture cible src/football_predictor.
   - Flux : référence docs -> seed DB optionnel -> ingestion API -> stockage -> features -> modèle -> prédiction -> Discord.
   - Description des modules.
   - Inclure explicitement un module src/football_predictor/reference/.
   - Décrire comment les JSON docs/ sont utilisés pour éviter les IDs inventés et économiser le quota API.

5. docs/modeling_strategy.md :
   - Modèle sportif.
   - Modèle odds.
   - Stacking.
   - Calibration.
   - Évaluation.
   - Backtesting.
   - Règles anti data leakage.
   - Mention que les fichiers docs/ donnent le contexte et les IDs mais ne remplacent pas les snapshots dynamiques des features.

6. docs/data_contract.md :
   - Entités principales : fixture, team, player, odds, injury, lineup, player_stats, prediction_snapshot, feature_snapshot.
   - Règle de snapshot temporel.
   - Nommage des champs.
   - Chemins des fichiers référentiels :
     - docs/api_football_reference.json
     - docs/api_football_players_reference.json
     - docs/api_football_players_cache.json
   - Règles d’usage des fichiers Markdown vs JSON.
   - Champs minimaux attendus pour seed leagues, teams, venues, players, squads, bookmakers et bets depuis les docs.

N’écris pas encore le code applicatif.
Ajoute une section “Sprint 0 completed” dans README.md.

À la fin :
- Vérifie qu’aucun fichier référentiel docs/ n’a été supprimé ou écrasé.
- Vérifie qu’aucun secret n’a été ajouté.
- Vérifie que la documentation indique clairement de ne jamais inventer d’ID API-Football.
```

## Done

```text
- Tous les documents existent.
- AGENTS.md et blueprint.md sont respectés.
- Les 5 fichiers docs/ sont documentés comme sources de vérité.
- L’architecture est compréhensible sans contexte externe.
- Aucun fichier référentiel n’a été supprimé ou écrasé.
```

---

# Sprint 1 — Bootstrap technique du repository

## Objectif

Créer le squelette Python, la configuration, les dépendances, les commandes de base, le module `reference/` vide et les premiers tests.

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/api_football_reference.json et docs/api_football_players_reference.json pour comprendre qu’ils seront utilisés par le futur module reference/, mais ne parse pas encore toute leur structure si ce sprint ne le nécessite pas.
Ne modifie aucun fichier pour l’instant.

Nous passons au Sprint 1 : bootstrap technique du projet.

Contexte :
- Les documents README.md, AGENTS.md, blueprint.md, PLANS.md et docs/ existent déjà.
- Les 5 fichiers référentiels sous docs/ existent déjà et ne doivent pas être supprimés.
- Le projet doit être un package Python nommé football_predictor.
- On veut une base propre pour développer l’ingestion API-Football, les références locales, les features, les modèles et l’envoi Discord.

Objectif :
Créer la structure Python complète avec configuration moderne.

Contraintes :
- Python 3.11+.
- Utiliser pyproject.toml.
- Utiliser src/ layout.
- Utiliser pytest.
- Utiliser ruff.
- Utiliser mypy ou configuration prête pour typage.
- Utiliser typer pour la CLI.
- Utiliser pydantic-settings pour la configuration.
- Ne pas inclure de secret.
- Ajouter .env.example.
- Ajouter des tests smoke simples.
- Ajouter des commandes documentées dans README.md.
- Ajouter src/football_predictor/reference/ dans l’arborescence, même si les loaders complets seront implémentés plus tard.
- Ajouter dans .env.example les chemins configurables vers :
  - API_FOOTBALL_REFERENCE_PATH=docs/api_football_reference.json
  - API_FOOTBALL_PLAYERS_REFERENCE_PATH=docs/api_football_players_reference.json
  - API_FOOTBALL_PLAYERS_CACHE_PATH=docs/api_football_players_cache.json
- Ne jamais mettre de valeurs sensibles dans .env.example.
- Ne pas inventer d’ID API-Football dans les tests smoke.

À planifier :
1. Structure des dossiers.
2. Dépendances à ajouter.
3. Fichiers de configuration.
4. CLI minimale.
5. Settings, incluant les chemins des références docs/.
6. Module reference/ initial.
7. Tests minimaux.
8. Commandes de vérification.
9. Critères de done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 1.

Avant de modifier, relis AGENTS.md et blueprint.md.
Préserve les 5 fichiers référentiels déjà présents sous docs/.

Tâches :
1. Crée un pyproject.toml complet pour un projet Python 3.11+.
2. Ajoute les dépendances principales :
   - httpx
   - pydantic
   - pydantic-settings
   - sqlalchemy
   - alembic
   - pandas
   - numpy
   - scikit-learn
   - joblib
   - typer
   - rich
   - python-dotenv
3. Ajoute les dépendances dev :
   - pytest
   - pytest-cov
   - ruff
   - mypy
4. Crée la structure :
   - src/football_predictor/
   - src/football_predictor/config/
   - src/football_predictor/api/
   - src/football_predictor/db/
   - src/football_predictor/ingestion/
   - src/football_predictor/features/
   - src/football_predictor/modeling/
   - src/football_predictor/backtesting/
   - src/football_predictor/prediction/
   - src/football_predictor/discord/
   - src/football_predictor/reference/
   - src/football_predictor/utils/
   - tests/
5. Ajoute __init__.py dans les packages.
6. Crée src/football_predictor/cli.py avec une commande Typer minimale :
   - football-predictor version
   - football-predictor healthcheck
7. Crée .env.example avec :
   - API_FOOTBALL_KEY=
   - API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
   - DATABASE_URL=sqlite:///./data/football_predictor.db
   - DISCORD_WEBHOOK_URL=
   - APP_TIMEZONE=Europe/Paris
   - API_FOOTBALL_REFERENCE_PATH=docs/api_football_reference.json
   - API_FOOTBALL_PLAYERS_REFERENCE_PATH=docs/api_football_players_reference.json
   - API_FOOTBALL_PLAYERS_CACHE_PATH=docs/api_football_players_cache.json
8. Crée src/football_predictor/config/settings.py avec une classe Settings basée sur pydantic-settings.
   - Inclure les chemins des fichiers docs/.
   - Valider les chemins sans exiger que les secrets soient présents pour les tests.
   - Ne jamais afficher les secrets dans repr/logs.
9. Crée src/football_predictor/reference/__init__.py avec exports vides ou placeholders propres, sans implémenter encore les lookups complets.
10. Crée tests/test_healthcheck.py.
11. Mets à jour README.md avec les commandes :
   - installation
   - lancement CLI
   - tests
   - lint
   - rappel du rôle de AGENTS.md, blueprint.md et docs/.
12. Configure ruff et mypy dans pyproject.toml.

Définition de done :
- python -m football_predictor.cli healthcheck fonctionne ou la commande console équivalente fonctionne.
- pytest passe.
- ruff check passe.
- Aucun secret n’est ajouté.
- Les variables de chemins docs/ sont présentes dans .env.example.
- Le dossier reference/ existe.
- Aucun fichier docs/ référentiel n’a été supprimé ou modifié inutilement.
```

## Done

```text
- Projet installable.
- CLI minimale fonctionnelle.
- Tests smoke OK.
- Settings contient les chemins vers les références docs/.
- Module reference/ prêt pour le sprint suivant.
```

---

# Sprint 2 — Configuration, logging et client API-Football

## Objectif

Créer un client API robuste :

```text
authentification
GET uniquement
gestion erreurs
pagination
retry
rate limit
snapshots bruts
logs sans secret
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/api_football_reference.md ou docs/api_football_reference.json seulement si tu as besoin de comprendre les endpoints ou des IDs dans les exemples. Ne devine aucun ID.
Ne modifie aucun fichier pour l’instant.

Sprint 2 : configuration, logging et client API-Football.

Contexte :
- Le repo Python existe.
- Settings existe.
- Les chemins des fichiers de référence docs/ sont configurables.
- On doit maintenant créer un client API-Football robuste.
- API-Football utilise le header x-apisports-key.
- Les endpoints sont en GET.
- Certaines réponses sont paginées.
- On veut stocker les réponses brutes pour audit et reproductibilité.
- Les snapshots API dynamiques ne remplacent pas les référentiels docs/, et inversement.

Objectif :
Créer un client HTTP propre, typé, testable, avec retry, logs, pagination et sauvegarde optionnelle des réponses brutes.

Contraintes :
- Utiliser httpx.
- Ne jamais logger la clé API.
- Tous les appels doivent passer par un ApiFootballClient unique.
- Supporter les paramètres query.
- Supporter la pagination quand la réponse contient paging.current et paging.total.
- Gérer les codes 200, 204, 499, 500.
- Lever des exceptions explicites.
- Ajouter des tests unitaires avec mocking.
- Prévoir un mécanisme simple de raw snapshot JSON sur disque dans data/raw/api_football/.
- Ne pas faire de vrais appels réseau dans les tests.
- Les snapshots ne doivent jamais contenir API_FOOTBALL_KEY.
- Les exemples de paramètres ne doivent pas inventer d’IDs : utiliser des valeurs génériques ou des fixtures synthétiques clairement marquées.

À planifier :
1. Fichiers à créer.
2. Design de ApiFootballClient.
3. Exceptions.
4. Gestion pagination.
5. Gestion snapshots.
6. Masquage des secrets.
7. Tests.
8. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 2.

Avant de modifier, relis AGENTS.md et blueprint.md.
Ne fais aucun appel API réel dans les tests.
Ne loggue jamais API_FOOTBALL_KEY.

Crée :
- src/football_predictor/api/api_football_client.py
- src/football_predictor/api/endpoints.py
- src/football_predictor/api/exceptions.py
- src/football_predictor/api/rate_limit.py si utile
- src/football_predictor/utils/logging.py
- tests/test_api_client.py

Fonctionnalités attendues :
1. ApiFootballClient :
   - initialisé avec base_url, api_key, timeout, snapshot_dir.
   - méthode get(endpoint: str, params: dict | None = None, paginate: bool = False).
   - ajoute automatiquement le header x-apisports-key.
   - ne supporte que GET.
   - masque la clé API dans les logs.
   - retourne le JSON complet ou une liste consolidée si paginate=True.
   - si paginate=True, boucle sur page=1..paging.total.
   - respecte les paramètres existants sans les écraser sauf page.
   - gère 204 en retournant une réponse vide structurée.
   - gère 499 et 500 avec exceptions spécifiques.
   - inclut endpoint, params, status_code dans les exceptions, sans secret.

2. Snapshots :
   - option save_raw=True dans get().
   - sauvegarde dans data/raw/api_football/YYYY-MM-DD/{endpoint_sanitized}_{timestamp}.json.
   - inclut metadata : endpoint, params, fetched_at, status_code.
   - n’écrit jamais la clé API.

3. endpoints.py :
   - constantes pour tous les endpoints utiles :
     leagues
     teams
     teams/statistics
     standings
     fixtures
     fixtures/headtohead
     fixtures/statistics
     fixtures/events
     fixtures/lineups
     fixtures/players
     injuries
     predictions
     players
     players/squads
     players/topscorers
     players/topassists
     odds
     odds/bookmakers
     odds/bets
     odds/mapping

4. Logging :
   - configure un logger standard football_predictor.
   - logs lisibles en console.
   - logs sans secret.

5. Tests :
   - mock httpx.
   - test header présent.
   - test clé non loggée.
   - test pagination.
   - test 204.
   - test 499/500.
   - test snapshot écrit sans clé API.

Mets à jour README.md avec un exemple d’utilisation du client, sans vrai secret et sans ID inventé.
Exécute pytest et ruff si possible.
```

## Done

```text
- Client API centralisé.
- Pagination gérée.
- Snapshots bruts disponibles.
- Tests sans vrais appels réseau.
- Secrets masqués.
```

---

# Sprint 3 — Base de données et modèles de stockage

## Objectif

Créer le modèle de données local. C’est le cœur de la robustesse.

On veut stocker :

```text
raw_api_snapshots
leagues
teams
venues
fixtures
standings_snapshots
fixture_statistics
fixture_events
fixture_lineups
fixture_players
players
player_squads
injuries
odds_snapshots
api_predictions
feature_snapshots
model_predictions
discord_messages
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/api_football_reference.json et docs/api_football_players_reference.json pour comprendre les entités seedables depuis les docs : leagues, teams, venues, fixtures de référence, bookmakers, bets, players, squads.
Ne modifie aucun fichier pour l’instant.

Sprint 3 : base de données et modèles de stockage.

Contexte :
- Le client API-Football existe.
- Le repo contient les 5 fichiers référentiels sous docs/.
- On doit maintenant créer un stockage local robuste.
- SQLite sera utilisé en local, mais le design doit rester compatible PostgreSQL.
- On veut stocker à la fois les données normalisées et les payloads JSON bruts.
- On veut pouvoir seed certains référentiels depuis docs/ sans appel API.
- On veut pouvoir stocker les snapshots dynamiques issus de l’API pour les features point-in-time.

Objectif :
Créer les modèles SQLAlchemy, la session DB, l’initialisation, et les premières migrations Alembic.

Contraintes :
- SQLAlchemy 2.x style.
- Compatibilité SQLite et PostgreSQL.
- JSON doit être stocké proprement.
- Tous les snapshots doivent avoir fetched_at.
- Les fixtures doivent avoir fixture_id, league_id, season, date, status, home_team_id, away_team_id.
- Les tables de snapshots doivent garder le payload brut.
- Les prédictions modèle doivent garder prediction_time, model_version, feature_snapshot_id.
- Ne pas écraser les données : utiliser upsert ou fonctions idempotentes lorsque possible.
- Ajouter tests DB simples sur SQLite temporaire.
- Prévoir une table Venue si les données docs/API contiennent des venue_id.
- Prévoir si utile des tables ou structures pour bookmakers/bets de référence, ou les conserver dans payload_json jusqu’au sprint odds.
- Ne pas inventer d’IDs dans les tests réalistes : utiliser docs JSON ou données synthétiques clairement marquées.

À planifier :
1. Schéma de tables.
2. Relations principales.
3. Place des entités seedées depuis docs/.
4. Index importants.
5. Gestion des timestamps.
6. Fonctions d’init DB.
7. Tests.
8. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 3.

Avant de modifier, relis AGENTS.md et blueprint.md.
Préserve les fichiers docs/ existants.
Ne fais aucun appel réseau dans les tests.

Crée ou complète :
- src/football_predictor/db/models.py
- src/football_predictor/db/session.py
- src/football_predictor/db/init_db.py
- src/football_predictor/db/repositories.py
- alembic.ini
- migrations/env.py ou structure Alembic équivalente
- tests/test_db_models.py

Modèles SQLAlchemy attendus :
1. RawApiSnapshot
   - id
   - endpoint
   - params_json
   - payload_json
   - fetched_at
   - status_code
   - source

2. League
   - league_id
   - name
   - country
   - type
   - logo
   - payload_json

3. Venue, si les données disponibles le permettent
   - venue_id
   - name
   - address
   - city
   - capacity
   - surface
   - image
   - payload_json

4. Team
   - team_id
   - name
   - country
   - founded
   - logo
   - venue_id
   - payload_json

5. Fixture
   - fixture_id
   - league_id
   - season
   - round
   - date
   - timezone
   - status_short
   - status_long
   - elapsed
   - home_team_id
   - away_team_id
   - home_goals
   - away_goals
   - venue_id
   - payload_json

6. StandingSnapshot
   - id
   - league_id
   - season
   - team_id
   - rank
   - points
   - goals_diff
   - form
   - description
   - all_played
   - all_win
   - all_draw
   - all_lose
   - all_goals_for
   - all_goals_against
   - home_played
   - home_win
   - home_draw
   - home_lose
   - away_played
   - away_win
   - away_draw
   - away_lose
   - snapshot_date
   - payload_json

7. FixtureStatistics
   - id
   - fixture_id
   - team_id
   - statistics_json
   - fetched_at

8. FixtureEvent
   - id
   - fixture_id
   - team_id
   - player_id
   - assist_player_id
   - type
   - detail
   - elapsed
   - extra
   - payload_json

9. FixtureLineup
   - id
   - fixture_id
   - team_id
   - coach_id
   - formation
   - start_xi_json
   - substitutes_json
   - payload_json
   - fetched_at

10. FixturePlayerStats
    - id
    - fixture_id
    - team_id
    - player_id
    - statistics_json
    - rating
    - minutes
    - position
    - payload_json
    - fetched_at

11. Player
    - player_id
    - name
    - firstname
    - lastname
    - age
    - birth_date
    - nationality
    - height
    - weight
    - injured
    - photo
    - payload_json

12. PlayerSquad
    - id
    - team_id
    - player_id
    - position
    - number
    - payload_json
    - fetched_at

13. Injury
    - id
    - fixture_id
    - league_id
    - season
    - team_id
    - player_id
    - reason
    - type
    - date
    - payload_json
    - fetched_at

14. OddsSnapshot
    - id
    - fixture_id
    - league_id
    - season
    - bookmaker_id
    - bookmaker_name
    - bet_id
    - bet_name
    - values_json
    - fetched_at
    - payload_json

15. ApiPredictionSnapshot
    - id
    - fixture_id
    - winner_team_id
    - win_or_draw
    - advice
    - percent_home
    - percent_draw
    - percent_away
    - payload_json
    - fetched_at

16. FeatureSnapshot
    - id
    - fixture_id
    - prediction_time
    - feature_version
    - features_json
    - data_quality_json
    - created_at

17. ModelPrediction
    - id
    - fixture_id
    - prediction_time
    - model_version
    - p_home
    - p_draw
    - p_away
    - predicted_outcome
    - confidence
    - feature_snapshot_id
    - explanation_json
    - created_at

18. DiscordMessage
    - id
    - fixture_id
    - model_prediction_id
    - webhook_url_hash
    - message_hash
    - sent_at
    - status
    - response_text

Ajoute :
- indexes sur fixture_id, team_id, league_id, season, fetched_at.
- fonctions create_db_and_tables().
- repository avec méthodes upsert de base.
- support idempotent pour données seedées depuis docs/ et données API.
- tests sur SQLite temporaire.
- README : commande d’initialisation DB.

Exécute les tests.
```

## Done

```text
- DB initialisable.
- Tables créées.
- Tests DB OK.
- Modèle prêt pour seed depuis docs/ et snapshots API.
```

---

# Sprint 4 — Référentiels locaux et ingestion référentiels : leagues, teams, seasons, coverage, players

## Objectif

Récupérer ou charger les données de référence :

```text
leagues
seasons
coverage
teams
venues
players squads
bookmakers
bets
```

La coverage est importante pour savoir si une ligue a :

```text
events
lineups
statistics
players
injuries
odds
predictions
```

Ce sprint doit aussi intégrer les 5 fichiers docs/ comme source de seed locale, afin d’économiser le quota API.

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte obligatoirement :
- docs/api_football_reference.md
- docs/api_football_reference.json
- docs/api_football_players_reference.md
- docs/api_football_players_reference.json
- docs/api_football_players_cache.json

Ne modifie aucun fichier pour l’instant.
Ne supprime ni n’écrase aucun fichier docs/.

Sprint 4 : ingestion des référentiels API-Football et seed depuis les documents locaux.

Contexte :
- Client API disponible.
- DB disponible.
- Les fichiers docs/ contiennent déjà un référentiel des compétitions, équipes, venues, fixtures, standings, rounds, bookmakers, bets et joueurs.
- On veut ingérer les données de base avant les fixtures dynamiques.
- On veut pouvoir initialiser la DB sans refaire les appels API /players/squads grâce aux JSON locaux.
- API live doit rester disponible pour refresh explicite.

Objectif :
Créer les services d’ingestion pour :
- leagues
- seasons
- teams
- venues si disponibles dans les payloads
- players/squads
- coverage de ligue
- bookmakers et bets si présents dans docs/api_football_reference.json
- seed local depuis docs/api_football_reference.json
- seed local depuis docs/api_football_players_reference.json

Contraintes :
- Les ingestions doivent être idempotentes.
- Chaque réponse API live doit être stockée comme RawApiSnapshot.
- Les entités normalisées doivent être upsertées.
- Ne pas faire d’appel API dans les tests.
- Ajouter des commandes CLI.
- Gérer pagination quand nécessaire.
- Prévoir une config de ligues suivies dans un fichier YAML ou JSON.
- Créer un module reference/ avec loaders et lookups pour les fichiers JSON locaux.
- Les loaders reference/ ne doivent jamais appeler l’API live.
- Les tests doivent utiliser des payloads locaux ou de petits échantillons extraits des JSON docs/.
- docs/api_football_players_cache.json doit rester un cache technique, pas une source métier principale.

À planifier :
1. Fichiers à créer.
2. Format config des ligues suivies.
3. Module reference/ : schemas, loaders, lookups, erreurs.
4. Commande seed-reference-from-docs.
5. Ingestion API live leagues/teams/squads.
6. Usage du cache players uniquement si nécessaire.
7. Commandes CLI.
8. Tests avec payloads fixtures.
9. Tests d’idempotence.
10. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 4.

Avant de modifier, relis AGENTS.md et blueprint.md.
Utilise les JSON docs/ comme sources locales structurées.
Ne supprime ni n’écrase les 5 fichiers référentiels sous docs/.
Ne fais aucun appel réseau dans les tests.

Crée :
- src/football_predictor/reference/__init__.py
- src/football_predictor/reference/schemas.py
- src/football_predictor/reference/loaders.py
- src/football_predictor/reference/lookups.py
- src/football_predictor/reference/exceptions.py
- src/football_predictor/ingestion/ingest_reference.py
- src/football_predictor/ingestion/parsers.py
- src/football_predictor/config/competitions.py
- config/competitions.example.yaml
- tests/fixtures/api/leagues.json
- tests/fixtures/api/teams.json
- tests/fixtures/api/players_squads.json
- tests/fixtures/reference/reference_sample.json
- tests/fixtures/reference/players_reference_sample.json
- tests/test_reference_loaders.py
- tests/test_reference_lookups.py
- tests/test_ingest_reference.py

Fonctionnalités reference/ :
1. load_api_football_reference(path)
   - lit docs/api_football_reference.json ou un sample de test.
   - ne fait aucun appel API.
   - tolère les champs manquants.
   - retourne une structure typée ou dataclass/Pydantic.

2. load_players_reference(path)
   - lit docs/api_football_players_reference.json ou un sample de test.
   - ne fait aucun appel API.
   - retourne les joueurs et leurs liens team/league/season.

3. Lookups :
   - find_league_by_id(league_id)
   - find_team_by_id(team_id)
   - find_team_by_name(name, league_id=None)
   - find_player_by_id(player_id)
   - find_players_by_team(team_id)
   - find_bookmaker_by_id(bookmaker_id)
   - find_bet_by_id(bet_id)
   - validate_fixture_reference(fixture_id)

4. Erreurs :
   - ReferenceLookupError explicite.
   - Ne jamais retourner silencieusement un ID inventé.

Fonctionnalités config competitions :
1. Fichier YAML avec liste :
   - league_id
   - season
   - name
   - country
   - enabled
2. Charger ce fichier depuis settings.
3. Permettre de générer ou valider config/competitions.example.yaml depuis les références docs/ si possible.
4. Aucun ID inventé : utiliser les références docs/ ou des valeurs synthétiques marquées.

Fonctionnalités seed depuis docs :
1. seed_reference_from_docs(reference_path, players_path)
   - charge competitions/leagues.
   - charge teams.
   - charge venues si présentes.
   - charge bookmakers et bets si modélisés ou les conserve en payload selon design.
   - charge players.
   - charge PlayerSquad.
   - produit un résumé : leagues, teams, venues, players, squads, bookmakers, bets.
   - idempotent.
   - ne fait aucun appel API.

2. CLI :
   - football-predictor seed-reference-from-docs --reference docs/api_football_reference.json --players docs/api_football_players_reference.json
   - option --dry-run.

Fonctionnalités ingestion API live :
1. Ingestion leagues :
   - endpoint /leagues avec league + season.
   - stocke League.
   - stocke coverage dans payload_json.
   - stocke RawApiSnapshot.

2. Ingestion teams :
   - endpoint /teams avec league + season.
   - upsert Team.
   - conserve venue dans payload_json ou table Venue si créée.

3. Ingestion squads :
   - endpoint /players/squads avec team.
   - upsert Player.
   - upsert PlayerSquad.

4. CLI :
   - football-predictor ingest-reference --config config/competitions.example.yaml
   - option --dry-run
   - option --save-raw
   - option --prefer-docs pour utiliser les fichiers locaux quand possible.
   - option --refresh-live pour forcer API live.

Tests :
- utiliser payloads JSON locaux.
- vérifier loaders reference.
- vérifier lookups.
- vérifier erreur sur ID absent.
- vérifier seed depuis docs sample.
- vérifier upsert.
- vérifier idempotence : deux ingestions ne dupliquent pas.
- vérifier RawApiSnapshot pour ingestion API live mockée.
- vérifier qu’aucun appel réseau n’est effectué.

Mets à jour README.md, docs/architecture.md et docs/data_contract.md.
```

## Done

```text
- Ligues suivies configurables.
- Référentiels docs/ chargeables par le code.
- Seed DB depuis docs/ possible sans quota API.
- Teams et squads ingérables depuis API live ou docs.
- Idempotence testée.
```

---

# Sprint 5 — Ingestion fixtures, standings et historique match

## Objectif

Récupérer les matchs :

```text
calendrier
résultats passés
standings
head-to-head
fixtures terminées
fixtures à venir
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/api_football_reference.json pour valider les league_id, team_id et fixture_id utilisés dans les exemples ou tests réalistes.
Consulte docs/api_football_reference.md si tu dois comprendre les rounds, fixtures ou standings de manière humaine.
Ne modifie aucun fichier pour l’instant.

Sprint 5 : ingestion fixtures, standings et historique match.

Contexte :
- Référentiels leagues/teams/squads disponibles.
- Le module reference/ permet de lire les JSON docs/.
- On doit maintenant ingérer les matchs passés et futurs.
- Les features auront besoin des X derniers matchs avant une fixture cible.
- Les standings doivent être snapshotés avec date.
- Les fixtures issues des docs/ peuvent servir d’exemples ou de seed léger, mais les fixtures dynamiques doivent être snapshotées depuis l’API ou stockées en DB.

Objectif :
Créer l’ingestion des fixtures et standings.

Contraintes :
- Supporter ingestion par league + season.
- Supporter ingestion par date.
- Supporter ingestion par team + last N.
- Supporter ingestion next N.
- Stocker les fixtures terminées et futures.
- Les standings doivent être snapshotés avec fetched_at ou snapshot_date.
- Les payloads bruts doivent être conservés.
- Ne pas utiliser de données futures dans les futurs feature builders.
- Ajouter commandes CLI.
- Tests sans réseau.
- Aucun ID API-Football inventé dans tests réalistes : utiliser docs/api_football_reference.json ou données synthétiques marquées.
- Si des fixtures présentes dans docs/api_football_reference.json sont chargées, elles doivent être marquées comme source docs/reference, pas comme snapshot live récent.

À planifier :
1. Services d’ingestion.
2. Parsers fixtures.
3. Parsers standings.
4. Usage éventuel des références docs/ pour fixtures et IDs.
5. CLI.
6. Tests.
7. Risques anti data leakage.
8. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 5.

Avant de modifier, relis AGENTS.md et blueprint.md.
Utilise docs/api_football_reference.json pour les IDs de tests réalistes, ou marque les données comme synthétiques.
Ne fais aucun appel réseau dans les tests.

Crée :
- src/football_predictor/ingestion/ingest_fixtures.py
- src/football_predictor/ingestion/ingest_standings.py
- tests/fixtures/api/fixtures_finished.json
- tests/fixtures/api/fixtures_upcoming.json
- tests/fixtures/api/standings.json
- tests/test_ingest_fixtures.py
- tests/test_ingest_standings.py

Fonctionnalités fixtures :
1. Méthodes :
   - ingest_fixtures_by_league_season(league_id, season)
   - ingest_fixtures_by_date(date, league_id=None, season=None)
   - ingest_team_last_fixtures(team_id, n, season=None)
   - ingest_team_next_fixtures(team_id, n, season=None)
2. Parser Fixture :
   - fixture_id
   - date
   - timezone
   - status_short
   - status_long
   - elapsed
   - league_id
   - season
   - round
   - home_team_id
   - away_team_id
   - goals
   - venue
   - payload_json
3. Upsert idempotent.
4. Raw snapshot.
5. Validation optionnelle via reference lookups si les IDs sont présents dans docs/api_football_reference.json.
6. Tolérance si un ID live n’est pas encore dans le référentiel docs/ : ne pas bloquer l’ingestion live, mais logger clairement.

Fonctionnalités standings :
1. Méthode ingest_standings(league_id, season).
2. Stocker StandingSnapshot par team.
3. Inclure snapshot_date/fetched_at.
4. Conserver payload brut.
5. Ne jamais écraser les snapshots temporels utiles.

CLI :
- football-predictor ingest-fixtures --league 39 --season 2025
- football-predictor ingest-fixtures --date 2026-05-02
- football-predictor ingest-standings --league 39 --season 2025

Important pour les exemples CLI dans README :
- si tu utilises league 39 ou autre ID, vérifie qu’il existe dans docs/api_football_reference.json ; sinon utilise une variable placeholder ou mentionne “exemple à adapter selon docs/api_football_reference.json”.

Tests :
- parsing fixtures terminées.
- parsing fixtures à venir.
- upsert idempotent.
- standings snapshot.
- aucune duplication.
- aucun appel réseau.
- IDs réalistes issus de samples docs/ ou données synthétiques explicitement marquées.

Mets à jour README.md.
```

## Done

```text
- Matchs passés et futurs stockés.
- Standings snapshotés.
- CLI d’ingestion utilisable.
- Tests sans réseau.
```

---

# Sprint 6 — Ingestion stats match, events, lineups, joueurs, blessures, prédictions API

## Objectif

Ingestion des données de performance :

```text
fixtures/statistics
fixtures/events
fixtures/lineups
fixtures/players
injuries
predictions
```

C’est le sprint qui prépare les features avancées.

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/api_football_reference.json pour valider les fixture_id/team_id/league_id utilisés dans les tests.
Consulte docs/api_football_players_reference.json pour valider les player_id utilisés dans les tests ou mappings joueurs.
Ne modifie aucun fichier pour l’instant.

Sprint 6 : ingestion des données détaillées de match.

Contexte :
- Fixtures et standings sont stockés.
- Les référentiels docs/ et le module reference/ existent.
- On doit enrichir chaque fixture avec les statistiques détaillées.
- API-Football fournit notamment fixtures/statistics, events, lineups, players, injuries, predictions.
- Les lineups peuvent être disponibles seulement 20 à 40 minutes avant le match selon coverage.
- Les blessures peuvent être appelées par fixture, team, league, date.
- Les predictions API-Football doivent être stockées comme signal externe.
- Les joueurs inconnus rencontrés dans lineups/injuries/player stats doivent être upsertés prudemment avec payload, mais sans inventer leur identité si absente.

Objectif :
Créer une ingestion détaillée par fixture et par lot.

Contraintes :
- Idempotence.
- Raw snapshots.
- Gestion 204 No Content sans échec.
- Les lineups et player stats peuvent manquer selon coverage.
- Les parsers doivent tolérer les champs manquants.
- Stocker JSON complet pour audit.
- Ajouter CLI.
- Tests sans réseau.
- Aucun ID inventé : utiliser docs/api_football_reference.json et docs/api_football_players_reference.json pour les tests réalistes, ou marquer les données synthétiques.
- fetched_at doit être enregistré pour tout ce qui sera utilisé point-in-time.

À planifier :
1. Services d’ingestion détaillée.
2. Parsers par endpoint.
3. Gestion des données manquantes.
4. Upsert des joueurs inconnus depuis payload API.
5. Usage des références joueurs comme fallback.
6. CLI.
7. Tests.
8. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 6.

Avant de modifier, relis AGENTS.md et blueprint.md.
Utilise les références docs/ pour valider les IDs de tests réalistes.
Ne fais aucun appel réseau dans les tests.

Crée :
- src/football_predictor/ingestion/ingest_match_details.py
- tests/fixtures/api/fixture_statistics.json
- tests/fixtures/api/fixture_events.json
- tests/fixtures/api/fixture_lineups.json
- tests/fixtures/api/fixture_players.json
- tests/fixtures/api/injuries.json
- tests/fixtures/api/predictions.json
- tests/test_ingest_match_details.py

Fonctionnalités :
1. ingest_fixture_statistics(fixture_id)
   - endpoint /fixtures/statistics
   - parse en FixtureStatistics par team.
   - stocke statistics_json.
   - stocke fetched_at.

2. ingest_fixture_events(fixture_id)
   - endpoint /fixtures/events
   - parse goals, cards, subst, var.
   - stocke FixtureEvent.
   - relie player_id et assist_player_id si disponibles.
   - si un joueur n’existe pas encore, prévoir upsert minimal avec payload si possible.

3. ingest_fixture_lineups(fixture_id)
   - endpoint /fixtures/lineups
   - parse formation, coach, startXI, substitutes.
   - stocke FixtureLineup.
   - tolère absence de lineup.
   - stocke fetched_at, car les lineups doivent respecter prediction_time.

4. ingest_fixture_players(fixture_id)
   - endpoint /fixtures/players
   - parse player stats par team et player.
   - extrait si possible rating, minutes, position.
   - stocke FixturePlayerStats.
   - stocke fetched_at.
   - utilise docs/api_football_players_reference.json comme fallback d’identité si utile, sans appel réseau.

5. ingest_injuries_for_fixture(fixture_id)
   - endpoint /injuries?fixture=...
   - parse Injury.
   - tolère absence de données.
   - stocke fetched_at, car les blessures doivent respecter prediction_time.
   - relie aux joueurs du référentiel si possible.

6. ingest_api_prediction(fixture_id)
   - endpoint /predictions
   - stocke ApiPredictionSnapshot.
   - parse percent home/draw/away même si format string "45%".
   - stocke fetched_at.

7. ingest_full_fixture_details(fixture_id)
   - appelle tous les endpoints ci-dessus.
   - continue même si certains endpoints retournent 204.
   - log les endpoints manquants.
   - ne bloque pas tout le pipeline pour une source optionnelle absente.

CLI :
- football-predictor ingest-fixture-details --fixture 123456
- football-predictor ingest-fixture-details --league 39 --season 2025 --status FT
- option --include-upcoming
- option --save-raw

Important pour README : si un fixture_id ou league_id concret est utilisé, vérifier qu’il existe dans docs/api_football_reference.json ou le remplacer par un placeholder.

Tests :
- chaque parser.
- idempotence.
- 204 no content.
- payloads avec champs manquants.
- prediction percent parsing.
- fetched_at présent.
- aucun appel réseau.
- IDs réalistes vérifiés ou données synthétiques marquées.

Mets à jour README.md.
```

## Done

```text
- Tous les détails match sont ingérables.
- Les données manquantes ne cassent pas le pipeline.
- Les prédictions API sont stockées.
- Les timestamps nécessaires au point-in-time sont présents.
```

---

# Sprint 7 — Ingestion odds et moteur de probabilités marché

## Objectif

Créer le module odds :

```text
récupération odds pré-match
bookmakers
bets
mapping
conversion odds -> probabilités
suppression marge bookmaker
consensus bookmaker
mouvement de cotes
dispersion marché
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/api_football_reference.md pour comprendre les bookmakers et bets.
Consulte docs/api_football_reference.json pour valider ou charger bookmaker_id, bet_id, fixture_id, league_id et team_id.
Ne modifie aucun fichier pour l’instant.

Sprint 7 : ingestion odds et probabilités marché.

Contexte :
- Les fixtures sont stockées.
- On dispose de l’endpoint /odds pour les odds pré-match.
- Les fichiers docs/ contiennent des références bookmakers et bets.
- L’objectif est de transformer les odds 1X2 en probabilités implicites sans marge.
- On veut stocker plusieurs snapshots pour mesurer le mouvement des cotes.
- Les odds peuvent être paginées.
- Les bookmakers et bets doivent être référencés.

Objectif :
Créer ingestion odds + feature market probabilities.

Contraintes :
- Supporter /odds?fixture=...
- Supporter /odds?date=...
- Supporter /odds?league=...&season=...
- Supporter pagination.
- Identifier le bet 1X2 / Match Winner de manière configurable.
- Utiliser docs/api_football_reference.json pour valider les bookmakers/bets quand possible.
- Ne pas supposer qu’un bookmaker ou bet existe pour tous les matchs.
- Convertir odds décimales en probabilités normalisées.
- Calculer overround.
- Calculer consensus pondéré.
- Calculer dispersion entre bookmakers.
- Calculer mouvement si plusieurs snapshots existent.
- Tests sans réseau.
- Ne pas mélanger live odds et pre-match odds dans cette V1.
- Utiliser uniquement des odds snapshots fetched_at <= prediction_time dans les features futures.

À planifier :
1. Tables existantes à utiliser.
2. Ingestion odds.
3. Normalisation bookmaker.
4. Validation/reference bookmaker et bet.
5. Calcul market probabilities.
6. Mouvement des odds.
7. CLI.
8. Tests.
9. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 7.

Avant de modifier, relis AGENTS.md et blueprint.md.
Utilise docs/api_football_reference.json pour les références bookmaker_id et bet_id quand disponibles.
Ne fais aucun appel réseau dans les tests.

Crée :
- src/football_predictor/ingestion/ingest_odds.py
- src/football_predictor/features/odds_features.py
- tests/fixtures/api/odds_fixture.json
- tests/fixtures/api/odds_multiple_bookmakers.json
- tests/test_ingest_odds.py
- tests/test_odds_features.py

Fonctionnalités ingestion :
1. ingest_odds_for_fixture(fixture_id, bookmaker=None, bet=None)
2. ingest_odds_by_date(date, league_id=None, season=None, bookmaker=None, bet=None)
3. ingest_odds_by_league_season(league_id, season, bookmaker=None, bet=None)
4. Pagination.
5. Stockage OddsSnapshot avec :
   - fixture_id
   - league_id
   - season
   - bookmaker_id
   - bookmaker_name
   - bet_id
   - bet_name
   - values_json
   - payload_json
   - fetched_at
6. Validation optionnelle des bookmaker_id et bet_id via reference lookups.
7. Tolérance si un bookmaker live n’est pas dans docs/ : logger, ne pas bloquer.

Fonctionnalités odds_features :
1. decimal_odds_to_implied_probabilities(home, draw, away)
   - q = 1 / odd
   - p = q / sum(q)
   - overround = sum(q) - 1

2. extract_1x2_values(values_json)
   - supporte labels Home, Draw, Away
   - supporte labels avec noms d’équipes si présents
   - robuste aux variations de casse
   - ne suppose pas que les labels sont toujours identiques selon bookmaker.

3. compute_market_consensus(fixture_id, as_of_time=None)
   - récupère le dernier snapshot par bookmaker avant as_of_time.
   - calcule p_market_home, p_market_draw, p_market_away.
   - pondère par inverse de l’overround.
   - calcule market_confidence = max(p) - second_best(p).
   - calcule bookmaker_count.
   - calcule market_dispersion.
   - si as_of_time est fourni, ignore tout snapshot fetched_at > as_of_time.

4. compute_odds_movement(fixture_id, current_time)
   - compare premier snapshot disponible et dernier snapshot avant current_time.
   - retourne delta_home, delta_draw, delta_away.
   - ne regarde jamais de snapshot postérieur à current_time.

CLI :
- football-predictor ingest-odds --fixture 123456
- football-predictor odds-features --fixture 123456

Pour les exemples CLI, vérifier les IDs dans docs/api_football_reference.json ou utiliser placeholders.

Tests :
- conversion odds.
- overround.
- consensus multi-bookmakers.
- mouvement odds.
- labels robustes.
- snapshot avant as_of_time uniquement.
- bookmaker/bet lookup quand disponible.
- aucun appel réseau.

Mets à jour README.md et docs/data_contract.md.
```

## Done

```text
- Probabilités marché disponibles.
- Odds movement disponible.
- Marge bookmaker retirée.
- Bookmakers et bets reliés aux références quand possible.
```

---

# Sprint 8 — Features équipe : forme, domicile/extérieur, stats avancées, pseudo-xG

## Objectif

Créer les features équipe :

```text
forme last_3/5/10/15
EWMA
domicile/extérieur
buts pour/contre
tirs
tirs cadrés
tirs dans la surface
possession
passes
corners
cartons
fautes
clean sheets
failed to score
stats ajustées adversaire
pseudo-xG
repos
calendrier
classement
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/api_football_reference.json uniquement si des IDs de ligue, équipe ou fixture sont nécessaires pour des tests réalistes.
Ne modifie aucun fichier pour l’instant.

Sprint 8 : features équipe.

Contexte :
- Fixtures, standings, fixture_statistics et events sont stockés.
- Les référentiels docs/ servent aux IDs et au contexte, mais les features dynamiques doivent venir des snapshots DB et respecter prediction_time.
- On doit calculer des features point-in-time pour une fixture cible.
- Les features doivent utiliser uniquement les matchs terminés avant la date de prédiction.
- On veut plusieurs fenêtres : last_3, last_5, last_10, last_15 et EWMA.
- On veut séparer global, domicile et extérieur.
- On veut intégrer les stats de performance : shots, shots on goal, shots inside box, possession, passes, corners, fouls, cards, goalkeeper saves.
- API-Football ne garantit pas xG dans le PDF fourni ; on veut donc créer un pseudo-xG à partir des stats disponibles.

Objectif :
Créer le moteur de features équipe.

Contraintes :
- Aucun accès au futur.
- Toutes les fonctions prennent fixture_id et prediction_time.
- Les fonctions retournent un dict plat sérialisable JSON.
- Les noms de features doivent être stables et documentés.
- Les données manquantes doivent être imputées ou marquées avec flags.
- Ajouter data_quality flags.
- Tests avec petites fixtures synthétiques ou IDs issus des docs JSON.
- Ne pas entraîner encore de modèle.
- Exclure toujours la fixture cible.
- Ne jamais utiliser /teams/statistics sans paramètre date ou snapshot historique lorsqu’on reconstruit un match passé.

À planifier :
1. API publique du feature builder.
2. Liste des features.
3. Gestion fenêtres temporelles.
4. EWMA.
5. Stats ajustées adversaire.
6. Pseudo-xG heuristique initial.
7. Data quality.
8. Tests anti data leakage.
9. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 8.

Avant de modifier, relis AGENTS.md et blueprint.md.
Respecte strictement fixture_id + prediction_time.
Ne fais aucun appel réseau dans les tests.
Utilise docs/api_football_reference.json pour les IDs réalistes si nécessaire, sinon marque les données comme synthétiques.

Crée :
- src/football_predictor/features/team_features.py
- src/football_predictor/features/stat_parsing.py
- src/football_predictor/features/pseudo_xg.py
- src/football_predictor/features/context_features.py
- tests/test_team_features.py
- tests/test_pseudo_xg.py

Fonctionnalités :
1. build_team_features(fixture_id, prediction_time)
   - retourne features pour home et away.
   - utilise uniquement fixtures avec date < prediction_time et status terminé.
   - exclut toujours la fixture cible.

2. Fenêtres :
   - last_3
   - last_5
   - last_10
   - last_15
   - ewma

3. Résultats :
   - points_per_game
   - win_rate
   - draw_rate
   - loss_rate
   - goals_for_avg
   - goals_against_avg
   - goal_diff_avg
   - clean_sheet_rate
   - failed_to_score_rate

4. Home/Away :
   - pour home team : features globales + domicile.
   - pour away team : features globales + extérieur.
   - noms explicites : home_team_home_last5_ppg, away_team_away_last5_ppg, etc.

5. Fixture statistics :
   Parser les types :
   - Shots on Goal
   - Shots off Goal
   - Shots insidebox
   - Shots outsidebox
   - Total Shots
   - Blocked Shots
   - Fouls
   - Corner Kicks
   - Offsides
   - Ball Possession
   - Yellow Cards
   - Red Cards
   - Goalkeeper Saves
   - Total passes
   - Passes accurate
   - Passes %

   Calculer moyennes for et against :
   - shots_for_avg
   - shots_against_avg
   - shots_on_goal_for_avg
   - shots_on_goal_against_avg
   - possession_avg
   - corners_for_avg
   - corners_against_avg
   - cards_avg
   - pass_accuracy_avg

6. Ratios :
   - shot_accuracy = shots_on_goal / total_shots
   - goal_conversion = goals_for / shots_on_goal
   - box_shot_share = shots_insidebox / total_shots
   - save_rate = goalkeeper_saves / shots_on_goal_against

7. Opponent-adjusted :
   - Pour chaque match historique, comparer la stat de l’équipe à la moyenne concédée par l’adversaire avant ce match.
   - Créer au moins :
     - adj_goals_for
     - adj_goals_against
     - adj_shots_for
     - adj_shots_against
     - adj_shots_on_goal_for
     - adj_shots_on_goal_against
   - Vérifier que ce calcul n’utilise jamais des matchs postérieurs au match historique évalué.

8. Pseudo-xG :
   - Créer une fonction heuristic_pseudo_xg(stats):
     pseudo_xg = pondération basée sur shots_on_goal, shots_insidebox, shots_outsidebox, total_shots, penalties si events disponibles.
   - Documenter que c’est une approximation initiale.
   - Retourner pseudo_xg_for_avg et pseudo_xg_against_avg.

9. Context features :
   - rest_days_home
   - rest_days_away
   - matches_last_7_days
   - matches_last_14_days
   - travel proxy simple : away flag seulement pour V1
   - round number si extractible

10. Standings features :
   - rank
   - points
   - goals_diff
   - ppg standings
   - rank_diff
   - points_diff
   - goals_diff_diff
   - utiliser le dernier snapshot disponible avant prediction_time.

11. Data quality :
   - number of historical matches found.
   - missing_statistics_rate.
   - standings_available flag.

Tests :
- aucune fixture future utilisée.
- fixture cible exclue.
- fenêtres correctes.
- home/away split correct.
- parser stats avec valeurs "55%" et nombres.
- pseudo_xg stable.
- data_quality retourné.
- standings postérieurs à prediction_time ignorés.

Mets à jour docs/data_contract.md avec les features équipe.
```

## Done

```text
- Features équipe point-in-time.
- Fenêtres multiples.
- Stats avancées.
- Pseudo-xG initial.
- Tests anti-fuite.
```

---

# Sprint 9 — Features joueurs, XI type, absences et remplacement

## Objectif

Créer le module le plus différenciant :

```text
forme joueur
valeur joueur par poste
XI type
XI probable
formation probable
stabilité du XI
absents
impact absence
qualité remplaçant
paires stables
```

## Mode Codex

```text
Plan mode très important
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte obligatoirement docs/api_football_players_reference.md et docs/api_football_players_reference.json pour comprendre et valider les joueurs, player_id, team_id, postes, numéros et effectifs.
Consulte docs/api_football_reference.json si tu as besoin de valider fixture_id, team_id ou league_id.
Ne modifie aucun fichier pour l’instant.

Sprint 9 : features joueurs, XI type, absences et remplacement.

Contexte :
- Les lineups passées sont stockées.
- Les player stats par fixture sont stockées.
- Les injuries sont stockées.
- Les référentiels joueurs docs/ contiennent 4645 joueurs liés à team_id, compétition, saison et équipe.
- On veut construire un XI type/probable pour chaque équipe avant un match.
- On veut calculer l’impact des absences du XI type.
- On veut valoriser les joueurs par poste avec des métriques adaptées.
- Le modèle doit être robuste même si les stats joueurs sont partielles.
- Le référentiel joueurs doit servir de fallback d’identité et de poste quand les lineups/player stats sont absentes ou partielles.

Objectif :
Créer le moteur de features joueurs et XI.

Contraintes :
- Point-in-time strict : uniquement matchs avant prediction_time.
- Construire formation probable depuis les lineups des N derniers matchs.
- Construire P_start par joueur.
- Construire player_value normalisé par poste.
- Construire expected_xi avec contraintes poste/formation si possible.
- Intégrer injuries du fixture cible et/ou injuries connues avant prediction_time.
- Calculer absence impact = P_start * player_value * severity * replacement_gap.
- Calculer replacement_gap en comparant le joueur absent au meilleur remplaçant probable.
- Gérer les données manquantes avec flags.
- Ajouter tests sur lineups synthétiques ou IDs issus des docs JSON.
- Ne pas entraîner encore de modèle.
- Ne jamais comparer directement un GK, DEF, MID et ATT sans normalisation par poste.
- Ne jamais pénaliser fortement un joueur absent s’il n’était probablement pas titulaire.
- Ne jamais utiliser une injury ou lineup avec fetched_at > prediction_time.

À planifier :
1. Structures de données.
2. Usage du référentiel joueurs local comme fallback.
3. Calcul P_start.
4. Calcul formation probable.
5. Calcul player_value par poste.
6. Construction XI probable.
7. Injury severity.
8. Replacement gap.
9. Features finales.
10. Tests anti data leakage.
11. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 9.

Avant de modifier, relis AGENTS.md et blueprint.md.
Utilise docs/api_football_players_reference.json comme source structurée pour les joueurs et effectifs lorsque c’est utile.
Utilise docs/api_football_players_reference.md pour comprendre le référentiel humainement si nécessaire.
Ne fais aucun appel réseau dans les tests.
Respecte strictement prediction_time.

Crée :
- src/football_predictor/features/player_features.py
- src/football_predictor/features/xi_features.py
- src/football_predictor/features/availability_features.py
- tests/test_player_features.py
- tests/test_xi_features.py
- tests/test_availability_features.py

Fonctionnalités player_features :
1. build_player_recent_form(team_id, prediction_time, windows=(3,5,10))
   - minutes récentes
   - starts récents
   - average rating
   - goals si disponible dans events ou player stats
   - assists si disponible
   - cards
   - position la plus fréquente
   - last_match_minutes
   - ewma_minutes
   - ewma_rating
   - fallback position/identity depuis docs/api_football_players_reference.json si nécessaire.

2. compute_player_value(player_id, team_id, prediction_time)
   - normalisation par position.
   - poste GK, DEF, MID, ATT.
   - utilise rating, minutes, starts, contribution events, discipline.
   - retourne value_zscore et value_0_100.
   - robuste si rating absent.
   - utilise référentiel joueurs local comme fallback si les stats sont pauvres.

Fonctionnalités xi_features :
1. infer_probable_formation(team_id, prediction_time, n_matches=10)
   - formation la plus fréquente pondérée par récence.
   - retourne formation, confidence, formation_stability.

2. compute_start_probability(player_id, team_id, prediction_time)
   Formule initiale :
   - 0.50 * weighted_start_frequency
   - 0.25 * weighted_minutes_share
   - 0.15 * formation_position_compatibility
   - 0.10 * recent_availability
   Retourne 0..1.

3. build_expected_xi(team_id, prediction_time, fixture_id=None)
   - utilise les N derniers lineups.
   - exclut les joueurs indisponibles confirmés.
   - respecte si possible 1 GK et une structure cohérente selon formation.
   - utilise docs/api_football_players_reference.json pour enrichir les candidats si les données lineup sont insuffisantes.
   - retourne 11 joueurs + bench_candidates.
   - chaque joueur a player_id, name, position, p_start, player_value, expected_role.

4. xi_stability_features(team_id, prediction_time)
   - xi_stability_score
   - avg_starts_in_last5_for_expected_xi
   - formation_stability
   - gk_stability
   - defensive_line_stability proxy
   - pair_stability_score basé sur co-titularisations.

Fonctionnalités availability_features :
1. parse_injury_severity(injury)
   - Missing Fixture ou similaire : 1.0
   - Questionable ou incertain : 0.6
   - mineur/inconnu : 0.3
   - valeur par défaut documentée.

2. compute_absence_impact(team_id, fixture_id, prediction_time)
   - récupère injuries fixture/team.
   - ignore les injuries avec fetched_at > prediction_time.
   - identifie les absents dans le XI probable.
   - calcule replacement_gap.
   - applique multiplicateur poste :
     GK 1.30
     ATT 1.25
     MID créatif si détectable 1.20
     DEF central proxy 1.10
     autres 1.00
   - retourne :
     absent_expected_starters_count
     absent_total_value
     absence_impact_score
     replacement_quality_score
     availability_score

3. build_player_xi_features(fixture_id, prediction_time)
   - calcule pour home et away :
     - expected_xi_avg_value
     - expected_xi_total_value
     - bench_depth_score
     - xi_stability_score
     - formation_stability
     - absence_impact_score
     - absent_expected_starters_count
     - replacement_quality_score
     - availability_score
     - key_absences_json

Tests :
- formation probable.
- P_start pondéré par récence.
- XI contient 11 joueurs si assez de données.
- blessé titulaire baisse availability_score.
- blessé remplaçant impact faible.
- replacement_gap fonctionne.
- pas de données futures.
- injury postérieure à prediction_time ignorée.
- lineup postérieure à prediction_time ignorée.
- cas sans lineups ne casse pas et retourne flags.
- fallback depuis docs/api_football_players_reference.json testé sur sample.

Mets à jour docs/modeling_strategy.md et docs/data_contract.md.
```

## Done

```text
- XI type calculable.
- Absences pondérées.
- Score remplaçant.
- Features joueurs intégrées.
- Référentiel joueurs docs/ utilisé comme fallback propre.
```

---

# Sprint 10 — Feature builder global et dataset d’entraînement point-in-time

## Objectif

Créer le constructeur central :

```text
fixture_id + prediction_time -> features_json
```

Puis construire un dataset historique :

```text
X features
y target Home/Draw/Away
metadata
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte les docs JSON uniquement pour valider les IDs des tests ou fixtures réalistes. Les features dynamiques doivent venir de snapshots DB point-in-time, pas directement des docs statiques sauf fallback de référence.
Ne modifie aucun fichier pour l’instant.

Sprint 10 : feature builder global et dataset d’entraînement point-in-time.

Contexte :
- Features équipe disponibles.
- Features odds disponibles.
- Features joueurs/XI disponibles.
- Référentiels docs/ disponibles pour validation et fallback statique.
- On doit produire un snapshot complet de features pour une fixture et un prediction_time.
- On doit construire un dataset historique pour entraîner le modèle.
- La fuite de données est le risque principal.

Objectif :
Créer :
1. build_feature_snapshot(fixture_id, prediction_time)
2. build_training_dataset(league_ids, seasons, cutoff rules)

Contraintes :
- Point-in-time strict.
- Exclure la fixture cible des features.
- Les odds doivent utiliser uniquement les snapshots avant prediction_time.
- Les injuries doivent utiliser uniquement les données disponibles avant prediction_time quand fetched_at existe.
- Les standings doivent utiliser le dernier snapshot avant prediction_time.
- Les lineups officielles ne doivent être utilisées que si fetched_at <= prediction_time.
- Pour l’entraînement historique, simuler prediction_time par défaut à fixture.date - 24h, avec option -6h ou -40min si snapshots disponibles.
- Stocker FeatureSnapshot.
- Retourner features plates JSON.
- Ajouter data_quality_score.
- Tests anti-fuite.
- Export parquet/csv.
- Les docs/ ne doivent pas être utilisées comme source de résultats futurs ou de features dynamiques postérieures.
- Aucun ID inventé dans les tests réalistes.

À planifier :
1. API feature builder.
2. Fusion features.
3. Usage limité des références docs/.
4. Data quality.
5. Dataset builder.
6. Target encoding.
7. Tests anti-leakage.
8. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 10.

Avant de modifier, relis AGENTS.md et blueprint.md.
Respecte strictement les règles point-in-time.
Ne fais aucun appel réseau dans les tests.

Crée :
- src/football_predictor/features/feature_builder.py
- src/football_predictor/features/data_quality.py
- src/football_predictor/backtesting/dataset_builder.py
- tests/test_feature_builder.py
- tests/test_dataset_builder.py

Fonctionnalités feature_builder :
1. build_feature_snapshot(fixture_id, prediction_time, feature_version="v1")
   - récupère fixture.
   - appelle :
     - build_team_features
     - build_player_xi_features
     - compute_market_consensus
     - compute_odds_movement
     - API prediction snapshot le plus récent avant prediction_time
     - context features
   - fusionne dans un dict plat.
   - ajoute :
     - fixture_id
     - league_id
     - season
     - prediction_time
     - home_team_id
     - away_team_id
   - ne met pas la target dans features_json.
   - stocke FeatureSnapshot.
   - retourne FeatureSnapshot + dict.
   - ne lit pas les résultats finaux sauf pour metadata non utilisée comme feature.

2. Data quality :
   - historical_matches_home_count
   - historical_matches_away_count
   - team_stats_available_rate
   - player_stats_available_rate
   - lineups_available_flag
   - injuries_available_flag
   - odds_available_flag
   - api_prediction_available_flag
   - reference_docs_available_flag
   - overall_data_quality_score 0..100

3. API predictions :
   - récupérer dernier ApiPredictionSnapshot avant prediction_time.
   - parser percent_home/draw/away.
   - features :
     - api_pred_home
     - api_pred_draw
     - api_pred_away
     - api_pred_winner_home_flag
     - api_pred_winner_away_flag
     - api_pred_win_or_draw_flag

Fonctionnalités dataset_builder :
1. build_training_dataset(league_ids, seasons, prediction_offset_hours=24)
   - pour chaque fixture terminée :
     - prediction_time = fixture.date - offset
     - build_feature_snapshot
     - target :
       HOME si home_goals > away_goals
       DRAW si égalité
       AWAY si home_goals < away_goals
   - retourne pandas DataFrame.
   - option save_path en parquet/csv.
   - inclut metadata séparée ou colonnes metadata.

2. Splits temporels :
   - create_time_based_split(df, train_until, valid_until)
   - jamais de shuffle par défaut.

Tests :
- target correcte.
- fixture cible exclue.
- odds après prediction_time ignorées.
- API prediction après prediction_time ignorée.
- lineups après prediction_time ignorées.
- injuries après prediction_time ignorées.
- standings après prediction_time ignorés.
- FeatureSnapshot créé.
- Data quality score borné 0..100.
- aucun appel réseau.

Mets à jour README.md avec commande prévue dataset et docs/data_contract.md.
```

## Done

```text
- Une fixture peut produire un feature snapshot complet.
- Dataset historique entraînable.
- Tests anti data leakage en place.
```

---

# Sprint 11 — Modèles : Poisson, ML multiclass, stacking, calibration

## Objectif

Créer le moteur de prédiction :

```text
modèle sportif
modèle odds
modèle API prediction
stacking
calibration
fallback
```

Pour la V1 robuste, recommandation :

```text
baseline odds-only
baseline poisson
modèle ML multiclass
stacking final
calibration
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/modeling_strategy.md et docs/data_contract.md si présents.
Les docs/api_football_*.json ne sont nécessaires ici que pour comprendre les metadata ou fixtures de tests ; n’invente aucun ID.
Ne modifie aucun fichier pour l’instant.

Sprint 11 : modèles de prédiction.

Contexte :
- Le dataset d’entraînement peut être construit.
- On veut prédire P(Home), P(Draw), P(Away).
- Les odds sont un signal fort.
- Le modèle sportif doit utiliser les features équipe, joueurs, XI, absences, contexte.
- On veut un fallback si le modèle entraîné n’existe pas.
- Les probabilités doivent être calibrées et évaluables.

Objectif :
Créer un module modeling complet :
1. Baseline odds-only.
2. Baseline Poisson simple.
3. Modèle ML multiclass.
4. Stacking/blending final.
5. Calibration.
6. Sauvegarde/chargement modèle.

Contraintes :
- Sorties probabilistes toujours normalisées.
- Classes fixes : HOME, DRAW, AWAY.
- Évaluation avec log loss et Brier.
- Calibration optionnelle.
- Le modèle doit gérer features manquantes.
- Ne pas rendre CatBoost obligatoire si installation compliquée : prévoir fallback sklearn.
- Sauvegarder model artifact dans data/models.
- Inclure model_version.
- Tests unitaires avec dataset synthétique.
- Ne pas entraîner avec metadata interdites ou target leakage.
- Ne pas utiliser fixture_id/team_id comme signal naïf si cela risque d’overfitter, sauf encodage contrôlé et justifié.

À planifier :
1. Choix modèle par défaut.
2. Interfaces.
3. Baselines.
4. Stacking.
5. Calibration.
6. Sauvegarde.
7. Tests.
8. Contrôle anti target leakage.
9. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 11.

Avant de modifier, relis AGENTS.md et blueprint.md.
Assure-toi que les modèles ne consomment pas la target, les scores finaux ou des champs post-match dans X.
Ne fais aucun appel réseau dans les tests.

Crée :
- src/football_predictor/modeling/constants.py
- src/football_predictor/modeling/preprocessing.py
- src/football_predictor/modeling/poisson.py
- src/football_predictor/modeling/baselines.py
- src/football_predictor/modeling/multiclass_model.py
- src/football_predictor/modeling/stacking.py
- src/football_predictor/modeling/calibration.py
- src/football_predictor/modeling/train.py
- tests/test_modeling_baselines.py
- tests/test_modeling_training.py
- tests/test_stacking.py

Fonctionnalités :
1. constants.py :
   - CLASSES = ["HOME", "DRAW", "AWAY"]

2. preprocessing.py :
   - séparer metadata, target, features.
   - convertir features dict en DataFrame numérique.
   - gérer booléens.
   - imputer valeurs manquantes.
   - conserver feature_names.
   - exclure explicitement target, home_goals, away_goals, score final, status post-match et tout champ interdit.

3. baselines.py :
   - odds_only_predict(features)
     utilise p_market_home/draw/away si présents.
     sinon retourne prior league ou [0.45, 0.27, 0.28] configurable.
   - api_prediction_predict(features)
     utilise api_pred_home/draw/away si présents.
   - uniform_predict fallback.

4. poisson.py :
   - estimate_lambda_home_away(features)
     première version heuristique :
     λ_home basé sur goals_for, opponent goals_against, pseudo_xg, home advantage.
     λ_away idem.
   - score_matrix jusqu’à 8 buts.
   - convertir en P(Home/Draw/Away).

5. multiclass_model.py :
   - classe FootballOutcomeModel.
   - modèle par défaut sklearn HistGradientBoostingClassifier ou LogisticRegression fallback.
   - fit(X, y)
   - predict_proba(X)
   - save(path)
   - load(path)
   - model_version.

6. stacking.py :
   - blend_probabilities(p_sport, p_market, p_api, weights)
   - utiliser log probabilities + softmax.
   - poids par défaut :
     sport 0.55
     market 0.35
     api 0.10
   - si market manquant, redistribuer.
   - si api manquant, redistribuer.
   - probabilités toujours normalisées.

7. calibration.py :
   - wrapper CalibratedClassifierCV si applicable.
   - ou temperature scaling simple.
   - fonction calibrate_probabilities.

8. train.py :
   - train_model_from_dataset(dataset_path, output_dir)
   - split temporel si colonnes date disponibles.
   - sauvegarde :
     - model.joblib
     - metadata.json
     - feature_names.json
     - metrics.json

9. CLI :
   - football-predictor train --dataset data/processed/training.parquet --output-dir data/models/v1

Tests :
- probabilités somment à 1.
- classes dans bon ordre.
- fallback odds-only.
- poisson produit proba valide.
- stacking avec données manquantes.
- modèle sauvegarde/charge.
- entraînement sur dataset synthétique.
- preprocessing exclut les colonnes de target leakage.

Mets à jour docs/modeling_strategy.md et README.md.
```

## Done

```text
- Modèle entraînable.
- Probabilités valides.
- Stacking final disponible.
- Sauvegarde/chargement OK.
- Colonnes de fuite exclues.
```

---

# Sprint 12 — Backtesting, évaluation, calibration report

## Objectif

Mesurer sérieusement la performance :

```text
accuracy 1X2
log loss
Brier score
calibration curve
comparaison odds-only
comparaison API prediction
comparaison poisson
performance par ligue
performance par niveau de confiance
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/modeling_strategy.md et docs/data_contract.md.
Ne modifie aucun fichier pour l’instant.

Sprint 12 : backtesting et évaluation.

Contexte :
- Le dataset historique existe.
- Les modèles existent.
- On doit mesurer la performance proprement.
- L’accuracy seule est insuffisante.
- On veut comparer le modèle final à des baselines : odds-only, poisson, api-prediction-only.
- Le backtesting doit respecter l’ordre temporel et ne jamais mélanger futur et passé.

Objectif :
Créer un module backtesting complet avec rapports.

Contraintes :
- Split temporel obligatoire par défaut.
- Pas de shuffle par défaut.
- Métriques :
  - accuracy
  - log loss
  - Brier score multiclass
  - calibration bins
  - confusion matrix
  - coverage par seuil de confiance
  - accuracy par seuil de confiance
  - performance par ligue
  - performance par saison
- Export JSON + Markdown.
- Tests avec dataset synthétique.
- Pas besoin de graphiques dans V1, mais prévoir données pour graphiques.
- Le rapport doit indiquer clairement les périodes train/validation/test.
- Les colonnes de fuite doivent être absentes de l’évaluation.

À planifier :
1. Design evaluator.
2. Baselines.
3. Metrics.
4. Reports.
5. CLI.
6. Tests.
7. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 12.

Avant de modifier, relis AGENTS.md et blueprint.md.
Le backtest doit être temporel, sans shuffle par défaut.
Ne fais aucun appel réseau dans les tests.

Crée :
- src/football_predictor/backtesting/metrics.py
- src/football_predictor/backtesting/evaluator.py
- src/football_predictor/backtesting/reports.py
- tests/test_backtesting_metrics.py
- tests/test_backtesting_evaluator.py

Fonctionnalités metrics.py :
1. multiclass_brier_score(y_true, proba, classes)
2. accuracy_score_1x2(y_true, proba)
3. log_loss_safe(y_true, proba)
4. confidence_gap(proba)
5. calibration_bins(y_true, proba, n_bins=10)

Fonctionnalités evaluator.py :
1. evaluate_predictions(df, y_true, proba_columns)
2. compare_models :
   - final_model
   - odds_only
   - poisson
   - api_prediction
3. group metrics :
   - by league_id
   - by season
   - by confidence bucket
   - by data_quality bucket
4. Vérifier et documenter que l’évaluation utilise les probabilités produites point-in-time.

Fonctionnalités reports.py :
1. export_metrics_json(metrics, path)
2. export_markdown_report(metrics, path)
3. Format markdown clair :
   - résumé global
   - tableau comparaison modèles
   - performance par ligue
   - calibration
   - seuils de confiance
   - période évaluée
   - avertissement si data_quality faible.

CLI :
- football-predictor backtest --dataset data/processed/training.parquet --model-dir data/models/v1 --output-dir reports/backtest_v1

Tests :
- log loss stable.
- brier score borné.
- confidence gap correct.
- group metrics.
- markdown généré.
- pas de shuffle implicite.

Mets à jour README.md.
```

## Done

```text
- Backtest complet générable.
- Comparaison avec bookmaker-only.
- Rapport markdown disponible.
- Split temporel respecté.
```

---

# Sprint 13 — Pipeline de prédiction fixture unique

## Objectif

Créer la commande finale :

```text
football-predictor predict --fixture 123456
```

Elle doit :

```text
ingérer les données nécessaires
construire les features
charger le modèle
produire P(Home/Draw/Away)
calculer confiance
expliquer la prédiction
sauvegarder ModelPrediction
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/api_football_reference.json si un fixture_id/team_id/league_id concret est utilisé dans les tests ou exemples.
Consulte docs/api_football_players_reference.json si des joueurs d’exemple sont nécessaires.
Ne modifie aucun fichier pour l’instant.

Sprint 13 : pipeline de prédiction fixture unique.

Contexte :
- Ingestion disponible.
- Feature builder disponible.
- Modèle disponible.
- Backtesting disponible.
- Référentiels docs/ disponibles pour valider les IDs et enrichir les noms.
- On veut maintenant prédire un match donné.

Objectif :
Créer un pipeline predict_fixture robuste.

Contraintes :
- Entrée : fixture_id.
- prediction_time par défaut = now en timezone configurée.
- Option --prediction-time.
- Option --model-dir.
- Option --refresh-data pour appeler l’API avant prédiction.
- Option --no-refresh pour utiliser uniquement la DB.
- Si modèle absent, fallback odds-only + poisson + api.
- Stocker FeatureSnapshot et ModelPrediction.
- Retourner JSON et affichage console rich.
- Ajouter explications lisibles.
- Ne jamais planter si odds ou lineups manquent : baisser data_quality et utiliser fallback.
- Tests avec DB synthétique.
- Aucun ID inventé dans les tests réalistes.
- Si refresh_data=False, aucun appel API live.
- Les données utilisées doivent respecter prediction_time.

À planifier :
1. Pipeline.
2. Refresh data.
3. Chargement modèle.
4. Fallback.
5. Explication.
6. Usage des références docs/ pour noms/validation.
7. Sauvegarde prédiction.
8. CLI.
9. Tests.
10. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 13.

Avant de modifier, relis AGENTS.md et blueprint.md.
Respecte prediction_time.
Ne fais aucun appel réseau dans les tests.
Utilise les références docs/ pour valider ou enrichir les IDs si nécessaire.

Crée :
- src/football_predictor/prediction/predict_fixture.py
- src/football_predictor/prediction/confidence.py
- src/football_predictor/prediction/explain.py
- tests/test_predict_fixture.py
- tests/test_confidence.py
- tests/test_explain.py

Fonctionnalités :
1. predict_fixture(fixture_id, prediction_time=None, model_dir=None, refresh_data=False)
   - récupère fixture depuis DB.
   - si refresh_data=True :
     - refresh fixture details si possible.
     - refresh odds.
     - refresh injuries.
     - refresh predictions API.
     - ne pas échouer globalement si un endpoint manque.
   - si refresh_data=False, ne fait aucun appel API.
   - build_feature_snapshot.
   - charge modèle si model_dir existe.
   - calcule p_sport.
   - calcule p_market.
   - calcule p_api.
   - applique stacking.
   - calcule predicted_outcome.
   - calcule confidence.
   - génère explanation_json.
   - stocke ModelPrediction.

2. confidence.py :
   - confidence_gap.
   - confidence_label :
     - Very High
     - High
     - Medium
     - Low
     - Uncertain
   - règle :
     - p_max < 0.43 ou gap < 0.07 => Uncertain.

3. explain.py :
   - retourner top facteurs :
     - market favorite
     - team form edge
     - home/away edge
     - absence impact edge
     - XI stability edge
     - standings edge
     - pseudo_xG edge
     - odds movement
   - explication en français.
   - ne pas inventer de données : si feature manquante, l’indiquer.
   - utiliser noms d’équipes/joueurs disponibles en DB ou références docs/ si utile.

4. CLI :
   - football-predictor predict --fixture 123456
   - options :
     --prediction-time
     --model-dir
     --refresh-data
     --json-output path
   - affichage console clair.

Tests :
- prédiction avec modèle mock.
- fallback sans modèle.
- odds manquantes.
- injuries manquantes.
- ModelPrediction créé.
- probabilités somment à 1.
- confidence label correct.
- explanations non vides.
- refresh_data=False ne fait pas d’appel API.
- données postérieures à prediction_time ignorées.

Mets à jour README.md.
```

## Done

```text
- Une prédiction fixture complète est possible.
- La sortie est persistée.
- Les explications sont lisibles.
- Le pipeline est robuste aux sources manquantes.
```

---
# REPRENDRE ICI
# Sprint 14 — Formatter Discord markdown

## Objectif

Créer le rendu final dans Discord, en bloc de code markdown.

Format cible :

````text
```md
🏟️ PRÉDICTION FOOTBALL

Match : Arsenal vs Chelsea
Compétition : Premier League
Date : 2026-05-02 18:30 Europe/Paris

Résultat prédit : Arsenal gagne
Confiance : High
Score de confiance : 23.4 pts

Probabilités :
- Domicile : 52.8%
- Nul      : 25.6%
- Extérieur: 21.6%

Marché bookmakers :
- Domicile : 50.1%
- Nul      : 26.7%
- Extérieur: 23.2%
- Bookmakers utilisés : 8

Facteurs clés :
1. Forme domicile supérieure sur les 5 derniers matchs.
2. Chelsea a 2 titulaires probables absents.
3. Arsenal a un XI plus stable.
4. Le marché favorise aussi Arsenal.

Données :
- Qualité data : 87/100
- Lineups officielles : non
- Blessures : oui
- Odds : oui

Note : prédiction probabiliste, pas une certitude.
```
````

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte le format Discord attendu dans blueprint.md, AGENTS.md et docs/product_spec.md.
Consulte les références docs/ uniquement si des noms d’équipes ou joueurs sont nécessaires dans les exemples/tests ; ne devine aucun ID.
Ne modifie aucun fichier pour l’instant.

Sprint 14 : formatter Discord markdown.

Contexte :
- predict_fixture produit une ModelPrediction avec probabilities, confidence et explanations.
- On veut publier sur Discord via webhook.
- L’utilisateur veut un message clair, précis, en markdown, dans un bloc de code.
- Discord a des limites de taille de message de 2000 caractères.
- Il ne faut pas exposer de secrets.
- Le message doit être en français et honnête sur la nature probabiliste de la prédiction.

Objectif :
Créer un formatter Discord robuste.

Contraintes :
- Message en français.
- Bloc de code markdown.
- Format stable et lisible.
- Inclure :
  - match
  - compétition
  - date
  - résultat prédit
  - probabilités
  - confidence
  - odds/market si dispo
  - absences clés si dispo
  - facteurs clés
  - data quality
  - note probabiliste
- Gérer données manquantes.
- Tronquer proprement si message trop long.
- Tests unitaires.
- Ne jamais inclure API key, webhook URL ou secret.
- Ne pas inventer de noms de joueurs absents si key_absences_json est vide ou indisponible.

À planifier :
1. Format message.
2. Données nécessaires.
3. Gestion des absences.
4. Limites Discord.
5. Protection secrets.
6. Tests.
7. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 14.

Avant de modifier, relis AGENTS.md et blueprint.md.
Ne loggue ni n’inclus aucun secret dans le message.
Ne fais aucun appel réseau dans les tests.

Crée ou complète :
- src/football_predictor/discord/formatter.py
- tests/test_discord_formatter.py

Fonctionnalités :
1. format_prediction_markdown(prediction, fixture, features=None) -> str
   - retourne une string commençant par ```md et finissant par ```.
   - message en français.
   - probabilités formatées en pourcentage avec 1 décimale.
   - confidence gap en points.
   - predicted_outcome traduit :
     HOME -> victoire domicile
     DRAW -> match nul
     AWAY -> victoire extérieur.

2. Sections :
   - titre
   - match
   - compétition
   - date
   - résultat prédit
   - probabilités modèle
   - probabilités marché si disponibles
   - facteurs clés
   - absences clés
   - qualité des données
   - note finale

3. Gestion données manquantes :
   - afficher "non disponible" plutôt que planter.
   - ne pas inventer.
   - si les absences clés sont indisponibles, afficher une mention claire.

4. Limite Discord :
   - ajouter fonction truncate_discord_message(message, max_chars=1900)
   - préserver fermeture du bloc de code.
   - éviter de couper au milieu d’une ligne si possible.

5. Tests :
   - message commence/finit par bloc code.
   - probabilités formatées.
   - données manquantes.
   - troncature conserve fermeture.
   - predicted_outcome traduit.
   - aucune URL webhook ou secret n’apparaît.

Mets à jour docs/product_spec.md avec le format Discord.
```

## Done

```text
- Message Discord clair.
- Markdown stable.
- Compatible limite Discord.
- Secrets absents du rendu.
```

---

# Sprint 15 — Webhook Discord et commande d’envoi

## Objectif

Envoyer réellement le message dans Discord.

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/product_spec.md pour le format Discord.
Ne modifie aucun fichier pour l’instant.

Sprint 15 : webhook Discord.

Contexte :
- Le formatter Discord existe.
- On veut envoyer les prédictions dans un salon Discord via webhook.
- L’URL du webhook est dans DISCORD_WEBHOOK_URL.
- Il ne faut jamais logger l’URL complète.

Objectif :
Créer un client webhook Discord + commande CLI.

Contraintes :
- Utiliser httpx.
- Ne pas logger le webhook complet.
- Gérer erreurs HTTP.
- Sauvegarder DiscordMessage en DB.
- Option dry-run.
- Option print-only.
- Tests avec mock HTTP.
- Ne pas faire de vrais appels Discord dans les tests.
- Ne pas envoyer Discord par défaut dans les smoke tests.
- Hash court du webhook autorisé pour traçabilité.

À planifier :
1. Client webhook.
2. Sécurité secrets.
3. CLI.
4. Persistance.
5. Tests.
6. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 15.

Avant de modifier, relis AGENTS.md et blueprint.md.
Ne loggue jamais DISCORD_WEBHOOK_URL complet.
Ne fais aucun appel Discord réel dans les tests.

Crée :
- src/football_predictor/discord/webhook.py
- tests/test_discord_webhook.py

Fonctionnalités :
1. DiscordWebhookClient :
   - init(webhook_url)
   - send_message(content)
   - timeout configurable
   - raise DiscordWebhookError si erreur
   - ne log jamais l’URL complète.
   - log seulement un hash court du webhook.

2. send_prediction_to_discord(model_prediction_id)
   - récupère ModelPrediction + Fixture + FeatureSnapshot.
   - formatte le message.
   - envoie au webhook.
   - stocke DiscordMessage :
     - fixture_id
     - model_prediction_id
     - webhook_url_hash
     - message_hash
     - sent_at
     - status
     - response_text

3. CLI :
   - football-predictor discord-send --prediction-id 123
   - football-predictor predict-and-send --fixture 123456 --refresh-data
   - options :
     --dry-run
     --print-only

4. Tests :
   - mock httpx post.
   - succès.
   - erreur 400/500.
   - webhook non loggé.
   - DiscordMessage créé.
   - dry-run n’envoie pas.
   - print-only n’envoie pas.

Mets à jour README.md.
```

## Done

```text
- Envoi Discord fonctionnel.
- Secrets protégés.
- Dry-run disponible.
```

---

# Sprint 16 — Automatisation : prédictions du jour, fenêtres T-24h/T-6h/T-40min

## Objectif

Automatiser les prédictions.

On veut :

```text
prédire les matchs du jour
prédire les matchs d’une ligue
faire des snapshots T-24h, T-6h, T-40min
mettre à jour les lineups si disponibles
envoyer Discord
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte docs/api_football_reference.json pour valider les league_id utilisés dans les exemples ou tests réalistes.
Ne modifie aucun fichier pour l’instant.

Sprint 16 : automatisation des prédictions.

Contexte :
- On peut prédire une fixture.
- On peut envoyer une prédiction Discord.
- On veut automatiser les prédictions du jour.
- Les lineups officielles peuvent arriver 20 à 40 minutes avant le match.
- Les odds pré-match évoluent.
- On veut plusieurs fenêtres : early, mid, late.
- Les compétitions suivies peuvent venir de config/competitions.yaml, elle-même validée avec les docs de référence.

Objectif :
Créer des commandes d’automatisation.

Contraintes :
- Pas besoin d’un serveur web en V1.
- Utiliser CLI + cron possible.
- Ajouter un orchestrateur simple.
- Éviter les doublons Discord.
- Pouvoir filtrer par league_id, date, season.
- Respecter timezone Europe/Paris par défaut.
- Mode dry-run.
- Continuer si une fixture échoue.
- Produire un résumé d’exécution.
- Ne pas inventer de league_id dans docs/README.
- Ne pas faire d’appel API si --no-refresh-data.

À planifier :
1. Orchestrateur.
2. Fenêtres de prédiction.
3. Déduplication.
4. Refresh data.
5. Validation des ligues via références docs/ si possible.
6. CLI.
7. Tests.
8. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 16.

Avant de modifier, relis AGENTS.md et blueprint.md.
Utilise docs/api_football_reference.json pour valider les league_id des exemples réalistes.
Ne fais aucun appel réseau dans les tests.

Crée :
- src/football_predictor/prediction/run_daily.py
- src/football_predictor/prediction/scheduler.py
- tests/test_run_daily.py

Fonctionnalités :
1. get_fixtures_to_predict(date, league_ids=None, season=None)
   - récupère fixtures NS/TBD du jour.
   - filtre ligues enabled si config fournie.
   - peut valider league_ids via reference lookups si disponible.

2. prediction windows :
   - early : fixture.date - 24h
   - mid : fixture.date - 6h
   - late : fixture.date - 40min
   - now : heure actuelle
   - la CLI peut choisir une fenêtre.

3. run_daily_predictions(date=None, league_ids=None, window="now", send_discord=False, refresh_data=True, dry_run=False)
   - pour chaque fixture :
     - refresh fixture
     - refresh odds
     - refresh injuries
     - si late, refresh lineups
     - predict_fixture
     - send Discord si demandé
   - continue en cas d’erreur fixture.
   - retourne summary :
     - total
     - success
     - failed
     - sent
     - skipped

4. Déduplication :
   - éviter de renvoyer deux fois la même prédiction pour même fixture + model_version + window sauf option --force.
   - utiliser DiscordMessage ou ModelPrediction.

5. CLI :
   - football-predictor predict-today --date 2026-05-02 --league 39 --send-discord
   - options :
     --window early|mid|late|now
     --refresh-data / --no-refresh-data
     --dry-run
     --force

Important : dans README, si league 39 est utilisé comme exemple, vérifier qu’il existe dans docs/api_football_reference.json ou remplacer par un placeholder.

6. Tests :
   - filtre fixtures.
   - dry-run.
   - continue après erreur.
   - déduplication.
   - summary correct.
   - --no-refresh-data ne déclenche pas d’appel API mocké.

Mets à jour README.md avec exemples cron :
- prédiction matin
- update avant match
```

## Done

```text
- Prédictions quotidiennes automatisées.
- Fenêtres temporelles gérées.
- Discord optionnel.
- Déduplication gérée.
```

---

# Sprint 17 — Robustesse, observabilité et qualité

## Objectif

Durcir le projet :

```text
logs propres
gestion erreurs
validation settings
pré-commit
tests
CI locale
diagnostics
data quality report
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte les docs/ si les diagnostics doivent vérifier les chemins ou la présence des fichiers de référence.
Ne modifie aucun fichier pour l’instant.

Sprint 17 : robustesse, observabilité et qualité.

Contexte :
- Le pipeline complet existe.
- On veut le rendre fiable au quotidien.
- Les erreurs API, données manquantes, timeouts, odds absentes, lineups absentes doivent être compréhensibles.
- On veut des commandes de diagnostic.
- Les diagnostics doivent vérifier aussi la présence des fichiers référentiels docs/ et la validité JSON.

Objectif :
Ajouter robustesse, diagnostics, qualité de code.

Contraintes :
- Logs structurés lisibles.
- Pas de secrets dans les logs.
- Exceptions métier claires.
- Commande doctor.
- Commande data-quality.
- ruff, mypy, pytest.
- Ajouter pre-commit config si pertinent.
- Tests sur erreurs courantes.
- Vérifier les chemins : API_FOOTBALL_REFERENCE_PATH, API_FOOTBALL_PLAYERS_REFERENCE_PATH, API_FOOTBALL_PLAYERS_CACHE_PATH.
- Vérifier que les JSON docs/ sont lisibles sans charger inutilement trop de mémoire si possible.

À planifier :
1. Logging.
2. Exceptions.
3. Diagnostics.
4. Diagnostic des références docs/.
5. Data quality report.
6. Pre-commit.
7. Tests.
8. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 17.

Avant de modifier, relis AGENTS.md et blueprint.md.
Ne loggue jamais de secret.
Ne fais aucun appel réseau dans les tests.

Tâches :
1. Ajoute ou améliore :
   - src/football_predictor/utils/logging.py
   - src/football_predictor/utils/secrets.py
   - src/football_predictor/utils/diagnostics.py
   - src/football_predictor/features/data_quality.py

2. Secrets :
   - fonction mask_secret.
   - fonction hash_secret.
   - tests dédiés.

3. Diagnostics CLI :
   - football-predictor doctor
   Vérifie :
   - settings chargés.
   - API key présente sans l’afficher.
   - DB accessible.
   - tables présentes.
   - Discord webhook configuré ou non.
   - model-dir existe ou non.
   - config competitions existe ou non.
   - docs/api_football_reference.md existe.
   - docs/api_football_reference.json existe et JSON valide.
   - docs/api_football_players_reference.md existe.
   - docs/api_football_players_reference.json existe et JSON valide.
   - docs/api_football_players_cache.json existe et JSON valide si configuré.
   - les fichiers docs/ ne sont pas confondus : le cache joueurs n’est pas traité comme source métier principale.

4. Data quality CLI :
   - football-predictor data-quality --fixture 123456
   Affiche :
   - historique home/away disponible.
   - stats match disponibles.
   - lineups disponibles.
   - player stats disponibles.
   - injuries disponibles.
   - odds disponibles.
   - API prediction disponible.
   - références docs disponibles.
   - score global.

5. Ajoute .pre-commit-config.yaml avec ruff et tests basiques si adapté.

6. Ajoute tests :
   - secrets jamais affichés.
   - doctor avec settings incomplets.
   - doctor détecte docs JSON absents ou invalides.
   - data-quality fixture synthétique.
   - erreurs API converties en messages compréhensibles.

7. Mets à jour README.md :
   - troubleshooting.
   - checklist avant lancement quotidien.
   - vérification des fichiers de référence docs/.
```

## Done

```text
- Diagnostic utilisable.
- Logs sûrs.
- Qualité contrôlable.
- Références docs/ vérifiées par doctor.
```

---

# Sprint 18 — Packaging, Docker et exécution locale propre

## Objectif

Rendre l’outil facile à lancer depuis VSCode, terminal ou cron.

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte .env.example et les chemins docs/ attendus.
Ne modifie aucun fichier pour l’instant.

Sprint 18 : packaging, Docker et exécution locale.

Contexte :
- L’outil fonctionne en CLI.
- On veut simplifier l’installation et l’exécution.
- L’utilisateur développera dans VSCode avec Codex.
- On veut pouvoir lancer via cron ou Docker.
- Les fichiers docs/ référentiels doivent être inclus dans le contexte local du projet, mais aucun secret ne doit être inclus dans l’image.

Objectif :
Ajouter packaging opérationnel.

Contraintes :
- Dockerfile léger.
- docker-compose avec volume data.
- .env utilisé.
- Pas de secret dans l’image.
- Makefile avec commandes utiles.
- README clair.
- Tests non dépendants de Docker.
- Ne pas supprimer ou ignorer par erreur les fichiers docs/ référentiels nécessaires au fonctionnement local.
- S’assurer que les volumes data/ et docs/ sont accessibles dans Docker selon le mode choisi.

À planifier :
1. Dockerfile.
2. docker-compose.
3. Makefile.
4. Scripts.
5. Gestion des fichiers docs/ dans Docker.
6. Documentation.
7. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 18.

Avant de modifier, relis AGENTS.md et blueprint.md.
Ne mets aucun secret dans Dockerfile, docker-compose.yml, Makefile ou scripts.
Préserve les fichiers docs/.

Crée :
- Dockerfile
- docker-compose.yml
- Makefile
- scripts/init_local.sh
- scripts/run_predict_today.sh

Makefile doit contenir :
- make install
- make test
- make lint
- make format
- make typecheck
- make init-db
- make doctor
- make predict-fixture FIXTURE_ID=...
- make predict-today
- make train
- make backtest

Docker :
- image Python 3.11 slim.
- installer le package.
- utiliser .env au runtime.
- volume ./data:/app/data.
- garantir que docs/ est présent dans l’image ou monté en volume selon la stratégie retenue.
- commande par défaut : football-predictor doctor.

docker-compose :
- service app.
- env_file .env.
- volume data.
- volume docs si nécessaire.
- pas de secret codé en dur.

scripts :
- init_local.sh : crée data dirs, vérifie env, vérifie fichiers docs/, init db.
- run_predict_today.sh : lance predict-today avec variables optionnelles.

README :
- installation locale.
- Docker.
- cron examples.
- workflow quotidien.
- note sur les fichiers docs/ nécessaires.

Tests :
- pas forcément lancer Docker dans pytest.
- vérifier que les fichiers existent.
- vérifier que scripts ne contiennent pas de secret.
```

## Done

```text
- Projet lançable proprement.
- Docker prêt.
- Makefile pratique.
- docs/ pris en compte dans l’exécution locale.
```

---

# Sprint 19 — Documentation finale et scénario complet de bout en bout

## Objectif

Valider le workflow complet :

```text
configurer
initialiser DB
seed depuis docs/
ingérer références live si besoin
ingérer fixtures
ingérer détails
ingérer odds
entraîner
backtester
prédire
envoyer Discord
automatiser
```

## Mode Codex

```text
Plan mode
Puis Edit automatically / Agent
```

## Prompt Codex — Plan mode

```text
Lis AGENTS.md et blueprint.md.
Consulte tous les documents docs/ existants, notamment :
- docs/api_football_reference.md
- docs/api_football_reference.json
- docs/api_football_players_reference.md
- docs/api_football_players_reference.json
- docs/api_football_players_cache.json
- docs/product_spec.md
- docs/architecture.md
- docs/modeling_strategy.md
- docs/data_contract.md
Ne modifie aucun fichier pour l’instant.

Sprint 19 : documentation finale et scénario end-to-end.

Contexte :
- Le projet est complet.
- On veut une documentation finale exploitable.
- On veut un scénario de bout en bout pour vérifier que l’outil marche.
- Les fichiers docs/ sont des ressources centrales : ils doivent être expliqués dans la documentation utilisateur, développeur et exploitation.

Objectif :
Créer une documentation complète et un script smoke test.

Contraintes :
- Ne pas faire de vrais appels API dans le smoke test par défaut.
- Prévoir un mode live explicite.
- Documenter les variables d’environnement.
- Documenter les commandes dans l’ordre.
- Documenter les limites connues.
- Documenter les futures améliorations.
- Ajouter un guide VSCode/Codex.
- Documenter comment utiliser seed-reference-from-docs pour économiser le quota API.
- Documenter que docs/api_football_players_cache.json est un cache technique, pas la source principale.
- Ne pas mettre de vrais secrets dans la documentation.
- Ne pas utiliser d’IDs non vérifiés dans les exemples.

À planifier :
1. Documentation utilisateur.
2. Documentation développeur.
3. Documentation exploitation.
4. Documentation Codex.
5. Smoke test local.
6. Smoke test live explicite.
7. Place des fichiers docs/ dans le workflow.
8. Done.

Ne modifie aucun fichier pour l’instant.
```

## Prompt Codex — Edit automatically

```text
Implémente le Sprint 19.

Avant de modifier, relis AGENTS.md et blueprint.md.
Ne mets aucun secret dans la documentation ou les scripts.
Préserve les fichiers docs/ existants.

Crée :
- docs/user_guide.md
- docs/developer_guide.md
- docs/operations_guide.md
- docs/codex_workflow.md
- scripts/smoke_test_local.sh
- scripts/smoke_test_live.sh

Documentation user_guide.md :
- objectif.
- installation.
- configuration .env.
- rôle de AGENTS.md et blueprint.md.
- rôle des fichiers docs/ :
  - docs/api_football_reference.md
  - docs/api_football_reference.json
  - docs/api_football_players_reference.md
  - docs/api_football_players_reference.json
  - docs/api_football_players_cache.json
- config competitions.
- init DB.
- seed-reference-from-docs.
- ingestion.
- entraînement.
- backtest.
- prédiction fixture.
- envoi Discord.
- prédiction du jour.

Documentation developer_guide.md :
- architecture.
- modules.
- règles anti data leakage.
- hiérarchie des sources de vérité.
- usage du module reference/.
- ajout de nouvelles features.
- ajout de nouveaux modèles.
- tests.
- règles pour ne pas inventer d’IDs API-Football.

Documentation operations_guide.md :
- routine quotidienne.
- T-24h.
- T-6h.
- T-40min.
- surveillance logs.
- erreurs fréquentes.
- reset DB local.
- sauvegarde data/models.
- refresh des référentiels docs/.
- économie du quota API grâce au seed local et au cache joueurs.

Documentation codex_workflow.md :
- comment utiliser Plan mode.
- quand utiliser Agent/Edit automatically.
- comment faire relire le diff.
- prompts types.
- checklist avant commit.
- rappel de lire AGENTS.md et blueprint.md.
- rappel d’utiliser docs JSON pour les IDs.

Smoke tests :
1. smoke_test_local.sh :
   - sans réseau.
   - lance tests.
   - init DB sqlite temporaire.
   - doctor.
   - vérifie la présence des fichiers docs/.
2. smoke_test_live.sh :
   - demande API_FOOTBALL_KEY.
   - lance doctor.
   - optionnellement ingère une date ou fixture fournie.
   - ne doit pas envoyer Discord sauf variable SEND_DISCORD=true.

README :
- ajouter un “Quickstart end-to-end”.
- lister les sprints complétés.
- inclure seed-reference-from-docs dans le workflow recommandé.
- rappeler que les prédictions sont probabilistes, pas des certitudes.
```

## Done

```text
- Documentation complète.
- Workflow reproductible.
- Projet exploitable.
- Les fichiers docs/ sont pleinement intégrés dans le workflow.
```

---

# Ordre d’exécution recommandé

```text
Sprint 0  : documentation fondatrice alignée avec AGENTS.md, blueprint.md et docs/
Sprint 1  : bootstrap technique + settings chemins docs/ + dossier reference/
Sprint 2  : client API
Sprint 3  : base de données
Sprint 4  : référentiels locaux + seed depuis docs/ + ingestion référence live
Sprint 5  : fixtures + standings
Sprint 6  : détails match
Sprint 7  : odds
Sprint 8  : features équipe
Sprint 9  : features joueurs + XI
Sprint 10 : feature snapshot + dataset
Sprint 11 : modèles
Sprint 12 : backtesting
Sprint 13 : prédiction fixture
Sprint 14 : formatter Discord
Sprint 15 : webhook Discord
Sprint 16 : automatisation
Sprint 17 : robustesse
Sprint 18 : packaging
Sprint 19 : documentation finale
```

---

# Commandes finales attendues

À la fin, l’outil devra permettre :

```bash
football-predictor doctor
```

```bash
football-predictor init-db
```

```bash
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json
```

```bash
football-predictor ingest-reference --config config/competitions.yaml
```

```bash
football-predictor ingest-fixtures --league <LEAGUE_ID_FROM_DOCS> --season <SEASON>
```

```bash
football-predictor ingest-fixture-details --fixture <FIXTURE_ID_FROM_DOCS_OR_DB>
```

```bash
football-predictor ingest-odds --fixture <FIXTURE_ID_FROM_DOCS_OR_DB>
```

```bash
football-predictor build-dataset --league <LEAGUE_ID_FROM_DOCS> --season <SEASON> --output data/processed/training.parquet
```

```bash
football-predictor train --dataset data/processed/training.parquet --output-dir data/models/v1
```

```bash
football-predictor backtest --dataset data/processed/training.parquet --model-dir data/models/v1
```

```bash
football-predictor predict --fixture <FIXTURE_ID_FROM_DOCS_OR_DB> --model-dir data/models/v1 --refresh-data
```

```bash
football-predictor predict-and-send --fixture <FIXTURE_ID_FROM_DOCS_OR_DB> --model-dir data/models/v1 --refresh-data
```

```bash
football-predictor predict-today --date 2026-05-02 --league <LEAGUE_ID_FROM_DOCS> --window late --send-discord
```

---

# Format final Discord attendu

````md
```md
🏟️ PRÉDICTION FOOTBALL

Match : Arsenal vs Chelsea
Compétition : Premier League
Date : 2026-05-02 18:30 Europe/Paris

Résultat prédit : Victoire Arsenal
Confiance : High
Score de confiance : 23.4 pts

Probabilités modèle :
- Arsenal  : 52.8%
- Nul      : 25.6%
- Chelsea  : 21.6%

Probabilités marché :
- Arsenal  : 50.1%
- Nul      : 26.7%
- Chelsea  : 23.2%

Facteurs clés :
1. Arsenal a une meilleure forme domicile récente.
2. Chelsea a 2 titulaires probables absents.
3. Le XI probable d’Arsenal est plus stable.
4. Le marché favorise également Arsenal.

Absences clés :
- Chelsea : Joueur A, Joueur B
- Arsenal : aucune absence majeure détectée

Qualité des données :
- Score global : 87/100
- Odds : oui
- Blessures : oui
- Lineups officielles : non
- Stats joueurs : oui

Note : prédiction probabiliste, pas une certitude.
```
````

---

# Workflow Codex recommandé pour chaque sprint

```text
1. Ouvre une nouvelle branche Git.
2. Colle le prompt Plan mode.
3. Lis le plan de Codex.
4. S’il oublie un point, demande-lui de réviser le plan.
5. Colle le prompt Edit automatically / Agent.
6. Laisse Codex modifier.
7. Lance :
   pytest
   ruff check .
   mypy src si activé
8. Demande à Codex :
   "Review your own diff for bugs, data leakage risks, missing tests, secret exposure, invented API-Football IDs, and outdated documentation."
9. Corrige.
10. Commit.
```

Le point non négociable : toutes les features doivent être point-in-time. Toutes les valeurs d’IDs API-Football doivent venir des fichiers `docs/*.json`, de la base locale initialisée ou d’une donnée API live explicitement récupérée. Aucune prédiction ne doit être présentée comme une certitude.
