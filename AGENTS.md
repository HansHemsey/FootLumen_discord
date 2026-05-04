# AGENTS.md — Football Predictor

Ce fichier définit les règles de travail pour Codex, les agents IA et les développeurs intervenant sur ce projet.

Il doit être lu avant toute modification du code, des tests, de la documentation, des fichiers de configuration ou des scripts d’exploitation.

---

## 1. Identité du projet

Le projet est un outil Python de prédiction de matchs de football basé sur API-Football.

L’objectif est de prédire le résultat 1X2 d’un match :

```text
HOME = victoire de l’équipe à domicile
DRAW = match nul
AWAY = victoire de l’équipe extérieure
```

La sortie attendue est probabiliste :

```text
P(Home)
P(Draw)
P(Away)
Résultat prédit
Score de confiance
Explications principales
Qualité des données
```

Le projet doit produire des prédictions exploitables dans Discord via webhook, sous forme de bloc markdown clair, en français.

---

## 2. Documents à lire avant de travailler

Avant toute tâche importante, lire ou consulter les documents suivants selon le besoin :

```text
blueprint.md
README.md
PLANS.md
docs/product_spec.md
docs/architecture.md
docs/modeling_strategy.md
docs/data_contract.md
```

Le fichier le plus important pour le contexte métier et les règles projet est :

```text
blueprint.md
```

Règle obligatoire :

> Avant de modifier le code, vérifier si `blueprint.md` contient déjà une règle ou une orientation sur le sujet traité.

---

## 3. Références API-Football disponibles dans `docs/`

Le dossier `docs/` contient des référentiels déjà générés à partir d’API-Football.

Ils doivent être utilisés pour éviter d’inventer des IDs ou des données métier.

### 3.1 Fichiers disponibles

```text
docs/api_football_reference.md
docs/api_football_reference.json
docs/api_football_players_reference.md
docs/api_football_players_reference.json
docs/api_football_players_cache.json
```

### 3.2 Usage des fichiers

#### `docs/api_football_reference.md`

Documentation lisible des compétitions et métadonnées API.

À utiliser pour comprendre manuellement :

```text
league_id
team_id
venue_id
standings
rounds
fixtures
bookmakers
bets
```

#### `docs/api_football_reference.json`

Version structurée destinée au code.

À utiliser pour charger, valider ou rechercher :

```text
championnats
équipes
fixtures
venue_id
bookmaker_id
bet_id
IDs API-Football
```

#### `docs/api_football_players_reference.md`

Documentation lisible des joueurs.

À utiliser pour consulter manuellement :

```text
player_id
nom
âge
numéro
poste
équipe
compétition
saison
```

#### `docs/api_football_players_reference.json`

Version structurée destinée au code.

À utiliser pour charger ou valider :

```text
joueurs
effectifs
player_id
team_id
poste
numéro
saison
compétition
```

#### `docs/api_football_players_cache.json`

Cache technique de collecte.

À utiliser uniquement pour éviter de refaire les appels `/players/squads` si un script de collecte doit être relancé.

Ce fichier n’est pas la source métier principale.

---

## 4. Hiérarchie des sources de vérité

### 4.1 Compétitions, équipes, fixtures, venues, bookmakers et bets

Ordre de priorité :

```text
1. docs/api_football_reference.json pour le code
2. docs/api_football_reference.md pour la lecture humaine
3. base de données locale si elle a déjà été initialisée
4. API-Football live seulement si un refresh explicite est demandé
```

### 4.2 Joueurs et effectifs

Ordre de priorité :

```text
1. docs/api_football_players_reference.json pour le code
2. docs/api_football_players_reference.md pour la lecture humaine
3. base de données locale si elle a déjà été initialisée
4. docs/api_football_players_cache.json uniquement pour la reprise de collecte
5. API-Football live seulement si un refresh explicite est demandé
```

### 4.3 Données dynamiques de prédiction

Les fichiers `docs/` donnent les IDs et le contexte, mais ils ne remplacent pas les données dynamiques.

