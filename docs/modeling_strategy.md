# Modeling Strategy

## Objectif

Le système doit prédire les classes `HOME`, `DRAW`, `AWAY` avec des probabilités calibrées
et explicables. Les probabilités doivent toujours être normalisées.

## Modèle Sportif

Le modèle sportif exploite les features disponibles avant `prediction_time` :

- forme récente `last_3`, `last_5`, `last_10`, `last_15` ;
- EWMA de forme ;
- performance domicile/extérieur ;
- buts pour et contre ;
- clean sheets et failed to score ;
- statistiques de tirs, possession, passes, corners, fautes, cartons ;
- standings ;
- repos et calendrier ;
- joueurs, XI type, XI probable, absences et blessures ;
- stabilité du XI et qualité du banc.

Le modèle V1 doit accepter des données manquantes. Les imputations appartiennent au
preprocessing ou au modèle, et la qualité de couverture doit rester visible.

### Pseudo-xG V1

API-Football ne garantit pas une métrique xG exploitable dans tous les payloads. La V1
expose donc une heuristique `pseudo_xg` calculée depuis les statistiques disponibles :

```text
pseudo_xg =
0.03 * total_shots
+ 0.09 * shots_on_goal
+ 0.07 * shots_insidebox
+ 0.02 * shots_outsidebox
+ 0.76 * penalties
```

Cette valeur sert uniquement de signal sportif initial. Elle est calculée point-in-time
depuis `FixtureStatistics.fetched_at <= prediction_time`, jamais depuis une statistique
postérieure au moment de prédiction. Les penalties ne sont ajoutés que s'ils proviennent
d'events disponibles avant le cutoff. Si aucune métrique de tir ou penalty n'est disponible,
la feature reste `None` et la qualité des données le signale.

### Joueurs, XI Et Absences V1

Les features joueurs/XI enrichissent le modèle sportif avec la structure probable des deux
équipes avant le match. Elles sont construites sans API live, depuis les snapshots déjà
stockés et le référentiel joueurs local.

La formation probable est la formation modale pondérée par récence sur les derniers matchs
avec lineup disponible avant `prediction_time`.

La probabilité de titularisation V1 est :

```text
P_start =
0.50 * weighted_start_frequency
+ 0.25 * weighted_minutes_share
+ 0.15 * formation_position_compatibility
+ 0.10 * recent_availability
```

La valeur joueur V1 combine rating, minutes, contribution offensive et probabilité de
titularisation, puis normalise le résultat par groupe de poste (`GK`, `DEF`, `MID`, `ATT`).
Cette normalisation évite de comparer directement des rôles différents.
Les sorties intermédiaires incluent `value_zscore` et `value_0_100`, calculées au sein du
groupe de poste.

Le XI probable sélectionne les joueurs disponibles selon `P_start * player_value`, avec des
contraintes grossières dérivées de la formation. Les joueurs blessés ou suspendus avec une
sévérité complète sont exclus du XI attendu.

L'impact absence V1 est :

```text
absence_impact =
P_start * player_value * severity * replacement_gap * position_multiplier
```

Le `replacement_gap` compare l'absent au meilleur remplaçant disponible du même groupe de
poste. Un joueur peu probable titulaire (`P_start < 0.35`) est amorti afin de ne pas
surpénaliser les absences de rotation. Les coefficients initiaux sont `GK=1.30`,
`ATT=1.25`, `MID=1.00`, `DEF=1.00`, avec un bonus défenseur central seulement si la grille
de lineup permet de l'identifier.

La sévérité d'absence V1 est volontairement simple : `Missing Fixture` ou suspension vaut
`1.0`, `Questionable` / incertain vaut `0.6`, et un libellé mineur ou inconnu vaut `0.3`.

Le référentiel `docs/api_football_players_reference.json` sert uniquement de fallback
d'identité, poste et numéro. Les informations dynamiques utilisées par le modèle doivent
rester point-in-time : lineups, stats joueurs et injuries sont filtrées avec
`fetched_at <= prediction_time`, et la fixture cible est exclue des historiques.

