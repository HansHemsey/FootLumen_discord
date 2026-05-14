"""Shared prediction publication flow helpers.

This module stays in the prediction layer on purpose: DiscordDeliveryService is
generic and also sends standings, calendars, results, analyses and weekly
scores.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.prediction.publication_policy import (
    DEFAULT_MIN_DATA_QUALITY_SCORE,
    PublicationDecision,
    evaluate_publication,
    publication_decision_payload,
)

if TYPE_CHECKING:
    from football_predictor.discord.service import DiscordDeliveryService, DiscordSendResult

ModelFamily = Literal["v2", "v3", "ou25"]
JsonDict = dict[str, Any]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredPredictionRef:
    model_family: ModelFamily
    prediction_id: int | None


@dataclass(frozen=True)
class CandidatePrediction:
    model_family: ModelFamily
    fixture_id: int
    league_id: int | None
    season: int | None
    confidence_label: str | None
    confidence_score: float | None
    data_quality_json: Mapping[str, Any] | None
    prediction_time: datetime
    stored_prediction: StoredPredictionRef
    render_markdown: Callable[[], str]
    message_type: str = "prediction"
    channel_key: str | None = "predictions"
    competition_key: str | None = None
    model_prediction_id: int | None = None
    v3_model_prediction_id: int | None = None
    ou_model_prediction_id: int | None = None
    dedupe_key: str | None = None
    approved_labels: tuple[str, ...] | None = None
    payload_metadata: JsonDict = field(default_factory=dict)
    discord_payload_metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class CandidatePublicationState:
    decision: PublicationDecision
    payload_metadata: JsonDict


@dataclass(frozen=True)
class PredictionDeliveryResult:
    status: str
    decision: PublicationDecision
    non_publication_reason: str | None
    discord_message_id: int | None
    discord_sent: bool
    send_result: DiscordSendResult | None = None


def publication_metadata(decision: PublicationDecision) -> JsonDict:
    payload: JsonDict = {
        "publication_decision": publication_decision_payload(decision),
        "publication_policy_version": decision.policy_version,
    }
    if decision.reason is not None:
        payload["non_publication_reason"] = decision.reason
    return payload


def evaluate_candidate(
    candidate: CandidatePrediction,
    *,
    min_data_quality_score: float = DEFAULT_MIN_DATA_QUALITY_SCORE,
) -> PublicationDecision:
    return evaluate_publication(
        candidate.confidence_label,
        candidate.data_quality_json,
        min_data_quality_score=min_data_quality_score,
        approved_labels=candidate.approved_labels,
    )


def evaluate_and_persist_candidate(
    session: Session,
    candidate: CandidatePrediction,
    *,
    min_data_quality_score: float = DEFAULT_MIN_DATA_QUALITY_SCORE,
) -> CandidatePublicationState:
    decision = evaluate_candidate(
        candidate,
        min_data_quality_score=min_data_quality_score,
    )
    metadata = {
        **candidate.payload_metadata,
        **publication_metadata(decision),
    }
    persist_publication_metadata(session, candidate.stored_prediction, metadata)
    return CandidatePublicationState(decision=decision, payload_metadata=metadata)


def deliver_candidate_prediction(
    session: Session,
    delivery: DiscordDeliveryService,
    candidate: CandidatePrediction,
    *,
    dry_run: bool = False,
    print_only: bool = False,
    force: bool = False,
    min_data_quality_score: float = DEFAULT_MIN_DATA_QUALITY_SCORE,
) -> PredictionDeliveryResult:
    state = evaluate_and_persist_candidate(
        session,
        candidate,
        min_data_quality_score=min_data_quality_score,
    )
    decision = state.decision
    if not dry_run and not print_only and not decision.allowed:
        logger.info(
            "%s Discord publication skipped: fixture_id=%s confidence_label=%s "
            "confidence_score=%s data_quality_score=%s min_data_quality_score=%s "
            "reason=%s message_type=%s",
            candidate.model_family,
            candidate.fixture_id,
            decision.confidence_label,
            candidate.confidence_score,
            decision.data_quality_score,
            decision.min_data_quality_score,
            decision.reason,
            candidate.message_type,
        )
        return PredictionDeliveryResult(
            status="confidence_skipped",
            decision=decision,
            non_publication_reason=decision.reason,
            discord_message_id=None,
            discord_sent=False,
            send_result=None,
        )

    send_result = delivery.send_markdown(
        candidate.render_markdown(),
        competition_key=candidate.competition_key,
        league_id=candidate.league_id,
        season=candidate.season,
        channel_key=candidate.channel_key,
        message_type=candidate.message_type,
        fixture_id=candidate.fixture_id,
        model_prediction_id=candidate.model_prediction_id,
        v3_model_prediction_id=candidate.v3_model_prediction_id,
        ou_model_prediction_id=candidate.ou_model_prediction_id,
        dedupe_key=candidate.dedupe_key,
        dry_run=dry_run,
        print_only=print_only,
        force=force,
        payload_metadata={
            **state.payload_metadata,
            **candidate.discord_payload_metadata,
        },
    )
    return PredictionDeliveryResult(
        status=send_result.status,
        decision=decision,
        non_publication_reason=decision.reason,
        discord_message_id=send_result.discord_message_id,
        discord_sent=send_result.status == "sent",
        send_result=send_result,
    )


def persist_publication_metadata(
    session: Session,
    stored_prediction: StoredPredictionRef,
    metadata: Mapping[str, Any],
) -> None:
    prediction_id = stored_prediction.prediction_id
    if prediction_id is None:
        return
    model = _model_for_family(stored_prediction.model_family)
    prediction = session.get(model, prediction_id)
    if prediction is None:
        return
    payload = dict(prediction.payload_json) if isinstance(prediction.payload_json, dict) else {}
    payload.update(dict(metadata))
    prediction.payload_json = payload
    session.flush()


def _model_for_family(
    model_family: ModelFamily,
) -> type[models.ModelPrediction | models.V3ModelPrediction | models.OUModelPrediction]:
    if model_family == "v2":
        return models.ModelPrediction
    if model_family == "v3":
        return models.V3ModelPrediction
    return models.OUModelPrediction