Les données suivantes doivent venir de snapshots datés ou de la base locale :

```text
fixtures récentes ou futures
standings
statistiques de match
événements
lineups
statistiques joueurs
blessures
absences
odds
prédictions API-Football
```

Règle :

> Les référentiels `docs/` servent à éviter les suppositions. Les features prédictives doivent être point-in-time.

---

## 5. Règles absolues à respecter

### 5.1 Ne jamais inventer d’ID API-Football

Ne jamais inventer :

```text
league_id
team_id
fixture_id
player_id
venue_id
bookmaker_id
bet_id
coach_id
```

Avant d’utiliser un ID dans un exemple, un test, une configuration ou un mapping, vérifier les fichiers de référence sous `docs/`.

Mauvais exemple :

```python
league_id = 39
team_id = 33
player_id = 12345
```

Bon exemple :

```python
league_id = reference.find_league_by_name("Premier League", season=2025).league_id
team_id = reference.find_team_by_name("Manchester United", league_id=league_id).team_id
```

Si un ID est absent des fichiers de référence, ne pas le deviner. Expliquer le manque ou créer un test synthétique clairement marqué comme synthétique.

---

### 5.2 Ne jamais exposer de secret

Ne jamais committer, afficher ou logger :

```text
API_FOOTBALL_KEY
DISCORD_WEBHOOK_URL
clé API
URL webhook complète
token
secret
```

Les secrets doivent venir de variables d’environnement ou de `.env` local non versionné.

Le fichier `.env.example` peut contenir uniquement des placeholders vides.

Les logs doivent masquer les secrets.

Exemple autorisé :

```text
Discord webhook configured: yes, hash=ab12cd34
API key configured: yes
```

Exemple interdit :

```text
Discord webhook: https://discord.com/api/webhooks/...
API key: xxxxx
```

---

### 5.3 Ne jamais introduire de fuite de données

C’est la règle la plus importante du projet.

Aucune feature ne doit utiliser une information indisponible au moment de la prédiction.

Chaque calcul de feature doit respecter :

```text
fixture_id
prediction_time
```

Règles strictes :

```text
- exclure la fixture cible de ses propres features historiques ;
- utiliser uniquement les fixtures dont date < prediction_time ;
- utiliser uniquement les odds dont fetched_at <= prediction_time ;
- utiliser uniquement les injuries dont fetched_at <= prediction_time ;
- utiliser uniquement les standings dont snapshot_date ou fetched_at <= prediction_time ;
- utiliser uniquement les lineups dont fetched_at <= prediction_time ;
- utiliser uniquement les player stats connues avant prediction_time ;
- ne jamais utiliser le résultat final dans les features ;
- ne jamais utiliser une statistique post-match du match à prédire ;
- ne jamais utiliser `/teams/statistics` sans paramètre date ou snapshot historique lorsqu’on reconstruit un match passé.
```

Pour tout changement touchant aux features, ajouter ou maintenir des tests anti data leakage.

---

### 5.4 Ne pas faire échouer tout le pipeline à cause d’une source optionnelle

Certaines données peuvent manquer selon la compétition ou le moment :

```text
odds
lineups
player stats
injuries
predictions API-Football
fixture statistics
```

Le pipeline doit continuer avec :

```text
data_quality flags
valeurs manquantes explicites
fallbacks documentés
logs compréhensibles
```

Ne pas inventer les valeurs manquantes. Les imputer seulement dans les modules de preprocessing ou modèle, et marquer l’indisponibilité dans les features.

---

## 6. Architecture cible

Le projet suit un layout `src/`.

Arborescence cible :

