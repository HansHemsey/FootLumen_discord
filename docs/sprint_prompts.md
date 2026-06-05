# Prompts par sprint - Amelioration football-predictor

Ce document regroupe les prompts a executer sprint par sprint pour corriger et ameliorer l'outil selon l'audit projet.

## Usage

Chaque sprint doit etre execute separement.

Regles :
- Les prompts marques **Plan Mode** servent a analyser et produire un plan sans modifier les fichiers.
- Les prompts marques **Agent / Edit** servent a implementer apres validation du plan.
- Ne jamais lancer d'appel API reel ni d'envoi Discord reel sans confirmation explicite.
- Toujours respecter `AGENTS.md`, `blueprint.md` et les regles anti data leakage.
- Pour les prompts d'implementation, ajouter ou mettre a jour les tests pertinents, puis lancer les tests cibles et `ruff` si possible.

---

## Sprint A - Corrections critiques

### Prompt A1 - Plan de correction publication critique

Mode : **Plan Mode**

```text
Lis AGENTS.md, blueprint.md, README.md, docs/architecture.md, docs/modeling_strategy.md, docs/data_contract.md et docs/operations_guide.md.

Travaille en Plan Mode uniquement.

Objectif :
Planifier les corrections critiques de publication :
- centraliser la policy de publication ;
- imposer High / Very High uniquement ;
- ajouter un gate data_quality minimal ;
- appliquer la meme policy a V3, O/U, V2 rollback et predict-v3 --send-discord ;
- enregistrer une raison normalisee de non-publication ;
- empecher toute publication Discord faible ou insuffisamment fiable.

Ne modifie aucun fichier.
Ne lance aucun envoi Discord.
Ne lance aucun appel API reel.

Analyse les fichiers :
- src/football_predictor/prediction/publication_policy.py
- src/football_predictor/prediction/run_daily.py
- src/football_predictor/prediction/v3_service.py
- src/football_predictor/ou_model/prediction/
- src/football_predictor/cli.py
- src/football_predictor/discord/

Produis un plan precis avec :
- changements par module ;
- regles de publication finales ;
- tests a ajouter ;
- risques de regression ;
- criteres d'acceptation.
```

### Prompt A2 - Implementation publication critique

Mode : **Agent / Edit**

```text
Implemente le plan valide du Sprint A1.

Contraintes :
- respecte AGENTS.md et blueprint.md ;
- aucune fuite de donnees ;
- aucun secret logge ;
- aucune publication Discord reelle ;
- aucun appel API reel dans les tests.

A faire :
- centraliser la policy de publication ;
- ajouter data_quality comme gate obligatoire ;
- appliquer la policy a V3, O/U, V2 rollback et predict-v3 --send-discord ;
- stocker une non_publication_reason explicite ;
- ajouter ou mettre a jour les tests.

A la fin :
- lance pytest sur les tests concernes ;
- lance ruff check sur les fichiers modifies si possible ;
- relis le diff comme reviewer senior.
```

### Prompt A3 - Correction daily_ou.sh

Mode : **Agent / Edit**

```text
Corrige scripts/daily_ou.sh pour que tout echec du runner O/U remonte correctement au cron.

Objectif :
- eviter qu'un echec soit masque par tee ;
- conserver le resume JSON ;
- conserver les logs lisibles ;
- ne pas changer le comportement metier ;
- ne lancer aucun appel API reel.

Ajoute un test script/smoke si l'architecture de tests le permet.

A la fin :
- lance les tests concernes ;
- verifie que le script echoue si la commande O/U echoue.
```

---

## Sprint B - Data quality et anti-leakage

### Prompt B1 - Plan data quality

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Objectif :
Planifier un systeme data quality robuste pour empecher les publications insuffisamment fiables.

Analyse :
- src/football_predictor/features/data_quality.py
- src/football_predictor/utils/diagnostics.py
- src/football_predictor/features/feature_builder.py
- src/football_predictor/features/odds_features.py
- src/football_predictor/features/lineup_m30_features.py
- src/football_predictor/ou_model/features/
- docs/data_contract.md

