"""World Cup 2026 CLI commands."""

# ruff: noqa: F403,F405,I001

from __future__ import annotations

from football_predictor.commands.shared import *  # noqa: F403,F405


def register(app: typer.Typer) -> None:
    def _worldcup_bundle_from_settings(settings: Settings):
        from football_predictor.worldcup.references import load_worldcup_reference_bundle

        return load_worldcup_reference_bundle(
            fifa_ranking_path=settings.world_cup_fifa_ranking_path,
            elo_data_path=settings.world_cup_elo_data_path,
            elo_shortname_path=settings.world_cup_elo_shortname_path,
            historical_results_path=settings.world_cup_historical_results_path,
        )

    def _worldcup_fixture_teams(session) -> list[str]:
        from football_predictor.worldcup.service import WORLD_CUP_LEAGUE_ID, WORLD_CUP_SEASON

        fixtures = list(
            session.execute(
                select(Fixture).where(
                    Fixture.league_id == WORLD_CUP_LEAGUE_ID,
                    Fixture.season == WORLD_CUP_SEASON,
                )
            ).scalars()
        )
        return sorted(
            {fixture.home_team for fixture in fixtures}
            | {fixture.away_team for fixture in fixtures}
        )

    @app.command("worldcup-audit-reference")
    def worldcup_audit_reference() -> None:
        """Validate World Cup 2026 team coverage in local reference files."""
        from football_predictor.worldcup.references import audit_worldcup_references

        settings = get_settings()
        bundle = _worldcup_bundle_from_settings(settings)
        engine, session_factory = _engine_and_session(settings)
        init_db(engine)
        with session_scope(session_factory) as session:
            teams = _worldcup_fixture_teams(session)
        audit = audit_worldcup_references(teams, bundle)
        console.print(audit)
        if not audit.get("ok"):
            raise typer.Exit(2)

    @app.command("worldcup-build-dataset")
    def worldcup_build_dataset(
        output: Path = typer.Option(
            Path("data/processed/worldcup_1x2_training.parquet"),
            "--output",
            help="CSV or Parquet output path.",
        ),
        audit_teams: bool = typer.Option(
            True,
            "--audit-teams/--no-audit-teams",
            help="Require the 48 World Cup fixture teams to be covered before writing.",
        ),
    ) -> None:
        """Build the offline World Cup 1X2 dataset from local international results."""
        from football_predictor.worldcup.dataset import build_and_save_worldcup_dataset

        settings = get_settings()
        bundle = _worldcup_bundle_from_settings(settings)
        teams = None
        if audit_teams:
            engine, session_factory = _engine_and_session(settings)
            init_db(engine)
            with session_scope(session_factory) as session:
                teams = _worldcup_fixture_teams(session)
        frame, coverage = build_and_save_worldcup_dataset(
            bundle,
            output=output,
            audited_teams=teams,
        )
        console.print(
            {
                "rows": len(frame),
                "columns": len(frame.columns),
                "output": str(output),
                "reference_ok": coverage.get("ok"),
            }
        )

    @app.command("worldcup-train-1x2")
    def worldcup_train_1x2(
        dataset: Path = typer.Option(..., "--dataset", help="World Cup dataset CSV/Parquet."),
        output_dir: Path | None = typer.Option(
            None,
            "--output-dir",
            help="Output model dir. Defaults to WORLD_CUP_1X2_MODEL_DIR.",
        ),
        model_version: str = typer.Option("worldcup-1x2-v1", "--model-version"),
    ) -> None:
        """Train the dedicated World Cup 1X2 model."""
        from football_predictor.worldcup.model import (
            WorldCupTrainingConfig,
            train_worldcup_model_from_dataset,
        )
        from football_predictor.worldcup.references import audit_worldcup_references

        if not dataset.exists():
            raise typer.BadParameter(f"Dataset not found: {dataset}")
        settings = get_settings()
        bundle = _worldcup_bundle_from_settings(settings)
        engine, session_factory = _engine_and_session(settings)
        init_db(engine)
        with session_scope(session_factory) as session:
            teams = _worldcup_fixture_teams(session)
        coverage = audit_worldcup_references(teams, bundle)
        if not coverage.get("ok"):
            raise typer.BadParameter(
                f"World Cup references incomplete: {coverage.get('blocking_missing_teams')}"
            )
        result = train_worldcup_model_from_dataset(
            dataset,
            output_dir or settings.world_cup_1x2_model_dir,
            config=WorldCupTrainingConfig(model_version=model_version),
            reference_coverage=coverage,
        )
        console.print(
            {
                "model_version": result.model.model_version,
                "model_path": str(result.model_path),
                "metrics_path": str(result.metrics_path),
                "features": len(result.model.feature_names),
            }
        )

    @app.command("worldcup-backtest-1x2")
    def worldcup_backtest_1x2(
        dataset: Path = typer.Option(..., "--dataset", help="World Cup dataset CSV/Parquet."),
        model_dir: Path | None = typer.Option(
            None,
            "--model-dir",
            help="Optional trained model dir. Defaults to in-backtest training.",
        ),
        output_dir: Path = typer.Option(Path("reports/worldcup"), "--output-dir"),
    ) -> None:
        """Backtest the World Cup 1X2 model and baselines."""
        from football_predictor.worldcup.backtest import run_worldcup_backtest

        if not dataset.exists():
            raise typer.BadParameter(f"Dataset not found: {dataset}")
        result = run_worldcup_backtest(dataset, model_dir=model_dir, output_dir=output_dir)
        worldcup_test = (
            result.metrics.get("metrics_by_model", {}).get("worldcup_1x2", {}).get("test", {})
        )
        console.print(
            {
                "reports": {name: str(path) for name, path in result.report_paths.items()},
                "test_rows": worldcup_test.get("row_count"),
                "test_accuracy": worldcup_test.get("accuracy"),
                "test_log_loss": worldcup_test.get("log_loss"),
            }
        )

    @app.command("worldcup-optimize-blend")
    def worldcup_optimize_blend(
        dataset: Path = typer.Option(..., "--dataset", help="World Cup dataset CSV/Parquet."),
        model_dir: Path | None = typer.Option(
            None,
            "--model-dir",
            help="Optional trained model dir. Defaults to in-optimizer training.",
        ),
        output_dir: Path = typer.Option(Path("reports/worldcup_blend"), "--output-dir"),
        write_best_config: bool = typer.Option(
            False,
            "--write-best-config/--no-write-best-config",
            help="Write selected blend_config.json to --model-dir when provided.",
        ),
    ) -> None:
        """Optimize World Cup 1X2 blend weights on chronological validation."""
        from football_predictor.worldcup.blend_optimizer import optimize_worldcup_blend

        if not dataset.exists():
            raise typer.BadParameter(f"Dataset not found: {dataset}")
        result = optimize_worldcup_blend(
            dataset,
            model_dir=model_dir,
            output_dir=output_dir,
            write_best_config=write_best_config,
        )
        selection = result.metrics.get("selection", {})
        console.print(
            {
                "reports": {name: str(path) for name, path in result.report_paths.items()},
                "blend_config": str(result.blend_config_path) if result.blend_config_path else None,
                "selected_candidate": selection.get("selected_candidate"),
                "selection_reason": selection.get("selection_reason"),
                "validation_log_loss": selection.get("validation", {}).get("log_loss"),
                "test_accuracy": selection.get("test", {}).get("accuracy"),
                "test_log_loss": selection.get("test", {}).get("log_loss"),
            }
        )

    @app.command("predict-worldcup")
    def predict_worldcup(
        fixture_id: int = typer.Option(..., "--fixture", "--fixture-id"),
        prediction_time: str | None = typer.Option(None, "--prediction-time"),
        model_dir: Path | None = typer.Option(None, "--model-dir"),
        refresh_data: bool = typer.Option(False, "--refresh-data/--no-refresh-data"),
        save_raw: bool = typer.Option(False, "--save-raw/--no-save-raw"),
        send_discord: bool = typer.Option(False, "--send-discord/--no-send-discord"),
        dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run"),
        print_only: bool = typer.Option(False, "--print-only/--no-print-only"),
        force: bool = typer.Option(False, "--force/--no-force"),
        json_output: bool = typer.Option(False, "--json/--no-json"),
    ) -> None:
        """Predict one FIFA World Cup 2026 fixture with the dedicated model."""
        from football_predictor.prediction.publication_policy import (
            CONFIDENCE_SKIP_REASON,
            is_publishable_confidence,
        )
        from football_predictor.prediction.staff_publication import send_skipped_prediction_to_staff
        from football_predictor.worldcup.service import WorldCupPredictionService

        settings = get_settings()
        bundle = _worldcup_bundle_from_settings(settings)
        reference = load_api_football_reference(settings.api_football_reference_path)
        players_reference = load_players_reference(settings.api_football_players_reference_path)
        engine, session_factory = _engine_and_session(settings)
        init_db(engine)
        _, channels, webhooks = _load_discord_routing(settings)
        api_client = _api_client_from_settings(settings) if refresh_data else None
        with session_scope(session_factory) as session:
            try:
                delivery = DiscordDeliveryService(
                    session,
                    channels_config=channels,
                    webhooks_config=webhooks,
                    legacy_webhook_url=settings.discord_webhook_url,
                    timeout=settings.discord_timeout_seconds,
                )
                service = WorldCupPredictionService(
                    session,
                    bundle,
                    model_dir=model_dir or settings.world_cup_1x2_model_dir,
                    reference=reference,
                    players_reference=players_reference,
                    market_1x2_bet_name=settings.market_1x2_bet_name,
                    market_1x2_bet_id=settings.market_1x2_bet_id,
                )
                output = service.predict_fixture(
                    fixture_id,
                    parse_datetime(prediction_time) if prediction_time else None,
                    refresh_data=refresh_data,
                    save_raw=save_raw,
                    api_client=api_client,
                )
                fixture = session.get(Fixture, fixture_id)
                status = "predicted"
                discord_message_id = None
                if send_discord:
                    markdown = format_prediction_markdown(output)
                    if is_publishable_confidence(output.confidence_label):
                        result = delivery.send_markdown(
                            markdown,
                            competition_key="fifa_world_cup_2026",
                            league_id=1,
                            season=2026,
                            channel_key="predictions",
                            message_type="prediction",
                            fixture_id=fixture_id,
                            model_prediction_id=output.model_prediction_id,
                            dry_run=dry_run,
                            print_only=print_only,
                            force=force,
                            payload_metadata={"model_family": "worldcup_1x2"},
                        )
                        status = result.status
                        discord_message_id = result.discord_message_id
                    else:
                        status = "confidence_skipped"
                        if fixture is not None and not dry_run and not print_only:
                            send_skipped_prediction_to_staff(
                                delivery,
                                markdown,
                                fixture=fixture,
                                model_family="worldcup_1x2",
                                confidence_label=output.confidence_label,
                                confidence_score=output.confidence_score,
                                reason=CONFIDENCE_SKIP_REASON,
                                prediction_time=output.prediction_time,
                                automation_window="single",
                                model_prediction_id=output.model_prediction_id,
                                force=force,
                            )
                payload = {
                    "status": status,
                    "discord_message_id": discord_message_id,
                    **output.to_dict(),
                }
            finally:
                if api_client is not None:
                    api_client.close()
        if json_output:
            console.print_json(data=payload)
        else:
            console.print(json.dumps(payload, indent=2, ensure_ascii=False))

    @app.command("worldcup-run-daily")
    def worldcup_run_daily(
        run_date: str | None = typer.Option(None, "--date"),
        window: DailyPredictionWindow = typer.Option(DailyPredictionWindow.LATE, "--window"),
        model_dir: Path | None = typer.Option(None, "--model-dir"),
        refresh_data: bool = typer.Option(False, "--refresh-data/--no-refresh-data"),
        save_raw: bool = typer.Option(False, "--save-raw/--no-save-raw"),
        send_discord: bool = typer.Option(False, "--send-discord/--no-send-discord"),
        dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run"),
        print_only: bool = typer.Option(False, "--print-only/--no-print-only"),
        force: bool = typer.Option(False, "--force/--no-force"),
        limit: int | None = typer.Option(None, "--limit"),
        json_output: Path | None = typer.Option(None, "--json-output"),
    ) -> None:
        """Run the World Cup M-30 daily prediction routine."""
        from football_predictor.worldcup.run_daily import run_daily_worldcup_predictions

        settings = get_settings()
        bundle = _worldcup_bundle_from_settings(settings)
        reference = load_api_football_reference(settings.api_football_reference_path)
        players_reference = load_players_reference(settings.api_football_players_reference_path)
        engine, session_factory = _engine_and_session(settings)
        init_db(engine)
        _, channels, webhooks = _load_discord_routing(settings)
        api_client = _api_client_from_settings(settings) if refresh_data else None
        with session_scope(session_factory) as session:
            try:
                delivery = DiscordDeliveryService(
                    session,
                    channels_config=channels,
                    webhooks_config=webhooks,
                    legacy_webhook_url=settings.discord_webhook_url,
                    timeout=settings.discord_timeout_seconds,
                )
                summary = run_daily_worldcup_predictions(
                    session,
                    bundle,
                    target_date=date_type.fromisoformat(run_date) if run_date else utc_now().date(),
                    window=window,
                    model_dir=model_dir or settings.world_cup_1x2_model_dir,
                    delivery=delivery,
                    send_discord=send_discord,
                    refresh_data=refresh_data,
                    api_client=api_client,
                    reference=reference,
                    players_reference=players_reference,
                    save_raw=save_raw,
                    dry_run=dry_run,
                    print_only=print_only,
                    force=force,
                    timezone_name=settings.app_timezone,
                    limit=limit,
                )
                payload = summary.as_dict()
            finally:
                if api_client is not None:
                    api_client.close()
        if json_output is not None:
            json_output.parent.mkdir(parents=True, exist_ok=True)
            json_output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        console.print(payload)
