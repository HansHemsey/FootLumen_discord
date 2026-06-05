# Prompts Par Sprint - Power Rating / Pi-Rating

## Usage

Chaque sprint doit etre execute separement.

Regles generales :
- Les prompts marques **Plan Mode** servent a analyser et produire un plan sans modifier les fichiers.
- Les prompts marques **Agent / Edit** servent a implementer apres validation du plan.
- Ne jamais inventer d'ID API-Football.
- Ne jamais introduire de data leakage.
- Ne jamais lancer d'appel API reel ni d'envoi Discord reel sans confirmation explicite.
- Les features de rating doivent toujours etre point-in-time : uniquement les matchs termines avec `fixture.date < prediction_time`.
- L'integration doit preserver les modeles existants V2, V3 et O/U, avec fallback propre si les nouvelles features sont absentes.

---

## Sprint PR0 - Audit D'Integration Power Rating

### Prompt PR0 - Plan d'integration

Mode : **Plan Mode**

```text
Lis AGENTS.md, blueprint.md, README.md, docs/modeling_strategy.md et docs/data_contract.md.

Travaille en Plan Mode uniquement.
Ne modifie aucun fichier.

Objectif :
Planifier l'integration d'un systeme Power Rating / Pi-Rating point-in-time dans football-predictor.

Analyse :
- src/football_predictor/modeling/elo.py
- src/football_predictor/modeling/v2_model.py
- src/football_predictor/modeling/v2_features.py
- src/football_predictor/modeling/poisson_v2.py
- src/football_predictor/features/feature_builder.py
- src/football_predictor/features/team_features.py
- src/football_predictor/modeling/v3/
- src/football_predictor/ou_model/features/
- src/football_predictor/ou_model/modeling/
- src/football_predictor/backtesting/
- tests/test_modeling_v2.py
- tests/test_v3_stacker_composite.py
- tests/test_ou_daily.py

A verifier :
- comment Elo est calcule chronologiquement ;
- comment les features sont construites sans fuite temporelle ;
- comment V2, V3 et O/U peuvent consommer des features `power_*` ;
- ou ajouter un expert de probabilite `power_rating_v1` sans casser les artefacts existants ;
- comment comparer Power Rating vs Elo, Poisson, odds-only et modele final ;
- quels tests anti-leakage sont necessaires.

Formule cible a valider :
- rating 0-centered, non persistant en DB dans une premiere version ;
- etat par equipe avec composantes :
  - global_rating ;
  - home_rating ;
  - away_rating ;
  - attack_home ;
  - attack_away ;
  - defense_home ;
  - defense_away ;
- prediction pre-match :
  - expected_margin = home_advantage + home.home_rating - away.away_rating ;
  - expected_home_goals = base_home_goals + home.attack_home - away.defense_away + home_goal_advantage ;
  - expected_away_goals = base_away_goals + away.attack_away - home.defense_home ;
  - probabilites 1X2 derivees de expected_margin avec draw prior borne ;
- update chronologique uniquement apres lecture des features pre-match du match termine.

Produis un plan precis avec :
- choix de formule final ;
- nouvelles features exactes ;
- integration V2 ;
- integration V3 ;
- integration O/U ;
- backtests a ajouter ;
- documentation a mettre a jour ;
- risques de regression ;
- criteres d'acceptation.
```

---

## Sprint PR1 - Module Core Power Rating

### Prompt PR1 - Implementation module rating

Mode : **Agent / Edit**