```text
football-predictor/
├── AGENTS.md
├── blueprint.md
├── PLANS.md
├── README.md
├── pyproject.toml
├── .env.example
├── config/
│   └── competitions.example.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   └── models/
├── docs/
│   ├── api_football_reference.md
│   ├── api_football_reference.json
│   ├── api_football_players_reference.md
│   ├── api_football_players_reference.json
│   ├── api_football_players_cache.json
│   ├── product_spec.md
│   ├── architecture.md
│   ├── modeling_strategy.md
│   └── data_contract.md
├── src/
│   └── football_predictor/
│       ├── api/
│       ├── backtesting/
│       ├── config/
│       ├── db/
│       ├── discord/
│       ├── features/
│       ├── ingestion/
│       ├── modeling/
│       ├── prediction/
│       ├── reference/
│       └── utils/
└── tests/
```

Modules principaux :

```text
api/          Client API-Football, endpoints, erreurs, pagination, snapshots bruts.
config/       Settings, chemins, compétitions suivies.
db/           Modèles SQLAlchemy, session, repositories, migrations.
ingestion/    Ingestion référentiels, fixtures, stats, lineups, joueurs, injuries, odds.
reference/    Loaders et lookups pour les fichiers docs/*.json.
features/     Team features, player features, XI, odds, contexte, data quality.
modeling/     Baselines, Poisson, modèle multiclass, stacking, calibration, training.
backtesting/  Dataset historique, métriques, rapports.
prediction/   Pipeline fixture unique, confiance, explications, prédictions du jour.
discord/      Formatter markdown et webhook.
utils/        Logging, secrets, dates, math, diagnostics.
```

---

## 7. Stack technique attendue

Langage :

```text
Python 3.11+
```

Dépendances principales :

```text
httpx
pydantic
pydantic-settings
sqlalchemy
alembic
pandas
numpy
scikit-learn
joblib
typer
rich
python-dotenv
```

Dépendances dev :

```text
pytest
pytest-cov
ruff
mypy
```

Optionnel selon compatibilité :

```text
catboost
lightgbm
```

Si CatBoost ou LightGBM compliquent l’installation, prévoir un fallback scikit-learn.

---

## 8. Commandes de qualité attendues

Quand le projet est initialisé, les commandes suivantes doivent passer avant de considérer un sprint terminé :

```bash
pytest
ruff check .
mypy src
```

Si `mypy` n’est pas encore pleinement activé, ne pas bloquer le sprint sans raison, mais documenter les limites.

Commandes utiles prévues :

```bash
football-predictor doctor
football-predictor init-db
football-predictor ingest-reference --config config/competitions.yaml
football-predictor ingest-fixtures --league 39 --season 2025
football-predictor ingest-fixture-details --fixture 123456
football-predictor ingest-odds --fixture 123456
football-predictor build-dataset --league 39 --season 2025 --output data/processed/training.parquet
football-predictor train --dataset data/processed/training.parquet --output-dir data/models/v1
football-predictor backtest --dataset data/processed/training.parquet --model-dir data/models/v1
football-predictor predict --fixture 123456 --model-dir data/models/v1 --refresh-data
football-predictor predict-and-send --fixture 123456 --model-dir data/models/v1 --refresh-data
football-predictor predict-today --date 2026-05-02 --league 39 --window late --send-discord
```

---

## 9. Workflow Codex obligatoire

Pour chaque sprint ou changement important :

```text
1. Lire AGENTS.md.
2. Lire blueprint.md.
3. Lire les docs pertinentes.
4. Démarrer en Plan mode.
5. Produire un plan clair avant modification.
6. Passer en Edit automatically / Agent seulement après plan.
7. Modifier le code par petites étapes cohérentes.
8. Ajouter ou mettre à jour les tests.
9. Lancer pytest et ruff.
10. Relire le diff.
11. Vérifier les risques de data leakage.
12. Vérifier qu’aucun secret n’est exposé.
13. Mettre à jour la documentation si le comportement change.
```

Pour les changements simples et isolés, un plan court suffit, mais la checklist reste valable.

---

## 10. Règles de code

### 10.1 Style général

- Code clair, typé et modulaire.
- Fonctions petites et testables.
- Noms explicites.
- Pas de logique métier cachée dans la CLI.
- Pas de valeurs magiques sans constante ou commentaire.
- Pas de secrets en dur.
- Pas d’appel réseau dans les tests unitaires.
- Pas de dépendance implicite à l’ordre d’exécution des tests.

