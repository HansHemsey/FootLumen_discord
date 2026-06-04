# START_ROUTINE.md — Routine Locale Football Predictor

Ce document est le guide pratique pour faire tourner l'outil sur ton Mac en local.

Objectif :

- garder la DB locale à jour ;
- publier les bons messages dans les bons channels Discord ;
- économiser le quota API-Football ;
- éviter les doublons ;
- enrichir progressivement l'historique pour améliorer le modèle.

Toutes les commandes partent du dossier projet :

```bash
cd /Users/yanisruel/Documents/ProBet_discord
```

Si besoin :

```bash
source .venv/bin/activate
```

Les scripts utilisent automatiquement le bon binaire local via `scripts/lib.sh`. Ils évitent donc le problème fréquent `ModuleNotFoundError: football_predictor`.

---

## 1. Règles Simples

### Par défaut, Discord n'envoie rien

Les scripts sont sûrs par défaut :

```text
SEND_DISCORD=false
DRY_RUN=true
```

Pour envoyer réellement sur Discord :

```bash
SEND_DISCORD=true DRY_RUN=false <script>
```

### Pas d'appel API implicite dans les commandes dry-run Discord

Les publications Discord peuvent fonctionner depuis la DB locale.

Les scripts avec refresh API explicite sont ceux qui utilisent :

```text
REFRESH_DATA=true
REFRESH_DETAILS=true
--refresh-api
```

### Ne lance pas de gros backfill avant un match

Garde le quota API pour les prédictions proches du coup d'envoi.

---

## 2. Commandes De Diagnostic

A lancer avant une grosse session ou si quelque chose semble cassé :

```bash
football-predictor doctor --strict
football-predictor data-quality
```

Ce que ça vérifie :

- `.env` chargé ;
- API key présente sans l'afficher ;
- DB accessible ;
- fichiers `docs/` présents et JSON valides ;
- configs Discord présentes ;
- qualité des données disponibles.

Ces commandes ne font pas d'appel API live.

---

## 3. Routine Matin — Tous Les Jours

Commande dry-run recommandée :

```bash
scripts/daily_morning.sh
```

Ce que ça fait :

1. `doctor --strict` ;
2. `init-db` sans reset ;
3. `seed-reference-from-docs` idempotent ;
4. refresh des standings ;
5. refresh des odds du jour ;
6. publication dry-run de :
   - `classement` ;
   - `calendrier` ;
   - `matchs_du_jour` ;
   - `score_pronos_semaine`.

Ce que ça ne fait plus :

- aucune prédiction matinale ;
- aucun message dans `predictions`.

Les prédictions sont réservées à :

- l'analyse H-6 dans `analyses` ;
- la prédiction late M-30 dans `predictions`.

Envoi réel Discord :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_morning.sh
```

### Quand le lancer

```text
Tous les matins, vers 08h00-10h00.
```

Même s'il n'y a pas de match, c'est utile pour :

- vérifier la santé du projet ;
- maintenir standings / odds / fixtures ;
- publier classement, calendrier et matchs du jour si la DB contient les données.
- mettre à jour le score hebdomadaire des pronostics publiés.

---

## 4. Publications Quotidiennes Discord

Si tu veux publier uniquement les channels opérationnels sans lancer les prédictions :

Dry-run :

```bash
scripts/publish_daily_discord.sh
```

Envoi réel :

```bash
DRY_RUN=false scripts/publish_daily_discord.sh
```

Channels alimentés :

```text
classement
calendrier
matchs_du_jour
score_pronos_semaine
```

Le score hebdomadaire est global, toutes compétitions confondues. Il compte uniquement
les prédictions réellement envoyées dans le channel `predictions` : V2 legacy, V3 via
`v3_model_prediction_id`, et O/U 2.5 via `ou_model_prediction_id`. Les prédictions
stockées mais non publiées pour confiance insuffisante ne sont pas comptées. Les matchs
en attente ne sont pas affichés : seules les prédictions terminées, correctes ou
incorrectes, entrent dans le bilan. Le lundi, le script publie deux bilans :

- la finalisation de la semaine précédente, pour inclure les matchs du dimanche dont les
  scores sont arrivés pendant la nuit ;
- le message de la nouvelle semaine.

Chaque bilan est remplacé uniquement à l'intérieur de sa propre semaine (`week_key`).
Le message de la semaine précédente reste donc en historique quand une nouvelle semaine
commence.

Comportement important :

- ces messages sont en blocs markdown alignés ;
- chaque message reste sous 2000 caractères ;
- si un message est trop long, il est découpé en plusieurs parties ;
- `REPLACE_PREVIOUS=true` par défaut ;
- les anciens messages envoyés par l'outil sont supprimés puis remplacés ;
- les anciens messages envoyés avant le stockage du `message_id` peuvent devoir être supprimés manuellement une fois.

Forcer le remplacement :

```bash
FORCE=true DRY_RUN=false scripts/publish_daily_discord.sh
```

Désactiver le remplacement :

```bash
REPLACE_PREVIOUS=false DRY_RUN=false scripts/publish_daily_discord.sh
```

---

## 5. Analyse H-6

Une analyse est publiée dans le channel `analyses` une seule fois par match.

Commande dry-run :

```bash
scripts/publish_match_analyses.sh
```

Envoi réel :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh
```

