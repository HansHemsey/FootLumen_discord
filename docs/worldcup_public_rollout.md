# World Cup Public Rollout

Ce document decrit l'activation progressive des combinés Coupe du Monde 2026. La valeur
par defaut reste prudente : `staff_only_shadow_mode: true`.

## Phase 1 — Staff-Only

Objectif : verifier que le pipeline `generate -> lock -> publish -> settle` fonctionne sans
exposition publique.

Configuration :

```yaml
enabled: true
staff_only_shadow_mode: true
allow_public_matchday3: false
allow_public_knockout: false
publish_no_bet_public: false
```

Commandes :

```bash
football-predictor worldcup-combos-run --config config/worldcup_combos.yaml --execute
python scripts/lock_worldcup_combos.py --config config/worldcup_combos.yaml --execute
football-predictor worldcup-combos-publish --config config/worldcup_combos.yaml --execute
python scripts/settle_worldcup_combos.py --config config/worldcup_combos.yaml --execute
```

Criteres de sortie :

- aucun ticket avec plus de 3 legs ;
- aucun leg sans EV et edge positifs ;
- aucun message public ;
- no bet comprehensibles ;
- snapshots `generated`, `pre_lock`, `locked`, `published` ou `settled` presents ;
- settlement coherent sur matchs termines.

## Phase 2 — Shadow Mode Avec Rapports

Objectif : observer les tickets qui auraient pu etre publics, tout en les routant en staff.

Actions :

- conserver `staff_only_shadow_mode: true` ;
- verifier les tickets `PUBLIC_PUBLISHED` decisionnes puis bloques par shadow mode ;
- relire `no_publish_reason`, `warnings`, `post_lock_risk_score`, freshness et lineups ;
- comparer la performance des tickets staff-only aux resultats reels.

Monitoring :

```sql
select status, no_publish_reason, count(*)
from combo_tickets
group by status, no_publish_reason;
```

## Phase 3 — Public 2 Legs Seulement

Autoriser le public uniquement lorsque la phase 2 est stable.

Configuration minimale :

```yaml
enabled: true
staff_only_shadow_mode: false
max_public_legs: 2
max_staff_legs: 3
mirror_public_to_staff: true
publish_no_bet_public: false
allow_public_matchday3: false
allow_public_knockout: false
```

Garde-fous :

- public seulement si `LOCKED` ;
- public seulement si 2 legs ;
- EV ajustee positive ;
- confidence publique au-dessus du seuil ;
- pas de warning critique ;
- odds et prediction point-in-time ;
- lineups/freshness compatibles avec le risque public.

## Matchday 3

Garder `allow_public_matchday3: false` tant que les incentives de groupe ne sont pas
valides.

Conditions pour autoriser :

- group state snapshots point-in-time disponibles ;
- scenarios qualification/rotation calcules ;
- pas de legs multiples dans le meme groupe si la config l'interdit ;
- backtest ou shadow review montrant que les no-bet sont corrects ;
- staff valide manuellement plusieurs sessions matchday 3.

## Phases Finales

Garder `allow_public_knockout: false` au demarrage public.

Conditions pour autoriser :

- `market_scope` connu pour chaque leg ;
- distinction 90 minutes / qualification claire ;
- settlement teste pour `NINETY_MIN`, `TO_QUALIFY`, void/manual review ;
- formatter public lisible sans ambiguite ;
- cotes executees auditables.

## Criteres No Bet

Un ticket doit rester `NO_BET` ou staff si :

- moins de 2 legs propres ;
- EV ajustee <= 0 ;
- odds manquantes ou stale ;
- prediction trop ancienne ;
- data quality sous seuil ;
- fixture deja commencee ;
- lineup risk trop haut proche kickoff ;
- market scope inconnu en phase finale ;
- contradiction DRAW severe dans une prediction 1X2 ;
- source critique indisponible proche lock.

## Activation Et Rollback

Activation publique :

```bash
python - <<'PY'
from pathlib import Path
path = Path("config/worldcup_combos.yaml")
text = path.read_text(encoding="utf-8")
text = text.replace("staff_only_shadow_mode: true", "staff_only_shadow_mode: false")
path.write_text(text, encoding="utf-8")
PY
football-predictor worldcup-combos-publish --config config/worldcup_combos.yaml --dry-run
```

Rollback immediat :

```bash
python - <<'PY'
from pathlib import Path
path = Path("config/worldcup_combos.yaml")
text = path.read_text(encoding="utf-8")
text = text.replace("staff_only_shadow_mode: false", "staff_only_shadow_mode: true")
path.write_text(text, encoding="utf-8")
PY
```

Ne pas supprimer les tickets existants. Les conserver pour audit et settlement.
