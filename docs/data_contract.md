# Data Contract

## Principes

Le contrat de données garantit que chaque prédiction est traçable, reproductible et
point-in-time.

Règles centrales :

- aucune feature ne doit utiliser une information indisponible à `prediction_time` ;
- la fixture cible doit être exclue de ses propres historiques ;
- les données manquantes doivent rester explicites ;
- les IDs API-Football ne doivent jamais être inventés ;
- les payloads bruts utiles doivent être conservés pour audit.

## Référentiels Locaux

Chemins configurables attendus :

```text
docs/api_football_reference.json
docs/api_football_players_reference.json
docs/api_football_players_cache.json
```

Usage :

- `docs/api_football_reference.json` : source structurée pour leagues, teams, fixtures,
  venues, bookmakers et bets ;
- `docs/api_football_players_reference.json` : source structurée pour players et squads ;
- `docs/api_football_players_cache.json` : cache technique pour reprendre la collecte
  `/players/squads`, pas une source métier principale.

La configuration des compétitions suivies se trouve dans `config/competitions.example.yaml`
ou un fichier utilisateur équivalent pointé par `COMPETITIONS_CONFIG_PATH`. Les champs
`key`, `league_id`, `season`, `name`, `country` et `enabled` y sont validés contre
`docs/api_football_reference.json`; une valeur absente du référentiel doit lever une erreur
explicite.

Règles Markdown vs JSON :

- JSON : utilisé par le code, les validateurs, le seed DB et les tests réalistes ;
- Markdown : utilisé pour lecture humaine, documentation et vérification manuelle ;
- cache joueurs : utilisé seulement pour collecte ou reprise d'ingestion.

## Entités Principales

### `fixture`

Champs minimaux :

- `fixture_id` ;
- `league_id` ;
- `season` ;
- `date` ;
- `round` ;
- `status_short` ;
- `home_team_id` ;
- `away_team_id` ;
- `home_team` ;
- `away_team` ;
- `venue_id` si disponible ;
- `payload_json`.

### `team`

Champs minimaux :

- `team_id` ;
- `name` ;
- `country` ;
- `logo` si disponible ;
- `venue_id` si disponible ;
- `payload_json`.

### `player`

Champs minimaux :

- `player_id` ;
- `name` ;
- `age` si disponible ;
- `photo` si disponible ;
- `payload_json`.

### `player_squad`

Champs minimaux :

- `player_id` ;
- `team_id` ;
- `league_id` ;
- `season` ;
- `position` ;
- `number` si disponible ;
- `fetched_at` ou date de génération du référentiel ;
- `payload_json`.

### `odds`

Champs minimaux :

- `fixture_id` ;
- `bookmaker_id` ;
- `bet_id` ;
- `fetched_at` ;
- `is_live` ;
- `odd_home` ;
- `odd_draw` ;
- `odd_away` ;
- `values_json` ;
- `odds_json` ;
- `payload_json`.

La V1 ne mélange pas live odds et prematch odds : `is_live` doit rester `false` pour les
features marché 1X2. Le marché cible est résolu depuis le référentiel local, par défaut
`Match Winner`. Seules les odds avec `fetched_at <= prediction_time` sont utilisables.
Plusieurs snapshots d'un même bookmaker sont conservés pour calculer le mouvement des cotes.

Les features marché exposent au minimum :

- `p_market_home` ;
- `p_market_draw` ;
- `p_market_away` ;
- `market_confidence` = meilleure probabilité moins deuxième meilleure probabilité ;
- `bookmaker_count` ;
- `market_dispersion` ;
- `delta_home`, `delta_draw`, `delta_away` pour le mouvement entre premier snapshot
  disponible et dernier snapshot avant le cutoff.

Le calcul du consensus prend le dernier snapshot disponible par bookmaker avant le cutoff et
pondère chaque bookmaker par l'inverse de son overround. Un snapshot postérieur à
`prediction_time` ou `as_of_time` est interdit.

### `injury`

Champs minimaux :

- `fixture_id` si disponible ;
- `team_id` ;
- `player_id` ;
- `league_id` ;
- `season` ;
- `reason` ;
- `type` ;
- `date` si fournie par l'API ;
- `fetched_at` ;
- `payload_json`.

Une injury postérieure à `prediction_time` est interdite dans les features.

### `lineup`

Champs minimaux :

