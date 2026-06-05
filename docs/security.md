# Security

## Secrets

Real secrets are allowed only through environment variables or local files ignored by Git.

Never commit:

- `.env` or `.env.*` files, except `.env.example`;
- `.claude/settings.local.json`;
- `config/*.local.yaml`;
- `config/*secret*`;
- Discord webhook URLs;
- API-Football keys;
- The Odds API keys;
- Discord bot tokens;
- database passwords;
- local SQLite databases, runtime logs, raw API snapshots or model binaries.

The repository `.gitignore` blocks these local paths. Treat any accidental exposure as a
credential incident.

## Sanitization

Application sanitization is centralized in:

```text
src/football_predictor/security/sanitize.py
```

It masks:

- Discord webhook URLs;
- bearer tokens;
- values assigned to variables containing `key`, `token`, `secret`, `password` or
  `webhook`;
- mappings with sensitive keys;
- long suspicious token-like strings.

The sanitizer is applied before:

- project logging context;
- API-Football raw snapshot files;
- raw API snapshots persisted in DB;
- Discord `payload_json`, `response_json`, `response_text` and `message_markdown`;
- Discord webhook HTTP error text.

Discord sends are blocked before the HTTP call if the outgoing payload contains probable
secret material. `allowed_mentions` remains disabled with `{"parse": []}`.

## Audit Before Push

Run:

```bash
make security
make check
```

`make security` scans Git-versioned files for obvious committed credentials. It does not
scan ignored local secret files because those files must never be added to Git.

If a secret is detected:

1. Stop the commit.
2. Remove the secret from the file.
3. If the secret was real, rotate it immediately.
4. Re-run `make security`.
5. Re-run `git status --short` and verify only safe files are staged.

## Rotation Procedure

If a real secret is exposed locally, in logs, in Discord, or in Git history:

1. Disable or rotate the credential in the provider dashboard.
2. Update the value in the production environment or VPS secrets file.
3. Remove the leaked value from local files and logs when possible.
4. Audit Git history before pushing.
5. Re-run `make security` and `make check`.

If a secret was pushed to a public remote, consider it compromised even if deleted later.