Propose :
- nouveaux flags de fraicheur ;
- seuils par source ;
- score global ;
- rapport quotidien/hebdomadaire ;
- integration avec la publication Discord ;
- tests anti data leakage a ajouter.

Ne modifie aucun fichier.
```

### Prompt B2 - Implementation data quality

Mode : **Agent / Edit**

```text
Implemente le plan valide du Sprint B1.

A faire :
- ajouter les flags de fraicheur necessaires ;
- integrer un min_data_quality_score dans la publication ;
- generer un rapport data quality local Markdown/JSON ;
- ajouter les tests unitaires ;
- mettre a jour docs/data_contract.md si le contrat change.

Contraintes :
- aucune donnee future ;
- odds fetched_at <= prediction_time ;
- injuries fetched_at <= prediction_time ;
- lineups fetched_at <= prediction_time ;
- standings snapshot_date/fetched_at <= prediction_time ;
- fixture cible exclue des historiques.
```

### Prompt B3 - Audit anti-leakage cible features

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Audite specifiquement les risques de data leakage dans :
- team features ;
- player features ;
- XI features ;
- absences ;
- odds ;
- draw risk ;
- no-draw winner ;
- O/U 2.5 ;
- standings ;
- pseudo-xG.

Pour chaque source, indique :
- si prediction_time est respecte ;
- si la fixture cible est exclue ;
- si un test existe ;
- quel test ajouter si absent.

Ne modifie aucun fichier.
```

---

## Sprint C - Calibration et seuils

### Prompt C1 - Plan calibration

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Objectif :
Planifier une calibration robuste des seuils High / Very High pour V3 1X2 et O/U 2.5.

Analyse :
- src/football_predictor/prediction/confidence.py
- src/football_predictor/prediction/publication_policy.py
- src/football_predictor/backtesting/
- src/football_predictor/modeling/v3/
- src/football_predictor/ou_model/backtesting/
- docs/modeling_strategy.md

Propose :
- metriques par confidence label ;
- seuils separes V3 et O/U ;
- seuils par ligue si pertinent ;
- rapport published-only ;
- regles d'ajustement periodique ;
- criteres pour autoriser un modele en production.

Ne modifie aucun fichier.
```

### Prompt C2 - Implementation rapports published-only

Mode : **Agent / Edit**

```text
Implemente les rapports backtesting published-only valides au Sprint C1.

A faire :
- appliquer exactement la meme policy que la production ;
- separer predictions internes et publiees ;
- produire metriques par modele, ligue, saison, confidence label et data quality ;
- comparer V3 vs V2 vs odds-only ;
- comparer O/U vs market baseline ;
- generer Markdown et JSON.

Ajoute les tests necessaires.
Ne lance aucun appel API reel.
```

### Prompt C3 - Gate modele approuve production

Mode : **Agent / Edit**

```text
Ajoute un mecanisme empechant l'activation production d'un modele V3 ou O/U sans artefact d'approbation backtest.

Objectif :
- refuser production-mode si le modele n'a pas de rapport valide ;
- permettre shadow mode sans approbation ;
- logguer une erreur claire sans secret ;
- documenter le workflow.

Ajoute tests :
- production refusee sans approbation ;
- shadow mode autorise ;
- production autorisee avec artefact valide.
```

---

## Sprint D - Discord et publication

### Prompt D1 - Plan Discord

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Objectif :
Planifier la fiabilisation Discord.

Analyse :
- src/football_predictor/discord/
- src/football_predictor/prediction/run_daily.py
- src/football_predictor/ou_model/prediction/
- config/discord_channels.example.yaml
- config/discord_webhooks.example.yaml
- docs/operations_guide.md

Verifie :
- routage par championnat ;
- routing score-pronos-semaine ;
- deduplication ;
- dry-run ;
- print-only ;
- shadow mode ;
- taille max messages ;
- secrets masques ;
- published vs non-published.

Propose un plan pour :
- ajouter FKs V3/O-U si necessaire ;
- empecher doublons O/U ;
- completer les exemples de config ;
- renforcer tests Discord.
```

