# API-Football Player IDs

Generated at: `2026-05-02T09:09:36.880565+00:00`
Base URL: `https://v3.football.api-sports.io`
Endpoint: `/players/squads`
Requests made this run: `144`
Teams in scope: `144`
Teams fetched: `144`
Teams with errors: `0`
Players total: `4645`

## Objectif

Documentation des `player_id` API-Football pour les 5 championnats principaux et les equipes nationales de la CDM 2026.
Ces IDs servent ensuite aux squads, blessures, lineups, statistiques joueurs et rapprochements de noms.

## Notes

- Source utilisee: `/players/squads?team={team_id}`.
- Cet endpoint retourne l'effectif courant d'une equipe. Pour des statistiques joueur par saison, utiliser ensuite `/players?team={team_id}&season={season}`.
- Une equipe nationale peut retourner un groupe reduit ou vide selon la couverture API-Football disponible au moment de l'appel.
- Le fichier JSON garde la meme information dans une structure exploitable par le futur code.

## Resume par competition

| Competition | league_id | season | teams | teams fetched | players |
| --- | --- | --- | --- | --- | --- |
| Ligue 1 | 61 | 2025 | 18 | 18 | 562 |
| Premier League | 39 | 2025 | 20 | 20 | 611 |
| La Liga | 140 | 2025 | 20 | 20 | 683 |
| Bundesliga | 78 | 2025 | 18 | 18 | 528 |
| Serie A | 135 | 2025 | 20 | 20 | 645 |
| FIFA World Cup 2026 | 1 | 2026 | 48 | 48 | 1616 |


## Ligue 1

### Angers (`team_id=77`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `29`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 455243 | A. Moussaoui | 19 | 17 | Attacker |
| 191289 | A. Sbaï | 25 | 7 | Attacker |
| 579375 | Djibirin Harouna | 18 | 31 | Attacker |
| 20817 | G. Koyalipou | 25 | 9 | Attacker |
| 403277 | L. Machine | 20 | 36 | Attacker |
| 457541 | P. Peter | 18 | 35 | Attacker |
| 639473 | Yahia Jlidi | 17 | 44 | Attacker |
| 3234 | A. Bamba | 35 | 25 | Defender |
| 20850 | C. Arcus | 29 | 2 | Defender |
| 385569 | E. Biumla | 20 | 24 | Defender |
| 41146 | F. Hanin | 35 | 26 | Defender |
| 343609 | J. Ekomié | 22 | 3 | Defender |
| 21381 | J. Lefort | 32 | 21 | Defender |
| 174660 | L. Rao-Lisoa | 25 | 27 | Defender |
| 425207 | M. Courcoul | 18 | 5 | Defender |
| 570586 | M. Gernigon | 16 | 42 | Defender |
| 456831 | M. Louãr | 18 | 20 | Defender |
| 271540 | O. Camara | 22 | 4 | Defender |
| 22220 | H. Koffi | 29 | 12 | Goalkeeper |
| 174973 | M. Zinga | 23 | 16 | Goalkeeper |
| 396308 | Oumar Pona | 19 | 40 | Goalkeeper |
| 37652 | B. van den Boomen | 30 | 8 | Midfielder |
| 655113 | Bane Diatta | 17 | 46 | Midfielder |
| 419595 | Dan Sinaté | 19 | 23 | Midfielder |
| 20554 | H. Belkebla | 31 | 93 | Midfielder |
| 486627 | I. Garin | 19 | 38 | Midfielder |
| 289555 | L. Mouton | 23 | 6 | Midfielder |
| 21145 | P. Capelle | 38 | 15 | Midfielder |
| 174708 | Y. Belkhdim | 23 | 14 | Midfielder |


### Auxerre (`team_id=108`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 174915 | J. Casimir | 24 | 7 | Attacker |
| 90617 | L. Sinayoko | 26 | 10 | Attacker |
| 627298 | Mamoudou Cissokho | 17 | 44 | Attacker |
| 381123 | R. Rodin | 19 | 31 | Attacker |
| 190686 | S. Mara | 23 | 9 | Attacker |
| 613216 | Y. Zaddy | 19 | 41 | Attacker |
| 115588 | B. Okoh | 22 | 24 | Defender |
| 191189 | C. Akpa | 24 | 92 | Defender |
| 624607 | E. Diamalunda | 19 | 43 | Defender |
| 496787 | E. Legros | 17 | 35 | Defender |
| 31016 | F. Sierralta | 28 | 4 | Defender |
| 7578 | G. Mensah | 27 | 14 | Defender |
| 193953 | L. Sy | 23 | 27 | Defender |
| 191240 | M. Senaya | 24 | 29 | Defender |
| 162466 | S. Diomandé | 24 | 20 | Defender |
| 402542 | T. Siwe | 21 | 13 | Defender |
| 20542 | D. Léon | 33 | 16 | Goalkeeper |
| 614174 | Louis Mezerette | 19 | 37 | Goalkeeper |
| 193681 | T. De Percin | 24 | 40 | Goalkeeper |
| 275368 | T. Negrel | 22 | 30 | Goalkeeper |
| 30748 | A. Dioussé | 28 | 18 | Midfielder |
| 19625 | D. Namaso | 25 | 19 | Midfielder |
| 21010 | E. Owusu | 28 | 42 | Midfielder |
| 215827 | F. Oppegård | 23 | 22 | Midfielder |
| 323625 | K. Danois | 21 | 5 | Midfielder |
| 322595 | L. Coulibaly | 23 | 21 | Midfielder |
| 152418 | N. Ahamada | 23 | 8 | Midfielder |
| 319919 | O. El Azzouzi | 24 | 17 | Midfielder |
| 84082 | R. Faivre | 27 | 28 | Midfielder |
| 551415 | T. Devernois | 18 | 36 | Midfielder |


### Le Havre (`team_id=111`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 437349 | E. Koffi Vinette | 19 | 27 | Attacker |
| 961 | F. Mambimbi | 24 | 10 | Attacker |
| 21641 | G. Kyeremeh | 25 | 11 | Attacker |
| 584356 | K. Quetant | 19 | 33 | Attacker |
| 1945 | M. Samatta | 33 | 25 | Attacker |
| 437529 | N. Obougoujacquet | 18 | 20 | Attacker |
| 630733 | Yanis Beau Djellel | 20 | 34 | Attacker |
| 174927 | A. Sangante | 23 | 93 | Defender |
| 33165 | A. Seko | 25 | 15 | Defender |
| 64255 | G. Lloris | 30 | 4 | Defender |
| 2336 | L. Négo | 34 | 7 | Defender |
| 355955 | Rory Davidson | 25 | 4 | Defender |
| 513415 | Stephan Zagadou | 17 | 29 | Defender |
| 162067 | T. Pembélé | 23 | 32 | Defender |
| 23637 | Y. Zouaoui | 27 | 18 | Defender |
| 629834 | Yanis Monkolot | 16 | 14 | Defender |
| 162443 | É. Youté | 23 | 6 | Defender |
| 515772 | Alex Teixeira | 18 | 16 | Goalkeeper |
| 24012 | L. Mpasi | 31 | 77 | Goalkeeper |
| 119853 | M. Diaw | 32 | 99 | Goalkeeper |
| 395808 | Paul Argney | 19 | 50 | Goalkeeper |
| 471290 | A. Diabate | 20 | 39 | Midfielder |
| 21103 | A. Touré | 31 | 94 | Midfielder |
| 460805 | D. Mosengo | 19 | 78 | Midfielder |
| 174625 | F. Doucouré | 24 | 13 | Midfielder |
| 451961 | G. Zohouri | 18 | 24 | Midfielder |
| 156465 | I. Soumaré | 25 | 45 | Midfielder |
| 179843 | L. Gourna-Douath | 22 | 19 | Midfielder |
| 145476 | R. Khadra | 24 | 30 | Midfielder |
| 128342 | R. Ndiaye | 24 | 14 | Midfielder |
| 2710 | S. Boufal | 32 | 17 | Midfielder |
| 364093 | S. Ebonog | 21 | 26 | Midfielder |
| 630730 | Thierno Bah | 19 | 38 | Midfielder |
| 630731 | Thomas Rousseau | 17 | 37 | Midfielder |
| 174937 | Y. Kechta | 23 | 8 | Midfielder |


### Lens (`team_id=116`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 402066 | A. Bermont | 20 | 26 | Attacker |
| 22173 | A. Saint-Maximin | 28 | 9 | Attacker |
| 277191 | A. Sima | 24 | 19 | Attacker |
| 633361 | Erawan Garnier | 20 | 34 | Attacker |
| 20761 | F. Sotoca | 35 | 7 | Attacker |
| 1922 | F. Thauvin | 32 | 10 | Attacker |
| 1135 | O. Édouard | 27 | 11 | Attacker |
| 443579 | R. Fofana | 19 | 38 | Attacker |
| 21715 | W. Saïd | 30 | 22 | Attacker |
| 18816 | A. Masuaku | 32 | 27 | Defender |
| 369500 | I. Ganiou | 20 | 25 | Defender |
| 21635 | J. Gradit | 33 | 24 | Defender |
| 441264 | K. Antonio | 17 | 32 | Defender |
| 22166 | M. Sarr | 26 | 20 | Defender |
| 395589 | N. Äelik | 19 | 4 | Defender |
| 441256 | O. Lenne | 19 | 39 | Defender |
| 322984 | S. Baidoo | 21 | 6 | Defender |
| 44594 | Saud Abdulhamid | 26 | 23 | Defender |
| 437143 | A. Delplace | 19 | 50 | Goalkeeper |
| 497661 | I. Jourdren | 17 | 60 | Goalkeeper |
| 646 | M. Gorgelin | 35 | 16 | Goalkeeper |
| 21378 | R. Gurtner | 39 | 16 | Goalkeeper |
| 347211 | R. Risser | 21 | 40 | Goalkeeper |
| 394950 | A. Bulatović | 19 | 5 | Midfielder |
| 1153 | A. Haidara | 27 | 21 | Midfielder |
| 22261 | A. Thomasson | 32 | 28 | Midfielder |
| 395811 | F. Sylla | 19 | 18 | Midfielder |
| 277306 | M. Sangaré | 23 | 8 | Midfielder |
| 20525 | M. Udol | 29 | 14 | Midfielder |
| 21568 | R. Aguilar | 32 | 2 | Midfielder |


### Lille (`team_id=79`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `34`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 20732 | G. Perrin | 29 | 28 | Attacker |
| 306979 | H. Igamane | 23 | 29 | Attacker |
| 318416 | M. Broholm | 21 | 14 | Attacker |
| 340077 | M. Fernandez-Pardo | 20 | 7 | Attacker |
| 630702 | Matah Yondjio | 18 | 41 | Attacker |
| 430816 | N. Edjouma | 20 | 20 | Attacker |
| 2295 | O. Giroud | 39 | 9 | Attacker |
| 99576 | O. Sahraoui | 24 | 11 | Attacker |
| 487381 | S. Diaoune | 18 | 35 | Attacker |
| 368065 | Y. Lachaab | 20 | 43 | Attacker |
| 1567 | A. Mandi | 34 | 23 | Defender |
| 142691 | Alexsandro Ribeiro | 26 | 4 | Defender |
| 375 | C. Mbemba | 31 | 18 | Defender |
| 37151 | C. Verdonk | 28 | 24 | Defender |
| 437767 | M. Costarelli | 20 | 13 | Defender |
| 490745 | M. Goffi | 17 | 38 | Defender |
| 312964 | N. Ngoy | 22 | 3 | Defender |
| 20600 | R. Perraud | 28 | 15 | Defender |
| 264 | T. Meunier | 34 | 12 | Defender |
| 379329 | Tiago Santos | 23 | 22 | Defender |
| 2096 | A. Bodart | 27 | 16 | Goalkeeper |
| 1337 | B. Özer | 25 | 1 | Goalkeeper |
| 531323 | Samy Merzouk | 19 | 50 | Goalkeeper |
| 551417 | T. Sajous | 17 | 40 | Goalkeeper |
| 628379 | Zadig Lanssade | 17 | 60 | Goalkeeper |
| 438688 | A. Bouaddi | 18 | 32 | Midfielder |
| 2204 | B. André | 35 | 21 | Midfielder |
| 386287 | E. Mbappé | 19 | 8 | Midfielder |
| 135749 | Félix Correia | 24 | 27 | Midfielder |
| 67889 | H. Haraldsson | 22 | 10 | Midfielder |
| 401333 | L. Baret | 19 | 33 | Midfielder |
| 409 | N. Bentaleb | 31 | 6 | Midfielder |
| 375598 | N. Mukau | 21 | 17 | Midfielder |
| 630699 | Saad Boussadia | 17 | 42 | Midfielder |


### Lorient (`team_id=97`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 72457 | A. Tosin | 27 | 15 | Attacker |
| 284072 | B. Dieng | 25 | 12 | Attacker |
| 22171 | J. Makengo | 27 | 17 | Attacker |
| 200873 | M. Bamba | 24 | 9 | Attacker |
| 434785 | M. Bley | 19 | 34 | Attacker |
| 608028 | M. Kone |  | 33 | Attacker |
| 276662 | P. Pagis | 23 | 10 | Attacker |
| 144319 | S. Soumano | 24 | 28 | Attacker |
| 401389 | T. Sanusi | 18 | 14 | Attacker |
| 437776 | A. Faye | 21 | 25 | Defender |
| 193501 | B. Meité | 24 | 5 | Defender |
| 152669 | D. Yongwa | 25 | 44 | Defender |
| 399903 | I. Akakpo | 21 | 33 | Defender |
| 1031 | Igor Silva | 29 | 2 | Defender |
| 463613 | L. Leaudais | 21 | 35 | Defender |
| 50030 | M. Talbi | 27 | 3 | Defender |
| 214310 | N. Adjei | 23 | 32 | Defender |
| 632809 | Noah Le Gal |  | 17 | Defender |
| 446829 | S. Siba | 19 | 97 | Defender |
| 22241 | B. Kamara | 29 | 21 | Goalkeeper |
| 20936 | B. Leroy | 36 | 16 | Goalkeeper |
| 1142 | Y. Mvogo | 31 | 38 | Goalkeeper |
| 402265 | A. Avom | 21 | 62 | Midfielder |
| 162018 | B. Fadiga | 24 | 7 | Midfielder |
| 322865 | D. Karim | 22 | 29 | Midfielder |
| 629869 | D. Semedo | 22 | 35 | Midfielder |
| 486028 | I. Monnier | 19 | 19 | Midfielder |
| 402386 | K. Kouassi | 21 | 43 | Midfielder |
| 20917 | L. Abergel | 32 | 6 | Midfielder |
| 23363 | N. Cadiou | 27 | 8 | Midfielder |
| 384112 | P. Katseris | 24 | 77 | Midfielder |
| 174703 | T. Le Bris | 23 | 11 | Midfielder |


### Lyon (`team_id=80`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 361348 | M. Fofana | 20 | 11 | Attacker |
| 18780 | R. Ghezzal | 33 | 18 | Attacker |
| 497617 | R. Himbert | 17 | 45 | Attacker |
| 8493 | R. Yaremchuk | 30 | 77 | Attacker |
| 1456 | A. Maitland-Niles | 28 | 98 | Defender |
| 9700 | Abner | 25 | 16 | Defender |
| 68 | Clinton Mata | 33 | 22 | Defender |
| 30423 | H. Hateboer | 31 | 33 | Defender |
| 25916 | M. Niakhaté | 29 | 19 | Defender |
| 493026 | N. Kamara | 18 | 85 | Defender |
| 529 | N. Tagliafico | 33 | 3 | Defender |
| 637593 | Prince Mbatshi Mukuba | 20 | 67 | Defender |
| 193293 | R. Kluivert | 24 | 21 | Defender |
| 645969 | Steeve Kango | 19 | 34 | Defender |
| 61142 | D. Greif | 28 | 1 | Goalkeeper |
| 392671 | L. Diarra | 23 | 20 | Goalkeeper |
| 497080 | M. Da Silva | 18 | 35 | Goalkeeper |
| 20762 | R. Descamps | 29 | 40 | Goalkeeper |
| 438694 | Y. Konan | 18 | 30 | Goalkeeper |
| 623922 | A. Hamdani | 16 | 84 | Midfielder |
| 199871 | A. Karabec | 22 | 7 | Midfielder |
| 345388 | Afonso Moreira | 20 | 17 | Midfielder |
| 519 | C. Tolisso | 31 | 8 | Midfielder |
| 377122 | Endrick | 19 | 9 | Midfielder |
| 519664 | K. Merah | 18 | 44 | Midfielder |
| 438692 | M. de Carvalho | 20 | 39 | Midfielder |
| 361352 | N. Nartey | 20 | 99 | Midfielder |
| 24882 | O. Mangala | 27 | 5 | Midfielder |
| 66387 | P. Šulc | 25 | 10 | Midfielder |
| 585333 | T. Goncalves | 18 | 46 | Midfielder |
| 162590 | T. Morton | 23 | 23 | Midfielder |
| 80752 | T. Tessmann | 24 | 6 | Midfielder |


### Marseille (`team_id=81`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `29`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 85041 | A. Gouiri | 25 | 9 | Attacker |
| 606267 | Ange Lago | 20 | 78 | Attacker |
| 9363 | Igor Paixão | 25 | 14 | Attacker |
| 897 | M. Greenwood | 24 | 10 | Attacker |
| 1465 | P. Aubameyang | 36 | 17 | Attacker |
| 38747 | Q. Timber | 24 | 27 | Attacker |
| 568058 | U. Lamare El Kadmiri | 18 | 70 | Attacker |
| 2725 | B. Pavard | 29 | 28 | Defender |
| 181827 | C. Egan-Riley | 22 | 4 | Defender |
| 6231 | F. Medina | 26 | 32 | Defender |
| 656975 | Hilan Hamzaoui Slimani | 20 | 72 | Defender |
| 6 | L. Balerdi | 26 | 5 | Defender |
| 21694 | N. Aguerd | 29 | 21 | Defender |
| 568242 | P. N'Zinga Pambani | 18 | 5 | Defender |
| 47296 | G. Rulli | 33 | 1 | Goalkeeper |
| 336654 | J. Van Neck | 21 | 40 | Goalkeeper |
| 36827 | J. de Lange | 27 | 12 | Goalkeeper |
| 340154 | A. Vermeeren | 20 | 18 | Midfielder |
| 283216 | B. Nadir | 22 | 26 | Midfielder |
| 313236 | E. Nwaneri | 18 | 11 | Midfielder |
| 2284 | Emerson | 31 | 33 | Midfielder |
| 926 | G. Kondogbia | 32 | 19 | Midfielder |
| 20692 | H. Abdelli | 26 | 8 | Midfielder |
| 31057 | H. Traorè | 25 | 20 | Midfielder |
| 656976 | Nouhoum Kamissoko | 21 | 71 | Midfielder |
| 2735 | P. Højbjerg | 30 | 23 | Midfielder |
| 562661 | T. Mmadi | 18 | 76 | Midfielder |
| 354298 | T. Nnadi | 22 | 6 | Midfielder |
| 1138 | T. Weah | 25 | 22 | Midfielder |


### Metz (`team_id=112`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 404588 | C. Melieres | 20 | 25 | Attacker |
| 68177 | G. Abuashvili | 22 | 9 | Attacker |
| 20529 | G. Hein | 29 | 10 | Attacker |
| 8490 | G. Kvilitaia | 32 | 11 | Attacker |
| 20535 | H. Diallo | 30 | 30 | Attacker |
| 647405 | J. Pandore | 18 | 35 | Attacker |
| 343319 | L. Michal | 20 | 19 | Attacker |
| 584096 | N. Mbala | 17 | 34 | Attacker |
| 105 | F. Ballo-Touré | 28 | 97 | Defender |
| 96331 | K. Kouao | 27 | 39 | Defender |
| 19518 | M. Colin | 34 | 2 | Defender |
| 613215 | Moustapha Diop |  | 3 | Defender |
| 428084 | Sadibou Sané | 21 | 38 | Defender |
| 363792 | T. Yegbe | 24 | 15 | Defender |
| 378353 | U. Mboula | 22 | 4 | Defender |
| 456867 | Yannis Lawson | 21 | 27 | Defender |
| 158532 | J. Fischer | 24 | 1 | Goalkeeper |
| 237198 | O. Ba | 23 | 40 | Goalkeeper |
| 403878 | P. Sy | 28 | 61 | Goalkeeper |
| 613214 | Romain Jean-Baptiste | 19 | 16 | Goalkeeper |
| 434352 | A. Touré | 19 | 12 | Midfielder |
| 570580 | B. Munongo | 15 | 33 | Midfielder |
| 1915 | B. Sarr | 32 | 70 | Midfielder |
| 407 | B. Stambouli | 35 | 21 | Midfielder |
| 157912 | B. Traoré | 24 | 8 | Midfielder |
| 2181 | G. Tsitaishvili | 25 | 7 | Midfielder |
| 384683 | I. Guerti | 21 | 29 | Midfielder |
| 21640 | J. Deminguet | 27 | 20 | Midfielder |
| 3240 | J. Gbamin | 30 | 5 | Midfielder |
| 629779 | Tahirys Dos Santos | 19 | 17 | Midfielder |


### Monaco (`team_id=91`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 135775 | Ansu Fati | 23 | 31 | Attacker |
| 138835 | F. Balogun | 24 | 9 | Attacker |
| 274300 | M. Akliouche | 23 | 11 | Attacker |
| 283026 | M. Biereth | 22 | 14 | Attacker |
| 386276 | Paris Josua  Brunner | 19 | 29 | Attacker |
| 1101 | T. Minamino | 30 | 8 | Attacker |
| 399893 | B. Kiwa | 19 | 43 | Defender |
| 371916 | C. Mawissa Elebi | 20 | 13 | Defender |
| 10316 | Caio Henrique | 28 | 12 | Defender |
| 175 | E. Dier | 31 | 3 | Defender |
| 333137 | K. Ouattara | 21 | 20 | Defender |
| 47480 | M. Salisu | 26 | 22 | Defender |
| 261 | T. Kehrer | 29 | 5 | Defender |
| 291649 | Vanderson | 24 | 2 | Defender |
| 8694 | W. Faes | 27 | 25 | Defender |
| 440070 | J. Stawiecki | 18 | 40 | Goalkeeper |
| 963 | L. Hrádecký | 36 | 1 | Goalkeeper |
| 7313 | P. Köhn | 27 | 16 | Goalkeeper |
| 274296 | Y. Lienard | 22 | 50 | Goalkeeper |
| 453792 | A. Bamba | 19 | 23 | Midfielder |
| 109 | A. Golovin | 29 | 10 | Midfielder |
| 2810 | D. Zakaria | 29 | 6 | Midfielder |
| 531402 | I. Toure | 19 | 49 | Midfielder |
| 231 | J. Teze | 26 | 4 | Midfielder |
| 81 | K. Diatta | 26 | 27 | Midfielder |
| 374058 | L. Camara | 21 | 15 | Midfielder |
| 419035 | M. Coulibaly | 21 | 28 | Midfielder |
| 904 | P. Pogba | 32 | 8 | Midfielder |
| 543470 | Pape Cabral | 18 | 41 | Midfielder |
| 301771 | S. Adingra | 23 | 24 | Midfielder |
| 340152 | S. Idumbo-Muzambo | 20 | 17 | Midfielder |
| 449676 | S. Nibombé | 18 | 44 | Midfielder |


### Nantes (`team_id=83`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 428504 | A. Camara | 20 | 14 | Attacker |
| 443676 | Bahereba Guirassy | 19 | 11 | Attacker |
| 22177 | I. Ganago | 26 | 37 | Attacker |
| 610593 | J. Kone | 18 | 49 | Attacker |
| 2668 | Mostafa Mohamed | 28 | 31 | Attacker |
| 42086 | Y. El-Arabi | 38 | 19 | Attacker |
| 364810 | A. Sylla | 23 | 4 | Defender |
| 304427 | Ali Yousef Musrati | 24 | 2 | Defender |
| 50026 | C. Awaziem | 29 | 6 | Defender |
| 2483 | D. Machado | 32 | 27 | Defender |
| 20654 | F. Centonze | 29 | 18 | Defender |
| 21636 | F. Guilbert | 31 | 24 | Defender |
| 22134 | K. Amian | 27 | 98 | Defender |
| 386438 | M. Acapandié | 21 | 22 | Defender |
| 21570 | N. Cozza | 26 | 3 | Defender |
| 392569 | Sékou Doucouré | 20 | 72 | Defender |
| 522609 | T. Tati | 17 | 78 | Defender |
| 66013 | U. Radaković | 31 | 26 | Defender |
| 331856 | A. Mirbach | 20 | 50 | Goalkeeper |
| 647 | Anthony Lopes | 35 | 1 | Goalkeeper |
| 15684 | P. Carlgren | 34 | 30 | Goalkeeper |
| 443755 | B. Deuff | 19 | 52 | Midfielder |
| 388779 | D. Assoumani | 20 | 17 | Midfielder |
| 924 | F. Coquelin | 34 | 13 | Midfielder |
| 22260 | I. Sissoko | 28 | 28 | Midfielder |
| 193952 | J. Lepenant | 23 | 8 | Midfielder |
| 443674 | Louis Leroux | 19 | 66 | Midfielder |
| 161622 | M. Abline | 22 | 10 | Midfielder |
| 197779 | M. Kaba | 24 | 21 | Midfielder |
| 22093 | R. Cabella | 35 | 20 | Midfielder |
| 554353 | Sacha Ziani | 22 | 69 | Midfielder |


### Nice (`team_id=84`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `38`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 162707 | E. Wahi | 22 | 11 | Attacker |
| 603533 | Enguerrand Bouard | 18 | 38 | Attacker |
| 105154 | I. Jansson | 23 | 21 | Attacker |
| 607082 | J. Telusson | 17 | 42 | Attacker |
| 405237 | K. Boudache | 17 | 32 | Attacker |
| 188319 | Kevin Carlos | 24 | 90 | Attacker |
| 637591 | Kéfren Ali | 18 | 52 | Attacker |
| 158065 | Tiago Gouveia | 24 | 47 | Attacker |
| 362470 | Z. Diallo | 20 | 44 | Attacker |
| 49583 | A. Abdi | 32 | 2 | Defender |
| 313937 | A. Mendy | 21 | 33 | Defender |
| 449509 | Abdulay Bah | 19 | 28 | Defender |
| 611321 | Brad-Hamilton Mantsounga | 18 | 36 | Defender |
| 22163 | Dante | 42 | 4 | Defender |
| 25008 | J. Clauss | 33 | 92 | Defender |
| 404172 | K. Peprah Oppong | 21 | 37 | Defender |
| 339620 | L. Monteiro Alvarenga | 21 | 48 | Defender |
| 162465 | M. Bard | 25 | 26 | Defender |
| 444562 | M. Youssouf | 19 | 43 | Defender |
| 196343 | Mohamed Abdelmonem | 26 | 5 | Defender |
| 637439 | Yanis Sofikitis | 18 | 53 | Defender |
| 401493 | B. Żelazowski | 20 | 30 | Goalkeeper |
| 21079 | M. Dupé | 32 | 31 | Goalkeeper |
| 526451 | T. Bruyère | 19 | 50 | Goalkeeper |
| 20566 | Y. Diouf | 26 | 80 | Goalkeeper |
| 8680 | C. Vanhoutte | 27 | 24 | Midfielder |
| 504157 | D. Coulibaly | 17 | 39 | Midfielder |
| 442866 | E. Pereira | 18 | 41 | Midfielder |
| 483118 | G. Bernardeau | 19 | 23 | Midfielder |
| 4399 | H. Boudaoui | 26 | 6 | Midfielder |
| 629379 | M. Brignone | 18 | 45 | Midfielder |
| 274312 | M. Cho | 21 | 25 | Midfielder |
| 1914 | M. Sanson | 31 | 8 | Midfielder |
| 128987 | S. Abdul Samed | 25 | 99 | Midfielder |
| 107 | S. Diop | 25 | 10 | Midfielder |
| 193617 | T. Louchet | 22 | 20 | Midfielder |
| 662 | T. Ndombélé | 29 | 22 | Midfielder |
| 3099 | Y. Ndayishimiye | 27 | 55 | Midfielder |


### Paris FC (`team_id=114`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 20704 | A. Gory | 29 | 7 | Attacker |
| 1863 | C. Immobile | 35 | 36 | Attacker |
| 22842 | J. Krasso | 28 | 11 | Attacker |
| 20599 | J. López | 33 | 20 | Attacker |
| 23126 | L. Gueye | 27 | 26 | Attacker |
| 359603 | L. Koleosho | 21 | 24 | Attacker |
| 22003 | M. Cafaro | 28 | 13 | Attacker |
| 629706 | Mohamed Dao | 18 | 18 | Attacker |
| 20647 | P. Hamel | 31 | 29 | Attacker |
| 120 | W. Geubbels | 24 | 9 | Attacker |
| 84218 | A. Camara | 29 | 17 | Defender |
| 342063 | D. Coppola | 22 | 42 | Defender |
| 2202 | H. Traoré | 33 | 14 | Defender |
| 613217 | K. Prouchet | 20 | 36 | Defender |
| 174881 | M. Mbow | 25 | 5 | Defender |
| 389322 | N. Sangui | 19 | 19 | Defender |
| 266013 | Otávio | 23 | 6 | Defender |
| 20869 | S. Chergui | 26 | 31 | Defender |
| 8474 | T. De Smet | 27 | 28 | Defender |
| 22086 | T. Kolodziejczak | 34 | 15 | Defender |
| 55819 | T. Ollila | 25 | 2 | Defender |
| 1800 | K. Trapp | 35 | 35 | Goalkeeper |
| 194981 | O. Nkambadio | 22 | 16 | Goalkeeper |
| 83831 | I. Kebbal | 27 | 10 | Midfielder |
| 22229 | J. Ikoné | 27 | 93 | Midfielder |
| 1910 | M. Lopez | 28 | 21 | Midfielder |
| 3080 | M. Munetsi | 29 | 18 | Midfielder |
| 2781 | M. Simon | 30 | 27 | Midfielder |
| 22170 | P. Lees-Melou | 32 | 33 | Midfielder |
| 496896 | R. Matondo | 17 | 23 | Midfielder |
| 20925 | V. Marchetti | 28 | 4 | Midfielder |
| 629705 | Zakarya Khaldi | 20 | 15 | Midfielder |


### Paris Saint Germain (`team_id=85`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `28`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 161904 | B. Barcola | 23 | 29 | Attacker |
| 343027 | D. Doué | 20 | 14 | Attacker |
| 41585 | Gonçalo Ramos | 24 | 9 | Attacker |
| 446249 | I. Mbaye | 17 | 49 | Attacker |
| 483 | K. Kvaratskhelia | 24 | 7 | Attacker |
| 543469 | Mathis Jangeal | 17 | 24 | Attacker |
| 153 | O. Dembélé | 28 | 10 | Attacker |
| 471107 | Quentin Ndjantou Mbitcha | 18 | 5 | Attacker |
| 9 | A. Hakimi | 27 | 2 | Defender |
| 307835 | Beraldo | 22 | 4 | Defender |
| 610763 | D. Boly | 16 | 42 | Defender |
| 161671 | I. Zabarnyi | 23 | 6 | Defender |
| 33 | L. Hernández | 29 | 21 | Defender |
| 257 | Marquinhos | 31 | 5 | Defender |
| 263482 | Nuno Mendes | 23 | 25 | Defender |
| 16367 | W. Pacho | 24 | 51 | Defender |
| 162453 | L. Chevalier | 24 | 30 | Goalkeeper |
| 568266 | M. James | 17 | 60 | Goalkeeper |
| 2068 | M. Safonov | 26 | 39 | Goalkeeper |
| 437099 | Renato Bellucci | 19 | 89 | Goalkeeper |
| 328 | Fabián Ruiz | 29 | 8 | Midfielder |
| 335051 | João Neves | 21 | 87 | Midfielder |
| 927 | Lee Kang-In | 24 | 19 | Midfielder |
| 567804 | N. Nsoki | 18 | 20 | Midfielder |
| 491087 | Pedro Fernández | 17 | 27 | Midfielder |
| 409216 | Senny Mayulu | 19 | 24 | Midfielder |
| 128384 | Vitinha | 25 | 17 | Midfielder |
| 336657 | W. Zaïre-Emery | 19 | 33 | Midfielder |


### Rennes (`team_id=94`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 22097 | A. Nordin | 27 | 70 | Attacker |
| 421 | B. Embolo | 28 | 7 | Attacker |
| 163004 | E. Lepaul | 25 | 9 | Attacker |
| 625629 | Elias Legendre Quiñonez | 17 | 35 | Attacker |
| 456765 | H. Do Marcolino | 19 | 69 | Attacker |
| 585073 | L. Rosier | 18 | 12 | Attacker |
| 457101 | M. Zabiri | 20 | 77 | Attacker |
| 399890 | N. Mukiele | 19 | 65 | Attacker |
| 417830 | A. Ait Boudlal | 19 | 48 | Defender |
| 129681 | A. Rouault | 24 | 24 | Defender |
| 196187 | A. Seidu | 25 | 36 | Defender |
| 653231 | Isiaka Soukouna | 20 | 67 | Defender |
| 367636 | J. Jacquet | 20 | 97 | Defender |
| 640701 | Junior Ake | 18 | 75 | Defender |
| 126757 | L. Brassier | 26 | 3 | Defender |
| 438281 | M. Nagida | 20 | 18 | Defender |
| 3007 | P. Frankowski | 30 | 95 | Defender |
| 272460 | Q. Merlin | 23 | 26 | Defender |
| 562237 | Ayoube Akabou | 18 | 80 | Goalkeeper |
| 21628 | B. Samba | 31 | 30 | Goalkeeper |
| 601332 | Kilian Belazzoug | 19 | 60 | Goalkeeper |
| 361462 | M. Silistrie | 20 | 50 | Goalkeeper |
| 639279 | Chibuike Ugochukwu | 17 | 79 | Midfielder |
| 343792 | D. Cissé | 21 | 6 | Midfielder |
| 1754 | G. Kamara | 30 | 4 | Midfielder |
| 21497 | L. Blas | 28 | 10 | Midfielder |
| 24147 | M. Camara | 27 | 45 | Midfielder |
| 15286 | Mousa Tamari | 28 | 11 | Midfielder |
| 629380 | P. Limon | 20 | 13 | Midfielder |
| 40403 | S. Szymański | 26 | 17 | Midfielder |
| 21102 | V. Rongier | 31 | 21 | Midfielder |


### Stade Brestois 29 (`team_id=106`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `25`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 554352 | Ibrahim Yayiya Kante | 18 | 21 | Attacker |
| 22264 | L. Ajorque | 31 | 19 | Attacker |
| 41323 | Mama Baldé | 30 | 17 | Attacker |
| 375990 | P. Mboup | 22 | 99 | Attacker |
| 326073 | R. Labeau Lascary | 22 | 14 | Attacker |
| 485957 | Serigne Diop | 20 | 29 | Attacker |
| 20546 | B. Chardonnet | 31 | 5 | Defender |
| 274267 | B. Locko | 23 | 2 | Defender |
| 302868 | D. Guindo | 23 | 27 | Defender |
| 22247 | K. Lala | 34 | 77 | Defender |
| 422595 | L. Zogbe | 20 | 12 | Defender |
| 365742 | M. Diaz | 22 | 4 | Defender |
| 498791 | R. Le Guen | 19 | 71 | Defender |
| 162568 | S. Coulibaly | 22 | 44 | Defender |
| 21248 | G. Coudert | 26 | 30 | Goalkeeper |
| 348052 | N. Jauny | 21 | 50 | Goalkeeper |
| 40384 | R. Majecki | 26 | 1 | Goalkeeper |
| 629780 | Bernard Geraux Noan Didier | 19 | 19 | Midfielder |
| 20558 | H. Magnetti | 27 | 8 | Midfielder |
| 449153 | H. Makalou | 19 | 33 | Midfielder |
| 128287 | J. Chotard | 24 | 13 | Midfielder |
| 90594 | J. Dina Ebimbe | 25 | 7 | Midfielder |
| 326068 | K. Doumbia | 22 | 23 | Midfielder |
| 664 | L. Tousart | 28 | 24 | Midfielder |
| 2214 | R. Del Castillo | 29 | 10 | Midfielder |


### Strasbourg (`team_id=95`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 291476 | D. Fofana | 23 | 15 | Attacker |
| 335056 | Diego Moreira | 21 | 7 | Attacker |
| 203762 | E. Emegha | 22 | 10 | Attacker |
| 488976 | G. Kodia | 18 | 37 | Attacker |
| 70747 | J. Enciso | 21 | 19 | Attacker |
| 390742 | J. Panichelli | 23 | 9 | Attacker |
| 629148 | Jean-Baptiste Bosey | 17 | 33 | Attacker |
| 359386 | M. Godo | 22 | 20 | Attacker |
| 226803 | S. Nanasi | 23 | 11 | Attacker |
| 422780 | A. Anselmino | 20 | 5 | Defender |
| 551210 | A. Cisse | 19 | 45 | Defender |
| 147835 | A. Omobamidele | 23 | 2 | Defender |
| 2933 | B. Chilwell | 29 | 3 | Defender |
| 161747 | G. Doué | 23 | 22 | Defender |
| 271542 | I. Doukouré | 22 | 6 | Defender |
| 282549 | J. Mwanga | 22 | 18 | Defender |
| 396193 | L. Høgsberg | 19 | 24 | Defender |
| 303016 | M. Oyedele | 21 | 8 | Defender |
| 585206 | Y. Becker | 17 | 35 | Defender |
| 494590 | G. Kerckaert | 18 | 60 | Goalkeeper |
| 2850 | K. Johnsson | 35 | 1 | Goalkeeper |
| 340151 | M. Penders | 20 | 39 | Goalkeeper |
| 129673 | S. Bajić | 24 | 50 | Goalkeeper |
| 358166 | A. Ouattara | 20 | 42 | Midfielder |
| 369544 | Gessime Yassine | 20 | 80 | Midfielder |
| 656711 | Idrissa Sabaly | 18 | 34 | Midfielder |
| 395762 | M. Amougou | 19 | 17 | Midfielder |
| 584192 | M. Marechal | 18 | 46 | Midfielder |
| 345416 | Rafael LuÃ­s | 20 | 83 | Midfielder |
| 334035 | S. Amo-Ameyaw | 19 | 27 | Midfielder |
| 415431 | S. El Mourabet | 20 | 29 | Midfielder |
| 588425 | Tyrese Noubissie | 16 | 28 | Midfielder |
| 319572 | V. Barco | 21 | 32 | Midfielder |


### Toulouse (`team_id=96`)

- Competition: `Ligue 1`
- League ID: `61`
- Season: `2025`
- Country: `France`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 492727 | E. Faty | 18 | 20 | Attacker |
| 321648 | Emersonn | 21 | 20 | Attacker |
| 174724 | F. Magri | 26 | 9 | Attacker |
| 203428 | J. Russell-Rowe | 23 | 13 | Attacker |
| 457025 | Julián Vignolo | 19 | 7 | Attacker |
| 339417 | P. Diop | 22 | 18 | Attacker |
| 362741 | S. Hidalgo | 20 | 11 | Attacker |
| 489903 | Y. Azizi | 17 | 37 | Attacker |
| 84128 | Y. Gboho | 24 | 10 | Attacker |
| 278392 | C. Cresswell | 23 | 4 | Defender |
| 102 | D. Sidibé | 33 | 19 | Defender |
| 584362 | G. Bakhouche Piernas | 20 | 44 | Defender |
| 580818 | Louis Reynaud | 17 | 18 | Defender |
| 50735 | M. McKenzie | 26 | 3 | Defender |
| 366573 | N. Wasbauer | 21 | 12 | Defender |
| 15793 | R. Nicolaisen | 28 | 2 | Defender |
| 489905 | S. Koumbassa | 18 | 35 | Defender |
| 449543 | T. Garondo | 19 | 42 | Defender |
| 264383 | W. Kamanzi | 25 | 12 | Defender |
| 325346 | G. Restes | 20 | 1 | Goalkeeper |
| 39104 | K. Haug | 27 | 16 | Goalkeeper |
| 571904 | N. Said Mchindra | 20 | 40 | Goalkeeper |
| 47351 | Álex Domínguez | 27 | 16 | Goalkeeper |
| 39115 | A. Dønnum | 27 | 15 | Midfielder |
| 118345 | A. Francis | 24 | 17 | Midfielder |
| 514464 | A. Vossah | 17 | 45 | Midfielder |
| 50956 | C. Cásseres | 25 | 23 | Midfielder |
| 452697 | D. Methalie | 19 | 24 | Midfielder |
| 304140 | M. Sauer | 21 | 77 | Midfielder |
| 385351 | N. Lahmadi | 20 | 34 | Midfielder |
| 334952 | R. Messali | 22 | 22 | Midfielder |



## Premier League

### Arsenal (`team_id=42`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 457731 | A. Annous | 18 | 11 | Attacker |
| 463908 | B. Bailey-Joseph | 17 | 7 | Attacker |
| 1460 | B. Saka | 24 | 7 | Attacker |
| 557442 | C. O'Neill | 17 | 10 | Attacker |
| 19586 | E. Eze | 27 | 10 | Attacker |
| 643 | Gabriel Jesus | 28 | 9 | Attacker |
| 127769 | Gabriel Martinelli | 24 | 11 | Attacker |
| 978 | K. Havertz | 26 | 29 | Attacker |
| 1946 | L. Trossard | 31 | 19 | Attacker |
| 136723 | N. Madueke | 23 | 20 | Attacker |
| 18979 | V. Gyökeres | 27 | 14 | Attacker |
| 19959 | B. White | 28 | 4 | Defender |
| 333682 | Cristhian Mosquera | 21 | 3 | Defender |
| 22224 | Gabriel Magalhães | 28 | 6 | Defender |
| 38746 | J. Timber | 24 | 12 | Defender |
| 418403 | Jaden Dixon | 18 | 2 | Defender |
| 380696 | Joshua Nichols | 19 | 2 | Defender |
| 313245 | M. Lewis-Skelly | 19 | 49 | Defender |
| 482903 | M. Salmon | 16 | 89 | Defender |
| 127817 | P. Hincapié | 23 | 5 | Defender |
| 157052 | R. Calafiori | 23 | 33 | Defender |
| 22090 | W. Saliba | 24 | 2 | Defender |
| 337933 | Alexei Rojas Fedorushchenko | 20 | 51 | Goalkeeper |
| 19465 | David Raya | 30 | 1 | Goalkeeper |
| 416697 | J. Porter | 17 | 13 | Goalkeeper |
| 403221 | K. Ranson | 18 | 1 | Goalkeeper |
| 2273 | Kepa | 31 | 13 | Goalkeeper |
| 342243 | T. Setford | 19 | 1 | Goalkeeper |
| 30407 | C. Nørgaard | 31 | 16 | Midfielder |
| 2937 | D. Rice | 26 | 41 | Midfielder |
| 553530 | I. Ibrahim | 17 | 6 | Midfielder |
| 442044 | M. Dowman | 16 | 56 | Midfielder |
| 37127 | M. Ødegaard | 27 | 8 | Midfielder |
| 47315 | Martín Zubimendi | 26 | 36 | Midfielder |
| 47311 | Mikel Merino | 29 | 23 | Midfielder |


### Aston Villa (`team_id=66`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 464004 | Alysson Edward | 19 | 47 | Attacker |
| 514519 | Brian Madjo | 16 | 24 | Attacker |
| 18 | J. Sancho | 25 | 19 | Attacker |
| 983 | L. Bailey | 28 | 31 | Attacker |
| 19366 | O. Watkins | 30 | 11 | Attacker |
| 19194 | T. Abraham | 28 | 18 | Attacker |
| 553848 | T. Mulley | 18 | 9 | Attacker |
| 388013 | Andrés García | 22 | 16 | Defender |
| 19354 | E. Konsa | 28 | 4 | Defender |
| 138816 | I. Maatsen | 23 | 22 | Defender |
| 2724 | L. Digne | 32 | 12 | Defender |
| 482915 | L. Routh | 18 | 13 | Defender |
| 19298 | M. Cash | 28 | 2 | Defender |
| 46815 | Pau Torres | 28 | 14 | Defender |
| 19179 | T. Mings | 32 | 5 | Defender |
| 889 | V. Lindelöf | 31 | 3 | Defender |
| 415107 | Y. Mosquera | 20 | 5 | Defender |
| 19599 | E. Martínez | 33 | 23 | Goalkeeper |
| 284390 | J. Wright | 21 | 64 | Goalkeeper |
| 36878 | M. Bizot | 34 | 40 | Goalkeeper |
| 452427 | R. Oakley | 17 | 13 | Goalkeeper |
| 398004 | S. Proctor | 19 | 1 | Goalkeeper |
| 162714 | A. Onana | 24 | 24 | Midfielder |
| 1904 | B. Kamara | 26 | 44 | Midfielder |
| 47522 | Douglas Luiz | 27 | 21 | Midfielder |
| 19071 | E. Buendía | 29 | 10 | Midfielder |
| 364566 | George Hemmings | 18 | 11 | Midfielder |
| 19035 | H. Elliott | 22 | 9 | Midfielder |
| 19191 | J.  McGinn | 31 | 7 | Midfielder |
| 284457 | L. Bogarde | 21 | 26 | Midfielder |
| 553420 | M. Kone | 18 | 6 | Midfielder |
| 19170 | M. Rogers | 23 | 27 | Midfielder |
| 2287 | R. Barkley | 32 | 6 | Midfielder |
| 416250 | T. Carroll | 19 | 4 | Midfielder |
| 2926 | Y. Tielemans | 28 | 8 | Midfielder |


### Bournemouth (`team_id=35`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `29`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 129682 | A. Adli | 25 | 21 | Attacker |
| 343576 | B. Doak | 20 | 11 | Attacker |
| 47499 | E. Ünal | 28 | 26 | Attacker |
| 152856 | Evanilson | 26 | 9 | Attacker |
| 792 | J. Kluivert | 26 | 19 | Attacker |
| 407806 | Rayan | 19 | 37 | Attacker |
| 402434 | Remy Rees-Dottin | 19 | 50 | Attacker |
| 18869 | A. Smith | 34 | 15 | Defender |
| 162267 | A. Truffert | 24 | 3 | Defender |
| 22136 | B. Diakité | 24 | 18 | Defender |
| 20093 | J. Hill | 23 | 23 | Defender |
| 363333 | J. Soler | 20 | 6 | Defender |
| 6610 | M. Senesi | 28 | 5 | Defender |
| 412719 | Veljko Milosavljević | 18 | 44 | Defender |
| 330437 | Álex Jiménez | 20 | 20 | Defender |
| 26644 | C. Mandas | 24 | 29 | Goalkeeper |
| 18932 | F. Forster | 37 | 17 | Goalkeeper |
| 118307 | Đ. Petrović | 26 | 1 | Goalkeeper |
| 304853 | A. Scott | 22 | 8 | Midfielder |
| 361485 | A. Tóth | 20 | 27 | Midfielder |
| 573755 | C. Stevens | 18 | 53 | Midfielder |
| 18870 | D. Brooks | 28 | 7 | Midfielder |
| 368030 | E. Kroupi | 19 | 22 | Midfielder |
| 18872 | L. Cook | 28 | 4 | Midfielder |
| 19245 | M. Tavernier | 26 | 16 | Midfielder |
| 626383 | Malcom Dacosta | 17 | 51 | Midfielder |
| 390769 | Michael Dacosta | 20 | 51 | Midfielder |
| 1125 | R. Christie | 30 | 10 | Midfielder |
| 1150 | T. Adams | 26 | 12 | Midfielder |


### Brentford (`team_id=55`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `28`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 393193 | Kaye Iyowuna Furo | 18 | 47 | Attacker |
| 727 | R. Nelson | 26 | 11 | Attacker |
| 196156 | Thiago | 24 | 9 | Attacker |
| 44871 | A. Hickey | 23 | 2 | Defender |
| 19789 | E. Pinnock | 32 | 5 | Defender |
| 577002 | J. Stephenson | 18 | 50 | Defender |
| 1119 | K. Ajer | 27 | 20 | Defender |
| 106725 | K. Lewis-Potter | 24 | 23 | Defender |
| 342022 | M. Kayode | 21 | 33 | Defender |
| 19495 | N. Collins | 24 | 22 | Defender |
| 624708 | O. Shield | 19 | 49 | Defender |
| 19346 | R. Henry | 28 | 3 | Defender |
| 36922 | S. van den Berg | 24 | 4 | Defender |
| 281 | C. Kelleher | 27 | 1 | Goalkeeper |
| 19340 | E. Balcombe | 26 | 31 | Goalkeeper |
| 61742 | H. Valdimarsson | 24 | 12 | Goalkeeper |
| 389579 | J. Eyestone | 19 | 41 | Goalkeeper |
| 284797 | D. Ouattara | 23 | 19 | Midfielder |
| 153066 | Fábio Carvalho | 23 | 14 | Midfielder |
| 292 | J. Henderson | 35 | 6 | Midfielder |
| 178077 | K. Schade | 24 | 7 | Midfielder |
| 513316 | Luka Bentt | 18 | 48 | Midfielder |
| 15908 | M. Damsgaard | 25 | 24 | Midfielder |
| 47438 | M. Jensen | 29 | 8 | Midfielder |
| 402317 | R. Donovan | 19 | 45 | Midfielder |
| 327726 | R. Owen | 20 | 52 | Midfielder |
| 25073 | V. Janelt | 27 | 27 | Midfielder |
| 263538 | Y. Yarmolyuk | 21 | 18 | Midfielder |


### Brighton (`team_id=51`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `29`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 392482 | C. Kostoulas | 18 | 19 | Attacker |
| 1469 | D. Welbeck | 35 | 18 | Attacker |
| 90590 | G. Rutter | 23 | 10 | Attacker |
| 553958 | N. Oriola | 18 | 11 | Attacker |
| 18973 | S. March | 31 | 7 | Attacker |
| 343311 | S. Tzimas | 19 | 9 | Attacker |
| 328076 | C. Tasker | 19 | 2 | Defender |
| 1361 | F. Kadıoğlu | 26 | 24 | Defender |
| 412086 | F. Simmonds | 17 | 4 | Defender |
| 7600 | Igor | 27 | 3 | Defender |
| 537 | J. Veltman | 33 | 34 | Defender |
| 38695 | J. van Hecke | 25 | 6 | Defender |
| 18963 | L. Dunk | 34 | 5 | Defender |
| 162007 | M. De Cuyper | 25 | 29 | Defender |
| 92993 | M. Wieffer | 26 | 27 | Defender |
| 22160 | O. Boscagli | 28 | 21 | Defender |
| 129058 | B. Verbruggen | 23 | 1 | Goalkeeper |
| 18960 | J. Steele | 35 | 23 | Goalkeeper |
| 449076 | Nils Ramming | 18 | 1 | Goalkeeper |
| 356041 | C. Baleba | 21 | 17 | Midfielder |
| 278370 | D. Gómez | 22 | 25 | Midfielder |
| 392610 | H. Howell | 17 | 10 | Midfielder |
| 305730 | J. Hinshelwood | 20 | 13 | Midfielder |
| 296 | J. Milner | 39 | 20 | Midfielder |
| 106835 | K. Mitoma | 28 | 22 | Midfielder |
| 19030 | M. O&apos;Riley | 25 | 33 | Midfielder |
| 18970 | P. Groß | 34 | 30 | Midfielder |
| 265820 | Y. Ayari | 22 | 26 | Midfielder |
| 383685 | Y. Minteh | 21 | 11 | Midfielder |


### Burnley (`team_id=44`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 18927 | A. Barnes | 36 | 35 | Attacker |
| 138822 | A. Broja | 24 | 27 | Attacker |
| 98936 | L. Foster | 25 | 9 | Attacker |
| 37882 | M. Edwards | 27 | 10 | Attacker |
| 37381 | M. Trésor | 26 | 31 | Attacker |
| 36927 | Z. Flemming | 27 | 19 | Attacker |
| 19182 | A. Tuanzebe | 28 | 6 | Defender |
| 181797 | B. Humphreys | 22 | 12 | Defender |
| 47903 | H. Ekdal | 27 | 18 | Defender |
| 1746 | J. Worrall | 29 | 4 | Defender |
| 627 | K. Walker | 35 | 2 | Defender |
| 330238 | Lucas Pires | 24 | 23 | Defender |
| 179400 | M. Estève | 23 | 5 | Defender |
| 375915 | Q. Hartman | 24 | 3 | Defender |
| 18886 | M. Dúbravka | 36 | 1 | Goalkeeper |
| 328273 | M. Weiß | 21 | 13 | Goalkeeper |
| 44994 | V. Hladký | 35 | 32 | Goalkeeper |
| 361388 | E. Agyei | 20 | 7 | Midfielder |
| 575 | Florentino | 26 | 16 | Midfielder |
| 503414 | G. Brierley | 18 | 6 | Midfielder |
| 180560 | H. Mejbri | 22 | 28 | Midfielder |
| 196855 | J. Anthony | 26 | 11 | Midfielder |
| 22 | J. Bruun Larsen | 27 | 7 | Midfielder |
| 19827 | J. Cullen | 29 | 24 | Midfielder |
| 20303 | J. Laurent | 30 | 29 | Midfielder |
| 2938 | J. Ward-Prowse | 31 | 20 | Midfielder |
| 557387 | K. M. Brown | 17 |  | Midfielder |
| 161621 | L. Tchaouna | 22 | 17 | Midfielder |
| 270508 | L. Ugochukwu | 21 | 8 | Midfielder |
| 456637 | O. Pimlott | 18 | 3 | Midfielder |


### Chelsea (`team_id=49`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 425733 | Estêvão | 18 | 41 | Attacker |
| 286894 | J. Bynoe-Gittens | 21 | 11 | Attacker |
| 417653 | J. Derry | 18 | 55 | Attacker |
| 10329 | João Pedro | 24 | 20 | Attacker |
| 161948 | L. Delap | 22 | 9 | Attacker |
| 392270 | Marc Guiu | 19 | 38 | Attacker |
| 359117 | Shumaira Mheuka | 18 | 9 | Attacker |
| 95 | B. Badiashile | 24 | 5 | Defender |
| 341642 | J. Hato | 19 | 21 | Defender |
| 366735 | Joshua Kofi Acheampong | 19 | 34 | Defender |
| 161907 | M. Gusto | 22 | 27 | Defender |
| 276184 | M. Sarr | 20 | 19 | Defender |
| 47380 | Marc Cucurella | 27 | 3 | Defender |
| 19545 | R. James | 26 | 24 | Defender |
| 19145 | T. Adarabioyo | 28 | 4 | Defender |
| 19720 | T. Chalobah | 26 | 23 | Defender |
| 22094 | W. Fofana | 25 | 29 | Defender |
| 286616 | F. Jörgensen | 23 | 12 | Goalkeeper |
| 64167 | G. Słonina | 21 | 44 | Goalkeeper |
| 287868 | Max Merrick | 20 | 1 | Goalkeeper |
| 18959 | Robert Sánchez | 28 | 1 | Goalkeeper |
| 180940 | T. Sharman-Lowe | 22 | 28 | Goalkeeper |
| 284324 | A. Garnacho | 21 | 49 | Midfielder |
| 305834 | Andrey Santos | 21 | 17 | Midfielder |
| 610563 | C. Holland | 16 | 75 | Midfielder |
| 152982 | C. Palmer | 23 | 10 | Midfielder |
| 308678 | Dário Essugo | 20 | 14 | Midfielder |
| 5996 | E. Fernández | 24 | 8 | Midfielder |
| 116117 | M. Caicedo | 24 | 25 | Midfielder |
| 1864 | Pedro Neto | 25 | 7 | Midfielder |
| 557379 | R. Kavuma McQueen | 16 | 11 | Midfielder |
| 282125 | R. Lavia | 21 | 45 | Midfielder |
| 482888 | R. Walsh | 17 | 10 | Midfielder |


### Crystal Palace (`team_id=52`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 557475 | B. Casey | 17 | 18 | Attacker |
| 129711 | B. Johnson | 24 | 11 | Attacker |
| 137303 | E. Guessand | 24 | 29 | Attacker |
| 1468 | E. Nketiah | 26 | 9 | Attacker |
| 2218 | I. Sarr | 27 | 7 | Attacker |
| 25927 | J. Mateta | 28 | 14 | Attacker |
| 2032 | J. Strand Larsen | 25 | 22 | Attacker |
| 557416 | Z. Marsh | 20 | 9 | Attacker |
| 26303 | B. Sosa | 27 | 24 | Defender |
| 278898 | C. Riad | 22 | 34 | Defender |
| 126949 | C. Richards | 25 | 26 | Defender |
| 557414 | D. Benamar | 17 | 3 | Defender |
| 557584 | G. King | 18 | 2 | Defender |
| 412759 | J. Canvot | 19 | 23 | Defender |
| 20995 | M. Lacroix | 25 | 5 | Defender |
| 18862 | N. Clyne | 34 | 17 | Defender |
| 380703 | Rio Cardines | 19 | 7 | Defender |
| 19088 | D. Henderson | 28 | 1 | Goalkeeper |
| 19684 | R. Matthews | 31 | 31 | Goalkeeper |
| 22157 | W. Benítez | 32 | 44 | Goalkeeper |
| 288102 | A. Wharton | 21 | 20 | Midfielder |
| 403554 | Christantus Uche | 22 | 12 | Midfielder |
| 2601 | D. Kamada | 29 | 18 | Midfielder |
| 13736 | D. Muñoz | 29 | 2 | Midfielder |
| 286458 | J. Devenny | 22 | 55 | Midfielder |
| 557413 | J. Drakes-Thomas | 16 | 20 | Midfielder |
| 2490 | J. Lerma | 31 | 8 | Midfielder |
| 301295 | K. Rodney | 21 | 8 | Midfielder |
| 182201 | T. Mitchell | 26 | 3 | Midfielder |
| 18806 | W. Hughes | 30 | 19 | Midfielder |
| 184226 | Yeremy Pino | 23 | 10 | Midfielder |


### Everton (`team_id=45`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `29`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 413034 | B. Graham | 18 | 11 | Attacker |
| 125743 | Beto | 27 | 9 | Attacker |
| 343684 | T. Barry | 23 | 11 | Attacker |
| 334037 | Tyrique George | 19 | 19 | Attacker |
| 431921 | Adam Aznou Ben Cheikh | 19 | 39 | Defender |
| 17661 | J. Branthwaite | 23 | 32 | Defender |
| 270139 | J. O&apos;Brien | 24 | 15 | Defender |
| 2936 | J. Tarkowski | 33 | 6 | Defender |
| 2934 | M. Keane | 32 | 5 | Defender |
| 138417 | N. Patterson | 24 | 2 | Defender |
| 284327 | R. Welch | 22 | 4 | Defender |
| 18758 | S. Coleman | 37 | 23 | Defender |
| 2165 | V. Mykolenko | 26 | 16 | Defender |
| 2932 | J. Pickford | 31 | 1 | Goalkeeper |
| 18860 | M. Travers | 26 | 12 | Goalkeeper |
| 82855 | T. King | 30 | 31 | Goalkeeper |
| 195993 | C. Alcaraz | 23 | 24 | Midfielder |
| 546654 | C. Bates | 20 | 10 | Midfielder |
| 18929 | D. McNeil | 26 | 7 | Midfielder |
| 405360 | H. Armstrong | 18 | 45 | Midfielder |
| 2990 | I. Gueye | 36 | 27 | Midfielder |
| 18592 | I. Ndiaye | 25 | 10 | Midfielder |
| 895 | J. Garner | 24 | 37 | Midfielder |
| 19187 | J. Grealish | 30 | 18 | Midfielder |
| 148099 | K. Dewsbury-Hall | 27 | 22 | Midfielder |
| 202854 | M. Röhl | 23 | 34 | Midfielder |
| 588468 | Malik Olayiwola | 16 | 14 | Midfielder |
| 304317 | T. Dibling | 19 | 20 | Midfielder |
| 284500 | T. Iroegbunam | 22 | 42 | Midfielder |


### Fulham (`team_id=36`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `27`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 436443 | J. Kusi-Asare | 18 | 18 | Attacker |
| 237819 | Kevin | 22 | 22 | Attacker |
| 2887 | R. Jiménez | 34 | 7 | Attacker |
| 195106 | Rodrigo Muniz | 24 | 9 | Attacker |
| 19549 | A. Robinson | 28 | 33 | Defender |
| 152967 | C. Bassey | 26 | 3 | Defender |
| 18814 | I. Diop | 28 | 31 | Defender |
| 2729 | J. Andersen | 29 | 5 | Defender |
| 131 | Jorge Cuenca | 26 | 15 | Defender |
| 657 | K. Tete | 30 | 2 | Defender |
| 19032 | R. Sessegnon | 25 | 30 | Defender |
| 384981 | S. Amissah | 18 | 4 | Defender |
| 2920 | T. Castagne | 30 | 21 | Defender |
| 288129 | Alfie Shane McNally | 21 | 1 | Goalkeeper |
| 21566 | B. Lecomte | 34 | 23 | Goalkeeper |
| 1438 | B. Leno | 33 | 1 | Goalkeeper |
| 1455 | A. Iwobi | 29 | 17 | Midfielder |
| 1161 | E. Smith Rowe | 25 | 32 | Midfielder |
| 19480 | H. Reed | 30 | 6 | Midfielder |
| 19221 | H. Wilson | 28 | 8 | Midfielder |
| 389315 | Joshua King | 18 | 24 | Midfielder |
| 278133 | Oscar Bobb | 22 | 14 | Midfielder |
| 1934 | S. Berge | 27 | 16 | Midfielder |
| 1696 | S. Chukwueze | 26 | 19 | Midfielder |
| 2823 | S. Lukić | 29 | 20 | Midfielder |
| 557335 | S. Ridgeon | 17 | 10 | Midfielder |
| 19025 | T. Cairney | 34 | 10 | Midfielder |


### Leeds (`team_id=63`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `25`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 50739 | B. Aaronson | 25 | 11 | Attacker |
| 18766 | D. Calvert-Lewin | 28 | 9 | Attacker |
| 250 | J. Piroe | 26 | 10 | Attacker |
| 19461 | L. Nmecha | 27 | 14 | Attacker |
| 48389 | N. Okafor | 25 | 19 | Attacker |
| 162128 | W. Gnonto | 22 | 29 | Attacker |
| 833 | J. Bijol | 26 | 15 | Defender |
| 19760 | J. Justin | 27 | 24 | Defender |
| 19321 | J. Rodon | 28 | 6 | Defender |
| 64003 | P. Struijk | 26 | 5 | Defender |
| 1408 | S. Bornauw | 26 | 23 | Defender |
| 19287 | S. Byram | 32 | 25 | Defender |
| 20619 | I. Meslier | 25 | 1 | Goalkeeper |
| 18885 | K. Darlow | 35 | 26 | Goalkeeper |
| 80296 | Lucas Perri | 28 | 1 | Goalkeeper |
| 177665 | A. Stach | 27 | 18 | Midfielder |
| 32966 | A. Tanaka | 27 | 22 | Midfielder |
| 19329 | D. James | 28 | 7 | Midfielder |
| 2279 | E. Ampadu | 25 | 4 | Midfielder |
| 311334 | F. Buonanotte | 21 | 40 | Midfielder |
| 47969 | G. Gudmundsson | 26 | 3 | Midfielder |
| 129142 | I. Gruev | 25 | 44 | Midfielder |
| 19201 | J. Bogle | 25 | 2 | Midfielder |
| 351344 | S. Chambers | 18 | 7 | Midfielder |
| 18901 | S. Longstaff | 28 | 8 | Midfielder |


### Liverpool (`team_id=40`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 2864 | A. Isak | 26 | 9 | Attacker |
| 30410 | F. Chiesa | 28 | 14 | Attacker |
| 174565 | H. Ekitike | 23 | 22 | Attacker |
| 344223 | K. Figueroa | 19 | 14 | Attacker |
| 286764 | Kaide Gordon | 21 | 49 | Attacker |
| 452685 | R. Ngumoha | 17 | 73 | Attacker |
| 498377 | W. Wright | 17 | 79 | Attacker |
| 289 | A. Robertson | 31 | 26 | Defender |
| 180317 | C. Bradley | 22 | 12 | Defender |
| 293 | C. Jones | 24 | 17 | Defender |
| 380666 | C. Pinnington | 18 | 3 | Defender |
| 135525 | C. Ramsay | 22 | 2 | Defender |
| 1145 | I. Konaté | 26 | 5 | Defender |
| 152654 | J. Frimpong | 25 | 30 | Defender |
| 284 | J. Gomez | 28 | 2 | Defender |
| 206254 | M. Kerkez | 22 | 6 | Defender |
| 290 | V. van Dijk | 34 | 4 | Defender |
| 328081 | W. Omoruyi | 19 | 3 | Defender |
| 280 | Alisson Becker | 33 | 1 | Goalkeeper |
| 18889 | F. Woodman | 28 | 28 | Goalkeeper |
| 24760 | G. Mamardashvili | 25 | 25 | Goalkeeper |
| 415992 | K. Miściur | 18 | 13 | Goalkeeper |
| 342467 | Á. Pécsi | 20 | 1 | Goalkeeper |
| 6716 | A. Mac Allister | 27 | 10 | Midfielder |
| 407032 | A. Nallo | 19 | 3 | Midfielder |
| 247 | C. Gakpo | 26 | 18 | Midfielder |
| 1096 | D. Szoboszlai | 25 | 8 | Midfielder |
| 203224 | F. Wirtz | 22 | 7 | Midfielder |
| 389032 | K. Morrison | 19 | 7 | Midfielder |
| 339205 | M. Laffey | 20 | 16 | Midfielder |
| 306 | Mohamed Salah | 33 | 11 | Midfielder |
| 542 | R. Gravenberch | 23 | 38 | Midfielder |
| 397997 | T. Nyoni | 18 | 42 | Midfielder |
| 301286 | Tommy Pilling | 21 | 15 | Midfielder |
| 8500 | W. Endo | 32 | 3 | Midfielder |


### Manchester City (`team_id=50`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 1100 | E. Haaland | 25 | 9 | Attacker |
| 1422 | J. Doku | 23 | 11 | Attacker |
| 81573 | Omar Marmoush | 26 | 7 | Attacker |
| 448969 | Reigan Heskey | 17 | 11 | Attacker |
| 266657 | Sávio | 21 | 26 | Attacker |
| 360114 | A. Khusanov | 21 | 45 | Defender |
| 129033 | J. Gvardiol | 23 | 24 | Defender |
| 626 | J. Stones | 31 | 5 | Defender |
| 67971 | M. Guéhi | 25 | 15 | Defender |
| 41621 | Matheus Nunes | 27 | 27 | Defender |
| 293168 | Max Alleyne | 20 | 4 | Defender |
| 18861 | N. Aké | 30 | 6 | Defender |
| 21138 | R. Aït-Nouri | 24 | 21 | Defender |
| 284230 | R. Lewis | 21 | 82 | Defender |
| 567 | Rúben Dias | 28 | 3 | Defender |
| 1622 | G. Donnarumma | 26 | 25 | Goalkeeper |
| 162489 | J. Trafford | 23 | 1 | Goalkeeper |
| 19012 | M. Bettinelli | 33 | 13 | Goalkeeper |
| 19281 | A. Semenyo | 25 | 42 | Midfielder |
| 636 | Bernardo Silva | 31 | 20 | Midfielder |
| 389034 | Charlie Gray | 19 | 6 | Midfielder |
| 2291 | M. Kovačić | 31 | 8 | Midfielder |
| 307123 | N. O&apos;Reilly | 20 | 33 | Midfielder |
| 161933 | Nico González | 23 | 14 | Midfielder |
| 631 | P. Foden | 25 | 47 | Midfielder |
| 156477 | R. Cherki | 22 | 10 | Midfielder |
| 442048 | R. McAidoo | 17 | 7 | Midfielder |
| 44 | Rodri | 29 | 16 | Midfielder |
| 323591 | S. Nypan | 19 | 10 | Midfielder |
| 36902 | T. Reijnders | 27 | 4 | Midfielder |
| 568413 | T. Samba | 17 | 16 | Midfielder |


### Manchester United (`team_id=33`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 115589 | B. Šeško | 22 | 30 | Attacker |
| 404769 | Bendito Mantato | 17 | 15 | Attacker |
| 70100 | J. Zirkzee | 24 | 11 | Attacker |
| 1165 | Matheus Cunha | 26 | 10 | Attacker |
| 389309 | O. Martin | 18 | 9 | Attacker |
| 557462 | S. Lacey | 18 | 61 | Attacker |
| 402329 | A. Heaven | 19 | 26 | Defender |
| 886 | Diogo Dalot | 26 | 2 | Defender |
| 440159 | G. Kukonki | 17 | 5 | Defender |
| 2935 | H. Maguire | 32 | 5 | Defender |
| 891 | L. Shaw | 30 | 23 | Defender |
| 342970 | L. Yoro | 20 | 15 | Defender |
| 2467 | Lisandro Martínez | 27 | 6 | Defender |
| 532 | M. de Ligt | 26 | 4 | Defender |
| 545 | N. Mazraoui | 28 | 3 | Defender |
| 382452 | P. Dorgu | 21 | 13 | Defender |
| 328101 | T. Fredricson | 20 | 4 | Defender |
| 37145 | T. Malacia | 26 | 12 | Defender |
| 50132 | A. Bayındır | 27 | 1 | Goalkeeper |
| 162511 | S. Lammens | 23 | 31 | Goalkeeper |
| 2931 | T. Heaton | 39 | 22 | Goalkeeper |
| 157997 | A. Diallo | 23 | 16 | Midfielder |
| 20589 | B. Mbeumo | 26 | 19 | Midfielder |
| 1485 | Bruno Fernandes | 31 | 8 | Midfielder |
| 747 | Casemiro | 33 | 18 | Midfielder |
| 383770 | J. Fletcher | 18 | 10 | Midfielder |
| 344229 | J. Moorhouse | 20 | 8 | Midfielder |
| 284322 | K. Mainoo | 20 | 37 | Midfielder |
| 19220 | M. Mount | 26 | 7 | Midfielder |
| 51494 | M. Ugarte | 24 | 25 | Midfielder |
| 557460 | T. Fletcher | 18 | 6 | Midfielder |


### Newcastle (`team_id=34`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 153430 | A. Elanga | 23 | 20 | Attacker |
| 138787 | A. Gordon | 24 | 10 | Attacker |
| 158054 | N. Woltemade | 23 | 27 | Attacker |
| 394165 | S. Neave | 18 | 62 | Attacker |
| 315237 | W. Osula | 22 | 18 | Attacker |
| 20649 | Y. Wissa | 29 | 9 | Attacker |
| 318056 | A. Murphy | 21 | 37 | Defender |
| 18961 | D. Burn | 33 | 33 | Defender |
| 2855 | E. Krafth | 31 | 17 | Defender |
| 2806 | F. Schär | 34 | 5 | Defender |
| 169 | K. Trippier | 35 | 2 | Defender |
| 284492 | L. Hall | 21 | 3 | Defender |
| 328105 | L. Miley | 19 | 67 | Defender |
| 337934 | L. Shahar | 18 | 61 | Defender |
| 163189 | M. Thiaw | 24 | 12 | Defender |
| 38734 | S. Botman | 25 | 4 | Defender |
| 158694 | T. Livramento | 23 | 21 | Defender |
| 557523 | A. Harrison | 19 | 13 | Goalkeeper |
| 20355 | A. Ramsdale | 27 | 32 | Goalkeeper |
| 365988 | Aidan Harris | 19 | 1 | Goalkeeper |
| 18737 | J. Ruddy | 39 | 26 | Goalkeeper |
| 18911 | N. Pope | 33 | 1 | Goalkeeper |
| 10135 | Bruno Guimarães | 28 | 39 | Midfielder |
| 18778 | H. Barnes | 28 | 11 | Midfielder |
| 19163 | J. Murphy | 30 | 23 | Midfielder |
| 19192 | J. Ramsey | 24 | 41 | Midfielder |
| 1463 | J. Willock | 26 | 28 | Midfielder |
| 723 | Joelinton | 29 | 7 | Midfielder |
| 423714 | Park Seung-Soo | 18 | 11 | Midfielder |
| 567998 | S. Alabi | 16 | 85 | Midfielder |
| 31146 | S. Tonali | 25 | 8 | Midfielder |


### Nottingham Forest (`team_id=65`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 18931 | C. Wood | 34 | 11 | Attacker |
| 129695 | D. Bakwa | 23 | 29 | Attacker |
| 48648 | D. Ndoye | 25 | 14 | Attacker |
| 9366 | Igor Jesus | 24 | 19 | Attacker |
| 199089 | L. Lucca | 25 | 20 | Attacker |
| 8598 | T. Awoniyi | 28 | 9 | Attacker |
| 380663 | J. Sinclair | 19 | 61 | Defender |
| 362711 | Jair | 20 | 23 | Defender |
| 163069 | L. Netz | 22 | 25 | Defender |
| 67943 | Morato | 24 | 4 | Defender |
| 363695 | Murillo | 23 | 5 | Defender |
| 2817 | N. Milenković | 28 | 31 | Defender |
| 181806 | N. Savona | 22 | 37 | Defender |
| 138780 | N. Williams | 24 | 3 | Defender |
| 2771 | O. Aina | 29 | 34 | Defender |
| 18739 | W. Boly | 34 | 30 | Defender |
| 329357 | Z. Abbott | 19 | 44 | Defender |
| 18933 | A. Gunn | 29 | 18 | Goalkeeper |
| 329358 | Aaron Bott | 21 | 63 | Goalkeeper |
| 70366 | John | 29 | 13 | Goalkeeper |
| 357238 | Keehan Willows | 20 | 67 | Goalkeeper |
| 2919 | M. Sels | 33 | 26 | Goalkeeper |
| 25004 | S. Ortega | 33 | 27 | Goalkeeper |
| 353968 | A. Whitehall | 19 | 51 | Midfielder |
| 2298 | C. Hudson-Odoi | 25 | 7 | Midfielder |
| 138908 | E. Anderson | 23 | 8 | Midfielder |
| 22149 | I. Sangaré | 28 | 6 | Midfielder |
| 158697 | J. McAtee | 23 | 24 | Midfielder |
| 18746 | M. Gibbs-White | 25 | 10 | Midfielder |
| 6056 | N. Domínguez | 27 | 16 | Midfielder |
| 284428 | O. Hutchinson | 22 | 21 | Midfielder |
| 19305 | R. Yates | 28 | 22 | Midfielder |


### Sunderland (`team_id=746`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 388461 | A. Abdullahi | 21 | 9 | Attacker |
| 38750 | B. Brobbey | 23 | 9 | Attacker |
| 671 | B. Traoré | 30 | 25 | Attacker |
| 336659 | C. Talbi | 20 | 7 | Attacker |
| 349799 | Eliezer Mayenda | 20 | 12 | Attacker |
| 428076 | M. AleksiÄ | 20 | 11 | Attacker |
| 311543 | N. Angulo | 22 | 10 | Attacker |
| 284414 | R. Mundle | 22 | 14 | Attacker |
| 84087 | W. Isidor | 25 | 18 | Attacker |
| 55904 | D. Ballard | 26 | 5 | Defender |
| 162076 | D. Cirkin | 23 | 3 | Defender |
| 557488 | J. Jones | 19 | 3 | Defender |
| 37143 | L. Geertruida | 25 | 6 | Defender |
| 1146 | N. Mukiele | 28 | 20 | Defender |
| 6168 | O. Alderete | 29 | 15 | Defender |
| 22225 | Reinildo | 31 | 17 | Defender |
| 119121 | T. Hume | 23 | 32 | Defender |
| 278454 | M. Ellborg | 22 | 31 | Goalkeeper |
| 194536 | R. Roefs | 22 | 22 | Goalkeeper |
| 19089 | S. Moore | 35 | 21 | Goalkeeper |
| 339201 | C. Rigg | 18 | 11 | Midfielder |
| 20638 | E. Le Fée | 25 | 28 | Midfielder |
| 1464 | G. Xhaka | 33 | 34 | Midfielder |
| 327631 | H. Diarra | 21 | 19 | Midfielder |
| 330640 | Harrison Jones | 21 | 50 | Midfielder |
| 554280 | J. T. Bi | 20 | 37 | Midfielder |
| 362766 | J. Whittaker | 19 | 8 | Midfielder |
| 381014 | Jenson Jones | 19 | 4 | Midfielder |
| 19911 | L. O&apos;Nien | 31 | 13 | Midfielder |
| 365331 | N. Sadiki | 21 | 27 | Midfielder |


### Tottenham (`team_id=47`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `37`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 18883 | D. Solanke | 28 | 19 | Attacker |
| 418942 | J. Wilson | 18 | 7 | Attacker |
| 465310 | L. Williams-Barnett | 17 | 68 | Attacker |
| 270510 | M. Tel | 20 | 11 | Attacker |
| 2413 | Richarlison | 28 | 9 | Attacker |
| 557391 | T. Thompson | 17 | 11 | Attacker |
| 336564 | W. Odobert | 21 | 28 | Attacker |
| 164 | B. Davies | 32 | 33 | Defender |
| 30776 | C. Romero | 27 | 17 | Defender |
| 19235 | D. Spence | 25 | 24 | Defender |
| 204039 | D. Udogie | 23 | 13 | Defender |
| 467839 | J. Byfield | 17 | 67 | Defender |
| 361735 | James Rowswell | 19 | 2 | Defender |
| 25287 | K. Danso | 27 | 4 | Defender |
| 459203 | M. Hardy | 17 | 3 | Defender |
| 152849 | M. van de Ven | 24 | 37 | Defender |
| 47519 | Pedro Porro | 26 | 23 | Defender |
| 162498 | R. Drăgușin | 23 | 3 | Defender |
| 414455 | Souza | 19 | 38 | Defender |
| 265826 | A. Kinský | 22 | 31 | Goalkeeper |
| 156428 | B. Austin | 26 | 40 | Goalkeeper |
| 31354 | G. Vicario | 29 | 1 | Goalkeeper |
| 344247 | Luca Gunter | 20 | 1 | Goalkeeper |
| 328089 | A. Gray | 19 | 14 | Midfielder |
| 67972 | C. Gallagher | 25 | 22 | Midfielder |
| 380689 | C. Olusesi | 18 | 8 | Midfielder |
| 18784 | J. Maddison | 29 | 10 | Midfielder |
| 41104 | João Palhinha | 30 | 6 | Midfielder |
| 347316 | L. Bergvall | 19 | 15 | Midfielder |
| 15911 | M. Kudus | 25 | 20 | Midfielder |
| 237129 | P. Sarr | 23 | 29 | Midfielder |
| 863 | R. Bentancur | 28 | 30 | Midfielder |
| 21104 | R. Kolo Muani | 27 | 39 | Midfielder |
| 310531 | Rio Kyerematen | 20 | 8 | Midfielder |
| 584077 | T. Hall | 18 | 6 | Midfielder |
| 162016 | X. Simons | 22 | 7 | Midfielder |
| 18968 | Y. Bissouma | 29 | 8 | Midfielder |


### West Ham (`team_id=48`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `27`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 18753 | Adama Traoré | 29 | 17 | Attacker |
| 2939 | C. Wilson | 33 | 9 | Attacker |
| 432404 | J. Ajala | 19 | 10 | Attacker |
| 301187 | Pablo | 21 | 19 | Attacker |
| 50856 | V. Castellanos | 27 | 11 | Attacker |
| 21998 | A. Disasi | 27 | 4 | Defender |
| 557541 | A. Golambeckis | 17 | 4 | Defender |
| 18846 | A. Wan-Bissaka | 28 | 29 | Defender |
| 409303 | E. Diouf | 21 | 12 | Defender |
| 553065 | E. Mayers | 18 | 6 | Defender |
| 138 | J. Todibo | 26 | 25 | Defender |
| 1445 | K. Mavropanos | 28 | 15 | Defender |
| 171 | K. Walker-Peters | 28 | 2 | Defender |
| 18744 | M. Kilman | 28 | 3 | Defender |
| 327730 | O. Scarles | 20 | 30 | Defender |
| 253 | A. Areola | 32 | 23 | Goalkeeper |
| 337932 | F. Herrick | 19 | 49 | Goalkeeper |
| 15870 | M. Hermansen | 25 | 1 | Goalkeeper |
| 37724 | C. Summerville | 24 | 7 | Midfielder |
| 284446 | F. Potts | 22 | 32 | Midfielder |
| 19428 | J. Bowen | 29 | 20 | Midfielder |
| 358969 | K. Lamadrid | 22 | 21 | Midfielder |
| 288118 | L. Orford | 19 | 8 | Midfielder |
| 401278 | M. Kanté | 20 | 55 | Midfielder |
| 336585 | Mateus Fernandes | 21 | 18 | Midfielder |
| 326176 | S. Magassa | 22 | 27 | Midfielder |
| 1243 | T. Souček | 30 | 28 | Midfielder |


### Wolves (`team_id=39`)

- Competition: `Premier League`
- League ID: `39`
- Season: `2025`
- Country: `England`
- National team: `False`
- Players: `26`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 19484 | A. Armstrong | 28 | 9 | Attacker |
| 385726 | E. González | 20 | 7 | Attacker |
| 379678 | Ethan Sutherland | 19 | 3 | Attacker |
| 24888 | Hwang Hee-Chan | 29 | 11 | Attacker |
| 456206 | M. Mane | 18 | 36 | Attacker |
| 282770 | Rodrigo Gomes | 22 | 21 | Attacker |
| 110153 | T. Arokodare | 25 | 14 | Attacker |
| 265782 | D. Møller Wolfe | 23 | 6 | Defender |
| 296560 | J. Tchatchoua | 24 | 38 | Defender |
| 66407 | L. Krejčí | 26 | 37 | Defender |
| 18742 | M. Doherty | 33 | 2 | Defender |
| 135334 | S. Bueno | 27 | 4 | Defender |
| 397999 | S. Olagunju | 18 | 59 | Defender |
| 41606 | Toti Gomes | 26 | 24 | Defender |
| 19341 | D. Bentley | 32 | 25 | Goalkeeper |
| 1590 | José Sá | 32 | 1 | Goalkeeper |
| 19143 | S. Johnstone | 32 | 31 | Goalkeeper |
| 896 | A. Gomes | 25 | 47 | Midfielder |
| 265784 | André | 24 | 7 | Midfielder |
| 280687 | Hugo Bueno | 23 | 3 | Midfielder |
| 20665 | J. Bellegarde | 27 | 27 | Midfielder |
| 195103 | João Gomes | 24 | 8 | Midfielder |
| 401098 | L. Rawlings | 17 | 8 | Midfielder |
| 449245 | Pedro Lima | 19 | 17 | Midfielder |
| 546745 | T. Edozie | 19 | 74 | Midfielder |
| 195717 | Y. Mosquera | 24 | 15 | Midfielder |



## La Liga

### Alaves (`team_id=542`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 623902 | A. Manas | 22 | 34 | Attacker |
| 565586 | D. Morcillo | 22 | 29 | Attacker |
| 182784 | I. Diabate | 26 | 22 | Attacker |
| 608 | L. Boyé | 29 | 15 | Attacker |
| 760 | M. Díaz | 32 | 9 | Attacker |
| 47181 | Toni Martínez | 28 | 11 | Attacker |
| 183751 | A. Rebbach | 27 | 21 | Defender |
| 331369 | Angel Pérez | 23 | 7 | Defender |
| 387530 | Carlos Ballestero García | 21 | 30 | Defender |
| 601858 | E. Munoz | 21 | 27 | Defender |
| 6638 | F. Garcés | 26 | 2 | Defender |
| 182546 | Jon Pacheco | 24 | 5 | Defender |
| 18740 | Jonny | 31 | 17 | Defender |
| 6233 | N. Tenaglia | 29 | 14 | Defender |
| 646886 | P. Sanz | 21 | 36 | Defender |
| 106759 | V. Koski | 23 | 16 | Defender |
| 128951 | Víctor Parada | 23 | 24 | Defender |
| 361384 | Yusi | 20 | 3 | Defender |
| 442058 | Álvaro García | 20 | 26 | Defender |
| 377215 | G. Swiderski | 20 | 31 | Goalkeeper |
| 551461 | R. Montero | 20 | 33 | Goalkeeper |
| 46987 | Raúl Fernández | 37 | 13 | Goalkeeper |
| 47353 | Sivera | 29 | 1 | Goalkeeper |
| 162686 | Antonio Blanco | 25 | 8 | Midfielder |
| 6085 | C. Benavídez | 27 | 23 | Midfielder |
| 266658 | Calebe | 25 | 20 | Midfielder |
| 143 | Carles Aleñá | 27 | 10 | Midfielder |
| 1461 | Denis Suárez | 31 | 4 | Midfielder |
| 47309 | Guevara | 28 | 6 | Midfielder |
| 104821 | Jon Guridi | 30 | 18 | Midfielder |
| 315586 | Lander Pinillos | 22 | 28 | Midfielder |
| 139001 | Pablo Ibáñez | 27 | 19 | Midfielder |


### Athletic Club (`team_id=531`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `39`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 560954 | A. Hierro | 20 | 7 | Attacker |
| 377257 | Endika Bujan | 22 | 11 | Attacker |
| 47291 | Gorka Guruzeta | 29 | 11 | Attacker |
| 287680 | Maroan Sannadi | 24 | 21 | Attacker |
| 286593 | Nico Serrano | 22 | 22 | Attacker |
| 183776 | Urko Izeta | 26 | 25 | Attacker |
| 30510 | Álex Berenguer | 30 | 7 | Attacker |
| 336998 | A. Boiro | 23 | 19 | Defender |
| 561097 | A. Izagirre Cestona | 22 | 14 | Defender |
| 384262 | Aimar Duñabeitia | 22 | 4 | Defender |
| 183849 | Aitor Paredes | 25 | 4 | Defender |
| 622 | Aymeric Laporte | 31 | 14 | Defender |
| 47278 | Dani Vivian | 26 | 3 | Defender |
| 47299 | Gorosabel | 29 | 2 | Defender |
| 407677 | Iker Monreal | 20 | 5 | Defender |
| 182181 | Jesús Areso | 26 | 12 | Defender |
| 335490 | Jon de Luis | 22 | 3 | Defender |
| 47276 | Lekue | 32 | 15 | Defender |
| 332305 | Unai Eguíluz | 23 | 13 | Defender |
| 47271 | Yeray | 30 | 5 | Defender |
| 47273 | Yuri | 35 | 17 | Defender |
| 437637 | Mikel Santos | 21 | 13 | Goalkeeper |
| 47270 | Unai Simón | 28 | 1 | Goalkeeper |
| 312468 | Álex Padilla | 22 | 27 | Goalkeeper |
| 543467 | Adrian Perez | 18 | 22 | Midfielder |
| 332309 | Alejandro Rego | 22 | 30 | Midfielder |
| 560978 | E. Garcia | 21 | 49 | Midfielder |
| 560981 | E. Gift | 19 | 23 | Midfielder |
| 432555 | Efe Korkut Martin | 19 | 20 | Midfielder |
| 47294 | I. Williams | 31 | 9 | Midfielder |
| 384267 | Ibon Sánchez | 21 | 10 | Midfielder |
| 383780 | Mikel Jauregizar | 22 | 18 | Midfielder |
| 47418 | Mikel Vesga | 32 | 6 | Midfielder |
| 183799 | Nico Williams | 23 | 10 | Midfielder |
| 128398 | Oihan Sancet | 25 | 8 | Midfielder |
| 84086 | Robert Navarro | 23 | 23 | Midfielder |
| 47007 | Ruíz de Galarreta | 32 | 16 | Midfielder |
| 568156 | S. Sanchez | 18 | 33 | Midfielder |
| 332308 | Unai Gómez | 22 | 20 | Midfielder |


### Atletico Madrid (`team_id=530`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `38`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 56 | A. Griezmann | 34 | 7 | Attacker |
| 8492 | A. Sørloth | 30 | 9 | Attacker |
| 548706 | I. Luque | 20 | 37 | Attacker |
| 6009 | J. Álvarez | 25 | 19 | Attacker |
| 26315 | N. González | 27 | 23 | Attacker |
| 443668 | Rayane Belid | 20 | 29 | Attacker |
| 491091 | Sergio Esteban | 17 | 9 | Attacker |
| 428799 | A. Puric | 22 | 40 | Defender |
| 133 | C. Lenglet | 30 | 15 | Defender |
| 30399 | D. Hancko | 28 | 17 | Defender |
| 386869 | Dani MartÃ­nez | 21 | 30 | Defender |
| 441280 | G. Spina | 20 | 12 | Defender |
| 31 | J. Giménez | 30 | 2 | Defender |
| 336685 | Javier Boñar | 20 | 32 | Defender |
| 162012 | M. Ruggeri | 23 | 3 | Defender |
| 295793 | Marc Pubill | 22 | 18 | Defender |
| 753 | Marcos Llorente | 30 | 14 | Defender |
| 6503 | N. Molina | 27 | 16 | Defender |
| 47301 | Robin Le Normand | 29 | 24 | Defender |
| 2465 | J. Musso | 31 | 1 | Goalkeeper |
| 29 | J. Oblak | 32 | 13 | Goalkeeper |
| 189997 | Mario de Luis | 23 | 1 | Goalkeeper |
| 393198 | Salvador Esquivel | 20 | 31 | Goalkeeper |
| 646997 | Álvaro Moreno | 19 | 51 | Goalkeeper |
| 18767 | A. Lookman | 28 | 22 | Midfielder |
| 451594 | Alejandro Monserrate | 19 | 17 | Midfielder |
| 323935 | G. Simeone | 23 | 20 | Midfielder |
| 133185 | J. Cardoso | 24 | 5 | Midfielder |
| 548704 | J. Morcillo | 19 | 47 | Midfielder |
| 303378 | Javi Serrano | 22 | 6 | Midfielder |
| 386870 | Julio Díaz del Romo | 20 | 34 | Midfielder |
| 50 | Koke | 33 | 6 | Midfielder |
| 313383 | O. Vargas | 20 | 21 | Midfielder |
| 336594 | Pablo Barrios | 22 | 8 | Midfielder |
| 341371 | Rodrigo Mendoza | 20 | 4 | Midfielder |
| 6067 | T. Almada | 24 | 11 | Midfielder |
| 548867 | T. Seidu | 17 | 27 | Midfielder |
| 182219 | Álex Baena | 24 | 10 | Midfielder |


### Barcelona (`team_id=529`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 931 | Ferran Torres | 25 | 7 | Attacker |
| 579244 | Juan Hernández | 18 | 41 | Attacker |
| 909 | M. Rashford | 28 | 14 | Attacker |
| 521 | R. Lewandowski | 37 | 9 | Attacker |
| 1496 | Raphinha | 29 | 11 | Attacker |
| 445973 | Toni Fernández | 17 | 29 | Attacker |
| 2282 | A. Christensen | 29 | 15 | Defender |
| 161928 | Alejandro Balde | 22 | 3 | Defender |
| 181701 | Gerard Martín | 23 | 18 | Defender |
| 1257 | J. Koundé | 27 | 23 | Defender |
| 457214 | J. Onstein | 18 | 54 | Defender |
| 491250 | Jofre Torrents | 18 | 26 | Defender |
| 855 | João Cancelo | 31 | 2 | Defender |
| 414433 | P. PacÃ­fico | 19 | 14 | Defender |
| 396623 | Pau Cubarsí Paredes | 18 | 5 | Defender |
| 101814 | R. Araújo | 26 | 4 | Defender |
| 568001 | X. Espart | 18 | 42 | Defender |
| 433395 | Álvaro Cortés Moyano | 20 | 36 | Defender |
| 383647 | D. Kochen | 19 | 31 | Goalkeeper |
| 543468 | Eder Aller | 18 | 33 | Goalkeeper |
| 182718 | Joan García | 24 | 13 | Goalkeeper |
| 851 | W. Szczęsny | 35 | 25 | Goalkeeper |
| 1323 | Dani Olmo | 27 | 20 | Midfielder |
| 619 | Eric García | 24 | 24 | Midfielder |
| 538 | F. de Jong | 28 | 21 | Midfielder |
| 340626 | Fermín | 22 | 16 | Midfielder |
| 296667 | Gavi | 21 | 6 | Midfielder |
| 386828 | Lamine Yamal | 18 | 10 | Midfielder |
| 433396 | Marc Bernal | 18 | 22 | Midfielder |
| 329728 | Marc Casadó | 22 | 17 | Midfielder |
| 133609 | Pedri | 23 | 8 | Midfielder |
| 338958 | R. Bardghji | 20 | 19 | Midfielder |
| 491086 | Tomás Marqués | 19 | 43 | Midfielder |


### Celta Vigo (`team_id=538`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 554287 | A. Arcos | 19 | 11 | Attacker |
| 47348 | Borja Iglesias | 32 | 7 | Attacker |
| 570 | F. Cervi | 31 | 11 | Attacker |
| 122734 | Ferran Jutglà | 26 | 9 | Attacker |
| 161875 | Hugo González | 22 | 30 | Attacker |
| 329720 | Hugo Álvarez | 22 | 23 | Attacker |
| 47445 | Iago Aspas | 38 | 10 | Attacker |
| 351913 | J. El Abdellaoui | 19 | 39 | Attacker |
| 320517 | Pablo Durán | 24 | 18 | Attacker |
| 47988 | C. Starfelt | 30 | 2 | Defender |
| 286559 | Carlos Domínguez | 24 | 24 | Defender |
| 1926 | J. Aidoo | 30 | 4 | Defender |
| 384135 | Javi Rodríguez | 22 | 32 | Defender |
| 179955 | Javi Rueda | 23 | 17 | Defender |
| 21584 | M. Ristić | 30 | 21 | Defender |
| 182638 | Manu Fernández | 24 | 12 | Defender |
| 2278 | Marcos Alonso | 35 | 20 | Defender |
| 561063 | P. Meixus | 22 | 6 | Defender |
| 329722 | Yoel Lago | 21 | 29 | Defender |
| 182661 | Álvaro Núñez | 25 | 14 | Defender |
| 30765 | I. Radu | 28 | 13 | Goalkeeper |
| 47427 | Iván Villar | 28 | 1 | Goalkeeper |
| 561066 | M. Gonzalez | 19 | 25 | Goalkeeper |
| 182730 | Marc Vidal | 25 | 25 | Goalkeeper |
| 481678 | Andrés Antañón | 18 | 36 | Midfielder |
| 391822 | Fer López | 21 | 8 | Midfielder |
| 560930 | H. Burcio | 18 | 5 | Midfielder |
| 313651 | Hugo Sotelo | 22 | 22 | Midfielder |
| 162123 | I. Moriba | 22 | 6 | Midfielder |
| 211 | M. Vecino | 34 | 15 | Midfielder |
| 333502 | Miguel Román | 23 | 17 | Midfielder |
| 554286 | O. Marcos | 19 | 19 | Midfielder |
| 157988 | Sergio Carreira | 25 | 5 | Midfielder |
| 269163 | W. Swedberg | 21 | 19 | Midfielder |
| 162712 | Óscar Mingueza | 26 | 3 | Midfielder |


### Elche (`team_id=797`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 439293 | Adam Boayar | 20 | 32 | Attacker |
| 2063 | André Silva | 30 | 9 | Attacker |
| 18821 | G. Diangana | 27 | 19 | Attacker |
| 161963 | Germán Valera | 23 | 11 | Attacker |
| 318592 | L. Cepeda | 23 | 24 | Attacker |
| 307224 | Piri | 22 | 29 | Attacker |
| 47013 | Rafa Mir | 28 | 10 | Attacker |
| 47182 | Tete Morente | 29 | 15 | Attacker |
| 284415 | Yago Alonso | 22 | 7 | Attacker |
| 343202 | Á. Rodríguez | 21 | 20 | Attacker |
| 635179 | Álex Sánchez | 19 | 38 | Attacker |
| 47329 | Adrià Pedrosa | 27 | 3 | Defender |
| 47378 | Bigas | 35 | 6 | Defender |
| 446067 | Buba Sangaré | 18 | 42 | Defender |
| 126640 | D. Affengruber | 24 | 22 | Defender |
| 580677 | David Delgado | 17 | 31 | Defender |
| 386859 | Héctor Fort | 19 | 39 | Defender |
| 189866 | John Nwankwo | 25 | 18 | Defender |
| 157146 | L. Pétrot | 28 | 21 | Defender |
| 626638 | N. Salvador | 19 | 36 | Defender |
| 585068 | P. Felipe | 20 | 33 | Defender |
| 162058 | Víctor Chust | 25 | 23 | Defender |
| 315604 | Alejandro Iturbe | 22 | 45 | Goalkeeper |
| 126 | Iñaki Peña | 26 | 13 | Goalkeeper |
| 11346 | M. Dituro | 38 | 1 | Goalkeeper |
| 46711 | Aleix Febas | 29 | 14 | Midfielder |
| 637727 | Alex Herraiz |  | 43 | Midfielder |
| 508284 | Antonio Martinez | 19 | 37 | Midfielder |
| 439640 | B. Sina | 22 | 26 | Midfielder |
| 311345 | F. Redondo | 22 | 5 | Midfielder |
| 46982 | Gonzalo Villar | 27 | 12 | Midfielder |
| 46973 | Josan | 36 | 17 | Midfielder |
| 187318 | Marc Aguado | 25 | 8 | Midfielder |
| 271580 | Martim Neto | 22 | 16 | Midfielder |
| 483121 | Nicolás González | 19 | 43 | Midfielder |


### Espanyol (`team_id=540`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `28`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 297742 | Antoniu Roca | 23 | 20 | Attacker |
| 47349 | Javi Puado | 27 | 7 | Attacker |
| 182674 | Jofre Carreras | 24 | 17 | Attacker |
| 47396 | Kike García | 36 | 19 | Attacker |
| 549458 | L. Castell | 19 | 32 | Attacker |
| 312990 | Roberto Fernández | 23 | 9 | Attacker |
| 273732 | T. Dolan | 24 | 24 | Attacker |
| 282054 | C. Riedel | 22 | 38 | Defender |
| 184420 | Carlos Romero | 24 | 22 | Defender |
| 47478 | Fernando Calero | 30 | 5 | Defender |
| 585288 | J. A. Lopez | 19 | 26 | Defender |
| 184407 | José Salinas | 25 | 12 | Defender |
| 47249 | L. Cabrera | 34 | 6 | Defender |
| 47256 | Miguel Rubio | 27 | 15 | Defender |
| 286601 | O. El Hilali | 22 | 23 | Defender |
| 199824 | Rubén Sánchez | 24 | 2 | Defender |
| 461502 | Llorenç Serred | 20 | 31 | Goalkeeper |
| 2813 | M. Dmitrović | 33 | 13 | Goalkeeper |
| 162585 | Pol Tristán | 23 | 30 | Goalkeeper |
| 182735 | Ángel Fortuño | 24 | 1 | Goalkeeper |
| 85 | C. Ngonge | 25 | 16 | Midfielder |
| 48555 | C. Pickel | 28 | 18 | Midfielder |
| 46799 | Edu Expósito | 29 | 8 | Midfielder |
| 601891 | F. Gomez | 19 | 28 | Midfielder |
| 47398 | Pere Milla | 33 | 11 | Midfielder |
| 127426 | Pol Lozano | 26 | 10 | Midfielder |
| 187987 | Ramón Terrats | 25 | 14 | Midfielder |
| 183699 | Urko González | 24 | 4 | Midfielder |


### Getafe (`team_id=546`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `36`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 284441 | A. Kamara | 22 | 11 | Attacker |
| 394573 | Adrian Liso | 20 | 23 | Attacker |
| 47472 | Borja Mayoral | 28 | 9 | Attacker |
| 333369 | Joselu | 21 | 37 | Attacker |
| 47320 | Juanmi | 32 | 7 | Attacker |
| 6490 | L. Vázquez | 24 | 19 | Attacker |
| 551462 | M. Aleksandrov | 21 | 29 | Attacker |
| 195512 | M. Satriano | 24 | 10 | Attacker |
| 45804 | V. Birmančević | 27 | 20 | Attacker |
| 439616 | Yassin Tallal | 20 | 39 | Attacker |
| 184459 | Álex Sancris | 28 | 18 | Attacker |
| 46813 | A. Abqar | 26 | 3 | Defender |
| 47407 | A. Nyom | 37 | 12 | Defender |
| 47250 | D. Dakonam | 34 | 2 | Defender |
| 471478 | Davinchi | 18 | 26 | Defender |
| 18867 | Diego Rico | 32 | 16 | Defender |
| 46795 | Domingos Duarte | 30 | 22 | Defender |
| 625636 | Jorge Montes | 21 | 41 | Defender |
| 119742 | Juan Iglesias | 27 | 21 | Defender |
| 18794 | Kiko Femenía | 34 | 17 | Defender |
| 609740 | L. Laso | 22 | 32 | Defender |
| 297235 | Marc Vilaplana | 22 | 33 | Defender |
| 316516 | S. Boselli | 22 | 15 | Defender |
| 180927 | Z. Romero | 26 | 24 | Defender |
| 439617 | Z. Tassounte | 21 | 31 | Defender |
| 47247 | David Soria | 32 | 13 | Goalkeeper |
| 482071 | Diego Ferrer | 18 | 42 | Goalkeeper |
| 66491 | J. Letáček | 26 | 1 | Goalkeeper |
| 432080 | Jorge Benito | 19 | 35 | Goalkeeper |
| 579838 | A. Mestanza | 21 | 45 | Midfielder |
| 631889 | Adrián Riquelme | 19 | 44 | Midfielder |
| 386187 | Hugo Solozábal | 22 | 34 | Midfielder |
| 46860 | Javi Muñoz | 30 | 14 | Midfielder |
| 47085 | Luis Milla | 31 | 5 | Midfielder |
| 47258 | M. Arambarri | 30 | 8 | Midfielder |
| 343205 | Mario Martín | 21 | 6 | Midfielder |


### Girona (`team_id=547`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 155 | Abel Ruiz | 25 | 9 | Attacker |
| 2061 | Bryan Gil | 24 | 21 | Attacker |
| 414385 | C. Echeverri | 19 | 14 | Attacker |
| 2617 | C. Stuani | 39 | 7 | Attacker |
| 553313 | Javier Sarasa | 20 | 30 | Attacker |
| 626331 | Juan Arango | 19 | 32 | Attacker |
| 455366 | P. Ba | 21 | 44 | Attacker |
| 47520 | Portu | 33 | 8 | Attacker |
| 161670 | V. Vanat | 23 | 19 | Attacker |
| 162434 | Alejandro Francés | 23 | 16 | Defender |
| 439709 | Antonio Salguero | 20 | 31 | Defender |
| 283668 | Arnau Martínez | 22 | 4 | Defender |
| 531 | D. Blind | 35 | 17 | Defender |
| 47334 | David López | 36 | 5 | Defender |
| 491106 | Gibert Jordana | 18 | 28 | Defender |
| 313025 | Hugo Rincón | 22 | 2 | Defender |
| 429757 | Pol Arnau | 21 | 27 | Defender |
| 414359 | Vitor Nunes | 19 | 12 | Defender |
| 47547 | Álex Moreno | 32 | 24 | Defender |
| 442861 | A. Andreev | 19 | 43 | Goalkeeper |
| 127 | M. ter Stegen | 33 | 22 | Goalkeeper |
| 158 | P. Gazzaniga | 33 | 13 | Goalkeeper |
| 47426 | Rubén Blanco | 30 | 1 | Goalkeeper |
| 432476 | V. Krapyvtsov | 20 | 25 | Goalkeeper |
| 129678 | A. Ounahi | 25 | 18 | Midfielder |
| 20 | A. Witsel | 36 | 20 | Midfielder |
| 47435 | Fran Beltrán | 26 | 8 | Midfielder |
| 1700 | Iván Martín | 26 | 23 | Midfielder |
| 339105 | Joel Roca | 20 | 3 | Midfielder |
| 439305 | L. Kourouma | 21 | 29 | Midfielder |
| 327628 | Ricard Artero | 22 | 36 | Midfielder |
| 45 | T. Lemar | 30 | 11 | Midfielder |
| 2182 | V. Tsygankov | 28 | 15 | Midfielder |


### Levante (`team_id=539`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 450497 | Carlos Espí | 20 | 19 | Attacker |
| 644099 | Enrique Herrero | 21 | 11 | Attacker |
| 378284 | Etta Eyong | 22 | 21 | Attacker |
| 645724 | F. Cortes | 18 | 27 | Attacker |
| 128985 | Iker Losada | 24 | 18 | Attacker |
| 47467 | José Luis Morales | 38 | 11 | Attacker |
| 328139 | T. Abed | 21 | 55 | Attacker |
| 316517 | A. Matturro | 21 | 3 | Defender |
| 734 | Dela | 26 | 4 | Defender |
| 104832 | Diego Pampín | 25 | 6 | Defender |
| 609795 | H. Nakoha |  | 35 | Defender |
| 1118 | J. Toljan | 31 | 22 | Defender |
| 407597 | M. Krug | 19 | 28 | Defender |
| 421807 | M. Moreno | 22 | 2 | Defender |
| 64309 | Manu Sánchez | 25 | 23 | Defender |
| 504605 | Nacho Pérez | 17 | 29 | Defender |
| 46941 | Unai Elgezabal | 32 | 5 | Defender |
| 450562 | Cayetano | 20 | 34 | Goalkeeper |
| 2741 | M. Ryan | 33 | 13 | Goalkeeper |
| 286611 | Pablo Cuñat | 23 | 1 | Goalkeeper |
| 338295 | Primo | 21 | 32 | Goalkeeper |
| 47225 | Brugui | 29 | 7 | Midfielder |
| 182770 | Carlos Álvarez | 22 | 24 | Midfielder |
| 385383 | Dani Cervera | 22 | 37 | Midfielder |
| 192032 | Iván Romero | 24 | 9 | Midfielder |
| 182603 | Jon Ander Olasagasti | 25 | 8 | Midfielder |
| 125239 | K. Arriaga | 27 | 16 | Midfielder |
| 579287 | K. Tunde |  | 26 | Midfielder |
| 106727 | Oriol Rey | 27 | 20 | Midfielder |
| 610174 | P. Roson | 20 | 30 | Midfielder |
| 104949 | Pablo Martínez | 27 | 10 | Midfielder |
| 463279 | Paco Cortés | 18 | 27 | Midfielder |
| 334878 | U. Raghouber | 22 | 14 | Midfielder |
| 182639 | Unai Vencedor | 25 | 12 | Midfielder |
| 46790 | Víctor García | 28 | 17 | Midfielder |


### Mallorca (`team_id=798`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 46751 | Abdón Prats | 33 | 9 | Attacker |
| 405074 | J. Kalumba | 21 | 30 | Attacker |
| 491248 | Jan Virgili | 19 | 17 | Attacker |
| 293604 | Javi Llabrés | 23 | 19 | Attacker |
| 313059 | M. Joseph | 22 | 18 | Attacker |
| 25375 | T. Asano | 31 | 11 | Attacker |
| 50048 | V. Muriqi | 31 | 7 | Attacker |
| 140831 | Zito Luvumbo | 23 | 15 | Attacker |
| 335697 | David López | 22 | 27 | Defender |
| 462277 | I. Salhi | 18 | 26 | Defender |
| 64268 | J. Mojica | 33 | 22 | Defender |
| 551463 | J. Olaizola | 18 | 34 | Defender |
| 626497 | L. Orejuela | 18 | 29 | Defender |
| 647395 | Leo Sánchez | 19 | 32 | Defender |
| 30924 | M. Kumbulla | 25 | 4 | Defender |
| 46738 | M. Valjent | 30 | 24 | Defender |
| 108519 | Mateu Morey | 25 | 2 | Defender |
| 414 | Omar Mascarell | 32 | 5 | Defender |
| 26302 | Pablo Maffeo | 28 | 23 | Defender |
| 46733 | Raíllo | 34 | 21 | Defender |
| 920 | Toni Lato | 28 | 3 | Defender |
| 47399 | Iván Cuéllar | 41 | 25 | Goalkeeper |
| 152955 | L. Bergström | 23 | 13 | Goalkeeper |
| 179139 | Leo Román | 25 | 1 | Goalkeeper |
| 648740 | Rareș Vlad | 20 | 42 | Goalkeeper |
| 613218 | Torreguitart Nil | 24 | 38 | Goalkeeper |
| 107194 | Antonio Sánchez | 28 | 6 | Midfielder |
| 646868 | C. Riba | 19 | 28 | Midfielder |
| 47336 | Darder | 32 | 10 | Midfielder |
| 629089 | J. Garcia | 19 | 39 | Midfielder |
| 1701 | Manu Morlanes | 26 | 8 | Midfielder |
| 285909 | Pablo Torre | 22 | 20 | Midfielder |
| 190485 | Samú Costa | 25 | 12 | Midfielder |


### Osasuna (`team_id=727`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 46746 | A. Budimir | 34 | 17 | Attacker |
| 288800 | Iker Benito | 23 | 2 | Attacker |
| 46667 | Kike Barja | 28 | 11 | Attacker |
| 337011 | Manu Rico | 22 | 10 | Attacker |
| 391819 | Martin Pedroarena | 22 | 11 | Attacker |
| 47574 | Moi Gómez | 31 | 16 | Attacker |
| 264470 | Raul Moro | 23 | 18 | Attacker |
| 146751 | Raúl García | 25 | 9 | Attacker |
| 331003 | Roberto Arroyo | 22 | 17 | Attacker |
| 181259 | Abel Bretones | 25 | 23 | Defender |
| 47533 | Catena | 31 | 24 | Defender |
| 279822 | F. Boyomo | 24 | 22 | Defender |
| 47566 | Javi Galán | 31 | 20 | Defender |
| 338872 | Jon García | 22 | 14 | Defender |
| 182592 | Jorge Herrando | 24 | 5 | Defender |
| 46967 | Juan Cruz | 33 | 3 | Defender |
| 560997 | M. Serrano | 22 | 23 | Defender |
| 332304 | Raúl Chasco | 22 | 21 | Defender |
| 560924 | U. Santos | 20 | 5 | Defender |
| 21701 | V. Rosier | 29 | 19 | Defender |
| 421044 | Íñigo Arguibide | 20 | 41 | Defender |
| 47448 | Aitor Fernández | 34 | 13 | Goalkeeper |
| 348029 | D. Stamatakis | 22 | 31 | Goalkeeper |
| 46646 | Sergio Herrera | 32 | 1 | Goalkeeper |
| 67939 | Aimar Oroz | 24 | 10 | Midfielder |
| 381197 | Asier Osambela | 21 | 29 | Midfielder |
| 182621 | Iker Muñoz | 23 | 8 | Midfielder |
| 1825 | Lucas Torró | 31 | 6 | Midfielder |
| 429553 | Mauro Echegoyen | 20 | 6 | Midfielder |
| 46662 | Moncayola | 27 | 7 | Midfielder |
| 46658 | Rubén García | 32 | 14 | Midfielder |
| 338751 | Víctor Muñoz | 22 | 21 | Midfielder |


### Oviedo (`team_id=718`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 51530 | F. Viñas | 27 | 9 | Attacker |
| 19613 | O. Ejaria | 28 | 14 | Attacker |
| 197513 | T. Borbas | 23 | 17 | Attacker |
| 362750 | T. Fernández | 21 | 15 | Attacker |
| 184194 | Álex Forés | 24 | 19 | Attacker |
| 647008 | Adri Fernández | 20 | 34 | Defender |
| 46966 | Dani Calvo | 31 | 12 | Defender |
| 41970 | David Carmo | 26 | 16 | Defender |
| 47429 | David Costas | 30 | 4 | Defender |
| 885 | E. Bailly | 31 | 2 | Defender |
| 640804 | Espi | 21 | 33 | Defender |
| 182636 | Javi López | 23 | 25 | Defender |
| 131548 | Lucas Ahijado | 30 | 24 | Defender |
| 46657 | Nacho Vidal | 30 | 22 | Defender |
| 295223 | R. Alhassane | 23 | 3 | Defender |
| 46673 | Aarón Escandell | 30 | 13 | Goalkeeper |
| 42642 | H. Moldovan | 27 | 1 | Goalkeeper |
| 297243 | Miguel Narváez | 23 | 26 | Goalkeeper |
| 182486 | Alberto Reina | 28 | 5 | Midfielder |
| 443152 | Cheli | 20 | 31 | Midfielder |
| 562472 | D. Menendez | 20 | 32 | Midfielder |
| 20844 | H. Hassan | 23 | 10 | Midfielder |
| 266202 | I. Chaira | 24 | 7 | Midfielder |
| 3608 | K. Sibo | 27 | 6 | Midfielder |
| 2922 | L. Dendoncker | 30 | 20 | Midfielder |
| 38699 | L. Ilić | 26 | 21 | Midfielder |
| 30690 | N. Fonseca | 27 | 23 | Midfielder |
| 600938 | P. Agudin | 17 | 27 | Midfielder |
| 30927 | S. Colombatto | 28 | 11 | Midfielder |
| 1695 | Santi Cazorla | 41 | 8 | Midfielder |


### Rayo Vallecano (`team_id=728`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 91745 | Alemão | 27 | 9 | Attacker |
| 128582 | Jorge de Frutos | 28 | 19 | Attacker |
| 52 | Sergio Camello | 24 | 10 | Attacker |
| 46759 | A. Espino | 33 | 22 | Defender |
| 15900 | A. Mumin | 27 | 16 | Defender |
| 1703 | A. Rațiu | 27 | 2 | Defender |
| 18895 | F. Lejeune | 34 | 24 | Defender |
| 20520 | I. Balliu | 33 | 20 | Defender |
| 314006 | J. Vertrouwd | 21 | 33 | Defender |
| 1847 | Luiz Felipe | 28 | 5 | Defender |
| 478243 | Marco de las Sías | 20 | 26 | Defender |
| 358431 | N. Mendy | 21 | 32 | Defender |
| 181734 | Pep Chavarría | 27 | 3 | Defender |
| 626804 | S. Lozano | 19 | 27 | Defender |
| 11379 | A. Batalla | 29 | 13 | Goalkeeper |
| 478244 | Adrián Molina | 20 | 30 | Goalkeeper |
| 156488 | Dani Cárdenas | 28 | 1 | Goalkeeper |
| 285505 | Juanpe | 24 | 30 | Goalkeeper |
| 324750 | Carlos Martín | 23 | 14 | Midfielder |
| 162931 | Fran Pérez | 23 | 21 | Midfielder |
| 47414 | Gumbau | 31 | 15 | Midfielder |
| 290740 | Ilias Akhomach | 21 | 12 | Midfielder |
| 131546 | Isi Palazón | 31 | 7 | Midfielder |
| 626805 | M. Roman | 19 | 31 | Midfielder |
| 41552 | P. Ciss | 31 | 6 | Midfielder |
| 46887 | Pedro Díaz | 27 | 4 | Midfielder |
| 122657 | R. Nteka | 28 | 11 | Midfielder |
| 439633 | Samu Becerra | 19 | 28 | Midfielder |
| 47285 | Unai López | 30 | 17 | Midfielder |
| 47543 | Álvaro García | 33 | 18 | Midfielder |
| 47557 | Ó. Trejo | 37 | 8 | Midfielder |
| 47109 | Óscar Valentín | 31 | 23 | Midfielder |


### Real Betis (`team_id=543`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `36`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 47119 | Aitor Ruibal | 29 | 24 | Attacker |
| 3033 | C. Bakambu | 34 | 11 | Attacker |
| 47582 | C. Hernández | 26 | 19 | Attacker |
| 47579 | E. Ávila | 31 | 9 | Attacker |
| 544644 | J. A. Morante | 18 | 27 | Attacker |
| 443163 | Pablo García | 19 | 7 | Attacker |
| 548691 | R. Marina | 19 | 17 | Attacker |
| 610742 | C. De Roa | 18 | 32 | Defender |
| 289554 | D. Bladi | 21 | 23 | Defender |
| 47302 | Diego Llorente | 32 | 3 | Defender |
| 1439 | Héctor Bellerín | 30 | 2 | Defender |
| 1564 | Junior Firpo | 29 | 23 | Defender |
| 1561 | Marc Bartra | 35 | 5 | Defender |
| 195100 | Natan | 24 | 4 | Defender |
| 1631 | R. Rodríguez | 33 | 12 | Defender |
| 630908 | Robson | 19 | 6 | Defender |
| 355004 | V. Gómez | 22 | 16 | Defender |
| 334574 | Ángel Ortiz | 21 | 40 | Defender |
| 18812 | Adrián | 38 | 13 | Goalkeeper |
| 392455 | Germán García | 21 | 1 | Goalkeeper |
| 456619 | Manu González | 18 | 31 | Goalkeeper |
| 1557 | Pau López | 31 | 25 | Goalkeeper |
| 46990 | Álvaro Vallés | 28 | 1 | Goalkeeper |
| 181421 | A. Ezzalzouli | 24 | 10 | Midfielder |
| 9971 | Antony | 25 | 7 | Midfielder |
| 351131 | Dani Pérez | 20 | 8 | Midfielder |
| 1578 | G. Lo Celso | 29 | 20 | Midfielder |
| 745 | Isco | 33 | 22 | Midfielder |
| 450714 | Ivan Corralejo | 18 | 37 | Midfielder |
| 47341 | Marc Roca | 29 | 21 | Midfielder |
| 300885 | N. Deossa | 25 | 18 | Midfielder |
| 1697 | Pablo Fornals | 29 | 8 | Midfielder |
| 136117 | Rodrigo Riquelme | 25 | 17 | Midfielder |
| 74 | S. Amrabat | 29 | 14 | Midfielder |
| 286084 | Sergi Altimira | 24 | 6 | Midfielder |
| 750 | Álvaro Fidalgo | 28 | 15 | Midfielder |


### Real Madrid (`team_id=541`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `40`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 441497 | Daniel Yañez | 18 | 7 | Attacker |
| 449249 | Franco Mastantuono | 18 | 30 | Attacker |
| 336711 | Gonzalo García | 21 | 16 | Attacker |
| 278 | Kylian Mbappé | 27 | 10 | Attacker |
| 10009 | Rodrygo | 24 | 11 | Attacker |
| 762 | Vinícius Júnior | 25 | 7 | Attacker |
| 308998 | Ávaro Leiva | 21 | 39 | Attacker |
| 2285 | A. Rüdiger | 32 | 22 | Defender |
| 505 | D. Alaba | 33 | 4 | Defender |
| 361497 | D. Huijsen | 20 | 24 | Defender |
| 733 | Dani Carvajal | 33 | 2 | Defender |
| 330436 | David Jiménez | 21 | 2 | Defender |
| 451355 | Diego Aguado | 18 | 27 | Defender |
| 653 | F. Mendy | 30 | 23 | Defender |
| 736 | Fran García | 26 | 20 | Defender |
| 561033 | J. Martinez | 18 | 15 | Defender |
| 443595 | Jesús Fortea | 18 | 17 | Defender |
| 561032 | L. Fati | 19 | 23 | Defender |
| 341640 | Raúl Asencio | 22 | 17 | Defender |
| 283 | T. Alexander-Arnold | 27 | 12 | Defender |
| 560901 | V. Valdepenas | 19 | 3 | Defender |
| 284300 | Álvaro Fernández | 22 | 18 | Defender |
| 372 | Éder Militão | 27 | 3 | Defender |
| 47400 | A. Lunin | 26 | 13 | Goalkeeper |
| 396475 | Fran González | 20 | 26 | Goalkeeper |
| 544044 | J. Navarro Jimenez | 18 | 29 | Goalkeeper |
| 386872 | Sergio Mestre | 20 | 25 | Goalkeeper |
| 730 | T. Courtois | 33 | 1 | Goalkeeper |
| 291964 | A. Güler | 20 | 15 | Midfielder |
| 1271 | A. Tchouaméni | 25 | 14 | Midfielder |
| 744 | Brahim Díaz | 26 | 21 | Midfielder |
| 386306 | César Palacios | 21 | 10 | Midfielder |
| 748 | Dani Ceballos | 29 | 19 | Midfielder |
| 2207 | E. Camavinga | 23 | 6 | Midfielder |
| 756 | F. Valverde | 27 | 8 | Midfielder |
| 129718 | J. Bellingham | 22 | 5 | Midfielder |
| 560905 | J. Cestero Sancho | 19 | 28 | Midfielder |
| 313167 | Manuel Ángel | 21 | 37 | Midfielder |
| 371913 | Pol Fortuny | 20 | 20 | Midfielder |
| 509470 | Thiago Pitarch | 18 | 45 | Midfielder |


### Real Sociedad (`team_id=548`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 449063 | Alex Garcia | 18 | 19 | Attacker |
| 402168 | Arkaitz Mariezkurrena | 20 | 10 | Attacker |
| 412738 | Dani Díaz | 19 | 7 | Attacker |
| 925 | Gonçalo Guedes | 29 | 11 | Attacker |
| 403561 | Gorka Carrera | 20 | 18 | Attacker |
| 183748 | Jon Karrikaburu | 23 | 19 | Attacker |
| 47323 | Mikel Oyarzabal | 28 | 10 | Attacker |
| 61774 | O. Óskarsson | 21 | 9 | Attacker |
| 365287 | Wesley Gassova | 20 | 22 | Attacker |
| 47303 | Aihen Muñoz | 28 | 3 | Defender |
| 1902 | D. Ćaleta-Car | 29 | 16 | Defender |
| 47298 | Elustondo | 31 | 6 | Defender |
| 199044 | J. Aramburu | 23 | 2 | Defender |
| 387139 | J. Ochieng | 22 | 11 | Defender |
| 405073 | Jon Martín | 19 | 31 | Defender |
| 349063 | Luken Beitia | 21 | 38 | Defender |
| 737 | Odriozola | 30 | 20 | Defender |
| 23 | Sergio Gómez | 25 | 17 | Defender |
| 47314 | Zubeldia | 28 | 5 | Defender |
| 337843 | Aitor Fraga | 22 | 32 | Goalkeeper |
| 431160 | T. Folgado | 20 | 32 | Goalkeeper |
| 189832 | Unai Marrero | 24 | 13 | Goalkeeper |
| 47269 | Álex Remiro | 30 | 1 | Goalkeeper |
| 268960 | A. Zakharyan | 22 | 21 | Midfielder |
| 47317 | Barrenetxea | 24 | 7 | Midfielder |
| 183744 | Beñat Turrientes | 23 | 8 | Midfielder |
| 47440 | Brais Méndez | 28 | 23 | Midfielder |
| 930 | Carlos Soler | 28 | 18 | Midfielder |
| 469672 | Ibai Aguirre | 18 | 46 | Midfielder |
| 287654 | Jon Gorrotxategi | 23 | 4 | Midfielder |
| 7332 | L. Sučić | 23 | 24 | Midfielder |
| 445881 | Lander Astiazarán | 19 | 17 | Midfielder |
| 290106 | Pablo Marín | 22 | 15 | Midfielder |
| 32862 | T. Kubo | 24 | 14 | Midfielder |
| 2449 | Y. Herrera | 27 | 12 | Midfielder |


### Sevilla (`team_id=536`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 57446 | A. Adams | 25 | 9 | Attacker |
| 546872 | A. Costa | 22 | 9 | Attacker |
| 910 | A. Sánchez | 37 | 10 | Attacker |
| 39121 | C. Ejuke | 27 | 21 | Attacker |
| 185398 | Isaac | 25 | 7 | Attacker |
| 546798 | M. Sierra | 21 | 7 | Attacker |
| 19364 | N. Maupay | 29 | 17 | Attacker |
| 162126 | Peque Fernández | 23 | 14 | Attacker |
| 338902 | Andrés Castrín | 22 | 32 | Defender |
| 2280 | César Azpilicueta | 36 | 3 | Defender |
| 125331 | F. Gattoni | 26 | 22 | Defender |
| 41208 | Fábio Cardoso | 31 | 15 | Defender |
| 11421 | G. Suazo | 28 | 12 | Defender |
| 546857 | I. Munoz | 21 | 4 | Defender |
| 195923 | José Ángel Carmona | 23 | 2 | Defender |
| 297311 | Kike Salas | 23 | 4 | Defender |
| 433 | Marcão | 29 | 23 | Defender |
| 133110 | T. Nianzou | 23 | 5 | Defender |
| 308346 | Alberto Flores | 22 | 13 | Goalkeeper |
| 548843 | L. Luchino | 19 | 25 | Goalkeeper |
| 557 | O. Vlachodimos | 31 | 1 | Goalkeeper |
| 290686 | Rafael Romero | 22 | 1 | Goalkeeper |
| 19172 | Ø. Nyland | 35 | 13 | Goalkeeper |
| 2924 | A. Januzaj | 30 | 24 | Midfielder |
| 21087 | B. Mendy | 26 | 19 | Midfielder |
| 957 | D. Sow | 28 | 20 | Midfielder |
| 47389 | Joan Jordán | 31 | 8 | Midfielder |
| 182772 | Juanlu Sánchez | 22 | 16 | Midfielder |
| 21004 | L. Agoumé | 23 | 18 | Midfielder |
| 331607 | Manu Bueno | 21 | 28 | Midfielder |
| 1489 | N. Gudelj | 34 | 6 | Midfielder |
| 341453 | Oso | 22 | 36 | Midfielder |
| 48471 | R. Vargas | 27 | 11 | Midfielder |


### Valencia (`team_id=532`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `37`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 83 | A. Danjuma | 28 | 7 | Attacker |
| 1708 | Dani Raba | 30 | 19 | Attacker |
| 439578 | David Otorbi | 18 | 27 | Attacker |
| 162127 | Diego López | 23 | 16 | Attacker |
| 47264 | Hugo Duro | 26 | 9 | Attacker |
| 6010 | L. Beltrán | 24 | 15 | Attacker |
| 549444 | M. Jurado | 19 | 38 | Attacker |
| 364414 | Mario Domínguez | 21 | 39 | Attacker |
| 31406 | U. Sadiq | 28 | 6 | Attacker |
| 584165 | A. Panach | 19 | 32 | Defender |
| 641317 | Aaron Mayol | 17 | 42 | Defender |
| 181582 | Copete | 26 | 3 | Defender |
| 333672 | César Tárrega | 23 | 5 | Defender |
| 47251 | D. Foulquier | 32 | 20 | Defender |
| 48372 | E. Cömert | 27 | 24 | Defender |
| 162175 | Jesús Vázquez | 22 | 21 | Defender |
| 623732 | Joel Fontanet | 19 | 40 | Defender |
| 918 | José Gayà | 30 | 14 | Defender |
| 916 | M. Diakhaby | 29 | 4 | Defender |
| 47463 | Pepelu | 27 | 18 | Defender |
| 2470 | R. Saravia | 32 | 20 | Defender |
| 315701 | Rubo Iranzo | 22 | 26 | Defender |
| 1482 | Thierry Correia | 26 | 12 | Defender |
| 47277 | Unai Núñez | 28 | 4 | Defender |
| 913 | Cristian Rivero | 27 | 13 | Goalkeeper |
| 183848 | Julen Agirrezabala | 25 | 25 | Goalkeeper |
| 47527 | S. Dimitrievski | 32 | 1 | Goalkeeper |
| 401983 | Vicent Abril | 20 | 28 | Goalkeeper |
| 41157 | André Almeida | 25 | 10 | Midfielder |
| 21153 | B. Santamaría | 30 | 22 | Midfielder |
| 48465 | F. Ugrinic | 26 | 23 | Midfielder |
| 2476 | G. Rodríguez | 31 | 2 | Midfielder |
| 315699 | Javi Guerra | 22 | 8 | Midfielder |
| 297743 | Javier Navarro Girona | 21 | 36 | Midfielder |
| 138776 | L. Ramazani | 24 | 17 | Midfielder |
| 406043 | Lucas Nuñez | 19 | 29 | Midfielder |
| 46933 | Luis Rioja | 32 | 11 | Midfielder |


### Villarreal (`team_id=533`)

- Competition: `La Liga`
- League ID: `140`
- Season: `2025`
- Country: `Spain`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 119213 | Alfon González | 26 | 11 | Attacker |
| 18906 | Ayoze Pérez | 32 | 22 | Attacker |
| 180496 | G. Mikautadze | 25 | 9 | Attacker |
| 1707 | Gerard Moreno | 33 | 7 | Attacker |
| 514913 | Hugo López | 18 | 32 | Attacker |
| 548807 | J. A. Gaitan Diaz | 18 | 26 | Attacker |
| 351587 | T. Oluwaseyi | 25 | 21 | Attacker |
| 355994 | A. Freeman | 21 | 3 | Defender |
| 455356 | Daniel Budesca | 19 | 2 | Defender |
| 166 | J. Foyth | 27 | 8 | Defender |
| 484474 | J. Valou | 20 | 23 | Defender |
| 21997 | Logan Costa | 24 | 2 | Defender |
| 435552 | Pau Navarro | 20 | 6 | Defender |
| 1702 | Pedraza | 29 | 24 | Defender |
| 237066 | Rafa Marín | 23 | 4 | Defender |
| 336671 | Renato Veiga | 22 | 12 | Defender |
| 311773 | S. Mouriño | 23 | 15 | Defender |
| 70500 | Sergi Cardona | 26 | 23 | Defender |
| 288112 | Willy Kambwala Ndengushi | 21 | 5 | Defender |
| 162473 | Arnau Tenas | 24 | 25 | Goalkeeper |
| 122956 | Diego Conde | 27 | 13 | Goalkeeper |
| 278619 | Luíz Júnior | 24 | 1 | Goalkeeper |
| 463280 | A. Diatta | 20 | 38 | Midfielder |
| 182519 | Alberto Moleiro | 22 | 20 | Midfielder |
| 548734 | C. Macia | 17 | 28 | Midfielder |
| 928 | Dani Parejo | 36 | 10 | Midfielder |
| 3246 | N. Pépé | 30 | 19 | Midfielder |
| 20696 | P. Gueye | 26 | 18 | Midfielder |
| 47541 | Santi Comesaña | 29 | 14 | Midfielder |
| 51016 | T. Buchanan | 26 | 17 | Midfielder |
| 49 | T. Partey | 32 | 16 | Midfielder |



## Bundesliga

### 1. FC Heidenheim (`team_id=180`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `27`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 24641 | B. Zivzivadze | 31 | 11 | Attacker |
| 64302 | C. Conteh | 26 | 10 | Attacker |
| 24955 | M. Honsak | 29 | 17 | Attacker |
| 15732 | M. Kaufmann | 24 | 29 | Attacker |
| 125720 | S. Conteh | 29 | 31 | Attacker |
| 26530 | S. Schimmer | 31 | 9 | Attacker |
| 480613 | Y. Wagner | 18 | 38 | Attacker |
| 431917 | Adam Kölle | 19 | 28 | Defender |
| 353143 | Hennes Behrens | 20 | 26 | Defender |
| 24979 | J. Föhrenbach | 29 | 19 | Defender |
| 48481 | L. Stergiou | 23 | 25 | Defender |
| 24897 | M. Busch | 31 | 2 | Defender |
| 25502 | O. Traoré | 27 | 23 | Defender |
| 24899 | P. Mainka | 31 | 6 | Defender |
| 177815 | T. Siersleben | 25 | 4 | Defender |
| 24894 | D. Ramaj | 24 | 41 | Goalkeeper |
| 328008 | Frank  Feller | 21 | 40 | Goalkeeper |
| 207229 | P. Tschernuth | 23 | 34 | Goalkeeper |
| 8959 | A. Beck | 28 | 21 | Midfielder |
| 327897 | A. Ibrahimović | 20 | 22 | Midfielder |
| 25203 | B. Gimber | 28 | 5 | Midfielder |
| 202526 | E. Dinkçi | 24 | 8 | Midfielder |
| 203011 | J. Niehues | 24 | 16 | Midfielder |
| 127619 | J. Schöppner | 26 | 3 | Midfielder |
| 280055 | L. Kerber | 23 | 20 | Midfielder |
| 178106 | M. Pieringer | 26 | 18 | Midfielder |
| 24904 | N. Dorsch | 27 | 30 | Midfielder |


### 1. FC Köln (`team_id=192`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `26`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 610631 | C. Neumann | 18 | 36 | Attacker |
| 26260 | L. Waldschmidt | 29 | 7 | Attacker |
| 37439 | R. Ache | 27 | 9 | Attacker |
| 432310 | S. El Mala | 19 | 13 | Attacker |
| 72048 | C. Özkacar | 25 | 39 | Defender |
| 26237 | D. Heintz | 32 | 3 | Defender |
| 48765 | J. Schmied | 27 | 2 | Defender |
| 404656 | Jahmai Simpson-Pusey | 20 | 22 | Defender |
| 162386 | K. Lund | 23 | 32 | Defender |
| 287916 | R. van den Berg | 21 | 33 | Defender |
| 191740 | S. Sebulonsen | 25 | 28 | Defender |
| 24892 | M. Köbbing | 28 | 44 | Goalkeeper |
| 15871 | M. Schwäbe | 30 | 1 | Goalkeeper |
| 26293 | R. Zieler | 36 | 20 | Goalkeeper |
| 8641 | A. Castro-Montes | 28 | 17 | Midfielder |
| 202838 | D. Huseinbašić | 24 | 8 | Midfielder |
| 162480 | E. Martel | 23 | 6 | Midfielder |
| 414474 | F. Chávez | 18 | 27 | Midfielder |
| 24803 | F. Kainz | 33 | 11 | Midfielder |
| 610625 | F. Schenten | 18 | 40 | Midfielder |
| 40560 | J. Kamiński | 23 | 16 | Midfielder |
| 181908 | J. Thielmann | 23 | 29 | Midfielder |
| 25380 | L. Maina | 26 | 37 | Midfielder |
| 25242 | M. Bülter | 32 | 30 | Midfielder |
| 1156 | T. Krauß | 24 | 5 | Midfielder |
| 48198 | Í. Bergmann Jóhannesson | 22 | 18 | Midfielder |


### 1899 Hoffenheim (`team_id=167`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `29`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 66019 | A. Hložek | 23 | 9 | Attacker |
| 726 | A. Kramarić | 34 | 27 | Attacker |
| 202501 | F. Asllani | 23 | 11 | Attacker |
| 25389 | I. Bebou | 31 | 9 | Attacker |
| 387973 | Max Moerstedt | 19 | 33 | Attacker |
| 203040 | T. Lemperle | 23 | 19 | Attacker |
| 328617 | William Cole Campbell | 19 | 20 | Attacker |
| 404133 | Y. Eduardo | 19 | 31 | Attacker |
| 278453 | A. Hajdari | 22 | 21 | Defender |
| 7327 | A. Prass | 24 | 22 | Defender |
| 18964 | Bernardo | 30 | 13 | Defender |
| 25366 | K. Akpoguma | 30 | 25 | Defender |
| 380559 | Kelven Olagie Frees | 20 | 5 | Defender |
| 456187 | Luca Erlein | 18 | 24 | Defender |
| 26300 | O. Kabak | 25 | 5 | Defender |
| 162964 | R. Hranáč | 25 | 2 | Defender |
| 127631 | V. Gendrey | 25 | 15 | Defender |
| 163066 | L. Philipp | 25 | 37 | Goalkeeper |
| 702 | O. Baumann | 35 | 1 | Goalkeeper |
| 387643 | B. Touré | 19 | 29 | Midfielder |
| 340089 | Florian Micheler | 20 | 14 | Midfielder |
| 24854 | G. Prömel | 30 | 6 | Midfielder |
| 390586 | L. Avdullahu | 21 | 7 | Midfielder |
| 455332 | L. Engelns | 18 | 17 | Midfielder |
| 279913 | L. Đurić | 22 | 48 | Midfielder |
| 328262 | M. Damar | 21 | 10 | Midfielder |
| 1231 | V. Coufal | 33 | 34 | Midfielder |
| 202976 | V. Lässig | 22 | 6 | Midfielder |
| 37153 | W. Burger | 24 | 18 | Midfielder |


### Bayer Leverkusen (`team_id=168`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 505295 | Christian Kofane | 19 | 35 | Attacker |
| 343320 | E. Ben Seghir | 20 | 17 | Attacker |
| 567959 | E. C. Owen | 18 | 47 | Attacker |
| 312840 | E. Poku | 21 | 19 | Attacker |
| 380587 | I. Maza | 20 | 30 | Attacker |
| 663 | M. Terrier | 28 | 11 | Attacker |
| 231029 | N. Tella | 26 | 23 | Attacker |
| 794 | P. Schick | 29 | 14 | Attacker |
| 352375 | Arthur | 22 | 13 | Defender |
| 486523 | B. Hawighorst | 17 | 29 | Defender |
| 41150 | E. Tapsoba | 26 | 12 | Defender |
| 158698 | J. Quansah | 22 | 4 | Defender |
| 174918 | L. Badé | 25 | 5 | Defender |
| 24903 | R. Andrich | 31 | 8 | Defender |
| 280091 | T. Oermann | 22 | 15 | Defender |
| 37246 | J. Blaswich | 34 | 28 | Goalkeeper |
| 2801 | J. Omlin | 31 | 18 | Goalkeeper |
| 568379 | J. Schlich | 18 | 1 | Goalkeeper |
| 26232 | M. Flekken | 32 | 1 | Goalkeeper |
| 25168 | N. Lomb | 32 | 36 | Goalkeeper |
| 491103 | A. Tape | 18 | 16 | Midfielder |
| 47516 | Aleix García | 28 | 24 | Midfielder |
| 237087 | E. Fernández | 23 | 6 | Midfielder |
| 6002 | E. Palacios | 27 | 25 | Midfielder |
| 25635 | J. Hofmann | 33 | 7 | Midfielder |
| 493409 | J. Mensah | 17 | 10 | Midfielder |
| 757 | Lucas Vázquez | 34 | 21 | Midfielder |
| 444961 | M. Culbreath | 18 | 42 | Midfielder |
| 162037 | M. Tillman | 23 | 10 | Midfielder |
| 563 | Álex Grimaldo | 30 | 20 | Midfielder |


### Bayern München (`team_id=157`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `36`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 657672 | B. Assomo | 16 | 33 | Attacker |
| 184 | H. Kane | 32 | 9 | Attacker |
| 283058 | N. Jackson | 24 | 11 | Attacker |
| 510 | S. Gnabry | 30 | 7 | Attacker |
| 509 | A. Davies | 25 | 19 | Defender |
| 524214 | Cassiano Kiala | 16 | 30 | Defender |
| 567867 | D. Ofli | 18 | 34 | Defender |
| 1149 | D. Upamecano | 27 | 2 | Defender |
| 628356 | F. Pavic | 15 | 43 | Defender |
| 32893 | H. Ito | 26 | 21 | Defender |
| 125171 | J. Stanišić | 25 | 44 | Defender |
| 972 | J. Tah | 29 | 4 | Defender |
| 1157 | K. Laimer | 28 | 27 | Defender |
| 2897 | Kim Min-Jae | 29 | 3 | Defender |
| 610483 | V. Manuba | 20 | 41 | Defender |
| 203376 | J. Urbig | 22 | 40 | Goalkeeper |
| 432595 | Jannis Bärtl | 19 | 35 | Goalkeeper |
| 568316 | L. Prescott | 16 | 37 | Goalkeeper |
| 435089 | Leon Klanac | 18 | 48 | Goalkeeper |
| 497 | M. Neuer | 39 | 1 | Goalkeeper |
| 498 | S. Ulreich | 37 | 26 | Goalkeeper |
| 328033 | A. Pavlović | 21 | 45 | Midfielder |
| 630895 | Bara Ndiaye | 18 | 39 | Midfielder |
| 449689 | David Daiber | 18 | 47 | Midfielder |
| 648615 | Erblin Osmani | 16 | 38 | Midfielder |
| 568043 | G. Della Rovere | 18 | 31 | Midfielder |
| 502 | J. Kimmich | 30 | 6 | Midfielder |
| 181812 | J. Musiala | 22 | 10 | Midfielder |
| 2489 | L. Díaz | 28 | 14 | Midfielder |
| 511 | L. Goretzka | 30 | 8 | Midfielder |
| 494131 | L. Karl | 17 | 42 | Midfielder |
| 568042 | M. Cardozo | 17 | 49 | Midfielder |
| 19617 | M. Olise | 24 | 17 | Midfielder |
| 8 | Raphaël Guerreiro | 32 | 22 | Midfielder |
| 325975 | T. Bischof | 20 | 20 | Midfielder |
| 496738 | W. Mike | 17 | 36 | Midfielder |


### Borussia Dortmund (`team_id=165`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `29`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 129791 | Fábio Silva | 23 | 21 | Attacker |
| 984 | J. Brandt | 29 | 10 | Attacker |
| 7334 | K. Adeyemi | 23 | 27 | Attacker |
| 486522 | M. Albert | 16 | 41 | Attacker |
| 21393 | S. Guirassy | 29 | 9 | Attacker |
| 478991 | S. Inacio | 17 | 40 | Attacker |
| 394667 | Almugera Raouf Mohammed Kabar | 19 | 42 | Defender |
| 198654 | D. Svensson | 23 | 24 | Defender |
| 420351 | Elias  Benkara | 18 | 47 | Defender |
| 341839 | F. Mané | 20 | 39 | Defender |
| 568225 | L. Reggiani | 17 | 49 | Defender |
| 26243 | N. Schlotterbeck | 26 | 4 | Defender |
| 506 | N. Süle | 30 | 25 | Defender |
| 2194 | R. Bensebaïni | 30 | 5 | Defender |
| 25368 | W. Anton | 29 | 3 | Defender |
| 197448 | Yan Couto | 23 | 2 | Defender |
| 26292 | A. Meyer | 34 | 33 | Goalkeeper |
| 25282 | G. Kobel | 28 | 1 | Goalkeeper |
| 26395 | P. Drewes | 32 | 30 | Goalkeeper |
| 280463 | S. Ostrzinski | 22 | 31 | Goalkeeper |
| 138935 | C. Chukwuemeka | 22 | 17 | Midfielder |
| 864 | E. Can | 31 | 23 | Midfielder |
| 637 | F. Nmecha | 25 | 8 | Midfielder |
| 326757 | J. Bellingham | 20 | 7 | Midfielder |
| 24845 | J. Ryerson | 28 | 26 | Midfielder |
| 158644 | M. Beier | 23 | 14 | Midfielder |
| 1159 | M. Sabitzer | 31 | 20 | Midfielder |
| 592218 | Mussa Kaba | 16 | 48 | Midfielder |
| 24807 | S. Özcan | 27 | 6 | Midfielder |


### Borussia Mönchengladbach (`team_id=163`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 414384 | A. Sarco | 19 | 8 | Attacker |
| 585704 | F. Fleck | 18 | 24 | Attacker |
| 20784 | F. Honorat | 29 | 9 | Attacker |
| 28382 | H. Tabaković | 31 | 15 | Attacker |
| 428913 | Jan Urbich | 21 | 40 | Attacker |
| 106851 | S. Machino | 26 | 18 | Attacker |
| 26256 | T. Kleindienst | 30 | 11 | Attacker |
| 322627 | F. Chiarodia | 20 | 2 | Defender |
| 31043 | K. Diks | 29 | 4 | Defender |
| 337593 | K. Takai | 21 | 14 | Defender |
| 327646 | L. Ullrich | 21 | 26 | Defender |
| 24839 | M. Friedrich | 30 | 5 | Defender |
| 2803 | N. Elvedi | 29 | 30 | Defender |
| 24969 | P. Sander | 27 | 16 | Defender |
| 651914 | Simon Walde | 21 | 45 | Defender |
| 327664 | V. Stange | 21 | 48 | Defender |
| 178405 | J. Olschowsky | 24 | 23 | Goalkeeper |
| 25626 | M. Nicolas | 28 | 33 | Goalkeeper |
| 340155 | T. Pereira Cardoso | 19 | 42 | Goalkeeper |
| 25627 | T. Sippel | 37 | 21 | Goalkeeper |
| 25638 | F. Neuhaus | 28 | 10 | Midfielder |
| 161921 | G. Reyna | 23 | 13 | Midfielder |
| 335095 | H. Bolin | 22 | 38 | Midfielder |
| 280358 | J. Castrop | 22 | 17 | Midfielder |
| 50852 | J. Scally | 23 | 29 | Midfielder |
| 25461 | K. Stöger | 32 | 7 | Midfielder |
| 442151 | Niklas Swider | 18 | 39 | Midfielder |
| 725 | R. Hack | 27 | 25 | Midfielder |
| 203007 | R. Reitz | 23 | 27 | Midfielder |
| 501906 | W. Mohya | 17 | 36 | Midfielder |
| 178709 | Y. Engelhardt | 24 | 6 | Midfielder |


### Eintracht Frankfurt (`team_id=169`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 147831 | A. Kalimuendo | 23 | 25 | Attacker |
| 161922 | A. Knauff | 23 | 7 | Attacker |
| 567973 | A. Staff | 17 | 9 | Attacker |
| 25926 | J. Burkardt | 25 | 9 | Attacker |
| 2927 | M. Batshuayi | 32 | 30 | Attacker |
| 409190 | Y. Ebnoutalib | 22 | 11 | Attacker |
| 162414 | A. Amenda | 22 | 5 | Defender |
| 204043 | A. Theate | 25 | 3 | Defender |
| 21587 | E. Skhiri | 30 | 15 | Defender |
| 382492 | Elias Baum | 20 | 2 | Defender |
| 382491 | Fousseny Doumbia | 20 | 41 | Defender |
| 423789 | K. Kosugi | 19 | 26 | Defender |
| 280074 | N. Brown | 22 | 21 | Defender |
| 269531 | N. Collins | 21 | 34 | Defender |
| 26238 | R. Koch | 29 | 4 | Defender |
| 533 | R. Kristensen | 28 | 13 | Defender |
| 1803 | T. Chandler | 35 | 22 | Defender |
| 467927 | A. Siljevic | 18 | 39 | Goalkeeper |
| 26291 | J. Grahl | 37 | 33 | Goalkeeper |
| 362884 | Kauã Santos | 22 | 40 | Goalkeeper |
| 7288 | M. Zetterer | 30 | 23 | Goalkeeper |
| 535046 | A. Amaimouni | 20 | 29 | Midfielder |
| 339887 | C. Uzun | 20 | 42 | Midfielder |
| 276670 | F. Chaïbi | 23 | 8 | Midfielder |
| 335094 | H. Larsson | 21 | 16 | Midfielder |
| 369674 | J. Bahoya | 20 | 19 | Midfielder |
| 496976 | L. Arrhov | 17 | 31 | Midfielder |
| 14 | M. Dahoud | 29 | 18 | Midfielder |
| 478662 | M. Dills | 18 | 10 | Midfielder |
| 16 | M. Götze | 33 | 27 | Midfielder |
| 339874 | O. HÃ¸jlund | 20 | 6 | Midfielder |
| 2598 | R. Dōan | 27 | 20 | Midfielder |


### FC Augsburg (`team_id=170`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `27`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 25297 | M. Gregoritsch | 31 | 38 | Attacker |
| 341641 | Rodrigo Ribeiro | 20 | 21 | Attacker |
| 499495 | U. Ogundu | 19 | 39 | Attacker |
| 304686 | Arthur Chaves | 24 | 34 | Defender |
| 163039 | C. Matsima | 23 | 5 | Defender |
| 48574 | C. Zesiger | 27 | 16 | Defender |
| 2360 | D. Giannoulis | 30 | 13 | Defender |
| 25290 | J. Gouweleeuw | 34 | 6 | Defender |
| 26242 | K. Schlotterbeck | 28 | 31 | Defender |
| 15901 | M. Pedersen | 29 | 3 | Defender |
| 413065 | Noahkai Kai Daniel Banks | 19 | 40 | Defender |
| 404895 | O. Sorg | 18 | 43 | Defender |
| 143831 | R. Fellhauer | 27 | 19 | Defender |
| 585671 | T. Schnitzer | 17 | 37 | Defender |
| 163064 | D. Klein | 24 | 25 | Goalkeeper |
| 25903 | F. Dahmen | 27 | 1 | Goalkeeper |
| 14553 | N. Labrović | 26 | 22 | Goalkeeper |
| 20634 | A. Claude-Maurice | 27 | 20 | Midfielder |
| 279993 | A. Kade | 21 | 30 | Midfielder |
| 25413 | E. Rexhbeçaj | 28 | 8 | Midfielder |
| 163032 | F. Rieder | 23 | 32 | Midfielder |
| 110 | H. Massengo | 24 | 4 | Midfielder |
| 310196 | Ismaël Gharbi | 21 | 11 | Midfielder |
| 14395 | K. Jakić | 28 | 17 | Midfielder |
| 348888 | M. Kömür | 20 | 36 | Midfielder |
| 26 | M. Wolf | 30 | 27 | Midfielder |
| 178093 | Y. Keitel | 25 | 14 | Midfielder |


### FC St. Pauli (`team_id=186`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `28`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 178921 | A. Hountondji | 23 | 27 | Attacker |
| 474789 | Abdoulie Ceesay | 21 | 9 | Attacker |
| 1672 | D. Sinani | 28 | 10 | Attacker |
| 146586 | J. Fujita | 23 | 16 | Attacker |
| 37759 | M. Kaars | 26 | 19 | Attacker |
| 138873 | R. Jones | 23 | 26 | Attacker |
| 344284 | Romeo Aigbekaen | 21 | 38 | Attacker |
| 32871 | T. Hara | 26 | 18 | Attacker |
| 40274 | A. Dźwigała | 30 | 25 | Defender |
| 7649 | D. Nemeth | 24 | 4 | Defender |
| 276263 | F. Stevens | 22 | 14 | Defender |
| 24961 | H. Wahl | 31 | 5 | Defender |
| 384968 | J. Robatsch | 21 | 34 | Defender |
| 48142 | K. Mets | 32 | 3 | Defender |
| 202636 | L. Oppie | 23 | 23 | Defender |
| 90731 | L. Ritzka | 27 | 21 | Defender |
| 307929 | T. Ando | 26 | 15 | Defender |
| 119167 | B. Voll | 25 | 1 | Goalkeeper |
| 363773 | E. Gazdov | 22 | 47 | Goalkeeper |
| 9026 | N. Vasilj | 30 | 22 | Goalkeeper |
| 148448 | A. Pyrka | 23 | 11 | Midfielder |
| 6904 | C. Metcalfe | 26 | 24 | Midfielder |
| 8486 | E. Smith | 28 | 8 | Midfielder |
| 2749 | J. Irvine | 32 | 7 | Midfielder |
| 50863 | J. Sands | 25 | 6 | Midfielder |
| 15917 | M. Rasmussen | 28 | 20 | Midfielder |
| 27157 | M. Saliakas | 29 | 2 | Midfielder |
| 20780 | Mathias Pereira Lage | 29 | 28 | Midfielder |


### FSV Mainz 05 (`team_id=164`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 280339 | A. Sieb | 22 | 11 | Attacker |
| 162946 | B. Hollerbach | 24 | 17 | Attacker |
| 548511 | F. Moreno Fell | 25 | 36 | Attacker |
| 342177 | N. Weiper | 20 | 44 | Attacker |
| 26171 | P. Tietz | 28 | 20 | Attacker |
| 37938 | S. Becker | 30 | 23 | Attacker |
| 20617 | S. Katompa Mvumpa | 27 | 26 | Attacker |
| 199931 | W. Bøving | 22 | 14 | Attacker |
| 22244 | A. Caci | 28 | 19 | Defender |
| 39279 | A. Hanche-Olsen | 28 | 25 | Defender |
| 979 | D. Kohr | 31 | 31 | Defender |
| 1812 | D. da Costa | 32 | 21 | Defender |
| 442546 | K. Potulski | 18 | 48 | Defender |
| 25066 | M. Leitsch | 27 | 5 | Defender |
| 283753 | N. Veratschnig | 22 | 22 | Defender |
| 25907 | S. Bell | 34 | 16 | Defender |
| 711 | S. Posch | 28 | 4 | Defender |
| 90829 | D. Batz | 34 | 33 | Goalkeeper |
| 180553 | L. Rieß | 24 | 1 | Goalkeeper |
| 628381 | Louis Babatz | 19 | 35 | Goalkeeper |
| 25906 | R. Zentner | 31 | 27 | Goalkeeper |
| 621880 | D. Imafidon | 19 | 34 | Midfielder |
| 380603 | Daniel Gleiber | 20 | 42 | Midfielder |
| 33889 | K. Sano | 25 | 6 | Midfielder |
| 24842 | L. Maloney | 26 | 15 | Midfielder |
| 2906 | Lee Jae-Sung | 33 | 7 | Midfielder |
| 714 | N. Amiri | 29 | 10 | Midfielder |
| 25915 | P. Mwene | 31 | 2 | Midfielder |
| 202736 | P. Nebel | 23 | 8 | Midfielder |
| 199897 | S. Kawasaki | 24 | 24 | Midfielder |
| 48378 | S. Widmer | 32 | 30 | Midfielder |


### Hamburger SV (`team_id=175`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 334362 | D. Downs | 21 | 19 | Attacker |
| 380939 | Fabio Amadu Uri Baldé | 20 | 45 | Attacker |
| 41725 | Fábio Vieira | 25 | 20 | Attacker |
| 8483 | J. Dompé | 30 | 7 | Attacker |
| 444962 | Otto Emerson Stange | 18 | 49 | Attacker |
| 73879 | P. Otele | 26 | 27 | Attacker |
| 24914 | R. Glatzel | 31 | 9 | Attacker |
| 162773 | R. Königsdörffer | 24 | 11 | Attacker |
| 129693 | R. Philippe | 25 | 14 | Attacker |
| 1167 | Y. Poulsen | 31 | 15 | Attacker |
| 470282 | Alexander Røssing-Lelesiit | 18 | 38 | Defender |
| 265741 | G. Gocholeishvili | 24 | 16 | Defender |
| 25346 | J. Torunarigha | 28 | 25 | Defender |
| 570798 | L. Lemke | 16 | 37 | Defender |
| 387521 | L. Vušković | 18 | 44 | Defender |
| 48489 | M. Muheim | 27 | 28 | Defender |
| 5973 | N. Capaldo | 27 | 24 | Defender |
| 24792 | N. Katterbach | 24 | 3 | Defender |
| 480452 | S. Nandja | 18 | 43 | Defender |
| 162265 | W. Omari | 25 | 17 | Defender |
| 25033 | Daniel Heuer Fernandes | 33 | 1 | Goalkeeper |
| 380940 | H. Hermann | 20 | 40 | Goalkeeper |
| 264378 | S. Tangvik | 23 | 12 | Goalkeeper |
| 263177 | A. Grønbæk | 24 | 23 | Midfielder |
| 1427 | A. Sambi Lokonga | 26 | 6 | Midfielder |
| 24880 | B. Jatta | 27 | 18 | Midfielder |
| 324019 | Daniel Elfadli | 28 | 8 | Midfielder |
| 260898 | N. Remberg | 25 | 21 | Midfielder |
| 336020 | Omar Megeed | 20 | 39 | Midfielder |
| 302632 | W. Mikelbrencis | 21 | 2 | Midfielder |


### RB Leipzig (`team_id=173`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `27`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 314511 | A. Nusa | 20 | 7 | Attacker |
| 453722 | A. Thomas | 18 | 20 | Attacker |
| 328225 | B. Gruda | 21 | 10 | Attacker |
| 419916 | C. Harder | 20 | 11 | Attacker |
| 343286 | E. Banzuzi | 20 | 6 | Attacker |
| 290549 | J. Bakayoko | 22 | 9 | Attacker |
| 326102 | Rômulo | 23 | 40 | Attacker |
| 570742 | S. Konate | 16 | 45 | Attacker |
| 383665 | T. Gomis | 19 | 27 | Attacker |
| 513776 | Y. Diomande | 19 | 49 | Attacker |
| 98 | B. Henrichs | 28 | 39 | Defender |
| 162761 | C. Lukeba | 23 | 23 | Defender |
| 25158 | D. Raum | 27 | 22 | Defender |
| 268571 | E. Bitshiabu | 20 | 5 | Defender |
| 342320 | K. Nedeljković | 20 | 19 | Defender |
| 1144 | L. Klostermann | 29 | 16 | Defender |
| 355167 | Max Finkgräfe | 21 | 35 | Defender |
| 25917 | R. Baku | 27 | 17 | Defender |
| 1148 | W. Orbán | 33 | 4 | Defender |
| 24814 | L. Zingerle | 31 | 25 | Goalkeeper |
| 1924 | M. Vandevoordt | 23 | 26 | Goalkeeper |
| 1139 | P. Gulácsi | 35 | 1 | Goalkeeper |
| 398192 | A. MaksimoviÄ | 18 | 33 | Midfielder |
| 380978 | A. Ouédraogo | 19 | 20 | Midfielder |
| 715 | C. Baumgartner | 26 | 14 | Midfielder |
| 7328 | N. Seiwald | 24 | 13 | Midfielder |
| 1095 | X. Schlager | 28 | 24 | Midfielder |


### SC Freiburg (`team_id=160`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `26`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 431149 | Cyriaque Kalou Irié | 20 | 22 | Attacker |
| 202696 | I. Matanović | 22 | 31 | Attacker |
| 24 | M. Philipp | 31 | 26 | Attacker |
| 15874 | A. Jung | 34 | 5 | Defender |
| 26236 | C. Günter | 32 | 30 | Defender |
| 361393 | I. Ogbus | 20 | 43 | Defender |
| 25313 | J. Beste | 26 | 19 | Defender |
| 191160 | J. Makengo | 24 | 33 | Defender |
| 574674 | K. Steinmann | 20 | 65 | Defender |
| 26239 | L. Kübler | 33 | 17 | Defender |
| 2915 | M. Ginter | 31 | 28 | Defender |
| 202919 | M. Rosenfelder | 22 | 37 | Defender |
| 26240 | P. Lienhart | 29 | 3 | Defender |
| 178769 | P. Treu | 25 | 29 | Defender |
| 25905 | F. Müller | 28 | 21 | Goalkeeper |
| 25904 | J. Huth | 31 | 24 | Goalkeeper |
| 178768 | N. Atubolu | 23 | 1 | Goalkeeper |
| 286710 | D. Scherhant | 23 | 7 | Midfielder |
| 406244 | J. Manzambi | 20 | 44 | Midfielder |
| 26255 | L. Höler | 31 | 9 | Midfielder |
| 2917 | M. Eggestein | 29 | 8 | Midfielder |
| 26250 | N. Höfler | 35 | 27 | Midfielder |
| 163022 | P. Osterhage | 25 | 6 | Midfielder |
| 584890 | R. Tarnutzer | 18 | 69 | Midfielder |
| 26248 | V. Grifo | 32 | 32 | Midfielder |
| 199143 | Y. Suzuki | 24 | 14 | Midfielder |


### Union Berlin (`team_id=182`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `26`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 45892 | A. Ilić | 25 | 23 | Attacker |
| 440136 | Dmytro Bohdanov | 18 | 30 | Attacker |
| 380873 | Ilyas  Ansah | 21 | 10 | Attacker |
| 655116 | Linus Guther | 16 | 49 | Attacker |
| 430354 | Livan Burcu | 21 | 9 | Attacker |
| 1124 | O. Burke | 28 | 7 | Attacker |
| 413294 | Andrik Markgraf | 19 | 3 | Defender |
| 37117 | D. Doekhi | 27 | 5 | Defender |
| 128853 | D. Köhn | 27 | 39 | Defender |
| 376 | Diogo Leite | 26 | 4 | Defender |
| 14330 | J. Juranović | 30 | 18 | Defender |
| 288206 | L. Querfeld | 22 | 14 | Defender |
| 270 | S. Nsoki | 26 | 34 | Defender |
| 127471 | C. Klaus | 31 | 25 | Goalkeeper |
| 1798 | F. Rønnow | 33 | 1 | Goalkeeper |
| 262815 | M. Raab | 27 | 31 | Goalkeeper |
| 327831 | A. Kemlein | 21 | 6 | Midfielder |
| 1234 | A. Král | 27 | 33 | Midfielder |
| 30785 | A. Schäfer | 26 | 13 | Midfielder |
| 24848 | C. Trimmel | 38 | 28 | Midfielder |
| 327956 | David Preu | 21 | 17 | Midfielder |
| 26249 | J. Haberer | 31 | 19 | Midfielder |
| 512 | Jeong Woo-Yeong | 26 | 11 | Midfielder |
| 25300 | R. Khedira | 31 | 8 | Midfielder |
| 324957 | T. Rothe | 21 | 15 | Midfielder |
| 24910 | T. Skarke | 29 | 21 | Midfielder |


### VfB Stuttgart (`team_id=172`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 334879 | B. Bouanani | 21 | 27 | Attacker |
| 340573 | B. El Khannouss | 21 | 11 | Attacker |
| 26475 | D. Undav | 29 | 26 | Attacker |
| 46930 | E. Demirović | 27 | 9 | Attacker |
| 287927 | J. Diehl | 21 | 26 | Attacker |
| 350799 | Jeremy Arévalo | 20 | 32 | Attacker |
| 265363 | Tiago Tomás | 23 | 8 | Attacker |
| 323449 | A. Al Dakhil | 23 | 2 | Defender |
| 13 | D. Zagadou | 26 | 23 | Defender |
| 394734 | Finn Jeltsch | 19 | 29 | Defender |
| 38112 | J. Chabot | 27 | 24 | Defender |
| 24868 | J. Vagnoman | 25 | 4 | Defender |
| 349344 | L. Jaquez | 22 | 14 | Defender |
| 25342 | M. Mittelstädt | 28 | 7 | Defender |
| 420353 | Maximilian Tobias Herwerth | 19 | 4 | Defender |
| 26244 | P. Stenzel | 29 | 15 | Defender |
| 135883 | R. Hendriks | 24 | 3 | Defender |
| 399 | A. Nübel | 29 | 33 | Goalkeeper |
| 25597 | F. Bredlow | 30 | 1 | Goalkeeper |
| 409750 | Florian Hellstern | 18 | 1 | Goalkeeper |
| 178217 | S. Drljača | 26 | 41 | Goalkeeper |
| 24963 | A. Karazor | 29 | 16 | Midfielder |
| 137210 | A. Stiller | 24 | 6 | Midfielder |
| 24798 | C. Führich | 27 | 10 | Midfielder |
| 400750 | Christopher Olivier | 19 | 24 | Midfielder |
| 128533 | J. Leweling | 24 | 18 | Midfielder |
| 388871 | José María Andrés Baixauli | 20 | 30 | Midfielder |
| 180731 | L. Assignon | 25 | 22 | Midfielder |
| 398194 | L. JovanoviÄ | 19 | 45 | Midfielder |
| 535099 | L. Penna | 19 | 7 | Midfielder |
| 478610 | M. Catovic | 18 | 5 | Midfielder |
| 24806 | N. Nartey | 25 | 28 | Midfielder |
| 535120 | Y. Spalt | 18 | 23 | Midfielder |


### VfL Wolfsburg (`team_id=161`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 362564 | A. Daghim | 20 | 11 | Attacker |
| 584359 | B. Katz | 17 | 42 | Attacker |
| 342188 | D. Pejčinović | 20 | 17 | Attacker |
| 1302 | J. Wind | 26 | 23 | Attacker |
| 422572 | K. Shiogai | 20 | 7 | Attacker |
| 200139 | M. Amoura | 25 | 9 | Attacker |
| 584360 | T. Benedict | 18 | 43 | Attacker |
| 1291 | D. Vavro | 29 | 3 | Defender |
| 369425 | J. Adjetey | 22 | 18 | Defender |
| 343316 | J. Belocian | 20 | 6 | Defender |
| 290545 | J. Seelt | 22 | 14 | Defender |
| 177618 | K. Fischer | 25 | 2 | Defender |
| 162409 | K. Koulierakis | 22 | 4 | Defender |
| 231032 | M. Jenz | 26 | 15 | Defender |
| 334914 | S. Kumbedi | 20 | 26 | Defender |
| 435086 | T. Neininger | 18 | 34 | Defender |
| 15573 | K. Grabara | 26 | 1 | Goalkeeper |
| 1141 | M. Müller | 32 | 29 | Goalkeeper |
| 25396 | P. Pervan | 38 | 12 | Goalkeeper |
| 323951 | A. Zehnter | 21 | 25 | Midfielder |
| 380503 | Bence Dárdai | 19 | 8 | Midfielder |
| 174 | C. Eriksen | 33 | 24 | Midfielder |
| 15884 | J. Lindstrøm | 25 | 19 | Midfielder |
| 1930 | J. Mæhle | 28 | 21 | Midfielder |
| 149557 | K. Paredes | 22 | 40 | Midfielder |
| 1321 | L. Majer | 27 | 10 | Midfielder |
| 25408 | M. Arnold | 31 | 27 | Midfielder |
| 30484 | M. Svanberg | 26 | 32 | Midfielder |
| 585662 | P. Hensel | 18 | 37 | Midfielder |
| 126642 | P. Wimmer | 24 | 39 | Midfielder |
| 10169 | Vinicius Souza | 26 | 5 | Midfielder |
| 25400 | Y. Gerhardt | 31 | 31 | Midfielder |


### Werder Bremen (`team_id=162`)

- Competition: `Bundesliga`
- League ID: `78`
- Season: `2025`
- Country: `Germany`
- National team: `False`
- Players: `28`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 371911 | J. Milošević | 20 | 19 | Attacker |
| 177807 | J. Njinmah | 25 | 11 | Attacker |
| 15592 | J. Stage | 29 | 6 | Attacker |
| 334334 | K. Topp | 21 | 9 | Attacker |
| 7073 | M. Grüll | 27 | 17 | Attacker |
| 7562 | R. Schmid | 25 | 20 | Attacker |
| 346866 | S. Mbangula | 21 | 7 | Attacker |
| 561838 | S. Musah | 20 | 29 | Attacker |
| 39071 | V. Boniface | 25 | 44 | Attacker |
| 25011 | A. Pieper | 27 | 5 | Defender |
| 440147 | Abdoul Karim Coulibaly | 18 | 31 | Defender |
| 26319 | F. Agu | 26 | 27 | Defender |
| 265372 | I. Schmidt | 26 | 23 | Defender |
| 289460 | J. Malatini | 24 | 22 | Defender |
| 25314 | M. Friedl | 27 | 32 | Defender |
| 2048 | M. Wöber | 27 | 39 | Defender |
| 444984 | Mick Schmetgens | 18 | 33 | Defender |
| 2916 | N. Stark | 30 | 4 | Defender |
| 169295 | K. Hein | 23 | 13 | Goalkeeper |
| 329578 | M. Backhaus | 21 | 30 | Goalkeeper |
| 25519 | M. Kolke | 35 | 25 | Goalkeeper |
| 48642 | Cameron Puertas | 27 | 18 | Midfielder |
| 716 | L. Bittencourt | 32 | 10 | Midfielder |
| 8673 | O. Deman | 25 | 2 | Midfielder |
| 448468 | P. Čović | 18 | 24 | Midfielder |
| 38798 | S. Lynen | 26 | 14 | Midfielder |
| 455290 | Wesley Adeh | 18 | 34 | Midfielder |
| 32887 | Y. Sugawara | 25 | 3 | Midfielder |



## Serie A

### AC Milan (`team_id=489`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `27`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 598671 | A. Castiello | 18 | 80 | Attacker |
| 269 | C. Nkunku | 28 | 18 | Attacker |
| 17 | C. Pulišić | 27 | 11 | Attacker |
| 582073 | E. Borsani | 17 | 35 | Attacker |
| 25391 | N. Füllkrug | 32 | 9 | Attacker |
| 22236 | Rafael Leão | 26 | 10 | Attacker |
| 94562 | S. Giménez | 24 | 7 | Attacker |
| 394740 | D. Odogu | 19 | 27 | Defender |
| 19209 | F. Tomori | 28 | 23 | Defender |
| 162141 | K. De Winter | 23 | 5 | Defender |
| 56473 | M. Gabbia | 26 | 46 | Defender |
| 46731 | P. Estupiñán | 27 | 2 | Defender |
| 45826 | S. Pavlović | 24 | 31 | Defender |
| 396380 | Z. Athekame | 21 | 24 | Defender |
| 386298 | L. Torriani | 20 | 96 | Goalkeeper |
| 22221 | M. Maignan | 30 | 16 | Goalkeeper |
| 484293 | M. Pittarella | 17 | 37 | Goalkeeper |
| 30394 | P. Terracciano | 35 | 1 | Goalkeeper |
| 264705 | A. Jashari | 23 | 30 | Midfielder |
| 272 | A. Rabiot | 30 | 12 | Midfielder |
| 1417 | A. Saelemaekers | 26 | 56 | Midfielder |
| 374359 | D. Bartesaghi | 20 | 33 | Midfielder |
| 554588 | E. Sala | 17 | 42 | Midfielder |
| 754 | L. Modrić | 40 | 14 | Midfielder |
| 2292 | R. Loftus-Cheek | 29 | 8 | Midfielder |
| 31056 | S. Ricci | 24 | 4 | Midfielder |
| 22254 | Y. Fofana | 26 | 19 | Midfielder |


### AS Roma (`team_id=497`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 484027 | A. Arena | 16 | 9 | Attacker |
| 15811 | A. Dovbyk | 28 | 9 | Attacker |
| 286639 | Bryan Zaragoza | 24 | 97 | Attacker |
| 249 | D. Malen | 26 | 14 | Attacker |
| 129643 | E. Ferguson | 21 | 11 | Attacker |
| 452033 | L. Venturino | 19 | 20 | Attacker |
| 323936 | M. Soulé | 22 | 18 | Attacker |
| 356888 | N. Pisilli | 21 | 61 | Attacker |
| 875 | P. Dybala | 32 | 21 | Attacker |
| 435482 | R. Vaz | 18 | 78 | Attacker |
| 791 | S. El Shaarawy | 33 | 92 | Attacker |
| 227 | Angeliño | 29 | 3 | Defender |
| 342019 | D. Ghilardi | 22 | 87 | Defender |
| 162452 | D. Rensch | 22 | 2 | Defender |
| 598615 | E. Lulli | 18 | 77 | Defender |
| 1807 | E. Ndicka | 26 | 5 | Defender |
| 30425 | G. Mancini | 29 | 23 | Defender |
| 2669 | Hermoso | 30 | 22 | Defender |
| 384543 | J. Ziółkowski | 20 | 24 | Defender |
| 458411 | Jacopo Mirra | 19 | 76 | Defender |
| 1600 | K. Tsimikas | 29 | 12 | Defender |
| 483676 | G. De Marzi | 18 | 70 | Goalkeeper |
| 556 | M. Svilar | 26 | 99 | Goalkeeper |
| 30418 | P. Gollini | 30 | 95 | Goalkeeper |
| 452423 | R. Żelezny | 19 | 91 | Goalkeeper |
| 778 | B. Cristante | 30 | 4 | Midfielder |
| 782 | L. Pellegrini | 29 | 7 | Midfielder |
| 626686 | M. Bah | 18 | 8 | Midfielder |
| 22147 | M. Koné | 24 | 17 | Midfielder |
| 472080 | Mattia Della Rocca | 19 | 75 | Midfielder |
| 277003 | N. El Aynaoui | 24 | 8 | Midfielder |
| 349001 | Wesley | 22 | 43 | Midfielder |
| 22222 | Z. Çelik | 28 | 19 | Midfielder |


### Atalanta (`team_id=499`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 147859 | C. De Ketelaere | 24 | 17 | Attacker |
| 383017 | D. Vavassori | 20 | 99 | Attacker |
| 443501 | F. Cassa | 19 | 11 | Attacker |
| 30543 | G. Raspadori | 25 | 18 | Attacker |
| 30544 | G. Scamacca | 26 | 9 | Attacker |
| 199837 | K. Sulemana | 23 | 7 | Attacker |
| 66817 | N. Krstović | 25 | 90 | Attacker |
| 30421 | B. Djimsiti | 32 | 19 | Defender |
| 289761 | G. Scalvini | 22 | 42 | Defender |
| 453906 | H. Ahanor | 17 | 69 | Defender |
| 137976 | I. Hien | 26 | 4 | Defender |
| 530 | M. Bakker | 25 | 5 | Defender |
| 48119 | O. Kossounou | 24 | 3 | Defender |
| 436251 | P. Comi | 20 | 6 | Defender |
| 400530 | R. ObriÄ | 19 | 40 | Defender |
| 1442 | S. Kolašinac | 32 | 23 | Defender |
| 30419 | F. Rossi | 34 | 31 | Goalkeeper |
| 30417 | M. Carnesecchi | 25 | 29 | Goalkeeper |
| 31069 | M. Sportiello | 33 | 57 | Goalkeeper |
| 392279 | P. Pardel | 20 | 50 | Goalkeeper |
| 2286 | D. Zappacosta | 33 | 77 | Midfielder |
| 264857 | L. Bernasconi | 22 | 47 | Midfielder |
| 178749 | L. Samardžić | 23 | 10 | Midfielder |
| 2763 | M. Pašalić | 30 | 8 | Midfielder |
| 30432 | M. de Roon | 34 | 15 | Midfielder |
| 203474 | N. Zalewski | 23 | 59 | Midfielder |
| 91422 | R. Bellanova | 25 | 16 | Midfielder |
| 412893 | S. Levak | 19 | 47 | Midfielder |
| 162106 | Y. Musah | 23 | 6 | Midfielder |
| 10097 | Éderson | 26 | 13 | Midfielder |


### Bologna (`team_id=500`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 347265 | B. Domínguez | 22 | 30 | Attacker |
| 873 | F. Bernardeschi | 31 | 10 | Attacker |
| 584426 | F. Castaldo | 18 | 73 | Attacker |
| 30542 | J. Odgaard | 26 | 21 | Attacker |
| 278095 | J. Rowe | 22 | 11 | Attacker |
| 30438 | N. Cambiaghi | 25 | 28 | Attacker |
| 30488 | R. Orsolini | 28 | 7 | Attacker |
| 311067 | S. Castro | 21 | 9 | Attacker |
| 93016 | T. Dallinga | 25 | 24 | Attacker |
| 394947 | B. Tomašević | 19 | 30 | Defender |
| 30553 | C. Lykogiannis | 32 | 22 | Defender |
| 626715 | D. Baroncioni | 20 | 20 | Defender |
| 416062 | E. Helland | 20 | 5 | Defender |
| 1929 | J. Lucumí | 27 | 26 | Defender |
| 30498 | L. De Silvestri | 37 | 29 | Defender |
| 287564 | M. Vitík | 22 | 41 | Defender |
| 31099 | N. Casale | 27 | 16 | Defender |
| 128461 | N. Zortea | 26 | 20 | Defender |
| 616148 | Petar Markovic | 19 | 26 | Defender |
| 39254 | T. Heggem | 26 | 14 | Defender |
| 31098 | F. Ravaglia | 26 | 13 | Goalkeeper |
| 446089 | M. Pessina | 18 | 25 | Goalkeeper |
| 616142 | Matteo Franceschelli | 17 | 82 | Goalkeeper |
| 416518 | U. Happonen | 18 | 1 | Goalkeeper |
| 2998 | Ł. Skorupski | 34 | 1 | Goalkeeper |
| 41734 | João Mário | 25 | 17 | Midfielder |
| 134 | Juan Miranda | 25 | 33 | Midfielder |
| 559263 | K. Badori | 17 | 24 | Midfielder |
| 44814 | L. Ferguson | 26 | 19 | Midfielder |
| 1322 | N. Moro | 27 | 6 | Midfielder |
| 2807 | R. Freuler | 33 | 8 | Midfielder |
| 1014 | S. Sohm | 24 | 23 | Midfielder |
| 31273 | T. Pobega | 26 | 4 | Midfielder |


### Cagliari (`team_id=490`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 30509 | A. Belotti | 32 | 19 | Attacker |
| 31499 | G. Borrelli | 25 | 29 | Attacker |
| 30573 | L. Pavoletti | 37 | 30 | Attacker |
| 626704 | P. Mendy | 19 | 31 | Attacker |
| 215 | S. Esposito | 23 | 94 | Attacker |
| 336567 | S. Kılıçsoy | 20 | 9 | Attacker |
| 584116 | Y. Trepy | 19 | 37 | Attacker |
| 32034 | A. Dossena | 27 | 22 | Defender |
| 321744 | A. Obert | 23 | 33 | Defender |
| 438208 | Andra Cogoni | 19 | 13 | Defender |
| 200 | G. Zappa | 26 | 28 | Defender |
| 415155 | J. Rodríguez | 20 | 15 | Defender |
| 30505 | M. Adopo | 25 | 8 | Defender |
| 383018 | M. Palestra | 20 | 2 | Defender |
| 419627 | O. Raterink | 19 | 18 | Defender |
| 383026 | Riyad Idrissi | 20 | 3 | Defender |
| 2484 | Y. Mina | 31 | 26 | Defender |
| 41964 | Zé Pedro | 28 | 32 | Defender |
| 3737 | A. Sherri | 28 | 12 | Goalkeeper |
| 30731 | E. Caprile | 24 | 1 | Goalkeeper |
| 135863 | G. Ciocci | 23 | 24 | Goalkeeper |
| 485289 | V. Sarno | 17 | 34 | Goalkeeper |
| 404523 | A. Albarracín | 20 | 20 | Midfielder |
| 30561 | A. Deiola | 30 | 14 | Midfielder |
| 325 | G. Gaetano | 25 | 10 | Midfielder |
| 353609 | I. Sulemana | 22 | 25 | Midfielder |
| 341307 | Ivan Stoyanov Sulev | 19 | 38 | Midfielder |
| 417892 | J. Liteta | 19 | 27 | Midfielder |
| 30780 | L. Mazzitelli | 30 | 4 | Midfielder |
| 31734 | M. Felici | 24 | 17 | Midfielder |
| 56851 | M. Folorunsho | 27 | 90 | Midfielder |
| 468711 | N. Grandu | 19 | 36 | Midfielder |
| 626674 | R. Malfitano | 18 | 40 | Midfielder |


### Como (`team_id=895`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `28`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 354533 | J. Addai | 20 | 42 | Attacker |
| 443162 | Jesús Rodríguez | 20 | 17 | Attacker |
| 38753 | N. Kühn | 25 | 19 | Attacker |
| 26845 | T. Douvikas | 26 | 11 | Attacker |
| 59 | Álvaro Morata | 33 | 7 | Attacker |
| 288 | Alberto Moreno | 33 | 18 | Defender |
| 506554 | C. De Paoli | 17 | 56 | Defender |
| 21090 | Diego Carlos | 32 | 34 | Defender |
| 31073 | E. Goldaniga | 32 | 5 | Defender |
| 14266 | I. Smolčić | 25 | 28 | Defender |
| 129119 | I. Van der Brempt | 23 | 77 | Defender |
| 386305 | Jacobo Ramón Naveros | 20 | 14 | Defender |
| 26301 | M. Kempf | 30 | 2 | Defender |
| 8586 | M. Vojvoda | 30 | 31 | Defender |
| 336560 | Álex Valle | 21 | 3 | Defender |
| 8574 | J. Butez | 30 | 1 | Goalkeeper |
| 31719 | M. Vigorito | 35 | 22 | Goalkeeper |
| 193328 | N. Törnqvist | 23 | 21 | Goalkeeper |
| 207804 | N. Čavlina | 23 | 44 | Goalkeeper |
| 459029 | A. Lahdo | 18 | 15 | Midfielder |
| 400948 | Assane Diao | 20 | 38 | Midfielder |
| 162266 | L. da Cunha | 24 | 33 | Midfielder |
| 295026 | M. Baturina | 22 | 20 | Midfielder |
| 659 | M. Caqueret | 25 | 6 | Midfielder |
| 288699 | M. Perrone | 22 | 23 | Midfielder |
| 350037 | N. Paz | 21 | 10 | Midfielder |
| 567667 | S. Pisati | 16 | 58 | Midfielder |
| 137 | Sergi Roberto | 33 | 8 | Midfielder |


### Cremonese (`team_id=520`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 556945 | A. Lickunas | 19 | 15 | Attacker |
| 2522 | A. Sanabria | 29 | 99 | Attacker |
| 31219 | A. Zerbin | 26 | 7 | Attacker |
| 31436 | F. Bonazzoli | 28 | 90 | Attacker |
| 102447 | F. Moumbagna | 25 | 14 | Attacker |
| 18788 | J. Vardy | 38 | 10 | Attacker |
| 6383 | M. Payero | 27 | 32 | Attacker |
| 31692 | M. Đurić | 35 | 9 | Attacker |
| 616187 | Nouroudine Faye | 18 | 17 | Attacker |
| 492934 | D. Pavesi | 17 | 25 | Defender |
| 127035 | F. Baschirotto | 29 | 6 | Defender |
| 30397 | F. Ceccherini | 33 | 23 | Defender |
| 385788 | F. Folino | 23 | 55 | Defender |
| 264472 | F. Terracciano | 22 | 24 | Defender |
| 30775 | G. Pezzella | 28 | 3 | Defender |
| 30919 | M. Bianchetti | 32 | 15 | Defender |
| 237249 | M. Faye | 21 | 30 | Defender |
| 319 | S. Luperto | 29 | 5 | Defender |
| 126980 | T. Barbieri | 23 | 4 | Defender |
| 30441 | E. Audero | 28 | 1 | Goalkeeper |
| 342995 | L. Nava | 21 | 69 | Goalkeeper |
| 30915 | M. Silvestri | 34 | 16 | Goalkeeper |
| 31021 | A. Grassi | 30 | 33 | Midfielder |
| 30848 | D. Okereke | 28 | 77 | Midfielder |
| 31211 | J. Vandeputte | 29 | 27 | Midfielder |
| 126889 | M. Collocolo | 26 | 18 | Midfielder |
| 36980 | M. Thorsby | 29 | 2 | Midfielder |
| 342651 | R. Floriani Mussolini | 22 | 22 | Midfielder |
| 616178 | Simone Lottici Tessadri | 19 | 21 | Midfielder |
| 266813 | W. Bondo | 22 | 38 | Midfielder |
| 56560 | Y. Maleh | 27 | 29 | Midfielder |


### Fiorentina (`team_id=502`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 2799 | A. Guðmundsson | 28 | 10 | Attacker |
| 610726 | G. Bertolini | 19 | 7 | Attacker |
| 579241 | G. Puzzoli | 19 | 69 | Attacker |
| 19128 | J. Harrison | 29 | 17 | Attacker |
| 877 | M. Kean | 25 | 20 | Attacker |
| 697 | M. Solomon | 26 | 19 | Attacker |
| 437094 | R. Braschi | 19 | 61 | Attacker |
| 30440 | R. Piccoli | 24 | 91 | Attacker |
| 861 | D. Rugani | 31 | 3 | Defender |
| 41144 | Dodô | 27 | 2 | Defender |
| 448977 | E. Kouadio | 19 | 60 | Defender |
| 441290 | E. Košpo | 18 | 23 | Defender |
| 610778 | E. Sadotti | 19 | 5 | Defender |
| 136087 | F. Parisi | 25 | 65 | Defender |
| 575285 | L. Balbo | 19 | 62 | Defender |
| 31642 | L. Ranieri | 26 | 6 | Defender |
| 1084 | M. Pongračić | 28 | 5 | Defender |
| 437093 | N. Fortini | 19 | 29 | Defender |
| 396637 | P. Comuzzo | 20 | 15 | Defender |
| 882 | David de Gea | 35 | 43 | Goalkeeper |
| 31352 | L. Lezzerini | 30 | 1 | Goalkeeper |
| 642211 | Mattia Magalotti | 17 | 51 | Goalkeeper |
| 15843 | O. Christensen | 26 | 53 | Goalkeeper |
| 458413 | P. Leonardelli | 19 | 50 | Goalkeeper |
| 311083 | C. Ndour | 21 | 27 | Midfielder |
| 322630 | G. Fabbian | 22 | 80 | Midfielder |
| 340700 | J. Fazzini | 22 | 22 | Midfielder |
| 626661 | L. Deli | 19 | 64 | Midfielder |
| 1639 | M. Brescianini | 25 | 4 | Midfielder |
| 876 | N. Fagioli | 24 | 44 | Midfielder |
| 610724 | P. Bonanno | 18 | 4 | Midfielder |
| 30422 | R. Gosens | 31 | 21 | Midfielder |
| 30810 | R. Mandragora | 28 | 8 | Midfielder |


### Genoa (`team_id=495`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `38`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 3430 | C. Ekuban | 31 | 18 | Attacker |
| 616228 | Daniel Ndulue | 18 | 78 | Attacker |
| 451504 | J. Ekhator | 19 | 21 | Attacker |
| 592741 | Joi Nuredini | 18 | 86 | Attacker |
| 56396 | Junior Messias | 34 | 10 | Attacker |
| 263481 | L. Colombo | 23 | 29 | Attacker |
| 665 | M. Cornet | 29 | 70 | Attacker |
| 281408 | Vítinha | 25 | 9 | Attacker |
| 570213 | A. Kumer Celik | 18 | 42 | Defender |
| 281826 | A. Marcandalli | 23 | 27 | Defender |
| 25914 | Aarón Martín | 28 | 3 | Defender |
| 284570 | B. Norton-Cuffy | 21 | 15 | Defender |
| 616219 | Klisys | 18 | 40 | Defender |
| 616217 | Kris Gecaj | 16 | 76 | Defender |
| 18967 | L. Østigård | 26 | 5 | Defender |
| 616216 | Mamedi Doucoure | 18 | 74 | Defender |
| 644542 | Mamedi Doucoure | 19 | 74 | Defender |
| 443779 | N. Zätterström | 20 | 13 | Defender |
| 387128 | S. Otoa | 21 | 34 | Defender |
| 636538 | W. L. Ouedraogo | 18 | 99 | Defender |
| 45083 | B. Siegrist | 33 | 31 | Goalkeeper |
| 31445 | D. Sommariva | 28 | 39 | Goalkeeper |
| 395788 | E. Lysionok | 18 | 35 | Goalkeeper |
| 37137 | J. Bijlow | 27 | 16 | Goalkeeper |
| 31631 | N. Leali | 32 | 1 | Goalkeeper |
| 605470 | Rendijs Mihelsons | 17 | 32 | Goalkeeper |
| 405239 | Alexsandro Amorim | 20 | 4 | Midfielder |
| 393926 | Gaël Lafont | 19 | 75 | Midfielder |
| 41748 | J. Onana | 26 | 14 | Midfielder |
| 35544 | J. Vásquez | 27 | 22 | Midfielder |
| 616225 | Jacopo Grossi | 19 | 80 | Midfielder |
| 639655 | K. Meola | 19 | 20 | Midfielder |
| 89520 | M. Ellertsson | 23 | 77 | Midfielder |
| 15881 | M. Frendrup | 24 | 32 | Midfielder |
| 281096 | P. Masini | 24 | 73 | Midfielder |
| 1938 | R. Malinovskyi | 32 | 17 | Midfielder |
| 31137 | S. Sabelli | 32 | 20 | Midfielder |
| 288769 | T. Baldanzi | 22 | 8 | Midfielder |


### Hellas Verona (`team_id=504`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 236955 | A. Sarr | 24 | 9 | Attacker |
| 59421 | D. Mosquera | 26 | 25 | Attacker |
| 368260 | G. Orban | 23 | 16 | Attacker |
| 352940 | Ioan Vermeșan | 19 | 90 | Attacker |
| 414281 | Isaac | 21 | 41 | Attacker |
| 408634 | J. Ajayi | 21 | 72 | Attacker |
| 126690 | K. Bowie | 23 | 18 | Attacker |
| 340076 | L. Monticelli | 20 | 20 | Attacker |
| 194837 | T. Suslov | 23 | 10 | Attacker |
| 25061 | A. Bella-Kotchap | 24 | 37 | Defender |
| 169297 | A. Edmundsson | 25 | 5 | Defender |
| 14327 | D. Bradarić | 26 | 12 | Defender |
| 418846 | D. De Battisti | 19 | 71 | Defender |
| 153408 | D. Oyegoke | 22 | 2 | Defender |
| 527889 | Fallou Cham | 19 | 70 | Defender |
| 311071 | N. Valentini | 24 | 6 | Defender |
| 30525 | Pol Lirola | 28 | 14 | Defender |
| 368129 | T. Slotsager | 19 | 19 | Defender |
| 15912 | V. Nelsson | 27 | 15 | Defender |
| 350539 | G. Toniolo | 21 | 94 | Goalkeeper |
| 30611 | L. Montipò | 29 | 1 | Goalkeeper |
| 546632 | Mirko Castagnini | 18 | 76 | Goalkeeper |
| 31383 | S. Perilli | 30 | 34 | Goalkeeper |
| 1090 | A. Bernede | 26 | 24 | Midfielder |
| 37437 | A. Harroui | 27 | 21 | Midfielder |
| 42006 | Al Musrati | 29 | 73 | Midfielder |
| 22239 | C. Niasse | 25 | 36 | Midfielder |
| 31678 | J. Akpa Akpro | 33 | 11 | Midfielder |
| 626701 | J. Peci | 19 | 79 | Midfielder |
| 576967 | L. Szimionas | 19 | 8 | Midfielder |
| 15909 | M. Frese | 27 | 3 | Midfielder |
| 303362 | R. Belghali | 23 | 7 | Midfielder |
| 203 | R. Gagliardini | 31 | 63 | Midfielder |
| 7591 | S. Lovrić | 27 | 4 | Midfielder |
| 418 | S. Serdar | 28 | 8 | Midfielder |


### Inter (`team_id=505`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `39`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 275651 | A. Bonny | 22 | 14 | Attacker |
| 345808 | F. Esposito | 20 | 94 | Attacker |
| 217 | Lautaro Martínez | 28 | 10 | Attacker |
| 10077 | Luis Henrique | 24 | 11 | Attacker |
| 461830 | M. Lavelli | 19 | 90 | Attacker |
| 437678 | M. Mosconi | 18 | 48 | Attacker |
| 436238 | M. Spinaccè | 19 | 7 | Attacker |
| 21509 | M. Thuram | 28 | 9 | Attacker |
| 31009 | A. Bastoni | 26 | 95 | Defender |
| 343345 | C. Alexiou | 20 | 5 | Defender |
| 10238 | Carlos Augusto | 26 | 30 | Defender |
| 226 | D. Dumfries | 29 | 2 | Defender |
| 1836 | F. Acerbi | 37 | 15 | Defender |
| 558546 | I. Amerighi | 20 | 77 | Defender |
| 5 | M. Akanji | 30 | 25 | Defender |
| 392493 | M. Cocchi | 18 | 43 | Defender |
| 563846 | S. Cinquegrano | 21 | 46 | Defender |
| 194 | S. de Vrij | 33 | 6 | Defender |
| 24953 | Y. Bisseck | 25 | 31 | Defender |
| 563858 | Y. Maye | 19 | 6 | Defender |
| 336707 | A. Calligaris | 20 | 91 | Goalkeeper |
| 449683 | A. Taho | 18 | 1 | Goalkeeper |
| 46988 | Josep Martínez | 27 | 13 | Goalkeeper |
| 91488 | R. Di Gennaro | 32 | 12 | Goalkeeper |
| 2802 | Y. Sommer | 37 | 1 | Goalkeeper |
| 270509 | A. Diouf | 22 | 17 | Midfielder |
| 31173 | D. Frattesi | 26 | 16 | Midfielder |
| 31010 | F. Dimarco | 28 | 32 | Midfielder |
| 1457 | H. Mkhitaryan | 36 | 22 | Midfielder |
| 1640 | H. Çalhanoğlu | 31 | 20 | Midfielder |
| 383000 | I. Kamate | 21 | 10 | Midfielder |
| 161831 | Iwo Kaczmarski | 21 | 37 | Midfielder |
| 562597 | L. Bovo | 20 | 14 | Midfielder |
| 367878 | L. Topalović | 19 | 9 | Midfielder |
| 887 | M. Darmian | 36 | 36 | Midfielder |
| 30558 | N. Barella | 28 | 23 | Midfielder |
| 348205 | P. Sučić | 22 | 8 | Midfielder |
| 329 | P. Zieliński | 31 | 7 | Midfielder |
| 395849 | Thomas Berenbruch | 20 | 44 | Midfielder |


### Juventus (`team_id=496`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `34`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 333 | A. Milik | 31 | 14 | Attacker |
| 30415 | D. Vlahović | 25 | 9 | Attacker |
| 48392 | E. Zhegrova | 26 | 11 | Attacker |
| 161585 | Francisco Conceição | 23 | 7 | Attacker |
| 30531 | J. Boga | 28 | 13 | Attacker |
| 8489 | J. David | 25 | 30 | Attacker |
| 339883 | K. Yıldız | 20 | 10 | Attacker |
| 349218 | L. Anghelè | 20 | 10 | Attacker |
| 86 | L. Openda | 25 | 20 | Attacker |
| 30497 | Bremer | 28 | 3 | Defender |
| 47985 | E. Holm | 25 | 2 | Defender |
| 268341 | F. Gatti | 27 | 4 | Defender |
| 585519 | G. Mulazzi | 22 | 6 | Defender |
| 125674 | J. Cabal | 24 | 32 | Defender |
| 436925 | Javier Gil | 19 | 3 | Defender |
| 19263 | L. Kelly | 27 | 6 | Defender |
| 405298 | N. Rizzo | 18 | 13 | Defender |
| 162188 | P. Kalulu | 25 | 15 | Defender |
| 850 | C. Pinsoglio | 35 | 23 | Goalkeeper |
| 30670 | M. Di Gregorio | 28 | 16 | Goalkeeper |
| 408319 | M. Fuscaldo | 20 | 29 | Goalkeeper |
| 849 | M. Perin | 33 | 1 | Goalkeeper |
| 620060 | R. Huli | 17 | 37 | Goalkeeper |
| 597936 | R. Radu | 18 | 40 | Goalkeeper |
| 476231 | S. Mangiapoco | 21 | 22 | Goalkeeper |
| 335099 | S. Scaglia | 21 | 42 | Goalkeeper |
| 127011 | A. Cambiaso | 25 | 27 | Midfielder |
| 1821 | F. Kostić | 33 | 18 | Midfielder |
| 181808 | F. Miretti | 22 | 21 | Midfielder |
| 116 | K. Thuram | 24 | 19 | Midfielder |
| 30533 | M. Locatelli | 27 | 5 | Midfielder |
| 36899 | T. Koopmeiners | 27 | 8 | Midfielder |
| 339872 | Vasilije Adžić | 19 | 17 | Midfielder |
| 415 | W. McKennie | 27 | 22 | Midfielder |


### Lazio (`team_id=487`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 22015 | B. Dia | 29 | 19 | Attacker |
| 134926 | D. Maldini | 24 | 27 | Attacker |
| 436244 | F. Serra | 19 | 17 | Attacker |
| 135519 | G. Isaksen | 24 | 18 | Attacker |
| 286474 | M. Cancellieri | 23 | 22 | Attacker |
| 30937 | M. Zaccagni | 30 | 10 | Attacker |
| 301763 | P. Ratkov | 22 | 20 | Attacker |
| 2299 | Pedro | 38 | 9 | Attacker |
| 436193 | S. Fernandes | 19 | 77 | Attacker |
| 133729 | T. Noslin | 26 | 14 | Attacker |
| 1844 | A. Marušić | 33 | 77 | Defender |
| 1632 | A. Romagnoli | 30 | 13 | Defender |
| 317 | E. Hysaj | 31 | 23 | Defender |
| 30554 | L. Pellegrini | 26 | 3 | Defender |
| 30866 | M. Lazzari | 32 | 29 | Defender |
| 162952 | Mario Gila | 25 | 34 | Defender |
| 41577 | Nuno Tavares | 25 | 17 | Defender |
| 350857 | O. Provstgaard | 22 | 25 | Defender |
| 63934 | A. Furlanetto | 23 | 55 | Goalkeeper |
| 431413 | E. Motta | 20 | 40 | Goalkeeper |
| 616196 | Giacomo Giacomone | 17 | 99 | Goalkeeper |
| 31037 | I. Provedel | 31 | 94 | Goalkeeper |
| 616197 | Nicolo Pannozzo | 17 | 72 | Goalkeeper |
| 405241 | A. Przyborek | 18 | 28 | Midfielder |
| 1852 | D. Cataldi | 31 | 32 | Midfielder |
| 144740 | F. Dele-Bashiru | 24 | 7 | Midfielder |
| 38749 | K. Taylor | 23 | 24 | Midfielder |
| 30784 | N. Rovella | 24 | 6 | Midfielder |
| 1841 | Patric | 32 | 4 | Midfielder |
| 333116 | R. Belahyane | 21 | 21 | Midfielder |
| 1266 | T. Bašić | 29 | 26 | Midfielder |
| 483662 | V. Farcomeni | 19 | 18 | Midfielder |


### Lecce (`team_id=867`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 497079 | Bertram Skovgaard | 18 | 39 | Attacker |
| 436260 | F. Camarda | 17 | 22 | Attacker |
| 8643 | K. N’Dri | 25 | 11 | Attacker |
| 264122 | N. Štulić | 24 | 9 | Attacker |
| 31507 | R. Sottil | 26 | 23 | Attacker |
| 128478 | W. Cheddira | 27 | 99 | Attacker |
| 31543 | A. Gallo | 25 | 25 | Defender |
| 19738 | C. Ndaba | 26 | 3 | Defender |
| 161702 | Danilo Veiga | 23 | 17 | Defender |
| 23253 | G. Jean | 25 | 18 | Defender |
| 203219 | J. Siebert | 23 | 5 | Defender |
| 291589 | Kialonda Gaspar | 28 | 4 | Defender |
| 458543 | M. Pérez | 20 | 13 | Defender |
| 280431 | S. Fofana | 22 | 8 | Defender |
| 455316 | Tiago Gabriel | 21 | 44 | Defender |
| 495 | C. Früchtl | 25 | 1 | Goalkeeper |
| 628513 | Daniele Bleve | 17 | 95 | Goalkeeper |
| 156619 | J. Samooja | 22 | 32 | Goalkeeper |
| 446138 | P. Penev | 17 | 1 | Goalkeeper |
| 56459 | W. Falcone | 30 | 30 | Goalkeeper |
| 40563 | F. Marchwiński | 23 | 36 | Midfielder |
| 118956 | L. Banda | 24 | 19 | Midfielder |
| 1748 | L. Coulibaly | 29 | 29 | Midfielder |
| 335071 | M. Berisha | 22 | 10 | Midfielder |
| 340179 | N. Kovač  | 20 | 80 | Midfielder |
| 126974 | O. Gandelman | 25 | 16 | Midfielder |
| 334925 | O. Ngom | 21 | 79 | Midfielder |
| 387537 | Olaf Gorter | 20 | 28 | Midfielder |
| 6662 | S. Pierotti | 24 | 50 | Midfielder |
| 15673 | Y. Ramadani | 29 | 20 | Midfielder |
| 181218 | Álex Sala | 24 | 6 | Midfielder |
| 28744 | Þ. Helgason | 25 | 14 | Midfielder |


### Napoli (`team_id=492`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 310943 | Alisson Santos | 23 | 27 | Attacker |
| 552 | David Neres | 28 | 7 | Attacker |
| 312615 | Giovane | 22 | 23 | Attacker |
| 629 | K. De Bruyne | 34 | 11 | Attacker |
| 288006 | R. Højlund | 22 | 19 | Attacker |
| 907 | R. Lukaku | 32 | 9 | Attacker |
| 31226 | A. Buongiorno | 26 | 4 | Defender |
| 1314 | Amir Rrahmani | 31 | 13 | Defender |
| 561812 | C. Garofalo | 18 | 6 | Defender |
| 31042 | G. Di Lorenzo | 32 | 22 | Defender |
| 774 | Juan Jesus | 34 | 5 | Defender |
| 862 | L. Spinazzola | 32 | 37 | Defender |
| 47254 | M. Olivera | 28 | 17 | Defender |
| 31390 | P. Mazzocchi | 30 | 30 | Defender |
| 37604 | S. Beukema | 27 | 31 | Defender |
| 312 | A. Meret | 28 | 1 | Goalkeeper |
| 355007 | A. Yazıcı | 21 | 22 | Goalkeeper |
| 568115 | D. Spinelli | 17 | 95 | Goalkeeper |
| 32172 | N. Contini | 29 | 14 | Goalkeeper |
| 31156 | V. Milinković-Savić | 28 | 32 | Goalkeeper |
| 347395 | A. Vergara | 22 | 26 | Midfielder |
| 3406 | A. Zambo Anguissa | 30 | 99 | Midfielder |
| 130423 | B. Gilmour | 24 | 6 | Midfielder |
| 579072 | E. De Chiara | 19 | 8 | Midfielder |
| 1358 | E. Elmas | 26 | 20 | Midfielder |
| 579077 | F. Barido | 17 | 60 | Midfielder |
| 219 | M. Politano | 32 | 21 | Midfielder |
| 162032 | Miguel Gutiérrez | 24 | 3 | Midfielder |
| 47439 | S. Lobotka | 31 | 68 | Midfielder |
| 903 | S. McTominay | 29 | 8 | Midfielder |
| 561707 | V. Prisco | 17 | 14 | Midfielder |


### Parma (`team_id=523`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `34`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 595822 | Alessandro Cardinali | 19 | 11 | Attacker |
| 394882 | D. Mikołajewski | 19 | 76 | Attacker |
| 31624 | Gabriel Strefezza | 28 | 7 | Attacker |
| 191979 | J. Ondrejka | 23 | 17 | Attacker |
| 292172 | Mateo Pellegrino | 24 | 9 | Attacker |
| 301924 | N. Elphege | 24 | 23 | Attacker |
| 48193 | P. Almqvist | 26 | 11 | Attacker |
| 348568 | A. Circati | 22 | 39 | Defender |
| 203483 | A. N&apos;Diaye | 23 | 3 | Defender |
| 595810 | Bernardo Conde | 19 | 70 | Defender |
| 576948 | D. Drobnic | 18 | 17 | Defender |
| 286473 | F. Carboni | 22 | 29 | Defender |
| 6221 | L. Valenti | 26 | 5 | Defender |
| 575272 | M. Mena | 19 | 63 | Defender |
| 428237 | M. Troilo | 22 | 37 | Defender |
| 499380 | S. Britschgi | 19 | 27 | Defender |
| 180762 | E. Corvi | 24 | 40 | Goalkeeper |
| 237268 | F. Rinaldi | 23 | 66 | Goalkeeper |
| 595808 | Gabriele Casentini | 18 | 16 | Goalkeeper |
| 199578 | Z. Suzuki | 23 | 31 | Goalkeeper |
| 462188 | A. Ciardi | 18 | 19 | Midfielder |
| 595817 | Abdou Konate | 18 | 47 | Midfielder |
| 628 | Adrián Bernabé | 24 | 10 | Midfielder |
| 362061 | B. Cremaschi | 20 | 25 | Midfielder |
| 362752 | C. Ordoñez | 21 | 24 | Midfielder |
| 30420 | E. Del Prato | 26 | 15 | Midfielder |
| 446006 | E. Plicco | 18 | 14 | Midfielder |
| 91358 | E. Valeri | 27 | 14 | Midfielder |
| 595819 | Edoardo Tigani | 19 | 8 | Midfielder |
| 161859 | G. Oristanio | 23 | 21 | Midfielder |
| 881 | H. Nicolussi | 25 | 41 | Midfielder |
| 308836 | M. Keita | 23 | 16 | Midfielder |
| 6409 | N. Estévez | 30 | 8 | Midfielder |
| 161569 | O. Sørensen | 23 | 22 | Midfielder |


### Pisa (`team_id=801`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 123476 | F. Stojilković | 25 | 81 | Attacker |
| 331678 | H. Meister | 22 | 9 | Attacker |
| 341226 | R. Durosinmi | 22 | 17 | Attacker |
| 162173 | S. Iling-Junior | 22 | 19 | Attacker |
| 31560 | S. Moreo | 32 | 32 | Attacker |
| 30469 | A. Calabresi | 29 | 33 | Defender |
| 31604 | A. Caracciolo | 35 | 4 | Defender |
| 485960 | D. Denoon | 21 | 44 | Defender |
| 419603 | F. Coppola | 20 | 26 | Defender |
| 298165 | F. Loyola | 25 | 35 | Defender |
| 342310 | R. Bozhinov | 20 | 2 | Defender |
| 314 | Raúl Albiol | 40 | 39 | Defender |
| 91503 | S. Canestrelli | 25 | 5 | Defender |
| 30733 | A. Šemper | 27 | 1 | Goalkeeper |
| 640703 | Matteo Luppichini |  | 31 | Goalkeeper |
| 30792 | Nícolas | 37 | 12 | Goalkeeper |
| 50054 | S. Scuffet | 29 | 22 | Goalkeeper |
| 635992 | Tommaso Guizzo |  | 34 | Goalkeeper |
| 545975 | B. Bettazzi | 17 | 42 | Midfielder |
| 36910 | C. Stengs | 27 | 23 | Midfielder |
| 408635 | E. Akinsanmiro | 21 | 14 | Midfielder |
| 325387 | G. Piccinini | 24 | 36 | Midfielder |
| 56293 | I. Touré | 27 | 15 | Midfielder |
| 866 | J. Cuadrado | 37 | 11 | Midfielder |
| 403300 | Lorran | 19 | 99 | Midfielder |
| 951 | M. Aebischer | 28 | 20 | Midfielder |
| 15723 | M. Højholt | 24 | 8 | Midfielder |
| 30753 | M. Léris | 27 | 7 | Midfielder |
| 30723 | M. Marin | 27 | 6 | Midfielder |
| 20959 | M. Tramoni | 25 | 10 | Midfielder |
| 302069 | S. Angori | 22 | 3 | Midfielder |
| 364600 | İ. Vural | 19 | 21 | Midfielder |


### Sassuolo (`team_id=488`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 263699 | A. Fadera | 24 | 20 | Attacker |
| 2215 | A. Laurienté | 27 | 45 | Attacker |
| 31094 | A. Pinamonti | 26 | 99 | Attacker |
| 342035 | C. Volpato | 22 | 7 | Attacker |
| 30537 | D. Berardi | 31 | 10 | Attacker |
| 31440 | L. Moro | 24 | 24 | Attacker |
| 31318 | M&apos;Bala Nzola | 29 | 8 | Attacker |
| 30556 | F. Romagna | 28 | 19 | Defender |
| 41371 | Fali Candé | 27 | 5 | Defender |
| 135526 | J. Doig | 23 | 3 | Defender |
| 37651 | J. Idzes | 25 | 21 | Defender |
| 626695 | L. Barani | 19 | 76 | Defender |
| 415064 | Pedro Felipe | 21 | 66 | Defender |
| 40582 | S. Walukiewicz | 25 | 6 | Defender |
| 613352 | T. Macchioni | 19 | 4 | Defender |
| 271350 | T. Muharemović | 22 | 80 | Defender |
| 943 | U. Garcia | 29 | 23 | Defender |
| 128338 | W. Coulibaly | 26 | 25 | Defender |
| 616 | A. Murić | 27 | 49 | Goalkeeper |
| 30518 | G. Satalino | 26 | 12 | Goalkeeper |
| 292519 | G. Zacchi | 22 | 16 | Goalkeeper |
| 613213 | L. Nyarko | 18 | 80 | Goalkeeper |
| 30519 | S. Turati | 24 | 13 | Goalkeeper |
| 127413 | A. Vranckx | 23 | 40 | Midfielder |
| 584501 | C. Frangella | 19 | 33 | Midfielder |
| 455245 | D. Bakola | 18 | 50 | Midfielder |
| 291780 | D. Boloca | 27 | 11 | Midfielder |
| 281291 | E. Iannoni | 24 | 44 | Midfielder |
| 328046 | I. Koné | 23 | 90 | Midfielder |
| 39143 | K. Thorstvedt | 26 | 42 | Midfielder |
| 343562 | L. Lipani | 20 | 35 | Midfielder |
| 902 | N. Matić | 37 | 18 | Midfielder |


### Torino (`team_id=503`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 383006 | A. Njie | 20 | 92 | Attacker |
| 19524 | C. Adams | 29 | 19 | Attacker |
| 2495 | D. Zapata | 34 | 91 | Attacker |
| 30414 | G. Simeone | 30 | 18 | Attacker |
| 842 | N. Vlašić | 28 | 10 | Attacker |
| 40405 | S. Kulenović | 26 | 17 | Attacker |
| 437088 | T. Gabellini | 19 | 9 | Attacker |
| 243 | Z. Aboukhlal | 25 | 7 | Attacker |
| 14329 | A. Ismajli | 29 | 44 | Defender |
| 30396 | C. Biraghi | 33 | 34 | Defender |
| 20656 | E. Ebosse | 26 | 77 | Defender |
| 2553 | G. Maripán | 31 | 13 | Defender |
| 388547 | Luca Marianucci | 21 | 35 | Defender |
| 39362 | M. Pedersen | 25 | 16 | Defender |
| 598593 | M. Pellini | 18 | 2 | Defender |
| 156490 | N. Nkounkou | 25 | 25 | Defender |
| 268728 | S. Sazonov | 23 | 15 | Defender |
| 122468 | Saúl Coco | 26 | 23 | Defender |
| 30642 | A. Paleari | 33 | 1 | Goalkeeper |
| 56266 | F. Israel | 25 | 81 | Goalkeeper |
| 565709 | L. Siviero | 18 | 99 | Goalkeeper |
| 22174 | A. Tamèze | 31 | 61 | Midfielder |
| 270507 | C. Casadei | 22 | 22 | Midfielder |
| 336573 | E. İlkhan | 21 | 6 | Midfielder |
| 138777 | F. Anjorin | 24 | 14 | Midfielder |
| 343189 | G. Gineitis | 21 | 66 | Midfielder |
| 46170 | I. Ilić | 24 | 8 | Midfielder |
| 309388 | M. Prati | 22 | 4 | Midfielder |
| 265722 | Rafael Obrador | 21 | 33 | Midfielder |
| 452430 | S. Perciun | 19 | 10 | Midfielder |
| 25353 | V. Lazaro | 29 | 20 | Midfielder |
| 613435 | W. Acquah | 18 | 32 | Midfielder |


### Udinese (`team_id=494`)

- Competition: `Serie A`
- League ID: `135`
- Season: `2025`
- Country: `Italy`
- National team: `False`
- Players: `26`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 40594 | A. Buksa | 29 | 18 | Attacker |
| 434410 | I. Gueye | 19 | 7 | Attacker |
| 541 | J. Ekkelenkamp | 25 | 32 | Attacker |
| 19185 | K. Davis | 27 | 9 | Attacker |
| 786 | N. Zaniolo | 26 | 10 | Attacker |
| 1134 | V. Bayo | 28 | 15 | Attacker |
| 162907 | A. Zanoli | 25 | 59 | Defender |
| 507646 | Branimir Mlačić | 19 | 22 | Defender |
| 18797 | C. Kabasele | 34 | 27 | Defender |
| 19824 | J. Zemura | 26 | 33 | Defender |
| 315249 | N. Bertola | 22 | 13 | Defender |
| 656 | O. Solet | 25 | 28 | Defender |
| 281495 | T. Kristensen | 23 | 31 | Defender |
| 418940 | A. Nunziante | 18 | 1 | Goalkeeper |
| 189 | D. Padelli | 40 | 93 | Goalkeeper |
| 143648 | M. Okoye | 26 | 40 | Goalkeeper |
| 197830 | R. Sava | 23 | 90 | Goalkeeper |
| 347644 | A. Atta | 22 | 14 | Midfielder |
| 490138 | A. Camara | 17 | 29 | Midfielder |
| 22007 | H. Kamara | 31 | 11 | Midfielder |
| 411171 | J. Arizala | 20 | 20 | Midfielder |
| 48047 | J. Karlström | 30 | 8 | Midfielder |
| 1939 | J. Piotrowski | 28 | 24 | Midfielder |
| 36916 | K. Ehizibue | 30 | 19 | Midfielder |
| 343558 | L. Miller | 19 | 38 | Midfielder |
| 182560 | Oier Zarraga | 26 | 6 | Midfielder |



## FIFA World Cup 2026

### Algeria (`team_id=1532`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Algeria`
- National team: `True`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 292924 | A. Benbouali | 25 |  | Attacker |
| 329163 | A. Boulbina | 22 | 27 | Attacker |
| 85041 | A. Gouiri | 25 | 11 | Attacker |
| 326067 | A. Hadj-Moussa | 23 | 11 | Attacker |
| 393073 | Amin Chiakha | 19 | 9 | Attacker |
| 276670 | F. Chaïbi | 23 | 17 | Attacker |
| 334915 | F. Ghedjemis | 23 |  | Attacker |
| 200139 | M. Amoura | 25 | 18 | Attacker |
| 635 | R. Mahrez | 34 | 7 | Attacker |
| 342740 | A. Abada | 26 | 19 | Defender |
| 1567 | A. Mandi | 34 | 2 | Defender |
| 4997 | H. Baouche | 30 | 2 | Defender |
| 284935 | M. Dorval | 24 | 3 | Defender |
| 21138 | R. Aït-Nouri | 24 | 15 | Defender |
| 303362 | R. Belghali | 23 | 25 | Defender |
| 277029 | R. Benchaa | 23 | 22 | Defender |
| 2194 | R. Bensebaïni | 30 | 21 | Defender |
| 4707 | R. Halaïmia | 29 | 12 | Defender |
| 191336 | S. Nair | 23 | 4 | Defender |
| 4561 | Z. Belaïd | 26 | 5 | Defender |
| 21137 | A. Mandréa | 29 | 1 | Goalkeeper |
| 601332 | Kilian Belazzoug | 19 |  | Goalkeeper |
| 732 | L. Zidane | 27 | 23 | Goalkeeper |
| 304229 | M. Mastil | 25 |  | Goalkeeper |
| 137129 | A. Aouchiche | 23 | 10 | Midfielder |
| 658 | H. Aouar | 27 | 8 | Midfielder |
| 4399 | H. Boudaoui | 26 | 14 | Midfielder |
| 294652 | H. Mrezigue | 25 | 15 | Midfielder |
| 380587 | I. Maza | 20 | 22 | Midfielder |
| 129047 | R. Zerrouki | 27 | 6 | Midfielder |
| 327599 | Y. Titraoui | 22 | 8 | Midfielder |


### Argentina (`team_id=26`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Argentina`
- National team: `True`
- Players: `40`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 449249 | Franco Mastantuono | 18 | 10 | Attacker |
| 362755 | G. Prestianni | 19 | 20 | Attacker |
| 323935 | G. Simeone | 23 | 17 | Attacker |
| 295513 | J. López | 25 | 13 | Attacker |
| 390742 | J. Panichelli | 23 |  | Attacker |
| 6009 | J. Álvarez | 25 | 9 | Attacker |
| 154 | L. Messi | 38 | 10 | Attacker |
| 217 | Lautaro Martínez | 28 | 22 | Attacker |
| 26315 | N. González | 27 | 15 | Attacker |
| 6067 | T. Almada | 24 | 16 | Attacker |
| 306706 | A. Giay | 21 | 4 | Defender |
| 30776 | C. Romero | 27 | 13 | Defender |
| 2468 | G. Montiel | 28 | 4 | Defender |
| 6608 | G. Rojas | 28 |  | Defender |
| 166 | J. Foyth | 27 | 2 | Defender |
| 5967 | K. Mac Allister | 28 |  | Defender |
| 6 | L. Balerdi | 26 | 6 | Defender |
| 6000 | L. Martínez | 29 | 2 | Defender |
| 1493 | M. Acuña | 34 | 8 | Defender |
| 6610 | M. Senesi | 28 | 6 | Defender |
| 6503 | N. Molina | 27 | 16 | Defender |
| 624 | N. Otamendi | 37 | 19 | Defender |
| 529 | N. Tagliafico | 33 | 3 | Defender |
| 620791 | D. Talavera | 18 |  | Goalkeeper |
| 19599 | E. Martínez | 33 | 23 | Goalkeeper |
| 6364 | F. Cambeses | 28 | 1 | Goalkeeper |
| 47296 | G. Rulli | 33 | 12 | Goalkeeper |
| 2465 | J. Musso | 31 | 23 | Goalkeeper |
| 22157 | W. Benítez | 32 | 1 | Goalkeeper |
| 6716 | A. Mac Allister | 27 | 20 | Midfielder |
| 6347 | A. Moreno | 26 | 11 | Midfielder |
| 19071 | E. Buendía | 29 | 8 | Midfielder |
| 5996 | E. Fernández | 24 | 8 | Midfielder |
| 6002 | E. Palacios | 27 | 14 | Midfielder |
| 1578 | G. Lo Celso | 29 | 11 | Midfielder |
| 271 | L. Paredes | 31 | 5 | Midfielder |
| 288699 | M. Perrone | 22 | 22 | Midfielder |
| 350037 | N. Paz | 21 | 18 | Midfielder |
| 2472 | R. De Paul | 31 | 7 | Midfielder |
| 319572 | V. Barco | 21 | 3 | Midfielder |


### Australia (`team_id=20`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Australia`
- National team: `True`
- Players: `25`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 2755 | A. Mabil | 30 | 10 | Attacker |
| 316161 | A. Šuto | 25 |  | Attacker |
| 6904 | C. Metcalfe | 26 | 8 | Attacker |
| 14887 | D. Jurić | 28 | 19 | Attacker |
| 44843 | M. Boyle | 32 | 6 | Attacker |
| 338014 | N. Irankunda | 19 | 11 | Attacker |
| 312459 | N. Velupillay | 24 | 7 | Attacker |
| 225 | A. Behich | 35 | 16 | Defender |
| 348568 | A. Circati | 22 | 23 | Defender |
| 20457 | C. Burgess | 30 | 21 | Defender |
| 337587 | J. Bos | 23 | 5 | Defender |
| 33847 | J. Geria | 32 | 22 | Defender |
| 426480 | L. Herrington | 18 | 13 | Defender |
| 2741 | M. Ryan | 33 | 1 | Goalkeeper |
| 353883 | P. Beach | 22 | 12 | Goalkeeper |
| 6870 | P. Izzo | 30 | 12 | Goalkeeper |
| 38123 | A. Hrustić | 29 | 10 | Midfielder |
| 7050 | A. O&apos;Neill | 27 | 13 | Midfielder |
| 288109 | A. Robertson | 22 |  | Midfielder |
| 6808 | J. Italiano | 24 | 17 | Midfielder |
| 153622 | K. Trewin | 24 | 7 | Midfielder |
| 2742 | M. Degenek | 31 | 2 | Midfielder |
| 269539 | P. Yazbek | 23 | 19 | Midfielder |
| 441269 | Paul Michael Junior Okon-Engstler | 20 | 6 | Midfielder |
| 6913 | R. McGree | 27 | 14 | Midfielder |


### Austria (`team_id=775`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Austria`
- National team: `True`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 18830 | M. Arnautović | 36 | 7 | Attacker |
| 25297 | M. Gregoritsch | 31 | 11 | Attacker |
| 7073 | M. Grüll | 27 | 17 | Attacker |
| 428779 | Nikolaus Wurmbrand | 19 | 15 | Attacker |
| 270201 | R. Florucz | 24 | 22 | Attacker |
| 7722 | S. Kalajdzic | 28 | 21 | Attacker |
| 126640 | D. Affengruber | 24 | 20 | Defender |
| 505 | D. Alaba | 33 | 8 | Defender |
| 25287 | K. Danso | 27 | 3 | Defender |
| 288206 | L. Querfeld | 22 | 14 | Defender |
| 25314 | M. Friedl | 27 | 2 | Defender |
| 7090 | M. Svoboda | 27 | 3 | Defender |
| 26240 | P. Lienhart | 29 | 15 | Defender |
| 25915 | P. Mwene | 31 | 16 | Defender |
| 711 | S. Posch | 28 | 5 | Defender |
| 7525 | A. Schlager | 29 | 1 | Goalkeeper |
| 221605 | F. Wiegele | 24 |  | Goalkeeper |
| 169349 | N. Polster | 23 | 12 | Goalkeeper |
| 7598 | P. Pentz | 28 | 13 | Goalkeeper |
| 7195 | T. Lawal | 25 | 12 | Goalkeeper |
| 7327 | A. Prass | 24 | 8 | Midfielder |
| 417 | A. Schöpf | 31 | 23 | Midfielder |
| 715 | C. Baumgartner | 26 | 19 | Midfielder |
| 138935 | C. Chukwuemeka | 22 | 10 | Midfielder |
| 719 | F. Grillitsch | 30 | 10 | Midfielder |
| 1157 | K. Laimer | 28 | 20 | Midfielder |
| 1159 | M. Sabitzer | 31 | 9 | Midfielder |
| 7328 | N. Seiwald | 24 | 6 | Midfielder |
| 327895 | P. Wanner | 20 | 10 | Midfielder |
| 126642 | P. Wimmer | 24 | 21 | Midfielder |
| 7562 | R. Schmid | 25 | 18 | Midfielder |
| 1095 | X. Schlager | 28 | 4 | Midfielder |


### Belgium (`team_id=1`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Belgium`
- National team: `True`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 25458 | D. Lukebakio | 28 | 14 | Attacker |
| 1422 | J. Doku | 23 | 11 | Attacker |
| 86 | L. Openda | 25 | 9 | Attacker |
| 1946 | L. Trossard | 31 | 10 | Attacker |
| 2927 | M. Batshuayi | 32 | 23 | Attacker |
| 361348 | M. Fofana | 20 | 19 | Attacker |
| 271276 | R. Vermant | 21 | 17 | Attacker |
| 204043 | A. Theate | 25 | 3 | Defender |
| 69 | B. Mechele | 32 | 4 | Defender |
| 375974 | J. Seys | 20 | 2 | Defender |
| 162141 | K. De Winter | 23 | 16 | Defender |
| 162007 | M. De Cuyper | 25 | 5 | Defender |
| 2920 | T. Castagne | 30 | 21 | Defender |
| 264 | T. Meunier | 34 | 15 | Defender |
| 304228 | Z. Debast | 22 | 2 | Defender |
| 340151 | M. Penders | 20 | 1 | Goalkeeper |
| 2919 | M. Sels | 33 | 13 | Goalkeeper |
| 1924 | M. Vandevoordt | 23 | 12 | Goalkeeper |
| 162511 | S. Lammens | 23 | 1 | Goalkeeper |
| 730 | T. Courtois | 33 | 1 | Goalkeeper |
| 162714 | A. Onana | 24 | 18 | Midfielder |
| 1417 | A. Saelemaekers | 26 | 22 | Midfielder |
| 20 | A. Witsel | 36 | 6 | Midfielder |
| 147859 | C. De Ketelaere | 24 | 17 | Midfielder |
| 8680 | C. Vanhoutte | 27 | 18 | Midfielder |
| 335056 | Diego Moreira | 21 | 7 | Midfielder |
| 78 | H. Vanaken | 33 | 20 | Midfielder |
| 629 | K. De Bruyne | 34 | 7 | Midfielder |
| 2120 | N. Raskin | 24 | 23 | Midfielder |
| 453903 | Nathan De Cat | 17 | 6 | Midfielder |
| 2926 | Y. Tielemans | 28 | 8 | Midfielder |


### Bosnia & Herzegovina (`team_id=1113`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Bosnia`
- National team: `True`
- Players: `24`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 322101 | A. Memić | 24 | 15 | Attacker |
| 329409 | E. Bajraktarevic | 20 | 20 | Attacker |
| 46930 | E. Demirović | 27 | 10 | Attacker |
| 790 | E. Džeko | 39 | 11 | Attacker |
| 28382 | H. Tabaković | 31 | 23 | Attacker |
| 395559 | Kerim-Sam Alajbegović | 18 | 19 | Attacker |
| 314377 | S. Baždar | 21 | 9 | Attacker |
| 7318 | A. Dedić | 23 | 7 | Defender |
| 25129 | D. Burnić | 27 | 17 | Defender |
| 53517 | D. Hadžikadunić | 27 | 3 | Defender |
| 1741 | N. Katić | 29 | 18 | Defender |
| 76867 | N. Mujakić | 27 | 2 | Defender |
| 395589 | N. Äelik | 19 | 3 | Defender |
| 1442 | S. Kolašinac | 32 | 5 | Defender |
| 14301 | S. Radeljić | 28 | 21 | Defender |
| 271350 | T. Muharemović | 22 | 4 | Defender |
| 108370 | M. Zlomislić | 27 | 22 | Goalkeeper |
| 9026 | N. Vasilj | 30 | 1 | Goalkeeper |
| 70480 | O. Hadžikić | 29 | 12 | Goalkeeper |
| 70514 | A. Gigović | 23 | 8 | Midfielder |
| 50006 | A. Hadžiahmetović | 28 | 16 | Midfielder |
| 264094 | B. Tahirović | 22 | 6 | Midfielder |
| 162222 | I. Bašić | 23 | 13 | Midfielder |
| 1324 | I. Šunjić | 29 | 14 | Midfielder |


### Brazil (`team_id=6`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Brazil`
- National team: `True`
- Players: `46`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 377122 | Endrick | 19 | 19 | Attacker |
| 425733 | Estêvão | 18 | 20 | Attacker |
| 127769 | Gabriel Martinelli | 24 | 22 | Attacker |
| 9366 | Igor Jesus | 24 | 9 | Attacker |
| 10329 | João Pedro | 24 | 7 | Attacker |
| 265785 | Luiz Henrique | 24 | 19 | Attacker |
| 1165 | Matheus Cunha | 26 | 21 | Attacker |
| 1496 | Raphinha | 29 | 10 | Attacker |
| 407806 | Rayan | 19 | 7 | Attacker |
| 2413 | Richarlison | 28 | 9 | Attacker |
| 10009 | Rodrygo | 24 | 10 | Attacker |
| 196156 | Thiago | 24 |  | Attacker |
| 762 | Vinícius Júnior | 25 | 10 | Attacker |
| 340279 | Vitor Roque | 20 | 9 | Attacker |
| 860 | Alex Sandro | 34 | 6 | Defender |
| 307835 | Beraldo | 22 | 15 | Defender |
| 30497 | Bremer | 28 | 25 | Defender |
| 10316 | Caio Henrique | 28 | 16 | Defender |
| 618 | Danilo | 34 | 2 | Defender |
| 24866 | Douglas Santos | 31 | 6 | Defender |
| 10089 | Fabrício Bruno | 29 | 14 | Defender |
| 22224 | Gabriel Magalhães | 28 | 3 | Defender |
| 30424 | Ibañez | 27 | 15 | Defender |
| 309792 | Kaiki | 22 | 6 | Defender |
| 197383 | Luciano Juba | 26 |  | Defender |
| 10124 | Léo Pereira | 29 | 15 | Defender |
| 257 | Marquinhos | 31 | 4 | Defender |
| 133910 | Paulo Henrique | 29 |  | Defender |
| 8661 | Vitinho | 26 | 13 | Defender |
| 349001 | Wesley | 22 | 2 | Defender |
| 372 | Éder Militão | 27 | 3 | Defender |
| 10111 | Bento | 26 | 12 | Goalkeeper |
| 617 | Ederson | 32 | 23 | Goalkeeper |
| 123759 | Hugo Souza | 26 | 23 | Goalkeeper |
| 70366 | John | 29 |  | Goalkeeper |
| 305834 | Andrey Santos | 21 | 18 | Midfielder |
| 265784 | André | 24 | 18 | Midfielder |
| 10135 | Bruno Guimarães | 28 | 8 | Midfielder |
| 10238 | Carlos Augusto | 26 | 16 | Midfielder |
| 747 | Casemiro | 33 | 5 | Midfielder |
| 275170 | Danilo | 24 |  | Midfielder |
| 299 | Fabinho | 32 | 15 | Midfielder |
| 80552 | Gabriel Sara | 26 |  | Midfielder |
| 723 | Joelinton | 29 | 17 | Midfielder |
| 195103 | João Gomes | 24 | 5 | Midfielder |
| 1646 | Lucas Paquetá | 28 | 11 | Midfielder |


### Canada (`team_id=5529`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Canada`
- National team: `True`
- Players: `40`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 146325 | A. Pepple | 23 |  | Attacker |
| 2001 | C. Larin | 30 | 9 | Attacker |
| 296458 | D. Jebbison | 22 | 11 | Attacker |
| 8489 | J. David | 25 | 10 | Attacker |
| 19007 | J. Hoilett | 35 | 10 | Attacker |
| 193279 | J. Nelson | 23 | 25 | Attacker |
| 203428 | J. Russell-Rowe | 23 | 12 | Attacker |
| 50826 | J. Shaffelburg | 26 | 14 | Attacker |
| 44798 | L. Millar | 26 | 23 | Attacker |
| 541949 | M. Aiyenero | 17 | 9 | Attacker |
| 313353 | P. David | 24 | 24 | Attacker |
| 51293 | T. Bair | 26 | 11 | Attacker |
| 370938 | T. Coimbra | 21 | 19 | Attacker |
| 351587 | T. Oluwaseyi | 25 | 12 | Attacker |
| 51295 | D. Cornelius | 28 | 13 | Defender |
| 201707 | J. Marshall-Rutty | 21 |  | Defender |
| 78494 | J. Waterman | 29 | 5 | Defender |
| 50925 | K. Miller | 28 | 4 | Defender |
| 327738 | L. De Fougerolles | 20 | 15 | Defender |
| 370936 | N. Abatneh | 21 | 2 | Defender |
| 50816 | R. Laryea | 30 | 22 | Defender |
| 8660 | Z. Bassong | 26 | 3 | Defender |
| 51148 | D. St. Clair | 28 | 1 | Goalkeeper |
| 50778 | J. Pantemis | 28 | 16 | Goalkeeper |
| 351582 | L. Gavran | 25 |  | Goalkeeper |
| 51274 | M. Crépeau | 31 | 16 | Goalkeeper |
| 284554 | O. Goodman | 22 | 1 | Goalkeeper |
| 362145 | A. Ahmed | 25 | 20 | Midfielder |
| 328046 | I. Koné | 23 | 8 | Midfielder |
| 407583 | J. Badwal | 19 | 8 | Midfielder |
| 50817 | J. Osorio | 33 | 21 | Midfielder |
| 50788 | M. Choinière | 26 | 6 | Midfielder |
| 284061 | M. Flores | 22 | 18 | Midfielder |
| 269936 | M. de Brienne | 23 |  | Midfielder |
| 512956 | Malik Henry | 23 |  | Midfielder |
| 294824 | N. Saliba | 21 | 19 | Midfielder |
| 416901 | N. Sigur | 22 | 23 | Midfielder |
| 203436 | R. Priso | 23 | 8 | Midfielder |
| 35570 | S. Eustáquio | 29 | 7 | Midfielder |
| 51016 | T. Buchanan | 26 | 17 | Midfielder |


### Cape Verde Islands (`team_id=1533`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Cape-Verde-Islands`
- National team: `True`
- Players: `26`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 343287 | D. Livramento | 24 | 9 | Attacker |
| 567803 | F. Domingos | 18 | 11 | Attacker |
| 44612 | Garry Rodrigues | 35 | 11 | Attacker |
| 544511 | Ieltsin Camoes | 26 |  | Attacker |
| 1494 | Jovane Cabral | 27 | 7 | Attacker |
| 22265 | Nuno da Costa | 34 | 21 | Attacker |
| 50270 | Ryan Mendes | 36 | 20 | Attacker |
| 113580 | Willy Semedo | 31 | 17 | Attacker |
| 41608 | Diney Borges | 30 | 3 | Defender |
| 351022 | J. Soares | 26 |  | Defender |
| 268806 | Kelvin Pires | 25 | 13 | Defender |
| 69260 | Pico | 33 | 4 | Defender |
| 308689 | S. Lopes Cabral | 23 | 13 | Defender |
| 22139 | S. Moreira | 31 | 22 | Defender |
| 332056 | Wagner Pina | 23 | 7 | Defender |
| 163200 | C. dos Santos | 25 | 21 | Goalkeeper |
| 41764 | Márcio Rosa | 28 | 12 | Goalkeeper |
| 15304 | Vózinha | 39 | 1 | Goalkeeper |
| 435739 | A. Santos | 20 |  | Midfielder |
| 37435 | Deroy Duarte | 26 | 14 | Midfielder |
| 418978 | J. Mendes | 21 |  | Midfielder |
| 142016 | João Paulo | 27 | 8 | Midfielder |
| 96512 | Kevin Pina | 28 | 6 | Midfielder |
| 37436 | L. Duarte | 28 | 15 | Midfielder |
| 265556 | Telmo Arcanjo | 24 | 18 | Midfielder |
| 128007 | Yannick Semedo | 30 | 16 | Midfielder |


### Colombia (`team_id=8`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Colombia`
- National team: `True`
- Players: `36`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 345748 | A. Gómez | 23 | 18 | Attacker |
| 47582 | C. Hernández | 26 | 14 | Attacker |
| 13708 | J. Arias | 28 | 11 | Attacker |
| 13376 | J. Campaz | 25 | 21 | Attacker |
| 13691 | J. Carbonero | 26 | 21 | Attacker |
| 5994 | J. Carrascal | 27 | 8 | Attacker |
| 24810 | J. Córdoba | 32 | 9 | Attacker |
| 70849 | K. Serna | 28 |  | Attacker |
| 2489 | L. Díaz | 28 | 7 | Attacker |
| 47237 | L. Suárez | 28 | 19 | Attacker |
| 6011 | R. Borré | 30 | 19 | Attacker |
| 13642 | A. Román | 30 | 2 | Defender |
| 13283 | C. Cuesta | 26 | 2 | Defender |
| 2483 | D. Machado | 32 | 4 | Defender |
| 13736 | D. Muñoz | 29 | 2 | Defender |
| 168 | D. Sánchez | 29 | 23 | Defender |
| 125674 | J. Cabal | 24 | 2 | Defender |
| 1929 | J. Lucumí | 27 | 3 | Defender |
| 64268 | J. Mojica | 33 | 14 | Defender |
| 30 | S. Arias | 33 | 4 | Defender |
| 13571 | W. Ditta | 28 | 2 | Defender |
| 2484 | Y. Mina | 31 | 13 | Defender |
| 13729 | Á. Angulo | 28 | 8 | Defender |
| 2482 | C. Vargas | 36 | 12 | Goalkeeper |
| 313 | D. Ospina | 37 | 1 | Goalkeeper |
| 13278 | K. Mier | 25 | 22 | Goalkeeper |
| 2481 | Á. Montero | 30 | 22 | Goalkeeper |
| 324034 | G. Puerta | 22 | 20 | Midfielder |
| 2490 | J. Lerma | 31 | 16 | Midfielder |
| 13151 | J. Portilla | 27 | 15 | Midfielder |
| 6005 | J. Quintero | 32 | 20 | Midfielder |
| 517 | J. Rodríguez | 34 | 10 | Midfielder |
| 289592 | K. Castaño | 25 | 5 | Midfielder |
| 195104 | R. Rios | 25 | 6 | Midfielder |
| 281795 | Y. Asprilla | 22 | 8 | Midfielder |
| 195717 | Y. Mosquera | 24 | 2 | Midfielder |


### Congo DR (`team_id=1508`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Congo-DR`
- National team: `True`
- Players: `24`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 3033 | C. Bakambu | 34 | 17 | Attacker |
| 179699 | F. Mayele | 31 | 19 | Attacker |
| 3034 | M. Elia | 28 | 13 | Attacker |
| 129670 | N. Mbuku | 23 | 7 | Attacker |
| 20674 | S. Banza | 29 | 23 | Attacker |
| 8627 | T. Bongonda | 30 | 10 | Attacker |
| 20649 | Y. Wissa | 29 | 20 | Attacker |
| 18816 | A. Masuaku | 32 | 11 | Defender |
| 19182 | A. Tuanzebe | 28 | 4 | Defender |
| 18846 | A. Wan-Bissaka | 28 | 2 | Defender |
| 375 | C. Mbemba | 31 | 22 | Defender |
| 8445 | D. Batubinsika | 29 | 5 | Defender |
| 21098 | J. Kayembe | 31 | 12 | Defender |
| 8634 | R. Bushiri | 26 | 15 | Defender |
| 199767 | S. Kapuadi | 27 | 3 | Defender |
| 24012 | L. Mpasi | 31 | 1 | Goalkeeper |
| 314509 | M. Epolo | 20 | 21 | Goalkeeper |
| 48501 | T. Fayulu | 26 | 16 | Goalkeeper |
| 279482 | B. Cipenga | 27 | 9 | Midfielder |
| 48555 | C. Pickel | 28 | 18 | Midfielder |
| 1424 | E. Kayembe | 27 | 5 | Midfielder |
| 375598 | N. Mukau | 21 | 6 | Midfielder |
| 365331 | N. Sadiki | 21 | 14 | Midfielder |
| 21101 | S. Moutoussamy | 29 | 8 | Midfielder |


### Croatia (`team_id=3`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Croatia`
- National team: `True`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 46746 | A. Budimir | 34 | 11 | Attacker |
| 726 | A. Kramarić | 34 | 9 | Attacker |
| 202951 | F. Ivanović | 22 | 20 | Attacker |
| 202696 | I. Matanović | 22 | 21 | Attacker |
| 207 | I. Perišić | 36 | 14 | Attacker |
| 1330 | M. Oršić | 33 | 16 | Attacker |
| 260865 | M. Pašalić | 25 | 7 | Attacker |
| 66055 | P. Musa | 27 | 11 | Attacker |
| 14327 | D. Bradarić | 26 | 6 | Defender |
| 1902 | D. Ćaleta-Car | 29 | 5 | Defender |
| 14266 | I. Smolčić | 25 | 2 | Defender |
| 129033 | J. Gvardiol | 23 | 4 | Defender |
| 125171 | J. Stanišić | 25 | 2 | Defender |
| 14701 | J. Šutalo | 25 | 6 | Defender |
| 387521 | L. Vušković | 18 | 4 | Defender |
| 30827 | M. Erlić | 27 | 22 | Defender |
| 1084 | M. Pongračić | 28 | 3 | Defender |
| 524 | D. Kotarski | 25 | 12 | Goalkeeper |
| 1305 | D. Livaković | 31 | 1 | Goalkeeper |
| 14297 | I. Ivušić | 30 | 23 | Goalkeeper |
| 14268 | I. Pandur | 25 | 12 | Goalkeeper |
| 64 | K. Letica | 28 | 23 | Goalkeeper |
| 14395 | K. Jakić | 28 | 18 | Midfielder |
| 1321 | L. Majer | 27 | 7 | Midfielder |
| 754 | L. Modrić | 40 | 10 | Midfielder |
| 7332 | L. Sučić | 23 | 21 | Midfielder |
| 295026 | M. Baturina | 22 | 16 | Midfielder |
| 2291 | M. Kovačić | 31 | 8 | Midfielder |
| 2763 | M. Pašalić | 30 | 15 | Midfielder |
| 1322 | N. Moro | 27 | 8 | Midfielder |
| 842 | N. Vlašić | 28 | 13 | Midfielder |
| 348205 | P. Sučić | 22 | 17 | Midfielder |
| 284869 | T. Fruk | 24 | 19 | Midfielder |


### Curaçao (`team_id=5530`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Curacao`
- National team: `True`
- Players: `26`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 38708 | G. Kastaneer | 29 | 9 | Attacker |
| 163220 | J. Antonisse | 23 | 11 | Attacker |
| 19047 | J. Bacuna | 28 | 7 | Attacker |
| 18981 | J. Locadia | 32 | 9 | Attacker |
| 195067 | J. Margaritha | 25 | 16 | Attacker |
| 41627 | K. Gorré | 31 | 14 | Attacker |
| 161884 | S. Hansen | 23 | 12 | Attacker |
| 906 | T. Chong | 26 | 14 | Attacker |
| 162199 | A. Martha | 22 | 15 | Defender |
| 228 | A. Obispo | 26 | 18 | Defender |
| 353808 | Deveron Fonville | 22 | 13 | Defender |
| 706 | J. Brenet | 31 | 20 | Defender |
| 36857 | J. Gaari | 32 | 3 | Defender |
| 18997 | L. Bacuna | 34 | 10 | Defender |
| 37175 | R. Bazoer | 29 | 24 | Defender |
| 37066 | R. van Eijma | 27 | 4 | Defender |
| 36970 | S. Floranus | 27 | 5 | Defender |
| 194645 | S. Sambo | 24 | 2 | Defender |
| 406846 | T. Noslin | 23 | 17 | Defender |
| 221 | E. Room | 36 | 1 | Goalkeeper |
| 214129 | T. Bodak | 23 | 22 | Goalkeeper |
| 36967 | T. Doornbusch | 26 | 23 | Goalkeeper |
| 37272 | B. Kuwas | 33 | 17 | Midfielder |
| 36842 | G. Roemeratoe | 26 | 6 | Midfielder |
| 37461 | K. Felida | 26 | 21 | Midfielder |
| 309763 | L. Comenencia | 21 | 8 | Midfielder |


### Czech Republic (`team_id=770`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Czech-Republic`
- National team: `True`
- Players: `25`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 290212 | D. Višinský | 22 | 21 | Attacker |
| 90746 | J. Kliment | 32 | 11 | Attacker |
| 66275 | M. Chytil | 26 | 13 | Attacker |
| 794 | P. Schick | 29 | 10 | Attacker |
| 818 | T. Chorý | 30 | 19 | Attacker |
| 128793 | D. Jurásek | 25 | 17 | Defender |
| 1237 | J. Zelený | 33 | 20 | Defender |
| 66407 | L. Krejčí | 26 | 7 | Defender |
| 287564 | M. Vitík | 22 | 6 | Defender |
| 162964 | R. Hranáč | 25 | 4 | Defender |
| 2252 | T. Holeš | 32 | 3 | Defender |
| 1231 | V. Coufal | 33 | 5 | Defender |
| 66270 | V. Jemelka | 30 | 3 | Defender |
| 337740 | Š. Chaloupek | 22 | 2 | Defender |
| 269349 | L. Horníček | 23 | 16 | Goalkeeper |
| 61161 | M. Jedlička | 27 | 23 | Goalkeeper |
| 138804 | M. Kovář | 25 | 1 | Goalkeeper |
| 199871 | A. Karabec | 22 | 9 | Midfielder |
| 66353 | L. Provod | 29 | 14 | Midfielder |
| 162194 | L. Červ | 24 | 12 | Midfielder |
| 241 | M. Sadílek | 26 | 18 | Midfielder |
| 66387 | P. Šulc | 25 | 15 | Midfielder |
| 66253 | T. Ladra | 28 | 9 | Midfielder |
| 1243 | T. Souček | 30 | 22 | Midfielder |
| 25348 | V. Darida | 35 | 8 | Midfielder |


### Ecuador (`team_id=2382`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Ecuador`
- National team: `True`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 280695 | A. Minda | 22 | 14 | Attacker |
| 356456 | Bryan Josías Ramírez León | 25 | 20 | Attacker |
| 35533 | E. Valencia | 36 | 13 | Attacker |
| 16369 | G. Plata | 25 | 19 | Attacker |
| 16590 | J. Caicedo | 28 | 19 | Attacker |
| 237122 | J. Mercado | 23 | 18 | Attacker |
| 350799 | Jeremy Arévalo | 20 | 8 | Attacker |
| 2584 | L. Campana | 25 | 8 | Attacker |
| 311543 | N. Angulo | 22 | 20 | Attacker |
| 2583 | A. Preciado | 27 | 17 | Defender |
| 2076 | C. Ramírez | 31 | 5 | Defender |
| 63964 | F. Torres | 28 | 2 | Defender |
| 237191 | J. Chávez | 23 |  | Defender |
| 354027 | J. Ordoñez | 21 | 4 | Defender |
| 2575 | J. Porozo | 25 | 5 | Defender |
| 16370 | L. Realpe | 24 | 20 | Defender |
| 46731 | P. Estupiñán | 27 | 7 | Defender |
| 127817 | P. Hincapié | 23 | 3 | Defender |
| 16367 | W. Pacho | 24 | 6 | Defender |
| 306940 | Y. Medina | 21 | 7 | Defender |
| 410134 | C. Loor | 19 | 1 | Goalkeeper |
| 16642 | G. Valle | 29 | 22 | Goalkeeper |
| 16380 | H. Galíndez | 38 | 1 | Goalkeeper |
| 81224 | M. Ramírez | 25 | 12 | Goalkeeper |
| 16360 | A. Franco | 27 | 21 | Midfielder |
| 198347 | A. Valencia | 22 |  | Midfielder |
| 338045 | D. Castillo | 21 | 16 | Midfielder |
| 16470 | J. Alcívar | 26 | 18 | Midfielder |
| 25414 | J. Yeboah | 25 | 9 | Midfielder |
| 406303 | K. Páez | 18 | 10 | Midfielder |
| 361966 | K. Rodríguez | 25 | 11 | Midfielder |
| 116117 | M. Caicedo | 24 | 23 | Midfielder |
| 540961 | M. Lawrence | 26 | 17 | Midfielder |
| 321658 | P. Mercado | 22 | 16 | Midfielder |
| 237078 | P. Vite | 23 | 15 | Midfielder |


### Egypt (`team_id=32`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Egypt`
- National team: `True`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 20844 | H. Hassan | 23 | 15 | Attacker |
| 70535 | Ibrahim Adel | 24 | 20 | Attacker |
| 306 | Mohamed Salah | 33 | 10 | Attacker |
| 16862 | Mostafa Fathi | 31 | 18 | Attacker |
| 2668 | Mostafa Mohamed | 28 | 11 | Attacker |
| 550372 | N. Mansy | 27 | 21 | Attacker |
| 81573 | Omar Marmoush | 26 | 22 | Attacker |
| 269275 | Osama Faisal | 24 | 21 | Attacker |
| 2666 | Salah Mohsen | 27 | 9 | Attacker |
| 16871 | Zizo | 29 | 25 | Attacker |
| 2649 | Ahmed Abou El Fotouh | 27 | 13 | Defender |
| 190576 | Ahmed Eid | 24 | 24 | Defender |
| 269621 | Hossam Abdelmaguid | 24 | 4 | Defender |
| 17032 | Khaled Sobhy | 30 | 2 | Defender |
| 550412 | M. Hamdi | 30 | 12 | Defender |
| 550448 | M. Ismail | 26 | 28 | Defender |
| 196343 | Mohamed Abdelmonem | 26 | 6 | Defender |
| 2654 | Mohamed Hany | 29 | 3 | Defender |
| 16805 | Rami Rabia | 32 | 5 | Defender |
| 16804 | Yasser Ibrahim | 32 | 6 | Defender |
| 2648 | Ahmed El Shenawy | 34 | 1 | Goalkeeper |
| 16831 | Al Mahdi Soliman | 38 | 16 | Goalkeeper |
| 16797 | Mohamed El Shenawy | 37 | 23 | Goalkeeper |
| 17190 | Mohamed Sobhi | 26 | 16 | Goalkeeper |
| 269174 | Mostafa Shobeir | 25 | 26 | Goalkeeper |
| 292695 | Ahmed Koka | 24 | 15 | Midfielder |
| 17269 | Emam Ashour | 27 | 8 | Midfielder |
| 16813 | Hamdi Fathy | 31 | 14 | Midfielder |
| 16901 | Islam Issa | 29 | 8 | Midfielder |
| 69196 | Mahmoud Saber | 24 | 27 | Midfielder |
| 190575 | Marwan Attia | 27 | 19 | Midfielder |
| 182021 | Mohamed Shehata | 24 | 15 | Midfielder |
| 16841 | Mohanad Lasheen | 29 | 17 | Midfielder |
| 550371 | T. Alaa | 23 |  | Midfielder |
| 2664 | Trézéguet | 31 | 7 | Midfielder |


### England (`team_id=10`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `England`
- National team: `True`
- Players: `44`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 138787 | A. Gordon | 24 | 17 | Attacker |
| 1460 | B. Saka | 24 | 7 | Attacker |
| 18766 | D. Calvert-Lewin | 28 | 18 | Attacker |
| 18883 | D. Solanke | 28 | 19 | Attacker |
| 18778 | H. Barnes | 28 | 17 | Attacker |
| 184 | H. Kane | 32 | 9 | Attacker |
| 19428 | J. Bowen | 29 | 20 | Attacker |
| 909 | M. Rashford | 28 | 11 | Attacker |
| 136723 | N. Madueke | 23 | 21 | Attacker |
| 19366 | O. Watkins | 30 | 19 | Attacker |
| 19959 | B. White | 28 | 21 | Defender |
| 18961 | D. Burn | 33 | 12 | Defender |
| 19235 | D. Spence | 25 | 14 | Defender |
| 19354 | E. Konsa | 28 | 2 | Defender |
| 19209 | F. Tomori | 28 | 12 | Defender |
| 2935 | H. Maguire | 32 | 6 | Defender |
| 158698 | J. Quansah | 22 | 2 | Defender |
| 626 | J. Stones | 31 | 5 | Defender |
| 284492 | L. Hall | 21 | 3 | Defender |
| 67971 | M. Guéhi | 25 | 5 | Defender |
| 313245 | M. Lewis-Skelly | 19 | 3 | Defender |
| 19545 | R. James | 26 | 3 | Defender |
| 19720 | T. Chalobah | 26 | 6 | Defender |
| 158694 | T. Livramento | 23 | 16 | Defender |
| 20355 | A. Ramsdale | 27 | 1 | Goalkeeper |
| 19088 | D. Henderson | 28 | 13 | Goalkeeper |
| 2932 | J. Pickford | 31 | 1 | Goalkeeper |
| 18960 | J. Steele | 35 | 18 | Goalkeeper |
| 162489 | J. Trafford | 23 | 22 | Goalkeeper |
| 304853 | A. Scott | 22 | 23 | Midfielder |
| 288102 | A. Wharton | 21 | 16 | Midfielder |
| 152982 | C. Palmer | 23 | 20 | Midfielder |
| 2937 | D. Rice | 26 | 4 | Midfielder |
| 138908 | E. Anderson | 23 | 21 | Midfielder |
| 19586 | E. Eze | 27 | 19 | Midfielder |
| 129718 | J. Bellingham | 22 | 10 | Midfielder |
| 895 | J. Garner | 24 | 14 | Midfielder |
| 292 | J. Henderson | 35 | 8 | Midfielder |
| 284322 | K. Mainoo | 20 | 18 | Midfielder |
| 18746 | M. Gibbs-White | 25 | 16 | Midfielder |
| 19170 | M. Rogers | 23 | 15 | Midfielder |
| 307123 | N. O&apos;Reilly | 20 | 18 | Midfielder |
| 631 | P. Foden | 25 | 17 | Midfielder |
| 2292 | R. Loftus-Cheek | 29 | 18 | Midfielder |


### France (`team_id=2`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `France`
- National team: `True`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 161904 | B. Barcola | 23 | 20 | Attacker |
| 269 | C. Nkunku | 28 | 7 | Attacker |
| 343027 | D. Doué | 20 | 12 | Attacker |
| 1922 | F. Thauvin | 32 | 8 | Attacker |
| 174565 | H. Ekitike | 23 | 9 | Attacker |
| 25927 | J. Mateta | 28 | 19 | Attacker |
| 508 | K. Coman | 29 | 7 | Attacker |
| 278 | Kylian Mbappé | 27 | 10 | Attacker |
| 274300 | M. Akliouche | 23 | 12 | Attacker |
| 21509 | M. Thuram | 28 | 9 | Attacker |
| 153 | O. Dembélé | 28 | 7 | Attacker |
| 21104 | R. Kolo Muani | 27 | 12 | Attacker |
| 2725 | B. Pavard | 29 | 15 | Defender |
| 1149 | D. Upamecano | 27 | 4 | Defender |
| 1145 | I. Konaté | 26 | 15 | Defender |
| 1257 | J. Koundé | 27 | 5 | Defender |
| 2724 | L. Digne | 32 | 3 | Defender |
| 33 | L. Hernández | 29 | 21 | Defender |
| 161907 | M. Gusto | 22 | 2 | Defender |
| 20995 | M. Lacroix | 25 | 19 | Defender |
| 162188 | P. Kalulu | 25 | 19 | Defender |
| 47300 | T. Hernández | 28 | 22 | Defender |
| 22090 | W. Saliba | 24 | 17 | Defender |
| 21628 | B. Samba | 31 | 1 | Goalkeeper |
| 162453 | L. Chevalier | 24 | 23 | Goalkeeper |
| 22221 | M. Maignan | 30 | 16 | Goalkeeper |
| 272 | A. Rabiot | 30 | 14 | Midfielder |
| 1271 | A. Tchouaméni | 25 | 8 | Midfielder |
| 2207 | E. Camavinga | 23 | 6 | Midfielder |
| 116 | K. Thuram | 24 | 6 | Midfielder |
| 22147 | M. Koné | 24 | 8 | Midfielder |
| 19617 | M. Olise | 24 | 11 | Midfielder |
| 2290 | N. Kanté | 34 | 13 | Midfielder |
| 156477 | R. Cherki | 22 | 14 | Midfielder |
| 336657 | W. Zaïre-Emery | 19 | 18 | Midfielder |


### Germany (`team_id=25`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Germany`
- National team: `True`
- Players: `37`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 24798 | C. Führich | 27 | 11 | Attacker |
| 26475 | D. Undav | 29 | 13 | Attacker |
| 25926 | J. Burkardt | 25 | 10 | Attacker |
| 128533 | J. Leweling | 24 | 7 | Attacker |
| 7334 | K. Adeyemi | 23 | 14 | Attacker |
| 978 | K. Havertz | 26 | 7 | Attacker |
| 644 | L. Sané | 30 | 19 | Attacker |
| 158644 | M. Beier | 23 | 9 | Attacker |
| 158054 | N. Woltemade | 23 | 11 | Attacker |
| 510 | S. Gnabry | 30 | 20 | Attacker |
| 2285 | A. Rüdiger | 32 | 2 | Defender |
| 25158 | D. Raum | 27 | 22 | Defender |
| 972 | J. Tah | 29 | 4 | Defender |
| 24868 | J. Vagnoman | 25 | 2 | Defender |
| 163189 | M. Thiaw | 24 | 2 | Defender |
| 280074 | N. Brown | 22 | 18 | Defender |
| 26243 | N. Schlotterbeck | 26 | 15 | Defender |
| 26238 | R. Koch | 29 | 3 | Defender |
| 25368 | W. Anton | 29 | 3 | Defender |
| 399 | A. Nübel | 29 | 12 | Goalkeeper |
| 25903 | F. Dahmen | 27 | 21 | Goalkeeper |
| 702 | O. Baumann | 35 | 1 | Goalkeeper |
| 380978 | A. Ouédraogo | 19 | 9 | Midfielder |
| 328033 | A. Pavlović | 21 | 5 | Midfielder |
| 177665 | A. Stach | 27 | 23 | Midfielder |
| 137210 | A. Stiller | 24 | 16 | Midfielder |
| 637 | F. Nmecha | 25 | 13 | Midfielder |
| 203224 | F. Wirtz | 22 | 17 | Midfielder |
| 502 | J. Kimmich | 30 | 6 | Midfielder |
| 178077 | K. Schade | 24 | 16 | Midfielder |
| 511 | L. Goretzka | 30 | 8 | Midfielder |
| 494131 | L. Karl | 17 | 21 | Midfielder |
| 714 | N. Amiri | 29 | 10 | Midfielder |
| 18970 | P. Groß | 34 | 5 | Midfielder |
| 24903 | R. Andrich | 31 | 23 | Midfielder |
| 25917 | R. Baku | 27 | 23 | Midfielder |
| 432310 | S. El Mala | 19 | 7 | Midfielder |


### Ghana (`team_id=1504`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Ghana`
- National team: `True`
- Players: `36`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 303467 | A. Fatawu | 21 | 7 | Attacker |
| 19281 | A. Semenyo | 25 |  | Attacker |
| 82090 | B. Thomas-Asante | 27 | 10 | Attacker |
| 411800 | C. Bonsu Baah | 21 | 17 | Attacker |
| 87791 | D. Agyei | 28 |  | Attacker |
| 3428 | J. Ayew | 34 | 9 | Attacker |
| 1944 | J. Paintsil | 28 | 13 | Attacker |
| 435776 | K. Nkrumah | 18 |  | Attacker |
| 199837 | K. Sulemana | 23 | 22 | Attacker |
| 410016 | P. Adu | 22 |  | Attacker |
| 526524 | P. Owusu | 19 | 19 | Attacker |
| 26140 | P. Owusu | 28 | 19 | Attacker |
| 162773 | R. Königsdörffer | 24 | 18 | Attacker |
| 21633 | A. Djiku | 31 | 23 | Defender |
| 196187 | A. Seidu | 25 | 2 | Defender |
| 128853 | D. Köhn | 27 |  | Defender |
| 25341 | D. Luckassen | 30 | 3 | Defender |
| 305450 | E. Annan | 23 | 21 | Defender |
| 7578 | G. Mensah | 27 | 14 | Defender |
| 369425 | J. Adjetey | 22 | 4 | Defender |
| 137223 | J. Opoku | 27 | 18 | Defender |
| 404172 | K. Peprah Oppong | 21 | 15 | Defender |
| 47480 | M. Salisu | 26 | 6 | Defender |
| 191240 | M. Senaya | 24 |  | Defender |
| 108475 | P. Pfeiffer | 26 |  | Defender |
| 144709 | J. Anang | 25 | 12 | Goalkeeper |
| 3412 | L. Zigi | 29 | 1 | Goalkeeper |
| 559233 | S. Mohan | 19 | 16 | Goalkeeper |
| 118345 | A. Francis | 24 | 21 | Midfielder |
| 475575 | Caleb Marfo Yirenkyi | 19 | 3 | Midfielder |
| 21010 | E. Owusu | 28 | 15 | Midfielder |
| 353609 | I. Sulemana | 22 | 8 | Midfielder |
| 3608 | K. Sibo | 27 | 8 | Midfielder |
| 15911 | M. Kudus | 25 | 20 | Midfielder |
| 559129 | P. Owusu | 21 |  | Midfielder |
| 49 | T. Partey | 32 | 5 | Midfielder |


### Haiti (`team_id=2386`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Haiti`
- National team: `True`
- Players: `29`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 50958 | D. Etienne | 29 | 7 | Attacker |
| 45020 | D. Nazon | 31 | 9 | Attacker |
| 8601 | F. Pierrot | 30 | 20 | Attacker |
| 174915 | J. Casimir | 24 | 21 | Attacker |
| 128766 | L. Deedson | 24 | 11 | Attacker |
| 162733 | R. Providence | 24 | 15 | Attacker |
| 24140 | S. Lambese | 30 | 19 | Attacker |
| 84087 | W. Isidor | 25 | 18 | Attacker |
| 326017 | W. Pacius | 24 | 16 | Attacker |
| 48535 | Y. Fortuné | 26 | 19 | Attacker |
| 20850 | C. Arcus | 29 | 2 | Defender |
| 102505 | D. Lacroix | 32 | 13 | Defender |
| 103065 | D. Pierre | 25 |  | Defender |
| 318930 | G. Métusala | 26 | 6 | Defender |
| 1411 | H. Delcroix | 26 | 5 | Defender |
| 20655 | J. Duverne | 28 | 22 | Defender |
| 573613 | K. Thermoncy | 19 | 3 | Defender |
| 190747 | M. Expérience | 26 | 8 | Defender |
| 12303 | Ricardo Ade | 35 | 4 | Defender |
| 275367 | W. Paugain | 24 | 24 | Defender |
| 174768 | A. Pierre | 24 | 12 | Goalkeeper |
| 123742 | J. Duverger | 23 | 23 | Goalkeeper |
| 87789 | J. Placide | 37 | 1 | Goalkeeper |
| 162129 | C. Attys | 24 | 22 | Midfielder |
| 540857 | C. F. Sainte | 23 | 18 | Midfielder |
| 338367 | D. Jean-Jacques | 25 | 17 | Midfielder |
| 20665 | J. Bellegarde | 27 | 10 | Midfielder |
| 20538 | L. Pierre | 27 | 14 | Midfielder |
| 371050 | W. Pierre | 21 | 6 | Midfielder |


### Iran (`team_id=22`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Iran`
- National team: `True`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 29720 | A. Alipour | 30 | 8 | Attacker |
| 29937 | A. Hosseinzadeh | 25 | 10 | Attacker |
| 2700 | A. Jahanbakhsh | 32 | 7 | Attacker |
| 29992 | A. Koushki | 25 | 2 | Attacker |
| 613145 | A. Mahmoudi | 19 |  | Attacker |
| 357029 | M. Hashemnejad | 24 | 16 | Attacker |
| 134217 | M. Mohebi | 27 | 27 | Attacker |
| 42315 | M. Taremi | 33 | 9 | Attacker |
| 532798 | M. Tikdari | 29 | 6 | Attacker |
| 89982 | S. Moghanlou | 31 | 24 | Attacker |
| 532925 | A. Abdullayev | 19 | 23 | Defender |
| 533035 | A. Nemati | 29 | 5 | Defender |
| 343405 | A. Yousefi | 23 | 18 | Defender |
| 2685 | E. Hajisafi | 35 | 3 | Defender |
| 2687 | H. Kanani | 31 | 13 | Defender |
| 341844 | M. Ghorbani | 24 | 26 | Defender |
| 2686 | M. Hosseini | 29 | 19 | Defender |
| 2688 | M. Mohammadi | 32 | 5 | Defender |
| 2691 | R. Rezaeian | 35 | 23 | Defender |
| 29704 | S. Khalilzadeh | 36 | 4 | Defender |
| 136880 | Saleh Hardani | 27 | 5 | Defender |
| 2682 | A. Beiranvand | 33 | 1 | Goalkeeper |
| 29755 | H. Hosseini | 33 | 22 | Goalkeeper |
| 2681 | P. Niazmand | 30 | 1 | Goalkeeper |
| 8564 | A. Gholizadeh | 29 | 11 | Midfielder |
| 423753 | A. Razzaghinia | 19 | 6 | Midfielder |
| 290554 | M. Mohebi | 25 | 25 | Midfielder |
| 532944 | M. Murodov | 16 |  | Midfielder |
| 29775 | O. Noorafkan | 28 | 21 | Midfielder |
| 19614 | S. Ezatolahi | 29 | 6 | Midfielder |
| 2699 | S. Ghoddos | 32 | 14 | Midfielder |


### Iraq (`team_id=1567`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Iraq`
- National team: `True`
- Players: `26`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 542842 | A. Y. Hashim | 29 | 13 | Attacker |
| 299813 | Ali Al Hamadi | 23 | 9 | Attacker |
| 49451 | Aymen Hussein | 29 | 18 | Attacker |
| 542866 | H. Abdulkareem | 26 | 11 | Attacker |
| 348089 | Hasan Abdulkareem | 26 | 11 | Attacker |
| 265448 | M. Farji | 21 | 21 | Attacker |
| 542697 | Meme | 25 | 10 | Attacker |
| 292253 | Ahmed Hasan Al Reeshawee | 24 | 23 | Defender |
| 15769 | Frans Putros | 32 | 6 | Defender |
| 145465 | Hussein Ali | 23 | 3 | Defender |
| 271444 | Merchas Doski | 26 | 23 | Defender |
| 295394 | Munaf Younus | 29 | 6 | Defender |
| 42261 | Rebin Solaka | 33 | 2 | Defender |
| 296373 | Zayed Tahseen | 24 | 4 | Defender |
| 197933 | Ahmed Basil | 29 | 22 | Goalkeeper |
| 123802 | Fahad Talib | 31 | 1 | Goalkeeper |
| 453431 | Kamil Saad | 21 | 12 | Goalkeeper |
| 542644 | A. Jasim | 21 | 17 | Midfielder |
| 48129 | A. Sher | 23 | 20 | Midfielder |
| 453073 | Akam Rahman | 27 | 5 | Midfielder |
| 47792 | Amir Al Ammari | 28 | 16 | Midfielder |
| 140747 | Ibraheem Bayesh | 25 | 8 | Midfielder |
| 48025 | Kevin Yakob | 25 | 19 | Midfielder |
| 282065 | Youssef Amyn | 22 | 7 | Midfielder |
| 626479 | Z. Ismaeel | 23 | 15 | Midfielder |
| 284295 | Zidane Iqbal | 22 | 14 | Midfielder |


### Ivory Coast (`team_id=1501`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Ivory-Coast`
- National team: `True`
- Players: `28`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 157997 | A. Diallo | 23 | 15 | Attacker |
| 137303 | E. Guessand | 24 | 22 | Attacker |
| 22842 | J. Krasso | 28 | 11 | Attacker |
| 3246 | N. Pépé | 30 | 19 | Attacker |
| 334429 | O. Diakité | 22 | 14 | Attacker |
| 1826 | S. Haller | 31 | 22 | Attacker |
| 1134 | V. Bayo | 28 | 9 | Attacker |
| 3247 | W. Zaha | 33 | 10 | Attacker |
| 513776 | Y. Diomande | 19 | 26 | Attacker |
| 291999 | A. Zohouri | 24 | 5 | Defender |
| 20836 | C. Operi | 28 | 13 | Defender |
| 135068 | E. Agbadou | 28 | 20 | Defender |
| 1807 | E. Ndicka | 26 | 21 | Defender |
| 161747 | G. Doué | 23 | 17 | Defender |
| 22002 | G. Konan | 30 | 3 | Defender |
| 3240 | J. Gbamin | 30 | 25 | Defender |
| 354753 | O. Diomande | 22 | 2 | Defender |
| 48119 | O. Kossounou | 24 | 7 | Defender |
| 18739 | W. Boly | 34 | 12 | Defender |
| 30393 | A. Lafont | 26 | 23 | Goalkeeper |
| 277046 | M. Koné | 23 | 16 | Goalkeeper |
| 64190 | Y. Fofana | 25 | 1 | Goalkeeper |
| 387643 | B. Touré | 19 | 24 | Midfielder |
| 474591 | C. Inao OulaÃ¯ | 19 | 19 | Midfielder |
| 1642 | F. Kessié | 29 | 8 | Midfielder |
| 22149 | I. Sangaré | 28 | 18 | Midfielder |
| 3243 | J. Seri | 34 | 4 | Midfielder |
| 30807 | S. Fofana | 30 | 6 | Midfielder |


### Japan (`team_id=12`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Japan`
- National team: `True`
- Players: `37`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 72155 | A. Ueda | 27 | 9 | Attacker |
| 33224 | D. Maeda | 28 | 11 | Attacker |
| 1942 | J. Ito | 32 | 14 | Attacker |
| 375930 | K. Goto | 20 |  | Attacker |
| 106835 | K. Mitoma | 28 | 7 | Attacker |
| 33838 | K. Saito | 24 | 24 | Attacker |
| 422572 | K. Shiogai | 20 | 14 | Attacker |
| 33321 | Keito Nakamura | 25 | 13 | Attacker |
| 33289 | Koki Ogawa | 28 | 19 | Attacker |
| 106851 | S. Machino | 26 | 18 | Attacker |
| 32862 | T. Kubo | 24 | 10 | Attacker |
| 1101 | T. Minamino | 30 | 8 | Attacker |
| 32902 | Y. Soma | 28 | 7 | Attacker |
| 199143 | Y. Suzuki | 24 | 8 | Attacker |
| 33165 | A. Seko | 25 | 22 | Defender |
| 33095 | D. Hashioka | 26 | 22 | Defender |
| 455193 | H. Mochizuki | 24 | 2 | Defender |
| 351014 | J. Suzuki | 22 | 4 | Defender |
| 38114 | K. Itakura | 28 | 4 | Defender |
| 32954 | S. Taniguchi | 34 | 3 | Defender |
| 307929 | T. Ando | 26 | 16 | Defender |
| 32858 | T. Watanabe | 28 | 4 | Defender |
| 440 | Y. Nagatomo | 39 | 5 | Defender |
| 32887 | Y. Sugawara | 25 | 2 | Defender |
| 33034 | K. Osako | 26 | 1 | Goalkeeper |
| 162482 | L. Kokubo | 24 | 1 | Goalkeeper |
| 304782 | T. Hayakawa | 26 | 12 | Goalkeeper |
| 109381 | T. Nozawa | 23 | 12 | Goalkeeper |
| 199578 | Z. Suzuki | 23 | 1 | Goalkeeper |
| 32966 | A. Tanaka | 27 | 17 | Midfielder |
| 2601 | D. Kamada | 29 | 15 | Midfielder |
| 146586 | J. Fujita | 23 | 7 | Midfielder |
| 33889 | K. Sano | 25 | 5 | Midfielder |
| 2598 | R. Dōan | 27 | 10 | Midfielder |
| 542861 | R. Sato | 19 | 10 | Midfielder |
| 288073 | S. Kitano | 21 | 10 | Midfielder |
| 8500 | W. Endo | 32 | 6 | Midfielder |


### Jordan (`team_id=1548`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Jordan`
- National team: `True`
- Players: `39`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 575283 | A. Azaizeh | 21 | 23 | Attacker |
| 53907 | Ahmad Ersan | 30 | 10 | Attacker |
| 164026 | Ali Olwan | 25 | 9 | Attacker |
| 53913 | Baha&apos; Faisal | 30 | 9 | Attacker |
| 432841 | Ibrahim Sabra | 20 | 18 | Attacker |
| 601853 | M. Taha | 20 | 13 | Attacker |
| 15286 | Mousa Tamari | 28 | 10 | Attacker |
| 568556 | O. Al Fakhouri | 19 | 10 | Attacker |
| 213947 | Yazan Al Naimat | 26 | 11 | Attacker |
| 543038 | A. A. Asad Hajabi | 21 | 3 | Defender |
| 310835 | Abdallah Naseeb | 31 | 3 | Defender |
| 163865 | Adham Al Quraishi | 30 | 23 | Defender |
| 542855 | Ahmad Assaf | 26 | 17 | Defender |
| 542822 | H. Abu Al Dahab | 25 | 4 | Defender |
| 213977 | Hadi Al Hourani | 25 | 5 | Defender |
| 577714 | Issam Smeeri | 26 | 17 | Defender |
| 542710 | M. Abu Hasheesh | 30 | 2 | Defender |
| 102538 | M. Abualnadi | 24 | 16 | Defender |
| 213978 | Saed Al Rosan | 28 | 19 | Defender |
| 72140 | Saleem Obaid | 33 | 18 | Defender |
| 53900 | Yazan Al Arab | 29 | 5 | Defender |
| 140608 | Yousef Abu Al Jazar | 26 | 6 | Defender |
| 631554 | A. Al Talalga | 22 | 22 | Goalkeeper |
| 163884 | Abdallah Al Fakhouri | 25 | 22 | Goalkeeper |
| 658053 | Malek Shalabiya | 38 | 12 | Goalkeeper |
| 163908 | Noureddin Zaid | 32 | 22 | Goalkeeper |
| 140607 | Yazid Abu Layla | 32 | 1 | Goalkeeper |
| 198211 | Amer Jamous | 23 | 6 | Midfielder |
| 542768 | Ibrahim Sa'deh | 25 | 15 | Midfielder |
| 543035 | M. Abu Dahab | 25 | 4 | Midfielder |
| 542856 | M. Al Aldahod | 33 | 14 | Midfielder |
| 651096 | M. Al Daoud | 33 | 15 | Midfielder |
| 123530 | Mahmoud Al Mardi | 32 | 13 | Midfielder |
| 72142 | Mohammed Abu Zurayq | 28 | 7 | Midfielder |
| 310785 | Mohannad Abu Taha | 22 | 20 | Midfielder |
| 213980 | Nizar Al Rashdan | 26 | 21 | Midfielder |
| 140609 | Noor Al Rawabdeh | 28 | 8 | Midfielder |
| 104242 | Rajaei Ayed | 32 | 14 | Midfielder |
| 618026 | Y. Qashi | 20 | 6 | Midfielder |


### Mexico (`team_id=16`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Mexico`
- National team: `True`
- Players: `49`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 291713 | A. González | 22 |  | Attacker |
| 2889 | A. Vega | 28 | 10 | Attacker |
| 1577 | D. Lainez | 25 | 16 | Attacker |
| 6485 | G. Berterame | 27 | 17 | Attacker |
| 36088 | G. Martínez | 30 | 22 | Attacker |
| 248 | H. Lozano | 30 | 22 | Attacker |
| 35532 | J. Quiñones | 28 | 16 | Attacker |
| 341970 | J. Ruvalcaba | 24 | 17 | Attacker |
| 2887 | R. Jiménez | 34 | 9 | Attacker |
| 35645 | Á. Sepúlveda | 34 | 18 | Attacker |
| 2873 | C. Montes | 28 | 3 | Defender |
| 141155 | D. Campillo | 24 |  | Defender |
| 375586 | E.  Águila | 23 |  | Defender |
| 362815 | E. López | 20 | 2 | Defender |
| 127227 | I. Reyes | 25 | 15 | Defender |
| 35773 | J. Angulo | 27 | 14 | Defender |
| 2881 | J. Gallardo | 31 | 23 | Defender |
| 35524 | J. Garza | 25 |  | Defender |
| 290059 | J. Orozco | 23 | 19 | Defender |
| 2878 | J. Sánchez | 28 | 2 | Defender |
| 35544 | J. Vásquez | 27 | 5 | Defender |
| 126751 | K. Álvarez | 26 | 3 | Defender |
| 180734 | R. Juárez | 24 | 15 | Defender |
| 129943 | V. Guzmán | 23 | 22 | Defender |
| 35769 | C. Acevedo | 29 | 12 | Goalkeeper |
| 2098 | G. Ochoa | 40 | 13 | Goalkeeper |
| 270774 | J. Rangel | 25 | 12 | Goalkeeper |
| 35930 | L. Malagón | 28 | 1 | Goalkeeper |
| 35573 | A. Gutiérrez | 25 | 15 | Midfielder |
| 237060 | B. González | 22 | 26 | Midfielder |
| 212233 | B. Gutiérrez | 22 | 15 | Midfielder |
| 2888 | C. Rodríguez | 28 | 8 | Midfielder |
| 359835 | D. García | 22 | 8 | Midfielder |
| 2869 | E. Álvarez | 28 | 4 | Midfielder |
| 51068 | E. Álvarez | 23 | 20 | Midfielder |
| 167014 | F. Ambríz | 22 | 6 | Midfielder |
| 482605 | G. Mora | 17 | 11 | Midfielder |
| 426512 | Iker Jareth Fimbres Ochoa | 20 | 5 | Midfielder |
| 35716 | K. Castañeda | 26 |  | Midfielder |
| 35970 | L. Romo | 30 | 7 | Midfielder |
| 390002 | M. Chávez | 21 | 26 | Midfielder |
| 35981 | M. Ruiz | 25 | 14 | Midfielder |
| 35576 | O. Pineda | 29 | 17 | Midfielder |
| 313383 | O. Vargas | 20 | 18 | Midfielder |
| 2879 | R. Alvarado | 27 | 25 | Midfielder |
| 102851 | R. Ledezma | 25 | 20 | Midfielder |
| 750 | Álvaro Fidalgo | 28 |  | Midfielder |
| 266345 | É. Lira | 25 | 6 | Midfielder |
| 36093 | É. Sánchez | 26 | 14 | Midfielder |


### Morocco (`team_id=31`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Morocco`
- National team: `True`
- Players: `39`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 2722 | A. El Kaabi | 32 | 20 | Attacker |
| 181421 | A. Ezzalzouli | 24 | 17 | Attacker |
| 336659 | C. Talbi | 20 | 21 | Attacker |
| 343320 | E. Ben Seghir | 20 | 13 | Attacker |
| 306979 | H. Igamane | 23 | 7 | Attacker |
| 290740 | Ilias Akhomach | 21 | 16 | Attacker |
| 457101 | M. Zabiri | 20 | 21 | Attacker |
| 36579 | S. Rahimi | 29 | 9 | Attacker |
| 47422 | Y. En-Nesyri | 28 | 19 | Attacker |
| 417830 | A. Ait Boudlal | 19 | 27 | Defender |
| 9 | A. Hakimi | 27 | 2 | Defender |
| 162451 | A. Salah-Eddine | 24 | 26 | Defender |
| 278898 | C. Riad | 22 | 6 | Defender |
| 396198 | I. Baouf | 19 | 4 | Defender |
| 18814 | I. Diop | 28 | 3 | Defender |
| 31386 | J. El Yamiq | 33 | 18 | Defender |
| 194572 | M. Chibi | 32 | 15 | Defender |
| 21694 | N. Aguerd | 29 | 5 | Defender |
| 545 | N. Mazraoui | 28 | 3 | Defender |
| 326183 | R. Halhal | 22 | 4 | Defender |
| 127803 | S. El Karouani | 25 | 3 | Defender |
| 283252 | Z. El Ouahdi | 24 | 11 | Defender |
| 144879 | M. Benabid | 27 | 12 | Goalkeeper |
| 294290 | M. Harrar | 25 | 22 | Goalkeeper |
| 2702 | M. Mohamedi | 36 | 12 | Goalkeeper |
| 2701 | Y. Bounou | 34 | 1 | Goalkeeper |
| 129682 | A. Adli | 25 | 21 | Midfielder |
| 129678 | A. Ounahi | 25 | 8 | Midfielder |
| 340573 | B. El Khannouss | 21 | 23 | Midfielder |
| 744 | Brahim Díaz | 26 | 10 | Midfielder |
| 369544 | Gessime Yassine | 20 | 17 | Midfielder |
| 161897 | I. Saibari | 24 | 11 | Midfielder |
| 146771 | M. Hrimat | 31 | 6 | Midfielder |
| 277003 | N. El Aynaoui | 24 | 24 | Midfielder |
| 284071 | O. Targhalline | 23 | 14 | Midfielder |
| 396202 | Rayane Bounida | 19 | 15 | Midfielder |
| 74 | S. Amrabat | 29 | 4 | Midfielder |
| 415431 | S. El Mourabet | 20 |  | Midfielder |
| 146772 | Y. Belammari | 27 | 28 | Midfielder |


### Netherlands (`team_id=1118`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Netherlands`
- National team: `True`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 38750 | B. Brobbey | 23 | 9 | Attacker |
| 247 | C. Gakpo | 26 | 11 | Attacker |
| 249 | D. Malen | 26 | 18 | Attacker |
| 203762 | E. Emegha | 22 | 9 | Attacker |
| 792 | J. Kluivert | 26 | 19 | Attacker |
| 667 | M. Depay | 31 | 10 | Attacker |
| 544 | N. Lang | 26 | 17 | Attacker |
| 25416 | W. Weghorst | 33 | 9 | Attacker |
| 226 | D. Dumfries | 29 | 22 | Defender |
| 341642 | J. Hato | 19 | 4 | Defender |
| 38746 | J. Timber | 24 | 3 | Defender |
| 38695 | J. van Hecke | 25 | 12 | Defender |
| 37143 | L. Geertruida | 25 | 2 | Defender |
| 532 | M. de Ligt | 26 | 6 | Defender |
| 152849 | M. van de Ven | 24 | 15 | Defender |
| 18861 | N. Aké | 30 | 5 | Defender |
| 375915 | Q. Hartman | 24 | 17 | Defender |
| 194 | S. de Vrij | 33 | 6 | Defender |
| 290 | V. van Dijk | 34 | 4 | Defender |
| 129058 | B. Verbruggen | 23 | 1 | Goalkeeper |
| 37137 | J. Bijlow | 27 | 13 | Goalkeeper |
| 26232 | M. Flekken | 32 | 23 | Goalkeeper |
| 194536 | R. Roefs | 22 | 13 | Goalkeeper |
| 538 | F. de Jong | 28 | 21 | Midfielder |
| 152654 | J. Frimpong | 25 | 12 | Midfielder |
| 37890 | J. Schouten | 28 | 16 | Midfielder |
| 388786 | K. Smit | 19 | 8 | Midfielder |
| 314266 | L. Valente | 22 | 22 | Midfielder |
| 38747 | Q. Timber | 24 | 12 | Midfielder |
| 542 | R. Gravenberch | 23 | 8 | Midfielder |
| 36899 | T. Koopmeiners | 27 | 20 | Midfielder |
| 36902 | T. Reijnders | 27 | 14 | Midfielder |
| 162016 | X. Simons | 22 | 7 | Midfielder |


### New Zealand (`team_id=4673`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `New-Zealand`
- National team: `True`
- Players: `40`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 291397 | A. Greive | 26 | 11 | Attacker |
| 179856 | B. Old | 23 | 19 | Attacker |
| 6938 | B. Waine | 24 | 18 | Attacker |
| 18931 | C. Wood | 34 | 11 | Attacker |
| 94333 | E. Just | 25 | 11 | Attacker |
| 158688 | J. Randall | 23 | 7 | Attacker |
| 6865 | K. Barbarouses | 35 | 17 | Attacker |
| 26161 | L. Rogerson | 27 | 18 | Attacker |
| 94380 | M. Mata | 25 | 27 | Attacker |
| 94354 | O. van Hattum | 23 | 18 | Attacker |
| 51236 | B. Tuiloma | 30 | 6 | Defender |
| 6932 | C. Elliot | 26 | 21 | Defender |
| 7025 | D. Ingham | 26 | 16 | Defender |
| 94332 | D. Wilkins | 26 | 3 | Defender |
| 210165 | F. Surman | 22 | 14 | Defender |
| 94405 | F. de Vries | 31 | 3 | Defender |
| 36782 | J. McGarry | 27 | 15 | Defender |
| 6931 | L. Cacace | 25 | 13 | Defender |
| 376246 | L. Kelly-Heald | 20 | 13 | Defender |
| 51149 | M. Boxall | 37 | 5 | Defender |
| 94344 | N. Pijnaker | 26 | 3 | Defender |
| 6852 | S. Roux | 32 | 15 | Defender |
| 94352 | S. Sutton | 24 | 3 | Defender |
| 94346 | T. Payne | 31 | 2 | Defender |
| 51307 | T. Smith | 35 | 15 | Defender |
| 430835 | Tyler Bindon | 20 | 4 | Defender |
| 94360 | A. Paulsen | 23 | 12 | Goalkeeper |
| 18110 | M. Crocombe | 32 | 15 | Goalkeeper |
| 20356 | N. Tzanev | 29 | 22 | Goalkeeper |
| 6922 | O. Sail | 29 | 22 | Goalkeeper |
| 6934 | A. Rufer | 29 | 16 | Midfielder |
| 38840 | C. Howieson | 31 | 18 | Midfielder |
| 20471 | C. Lewis | 28 | 15 | Midfielder |
| 94322 | C. McCowatt | 26 | 17 | Midfielder |
| 376250 | F. Conchie | 22 | 16 | Midfielder |
| 94541 | J. Bell | 26 | 8 | Midfielder |
| 180455 | M. Garbett | 23 | 7 | Midfielder |
| 179862 | M. Stamenić | 23 | 32 | Midfielder |
| 242 | R. Thomas | 31 | 23 | Midfielder |
| 6935 | S. Singh | 26 | 10 | Midfielder |


### Norway (`team_id=1090`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Norway`
- National team: `True`
- Players: `34`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 133916 | A. Heggebø | 24 | 15 | Attacker |
| 314511 | A. Nusa | 20 | 20 | Attacker |
| 301528 | A. Schjelderup | 21 | 10 | Attacker |
| 8492 | A. Sørloth | 30 | 7 | Attacker |
| 1100 | E. Haaland | 25 | 9 | Attacker |
| 39073 | J. Hauge | 26 | 15 | Attacker |
| 2032 | J. Strand Larsen | 25 | 11 | Attacker |
| 39279 | A. Hanche-Olsen | 28 | 21 | Defender |
| 265782 | D. Møller Wolfe | 23 | 5 | Defender |
| 416062 | E. Helland | 20 | 5 | Defender |
| 39058 | F. Bjørkan | 27 | 15 | Defender |
| 180937 | H. Falchener | 22 |  | Defender |
| 24845 | J. Ryerson | 28 | 14 | Defender |
| 1119 | K. Ajer | 27 | 3 | Defender |
| 18967 | L. Østigård | 26 | 4 | Defender |
| 39362 | M. Pedersen | 25 | 16 | Defender |
| 39083 | O. Bjørtuft | 27 | 4 | Defender |
| 265444 | S. Langås | 24 | 21 | Defender |
| 191740 | S. Sebulonsen | 25 | 2 | Defender |
| 39254 | T. Heggem | 26 | 17 | Defender |
| 39082 | E. Selvik | 28 | 13 | Goalkeeper |
| 57429 | M. Dyngeland | 30 | 12 | Goalkeeper |
| 264378 | S. Tangvik | 23 | 13 | Goalkeeper |
| 39325 | V. Myhra | 29 | 13 | Goalkeeper |
| 19172 | Ø. Nyland | 35 | 1 | Goalkeeper |
| 39115 | A. Dønnum | 27 | 19 | Midfielder |
| 39066 | F. Myhre | 26 | 16 | Midfielder |
| 277745 | K. Arnstad | 22 | 19 | Midfielder |
| 39143 | K. Thorstvedt | 26 | 18 | Midfielder |
| 36980 | M. Thorsby | 29 | 2 | Midfielder |
| 278133 | Oscar Bobb | 22 |  | Midfielder |
| 39064 | P. Berg | 28 | 6 | Midfielder |
| 1934 | S. Berge | 27 | 8 | Midfielder |
| 277930 | T. Aasgaard | 23 | 23 | Midfielder |


### Panama (`team_id=11`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Panama`
- National team: `True`
- Players: `51`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 2981 | A. Arroyo | 32 | 18 | Attacker |
| 292396 | A. Londoño | 24 | 11 | Attacker |
| 2978 | A. Quintero | 38 | 19 | Attacker |
| 51648 | C. Waterman | 34 | 18 | Attacker |
| 57875 | C. Yanis | 29 | 21 | Attacker |
| 535837 | G. Herbert | 20 | 10 | Attacker |
| 445633 | G. Herrera | 20 | 9 | Attacker |
| 305698 | H. Hurtado | 27 |  | Attacker |
| 96615 | I. Díaz | 28 | 10 | Attacker |
| 2983 | J. Fajardo | 32 | 17 | Attacker |
| 39612 | J. Murillo | 30 | 13 | Attacker |
| 544681 | K. Barria | 18 |  | Attacker |
| 336526 | K. Lenis | 24 | 13 | Attacker |
| 2982 | O. Browne | 31 | 21 | Attacker |
| 57910 | T. Rodríguez | 26 | 9 | Attacker |
| 46855 | Y. Bárcenas | 32 | 11 | Attacker |
| 7197 | A. Andrade | 27 | 16 | Defender |
| 2973 | A. Murillo | 29 | 23 | Defender |
| 2975 | C. Blackman | 27 | 2 | Defender |
| 71230 | C. Harvey | 25 | 14 | Defender |
| 328148 | E. Fariña | 24 | 5 | Defender |
| 2971 | F. Escobar | 30 | 4 | Defender |
| 57805 | I. Anderson | 28 | 3 | Defender |
| 57739 | J. Córdoba | 24 | 3 | Defender |
| 57803 | J. Gutiérrez | 27 | 23 | Defender |
| 535861 | J. Hall | 19 | 14 | Defender |
| 57667 | J. Ramos | 28 | 3 | Defender |
| 577841 | J. Rivera | 27 |  | Defender |
| 57775 | K. Galván | 29 | 6 | Defender |
| 407597 | M. Krug | 19 | 13 | Defender |
| 57728 | O. Córdoba | 31 | 4 | Defender |
| 304057 | O. Davis | 23 | 20 | Defender |
| 81659 | R. Miller | 33 | 25 | Defender |
| 57890 | R. Peralta | 32 | 5 | Defender |
| 2970 | É. Davis | 34 | 15 | Defender |
| 57861 | C. Samudio | 31 | 12 | Goalkeeper |
| 57725 | E. Roberts | 31 | 1 | Goalkeeper |
| 458846 | JD Gunn | 25 | 12 | Goalkeeper |
| 2967 | L. Mejía | 34 | 1 | Goalkeeper |
| 2968 | O. Mosquera | 31 | 22 | Goalkeeper |
| 57807 | A. Carrasquilla | 27 | 8 | Midfielder |
| 2977 | A. Godoy | 35 | 20 | Midfielder |
| 535870 | A. Knight | 23 | 6 | Midfielder |
| 554208 | C. Martinez | 28 | 6 | Midfielder |
| 153384 | D. Aparicio | 25 |  | Midfielder |
| 337359 | E. Cedeño | 22 | 13 | Midfielder |
| 2979 | J. Rodríguez | 27 | 7 | Midfielder |
| 57904 | J. Welch | 26 | 14 | Midfielder |
| 635194 | M. Sanchez | 36 | 8 | Midfielder |
| 199464 | R. Phillips | 24 | 7 | Midfielder |
| 325468 | Á. Caicedo | 26 |  | Midfielder |


### Paraguay (`team_id=2380`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Paraguay`
- National team: `True`
- Players: `29`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 95460 | A. Arce | 30 | 18 | Attacker |
| 2522 | A. Sanabria | 29 | 9 | Attacker |
| 6483 | G. Ávalos | 35 | 19 | Attacker |
| 2507 | M. Almirón | 31 | 10 | Attacker |
| 95314 | R. Martínez | 29 | 21 | Attacker |
| 2521 | Á. Romero | 33 | 11 | Attacker |
| 70723 | A. Benítez | 31 | 13 | Defender |
| 70549 | A. Duarte | 25 | 5 | Defender |
| 278373 | A. Sandez | 24 | 6 | Defender |
| 48376 | B. Riveros | 27 | 14 | Defender |
| 475598 | D. León | 18 | 4 | Defender |
| 2502 | G. Gómez | 32 | 15 | Defender |
| 35808 | G. Velázquez | 34 | 2 | Defender |
| 2499 | J. Alonso | 32 | 6 | Defender |
| 195992 | J. Cáceres | 25 | 4 | Defender |
| 6168 | O. Alderete | 29 | 3 | Defender |
| 2496 | J. Espínola | 31 | 1 | Goalkeeper |
| 70852 | O. Gill | 25 | 22 | Goalkeeper |
| 535737 | R. Fernandez | 37 | 12 | Goalkeeper |
| 6236 | A. Cubas | 29 | 14 | Midfielder |
| 2514 | A. Romero | 30 | 10 | Midfielder |
| 70767 | B. Ojeda | 25 | 20 | Midfielder |
| 195107 | D. Bobadilla | 24 | 16 | Midfielder |
| 278370 | D. Gómez | 22 | 8 | Midfielder |
| 382947 | H. Cuenca | 20 | 23 | Midfielder |
| 70747 | J. Enciso | 21 | 19 | Midfielder |
| 363117 | L. Romero | 23 | 13 | Midfielder |
| 305832 | M. Galarza | 23 | 23 | Midfielder |
| 196298 | R. Sosa | 26 | 7 | Midfielder |


### Portugal (`team_id=27`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Portugal`
- National team: `True`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 282126 | Carlos Forbs | 21 | 7 | Attacker |
| 874 | Cristiano Ronaldo | 40 | 7 | Attacker |
| 161585 | Francisco Conceição | 23 | 19 | Attacker |
| 41585 | Gonçalo Ramos | 24 | 9 | Attacker |
| 583 | João Félix | 26 | 11 | Attacker |
| 41111 | Paulinho | 33 | 9 | Attacker |
| 1864 | Pedro Neto | 25 | 18 | Attacker |
| 22236 | Rafael Leão | 26 | 17 | Attacker |
| 41112 | Trincão | 26 | 16 | Attacker |
| 331832 | António Silva | 22 | 4 | Defender |
| 886 | Diogo Dalot | 26 | 5 | Defender |
| 265595 | Gonçalo Inácio | 24 | 14 | Defender |
| 855 | João Cancelo | 31 | 20 | Defender |
| 263482 | Nuno Mendes | 23 | 19 | Defender |
| 41577 | Nuno Tavares | 25 | 14 | Defender |
| 130 | Nélson Semedo | 32 | 2 | Defender |
| 336671 | Renato Veiga | 22 | 13 | Defender |
| 567 | Rúben Dias | 28 | 3 | Defender |
| 369 | Diogo Costa | 26 | 1 | Goalkeeper |
| 1590 | José Sá | 32 | 12 | Goalkeeper |
| 361433 | João Carvalho | 21 | 1 | Goalkeeper |
| 41960 | Ricardo Velho | 27 | 12 | Goalkeeper |
| 46672 | Rui Silva | 31 | 22 | Goalkeeper |
| 636 | Bernardo Silva | 31 | 10 | Midfielder |
| 1485 | Bruno Fernandes | 31 | 8 | Midfielder |
| 335051 | João Neves | 21 | 15 | Midfielder |
| 41104 | João Palhinha | 30 | 6 | Midfielder |
| 41621 | Matheus Nunes | 27 | 18 | Midfielder |
| 18748 | Pote | 27 | 17 | Midfielder |
| 2676 | Rúben Neves | 28 | 21 | Midfielder |
| 190485 | Samú Costa | 25 | 6 | Midfielder |
| 128384 | Vitinha | 25 | 23 | Midfielder |


### Qatar (`team_id=1569`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Qatar`
- National team: `True`
- Players: `22`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 2544 | Akram Afif | 29 | 10 | Attacker |
| 42075 | Edmilson Junior | 31 | 11 | Attacker |
| 542531 | M. Gouda | 20 | 11 | Attacker |
| 42089 | Mohammed Muntari | 32 | 9 | Attacker |
| 542542 | A. Al Hussain | 22 | 4 | Defender |
| 542548 | A. Al Oui | 20 | 13 | Defender |
| 2535 | Assim Madibo | 29 | 23 | Defender |
| 175439 | Homam Ahmed | 26 | 14 | Defender |
| 200981 | Jassem Gaber | 23 | 8 | Defender |
| 42288 | Lucas Mendes | 35 | 3 | Defender |
| 42060 | Sultan Al Braik | 29 | 18 | Defender |
| 42421 | Youssef Ayman | 26 | 15 | Defender |
| 42207 | Mahmud Abunada | 25 | 21 | Goalkeeper |
| 42021 | Meshaal Barsham | 27 | 22 | Goalkeeper |
| 42055 | Shehab Ellethy | 25 | 1 | Goalkeeper |
| 2533 | Abdulaziz Hatem | 35 | 6 | Midfielder |
| 2539 | Ahmed Fathi | 32 | 20 | Midfielder |
| 534032 | Ali | 24 | 12 | Midfielder |
| 542536 | G. Laye | 27 | 2 | Midfielder |
| 283174 | Mohamed Al Manai | 22 | 17 | Midfielder |
| 42180 | Mohammed Waad | 26 | 4 | Midfielder |
| 2541 | Tarek Salman | 28 | 5 | Midfielder |


### Saudi Arabia (`team_id=23`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Saudi-Arabia`
- National team: `True`
- Players: `43`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 578901 | A. S. Al Aliwa | 21 | 7 | Attacker |
| 44382 | Abdullah Al Hamdan | 26 | 19 | Attacker |
| 44586 | Abdulrahman Al Obud | 30 | 20 | Attacker |
| 147812 | Ayman Yahya | 24 | 8 | Attacker |
| 44324 | Feras Al Brikan | 25 | 9 | Attacker |
| 44701 | Khalid Al Ghannam | 25 | 16 | Attacker |
| 381176 | Marwan Al Sahafi | 21 | 20 | Attacker |
| 44551 | Saleh Al Shehri | 32 | 11 | Attacker |
| 2639 | Sultan Mandash | 31 |  | Attacker |
| 44475 | Abdulelah Al Amri | 28 | 4 | Defender |
| 44507 | Ali Lajami | 29 | 3 | Defender |
| 44367 | Ali Majrashi | 26 | 2 | Defender |
| 44335 | Hassan Kadesh | 33 | 14 | Defender |
| 44362 | Hassan Tambakti | 26 | 5 | Defender |
| 543059 | J. Thakri | 24 | 3 | Defender |
| 44684 | Khalifah Al Dawsari | 26 | 4 | Defender |
| 369413 | Mohammed Bakor | 21 | 17 | Defender |
| 363310 | Mohammed Essa Harbush | 22 | 5 | Defender |
| 2628 | Muteb Al Mufarrij | 29 | 4 | Defender |
| 134995 | Nawaf Boushal | 26 | 13 | Defender |
| 542829 | R. Hamidou | 23 | 2 | Defender |
| 44594 | Saud Abdulhamid | 26 | 12 | Defender |
| 44337 | Waleed Al Ahmad | 26 | 14 | Defender |
| 310827 | Abdulrahman Al Sanbi | 24 | 21 | Goalkeeper |
| 44449 | Ahmed Al Kassar | 34 | 22 | Goalkeeper |
| 543009 | M. Al Rubaie | 28 | 22 | Goalkeeper |
| 44411 | Mohammed Al Owais | 34 | 21 | Goalkeeper |
| 193288 | Nawaf Al Aqidi | 25 | 1 | Goalkeeper |
| 44360 | Raghed Najjar | 29 | 22 | Goalkeeper |
| 44315 | Abdullah Al Khaibari | 29 | 15 | Midfielder |
| 44349 | Mohamed Kanno | 31 | 23 | Midfielder |
| 403087 | Mohammed Abu Al Shamat | 23 | 12 | Midfielder |
| 44510 | Mohammed Al-Majhad | 27 | 20 | Midfielder |
| 326984 | Mohammed Mater Mohsin Mahzari | 23 | 23 | Midfielder |
| 442343 | Murad Al Hawsawi | 24 | 16 | Midfielder |
| 306380 | Musab Al Juwayr | 22 | 10 | Midfielder |
| 578970 | N. Masoud | 24 | 6 | Midfielder |
| 44339 | Nasser Al Dawsari | 27 | 6 | Midfielder |
| 44340 | Salem Al Dawsari | 34 | 10 | Midfielder |
| 44341 | Salman Al Faraj | 36 | 7 | Midfielder |
| 44374 | Turki Al Ammar | 26 | 19 | Midfielder |
| 312652 | Waheb Saleh | 23 | 18 | Midfielder |
| 269172 | Ziyad Al Johani | 24 | 8 | Midfielder |


### Scotland (`team_id=1108`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Scotland`
- National team: `True`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 343576 | B. Doak | 20 | 17 | Attacker |
| 19524 | C. Adams | 29 | 10 | Attacker |
| 8794 | G. Hirst | 26 | 18 | Attacker |
| 126690 | K. Bowie | 23 | 20 | Attacker |
| 45307 | L. Dykes | 30 | 9 | Attacker |
| 45175 | L. Shankland | 30 | 20 | Attacker |
| 282767 | T. Conway | 23 | 9 | Attacker |
| 44871 | A. Hickey | 23 | 2 | Defender |
| 1115 | A. Ralston | 27 | 22 | Defender |
| 289 | A. Robertson | 31 | 3 | Defender |
| 19066 | G. Hanley | 34 | 5 | Defender |
| 1111 | J. Hendry | 30 | 13 | Defender |
| 44865 | J. Souttar | 29 | 15 | Defender |
| 1117 | K. Tierney | 28 | 6 | Defender |
| 268595 | M. Johnston | 22 | 22 | Defender |
| 1743 | R. McCrorie | 27 | 21 | Defender |
| 44811 | S. McKenna | 29 | 16 | Defender |
| 18933 | A. Gunn | 29 | 1 | Goalkeeper |
| 1106 | C. Gordon | 43 | 1 | Goalkeeper |
| 44937 | L. Kelly | 29 | 12 | Goalkeeper |
| 1104 | S. Bain | 34 | 21 | Goalkeeper |
| 68466 | A. Irving | 25 |  | Midfielder |
| 130423 | B. Gilmour | 24 | 8 | Midfielder |
| 138460 | C. Barron | 23 | 14 | Midfielder |
| 433272 | Findlay Curtis | 19 | 22 | Midfielder |
| 19191 | J.  McGinn | 31 | 7 | Midfielder |
| 64315 | J. Mulligan | 23 | 8 | Midfielder |
| 19077 | K. McLean | 33 | 23 | Midfielder |
| 44814 | L. Ferguson | 26 | 19 | Midfielder |
| 343558 | L. Miller | 19 | 14 | Midfielder |
| 1125 | R. Christie | 30 | 11 | Midfielder |
| 903 | S. McTominay | 29 | 4 | Midfielder |


### Senegal (`team_id=13`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Senegal`
- National team: `True`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 400948 | Assane Diao | 20 | 7 | Attacker |
| 22015 | B. Dia | 29 | 9 | Attacker |
| 284072 | B. Dieng | 25 | 9 | Attacker |
| 14379 | C. Ndiaye | 30 | 12 | Attacker |
| 20534 | C. Sabaly | 26 | 21 | Attacker |
| 20535 | H. Diallo | 30 | 20 | Attacker |
| 446249 | I. Mbaye | 17 | 27 | Attacker |
| 18592 | I. Ndiaye | 25 | 13 | Attacker |
| 2218 | I. Sarr | 27 | 18 | Attacker |
| 386481 | M. Diakhon | 20 | 20 | Attacker |
| 283058 | N. Jackson | 24 | 11 | Attacker |
| 203456 | O. Niang | 24 | 22 | Attacker |
| 304 | S. Mané | 33 | 10 | Attacker |
| 313937 | A. Mendy | 21 | 24 | Defender |
| 8450 | A. Seck | 33 | 4 | Defender |
| 409303 | E. Diouf | 21 | 25 | Defender |
| 158121 | I. Jakobs | 26 | 14 | Defender |
| 318 | K. Koulibaly | 34 | 3 | Defender |
| 25916 | M. Niakhaté | 29 | 19 | Defender |
| 276184 | M. Sarr | 20 | 2 | Defender |
| 358431 | N. Mendy | 21 |  | Defender |
| 119853 | M. Diaw | 32 | 23 | Goalkeeper |
| 20566 | Y. Diouf | 26 | 1 | Goalkeeper |
| 2986 | É. Mendy | 33 | 16 | Goalkeeper |
| 327631 | H. Diarra | 21 | 7 | Midfielder |
| 371839 | I. Camara | 22 | 14 | Midfielder |
| 2990 | I. Gueye | 36 | 5 | Midfielder |
| 81 | K. Diatta | 26 | 15 | Midfielder |
| 374058 | L. Camara | 21 | 8 | Midfielder |
| 344813 | M. Camara | 22 | 28 | Midfielder |
| 41552 | P. Ciss | 31 | 6 | Midfielder |
| 20696 | P. Gueye | 26 | 26 | Midfielder |
| 237129 | P. Sarr | 23 | 17 | Midfielder |


### South Africa (`team_id=1531`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `South-Africa`
- National team: `True`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 46641 | B. Hlongwane | 25 | 12 | Attacker |
| 201354 | E. Makgopa | 25 | 23 | Attacker |
| 330170 | E. Mokwana | 26 | 12 | Attacker |
| 98936 | L. Foster | 25 | 9 | Attacker |
| 483109 | M. Nkota | 21 | 11 | Attacker |
| 179893 | O. Appollis | 24 | 7 | Attacker |
| 414149 | R. Mofokeng | 21 | 10 | Attacker |
| 430077 | S. Campbell | 20 | 24 | Attacker |
| 354831 | T. Maseko | 22 | 12 | Attacker |
| 295977 | T. Moremi | 25 | 8 | Attacker |
| 46334 | A. Modiba | 30 | 6 | Defender |
| 406752 | I. Okon | 21 | 5 | Defender |
| 46601 | K. Mudau | 30 | 20 | Defender |
| 474630 | K. Ndamase | 21 | 3 | Defender |
| 510799 | M. Mbokazi | 20 | 14 | Defender |
| 46458 | N. Sibisi | 30 | 19 | Defender |
| 430078 | S. Kabini | 21 | 18 | Defender |
| 46365 | S. Ngezana | 28 | 21 | Defender |
| 461412 | T. Smith | 20 | 2 | Defender |
| 46245 | R. Goss | 31 | 22 | Goalkeeper |
| 278387 | R. Leaner | 27 | 1 | Goalkeeper |
| 3275 | R. Williams | 33 | 1 | Goalkeeper |
| 46417 | S. Chaine | 29 | 16 | Goalkeeper |
| 99017 | B. Aubaas | 30 | 15 | Midfielder |
| 268710 | J. Adams | 24 | 8 | Midfielder |
| 46344 | S. Mbule | 27 | 17 | Midfielder |
| 158433 | S. Sithole | 26 | 13 | Midfielder |
| 330174 | T. Matuludi | 26 | 25 | Midfielder |
| 194430 | T. Mbatha | 25 | 5 | Midfielder |
| 3287 | T. Mokoena | 28 | 4 | Midfielder |
| 3289 | T. Zwane | 36 | 11 | Midfielder |


### South Korea (`team_id=17`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `South-Korea`
- National team: `True`
- Players: `32`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 34211 | Cho Gue-Sung | 27 | 9 | Attacker |
| 24888 | Hwang Hee-Chan | 29 | 11 | Attacker |
| 237047 | Jeong Sang-Bin | 23 | 11 | Attacker |
| 34710 | Oh Hyeon-Gyu | 24 | 9 | Attacker |
| 186 | Son Heung-Min | 33 | 7 | Attacker |
| 423708 | Yang Min-Hyeok | 19 | 17 | Attacker |
| 34239 | Cho Yu-Min | 29 | 14 | Defender |
| 356237 | Kim Ji-Soo | 21 | 23 | Defender |
| 34496 | Kim Ju-Sung | 25 | 4 | Defender |
| 2897 | Kim Min-Jae | 29 | 4 | Defender |
| 2912 | Kim Moon-Hwan | 30 | 15 | Defender |
| 34418 | Kim Tae-Hyeon | 25 | 26 | Defender |
| 237218 | Lee Han-Beom | 23 | 16 | Defender |
| 34420 | Lee Myung-Jae | 32 | 3 | Defender |
| 237220 | Lee Tae-Seok | 23 | 3 | Defender |
| 197985 | Seol Young-Woo | 27 | 22 | Defender |
| 2890 | Jo Hyeon-Woo | 34 | 21 | Goalkeeper |
| 2892 | Kim Seung-Gyu | 35 | 1 | Goalkeeper |
| 34374 | Song Bum-Keun | 28 | 1 | Goalkeeper |
| 357286 | Bae Jun-Ho | 22 | 17 | Midfielder |
| 237050 | Eom Ji-Sung | 23 | 18 | Midfielder |
| 2901 | Hwang In-Beom | 29 | 6 | Midfielder |
| 280358 | J. Castrop | 22 | 13 | Midfielder |
| 34168 | Kim Jin-Gyu | 28 | 6 | Midfielder |
| 137296 | Kwon Hyeok-Kyu | 24 | 16 | Midfielder |
| 34431 | Lee Dong-Gyeong | 28 | 10 | Midfielder |
| 2906 | Lee Jae-Sung | 33 | 10 | Midfielder |
| 927 | Lee Kang-In | 24 | 18 | Midfielder |
| 2909 | Paik Seung-Ho | 28 | 5 | Midfielder |
| 99211 | Park Jin-Seop | 30 | 5 | Midfielder |
| 224652 | Seo Min-Woo | 27 | 23 | Midfielder |
| 33937 | Won Du-Jae | 28 | 19 | Midfielder |


### Spain (`team_id=9`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Spain`
- National team: `True`
- Players: `35`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 47317 | Barrenetxea | 24 | 11 | Attacker |
| 47348 | Borja Iglesias | 32 | 9 | Attacker |
| 931 | Ferran Torres | 25 | 7 | Attacker |
| 128582 | Jorge de Frutos | 28 | 2 | Attacker |
| 386828 | Lamine Yamal | 18 | 19 | Attacker |
| 47323 | Mikel Oyarzabal | 28 | 21 | Attacker |
| 358628 | Samu | 21 | 3 | Attacker |
| 338751 | Víctor Muñoz | 22 |  | Attacker |
| 184226 | Yeremy Pino | 23 | 11 | Attacker |
| 182219 | Álex Baena | 24 | 16 | Attacker |
| 622 | Aymeric Laporte | 31 | 14 | Defender |
| 333682 | Cristhian Mosquera | 21 | 3 | Defender |
| 361497 | D. Huijsen | 20 | 5 | Defender |
| 47278 | Dani Vivian | 26 | 4 | Defender |
| 47380 | Marc Cucurella | 27 | 22 | Defender |
| 753 | Marcos Llorente | 30 | 5 | Defender |
| 396623 | Pau Cubarsí Paredes | 18 | 15 | Defender |
| 47519 | Pedro Porro | 26 | 12 | Defender |
| 47301 | Robin Le Normand | 29 | 3 | Defender |
| 563 | Álex Grimaldo | 30 | 3 | Defender |
| 19465 | David Raya | 30 | 1 | Goalkeeper |
| 47270 | Unai Simón | 28 | 23 | Goalkeeper |
| 47269 | Álex Remiro | 30 | 13 | Goalkeeper |
| 47516 | Aleix García | 28 | 20 | Midfielder |
| 930 | Carlos Soler | 28 | 19 | Midfielder |
| 1323 | Dani Olmo | 27 | 10 | Midfielder |
| 328 | Fabián Ruiz | 29 | 8 | Midfielder |
| 340626 | Fermín | 22 | 19 | Midfielder |
| 443162 | Jesús Rodríguez | 20 | 11 | Midfielder |
| 47315 | Martín Zubimendi | 26 | 18 | Midfielder |
| 47311 | Mikel Merino | 29 | 6 | Midfielder |
| 336594 | Pablo Barrios | 22 | 2 | Midfielder |
| 1697 | Pablo Fornals | 29 | 17 | Midfielder |
| 133609 | Pedri | 23 | 20 | Midfielder |
| 44 | Rodri | 29 | 16 | Midfielder |


### Sweden (`team_id=5`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Sweden`
- National team: `True`
- Players: `31`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 47696 | A. Bernhardsson | 27 | 21 | Attacker |
| 153430 | A. Elanga | 23 | 11 | Attacker |
| 2864 | A. Isak | 26 | 9 | Attacker |
| 48002 | B. Nygren | 24 | 10 | Attacker |
| 15683 | G. Nilsson | 28 | 9 | Attacker |
| 338958 | R. Bardghji | 20 | 14 | Attacker |
| 18979 | V. Gyökeres | 27 | 17 | Attacker |
| 47988 | C. Starfelt | 30 | 15 | Defender |
| 2855 | E. Krafth | 31 | 20 | Defender |
| 47969 | G. Gudmundsson | 26 | 5 | Defender |
| 137721 | G. Lagerbielke | 25 | 2 | Defender |
| 137976 | I. Hien | 26 | 4 | Defender |
| 889 | V. Lindelöf | 31 | 3 | Defender |
| 48033 | J. Widell Zetterström | 27 | 1 | Goalkeeper |
| 2851 | K. Nordfeldt | 36 | 23 | Goalkeeper |
| 278454 | M. Ellborg | 22 | 12 | Goalkeeper |
| 193328 | N. Törnqvist | 23 | 1 | Goalkeeper |
| 158700 | V. Johansson | 27 | 6 | Goalkeeper |
| 350850 | B. Zeneli | 23 | 22 | Midfielder |
| 198654 | D. Svensson | 23 | 8 | Midfielder |
| 47985 | E. Holm | 25 | 6 | Midfielder |
| 8486 | E. Smith | 28 | 13 | Midfielder |
| 226765 | E. Stroud | 23 |  | Midfielder |
| 239472 | G. Lundgren | 30 | 11 | Midfielder |
| 161504 | H. Johansson | 28 | 6 | Midfielder |
| 335094 | H. Larsson | 21 | 20 | Midfielder |
| 48047 | J. Karlström | 30 | 16 | Midfielder |
| 347316 | L. Bergvall | 19 | 7 | Midfielder |
| 30484 | M. Svanberg | 26 | 19 | Midfielder |
| 160925 | T. Ali | 27 | 21 | Midfielder |
| 265820 | Y. Ayari | 22 | 18 | Midfielder |


### Switzerland (`team_id=15`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Switzerland`
- National team: `True`
- Players: `33`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 48649 | A. Zeqiri | 26 | 14 | Attacker |
| 421 | B. Embolo | 28 | 7 | Attacker |
| 952 | C. Fassnacht | 32 | 16 | Attacker |
| 48497 | C. Itten | 29 | 19 | Attacker |
| 48648 | D. Ndoye | 25 | 11 | Attacker |
| 163032 | F. Rieder | 23 | 22 | Attacker |
| 265372 | I. Schmidt | 26 | 23 | Attacker |
| 48389 | N. Okafor | 25 | 9 | Attacker |
| 162414 | A. Amenda | 22 | 18 | Defender |
| 180320 | A. Bajrami | 23 | 19 | Defender |
| 999 | B. Omeragić | 23 | 6 | Defender |
| 48372 | E. Cömert | 27 | 18 | Defender |
| 349344 | L. Jaquez | 22 | 20 | Defender |
| 5 | M. Akanji | 30 | 5 | Defender |
| 48489 | M. Muheim | 27 | 2 | Defender |
| 2803 | N. Elvedi | 29 | 4 | Defender |
| 1631 | R. Rodríguez | 33 | 13 | Defender |
| 48378 | S. Widmer | 32 | 3 | Defender |
| 25282 | G. Kobel | 28 | 1 | Goalkeeper |
| 123468 | M. Keller | 23 | 21 | Goalkeeper |
| 1142 | Y. Mvogo | 31 | 12 | Goalkeeper |
| 264705 | A. Jashari | 23 | 20 | Midfielder |
| 290646 | A. Sanches | 22 | 10 | Midfielder |
| 957 | D. Sow | 28 | 15 | Midfielder |
| 2810 | D. Zakaria | 29 | 6 | Midfielder |
| 1464 | G. Xhaka | 33 | 10 | Midfielder |
| 406244 | J. Manzambi | 20 | 9 | Midfielder |
| 277862 | Joël Monteiro | 26 | 14 | Midfielder |
| 951 | M. Aebischer | 28 | 20 | Midfielder |
| 2807 | R. Freuler | 33 | 8 | Midfielder |
| 48471 | R. Vargas | 27 | 17 | Midfielder |
| 1014 | S. Sohm | 24 | 8 | Midfielder |
| 48491 | V. Sierro | 30 | 16 | Midfielder |


### Tunisia (`team_id=28`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Tunisia`
- National team: `True`
- Players: `30`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 42012 | E. Achouri | 26 | 7 | Attacker |
| 2962 | F. Chaouat | 29 | 19 | Attacker |
| 344862 | H. Mastouri | 28 | 9 | Attacker |
| 2958 | N. Sliti | 33 | 23 | Attacker |
| 16933 | S. Jaziri | 32 | 27 | Attacker |
| 264419 | S. Ltaief | 25 | 7 | Attacker |
| 57518 | S. Tounekti | 23 | 26 | Attacker |
| 49583 | A. Abdi | 32 | 2 | Defender |
| 393977 | A. Arous | 21 | 24 | Defender |
| 2947 | A. Maâloul | 35 | 12 | Defender |
| 2945 | D. Bronn | 30 | 6 | Defender |
| 49437 | M. Ben Ali | 30 | 14 | Defender |
| 50030 | M. Talbi | 27 | 3 | Defender |
| 8990 | N. Ghandri | 30 | 18 | Defender |
| 1597 | Y. Meriah | 32 | 4 | Defender |
| 18942 | Y. Valery | 26 | 20 | Defender |
| 49424 | A. Dahmen | 28 | 16 | Goalkeeper |
| 49610 | B. Ben Saïd | 33 | 22 | Goalkeeper |
| 199523 | N. Farhati | 25 | 1 | Goalkeeper |
| 49423 | S. Ben Hsan | 29 | 16 | Goalkeeper |
| 323974 | E. Saad | 26 | 8 | Midfielder |
| 21587 | E. Skhiri | 30 | 17 | Midfielder |
| 2957 | F. Sassi | 33 | 13 | Midfielder |
| 67195 | H. Mahmoud | 25 | 15 | Midfielder |
| 180560 | H. Mejbri | 22 | 10 | Midfielder |
| 49636 | Houssem Teka | 25 | 25 | Midfielder |
| 310196 | Ismaël Gharbi | 21 | 11 | Midfielder |
| 49469 | M. Ben Ouanes | 31 | 21 | Midfielder |
| 49404 | M. Ben Romdhane | 26 | 5 | Midfielder |
| 375608 | M. Neffati | 21 | 17 | Midfielder |


### Türkiye (`team_id=777`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Turkey`
- National team: `True`
- Players: `27`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 161790 | A. Şimşir | 23 | 20 | Attacker |
| 63274 | B. Yılmaz | 25 | 9 | Attacker |
| 388570 | D. Gül | 21 | 13 | Attacker |
| 142959 | K. Aktürkoğlu | 27 | 7 | Attacker |
| 339883 | K. Yıldız | 20 | 11 | Attacker |
| 454 | Y. Akgün | 25 | 21 | Attacker |
| 49857 | İ. Kahveci | 30 | 17 | Attacker |
| 61837 | A. Bardakcı | 31 | 14 | Defender |
| 50057 | E. Elmalı | 25 | 3 | Defender |
| 1361 | F. Kadıoğlu | 26 | 20 | Defender |
| 25448 | K. Ayhan | 31 | 22 | Defender |
| 30521 | M. Demiral | 27 | 3 | Defender |
| 1719 | M. Müldür | 26 | 18 | Defender |
| 26300 | O. Kabak | 25 | 15 | Defender |
| 62490 | S. Akaydin | 31 | 4 | Defender |
| 22222 | Z. Çelik | 28 | 2 | Defender |
| 50132 | A. Bayındır | 27 | 12 | Goalkeeper |
| 49837 | M. Günok | 36 | 1 | Goalkeeper |
| 49866 | U. Çakır | 29 | 23 | Goalkeeper |
| 291964 | A. Güler | 20 | 8 | Midfielder |
| 24963 | A. Karazor | 29 | 2 | Midfielder |
| 1640 | H. Çalhanoğlu | 31 | 10 | Midfielder |
| 62323 | M. Eskihellaç | 28 | 22 | Midfielder |
| 134590 | O. Aydın | 25 | 19 | Midfielder |
| 37155 | O. Kökçü | 25 | 6 | Midfielder |
| 24807 | S. Özcan | 27 | 5 | Midfielder |
| 214463 | İ. Yüksek | 27 | 16 | Midfielder |


### USA (`team_id=2384`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `USA`
- National team: `True`
- Players: `34`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 17 | C. Pulišić | 27 | 10 | Attacker |
| 138835 | F. Balogun | 24 | 20 | Attacker |
| 427 | H. Wright | 27 | 19 | Attacker |
| 362400 | M. Arfsten | 24 | 18 | Attacker |
| 407652 | P. Agyemang | 25 | 24 | Attacker |
| 73868 | R. Pepi | 22 | 9 | Attacker |
| 355994 | A. Freeman | 21 | 16 | Defender |
| 19549 | A. Robinson | 28 | 5 | Defender |
| 50737 | A. Trusty | 27 | 2 | Defender |
| 126949 | C. Richards | 25 | 3 | Defender |
| 50852 | J. Scally | 23 | 19 | Defender |
| 119002 | J. Tolkin | 23 | 2 | Defender |
| 50735 | M. McKenzie | 26 | 22 | Defender |
| 50879 | M. Robinson | 28 | 12 | Defender |
| 38735 | S. Dest | 25 | 2 | Defender |
| 19023 | T. Ream | 38 | 13 | Defender |
| 266606 | C. Brady | 21 | 26 | Goalkeeper |
| 25335 | J. Klinsmann | 28 | 1 | Goalkeeper |
| 50728 | M. Freese | 27 | 25 | Goalkeeper |
| 50999 | M. Turner | 31 | 1 | Goalkeeper |
| 102685 | P. Schulte | 24 | 18 | Goalkeeper |
| 351571 | R. Celentano | 25 |  | Goalkeeper |
| 201714 | A. Morris | 24 | 16 | Midfielder |
| 50739 | B. Aaronson | 25 | 11 | Midfielder |
| 51114 | C. Roldan | 30 | 10 | Midfielder |
| 312896 | D. Luna | 22 | 10 | Midfielder |
| 161921 | G. Reyna | 23 | 7 | Midfielder |
| 133185 | J. Cardoso | 24 | 15 | Midfielder |
| 162037 | M. Tillman | 23 | 17 | Midfielder |
| 201713 | S. Berhalter | 24 | 8 | Midfielder |
| 80752 | T. Tessmann | 24 | 11 | Midfielder |
| 25617 | T. Tillman | 26 | 26 | Midfielder |
| 1138 | T. Weah | 25 | 21 | Midfielder |
| 415 | W. McKennie | 27 | 8 | Midfielder |


### Uruguay (`team_id=7`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Uruguay`
- National team: `True`
- Players: `49`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 51603 | A. Canobbio | 27 | 14 | Attacker |
| 278190 | A. Álvarez | 24 | 9 | Attacker |
| 51618 | B. Rodríguez | 25 | 10 | Attacker |
| 51617 | D. Núñez | 26 | 9 | Attacker |
| 546169 | F. Martinez | 17 | 15 | Attacker |
| 51553 | F. Martínez | 29 | 3 | Attacker |
| 70078 | F. Pellistri | 24 | 11 | Attacker |
| 51620 | F. Torres | 25 | 21 | Attacker |
| 51530 | F. Viñas | 27 | 13 | Attacker |
| 51464 | I. Laquintana | 26 | 11 | Attacker |
| 414340 | L. González | 19 | 9 | Attacker |
| 297749 | L. Rodríguez | 22 | 19 | Attacker |
| 51776 | M. Araújo | 25 | 20 | Attacker |
| 16482 | R. Aguirre | 31 | 7 | Attacker |
| 575275 | B. Barboza | 17 | 4 | Defender |
| 1290 | G. Varela | 32 | 13 | Defender |
| 31 | J. Giménez | 30 | 2 | Defender |
| 51466 | J. Piquerez | 27 | 22 | Defender |
| 51426 | J. Rodríguez | 28 | 14 | Defender |
| 377326 | K. Amaro | 21 | 16 | Defender |
| 47254 | M. Olivera | 28 | 16 | Defender |
| 1160 | M. Saracchi | 27 | 14 | Defender |
| 51572 | M. Viña | 28 | 17 | Defender |
| 101814 | R. Araújo | 26 | 4 | Defender |
| 135334 | S. Bueno | 27 | 2 | Defender |
| 51535 | S. Cáceres | 26 | 3 | Defender |
| 311773 | S. Mouriño | 23 | 16 | Defender |
| 51822 | C. Fiermarín | 27 | 1 | Goalkeeper |
| 56266 | F. Israel | 25 | 12 | Goalkeeper |
| 429 | F. Muslera | 39 | 1 | Goalkeeper |
| 405124 | K. Martínez | 20 | 1 | Goalkeeper |
| 575274 | P. Da Costa | 17 | 12 | Goalkeeper |
| 61895 | S. Mele | 28 | 23 | Goalkeeper |
| 50077 | S. Rochet | 32 | 1 | Goalkeeper |
| 153083 | E. Martínez | 26 | 20 | Midfielder |
| 756 | F. Valverde | 27 | 15 | Midfielder |
| 2612 | G. de Arrascaeta | 31 | 10 | Midfielder |
| 472611 | J. Daguer | 17 | 5 | Midfielder |
| 162891 | J. Sanabria | 25 | 18 | Midfielder |
| 51494 | M. Ugarte | 24 | 5 | Midfielder |
| 503271 | N. Azambuja | 17 | 9 | Midfielder |
| 30690 | N. Fonseca | 27 | 15 | Midfielder |
| 195505 | N. Marichal | 24 | 19 | Midfielder |
| 2614 | N. Nández | 30 | 8 | Midfielder |
| 5995 | N. de la Cruz | 28 | 7 | Midfielder |
| 545898 | P. Alcoba | 16 | 19 | Midfielder |
| 863 | R. Bentancur | 28 | 6 | Midfielder |
| 108563 | R. Zalazar | 26 | 21 | Midfielder |
| 315243 | S. Homenchenko | 22 | 18 | Midfielder |


### Uzbekistan (`team_id=1568`)

- Competition: `FIFA World Cup 2026`
- League ID: `1`
- Season: `2026`
- Country: `Uzbekistan`
- National team: `True`
- Players: `26`

| player_id | name | age | number | position |
| --- | --- | --- | --- | --- |
| 532640 | A. Odilov | 24 | 28 | Attacker |
| 53834 | D. Khamdamov | 29 | 17 | Attacker |
| 53535 | E. Shomurodov | 30 | 14 | Attacker |
| 72128 | I. Sergeev | 32 | 21 | Attacker |
| 72127 | O. O&apos;runov | 25 | 11 | Attacker |
| 360114 | A. Khusanov | 21 | 2 | Defender |
| 416964 | B. Karimov | 18 | 16 | Defender |
| 532759 | F. Sayfiev | 34 | 4 | Defender |
| 358427 | J. Urozov | 22 | 6 | Defender |
| 72122 | K. Alijonov | 28 | 3 | Defender |
| 410549 | M. Abdumajidov | 21 |  | Defender |
| 311906 | M. Khamraliev | 24 | 5 | Defender |
| 34121 | R. Ashurmatov | 29 | 5 | Defender |
| 73514 | S. Nasrullayev | 27 | 13 | Defender |
| 73510 | U. Eshmurodov | 33 | 15 | Defender |
| 73507 | A. Ne&apos;matov | 24 | 12 | Goalkeeper |
| 72120 | B. Ergashev | 30 | 16 | Goalkeeper |
| 73534 | U. Yusupov | 34 | 1 | Goalkeeper |
| 73520 | A. Gʻaniyev | 27 | 10 | Midfielder |
| 73522 | A. Mozgovoy | 26 | 6 | Midfielder |
| 200946 | I. Ibragimov | 24 | 8 | Midfielder |
| 65576 | J. Iskanderov | 32 | 8 | Midfielder |
| 53835 | O. Hamrobekov | 29 | 9 | Midfielder |
| 50272 | O. Shukurov | 29 | 7 | Midfielder |
| 546505 | S. Temirov | 27 | 11 | Midfielder |
| 328759 | U. Rahmonaliyev | 22 | 15 | Midfielder |

