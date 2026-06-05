"""Over/Under 2.5 CLI sub-application."""

# ruff: noqa: F403,F405,I001

from __future__ import annotations

from football_predictor.commands.shared import *  # noqa: F403,F405


def register(app: typer.Typer) -> None:
    ou_app = typer.Typer(help="Over/Under 2.5 prediction commands")
    app.add_typer(ou_app, name="ou")

    @ou_app.command("ingest-odds")
    def ou_ingest_odds(
        date_str: str | None = typer.Option(None, "--date", help="YYYY-MM-DD (default: today)"),
        league_id: list[int] = typer.Option([], "--league-id", help="Repeat for multiple leagues"),
        season: int | None = typer.Option(None, "--season"),
        fixture: int | None = typer.Option(None, "--fixture-id", help="Single fixture override"),
    ) -> None:
        """Ingest O/U 2.5 market odds from API-Football into odds_snapshots."""
        from football_predictor.ou_model.ingestion.ingest_ou_odds import OUOddsIngestionService

        settings = get_settings()
        reference = load_api_football_reference(settings.api_football_reference_path)
        engine, session_factory = _engine_and_session(settings)
        target_date = date_type.fromisoformat(date_str) if date_str else date_type.today()

        with (
            session_scope(session_factory) as session,
            _api_client_from_settings(settings) as client,
        ):
            svc = OUOddsIngestionService(
                session,
                client,
                reference=reference,
                ou_bet_id=settings.market_ou25_bet_id,
            )
            if fixture is not None:
                summary = svc.ingest_ou_odds_for_fixture(fixture)
                console.print(json.dumps(summary.as_dict(), indent=2))
            elif league_id:
                for lid in league_id:
                    summary = svc.ingest_ou_odds_by_date(target_date, league_id=lid, season=season)
                    console.print(f"league={lid}: {json.dumps(summary.as_dict())}")
            else:
                summary = svc.ingest_ou_odds_by_date(target_date, season=season)
                console.print(json.dumps(summary.as_dict(), indent=2))
        console.print("[green]O/U odds ingestion complete.[/green]")

    @ou_app.command("build-dataset")
    def ou_build_dataset(
        league_id: list[int] = typer.Option([], "--league-id"),
        season: list[int] = typer.Option([], "--season"),
        output: Path = typer.Option(Path("data/processed/training_ou_v1.parquet"), "--output"),
        limit: int | None = typer.Option(None, "--limit"),
    ) -> None:
        """Build a PIT-safe O/U 2.5 training dataset and save to parquet."""
        from football_predictor.ou_model.backtesting.ou_dataset_builder import (
            build_ou_training_dataset,
        )

        settings = get_settings()
        engine, session_factory = _engine_and_session(settings)

        with session_scope(session_factory) as session:
            frame = build_ou_training_dataset(
                session,
                ou_bet_id=settings.market_ou25_bet_id,
                league_ids=league_id or None,
                seasons=season or None,
                save_path=output,
                limit=limit,
            )
        console.print(f"[green]Dataset saved: {output} ({len(frame)} rows)[/green]")

    @ou_app.command("train")
    def ou_train(
        dataset: Path = typer.Option(Path("data/processed/training_ou_v1.parquet"), "--dataset"),
        output_dir: Path = typer.Option(Path("data/models/ou-v1"), "--output-dir"),
        version: str = typer.Option("ou-v1", "--version"),
    ) -> None:
        """Train OUCompositeModel from a parquet dataset and save artifacts."""
        from football_predictor.ou_model.modeling.ou_train import (
            OUTrainingConfig,
            train_ou_model_from_dataset,
        )

        result = train_ou_model_from_dataset(
            dataset,
            output_dir,
            config=OUTrainingConfig(model_version=version),
        )
        console.print(f"[green]Model saved to {result.model_path}[/green]")
        console.print(json.dumps(result.metrics, indent=2))

    @ou_app.command("backtest")
    def ou_backtest(
        dataset: Path = typer.Option(Path("data/processed/training_ou_v1.parquet"), "--dataset"),
        output_dir: Path | None = typer.Option(None, "--output-dir"),
        n_splits: int = typer.Option(5, "--n-splits"),
    ) -> None:
        """Walk-forward O/U backtest and print aggregate metrics."""
        from football_predictor.ou_model.backtesting.ou_evaluator import (
            OUBacktestConfig,
            run_ou_backtest,
        )

        result = run_ou_backtest(
            dataset,
            output_dir=output_dir,
            config=OUBacktestConfig(n_splits=n_splits),
        )
        console.print(json.dumps(result.aggregate, indent=2))
        if output_dir:
            console.print(f"[green]Backtest results saved to {output_dir}[/green]")

    @ou_app.command("backtest-publication-v2")
    def ou_backtest_publication_v2(
        dataset: Path = typer.Option(Path("data/processed/training_ou_v1.parquet"), "--dataset"),
        output_dir: Path = typer.Option(Path("reports/ou_v2"), "--output-dir"),
        start_date: str | None = typer.Option(None, "--start-date"),
        end_date: str | None = typer.Option(None, "--end-date"),
        competition: str | None = typer.Option(None, "--competition"),
        n_splits: int = typer.Option(5, "--n-splits"),
        min_train_rows: int = typer.Option(300, "--min-train-rows"),
        min_recommended_bets: int = typer.Option(20, "--min-recommended-bets"),
    ) -> None:
        """Backtest O/U V2 publication policy and write calibration/ROI reports."""
        from football_predictor.ou_model.backtesting.ou_evaluator import OUBacktestConfig
        from football_predictor.ou_model.backtesting.ou_publication_backtest import (
            OUPublicationBacktestConfig,
            run_ou_publication_backtest,
        )

        result = run_ou_publication_backtest(
            dataset,
            output_dir=output_dir,
            start_date=start_date,
            end_date=end_date,
            competition=competition,
            config=OUPublicationBacktestConfig(
                ou_backtest_config=OUBacktestConfig(
                    n_splits=n_splits,
                    min_train_rows=min_train_rows,
                ),
                min_recommended_bets=min_recommended_bets,
            ),
        )
        console.print(json.dumps(result.summary["recommendation"], indent=2, default=str))
        console.print(f"[green]O/U V2 publication reports saved to {output_dir}[/green]")

    @ou_app.command("predict")
    def ou_predict(
        fixture_id: int = typer.Option(..., "--fixture-id"),
        prediction_time: str | None = typer.Option(None, "--prediction-time", help="ISO datetime"),
        model_dir: Path | None = typer.Option(None, "--model-dir"),
        no_save: bool = typer.Option(False, "--no-save"),
    ) -> None:
        """Predict O/U 2.5 for a single fixture and print the Discord-formatted result."""
        from football_predictor.ou_model.discord.ou_formatter import format_ou_prediction_markdown
        from football_predictor.ou_model.prediction.ou_service import OUPredictionService

        settings = get_settings()
        engine, session_factory = _engine_and_session(settings)
        pred_time = parse_datetime(prediction_time) if prediction_time else None

        with session_scope(session_factory) as session:
            fixture = session.get(Fixture, fixture_id)
            svc = OUPredictionService(session, model_dir=model_dir, settings=settings)
            output = svc.predict_fixture_ou(fixture_id, pred_time, save_to_db=not no_save)
            md = format_ou_prediction_markdown(output, fixture)
        console.print(md)

    @ou_app.command("run-daily")
    def ou_run_daily(
        date_str: str | None = typer.Option(None, "--date"),
        league_id: list[int] = typer.Option([], "--league-id"),
        season: int | None = typer.Option(None, "--season"),
        model_dir: Path | None = typer.Option(None, "--model-dir"),
        window: DailyPredictionWindow = typer.Option(
            DailyPredictionWindow.LATE,
            "--window",
            help="Prediction window to select fixtures; late is M-30.",
        ),
        send_discord: bool = typer.Option(False, "--send-discord"),
        dry_run: bool = typer.Option(False, "--dry-run"),
        print_only: bool = typer.Option(False, "--print-only"),
        limit: int | None = typer.Option(None, "--limit"),
        edge_threshold: float = typer.Option(0.02, "--edge-threshold"),
    ) -> None:
        """Run O/U 2.5 predictions for all fixtures on a given date."""
        from football_predictor.ou_model.prediction.ou_run_daily import run_daily_ou_predictions

        settings = get_settings()
        engine, session_factory = _engine_and_session(settings)
        init_db(engine)
        target_date = date_type.fromisoformat(date_str) if date_str else None

        discord_delivery = None
        if send_discord:
            _, channels_config, webhooks_config = _load_discord_routing(settings)

        with session_scope(session_factory) as session:
            if send_discord:
                discord_delivery = DiscordDeliveryService(
                    session,
                    channels_config=channels_config,
                    webhooks_config=webhooks_config,
                )
            summary = run_daily_ou_predictions(
                target_date,
                session=session,
                discord_delivery=discord_delivery,
                league_ids=league_id or None,
                season=season,
                model_dir=model_dir,
                ou_bet_id=settings.market_ou25_bet_id,
                send_discord=send_discord,
                dry_run=dry_run,
                print_only=print_only,
                window=window,
                limit=limit,
                edge_threshold=edge_threshold,
            )

        console.print(json.dumps(summary.as_dict(), indent=2, default=str))
