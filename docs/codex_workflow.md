# Codex Workflow

Ce guide decrit comment travailler avec Codex sur Football Predictor.

## Plan Mode

Utilise Plan mode pour tout sprint ou changement large :

1. Lire `AGENTS.md`.
2. Lire `blueprint.md`.
3. Lire les docs pertinentes.
4. Explorer le repo sans modifier.
5. Proposer un plan decision-complete.

Le plan doit couvrir objectifs, fichiers touches, tests, risques data leakage et protection des
secrets.

## Agent / Edit Automatically

Passe en implementation seulement apres plan valide ou demande explicite d'execution. Pendant
l'implementation :

- faire des patches limites ;
- ne pas modifier les referentiels `docs/api_football_*` ;
- ne pas faire d'appel reseau dans les tests ;
- ajouter ou ajuster les tests ;
- lancer `pytest`, `ruff check .` et `mypy src` si possible.

## Relecture De Diff

Demande une relecture senior avec ce prompt :

```text
Relis le diff comme un reviewer senior.
Cherche bugs, fuite de donnees, secrets, IDs inventes, tests manquants et documentation obsolete.
```

## Prompts Types

Plan :

```text
Lis AGENTS.md, blueprint.md et les docs pertinentes.
Travaille en Plan mode.
Ne modifie aucun fichier avant d'avoir propose un plan.
```

Implementation :

```text
Implemente le plan valide.
N'invente aucun ID API-Football.
N'expose aucun secret.
Ajoute les tests necessaires.
```

Controle anti-fuite :

```text
Verifie que toutes les features utilisent uniquement les donnees disponibles a prediction_time.
Confirme que la fixture cible est exclue des historiques.
```

## Checklist Avant Commit

- `AGENTS.md` et `blueprint.md` lus.
- IDs positifs verifies dans les JSON docs.
- Aucun secret dans code, docs, scripts ou tests.
- Tests sans reseau.
- `pytest` passe.
- `ruff check .` passe.
- `mypy src` passe si le typage global le permet.
- Documentation mise a jour si une commande ou structure change.
- Les cinq fichiers referentiels `docs/api_football_*` sont presents et inchanges.

