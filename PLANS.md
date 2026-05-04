# Plans

Ce fichier décrit la manière de planifier les sprints et les changements importants.

Pour tout sprint ou changement significatif, Codex doit commencer en Plan mode, lire
`AGENTS.md`, lire `blueprint.md`, puis consulter les fichiers `docs/` pertinents avant
de proposer ou d'exécuter une modification.

## Format ExecPlan

Un ExecPlan doit être assez précis pour être confié à un autre développeur ou agent sans
ambiguïté. Il doit contenir :

```text
Titre
Objectif
Contexte
Contraintes
Sources de vérité consultées
Étapes d'implémentation
Tests et validation
Risques
Définition de done
```

Pour les changements simples, le plan peut être court, mais il doit toujours indiquer les
sources à respecter et les validations attendues.

## Gabarit De Sprint

Chaque sprint doit documenter :

- objectif : résultat métier ou technique attendu ;
- contexte : documents lus, état du projet, dépendances ;
- contraintes : sécurité, anti data leakage, sources de vérité, compatibilité ;
- étapes : ordre d'exécution, fichiers ou modules concernés, limites explicites ;
- tests : tests unitaires, intégration locale, lint, type checking si applicable ;
- risques : data leakage, secrets, IDs inventés, quota API, données manquantes ;
- done : critères vérifiables de fin de sprint.

## Règles De Planification

- Lire `AGENTS.md` avant toute tâche importante.
- Lire `blueprint.md` avant toute modification importante.
- Consulter `docs/api_football_reference.json` pour tout ID compétition, équipe,
  fixture, venue, bookmaker ou bet utilisé par du code ou des tests.
- Consulter `docs/api_football_players_reference.json` pour tout `player_id` ou squad.
- Utiliser les fichiers Markdown de référence pour comprendre et documenter.
- Ne jamais utiliser `docs/api_football_players_cache.json` comme source métier principale.
- Ne jamais lancer d'appel API live sauf si le sprint prévoit explicitement un refresh.
- Ne jamais inventer d'ID API-Football.
- Ne jamais logger ou committer de secret.

## Sprint 0 - Documentation De Base

Objectif : rendre le projet compréhensible sans contexte externe et fixer les règles de
travail avant le code applicatif.

Contexte :

- `AGENTS.md` définit les règles de développement, sécurité, tests et anti data leakage.
- `blueprint.md` définit le contexte métier central.
- Les cinq référentiels `docs/` existent déjà et doivent être préservés.

Contraintes :

- ne pas supprimer, renommer ou écraser les cinq fichiers de référence ;
- ne pas réécrire `AGENTS.md` ou `blueprint.md` ;
- ne pas ajouter de secret ;
- documenter explicitement que les IDs viennent des JSON locaux ou de la base locale.

Étapes :

- compléter `README.md` ;
- compléter `PLANS.md` ;
- compléter `docs/product_spec.md` ;
- compléter `docs/architecture.md` ;
- compléter `docs/modeling_strategy.md` ;
- compléter `docs/data_contract.md` ;
- vérifier la présence et l'intégrité des cinq fichiers référentiels.

Tests et validation :

- vérifier que les documents existent ;
- rechercher les secrets accidentels ;
- vérifier que la documentation interdit les IDs inventés ;
- vérifier que les référentiels n'ont pas été supprimés ou écrasés.

Risques :

- mélanger source statique et snapshot dynamique ;
- utiliser un ID d'exemple non vérifié ;
- présenter la prédiction comme certaine ;
- oublier que le cache joueurs est seulement technique.

Done :

- tous les documents Sprint 0 existent ;
- les cinq fichiers référentiels sont documentés comme sources de vérité ;
- l'architecture cible est compréhensible ;
- les règles anti data leakage sont visibles ;
- aucun secret n'a été ajouté ;
- aucun fichier référentiel n'a été supprimé ou écrasé.