### Prompt D2 - Implementation deduplication O/U

Mode : **Agent / Edit**

```text
Implemente une deduplication O/U par fixture_id, window, model_version et message_type.

Contraintes :
- ne pas casser la deduplication existante par hash ;
- ne pas compter les dry-run/print-only comme publications ;
- ne pas modifier les predictions internes ;
- ajouter tests weekly score et duplicate O/U.

A la fin :
- lance les tests Discord/O-U concernes ;
- verifie qu'une prediction O/U deja envoyee n'est pas renvoyee.
```

### Prompt D3 - Score-pronos-semaine audit

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Audite uniquement score-pronos-semaine.

Verifie :
- seules les predictions Discord reellement envoyees sont comptees ;
- dry-run et print-only exclus ;
- predictions internes exclues ;
- V3 et O/U geres correctement ;
- fixtures non terminees exclues ou marquees pending ;
- cas de suppression/modification Discord ;
- tracabilite par model_family.

Propose les corrections et tests necessaires.
Ne modifie aucun fichier.
```

---

## Sprint E - Backtesting

### Prompt E1 - Plan backtesting production-like

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Objectif :
Planifier un backtest qui reflete vraiment la production M-30.

Analyse :
- src/football_predictor/backtesting/
- src/football_predictor/modeling/v3/
- src/football_predictor/ou_model/backtesting/
- src/football_predictor/prediction/scheduler.py
- src/football_predictor/features/

Le backtest doit :
- simuler prediction_time ;
- utiliser uniquement donnees disponibles avant prediction_time ;
- simuler la policy de publication reelle ;
- produire metriques internes et publiees ;
- mesurer performance par ligue, saison, data quality, confidence label ;
- comparer V3, V2, odds-only, API, Poisson et O/U market.

Ne modifie aucun fichier.
```

### Prompt E2 - Implementation backtest production-like

Mode : **Agent / Edit**

```text
Implemente le backtest production-like valide au Sprint E1.

Contraintes :
- aucun appel API reel ;
- aucune donnee future ;
- fixture cible exclue ;
- policy publication identique a production ;
- rapports Markdown et JSON.

Ajoute tests :
- published-only exclut Low/Medium/Uncertain ;
- data_quality gate applique ;
- M-30 respecte prediction_time ;
- odds apres prediction_time ignorees.
```

---

## Sprint F - Ops VPS

### Prompt F1 - Plan VPS

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Objectif :
Auditer et planifier l'exploitation VPS Linux.

Analyse :
- scripts/
- config/prod.crontab
- docs/operations_guide.md
- README.md

Verifie :
- cron ;
- locks ;
- logs ;
- logrotate ;
- backups ;
- restart VPS ;
- shadow mode ;
- rollback ;
- diagnostics ;
- risque double publication ;
- chemins absolus ;
- dependances shell Linux.

Propose :
- crontab Linux ou systemd timers ;
- flock ;
- backup SQLite ;
- logrotate ;
- healthcheck ;
- smoke test no-network ;
- guide de rollback.
```

### Prompt F2 - Implementation ops VPS

Mode : **Agent / Edit**

```text
Implemente le plan VPS valide.

A faire :
- fournir une config cron Linux ou systemd timer ;
- remplacer les dependances macOS non portables ;
- ajouter lock robuste avec flock ;
- ajouter scripts backup/healthcheck si valides ;
- ajouter logrotate ou documentation equivalente ;
- mettre a jour docs/operations_guide.md.

Ne lance aucun appel API reel.
Ne lance aucun envoi Discord reel.
```

### Prompt F3 - Smoke test local sans reseau

Mode : **Agent / Edit**

```text
Ajoute un smoke test local sans reseau.

Objectif :
- verifier import CLI ;
- verifier chargement config ;
- verifier DB init sur SQLite temporaire ;
- verifier policy publication ;
- verifier formatting Discord sans envoyer ;
- verifier qu'aucun appel reseau n'est fait.

