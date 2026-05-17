# Blueprint du projet — Football Predictor

Ce fichier sert de document de contexte central pour Codex, les agents IA et les développeurs du projet.  
Il doit être lu avant toute modification importante du code, en complément de `AGENTS.md`, `README.md` et des fichiers présents dans `docs/`.

---

## 1. Objectif du projet

Le projet vise à développer un outil Python de prédiction de matchs de football basé sur API-Football.

L’outil doit :

- prédire le résultat 1X2 d’un match : victoire domicile, match nul, victoire extérieur ;
- produire des probabilités calibrées : `P(Home)`, `P(Draw)`, `P(Away)` ;
- intégrer les données équipe, joueur, forme récente, domicile/extérieur, statistiques détaillées, blessures, absences, XI probable, odds bookmakers et prédictions API-Football ;
- éviter toute fuite de données en calculant les features uniquement avec les données disponibles avant l’heure de prédiction ;
- publier une prédiction claire dans Discord via webhook, sous forme de bloc markdown ;
- être exploitable en CLI depuis VSCode, un terminal, Docker ou une tâche planifiée.

---

## 2. Documents de référence disponibles

Le dossier `docs/` contient plusieurs fichiers importants déjà générés à partir d’API-Football.  
Codex doit les utiliser avant d’inventer un identifiant, un nom de compétition, un nom d’équipe, un `player_id`, un `team_id`, un `league_id`, un `venue_id`, un `bookmaker_id` ou un `bet_id`.

### 2.1 `docs/api_football_reference.md`

Documentation lisible des compétitions et métadonnées API.

Ce fichier contient notamment :

- `league_id` ;
- `team_id` ;
- `venue_id` ;
- standings ;
- rounds ;
- fixtures ;
- bookmakers ;
- bets.

Utilisation recommandée :

- ouvrir ce fichier lorsqu’il faut comprendre quels identifiants API utiliser ;
- vérifier manuellement les compétitions suivies ;
- vérifier les équipes disponibles dans une compétition ;
- retrouver les IDs utiles pour des exemples, tests, fixtures ou configurations ;
- rédiger de la documentation humaine.

Règle :

> Pour toute question humaine du type « quel ID utiliser ? », « quelle équipe correspond à ce nom ? », « quelle compétition est disponible ? », ouvrir d’abord `docs/api_football_reference.md`.

---

### 2.2 `docs/api_football_reference.json`

Version structurée et exploitable par le code du fichier précédent.

Ce fichier doit servir de base machine-readable pour :

- charger les championnats suivis ;
- charger les équipes ;
- charger les fixtures connues ;
- charger les IDs API ;
- créer des fixtures de tests cohérentes ;
- générer une config de compétitions ;
- valider qu’un `league_id`, `team_id`, `fixture_id`, `bookmaker_id` ou `bet_id` existe dans le référentiel local.

Utilisation recommandée :

- préférer ce fichier au `.md` lorsque le code doit parser ou charger des données ;
- ne pas hardcoder des IDs si le JSON peut être interrogé ;
- utiliser ce fichier pour créer des fixtures de tests réalistes.

Règle :

> Pour le code, les tests et les validateurs, utiliser prioritairement `docs/api_football_reference.json` plutôt que le `.md`.

---

### 2.3 `docs/api_football_players_reference.md`

Documentation lisible des joueurs.

Ce fichier contient les joueurs par :

- compétition ;
- équipe ;
- `player_id` ;
- nom ;
- âge ;
- numéro ;
- poste.

Utilisation recommandée :

- consulter manuellement les joueurs d’une équipe ;
- vérifier l’identité d’un joueur ;
- comprendre la composition des effectifs ;
- rédiger une explication ou une documentation lisible.

Règle :

> Pour toute question humaine sur un joueur ou un effectif, ouvrir d’abord `docs/api_football_players_reference.md`.

---

### 2.4 `docs/api_football_players_reference.json`

Version structurée et exploitable par le code du référentiel joueurs.

Ce fichier contient les 4 645 joueurs récupérés, reliés à :

- leur `player_id` ;
- leur `team_id` ;
- leur compétition ;
- leur saison ;
- leur équipe ;
- leur poste ;
- leur âge ;
- leur numéro quand disponible.

Utilisation recommandée :

- charger les joueurs dans la base locale ;
- créer les tables `Player` et `PlayerSquad` ;
- générer des tests réalistes ;
- relier les blessures, lineups et statistiques joueurs à un référentiel local ;
- éviter les appels API inutiles à `/players/squads`.

