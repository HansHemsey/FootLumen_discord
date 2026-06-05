# Public Ready Audit

Generated: 2026-06-05
Branch: `production/public-ready-cdm-2026`
Status: `READY_WITH_WARNINGS`

## Summary

The codebase is technically ready for a controlled public-production rollout, with
the World Cup combo feature still protected by `staff_only_shadow_mode: true` by
default. No Discord publication was executed during this audit. All write/publish
paths tested here were run in dry-run mode or returned a safe no-op.

Public activation should not happen until the VPS has run migrations and the CDM
dynamic data coverage has been verified in staff-only shadow mode.

## Tests Run

| Check | Result | Notes |
| --- | --- | --- |
| `git status --short` | OK | Initial worktree was clean. |
| `.venv/bin/python -m compileall src tests scripts alembic` | OK | No syntax errors. |
| `.venv/bin/python -m ruff check .` | OK | Lint clean. |
| `.venv/bin/python -m mypy src` | OK | Type check clean. |
| `.venv/bin/python -m pytest` | OK | `587 passed`, 1 non-blocking joblib/loky CPU warning. |
| `make security` | OK | Secret scan passed. |
| `make check` | OK | Compile, ruff, mypy, security and pytest passed with `587 passed`, 1 warning. |

## Dry Runs

| Dry-run | Result | Notes |
| --- | --- | --- |
| `football-predictor healthcheck` | OK with warning | DB accessible, but local DB reports missing tables. Secrets are masked. |
| `football-predictor doctor --strict` | OK with warning | Same DB warning, no critical error. |
| `scripts/worldcup_coverage_report.py` | OK | `fixtures_total=72`; fixtures and standings coverage 100%; dynamic sources currently 0%. |
| `scripts/dry_run_worldcup_combo_candidates.py` | OK | 37 sessions, 72 fixtures, 0 candidates. Main reasons: missing predictions, unavailable market, no O/U value side. |
| `scripts/dry_run_worldcup_combo_builder.py` | OK | 0 tickets, no publish. |
| `football-predictor worldcup-combos-run --dry-run` | OK | 0 persisted tickets. |
| `football-predictor worldcup-combos-publish --dry-run` | OK | Safe no-op when combo tables are missing; `--execute` fails clearly. |
| `scripts/lock_worldcup_combos.py` | OK | Safe no-op when combo tables are missing; `--execute` fails clearly. |
| `scripts/settle_worldcup_combos.py` | OK | Safe no-op when combo tables are missing; `--execute` fails clearly. |
| `scripts/maintenance_worldcup_combo_snapshots.py` | OK | 0 snapshots, no deletion. |
| `scripts/backtest_ou_v2_publication.py --dry-run` | OK | 766 rows after filters; no reports written in dry-run. |

## Security Checks

- `.env.example` is present.
- No real `.env`, `.env.*`, local Discord webhook file, DB file, logs directory or Claude local settings file is tracked.
- `make security` passed.
- Discord webhook payloads use `allowed_mentions={"parse": []}`.
- Secret sanitizer coverage exists for webhook URLs, API keys, stored Discord markdown and payloads.
- No Discord publication was executed.

## Config Checks

- `config/worldcup_combos.example.yaml` is present.
- `staff_only_shadow_mode` is documented and remains the safe default.
- `public_channel_key` and `staff_channel_key` are documented.
- `config/prod_worldcup.example.crontab` is present.
- Direct script cron examples now use `PYTHONPATH=src python` or documented `PYTHONPATH=src .venv/bin/python`.
- Combo cron lines pass the explicit combo config path.

## Combo Readiness

- `effective_cutoff_time = min(now, lock_time)` is implemented and used in combo candidate selection and pre-lock revalidation.
- Pre-lock revalidation reloads current point-in-time sources and can replace degraded legs or downgrade to `STAFF_ONLY` / `NO_BET`.
- Shadow mode prevents public publication by default.
- Publication idempotency is covered.
- No-bet routing is covered.
- Lock, publish and settlement dry-runs are safe if the combo tables are not migrated yet.
- Lock, publish and settlement execute modes fail clearly if combo tables are missing.

## Model Readiness

- DRAW-specific metrics are present for V3 and World Cup reports:
  `draw_precision`, `draw_recall`, `draw_f1`, `observed_draw_rate`,
  `mean_predicted_p_draw`, `draw_calibration_bins`, `confusion_matrix_labeled`.
- DRAW safety is enabled by default and caps/reroutes severe draw contradictions without changing raw probabilities.
- O/U V2 publication gates enforce value-side, positive edge/EV, non-legacy version and bookmaker-count checks.
- O/U legacy decisions are staff-only / non-public.
- World Cup data quality reporting exists and is runnable in dry-run.

## Warnings

1. Local DB is not fully migrated for combo tables.
   - Healthcheck reports missing DB tables.
   - Combo publish, lock and settlement correctly return a safe no-op in dry-run.
   - Execute mode fails clearly instead of hiding the missing migration.
   - Production action: run `alembic upgrade head` on the VPS before any execute mode.

2. Local CDM dynamic coverage is not production-ready yet.
   - Fixtures and standings are present.
   - Odds, API predictions, lineups, injuries, fixture statistics, events and player statistics are currently 0% in the local coverage report.
   - Production action: run the CDM ingestion/coverage cycle and keep combinés staff-only until coverage is verified.

3. Current local environment requires package path awareness for direct scripts.
   - The `football-predictor` entrypoint works.
   - Direct script commands should use `PYTHONPATH=src .venv/bin/python ...` or a verified editable install.
   - Production docs and cron examples were updated accordingly.

4. O/U backtest dry-run emitted local Arrow/sysctl CPU-info warnings in this sandbox.
   - The command completed successfully.
   - No production impact observed.

## Blockers

None for a staff-only, shadow-mode production rollout.

Public publication remains gated by the rollout checklist below and should not be
enabled until the data-coverage warning is resolved.

## Production Checklist

- [x] CI-equivalent local checks pass.
- [x] Secret scan passes.
- [x] Safe execution defaults are documented.
- [x] Discord `allowed_mentions` is disabled.
- [x] Combo shadow mode remains documented and safe by default.
- [x] Effective cutoff anti-leakage is implemented and tested.
- [x] Pre-lock revalidation is implemented and tested.
- [x] O/U V2 public gates are implemented and tested.
- [x] DRAW safety is implemented and tested.
- [ ] VPS migrations applied with `alembic upgrade head`.
- [ ] VPS combo tables verified.
- [ ] CDM coverage report shows useful odds/predictions/lineups where expected.
- [ ] Staff Discord route tested in dry-run/no-secret mode.
- [ ] Shadow-mode combo cycle observed for at least one match window.
- [ ] `staff_only_shadow_mode` intentionally reviewed before any public activation.

## Recommended Next Actions

1. Deploy this branch to VPS without enabling public combo publication.
2. Run `alembic upgrade head`.
3. Run `football-predictor healthcheck` and `football-predictor doctor --strict`.
4. Run the CDM coverage report with `PYTHONPATH=src .venv/bin/python scripts/worldcup_coverage_report.py`.
5. Run combo candidate, builder, run, lock, publish and settle dry-runs.
6. Keep `staff_only_shadow_mode: true` through the first staff-only observation window.
7. Re-run this audit after CDM odds/predictions/lineups coverage is populated.