## Modèle Odds

Le modèle odds utilise les cotes prematch du marché 1X2 / `Match Winner`.

Pour chaque bookmaker :

```text
q_home = 1 / odd_home
q_draw = 1 / odd_draw
q_away = 1 / odd_away
overround = q_home + q_draw + q_away - 1
```

Puis les probabilités sans marge :

```text
p_home = q_home / (q_home + q_draw + q_away)
p_draw = q_draw / (q_home + q_draw + q_away)
p_away = q_away / (q_home + q_draw + q_away)
```

Le consensus multi-bookmakers peut pondérer les bookmakers par inverse de l'overround,
calculer une dispersion et mesurer le mouvement si plusieurs snapshots existent.

Règles :

- utiliser uniquement des odds prematch en V1 ;
- utiliser uniquement `fetched_at <= prediction_time` ;
- ne pas supposer qu'un bookmaker existe pour tous les matchs ;
- gérer les odds manquantes sans bloquer toute la prédiction.

## Prédiction API-Football

Les prédictions API-Football peuvent être utilisées comme source auxiliaire si elles ont été
snapshotées avant `prediction_time`.

Elles ne remplacent pas le modèle sportif ni les odds. Elles doivent être traçables via
`ApiPredictionSnapshot`.

## Feature Builder Global

`global_features_v1` assemble les signaux sportifs, joueurs/XI, marché et prédiction API
dans un snapshot unique. Il ne déclenche aucune ingestion et lit uniquement les snapshots
déjà disponibles avant `prediction_time`.

La qualité globale est exprimée par `data_quality_score` sur 100. Les sources manquantes
ne bloquent pas la construction du snapshot ; elles restent explicites via flags et
warnings afin que le modèle ou le preprocessing puisse décider de l'imputation.

## Dataset D'Entraînement

Le dataset historique reconstruit chaque ligne comme une prédiction passée :

- fixtures terminées uniquement ;
- `prediction_time = fixture.date - 24h` par défaut ;
- variantes supportées : `6h`, `30m` et `40m` avant le match ;
- labels `HOME/DRAW/AWAY` ajoutés après la construction du snapshot ;
- aucune cible ou score final dans `features_json`.

Cette séparation permet d'entraîner, calibrer et backtester sans fuite de résultats ou de
statistiques postérieures au match.

## Modèle ML V1

Le modèle sportif entraîné par défaut utilise scikit-learn uniquement :

```text
HistGradientBoostingClassifier multiclass
```

Ce choix privilégie une V1 robuste, installable et capable de gérer les valeurs manquantes.
Si l'estimateur par défaut échoue sur un dataset donné, le fallback est une pipeline
`SimpleImputer -> StandardScaler -> LogisticRegression`. CatBoost et LightGBM restent
optionnels pour de futurs sprints, mais ne sont pas requis.

Le sélecteur de features V1 n'utilise que les colonnes numériques sûres. Sont exclues avant
entraînement :

- cible et scores finaux : `target`, `home_goals`, `away_goals` ;
- IDs naïfs : `fixture_id`, `feature_snapshot_id`, `league_id`, `season`, `home_team_id`,
  `away_team_id`, `player_id`, `bookmaker_id`, `bet_id` ;
- statuts post-match : `status`, `status_short`, `status_long` ;
- dates et timestamps : `fixture_date`, `prediction_time`, `*_date`, `*_time`, `fetched_at`,
  `created_at`, `updated_at` ;
- JSON bruts et payloads : `*_json`, `payload*`.

Les probabilités marché et API déjà construites point-in-time peuvent rester dans le modèle
comme colonnes numériques. Les colonnes identifiantes pourront être réintroduites seulement
avec un encodage contrôlé et validé par backtesting.

## Baselines V1

Les baselines servent à comparer le modèle et à fournir des fallbacks :

- odds-only : lit `market_home`, `market_draw`, `market_away` ou `p_market_*`, puis
  normalise ;
- API prediction : lit `api_pred_home`, `api_pred_draw`, `api_pred_away` si disponibles ;
- Poisson simple : estime des lambdas depuis les moyennes de buts pour/contre et énumère les
  scores `0..10` pour produire `HOME/DRAW/AWAY` ;