Fenêtre d'envoi :

```text
H-6 -> H-5h45
```

Par défaut :

```text
ANALYSIS_GRACE_MINUTES=15
```

Exemple avec marge plus large :

```bash
ANALYSIS_GRACE_MINUTES=400 SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh
```

Ce que contient l'analyse :

- contexte du match ;
- forme récente home / away ;
- classement et dynamique ;
- odds et mouvement des cotes ;
- absences / XI probable si disponibles ;
- points forts / faibles ;
- niveau de fiabilité des données ;
- conclusion prudente.

Important :

- pas de remplacement ;
- pas d'écrasement ;
- historique conservé dans `analyses` ;
- un verrou DB évite de republier la même analyse sauf `FORCE=true`.

### Quand le lancer

```text
Toutes les 15 minutes les jours de match.
```

Manuellement :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh
```

---

## 6. Prédiction Late M-30

La prédiction late est le message principal envoyé dans `predictions`.
Depuis Sprint 10, `scripts/daily_late.sh` utilise la V3 par défaut.

Commande dry-run :

```bash
scripts/daily_late.sh
```

Envoi réel :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

Rollback V2 explicite :

```bash
PREDICTION_ENGINE=v2 SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

Règle publique commune V3 1X2 et O/U 2.5 : Discord publie uniquement `High` ou
`Very High`. Les labels `Medium`, `Low`, `Uncertain` et assimilés restent internes avec
`confidence_skipped`.

Ce que ça fait :

- sélectionne uniquement les matchs qui commencent dans les 30 prochaines minutes ;
- utilise `prediction_time=now` ;
- refresh les données utiles avant match :
  - fixture ;
  - odds ;
  - injuries ;
  - predictions API ;
  - lineups si disponibles ;
- construit le `FeatureSnapshot` ;
- calcule la prédiction V3 et persiste `V3FeatureSnapshot` / `V3ModelPrediction` ;
- envoie dans `predictions` si Discord réel est activé ;
- ne renvoie pas deux fois une prédiction late pour le même match sauf `FORCE=true`.

Statut : la V3 est activée en production Discord malgré un backtest non validé. Surveiller
les premiers envois réels, surtout la couverture odds/API/lineups rafraîchie à M-30.

### Quand le lancer

```text
Toutes les 5-10 minutes les jours de match.
```

Manuellement, autour de M-30 :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

Avec limite pour tester :

```bash
LIMIT=1 scripts/daily_late.sh
```

Forcer un nouvel envoi si nécessaire :

```bash
FORCE=true SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

---

## 7. Résultats Après Match

Les résultats sont publiés dans `resultats`, une seule fois par match terminé.

Commande dry-run :

```bash
scripts/publish_match_results.sh
```

Envoi réel sans refresh :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
```

Envoi réel avec refresh des scores finaux :

```bash
REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
```

Ce que ça fait :

- sélectionne les fixtures en statut `FT`, `AET` ou `PEN` ;
- vérifie que le score final est en DB ;
- compare avec la dernière prédiction pré-match publiée si disponible ;
- publie :
  - score final ;
  - résultat 1X2 ;
  - prédiction publiée ;
  - probabilités pré-match ;
  - confiance initiale ;
  - bon / mauvais pronostic ;
  - mini bilan.

Important :

