"""Command line interface for Football Predictor."""

# ruff: noqa: F403,F405,I001

from __future__ import annotations

import typer

from football_predictor.commands.backtesting import register as register_backtesting_commands
from football_predictor.commands.core import register as register_core_commands
from football_predictor.commands.maintenance import register as register_maintenance_commands
from football_predictor.commands.ou import register as register_ou_commands
from football_predictor.commands.shared import *  # noqa: F403,F405
from football_predictor.commands.worldcup import register as register_worldcup_commands
from football_predictor.commands.worldcup_combos import register as register_worldcup_combo_commands

app = typer.Typer(help="Football Predictor CLI")
register_core_commands(app)
register_maintenance_commands(app)


@app.command("ingest-reference")
def ingest_reference(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions config resolved against local docs reference.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run ingestion and roll back DB writes.",
    ),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
    prefer_docs: bool = typer.Option(
        True,
        "--prefer-docs/--no-prefer-docs",
        help="Seed local docs references before optional live refresh.",
    ),
    refresh_live: bool = typer.Option(
        False,
        "--refresh-live",
        help="Explicitly call API-Football for leagues, teams and squads.",
    ),
) -> None:
    """Ingest reference entities from docs and optionally API-Football live."""
    if not prefer_docs and not refresh_live:
        console.print("Nothing to ingest. Use --prefer-docs and/or --refresh-live.")
        raise typer.Exit(2)

    settings = get_settings()
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    summary = SeedSummary()
    try:
        if prefer_docs:
            summary.merge(
                seed_reference_from_docs(
                    session,
                    settings.api_football_reference_path,
                    settings.api_football_players_reference_path,
                )
            )
        if refresh_live:
            with _api_client_from_settings(settings) as client:
                summary.merge(
                    ingest_reference_live(
                        session,
                        client,
                        competitions,
                        save_raw=save_raw,
                    )
                )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    output["prefer_docs"] = int(prefer_docs)
    output["refresh_live"] = int(refresh_live)
    console.print(output)


