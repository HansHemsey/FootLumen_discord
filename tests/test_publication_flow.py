from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.prediction.publication_flow import (
    CandidatePrediction,
    StoredPredictionRef,
    deliver_candidate_prediction,
    evaluate_and_persist_candidate,
    persist_publication_metadata,
)
from football_predictor.prediction.publication_policy import (
    CONFIDENCE_LABEL_NOT_APPROVED_REASON,
    CONFIDENCE_SKIP_REASON,
    DATA_QUALITY_SKIP_REASON,
)

PREDICTION_TIME = datetime(2026, 5, 2, 12, 0, tzinfo=UTC)


class FakeDelivery:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send_markdown(self, markdown: str, **kwargs: Any) -> Any:
        self.calls.append({"markdown": markdown, **kwargs})
        return SimpleNamespace(
            status="sent" if not kwargs.get("dry_run") and not kwargs.get("print_only") else (
                "print_only" if kwargs.get("print_only") else "dry_run"
            ),
            discord_message_id=123,
        )


def test_deliver_candidate_blocks_non_publishable_live_and_persists_reason(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publication_flow_block.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        ids = _seed_predictions(session)
        candidate = _candidate(
            model_family="v2",
            prediction_id=ids["v2"],
            confidence_label="Medium",
            quality_score=95,
        )
        delivery = FakeDelivery()

        result = deliver_candidate_prediction(session, delivery, candidate)
        prediction = session.get(models.ModelPrediction, ids["v2"])

    assert result.status == "confidence_skipped"
    assert result.non_publication_reason == CONFIDENCE_SKIP_REASON
    assert result.discord_sent is False
    assert delivery.calls == []
    assert prediction is not None
    assert prediction.payload_json["non_publication_reason"] == CONFIDENCE_SKIP_REASON
    assert prediction.payload_json["publication_decision"]["allowed"] is False


def test_deliver_candidate_blocks_low_quality_live_and_persists_reason(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publication_flow_quality.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        ids = _seed_predictions(session)
        candidate = _candidate(
            model_family="v2",
            prediction_id=ids["v2"],
            confidence_label="High",
            quality_score=59.9,
        )

        result = deliver_candidate_prediction(session, FakeDelivery(), candidate)
        prediction = session.get(models.ModelPrediction, ids["v2"])

    assert result.status == "confidence_skipped"
    assert result.non_publication_reason == DATA_QUALITY_SKIP_REASON
    assert prediction is not None
    assert prediction.payload_json["non_publication_reason"] == DATA_QUALITY_SKIP_REASON


def test_deliver_candidate_blocks_unapproved_calibrated_label(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publication_flow_labels.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        ids = _seed_predictions(session)
        candidate = _candidate(
            model_family="v3",
            prediction_id=ids["v3"],
            confidence_label="High",
            quality_score=95,
            v3_model_prediction_id=ids["v3"],
            approved_labels=("Very High",),
        )

        result = deliver_candidate_prediction(session, FakeDelivery(), candidate)
        prediction = session.get(models.V3ModelPrediction, ids["v3"])

    assert result.status == "confidence_skipped"
    assert result.non_publication_reason == CONFIDENCE_LABEL_NOT_APPROVED_REASON
    assert prediction is not None
    assert prediction.payload_json["non_publication_reason"] == (
        CONFIDENCE_LABEL_NOT_APPROVED_REASON
    )


def test_deliver_candidate_allows_high_quality_and_passes_ids_to_delivery(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publication_flow_allowed.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        ids = _seed_predictions(session)
        candidate = _candidate(
            model_family="ou25",
            prediction_id=ids["ou25"],
            confidence_label="High",
            quality_score=80,
            message_type="ou_prediction",
            ou_model_prediction_id=ids["ou25"],
            dedupe_key="ou25:-100:late:synthetic:ou_prediction",
        )
        delivery = FakeDelivery()

        result = deliver_candidate_prediction(session, delivery, candidate)
        prediction = session.get(models.OUModelPrediction, ids["ou25"])

    assert result.status == "sent"
    assert result.discord_sent is True
    assert result.discord_message_id == 123
    assert prediction is not None
    assert prediction.payload_json["publication_decision"]["allowed"] is True
    assert delivery.calls[0]["message_type"] == "ou_prediction"
    assert delivery.calls[0]["ou_model_prediction_id"] == ids["ou25"]
    assert delivery.calls[0]["dedupe_key"] == "ou25:-100:late:synthetic:ou_prediction"


def test_deliver_candidate_allows_non_publishable_dry_run_preview(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publication_flow_dry_run.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        ids = _seed_predictions(session)
        candidate = _candidate(
            model_family="v3",
            prediction_id=ids["v3"],
            confidence_label="Low",
            quality_score=90,
            v3_model_prediction_id=ids["v3"],
            discord_payload_metadata={"v3_feature_snapshot_id": ids["v3_feature"]},
        )
        delivery = FakeDelivery()

        result = deliver_candidate_prediction(session, delivery, candidate, dry_run=True)
        prediction = session.get(models.V3ModelPrediction, ids["v3"])

    assert result.status == "dry_run"
    assert result.discord_sent is False
    assert delivery.calls[0]["dry_run"] is True
    assert delivery.calls[0]["v3_model_prediction_id"] == ids["v3"]
    assert delivery.calls[0]["payload_metadata"]["v3_feature_snapshot_id"] == ids["v3_feature"]
    assert prediction is not None
    assert prediction.payload_json["non_publication_reason"] == CONFIDENCE_SKIP_REASON


def test_evaluate_and_persist_supports_all_prediction_tables_and_missing_id(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'publication_flow_tables.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        ids = _seed_predictions(session)
        for family in ("v2", "v3", "ou25"):
            evaluate_and_persist_candidate(
                session,
                _candidate(
                    model_family=family,
                    prediction_id=ids[family],
                    confidence_label="Very High",
                    quality_score=92,
                ),
            )
        persist_publication_metadata(
            session,
            StoredPredictionRef("v2", None),
            {"non_publication_reason": "should_not_raise"},
        )
        v2 = session.get(models.ModelPrediction, ids["v2"])
        v3 = session.get(models.V3ModelPrediction, ids["v3"])
        ou25 = session.get(models.OUModelPrediction, ids["ou25"])

    assert v2 is not None
    assert v3 is not None
    assert ou25 is not None
    assert v2.payload_json["publication_decision"]["allowed"] is True
    assert v3.payload_json["publication_decision"]["allowed"] is True
    assert ou25.payload_json["publication_decision"]["allowed"] is True


def _candidate(
    *,
    model_family,
    prediction_id: int | None,
    confidence_label: str,
    quality_score: float,
    message_type: str = "prediction",
    model_prediction_id: int | None = None,
    v3_model_prediction_id: int | None = None,
    ou_model_prediction_id: int | None = None,
    dedupe_key: str | None = None,
    approved_labels: tuple[str, ...] | None = None,
    discord_payload_metadata: dict[str, Any] | None = None,
) -> CandidatePrediction:
    return CandidatePrediction(
        model_family=model_family,
        fixture_id=-100,
        league_id=-1,
        season=2026,
        confidence_label=confidence_label,
        confidence_score=72.0,
        data_quality_json={"publication_data_quality_score": quality_score},
        prediction_time=PREDICTION_TIME,
        stored_prediction=StoredPredictionRef(model_family, prediction_id),
        render_markdown=lambda: "```md\nsynthetic\n```",
        message_type=message_type,
        model_prediction_id=model_prediction_id
        if model_prediction_id is not None
        else (prediction_id if model_family == "v2" else None),
        v3_model_prediction_id=v3_model_prediction_id,
        ou_model_prediction_id=ou_model_prediction_id,
        dedupe_key=dedupe_key,
        approved_labels=approved_labels,
        payload_metadata={"synthetic": True},
        discord_payload_metadata=discord_payload_metadata or {},
    )


def _seed_predictions(session) -> dict[str, int]:
    session.add_all(
        [
            models.Team(team_id=-10, name="Synthetic Home", payload_json={}),
            models.Team(team_id=-20, name="Synthetic Away", payload_json={}),
            models.Fixture(
                fixture_id=-100,
                date=PREDICTION_TIME,
                league_id=-1,
                season=2026,
                home_team_id=-10,
                away_team_id=-20,
                home_team="Synthetic Home",
                away_team="Synthetic Away",
                status="NS",
                status_short="NS",
                payload_json={},
            ),
        ]
    )
    session.flush()
    feature = models.FeatureSnapshot(
        fixture_id=-100,
        prediction_time=PREDICTION_TIME,
        feature_version="synthetic-publication-flow",
        features_json={},
        data_quality_json={},
    )
    v3_feature = models.V3FeatureSnapshot(
        fixture_id=-100,
        prediction_time=PREDICTION_TIME,
        feature_version="synthetic-publication-flow",
        features_json={},
        data_quality_json={},
    )
    ou_feature = models.OUFeatureSnapshot(
        fixture_id=-100,
        prediction_time=PREDICTION_TIME,
        feature_version="synthetic-publication-flow",
        threshold=2.5,
        features_json={},
        data_quality_json={},
    )
    session.add_all([feature, v3_feature, ou_feature])
    session.flush()
    v2 = models.ModelPrediction(
        fixture_id=-100,
        feature_snapshot_id=feature.id,
        prediction_time=PREDICTION_TIME,
        model_version="synthetic-v2",
        p_home=0.5,
        p_draw=0.25,
        p_away=0.25,
        predicted_outcome="HOME",
        predicted_result="HOME",
        confidence=72,
        confidence_label="High",
        confidence_score=72,
        explanation_json=[],
        explanations_json=[],
        data_quality_json={},
        payload_json={"existing": True},
    )
    v3 = models.V3ModelPrediction(
        fixture_id=-100,
        v3_feature_snapshot_id=v3_feature.id,
        prediction_time=PREDICTION_TIME,
        model_version="synthetic-v3",
        fusion_strategy="synthetic",
        p_v3_final_home=0.5,
        p_v3_final_draw=0.25,
        p_v3_final_away=0.25,
        predicted_result="HOME",
        confidence_score=72,
        confidence_label="High",
        expert_probabilities_json={},
        explanations_json=[],
        data_quality_json={},
        payload_json={"existing": True},
    )
    ou25 = models.OUModelPrediction(
        fixture_id=-100,
        ou_feature_snapshot_id=ou_feature.id,
        prediction_time=PREDICTION_TIME,
        model_version="synthetic-ou",
        threshold=2.5,
        p_over=0.62,
        p_under=0.38,
        confidence_score=72,
        confidence_label="High",
        expert_probabilities_json={},
        data_quality_json={},
        payload_json={"existing": True},
    )
    session.add_all([v2, v3, ou25])
    session.flush()
    return {
        "v2": v2.id,
        "v3": v3.id,
        "v3_feature": v3_feature.id,
        "ou25": ou25.id,
    }
