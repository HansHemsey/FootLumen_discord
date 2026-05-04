from __future__ import annotations

import re
from pathlib import Path

REFERENCE_FILES = (
    "docs/api_football_reference.md",
    "docs/api_football_reference.json",
    "docs/api_football_players_reference.md",
    "docs/api_football_players_reference.json",
    "docs/api_football_players_cache.json",
)


def _read(repo_root: Path, relative_path: str) -> str:
    return (repo_root / relative_path).read_text(encoding="utf-8")


def test_final_guides_document_end_to_end_workflow(repo_root: Path) -> None:
    user_guide = _read(repo_root, "docs/user_guide.md")
    developer_guide = _read(repo_root, "docs/developer_guide.md")
    operations_guide = _read(repo_root, "docs/operations_guide.md")
    codex_workflow = _read(repo_root, "docs/codex_workflow.md")
    readme = _read(repo_root, "README.md")

    for text in (user_guide, readme):
        assert "seed-reference-from-docs" in text
        assert "scripts/smoke_test_local.sh" in text or "make smoke" in text
        assert "--no-refresh-data" in text
        assert "--dry-run" in text

    assert "VSCode" in developer_guide
    assert "Architecture Et Modules" in developer_guide
    assert "Hierarchie Des Sources De Verite" in developer_guide
    assert "prediction_time" in developer_guide
    assert "pytest" in developer_guide
    assert "cron" in operations_guide
    assert "T-24h" in operations_guide
    assert "H-6h" in operations_guide
    assert "M-30min" in operations_guide
    assert "Docker" in operations_guide
    assert "Plan Mode" in codex_workflow
    assert "Agent / Edit Automatically" in codex_workflow
    assert "AGENTS.md" in codex_workflow
    assert "blueprint.md" in codex_workflow


def test_reference_files_are_documented_with_cache_role(repo_root: Path) -> None:
    combined = "\n".join(
        _read(repo_root, path)
        for path in (
            "README.md",
            "docs/user_guide.md",
            "docs/developer_guide.md",
            "docs/operations_guide.md",
            "docs/codex_workflow.md",
        )
    )

    for reference_file in REFERENCE_FILES:
        assert reference_file in combined
    assert "cache technique" in combined
    assert "pas la source metier principale" in combined


def test_smoke_script_is_local_by_default_and_live_is_explicit(repo_root: Path) -> None:
    text = _read(repo_root, "scripts/smoke_test.sh")
    local_text = _read(repo_root, "scripts/smoke_test_local.sh")
    live_text = _read(repo_root, "scripts/smoke_test_live.sh")

    for reference_file in REFERENCE_FILES:
        assert reference_file in text
        assert reference_file in local_text
    assert "--no-refresh-data" in text
    assert "--dry-run" in text
    assert "pytest" in local_text
    assert "SMOKE_LIVE" in text
    assert "--live" in text
    assert "requires API_FOOTBALL_KEY" in text
    assert "API_FOOTBALL_KEY is required for live smoke" in live_text
    assert "--refresh-data" in text
    assert "SMOKE_FIXTURE_ID" in text
    assert "SEND_DISCORD:-false" in live_text
    assert "DISCORD_WEBHOOK_URL=" not in text
    assert "DISCORD_BOT_TOKEN=" not in text
    assert "discord.com/api/webhooks" not in text


def test_makefile_exposes_smoke_targets(repo_root: Path) -> None:
    text = _read(repo_root, "Makefile")

    assert re.search(r"^smoke:\n\tscripts/smoke_test_local\.sh$", text, flags=re.MULTILINE)
    assert "smoke-live:" in text
    assert "scripts/smoke_test_live.sh" in text


def test_sprint19_docs_do_not_contain_real_secrets(repo_root: Path) -> None:
    checked_paths = (
        "README.md",
        "docs/user_guide.md",
        "docs/developer_guide.md",
        "docs/operations_guide.md",
        "docs/codex_workflow.md",
        "scripts/smoke_test.sh",
        "scripts/smoke_test_local.sh",
        "scripts/smoke_test_live.sh",
    )
    combined = "\n".join(_read(repo_root, path) for path in checked_paths)

    webhook_prefix = "https://discord.com/api/" + "webhooks/"
    assert webhook_prefix not in combined
    assert not re.search(r"API_FOOTBALL_KEY=[A-Za-z0-9_-]{12,}", combined)
    assert not re.search(r"DISCORD_BOT_TOKEN=[A-Za-z0-9._-]{12,}", combined)