### 10.2 Typage

Préférer :

```python
from pathlib import Path
from typing import Any
```

Utiliser des `dataclass`, `TypedDict` ou modèles Pydantic lorsque cela améliore la clarté des structures.

### 10.3 Gestion des erreurs

Créer des exceptions métier explicites.

Exemples :

```text
ApiFootballError
ApiFootballRateLimitError
ApiFootballNoContentError
ReferenceLookupError
DataQualityError
PredictionError
DiscordWebhookError
```

Les erreurs doivent contenir le contexte utile sans secret.

---

## 11. Règles API-Football

Tous les appels API doivent passer par un client centralisé :

```text
src/football_predictor/api/api_football_client.py
```

Le client doit gérer :

```text
authentification par header x-apisports-key
GET uniquement
timeout
retry raisonnable
pagination
codes 204, 499, 500
exceptions explicites
snapshots bruts optionnels
logs sans secret
```

Chaque réponse brute utile doit pouvoir être stockée avec :

```text
endpoint
params
payload
fetched_at
status_code
source
```

Les snapshots bruts ne doivent jamais contenir la clé API.

---

## 12. Règles base de données

La base locale commence en SQLite, mais le design doit rester compatible PostgreSQL.

Utiliser SQLAlchemy 2.x style.

Les tables importantes incluent :

```text
RawApiSnapshot
League
Team
Fixture
StandingSnapshot
FixtureStatistics
FixtureEvent
FixtureLineup
FixturePlayerStats
Player
PlayerSquad
Injury
OddsSnapshot
ApiPredictionSnapshot
FeatureSnapshot
ModelPrediction
DiscordMessage
```

Règles :

```text
- les ingestions doivent être idempotentes ;
- privilégier upsert ou équivalent ;
- conserver payload_json pour audit ;
- indexer fixture_id, team_id, league_id, season, fetched_at ;
- ne pas écraser les snapshots temporels importants ;
- toujours conserver prediction_time pour les features et prédictions.
```

---

## 13. Règles ingestion

Les modules d’ingestion doivent :

```text
- tolérer les champs manquants ;
- stocker les payloads bruts ;
- être idempotents ;
- ne pas dupliquer les entités ;
- logger les endpoints indisponibles sans casser tout le batch ;
- ne pas faire d’appel live sauf commande explicite ;
- permettre un mode dry-run lorsque pertinent.
```

Sources d’ingestion principales :

```text
/leagues
/teams
/teams/statistics
/standings
/fixtures
/fixtures/headtohead
/fixtures/statistics
/fixtures/events
/fixtures/lineups
/fixtures/players
/injuries
/predictions
/players
/players/squads
/odds
/odds/bookmakers
/odds/bets
/odds/mapping
```

---

## 14. Règles référentiels locaux

Créer ou maintenir un module :

```text
src/football_predictor/reference/
```

Fonctions recommandées :

```python
load_api_football_reference(path)
load_players_reference(path)
find_league_by_id(league_id)
find_team_by_id(team_id)
find_team_by_name(name, league_id=None)
find_player_by_id(player_id)
find_players_by_team(team_id)
find_bookmaker_by_id(bookmaker_id)
find_bet_by_id(bet_id)
validate_fixture_reference(fixture_id)
```

Ces fonctions doivent :

```text
- lire uniquement les fichiers locaux ;
- ne jamais appeler l’API live ;
- être typées ;
- tolérer les champs manquants ;
- retourner des erreurs explicites ;
- être testées.
```

---

## 15. Règles features

Toutes les features doivent être sérialisables en JSON.

Le feature builder central doit produire :

```text
fixture_id
prediction_time
feature_version
features_json
data_quality_json
```

Les features doivent couvrir :

