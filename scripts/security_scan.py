#!/usr/bin/env python3
"""Scan versioned project files for obvious committed secrets."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOWED_VALUES = {
    "",
    "REPLACE_WITH_WEBHOOK_URL",
    "REPLACE_WITH_TOKEN",
    "REPLACE_WITH_API_KEY",
    "CHANGEME",
    "changeme",
    "example",
    "placeholder",
}

BINARY_SUFFIXES = {
    ".db",
    ".gif",
    ".ico",
    ".jpg",
    ".jpeg",
    ".joblib",
    ".parquet",
    ".pdf",
    ".png",
    ".pyc",
    ".sqlite",
    ".sqlite3",
    ".zip",
}

SKIPPED_PATH_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line_number: int
    reason: str
    line_preview: str


DISCORD_WEBHOOK_RE = re.compile(
    r"https://discord\.com/api/webhooks/\d{15,25}/[A-Za-z0-9_.-]{40,}"
)

SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    \b(
        API_FOOTBALL_KEY
        | THE_ODDS_API_KEY
        | DISCORD_BOT_TOKEN
        | DISCORD_WEBHOOK_URL
        | DISCORD_WEBHOOK_[A-Z0-9_]+
        | DATABASE_PASSWORD
        | DB_PASSWORD
    )
    \s*=\s*
    ["']?
    ([^"'\s#]+)
    """
)

SENSITIVE_MAPPING_RE = re.compile(
    r"""(?ix)
    \b(
        api[_-]?key
        | password
        | secret
        | token
        | webhook_url
        | x-apisports-key
    )
    \b
    \s*[:=]\s*
    ["']?
    ([^"',\s#}]+)
    """
)

BEARER_TOKEN_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{20,}")


def _is_allowed_value(value: str) -> bool:
    cleaned = value.strip().strip("\"'")
    if cleaned in ALLOWED_VALUES:
        return True
    upper = cleaned.upper()
    return (
        upper.startswith("REPLACE_")
        or upper.startswith("YOUR_")
        or upper.startswith("<")
        or cleaned.startswith("${")
    )


def _looks_like_reference(value: str) -> bool:
    cleaned = value.strip().strip("\"'").rstrip(",")
    if cleaned in {"None", "False", "True", "str", "int", "float", "bool"}:
        return True
    if cleaned.startswith(("<", "f\"", "f'", "{", "(", "[", "field(", "os.environ[")):
        return True
    if re.fullmatch(r"[A-Za-z_][\w.]*\(.*\)", cleaned):
        return True
    if "[" in cleaned and not cleaned.startswith(("http://", "https://")):
        return True
    if "." in cleaned and not cleaned.startswith(("http://", "https://")):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9_]+", cleaned):
        return True
    if cleaned.endswith((".local.yaml", ".example.yaml", ".example")):
        return True
    if "example.invalid" in cleaned or "synthetic" in cleaned:
        return True
    return len(cleaned) < 12


def _tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        text=False,
    )
    return [root / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def _should_scan(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if path.suffix.lower() in BINARY_SUFFIXES:
        return False
    return not any(part in SKIPPED_PATH_PARTS for part in rel.parts)


def scan_paths(paths: list[Path], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        if not path.exists() or not _should_scan(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        rel = path.relative_to(root)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if DISCORD_WEBHOOK_RE.search(line):
                findings.append(
                    Finding(rel, line_number, "discord_webhook_url", line.strip()[:160])
                )
            if BEARER_TOKEN_RE.search(line):
                findings.append(Finding(rel, line_number, "bearer_token", line.strip()[:160]))

            for match in SENSITIVE_ASSIGNMENT_RE.finditer(line):
                value = match.group(2)
                if not _is_allowed_value(value) and not _looks_like_reference(value):
                    findings.append(
                        Finding(rel, line_number, "sensitive_env_assignment", line.strip()[:160])
                    )

            for match in SENSITIVE_MAPPING_RE.finditer(line):
                value = match.group(2)
                if not _is_allowed_value(value) and not _looks_like_reference(value):
                    findings.append(
                        Finding(rel, line_number, "sensitive_mapping_value", line.strip()[:160])
                    )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to scan. Defaults to the project root.",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    findings = scan_paths(_tracked_files(root), root)
    if findings:
        print("Potential secrets found in versioned files:", file=sys.stderr)
        for finding in findings:
            print(
                f"{finding.path}:{finding.line_number}: {finding.reason}: "
                f"{finding.line_preview}",
                file=sys.stderr,
            )
        return 1

    print("Secret scan passed: no obvious credentials found in versioned files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