- `fixture_id` ;
- `team_id` ;
- `formation` ;
- `start_xi_json` ;
- `substitutes_json` ;
- `players_json` ;
- `fetched_at` ;
- `payload_json`.

Une lineup officielle ne peut être utilisée que si elle a été récupérée avant
`prediction_time`.

### `player_stats`

Champs minimaux :

- `fixture_id` ;
- `team_id` ;
- `player_id` ;
- `fetched_at` ;
- `statistics_json` ;
- `stats_json` ;
- `rating` si disponible ;
- `minutes` si disponible ;
- `position` si disponible ;
- `payload_json`.

Les stats joueurs du match cible ne doivent jamais servir à prédire ce même match.

### `fixture_statistics`

Champs minimaux :

- `fixture_id` ;
- `team_id` ;
- `statistics_json` ;
- `fetched_at` ;
- `payload_json`.

Ces statistiques post-match ne sont utilisables que pour des historiques strictement
antérieurs à la fixture cible.

### `fixture_event`

Champs minimaux :

- `fixture_id` ;
- `team_id` si disponible ;
- `player_id` si disponible ;
- `assist_player_id` si disponible ;
- `type` ;
- `detail` ;
- `elapsed` ;
- `extra` ;
- `fetched_at` ;
- `payload_json`.

### `prediction_snapshot`

Champs minimaux :

- `fixture_id` ;
- `fetched_at` ;
- `source` ;
- `payload_json`.

Pour API-Football predictions, le snapshot doit être antérieur ou égal à
`prediction_time`.

### `feature_snapshot`

Champs minimaux :

- `fixture_id` ;
- `prediction_time` ;
- `feature_version` ;
- `features_json` ;
- `data_quality_json`.

Toutes les valeurs doivent être sérialisables en JSON.

### Features Coupe Du Monde `worldcup-1x2-v1`

Le modèle Coupe du Monde écrit des snapshots `FeatureSnapshot` avec
`feature_version="worldcup-1x2-v1"`. Ces snapshots sont séparés des features championnats.

Champs principaux :

- `wc_home_*` et `wc_away_*` : agrégats par sélection ;
- `wc_diff_*` : différence home moins away pour les features numériques comparables ;
- `wc_*_last5`, `wc_*_last10`, `wc_*_last20` : formes rolling avant `prediction_time` ;
- `wc_*_recent2021` et `wc_*_recent2024` : formes filtrées sur les matchs précédents
  depuis 2021 ou 2024 ;
- `wc_internal_elo_diff`, `wc_power_rating_diff`, `wc_expected_margin` ;
- `wc_expected_home_goals`, `wc_expected_away_goals`, `wc_total_expected_goals` ;
- `p_wc_rating_home`, `p_wc_rating_draw`, `p_wc_rating_away` ;
- `p_wc_poisson_home`, `p_wc_poisson_draw`, `p_wc_poisson_away` ;
- `wc_market_*` et `p_wc_market_*` : consensus odds 1X2 pré-match, uniquement si
  `OddsSnapshot.fetched_at <= prediction_time` ;
- `wc_api_pred_*` et `p_wc_api_*` : dernière prédiction API-Football disponible avant
  `prediction_time` ;
- `wc_official_lineup_*`, `wc_home_lineup_surprise_score`,
  `wc_away_lineup_surprise_score` : disponibilité et impact lineups M-30 ;
- `wc_home_absence_*`, `wc_away_absence_*`, `wc_*_availability_score` : absences et
  disponibilité des joueurs issues des injuries point-in-time ;
- `wc_dynamic_*` : flags de couverture dynamique et pénalités bornées appliquées au rating
  et au Poisson ;
- `p_wc_rating_dynamic_home/draw/away` et `p_wc_poisson_dynamic_home/draw/away` :
  probabilités après ajustement injuries/lineups ;
- `wc_fifa_*` et `wc_current_elo_*` seulement pour les prédictions CDM 2026 futures.

Règles :

- les matchs historiques utilisés doivent avoir `date < prediction_time` ;
- le résultat du match cible (`home_goals`, `away_goals`, `target`) est interdit dans
  `features_json` ;
- les rankings FIFA/Elo actuels sont interdits dans les lignes historiques de backtest ;
- les odds, predictions API, lineups et injuries doivent respecter
  `fetched_at <= prediction_time` ;
- le backtest CDM strict n'invente pas de source dynamique manquante et expose sa couverture ;
- les aliases doivent résoudre les 48 équipes CDM 2026 avant production ;
- les features CDM ne doivent pas être utilisées par les pipelines championnats.

