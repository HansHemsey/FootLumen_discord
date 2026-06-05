"""Backtesting, dataset and model-training CLI commands."""

# ruff: noqa: F403,F405,I001

from __future__ import annotations

from football_predictor.commands.shared import *  # noqa: F403,F405


def register(app: typer.Typer) -> None:
    @app.command("build-dataset")
    def build_dataset(
        league_ids: list[int] | None = typer.Option(
            None,
            "--league",
            "--league-id",
            help="API-Football league ID. Repeat for multiple leagues.",
        ),
        seasons: list[int] | None = typer.Option(
            None,
            "--season",
            help="API-Football season. Repeat for multiple seasons.",
        ),
        prediction_window: str = typer.Option(
            "24h",
            "--prediction-window",
            help="Point-in-time simulation window: 24h, 6h, 30m, or 40m before fixture date.",
        ),
        output: Path | None = typer.Option(
            None,
            "--output",
            help="Optional CSV or Parquet output path.",
        ),
        output_format: str | None = typer.Option(
            None,
            "--format",
            help="Optional export format override: csv or parquet.",
        ),
        limit: int | None = typer.Option(None, "--limit", help="Maximum fixtures to process."),
        min_quality: int = typer.Option(0, "--min-quality", help="Minimum data quality score."),
    ) -> None:
        """Build a point-in-time historical training dataset."""
        if not league_ids:
            raise typer.BadParameter("At least one --league is required")
        if not seasons:
            raise typer.BadParameter("At least one --season is required")
        try:
            prediction_offset = parse_prediction_window(prediction_window)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if output_format is not None and output_format.casefold() not in {"csv", "parquet"}:
            raise typer.BadParameter("--format must be csv or parquet")

        settings = get_settings()
        engine, session_factory = _engine_and_session(settings)
        init_db(engine)
        players_reference = load_players_reference(settings.api_football_players_reference_path)
        with session_scope(session_factory) as session:
            frame = build_training_dataset(
                session,
                league_ids,
                seasons,
                prediction_offset=prediction_offset,
                output_path=output,
                output_format=output_format,
                players_reference=players_reference,
                limit=limit,
                min_quality=min_quality,
            )
        console.print(
            {
                "rows": len(frame),
                "columns": len(frame.columns),
                "prediction_window": prediction_window,
                "output": str(output) if output is not None else None,
            }
        )

    @app.command()
    def train(
        dataset: Path = typer.Option(..., "--dataset", help="CSV or Parquet training dataset."),
        output_dir: Path = typer.Option(
            Path("data/models/v1"),
            "--output-dir",
            help="Directory where model.joblib and metadata.json are written.",
        ),
        model_version: str = typer.Option("v1", "--model-version", help="Model version label."),
        calibration: str = typer.Option(
            "sigmoid",
            "--calibration",
            help="Calibration method: sigmoid, isotonic, or none.",
        ),
        valid_until: str | None = typer.Option(
            None,
            "--valid-until",
            help="Fixture-date cutoff for train/validation split.",
        ),
        test_until: str | None = typer.Option(
            None,
            "--test-until",
            help="Optional fixture-date cutoff after validation for held-out test rows.",
        ),
    ) -> None:
        """Train the Sprint 11 sklearn sport model and save an artifact."""
        normalized_calibration = calibration.casefold()
        if normalized_calibration not in {"sigmoid", "isotonic", "none"}:
            raise typer.BadParameter("--calibration must be sigmoid, isotonic, or none")
        if not dataset.exists():
            raise typer.BadParameter(f"Dataset not found: {dataset}")

        if valid_until is not None or test_until is not None:
            console.print(
                "Note: Sprint 11 train_model_from_dataset uses chronological 80/20 split "
                "when fixture_date is present; explicit cutoffs are reserved for backtesting."
            )
        result = train_model_from_dataset(
            dataset,
            output_dir,
            model_version=model_version,
        )
        console.print(
            {
                "model_version": result.model.model_version,
                "output_dir": str(output_dir),
                "features": len(result.model.feature_names),
                "model_path": str(result.model_path),
                "metadata_path": str(result.metadata_path),
                "feature_names_path": str(result.feature_names_path),
                "metrics_path": str(result.metrics_path),
                "feature_coverage_path": str(result.feature_coverage_path)
                if result.feature_coverage_path is not None
                else None,
                "calibration_requested": normalized_calibration,
            }
        )

    @app.command("train-v3-draw-risk")
    def train_v3_draw_risk(
        dataset: Path = typer.Option(..., "--dataset", help="CSV or Parquet V3 dataset."),
        output_dir: Path = typer.Option(
            Path("data/models/v3/draw_risk"),
            "--output-dir",
            help="Directory where Draw Risk artifacts are written.",
        ),
        model_version: str = typer.Option(
            "v3.0-draw-risk",
            "--model-version",
            help="Draw Risk model version label.",
        ),
        calibration: str = typer.Option(
            "isotonic",
            "--calibration",
            help="Calibration method: isotonic or none.",
        ),
        train_ratio: float = typer.Option(
            0.60,
            "--train-ratio",
            help="Chronological train split ratio.",
        ),
        valid_ratio: float = typer.Option(
            0.20,
            "--valid-ratio",
            help="Chronological validation split ratio.",
        ),
    ) -> None:
        """Train the V3 binary Draw Risk model and save its artifacts."""
        normalized_calibration = calibration.casefold()
        if normalized_calibration not in {"isotonic", "none"}:
            raise typer.BadParameter("--calibration must be isotonic or none")
        if train_ratio <= 0 or valid_ratio <= 0 or train_ratio + valid_ratio >= 1:
            raise typer.BadParameter("--train-ratio and --valid-ratio must be positive and sum < 1")
        if not dataset.exists():
            raise typer.BadParameter(f"Dataset not found: {dataset}")

        from football_predictor.modeling.v3.draw_risk_model import (
            CalibrationMode,
            DrawRiskTrainingConfig,
            train_draw_risk_from_dataset,
        )

        calibration_mode = cast(CalibrationMode, normalized_calibration)
        result = train_draw_risk_from_dataset(
            dataset,
            output_dir,
            config=DrawRiskTrainingConfig(
                model_version=model_version,
                calibration=calibration_mode,
                train_ratio=train_ratio,
                valid_ratio=valid_ratio,
            ),
        )
        validation = result.metrics.get("validation") or {}
        test = result.metrics.get("test") or {}
        console.print(
            {
                "model_version": result.model.model_version,
                "output_dir": str(output_dir),
                "features": len(result.model.feature_names),
                "model_path": str(result.model_path),
                "metadata_path": str(result.metadata_path),
                "feature_names_path": str(result.feature_names_path),
                "metrics_path": str(result.metrics_path),
                "feature_coverage_path": str(result.feature_coverage_path),
                "calibration": result.model.calibration_decision,
                "validation_log_loss": validation.get("log_loss"),
                "validation_brier": validation.get("brier_score"),
                "test_log_loss": test.get("log_loss"),
                "test_brier": test.get("brier_score"),
            }
        )

    @app.command("train-v3-no-draw-winner")
    def train_v3_no_draw_winner(
        dataset: Path = typer.Option(..., "--dataset", help="CSV or Parquet V3 dataset."),
        output_dir: Path = typer.Option(
            Path("data/models/v3/no_draw_winner"),
            "--output-dir",
            help="Directory where No-Draw Winner artifacts are written.",
        ),
        model_version: str = typer.Option(
            "v3.0-no-draw-winner",
            "--model-version",
            help="No-Draw Winner model version label.",
        ),
        calibration: str = typer.Option(
            "sigmoid",
            "--calibration",
            help="Calibration method: sigmoid or none.",
        ),
        train_ratio: float = typer.Option(
            0.60,
            "--train-ratio",
            help="Chronological train split ratio after draw rows are filtered.",
        ),
        valid_ratio: float = typer.Option(
            0.20,
            "--valid-ratio",
            help="Chronological validation split ratio after draw rows are filtered.",
        ),
    ) -> None:
        """Train the V3 binary No-Draw Winner model and save its artifacts."""
        normalized_calibration = calibration.casefold()
        if normalized_calibration not in {"sigmoid", "none"}:
            raise typer.BadParameter("--calibration must be sigmoid or none")
        if train_ratio <= 0 or valid_ratio <= 0 or train_ratio + valid_ratio >= 1:
            raise typer.BadParameter("--train-ratio and --valid-ratio must be positive and sum < 1")
        if not dataset.exists():
            raise typer.BadParameter(f"Dataset not found: {dataset}")

        from football_predictor.modeling.v3.no_draw_winner_model import (
            CalibrationMode,
            NoDrawWinnerTrainingConfig,
            train_no_draw_winner_from_dataset,
        )

        calibration_mode = cast(CalibrationMode, normalized_calibration)
        result = train_no_draw_winner_from_dataset(
            dataset,
            output_dir,
            config=NoDrawWinnerTrainingConfig(
                model_version=model_version,
                calibration=calibration_mode,
                train_ratio=train_ratio,
                valid_ratio=valid_ratio,
            ),
        )
        validation = result.metrics.get("validation") or {}
        test = result.metrics.get("test") or {}
        console.print(
            {
                "model_version": result.model.model_version,
                "output_dir": str(output_dir),
                "features": len(result.model.feature_names),
                "model_path": str(result.model_path),
                "metadata_path": str(result.metadata_path),
                "feature_names_path": str(result.feature_names_path),
                "metrics_path": str(result.metrics_path),
                "feature_coverage_path": str(result.feature_coverage_path),
                "calibration": result.model.calibration_decision,
                "validation_log_loss": validation.get("log_loss"),
                "validation_brier": validation.get("brier_score"),
                "test_log_loss": test.get("log_loss"),
                "test_brier": test.get("brier_score"),
            }
        )

    @app.command("train-v3")
    def train_v3(
        dataset: Path = typer.Option(..., "--dataset", help="CSV or Parquet V3 dataset."),
        output_dir: Path = typer.Option(
            Path("data/models/v3"),
            "--output-dir",
            help="Directory where V3 component and stacker artifacts are written.",
        ),
        v2_model_dir: Path | None = typer.Option(
            None,
            "--v2-model-dir",
            help="Optional V2 model directory used as a stacker signal.",
        ),
        calibration: str = typer.Option(
            "isotonic_draw,sigmoid_ndw",
            "--calibration",
            help="Calibration spec: isotonic_draw,sigmoid_ndw or none.",
        ),
        train_ratio: float = typer.Option(
            0.60,
            "--train-ratio",
            help="Chronological train split ratio.",
        ),
        valid_ratio: float = typer.Option(
            0.20,
            "--valid-ratio",
            help="Chronological validation split ratio used for stacker training.",
        ),
    ) -> None:
        """Train the V3 Draw Risk, No-Draw Winner and stacker artifacts."""
        if train_ratio <= 0 or valid_ratio <= 0 or train_ratio + valid_ratio >= 1:
            raise typer.BadParameter("--train-ratio and --valid-ratio must be positive and sum < 1")
        if not dataset.exists():
            raise typer.BadParameter(f"Dataset not found: {dataset}")
        if v2_model_dir is not None and not v2_model_dir.exists():
            raise typer.BadParameter(f"V2 model path not found: {v2_model_dir}")

        draw_calibration, ndw_calibration = _parse_v3_calibration(calibration)

        from football_predictor.modeling.v3.training import V3TrainingConfig, train_v3_from_dataset

        result = train_v3_from_dataset(
            dataset,
            output_dir,
            v2_model_dir=v2_model_dir,
            config=V3TrainingConfig(
                draw_calibration=draw_calibration,
                no_draw_winner_calibration=ndw_calibration,
                train_ratio=train_ratio,
                valid_ratio=valid_ratio,
            ),
        )
        stacker_test = (result.metrics.get("stacker") or {}).get("test") or {}
        console.print(
            {
                "model_version": result.model.model_version,
                "output_dir": str(output_dir),
                "model_path": str(result.model_path),
                "metadata_path": str(result.metadata_path),
                "metrics_path": str(result.metrics_path),
                "draw_risk_model_path": str(result.draw_risk_model_path),
                "no_draw_winner_model_path": str(result.no_draw_winner_model_path),
                "stacker_model_path": str(result.stacker_result.model_path),
                "stacker_decision": result.stacker_result.model.training_decision,
                "stacker_test_log_loss": stacker_test.get("log_loss"),
                "stacker_test_brier": stacker_test.get("brier_score"),
            }
        )

    def _parse_v3_calibration(value: str) -> tuple[str, str]:
        normalized = {part.strip().casefold() for part in value.split(",") if part.strip()}
        if not normalized or normalized == {"none"}:
            return "none", "none"
        allowed = {"isotonic_draw", "none_draw", "sigmoid_ndw", "none_ndw"}
        unknown = sorted(normalized - allowed)
        if unknown:
            raise typer.BadParameter(
                "--calibration must contain isotonic_draw/none_draw and sigmoid_ndw/none_ndw"
            )
        draw = "none" if "none_draw" in normalized else "isotonic"
        ndw = "none" if "none_ndw" in normalized else "sigmoid"
        return draw, ndw

    @app.command("backtest-v3")
    def backtest_v3(
        dataset: Path = typer.Option(..., "--dataset", help="CSV or Parquet V3 dataset."),
        model_dir: Path = typer.Option(
            Path("data/models/v3"),
            "--model-dir",
            help="Directory containing V3 component artifacts.",
        ),
        v2_model_dir: Path | None = typer.Option(
            None,
            "--v2-model-dir",
            help="Optional V2 model directory used for comparison and V3 blend signals.",
        ),
        output_dir: Path = typer.Option(
            Path("reports/v3"),
            "--output-dir",
            "--report",
            help="Directory where V3 comparison reports are written.",
        ),
        output_format: str = typer.Option(
            "both",
            "--format",
            help="Report format: json, markdown, or both.",
        ),
        train_ratio: float = typer.Option(0.60, "--train-ratio"),
        valid_ratio: float = typer.Option(0.20, "--valid-ratio"),
        retrain_v3: bool = typer.Option(
            False,
            "--retrain-v3/--no-retrain-v3",
            help="Retrain V3 from the dataset before evaluating the chronological test fold.",
        ),
    ) -> None:
        """Backtest V3 against V2 and baselines on a chronological test fold."""
        normalized_format = output_format.casefold()
        if normalized_format not in {"json", "markdown", "both"}:
            raise typer.BadParameter("--format must be json, markdown, or both")
        if not dataset.exists():
            raise typer.BadParameter(f"Dataset not found: {dataset}")
        if v2_model_dir is not None and not v2_model_dir.exists():
            raise typer.BadParameter(f"V2 model path not found: {v2_model_dir}")

        from football_predictor.backtesting import v3_evaluator

        try:
            result = v3_evaluator.run_v3_backtest(
                dataset,
                model_dir,
                v2_model_dir=v2_model_dir,
                output_dir=output_dir,
                config=v3_evaluator.V3BacktestConfig(
                    train_ratio=train_ratio,
                    valid_ratio=valid_ratio,
                    report_format=cast(v3_evaluator.ReportFormat, normalized_format),
                    retrain_v3=retrain_v3,
                ),
            )
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        primary = result.metrics_by_model.get("v3_stacker_full", {})
        v2 = result.metrics_by_model.get("v2_existing", {})
        console.print(
            {
                "test_rows": result.periods["test"].row_count,
                "reports": {name: str(path) for name, path in result.report_paths.items()},
                "success_status": result.success_criteria.get("status"),
                "v3_log_loss": primary.get("log_loss"),
                "v3_brier": primary.get("brier_score"),
                "v2_available": v2.get("available", False),
                "models": list(result.metrics_by_model),
            }
        )

    @app.command()
    def backtest(
        dataset: Path = typer.Option(..., "--dataset", help="CSV or Parquet backtest dataset."),
        model_dir: Path | None = typer.Option(
            None,
            "--model-dir",
            help="Directory containing model.joblib. Omit to evaluate baselines only.",
        ),
        output_dir: Path | None = typer.Option(
            None,
            "--output-dir",
            help="Report directory. Defaults to data/processed/backtests/<timestamp>.",
        ),
        output_format: str = typer.Option(
            "both",
            "--format",
            help="Report format: json, markdown, or both.",
        ),
        train_ratio: float = typer.Option(0.60, "--train-ratio"),
        valid_ratio: float = typer.Option(0.20, "--valid-ratio"),
        test_ratio: float = typer.Option(0.20, "--test-ratio"),
        retrain_v2_model_version: str | None = typer.Option(
            None,
            "--retrain-v2-model-version",
            help=(
                "Train a V2 model inside the temporal backtest on train/validation only, "
                "then evaluate test."
            ),
        ),
    ) -> None:
        """Backtest a model artifact and baselines with a temporal split."""
        normalized_format = output_format.casefold()
        if normalized_format not in {"json", "markdown", "both"}:
            raise typer.BadParameter("--format must be json, markdown, or both")
        if not dataset.exists():
            raise typer.BadParameter(f"Dataset not found: {dataset}")
        if model_dir is not None and not model_dir.exists():
            raise typer.BadParameter(f"Model directory or file not found: {model_dir}")
        try:
            config = BacktestConfig(
                train_ratio=train_ratio,
                valid_ratio=valid_ratio,
                test_ratio=test_ratio,
                report_format=cast(ReportFormat, normalized_format),
                retrain_v2_model_version=retrain_v2_model_version,
            )
            result = run_backtest(
                dataset,
                model_dir=model_dir,
                output_dir=output_dir,
                config=config,
            )
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.print(
            {
                "test_rows": result.periods["test"].row_count,
                "models": list(result.metrics_by_model),
                "reports": {name: str(path) for name, path in result.report_paths.items()},
                "test_accuracy": {
                    name: metrics.get("accuracy")
                    for name, metrics in result.metrics_by_model.items()
                },
            }
        )