```text
Implemente le module core Power Rating / Pi-style rating valide au Sprint PR0.

Contraintes :
- respecte AGENTS.md et blueprint.md ;
- aucune migration DB ;
- aucun appel API reel ;
- aucune fuite de donnees ;
- aucun changement de comportement Discord ;
- ne remplace pas Elo, ajoute une source complementaire.

A creer :
- src/football_predictor/modeling/power_rating.py

Interface attendue :
- PowerRatingConfig
- TeamPowerRating
- PowerRatingState
- add_power_rating_features_to_dataset(frame, config=None)
- power_rating_features_for_row(row, state)
- power_rating_probability_from_features(row)

Formule attendue :
- etat initial 0-centered ;
- `base_home_goals=1.35`, `base_away_goals=1.10` ;
- `home_advantage_margin=0.25` ;
- `home_goal_advantage=0.10` ;
- `k_margin=0.08` ;
- `k_goals=0.04` ;
- `margin_scale=1.15` ;
- `draw_base=0.29` ;
- `draw_slope=0.06` ;
- borner les lambdas de buts entre `0.2` et `3.8` ;
- borner les probabilites pour toujours sommer a 1.

Regle anti-leakage :
- pour chaque ligne du dataset, ecrire les features avant de mettre a jour l'etat avec le resultat du match ;
- ne jamais utiliser `home_goals`, `away_goals` ou `target` dans les features de la ligne courante ;
- mise a jour seulement si `target in HOME/DRAW/AWAY` et scores finaux disponibles.

Features a produire :
- power_home_global_rating
- power_away_global_rating
- power_home_home_rating
- power_away_away_rating
- power_rating_diff
- power_expected_margin
- power_expected_home_goals
- power_expected_away_goals
- power_total_expected_goals
- power_home_win_expectation
- p_power_home
- p_power_draw
- p_power_away

Tests a ajouter :
- calcul initial neutre sans historique ;
- update chronologique modifie seulement les lignes suivantes ;
- aucune ligne ne lit son propre resultat ;
- probabilites normalisees ;
- ratings domicile/exterieur evoluent separement ;
- valeurs bornees meme sur scores extremes ;
- dataset desordonne trie par `fixture_date`.

A la fin :
- lance les tests cibles du module ;
- lance ruff sur les fichiers modifies ;
- relis le diff en cherchant data leakage et compatibilite.
```

---

## Sprint PR2 - Integration Features Et Dataset

### Prompt PR2 - Ajout des features power dans les datasets

Mode : **Agent / Edit**

```text
Integre les features Power Rating dans les datasets d'entrainement et de backtest.

Contraintes :
- aucune migration DB ;
- aucun appel API reel ;
- aucune modification des fixtures ou donnees sources ;
- ne casse pas les datasets existants si les colonnes `power_*` sont absentes.

A faire :
- integrer `add_power_rating_features_to_dataset()` dans les chemins dataset/backtest chronologiques existants ;
- ajouter les colonnes `power_*` aux datasets V2/V3/O-U quand `fixture_date`, `home_team_id`, `away_team_id`, `target`, `home_goals`, `away_goals` sont disponibles ;
- si scores absents ou match non termine, produire les features pre-match sans update ;
- ajouter `power_` et `p_power_` aux selecteurs de features autorisees ;
- conserver les colonnes cibles interdites dans les filtres anti-leakage.

A verifier :
- V2 accepte les features `power_*` dans `select_v2_feature_names`;
- V3 Draw Risk / No-Draw Winner peuvent selectionner `power_*` sans lire de target ;
- O/U peut selectionner `power_expected_home_goals`, `power_expected_away_goals`, `power_total_expected_goals`, `power_rating_diff`.

Tests a ajouter :
- dataset avec 3 matchs chronologiques : le match 2 utilise seulement le match 1 ;
- fixture cible exclue ;
- `power_*` absent ne casse pas les anciens modeles ;
- `power_*` present est selectionnable par V2 ;
- V3 forbidden patterns excluent toujours `target`, `home_goals`, `away_goals`;
- O/U forbidden patterns excluent toujours les champs de resultat.

A la fin :
- lance les tests dataset/features concernes ;
- lance ruff sur les fichiers modifies.
```

---

## Sprint PR3 - Integration V2 Comme Expert De Probabilite

### Prompt PR3 - Ajouter Power Rating a V2

Mode : **Agent / Edit**

```text
Ajoute Power Rating comme source experte dans le modele V2 composite.

Contraintes :
- ne supprime pas Elo ;
- ne change pas les sorties publiques Discord ;
- les anciens artefacts V2 doivent rester chargeables ;
- si `power_*` manque, fallback silencieux sans crash.

A faire :
- ajouter `power_rating_v1` dans les expert probabilities V2 ;
- `power_rating_v1` doit utiliser `p_power_home`, `p_power_draw`, `p_power_away` si presents ;
- sinon reconstruire les probabilites depuis `power_expected_margin` si possible ;
- sinon ne pas fournir l'expert ;
- ajouter `power_rating_v1` a `meta_sources` pour les nouveaux modeles ;
- ajuster les poids fallback de maniere conservatrice :
  - market_calibrated: 0.32
  - poisson_v2: 0.22
  - elo_v2: 0.14
  - power_rating_v1: 0.14
  - tabular_v2: 0.18
- documenter dans metadata les sources disponibles.

Tests a ajouter :
- V2 expert probabilities contient `power_rating_v1` quand les features existent ;
- V2 fonctionne sans `power_*` ;
- anciens modeles sans source power restent compatibles ;
- fallback weighted blend somme a 1 ;
- le meta-model peut s'entrainer avec la nouvelle source ;
- backtest V2 expose une metrique separee pour `power_rating_v1`.

A la fin :
- lance tests V2/modeling/backtesting cibles ;
- lance ruff ;
- relis le diff pour compatibilite artefacts.
```

