from __future__ import annotations

from pathlib import Path

REFERENCE_FILES = {
    "docs/api_football_reference.md",
    "docs/api_football_reference.json",
    "docs/api_football_players_reference.md",
    "docs/api_football_players_reference.json",
    "docs/api_football_players_cache.json",
}


def test_dockerfile_copies_runtime_context_without_secrets(repo_root: Path) -> None:
    text = (repo_root / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.11-slim" in text
    assert "ENTRYPOINT" in text
    assert 'CMD ["doctor"]' in text
    assert ".env" not in text
    assert "config/discord_webhooks.local.yaml" not in text
    assert "*.secrets.yaml" not in text
    assert "COPY data" not in text
    for reference_file in REFERENCE_FILES:
        assert reference_file in text


def test_dockerignore_excludes_secrets_and_keeps_reference_docs(repo_root: Path) -> None:
    lines = {
        line.strip()
        for line in (repo_root / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert ".env" in lines
    assert "config/*.local.yaml" in lines
    assert "*.secrets.yaml" in lines
    assert ".venv/" in lines
    assert ".pytest_cache/" in lines
    assert ".ruff_cache/" in lines
    assert ".mypy_cache/" in lines
    assert "data/*" in lines
    assert not any(line == "docs" or line.startswith("docs/") for line in lines)


def test_docker_compose_mounts_data_docs_and_config(repo_root: Path) -> None:
    text = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "  app:" in text
    assert "env_file:" in text
    assert "- .env" in text
    assert 'command: ["doctor"]' in text
    assert "- ./data:/app/data" in text
    assert "- ./docs:/app/docs:ro" in text
    assert "- ./config:/app/config:ro" in text
    assert "DATABASE_URL: sqlite:////app/data/football_predictor.db" in text


def test_makefile_exposes_local_and_docker_targets(repo_root: Path) -> None:
    text = (repo_root / "Makefile").read_text(encoding="utf-8")
    targets = {
        "install:",
        "test:",
        "lint:",
        "format:",
        "typecheck:",
        "check:",
        "doctor:",
        "init-db:",
        "seed-reference:",
        "data-quality:",
        "predict-fixture:",
        "predict-today:",
        "train:",
        "backtest:",
        "docker-build:",
        "docker-doctor:",
        "docker-init-db:",
        "docker-seed-reference:",
        "docker-data-quality:",
        "docker-predict-today-dry-run:",
        "docker-shell:",
        "compose-doctor:",
        "compose-run:",
        "compose-down:",
    }

    for target in targets:
        assert target in text


def test_docker_entrypoint_routes_cli_commands(repo_root: Path) -> None:
    text = (repo_root / "scripts/docker-entrypoint.sh").read_text(encoding="utf-8")

    assert "mkdir -p /app/data/raw /app/data/processed /app/data/models" in text
    assert "set -- doctor" in text
    assert 'exec football-predictor "$@"' in text


def test_local_scripts_exist_and_do_not_embed_secrets(repo_root: Path) -> None:
    for relative_path in ("scripts/init_local.sh", "scripts/run_predict_today.sh"):
        text = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "API_FOOTBALL_KEY" + "=" not in text
        assert "DISCORD_WEBHOOK_URL" + "=" not in text
        assert "DISCORD_BOT_TOKEN" + "=" not in text
        assert "discord.com/api/webhooks" not in text

    init_text = (repo_root / "scripts/init_local.sh").read_text(encoding="utf-8")
    assert "docs/api_football_reference.json" in init_text
    assert "docs/api_football_players_reference.json" in init_text
    assert "docs/api_football_players_cache.json" in init_text
    assert "init-db" in init_text

    run_text = (repo_root / "scripts/run_predict_today.sh").read_text(encoding="utf-8")
    assert "predict-today" in run_text
    assert "--no-refresh-data" in run_text