Règle :

> Pour le code relatif aux joueurs, utiliser prioritairement `docs/api_football_players_reference.json` comme source structurée.

---

### 2.5 `docs/api_football_players_cache.json`

Cache technique de collecte.

Ce fichier correspond au cache utilisé pour éviter de refaire les 144 appels API `/players/squads`.

Utilisation recommandée :

- conserver ce fichier pour économiser le quota API ;
- l’utiliser seulement si un script de collecte doit reprendre ou éviter de rappeler API-Football ;
- ne pas le considérer comme la documentation principale ;
- ne pas construire les features métier directement dessus si `api_football_players_reference.json` suffit.

Règle :

> `docs/api_football_players_cache.json` est un cache technique, pas la source métier principale. Ne l’utiliser que pour la collecte ou la reprise d’ingestion.

---

## 3. Hiérarchie des sources de vérité

Quand plusieurs sources peuvent contenir la même information, appliquer l’ordre suivant.

### 3.1 Pour les compétitions, équipes, fixtures, bookmakers et bets

1. `docs/api_football_reference.json` pour le code ;
2. `docs/api_football_reference.md` pour la lecture humaine ;
3. base de données locale si elle a déjà été initialisée ;
4. API-Football live seulement si un refresh explicite est demandé.

### 3.2 Pour les joueurs et effectifs

1. `docs/api_football_players_reference.json` pour le code ;
2. `docs/api_football_players_reference.md` pour la lecture humaine ;
3. base de données locale si elle a déjà été initialisée ;
4. `docs/api_football_players_cache.json` uniquement pour la reprise de collecte ;
5. API-Football live seulement si un refresh explicite est demandé.

### 3.3 Pour les prédictions et features dynamiques

Les fichiers de référence ne remplacent pas les données dynamiques nécessaires à la prédiction.

Les données suivantes doivent être récupérées ou stockées en snapshots temporels :

- fixtures passées et futures ;
- standings à une date donnée ;
- statistiques de match ;
- événements ;
- lineups ;
- player stats ;
- injuries ;
- odds ;
- predictions API-Football.

Règle :

> Les fichiers de référence donnent le contexte et les IDs. Les features prédictives doivent rester point-in-time et provenir de snapshots datés.

---

## 4. Règles pour Codex

Codex doit suivre ces règles pendant tout le développement.

### 4.1 Toujours chercher dans `docs/` avant d’inventer

Avant d’écrire un exemple, un test, une configuration ou un mapping contenant un ID API-Football, Codex doit vérifier les fichiers de référence.

Exemples d’éléments à vérifier :

- `league_id` ;
- `team_id` ;
- `fixture_id` ;
- `player_id` ;
- `venue_id` ;
- `bookmaker_id` ;
- `bet_id` ;
- nom exact d’une équipe ;
- nom exact d’un joueur ;
- saison liée à une compétition.

À éviter :

```python
league_id = 39  # sans vérifier le référentiel
team_id = 33    # sans vérifier le référentiel
player_id = 123 # inventé
```

Préférer :

```python
# Charger depuis docs/api_football_reference.json ou depuis la DB initialisée.
league_id = reference.get_league_id(name="Premier League", season=2025)
```

---

### 4.2 Utiliser le JSON pour le code, le Markdown pour comprendre

- Pour écrire des parseurs, des tests ou des validateurs : utiliser les `.json`.
- Pour comprendre la structure ou répondre à une question métier : utiliser les `.md`.
- Pour rédiger une documentation utilisateur : s’appuyer sur les `.md`.
- Pour charger les référentiels initiaux : s’appuyer sur les `.json`.

---

### 4.3 Ne jamais considérer le cache comme source métier principale

`api_football_players_cache.json` existe pour économiser des appels API.

Il ne doit pas devenir :

- la source principale du modèle ;
- la source principale des features ;
- une dépendance obligatoire pour prédire ;
- une référence fonctionnelle plus importante que `api_football_players_reference.json`.

---

### 4.4 Préserver l’anti data leakage

Aucune feature ne doit utiliser une information qui n’était pas disponible au moment de la prédiction.

Chaque fonction de feature doit accepter ou respecter :

```text
fixture_id
prediction_time
```

Règles strictes :

