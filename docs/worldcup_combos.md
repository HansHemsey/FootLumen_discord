# Combinés CDM 2026

## Objectif

Cette feature prépare un socle indépendant pour de futurs tickets combinés Coupe du Monde
2026.

Le sprint 1 ajoute la configuration, les objets métier et la persistance.
Le sprint 2 ajoute la lecture des fixtures CDM 2026, la création de sessions horaires et
la sélection de legs candidats à partir des prédictions déjà persistées.
Le sprint 3 ajoute la construction de tickets candidats, le scoring combiné, les pénalités
de risque et la décision `PUBLIC_PUBLISHED` / `STAFF_ONLY` / `NO_BET`.
Le sprint 4 ajoute refresh policy, revalidation pre-lock, lock final, formatage Discord,
publication contrôlée et settlement.
Le passage production ajoute une orchestration contrôlée `generate -> lock -> publish -> settle`
sans activer de cron par défaut.
Le sprint pre-lock public-ready relit les sources dynamiques juste avant lock et peut
remplacer ou annuler un ticket si les données se dégradent.
Le sprint public routing rend les tickets lisibles côté Discord, prépare le channel public
`combines`, mais conserve `staff_only_shadow_mode: true` par défaut.

La feature ne modifie pas les prédictions 1X2, V3 ou O/U existantes.

## Feature Flag

La configuration dédiée est `config/worldcup_combos.yaml`.

Par défaut :

```yaml
enabled: false
```

Le chemin peut être surchargé avec :

```env
WORLD_CUP_COMBOS_CONFIG_PATH=config/worldcup_combos.yaml
WORLD_CUP_COMBOS_ENABLED=false
```

Champs de publication Discord :

```yaml
staff_channel_key: predictions_staff
public_channel_key: combines
mirror_public_to_staff: true
publish_no_bet_public: false
staff_only_shadow_mode: true
snapshot_duplicate_throttle_minutes: 30
```

Avec `staff_only_shadow_mode: true`, tout ticket est envoyé en staff, même s'il est
techniquement publiable. Pour autoriser une publication publique contrôlée, il faut :

1. créer et valider la route Discord CDM `combines` côté secrets VPS ;
2. lancer les commandes en dry-run ;
3. vérifier l'idempotence dans `discord_messages` ;
4. passer seulement ensuite `staff_only_shadow_mode: false`.

`mirror_public_to_staff: true` envoie une copie staff lorsqu'un ticket part en public.
`publish_no_bet_public: false` garde les no bet en staff.

## Tables Ajoutées

- `combo_tickets`
- `combo_ticket_legs`
- `combo_ticket_snapshots`

Les tables contiennent `created_at`, `updated_at`, `model_versions_json` et `warnings_json`.
Les snapshots JSON sont conservés pour permettre l'audit sans multiplier les migrations.

## Sprint 2

Services ajoutés :

- `worldcup_combo_sessions.py` : groupe les fixtures CDM 2026 par date Europe/Paris et
  fenêtres horaires.
- `adapters.py` : lit les fixtures, prédictions 1X2, décisions O/U V2, odds et lineups
  déjà stockées. Les legs O/U ne sont exposés que si la prédiction est explicitement
  `ou_decision_version="ou_v2"`, possède un `value_side` clair et porte une décision de
  publication O/U publique ; une sortie legacy ou staff-only est ignorée.
- `worldcup_combo_leg_selector.py` : filtre les legs candidats selon EV, edge, qualité
  data, confiance, statut fixture et fraîcheur.
- `scripts/dry_run_worldcup_combo_candidates.py` : affiche sessions, candidats et raisons
  d'exclusion sans écrire en DB.

Règles point-in-time et anti time-travel :

- `lock_time` est uniquement l'heure prévue de verrouillage du ticket ;
- `effective_cutoff_time = min(now, lock_time)` est l'heure maximale réellement autorisée
  pour lire les snapshots dynamiques ;
- prédictions avec `prediction_time <= effective_cutoff_time` uniquement ;
- odds avec `fetched_at <= effective_cutoff_time` uniquement ;
- lineups avec `fetched_at <= effective_cutoff_time` uniquement ;
- toute source dynamique ajoutée ensuite, par exemple injuries ou prédictions API,
  doit utiliser le même cutoff effectif.

