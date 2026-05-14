# Product Spec

## Objectif Produit

Football Predictor doit prédire le résultat 1X2 d'un match de football à partir de données
API-Football et de snapshots locaux traçables.

Classes cibles :

- `HOME` : victoire de l'équipe à domicile ;
- `DRAW` : match nul ;
- `AWAY` : victoire de l'équipe extérieure.

Le produit doit être robuste, explicable et exploitable en CLI puis dans Discord. Il doit
toujours présenter une prédiction comme probabiliste, jamais comme certaine.

## Fonctionnalités Finales Attendues

- charger et valider les référentiels locaux API-Football ;
- initialiser une base locale depuis les JSON sous `docs/` sans consommer de quota API ;
- ingérer explicitement les données dynamiques API-Football en snapshots ;
- construire des features point-in-time ;
- prédire `P(Home)`, `P(Draw)`, `P(Away)` ;
- fournir un résultat prédit et un score de confiance ;
- expliquer les principaux facteurs de la prédiction ;
- mesurer la qualité des données disponibles ;
- backtester et évaluer les modèles ;
- envoyer un message Discord en français via webhook ;
- continuer avec des fallbacks quand une source optionnelle manque.

État opérationnel actuel :

- V3 1X2 est le moteur quotidien par défaut pour la fenêtre `late` ;
- V2 1X2 reste le rollback officiel et un signal consommable par V3 ;
- O/U 2.5 est un pipeline séparé avec la même exigence de publication sélective ;
- une publication Discord réelle est autorisée uniquement pour `High` ou `Very High`,
  `publication_data_quality_score >= PUBLICATION_MIN_DATA_QUALITY_SCORE` et aucun
  `publication_blockers`.

## Sortie De Prédiction

Une prédiction doit contenir au minimum :

- `fixture_id` ;
- match domicile vs extérieur ;
- compétition et saison ;
- date du match ;
- `prediction_time` ;
- probabilités normalisées `p_home`, `p_draw`, `p_away` ;
- résultat prédit `HOME`, `DRAW` ou `AWAY` ;
- score et label de confiance ;
- explications principales ;
- qualité des données ;
- sources disponibles ou manquantes.

Les probabilités doivent toujours vérifier :

```text
p_home + p_draw + p_away = 1
```

## Format Discord Attendu

Le message Discord doit être court, clair, en français et dans un bloc markdown fermé :

````md
```md
🏟️ PRÉDICTION FOOTBALL

Match : Équipe domicile vs Équipe extérieur
Compétition : Nom de compétition
Date : YYYY-MM-DD HH:mm Europe/Paris

Résultat prédit : victoire domicile / match nul / victoire extérieur
Confiance : High / Medium / Low / Uncertain
Score de confiance : XX.X pts
Écart de confiance : XX.X pts

Probabilités modèle :
- Domicile  : XX.X%
- Nul       : XX.X%
- Extérieur : XX.X%

Probabilités marché :
- Domicile  : XX.X%
- Nul       : XX.X%
- Extérieur : XX.X%

Facteurs clés :
1. ...
2. ...
3. ...

Absences clés :
- Équipe A : ...
- Équipe B : ...

Qualité des données :
- Score global : XX/100
- Odds : oui/non
- Blessures : oui/non
- Lineups officielles : oui/non
- Stats joueurs : oui/non

Note : prédiction probabiliste, pas une certitude.
```
````

Si le marché n'est pas disponible avant `prediction_time`, afficher
`Probabilités marché : non disponible`. Si aucune absence exploitable n'est disponible
avant `prediction_time`, afficher une mention explicite `non disponible` plutôt que
d'inventer un joueur ou une blessure.

La limite Discord doit être respectée. Le formatter vise 1900 caractères par défaut pour
rester sous la limite Discord de 2000 caractères. Toute troncature doit éviter de couper au
milieu d'une ligne quand c'est possible et conserver la fermeture du bloc de code.

Le rendu ne doit jamais inclure de secret : clé API, URL webhook Discord complète, token ou
valeur assimilable à un secret doivent être masqués avant publication.