```text
forme équipe last_3, last_5, last_10, last_15
EWMA de forme
forme domicile / extérieur
buts pour / contre
clean sheets
failed to score
statistiques tirs, tirs cadrés, tirs dans la surface
possession
passes
corners
fautes
cartons
arrêts gardien
pseudo-xG si xG absent
stats ajustées adversaire
classement
repos et calendrier
features joueurs
XI type
XI probable
formation probable
stabilité du XI
absences
impact absences
qualité remplaçants
odds consensus
odds movement
prédictions API-Football
qualité des données
```

Règles :

```text
- chaque feature dynamique doit respecter prediction_time ;
- les noms de features doivent être stables ;
- les unités doivent être claires ;
- utiliser des suffixes explicites : _last3, _last5, _last10, _last15, _ewma ;
- séparer home_team_* et away_team_* ;
- ajouter des flags quand une source est absente ;
- documenter les nouvelles features dans docs/data_contract.md.
```

---

## 16. Règles XI, joueurs et absences

Le module XI est central pour la qualité du modèle.

Il doit calculer :

```text
formation probable
P_start par joueur
XI type
XI probable
player_value par poste
bench_depth_score
xi_stability_score
absence_impact_score
replacement_quality_score
availability_score
key_absences_json
```

Règles importantes :

```text
- un joueur ne doit être pénalisant que s’il était probablement titulaire ;
- une absence doit être pondérée par l’importance du joueur ;
- une absence doit être pondérée par la qualité du remplaçant ;
- les postes doivent être comparés par groupe : GK, DEF, MID, ATT ;
- les joueurs du référentiel local peuvent servir de fallback si les player stats manquent ;
- les blessures doivent respecter fetched_at <= prediction_time ;
- les lineups officielles ne peuvent être utilisées que si disponibles avant prediction_time.
```

Formule initiale autorisée pour `P_start` :

```text
P_start =
0.50 * weighted_start_frequency
+ 0.25 * weighted_minutes_share
+ 0.15 * formation_position_compatibility
+ 0.10 * recent_availability
```

Formule initiale autorisée pour l’impact absence :

```text
absence_impact = P_start * player_value * severity * replacement_gap * position_multiplier
```

Multiplicateurs initiaux :

```text
GK  = 1.30
ATT = 1.25
MID créatif = 1.20
DEF central = 1.10
autres = 1.00
```

---

## 17. Règles odds

Les odds doivent être converties en probabilités implicites sans marge bookmaker.

Pour des odds décimales :

```text
q_home = 1 / odd_home
q_draw = 1 / odd_draw
q_away = 1 / odd_away
```

Puis :

```text
p_home = q_home / (q_home + q_draw + q_away)
p_draw = q_draw / (q_home + q_draw + q_away)
p_away = q_away / (q_home + q_draw + q_away)
```

Overround :

```text
overround = q_home + q_draw + q_away - 1
```

Règles :

```text
- ne pas mélanger odds live et pre-match dans la V1 ;
- utiliser uniquement les odds snapshots avant prediction_time ;
- calculer un consensus multi-bookmakers ;
- pondérer par inverse de l’overround si possible ;
- calculer la dispersion entre bookmakers ;
- calculer le mouvement de cotes si plusieurs snapshots existent ;
- gérer les odds manquantes sans casser la prédiction.
```

---

## 18. Règles modèles

Classes fixes :

```text
HOME
DRAW
AWAY
```

Le modèle doit toujours retourner des probabilités normalisées :

```text
p_home + p_draw + p_away = 1
```

Modèles attendus :

```text
baseline odds-only
baseline API prediction
baseline Poisson
modèle ML multiclass
stacking final
calibration
```

Le stacking initial peut utiliser :

```text
sport  = 0.55
market = 0.35
api    = 0.10
```

Mais ces poids doivent être ajustables et idéalement appris ou validés par backtesting.

Métriques obligatoires :

```text
accuracy 1X2
log loss
Brier score
calibration bins
confusion matrix
performance par ligue
performance par saison
performance par niveau de confiance
comparaison odds-only
comparaison API prediction
comparaison Poisson
```