- prior conservateur : utilisé seulement si aucune source plus informative n'est disponible.

## Stacking

Le stacking combine plusieurs sources :

Le blending V1 combine les sources en espace log puis applique une softmax finale, afin de
limiter les effets de probabilités extrêmes tout en conservant une sortie normalisée.

Poids initiaux autorisés :

```text
sport  = 0.55
market = 0.35
api    = 0.10
```

Les poids doivent être configurables puis ajustés par backtesting. Si une source manque, les
poids restants sont renormalisés ou un fallback documenté est utilisé.

## Calibration

La calibration est obligatoire avant de considérer les probabilités comme exploitables.

Approches possibles :

- calibration isotonic ;
- Platt scaling / sigmoid ;
- calibration par ligue si le volume le permet ;
- calibration globale si le volume par ligue est insuffisant.

La calibration doit être entraînée uniquement sur des données antérieures au jeu de test.

La V1 applique par défaut une calibration sigmoid cross-validée sur le train uniquement si
le volume est suffisant. Si le nombre de lignes ou la couverture par classe est insuffisant,
le modèle reste non calibré et l'artefact documente la raison du skip.

## Artefacts Modèle

Un entraînement écrit quatre fichiers dans `data/models/<version>/` :

- `model.joblib` : modèle sportif sérialisé ;
- `metadata.json` : résumé lisible avec `model_version`, `created_at`, classes et lignes ;
- `feature_names.json` : colonnes effectivement utilisées par le modèle ;
- `metrics.json` : métriques train/validation.

Le `model_version` doit être fourni explicitement en CLI ou par configuration. Les artefacts
ne contiennent aucun secret.

## Évaluation

Métriques obligatoires :

- accuracy 1X2 ;
- log loss ;
- Brier score ;
- calibration bins ;
- confusion matrix ;
- performance par ligue ;
- performance par saison ;
- performance par niveau de confiance ;
- comparaison odds-only ;
- comparaison API prediction ;
- comparaison Poisson.

Le backtest V1 évalue les sources suivantes sur le split test :

## Modèle 1X2 Spécial Coupe Du Monde

La Coupe du Monde 2026 utilise un modèle séparé des championnats afin d'éviter de mélanger
des dynamiques de clubs et de sélections nationales. Les artefacts sont écrits par défaut
dans `data/models/worldcup-1x2` et ne remplacent pas les modèles V2, V3 ou O/U.

Les sources locales dédiées sont :

- `data/reference/historical_worldcup_result.csv` : résultats internationaux depuis 2016 ;
- `data/reference/classement_fifa_officiel.csv` : ranking FIFA courant, utilisé uniquement
  comme prior de prédiction 2026 ;
- `data/reference/elo_wc_teams_data.tsv` et `elo_wc_teams_shortname.tsv` : ranking Elo
  courant et aliases.

Le dataset historique est construit chronologiquement. Pour une ligne datée `D`, les
features n'utilisent que les matchs internationaux dont `date < D`. Les rankings FIFA/Elo
courants ne sont jamais injectés dans les backtests historiques, car ils représenteraient
une information future. Ils sont autorisés seulement pour les fixtures CDM 2026 à venir.

Les features principales couvrent forme 5/10/20 matchs, forme pondérée par récence,
buts marqués/encaissés, clean sheets, BTTS, over/under historique, force attaque/défense,
performance contre adversaires forts/faibles, terrain neutre, compétitions officielles,
Coupe du Monde, qualifications et compétitions continentales. Le modèle ajoute aussi un
Elo international chronologique interne et un power rating simple attaque/défense.

Les probabilités finales combinent :

- `p_wc_rating_home/draw/away` depuis le différentiel de rating ;
- `p_wc_poisson_home/draw/away` depuis les buts attendus ;
- `p_wc_market_home/draw/away` si des odds 1X2 pré-match sont snapshotées avant
  `prediction_time` ;
- `p_wc_api_home/draw/away` si une prediction API-Football est snapshotée avant
  `prediction_time` ;