## Routage Discord Multi-Channels

Le serveur Discord peut être organisé par compétition, avec des channels textuels
standardisés : `classement`, `calendrier`, `matchs_du_jour`, `analyses`, `predictions`,
`resultats` et `discussions`. Chaque channel peut avoir son propre webhook.

Les prédictions sont routées vers `predictions`, les résultats vers `resultats`, les matchs
du jour vers `matchs_du_jour`, les classements vers `classement`, les calendriers vers
`calendrier` et les analyses vers `analyses`. Les messages automatiques vers
`discussions` sont refusés par défaut.

Le channel `analyses` reçoit au plus une analyse T-6 par match suivi, en bloc `md` sous
2000 caractères. Elle couvre le contexte, la forme récente, le classement, le marché,
les absences ou XI disponibles, les points forts/faibles, la fiabilité des données et une
conclusion prudente. Le channel `resultats` reçoit un bilan après `FT/AET/PEN` avec score
final, résultat 1X2 et comparaison avec la prédiction pré-match quand elle existe. Ces deux
channels conservent l'historique et ne sont pas nettoyés par le remplacement quotidien.

Le channel global `score_pronos_semaine` publie un bilan hebdomadaire des seuls pronostics
réellement envoyés dans Discord : `status="sent"`, `dry_run=false`, `print_only=false`,
match terminé et message de prédiction V2, V3 ou O/U. Les prédictions internes, les doublons
ignorés et les publications bloquées par confidence/data quality ne sont jamais comptées.

Les URLs webhook réelles doivent rester dans `config/discord_webhooks.local.yaml`, dans des
variables d'environnement ou dans un secret manager futur. Les fichiers example ne doivent
contenir que des placeholders. La base locale conserve uniquement un hash court du webhook
et un hash du message pour la traçabilité et la déduplication.

## Données API-Football Utilisées

Données statiques ou quasi statiques :

- compétitions ;
- équipes ;
- stades ;
- fixtures connues ;
- bookmakers ;
- bets ;
- joueurs ;
- squads.

Données dynamiques nécessaires aux features :

- fixtures récentes ou futures ;
- standings datés ;
- statistiques de match ;
- événements ;
- lineups ;
- statistiques joueurs ;
- blessures et absences ;
- odds ;
- prédictions API-Football.

## Rôle Des 5 Référentiels Sous `docs/`

- `docs/api_football_reference.md` : documentation lisible des compétitions, équipes,
  fixtures, standings, rounds, venues, bookmakers et bets.
- `docs/api_football_reference.json` : source machine-readable pour charger, seed et
  valider leagues, teams, fixtures, venues, bookmakers et bets.
- `docs/api_football_players_reference.md` : documentation lisible des joueurs par
  compétition et équipe.
- `docs/api_football_players_reference.json` : source machine-readable pour charger,
  seed et valider players et squads.
- `docs/api_football_players_cache.json` : cache technique de collecte `/players/squads`,
  utilisable seulement pour reprendre ou éviter des appels API ; ce n'est pas la source
  métier principale.

Les IDs API-Football ne doivent jamais être inventés. Ils doivent venir des JSON locaux ou
de la base locale initialisée depuis eux.

## Référentiels, Snapshots Et API Live

Référentiels statiques :

- donnent les IDs, noms, stades, squads et métadonnées de base ;
- servent à économiser le quota API ;
- permettent de seed une base locale ;
- ne remplacent pas les données temporelles des features.

Snapshots dynamiques :

- représentent ce qui était connu à un moment donné ;
- portent `fetched_at`, `snapshot_date` ou `prediction_time` ;
- sont nécessaires pour éviter toute fuite de données ;
- alimentent les features et les backtests.

API live :

- doit être utilisée seulement sur demande explicite de refresh ou d'ingestion ;
- doit passer par un client centralisé ;
- doit stocker les payloads utiles en snapshots ;
- ne doit jamais exposer la clé API dans les logs ou les snapshots.