- pas de remplacement ;
- historique conservé dans `resultats` ;
- un résultat déjà publié n'est pas renvoyé sauf `FORCE=true`.

### Quand le lancer

```text
Toutes les 30-60 minutes après les matchs.
```

---

## 8. Routine Jour Avec Match

### Le matin

```bash
scripts/daily_morning.sh
```

ou en réel Discord :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_morning.sh
```

### Autour de H-6

```bash
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh
```

### Autour de M-30

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

### Après le match

```bash
REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
```

### Version prudente en dry-run

```bash
scripts/daily_morning.sh
scripts/publish_match_analyses.sh
scripts/daily_late.sh
scripts/publish_match_results.sh
```

---

## 9. Routine Jour Sans Match

Commande minimale :

```bash
scripts/daily_morning.sh
football-predictor data-quality
```

Tu peux aussi utiliser les jours sans match pour enrichir l'historique :

```bash
REFRESH_DETAILS=true \
DETAILS_ONLY="statistics events players" \
DETAILS_DAYS_BACK=7 \
DETAILS_STATUSES="FT AET PEN" \
DETAILS_LIMIT=100 \
DETAILS_DELAY_SECONDS=3 \
DETAILS_SKIP_IF_COMPLETE=true \
scripts/refresh_all_leagues.sh
```

Puis :

```bash
football-predictor data-quality
```

---

## 10. Enrichissement Historique Hebdomadaire

But : récupérer les données détaillées des matchs passés pour améliorer les features et le futur entraînement.

Commande recommandée, une fois par semaine :

```bash
REFRESH_DETAILS=true \
DETAILS_ONLY="statistics events players" \
DETAILS_DAYS_BACK=7 \
DETAILS_STATUSES="FT AET PEN" \
DETAILS_LIMIT=100 \
DETAILS_DELAY_SECONDS=3 \
DETAILS_SKIP_IF_COMPLETE=true \
scripts/refresh_all_leagues.sh
```

Ce que ça récupère :

```text
/fixtures/statistics
/fixtures/events
/fixtures/players
```

Ce que ça cible :

```text
matchs terminés des 7 derniers jours
statuts FT, AET, PEN
toutes les compétitions enabled dans config/competitions.yaml
```

Par défaut, `refresh_all_leagues.sh` utilise maintenant :

```text
DETAILS_SKIP_IF_COMPLETE=true
```

Cela veut dire que, pour une fixture déjà enrichie, le script ne rappelle pas les endpoints
déjà présents en DB ou déjà connus comme `no content`. Le skip se fait endpoint par endpoint :
si `statistics` et `players` existent déjà mais que `events` manque, seul `events` est rappelé.
Tu économises donc du quota sans empêcher la DB de compléter les trous.

Budget approximatif :

```text
1 match = 3 appels API
50 matchs = 150 appels
100 matchs = 300 appels
```

Avec `DETAILS_DELAY_SECONDS=3`, le script est volontairement lent pour limiter les `429`.

Options utiles :

```bash
# Plus prudent
DETAILS_LIMIT=30

# Plus large si quota OK
DETAILS_LIMIT=150

