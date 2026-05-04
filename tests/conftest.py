from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def reference_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "api_football_reference.json"


@pytest.fixture(scope="session")
def players_reference_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "api_football_players_reference.json"


@pytest.fixture(scope="session")
def players_cache_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "api_football_players_cache.json"


@pytest.fixture(scope="session")
def reference_sample_path(repo_root: Path) -> Path:
    return repo_root / "tests" / "fixtures" / "reference" / "reference_sample.json"


@pytest.fixture(scope="session")
def players_reference_sample_path(repo_root: Path) -> Path:
    return repo_root / "tests" / "fixtures" / "reference" / "players_reference_sample.json"
