# Production Public Runbook

Ce runbook decrit le passage en production publique de `soccer-pronos` pour la Coupe du
Monde 2026. Il ne remplace pas les checks CI : il donne l'ordre d'exploitation, les
commandes dry-run, les commandes execute et le rollback.

## Principes

- Ne jamais installer un cron public avant une CI verte.
- Ne jamais publier sans configuration Discord verifiee.
- Ne jamais stocker de secret dans Git.
- Toute commande qui ecrit, publie ou appelle massivement l'API doit etre explicite :
  `--execute`, `--refresh-api`, `--send-discord`, `DRY_RUN=false` ou equivalent documente.
- Les combinés CDM doivent rester en `staff_only_shadow_mode: true` jusqu'a validation
  manuelle du rollout.

## Installation VPS

```bash
cd /opt/football-predictor/app
git fetch origin
git checkout production/public-ready-cdm-2026
git pull --ff-only
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/repair_editable_install.py
```

Verifier ensuite :

```bash
football-predictor version
football-predictor healthcheck
make check
```

## Variables D'Environnement

Les secrets restent dans `.env` local ou dans l'environnement systeme. Le fichier
`.env.example` ne doit contenir que des placeholders vides.

Variables critiques :

```bash
API_FOOTBALL_KEY=
DATABASE_URL=sqlite:///./data/football_predictor.db
DISCORD_WEBHOOK_URL=
DISCORD_BOT_TOKEN=
APP_TIMEZONE=Europe/Paris
WORLD_CUP_COMBOS_CONFIG_PATH=config/worldcup_combos.yaml
```

Ne jamais afficher les valeurs completes. Les diagnostics doivent seulement indiquer
`configured: yes` et un hash court.

## Migrations

```bash
alembic upgrade head
sqlite3 data/football_predictor.db ".tables"
sqlite3 data/football_predictor.db "select count(*) from combo_tickets;"
sqlite3 data/football_predictor.db "select count(*) from combo_ticket_legs;"
sqlite3 data/football_predictor.db "select count(*) from combo_ticket_snapshots;"
```

Si une migration echoue :

```bash
alembic current
git status --short
```

Ne pas installer les crons tant que la migration n'est pas terminee.

## Seed Reference

Seed local sans quota API :

```bash
football-predictor seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json
```

Refresh live uniquement si demande explicite :

```bash
football-predictor ingest-reference \
  --config config/competitions_worldcup.yaml \
  --prefer-docs \
  --refresh-live \
  --save-raw
```

## Healthcheck

```bash
football-predictor healthcheck
football-predictor doctor --strict
python scripts/security_scan.py
```

Un warning DB peut etre acceptable sur un clone vide. En production, les tables attendues
doivent exister apres `alembic upgrade head`.

## Commandes Dry-Run

Ces commandes ne doivent rien publier et ne doivent pas appeler l'API live sauf option
explicite :

```bash
football-predictor worldcup-run-daily \
  --window late \
  --model-dir data/models/worldcup-1x2 \
  --refresh-data \
  --save-raw \
  --dry-run

football-predictor worldcup-combos-run \
  --config config/worldcup_combos.yaml \
  --dry-run

football-predictor worldcup-combos-publish \
  --config config/worldcup_combos.yaml \
  --dry-run

python scripts/lock_worldcup_combos.py --config config/worldcup_combos.yaml
python scripts/settle_worldcup_combos.py --config config/worldcup_combos.yaml
python scripts/maintenance_worldcup_combo_snapshots.py --config config/worldcup_combos.yaml
python scripts/worldcup_coverage_report.py
python scripts/sync_worldcup_odds_snapshots.py --markets 1x2,ou25,btts
```

## Commandes Execute

Ces commandes modifient la DB, publient Discord ou appellent l'API. Elles ne doivent etre
utilisees qu'apres dry-run et validation staff.

```bash
football-predictor worldcup-combos-run \
  --config config/worldcup_combos.yaml \
  --execute \
  --json-output reports/daily/worldcup_combos_run_latest.json

python scripts/lock_worldcup_combos.py \
  --config config/worldcup_combos.yaml \
  --execute

football-predictor worldcup-combos-publish \
  --config config/worldcup_combos.yaml \
  --execute \
  --json-output reports/daily/worldcup_combos_publish_latest.json

python scripts/settle_worldcup_combos.py \
  --config config/worldcup_combos.yaml \
  --execute

python scripts/worldcup_coverage_report.py --execute

python scripts/sync_worldcup_odds_snapshots.py \
  --execute \
  --refresh-api \
  --markets 1x2,ou25,btts
```

