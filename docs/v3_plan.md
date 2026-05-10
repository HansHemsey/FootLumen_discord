# Plan V3 — Architecture multi-modèles (Draw Risk + No-Draw Winner) à M-30

> Document de planification. Ne contient ni code ni modification du repo.
> Choix structurants validés : **tables DB dédiées V3**, **stacker appris pour la fusion**, **dataset M-30 simulé avec flag XI**.

---

## 0. Contexte

La V2 actuelle (`FootballOutcomeV2Model`, [src/football_predictor/modeling/v2_model.py:59](src/football_predictor/modeling/v2_model.py#L59)) prédit directement les 3 classes `HOME / DRAW / AWAY` via un meta-modèle Logistic Regression empilant 4 experts (`tabular_v2`, `market_calibrated`, `poisson_v2`, `elo_v2`). Cette approche apprend simultanément deux signaux très différents : *qui va gagner* et *est-ce que ce sera nul*. Le nul est notoirement difficile à modéliser (déséquilibre de classes, signaux spécifiques : parité de niveau, faible volume de buts attendus, contexte tactique). En forçant un modèle unique à arbitrer ces deux objectifs, on dilue les features utiles à chacun.

La V3 sépare explicitement les deux questions :

1. **No-Draw Winner** — étant donné qu'il n'y a pas de nul, qui gagne ?
2. **Draw Risk** — quelle est la probabilité d'un nul ?

Les deux sorties sont fusionnées en un 1X2 final via un **stacker entraîné** qui combine aussi V2 et marché. La V2 reste en production comme baseline / signal de stacking / garde-fou.

Cette séparation permet :
- des features distinctes optimisées pour chaque sous-question ;
- un dataset Draw Risk équilibré (binaire) ;
- un dataset No-Draw Winner sans bruit du nul ;
- un suivi indépendant de la calibration du nul ;
- un débogage et une explicabilité plus clairs (« le modèle voit un fort risque de nul mais favorise Home en cas de no-draw »).

Cible d'inférence : **M-30** (kickoff − 30 minutes), où les XI officiels peuvent être disponibles selon la compétition.

---

## 1. Résumé exécutif

### 1.1 Apport V3
- Décomposition de la prédiction 1X2 en **deux sous-modèles spécialisés** (Draw Risk binaire + No-Draw Winner binaire) recombinés via un stacker appris.
- **Fenêtre M-30** explicitement modélisée, avec gestion duale XI officiel / XI probable historique via un flag.
- **Tables DB dédiées V3** (`V3FeatureSnapshot`, `V3ModelPrediction`) en parallèle des tables V2 et OU existantes — aucun impact sur la production V2.
- Fusion par **stacker LR/GBDT** entraîné sur (Draw Risk, No-Draw Winner, V2, market, API) — apprend à pondérer dynamiquement selon la qualité des données.
- Réutilisation maximale des pipelines existants : ingestion, `FeatureBuilder`, backtesting, Discord routing — V3 s'ajoute, ne remplace rien.

### 1.2 Pourquoi séparer Draw Risk et No-Draw Winner
- **Signaux distincts** : la probabilité du nul corrèle avec parité de niveau, défense solide × 2, faible xG total, ligue à fort taux de nuls. La probabilité de victoire (hors nul) corrèle avec différentiel d'attaque, qualité XI, avantage domicile, mouvements de cotes Home vs Away.
- **Déséquilibre** : ~25 % de nuls. Un modèle 3-classes calibre mal le 25 %. Un modèle binaire dédié peut utiliser des techniques (class weights, cost-sensitive, isotonic) sans perturber les autres classes.
- **Datasets différents** : No-Draw Winner exclut les nuls à l'entraînement (~75 % des données utiles, target binaire HOME/AWAY). Draw Risk garde 100 % des données avec target binaire DRAW vs NOT_DRAW.
- **Calibration séparée** : on peut calibrer p_draw avec sigmoid+isotonic et p_home_no_draw indépendamment.

### 1.3 Intégration V2
La V2 reste **vivante** :
- production continue d'utiliser V2 jusqu'à validation V3 (compatibilité préservée) ;
- V2 sert de **feature** (signal expert) au stacker V3 final ;
- V2 sert de **fallback** si Draw Risk ou No-Draw Winner échoue (data quality faible) ;
- V2 sert de **benchmark** dans le backtest comparatif.

---

## 2. Audit de l'existant

### 2.1 Fichiers lus
- [AGENTS.md](AGENTS.md), [blueprint.md](blueprint.md), [README.md](README.md)
- [docs/product_spec.md](docs/product_spec.md), [docs/architecture.md](docs/architecture.md), [docs/modeling_strategy.md](docs/modeling_strategy.md), [docs/data_contract.md](docs/data_contract.md)
- [docs/api_football_reference.json](docs/api_football_reference.json), [docs/api_football_players_reference.json](docs/api_football_players_reference.json)
- Sources V2 (modeling, prediction, features, backtesting), schéma DB, migrations Alembic, OU model

### 2.2 Modules identifiés
- **modeling/** : V2 multi-experts dans [v2_model.py](src/football_predictor/modeling/v2_model.py), V1 dans [sport_model.py](src/football_predictor/modeling/sport_model.py), stacking [stacking.py](src/football_predictor/modeling/stacking.py), calibration [calibration.py](src/football_predictor/modeling/calibration.py), Poisson [poisson_v2.py](src/football_predictor/modeling/poisson_v2.py), ELO [elo.py](src/football_predictor/modeling/elo.py), preprocessing anti-leakage [preprocessing.py](src/football_predictor/modeling/preprocessing.py), sélection features V2 [v2_features.py](src/football_predictor/modeling/v2_features.py)
- **features/** : orchestrateur [feature_builder.py](src/football_predictor/features/feature_builder.py) (`build_feature_snapshot`), point-in-time [point_in_time.py](src/football_predictor/features/point_in_time.py), équipes [team_features.py](src/football_predictor/features/team_features.py), XI/joueurs [xi_features.py](src/football_predictor/features/xi_features.py), absences [availability_features.py](src/football_predictor/features/availability_features.py), odds [odds_features.py](src/football_predictor/features/odds_features.py), pseudo-xG [pseudo_xg.py](src/football_predictor/features/pseudo_xg.py), data quality [data_quality.py](src/football_predictor/features/data_quality.py)
- **prediction/** : `PredictionService` [service.py](src/football_predictor/prediction/service.py), pipeline fixture [predict_fixture.py](src/football_predictor/prediction/predict_fixture.py), batch quotidien [run_daily.py](src/football_predictor/prediction/run_daily.py)
- **backtesting/** : [evaluator.py](src/football_predictor/backtesting/evaluator.py), [dataset_builder.py](src/football_predictor/backtesting/dataset_builder.py) (`prediction_offset_hours=24` actuel — V3 le réduira à 0.5h), [metrics.py](src/football_predictor/backtesting/metrics.py)
- **db/** : modèles SQLAlchemy 2.x [models.py](src/football_predictor/db/models.py)
- **ou_model/** : modèle binaire parallèle (template direct pour Draw Risk)
- **discord/** : formatter, router, services existants

### 2.3 Pipeline V2 actuel
1. Dataset construit par [`build_training_dataset`](src/football_predictor/backtesting/dataset_builder.py#L23) avec `prediction_offset_hours=24` ;
2. Split chronologique 60/20/20 par `fixture_date` ([BacktestConfig](src/football_predictor/backtesting/evaluator.py#L39)) ;
3. Sélection de features V2 via `select_v2_feature_names` (min_coverage 2 %, max 260) ;
4. Entraînement multi-experts dans [`train_v2_model_from_frame`](src/football_predictor/modeling/v2_model.py#L226) :
   - `tabular_v2` = `HistGradientBoostingClassifier(max_iter=220, lr=0.04, l2=0.12)` (fallback `LogisticRegression`)
   - `market_calibrated` = `LogisticRegression` sur `[p_market_home, p_market_draw, p_market_away]`
   - `poisson_v2` = lambdas estimées depuis form pondérée + pseudo-xG
   - `elo_v2` = ELO chronologique
   - **Meta-model** = `LogisticRegression` sur les 4 experts, fitté sur validation si ≥ 45 lignes
5. Calibration optionnelle (sigmoid/isotonic) sur tabular_v2 ;
6. Persistance via `joblib` + métadonnées JSON dans `data/models/` ;
7. Inférence dans `PredictionService.predict_fixture` : récupère features → predict_proba V2 → ajoute confidence/explanations → upsert `ModelPrediction` → push Discord.

### 2.4 Points forts
- Discipline point-in-time **forte** (filtrages `fetched_at <= prediction_time` partout) ;
- Liste de patterns interdits dans les features ([`FORBIDDEN_FEATURE_PATTERNS`](src/football_predictor/modeling/preprocessing.py#L12)) ;
- Snapshots typés avec `feature_version` versionnée → ajout de `v3.0` non-cassant ;
- Pattern OU déjà éprouvé pour modèle binaire parallèle avec tables dédiées ;
- Coverage compétitions : 5 ligues majeures × 2022–2025 (config/competitions_history.yaml) ;
- Ingestion solide pour 16 endpoints API-Football (voir §3).

### 2.5 Limites
- `prediction_offset_hours=24` au lieu de 0.5h → datasets V2 **ne reflètent pas M-30**. La V3 doit corriger cela.
- Pas de modélisation explicite de la disponibilité des lineups officiels à M-30 (booléen XI utilisé sans contexte temporel).
- Pas d'ingestion `/odds/movement` (multi-snapshots) → impossible de calculer un mouvement de cotes propre — le code ([`compute_odds_movement`](src/football_predictor/features/odds_features.py)) existe mais a besoin de plusieurs `OddsSnapshot.fetched_at` distincts pour fonctionner.
- Pas de calibration dédiée pour le nul ; meta-model LR ne peut pas corriger isolément la classe DRAW.
- Pas de feature « market_no_draw » (sous-marché Home-vs-Away conditionnel hors nul) calculée à partir des odds Match Winner.
- `meta_model` LR à 4 entrées × 3 classes → 15 paramètres seulement → sous-paramétré, peu apte à apprendre des interactions Draw vs No-Draw.

### 2.6 Risques relevés
- Tests anti-leakage présents mais limités ; un nouveau pipeline V3 doit en ajouter spécifiquement pour : (a) feature lineup avant fetched_at ; (b) feature market_movement avec deux snapshots <= prediction_time ; (c) absence_impact basé sur injuries antérieures.
- `OddsSnapshot` n'a **pas de unique constraint** ([db/models.py](src/football_predictor/db/models.py)) → risque de duplications potentielles dans les joins de features ; à valider avant de calculer market_movement.
- Coverage `/predictions` API-Football inégale selon ligue → fallback obligatoire.

---

## 3. Inventaire des données disponibles

### 3.1 Données déjà ingérées (✅ utilisables sans nouveau code d'ingestion)

| Famille | Table SQLA | Module ingestion | Point-in-time | Suffisant V3 ? |
|---|---|---|---|---|
| Fixtures | `Fixture` | [fixtures.py](src/football_predictor/ingestion/fixtures.py#L69) | ✅ | ✅ |
| Standings | `StandingSnapshot` | [fixtures.py](src/football_predictor/ingestion/fixtures.py#L151) (snapshot_date) | ✅ | ✅ |
| Stats match | `FixtureStatistics` | [ingest_match_details.py](src/football_predictor/ingestion/ingest_match_details.py#L207) | ✅ | ✅ |
| Events | `FixtureEvent` | [ingest_match_details.py](src/football_predictor/ingestion/ingest_match_details.py#L211) | ✅ | ✅ |
| Lineups | `FixtureLineup` | [ingest_match_details.py](src/football_predictor/ingestion/ingest_match_details.py#L215) | ✅ (fetched_at) | ✅ |
| Stats joueurs match | `FixturePlayerStats` | [ingest_match_details.py](src/football_predictor/ingestion/ingest_match_details.py#L219) | ✅ | ✅ |
| Injuries | `Injury` | [ingest_match_details.py](src/football_predictor/ingestion/ingest_match_details.py#L223) | ✅ | ✅ |
| Squads | `PlayerSquad` | [api_reference.py](src/football_predictor/ingestion/api_reference.py#L88) | partiel | ✅ |
| Odds Match Winner | `OddsSnapshot` | [ingest_odds.py](src/football_predictor/ingestion/ingest_odds.py#L68) | ✅ | ⚠️ multi-snapshots à valider |
| Predictions API-FB | `ApiPredictionSnapshot` | [ingest_match_details.py](src/football_predictor/ingestion/ingest_match_details.py#L227) | ✅ | ✅ |
| Bookmakers/Bets | `Bookmaker`, `Bet` | [api_reference.py](src/football_predictor/ingestion/api_reference.py#L107) | n/a | ✅ |
| Players | `Player` | [unknown_players.py](src/football_predictor/ingestion/unknown_players.py) | partiel | ✅ |
| Reference docs | JSON locaux | [reference/loaders.py](src/football_predictor/reference/loaders.py) | n/a | ✅ |

### 3.2 Données disponibles mais sous-exploitées
- **Multi-snapshots OddsSnapshot** : si plusieurs `fetched_at` existent par fixture, un mouvement de cotes peut être calculé. Action : valider la cardinalité actuelle ; si médiane < 2 snapshots/fixture, prévoir un cron `refresh-odds` plus fréquent (ex. T-24h, T-12h, T-3h, T-30min).
- **Standings historiques** : déjà snapshotés, mais peu utilisés au-delà du rang. Possibilité d'ajouter `points_gap_to_target_race` (titre / Europe / relégation) pour le contexte motivation.
- **API-Football predictions** (`ApiPredictionSnapshot.percent_*` et `advice`) : déjà ingéré, utilisé par V2 comme feature ; V3 le réutilise tel quel.
- **FixturePlayerStats.rating** : utilisé partiellement par xi_features ; peut servir à calibrer `replacement_quality_score`.
- **FixtureLineup.formation** : disponible mais pas exploité comme feature catégorielle (4-3-3 vs 5-3-2) → utile pour Draw Risk (formations défensives).

### 3.3 Données manquantes / à enrichir

| Donnée | Endpoint API-FB | Pourquoi V3 en a besoin | Pour quel modèle | Dispo M-30 | Coverage | Coût API | Priorité |
|---|---|---|---|---|---|---|---|
| Multi-snapshots odds 1X2 | `/odds` répété | Calcul `odds_movement_*` propre | Draw Risk **et** No-Draw Winner | ✅ | bonne | +N appels par fixture | **P0** |
| Odds **Over/Under 2.5** au market 1X2 | `/odds` filtré sur `bet_id=5` (Goals O/U) | Signal très fort pour Draw Risk (faible total = nul plus probable). La table OddsSnapshot stocke `odd_home/draw/away` mais pas le marché OU. | Draw Risk | ✅ | bonne (déjà ingéré dans `ou_model/`) | déjà payé | **P0** (réutiliser ingestion OU) |
| Odds **Both Teams To Score** | `/odds` `bet_id=8` (BTTS) | BTTS=No corrèle avec nuls 0-0/1-0/0-1 | Draw Risk | ✅ | bonne | +1 bet | P1 |
| `/teams/statistics` avec `date` | `/teams/statistics` | Stats de saison agrégées à la date du match (fixtures jouées, % de nuls saison-to-date, % clean sheets, etc.) | Draw Risk | ✅ | excellente | +2 appels par fixture (×N teams) | P1 |
| `/predictions` (re-ingest récent) | `/predictions?fixture` | Confiance pré-match d'API-Football, advice | les deux | ✅ | inégale | déjà payé | P0 (déjà fait, à conserver) |
| `/players/topscorers` | `/players/topscorers` | Identifier joueurs cruciaux pour `attacking_absence_impact` | No-Draw Winner | n/a | bonne | +1 par ligue/saison | P2 |
| `/odds/movement` multi-T | re-call `/odds` sur fenêtres | Variance bookmakers et drift T-24h → T-30min | Draw Risk surtout | ✅ | dépend cron | élevé | P0 |

**Coût API total estimé** pour la V3 par jour de matchs (10 fixtures actives) :
- Refresh odds 4× (T-24h/-12h/-3h/-30min) × 10 fixtures = +30 appels (déjà 1 baseline) ;
- BTTS et O/U via mêmes endpoints `/odds` filtrés ;
- `/teams/statistics` historiques à reconstruire (one-time pour backtest, ~2 ligues × 4 saisons × 20 équipes × 1 appel par snapshot mensuel = ~1 600 appels one-time).

### 3.4 Recommandation
La V3 **n'introduit pas** de nouvel endpoint critique : 95 % des features peuvent être calculées avec ce qui est déjà ingéré. Les seules ajouts à prévoir sont :
1. Refresh `/odds` plus fréquent (cron) pour multi-snapshots.
2. Ingestion **odds OU 2.5 et BTTS** dans `OddsSnapshot` ou nouvelle table dédiée — le code OU lit déjà ces marchés ([ou_odds_features.py](src/football_predictor/ou_model/features/ou_odds_features.py)), à factoriser.
3. Optionnel : `/teams/statistics` historique pour features ligue-niveau saison.

---

## 4. Architecture cible V3

### 4.1 Vue d'ensemble

```
                    ┌─────────────────────┐
                    │ Feature builder V3  │ (étend feature_builder.py)
                    │  prediction_time =  │
                    │  kickoff − 30min    │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    ┌──────────────┐  ┌──────────────────┐  ┌─────────────┐
    │ Draw Risk    │  │ No-Draw Winner   │  │  V2 model   │
    │ Model (bin)  │  │ Model (bin)      │  │ (existant)  │
    │ → P(Draw)    │  │ → P(H|noDraw)    │  │ → P(H/D/A)  │
    └──────┬───────┘  └────────┬─────────┘  └──────┬──────┘
           │                   │                   │
           └─────────┬─────────┴───────────┬───────┘
                     │                     │
                     ▼                     ▼
              ┌─────────────────────────────────┐
              │  Stacker V3 (LR ou GBDT)        │
              │  Inputs: P_v3_draw, P_v3_h_nd,  │
              │  P_v3_a_nd, P_v2_h, P_v2_d,     │
              │  P_v2_a, p_market_*, p_api_*,   │
              │  data_quality_score             │
              │  Output: P_v3_final_h/d/a       │
              └────────────┬────────────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │   Calibration    │
                  │   3-classe (LR + │
                  │   isotonic Draw) │
                  └────────┬─────────┘
                           │
                           ▼
                ┌────────────────────┐
                │ V3ModelPrediction  │ → Discord
                └────────────────────┘
```

### 4.2 Composants

#### 4.2.1 Draw Risk Model
- **Fichier cible** : `src/football_predictor/modeling/v3/draw_risk_model.py`
- **Type** : binaire (target `is_draw` ∈ {0, 1})
- **Algo recommandé** : `HistGradientBoostingClassifier` (cohérent avec V2) avec `class_weight` ajusté car ~75/25. Fallback `LogisticRegression` avec L2.
- **Calibration** : isotonic obligatoire (le binaire DRAW est typiquement mal-calibré).
- **Sortie** : `P(Draw)` ∈ [0, 1].

#### 4.2.2 No-Draw Winner Model
- **Fichier cible** : `src/football_predictor/modeling/v3/no_draw_winner_model.py`
- **Type** : binaire (target `home_wins` ∈ {0, 1}, dataset filtré `outcome ≠ DRAW`)
- **Algo recommandé** : `HistGradientBoostingClassifier`. Fallback `LogisticRegression`.
- **Calibration** : sigmoid (Platt) suffit généralement pour binaire ~50/50.
- **Sortie** : `P(Home | No Draw)` ; `P(Away | No Draw) = 1 − P(Home | No Draw)`.

#### 4.2.3 V2 1X2 (existant, conservé)
- Aucune modification. Fournit ses 3 probas comme features au stacker.

#### 4.2.4 Odds-only baseline
- Réutilisé : [`odds_only_probability`](src/football_predictor/modeling/baselines.py).
- Calcul auxiliaire `p_market_home_no_draw = q_home / (q_home + q_away)` (sans nul) pour informer le stacker.

#### 4.2.5 API-Football predictions
- Réutilisé tel quel ([`api_prediction_probability`](src/football_predictor/modeling/baselines.py)).

#### 4.2.6 Stacker V3 final (appris)
- **Fichier cible** : `src/football_predictor/modeling/v3/stacker.py`
- **Algo** : `LogisticRegression` multinomiale (3 classes) avec L2, comme `meta_model` V2 mais **enrichi** :
  - features = (P_v3_draw, P_v3_home_no_draw, P_v3_away_no_draw, P_v2_home, P_v2_draw, P_v2_away, p_market_home, p_market_draw, p_market_away, p_market_home_no_draw, p_market_away_no_draw, market_overround, market_dispersion, p_api_home, p_api_draw, p_api_away, data_quality_score, official_lineup_available_flag).
  - target = `HOME / DRAW / AWAY` (3-classe).
- **Entraînement** : sur le **fold validation** uniquement (jamais sur train) pour éviter de sur-apprendre les sorties des sous-modèles. Si moins de 45 lignes valid → fallback fusion déterministe (§7.4).
- **Calibration** : optionnelle, `CalibratedClassifierCV` cv=3, sigmoid.

#### 4.2.7 Fallback déterministe
Si stacker absent ou data_quality < seuil :
```
p_draw   = P_v3_draw
p_home   = (1 − P_v3_draw) * P_v3_home_no_draw
p_away   = (1 − P_v3_draw) * (1 − P_v3_home_no_draw)
puis blending avec V2 si disponible : 0.6 V3 + 0.3 V2 + 0.1 market
puis renormalisation
```

### 4.3 Versioning
- `model_version = "v3.0-draw-risk"` pour le sous-modèle Draw Risk
- `model_version = "v3.0-no-draw-winner"` pour le sous-modèle No-Draw Winner
- `model_version = "v3.0-stacker"` pour le stacker
- `model_version = "v3.0-final"` pour la prédiction finale persistée
- `feature_version = "v3.0"` pour le `V3FeatureSnapshot`

---

## 5. Feature design détaillé

Toutes les features respectent **prediction_time = kickoff − 30 min**. Toutes sont JSON-sérialisables, suffixées (`_last3`, `_last5`, `_last10`, `_last15`, `_ewma`), préfixées (`home_team_*` / `away_team_*`).

### 5.1 Features communes (Draw Risk + No-Draw Winner + Stacker)

Réutilisation des modules existants :
- **Forme équipe** ([team_features.py](src/football_predictor/features/team_features.py)) : ppg, goals_for, goals_against, clean_sheets, failed_to_score, win_rate, draw_rate sur fenêtres `_last3 / _last5 / _last10 / _last15` + `_ewma` ; séparé `home_team_*_at_home` et `away_team_*_at_away`.
- **Stats de tirs et possession** ([team_features.py](src/football_predictor/features/team_features.py)) : shots, shots_on_target, shots_inside_box, possession_pct, corners, fouls, cards.
- **Pseudo-xG** ([pseudo_xg.py](src/football_predictor/features/pseudo_xg.py)) : `home_team_pseudo_xg_for_last10`, `home_team_pseudo_xg_against_last10`, idem away.
- **Stats ajustées adversaire** : moyennes pondérées par la qualité défensive/offensive de l'adversaire historique.
- **Classement** : `home_team_rank`, `home_team_points`, `away_team_rank`, `points_gap`, `rank_gap`, `home_team_form_string` (W/D/L codé).
- **Calendrier** : `home_team_rest_days`, `home_team_matches_last_7d`, `home_team_matches_last_14d`, idem away, `rest_days_diff`.
- **XI / joueurs** ([xi_features.py](src/football_predictor/features/xi_features.py)) : `home_team_xi_value_total`, `home_team_xi_stability`, `home_team_xi_value_attack`, `home_team_xi_value_defense`, idem away.
- **Absences** ([availability_features.py](src/football_predictor/features/availability_features.py)) : `home_team_absence_impact`, `home_team_key_absences_count`, `home_team_attacking_absence_impact`, `home_team_defensive_absence_impact`, `home_team_goalkeeper_absence_impact`, `home_team_questionable_count`, `home_team_replacement_quality`, idem away.
- **Odds** ([odds_features.py](src/football_predictor/features/odds_features.py)) : `p_market_home`, `p_market_draw`, `p_market_away`, `market_overround`, `market_confidence`, `market_dispersion`, `bookmaker_count`.
- **API-Football prediction** : `p_api_home`, `p_api_draw`, `p_api_away`, `api_advice_supports_home`, `api_advice_supports_draw`, `api_advice_supports_away` (booléens dérivés du champ `advice`).
- **Data quality** ([data_quality.py](src/football_predictor/features/data_quality.py)) : `data_quality_score` (0–100), flags `has_odds`, `has_lineups_official`, `has_injuries`, `has_player_stats`, `has_api_prediction`, `has_standings`.

### 5.2 Features spécifiques **No-Draw Winner**

| Feature | Définition |
|---|---|
| `home_away_strength_edge` | (`home_team_ppg_at_home_last10` − `away_team_ppg_at_away_last10`) |
| `attack_defense_edge` | (`home_team_pseudo_xg_for_last10` − `away_team_pseudo_xg_against_last10`) − (`away_team_pseudo_xg_for_last10` − `home_team_pseudo_xg_against_last10`) |
| `home_advantage_edge` | `home_team_ppg_at_home_last10` − `home_team_ppg_at_away_last10` |
| `xi_value_edge` | `home_team_xi_value_total` − `away_team_xi_value_total` |
| `absence_impact_edge` | `away_team_absence_impact` − `home_team_absence_impact` (absences adverses = avantage) |
| `odds_no_draw_home_prob` | `q_home / (q_home + q_away)` où `q_x = 1/odd_x` |
| `odds_no_draw_away_prob` | `1 − odds_no_draw_home_prob` |
| `market_no_draw_confidence` | `1 − abs(odds_no_draw_home_prob − 0.5) * 2` (proche de 0.5 = équilibré, gros incertitude hors nul) |
| `home_form_diff_no_draw` | `home_team_win_rate_at_home_last10` − `away_team_win_rate_at_away_last10` |
| `head_to_head_home_winrate` | si dispo, % victoires Home dans les 5 derniers H2H |
| `motivation_diff` | écart d'enjeu classement (titre/Europe/relégation) entre les deux équipes (heuristique signée) |

### 5.3 Features spécifiques **Draw Risk**

| Feature | Définition |
|---|---|
| `team_strength_parity_score` | `1 / (1 + abs(home_team_ppg_last10 − away_team_ppg_last10))` |
| `expected_goals_total_low_score` | `1 / (1 + (home_team_pseudo_xg_for_last10 + away_team_pseudo_xg_for_last10))` |
| `expected_goals_gap_abs` | `abs(home_team_pseudo_xg_diff − away_team_pseudo_xg_diff)` |
| `defensive_solidity_combined` | `home_team_clean_sheets_rate_last10 + away_team_clean_sheets_rate_last10` |
| `attacking_weakness_combined` | `home_team_failed_to_score_rate_last10 + away_team_failed_to_score_rate_last10` |
| `league_draw_rate` | % de nuls de la ligue à la `prediction_time` (calculé sur les fixtures terminées de la saison/ligue, hors fixture cible) |
| `team_draw_rate_last_10` | par équipe |
| `home_draw_rate_home_last_10` | nuls quand l'équipe joue à domicile |
| `away_draw_rate_away_last_10` | nuls quand l'équipe joue en extérieur |
| `market_draw_probability` | `p_market_draw` |
| `market_draw_movement` | (`p_market_draw_now − p_market_draw_t24h`), nécessite multi-snapshots odds |
| `market_draw_dispersion` | std-dev de p_draw entre bookmakers |
| `poisson_draw_probability` | `sum_k=0..K Poisson(λ_h, k) * Poisson(λ_a, k)` (réutilise [poisson_v2.py](src/football_predictor/modeling/poisson_v2.py)) |
| `low_scoring_draw_score` | `Poisson(λ_h, 0)*Poisson(λ_a, 0) + Poisson(λ_h, 1)*Poisson(λ_a, 1)` |
| `ou25_under_market_prob` | implicite depuis odds Over/Under 2.5 (à ingérer si pas déjà dans OU module) |
| `btts_no_market_prob` | implicite depuis odds Both Teams To Score |
| `formation_defensive_indicator` | flag 1 si formation probable contient 5 défenseurs |
| `draw_risk_score` | combinaison heuristique normalisée des 6 signaux ci-dessus (utile aussi comme feature input du modèle ML) |

### 5.4 Features XI / joueurs (officiel ou probable à M-30)

| Feature | Définition |
|---|---|
| `official_lineup_available_flag` | 1 si `FixtureLineup.fetched_at` exists et `< prediction_time` pour les **deux** équipes, sinon 0 |
| `expected_xi_total_value_home` | somme des `player_value` du XI probable (issu de `P_start ≥ 0.55`) |
| `official_xi_total_value_home` | somme `player_value` du XI officiel (si dispo) |
| `xi_value_delta_vs_expected_home` | `official_xi_total_value − expected_xi_total_value` (positif = XI plus fort que prévu) |
| `missing_expected_starters_count_home` | nombre de joueurs avec `P_start ≥ 0.55` absents du XI officiel (si dispo) |
| `key_absence_impact_home` | somme `absence_impact` des joueurs avec `P_start ≥ 0.55` non présents |
| `replacement_quality_score_home` | qualité moyenne des remplaçants par poste manquant |
| `formation_change_flag_home` | 1 si formation officielle ≠ formation probable la plus fréquente |
| `formation_stability_score_home` | stabilité de la formation sur les 10 derniers matchs |
| `lineup_surprise_score_home` | nombre de titulaires officiels jamais titulaires sur les 10 derniers matchs |
| (idem pour `_away`) | |

### 5.5 Features absences détaillées

Réutilise [availability_features.py](src/football_predictor/features/availability_features.py) avec extension :
- `attacking_absence_impact_home` (poids ATT × P_start × player_value × severity × replacement_gap)
- `defensive_absence_impact_home` (poids DEF central)
- `goalkeeper_absence_impact_home` (multiplicateur 1.30)
- `midfield_absence_impact_home` (créatif vs défensif si distinguable)
- `key_absences_count_home` (joueurs P_start ≥ 0.7 manquants)
- `questionable_players_count_home`
- `replacement_gap_home` (delta player_value entre titulaire historique et remplaçant prévu)

### 5.6 Features odds (avec multi-snapshots)

| Feature | Définition |
|---|---|
| `p_market_home / draw / away` | consensus normalisé sans overround |
| `market_overround` | `q_home + q_draw + q_away − 1` |
| `bookmaker_count` | n distinct au snapshot le plus récent |
| `bookmaker_dispersion_home / draw / away` | std-dev entre bookmakers |
| `odds_movement_home / draw / away` | `p_market_x_now − p_market_x_t24h` (si T-24h dispo) |
| `odds_movement_velocity_draw` | dérivée plus fine si plusieurs snapshots intermédiaires |
| `p_market_home_no_draw` | `q_home / (q_home + q_away)` |
| `p_market_away_no_draw` | complément |
| `p_market_under25` | implicite depuis odds OU 2.5 |
| `p_market_btts_no` | implicite depuis odds BTTS |

### 5.7 Features contexte ligue / motivation

- `league_draw_rate_season` (déjà §5.3)
- `league_home_winrate_season`
- `competition_type` ∈ {league, cup_group, cup_knockout} catégorielle
- `is_end_of_season` (binaire si ≤ 5 journées restantes)
- `home_team_title_race_proximity` (distance au leader en points / matchs restants)
- `home_team_european_race_proximity`
- `home_team_relegation_race_proximity`
- `away_team_*_race_*` (idem)
- `motivation_disparity` (un seul des deux a un enjeu fort)

> Toute feature de motivation est **approximative**. Documenter la limite dans `data_contract.md` et considérer comme « weak signal » à pondérer par data_quality.

### 5.8 Features data quality (input du stacker)

| Feature | Description |
|---|---|
| `data_quality_score` | 0–100 (réutilise [data_quality.py](src/football_predictor/features/data_quality.py)) |
| `has_official_lineup_home` | flag |
| `has_official_lineup_away` | flag |
| `has_odds_multi_snapshot` | ≥ 2 snapshots `OddsSnapshot.fetched_at <= prediction_time` |
| `has_recent_injuries` | injury fetched_at dans les 7 derniers jours avant prediction_time |
| `has_api_prediction` | flag |
| `has_team_statistics_recent` | snapshot `/teams/statistics` daté ≤ 14 jours avant prediction_time |
| `coverage_warning_flags_count` | nombre total de signaux dégradés |

---

## 6. Construction des datasets

### 6.1 Convention prediction_time = M-30
Pour chaque fixture historique terminée :
- `prediction_time = fixture_date − timedelta(minutes=30)`
- toutes les features filtrent `fetched_at <= prediction_time` ou `snapshot_date <= prediction_time` ou `match_date < prediction_time`.

Conséquence : modifier ou paramétrer [`build_training_dataset`](src/football_predictor/backtesting/dataset_builder.py#L23) pour accepter `prediction_offset_minutes=30` (au lieu du `prediction_offset_hours=24` actuel) sans casser V2.

### 6.2 Dataset Draw Risk
- Source : toutes les fixtures terminées des compétitions cibles.
- Features : §5.1 + §5.3 + §5.4 + §5.5 + §5.6 + §5.7.
- **Target** : `is_draw ∈ {0, 1}`.
- Filtre : aucun (dataset complet, ~75 % NOT_DRAW vs 25 % DRAW).
- Splits : chronologique 60/20/20 (cohérence V2).

### 6.3 Dataset No-Draw Winner
- Source : fixtures terminées **où outcome ≠ DRAW**.
- Features : §5.1 + §5.2 + §5.4 + §5.5 + §5.6 + §5.7.
- **Target** : `home_wins ∈ {0, 1}`.
- Filtre : `outcome IN ('HOME', 'AWAY')`.
- Splits : chronologique 60/20/20.

### 6.4 Dataset Stacker
- Source : **fold validation uniquement** des deux datasets précédents (jointure par fixture_id).
- Features : sorties Draw Risk + No-Draw Winner + V2 + market + API + data_quality_score + official_lineup_available_flag (§4.2.6).
- Target : `outcome ∈ {HOME, DRAW, AWAY}` (3-classe).
- Splits : chronologique. Le stacker s'entraîne sur valid (fold V2) et s'évalue sur test.

### 6.5 Targets
- Draw Risk : `is_draw = (home_goals == away_goals).astype(int)`
- No-Draw Winner : `home_wins = (home_goals > away_goals).astype(int)` (uniquement sur sous-dataset filtré)
- Stacker / final : `outcome` string conventionnel `HOME/DRAW/AWAY`.

### 6.6 Splits temporels
Cohérent avec V2 ([BacktestConfig](src/football_predictor/backtesting/evaluator.py#L39)) :
- **Train** : 60 % les plus anciennes fixtures
- **Validation** : 20 % suivantes
- **Test** : 20 % les plus récentes
- Pas de shuffle. Tri par `fixture_date` croissant.
- Optionnel : walk-forward validation par saison (saison 2022 train → saison 2023 valid ; 2022+2023 train → 2024 valid+test ; etc.).

### 6.7 Simulation M-30
Pour chaque fixture :
1. Lookup `FixtureLineup.fetched_at` les plus anciens **qui restent ≤ prediction_time** (M-30) ;
2. Si trouvés : `official_lineup_available_flag = 1`, utiliser le XI réel ;
3. Sinon : `official_lineup_available_flag = 0`, calculer le XI probable depuis la fenêtre historique (méthode P_start existante) ;
4. Idem pour injuries (snapshot le plus récent ≤ prediction_time) et odds (idem).

Ce mécanisme garantit que le dataset reflète fidèlement la réalité M-30 production : certains matchs auront XI officiel, d'autres non. Le modèle apprend à exploiter le flag.

---

## 7. Entraînement et modèles

### 7.1 Algorithmes candidats par sous-modèle

| Sous-modèle | Candidat 1 | Candidat 2 | Candidat 3 | Recommandation |
|---|---|---|---|---|
| Draw Risk | `HistGradientBoostingClassifier` | `LogisticRegression L2` | `CatBoostClassifier` (déjà dans dépendances) | **HistGradientBoostingClassifier** + `class_weight='balanced'` |
| No-Draw Winner | `HistGradientBoostingClassifier` | `LogisticRegression L2` | `CatBoostClassifier` | **HistGradientBoostingClassifier** |
| Stacker | `LogisticRegression` (multinomial) | `HistGradientBoostingClassifier` 3-classes | — | **LogisticRegression** (faible nb de features, risque overfit GBDT sur valid) |

Hyperparamètres initiaux (alignés sur V2) :
- `HistGradientBoostingClassifier(max_iter=220, learning_rate=0.04, l2_regularization=0.12, max_depth=None, min_samples_leaf=20, random_state=42)`
- `LogisticRegression(C=1.0, max_iter=1000, multi_class='multinomial', solver='lbfgs', random_state=42)`

### 7.2 Calibration
- **Draw Risk** : `CalibratedClassifierCV(base, method='isotonic', cv=3)` après training. Critique car cible binaire ~25 %.
- **No-Draw Winner** : `CalibratedClassifierCV(base, method='sigmoid', cv=3)`. Suffit pour binaire ~50/50.
- **Stacker final** : optionnel `CalibratedClassifierCV(stacker, method='sigmoid', cv=3)` sur le fold test.
- Toujours skip si `len(train) < 200` → `calibration_decision = "skipped_low_volume"` consigné dans metadata.

### 7.3 Sauvegarde et versioning
Pattern `joblib` aligné sur [`artifacts.py`](src/football_predictor/modeling/artifacts.py) :
```
data/models/v3/
├── draw_risk/
│   ├── model.joblib
│   ├── metadata.json (artifact_format=draw_risk_v3, model_version, created_at, classes=[NOT_DRAW, DRAW], calibration_decision)
│   ├── feature_names.json
│   ├── feature_coverage.json
│   └── metrics.json
├── no_draw_winner/
│   ├── model.joblib
│   ├── metadata.json (classes=[AWAY_WIN, HOME_WIN])
│   ├── feature_names.json
│   ├── feature_coverage.json
│   └── metrics.json
└── stacker/
    ├── model.joblib
    ├── metadata.json (classes=[HOME, DRAW, AWAY], inputs=[draw_risk, no_draw_winner, v2, market, api, data_quality])
    └── metrics.json
```

### 7.4 Modèle V3 composite (orchestrateur)
Nouvelle classe `FootballOutcomeV3Model` (parallèle à `FootballOutcomeV2Model`) qui charge les 3 artefacts ci-dessus + référence au V2 model (`v2_model_dir` chemin lu en métadonnées) :
- `predict_proba(frame)` → applique Draw Risk, No-Draw Winner, charge V2.predict_proba, calcule market_probs et api_probs depuis le DataFrame, assemble les features stacker, applique stacker.
- Si stacker absent → fallback déterministe (§4.2.7).

---

## 8. Inférence à M-30

### 8.1 Pipeline
1. **Récupérer la fixture** depuis DB (avec home/away IDs).
2. **Refresh data optionnel** (commande `--refresh-data`) :
   - re-call `/odds` → `OddsSnapshot.fetched_at = now`
   - re-call `/injuries?fixture=X` → `Injury.fetched_at = now`
   - re-call `/fixtures/lineups?fixture=X` → `FixtureLineup.fetched_at = now`
   - re-call `/predictions?fixture=X` → `ApiPredictionSnapshot.fetched_at = now`
3. **Construire `V3FeatureSnapshot`** avec `prediction_time = max(now, kickoff − 30 min)`. Idéalement, on appelle ce pipeline à exactement T-30min en cron.
4. **Charger les modèles** : `FootballOutcomeV3Model.load("data/models/v3/")` + V2 lookup.
5. **Inférer** :
   - `P_v3_draw = draw_risk.predict_proba(features)[:, 1]`
   - `P_v3_home_no_draw = no_draw_winner.predict_proba(features)[:, 1]`
   - `P_v2_home, P_v2_draw, P_v2_away = v2_model.predict_proba(features)`
   - `p_market_*` directs depuis features
   - `p_api_*` directs depuis features
6. **Stacker** ou **fallback déterministe** → `P_v3_final_home, P_v3_final_draw, P_v3_final_away`.
7. **Confidence** : réutilise [`confidence.py`](src/football_predictor/prediction/confidence.py).
8. **Explanations** : top features Draw Risk + top features No-Draw Winner via SHAP local ou inspection des coefficients du stacker.
9. **Persistance** : nouvelle ligne dans `V3ModelPrediction` avec **toutes** les sorties intermédiaires.
10. **Discord** : nouveau format (§14) routé sur le canal `predictions`.

### 8.2 Gestion des données manquantes
- Stacker reçoit un vecteur d'inputs avec `NaN` pour signaux absents (V2 absent, market absent, api absent) → `LogisticRegression` ne tolère pas NaN → on remplace par 1/3 (uniform prior) **et** on signale via les flags `has_*` que le stacker peut utiliser.
- Si Draw Risk **ou** No-Draw Winner échoue (ex. feature critique manquante) → fallback intégral V2.
- Toujours retourner `data_quality_json` honnête.

---

## 9. Backtesting et validation

### 9.1 Modèles à comparer

| Modèle | Description |
|---|---|
| `odds_only` | Baseline du marché (déjà dans [baselines.py](src/football_predictor/modeling/baselines.py)) |
| `api_prediction_only` | Baseline API-Football quand dispo |
| `poisson_baseline` | `poisson_v2_probabilities` seul |
| `v2_existing` | `FootballOutcomeV2Model` actuel |
| `v3_draw_risk_only` | Sortie brute Draw Risk étendue à 3-classe : `(0.5*(1-p_draw), p_draw, 0.5*(1-p_draw))` |
| `v3_no_draw_winner_only` | Sortie : `(0.5 * P_h_nd, 0, 0.5 * P_a_nd)` non-trivial à 3-classe → reporter |
| `v3_deterministic_fusion` | Fusion §4.2.7 sans stacker |
| `v3_stacker_full` | Pipeline V3 complet |
| `v3_blend_v2` | `0.5 * v3 + 0.5 * v2` |

### 9.2 Métriques à reporter
- **3-classe** : accuracy 1X2, log loss, multiclass Brier, calibration bins (10), confusion matrix.
- **Per-classe Draw** : precision, recall, F1, ROC-AUC binaire (DRAW vs NOT_DRAW), PR-AUC.
- **Per-classe No-Draw** : accuracy Home-vs-Away conditionnel, AUC binaire.
- **Calibration plots** : Draw Risk seul, No-Draw Winner seul, V3 final.
- **Confidence gap** ([metrics.py](src/football_predictor/backtesting/metrics.py)).

### 9.3 Group metrics
- Par ligue (`league_id` × `season`)
- Par saison
- Par `data_quality_score` bins (0–25, 25–50, 50–75, 75–100)
- Par `confidence_label` (High / Medium / Low / Uncertain)
- Par `official_lineup_available_flag` (0 vs 1) — mesure si l'XI officiel améliore la performance
- Par window simulée (vérifier coherence M-30)

### 9.4 Critères de succès V3
La V3 est considérée meilleure que V2 si **toutes** les conditions sont remplies sur fold test :
- log_loss V3 ≤ log_loss V2 − 0.005
- Brier V3 ≤ Brier V2 − 0.003
- Pas de régression > 0.005 log_loss sur aucune ligue avec ≥ 100 matchs test
- ECE (expected calibration error) Draw V3 ≤ ECE Draw V2 − 0.01
- Pas de régression sur le confidence_gap entre V2 et V3

Si V3 n'atteint pas ces critères → conserver V2 en production, V3 reste candidat.

### 9.5 Walk-forward optionnel
Pour réduire la variance d'estimation : repeat le test sur 4 folds chronologiques (par ex. saison par saison). Plus coûteux mais robuste.

---

## 10. Intégration dans le code existant

### 10.1 Fichiers à créer

```
src/football_predictor/modeling/v3/
├── __init__.py
├── constants.py                # CLASSES_BIN_DRAW, CLASSES_BIN_NDW
├── features_selection.py       # select_v3_draw_features, select_v3_ndw_features
├── draw_risk_model.py          # DrawRiskModel + train_draw_risk_from_frame
├── no_draw_winner_model.py     # NoDrawWinnerModel + train_ndw_from_frame
├── stacker.py                  # V3Stacker + train_stacker_from_frame
├── composite.py                # FootballOutcomeV3Model + load/save
├── training.py                 # train_v3_full_pipeline orchestration
├── fusion.py                   # deterministic_fusion fallback
└── inference.py                # predict_v3_for_features

src/football_predictor/features/
├── draw_risk_features.py       # team_strength_parity_score, league_draw_rate, etc.
├── no_draw_winner_features.py  # home_away_strength_edge, attack_defense_edge, etc.
└── lineup_m30_features.py      # official_lineup_available_flag, missing_expected_starters, etc.

src/football_predictor/backtesting/
└── v3_evaluator.py             # comparaison V2 vs V3 vs baselines

src/football_predictor/prediction/
└── v3_service.py               # PredictionV3Service (parallèle à PredictionService)

src/football_predictor/discord/
└── v3_formatter.py             # format Discord V3 enrichi (§14)

tests/
├── test_v3_draw_risk_model.py
├── test_v3_no_draw_winner_model.py
├── test_v3_stacker.py
├── test_v3_composite.py
├── test_v3_features_no_leakage.py     # critique
├── test_v3_dataset_builder_m30.py
├── test_v3_fusion_fallback.py
├── test_v3_predict_service.py
└── fixtures/v3/
    ├── synthetic_dataset_minimal.parquet
    └── ...
```

### 10.2 Fichiers à modifier (extension non-cassante)

| Fichier | Modification |
|---|---|
| [src/football_predictor/db/models.py](src/football_predictor/db/models.py) | Ajouter `V3FeatureSnapshot`, `V3ModelPrediction` (analogue OU). |
| [src/football_predictor/backtesting/dataset_builder.py](src/football_predictor/backtesting/dataset_builder.py) | Paramétrer `prediction_offset_minutes` (défaut 1440 pour préserver V2 ; V3 passera 30). |
| [src/football_predictor/features/feature_builder.py](src/football_predictor/features/feature_builder.py) | Étendre pour produire les nouvelles features V3 (draw_risk_features, no_draw_winner_features, lineup_m30_features) sans casser l'API actuelle ; nouveau `feature_version="v3.0"`. |
| [src/football_predictor/features/data_quality.py](src/football_predictor/features/data_quality.py) | Ajouter flag `has_official_lineup_home/away` séparés et `has_odds_multi_snapshot`. |
| [src/football_predictor/cli.py](src/football_predictor/cli.py) | Nouvelles commandes V3 (§10.3). |
| [src/football_predictor/modeling/loader.py](src/football_predictor/modeling/loader.py) | Détecter `artifact_format=football_outcome_model_v3` et charger `FootballOutcomeV3Model`. |
| [config/competitions_history.yaml](config/competitions_history.yaml) | Aucun changement structurel (saisons existantes suffisent). |

### 10.3 Commandes CLI à ajouter

```bash
# Build dataset M-30 (étend build-dataset)
football-predictor build-dataset-v3 --leagues 39,140,61,78,135 \
  --seasons 2022,2023,2024,2025 \
  --prediction-offset-minutes 30 \
  --output data/processed/training_v3_m30.parquet

# Train V3 pipeline complet (3 sous-modèles + stacker)
football-predictor train-v3 \
  --dataset data/processed/training_v3_m30.parquet \
  --output-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --calibration isotonic_draw,sigmoid_ndw \
  --train-ratio 0.6 --valid-ratio 0.2 --test-ratio 0.2

# Backtest V3 vs V2 vs baselines
football-predictor backtest-v3 \
  --dataset data/processed/training_v3_m30.parquet \
  --model-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --report reports/v3/

# Predict V3 pour une fixture
football-predictor predict-v3 \
  --fixture 123456 \
  --model-dir data/models/v3 \
  --v2-model-dir data/models/v2-late \
  --refresh-data

# Predict-today V3 (analogue predict-today)
football-predictor predict-today-v3 \
  --date 2026-05-08 --window late \
  --league 39 --send-discord
```

### 10.4 Migrations DB
Nouvelle migration Alembic : `0004_v3_model_tables.py`
- `v3_feature_snapshots` (analogue `OUFeatureSnapshot` mais sans `threshold`, avec `feature_version="v3.0"`).
- `v3_model_predictions` :
  - `id, fixture_id, v3_feature_snapshot_id, prediction_time, model_version, fusion_strategy`
  - `p_v3_final_home, p_v3_final_draw, p_v3_final_away`
  - `p_v3_draw_risk, p_v3_home_no_draw, p_v3_away_no_draw`
  - `p_v2_home, p_v2_draw, p_v2_away` (snapshot V2 au moment de la prédiction V3)
  - `p_market_home, p_market_draw, p_market_away`
  - `p_api_home, p_api_draw, p_api_away`
  - `data_quality_score, official_lineup_available_flag`
  - `confidence_score, confidence_label`
  - `predicted_result`
  - `expert_probabilities_json, explanations_json, payload_json`
  - Indexes : `(fixture_id, prediction_time)`, `model_version`

### 10.5 Tests à ajouter
- **Anti data leakage V3** : pour chaque famille de feature V3, asserter qu'un snapshot construit avec `prediction_time = T` n'utilise jamais de donnée de `fetched_at > T` ni de `match_date >= T` (pour la fixture cible).
- **Test M-30 specific** : un dataset construit avec `prediction_offset_minutes=30` ne contient aucune statistique post-match.
- **Test fusion fallback** : si stacker absent, le fallback déterministe normalise correctement.
- **Test calibration** : Brier Draw Risk après calibration ≤ Brier avant.
- **Test composite predict_proba** : sortie ∈ [0, 1]³ et somme = 1.
- **Test integration V2→V3** : V3Service ne casse pas si V2 model_dir absent (utilise prior uniform).
- **Test Discord format V3** : message ≤ 1900 chars, fermeture markdown propre, secrets masqués.

### 10.6 Compatibilité V2
- Tables V2 (`FeatureSnapshot`, `ModelPrediction`) inchangées.
- `predict-today` (V2) reste fonctionnel.
- Cron production peut passer progressivement de `predict-today` à `predict-today-v3` après validation.
- Période de **shadow mode** prévue : V3 calcule en parallèle sans publier sur Discord, on compare V2 vs V3 sur 2–4 semaines.

---

## 11. Plan de développement par étapes

| Sprint | Objectif | Livrables clés | DoD |
|---|---|---|---|
| **S1 — Audit & DB** | Préparer le terrain | Migration `0004_v3_model_tables.py`, tests de migration up/down, audit cardinalité multi-snapshots `OddsSnapshot` | pytest passe, alembic up/down OK |
| **S2 — Features M-30** | Reconstruire le dataset à M-30 | Paramètre `prediction_offset_minutes`, nouveau `feature_version="v3.0"`, features `lineup_m30_features.py`, `draw_risk_features.py`, `no_draw_winner_features.py` | Tests anti-leakage M-30 verts |
| **S3 — Datasets** | Builders pour les 3 datasets | `build_v3_draw_risk_dataset`, `build_v3_ndw_dataset`, jointure stacker, parquet de référence | Datasets reproductibles, schéma documenté |
| **S4 — Draw Risk Model** | Modèle binaire DRAW | `draw_risk_model.py`, training CLI, calibration isotonic, métriques | AUC DRAW ≥ baseline, ECE ≤ V2 ECE_DRAW |
| **S5 — No-Draw Winner Model** | Modèle binaire HOME-vs-AWAY | `no_draw_winner_model.py`, training, calibration sigmoid | AUC ≥ odds-only baseline |
| **S6 — Stacker & Fusion** | Composite V3 + fallback | `stacker.py`, `fusion.py`, `composite.py`, training stacker sur valid, `FootballOutcomeV3Model.predict_proba` | predict_proba ∈ [0,1]³, somme=1 |
| **S7 — Backtest & comparaison** | Évaluation V2 vs V3 | `v3_evaluator.py`, `reports/v3/*.md`, tableau comparatif | Critères §9.4 évalués honnêtement |
| **S8 — Inférence & Discord** | Pipeline production | `v3_service.py`, `v3_formatter.py`, commandes CLI, persistance `V3ModelPrediction` | predict-v3 fonctionne sur 1 fixture live |
| **S9 — Shadow mode** | V2 et V3 parallèles | Cron daily-late publie V2, V3 logge en DB sans Discord | 14 jours de données comparatives |
| **S10 — Migration prod & doc** | Bascule sur V3 | Activation V3 Discord après validation, mise à jour `docs/modeling_strategy.md`, `docs/data_contract.md` | Documentation à jour, tests pleins, rollback documenté |

---

## 12. Risques et points d'attention

### 12.1 Data leakage
- **Plus grand risque** : reconstituer M-30 sans rigueur. Vérifier exhaustivement :
  - `FixtureLineup` doit utiliser `fetched_at <= prediction_time` (pas `match_date`).
  - `Injury.fetched_at <= prediction_time`.
  - `OddsSnapshot.fetched_at <= prediction_time` (et tri pour le dernier snapshot valide).
  - `FixtureStatistics` ne doit jamais inclure la fixture cible (toutes les stats pré-match d'une équipe excluent le match en cours d'analyse).
  - `StandingSnapshot` filtré sur `snapshot_date <= prediction_time`.
- Tests dédiés `test_v3_features_no_leakage.py` sur les 3 nouvelles familles + tests de simulation chronologique.

### 12.2 Lineups historiques
- Les lineups officiels sont publiés par API-Football typiquement 1h avant kickoff → à M-30 elles sont disponibles dans la majorité des cas mais pas toutes (compétitions mineures, matchs reportés).
- Risque : sur le dataset historique, `FixtureLineup.fetched_at` peut être proche de kickoff sans qu'on sache exactement quand l'XI a été publié → utiliser `min(fetched_at)` est un bon proxy. Documenter cette limite.

### 12.3 Données manquantes
- Ne **jamais** échouer si Draw Risk ou No-Draw Winner ne peut pas inférer → fallback V2 ou prior.
- Marquer chaque cas dans `data_quality_json`.

### 12.4 Coverage API-Football
- `/predictions` : couverture inégale → flag `has_api_prediction`.
- `/odds` : pas tous bookmakers/bets disponibles selon ligue → `bookmaker_count` peut être 1.
- `/injuries` : couverture mineure pour ligues secondaires → impact_absence sera proche de 0.

### 12.5 Odds snapshots
- Si `OddsSnapshot` n'a qu'un seul snapshot par fixture (cas actuel à valider en S1) → `odds_movement_*` sera 0 partout → la feature devient peu informative.
- Action S1 : vérifier la cardinalité actuelle ; sprint cron `refresh-odds-multi` à programmer si insuffisant.

### 12.6 Calibration du nul
- Le nul est typiquement sur-prédit ou sous-prédit selon la calibration. Isotonic est plus robuste mais demande plus de données.
- Suivre ECE par bin pour Draw spécifiquement.

### 12.7 Déséquilibre de classes
- Draw Risk : ~75/25 → utiliser `class_weight='balanced'` ou pondérer la log-loss.
- No-Draw Winner : ~55/45 (Home advantage) → marginal, sigmoid Platt suffit.

### 12.8 Surapprentissage du stacker
- Le stacker s'entraîne sur **valid** où les sous-modèles n'ont **jamais vu** ces données. Risque d'overfit faible mais le valid est petit (~20 % du dataset) → risque modéré.
- Si valid < 200 lignes → **désactiver** le stacker et utiliser fallback déterministe.
- Optionnel : utiliser cross-fitting (K-fold OOF predictions) pour entraîner le stacker sur tout le train.

### 12.9 Généralisation par ligue
- Rapport de métriques par ligue impératif. Si une ligue régresse sévèrement, ajouter un flag `league_id` catégoriel au stacker (one-hot).

### 12.10 Régression silencieuse
- Cron de comparaison V2 vs V3 sur les prédictions live (2 semaines shadow mode) pour détecter dérive avant promotion.

---

## 13. Compatibilité Discord

### 13.1 Structure du message V3 (en français, ≤ 1900 chars)

```
```md
🏟️ PRÉDICTION FOOTBALL — V3

Match : {Home} vs {Away}
Compétition : {league_name}
Date : YYYY-MM-DD HH:mm Europe/Paris
Fenêtre : M-30 (kickoff − 30 min)

Résultat prédit : {Victoire domicile / Match nul / Victoire extérieur}
Confiance : {High/Medium/Low/Uncertain}
Score de confiance : XX.X pts

Probabilités modèle V3 (finales) :
- Domicile  : XX.X%
- Nul       : XX.X%
- Extérieur : XX.X%

Décomposition V3 :
- Risque de nul        : XX.X% ({faible/moyen/élevé})
- Avantage hors nul    : {Home/Away} ({write_force XX.X%})

Probabilités marché :
- Domicile  : XX.X%
- Nul       : XX.X%
- Extérieur : XX.X%

Comparaison V2 :
- Domicile  : XX.X%
- Nul       : XX.X%
- Extérieur : XX.X%

Top facteurs (Risque de nul) :
1. ...
2. ...

Top facteurs (Hors nul → {Home|Away}) :
1. ...
2. ...

XI :
- {XI officiel utilisé} ou {XI probable utilisé, lineups officielles indisponibles}

Absences clés :
- {Home} : ...
- {Away} : ...

Qualité des données :
- Score global : XX/100
- Odds : oui/non
- Lineups officielles : oui/non
- Blessures : oui/non
- Stats joueurs : oui/non

Note : prédiction probabiliste à M-30, pas une certitude.
```
```

### 13.2 Champs nouveaux à formater
- `risque_de_nul_label` : seuils ex. `< 22% = faible`, `22–32% = moyen`, `> 32% = élevé`.
- `avantage_hors_nul_label` : `Home` si `P(H|noDraw) > 0.55`, `Away` si < 0.45, sinon `équilibré`.
- `comparaison_v2` : optionnel ; à afficher seulement si delta > 5 % sur une classe.
- `top_facteurs_*` : top-3 features les plus contributives par sous-modèle. Implémentation : SHAP local (si CatBoost ou GBDT) ou inspection des coefficients standardisés (si LR). Fallback heuristique sur les écarts feature vs distribution moyenne.

### 13.3 Routing Discord
Inchangé : passer par [`router.py`](src/football_predictor/discord/router.py) avec `message_type="prediction"` et `competition_key` issu de la fixture. Aucun nouveau channel requis.

### 13.4 Backwards-compat
- `format_prediction_markdown` original conservé pour V2.
- Nouveau `format_prediction_v3_markdown` dans `v3_formatter.py`.
- Pendant le shadow mode, V2 publie sur `predictions` ; V3 logge en DB seulement.

---

## 14. Persistance et versioning

### 14.1 Champs `V3ModelPrediction` (rappel)
Voir §10.4. Tous les champs sont obligatoires sauf ceux explicitement nullable.

### 14.2 Versions à tracer
- `feature_version` (sur `V3FeatureSnapshot`) : `"v3.0"`, `"v3.1"`, etc.
- `model_version` (sur `V3ModelPrediction`) : `"v3.0-final"` (composite) ; sous-versions stockées dans `payload_json["component_versions"]`.
- `fusion_strategy` ∈ `{"stacker_lr", "deterministic_fallback", "blend_v2_only"}` — colonne typée.
- `calibration_decision` JSON dans `payload_json` : `{"draw_risk": "isotonic_cv3", "no_draw_winner": "sigmoid_cv3", "stacker": "none"}`.

### 14.3 `data_quality_json` minimal
```json
{
  "score": 78,
  "has_official_lineup_home": true,
  "has_official_lineup_away": false,
  "has_odds_multi_snapshot": true,
  "bookmaker_count": 7,
  "has_recent_injuries_home": true,
  "has_api_prediction": true,
  "warnings": ["away_lineup_missing"]
}
```

### 14.4 `explanation_json` minimal
```json
{
  "draw_risk_label": "moyen",
  "no_draw_winner_label": "Home",
  "top_factors_draw_risk": [
    {"name": "team_strength_parity_score", "value": 0.91, "shap": 0.12},
    {"name": "expected_goals_total_low_score", "value": 0.62, "shap": 0.08},
    {"name": "league_draw_rate", "value": 0.27, "shap": 0.06}
  ],
  "top_factors_no_draw_winner_home": [
    {"name": "home_advantage_edge", "value": 0.45, "shap": 0.18},
    {"name": "xi_value_edge", "value": 12.4, "shap": 0.14}
  ]
}
```

### 14.5 Migrations DB
Une seule nouvelle migration : `0004_v3_model_tables.py` (S1). Pas de modification rétroactive des tables V2 ou OU.

---

## 15. Vérification de bout en bout (DoD du plan)

Avant de considérer la V3 livrable :

1. **Tests unitaires** : tous verts (`pytest`).
2. **Anti-leakage** : `pytest tests/test_v3_features_no_leakage.py` vert.
3. **Lint** : `ruff check src/football_predictor/modeling/v3 src/football_predictor/features/draw_risk_features.py ...` vert.
4. **Type checking** : `mypy src/football_predictor/modeling/v3` vert.
5. **End-to-end synthétique** : `pytest tests/test_v3_predict_service.py::test_predict_v3_synthetic_fixture` produit une `V3ModelPrediction` valide.
6. **End-to-end live** : `football-predictor predict-v3 --fixture <id> --refresh-data --no-send-discord` génère un objet complet sans erreur sur une fixture réelle de la saison en cours.
7. **Backtest** : `football-predictor backtest-v3` produit `reports/v3/comparison_vs_v2.md` avec les métriques §9.2.
8. **Discord dry-run** : `football-predictor predict-today-v3 --dry-run --print-only` rend un message valide.
9. **Shadow mode 14 jours** : V3 logge sans publier ; comparaison documentée.
10. **Documentation** : `docs/modeling_strategy.md` mis à jour, `docs/data_contract.md` listant les champs V3, `README.md` mentionnant V3 avec son statut.

---

## 16. Questions ouvertes (non bloquantes)

1. **Multi-snapshots OddsSnapshot** : la cardinalité actuelle est inconnue côté audit. Si médiane = 1 snapshot par fixture, les features `odds_movement_*` seront vides. Action : audit S1 ; si insuffisant, ajouter un cron `refresh-odds` 4×/jour pendant la fenêtre J-1 → M-30.
2. **Cross-fitting du stacker** : sur valid uniquement (simple) vs OOF K-fold (complexe). Recommandation S6 : commencer simple, mesurer overfitting, escalader si valid trop petit.
3. **Catégorisation `competition_type`** : La V3 inclut-elle les coupes (Coupe d'Europe, Coupe Nationale) ou reste-t-elle sur les championnats ? Recommandation : commencer ligues domestiques (cohérence V2) ; étendre coupes en S10+.
4. **Choix d'algorithme final** : `HistGradientBoostingClassifier` recommandé. Bench `CatBoost` (déjà installé) sur S4-S5 si volume suffisant et mesurer si gain.
5. **Seuil `P_start` pour XI probable** : actuellement non documenté ; valider 0.55 vs 0.50 vs distribution observée.
6. **Walk-forward complet** : implémenté dès S7 ou seulement après validation V3 simple ? Recommandation : simple d'abord, walk-forward optionnel S10+.

---

## 17. Critical files (récapitulatif)

### Fichiers à lire avant tout sprint V3
- [AGENTS.md](AGENTS.md), [blueprint.md](blueprint.md), [docs/data_contract.md](docs/data_contract.md), [docs/modeling_strategy.md](docs/modeling_strategy.md)
- [src/football_predictor/modeling/v2_model.py](src/football_predictor/modeling/v2_model.py) (référence pattern)
- [src/football_predictor/ou_model/](src/football_predictor/ou_model/) (template multi-modèle parallèle)
- [src/football_predictor/features/feature_builder.py](src/football_predictor/features/feature_builder.py)
- [src/football_predictor/db/models.py](src/football_predictor/db/models.py)
- [src/football_predictor/backtesting/dataset_builder.py](src/football_predictor/backtesting/dataset_builder.py)

### Fichiers à modifier (extension non-cassante)
Voir §10.2.

### Fichiers à créer
Voir §10.1.

### Documentation à mettre à jour à la fin
- [docs/modeling_strategy.md](docs/modeling_strategy.md) — nouvelle section "V3 multi-modèles"
- [docs/data_contract.md](docs/data_contract.md) — nouvelles tables / nouveaux champs
- [docs/architecture.md](docs/architecture.md) — diagramme mis à jour
- [README.md](README.md) — V3 status + commandes
- [docs/operations_guide.md](docs/operations_guide.md) — nouveaux crons, scripts