# Dates explicites au lieu de DAYS_BACK
DETAILS_FROM=2026-05-01 DETAILS_TO=2026-05-07
```

Exemple dates explicites :

```bash
REFRESH_DETAILS=true \
DETAILS_ONLY="statistics events players" \
DETAILS_FROM=2026-05-01 \
DETAILS_TO=2026-05-07 \
DETAILS_STATUSES="FT AET PEN" \
DETAILS_LIMIT=100 \
DETAILS_DELAY_SECONDS=3 \
DETAILS_SKIP_IF_COMPLETE=true \
scripts/refresh_all_leagues.sh
```

Ne fais pas de backfill massif sans période :

```bash
# A éviter
REFRESH_DETAILS=true DETAILS_LIMIT=9999 scripts/refresh_all_leagues.sh
```

### Config production vs historique

```text
config/competitions.yaml         : production quotidienne, saison courante
config/competitions_history.yaml : entrainement/backtest, saisons 2022 a 2025
```

Le refresh quotidien et hebdomadaire ecrit toujours en DB avec le bon couple
`league_id` / `season`. Le modele retrouve ensuite ces fixtures via
`config/competitions_history.yaml`, parce que la saison courante y est incluse. Il ne faut
donc pas dupliquer les lignes historiques dans `config/competitions.yaml`.

### Backfill d'une saison complete

Pour remonter proprement une saison API-Football entiere sur toutes les ligues activees,
utilise le script dedie :

```bash
SEASON=2024 scripts/backfill_season.sh
```

Cela signifie :

```text
season API-Football : 2024
periode par defaut : 2024-08-01 -> 2025-07-31
ligues             : les cinq championnats de config/competitions_history.yaml
details            : statistics, events, players
statuts            : FT, AET, PEN
limite             : 400 fixtures par ligue/saison
delai              : 3 secondes entre fixtures
skip               : endpoints deja complets ignores
```

Le script genere automatiquement :

```text
data/processed/backfill/competitions_2024.yaml
```

avec uniquement les lignes de la saison demandee. Il lance aussi `ingest-teams` sur cette
config, ce qui permet de recuperer les equipes propres a cette saison, y compris les clubs
promus ou relegues. Les fixtures seront ensuite stockees avec leur `season` API-Football
reelle. Les competitions de coupe/globales, comme la CDM, restent exclues par defaut du
backfill de championnats.

Si tu veux resoudre les joueurs inconnus dans la meme passe :

```bash
SEASON=2024 \
RESOLVE_UNKNOWN_PLAYERS=true \
UNKNOWN_PLAYERS_LIMIT=100 \
UNKNOWN_PLAYERS_DELAY_SECONDS=2 \
scripts/backfill_season.sh
```

Pour plus de prudence quota, fais plutot en deux temps :

```bash
SEASON=2024 scripts/backfill_season.sh

REFRESH_FIXTURES=false \
REFRESH_STANDINGS=false \
REFRESH_ODDS=false \
REFRESH_DETAILS=false \
RESOLVE_UNKNOWN_PLAYERS=true \
UNKNOWN_PLAYERS_LIMIT=100 \
UNKNOWN_PLAYERS_DELAY_SECONDS=2 \
scripts/refresh_all_leagues.sh
```

---

## 11. Joueurs Inconnus

Quand l'API retourne des joueurs absents du référentiel local, ils sont enregistrés dans :

```text
data/processed/unknown_players.jsonl
```

Pour les résoudre et enrichir la DB locale :

```bash
RESOLVE_UNKNOWN_PLAYERS=true \
UNKNOWN_PLAYERS_LIMIT=50 \
UNKNOWN_PLAYERS_DELAY_SECONDS=2 \
scripts/refresh_all_leagues.sh
```

Ce que ça fait :

- lit `unknown_players.jsonl` ;
- déduplique les `player_id` ;
- appelle `/players?id=...&season=...` si possible ;
- peut utiliser `/players/squads?team=...` en fallback ;
- upsert `Player` et `PlayerSquad` en DB ;
- ne modifie jamais les fichiers `docs/api_football_players_reference.*`.

Depuis le patch récent :

- les joueurs résolus sont retirés de `unknown_players.jsonl` ;
- les joueurs déjà résolus en DB ne sont pas rappelés à l'API ;
- les joueurs encore inconnus restent dans le fichier ;
- en `--dry-run`, le fichier n'est pas nettoyé.

Commande complète avec détails + résolution :

```bash
REFRESH_DETAILS=true \
DETAILS_ONLY="statistics events players" \
DETAILS_DAYS_BACK=7 \
DETAILS_STATUSES="FT AET PEN" \
DETAILS_LIMIT=100 \
DETAILS_DELAY_SECONDS=3 \
DETAILS_SKIP_IF_COMPLETE=true \
RESOLVE_UNKNOWN_PLAYERS=true \
UNKNOWN_PLAYERS_LIMIT=50 \
UNKNOWN_PLAYERS_DELAY_SECONDS=2 \
scripts/refresh_all_leagues.sh
```

---

## 12. Entraînement Et Backtest

Le dossier `data/models/` reste vide tant que tu n'as pas entraîné de modèle.

Quand tu as assez de matchs terminés en DB :

```bash
scripts/train_backtest_all.sh
```

Ce que ça fait :

1. construit `data/processed/training_v2_late.parquet` en fenêtre M-30 ;
2. entraîne le modèle V2 dans `data/models/v2-late` ;
3. lance le backtest temporel V2 ;
4. écrit le rapport dans `reports/backtest_v2_late`.

Concept V2 :

- plusieurs experts produisent une probabilité : marché calibré, Poisson V2, Elo V2,
  modèle tabulaire ;
- un stacking V2 apprend à combiner ces experts sur validation temporelle ;
- les probabilités par expert sont stockées dans les prédictions pour expliquer les
  décisions ;
- la V1 reste disponible en rollback dans `data/models/v1`.

Rythme conseillé :

```text
Début du projet : manuel, après avoir accumulé assez de données.
Ensuite         : une fois par semaine.
```

Commande avec paramètres :

```bash
PREDICTION_WINDOW=30m \
MODEL_DIR=data/models/v2-late \
MODEL_VERSION=v2-late \
scripts/train_backtest_all.sh
```

---

## 13. Prédire Une Fixture Précise

Sans refresh API :

```bash
football-predictor predict --fixture <fixture_id> --model-dir data/models/v2-late
```

Avec refresh API explicite :

```bash
football-predictor predict \
  --fixture <fixture_id> \
  --model-dir data/models/v2-late \
  --refresh-data
