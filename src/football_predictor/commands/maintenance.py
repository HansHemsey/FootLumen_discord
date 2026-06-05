"""Maintenance and local reference CLI commands."""

# ruff: noqa: F403,F405,I001

from __future__ import annotations

from football_predictor.commands.shared import *  # noqa: F403,F405


def register(app: typer.Typer) -> None:
    @app.command("init-db")
    def init_db_command() -> None:
        """Create local database tables."""
        settings = get_settings()
        engine = create_db_engine(settings.database_url)
        init_db(engine)
        console.print("Database initialized")

    @app.command("seed-reference-from-docs")
    def seed_reference_from_docs_command(
        reference: Path = typer.Option(
            Path("docs/api_football_reference.json"),
            "--reference",
            help="Machine-readable competitions reference JSON.",
        ),
        players: Path = typer.Option(
            Path("docs/api_football_players_reference.json"),
            "--players",
            help="Machine-readable players reference JSON.",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Load and validate docs references, then roll back DB writes.",
        ),
    ) -> None:
        """Seed local DB from docs JSON without network calls."""
        settings = get_settings()
        engine, session_factory = _engine_and_session(settings)
        init_db(engine)
        session = session_factory()
        try:
            summary = seed_reference_from_docs(session, reference, players)
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