---

## 19. Règles prédiction

Le pipeline de prédiction fixture unique doit :

```text
1. récupérer la fixture ;
2. rafraîchir les données si demandé ;
3. construire le FeatureSnapshot ;
4. charger le modèle disponible ;
5. calculer p_sport ;
6. récupérer p_market ;
7. récupérer p_api ;
8. appliquer le stacking ;
9. calculer la confiance ;
10. générer les explications ;
11. sauvegarder ModelPrediction ;
12. retourner une sortie CLI claire.
```

Fallbacks :

```text
- si modèle absent : odds-only + Poisson + API prediction si disponibles ;
- si odds absentes : modèle sportif + API prediction ;
- si API prediction absente : modèle sportif + odds ;
- si tout est pauvre : prior configurable + data_quality faible.
```

Règle :

> Une prédiction doit être honnête sur la qualité des données. Ne jamais masquer une faible couverture.

---

## 20. Règles Discord

Les messages Discord doivent être :

```text
en français
clairs
courts
formatés en bloc de code markdown
sans secret
sans promesse de certitude
```

Format attendu :

````md
```md
🏟️ PRÉDICTION FOOTBALL

Match : Équipe domicile vs Équipe extérieur
Compétition : Nom de compétition
Date : YYYY-MM-DD HH:mm Europe/Paris

Résultat prédit : Victoire domicile / Match nul / Victoire extérieur
Confiance : High / Medium / Low / Uncertain
Score de confiance : XX.X pts

Probabilités modèle :
- Domicile  : XX.X%
- Nul       : XX.X%
- Extérieur : XX.X%

Probabilités marché :
- Domicile  : XX.X%
- Nul       : XX.X%
- Extérieur : XX.X%

Facteurs clés :
1. ...
2. ...
3. ...

Absences clés :
- Équipe A : ...
- Équipe B : ...

Qualité des données :
- Score global : XX/100
- Odds : oui/non
- Blessures : oui/non
- Lineups officielles : oui/non
- Stats joueurs : oui/non

Note : prédiction probabiliste, pas une certitude.
```
````

La limite Discord doit être respectée. Prévoir une troncature propre qui conserve la fermeture du bloc de code.

---

## 21. Règles tests

Les tests unitaires ne doivent jamais faire d’appel réseau.

Utiliser :

```text
tests/fixtures/
mock httpx
SQLite temporaire
payloads JSON minimaux
échantillons extraits des docs JSON si besoin
```

Tests obligatoires selon les modules :

```text
api client : auth, pagination, erreurs, snapshot sans secret
reference : lookups et validation IDs
DB : création tables, upsert, idempotence
ingestion : parsers, champs manquants, 204 no content
features : fenêtres, home/away, anti data leakage
odds : conversion proba, overround, consensus, movement
players/XI : P_start, formation, absences, replacement gap
feature builder : snapshot point-in-time
modeling : probabilités valides, save/load, stacking
backtesting : log loss, brier, calibration, group metrics
prediction : fallback, explanations, ModelPrediction
discord : format markdown, troncature, webhook mocké
```

Pour chaque bug corrigé, ajouter un test qui échouait avant la correction.

---

## 22. Règles documentation

Mettre à jour la documentation si un changement modifie :

```text
commande CLI
variable d’environnement
structure DB
feature
format Discord
workflow d’ingestion
workflow training/backtesting
format des fichiers de référence
hypothèse modèle
```

Documents à tenir à jour :

```text
README.md
docs/product_spec.md
docs/architecture.md
docs/modeling_strategy.md
docs/data_contract.md
docs/user_guide.md
docs/developer_guide.md
docs/operations_guide.md
```

---

## 23. Variables d’environnement attendues

`.env.example` doit contenir au minimum :