### `discord_message`

Champs minimaux :

- `fixture_id` si le message concerne une fixture ;
- `model_prediction_id` si le message publie une prédiction ;
- `competition_key` ;
- `league_id` ;
- `season` ;
- `channel_key` ;
- `message_type` ;
- `webhook_hash` ou `webhook_url_hash`, jamais l'URL complète ;
- `message_hash` pour déduplication ;
- `message_markdown` ;
- `dry_run` ;
- `print_only` ;
- `route_json` sans secret ;
- `payload_json` sans secret, par exemple le contenu envoyé et `allowed_mentions` ;
- `sent_at` si un envoi réel a eu lieu ;
- `status` ;
- `response_json` et `response_text` sans secret.

Le routage Discord cible les channels `classement`, `calendrier`, `matchs_du_jour`,
`analyses`, `predictions`, `resultats` et `discussions`. Les messages automatiques vers
`discussions` sont refusés par défaut. Les vraies URLs webhook et `DISCORD_BOT_TOKEN`
restent hors base et hors logs ; seuls des hashes courts non réversibles sont conservés.

## Règle De Snapshot Temporel

Chaque table dynamique doit porter un horodatage exploitable :

- `fetched_at` pour payloads API ;
- `snapshot_date` pour standings ou agrégats datés ;
- `prediction_time` pour features et prédictions.

Une feature est valide seulement si chaque source respecte :

```text
source_time <= prediction_time
```

La reconstruction d'un match passé doit produire les mêmes données disponibles à l'époque,
pas les données connues après le match.

## Nommage Des Champs

Règles de nommage :

- classes de résultat : `HOME`, `DRAW`, `AWAY` ;
- probabilités : `p_home`, `p_draw`, `p_away` ;
- préfixes équipe : `home_team_`, `away_team_` ;
- fenêtres : `_last3`, `_last5`, `_last10`, `_last15` ;
- moyennes exponentielles : `_ewma` ;
- disponibilité : suffixes ou flags `_available`, `_missing`, `_coverage` ;
- qualité des données : `data_quality_json`.

Les noms de features doivent rester stables entre training, backtesting et prédiction.

## Features Équipe V1

Le builder `team_features_v1` produit un dict plat dans `FeatureSnapshot.features_json`.
Chaque appel doit fournir `fixture_id` et `prediction_time`.

Familles de champs :

- contexte : `target_fixture_id`, `league_id`, `season`, `home_team_id`,
  `away_team_id`, `prediction_time` ;
- forme : `home_team_global_points_per_match_last3`,
  `home_team_home_last5_ppg`, `away_team_away_last5_ppg`, avec fenêtres `last3`,
  `last5`, `last10`, `last15` ;
- splits : `*_global_*`, `*_home_*`, `*_away_*` ;
- buts : `goals_for_avg`, `goals_against_avg`, `goal_diff_avg`,
  `clean_sheet_rate`, `failed_to_score_rate` ;
- EWMA : `*_global_points_ewma`, `*_global_goals_for_ewma`,
  `*_global_goals_against_ewma`, `*_global_goal_diff_ewma` ;
- stats match : `shots_for_avg`, `shots_against_avg`, `shots_on_goal_for_avg`,
  `shots_on_goal_against_avg`, `possession_avg`, `corners_for_avg`,
  `corners_against_avg`, `cards_avg`, `pass_accuracy_avg` ;
- ratios : `shot_accuracy`, `goal_conversion`, `box_shot_share`, `save_rate` ;
- pseudo-xG : `*_pseudo_xg_avg_lastN` ;
- adversaire : `adj_goals_for`, `adj_goals_against`, `adj_shots_for`,
  `adj_shots_against`, `adj_shots_on_goal_for`, `adj_shots_on_goal_against` ;
- contexte : `rest_days_home`, `rest_days_away`, `matches_last_7_days_home`,
  `matches_last_14_days_home`, `home_team_travel_away_flag`,
  `away_team_travel_away_flag`, `fixture_round_number` ;
- standings : `*_standing_rank`, `*_standing_points`, `*_standing_goals_diff`,
  `*_standing_played`, `*_standing_points_per_match`, `rank_diff`, `points_diff`,
  `goals_diff_diff`.

Le pseudo-xG V1 est une heuristique de disponibilité, pas une métrique officielle :

