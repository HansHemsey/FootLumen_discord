from __future__ import annotations

from football_predictor.worldcup.groups import (
    extract_group_from_payload,
    normalize_worldcup_group_label,
)


def test_normalize_worldcup_group_label_rejects_group_stage_round() -> None:
    assert normalize_worldcup_group_label("Group Stage - 1") is None
    assert normalize_worldcup_group_label("Group A") == "Group A"
    assert normalize_worldcup_group_label("Groupe L") == "Group L"


def test_extract_group_from_payload_ignores_fixture_round_without_group() -> None:
    assert extract_group_from_payload({"league": {"round": "Group Stage - 1"}}) is None
    assert extract_group_from_payload({"raw": {"league": {"round": "Group Stage - 2"}}}) is None
    assert extract_group_from_payload({"raw": {"group": "Group C"}}) == "Group C"
