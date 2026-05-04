"""Weekly Discord scorecard for published predictions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.discord.formatter import CODE_CLOSE, CODE_OPEN, truncate_discord_message
from football_predictor.discord.service import DiscordDeliveryService

WEEKLY_SCORE_CHANNEL = "score_pronos_semaine"
WEEKLY_SCORE_MESSAGE_TYPE = "weekly_prediction_score"
WEEKLY_SCORE_REPORT_KIND = "weekly_prediction_score"
FINISHED_STATUSES = {"FT", "AET", "PEN"}
DISCORD_SAFE_LIMIT = 1900

JsonDict = dict[str, object]


@dataclass(frozen=True)
class WeeklyScoreLine:
    fixture_id: int
    fixture_date: datetime | None
    match_label: str
    predicted: str
    actual: str | None
    score_label: str
    confidence_label: str
    confidence_score: float | None
    status: str
    correct: bool | None


@dataclass(frozen=True)
class WeeklyScoreReport:
    week_key: str
    week_start: date
    week_end: date
    title_suffix: str
    lines: list[WeeklyScoreLine]

    @property
    def total_predictions(self) -> int:
        return len(self.lines)

    @property
    def completed(self) -> int:
        return sum(1 for line in self.lines if line.correct is not None)

    @property
    def correct(self) -> int:
        return sum(1 for line in self.lines if line.correct is True)

    @property
    def incorrect(self) -> int:
        return sum(1 for line in self.lines if line.correct is False)

    @property
    def pending(self) -> int:
        return 0

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.completed if self.completed else None


@dataclass(frozen=True)
class WeeklyScorePublishResult:
    week_key: str
    status: str
    message_count: int
    discord_message_ids: list[int] = field(default_factory=list)
    replaced_count: int = 0
    replace_warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> JsonDict:
        return {
            "week_key": self.week_key,
            "status": self.status,
            "message_count": self.message_count,
            "discord_message_ids": self.discord_message_ids,
            "replaced_count": self.replaced_count,
            "replace_warnings": self.replace_warnings,
        }


@dataclass(frozen=True)
class WeeklyScorePublishSummary:
    target_date: date
    results: list[WeeklyScorePublishResult]

    @property
    def sent(self) -> int:
        return sum(1 for result in self.results if result.status == "sent")

    @property
    def dry_run(self) -> int:
        return sum(1 for result in self.results if result.status == "dry_run")

    @property
    def print_only(self) -> int:
        return sum(1 for result in self.results if result.status == "print_only")

    def as_dict(self) -> JsonDict:
        return {
            "target_date": self.target_date.isoformat(),
            "sent": self.sent,
            "dry_run": self.dry_run,
            "print_only": self.print_only,
            "results": [result.as_dict() for result in self.results],
        }


def publish_weekly_prediction_score(
    *,
    session: Session,
    delivery: DiscordDeliveryService,
    target_date: date,
    timezone_name: str = "Europe/Paris",
    include_previous_week_finalization: bool = True,
    dry_run: bool = False,
    print_only: bool = False,
    force: bool = False,
    replace_current_week: bool = True,
    echo: Callable[[str], None] | None = None,
) -> WeeklyScorePublishSummary:
    """Publish current weekly score, plus previous week finalization on Mondays."""
    reports = build_weekly_score_reports(
        session,
        target_date=target_date,
        timezone_name=timezone_name,
        include_previous_week_finalization=include_previous_week_finalization,
    )
    results = [
        _publish_report(
            delivery,
            report,
            timezone_name=timezone_name,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            replace_current_week=replace_current_week,
            echo=echo,
        )
        for report in reports
    ]
    return WeeklyScorePublishSummary(target_date=target_date, results=results)


def build_weekly_score_reports(
    session: Session,
    *,
    target_date: date,
    timezone_name: str = "Europe/Paris",
    include_previous_week_finalization: bool = True,
) -> list[WeeklyScoreReport]:
    session.flush()
    timezone = ZoneInfo(timezone_name)
    current_start = _week_start(target_date)
    week_starts = [current_start]
    if include_previous_week_finalization and target_date.weekday() == 0:
        week_starts.insert(0, current_start - timedelta(days=7))
    reports: list[WeeklyScoreReport] = []
    for start in week_starts:
        end = start + timedelta(days=7)
        week_key = _week_key(start)
        suffix = " (finalisation lundi)" if start < current_start else ""
        reports.append(
            WeeklyScoreReport(
                week_key=week_key,
                week_start=start,
                week_end=end,
                title_suffix=suffix,
                lines=_weekly_lines(session, start, end, timezone),
            )
        )
    return reports


def format_weekly_score_messages(
    report: WeeklyScoreReport,
    *,
    timezone_name: str = "Europe/Paris",
    max_chars: int = DISCORD_SAFE_LIMIT,
) -> list[str]:
    """Render one or more Discord-safe markdown scorecard messages."""
    header = _header_lines(report)
    detail_header = ["", "Détail :"]
    detail_lines = [_detail_line(line, timezone_name) for line in report.lines]
    if not detail_lines:
        detail_lines = ["- aucune prédiction late terminée cette semaine."]
    return _split_markdown_messages(header, detail_header, detail_lines, max_chars=max_chars)


def _publish_report(
    delivery: DiscordDeliveryService,
    report: WeeklyScoreReport,
    *,
    timezone_name: str,
    dry_run: bool,
    print_only: bool,
    force: bool,
    replace_current_week: bool,
    echo: Callable[[str], None] | None,
) -> WeeklyScorePublishResult:
    messages = format_weekly_score_messages(report, timezone_name=timezone_name)
    payload_metadata = _report_payload(report)
    replace_summary = (
        delivery.replace_previous_messages(
            channel_key=WEEKLY_SCORE_CHANNEL,
            message_type=WEEKLY_SCORE_MESSAGE_TYPE,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            payload_match={
                "report_kind": WEEKLY_SCORE_REPORT_KIND,
                "week_key": report.week_key,
            },
        )
        if replace_current_week
        else {"deleted": 0, "errors": []}
    )
    statuses: list[str] = []
    ids: list[int] = []
    for message in messages:
        if print_only and echo is not None:
            echo(message)
        result = delivery.send_markdown(
            message,
            channel_key=WEEKLY_SCORE_CHANNEL,
            message_type=WEEKLY_SCORE_MESSAGE_TYPE,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            wait=True,
            payload_metadata=payload_metadata,
        )
        statuses.append(result.status)
        if result.discord_message_id is not None:
            ids.append(result.discord_message_id)
    return WeeklyScorePublishResult(
        week_key=report.week_key,
        status=_combined_status(statuses),
        message_count=len(messages),
        discord_message_ids=ids,
        replaced_count=_int_summary_value(replace_summary, "deleted"),
        replace_warnings=_replace_warnings(replace_summary),
    )


def _weekly_lines(
    session: Session,
    week_start: date,
    week_end: date,
    timezone: ZoneInfo,
) -> list[WeeklyScoreLine]:
    start_utc = datetime.combine(week_start, time.min, tzinfo=timezone).astimezone(UTC)
    end_utc = datetime.combine(week_end, time.min, tzinfo=timezone).astimezone(UTC)
    rows = session.execute(
        select(models.Fixture, models.ModelPrediction, models.DiscordMessage)
        .join(
            models.ModelPrediction,
            models.ModelPrediction.fixture_id == models.Fixture.fixture_id,
        )
        .join(
            models.DiscordMessage,
            models.DiscordMessage.model_prediction_id == models.ModelPrediction.id,
        )
        .where(
            models.Fixture.date.is_not(None),
            models.Fixture.date >= start_utc,
            models.Fixture.date < end_utc,
            models.ModelPrediction.prediction_time < models.Fixture.date,
            models.DiscordMessage.message_type == "prediction",
            models.DiscordMessage.status == "sent",
            models.DiscordMessage.dry_run.is_(False),
            models.DiscordMessage.print_only.is_(False),
        )
        .order_by(
            models.Fixture.fixture_id.asc(),
            models.ModelPrediction.prediction_time.desc(),
            models.DiscordMessage.sent_at.desc(),
        )
    ).all()
    latest_by_fixture: dict[int, tuple[models.Fixture, models.ModelPrediction]] = {}
    for fixture, prediction, message in rows:
        if not _is_late_prediction_message(message):
            continue
        if _actual_outcome(fixture) is None:
            continue
        latest_by_fixture.setdefault(fixture.fixture_id, (fixture, prediction))
    return [
        _score_line(fixture, prediction)
        for fixture, prediction in sorted(
            latest_by_fixture.values(),
            key=lambda item: (item[0].date or datetime.min, item[0].fixture_id),
        )
    ]


def _score_line(
    fixture: models.Fixture,
    prediction: models.ModelPrediction,
) -> WeeklyScoreLine:
    actual = _actual_outcome(fixture)
    predicted = prediction.predicted_result or prediction.predicted_outcome
    correct = actual == predicted if actual is not None and predicted else None
    return WeeklyScoreLine(
        fixture_id=fixture.fixture_id,
        fixture_date=fixture.date,
        match_label=f"{fixture.home_team} - {fixture.away_team}",
        predicted=_outcome_label(predicted),
        actual=_outcome_label(actual) if actual is not None else None,
        score_label=_score_label(fixture),
        confidence_label=prediction.confidence_label,
        confidence_score=prediction.confidence_score,
        status=(fixture.status_short or fixture.status or "").upper(),
        correct=correct,
    )


def _header_lines(report: WeeklyScoreReport) -> list[str]:
    accuracy = f"{report.accuracy * 100:.1f}%" if report.accuracy is not None else "n.d."
    return [
        f"📊 SCORE PRONOS - SEMAINE {report.week_key}{report.title_suffix}",
        f"Période : {report.week_start.isoformat()} -> "
        f"{(report.week_end - timedelta(days=1)).isoformat()}",
        "",
        "Résumé :",
        "- Base : prédictions M-30 daily_late envoyées, matchs terminés uniquement",
        f"- Pronostics terminés : {report.completed}",
        f"- Corrects : {report.correct}",
        f"- Incorrects : {report.incorrect}",
        f"- Accuracy : {accuracy}",
    ]


def _detail_line(line: WeeklyScoreLine, timezone_name: str) -> str:
    date_label = (
        _aware_datetime(line.fixture_date)
        .astimezone(ZoneInfo(timezone_name))
        .strftime("%d/%m %H:%M")
        if line.fixture_date is not None
        else "date n.d."
    )
    verdict = "OK" if line.correct is True else "KO" if line.correct is False else "ATT"
    confidence = (
        f"{line.confidence_label} {line.confidence_score:.1f} pts"
        if line.confidence_score is not None
        else line.confidence_label
    )
    actual = line.actual or "en attente"
    return (
        f"- {date_label} | {line.match_label} | prono {line.predicted} | "
        f"score {line.score_label} | réel {actual} | {verdict} | {confidence}"
    )


def _split_markdown_messages(
    header: list[str],
    detail_header: list[str],
    detail_lines: list[str],
    *,
    max_chars: int,
) -> list[str]:
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in detail_lines:
        candidate = _message_text(header, detail_header, [*current, line], None, None)
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append(current)
    if not chunks:
        chunks = [[]]
    messages: list[str] = []
    total = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        text = _message_text(header, detail_header, chunk, index, total if total > 1 else None)
        messages.append(truncate_discord_message(text, max_chars=max_chars))
    return messages


def _message_text(
    header: list[str],
    detail_header: list[str],
    details: list[str],
    part: int | None,
    total: int | None,
) -> str:
    lines = [CODE_OPEN, *header]
    if total is not None:
        lines.append(f"Message : Partie {part}/{total}")
    lines.extend(
        [
            *detail_header,
            *details,
            "",
            "Note : bilan basé uniquement sur les prédictions late publiées.",
        ]
    )
    lines.append(CODE_CLOSE)
    return "\n".join(lines)


def _report_payload(report: WeeklyScoreReport) -> dict[str, object]:
    return {
        "report_kind": WEEKLY_SCORE_REPORT_KIND,
        "week_key": report.week_key,
        "week_start": report.week_start.isoformat(),
        "week_end": report.week_end.isoformat(),
        "completed": report.completed,
        "correct": report.correct,
        "incorrect": report.incorrect,
        "pending": 0,
    }


def _actual_outcome(fixture: models.Fixture) -> str | None:
    status = (fixture.status_short or fixture.status or "").upper()
    if status not in FINISHED_STATUSES:
        return None
    home = _goals_home(fixture)
    away = _goals_away(fixture)
    if home is None or away is None:
        return None
    if home > away:
        return "HOME"
    if away > home:
        return "AWAY"
    return "DRAW"


def _goals_home(fixture: models.Fixture) -> int | None:
    return fixture.home_goals if fixture.home_goals is not None else fixture.goals_home


def _goals_away(fixture: models.Fixture) -> int | None:
    return fixture.away_goals if fixture.away_goals is not None else fixture.goals_away


def _score_label(fixture: models.Fixture) -> str:
    home = _goals_home(fixture)
    away = _goals_away(fixture)
    if home is None or away is None:
        return "en attente"
    return f"{home}-{away}"


def _outcome_label(value: str | None) -> str:
    labels = {"HOME": "domicile", "DRAW": "nul", "AWAY": "extérieur"}
    if value is None:
        return "en attente"
    return labels.get(str(value).upper(), str(value).lower())


def _is_late_prediction_message(message: models.DiscordMessage) -> bool:
    payload = message.payload_json if isinstance(message.payload_json, dict) else {}
    window = payload.get("automation_window") or payload.get("daily_window")
    return window == "late"


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _week_key(value: date) -> str:
    year, week, _weekday = value.isocalendar()
    return f"{year}-W{week:02d}"


def _aware_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _combined_status(statuses: list[str]) -> str:
    if not statuses:
        return "skipped"
    if all(status == statuses[0] for status in statuses):
        return statuses[0]
    if "sent" in statuses:
        return "sent"
    if "dry_run" in statuses:
        return "dry_run"
    if "print_only" in statuses:
        return "print_only"
    return statuses[0]


def _replace_warnings(summary: dict[str, object]) -> list[str]:
    raw_errors = summary.get("errors", [])
    errors = raw_errors if isinstance(raw_errors, list) else []
    warnings = [str(item) for item in errors if str(item)]
    missing = _int_summary_value(summary, "missing_message_ids")
    if missing:
        warnings.append(f"missing_discord_message_ids={missing}")
    return warnings


def _int_summary_value(summary: dict[str, object], key: str) -> int:
    value = summary.get(key, 0)
    return value if isinstance(value, int) else 0