- `p_wc_rating_dynamic_*` et `p_wc_poisson_dynamic_*`, qui appliquent un ajustement borné
  à partir des absences, lineups officielles, surprises de XI et changements de formation ;
- le modèle tabulaire `WorldCup1X2Model` quand l'artefact existe.

Le poids de ces sources est piloté par `blend_config.json` dans le dossier modèle. En
absence de configuration, le fallback reste conservateur : rating et Poisson dominent, le
tabulaire ne pèse que faiblement, et les sources live market/API sont intégrées seulement
si elles existent. La commande `worldcup-optimize-blend` teste les blends candidats sur
validation chronologique, évalue ensuite le test et peut écrire le meilleur
`blend_config.json`.

La commande `worldcup-audit-reference` doit valider que les 48 équipes CDM 2026 sont
résolues avant entraînement ou publication.

En live, `predict-worldcup --refresh-data` et `worldcup-run-daily --refresh-data` récupèrent
fixture, odds, injuries, API prediction et lineups avant de construire la prédiction. Chaque
source reste strictement filtrée par `fetched_at <= prediction_time`. En backtest, aucune
donnée récupérée après coup n'est utilisée pour simuler M-30 : les rapports indiquent la
couverture dynamique disponible et évaluent seulement les snapshots réellement point-in-time.

- modèle final chargé depuis `model.joblib` si `--model-dir` est fourni ;
- `stacking_final` quand le modèle sportif et au moins une source marché/API existent ;
- `odds_only` ;
- `poisson` ;
- `api_prediction_only`, avec coverage explicite si certains matchs n'ont pas de snapshot
  API prediction.

Les seuils de confiance exposent, pour chaque modèle, la couverture et l'accuracy au-dessus
de seuils configurables. Les métriques par ligue et par saison sont calculées uniquement si
`league_id` et `season` existent dans le dataset.

## Prédiction Fixture Unique

Le pipeline de prédiction applique le même contrat point-in-time que le backtesting :

- construire `FeatureSnapshot(fixture_id, prediction_time)` avant toute prédiction ;
- charger le modèle sportif si `model.joblib` existe dans `--model-dir` ;
- utiliser Poisson comme fallback sportif si le modèle est absent ;
- utiliser odds et prédiction API uniquement si les features contiennent des snapshots
  disponibles avant `prediction_time` ;
- appliquer le stacking `sport / market / api` avec redistribution automatique des poids
  manquants ;
- sauvegarder `ModelPrediction` avec probabilités normalisées, explications, sources et
  qualité des données.

L'option CLI par défaut `--no-refresh` interdit les appels API live. `--refresh-data` lance
un refresh explicite des fixtures, détails, odds et standings avant de reconstruire les
features. Une source optionnelle absente ne bloque pas la prédiction : elle produit un
warning, un flag de qualité et un fallback documenté.

## Backtesting

Le backtesting doit reconstruire chaque prédiction comme si elle était faite avant le coup
d'envoi :

- utiliser un `prediction_time` explicite ;
- exclure la fixture cible des historiques ;
- filtrer tous les snapshots par date ;
- ne jamais utiliser le score final ou une statistique post-match dans les features ;
- séparer train, validation et test chronologiquement.

Par défaut, `football-predictor backtest` trie le dataset par `fixture_date` puis applique
un split `60% train / 20% validation / 20% test`, sans shuffle. Le rapport indique
clairement `start`, `end` et `row_count` pour chaque période.

Exports V1 :

- `backtest_report.json` : métriques complètes, périodes, group metrics, calibration bins et
  données de seuils de confiance réutilisables pour de futurs graphiques ;
- `backtest_report.md` : résumé lisible des mêmes résultats.

## Modélisation V2 Late M-30

La V2 est pensée pour les prédictions `late` M-30 et reste le rollback officiel de
`daily_late` ainsi qu'un signal consommé par la V3. Elle ne cherche pas à remplacer le
marché avec un seul gros modèle : elle combine plusieurs experts, puis apprend un
meta-modèle sur validation temporelle.

