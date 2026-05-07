#!/usr/bin/env python
"""Ingest historical O/U 2.5 average odds from a CSV file into odds_snapshots.

Usage:
    python scripts/ingest_historical_ou_csv.py [--csv PATH] [--league-id INT] [--season INT]

Default CSV: data/reference/Ligue1-2025-2026_histo_OU_odds.csv

CSV format expected:
    League,Date,HomeTeam,AwayTeam,Avg>2.5,Avg<2.5

The script:
  1. Normalises team names to match the DB (configurable via NAME_MAP)
  2. Matches each row to a fixture_id by (date_day, home_name, away_name)
  3. Ingests odds into odds_snapshots with bookmaker_id=9999 ("Market Average (CSV)")
     and fetched_at = kickoff_utc - 24h (visible by the feature builder at prediction offsets >= 24h)
  4. Writes an enriched CSV alongside the source with _enriched suffix

Re-running is safe: upsert_by_fields deduplicates on
(fixture_id, bookmaker_id, bet_id, fetched_at, is_live).
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# make src/ importable when run from repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from football_predictor.config.settings import Settings
from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from sqlalchemy import select, text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Team name mapping: CSV value → DB name
# Extend this dict whenever a new season CSV uses different short names.
# ---------------------------------------------------------------------------
NAME_MAP: dict[str, str] = {
    "Brest":    "Stade Brestois 29",
    "Paris SG": "Paris Saint Germain",
    "Man United": "Manchester United",
    "Man City":   "Manchester City",
    "Spurs":      "Tottenham",
}

BOOKMAKER_ID   = 9999
BOOKMAKER_NAME = "Market Average (CSV)"
BET_ID         = 5
BET_NAME       = "Goals Over/Under"
PARIS          = ZoneInfo("Europe/Paris")
UTC            = ZoneInfo("UTC")


def _norm(name: str) -> str:
    return NAME_MAP.get(name.strip(), name.strip())


def _parse_odd(value: str) -> float | None:
    try:
        cleaned = value.strip().replace(",", ".")
        # handle "02.05" → "2.05"
        f = float(cleaned)
        return f if f > 1.0 else None
    except (ValueError, TypeError):
        return None


def _build_fixture_index(
    session,
    league_id: int,
    season: int,
) -> dict[tuple[str, str, str], tuple[int, datetime, int, int]]:
    rows = session.execute(text("""
        SELECT f.fixture_id, f.date, t_h.name, t_a.name, f.league_id, f.season
        FROM fixtures f
        JOIN teams t_h ON t_h.team_id = f.home_team_id
        JOIN teams t_a ON t_a.team_id = f.away_team_id
        WHERE f.league_id = :lid AND f.season = :s
    """), {"lid": league_id, "s": season}).fetchall()

    idx: dict[tuple[str, str, str], tuple[int, datetime, int, int]] = {}
    for fixture_id, date_str, home, away, lid, szn in rows:
        dt_utc = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
        day = dt_utc.astimezone(PARIS).strftime("%Y%m%d")
        idx[(day, home, away)] = (fixture_id, dt_utc, lid, szn)
    return idx


def ingest_csv(
    csv_path: Path,
    *,
    league_id: int,
    season: int,
    dry_run: bool = False,
) -> None:
    s = Settings()
    engine = create_db_engine(s.database_url)
    sf = create_session_factory(engine)

    enriched_rows: list[dict] = []
    unmatched: list[tuple] = []
    parse_errors: list[str] = []

    with session_scope(sf) as sess:
        idx = _build_fixture_index(sess, league_id, season)
        logger.info("Loaded %d fixtures for league=%d season=%d", len(idx), league_id, season)

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                date_str = row.get("Date", "").strip()
                home_csv = row.get("HomeTeam", "").strip()
                away_csv = row.get("AwayTeam", "").strip()
                over_str = row.get("Avg>2.5", "").strip()
                under_str = row.get("Avg<2.5", "").strip()

                try:
                    d = datetime.strptime(date_str, "%d/%m/%Y")
                except ValueError:
                    parse_errors.append(f"Bad date: {date_str} ({home_csv} vs {away_csv})")
                    continue

                odd_over  = _parse_odd(over_str)
                odd_under = _parse_odd(under_str)
                if odd_over is None or odd_under is None:
                    parse_errors.append(f"Bad odds: over={over_str!r} under={under_str!r} ({home_csv} vs {away_csv})")
                    continue

                key = (d.strftime("%Y%m%d"), _norm(home_csv), _norm(away_csv))
                match = idx.get(key)
                if match is None:
                    unmatched.append((date_str, home_csv, away_csv))
                    continue

                fixture_id, kickoff_utc, lid, szn = match
                fetched_at = kickoff_utc - timedelta(hours=24)
                enriched_rows.append({
                    "fixture_id":  fixture_id,
                    "league_id":   lid,
                    "season":      szn,
                    "home":        _norm(home_csv),
                    "away":        _norm(away_csv),
                    "odd_over":    odd_over,
                    "odd_under":   odd_under,
                    "fetched_at":  fetched_at,
                    "kickoff_utc": kickoff_utc,
                })

        logger.info("Matched %d/%d rows (%d unmatched, %d parse errors)",
                    len(enriched_rows), len(enriched_rows) + len(unmatched),
                    len(unmatched), len(parse_errors))
        if unmatched:
            logger.warning("Unmatched rows:")
            for u in unmatched:
                logger.warning("  %s", u)
        if parse_errors:
            logger.warning("Parse errors:")
            for e in parse_errors:
                logger.warning("  %s", e)

        if dry_run:
            logger.info("Dry run — no DB writes.")
            return

        # Ensure pseudo-bookmaker exists
        existing_bk = sess.execute(
            select(models.Bookmaker).where(models.Bookmaker.bookmaker_id == BOOKMAKER_ID)
        ).scalar_one_or_none()
        if existing_bk is None:
            sess.add(models.Bookmaker(bookmaker_id=BOOKMAKER_ID, name=BOOKMAKER_NAME))
            sess.flush()
            logger.info("Created bookmaker id=%d name=%s", BOOKMAKER_ID, BOOKMAKER_NAME)

        inserted = 0
        errors: list[str] = []
        for r in enriched_rows:
            try:
                match_fields = {
                    "fixture_id":   r["fixture_id"],
                    "bookmaker_id": BOOKMAKER_ID,
                    "bet_id":       BET_ID,
                    "fetched_at":   r["fetched_at"],
                    "is_live":      False,
                }
                update_fields = {
                    "league_id":      r["league_id"],
                    "season":         r["season"],
                    "bookmaker_name": BOOKMAKER_NAME,
                    "bet_name":       BET_NAME,
                    "odd_home":       r["odd_over"],
                    "odd_draw":       None,
                    "odd_away":       r["odd_under"],
                    "payload_json": {
                        "home": r["odd_over"],
                        "away": r["odd_under"],
                        "ingestion_source": "csv_historical",
                        "threshold": 2.5,
                    },
                }
                upsert_by_fields(sess, models.OddsSnapshot, match_fields, update_fields)
                inserted += 1
            except Exception as exc:
                errors.append(f"fixture={r['fixture_id']}: {exc}")

        sess.flush()
        logger.info("DB: %d inserted, %d errors", inserted, len(errors))
        for e in errors[:10]:
            logger.error("  %s", e)

    # Write enriched CSV
    out_path = csv_path.with_name(csv_path.stem + "_enriched.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fixture_id", "league_id", "season", "HomeTeam", "AwayTeam",
                    "Avg>2.5", "Avg<2.5", "fetched_at", "kickoff_utc"])
        for r in enriched_rows:
            w.writerow([r["fixture_id"], r["league_id"], r["season"],
                        r["home"], r["away"],
                        r["odd_over"], r["odd_under"],
                        r["fetched_at"].isoformat(), r["kickoff_utc"].isoformat()])
    logger.info("Enriched CSV written: %s", out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", type=Path,
                        default=Path("data/reference/Ligue1-2025-2026_histo_OU_odds.csv"))
    parser.add_argument("--league-id", type=int, default=61)
    parser.add_argument("--season",    type=int, default=2025)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.csv.exists():
        logger.error("CSV not found: %s", args.csv)
        sys.exit(1)

    ingest_csv(args.csv, league_id=args.league_id, season=args.season, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
