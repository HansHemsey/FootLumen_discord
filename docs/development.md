# Development And CI

## Python Version

The public-ready baseline targets Python `3.11`.

Supported range:

```text
>=3.11,<3.13
```

Use the repository `.python-version` file when working with `pyenv` or compatible tools.

## Clean Install

From a fresh clone:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` pins the direct runtime and development dependencies used by CI.
Heavy optional ML packages remain optional and are not required for the standard CI path.

## Local Checks

Run the full local baseline:

```bash
make check
```

Equivalent individual commands:

```bash
make compile
make lint
make typecheck
make security
make test
```

`make check` runs:

```text
python -m compileall -q src tests scripts alembic
python -m ruff check .
python -m mypy src
python scripts/security_scan.py
python -m pytest
```

## Secret Scanning

The repository includes a lightweight scanner:

```bash
make security
```

It scans Git-versioned files only. Local files ignored by Git, such as `.env`,
`config/*.local.yaml`, SQLite databases, runtime logs, model binaries and exports, are not
scanned because they must not be committed.

The scanner blocks obvious committed credentials, including:

- full Discord webhook URLs;
- non-empty API key environment assignments;
- bearer tokens;
- suspicious token/password/secret mapping values.

Keep real secrets in local `.env` files or in the production environment only.

## GitHub Actions

CI is defined in:

```text
.github/workflows/ci.yml
```

The workflow runs on pushes to `main`, `feature/**`, `production/**`, and on pull requests.
It uses Python `3.11`, installs `requirements-dev.txt`, then runs compile, Ruff, Mypy,
secret scanning and Pytest.

## Current Quality Baseline

Ruff and Mypy have explicit baseline configuration in `pyproject.toml` to avoid changing
business logic while making CI reproducible. New code outside the listed legacy paths is
still checked by the global Ruff rules, and Mypy remains part of the command surface for
future tightening.