Experts V2 :

- `market_calibrated` : probabilités bookmaker corrigées par une régression logistique si
  assez de données sont disponibles ;
- `poisson_v2` : lambdas de buts issus de la forme, pseudo-xG, avantage domicile et impact
  absences, avec correction légère des petits scores ;
- `elo_v2` : rating dynamique calculé avant chaque match dans l'ordre chronologique ;
- `tabular_v2` : modèle tabulaire LightGBM si installé, sinon fallback sklearn ;
- `stacking_v2` : meta-modèle multinomial appris sur validation, ou mélange pondéré si le
  volume est insuffisant.

L'entraînement V2 écrit `model.joblib`, `metadata.json`, `feature_names.json`,
`metrics.json` et `feature_coverage.json` dans `data/models/v2-late`. Le fichier de
couverture indique quelles familles de features sont réellement exploitables. Les
probabilités par expert sont aussi persistées dans `ModelPrediction.payload_json` afin de
comprendre pourquoi une prédiction a été envoyée.

Commandes recommandées :

```bash
football-predictor build-dataset \
  --league 39 \
  --season 2025 \
  --prediction-window 30m \
  --output data/processed/training_v2_late.parquet

football-predictor train \
  --dataset data/processed/training_v2_late.parquet \
  --output-dir data/models/v2-late \
  --model-version v2-late

football-predictor backtest \
  --dataset data/processed/training_v2_late.parquet \
  --model-dir data/models/v2-late \
  --output-dir reports/backtest_v2_late \
  --retrain-v2-model-version v2-late \
  --format both
```

Le script `scripts/train_backtest_all.sh` utilise ces paramètres par défaut. Le backtest
avec `--retrain-v2-model-version` réentraîne un modèle V2 uniquement sur le split train,
calibre/choisit le meta-modèle sur validation, puis évalue le test. C'est le rapport à
utiliser pour juger la V2.

## Modélisation V3 Draw Risk

La V3 démarre par un sous-modèle binaire isolé : `DRAW` contre `NOT_DRAW`. Il consomme le
dataset V3 M-30 produit par `backtesting.v3_dataset_builder` et ne modifie pas les chemins
de production V1/V2. Le modèle sert uniquement de candidat pour le futur stacker V3.

Commande :

```bash
football-predictor train-v3-draw-risk \
  --dataset data/processed/training_v3_m30.parquet \
  --output-dir data/models/v3/draw_risk \
  --model-version v3.0-draw-risk \
  --calibration isotonic \
  --train-ratio 0.6 \
  --valid-ratio 0.2
```

Le split est chronologique par `fixture_date`. La sélection de features conserve les
colonnes numériques point-in-time utiles au nul (`draw_risk_*`, marché/API, lineups,
qualité des données) et exclut les targets, IDs, dates, scores finaux, JSON/payloads et
sorties d'autres modèles destinées au stacker.

Artefacts écrits dans `data/models/v3/draw_risk/` :

- `model.joblib` ;
- `metadata.json` ;
- `feature_names.json` ;
- `feature_coverage.json` ;
- `metrics.json`.

Les métriques couvrent train, validation et test quand les splits existent : accuracy
binaire, log loss, Brier, ROC-AUC/PR-AUC si calculables, calibration bins, ECE, baseline
taux de nul prior et baseline probabilité marché du nul quand disponible. La calibration
isotonic est appliquée seulement si le volume est suffisant ; sinon la décision de skip est
consignée dans les métadonnées.

### V3 No-Draw Winner

Le second sous-modèle V3 est binaire : `HOME` contre `AWAY`, uniquement sur les matchs non
nuls. Il estime `P(Home | NoDraw)` et laisse `P(Away | NoDraw) = 1 - P(Home | NoDraw)`.
Les lignes `DRAW` sont exclues avant le split chronologique.

Commande :

```bash
football-predictor train-v3-no-draw-winner \
  --dataset data/processed/training_v3_m30.parquet \
  --output-dir data/models/v3/no_draw_winner \
  --model-version v3.0-no-draw-winner \
  --calibration sigmoid \
  --train-ratio 0.6 \
  --valid-ratio 0.2
```