```text
0.03 * total_shots
+ 0.09 * shots_on_goal
+ 0.07 * shots_insidebox
+ 0.02 * shots_outsidebox
+ 0.76 * penalties
```

Il n'est calculé que si au moins une métrique de tir ou un penalty connu existe. Les
composants absents valent `0` dans la formule, mais les flags de couverture restent
visibles dans `data_quality_json`.

`data_quality_json` expose notamment `home_team_history_count`,
`away_team_history_count`, `fixture_statistics_coverage_ratio`,
`missing_statistics_rate`, `events_coverage_ratio`, `standings_available`,
`standings_available_home`, `standings_available_away`, `pseudo_xg_available_home`,
`pseudo_xg_available_away` et `warnings`.

## Features Joueurs Et XI V1

Le builder `player_xi_features_v1` produit un dict plat dans
`FeatureSnapshot.features_json`. Chaque appel doit fournir `fixture_id` et
`prediction_time`.

Sources autorisées :

- `FixtureLineup` avec `Fixture.date < prediction_time`,
  `Fixture.fixture_id != fixture_id` et `FixtureLineup.fetched_at <= prediction_time` ;
- `FixturePlayerStats` avec `Fixture.date < prediction_time`,
  `Fixture.fixture_id != fixture_id` et `FixturePlayerStats.fetched_at <= prediction_time` ;
- `Injury` du fixture cible ou de l'équipe, uniquement si `fetched_at <= prediction_time` ;
- `Player` et `PlayerSquad` locaux ;
- `docs/api_football_players_reference.json` comme fallback d'identité, poste et numéro.

Le référentiel joueurs local ne remplace pas les snapshots dynamiques. Il sert à éviter les
IDs ou postes inventés quand les lineups ou stats joueurs sont partielles.

Familles de champs :

- formation : `home_team_probable_formation`, `away_team_probable_formation` ;
- XI probable : `home_team_expected_xi_json`, `away_team_expected_xi_json` ;
- absences : `home_team_key_absences_json`, `away_team_key_absences_json`,
  `*_absence_impact_score`, `*_starter_missing_count`,
  `*_absent_expected_starters_count` ;
- stabilité et profondeur : `*_xi_stability_score`, `*_bench_depth_score`,
  `*_replacement_quality_score`, `*_availability_score` ;
- valeur XI : `*_expected_xi_avg_value`, `*_expected_xi_total_value` ;
- couverture : `*_player_stats_coverage_ratio`, `*_lineup_coverage_ratio`.

Chaque ligne de `*_expected_xi_json` expose au minimum :

- `player_id` ;
- `name` ;
- `position` ;
- `position_group` parmi `GK`, `DEF`, `MID`, `ATT`, `UNK` ;
- `number` si disponible ;
- `p_start` ;
- `player_value` ;
- `score`.

Chaque ligne de `*_key_absences_json` expose au minimum :

- `player_id` ;
- `name` ;
- `position_group` ;
- `p_start` ;
- `player_value` ;
- `severity` ;
- `replacement_player_id` si disponible ;
- `replacement_value` ;
- `replacement_gap` ;
- `absence_impact` ;
- `reason` ;
- `type`.

Formule V1 de `P_start` :

```text
P_start =
0.50 * weighted_start_frequency
+ 0.25 * weighted_minutes_share
+ 0.15 * formation_position_compatibility
+ 0.10 * recent_availability
```

`player_value` est normalisé par groupe de poste. Un gardien, un défenseur, un milieu et
un attaquant ne sont jamais comparés directement sur une même échelle brute.

Les helpers `build_player_recent_form` et `compute_player_value` exposent les signaux
joueurs avant agrégation XI :

- minutes et titularisations récentes par fenêtre `last3`, `last5`, `last10` ;
- rating moyen, buts, passes décisives et cartons si disponibles ;
- position la plus fréquente et groupe de poste ;
- `last_match_minutes`, `ewma_minutes`, `ewma_rating` ;
- `value_zscore` et `value_0_100`, normalisés au sein du groupe de poste.

Formule V1 d'impact absence :

```text
absence_impact =
P_start * player_value * severity * replacement_gap * position_multiplier
```

Un joueur peu probable titulaire (`P_start < 0.35`) est fortement amorti. Le
`replacement_gap` compare l'absent au meilleur remplaçant disponible du même groupe de
poste. Les multiplicateurs initiaux sont `GK=1.30`, `ATT=1.25`, `MID=1.00`, `DEF=1.00`,
avec `DEF central=1.10` uniquement si identifiable depuis la grille de lineup.