```env
API_FOOTBALL_KEY=
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
DATABASE_URL=sqlite:///./data/football_predictor.db
DISCORD_WEBHOOK_URL=
APP_TIMEZONE=Europe/Paris
API_FOOTBALL_REFERENCE_PATH=docs/api_football_reference.json
API_FOOTBALL_PLAYERS_REFERENCE_PATH=docs/api_football_players_reference.json
API_FOOTBALL_PLAYERS_CACHE_PATH=docs/api_football_players_cache.json
```

Règle :

> Les valeurs sensibles restent vides dans `.env.example`.

---

## 24. Définition générale de Done

Un changement est terminé seulement si :

```text
- le code répond au besoin ;
- les tests pertinents sont ajoutés ou mis à jour ;
- pytest passe ;
- ruff check passe ;
- aucun secret n’est exposé ;
- aucun ID API-Football n’est inventé ;
- les règles point-in-time sont respectées ;
- les erreurs sont compréhensibles ;
- les données manquantes sont gérées ;
- la documentation est mise à jour si nécessaire ;
- le diff a été relu ;
- les risques de data leakage ont été explicitement vérifiés.
```

---

## 25. Checklist avant commit

Avant chaque commit, vérifier :

```text
[ ] Ai-je lu blueprint.md si le changement est important ?
[ ] Ai-je utilisé les fichiers docs JSON quand des IDs sont nécessaires ?
[ ] Ai-je évité tout ID inventé ?
[ ] Ai-je respecté prediction_time pour les features ?
[ ] Ai-je exclu la fixture cible des historiques ?
[ ] Ai-je évité de logger des secrets ?
[ ] Ai-je ajouté ou mis à jour les tests ?
[ ] Ai-je exécuté pytest ?
[ ] Ai-je exécuté ruff check . ?
[ ] Ai-je mis à jour la documentation si nécessaire ?
[ ] Ai-je relu le diff pour détecter les régressions ?
```

---

## 26. Prompts utiles pour Codex

### 26.1 Démarrage d’un sprint

```text
Lis AGENTS.md, blueprint.md et les docs pertinentes.
Travaille en Plan mode.
Ne modifie aucun fichier avant d’avoir proposé un plan.
Vérifie les risques de data leakage et les sources de vérité sous docs/.
```

### 26.2 Implémentation

```text
Implémente le plan validé.
Respecte AGENTS.md et blueprint.md.
Ajoute les tests nécessaires.
N’invente aucun ID API-Football.
N’expose aucun secret.
À la fin, exécute pytest et ruff check . si possible.
```

### 26.3 Relecture du diff

```text
Relis ton diff comme un reviewer senior.
Cherche : bugs, fuite de données, secrets exposés, IDs inventés, tests manquants, erreurs de typage, documentation obsolète.
Propose les corrections nécessaires.
```

### 26.4 Contrôle anti data leakage

```text
Vérifie que toutes les features utilisent uniquement les données disponibles à prediction_time.
Vérifie particulièrement odds, injuries, standings, lineups, player stats, fixture statistics et résultats historiques.
Confirme que la fixture cible est exclue des historiques.
```

### 26.5 Validation des IDs

```text
Vérifie que tous les league_id, team_id, player_id, fixture_id, venue_id, bookmaker_id et bet_id utilisés existent dans docs/api_football_reference.json ou docs/api_football_players_reference.json.
Si un ID est absent, remplace-le par une valeur vérifiée ou marque le test comme synthétique.
```

---

## 27. Principe final

Ce projet doit être développé comme un système prédictif sérieux, traçable et maintenable.

Priorités :

```text
1. robustesse ;
2. absence de fuite de données ;
3. traçabilité ;
4. qualité des probabilités ;
5. explicabilité ;
6. automatisation Discord ;
7. économie du quota API ;
8. facilité de maintenance avec Codex.
```

Rappels finaux :

```text
Ne jamais inventer ce que les fichiers docs peuvent vérifier.
Ne jamais utiliser le futur pour prédire le passé.
Ne jamais logger de secret.
Ne jamais bloquer toute une prédiction parce qu’une source optionnelle manque.
Ne jamais présenter une prédiction probabiliste comme une certitude.
```