La sélection de features conserve les signaux numériques point-in-time utiles au choix
Home-vs-Away hors nul (`ndw_*`, edge home/away, marché/API home-away, lineups, absences et
qualité des données) et exclut les targets, scores finaux, dates, IDs, payloads et sorties
d'autres modèles.

Les artefacts sont écrits dans `data/models/v3/no_draw_winner/` avec le même format que
Draw Risk : `model.joblib`, `metadata.json`, `feature_names.json`,
`feature_coverage.json` et `metrics.json`. Les métriques incluent les baselines taux home
hors nul et probabilité marché `p_market_home / (p_market_home + p_market_away)` quand
elle est disponible. La calibration sigmoid est sautée et documentée si le volume est
insuffisant.

### V3 Stacker Et Fusion

Le sprint stacker assemble Draw Risk, No-Draw Winner, V2, marché, API et qualité data en
probabilités finales `HOME/DRAW/AWAY`. Les sous-modèles sont entraînés sur le fold train ;
le stacker est entraîné uniquement sur le fold validation pour éviter d'apprendre sur les
lignes vues par les sous-modèles.

Commande :

```bash
football-predictor train-v3 \
  --dataset data/processed/training_v3_m30.parquet \
  --output-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --calibration isotonic_draw,sigmoid_ndw \
  --train-ratio 0.6 \
  --valid-ratio 0.2
```

Si le fold validation est trop faible ou ne contient pas les trois classes, le stacker
écrit quand même un artefact en mode fallback déterministe :

```text
p_draw = Draw Risk
p_home = (1 - p_draw) * P(Home | NoDraw)
p_away = (1 - p_draw) * P(Away | NoDraw)
```

Ce vecteur V3 est ensuite mélangé avec V2 et le marché quand ils sont disponibles, puis
normalisé. L'artefact racine `data/models/v3/model.joblib` charge les trois composants et
`predict_proba(frame)` retourne toujours des lignes `[P(Home), P(Draw), P(Away)]`
normalisées.

### V3 Backtest Et Comparaison

Le backtest V3 compare le composite complet, ses variantes et les baselines sur le fold
test chronologique du dataset V3 M-30. Il n'appelle aucune API live et n'utilise pas les
résultats du fold test pour entraîner le modèle. Par défaut, la commande évalue les
artefacts déjà présents dans `data/models/v3`. Pour un backtest reproductible depuis le
dataset, utiliser `--retrain-v3`, ce qui entraîne les sous-modèles sur train, le stacker
sur validation, puis évalue uniquement test.

Commande :

```bash
football-predictor backtest-v3 \
  --dataset data/processed/training_v3_m30.parquet \
  --model-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --output-dir reports/v3 \
  --format both \
  --retrain-v3
```

Rapports écrits :

- `reports/v3/v3_backtest_report.json` : payload complet, métriques et critères ;
- `reports/v3/comparison_vs_v2.md` : tableau lisible V3 vs V2 vs baselines.

Modèles reportés : `odds_only`, `api_prediction_only`, `poisson_baseline`,
`v2_existing`, `v3_draw_risk_only`, `v3_no_draw_winner_only` (reporter conditionnel),
`v3_deterministic_fusion`, `v3_stacker_full` et `v3_blend_v2`.

Les métriques principales sont l'accuracy 1X2, log loss, Brier multiclass, calibration,
ECE draw, précision/rappel/F1 du nul, AUC draw quand calculable, métriques Home-vs-Away
conditionnelles hors nul, confidence gap et découpes par ligue, saison, qualité data,
confiance et disponibilité de la lineup officielle.

La V3 reste candidate tant que tous les critères de succès ne sont pas validés contre une
baseline V2 réelle : log loss améliorée d'au moins `0.005`, Brier amélioré d'au moins
`0.003`, aucune régression de log loss `> 0.005` sur les ligues avec au moins 100 matchs
test, ECE draw amélioré d'au moins `0.01` et pas de régression du confidence gap. Si le
modèle V2 ou les colonnes `p_v2_*` sont absents, le rapport marque ces critères comme
`not_evaluable`.