Sévérité V1 :

- `Missing Fixture`, suspension ou libellé équivalent : `1.0` ;
- `Questionable` / incertain : `0.6` ;
- mineur, inconnu ou absent de libellé : `0.3`.

`data_quality_json` expose notamment :

- `*_lineups_available` ;
- `*_player_stats_available` ;
- `*_players_with_reference_position` ;
- `*_injuries_available` ;
- `*_reference_fallback_used` ;
- `*_warnings`.

## Feature Snapshot Global V1

Le builder public `features.feature_builder.build_feature_snapshot` fusionne les familles
équipe, joueurs/XI, marché et
prédiction API-Football dans un `FeatureSnapshot` unique par `(fixture_id,
prediction_time)`.

Règles :

- `features_json` ne contient jamais `target`, `home_goals` ou `away_goals` ;
- odds : dernier snapshot prematch par bookmaker avec `fetched_at <= prediction_time` ;
- API prediction : dernier `ApiPredictionSnapshot` avec `fetched_at <= prediction_time` ;
- sources absentes : valeurs `None`, compteurs à `0`, warnings dans `data_quality_json` ;
- `feature_version` vaut `v1` par défaut.

Champs globaux ajoutés :

- marché : `market_home`, `market_draw`, `market_away`,
  `market_bookmaker_count`, `market_dispersion`, `market_confidence` ;
- mouvement odds : `odds_movement_home`, `odds_movement_draw`, `odds_movement_away` ;
- API prediction : `api_pred_home`, `api_pred_draw`, `api_pred_away`,
  `api_pred_winner_home_flag`, `api_pred_winner_away_flag`,
  `api_pred_win_or_draw_flag` ;
- qualité : `overall_data_quality_score`.

Score qualité V1 :

```text
historique équipe = 20
stats équipe      = 15
stats joueurs     = 15
lineups / XI      = 10
odds              = 20
API prediction    = 10
injuries          = 5
référence docs    = 3
standings         = 2
```

`data_quality_json` expose explicitement `historical_matches_home_count`,
`historical_matches_away_count`, `team_stats_available_rate`,
`player_stats_available_rate`, `lineups_available_flag`, `injuries_available_flag`,
`odds_available_flag`, `api_prediction_available_flag`,
`reference_docs_available_flag` et `overall_data_quality_score`.

Depuis la clarification qualité live, les lineups et stats joueurs sont aussi séparées :

- `target_lineups_available_flag`, `target_lineups_home_available_flag`,
  `target_lineups_away_available_flag` : lineups officielles du match cible connues avec
  `fetched_at <= prediction_time` ;
- `historical_lineups_available_flag` : historique de lineups disponible pour les deux équipes ;
- `historical_player_stats_available_rate` : part domicile/extérieur avec stats joueurs
  historiques disponibles ;
- `lineups_available_flag` reste compatible et vaut `true` si les lineups cible ou
  l'historique lineups sont disponibles.

## Feature Snapshot V3 M-30

Quand `features.feature_builder.build_feature_snapshot` est appelé avec
`feature_version="v3.0"` ou une version préfixée `v3`, le snapshot global reste
point-in-time et ajoute des features spécialisées V3. La fenêtre recommandée est
`prediction_time = fixture.date - 30 minutes`.

Familles ajoutées :

- `lineup_m30_*` / `official_lineup_*` : disponibilité des XI officiels du match cible,
  formations, changement de formation et surprise du XI, toujours avec
  `FixtureLineup.fetched_at <= prediction_time` ;
- `draw_risk_*` : parité de niveau, faible total attendu, solidité défensive, faiblesse
  offensive, taux de nul ligue/saison, signal marché draw et probabilité de nul Poisson ;
- `ndw_*` : edge domicile/extérieur hors nul, edge attaque/défense, edge XI, edge absences,
  et probabilités marché conditionnelles `P(Home | No Draw)` / `P(Away | No Draw)`.

Flags qualité V3 :

- `has_official_lineup_home`, `has_official_lineup_away`, `has_official_lineup` ;
- `official_lineup_available_flag` vaut `true` seulement si les deux XI officiels sont
  disponibles avant `prediction_time` ;
- `has_odds_multi_snapshot` vaut `true` si au moins deux timestamps d'odds prematch
  distincts existent pour la fixture avant `prediction_time` ;
