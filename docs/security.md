# Sécurité

Ce projet manipule des clés API, webhooks Discord, snapshots bruts, messages persistés et
rapports d'exploitation. La règle principale est simple : aucun secret ne doit entrer dans
Git, les logs, les snapshots ou Discord.

## Règles Absolues

Ne jamais committer, afficher ou logger :

- clé API-Football ;
- URL webhook Discord complète ;
- token Discord bot ;
- clé The Odds API ;
- mot de passe DB ;
- bearer token ;
- fichier `.env` réel ;
- config locale contenant un secret ;
- base SQLite privée, logs runtime ou snapshots bruts sensibles.

Les secrets doivent venir uniquement de variables d'environnement ou de fichiers locaux
ignorés par Git.

## Fichiers Autorisés Et Interdits

Autorisés :

- `.env.example` avec valeurs vides ou placeholders ;
- `config/*.example.yaml` ;
- `config/*.example.crontab` ;
- documentation décrivant les variables sans valeur réelle.

Interdits :

- `.env` et `.env.*` sauf `.env.example` ;
- `.claude/settings.local.json` ;
- `config/*.local.yaml` ;
- `config/*secret*` ;
- `*.secrets.yaml` ;
- `logs/` ;
- bases locales sensibles ;
- fichiers contenant webhook, token, password, bearer ou API key réels.

Avant chaque commit :

```bash
git status --short
make security
```

## Sanitization

La sanitization applicative est centralisée dans :

```text
src/football_predictor/security/sanitize.py
```

Elle masque notamment :

- URLs webhook Discord ;
- bearer tokens ;
- valeurs associées à `key`, `token`, `secret`, `password`, `webhook` ;
- chaînes longues ressemblant à des tokens ;
- mappings contenant des clés sensibles.

Le sanitizer est appliqué avant stockage ou affichage des éléments sensibles :

- logs API ;
- erreurs HTTP ;
- raw snapshots ;
- payloads JSON ;
- réponses Discord ;
- `message_markdown` persisté ;
- diagnostics et healthchecks.

## Discord

Les publications Discord doivent rester sûres :

- `allowed_mentions` reste désactivé avec `{"parse": []}` ;
- aucun message ne doit contenir un webhook, token ou secret probable ;
- une publication contenant un secret probable doit être bloquée avant l'appel HTTP ;
- les messages publics ne doivent jamais promettre un gain ou une certitude.

Les messages persistés en DB peuvent contenir le markdown complet, mais ils doivent être
sanitizés avant stockage.

## Scans Et CI

Commandes de contrôle :

```bash
make security
make check
.venv/bin/python scripts/security_scan.py
```

`make security` scanne les fichiers versionnés. Il ne remplace pas une revue manuelle des
fichiers locaux ignorés, qui ne doivent jamais être ajoutés à Git.

La CI exécute également le scan anti-secret. Si elle échoue, ne contourne pas le test :
corrige le fichier concerné, puis relance le scan.

## Procédure En Cas D'Incident

Si un secret réel apparaît dans un fichier, un log, Discord ou l'historique Git :

1. Stopper le commit, le push ou le déploiement.
2. Supprimer la valeur exposée du fichier concerné.
3. Rotater immédiatement le secret côté fournisseur.
4. Mettre à jour la valeur dans l'environnement VPS ou le fichier local ignoré.
5. Rejouer `make security` et `make check`.
6. Vérifier `git status --short`.

Si le secret a déjà été poussé sur un dépôt public, il doit être considéré comme compromis,
même s'il est supprimé ensuite.

## Checklist Avant Push

- Aucun `.env` réel n'est versionné.
- Aucun webhook Discord complet n'apparaît dans le diff.
- Aucun token ou bearer n'apparaît dans le diff.
- Les nouveaux logs ou payloads passent par le sanitizer.
- Les commandes dangereuses restent en dry-run ou exigent `--execute`.
- `make security` passe.

## Checklist Avant VPS

- `.env` existe sur le VPS et n'est pas écrasé.
- Les chemins de configs Discord pointent vers des fichiers locaux sûrs.
- Les webhooks staff/public sont configurés sans être affichés.
- `football-predictor healthcheck` masque les secrets.
- `football-predictor doctor --strict` passe.
- Les crons ne publient en public que si la config le permet explicitement.