- ne jamais utiliser la fixture cible dans ses propres features historiques ;
- ne jamais utiliser une statistique calculée après le match cible ;
- ne jamais utiliser une lineup officielle si son `fetched_at` est postérieur à `prediction_time` ;
- ne jamais utiliser une injury si son `fetched_at` est postérieur à `prediction_time` ;
- ne jamais utiliser une odd snapshot si son `fetched_at` est postérieur à `prediction_time` ;
- ne jamais utiliser un standing snapshot postérieur à `prediction_time` ;
- ne jamais utiliser un résultat final dans les features.

---

## 5. Usage attendu des documents dans le développement

### 5.1 Sprint ingestion référentiels

Lors de l’implémentation des référentiels :

- créer un loader pour `docs/api_football_reference.json` ;
- créer un loader pour `docs/api_football_players_reference.json` ;
- permettre d’initialiser la base locale sans refaire tous les appels API ;
- conserver la possibilité de refresh live via API-Football ;
- documenter la différence entre seed local et refresh API.

Modules concernés :

```text
src/football_predictor/ingestion/ingest_reference.py
src/football_predictor/config/competitions.py
src/football_predictor/db/repositories.py
```

---

### 5.2 Sprint joueurs et XI probable

Lors du développement des features joueurs :

- utiliser `api_football_players_reference.json` pour relier les joueurs aux équipes ;
- ne pas dépendre exclusivement des lineups si elles sont absentes ;
- utiliser le poste du référentiel comme fallback ;
- utiliser les statistiques de match comme source de forme récente quand disponibles ;
- gérer les joueurs inconnus rencontrés dans les lineups ou injuries en les upsertant avec le payload API.

Modules concernés :

```text
src/football_predictor/features/player_features.py
src/football_predictor/features/xi_features.py
src/football_predictor/features/availability_features.py
```

---

### 5.3 Sprint odds

Lors du développement des odds :

- utiliser `api_football_reference.json` pour comprendre les `bookmaker_id` et `bet_id` disponibles ;
- identifier proprement le marché 1X2 / Match Winner ;
- ne pas supposer qu’un bookmaker ou bet existe pour tous les matchs ;
- gérer les odds manquantes sans faire échouer la prédiction.

Modules concernés :

```text
src/football_predictor/ingestion/ingest_odds.py
src/football_predictor/features/odds_features.py
```

---

### 5.4 Sprint tests

Les tests doivent éviter les IDs inventés.

Pour les tests réalistes :

- extraire de petits échantillons depuis `api_football_reference.json` ;
- extraire de petits échantillons depuis `api_football_players_reference.json` ;
- stocker ces échantillons dans `tests/fixtures/` ;
- ne pas faire dépendre les tests unitaires de fichiers énormes si cela ralentit trop l’exécution ;
- ne jamais faire d’appels réseau dans les tests unitaires.

Bonnes pratiques :

```text
- tests unitaires : payloads minimaux et déterministes
- tests intégration locale : référentiels JSON docs/
- tests live : uniquement avec flag explicite ou script séparé
```

---

## 6. Modules à prévoir autour des fichiers docs

Codex peut créer un module de chargement des référentiels locaux.

Nom recommandé :

```text
src/football_predictor/reference/
```

Fichiers recommandés :

```text
src/football_predictor/reference/__init__.py
src/football_predictor/reference/loaders.py
src/football_predictor/reference/schemas.py
src/football_predictor/reference/lookups.py
```

Fonctions utiles :

```python
load_api_football_reference(path: str | Path) -> ApiFootballReference
load_players_reference(path: str | Path) -> PlayersReference
find_league_by_id(league_id: int)
find_team_by_id(team_id: int)
find_team_by_name(name: str, league_id: int | None = None)
find_player_by_id(player_id: int)
find_players_by_team(team_id: int)
find_bookmaker_by_id(bookmaker_id: int)
find_bet_by_id(bet_id: int)
validate_fixture_reference(fixture_id: int)
```

Ces fonctions doivent :

- être typées ;
- tolérer les champs manquants ;
- retourner des erreurs explicites ;
- ne jamais appeler l’API live ;
- lire uniquement les fichiers locaux.

---

## 7. Configuration recommandée

Ajouter dans `.env.example` ou settings :

```env
API_FOOTBALL_REFERENCE_PATH=docs/api_football_reference.json
API_FOOTBALL_PLAYERS_REFERENCE_PATH=docs/api_football_players_reference.json
API_FOOTBALL_PLAYERS_CACHE_PATH=docs/api_football_players_cache.json
```