- `data_quality_score` est un alias numérique V3 de `overall_data_quality_score`.

Règles anti fuite V3 :

- aucune lineup officielle récupérée après `prediction_time` ne peut activer un flag ;
- les fixtures historiques utilisées pour les taux ou formations doivent avoir
  `Fixture.date < prediction_time` et `fixture_id != fixture_id cible` ;
- le mouvement de cotes et `has_odds_multi_snapshot` ignorent toute odd dont
  `fetched_at > prediction_time`.

## Dataset D'Entraînement

Le dataset historique est construit uniquement depuis la DB locale via
`backtesting.dataset_builder`. Les fixtures éligibles sont terminées (`FT`, `AET`, `PEN`)
et possèdent `home_goals` et `away_goals`.

Colonnes cible hors features :

- `target` : `HOME`, `DRAW` ou `AWAY` ;
- `home_goals` ;
- `away_goals` ;
- `fixture_date` ;
- `prediction_time` ;
- `feature_snapshot_id`.

Par défaut, `prediction_time = fixture.date - 24h`. La fenêtre `30m` est disponible pour
entraîner la V2 alignée avec `daily_late`; `40m` reste accepté pour compatibilité. Les
exports `.csv` et `.parquet` sont
supportés. Les splits temporels utilisent `fixture_date` et ne mélangent jamais les lignes
par défaut.

### Datasets V3

Le module `backtesting.v3_dataset_builder` construit les datasets V3 à partir du builder
global avec `feature_version="v3.0"` et `prediction_offset_minutes=30` par défaut.

Datasets produits :

- Draw Risk : toutes les fixtures terminées, avec `outcome` et `is_draw` (`1` si
  `outcome == "DRAW"`) ;
- No-Draw Winner : fixtures `HOME` ou `AWAY` uniquement, avec `home_wins` (`1` si
  `outcome == "HOME"`) ;
- Stacker : jointure par `fixture_id` entre le fold choisi, les prédictions Draw Risk,
  les prédictions No-Draw Winner, les probabilités V2 éventuelles, les signaux marché/API
  point-in-time, `data_quality_score` et `official_lineup_available_flag`.

Les splits V3 sont chronologiques, par défaut `60 % train / 20 % valid / 20 % test`.
Le dataset stacker est destiné au fold validation par défaut, afin de ne pas entraîner le
stacker sur des lignes vues par les sous-modèles.

## Dataset Modèle Et Artefact

Le module `modeling/` consomme le dataset d'entraînement sous forme `pandas.DataFrame`.
La colonne cible est obligatoire :

- `target` avec les classes fixes `HOME`, `DRAW`, `AWAY`.

Colonnes explicitement interdites comme features modèle V1 :

- `target`, `home_goals`, `away_goals` ;
- `fixture_id`, `target_fixture_id`, `feature_snapshot_id` ;
- `league_id`, `season`, `home_team_id`, `away_team_id` ;
- tout `*_id` lié à un joueur, coach, venue, bookmaker ou bet ;
- `status`, `status_short`, `status_long` et tout statut post-match équivalent ;
- `fixture_date`, `prediction_time`, `*_date`, `*_time`, `fetched_at`, `created_at`,
  `updated_at` ;
- `*_json` et tout payload brut.

Le modèle V1 ne garde que des colonnes numériques sûres après coercition. Les colonnes
probabilistes déjà construites point-in-time, comme `market_home`, `market_draw`,
`market_away`, `api_pred_home`, `api_pred_draw` et `api_pred_away`, sont autorisées.

Un artefact modèle versionné contient :

- `model_version` ;
- `created_at` ;
- `feature_columns` ;
- configuration d'entraînement et méthode de calibration ;
- métriques train/validation ;
- modèle sérialisé dans `model.joblib` ;
- résumé lisible dans `metadata.json` ;
- liste des colonnes dans `feature_names.json` ;
- métriques détaillées dans `metrics.json`.

Métriques attendues :

- accuracy 1X2 ;
- log loss multiclass ;
- Brier score multiclass ;
- confusion matrix `HOME/DRAW/AWAY` ;
- calibration bins.

## Rapport De Backtest

Le backtest consomme un dataset CSV ou Parquet contenant au minimum :

- `fixture_date` pour le split temporel obligatoire ;
- `target` pour l'évaluation ;
- features numériques point-in-time ;
- metadata optionnelle `league_id` et `season` pour les métriques groupées.

Le split par défaut est chronologique et sans shuffle :