---

## Sprint PR4 - Integration V3 Et O/U

### Prompt PR4 - Ajouter Power Rating a V3 et O/U

Mode : **Agent / Edit**

```text
Integre les signaux Power Rating dans V3 et O/U sans casser les artefacts existants.

Contraintes :
- aucun changement de format Discord obligatoire ;
- les modeles V3 existants doivent encore charger ;
- les modeles O/U existants doivent encore charger ;
- si les features `power_*` sont absentes, utiliser fallback neutre.

V3 :
- ajouter `p_power_home`, `p_power_draw`, `p_power_away`, `power_rating_diff`, `power_expected_margin`, `power_total_expected_goals` aux inputs disponibles du stacker pour les nouveaux entrainements ;
- ajouter `has_power_signal` dans le frame stacker ;
- ne pas modifier le comportement des artefacts V3 deja entraines ;
- ajouter des features derivees a Draw Risk :
  - power_parity_score = 1 / (1 + abs(power_expected_margin))
  - power_low_total_goals_score = 1 / (1 + power_total_expected_goals)
- ajouter des features derivees a No-Draw Winner :
  - ndw_power_rating_edge = power_rating_diff
  - ndw_power_expected_margin = power_expected_margin

O/U :
- ajouter aux features O/U :
  - power_expected_home_goals
  - power_expected_away_goals
  - power_total_expected_goals
  - power_rating_diff
- ajouter ces features aux listes candidates O/U si elles passent la couverture ;
- ne pas forcer leur presence dans le modele logistique si elles sont absentes.

Tests a ajouter :
- V3 stacker feature frame inclut `has_power_signal`;
- V3 stacker ancien artefact avec ancienne feature list reste compatible ;
- Draw Risk produit les features power derivees sans DB supplementaire ;
- No-Draw Winner produit les edges power sans leakage ;
- O/U feature snapshot contient les features power si base features les expose ;
- O/U training fonctionne avec et sans features power.

A la fin :
- lance tests V3/O-U cibles ;
- lance ruff ;
- relis le diff comme reviewer senior.
```

---

## Sprint PR5 - Backtesting Et Comparaison De Performance

### Prompt PR5A - Plan backtesting power rating

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.
Ne modifie aucun fichier.

Objectif :
Planifier les rapports de backtesting necessaires pour valider l'apport de Power Rating / Pi-style rating.

Analyse :
- src/football_predictor/backtesting/
- src/football_predictor/backtesting/v3_evaluator.py
- src/football_predictor/ou_model/backtesting/
- src/football_predictor/modeling/v2_model.py
- src/football_predictor/modeling/power_rating.py si present

Le rapport doit comparer :
- odds_only ;
- poisson ;
- elo_v2 ;
- power_rating_v1 ;
- tabular_v2 ;
- V2 final ;
- V3 final ;
- O/U final ;
- O/U market baseline.

Metriques :
- accuracy 1X2 ;
- log loss ;
- Brier ;
- calibration bins ;
- performance par ligue ;
- performance par saison ;
- performance par confidence label ;
- performance par presence/absence de signal power ;
- O/U log loss, Brier, win rate, ROI si odds disponibles.

A verifier :
- les ratings sont calcules uniquement sur les matchs anterieurs ;
- les metriques Power Rating sont evaluees sur le meme split que les autres baselines ;
- aucun resultat de test ne sert a entrainer ou calibrer.

Produis un plan precis :
- changements de rapports ;
- JSON/Markdown attendus ;
- tests a ajouter ;
- criteres pour conserver ou desactiver Power Rating en production.
```

### Prompt PR5B - Implementation rapports backtesting

Mode : **Agent / Edit**

```text
Implemente les rapports de backtesting Power Rating valides au Sprint PR5A.

Contraintes :
- aucun appel API reel ;
- aucun envoi Discord ;
- aucun dataset modifie manuellement ;
- rapports ecrits localement uniquement.

A faire :
- ajouter `power_rating_v1` comme baseline explicite dans les backtests V2/V3 ;
- ajouter les metriques groupees par ligue, saison, confidence label et presence `has_power_signal`;
- ajouter les metriques O/U quand les features power sont presentes ;
- produire JSON et Markdown ;
- ajouter un resume clair :
  - power vs elo ;
  - power vs poisson ;
  - power contribution au modele final ;
  - cas ou power degrade les performances.