```

Sans modèle entraîné, l'outil utilise les fallbacks disponibles :

```text
odds
Poisson
API prediction si disponible
prior conservateur si données pauvres
```

---

## 14. Ordre Recommandé Par Situation

### A. Premier lancement de la journée

```bash
scripts/daily_morning.sh
football-predictor data-quality
```

### B. Matin avec envoi Discord réel

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_morning.sh
```

### C. Analyse H-6

```bash
SEND_DISCORD=true DRY_RUN=false scripts/publish_match_analyses.sh
```

### D. Prédiction M-30

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

### E. Résultat post-match

```bash
REFRESH_DATA=true SEND_DISCORD=true DRY_RUN=false scripts/publish_match_results.sh
```

### F. Enrichissement hebdomadaire

```bash
REFRESH_DETAILS=true \
DETAILS_ONLY="statistics events players" \
DETAILS_DAYS_BACK=7 \
DETAILS_STATUSES="FT AET PEN" \
DETAILS_LIMIT=100 \
DETAILS_DELAY_SECONDS=3 \
DETAILS_SKIP_IF_COMPLETE=true \
scripts/refresh_all_leagues.sh
```

### G. Résolution joueurs inconnus

```bash
RESOLVE_UNKNOWN_PLAYERS=true \
UNKNOWN_PLAYERS_LIMIT=50 \
UNKNOWN_PLAYERS_DELAY_SECONDS=2 \
scripts/refresh_all_leagues.sh
```

### H. Entraînement hebdomadaire

```bash
scripts/train_backtest_all.sh
scripts/train_backtest_ou.sh
```

Ces scripts utilisent `config/competitions_history.yaml` par defaut :

```text
1X2 : data/models/v2-late
O/U : data/models/ou-v1
```

Les scripts de production (`daily_morning.sh`, `daily_late.sh`, `daily_ou.sh`) restent sur
`config/competitions.yaml`.

Le lundi, `scripts/weekly_ingestion.sh` prépare les fixtures futures selon la convention
`J+7` : date locale d'exécution incluse puis les 6 dates suivantes. Ne pas confondre avec
`DETAILS_DAYS_BACK=7`, qui reste un `J-7` pour enrichir les détails des matchs terminés.

---

## 15. Fréquence Conseillée

```text
Tous les matins       : scripts/daily_morning.sh
Jours de match H-6    : scripts/publish_match_analyses.sh toutes les 15 min
Jours de match M-30   : scripts/daily_late.sh toutes les 5-10 min
Jours de match M-30   : scripts/daily_ou.sh toutes les 5-10 min
Après les matchs      : scripts/publish_match_results.sh toutes les 30-60 min
Chaque lundi          : scripts/weekly_ingestion.sh pour les fixtures J+7
Une fois par semaine  : refresh_all_leagues.sh avec DETAILS_DAYS_BACK=7 pour le passé
Une fois par semaine  : train_backtest_all.sh, quand assez de données existent
Au besoin             : resolve unknown players
```

Sur ton PC local, tu peux lancer ces scripts manuellement. Un cron n'est utile que si ton Mac reste allumé et éveillé.

La crontab prod autonome est versionnée et installable directement :