Le smoke test doit etre documente et rapide.
```

---

## Sprint G - Documentation et maintenabilite

### Prompt G1 - Plan documentation

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Objectif :
Planifier la mise a jour documentaire complete.

Analyse :
- README.md
- blueprint.md
- docs/product_spec.md
- docs/architecture.md
- docs/modeling_strategy.md
- docs/data_contract.md
- docs/operations_guide.md
- docs/developer_guide.md
- docs/v3_plan.md
- config/*.example.yaml
- .env.example

Cherche :
- commandes obsoletes ;
- incoherences V2/V3/O-U ;
- M-30 vs fenetre late ;
- seuils de publication ;
- workflow score-pronos-semaine ;
- variables d'environnement manquantes ;
- guide rollback manquant ;
- guide exploitation quotidien manquant.

Ne modifie aucun fichier.
Produis un plan exact de mise a jour.
```

### Prompt G2 - Implementation documentation

Mode : **Agent / Edit**

```text
Implemente les mises a jour documentaires validees au Sprint G1.

Contraintes :
- ne pas inventer d'ID API-Football ;
- ne pas ajouter de secret ;
- garder les exemples webhook avec placeholders vides ;
- documenter clairement shadow mode, dry-run, production-mode ;
- documenter la policy High/Very High + data quality ;
- documenter le score-pronos-semaine.

A la fin :
- relis les docs pour detecter les contradictions ;
- verifie .env.example et configs example.
```

---

## Sprint H - Refactoring maintenable

### Prompt H1 - Plan refactoring runners

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Objectif :
Planifier un refactoring leger pour reduire la duplication entre V2, V3 et O/U.

Analyse :
- src/football_predictor/prediction/run_daily.py
- src/football_predictor/prediction/v3_service.py
- src/football_predictor/ou_model/prediction/
- src/football_predictor/discord/service.py

Propose une interface commune pour :
- candidate prediction ;
- stored prediction ;
- publication decision ;
- delivery result ;
- non_publication_reason ;
- model_family.

Ne modifie aucun fichier.
Le plan doit minimiser les risques de regression.
```

### Prompt H2 - Implementation refactoring minimal

Mode : **Agent / Edit**

```text
Implemente uniquement le refactoring minimal valide au Sprint H1.

Contraintes :
- comportement metier inchange ;
- tests existants doivent continuer a passer ;
- eviter les gros renommages ;
- preserver V2, V3 et O/U.

Ajoute tests de non-regression sur :
- V3 late publication ;
- O/U late publication ;
- V2 rollback ;
- dry-run ;
- shadow mode ;
- score hebdo.
```

---

## Sprint I - Securite

### Prompt I1 - Audit securite lecture seule

Mode : **Plan Mode**

```text
Travaille en Plan Mode uniquement.

Objectif :
Auditer securite et secrets.

Analyse :
- .gitignore
- .env.example
- config/*.example.yaml
- src/football_predictor/utils/
- src/football_predictor/discord/
- tests lies aux secrets
- scripts/

Verifie :
- aucun secret suivi par git ;
- webhook jamais loggue ;
- API key jamais logguee ;
- DB ne stocke pas d'URL webhook ;
- logs surs ;
- exemples propres ;
- permissions recommandees.

Ne lis pas .env reel.
Ne lis pas config locale contenant des webhooks reels.
Ne modifie aucun fichier.
```

### Prompt I2 - Renforcement securite

Mode : **Agent / Edit**

```text
Implemente les renforcements securite valides au Sprint I1.

A faire selon plan :
- ajouter tests anti-secret ;
- ajouter masquage central si necessaire ;
- empecher persistance de contenu Discord contenant webhook/token ;
- ameliorer docs securite ;
- verifier .gitignore et exemples.

Ne lis pas .env reel.
Ne commite aucun secret.
```

---

## Ordre recommande

1. Sprint A
2. Sprint B
3. Sprint C
4. Sprint D
5. Sprint E
6. Sprint F
7. Sprint G
8. Sprint I
9. Sprint H

Sprint H doit venir apres stabilisation des comportements critiques, car il touche la maintenabilite et peut creer des regressions si lance trop tot.