Tests a ajouter :
- rapport contient `power_rating_v1`;
- les metriques power utilisent le meme test fold que les autres modeles ;
- pas de leakage sur un dataset synthetique desordonne ;
- rapport Markdown mentionne power rating ;
- si les colonnes power manquent, le rapport reste valide avec `coverage=0`.

A la fin :
- lance tests backtesting cibles ;
- lance ruff.
```

---

## Sprint PR6 - Explications, Documentation Et Rollout

### Prompt PR6 - Documentation et rollout sans casse

Mode : **Agent / Edit**

```text
Documente et prepare le rollout de Power Rating / Pi-style rating.

Contraintes :
- ne pas changer le comportement de publication Discord ;
- ne pas imposer Power Rating comme gate de publication ;
- ne pas inventer de nouvelle source de donnees externe ;
- ne pas ajouter de secret ni de variable sensible.

A faire :
- mettre a jour docs/modeling_strategy.md :
  - objectif Power Rating ;
  - difference avec Elo ;
  - formule ;
  - regles point-in-time ;
  - usage V2/V3/O-U ;
- mettre a jour docs/data_contract.md :
  - colonnes `power_*` ;
  - probabilites `p_power_*` ;
  - champs interdits ;
- mettre a jour README.md :
  - commandes de backtest recommandees ;
  - interpretation du rapport ;
- ajouter dans les explications internes, si deja disponibles :
  - avantage rating structurel ;
  - expected margin ;
  - total goals attendu ;
- garder le format Discord public stable, sauf si un formatter existant a deja une section facteurs cles qui peut mentionner Power Rating sans allonger excessivement le message.

Tests a ajouter :
- docs ne mentionnent pas de source externe reellement integree si elle ne l'est pas ;
- les nouveaux champs sont documentes ;
- aucun secret dans docs/configs ;
- formatter ne casse pas avec ou sans power features.

A la fin :
- lance tests docs/formatters cibles ;
- lance ruff si code modifie ;
- relis README/docs pour contradictions.
```

---

## Sprint PR7 - Validation Production Locale

### Prompt PR7 - Smoke test et decision production

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.
Ne modifie aucun fichier.

Objectif :
Definir la validation finale avant activation production de Power Rating.

Analyse les resultats des sprints PR1 a PR6.

Verifie :
- tests unitaires core rating ;
- tests anti-leakage ;
- backtests V2/V3/O-U ;
- compatibilite anciens artefacts ;
- absence de migration DB ;
- absence de changement Discord risque ;
- documentation a jour.

Propose :
- checklist de production ;
- commandes de smoke test local ;
- criteres de rollback ;
- criteres de conservation du signal Power Rating ;
- strategie si Power Rating ameliore V2 mais degrade V3 ou O/U.

Regle de decision recommandee :
- activer les features Power Rating dans les datasets et modeles seulement si :
  - log loss V2 final ne se degrade pas ;
  - Brier V2 final ne se degrade pas ;
  - `power_rating_v1` bat Elo ou apporte une complementarite mesurable sur au moins une ligue majeure ;
  - V3/O-U ne regressent pas sur le test fold global ;
  - aucun test anti-leakage ne signale de fuite.

Ne modifie aucun fichier.
```

---

## Ordre Recommande

1. PR0 - Plan d'integration.
2. PR1 - Module core Power Rating.
3. PR2 - Features et datasets.
4. PR3 - Integration V2.
5. PR4 - Integration V3 et O/U.
6. PR5A - Plan backtesting.
7. PR5B - Rapports backtesting.
8. PR6 - Documentation et rollout.
9. PR7 - Validation production.

---

## Recapitulatif Des Modes

| Sprint | Prompt | Mode |
|---|---|---|
| PR0 | Plan d'integration | **Plan Mode** |
| PR1 | Module core Power Rating | **Agent / Edit** |
| PR2 | Features et datasets | **Agent / Edit** |
| PR3 | Integration V2 | **Agent / Edit** |
| PR4 | Integration V3 et O/U | **Agent / Edit** |
| PR5A | Plan backtesting | **Plan Mode** |
| PR5B | Rapports backtesting | **Agent / Edit** |
| PR6 | Documentation et rollout | **Agent / Edit** |
| PR7 | Validation production | **Plan Mode** |
