# Codex Guide

Ce guide complete `AGENTS.md` et `blueprint.md` pour les sessions Codex dans VSCode.

## Demarrage D'Une Tache

1. Lire `AGENTS.md`.
2. Lire `blueprint.md`.
3. Lire les docs pertinentes.
4. Explorer le repo avant de modifier.
5. Proposer ou suivre un plan clair.

Pour les sprints importants, demarrer en Plan mode. En implementation, modifier par petites etapes
et lancer les tests pertinents.

## Regles Non Negociables

- Ne jamais inventer d'ID API-Football.
- Ne jamais exposer de secret.
- Ne jamais faire d'appel reseau dans les tests.
- Ne jamais modifier les cinq referentiels `docs/api_football_*` sans demande explicite.
- Respecter `prediction_time` pour toute feature dynamique.

## References A Utiliser

- `docs/api_football_reference.json` : IDs competitions, equipes, fixtures, venues, bookmakers,
  bets.
- `docs/api_football_reference.md` : lecture humaine des memes references.
- `docs/api_football_players_reference.json` : joueurs, effectifs, postes et numeros.
- `docs/api_football_players_reference.md` : lecture humaine joueurs/effectifs.
- `docs/api_football_players_cache.json` : cache technique, pas source metier principale.

## Workflow Recommande

```bash
make doctor
make smoke
pytest
ruff check .
mypy src
```

Pour un changement de documentation ou de script, ajoute un test statique quand le comportement est
important : absence de secret, mode dry-run par defaut, references docs verifiees.

## Checklist Avant Reponse Finale

- Le diff ne contient aucun secret.
- Les docs ne presentent aucune prediction comme certaine.
- Les exemples utilisent des placeholders ou IDs verifies.
- Les tests n'appellent ni API-Football ni Discord.
- Les fichiers de reference sont presents et inchanges.