### V3 Inférence Fixture Unique

Le sprint inférence ajoute un chemin fixture unique isolé de la production V2 :

```bash
football-predictor predict-v3 \
  --fixture 123456 \
  --model-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --no-refresh \
  --json
```

La commande construit les features avec `feature_version="v3.0"`, persiste un
`V3FeatureSnapshot`, charge le composite V3, puis écrit une ligne `V3ModelPrediction` avec
les probabilités finales et les sorties intermédiaires Draw Risk, No-Draw Winner, V2,
marché et API. Si `--v2-model-dir` est absent, le composite garde un prior uniforme pour
le signal V2 et la prédiction ne doit pas échouer.

Discord est optionnel et désactivé par défaut :

```bash
football-predictor predict-v3 \
  --fixture 123456 \
  --model-dir data/models/v3 \
  --send-discord \
  --dry-run
```

Le message utilise le formatter V3 dédié, reste routé vers `message_type="prediction"` et
stocke `v3_model_prediction_id` dans `DiscordMessage.payload_json` plutôt que dans
`model_prediction_id`, car cette FK reste réservée aux prédictions V2.

### V3 Quotidien Et Production Discord

La commande quotidienne V3 sélectionne les fixtures comme `predict-today`, calcule les
prédictions V3 et persiste `V3ModelPrediction` avec les métadonnées de fenêtre quotidienne.
Depuis Sprint 10, `scripts/daily_late.sh` utilise la V3 par défaut pour publier dans le
channel Discord `predictions`.

Commande manuelle production M-30 :

```bash
football-predictor predict-today-v3 \
  --date 2026-05-08 \
  --window late \
  --model-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --production-mode \
  --no-refresh-data \
  --json
```

Le statut de résultat est `shadow_logged` quand Discord est désactivé. Les champs
`payload_json["shadow_mode"]`, `payload_json["daily_window"]`,
`payload_json["automation_date"]` et `payload_json["run_key"]` permettent de comparer les
prédictions live V2/V3. En production, `shadow_mode=false`, les prédictions sans Discord
sont `predicted` et les vrais envois Discord sont `sent`.

Routine production et rollback :

```bash
SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
PREDICTION_ENGINE=v2 SEND_DISCORD=true DRY_RUN=false scripts/daily_late.sh
```

La promotion V3 est volontaire malgré un backtest non validé. Les probabilités et le taux
de réussite doivent donc être surveillés après activation, avec une attention particulière
aux sources live M-30 : odds, prédictions API, lineups et blessures.

La publication Discord n'est pas automatique pour toutes les prédictions calculées. La
règle métier commune V3 1X2 et O/U 2.5 est : publier uniquement les confiances `High` et
`Very High`. Les prédictions `Medium`, `Low`, `Uncertain` ou non normalisables restent
stockées en base avec `confidence_skipped` et ne sont pas prises en compte dans le score
public hebdomadaire.

Pour valider le rendu Discord V3 sans envoi réel :

```bash
football-predictor predict-today-v3 \
  --window late \
  --dry-run \
  --print-only
```

Un envoi Discord V3 réel depuis la CLI exige `--production-mode --send-discord` et
`--dry-run=false` / `--print-only=false`. Sans `--production-mode`, `predict-today-v3`
reste bloqué pour les envois live.

## Règles Anti Data Leakage

Chaque feature dynamique doit respecter :

```text
fixture_id
prediction_time
```

Filtres requis :

- fixtures historiques : date du match `< prediction_time` ;
- odds : `fetched_at <= prediction_time` ;
- injuries : `fetched_at <= prediction_time` ;
- standings : `snapshot_date <= prediction_time` ou `fetched_at <= prediction_time` ;
- lineups : `fetched_at <= prediction_time` ;
- player stats : connues avant `prediction_time`.

Les fichiers `docs/` donnent le contexte, les IDs et les référentiels initiaux. Ils ne
remplacent pas les snapshots dynamiques nécessaires aux features.