Dans le code, ces chemins doivent être configurables, mais les valeurs ci-dessus peuvent servir de défauts.

---

## 8. Initialisation locale depuis les docs

Prévoir une commande CLI permettant de charger la base locale depuis les fichiers de référence, sans consommer de quota API.

Commande recommandée :

```bash
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json
```

Comportement attendu :

- charger les compétitions ;
- charger les équipes ;
- charger les venues si présentes ;
- charger les joueurs ;
- charger les squads ;
- produire un résumé : nombre de leagues, teams, venues, players, squads ;
- être idempotent ;
- ne faire aucun appel API.

---

## 9. Quand utiliser l’API live malgré les docs

Les fichiers `docs/` sont des référentiels, mais ils ne remplacent pas toutes les données dynamiques.

Utiliser API-Football live pour :

- fixtures récentes ou futures ;
- nouveaux standings ;
- blessures récentes ;
- odds récentes ;
- lineups officielles ;
- statistiques des derniers matchs ;
- predictions API-Football ;
- mise à jour des squads si le référentiel est obsolète.

Règle :

> Les fichiers docs servent à éviter les suppositions et à accélérer l’initialisation. Les données temporelles doivent être snapshotées depuis l’API ou depuis la DB.

---

## 10. Format des prédictions Discord attendu

La sortie Discord doit rester claire, concise et en français.

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

---

## 11. Checklist avant modification importante

Avant toute tâche importante, Codex doit vérifier :

```text
1. Le besoin concerne-t-il des IDs API-Football ?
   -> ouvrir docs/api_football_reference.json ou .md.

2. Le besoin concerne-t-il des joueurs ?
   -> ouvrir docs/api_football_players_reference.json ou .md.

3. Le besoin concerne-t-il un cache de collecte ?
   -> utiliser docs/api_football_players_cache.json uniquement si nécessaire.

4. Le besoin concerne-t-il des features historiques ?
   -> vérifier prediction_time et anti data leakage.

5. Le besoin concerne-t-il des tests ?
   -> utiliser des fixtures locales, pas d’appel réseau.

6. Le besoin concerne-t-il Discord ou API keys ?
   -> ne jamais logger les secrets.
```

---

## 12. Prompts utiles pour Codex

### Demander à Codex de se référer aux docs

```text
Avant de modifier le code, ouvre et utilise les fichiers suivants si nécessaire :
- docs/api_football_reference.md
- docs/api_football_reference.json
- docs/api_football_players_reference.md
- docs/api_football_players_reference.json
- docs/api_football_players_cache.json

Ne devine aucun ID API-Football. Utilise les JSON pour le code et les MD pour comprendre le contexte.
```

### Demander un contrôle anti fuite de données

```text
Relis ton diff et vérifie qu’aucune feature n’utilise de donnée postérieure à prediction_time.
Vérifie particulièrement : odds, injuries, standings, lineups, player stats et fixtures historiques.
```

### Demander une validation des IDs

```text
Vérifie que tous les league_id, team_id, player_id, bookmaker_id et bet_id utilisés dans ce changement existent dans les fichiers de référence sous docs/.
Si un ID est absent, remplace-le ou explique pourquoi il est nécessaire.
```

---

## 13. Règles de mise à jour des fichiers docs

Les fichiers de référence ne doivent pas être modifiés manuellement sans raison.

Modifier ces fichiers seulement si :

- un script de collecte ou refresh les régénère ;
- le format de référence est volontairement amélioré ;
- une nouvelle compétition est ajoutée ;
- une nouvelle saison est ajoutée ;
- les squads sont rafraîchis.

Après modification :

- vérifier que les JSON restent valides ;
- vérifier que les Markdown restent lisibles ;
- vérifier que les compteurs de joueurs, équipes et ligues sont cohérents ;
- documenter la date de refresh si possible.

---

## 14. Principe général

Ce projet doit être construit comme un système prédictif sérieux, pas comme un script ponctuel.

Les priorités sont :

1. robustesse ;
2. absence de fuite de données ;
3. traçabilité des données ;
4. qualité des probabilités ;
5. explicabilité ;
6. automatisation Discord ;
7. économie du quota API ;
8. facilité de maintenance avec Codex.

Rappel final :

> Ne jamais inventer ce que les fichiers `docs/` peuvent vérifier.  
> Ne jamais utiliser le futur pour prédire le passé.  
> Ne jamais logger de secret.  
> Ne jamais faire échouer toute une prédiction parce qu’une source optionnelle est absente.