@app.command("ingest-leagues")
def ingest_leagues(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions config resolved against local docs reference.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh leagues from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_leagues(competitions)
    console.print(summary.as_dict())


@app.command("ingest-teams")
def ingest_teams(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions config resolved against local docs reference.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh teams and venues from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_teams(competitions)
    console.print(summary.as_dict())


@app.command("ingest-player-squads")
def ingest_player_squads(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions config resolved against local docs reference.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh player squads from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_player_squads(competitions)
    console.print(summary.as_dict())


@app.command("resolve-unknown-players")
def resolve_unknown_players(
    input_path: Path = typer.Option(
        DEFAULT_UNKNOWN_PLAYERS_PATH,
        "--input",
        help="JSONL file populated during fixture detail ingestion.",
    ),
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="Optional league_id filter or fallback context.",
    ),
    season: int | None = typer.Option(
        None,
        "--season",
        help="Optional season filter or fallback context for /players?id&season.",
    ),
    team_id: int | None = typer.Option(
        None,
        "--team",
        "--team-id",
        help="Optional team_id filter or fallback context for /players/squads.",
    ),
    limit: int | None = typer.Option(
        50,
        "--limit",
        help="Maximum deduplicated unknown players to resolve in this run.",
    ),
    delay_seconds: float = typer.Option(
        2.0,
        "--delay-seconds",
        help="Sleep between player resolution attempts to reduce API rate pressure.",
    ),
    squads_fallback: bool = typer.Option(
        True,
        "--squads-fallback/--no-squads-fallback",
        help="Fallback to /players/squads?team=... when direct player lookup is incomplete.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run resolution then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
) -> None:
    """Resolve live players missing from local docs into the local DB."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    try:
        with _api_client_from_settings(settings) as client:
            summary = UnknownPlayerResolutionService(
                session,
                client,
                save_raw=save_raw,
            ).resolve_unknown_players(
                input_path=input_path,
                league_id=league_id,
                season=season,
                team_id=team_id,
                limit=limit,
                delay_seconds=delay_seconds,
                squads_fallback=squads_fallback,
                prune_resolved=not dry_run,
            )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("ingest-bookmakers")
def ingest_bookmakers(
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh bookmaker references from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_bookmakers()
    console.print(summary.as_dict())


@app.command("ingest-bets")
def ingest_bets(
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
) -> None:
    """Refresh bet references from API-Football and store raw snapshots."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with _api_client_from_settings(settings) as client, session_scope(session_factory) as session:
        summary = ApiReferenceIngestionService(session, client).ingest_bets()
    console.print(summary.as_dict())


@app.command()
def predict(
    fixture: int = typer.Option(..., "--fixture", help="API-Football fixture_id from local docs."),
    prediction_time: str | None = typer.Option(
        None,
        "--prediction-time",
        help="Prediction cutoff timestamp, ISO 8601. Defaults to now.",
    ),
    model_dir: Path | None = typer.Option(
        Path("data/models/v1"),
        "--model-dir",
        help="Model directory or model.joblib path. Missing model falls back safely.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh",
        help="Explicitly refresh API-Football before prediction.",
    ),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also save raw API payload snapshots to disk during live refresh.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON only."),
    json_output_path: Path | None = typer.Option(
        None,
        "--json-output",
        help="Write prediction JSON to this path.",
    ),
) -> None:
    """Predict a single fixture with point-in-time features and robust fallbacks."""
    settings = get_settings()
    reference = load_api_football_reference(settings.api_football_reference_path)
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    cutoff = _parse_optional_prediction_time(prediction_time)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        service = PredictionService(
            reference,
            session,
            players_reference=players_reference,
            market_1x2_bet_name=settings.market_1x2_bet_name,
            market_1x2_bet_id=settings.market_1x2_bet_id,
        )
        if refresh_data:
            with _api_client_from_settings(settings) as client:
                prediction = service.predict_fixture(
                    fixture,
                    cutoff,
                    model_dir=model_dir,
                    refresh_data=True,
                    save_raw=save_raw,
                    api_client=client,
                )
        else:
            prediction = service.predict_fixture(
                fixture,
                cutoff,
                model_dir=model_dir,
                refresh_data=False,
                save_raw=save_raw,
            )
    prediction_json = json.dumps(prediction.to_dict(), indent=2, sort_keys=True)
    if json_output_path is not None:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        json_output_path.write_text(prediction_json + "\n", encoding="utf-8")
    if json_output:
        console.out(prediction_json)
    else:
        _print_prediction_summary(prediction, settings.app_timezone)


@app.command("predict-v3")
def predict_v3(
    fixture: int = typer.Option(..., "--fixture", help="API-Football fixture_id from local docs."),
    prediction_time: str | None = typer.Option(
        None,
        "--prediction-time",
        help="Prediction cutoff timestamp, ISO 8601. Defaults to max(now, kickoff - 30m).",
    ),
    model_dir: Path = typer.Option(
        Path("data/models/v3"),
        "--model-dir",
        help="Directory containing V3 component artifacts.",
    ),
    v2_model_dir: Path | None = typer.Option(
        None,
        "--v2-model-dir",
        help="Optional V2 model directory used as a V3 signal.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh",
        help="Explicitly refresh API-Football before prediction.",
    ),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also save raw API payload snapshots to disk during live refresh.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON only."),
    send_discord: bool = typer.Option(
        False,
        "--send-discord",
        help="Send the V3 markdown prediction to Discord.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist Discord route without sending."),
    print_only: bool = typer.Option(
        False,
        "--print-only",
        help="Print markdown and persist Discord trace without sending.",
    ),
    force: bool = typer.Option(False, "--force", help="Bypass Discord message dedupe."),
    discord_channels: Path | None = typer.Option(
        None,
        "--discord-channels",
        help="Discord channels config path. Defaults to settings.",
    ),
    discord_webhooks: Path | None = typer.Option(
        None,
        "--discord-webhooks",
        help="Discord webhook config path. Defaults to settings.",
    ),
) -> None:
    """Predict a single fixture with V3 and optional Discord delivery."""
    settings = get_settings()
    if send_discord or dry_run or print_only:
        reference, channels_config, webhooks_config = _load_discord_routing(
            settings,
            channels_path=discord_channels,
            webhooks_path=discord_webhooks,
        )
    else:
        reference = load_api_football_reference(settings.api_football_reference_path)
        channels_config = None
        webhooks_config = None
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    cutoff = _parse_optional_prediction_time(prediction_time)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)

    from football_predictor.discord.v3_formatter import format_prediction_v3_markdown
    from football_predictor.prediction.v3_service import PredictionV3Service

    discord_payload: dict[str, Any] | None = None
    with session_scope(session_factory) as session:
        service = PredictionV3Service(
            reference,
            session,
            players_reference=players_reference,
            market_1x2_bet_name=settings.market_1x2_bet_name,
            market_1x2_bet_id=settings.market_1x2_bet_id,
        )
        if refresh_data:
            with _api_client_from_settings(settings) as api_client:
                prediction = service.predict_fixture_v3(
                    fixture,
                    cutoff,
                    model_dir=model_dir,
                    v2_model_dir=v2_model_dir,
                    refresh_data=True,
                    save_raw=save_raw,
                    api_client=api_client,
                )
        else:
            prediction = service.predict_fixture_v3(
                fixture,
                cutoff,
                model_dir=model_dir,
                v2_model_dir=v2_model_dir,
                refresh_data=False,
                save_raw=save_raw,
            )
        markdown = format_prediction_v3_markdown(
            prediction,
            timezone_name=settings.app_timezone,
        )
        if print_only and not json_output:
            console.print(markdown)
        if send_discord or dry_run or print_only:
            fixture_row = session.get(Fixture, fixture)
            competition_key = _competition_key_from_fixture(reference, fixture_row, None)
            route_league_id = (
                fixture_row.league_id
                if fixture_row is not None
                and (competition_key is not None or (fixture_row.league_id or 0) > 0)
                else None
            )
            route_season = (
                fixture_row.season
                if fixture_row is not None
                and (competition_key is not None or route_league_id is not None)
                else None
            )
            routing_config_available = competition_key is not None or route_league_id is not None
            delivery = DiscordDeliveryService(
                session,
                channels_config=channels_config if routing_config_available else None,
                webhooks_config=webhooks_config if routing_config_available else None,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            )
            result = delivery.send_markdown(
                markdown,
                competition_key=competition_key,
                league_id=route_league_id,
                season=route_season,
                channel_key="predictions",
                message_type="prediction",
                fixture_id=fixture,
                model_prediction_id=None,
                dry_run=dry_run,
                print_only=print_only,
                force=force,
                payload_metadata={
                    "model_family": "v3",
                    "v3_model_prediction_id": prediction.v3_model_prediction_id,
                    "v3_feature_snapshot_id": prediction.v3_feature_snapshot_id,
                },
            )
            discord_payload = {
                "status": result.status,
                "discord_message_id": result.discord_message_id,
                "webhook_hash": result.webhook_hash,
                "channel": result.route.channel_key,
            }

    payload = prediction.to_dict()
    if discord_payload is not None:
        payload["discord"] = discord_payload
    if json_output:
        console.out(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_prediction_v3_summary(prediction, settings.app_timezone)
        if discord_payload is not None:
            console.print({"discord": discord_payload})


@app.command("predict-and-send")
def predict_and_send(
    fixture: int = typer.Option(..., "--fixture", help="API-Football fixture_id from local docs."),
    prediction_time: str | None = typer.Option(
        None,
        "--prediction-time",
        help="Prediction cutoff timestamp, ISO 8601. Defaults to now.",
    ),
    model_dir: Path | None = typer.Option(
        Path("data/models/v1"),
        "--model-dir",
        help="Model directory or model.joblib path. Missing model falls back safely.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh",
        help="Explicitly refresh API-Football before prediction.",
    ),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also save raw API payload snapshots to disk during live refresh.",
    ),
    competition_key: str | None = typer.Option(
        None,
        "--competition-key",
        help="Discord competition key. Defaults to fixture league from local reference.",
    ),
    channel: str = typer.Option("predictions", "--channel", help="Discord channel key."),
    discord_webhooks: Path | None = typer.Option(
        None,
        "--discord-webhooks",
        help="Discord webhook config path. Defaults to settings.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(
        False,
        "--print-only",
        help="Print markdown and persist trace without sending.",
    ),
    force: bool = typer.Option(False, "--force", help="Bypass Discord message dedupe."),
) -> None:
    """Predict a fixture and send the markdown block to Discord."""
    settings = get_settings()
    reference, channels_config, webhooks_config = _load_discord_routing(
        settings,
        webhooks_path=discord_webhooks,
    )
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    cutoff = _parse_optional_prediction_time(prediction_time)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        service = PredictionService(
            reference,
            session,
            players_reference=players_reference,
            market_1x2_bet_name=settings.market_1x2_bet_name,
            market_1x2_bet_id=settings.market_1x2_bet_id,
        )
        if refresh_data:
            with _api_client_from_settings(settings) as api_client:
                prediction = service.predict_fixture(
                    fixture,
                    cutoff,
                    model_dir=model_dir,
                    refresh_data=True,
                    save_raw=save_raw,
                    api_client=api_client,
                )
        else:
            prediction = service.predict_fixture(
                fixture,
                cutoff,
                model_dir=model_dir,
                refresh_data=False,
                save_raw=save_raw,
            )
        fixture_row = session.get(Fixture, fixture)
        markdown = format_prediction_markdown(prediction, settings.app_timezone)
        if print_only:
            console.print(markdown)
        delivery = DiscordDeliveryService(
            session,
            channels_config=channels_config,
            webhooks_config=webhooks_config,
            legacy_webhook_url=settings.discord_webhook_url,
            timeout=settings.discord_timeout_seconds,
        )
        result = delivery.send_markdown(
            markdown,
            competition_key=_competition_key_from_fixture(
                reference,
                fixture_row,
                competition_key,
            ),
            league_id=fixture_row.league_id if fixture_row is not None else None,
            season=fixture_row.season if fixture_row is not None else None,
            channel_key=channel,
            message_type="prediction",
            fixture_id=fixture,
            model_prediction_id=prediction.model_prediction_id,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
        )
    console.print(
        "Discord route "
        f"status={result.status} channel={result.route.channel_key} "
        f"webhook_hash={result.webhook_hash or 'none'}"
    )


@app.command("discord-check-config")
def discord_check_config(
    channels: Path | None = typer.Option(None, "--channels", help="Discord channels YAML."),
    webhooks: Path | None = typer.Option(None, "--webhooks", help="Discord webhooks YAML."),
) -> None:
    """Validate Discord routing config without sending messages."""
    settings = get_settings()
    _, channels_config, webhooks_config = _load_discord_routing(
        settings,
        channels_path=channels,
        webhooks_path=webhooks,
    )
    configured = sum(1 for route in webhooks_config.routes if route.webhook_url)
    console.print(
        "Discord config OK: "
        f"competitions={len(channels_config.competitions)} "
        f"routes={len(webhooks_config.routes)} configured_webhooks={configured}"
    )


@app.command("discord-send")
def discord_send(
    prediction_id: int = typer.Option(..., "--prediction-id", help="ModelPrediction ID."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print only, no send."),
    force: bool = typer.Option(False, "--force", help="Bypass message dedupe."),
) -> None:
    """Send a stored model prediction to the competition predictions channel."""
    settings = get_settings()
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        result = send_prediction_to_discord(
            DiscordDeliveryService(
                session,
                channels_config=channels_config,
                webhooks_config=webhooks_config,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            ),
            prediction_id,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            timezone_name=settings.app_timezone,
        )
    console.print(
        f"Discord prediction status={result.status} webhook_hash={result.webhook_hash or 'none'}"
    )


@app.command("discord-send-message")
def discord_send_message(
    competition_key: str | None = typer.Option(None, "--competition-key", help="Competition key."),
    competition_alias: str | None = typer.Option(
        None,
        "--competition",
        help="Alias for --competition-key.",
    ),
    channel: str = typer.Option(..., "--channel", help="Discord channel key."),
    message_type: str = typer.Option("analysis", "--message-type", help="Message type."),
    content_file: Path = typer.Option(..., "--content-file", help="Markdown content file."),
    season: int | None = typer.Option(None, "--season", help="Optional season."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print only, no send."),
    force: bool = typer.Option(False, "--force", help="Bypass message dedupe."),
) -> None:
    """Send an already formatted message through the Discord router."""
    settings = get_settings()
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    resolved_competition_key = competition_alias or competition_key
    if not resolved_competition_key:
        raise typer.BadParameter("--competition or --competition-key is required")
    competition = channels_config.find_competition(
        competition_key=resolved_competition_key,
        season=season,
    )
    if competition is None:
        raise typer.BadParameter("Unknown Discord competition route")
    markdown = content_file.read_text(encoding="utf-8")
    if print_only:
        console.print(markdown)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        result = DiscordDeliveryService(
            session,
            channels_config=channels_config,
            webhooks_config=webhooks_config,
            legacy_webhook_url=settings.discord_webhook_url,
            timeout=settings.discord_timeout_seconds,
        ).send_markdown(
            markdown,
            competition_key=resolved_competition_key,
            league_id=competition.league_id,
            season=competition.season,
            channel_key=channel,
            message_type=message_type,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
        )
    console.print(
        f"Discord message status={result.status} webhook_hash={result.webhook_hash or 'none'}"
    )


@app.command("publish-daily-discord")
def publish_daily_discord(
    publish_date: str | None = typer.Option(
        None,
        "--date",
        help="Local date to publish, format YYYY-MM-DD. Defaults to today in APP_TIMEZONE.",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions YAML/JSON config. Defaults to settings.",
    ),
    standings: bool = typer.Option(
        True,
        "--standings/--no-standings",
        help="Publish standings to the classement channel.",
    ),
    calendar: bool = typer.Option(
        True,
        "--calendar/--no-calendar",
        help="Publish next round calendar to the calendrier channel.",
    ),
    daily_matches: bool = typer.Option(
        True,
        "--daily-matches/--no-daily-matches",
        help="Publish target-date fixtures to the matchs_du_jour channel.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist routes without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print messages without sending."),
    force: bool = typer.Option(False, "--force", help="Bypass Discord message dedupe."),
    replace_previous: bool = typer.Option(
        True,
        "--replace-previous/--no-replace-previous",
        help=(
            "Delete previous operational messages for the same competition/channel before sending."
        ),
    ),
) -> None:
    """Publish standings, next round calendar and daily matches to routed Discord channels."""
    settings = get_settings()
    if publish_date is None:
        target_date = datetime.now(ZoneInfo(settings.app_timezone)).date()
    else:
        try:
            target_date = date_type.fromisoformat(publish_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        summary = publish_daily_discord_messages(
            session=session,
            competitions=competitions,
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels_config,
                webhooks_config=webhooks_config,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            ),
            target_date=target_date,
            timezone_name=settings.app_timezone,
            include_standings=standings,
            include_calendar=calendar,
            include_daily_matches=daily_matches,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            replace_previous=replace_previous,
            echo=console.print,
        )
    console.print(summary.as_dict())


@app.command("publish-weekly-score")
def publish_weekly_score(
    publish_date: str | None = typer.Option(
        None,
        "--date",
        help="Local date to publish, format YYYY-MM-DD. Defaults to today in APP_TIMEZONE.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print messages without sending."),
    force: bool = typer.Option(False, "--force", help="Bypass Discord message dedupe."),
    include_previous_week_finalization: bool = typer.Option(
        True,
        "--include-previous-week-finalization/--no-include-previous-week-finalization",
        help="On Mondays, also update the previous week scorecard.",
    ),
    replace_current_week: bool = typer.Option(
        True,
        "--replace-current-week/--no-replace-current-week",
        help="Replace previous score messages with the same week_key.",
    ),
) -> None:
    """Publish the weekly scorecard for Discord predictions."""
    settings = get_settings()
    if publish_date is None:
        target_date = datetime.now(ZoneInfo(settings.app_timezone)).date()
    else:
        try:
            target_date = date_type.fromisoformat(publish_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        summary = publish_weekly_prediction_score(
            session=session,
            delivery=DiscordDeliveryService(
                session,
                channels_config=channels_config,
                webhooks_config=webhooks_config,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            ),
            target_date=target_date,
            timezone_name=settings.app_timezone,
            include_previous_week_finalization=include_previous_week_finalization,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            replace_current_week=replace_current_week,
            echo=console.print,
        )
    console.print(summary.as_dict())


@app.command("publish-match-analyses")
def publish_match_analyses_cli(
    publish_date: str | None = typer.Option(
        None,
        "--date",
        help="Local match date, format YYYY-MM-DD. Defaults to today in APP_TIMEZONE.",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions YAML/JSON config. Defaults to settings.",
    ),
    model_dir: Path | None = typer.Option(
        Path("data/models/v1"),
        "--model-dir",
        help="Model directory or model.joblib path. Missing model falls back safely.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh-data",
        help="Explicitly refresh API-Football before building missing H-6 predictions.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print messages only."),
    force: bool = typer.Option(False, "--force", help="Bypass analysis dedupe."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum due analyses."),
    analysis_grace_minutes: int = typer.Option(
        45,
        "--analysis-grace-minutes",
        help="Minutes after H-6 during which an analysis may still be sent.",
    ),
    save_raw: bool = typer.Option(False, "--save-raw", help="Save raw API payload snapshots."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON summary only."),
    json_output_path: Path | None = typer.Option(
        None,
        "--json-output",
        help="Write JSON summary to this path.",
    ),
) -> None:
    """Publish one H-6 analysis per due followed fixture to the analyses channel."""
    settings = get_settings()
    target_date = _parse_cli_date_or_today(publish_date, settings.app_timezone)
    if limit is not None and limit < 1:
        raise typer.BadParameter("--limit must be greater than 0")
    if analysis_grace_minutes < 0:
        raise typer.BadParameter("--analysis-grace-minutes must be positive")
    reference = load_api_football_reference(settings.api_football_reference_path)
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    api_client = _api_client_from_settings(settings) if refresh_data else None
    with session_scope(session_factory) as session:
        try:
            summary = publish_match_analyses(
                session=session,
                competitions=competitions,
                delivery=DiscordDeliveryService(
                    session,
                    channels_config=channels_config,
                    webhooks_config=webhooks_config,
                    legacy_webhook_url=settings.discord_webhook_url,
                    timeout=settings.discord_timeout_seconds,
                ),
                reference=reference,
                players_reference=players_reference,
                target_date=target_date,
                model_dir=model_dir,
                api_client=api_client,
                refresh_data=refresh_data,
                save_raw=save_raw,
                timezone_name=settings.app_timezone,
                dry_run=dry_run,
                print_only=print_only,
                force=force,
                limit=limit,
                analysis_grace_minutes=analysis_grace_minutes,
                echo=console.print,
            )
        finally:
            if api_client is not None:
                api_client.close()
    _emit_json_or_summary(
        summary.as_dict(),
        json_output=json_output,
        json_output_path=json_output_path,
        fallback_label="Match analyses",
    )


@app.command("publish-match-results")
def publish_match_results_cli(
    publish_date: str | None = typer.Option(
        None,
        "--date",
        help="Local match date, format YYYY-MM-DD. Defaults to today in APP_TIMEZONE.",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions YAML/JSON config. Defaults to settings.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh-data",
        help="Explicitly refresh fixtures before selecting finished matches.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print messages only."),
    force: bool = typer.Option(False, "--force", help="Bypass result dedupe."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum finished results."),
    save_raw: bool = typer.Option(False, "--save-raw", help="Save raw API payload snapshots."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON summary only."),
    json_output_path: Path | None = typer.Option(
        None,
        "--json-output",
        help="Write JSON summary to this path.",
    ),
) -> None:
    """Publish one post-match result summary per finished followed fixture."""
    settings = get_settings()
    target_date = _parse_cli_date_or_today(publish_date, settings.app_timezone)
    if limit is not None and limit < 1:
        raise typer.BadParameter("--limit must be greater than 0")
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    api_client = _api_client_from_settings(settings) if refresh_data else None
    with session_scope(session_factory) as session:
        try:
            summary = publish_match_results(
                session=session,
                competitions=competitions,
                delivery=DiscordDeliveryService(
                    session,
                    channels_config=channels_config,
                    webhooks_config=webhooks_config,
                    legacy_webhook_url=settings.discord_webhook_url,
                    timeout=settings.discord_timeout_seconds,
                ),
                target_date=target_date,
                api_client=api_client,
                refresh_data=refresh_data,
                save_raw=save_raw,
                timezone_name=settings.app_timezone,
                dry_run=dry_run,
                print_only=print_only,
                force=force,
                limit=limit,
                echo=console.print,
            )
        finally:
            if api_client is not None:
                api_client.close()
    _emit_json_or_summary(
        summary.as_dict(),
        json_output=json_output,
        json_output_path=json_output_path,
        fallback_label="Match results",
    )


@app.command("discord-test-route")
def discord_test_route(
    competition_key: str | None = typer.Option(
        None,
        "--competition-key",
        help="Competition key. Omit it for global channels like predictions_staff.",
    ),
    channel: str = typer.Option("predictions", "--channel", help="Discord channel key."),
    message_type: str = typer.Option("prediction", "--message-type", help="Message type."),
    send: bool = typer.Option(False, "--send", help="Actually send the test message."),
) -> None:
    """Resolve and optionally send a synthetic Discord routing test."""
    settings = get_settings()
    _, channels_config, webhooks_config = _load_discord_routing(settings)
    competition = (
        channels_config.find_competition(competition_key=competition_key)
        if competition_key
        else None
    )
    if competition_key and competition is None:
        raise typer.BadParameter("Unknown Discord competition route")
    markdown = "```md\nTest routage Discord Football Predictor\n```"
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        result = DiscordDeliveryService(
            session,
            channels_config=channels_config,
            webhooks_config=webhooks_config,
            legacy_webhook_url=settings.discord_webhook_url,
            timeout=settings.discord_timeout_seconds,
        ).send_markdown(
            markdown,
            competition_key=competition_key,
            league_id=competition.league_id if competition else None,
            season=competition.season if competition else None,
            channel_key=channel,
            message_type=message_type,
            dry_run=not send,
            force=True,
        )
    console.print(
        f"Discord test status={result.status} "
        f"route={result.route.competition_key or 'global'}/{result.route.channel_key} "
        f"webhook_hash={result.webhook_hash or 'none'}"
    )


@app.command("discord-provision-webhooks")
def discord_provision_webhooks(
    channels: Path | None = typer.Option(
        None,
        "--channels-config",
        "--channels",
        help="Discord channels YAML.",
    ),
    output: Path = typer.Option(
        Path("config/discord_webhooks.local.yaml"),
        "--output",
        help="Local gitignored webhook config output.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Actually provision webhooks and write local config.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview routes without creating Discord webhooks.",
    ),
    force: bool = typer.Option(False, "--force", help="Reserved for future overwrite support."),
    only_competition: str | None = typer.Option(None, "--only-competition"),
    only_channel: str | None = typer.Option(None, "--only-channel"),
) -> None:
    """Optionally create Discord webhooks from configured channel IDs."""
    settings = get_settings()
    if yes and dry_run:
        raise typer.BadParameter("Use either --dry-run or --yes, not both")
    reference = load_api_football_reference(settings.api_football_reference_path)
    resolved_channels_path = _existing_or_example(
        channels or settings.discord_channels_config_path,
        Path("config/discord_channels.example.yaml"),
    )
    channels_config = load_discord_channels_config(
        resolved_channels_path,
        reference,
    )
    should_write = yes or (settings.discord_provision_webhooks_enabled and not dry_run)
    if should_write and not settings.discord_provision_webhooks_enabled and not yes:
        raise typer.BadParameter("Set DISCORD_PROVISION_WEBHOOKS_ENABLED=true or pass --yes")
    provisioner = None
    if should_write:
        if not settings.discord_bot_token:
            raise typer.BadParameter("DISCORD_BOT_TOKEN is required for provisioning")
        provisioner = DiscordWebhookProvisioner(
            settings.discord_bot_token,
            base_url=settings.discord_api_base_url,
            timeout=settings.discord_timeout_seconds,
        )
    routes = provision_webhooks(
        channels_config,
        provisioner=provisioner,
        dry_run=dry_run or not should_write,
        only_competition=only_competition,
        only_channel=only_channel,
    )
    if should_write:
        write_local_webhooks_config(output, routes)
        console.print(f"Discord webhooks written to {output} force={force}")
    else:
        console.print(f"Discord provisioning dry-run routes={len(routes)}")


@app.command("predict-today")
def predict_today(
    prediction_date: str | None = typer.Option(
        None,
        "--date",
        help="Date to scan, format YYYY-MM-DD. Defaults to the local date at prediction time.",
    ),
    window: DailyPredictionWindow = typer.Option(
        DailyPredictionWindow.NOW,
        "--window",
        help="Prediction window: early, mid, late, now, or all.",
    ),
    league: list[int] | None = typer.Option(
        None,
        "--league",
        help="Repeatable API-Football league_id filter, validated against docs reference.",
    ),
    season: int | None = typer.Option(None, "--season", help="Optional season filter."),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions YAML/JSON config. Defaults to settings.",
    ),
    model_dir: Path | None = typer.Option(
        Path("data/models/v1"),
        "--model-dir",
        help="Model directory or model.joblib path. Missing model falls back safely.",
    ),
    prediction_time: str | None = typer.Option(
        None,
        "--prediction-time",
        help="Prediction cutoff timestamp, ISO 8601. Defaults to now.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh-data",
        help="Explicitly refresh API-Football before prediction.",
    ),
    send_discord: bool = typer.Option(
        False,
        "--send-discord",
        help="Send each prediction to the routed Discord predictions channel.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist Discord route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print only, no Discord send."),
    force: bool = typer.Option(False, "--force", help="Bypass Discord automation dedupe."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum selected fixtures to predict."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also save raw API payload snapshots to disk during live refresh.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON summary only."),
    json_output_path: Path | None = typer.Option(
        None,
        "--json-output",
        help="Write JSON summary to this path.",
    ),
) -> None:
    """Automate predictions for fixtures scheduled on a date."""
    target_date = None
    if prediction_date is not None:
        try:
            target_date = date_type.fromisoformat(prediction_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
    if limit is not None and limit < 1:
        raise typer.BadParameter("--limit must be greater than 0")
    settings = get_settings()
    cutoff = _parse_optional_prediction_time(prediction_time)
    reference = load_api_football_reference(settings.api_football_reference_path)
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    if league:
        for league_id in league:
            _validate_league_id(settings, league_id, season, strict=True)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    api_client = None
    if refresh_data:
        api_client = _api_client_from_settings(settings)
    with session_scope(session_factory) as session:
        delivery = None
        if send_discord:
            _, channels_config, webhooks_config = _load_discord_routing(settings)
            delivery = DiscordDeliveryService(
                session,
                channels_config=channels_config,
                webhooks_config=webhooks_config,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            )
        try:
            summary = run_daily_predictions(
                target_date,
                league_ids=tuple(league or ()),
                window=window,
                send_discord=send_discord,
                refresh_data=refresh_data,
                dry_run=dry_run,
                session=session,
                reference=reference,
                players_reference=players_reference,
                competitions=competitions,
                season=season,
                model_dir=model_dir,
                api_client=api_client,
                discord_delivery=delivery,
                timezone_name=settings.app_timezone,
                force=force,
                print_only=print_only,
                limit=limit,
                save_raw=save_raw,
                now=cutoff,
            )
        finally:
            if api_client is not None:
                api_client.close()
    summary_payload = summary.as_dict()
    summary_json = json.dumps(summary_payload, indent=2, sort_keys=True)
    if json_output_path is not None:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        json_output_path.write_text(summary_json + "\n", encoding="utf-8")
    if json_output:
        console.out(summary_json)
    else:
        console.print(
            "Prediction automation "
            f"date={summary.target_date.isoformat()} window={summary.window.value} "
            f"found={summary.found} predicted={summary.predicted} sent={summary.sent} "
            f"duplicates={summary.duplicate_skipped} skipped={summary.skipped} "
            f"failed={summary.failed}"
        )


@app.command("predict-today-v3")
def predict_today_v3(
    prediction_date: str | None = typer.Option(
        None,
        "--date",
        help="Date to scan, format YYYY-MM-DD. Defaults to the local date at prediction time.",
    ),
    window: DailyPredictionWindow = typer.Option(
        DailyPredictionWindow.LATE,
        "--window",
        help="Prediction window: early, mid, late, now, or all. V3 shadow defaults to late.",
    ),
    league: list[int] | None = typer.Option(
        None,
        "--league",
        help="Repeatable API-Football league_id filter, validated against docs reference.",
    ),
    season: int | None = typer.Option(None, "--season", help="Optional season filter."),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Competitions YAML/JSON config. Defaults to settings.",
    ),
    model_dir: Path | None = typer.Option(
        Path("data/models/v3"),
        "--model-dir",
        help="Directory containing V3 component artifacts.",
    ),
    v2_model_dir: Path | None = typer.Option(
        None,
        "--v2-model-dir",
        help="Optional V2 model directory used as a V3 signal.",
    ),
    prediction_time: str | None = typer.Option(
        None,
        "--prediction-time",
        help="Prediction cutoff timestamp, ISO 8601. Defaults to now.",
    ),
    refresh_data: bool = typer.Option(
        False,
        "--refresh-data/--no-refresh-data",
        help="Explicitly refresh API-Football before prediction.",
    ),
    send_discord: bool = typer.Option(
        False,
        "--send-discord",
        help="Send V3 Discord output. Requires --production-mode for live sends.",
    ),
    shadow_mode: bool = typer.Option(
        True,
        "--shadow-mode/--production-mode",
        help="Shadow mode logs V3 without live Discord sends; production mode allows live sends.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Persist Discord route without sending."),
    print_only: bool = typer.Option(False, "--print-only", help="Print only, no Discord send."),
    force: bool = typer.Option(False, "--force", help="Bypass Discord dry-run dedupe."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum selected fixtures to predict."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also save raw API payload snapshots to disk during live refresh.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON summary only."),
    json_output_path: Path | None = typer.Option(
        None,
        "--json-output",
        help="Write JSON summary to this path.",
    ),
) -> None:
    """Run V3 daily predictions, shadow-safe by default."""
    target_date = None
    if prediction_date is not None:
        try:
            target_date = date_type.fromisoformat(prediction_date)
        except ValueError as exc:
            raise typer.BadParameter("--date must use YYYY-MM-DD format") from exc
    if limit is not None and limit < 1:
        raise typer.BadParameter("--limit must be greater than 0")
    if shadow_mode and send_discord and not dry_run and not print_only:
        raise typer.BadParameter(
            "V3 shadow mode blocks live Discord sends; use --production-mode or "
            "--dry-run/--print-only"
        )

    settings = get_settings()
    cutoff = _parse_optional_prediction_time(prediction_time)
    reference = load_api_football_reference(settings.api_football_reference_path)
    players_reference = load_players_reference(settings.api_football_players_reference_path)
    competitions = _load_competitions(settings, config or settings.competitions_config_path)
    if league:
        for league_id in league:
            _validate_league_id(settings, league_id, season, strict=True)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    api_client = None
    if refresh_data:
        api_client = _api_client_from_settings(settings)

    discord_requested = send_discord or dry_run or print_only
    with session_scope(session_factory) as session:
        delivery = None
        if discord_requested:
            if send_discord:
                _, channels_config, webhooks_config = _load_discord_routing(settings)
            else:
                channels_config = None
                webhooks_config = None
            delivery = DiscordDeliveryService(
                session,
                channels_config=channels_config,
                webhooks_config=webhooks_config,
                legacy_webhook_url=settings.discord_webhook_url if send_discord else None,
                timeout=settings.discord_timeout_seconds,
            )
        try:
            summary = run_daily_predictions_v3(
                target_date,
                league_ids=tuple(league or ()),
                window=window,
                send_discord=discord_requested,
                refresh_data=refresh_data,
                dry_run=dry_run,
                session=session,
                reference=reference,
                players_reference=players_reference,
                competitions=competitions,
                season=season,
                model_dir=model_dir,
                v2_model_dir=v2_model_dir,
                api_client=api_client,
                discord_delivery=delivery,
                timezone_name=settings.app_timezone,
                force=force,
                print_only=print_only,
                limit=limit,
                save_raw=save_raw,
                now=cutoff,
                shadow_mode=shadow_mode,
            )
        finally:
            if api_client is not None:
                api_client.close()
    summary_payload = summary.as_dict()
    summary_json = json.dumps(summary_payload, indent=2, sort_keys=True)
    if json_output_path is not None:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        json_output_path.write_text(summary_json + "\n", encoding="utf-8")
    if json_output:
        console.out(summary_json)
    else:
        console.print(
            f"Prediction automation V3 {'shadow' if summary.shadow_mode else 'production'} "
            f"date={summary.target_date.isoformat()} window={summary.window.value} "
            f"found={summary.found} predicted={summary.predicted} sent={summary.sent} "
            f"duplicates={summary.duplicate_skipped} skipped={summary.skipped} "
            f"failed={summary.failed}"
        )


@app.command("ingest-fixtures")
def ingest_fixtures(
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="Validated API-Football league_id.",
    ),
    season: int | None = typer.Option(None, "--season", help="API-Football season."),
    fixture_date: str | None = typer.Option(
        None,
        "--date",
        help="Fixture date for API-Football /fixtures, format YYYY-MM-DD.",
    ),
    team_id: int | None = typer.Option(None, "--team-id", help="Validated API-Football team_id."),
    last: int | None = typer.Option(None, "--last", help="Fetch last N fixtures for team_id."),
    next_count: int | None = typer.Option(
        None,
        "--next",
        help="Fetch next N fixtures for team_id.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    prefer_docs: bool = typer.Option(
        False,
        "--prefer-docs",
        help="Seed fixtures and standings from docs reference instead of live API.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
) -> None:
    """Ingest fixtures from docs/reference or API-Football live."""
    docs_supported = team_id is None
    effective_prefer_docs = prefer_docs or (not refresh_api and docs_supported)
    if not refresh_api and not effective_prefer_docs:
        console.print("Fixture ingestion requires --prefer-docs or explicit --refresh-api.")
        raise typer.Exit(2)
    settings = get_settings()
    _validate_fixture_ingestion_args(
        settings,
        league_id,
        season,
        fixture_date,
        team_id,
        last,
        next_count,
        strict_reference=effective_prefer_docs or not refresh_api,
    )
    if effective_prefer_docs and fixture_date is None and (league_id is None or season is None):
        raise typer.BadParameter("--prefer-docs fixture seed requires --league-id and --season")

    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    summary = MatchIngestionSummary()
    try:
        if effective_prefer_docs:
            summary.merge(
                seed_fixtures_and_standings_from_reference(
                    session,
                    settings.api_football_reference_path,
                    league_id=league_id,
                    season=season,
                    fixture_date=date_type.fromisoformat(fixture_date)
                    if fixture_date is not None
                    else None,
                    include_fixtures=True,
                    include_standings=fixture_date is None,
                )
            )
        if refresh_api:
            with _api_client_from_settings(settings) as client:
                service = FixtureIngestionService(session, client, save_raw=save_raw)
                if fixture_date is not None:
                    summary.merge(
                        service.ingest_date(
                            date_type.fromisoformat(fixture_date),
                            league_id=league_id,
                            season=season,
                        )
                    )
                elif league_id is not None and season is not None:
                    summary.merge(service.ingest_league_season(league_id, season))
                elif team_id is not None and last is not None:
                    summary.merge(service.ingest_team_last(team_id, last))
                elif team_id is not None and next_count is not None:
                    summary.merge(service.ingest_team_next(team_id, next_count))
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("ingest-standings")
def ingest_standings(
    league_id: int = typer.Option(
        ...,
        "--league",
        "--league-id",
        help="Validated API-Football league_id.",
    ),
    season: int = typer.Option(..., "--season", help="API-Football season."),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    prefer_docs: bool = typer.Option(
        False,
        "--prefer-docs",
        help="Seed standings from docs reference instead of live API.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
) -> None:
    """Ingest standings snapshots from docs/reference or API-Football live."""
    effective_prefer_docs = prefer_docs or not refresh_api
    settings = get_settings()
    _validate_league_id(
        settings,
        league_id,
        season,
        strict=effective_prefer_docs or not refresh_api,
    )
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    summary = MatchIngestionSummary()
    try:
        if effective_prefer_docs:
            summary.merge(
                seed_fixtures_and_standings_from_reference(
                    session,
                    settings.api_football_reference_path,
                    league_id=league_id,
                    season=season,
                    include_fixtures=False,
                    include_standings=True,
                )
            )
        if refresh_api:
            with _api_client_from_settings(settings) as client:
                service = StandingIngestionService(session, client, save_raw=save_raw)
                summary.merge(
                    service.ingest_league_season(
                        league_id,
                        season,
                    )
                )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("ingest-fixture-details")
def ingest_fixture_details(
    fixture: int | None = typer.Option(
        None,
        "--fixture",
        help="API-Football fixture_id already stored in the local DB.",
    ),
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="Optional API-Football league_id filter for batch mode.",
    ),
    season: int | None = typer.Option(None, "--season", help="Optional season filter."),
    fixture_date: str | None = typer.Option(
        None,
        "--date",
        help="Optional fixture date filter for batch mode, format YYYY-MM-DD.",
    ),
    date_from: str | None = typer.Option(
        None,
        "--from-date",
        help="Optional inclusive start date for batch mode, format YYYY-MM-DD.",
    ),
    date_to: str | None = typer.Option(
        None,
        "--to-date",
        help="Optional inclusive end date for batch mode, format YYYY-MM-DD.",
    ),
    days_back: int | None = typer.Option(
        None,
        "--days-back",
        help="Use fixtures from APP_TIMEZONE today minus N days through today.",
    ),
    status: list[str] | None = typer.Option(
        None,
        "--status",
        help=(
            "Repeatable fixture status_short filter. Also accepts whitespace lists "
            "like 'FT AET PEN'."
        ),
    ),
    limit: int | None = typer.Option(None, "--limit", help="Maximum fixtures in batch mode."),
    include_upcoming: bool = typer.Option(
        False,
        "--include-upcoming",
        help="In batch mode, include upcoming fixtures when --status is not provided.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    only: list[str] | None = typer.Option(
        None,
        "--only",
        help="Repeatable detail key: statistics, events, lineups, players, injuries, predictions.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
    delay_seconds: float = typer.Option(
        0.0,
        "--delay-seconds",
        help="Sleep between fixtures in batch mode to reduce API rate pressure.",
    ),
    stop_on_rate_limit: bool = typer.Option(
        True,
        "--stop-on-rate-limit/--continue-on-rate-limit",
        help="Stop batch ingestion after the first API-Football rate-limit response.",
    ),
    skip_if_complete: bool = typer.Option(
        False,
        "--skip-if-complete",
        help=(
            "Skip detail endpoints already present in DB or already known as no-content. "
            "This saves API quota in repeated historical refreshes."
        ),
    ),
) -> None:
    """Ingest detailed dynamic data for one fixture or DB-filtered fixture batch."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    parsed_date, parsed_from, parsed_to, status_values = _validate_fixture_details_cli_args(
        settings,
        fixture,
        league_id,
        season,
        fixture_date,
        date_from,
        date_to,
        days_back,
        status,
        limit,
    )
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    try:
        reference = load_api_football_reference(settings.api_football_reference_path)
        players_reference = load_players_reference(settings.api_football_players_reference_path)
        with _api_client_from_settings(settings) as client:
            service = FixtureDetailsIngestionService(
                session,
                client,
                reference=reference,
                players_reference=players_reference,
                save_raw=save_raw,
                unknown_players_path=DEFAULT_UNKNOWN_PLAYERS_PATH,
            )
            if fixture is not None:
                if only:
                    summary = service.ingest_fixture_details(
                        fixture,
                        include=only,
                        skip_if_complete=skip_if_complete,
                    )
                else:
                    summary = service.ingest_fixture_details(
                        fixture,
                        skip_if_complete=skip_if_complete,
                    )
            else:
                effective_statuses = status_values
                if effective_statuses is None and not include_upcoming:
                    effective_statuses = ["FT"]
                summary = service.ingest_fixture_details_for_filters(
                    league_id=league_id,
                    season=season,
                    fixture_date=parsed_date,
                    date_from=parsed_from,
                    date_to=parsed_to,
                    statuses=effective_statuses,
                    limit=limit,
                    include=only,
                    stop_on_rate_limit=stop_on_rate_limit,
                    delay_seconds=delay_seconds,
                    skip_if_complete=skip_if_complete,
                )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("ingest-fixture-details-batch")
def ingest_fixture_details_batch(
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="Optional API-Football league_id filter.",
    ),
    season: int | None = typer.Option(None, "--season", help="Optional season filter."),
    fixture_date: str | None = typer.Option(
        None,
        "--date",
        help="Optional fixture date filter, format YYYY-MM-DD.",
    ),
    date_from: str | None = typer.Option(
        None,
        "--from-date",
        help="Optional inclusive start date filter, format YYYY-MM-DD.",
    ),
    date_to: str | None = typer.Option(
        None,
        "--to-date",
        help="Optional inclusive end date filter, format YYYY-MM-DD.",
    ),
    days_back: int | None = typer.Option(
        None,
        "--days-back",
        help="Use fixtures from APP_TIMEZONE today minus N days through today.",
    ),
    status: list[str] | None = typer.Option(
        None,
        "--status",
        help="Repeatable fixture status_short filter such as FT, AET or PEN.",
    ),
    limit: int | None = typer.Option(None, "--limit", help="Maximum fixtures to process."),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    only: list[str] | None = typer.Option(
        None,
        "--only",
        help="Repeatable detail key: statistics, events, lineups, players, injuries, predictions.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
    delay_seconds: float = typer.Option(
        0.0,
        "--delay-seconds",
        help="Sleep between fixtures in batch mode to reduce API rate pressure.",
    ),
    stop_on_rate_limit: bool = typer.Option(
        True,
        "--stop-on-rate-limit/--continue-on-rate-limit",
        help="Stop batch ingestion after the first API-Football rate-limit response.",
    ),
    skip_if_complete: bool = typer.Option(
        False,
        "--skip-if-complete",
        help="Skip detail endpoints already present in DB or already known as no-content.",
    ),
) -> None:
    """Compatibility command for fixture detail batch ingestion."""
    ingest_fixture_details(
        fixture=None,
        league_id=league_id,
        season=season,
        fixture_date=fixture_date,
        date_from=date_from,
        date_to=date_to,
        days_back=days_back,
        status=status,
        limit=limit,
        include_upcoming=False,
        refresh_api=refresh_api,
        only=only,
        dry_run=dry_run,
        save_raw=save_raw,
        delay_seconds=delay_seconds,
        stop_on_rate_limit=stop_on_rate_limit,
        skip_if_complete=skip_if_complete,
    )


@app.command("ingest-odds")
def ingest_odds(
    fixture: int | None = typer.Option(
        None,
        "--fixture",
        help="API-Football fixture_id for prematch odds.",
    ),
    odds_date: str | None = typer.Option(
        None,
        "--date",
        help="Odds date for API-Football /odds, format YYYY-MM-DD.",
    ),
    league_id: int | None = typer.Option(
        None,
        "--league",
        "--league-id",
        help="API-Football league_id for odds ingestion.",
    ),
    season: int | None = typer.Option(None, "--season", help="API-Football season."),
    bookmaker_ids: list[int] | None = typer.Option(
        None,
        "--bookmaker",
        help="Repeatable bookmaker_id filter validated against local docs when possible.",
    ),
    refresh_api: bool = typer.Option(
        False,
        "--refresh-api",
        help="Explicitly allow live API-Football calls.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run ingestion then roll back."),
    save_raw: bool = typer.Option(
        False,
        "--save-raw",
        help="Also write API live payloads to disk through ApiFootballClient.",
    ),
) -> None:
    """Ingest prematch 1X2 odds from API-Football."""
    _require_refresh_api(refresh_api)
    settings = get_settings()
    parsed_date = _validate_odds_ingestion_args(
        settings,
        fixture,
        league_id,
        season,
        odds_date,
        bookmaker_ids,
    )
    reference = load_api_football_reference(settings.api_football_reference_path)
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    session = session_factory()
    try:
        with _api_client_from_settings(settings) as client:
            service = OddsIngestionService(
                session,
                client,
                reference=reference,
                market_bet_name=settings.market_1x2_bet_name,
                market_bet_id=settings.market_1x2_bet_id,
                save_raw=save_raw,
            )
            if fixture is not None:
                summary = service.ingest_odds_for_fixture(
                    fixture,
                    bookmaker_ids=bookmaker_ids,
                )
            elif parsed_date is not None:
                summary = service.ingest_odds_by_date(
                    parsed_date,
                    league_id=league_id,
                    season=season,
                    bookmaker_ids=bookmaker_ids,
                )
            else:
                if league_id is None or season is None:
                    raise typer.BadParameter("--league and --season must be provided together")
                summary = service.ingest_odds_by_league_season(
                    league_id,
                    season,
                    bookmaker_ids=bookmaker_ids,
                )
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    output = summary.as_dict()
    output["dry_run"] = int(dry_run)
    console.print(output)


@app.command("odds-features")
def odds_features_command(
    fixture: int = typer.Option(
        ...,
        "--fixture",
        help="API-Football fixture_id used to read local prematch odds snapshots.",
    ),
    as_of: str | None = typer.Option(
        None,
        "--as-of",
        help="Point-in-time cutoff for odds snapshots. Defaults to now.",
    ),
) -> None:
    """Compute local market probabilities and odds movement without live API calls."""
    settings = get_settings()
    _validate_fixture_id(settings, fixture, strict=False)
    parsed_as_of = parse_datetime(as_of) if as_of is not None else utc_now()
    if parsed_as_of is None:
        raise typer.BadParameter("--as-of must be an ISO datetime")
    reference = load_api_football_reference(settings.api_football_reference_path)
    bet_id = resolve_1x2_bet_id(
        reference,
        configured_bet_id=settings.market_1x2_bet_id,
        configured_bet_name=settings.market_1x2_bet_name,
    )
    engine, session_factory = _engine_and_session(settings)
    init_db(engine)
    with session_scope(session_factory) as session:
        consensus = compute_market_consensus(
            session,
            fixture,
            as_of_time=parsed_as_of,
            bet_id=bet_id,
        )
        movement = compute_odds_movement(
            session,
            fixture,
            parsed_as_of,
            bet_id=bet_id,
        )

    if consensus is None:
        console.print("No prematch 1X2 odds snapshots available before the requested time.")
        raise typer.Exit(2)
    console.print(
        {
            "fixture_id": fixture,
            "as_of_time": parsed_as_of.isoformat(),
            "p_market_home": round(consensus.p_market_home, 6),
            "p_market_draw": round(consensus.p_market_draw, 6),
            "p_market_away": round(consensus.p_market_away, 6),
            "market_confidence": round(consensus.market_confidence, 6),
            "market_dispersion": round(consensus.market_dispersion, 6),
            "bookmaker_count": consensus.bookmaker_count,
            "delta_home": movement.delta_home,
            "delta_draw": movement.delta_draw,
            "delta_away": movement.delta_away,
        }
    )


register_backtesting_commands(app)
register_worldcup_commands(app)
register_worldcup_combo_commands(app)
register_ou_commands(app)


def main() -> None:
    try:
        app()
    except FootballPredictorError as exc:
        console.print(f"Error: {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    main()
