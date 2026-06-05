"""World Cup combo CLI commands."""

# ruff: noqa: F403,F405,I001

from __future__ import annotations

from football_predictor.commands.shared import *  # noqa: F403,F405


def register(app: typer.Typer) -> None:
    @app.command("worldcup-combos-run")
    def worldcup_combos_run(
        run_date: str | None = typer.Option(None, "--date"),
        config_path: Path | None = typer.Option(None, "--config"),
        execute: bool = typer.Option(False, "--execute/--dry-run"),
        json_output: Path | None = typer.Option(None, "--json-output"),
    ) -> None:
        """Generate World Cup combo tickets; persist only with --execute."""
        from football_predictor.world_cup_combos.config import load_world_cup_combo_config
        from football_predictor.world_cup_combos.persistence import ensure_combo_tables
        from football_predictor.world_cup_combos.worldcup_combo_run_service import (
            WorldCupComboRunService,
        )

        settings = get_settings()
        resolved_config_path = config_path or settings.world_cup_combos_config_path
        combo_config = load_world_cup_combo_config(resolved_config_path)
        target_date = date_type.fromisoformat(run_date) if run_date else None
        engine, session_factory = _engine_and_session(settings)
        if execute:
            ensure_combo_tables(engine)
        with session_scope(session_factory) as session:
            summary = WorldCupComboRunService(session, combo_config).run(
                target_date=target_date,
                execute=execute,
            )
            payload = summary.as_dict()
        payload["config_path"] = str(resolved_config_path)
        if json_output is not None:
            json_output.parent.mkdir(parents=True, exist_ok=True)
            json_output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        console.print_json(data=payload)

    @app.command("worldcup-combos-publish")
    def worldcup_combos_publish(
        run_date: str | None = typer.Option(None, "--date"),
        config_path: Path | None = typer.Option(None, "--config"),
        execute: bool = typer.Option(False, "--execute/--dry-run"),
        json_output: Path | None = typer.Option(None, "--json-output"),
    ) -> None:
        """Publish persisted World Cup combo tickets to staff; dry-run unless --execute."""
        from football_predictor.db import models as db_models
        from football_predictor.world_cup_combos.config import load_world_cup_combo_config
        from football_predictor.world_cup_combos.enums import ComboTicketStatus
        from football_predictor.world_cup_combos.worldcup_combo_lock_service import (
            combo_ticket_candidate_from_payload,
        )
        from football_predictor.world_cup_combos.worldcup_combo_publication_service import (
            WorldCupComboPublicationService,
        )

        publishable_statuses = {
            ComboTicketStatus.DRAFT.value,
            ComboTicketStatus.WATCHLIST_STAFF.value,
            ComboTicketStatus.PRE_LOCK_REVALIDATION.value,
            ComboTicketStatus.LOCKED.value,
            ComboTicketStatus.STAFF_ONLY.value,
            ComboTicketStatus.NO_BET.value,
        }
        settings = get_settings()
        resolved_config_path = config_path or settings.world_cup_combos_config_path
        combo_config = load_world_cup_combo_config(resolved_config_path)
        target_date = date_type.fromisoformat(run_date) if run_date else None
        if not combo_config.enabled:
            payload = {
                "enabled": False,
                "execute": execute,
                "target_date": run_date,
                "config_path": str(resolved_config_path),
                "results": [],
                "message": "worldcup_combos disabled",
            }
            if json_output is not None:
                json_output.parent.mkdir(parents=True, exist_ok=True)
                json_output.write_text(
                    json.dumps(payload, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
            console.print_json(data=payload)
            return

        engine, session_factory = _engine_and_session(settings)
        _, channels, webhooks = _load_discord_routing(settings)
        with session_scope(session_factory) as session:
            delivery = DiscordDeliveryService(
                session,
                channels_config=channels,
                webhooks_config=webhooks,
                legacy_webhook_url=settings.discord_webhook_url,
                timeout=settings.discord_timeout_seconds,
            )
            service = WorldCupComboPublicationService(
                session,
                combo_config,
                delivery_service=delivery,
            )
            stmt = (
                select(db_models.ComboTicket)
                .where(db_models.ComboTicket.competition_key == combo_config.competition_key)
                .where(db_models.ComboTicket.status.in_(publishable_statuses))
                .order_by(db_models.ComboTicket.combo_date.asc(), db_models.ComboTicket.id.asc())
            )
            if target_date is not None:
                stmt = stmt.where(db_models.ComboTicket.combo_date == target_date)
            results = []
            for record in session.execute(stmt).scalars():
                ticket = combo_ticket_candidate_from_payload(record.payload_json)
                dry_run = not execute
                if record.status == ComboTicketStatus.LOCKED.value:
                    result = service.publish_locked(
                        ticket,
                        locked_at=utc_now(),
                        dry_run=dry_run,
                        execute=execute,
                    )
                elif record.status == ComboTicketStatus.NO_BET.value:
                    result = service.publish_no_bet(
                        reason=ticket.no_publish_reason or "no_bet",
                        ticket=ticket,
                        dry_run=dry_run,
                        execute=execute,
                    )
                else:
                    result = service.publish_watchlist_staff(
                        ticket,
                        dry_run=dry_run,
                        execute=execute,
                    )
                results.append(result.__dict__)
        payload = {
            "enabled": True,
            "execute": execute,
            "target_date": target_date.isoformat() if target_date else None,
            "config_path": str(resolved_config_path),
            "results": results,
        }
        if json_output is not None:
            json_output.parent.mkdir(parents=True, exist_ok=True)
            json_output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        console.print_json(data=payload)