- train : 60% ;
- validation : 20% ;
- test : 20%.

Le rapport JSON expose :

- `periods.train`, `periods.validation`, `periods.test` avec `row_count`, `start`, `end` ;
- `metrics.test` et `metrics.validation` par modèle évalué ;
- `confidence_thresholds` par modèle ;
- `group_metrics` par ligue et saison si les colonnes existent ;
- `comparisons.test` avec deltas entre baselines et modèle final ;
- `leakage.forbidden_columns_in_features`, qui doit rester vide.

Les rapports Markdown reprennent les mêmes informations principales pour lecture humaine.
Les scores finaux et IDs naïfs restent metadata ou target, jamais features modèle.

## Seed Minimal Depuis Les Docs

Depuis `docs/api_football_reference.json`, le seed doit pouvoir charger :

- leagues : `league.id`, `league.name`, pays, saison, coverage ;
- teams : `team_id`, nom, pays, logo, statut national ;
- venues : `venue_id`, nom, ville, capacité, surface ;
- fixtures : `fixture_id`, date, ligue, saison, équipes, statut, score si terminé ;
- standings : rang, points, forme, buts, snapshot/update ;
- bookmakers : `id`, `name` ;
- bets : `id`, `name`, type prematch/live.

Depuis `docs/api_football_players_reference.json`, le seed doit pouvoir charger :

- players : `player_id`, nom, âge, photo ;
- squads : `player_id`, `team_id`, `league_id`, saison, poste, numéro.

## Snapshots API Live

Toute ingestion API-Football live doit créer un `RawApiSnapshot` avec :

- `endpoint` ;
- `params_json` ;
- `payload_json` ;
- `fetched_at` ;
- `status_code` ;
- `source`.

Les snapshots live sont des preuves d'audit et de reproductibilité. Ils ne remplacent pas
les référentiels `docs/*.json`, et les référentiels ne remplacent pas les snapshots
dynamiques nécessaires aux futures features point-in-time.

Pour Sprint 5, les fixtures et standings chargés depuis `docs/api_football_reference.json`
ne créent pas de `RawApiSnapshot` live et portent `payload_json.ingestion_source =
"docs/reference"`. Les fixtures et standings issus d'API-Football live portent la source du
client API et sont toujours accompagnés d'un `RawApiSnapshot`.

Pour Sprint 6, les endpoints détaillés suivants produisent chacun un `RawApiSnapshot` live
quand ils sont appelés :

- `/fixtures/statistics` ;
- `/fixtures/events` ;
- `/fixtures/lineups` ;
- `/fixtures/players` ;
- `/injuries` ;
- `/predictions`.

Une réponse vide ou `204` reste un snapshot utile : elle prouve que l'information n'était
pas disponible au moment de collecte. Les joueurs inconnus rencontrés dans ces payloads ne
sont insérés dans `Player` que si l'API fournit un `player.id`; sinon le payload parent est
conservé sans création d'identité.

Les futurs builders de features doivent filtrer :

- fixtures historiques : `Fixture.date < prediction_time` et `fixture_id` cible exclu ;
- standings : `snapshot_date <= prediction_time` ou `fetched_at <= prediction_time`.
- fixture details, injuries, lineups, player stats et predictions API :
  `fetched_at <= prediction_time`.
- odds prematch : `is_live = false` et `fetched_at <= prediction_time`; prendre le dernier
  snapshot par bookmaker avant de calculer consensus, overround, dispersion et mouvement.

Depuis `docs/api_football_players_cache.json`, aucune entité métier ne doit dépendre
directement du cache. Il sert uniquement à éviter de refaire des appels `/players/squads`
lors d'un workflow de refresh ou de reprise de collecte.

## Qualité Des Données

Chaque prédiction doit indiquer les sources disponibles :

- odds ;
- injuries ;
- lineups officielles ;
- stats joueurs ;
- standings ;
- prédiction API-Football.

Une faible couverture doit réduire la confiance et apparaître dans la sortie.

## Prédiction Fixture Unique

Le pipeline `predict_fixture` prend toujours `fixture_id` et `prediction_time`. Il stocke un
`FeatureSnapshot` puis un `ModelPrediction` lié par `feature_snapshot_id`.

Champs persistés dans `ModelPrediction` :