Les scripts d'enrichissement CDM acceptent aussi `--write` pour compatibilite, mais le
standard d'exploitation public-ready est `--execute`.

## Crons Recommandes

Utiliser le modele :

```bash
cp config/prod_worldcup.example.crontab /tmp/prod_worldcup.crontab
crontab /tmp/prod_worldcup.crontab
crontab -l
```

Ne pas installer `config/prod_worldcup.example.crontab` sans verifier :

- `PROJECT` ;
- `DATABASE_URL` ;
- `CONFIG_WC` ;
- `COMBOS_CONFIG` ;
- `staff_only_shadow_mode` ;
- routes Discord staff/public.

## Ordre De Demarrage

1. Pull + install.
2. `alembic upgrade head`.
3. Seed reference local.
4. `football-predictor doctor --strict`.
5. `make check`.
6. Dry-run CDM 1X2.
7. Dry-run combinés generate/lock/publish/settle.
8. Activer `enabled: true` et garder `staff_only_shadow_mode: true`.
9. Installer les crons staff-only.
10. Observer au moins une semaine de logs et snapshots.
11. Activer le public seulement via `docs/worldcup_public_rollout.md`.

## Monitoring

Fichiers a surveiller :

```bash
tail -n 100 logs/cron/worldcup_late.log
tail -n 100 logs/cron/worldcup_combos_run.log
tail -n 100 logs/cron/worldcup_combos_lock.log
tail -n 100 logs/cron/worldcup_combos_publish.log
tail -n 100 logs/cron/worldcup_combos_settle.log
```

Checks DB :

```sql
select status, count(*) from combo_tickets group by status;
select snapshot_type, count(*) from combo_ticket_snapshots group by snapshot_type;
select message_type, status, count(*) from discord_messages group by message_type, status;
```

Signals a investiguer :

- `odds_missing` ou `odds_stale` repetes ;
- `lineup_risk_too_high` proche kickoff ;
- tickets publics sans `LOCKED` ;
- plusieurs messages Discord pour le meme idempotency key ;
- data quality sous seuil.

## Rollback

Rollback sans toucher aux donnees :

```bash
crontab -l > ~/crontab.backup.before_rollback.$(date +%F-%H%M%S)
crontab -r
```

Rollback combinés seulement :

```bash
python - <<'PY'
from pathlib import Path
path = Path("config/worldcup_combos.yaml")
text = path.read_text(encoding="utf-8")
text = text.replace("enabled: true", "enabled: false")
text = text.replace("staff_only_shadow_mode: false", "staff_only_shadow_mode: true")
path.write_text(text, encoding="utf-8")
PY
```

Rollback code :

```bash
git fetch origin
git checkout production/public-ready-cdm-2026
git reset --hard origin/production/public-ready-cdm-2026
```

N'utiliser `git reset --hard` que sur VPS apres sauvegarde et verification que le worktree
ne contient pas de modification locale utile.

## Rotation Secrets

Rotation obligatoire si un secret a ete expose en log, DB, Discord ou Git :

1. Revoquer la cle ou le webhook cote fournisseur.
2. Creer un nouveau secret.
3. Mettre a jour `.env` ou le secret manager.
4. Redemarrer les crons/services.
5. Lancer `python scripts/security_scan.py`.
6. Verifier que `healthcheck` masque le secret.

## Checklist Avant Publication Publique

- [ ] CI verte.
- [ ] `make check` vert sur VPS.
- [ ] Secret scan vert.
- [ ] Migrations appliquees.
- [ ] Seed reference OK.
- [ ] Coverage monitor OK.
- [ ] Tests anti data leakage OK.
- [ ] Backtest O/U V2 relu.
- [ ] Combinés shadow OK.
- [ ] Discord staff OK.
- [ ] `public_channel_key` configure.
- [ ] `staff_only_shadow_mode` choisi volontairement.
- [ ] `allow_public_matchday3` toujours false au demarrage public.
- [ ] `allow_public_knockout` toujours false au demarrage public.
- [ ] Rollback crontab pret.
