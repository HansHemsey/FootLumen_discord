"""Public fixture prediction entrypoint."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from football_predictor.api.api_football_client import ApiFootballClient
from football_predictor.config import Settings, get_settings
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.prediction.service import (
    ApiFootballPayloadClient,
    PredictionOutput,
    PredictionService,
)
from football_predictor.reference.loaders import load_api_football_reference, load_players_reference
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import PredictionError


def predict_fixture(
    fixture_id: int,
    prediction_time: datetime | None = None,
    model_dir: Path | str | None = None,
    refresh_data: bool = False,
    *,
    session: Session | None = None,
    reference: ApiFootballReference | None = None,
    players_reference: PlayersReference | None = None,
    api_client: ApiFootballPayloadClient | None = None,
    save_raw: bool = False,
    settings: Settings | None = None,
) -> PredictionOutput:
    """Predict one fixture from local DB/docs, with live refresh only when requested."""
    resolved_settings = settings or get_settings()
    resolved_reference = reference or load_api_football_reference(
        resolved_settings.api_football_reference_path
    )
    resolved_players_reference = players_reference or load_players_reference(
        resolved_settings.api_football_players_reference_path
    )
    if session is not None:
        return _predict_with_session(
            session,
            fixture_id,
            prediction_time,
            model_dir,
            refresh_data,
            reference=resolved_reference,
            players_reference=resolved_players_reference,
            api_client=api_client,
            save_raw=save_raw,
            settings=resolved_settings,
        )

    engine = create_db_engine(resolved_settings.database_url)
    init_db(engine)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as managed_session:
        return _predict_with_session(
            managed_session,
            fixture_id,
            prediction_time,
            model_dir,
            refresh_data,
            reference=resolved_reference,
            players_reference=resolved_players_reference,
            api_client=api_client,
            save_raw=save_raw,
            settings=resolved_settings,
        )


def _predict_with_session(
    session: Session,
    fixture_id: int,
    prediction_time: datetime | None,
    model_dir: Path | str | None,
    refresh_data: bool,
    *,
    reference: ApiFootballReference,
    players_reference: PlayersReference,
    api_client: ApiFootballPayloadClient | None,
    save_raw: bool,
    settings: Settings,
) -> PredictionOutput:
    service = PredictionService(
        reference,
        session,
        players_reference=players_reference,
        market_1x2_bet_name=settings.market_1x2_bet_name,
        market_1x2_bet_id=settings.market_1x2_bet_id,
    )
    if not refresh_data:
        return service.predict_fixture(
            fixture_id,
            prediction_time,
            model_dir=model_dir,
            refresh_data=False,
            save_raw=save_raw,
        )

    if api_client is not None:
        return service.predict_fixture(
            fixture_id,
            prediction_time,
            model_dir=model_dir,
            refresh_data=True,
            save_raw=save_raw,
            api_client=api_client,
        )
    if not settings.api_football_key:
        raise PredictionError("API_FOOTBALL_KEY is required when refresh_data=True")
    with ApiFootballClient(
        base_url=settings.api_football_base_url,
        api_key=settings.api_football_key,
        timeout=settings.api_football_timeout_seconds,
        snapshot_dir=settings.api_football_raw_snapshot_dir,
        retries=settings.api_football_max_retries,
    ) as client:
        return service.predict_fixture(
            fixture_id,
            prediction_time,
            model_dir=model_dir,
            refresh_data=True,
            save_raw=save_raw,
            api_client=client,
        )
