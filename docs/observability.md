# Observability And Job Health

This project treats dynamic data sources as optional but auditable inputs. A failed
optional source must not crash a full prediction batch, but it must be visible in
logs, reports, persisted payloads and data-quality warnings.

## Source Health

Optional refresh jobs should emit a structured source health record with:

- `source_name`: source identifier, for example `odds`, `lineups`, `api_prediction`.
- `status`: `success` or `failed`.
- `last_success_at` / `last_failure_at`: UTC timestamp for the attempt.
- `error_type`: sanitized exception class for failed attempts.
- `warning`: stable warning code surfaced to downstream quality checks.
- `fixture_id`: fixture concerned, when applicable.
- `duration_ms`: source call duration.

World Cup dynamic refresh stores this list in:

- `PredictionOutput.refresh_summary.source_health`
- `FeatureSnapshot.data_quality_json.source_health`
- `ModelPrediction.payload_json.source_health`
- Discord payload metadata for World Cup predictions and staff skips.

## Structured Logs

Source attempts log compact key-value events:

```text
event=worldcup_dynamic_refresh_source competition_key=fifa_world_cup_2026 fixture_id=... source=odds status=success duration_ms=...
event=worldcup_dynamic_refresh_source competition_key=fifa_world_cup_2026 fixture_id=... source=lineups status=failed warning=lineups_failed error_type=...
```

Unexpected optional source failures include a sanitized traceback. Webhooks, API
keys, bearer tokens and secret-looking values must be redacted before logging.

## Warning Codes

Current World Cup refresh warnings:

- `fixtures_failed`
- `odds_failed`
- `lineups_failed`
- `api_prediction_failed`
- `injuries_failed`
- `odds_failed_close_to_kickoff`
- `lineups_failed_close_to_kickoff`

Close-to-kickoff warnings are added when the prediction is within 90 minutes of
kickoff and a critical source fails.

## Data Quality Impact

Refresh failures reduce `overall_data_quality_score` instead of silently
disappearing. Approximate penalties:

- odds failure: strong penalty;
- lineups failure: moderate penalty, strong within 90 minutes of kickoff;
- API prediction failure: light penalty;
- injuries failure: light penalty;
- fixture refresh failure: strong penalty.

World Cup publication confidence is capped when quality is poor:

- Low cap if lineups fail close to kickoff or quality drops below the critical threshold.
- Medium cap if odds fail or quality is partial.

Combinés CDM inherit source warnings from their leg predictions. Critical source
warnings, such as close-to-kickoff odds or lineup failures, force `NO_BET` rather
than public publication.

## Operator Checklist

For a failed or staff-only World Cup prediction, inspect:

1. `refresh_summary.warnings`
2. `data_quality_json.warnings`
3. `data_quality_json.source_health`
4. cron log lines with `event=worldcup_dynamic_refresh_source`
5. Discord staff payload metadata

Secrets must only come from environment variables or local ignored config files.
If a real secret appears in any log, rotate it before continuing production work.