```bash
scripts/install_prod_cron.sh
crontab -l
```

Elle utilise `config/prod.crontab`, publie réellement dans Discord avec
`SEND_DISCORD=true DRY_RUN=false`, protège chaque routine avec `lockf`, et écrit les logs
dans `logs/cron/`.

---

## 16. Variables Utiles

### Communes

```text
DATE=YYYY-MM-DD
CONFIG=config/competitions.yaml
PREDICTION_ENGINE=v3
MODEL_DIR=data/models/v3
V2_MODEL_DIR=data/models/v2-late
LIMIT=1
FORCE=true
SAVE_RAW=true
```

### Discord

```text
SEND_DISCORD=true
DRY_RUN=false
PRINT_ONLY=true
REPLACE_PREVIOUS=true
```

### Analyses

```text
ANALYSIS_GRACE_MINUTES=15
```

### Résultats

```text
REFRESH_DATA=true
```

### Backfill détails

```text
REFRESH_DETAILS=true
DETAILS_ONLY="statistics events players"
DETAILS_DAYS_BACK=7
DETAILS_STATUSES="FT AET PEN"
DETAILS_LIMIT=100
DETAILS_DELAY_SECONDS=3
DETAILS_SKIP_IF_COMPLETE=true
DETAILS_FROM=YYYY-MM-DD
DETAILS_TO=YYYY-MM-DD
```

### Joueurs inconnus

```text
RESOLVE_UNKNOWN_PLAYERS=true
UNKNOWN_PLAYERS_LIMIT=50
UNKNOWN_PLAYERS_DELAY_SECONDS=2
UNKNOWN_PLAYERS_SQUADS_FALLBACK=true
```

---

## 17. Gestion Du Quota API-Football

Ton quota est de 7500 appels par jour.

Ordres de grandeur :

```text
daily_morning         : léger à modéré selon ligues enabled
daily_late            : important mais ciblé sur les matchs proches et prédits à M-30
publish results refresh: léger si seulement fixtures du jour
details historiques   : 3 appels par match avec statistics/events/players
unknown players       : jusqu'à UNKNOWN_PLAYERS_LIMIT appels, plus fallback squad éventuel
```

Conseils :

- garde `DETAILS_DELAY_SECONDS=3` ;
- garde `UNKNOWN_PLAYERS_DELAY_SECONDS=2` ;
- ne lance pas un backfill détails complet les jours avec beaucoup de matchs ;
- si tu vois `429`, arrête et attends le reset API ;
- réserve toujours du quota pour `daily_late`.

---

## 18. Ce Que Chaque Channel Reçoit

```text
classement       : classement actuel, remplacé à chaque publication quotidienne
calendrier       : prochaine journée / round, remplacé à chaque publication quotidienne
matchs_du_jour   : matchs de la date cible, remplacé à chaque publication quotidienne
analyses         : analyse H-6 unique par match, historique conservé
predictions      : prédiction late M-30 unique par match, historique conservé
resultats        : bilan post-match unique par match, historique conservé
discussions      : jamais alimenté automatiquement par défaut
```

---

## 19. Commandes De Secours

Vérifier la santé :

```bash
football-predictor doctor --strict
```

Voir la qualité des données :

```bash
football-predictor data-quality
```

Tester les webhooks sans envoyer :

```bash
football-predictor discord-check-config
```

Publier uniquement en console :

```bash
PRINT_ONLY=true scripts/publish_daily_discord.sh
```

Limiter un run à un seul élément :

```bash
LIMIT=1 scripts/daily_late.sh
LIMIT=1 scripts/publish_match_results.sh
```

---

## 20. Règles À Ne Pas Oublier

- Ne mets jamais de clé API, webhook ou bot token dans une commande partagée.
- Les prédictions sont probabilistes, jamais des certitudes.
- Si une donnée manque, l'outil doit afficher `non disponible`.
- Les features doivent respecter `prediction_time`.
- Les détails `statistics/events/players` servent surtout aux matchs passés.
- Les matchs à venir utilisent surtout odds, standings, blessures et lineups pré-match si disponibles.
- `lineups` n'est pas à backfill massivement tous les jours.
- `data/models/` reste vide tant qu'un entraînement n'a pas été lancé.
- Les fichiers `docs/api_football_*` ne doivent pas être modifiés par les routines.
