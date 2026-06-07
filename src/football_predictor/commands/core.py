"""Core diagnostics CLI commands."""

# ruff: noqa: F403,F405,I001

from __future__ import annotations

from football_predictor.commands.shared import *  # noqa: F403,F405


def _print_healthcheck(*, json_output: bool = False, strict: bool = False) -> None:
    settings = get_settings()
    report = build_diagnostic_report(settings, version=__version__)
    if json_output:
        typer.echo(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        if strict and report.has_critical_errors:
            raise typer.Exit(1)
        return

    console.print("FootLumen healthcheck")
    console.print(f"Version: {__version__}")
    console.print(f"Database URL: {mask_database_url(settings.database_url)}")
    console.print(f"Timezone: {settings.app_timezone}")
    console.print(f"API timeout seconds: {settings.api_football_timeout_seconds}")
    console.print(f"API max retries: {settings.api_football_max_retries}")
    console.print(f"API raw snapshot dir: {settings.api_football_raw_snapshot_dir}")
    console.print(f"Competitions config path: {settings.competitions_config_path}")
    console.print(f"Reference path: {settings.api_football_reference_path}")
    console.print(f"Players path: {settings.api_football_players_reference_path}")
    console.print(f"Players cache path: {settings.api_football_players_cache_path}")
    for line in settings.secret_status_lines():
        console.print(line)
    for path in (
        settings.api_football_reference_path,
        settings.api_football_players_reference_path,
        settings.api_football_players_cache_path,
    ):
        console.print(f"{path}: {'exists' if path.exists() else 'missing'}")
    _print_diagnostic_table(report)
    if strict and report.has_critical_errors:
        raise typer.Exit(1)


def _print_diagnostic_table(report) -> None:
    table = Table(title="Diagnostics")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    for check in report.checks:
        table.add_row(check.name, check.status.value, check.message)
    console.print(table)


def _print_data_quality_report(report: dict) -> None:
    console.print("FootLumen data-quality")
    scope = report.get("scope", {})
    console.print(
        "Scope: "
        f"fixture={scope.get('fixture_id')} "
        f"date={scope.get('date')} "
        f"league={scope.get('league_id')} "
        f"season={scope.get('season')}"
    )
    table = Table(title="Data Quality")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in report.items():
        if key == "scope":
            continue
        if isinstance(value, dict):
            table.add_row(key, json.dumps(value, sort_keys=True))
        else:
            table.add_row(key, str(value))
    console.print(table)


def register(app: typer.Typer) -> None:
    @app.command("version")
    def version_command() -> None:
        """Print the installed package version."""
        console.print(__version__)

    @app.command("healthcheck")
    def healthcheck(
        json_output: bool = typer.Option(False, "--json", help="Output a machine-readable report."),
        strict: bool = typer.Option(False, "--strict", help="Exit non-zero on critical errors."),
    ) -> None:
        """Check local configuration without exposing secrets."""
        _print_healthcheck(json_output=json_output, strict=strict)

    @app.command()
    def doctor(
        json_output: bool = typer.Option(False, "--json", help="Output a machine-readable report."),
        strict: bool = typer.Option(False, "--strict", help="Exit non-zero on critical errors."),
    ) -> None:
        """Run local diagnostics without API-Football or Discord calls."""
        _print_healthcheck(json_output=json_output, strict=strict)

    @app.command("data-quality")
    def data_quality_command(
        fixture_id: int | None = typer.Option(None, "--fixture", help="Scope report to a fixture."),
        report_date: str | None = typer.Option(None, "--date", help="Scope report to YYYY-MM-DD."),
        league_id: int | None = typer.Option(None, "--league", help="Scope report to a league."),
        season: int | None = typer.Option(None, "--season", help="Scope report to a season."),
        json_output: bool = typer.Option(False, "--json", help="Output a machine-readable report."),
    ) -> None:
        """Report local DB coverage for prediction inputs without network calls."""
        settings = get_settings()
        parsed_date = None
        if report_date is not None:
            try:
                parsed_date = date_type.fromisoformat(report_date)
            except ValueError as exc:
                raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
        if league_id is not None and season is None:
            raise typer.BadParameter("--season is required with --league")

        reference = load_api_football_reference(settings.api_football_reference_path)
        try:
            validate_positive_reference_ids(
                reference,
                fixture_id=fixture_id,
                league_id=league_id,
                season=season,
            )
        except FootballPredictorError as exc:
            raise typer.BadParameter(str(exc)) from exc

        engine, session_factory = _engine_and_session(settings)
        init_db(engine)
        with session_factory() as session:
            report = build_data_quality_report(
                session,
                fixture_id=fixture_id,
                target_date=parsed_date,
                league_id=league_id,
                season=season,
            )
        if json_output:
            typer.echo(json.dumps(report, indent=2, sort_keys=True))
        else:
            _print_data_quality_report(report)