- `fixture_id`, `prediction_time`, `model_version` ;
- `p_home`, `p_draw`, `p_away`, `predicted_result` / `predicted_outcome` ;
- `confidence_score`, `confidence_label` ;
- `explanation_json`, `data_quality_json` ;
- `payload_json.sources_used`, `payload_json.stacking_weights`, `payload_json.sport_source`.

Sources probabilistes autorisées :

- modèle sportif chargé depuis `model.joblib`, si disponible ;
- Poisson comme fallback sportif ;
- odds prematch déjà filtrées par `fetched_at <= prediction_time` ;
- prédiction API-Football déjà filtrée par `fetched_at <= prediction_time`.

Avec un artefact V2, `ModelPrediction.payload_json.expert_probabilities` peut contenir :

- `market_calibrated` ;
- `poisson_v2` ;
- `elo_v2` ;
- `tabular_v2`.

Ces probabilités sont des diagnostics exploitables pour expliquer la décision finale. Elles
ne remplacent pas `p_home`, `p_draw`, `p_away`, qui restent la sortie officielle.

Sans `--refresh-data`, le pipeline lit seulement la DB locale et les référentiels `docs/`.
Avec `--refresh-data`, les appels live sont explicites et snapshotés avant construction des
features.

## Automatisation Des Prédictions Du Jour

La commande `predict-today` produit un résumé d'exécution sérialisable en JSON. Elle ne
fait aucun appel API implicite : sans `--refresh-data`, les fixtures doivent déjà être en
DB. Avec `--refresh-data`, les fixtures de la date cible sont ingérées par ligue/saison,
puis chaque prédiction réutilise le pipeline fixture unique.

Fenêtres de prédiction, calculées fixture par fixture :

- `early` : `prediction_time = fixture.date - 24h` ;
- `mid` : `prediction_time = fixture.date - 6h` ;
- `late` : `prediction_time = heure courante`, avec sélection des matchs dans les 30
  prochaines minutes ;
- `now` : `prediction_time = heure courante` ;
- `all` : alias de compatibilité pour l'heure courante.

Les fixtures avec coup d'envoi `<= prediction_time` ou un statut commencé/terminé sont
ignorées par défaut. Les IDs de ligue fournis à la CLI doivent être validés contre
`docs/api_football_reference.json` ou venir de `config/competitions.yaml`.

Métadonnées ajoutées dans `ModelPrediction.payload_json` et, si Discord est utilisé, dans
`DiscordMessage.payload_json` :

- `automation_window` ;
- `automation_date` ;
- `prediction_time` ;
- `run_key`.

### Automatisation V3

`predict-today-v3` et `scripts/daily_late.sh` utilisent les mêmes fenêtres, mais écrivent
les sorties modèle dans `V3ModelPrediction` et ne remplissent pas `ModelPrediction`.
`scripts/daily_late.sh` lance la V3 par défaut depuis Sprint 10 avec
`MODEL_DIR=data/models/v3` et `V2_MODEL_DIR=data/models/v2-late`.

Métadonnées ajoutées dans `V3ModelPrediction.payload_json` :

- `model_family="v3"` ;
- `shadow_mode` (`true` par défaut pour les appels manuels, `false` en production) ;
- `daily_window` et `automation_window` ;
- `automation_date` ;
- `prediction_time` ;
- `run_key` ;
- `refresh_warnings`.

Quand un message Discord V3 est créé, `DiscordMessage.model_prediction_id` reste `null`
car la FK pointe vers les prédictions V2. Le lien V3 est porté par
`DiscordMessage.payload_json` :

- `v3_model_prediction_id` pour les prédictions V3 1X2 publiées ;
- `v3_feature_snapshot_id` pour les prédictions V3 1X2 publiées ;
- `ou_model_prediction_id` pour les prédictions O/U 2.5 publiées ;
- `model_family` (`v3` ou `ou25`) ;
- `shadow_mode` pour V3 ;
- `daily_window` / `automation_window` ;
- `automation_date` ;
- `run_key`.

Les prédictions V3 et O/U à confiance insuffisante sont persistées mais ne créent pas de
message Discord réel. Le statut opérationnel est `confidence_skipped` avec la raison
`confidence_below_publish_threshold`; ces lignes ne sont pas éligibles au score public
hebdomadaire.

Les vrais messages `predictions` sont dédupliqués par `fixture_id + window` pour éviter un
second envoi réel V2 ou V3 sur la même fenêtre. `dry_run` et `print_only` ne bloquent
jamais un futur envoi réel. `--force` permet de renvoyer explicitement.