Exemple : si le job tourne à `09:00` et que le lock est prévu à `18:40`, le système
ne peut lire que des snapshots disponibles à `09:00` ou avant. Il ne doit jamais
"voir" les odds, lineups ou prédictions qui seront collectées plus tard dans la journée.
Les sorties dry-run et les payloads tickets exposent `generated_at`, `lock_time` et
`data_cutoff_time` pour auditer cette règle.

## Sprint 3

Services ajoutés :

- `worldcup_combo_builder.py` : construit au plus un ticket 2 legs safe et un ticket
  3 legs staff-only par session.
- `worldcup_combo_scoring.py` : calcule cotes combinées, probabilités, EV brute/ajustée,
  risques, fraîcheur et confiance combinée.
- `worldcup_combo_publication_policy.py` : applique la policy public/staff/no-bet sans
  envoyer de message Discord.
- `scripts/dry_run_worldcup_combo_builder.py` : affiche les meilleurs tickets par session
  sans écrire en DB ni publier.

Les snapshots de cycle supportés sont :

- `generated`
- `scored`
- `policy_decided`
- `pre_lock`
- `settled`

## Sprint 4

Services ajoutés :

- `worldcup_combo_refresh_policy.py` : décide si odds, prédictions ou lineups sont trop
  anciennes selon la proximité du kickoff.
- `worldcup_combo_lock_service.py` : revalide un ticket avant lock, recalcule scoring/policy,
  crée le snapshot `pre_lock`, puis passe `LOCKED`, `STAFF_ONLY` ou `NO_BET`.
- `worldcup_combo_formatter.py` : formate watchlist staff, ticket verrouillé public lisible
  et no bet.
- `worldcup_combo_publication_service.py` : route staff/public selon la config, avec
  idempotence par ticket, statut, channel et type de message.
- `worldcup_combo_settlement.py` : calcule `WON`, `LOST`, `VOID`, `PARTIAL_VOID` et
  `profit_unit` après résultats.

Cycle opérationnel :

- `DRAFT` : ticket généré à partir des snapshots disponibles à `generated_at` ;
- `WATCHLIST_STAFF` : ticket observé côté staff, sans promesse de publication ;
- `PRE_LOCK_REVALIDATION` : relecture des fixtures, prédictions, odds et lineups avec
  `effective_cutoff_time = min(now, lock_time)` ;
- `LOCKED` : ticket verrouillé seulement si la policy reste publiable après revalidation ;
- `STAFF_ONLY` : ticket intéressant mais trop risqué pour public ;
- `NO_BET` : ticket annulé avant publication ;
- `SETTLED` : résultat calculé après matchs terminés.

Revalidation pre-lock :

- chaque leg d'origine est reconstruit depuis les sources point-in-time les plus récentes ;
- si EV, edge, odds, data quality ou market scope se dégradent, le leg est retiré ;
- un remplaçant propre peut être utilisé s'il respecte les seuils et ne crée pas de
  conflit de fixture ;
- sans au moins deux legs propres, le ticket passe `NO_BET` ;
- un risque lineups élevé force `STAFF_ONLY`, même si l'EV reste correcte.

Snapshots pre-lock :

- `pre_lock_revalidated` : ticket relu et rescored ;
- `pre_lock_replaced_leg` : au moins un leg a été remplacé ;
- `pre_lock_no_bet` : ticket annulé avant lock.

Règles staff/public/no bet :

- `staff_only_shadow_mode: true` force toutes les publications vers `predictions_staff` ;
- `staff_only_shadow_mode: false` permet `PUBLIC_PUBLISHED` vers `public_channel_key` ;
- `STAFF_ONLY` reste toujours dans `staff_channel_key` ;
- `NO_BET` reste dans `staff_channel_key` sauf `publish_no_bet_public: true` ;
- `mirror_public_to_staff: true` conserve une copie staff des tickets publics ;
- no bet si EV ajustée non positive, market scope inconnu, data insuffisante ou warning
  critique ;
- aucun message ne promet un gain ou une certitude.

Idempotence Discord :

- chaque publication stocke un `idempotency_key` dans `discord_messages.payload_json` ;
- ce même `idempotency_key` est aussi stocké dans une colonne dédiée indexée ;
- la clé est stable par `ticket_key`, statut cible, channel et `message_type` ;
- une relance cron sur le même ticket/channel/statut est ignorée ;
- un dry-run ne bloque pas une exécution réelle, car l'exécution ne déduplique que les
  messages `sent`.

Politique de snapshots :

- les snapshots critiques sont toujours conservés : `generated`, `pre_lock*`, `locked`,
  `published*`, `settled` ;
- les snapshots non critiques identiques, par exemple `scored` ou `policy_decided`, sont
  dédupliqués sur `snapshot_duplicate_throttle_minutes` ;
- chaque snapshot récent reçoit un `snapshot_hash` dans `snapshot_json` pour faciliter
  l'audit et la maintenance.

## Commandes Contrôlées

Le fichier prod `config/worldcup_combos.yaml` est activé, mais staff-only.

Dry-run :

```bash
football-predictor worldcup-combos-run --dry-run
football-predictor worldcup-combos-publish --dry-run
PYTHONPATH=src .venv/bin/python scripts/dry_run_worldcup_combo_candidates.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/dry_run_worldcup_combo_builder.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/dry_run_worldcup_combo_publish.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/run_worldcup_combos.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/publish_worldcup_combos.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/lock_worldcup_combos.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/settle_worldcup_combos.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/maintenance_worldcup_combo_snapshots.py --config config/worldcup_combos.yaml
```

Execution explicite :

```bash
football-predictor worldcup-combos-run --execute
football-predictor worldcup-combos-publish --execute
PYTHONPATH=src .venv/bin/python scripts/run_worldcup_combos.py --config config/worldcup_combos.yaml --execute
PYTHONPATH=src .venv/bin/python scripts/publish_worldcup_combos.py --config config/worldcup_combos.yaml --execute
PYTHONPATH=src .venv/bin/python scripts/lock_worldcup_combos.py --config config/worldcup_combos.yaml --execute
PYTHONPATH=src .venv/bin/python scripts/settle_worldcup_combos.py --config config/worldcup_combos.yaml --execute
PYTHONPATH=src .venv/bin/python scripts/maintenance_worldcup_combo_snapshots.py --config config/worldcup_combos.yaml --execute
```

`worldcup-combos-run` génère et persiste les tickets, mais ne publie aucun message Discord.
`worldcup-combos-publish` publie uniquement des tickets déjà persistés, avec dry-run par défaut.

La maintenance snapshots affiche le volume total, les groupes de doublons probables et les
IDs proposés. Sans `--execute`, elle ne supprime rien.

## Settlement

Le settlement reste conservateur :

- `NINETY_MIN` est settlé uniquement sur des matchs `FT` avec buts disponibles ;
- `AET` et `PEN` déclenchent une revue manuelle, car le score 90 minutes peut être ambigu
  selon la source disponible ;
- `TO_QUALIFY`, `EXTRA_TIME_INCLUDED` et `UNKNOWN` déclenchent une revue manuelle tant
  qu'un adaptateur dédié n'expose pas l'information correcte ;
- `CANC`, `ABD`, `AWD` et `WO` sont traités comme legs void ;
- `PST` reste pending ;
- `PARTIAL_VOID` recalcule le profit sur les legs gagnants restants.

La payload settlement expose `settlement_status`, `settlement_warning` et
`manual_review_required`.

## SQLite

Le moteur SQLite active `busy_timeout=30000`, `foreign_keys=ON` et `journal_mode=WAL`
quand la base n'est pas en mémoire. Cela réduit les erreurs de verrouillage entre crons,
mais SQLite reste limité si plusieurs jobs écrivent en même temps. Si le volume de
snapshots, odds et messages Discord augmente fortement, PostgreSQL est recommandé pour
la production.

## Passage Production VPS

Avant toute activation :

```bash
alembic upgrade head
football-predictor worldcup-combos-run --dry-run
football-predictor worldcup-combos-publish --dry-run
```

Configuration de production :

```yaml
enabled: true
staff_only_shadow_mode: true
staff_channel_key: predictions_staff
public_channel_key: combines
mirror_public_to_staff: true
publish_no_bet_public: false
snapshot_duplicate_throttle_minutes: 30
allow_public_matchday3: false
allow_public_knockout: false
```

Les cron combinés de `config/prod_worldcup.crontab` sont actifs. Ils génèrent, verrouillent,
publient en staff et settlent les tickets tant que shadow mode reste activé. Le channel
public `combines` peut être configuré à l'avance, mais il ne reçoit rien tant que
`staff_only_shadow_mode` vaut `true`.

La feature reste CDM 2026 uniquement : `competition_key=fifa_world_cup_2026`,
`league_id=1`, `season=2026`.
