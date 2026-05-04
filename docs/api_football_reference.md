# API-Football Reference

Generated at: `2026-05-02T08:36:37.139917+00:00`
Base URL: `https://v3.football.api-sports.io`
Club season: `2025`
World Cup season: `2026`
Requests made: `34`

## Objectif

Reference technique pour reconstruire le projet autour d'API-Football.
Le fichier liste les competitions ciblees, les IDs de ligue, les IDs d'equipe, les IDs de stade et les references globales utiles.

## Endpoints a prevoir dans le futur bot

| Endpoint | IDs | Usage |
| --- | --- | --- |
| /leagues | league.id, seasons.year, coverage flags | Resolve and verify competition IDs for a season. |
| /teams | team.id, venue.id | Get participating teams for a league and season. |
| /standings | team.id inside ranking rows | Get current table/rank for score context. |
| /fixtures/rounds | round labels | Know competition rounds available for filtering fixtures. |
| /fixtures | fixture.id, team.id, venue.id, referee, status | Runtime source for match IDs used by odds, injuries, lineups, events and stats. |
| /fixtures/headtohead | fixture.id | Use h2h={home_id}-{away_id} for direct comparison history. |
| /injuries | fixture.id, team.id, player.id | Get unavailable players by fixture, team or league/season. |
| /fixtures/lineups | fixture.id, team.id, player.id | Get starting XI and substitutes once lineups are available. |
| /fixtures/statistics | fixture.id, team.id | Post/live match statistics by fixture and optional team. |
| /teams/statistics | league.id, team.id, season | Season-level team form and aggregate stats. |
| /players/squads | team.id, player.id | Current squad and player IDs. Optional in this script because it costs one call per team. |
| /players | player.id, team.id, league.id, season | Paginated player statistics for a league/team/season. |
| /odds | fixture.id, bookmaker.id, bet.id | Prematch odds. For 1X2, bet id is usually resolved from /odds/bets. |
| /odds/bookmakers | bookmaker.id | Global reference list for bookmaker filters. |
| /odds/bets | bet.id | Global reference list for prematch odds market filters. |
| /odds/live/bets | live bet.id | Separate reference list for live odds market filters. |
| /predictions | fixture.id | API-Football prediction payload by fixture. |


## Competitions ciblees

| Nom | Type | league_id | Nom API | Pays | Saison | Teams | Fixtures exportees |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ligue 1 | club | 61 | Ligue 1 | France | 2025 | 18 | 306 |
| Premier League | club | 39 | Premier League | England | 2025 | 20 | 380 |
| La Liga | club | 140 | La Liga | Spain | 2025 | 20 | 380 |
| Bundesliga | club | 78 | Bundesliga | Germany | 2025 | 18 | 306 |
| Serie A | club | 135 | Serie A | Italy | 2025 | 20 | 380 |
| FIFA World Cup 2026 | national | 1 | World Cup | World | 2026 | 48 | 72 |


## References globales

### Bookmakers

| bookmaker_id | name |
| --- | --- |
| 1 | 10Bet |
| 2 | Marathonbet |
| 3 | Betfair |
| 4 | Pinnacle |
| 5 | SBO |
| 6 | Bwin |
| 7 | William Hill |
| 8 | Bet365 |
| 9 | Dafabet |
| 10 | Ladbrokes |
| 11 | 1xBet |
| 12 | BetFred |
| 13 | 188Bet |
| 15 | Interwetten |
| 16 | Unibet |
| 17 | 5Dimes |
| 18 | Intertops |
| 19 | Bovada |
| 20 | Betcris |
| 21 | 888Sport |
| 22 | Tipico |
| 23 | Sportingbet |
| 24 | Betway |
| 25 | Expekt |
| 26 | Betsson |
| 27 | NordicBet |
| 28 | ComeOn |
| 30 | Netbet |
| 32 | Betano |
| 33 | Fonbet |
| 34 | Superbet |
| 36 | BetVictor |
| 37 |  |


### Bets prematch

| bet_id | name |
| --- | --- |
| 1 | Match Winner |
| 2 | Home/Away |
| 3 | Second Half Winner |
| 4 | Asian Handicap |
| 5 | Goals Over/Under |
| 6 | Goals Over/Under First Half |
| 7 | HT/FT Double |
| 8 | Both Teams Score |
| 9 | Handicap Result |
| 10 | Exact Score |
| 11 | Highest Scoring Half |
| 12 | Double Chance |
| 13 | First Half Winner |
| 14 | Team To Score First |
| 15 | Team To Score Last |
| 16 | Total - Home |
| 17 | Total - Away |
| 18 | Handicap Result - First Half |
| 19 | Asian Handicap First Half |
| 20 | Double Chance - First Half |
| 21 | Odd/Even |
| 22 | Odd/Even - First Half |
| 23 | Home Odd/Even |
| 24 | Results/Both Teams Score |
| 25 | Result/Total Goals |
| 26 | Goals Over/Under - Second Half |
| 27 | Clean Sheet - Home |
| 28 | Clean Sheet - Away |
| 29 | Win to Nil - Home |
| 30 | Win to Nil - Away |
| 31 | Correct Score - First Half |
| 32 | Win Both Halves |
| 33 | Double Chance - Second Half |
| 34 | Both Teams Score - First Half |
| 35 | Both Teams To Score - Second Half |
| 36 | Win To Nil |
| 37 | Home win both halves |
| 38 | Exact Goals Number |
| 39 | To Win Either Half |
| 40 | Home Team Exact Goals Number |
| 41 | Away Team Exact Goals Number |
| 42 | Second Half Exact Goals Number |
| 43 | Home Team Score a Goal |
| 44 | Away Team Score a Goal |
| 45 | Corners Over Under |
| 46 | Exact Goals Number - First Half |
| 47 | Winning Margin |
| 48 | To Score In Both Halves By Teams |
| 49 | Total Goals/Both Teams To Score |
| 50 | Goal Line |
| 51 | Halftime Result/Total Goals |
| 52 | Halftime Result/Both Teams Score |
| 53 | Away win both halves |
| 54 | First 10 min Winner |
| 55 | Corners 1x2 |
| 56 | Corners Asian Handicap |
| 57 | Home Corners Over/Under |
| 58 | Away Corners Over/Under |
| 59 | Own Goal |
| 60 | Away Odd/Even |
| 61 | To Qualify |
| 62 | Correct Score - Second Half |
| 63 | Odd/Even - Second Half |
| 72 | Goal Line (1st Half) |
| 73 | Both Teams to Score 1st Half - 2nd Half |
| 74 | 10 Over/Under |
| 75 | Last Corner |
| 76 | First Corner |
| 77 | Total Corners (1st Half) |
| 78 | RTG_H1 |
| 79 | Cards European Handicap |
| 80 | Cards Over/Under |
| 81 | Cards Asian Handicap |
| 82 | Home Team Total Cards |
| 83 | Away Team Total Cards |
| 84 | Total Corners (3 way) (1st Half) |
| 85 | Total Corners (3 way) |
| 86 | RCARD |
| 87 | Total ShotOnGoal |
| 88 | Home Total ShotOnGoal |
| 89 | Away Total ShotOnGoal |
| 91 | Total Goals (3 way) |
| 92 | Anytime Goal Scorer |
| 93 | First Goal Scorer |
| 94 | Last Goal Scorer |
| 95 | To Score Two or More Goals |
| 96 | Last Goal Scorer |
| 97 | First Goal Method |
| 99 | To Score A Penalty |
| 100 | To Miss A Penalty |
| 102 | Player to be booked |
| 103 | Player to be Sent Off |
| 104 | Asian Handicap (2nd Half) |
| 105 | Home Team Total Goals(1st Half) |
| 106 | Away Team Total Goals(1st Half) |
| 107 | Home Team Total Goals(2nd Half) |
| 108 | Away Team Total Goals(2nd Half) |
| 109 | Draw No Bet (1st Half) |
| 110 | Scoring Draw |
| 111 | Home team will score in both halves |
| 112 | Away team will score in both halves |
| 113 | Both Teams To Score in Both Halves |
| 114 | Home Team Score a Goal (1st Half) |
| 115 | Home Team Score a Goal (2nd Half) |
| 116 | Away Team Score a Goal (1st Half) |
| 117 | Away Team Score a Goal (2nd Half) |
| 118 | Home Win/Over |
| 119 | Home Win/Under |
| 120 | Away Win/Over |
| 121 | Away Win/Under |
| 122 | Home team will win either half |
| 123 | Away team will win either half |
| 124 | Home Come From Behind and Win |
| 125 | Corners Asian Handicap (1st Half) |
| 126 | Corners Asian Handicap (2nd Half) |
| 127 | Total Corners (2nd Half) |
| 128 | Total Corners (3 way) (2nd Half) |
| 129 | Away Come From Behind and Win |
| 130 | Corners 1x2 (1st Half) |
| 131 | Corners 1x2 (2nd Half) |
| 132 | Home Total Corners (1st Half) |
| 133 | Home Total Corners (2nd Half) |
| 134 | Away Total Corners (1st Half) |
| 135 | Away Total Corners (2nd Half) |
| 136 | 1x2 - 15 minutes |
| 137 | 1x2 - 60 minutes |
| 138 | 1x2 - 75 minutes |
| 139 | 1x2 - 30 minutes |
| 140 | DC - 30 minutes |
| 141 | DC - 15 minutes |
| 142 | DC - 60 minutes |
| 143 | DC - 75 minutes |
| 144 | Goal in 1-15 minutes |
| 145 | Goal in 16-30 minutes |
| 146 | Goal in 31-45 minutes |
| 147 | Goal in 46-60 minutes |
| 148 | Goal in 61-75 minutes |
| 149 | Goal in 76-90 minutes |
| 150 | Home Team Yellow Cards |
| 151 | Away Team Yellow Cards |
| 152 | Yellow Asian Handicap |
| 153 | Yellow Over/Under |
| 154 | Yellow Double Chance |
| 155 | Yellow Over/Under (1st Half) |
| 156 | Yellow Over/Under (2nd Half) |
| 157 | Yellow Odd/Even |
| 158 | Yellow Cards 1x2 |
| 159 | Yellow Asian Handicap (1st Half) |
| 160 | Yellow Asian Handicap (2nd Half) |
| 161 | Yellow Cards 1x2 (1st Half) |
| 162 | Yellow Cards 1x2 (2nd Half) |
| 163 | Penalty Awarded |
| 164 | Offsides Total |
| 165 | Offsides 1x2 |
| 166 | Offsides Handicap |
| 167 | Offsides Home Total |
| 168 | Offsides Away Total |
| 169 | Offsides Double Chance |
| 170 | Fouls. Away Total |
| 171 | Fouls. Home Total |
| 172 | Fouls. Double Chance |
| 173 | Fouls. Total |
| 174 | Fouls. Handicap |
| 175 | Fouls. 1x2 |
| 176 | ShotOnTarget 1x2 |
| 177 | ShotOnTarget Handicap |
| 178 | ShotOnTarget Double Chance |
| 179 | First Team to Score |
| 180 | Last Team to Score |
| 181 | European Handicap (2nd Half) |
| 182 | Draw No Bet (2nd Half) |
| 183 | Double Chance/Total |
| 184 | To Score in Both Halves |
| 185 | First Team to Score (3 way) 1st Half |
| 186 | Total Goals Number By Ranges |
| 187 | Total Goals By Ranges (1st Half) |
| 188 | Clean Sheet |
| 189 | To Advance Handicap |
| 190 | Home Exact Goals Number (1st Half) |
| 191 | Away Exact Goals Number (1st Half) |
| 192 | Home Highest Scoring Half |
| 193 | Away Highest Scoring Half |
| 194 | Result/Total Goals (2nd Half) |
| 195 | Either Team Wins By 1 Goals |
| 196 | Either Team Wins By 2 Goals |
| 197 | Over/Under 15m-30m |
| 198 | Over/Under 30m-45m |
| 199 | Home Win To Nill (1st Half) |
| 200 | Home Win To Nill (2nd Half) |
| 201 | To Score In 1st Half |
| 202 | To Score In 2nd Half |
| 203 | Yellow Cards. Odd/Even (1st Half) |
| 204 | Yellow Cards. Odd/Even (2nd Half) |
| 205 | First Team to Score (3 way) 2nd Half |
| 206 | Home No Bet |
| 207 | Away No Bet |
| 208 | Corners. First Corner (3 way) |
| 209 | Home Come From Behind and Draw |
| 210 | Away Come From Behind and Draw |
| 211 | Total Shots |
| 212 | Player Assists |
| 213 | Player Triples |
| 214 | Player Points |
| 215 | Player Singles |
| 216 | Multi Touchdown Scorer (2 or More) |
| 217 | Multi Touchdown Scorer (3 or More) |
| 218 | Away Anytime Goal Scorer |
| 219 | Away First Goal Scorer |
| 220 | Shots. Away Total |
| 221 | Shots. Home Total |
| 222 | To Win From Behind |
| 223 | Number of Goals In Match (Range) |
| 224 | Game Decided After Penalties |
| 225 | Game Decided in Extra Time |
| 226 | Away Last Goal Scorer |
| 227 | Goal Method Header |
| 228 | Home Goal Method Header |
| 229 | Goal Method Outside the Box |
| 230 | Home Goal Method Outside the Box |
| 231 | Home Anytime Goal Scorer |
| 232 | Home First Goal Scorer |
| 233 | Home Last Goal Scorer |
| 234 | Home To Score Three or More Goals |
| 235 | Away To Score Three or More Goals |
| 236 | Away To Score Two or More Goals |
| 237 | Home To Score Two or More Goals |
| 238 | Home Team Goalscorers First |
| 239 | Corners. European Handicap |
| 240 | Home Player Shots |
| 241 | Away Player Shots |
| 242 | Player Shots On Target |
| 243 | Home Shots On Target |
| 244 | Away Shots On Target |
| 245 | Away Goal Method Header |
| 246 | Away Goal Method Outside the Box |
| 247 | Corners Race To |
| 248 | Time Of 1st Score |
| 249 | Multicorners |
| 250 | First Card Received (3 way) |
| 251 | Player to be booked |
| 252 | Both Teams to Receive a Card |
| 253 | Time Of 1st Score |
| 254 | Team Performances (Range) |
| 255 | Home Player Assists |
| 256 | Away Player Assists |
| 257 | Player to Score or Assist |
| 258 | Home Player to Score or Assist |
| 259 | Away Player to Score or Assist |
| 260 | Team Time Of 1st Score |
| 261 | Total Goal Minutes (Range) |
| 262 | Late Goal (Range) |
| 263 | Early Goal (Range) |
| 264 | Player Shots On Target Total |
| 265 | Player Shots Total |
| 266 | Player Fouls Committed |
| 267 | Goalkeeper Saves |
| 268 | Home Goalkeeper Saves |
| 269 | Home Player Shots On Target Total |
| 270 | Home Player Shots Total |
| 271 | Home Player Fouls Committed |
| 272 | Home Player Tackles |
| 273 | Home Player Passes |
| 274 | Away Goalkeeper Saves |
| 275 | Away Player Shots On Target Total |
| 276 | Away Player Shots Total |
| 277 | Away Player Fouls Committed |
| 278 | Away Player Tackles |
| 279 | Away Player Passes |
| 280 | First Set Piece 5 Minutes |
| 281 | Total Tackles |
| 282 | Double Chance/Both Teams To Score |
| 283 | Away Win To Nill (1st Half) |
| 284 | Away Win To Nill (2nd Half) |
| 285 | Team To Score (Goals) |
| 286 | Team Goalscorers First |
| 287 | Team Goalscorers Last |
| 288 | Home Team Goalscorers Last |
| 289 | Away Team Goalscorers First |
| 290 | Away Team Goalscorers Last |
| 291 | Time of First Goal Brackets (Range) |
| 292 | Over/Under between 0 and 10m |
| 293 | Double Chance 0-15m |
| 294 | Double Chance 15-30m |
| 295 | Corners. Total (Range) |
| 296 | Double Chance 30-45m |
| 297 | Corners. total between 0 and 10m |
| 298 | Method of Victory |
| 299 | Cards over/under between 0 and 10 m |
| 300 | Both Teams to Receive 2+ Cards |
| 301 | Tackles. Away Total |
| 302 | Tackles. Home Total |
| 303 | Over/Under between 0 and 10 m |
| 304 | Over/Under between  0 and 10 m |
| 305 | Race to the 2nd goal? |
| 306 | Race to the 3rd goal? |
| 307 | Corners. Double Chance |
| 308 | Race To |
| 309 | Yellow Cards. Home Total (1st Half) |
| 310 | Yellow Cards Away Total (1st Half) |
| 311 | Which team will score the 1st goal? |
| 312 | 1x2 - 20 minutes |
| 313 | Offsides Odd/Even |
| 314 | Fouls Odd/Even |
| 315 | Saves Total |
| 316 | Saves 1x2 |
| 317 | Saves Asian H |
| 318 | Saves O/U Home |
| 319 | Saves O/U Away |
| 320 | Saves Double Chance |
| 321 | Penalty Awarded (1st Half) |
| 322 | Penalty Awarded (2nd Half) |
| 323 | Saves Odd/Even |
| 324 | Corner in 1-15 minutes |
| 325 | Corner in 16-30 minutes |
| 326 | Corner in 31-45 minutes |
| 327 | Corner in 45-60 minutes |
| 328 | Corner in 60-75 minutes |
| 329 | Corner in 75-90 minutes |
| 330 | Home Not lose/Over |
| 331 | Home Not lose/Under |
| 332 | Away Not lose/Over |
| 333 | Away Not lose/Under |
| 334 | 1x2 - 70 minutes |
| 335 | Red Cards Over/Under |
| 336 | Goal Line |
| 337 | Asian Handicap (Sets) |
| 338 | Corners. Odd/Even |
| 339 | Corners. Double Chance |
| 340 | Shots.1x2 |
| 341 |  |
| 342 | Red Card In The Match (1st Half) |
| 343 | Fouls. Odd/Even |
| 344 | Odd/Even (1st Set) |
| 345 | Set Betting |
| 346 | Extra Point (1st Set) |
| 347 | Home Winning Margin (1st Set) |
| 348 | Away Winning Margin (1st Set) |


### Bets live

| live_bet_id | name |
| --- | --- |
| 1 | Over/Under Extra Time |
| 2 | 1x2 Extra Time |
| 3 | Extra Time Asian Corners |
| 4 | Extra Time Total Corners (3 Ways) (1st Half) |
| 5 | Extra Time Double Result |
| 6 | Which team will score the 1st goal in extra time? |
| 7 | Extra Time Asian Corners (1st Half) |
| 8 | Method of Victory |
| 9 | Both Teams To Score (ET) |
| 10 | To Qualify |
| 11 | Asian Handicap Extra Time |
| 12 | 1x2 Extra Time (1st Half) |
| 13 | Extra Time Total Corners (3 Ways) |
| 14 | Over/Under Extra Time (1st Half) |
| 15 | Last Corner |
| 16 | How many goals will Away Team score? |
| 17 | Asian Handicap (1st Half) |
| 18 | 1st Goal in Interval |
| 19 | 1x2 (1st Half) |
| 20 | Match Corners |
| 21 | 3-Way Handicap |
| 22 | 1x2 - 30 minutes |
| 23 | Final Score |
| 24 | Over/Under Line (1st Half) |
| 25 | Match Goals |
| 26 | European Handicap (1st Half) |
| 27 | Home Team Score a Goal (2nd Half) |
| 28 | Home Team  to Score in Both Halves |
| 29 | Result / Both Teams To Score |
| 30 | Both Teams To Score (1st Half) |
| 31 | Total Corners (3way) (2nd Half) |
| 32 | Asian Corners |
| 33 | Asian Handicap |
| 34 | 1x2 - 40 minutes |
| 35 | To Win 2nd Half |
| 36 | Over/Under Line |
| 37 | Total Corners |
| 38 | Away Team to Score in Both Halves |
| 39 | Away Team Goals |
| 40 | Total Corners (3 way) (1st Half) |
| 41 | 1x2 - 50 minutes |
| 42 | Race to the 3rd corner? |
| 43 | Both Teams To Score (2nd Half) |
| 44 | Race to the 9th corner? |
| 45 | Race to the 7th corner? |
| 46 | Goal Scorer |
| 47 | Away 1st Goal in Interval |
| 48 | Draw No Bet |
| 49 | Over/Under (1st Half) |
| 50 | 1x2 - 60 minutes |
| 51 | Asian Corners (1st Half) |
| 52 | 1x2 - 80 minutes |
| 53 | To Score 2 or More |
| 54 | Home 1st Goal in Interval |
| 55 | Correct Score (1st Half) |
| 56 | 1x2 - 70 minutes |
| 57 | Away Team Clean Sheet |
| 58 | Home Team Goals |
| 59 | Fulltime Result |
| 60 | To Score 3 or More |
| 61 | Race to the 5th corner? |
| 62 | Last Team to Score (3 way) |
| 63 | Anytime Goal Scorer |
| 64 | Half Time/Full Time |
| 65 | Next 10 Minutes Total |
| 66 | Home Team Clean Sheet |
| 67 | How many goals will Home Team score? |
| 68 | Goals Odd/Even |
| 69 | Both Teams to Score |
| 70 | Away Team Score a Goal (2nd Half) |
| 71 | Which team will score the 4th corner? (2 Way) |
| 72 | Double Chance |
| 73 | Which team will score the 1st goal? |
| 74 | Which team will score the 3rd corner? (2 Way) |
| 75 | Which team will score the 2nd corner? (2 Way) |
| 76 | Corners European Handicap |
| 77 | 1x2 - 10 minutes |
| 78 | Corners 1x2 |
| 79 | 1x2 - 20 minutes |
| 80 | Method of 1st Goal |
| 81 | Method of Qualification |
| 82 | Game Won After Penalties Shootout |
| 83 | Game Won In Extra Time |
| 84 | Which team will score the 2nd goal? |
| 85 | Which team will score the 2nd goal? |
| 86 | Which team will score the 6th corner? (2 Way) |
| 87 | Which team will score the 5th corner? (2 Way) |
| 88 | Which team will score the 7th corner? (2 Way) |
| 89 | Which team will score the 9th corner? (2 Way) |
| 90 | 2nd Goal in Interval |
| 91 | Away 2nd Goal in Interval |
| 92 | Which team will score the 3rd goal? |
| 93 | Which team will score the 10th corner? (2 Way) |
| 94 | 3rd Goal in Interval |
| 95 | Home 2nd Goal in Interval |
| 96 | Asian Handicap Converted Penalties |
| 97 | Sudden Death |
| 98 | Away Penalty Shootout |
| 99 | Home Penalty Shootout |
| 100 | Home Total Converted Penalties |
| 101 | Total Penalties in Shootout |
| 102 | Last Penalty Score/Miss |
| 103 | Correct Score in Shootouts |
| 104 | Total Converted Penalties |
| 105 | Total Converted Penalties - Goal Line |
| 106 | Away Total Converted Penalties |
| 107 | Penalties Shootout Winner |
| 108 | Which team will score the 11th corner? (2 Way) |
| 109 | Which team will score the 4th goal? |
| 110 | Which team will score the 8th corner? (2 Way) |
| 111 | Last Penalty Scorer in Shootout |
| 112 | Which team will score the 5th goal? |
| 113 | Method of 2nd Goal |
| 114 | Which team will score the 13th corner? (2 Way) |
| 115 | Player to be Booked |
| 116 | Action In Next 1 Minutes |
| 117 | First Action In Next 5 Minutes |
| 118 | Player to be Sent Off |
| 119 | Total Cards |
| 120 | Which team will score the 12th corner? (2 Way) |
| 121 | Which team will score the 14th corner? (2 Way) |
| 122 | Which team will score the 15th corner? (2 Way) |
| 123 | Which team will score the 16th corner? (2 Way) |
| 124 | Which team will score the 17th corner? (2 Way) |
| 125 | Home 3rd Goal in Interval |
| 126 | Which team will score the 18th corner? (2 Way) |
| 127 | Which team will score the 6th goal? |
| 128 | Away 3rd Goal in Interval |
| 129 | Which team will score the 2nd goal in extra time? |
| 130 | Method of 3rd Goal |
| 131 | 4th Goal in Interval |
| 132 | Which team will score the 7th goal? |
| 133 | Which team will score the 19th corner? (2 Way) |
| 134 | Home 4th Goal in Interval |
| 135 | Away 4th Goal in Interval |
| 136 | 5th Goal in Interval |
| 137 | Home 5th Goal in Interval |
| 138 | Method of 4th Goal |
| 139 | Which team will score the 8th goal? |
| 140 | Which team will score the 9th goal? |
| 141 | Which team will score the 10th goal? |
| 142 | Which team will score the 11th goal? |
| 143 | Which team will score the 12th goal? |
| 144 | 6th Goal in Interval |
| 145 | Method of 5th Goal |
| 146 | Method of 6th Goal |
| 147 | Which team will score the 20th corner? (2 Way) |
| 148 | Player Shots |
| 149 | Total Shots |
| 150 | Total shots on goal |
| 151 | Away Total Shots |
| 152 | Home Total Shots |
| 153 | Player Shots on Targets |
| 154 | Home Total shots on goal |
| 155 | Player Assists |
| 156 | Away Total shots on goal |
| 157 | Method of 7th Goal |
| 158 | Method of 8th Goal |
| 159 | 7th Goal in Interval |
| 160 | To Win the Trophy |
| 161 | Away 5th Goal in Interval |
| 162 | Which team will score the 3rd goal in extra time? |
| 163 | Which team will score the 13th goal? |
| 164 | Which team will score the 4th goal in extra time? |
| 165 | Double Chance Extra Time |
| 166 | Double Chance Extra Time (1st Half) |
| 167 | Asian Handicap Extra Time (1st Half) |
| 168 | Corners Double Chance |
| 169 | Home Total Corners |
| 170 | Which team will score the 10th corner? |
| 171 | Away Not lose/Over |
| 172 | Away Not lose/Under |
| 173 | Home Not lose/Over |
| 174 | Corners Asian Handicap |
| 175 | Home Not lose/Under |
| 176 | Away Total Corners |
| 177 | Over/Under (2nd Half) |
| 178 | Total shots on goal (1st Half) |
| 179 | Home team will win either half |
| 180 | Double Chance (1st Half) |
| 181 | Which team will score the 13th corner? |
| 182 | Yellow Asian Handicap |
| 183 | Draw/Over |
| 184 | Asian Handicap (2nd Half) |
| 185 | Double Chance shots on goal |
| 186 | Away Win/Over |
| 187 | Yellow Double Chance (1st Half) |
| 188 | Away Total Corners (1st Half) |
| 189 | Total Corners (1st Half) |
| 190 | Home Total Corners (1st Half) |
| 191 | Home Team Total (1st Half) |
| 192 | Race to the 3rd goal? |
| 193 | Corners 1x2 (1st Half) |
| 194 | 1x2 shots on goal |
| 195 | Home Team Total (2nd Half) |
| 196 | Away Team Total Goals (2nd Half) |
| 197 | Yellow Asian Handicap (1st Half) |
| 198 | Away Team Total Points (1st Half) |
| 199 | Yellow Double Chance |
| 200 | Home Team Yellow cards |
| 201 | Home Win/Over |
| 202 | 1x2 shots on goal (1st Half) |
| 203 | Yellow Cards 1x2 |
| 204 | Corners Asian Handicap (1st Half) |
| 205 | Asian Handicap shots on goal |
| 206 | Home Team Yellow Cards (1st Half) |
| 207 | Yellow Cards 1x2 (1st Half) |
| 208 | Double Chance shots on goal (1st Half) |
| 209 | Yellow Over/Under (1st Half) |
| 210 | Yellow Over/Under |
| 211 | Away Team Yellow Cards (1st Half) |
| 212 | Asian Handicap shots on goal (1st Half) |
| 213 | Away Team Yellow Cards |
| 214 | Away team will win either half |
| 215 | Both Teams To Score Under |
| 216 | Both Halves Over |
| 217 | Race to the 2nd goal? |
| 218 | Away Team Score a Goal |
| 219 | Both Teams To Score Over |
| 220 | Both Halves Under |
| 221 | Home Win/Under |
| 222 | Away Team Score a Goal (1st Half) |
| 223 | Which team will score the 5th corner? |
| 224 | Which team will score the 4th corner? |
| 225 | Home Team Score a Goal (1st Half) |
| 226 | Home Team Score a Goal |
| 227 | Draw/Under |
| 228 | Away Win/Under |
| 229 | Home Red Over/Under |
| 230 | Away Red Over/Under |
| 231 | Which team will score the 7th corner? |
| 232 | Red Over/Under |
| 233 | Yellow Odd/Even |
| 234 | Which team will score the 6th corner? |
| 235 | Which team will score the 8th corner? |
| 236 | Which team will score the 9th corner? |
| 237 | Which team will score the 11th corner? |
| 238 | Which team will score the 12th corner? |
| 239 | Which team will score the 14th corner? |
| 240 | Which team will score the 15th corner? |
| 241 | Which team will score the 1st corner? |
| 242 | Which team will score the 2nd corner? |
| 243 | Away Total shots on goal (1st Half) |
| 244 | Home Total shots on goal (1st Half) |
| 245 | Away Penalty Over/Under |
| 246 | Home Penalty Over/Under |
| 247 | Penalty Over/Under |
| 248 | Which team will score the 5th goal in extra time? |
| 249 | Which team will score the 6th goal in extra time? |
| 250 | Extra Time Over/Under Line |
| 251 | Result/Total Goals |
| 252 | Total Goals/Both Teams To Score |
| 253 | Over/Under between 70:01 m and 80:00 m |
| 254 | Over/Under between 60:01 m and 70:00 m |
| 255 | Over/Under between 50:01 m and 60:00 m |
| 256 | Which team will score the 3rd corner? |
| 257 | Over/Under between 40:01 m and 50:00 m |
| 258 | Over/Under between 30:01 m and 40:00 m |
| 259 | Home Win Both Halves |
| 260 | Away Win Both Halves |
| 261 | Over/Under between 00:00 m and 10:00 m |
| 262 | Over/Under between 20:01 m and 30:00 m |
| 263 | Over/Under between 10:01 m and 20:00 m |
| 264 | Corners over/under between 00:00 m and 10:00 m |
| 265 | Corners over/under between 20:01 m and 30:00 m |
| 266 | Corners over/under between 10:01 m and 20:00 m |


## Ligue 1

| Champ | Valeur |
| --- | --- |
| league_id | 61 |
| api_name | Ligue 1 |
| country | France |
| type | League |
| season | 2025 |
| season_start | 2025-08-17 |
| season_end | 2026-05-16 |


### Coverage

```json
{
  "fixtures": {
    "events": true,
    "lineups": true,
    "statistics_fixtures": true,
    "statistics_players": true
  },
  "standings": true,
  "players": true,
  "top_scorers": true,
  "top_assists": true,
  "top_cards": true,
  "injuries": true,
  "predictions": true,
  "odds": true
}
```

### Teams et stades

| team_id | name | code | country | national | venue_id | venue | city | capacity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 77 | Angers | ANG | France | False | 634 | Stade Raymond-Kopa | Angers | 19000 |
| 108 | Auxerre | AUX | France | False | 636 | Stade de l'Abbé Deschamps | Auxerre | 23467 |
| 111 | Le Havre | HAV | France | False | 652 | Stade Océane | Le Havre | 25178 |
| 116 | Lens | LEN | France | False | 654 | Stade Bollaert-Delelis | Lens | 41233 |
| 79 | Lille | LIL | France | False | 19207 | Decathlon Arena – Stade Pierre-Mauroy | Villeneuve d&apos;Ascq | 50083 |
| 97 | Lorient | LOR | France | False | 21430 | Stade du Moustoir - Yves Allainmat | Lorient | 18970 |
| 80 | Lyon | LYO | France | False | 666 | Groupama Stadium | Décines-Charpieu | 61556 |
| 81 | Marseille | MAR | France | False | 12678 | Stade Orange Vélodrome | Marseille | 67394 |
| 112 | Metz | MET | France | False | 658 | Stade Saint-Symphorien | Longeville-lès-Metz | 30000 |
| 91 | Monaco | MON | France | False | 20470 | Stade Louis-II | Monaco | 18523 |
| 83 | Nantes | NAN | France | False | 662 | Stade de la Beaujoire - Louis Fonteneau | Nantes | 38285 |
| 84 | Nice | NIC | France | False | 663 | Allianz Riviera | Nice | 35624 |
| 114 | Paris FC | PAR | France | False | 12585 | Stade Charléty | Paris | 20000 |
| 85 | Paris Saint Germain | PSG | France | False | 671 | Parc des Princes | Paris | 47929 |
| 94 | Rennes | REN | France | False | 680 | Roazhon Park | Rennes | 31127 |
| 106 | Stade Brestois 29 | BRE | France | False | 641 | Stade Francis-Le Blé | Brest | 15931 |
| 95 | Strasbourg | STR | France | False | 681 | Stade de la Meinau | Strasbourg | 26109 |
| 96 | Toulouse | TOU | France | False | 682 | Stadium de Toulouse | Toulouse | 33150 |


### Rounds

- `Regular Season - 1`
- `Regular Season - 2`
- `Regular Season - 3`
- `Regular Season - 4`
- `Regular Season - 5`
- `Regular Season - 6`
- `Regular Season - 7`
- `Regular Season - 8`
- `Regular Season - 9`
- `Regular Season - 10`
- `Regular Season - 11`
- `Regular Season - 12`
- `Regular Season - 13`
- `Regular Season - 14`
- `Regular Season - 15`
- `Regular Season - 16`
- `Regular Season - 17`
- `Regular Season - 18`
- `Regular Season - 19`
- `Regular Season - 20`
- `Regular Season - 21`
- `Regular Season - 22`
- `Regular Season - 23`
- `Regular Season - 24`
- `Regular Season - 25`
- `Regular Season - 26`
- `Regular Season - 27`
- `Regular Season - 28`
- `Regular Season - 29`
- `Regular Season - 30`
- `Regular Season - 31`
- `Regular Season - 32`
- `Regular Season - 33`
- `Regular Season - 34`

### Standings

| rank | team_id | team | group | pts | played | W | D | L | GD | form |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 85 | Paris Saint Germain | Ligue 1  | 69 | 30 | 22 | 3 | 5 | 43 | WWLWW |
| 2 | 116 | Lens | Ligue 1  | 63 | 30 | 20 | 3 | 7 | 28 | DWLWL |
| 3 | 80 | Lyon | Ligue 1  | 57 | 31 | 17 | 6 | 8 | 16 | WWWDL |
| 4 | 79 | Lille | Ligue 1  | 57 | 31 | 17 | 6 | 8 | 16 | WDWWW |
| 5 | 94 | Rennes | Ligue 1  | 56 | 31 | 16 | 8 | 7 | 12 | WWWWD |
| 6 | 81 | Marseille | Ligue 1  | 53 | 31 | 16 | 5 | 10 | 18 | DLWLL |
| 7 | 91 | Monaco | Ligue 1  | 51 | 31 | 15 | 6 | 10 | 7 | DDLWW |
| 8 | 95 | Strasbourg | Ligue 1  | 46 | 30 | 13 | 7 | 10 | 10 | WLWWD |
| 9 | 97 | Lorient | Ligue 1  | 41 | 31 | 10 | 11 | 10 | -5 | LWLDL |
| 10 | 96 | Toulouse | Ligue 1  | 38 | 31 | 10 | 8 | 13 | -1 | DLLLW |
| 11 | 106 | Stade Brestois 29 | Ligue 1  | 38 | 30 | 10 | 8 | 12 | -6 | DDLLL |
| 12 | 114 | Paris FC | Ligue 1  | 38 | 31 | 9 | 11 | 11 | -7 | LWWDW |
| 13 | 77 | Angers | Ligue 1  | 34 | 31 | 9 | 7 | 15 | -17 | LDLDL |
| 14 | 111 | Le Havre | Ligue 1  | 31 | 31 | 6 | 13 | 12 | -13 | DDDDL |
| 15 | 84 | Nice | Ligue 1  | 30 | 31 | 7 | 9 | 15 | -22 | DDDLL |
| 16 | 108 | Auxerre | Ligue 1  | 25 | 31 | 5 | 10 | 16 | -15 | LDDDW |
| 17 | 83 | Nantes | Ligue 1  | 20 | 31 | 4 | 8 | 19 | -25 | LLDDD |
| 18 | 112 | Metz | Ligue 1  | 16 | 31 | 3 | 7 | 21 | -39 | DLLDD |


### Fixtures

| fixture_id | date | round | home_id | home | away_id | away | venue_id | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1387706 | 2025-08-15T18:45:00+00:00 | Regular Season - 1 | 94 | Rennes | 81 | Marseille | 680 | FT |
| 1387701 | 2025-08-16T15:00:00+00:00 | Regular Season - 1 | 116 | Lens | 80 | Lyon | 654 | FT |
| 1387703 | 2025-08-16T17:00:00+00:00 | Regular Season - 1 | 91 | Monaco | 111 | Le Havre | 20470 | FT |
| 1387705 | 2025-08-16T19:05:00+00:00 | Regular Season - 1 | 84 | Nice | 96 | Toulouse | 663 | FT |
| 1387700 | 2025-08-17T13:00:00+00:00 | Regular Season - 1 | 106 | Stade Brestois 29 | 79 | Lille | 641 | FT |
| 1387698 | 2025-08-17T15:15:00+00:00 | Regular Season - 1 | 77 | Angers | 114 | Paris FC | 634 | FT |
| 1387699 | 2025-08-17T15:15:00+00:00 | Regular Season - 1 | 108 | Auxerre | 97 | Lorient | 636 | FT |
| 1387702 | 2025-08-17T15:15:00+00:00 | Regular Season - 1 | 112 | Metz | 95 | Strasbourg | 658 | FT |
| 1387704 | 2025-08-17T18:45:00+00:00 | Regular Season - 1 | 83 | Nantes | 85 | Paris Saint Germain | 662 | FT |
| 1387713 | 2025-08-22T18:45:00+00:00 | Regular Season - 2 | 85 | Paris Saint Germain | 77 | Angers | 671 | FT |
| 1387711 | 2025-08-23T15:00:00+00:00 | Regular Season - 2 | 81 | Marseille | 114 | Paris FC | 667 | FT |
| 1387712 | 2025-08-23T17:00:00+00:00 | Regular Season - 2 | 84 | Nice | 108 | Auxerre | 663 | FT |
| 1387710 | 2025-08-23T19:05:00+00:00 | Regular Season - 2 | 80 | Lyon | 112 | Metz | 666 | FT |
| 1387709 | 2025-08-24T13:00:00+00:00 | Regular Season - 2 | 97 | Lorient | 94 | Rennes | 21430 | FT |
| 1387714 | 2025-08-24T15:15:00+00:00 | Regular Season - 2 | 95 | Strasbourg | 83 | Nantes | 681 | FT |
| 1387715 | 2025-08-24T15:15:00+00:00 | Regular Season - 2 | 96 | Toulouse | 106 | Stade Brestois 29 | 682 | FT |
| 1387707 | 2025-08-24T15:15:00+00:00 | Regular Season - 2 | 111 | Le Havre | 116 | Lens | 652 | FT |
| 1387708 | 2025-08-24T18:45:00+00:00 | Regular Season - 2 | 79 | Lille | 91 | Monaco |  | FT |
| 1387718 | 2025-08-29T18:45:00+00:00 | Regular Season - 3 | 116 | Lens | 106 | Stade Brestois 29 | 654 | FT |
| 1387719 | 2025-08-30T15:00:00+00:00 | Regular Season - 3 | 97 | Lorient | 79 | Lille | 21430 | FT |
| 1387722 | 2025-08-30T17:00:00+00:00 | Regular Season - 3 | 83 | Nantes | 108 | Auxerre | 662 | FT |
| 1387724 | 2025-08-30T19:05:00+00:00 | Regular Season - 3 | 96 | Toulouse | 85 | Paris Saint Germain | 682 | FT |
| 1387716 | 2025-08-31T13:00:00+00:00 | Regular Season - 3 | 77 | Angers | 94 | Rennes | 634 | FT |
| 1387721 | 2025-08-31T15:15:00+00:00 | Regular Season - 3 | 91 | Monaco | 95 | Strasbourg | 20470 | FT |
| 1387717 | 2025-08-31T15:15:00+00:00 | Regular Season - 3 | 111 | Le Havre | 84 | Nice | 652 | FT |
| 1387723 | 2025-08-31T15:15:00+00:00 | Regular Season - 3 | 114 | Paris FC | 112 | Metz | 18861 | FT |
| 1387720 | 2025-08-31T18:45:00+00:00 | Regular Season - 3 | 80 | Lyon | 81 | Marseille | 666 | FT |
| 1387728 | 2025-09-12T18:45:00+00:00 | Regular Season - 4 | 81 | Marseille | 97 | Lorient | 667 | FT |
| 1387730 | 2025-09-13T15:00:00+00:00 | Regular Season - 4 | 84 | Nice | 83 | Nantes | 663 | FT |
| 1387725 | 2025-09-13T19:05:00+00:00 | Regular Season - 4 | 108 | Auxerre | 91 | Monaco | 636 | FT |
| 1387727 | 2025-09-14T13:00:00+00:00 | Regular Season - 4 | 79 | Lille | 96 | Toulouse |  | FT |
| 1387731 | 2025-09-14T15:15:00+00:00 | Regular Season - 4 | 85 | Paris Saint Germain | 116 | Lens | 671 | FT |
| 1387733 | 2025-09-14T15:15:00+00:00 | Regular Season - 4 | 95 | Strasbourg | 111 | Le Havre | 681 | FT |
| 1387726 | 2025-09-14T15:15:00+00:00 | Regular Season - 4 | 106 | Stade Brestois 29 | 114 | Paris FC | 641 | FT |
| 1387729 | 2025-09-14T15:15:00+00:00 | Regular Season - 4 | 112 | Metz | 77 | Angers | 658 | FT |
| 1387732 | 2025-09-14T18:45:00+00:00 | Regular Season - 4 | 94 | Rennes | 80 | Lyon | 680 | FT |
| 1387738 | 2025-09-19T18:45:00+00:00 | Regular Season - 5 | 80 | Lyon | 77 | Angers | 666 | FT |
| 1387741 | 2025-09-20T15:00:00+00:00 | Regular Season - 5 | 83 | Nantes | 94 | Rennes | 662 | FT |
| 1387735 | 2025-09-20T17:00:00+00:00 | Regular Season - 5 | 106 | Stade Brestois 29 | 84 | Nice | 641 | FT |
| 1387737 | 2025-09-20T19:05:00+00:00 | Regular Season - 5 | 116 | Lens | 79 | Lille | 654 | FT |
| 1387742 | 2025-09-21T13:00:00+00:00 | Regular Season - 5 | 114 | Paris FC | 95 | Strasbourg | 18861 | FT |
| 1387740 | 2025-09-21T15:15:00+00:00 | Regular Season - 5 | 91 | Monaco | 112 | Metz | 20470 | FT |
| 1387734 | 2025-09-21T15:15:00+00:00 | Regular Season - 5 | 108 | Auxerre | 96 | Toulouse | 636 | FT |
| 1387736 | 2025-09-21T15:15:00+00:00 | Regular Season - 5 | 111 | Le Havre | 97 | Lorient | 652 | FT |
| 1387739 | 2025-09-22T18:00:00+00:00 | Regular Season - 5 | 81 | Marseille | 85 | Paris Saint Germain | 667 | FT |
| 1387750 | 2025-09-26T18:45:00+00:00 | Regular Season - 6 | 95 | Strasbourg | 81 | Marseille | 681 | FT |
| 1387745 | 2025-09-27T15:00:00+00:00 | Regular Season - 6 | 97 | Lorient | 91 | Monaco | 21430 | FT |
| 1387751 | 2025-09-27T17:00:00+00:00 | Regular Season - 6 | 96 | Toulouse | 83 | Nantes | 682 | FT |
| 1387748 | 2025-09-27T19:05:00+00:00 | Regular Season - 6 | 85 | Paris Saint Germain | 108 | Auxerre | 671 | FT |
| 1387747 | 2025-09-28T13:00:00+00:00 | Regular Season - 6 | 84 | Nice | 114 | Paris FC | 663 | FT |
| 1387743 | 2025-09-28T15:15:00+00:00 | Regular Season - 6 | 77 | Angers | 106 | Stade Brestois 29 | 634 | FT |
| 1387744 | 2025-09-28T15:15:00+00:00 | Regular Season - 6 | 79 | Lille | 80 | Lyon |  | FT |
| 1387746 | 2025-09-28T15:15:00+00:00 | Regular Season - 6 | 112 | Metz | 111 | Le Havre | 658 | FT |
| 1387749 | 2025-09-28T18:45:00+00:00 | Regular Season - 6 | 94 | Rennes | 116 | Lens | 680 | FT |
| 1387759 | 2025-10-03T18:45:00+00:00 | Regular Season - 7 | 114 | Paris FC | 97 | Lorient | 18861 | FT |
| 1387757 | 2025-10-04T15:00:00+00:00 | Regular Season - 7 | 112 | Metz | 81 | Marseille | 658 | FT |
| 1387753 | 2025-10-04T17:00:00+00:00 | Regular Season - 7 | 106 | Stade Brestois 29 | 83 | Nantes | 641 | FT |
| 1387752 | 2025-10-04T19:05:00+00:00 | Regular Season - 7 | 108 | Auxerre | 116 | Lens | 636 | FT |
| 1387756 | 2025-10-05T13:00:00+00:00 | Regular Season - 7 | 80 | Lyon | 96 | Toulouse | 666 | FT |
| 1387758 | 2025-10-05T15:15:00+00:00 | Regular Season - 7 | 91 | Monaco | 84 | Nice | 20470 | FT |
| 1387760 | 2025-10-05T15:15:00+00:00 | Regular Season - 7 | 95 | Strasbourg | 77 | Angers | 681 | FT |
| 1387754 | 2025-10-05T15:15:00+00:00 | Regular Season - 7 | 111 | Le Havre | 94 | Rennes | 652 | FT |
| 1387755 | 2025-10-05T18:45:00+00:00 | Regular Season - 7 | 79 | Lille | 85 | Paris Saint Germain |  | FT |
| 1387767 | 2025-10-17T18:45:00+00:00 | Regular Season - 8 | 85 | Paris Saint Germain | 95 | Strasbourg | 671 | FT |
| 1387766 | 2025-10-18T15:00:00+00:00 | Regular Season - 8 | 84 | Nice | 80 | Lyon | 663 | FT |
| 1387761 | 2025-10-18T17:00:00+00:00 | Regular Season - 8 | 77 | Angers | 91 | Monaco | 634 | FT |
| 1387764 | 2025-10-18T19:05:00+00:00 | Regular Season - 8 | 81 | Marseille | 111 | Le Havre | 667 | FT |
| 1387762 | 2025-10-19T13:00:00+00:00 | Regular Season - 8 | 116 | Lens | 114 | Paris FC | 654 | FT |
| 1387768 | 2025-10-19T15:15:00+00:00 | Regular Season - 8 | 94 | Rennes | 108 | Auxerre | 680 | FT |
| 1387769 | 2025-10-19T15:15:00+00:00 | Regular Season - 8 | 96 | Toulouse | 112 | Metz | 682 | FT |
| 1387763 | 2025-10-19T15:15:00+00:00 | Regular Season - 8 | 97 | Lorient | 106 | Stade Brestois 29 | 21430 | FT |
| 1387765 | 2025-10-19T18:45:00+00:00 | Regular Season - 8 | 83 | Nantes | 79 | Lille | 662 | FT |
| 1387777 | 2025-10-24T18:45:00+00:00 | Regular Season - 9 | 114 | Paris FC | 83 | Nantes | 18861 | FT |
| 1387772 | 2025-10-25T15:00:00+00:00 | Regular Season - 9 | 106 | Stade Brestois 29 | 85 | Paris Saint Germain | 641 | FT |
| 1387776 | 2025-10-25T17:00:00+00:00 | Regular Season - 9 | 91 | Monaco | 96 | Toulouse | 20470 | FT |
| 1387773 | 2025-10-25T19:05:00+00:00 | Regular Season - 9 | 116 | Lens | 81 | Marseille | 654 | FT |
| 1387774 | 2025-10-26T14:00:00+00:00 | Regular Season - 9 | 79 | Lille | 112 | Metz |  | FT |
| 1387770 | 2025-10-26T16:15:00+00:00 | Regular Season - 9 | 77 | Angers | 97 | Lorient | 634 | FT |
| 1387778 | 2025-10-26T16:15:00+00:00 | Regular Season - 9 | 94 | Rennes | 84 | Nice | 680 | FT |
| 1387771 | 2025-10-26T16:15:00+00:00 | Regular Season - 9 | 108 | Auxerre | 111 | Le Havre | 636 | FT |
| 1387775 | 2025-10-26T19:45:00+00:00 | Regular Season - 9 | 80 | Lyon | 95 | Strasbourg | 666 | FT |
| 1387784 | 2025-10-29T18:00:00+00:00 | Regular Season - 10 | 84 | Nice | 79 | Lille | 663 | FT |
| 1387780 | 2025-10-29T18:00:00+00:00 | Regular Season - 10 | 97 | Lorient | 85 | Paris Saint Germain | 21430 | FT |
| 1387779 | 2025-10-29T18:00:00+00:00 | Regular Season - 10 | 111 | Le Havre | 106 | Stade Brestois 29 | 652 | FT |
| 1387782 | 2025-10-29T18:00:00+00:00 | Regular Season - 10 | 112 | Metz | 116 | Lens | 658 | FT |
| 1387781 | 2025-10-29T20:05:00+00:00 | Regular Season - 10 | 81 | Marseille | 77 | Angers | 667 | FT |
| 1387783 | 2025-10-29T20:05:00+00:00 | Regular Season - 10 | 83 | Nantes | 91 | Monaco | 662 | FT |
| 1387786 | 2025-10-29T20:05:00+00:00 | Regular Season - 10 | 95 | Strasbourg | 108 | Auxerre | 681 | FT |
| 1387787 | 2025-10-29T20:05:00+00:00 | Regular Season - 10 | 96 | Toulouse | 94 | Rennes | 682 | FT |
| 1387785 | 2025-10-29T20:05:00+00:00 | Regular Season - 10 | 114 | Paris FC | 80 | Lyon | 18861 | FT |
| 1387794 | 2025-11-01T16:00:00+00:00 | Regular Season - 11 | 85 | Paris Saint Germain | 84 | Nice | 671 | FT |
| 1387792 | 2025-11-01T18:00:00+00:00 | Regular Season - 11 | 91 | Monaco | 114 | Paris FC | 20470 | FT |
| 1387788 | 2025-11-01T20:05:00+00:00 | Regular Season - 11 | 108 | Auxerre | 81 | Marseille | 636 | FT |
| 1387795 | 2025-11-02T14:00:00+00:00 | Regular Season - 11 | 94 | Rennes | 95 | Strasbourg | 680 | FT |
| 1387791 | 2025-11-02T16:15:00+00:00 | Regular Season - 11 | 79 | Lille | 77 | Angers |  | FT |
| 1387793 | 2025-11-02T16:15:00+00:00 | Regular Season - 11 | 83 | Nantes | 112 | Metz | 662 | FT |
| 1387796 | 2025-11-02T16:15:00+00:00 | Regular Season - 11 | 96 | Toulouse | 111 | Le Havre | 682 | FT |
| 1387790 | 2025-11-02T16:15:00+00:00 | Regular Season - 11 | 116 | Lens | 97 | Lorient | 654 | FT |
| 1387789 | 2025-11-02T19:45:00+00:00 | Regular Season - 11 | 106 | Stade Brestois 29 | 80 | Lyon | 641 | FT |
| 1387804 | 2025-11-07T19:45:00+00:00 | Regular Season - 12 | 114 | Paris FC | 94 | Rennes | 18861 | FT |
| 1387801 | 2025-11-08T16:00:00+00:00 | Regular Season - 12 | 81 | Marseille | 106 | Stade Brestois 29 | 667 | FT |
| 1387798 | 2025-11-08T18:00:00+00:00 | Regular Season - 12 | 111 | Le Havre | 83 | Nantes | 652 | FT |
| 1387803 | 2025-11-08T20:05:00+00:00 | Regular Season - 12 | 91 | Monaco | 116 | Lens | 20470 | FT |
| 1387799 | 2025-11-09T14:00:00+00:00 | Regular Season - 12 | 97 | Lorient | 96 | Toulouse | 21430 | FT |
| 1387797 | 2025-11-09T16:15:00+00:00 | Regular Season - 12 | 77 | Angers | 108 | Auxerre | 634 | FT |
| 1387805 | 2025-11-09T16:15:00+00:00 | Regular Season - 12 | 95 | Strasbourg | 79 | Lille | 681 | FT |
| 1387802 | 2025-11-09T16:15:00+00:00 | Regular Season - 12 | 112 | Metz | 84 | Nice | 658 | FT |
| 1387800 | 2025-11-09T19:45:00+00:00 | Regular Season - 12 | 80 | Lyon | 85 | Paris Saint Germain | 666 | FT |
| 1387811 | 2025-11-21T19:45:00+00:00 | Regular Season - 13 | 84 | Nice | 81 | Marseille | 663 | FT |
| 1387808 | 2025-11-22T16:00:00+00:00 | Regular Season - 13 | 116 | Lens | 95 | Strasbourg | 654 | FT |
| 1387813 | 2025-11-22T18:00:00+00:00 | Regular Season - 13 | 94 | Rennes | 91 | Monaco | 680 | FT |
| 1387812 | 2025-11-22T20:05:00+00:00 | Regular Season - 13 | 85 | Paris Saint Germain | 111 | Le Havre | 671 | FT |
| 1387806 | 2025-11-23T14:00:00+00:00 | Regular Season - 13 | 108 | Auxerre | 80 | Lyon | 636 | FT |
| 1387810 | 2025-11-23T16:15:00+00:00 | Regular Season - 13 | 83 | Nantes | 97 | Lorient | 662 | FT |
| 1387814 | 2025-11-23T16:15:00+00:00 | Regular Season - 13 | 96 | Toulouse | 77 | Angers | 682 | FT |
| 1387807 | 2025-11-23T16:15:00+00:00 | Regular Season - 13 | 106 | Stade Brestois 29 | 112 | Metz | 641 | FT |
| 1387809 | 2025-11-23T19:45:00+00:00 | Regular Season - 13 | 79 | Lille | 114 | Paris FC |  | FT |
| 1387820 | 2025-11-28T19:45:00+00:00 | Regular Season - 14 | 112 | Metz | 94 | Rennes | 658 | FT |
| 1387821 | 2025-11-29T16:00:00+00:00 | Regular Season - 14 | 91 | Monaco | 85 | Paris Saint Germain | 20470 | FT |
| 1387822 | 2025-11-29T18:00:00+00:00 | Regular Season - 14 | 114 | Paris FC | 108 | Auxerre | 18861 | FT |
| 1387819 | 2025-11-29T20:05:00+00:00 | Regular Season - 14 | 81 | Marseille | 96 | Toulouse | 667 | FT |
| 1387823 | 2025-11-30T14:00:00+00:00 | Regular Season - 14 | 95 | Strasbourg | 106 | Stade Brestois 29 | 681 | FT |
| 1387815 | 2025-11-30T16:15:00+00:00 | Regular Season - 14 | 77 | Angers | 116 | Lens | 634 | FT |
| 1387817 | 2025-11-30T16:15:00+00:00 | Regular Season - 14 | 97 | Lorient | 84 | Nice | 21430 | FT |
| 1387816 | 2025-11-30T16:15:00+00:00 | Regular Season - 14 | 111 | Le Havre | 79 | Lille | 652 | FT |
| 1387818 | 2025-11-30T19:45:00+00:00 | Regular Season - 14 | 80 | Lyon | 83 | Nantes | 666 | FT |
| 1387825 | 2025-12-05T18:00:00+00:00 | Regular Season - 15 | 106 | Stade Brestois 29 | 91 | Monaco | 641 | FT |
| 1387827 | 2025-12-05T20:00:00+00:00 | Regular Season - 15 | 79 | Lille | 81 | Marseille |  | FT |
| 1387829 | 2025-12-06T16:00:00+00:00 | Regular Season - 15 | 83 | Nantes | 116 | Lens | 662 | FT |
| 1387832 | 2025-12-06T18:00:00+00:00 | Regular Season - 15 | 96 | Toulouse | 95 | Strasbourg | 682 | FT |
| 1387831 | 2025-12-06T20:05:00+00:00 | Regular Season - 15 | 85 | Paris Saint Germain | 94 | Rennes | 671 | FT |
| 1387830 | 2025-12-07T14:00:00+00:00 | Regular Season - 15 | 84 | Nice | 77 | Angers | 663 | FT |
| 1387824 | 2025-12-07T16:15:00+00:00 | Regular Season - 15 | 108 | Auxerre | 112 | Metz | 636 | FT |
| 1387826 | 2025-12-07T16:15:00+00:00 | Regular Season - 15 | 111 | Le Havre | 114 | Paris FC | 652 | FT |
| 1387828 | 2025-12-07T19:45:00+00:00 | Regular Season - 15 | 97 | Lorient | 80 | Lyon | 21430 | FT |
| 1387833 | 2025-12-12T19:45:00+00:00 | Regular Season - 16 | 77 | Angers | 83 | Nantes | 634 | FT |
| 1387840 | 2025-12-13T16:00:00+00:00 | Regular Season - 16 | 94 | Rennes | 106 | Stade Brestois 29 | 680 | FT |
| 1387838 | 2025-12-13T18:00:00+00:00 | Regular Season - 16 | 112 | Metz | 85 | Paris Saint Germain | 658 | FT |
| 1387839 | 2025-12-13T20:05:00+00:00 | Regular Season - 16 | 114 | Paris FC | 96 | Toulouse | 18861 | FT |
| 1387836 | 2025-12-14T14:00:00+00:00 | Regular Season - 16 | 80 | Lyon | 111 | Le Havre | 666 | FT |
| 1387841 | 2025-12-14T16:15:00+00:00 | Regular Season - 16 | 95 | Strasbourg | 97 | Lorient | 681 | FT |
| 1387834 | 2025-12-14T16:15:00+00:00 | Regular Season - 16 | 108 | Auxerre | 79 | Lille | 636 | FT |
| 1387835 | 2025-12-14T16:15:00+00:00 | Regular Season - 16 | 116 | Lens | 84 | Nice | 654 | FT |
| 1387837 | 2025-12-14T19:45:00+00:00 | Regular Season - 16 | 81 | Marseille | 91 | Monaco | 667 | FT |
| 1387850 | 2026-01-02T19:45:00+00:00 | Regular Season - 17 | 96 | Toulouse | 116 | Lens | 682 | FT |
| 1387847 | 2026-01-03T16:00:00+00:00 | Regular Season - 17 | 91 | Monaco | 80 | Lyon | 20470 | FT |
| 1387848 | 2026-01-03T18:00:00+00:00 | Regular Season - 17 | 84 | Nice | 95 | Strasbourg | 663 | FT |
| 1387844 | 2026-01-03T20:05:00+00:00 | Regular Season - 17 | 79 | Lille | 94 | Rennes |  | FT |
| 1387846 | 2026-01-04T14:00:00+00:00 | Regular Season - 17 | 81 | Marseille | 83 | Nantes | 667 | FT |
| 1387845 | 2026-01-04T16:15:00+00:00 | Regular Season - 17 | 97 | Lorient | 112 | Metz | 21430 | FT |
| 1387842 | 2026-01-04T16:15:00+00:00 | Regular Season - 17 | 106 | Stade Brestois 29 | 108 | Auxerre | 641 | FT |
| 1387843 | 2026-01-04T16:15:00+00:00 | Regular Season - 17 | 111 | Le Havre | 77 | Angers | 652 | FT |
| 1387849 | 2026-01-04T19:45:00+00:00 | Regular Season - 17 | 85 | Paris Saint Germain | 114 | Paris FC | 671 | FT |
| 1387854 | 2026-01-16T18:00:00+00:00 | Regular Season - 18 | 91 | Monaco | 97 | Lorient | 20470 | FT |
| 1387856 | 2026-01-16T20:00:00+00:00 | Regular Season - 18 | 85 | Paris Saint Germain | 79 | Lille | 671 | FT |
| 1387852 | 2026-01-17T16:00:00+00:00 | Regular Season - 18 | 116 | Lens | 108 | Auxerre | 654 | FT |
| 1387859 | 2026-01-17T18:00:00+00:00 | Regular Season - 18 | 96 | Toulouse | 84 | Nice | 682 | FT |
| 1387851 | 2026-01-17T20:05:00+00:00 | Regular Season - 18 | 77 | Angers | 81 | Marseille | 634 | FT |
| 1387858 | 2026-01-18T14:00:00+00:00 | Regular Season - 18 | 95 | Strasbourg | 112 | Metz | 681 | FT |
| 1387855 | 2026-01-18T16:15:00+00:00 | Regular Season - 18 | 83 | Nantes | 114 | Paris FC | 662 | FT |
| 1387857 | 2026-01-18T16:15:00+00:00 | Regular Season - 18 | 94 | Rennes | 111 | Le Havre | 680 | FT |
| 1387853 | 2026-01-18T19:45:00+00:00 | Regular Season - 18 | 80 | Lyon | 106 | Stade Brestois 29 | 666 | FT |
| 1387860 | 2026-01-23T19:00:00+00:00 | Regular Season - 19 | 108 | Auxerre | 85 | Paris Saint Germain | 636 | FT |
| 1387868 | 2026-01-24T16:00:00+00:00 | Regular Season - 19 | 94 | Rennes | 97 | Lorient | 680 | FT |
| 1387862 | 2026-01-24T18:00:00+00:00 | Regular Season - 19 | 111 | Le Havre | 91 | Monaco | 652 | FT |
| 1387864 | 2026-01-24T20:05:00+00:00 | Regular Season - 19 | 81 | Marseille | 116 | Lens | 667 | FT |
| 1387866 | 2026-01-25T14:00:00+00:00 | Regular Season - 19 | 83 | Nantes | 84 | Nice | 662 | FT |
| 1387861 | 2026-01-25T16:15:00+00:00 | Regular Season - 19 | 106 | Stade Brestois 29 | 96 | Toulouse | 641 | FT |
| 1387865 | 2026-01-25T16:15:00+00:00 | Regular Season - 19 | 112 | Metz | 80 | Lyon | 658 | FT |
| 1387867 | 2026-01-25T16:15:00+00:00 | Regular Season - 19 | 114 | Paris FC | 77 | Angers | 18861 | FT |
| 1387863 | 2026-01-25T19:45:00+00:00 | Regular Season - 19 | 79 | Lille | 95 | Strasbourg |  | FT |
| 1387870 | 2026-01-30T19:45:00+00:00 | Regular Season - 20 | 116 | Lens | 111 | Le Havre | 654 | FT |
| 1387875 | 2026-01-31T16:00:00+00:00 | Regular Season - 20 | 114 | Paris FC | 81 | Marseille | 18861 | FT |
| 1387871 | 2026-01-31T18:00:00+00:00 | Regular Season - 20 | 97 | Lorient | 83 | Nantes | 21430 | FT |
| 1387873 | 2026-01-31T20:05:00+00:00 | Regular Season - 20 | 91 | Monaco | 94 | Rennes | 20470 | FT |
| 1387872 | 2026-02-01T14:00:00+00:00 | Regular Season - 20 | 80 | Lyon | 79 | Lille | 666 | FT |
| 1387869 | 2026-02-01T16:15:00+00:00 | Regular Season - 20 | 77 | Angers | 112 | Metz | 634 | FT |
| 1387874 | 2026-02-01T16:15:00+00:00 | Regular Season - 20 | 84 | Nice | 106 | Stade Brestois 29 | 663 | FT |
| 1387877 | 2026-02-01T16:15:00+00:00 | Regular Season - 20 | 96 | Toulouse | 108 | Auxerre | 682 | FT |
| 1387876 | 2026-02-01T19:45:00+00:00 | Regular Season - 20 | 95 | Strasbourg | 85 | Paris Saint Germain | 681 | FT |
| 1387883 | 2026-02-06T19:45:00+00:00 | Regular Season - 21 | 112 | Metz | 79 | Lille | 658 | FT |
| 1387882 | 2026-02-07T16:00:00+00:00 | Regular Season - 21 | 116 | Lens | 94 | Rennes | 654 | FT |
| 1387880 | 2026-02-07T18:00:00+00:00 | Regular Season - 21 | 106 | Stade Brestois 29 | 97 | Lorient | 641 | FT |
| 1387884 | 2026-02-07T20:05:00+00:00 | Regular Season - 21 | 83 | Nantes | 80 | Lyon | 662 | FT |
| 1387885 | 2026-02-08T14:00:00+00:00 | Regular Season - 21 | 84 | Nice | 91 | Monaco | 663 | FT |
| 1387878 | 2026-02-08T16:15:00+00:00 | Regular Season - 21 | 77 | Angers | 96 | Toulouse | 634 | FT |
| 1387879 | 2026-02-08T16:15:00+00:00 | Regular Season - 21 | 108 | Auxerre | 114 | Paris FC | 636 | FT |
| 1387881 | 2026-02-08T16:15:00+00:00 | Regular Season - 21 | 111 | Le Havre | 95 | Strasbourg | 652 | FT |
| 1387886 | 2026-02-08T19:45:00+00:00 | Regular Season - 21 | 85 | Paris Saint Germain | 81 | Marseille | 671 | FT |
| 1387895 | 2026-02-13T18:00:00+00:00 | Regular Season - 22 | 94 | Rennes | 85 | Paris Saint Germain | 680 | FT |
| 1387893 | 2026-02-13T20:05:00+00:00 | Regular Season - 22 | 91 | Monaco | 83 | Nantes | 20470 | FT |
| 1387891 | 2026-02-14T16:00:00+00:00 | Regular Season - 22 | 81 | Marseille | 95 | Strasbourg | 667 | FT |
| 1387888 | 2026-02-14T18:00:00+00:00 | Regular Season - 22 | 79 | Lille | 106 | Stade Brestois 29 |  | FT |
| 1387894 | 2026-02-14T20:05:00+00:00 | Regular Season - 22 | 114 | Paris FC | 116 | Lens | 18861 | FT |
| 1387887 | 2026-02-15T14:00:00+00:00 | Regular Season - 22 | 111 | Le Havre | 96 | Toulouse | 652 | FT |
| 1387889 | 2026-02-15T16:15:00+00:00 | Regular Season - 22 | 97 | Lorient | 77 | Angers | 21430 | FT |
| 1387892 | 2026-02-15T16:15:00+00:00 | Regular Season - 22 | 112 | Metz | 108 | Auxerre | 658 | FT |
| 1387890 | 2026-02-15T19:45:00+00:00 | Regular Season - 22 | 80 | Lyon | 84 | Nice | 666 | FT |
| 1387898 | 2026-02-20T19:45:00+00:00 | Regular Season - 23 | 106 | Stade Brestois 29 | 81 | Marseille | 641 | FT |
| 1387899 | 2026-02-21T16:00:00+00:00 | Regular Season - 23 | 116 | Lens | 91 | Monaco | 654 | FT |
| 1387904 | 2026-02-21T18:00:00+00:00 | Regular Season - 23 | 96 | Toulouse | 114 | Paris FC | 682 | FT |
| 1387902 | 2026-02-21T20:05:00+00:00 | Regular Season - 23 | 85 | Paris Saint Germain | 112 | Metz | 671 | FT |
| 1387897 | 2026-02-22T14:00:00+00:00 | Regular Season - 23 | 108 | Auxerre | 94 | Rennes | 636 | FT |
| 1387896 | 2026-02-22T16:15:00+00:00 | Regular Season - 23 | 77 | Angers | 79 | Lille | 634 | FT |
| 1387900 | 2026-02-22T16:15:00+00:00 | Regular Season - 23 | 83 | Nantes | 111 | Le Havre | 662 | FT |
| 1387901 | 2026-02-22T16:15:00+00:00 | Regular Season - 23 | 84 | Nice | 97 | Lorient | 663 | FT |
| 1387903 | 2026-02-22T19:45:00+00:00 | Regular Season - 23 | 95 | Strasbourg | 80 | Lyon | 681 | FT |
| 1387913 | 2026-02-27T19:45:00+00:00 | Regular Season - 24 | 95 | Strasbourg | 116 | Lens | 681 | FT |
| 1387912 | 2026-02-28T16:00:00+00:00 | Regular Season - 24 | 94 | Rennes | 96 | Toulouse | 680 | FT |
| 1387910 | 2026-02-28T18:00:00+00:00 | Regular Season - 24 | 91 | Monaco | 77 | Angers | 20470 | FT |
| 1387905 | 2026-02-28T20:05:00+00:00 | Regular Season - 24 | 111 | Le Havre | 85 | Paris Saint Germain | 652 | FT |
| 1387911 | 2026-03-01T14:00:00+00:00 | Regular Season - 24 | 114 | Paris FC | 84 | Nice | 18861 | FT |
| 1387906 | 2026-03-01T16:15:00+00:00 | Regular Season - 24 | 79 | Lille | 83 | Nantes |  | FT |
| 1387907 | 2026-03-01T16:15:00+00:00 | Regular Season - 24 | 97 | Lorient | 108 | Auxerre | 21430 | FT |
| 1387909 | 2026-03-01T16:15:00+00:00 | Regular Season - 24 | 112 | Metz | 106 | Stade Brestois 29 | 658 | FT |
| 1387908 | 2026-03-01T19:45:00+00:00 | Regular Season - 24 | 81 | Marseille | 80 | Lyon | 667 | FT |
| 1387921 | 2026-03-06T19:45:00+00:00 | Regular Season - 25 | 85 | Paris Saint Germain | 91 | Monaco | 671 | FT |
| 1387919 | 2026-03-07T16:00:00+00:00 | Regular Season - 25 | 83 | Nantes | 77 | Angers | 662 | FT |
| 1387914 | 2026-03-07T18:00:00+00:00 | Regular Season - 25 | 108 | Auxerre | 95 | Strasbourg | 636 | FT |
| 1387922 | 2026-03-07T20:05:00+00:00 | Regular Season - 25 | 96 | Toulouse | 81 | Marseille | 682 | FT |
| 1387916 | 2026-03-08T14:00:00+00:00 | Regular Season - 25 | 116 | Lens | 112 | Metz | 654 | FT |
| 1387917 | 2026-03-08T16:15:00+00:00 | Regular Season - 25 | 79 | Lille | 97 | Lorient |  | FT |
| 1387920 | 2026-03-08T16:15:00+00:00 | Regular Season - 25 | 84 | Nice | 94 | Rennes | 663 | FT |
| 1387915 | 2026-03-08T16:15:00+00:00 | Regular Season - 25 | 106 | Stade Brestois 29 | 111 | Le Havre | 641 | FT |
| 1387918 | 2026-03-08T19:45:00+00:00 | Regular Season - 25 | 80 | Lyon | 114 | Paris FC | 666 | FT |
| 1387926 | 2026-03-13T19:45:00+00:00 | Regular Season - 26 | 81 | Marseille | 108 | Auxerre | 667 | FT |
| 1387925 | 2026-03-14T16:00:00+00:00 | Regular Season - 26 | 97 | Lorient | 116 | Lens | 21430 | FT |
| 1387923 | 2026-03-14T18:00:00+00:00 | Regular Season - 26 | 77 | Angers | 84 | Nice | 634 | FT |
| 1387928 | 2026-03-14T20:05:00+00:00 | Regular Season - 26 | 91 | Monaco | 106 | Stade Brestois 29 | 20470 | FT |
| 1387931 | 2026-03-15T14:00:00+00:00 | Regular Season - 26 | 95 | Strasbourg | 114 | Paris FC | 681 | FT |
| 1387924 | 2026-03-15T16:15:00+00:00 | Regular Season - 26 | 111 | Le Havre | 80 | Lyon | 652 | FT |
| 1387927 | 2026-03-15T16:15:00+00:00 | Regular Season - 26 | 112 | Metz | 96 | Toulouse | 658 | FT |
| 1387930 | 2026-03-15T19:45:00+00:00 | Regular Season - 26 | 94 | Rennes | 79 | Lille | 680 | FT |
| 1387933 | 2026-03-20T19:45:00+00:00 | Regular Season - 27 | 116 | Lens | 77 | Angers | 654 | FT |
| 1387940 | 2026-03-21T16:00:00+00:00 | Regular Season - 27 | 96 | Toulouse | 97 | Lorient | 682 | FT |
| 1387932 | 2026-03-21T18:00:00+00:00 | Regular Season - 27 | 108 | Auxerre | 106 | Stade Brestois 29 | 636 | FT |
| 1387937 | 2026-03-21T20:05:00+00:00 | Regular Season - 27 | 84 | Nice | 85 | Paris Saint Germain | 663 | FT |
| 1387934 | 2026-03-22T14:00:00+00:00 | Regular Season - 27 | 80 | Lyon | 91 | Monaco | 666 | FT |
| 1387935 | 2026-03-22T16:15:00+00:00 | Regular Season - 27 | 81 | Marseille | 79 | Lille | 667 | FT |
| 1387939 | 2026-03-22T16:15:00+00:00 | Regular Season - 27 | 94 | Rennes | 112 | Metz | 680 | FT |
| 1387938 | 2026-03-22T16:15:00+00:00 | Regular Season - 27 | 114 | Paris FC | 111 | Le Havre | 18861 | FT |
| 1387936 | 2026-03-22T19:45:00+00:00 | Regular Season - 27 | 83 | Nantes | 95 | Strasbourg | 662 | FT |
| 1387948 | 2026-04-03T18:45:00+00:00 | Regular Season - 28 | 85 | Paris Saint Germain | 96 | Toulouse | 671 | FT |
| 1387949 | 2026-04-04T15:00:00+00:00 | Regular Season - 28 | 95 | Strasbourg | 84 | Nice | 681 | FT |
| 1387942 | 2026-04-04T17:00:00+00:00 | Regular Season - 28 | 106 | Stade Brestois 29 | 94 | Rennes | 641 | FT |
| 1387944 | 2026-04-04T19:05:00+00:00 | Regular Season - 28 | 79 | Lille | 116 | Lens |  | FT |
| 1387941 | 2026-04-05T13:00:00+00:00 | Regular Season - 28 | 77 | Angers | 80 | Lyon | 0 | FT |
| 1387945 | 2026-04-05T15:15:00+00:00 | Regular Season - 28 | 97 | Lorient | 114 | Paris FC | 21430 | FT |
| 1387943 | 2026-04-05T15:15:00+00:00 | Regular Season - 28 | 111 | Le Havre | 108 | Auxerre | 652 | FT |
| 1387946 | 2026-04-05T15:15:00+00:00 | Regular Season - 28 | 112 | Metz | 83 | Nantes | 658 | FT |
| 1387947 | 2026-04-05T18:45:00+00:00 | Regular Season - 28 | 91 | Monaco | 81 | Marseille | 20470 | FT |
| 1387956 | 2026-04-10T17:00:00+00:00 | Regular Season - 29 | 114 | Paris FC | 91 | Monaco | 18861 | FT |
| 1387954 | 2026-04-10T19:05:00+00:00 | Regular Season - 29 | 81 | Marseille | 112 | Metz | 667 | FT |
| 1387950 | 2026-04-11T17:00:00+00:00 | Regular Season - 29 | 108 | Auxerre | 83 | Nantes | 636 | FT |
| 1387957 | 2026-04-11T19:05:00+00:00 | Regular Season - 29 | 94 | Rennes | 77 | Angers | 680 | FT |
| 1387955 | 2026-04-12T15:15:00+00:00 | Regular Season - 29 | 84 | Nice | 111 | Le Havre | 663 | FT |
| 1387958 | 2026-04-12T15:15:00+00:00 | Regular Season - 29 | 96 | Toulouse | 79 | Lille | 682 | FT |
| 1387953 | 2026-04-12T18:45:00+00:00 | Regular Season - 29 | 80 | Lyon | 97 | Lorient | 666 | FT |
| 1387960 | 2026-04-17T18:45:00+00:00 | Regular Season - 30 | 116 | Lens | 96 | Toulouse | 654 | FT |
| 1387962 | 2026-04-18T15:00:00+00:00 | Regular Season - 30 | 97 | Lorient | 81 | Marseille | 21430 | FT |
| 1387959 | 2026-04-18T17:00:00+00:00 | Regular Season - 30 | 77 | Angers | 111 | Le Havre | 0 | FT |
| 1387961 | 2026-04-18T19:05:00+00:00 | Regular Season - 30 | 79 | Lille | 84 | Nice | 0 | FT |
| 1387964 | 2026-04-19T13:00:00+00:00 | Regular Season - 30 | 91 | Monaco | 108 | Auxerre | 20470 | FT |
| 1387965 | 2026-04-19T15:15:00+00:00 | Regular Season - 30 | 83 | Nantes | 106 | Stade Brestois 29 | 662 | FT |
| 1387967 | 2026-04-19T15:15:00+00:00 | Regular Season - 30 | 95 | Strasbourg | 94 | Rennes | 681 | FT |
| 1387963 | 2026-04-19T15:15:00+00:00 | Regular Season - 30 | 112 | Metz | 114 | Paris FC | 658 | FT |
| 1387966 | 2026-04-19T18:45:00+00:00 | Regular Season - 30 | 85 | Paris Saint Germain | 80 | Lyon | 671 | FT |
| 1387929 | 2026-04-22T17:00:00+00:00 | Regular Season - 26 | 85 | Paris Saint Germain | 83 | Nantes | 671 | FT |
| 1387969 | 2026-04-24T18:45:00+00:00 | Regular Season - 31 | 106 | Stade Brestois 29 | 116 | Lens | 641 | FT |
| 1387972 | 2026-04-25T13:00:00+00:00 | Regular Season - 31 | 80 | Lyon | 108 | Auxerre | 666 | FT |
| 1387968 | 2026-04-25T17:00:00+00:00 | Regular Season - 31 | 77 | Angers | 85 | Paris Saint Germain | 0 | FT |
| 1387976 | 2026-04-25T19:05:00+00:00 | Regular Season - 31 | 96 | Toulouse | 91 | Monaco | 682 | FT |
| 1387971 | 2026-04-26T13:00:00+00:00 | Regular Season - 31 | 97 | Lorient | 95 | Strasbourg | 21430 | FT |
| 1387975 | 2026-04-26T15:15:00+00:00 | Regular Season - 31 | 94 | Rennes | 83 | Nantes | 680 | FT |
| 1387970 | 2026-04-26T15:15:00+00:00 | Regular Season - 31 | 111 | Le Havre | 112 | Metz | 652 | FT |
| 1387974 | 2026-04-26T15:15:00+00:00 | Regular Season - 31 | 114 | Paris FC | 79 | Lille | 18861 | FT |
| 1387973 | 2026-04-26T18:45:00+00:00 | Regular Season - 31 | 81 | Marseille | 84 | Nice | 667 | FT |
| 1387981 | 2026-05-02T13:00:00+00:00 | Regular Season - 32 | 83 | Nantes | 81 | Marseille | 662 | NS |
| 1387984 | 2026-05-02T15:00:00+00:00 | Regular Season - 32 | 85 | Paris Saint Germain | 97 | Lorient | 671 | NS |
| 1387980 | 2026-05-02T17:00:00+00:00 | Regular Season - 32 | 112 | Metz | 91 | Monaco | 658 | NS |
| 1387982 | 2026-05-02T19:05:00+00:00 | Regular Season - 32 | 84 | Nice | 116 | Lens | 663 | NS |
| 1387978 | 2026-05-03T13:00:00+00:00 | Regular Season - 32 | 79 | Lille | 111 | Le Havre |  | NS |
| 1387985 | 2026-05-03T15:15:00+00:00 | Regular Season - 32 | 95 | Strasbourg | 96 | Toulouse | 681 | NS |
| 1387977 | 2026-05-03T15:15:00+00:00 | Regular Season - 32 | 108 | Auxerre | 77 | Angers | 636 | NS |
| 1387983 | 2026-05-03T15:15:00+00:00 | Regular Season - 32 | 114 | Paris FC | 106 | Stade Brestois 29 | 18861 | NS |
| 1387979 | 2026-05-03T18:45:00+00:00 | Regular Season - 32 | 80 | Lyon | 94 | Rennes | 666 | NS |
| 1387989 | 2026-05-08T18:45:00+00:00 | Regular Season - 33 | 116 | Lens | 83 | Nantes | 654 | NS |
| 1387986 | 2026-05-10T19:00:00+00:00 | Regular Season - 33 | 77 | Angers | 95 | Strasbourg | 0 | NS |
| 1387992 | 2026-05-10T19:00:00+00:00 | Regular Season - 33 | 85 | Paris Saint Germain | 106 | Stade Brestois 29 | 671 | NS |
| 1387991 | 2026-05-10T19:00:00+00:00 | Regular Season - 33 | 91 | Monaco | 79 | Lille | 20470 | NS |
| 1387993 | 2026-05-10T19:00:00+00:00 | Regular Season - 33 | 94 | Rennes | 114 | Paris FC | 680 | NS |
| 1387994 | 2026-05-10T19:00:00+00:00 | Regular Season - 33 | 96 | Toulouse | 80 | Lyon | 682 | NS |
| 1387987 | 2026-05-10T19:00:00+00:00 | Regular Season - 33 | 108 | Auxerre | 84 | Nice | 636 | NS |
| 1387988 | 2026-05-10T19:00:00+00:00 | Regular Season - 33 | 111 | Le Havre | 81 | Marseille | 652 | NS |
| 1387990 | 2026-05-10T19:00:00+00:00 | Regular Season - 33 | 112 | Metz | 97 | Lorient | 658 | NS |
| 1387951 | 2026-05-13T17:00:00+00:00 | Regular Season - 29 | 106 | Stade Brestois 29 | 95 | Strasbourg | 641 | NS |
| 1387952 | 2026-05-13T19:00:00+00:00 | Regular Season - 29 | 116 | Lens | 85 | Paris Saint Germain | 654 | NS |
| 1387996 | 2026-05-17T19:00:00+00:00 | Regular Season - 34 | 79 | Lille | 108 | Auxerre | 0 | NS |
| 1387998 | 2026-05-17T19:00:00+00:00 | Regular Season - 34 | 80 | Lyon | 116 | Lens | 666 | NS |
| 1387999 | 2026-05-17T19:00:00+00:00 | Regular Season - 34 | 81 | Marseille | 94 | Rennes | 667 | NS |
| 1388000 | 2026-05-17T19:00:00+00:00 | Regular Season - 34 | 83 | Nantes | 96 | Toulouse | 662 | NS |
| 1388001 | 2026-05-17T19:00:00+00:00 | Regular Season - 34 | 84 | Nice | 112 | Metz | 663 | NS |
| 1388003 | 2026-05-17T19:00:00+00:00 | Regular Season - 34 | 95 | Strasbourg | 91 | Monaco | 681 | NS |
| 1387997 | 2026-05-17T19:00:00+00:00 | Regular Season - 34 | 97 | Lorient | 111 | Le Havre | 21430 | NS |
| 1387995 | 2026-05-17T19:00:00+00:00 | Regular Season - 34 | 106 | Stade Brestois 29 | 77 | Angers | 641 | NS |
| 1388002 | 2026-05-17T19:00:00+00:00 | Regular Season - 34 | 114 | Paris FC | 85 | Paris Saint Germain | 18861 | NS |


## Premier League

| Champ | Valeur |
| --- | --- |
| league_id | 39 |
| api_name | Premier League |
| country | England |
| type | League |
| season | 2025 |
| season_start | 2025-08-15 |
| season_end | 2026-05-24 |


### Coverage

```json
{
  "fixtures": {
    "events": true,
    "lineups": true,
    "statistics_fixtures": true,
    "statistics_players": true
  },
  "standings": true,
  "players": true,
  "top_scorers": true,
  "top_assists": true,
  "top_cards": true,
  "injuries": true,
  "predictions": true,
  "odds": true
}
```

### Teams et stades

| team_id | name | code | country | national | venue_id | venue | city | capacity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | Arsenal | ARS | England | False | 494 | Emirates Stadium | London | 60383 |
| 66 | Aston Villa | AST | England | False | 495 | Villa Park | Birmingham | 42824 |
| 35 | Bournemouth | BOU | England | False | 504 | Vitality Stadium | Bournemouth, Dorset | 12000 |
| 55 | Brentford | BRE | England | False | 10503 | Gtech Community Stadium | Brentford, Middlesex | 17250 |
| 51 | Brighton | BRI | England | False | 508 | American Express Stadium | Falmer, East Sussex | 31872 |
| 44 | Burnley | BUR | England | False | 512 | Turf Moor | Burnley | 22546 |
| 49 | Chelsea | CHE | England | False | 519 | Stamford Bridge | London | 41841 |
| 52 | Crystal Palace | CRY | England | False | 525 | Selhurst Park | London | 26309 |
| 45 | Everton | EVE | England | False | 22033 | Hill Dickinson Stadium | Liverpool, Merseyside | 52888 |
| 36 | Fulham | FUL | England | False | 535 | Craven Cottage | London | 29589 |
| 63 | Leeds | LEE | England | False | 546 | Elland Road | Leeds, West Yorkshire | 40204 |
| 40 | Liverpool | LIV | England | False | 550 | Anfield | Liverpool | 61276 |
| 50 | Manchester City | MCI | England | False | 555 | Etihad Stadium | Manchester | 55097 |
| 33 | Manchester United | MUN | England | False | 556 | Old Trafford | Manchester | 76212 |
| 34 | Newcastle | NEW | England | False | 562 | St. James' Park | Newcastle upon Tyne | 52758 |
| 65 | Nottingham Forest | NOT | England | False | 566 | The City Ground | Nottingham, Nottinghamshire | 30576 |
| 746 | Sunderland | SUN | England | False | 589 | Stadium of Light | Sunderland | 49000 |
| 47 | Tottenham | TOT | England | False | 593 | Tottenham Hotspur Stadium | London | 62850 |
| 48 | West Ham | WES | England | False | 598 | London Stadium | London | 64472 |
| 39 | Wolves | WOL | England | False | 600 | Molineux Stadium | Wolverhampton, West Midlands | 34624 |


### Rounds

- `Regular Season - 1`
- `Regular Season - 2`
- `Regular Season - 3`
- `Regular Season - 4`
- `Regular Season - 5`
- `Regular Season - 6`
- `Regular Season - 7`
- `Regular Season - 8`
- `Regular Season - 9`
- `Regular Season - 10`
- `Regular Season - 11`
- `Regular Season - 12`
- `Regular Season - 13`
- `Regular Season - 14`
- `Regular Season - 15`
- `Regular Season - 16`
- `Regular Season - 17`
- `Regular Season - 18`
- `Regular Season - 19`
- `Regular Season - 20`
- `Regular Season - 21`
- `Regular Season - 22`
- `Regular Season - 23`
- `Regular Season - 24`
- `Regular Season - 25`
- `Regular Season - 26`
- `Regular Season - 31`
- `Regular Season - 27`
- `Regular Season - 28`
- `Regular Season - 29`
- `Regular Season - 30`
- `Regular Season - 32`
- `Regular Season - 33`
- `Regular Season - 34`
- `Regular Season - 35`
- `Regular Season - 36`
- `Regular Season - 37`
- `Regular Season - 38`

### Standings

| rank | team_id | team | group | pts | played | W | D | L | GD | form |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 42 | Arsenal | Premier League | 73 | 34 | 22 | 7 | 5 | 38 | WLLWW |
| 2 | 50 | Manchester City | Premier League | 70 | 33 | 21 | 7 | 5 | 37 | WWWDD |
| 3 | 33 | Manchester United | Premier League | 61 | 34 | 17 | 10 | 7 | 14 | WWLDW |
| 4 | 40 | Liverpool | Premier League | 58 | 34 | 17 | 7 | 10 | 13 | WWWLD |
| 5 | 66 | Aston Villa | Premier League | 58 | 34 | 17 | 7 | 10 | 5 | LWDWL |
| 6 | 51 | Brighton | Premier League | 50 | 34 | 13 | 11 | 10 | 9 | WDWWW |
| 7 | 35 | Bournemouth | Premier League | 49 | 34 | 11 | 16 | 7 | 0 | DWWDD |
| 8 | 49 | Chelsea | Premier League | 48 | 34 | 13 | 9 | 12 | 8 | LLLLL |
| 9 | 55 | Brentford | Premier League | 48 | 34 | 13 | 9 | 12 | 3 | LDDDD |
| 10 | 36 | Fulham | Premier League | 48 | 34 | 14 | 6 | 14 | -2 | WDLWD |
| 11 | 45 | Everton | Premier League | 47 | 34 | 13 | 8 | 13 | 0 | LLDWL |
| 12 | 746 | Sunderland | Premier League | 46 | 34 | 12 | 10 | 12 | -9 | LLWWL |
| 13 | 52 | Crystal Palace | Premier League | 43 | 33 | 11 | 10 | 12 | -3 | LDWDW |
| 14 | 63 | Leeds | Premier League | 43 | 35 | 10 | 13 | 12 | -5 | WDWWD |
| 15 | 34 | Newcastle | Premier League | 42 | 34 | 12 | 6 | 16 | -4 | LLLLW |
| 16 | 65 | Nottingham Forest | Premier League | 39 | 34 | 10 | 9 | 15 | -4 | WWDWD |
| 17 | 48 | West Ham | Premier League | 36 | 34 | 9 | 9 | 16 | -16 | WDWLD |
| 18 | 47 | Tottenham | Premier League | 34 | 34 | 8 | 10 | 16 | -10 | WDLLD |
| 19 | 44 | Burnley | Premier League | 20 | 35 | 4 | 8 | 23 | -36 | LLLLL |
| 20 | 39 | Wolves | Premier League | 17 | 34 | 3 | 8 | 23 | -38 | LLLDW |


### Fixtures

| fixture_id | date | round | home_id | home | away_id | away | venue_id | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1378969 | 2025-08-15T19:00:00+00:00 | Regular Season - 1 | 40 | Liverpool | 35 | Bournemouth | 550 | FT |
| 1378970 | 2025-08-16T11:30:00+00:00 | Regular Season - 1 | 66 | Aston Villa | 34 | Newcastle | 495 | FT |
| 1378974 | 2025-08-16T14:00:00+00:00 | Regular Season - 1 | 47 | Tottenham | 44 | Burnley | 593 | FT |
| 1378971 | 2025-08-16T14:00:00+00:00 | Regular Season - 1 | 51 | Brighton | 36 | Fulham | 508 | FT |
| 1378973 | 2025-08-16T14:00:00+00:00 | Regular Season - 1 | 746 | Sunderland | 48 | West Ham | 589 | FT |
| 1378975 | 2025-08-16T16:30:00+00:00 | Regular Season - 1 | 39 | Wolves | 50 | Manchester City | 600 | FT |
| 1378976 | 2025-08-17T13:00:00+00:00 | Regular Season - 1 | 49 | Chelsea | 52 | Crystal Palace | 519 | FT |
| 1378972 | 2025-08-17T13:00:00+00:00 | Regular Season - 1 | 65 | Nottingham Forest | 55 | Brentford | 566 | FT |
| 1378977 | 2025-08-17T15:30:00+00:00 | Regular Season - 1 | 33 | Manchester United | 42 | Arsenal | 556 | FT |
| 1378978 | 2025-08-18T19:00:00+00:00 | Regular Season - 1 | 63 | Leeds | 45 | Everton | 546 | FT |
| 1378988 | 2025-08-22T19:00:00+00:00 | Regular Season - 2 | 48 | West Ham | 49 | Chelsea | 598 | FT |
| 1378986 | 2025-08-23T11:30:00+00:00 | Regular Season - 2 | 50 | Manchester City | 47 | Tottenham | 555 | FT |
| 1378980 | 2025-08-23T14:00:00+00:00 | Regular Season - 2 | 35 | Bournemouth | 39 | Wolves | 504 | FT |
| 1378982 | 2025-08-23T14:00:00+00:00 | Regular Season - 2 | 44 | Burnley | 746 | Sunderland | 512 | FT |
| 1378981 | 2025-08-23T14:00:00+00:00 | Regular Season - 2 | 55 | Brentford | 66 | Aston Villa | 10503 | FT |
| 1378979 | 2025-08-23T16:30:00+00:00 | Regular Season - 2 | 42 | Arsenal | 63 | Leeds | 494 | FT |
| 1378984 | 2025-08-24T13:00:00+00:00 | Regular Season - 2 | 45 | Everton | 51 | Brighton | 22033 | FT |
| 1378983 | 2025-08-24T13:00:00+00:00 | Regular Season - 2 | 52 | Crystal Palace | 65 | Nottingham Forest | 525 | FT |
| 1378985 | 2025-08-24T15:30:00+00:00 | Regular Season - 2 | 36 | Fulham | 33 | Manchester United | 535 | FT |
| 1378987 | 2025-08-25T19:00:00+00:00 | Regular Season - 2 | 34 | Newcastle | 40 | Liverpool | 562 | FT |
| 1378991 | 2025-08-30T11:30:00+00:00 | Regular Season - 3 | 49 | Chelsea | 36 | Fulham | 519 | FT |
| 1378994 | 2025-08-30T14:00:00+00:00 | Regular Season - 3 | 33 | Manchester United | 44 | Burnley | 556 | FT |
| 1378998 | 2025-08-30T14:00:00+00:00 | Regular Season - 3 | 39 | Wolves | 45 | Everton | 600 | FT |
| 1378997 | 2025-08-30T14:00:00+00:00 | Regular Season - 3 | 47 | Tottenham | 35 | Bournemouth | 593 | FT |
| 1378996 | 2025-08-30T14:00:00+00:00 | Regular Season - 3 | 746 | Sunderland | 55 | Brentford | 589 | FT |
| 1378992 | 2025-08-30T16:30:00+00:00 | Regular Season - 3 | 63 | Leeds | 34 | Newcastle | 546 | FT |
| 1378990 | 2025-08-31T13:00:00+00:00 | Regular Season - 3 | 51 | Brighton | 50 | Manchester City | 508 | FT |
| 1378995 | 2025-08-31T13:00:00+00:00 | Regular Season - 3 | 65 | Nottingham Forest | 48 | West Ham | 566 | FT |
| 1378993 | 2025-08-31T15:30:00+00:00 | Regular Season - 3 | 40 | Liverpool | 42 | Arsenal | 550 | FT |
| 1378989 | 2025-08-31T18:00:00+00:00 | Regular Season - 3 | 66 | Aston Villa | 52 | Crystal Palace | 495 | FT |
| 1378999 | 2025-09-13T11:30:00+00:00 | Regular Season - 4 | 42 | Arsenal | 65 | Nottingham Forest | 494 | FT |
| 1379007 | 2025-09-13T14:00:00+00:00 | Regular Season - 4 | 34 | Newcastle | 39 | Wolves | 562 | FT |
| 1379000 | 2025-09-13T14:00:00+00:00 | Regular Season - 4 | 35 | Bournemouth | 51 | Brighton | 504 | FT |
| 1379005 | 2025-09-13T14:00:00+00:00 | Regular Season - 4 | 36 | Fulham | 63 | Leeds | 535 | FT |
| 1379004 | 2025-09-13T14:00:00+00:00 | Regular Season - 4 | 45 | Everton | 66 | Aston Villa | 22033 | FT |
| 1379003 | 2025-09-13T14:00:00+00:00 | Regular Season - 4 | 52 | Crystal Palace | 746 | Sunderland | 525 | FT |
| 1379008 | 2025-09-13T16:30:00+00:00 | Regular Season - 4 | 48 | West Ham | 47 | Tottenham | 598 | FT |
| 1379001 | 2025-09-13T19:00:00+00:00 | Regular Season - 4 | 55 | Brentford | 49 | Chelsea | 10503 | FT |
| 1379002 | 2025-09-14T13:00:00+00:00 | Regular Season - 4 | 44 | Burnley | 40 | Liverpool | 512 | FT |
| 1379006 | 2025-09-14T15:30:00+00:00 | Regular Season - 4 | 50 | Manchester City | 33 | Manchester United | 555 | FT |
| 1379014 | 2025-09-20T11:30:00+00:00 | Regular Season - 5 | 40 | Liverpool | 45 | Everton | 550 | FT |
| 1379018 | 2025-09-20T14:00:00+00:00 | Regular Season - 5 | 39 | Wolves | 63 | Leeds | 600 | FT |
| 1379012 | 2025-09-20T14:00:00+00:00 | Regular Season - 5 | 44 | Burnley | 65 | Nottingham Forest | 512 | FT |
| 1379017 | 2025-09-20T14:00:00+00:00 | Regular Season - 5 | 48 | West Ham | 52 | Crystal Palace | 598 | FT |
| 1379011 | 2025-09-20T14:00:00+00:00 | Regular Season - 5 | 51 | Brighton | 47 | Tottenham | 508 | FT |
| 1379015 | 2025-09-20T16:30:00+00:00 | Regular Season - 5 | 33 | Manchester United | 49 | Chelsea | 556 | FT |
| 1379013 | 2025-09-20T19:00:00+00:00 | Regular Season - 5 | 36 | Fulham | 55 | Brentford | 535 | FT |
| 1379010 | 2025-09-21T13:00:00+00:00 | Regular Season - 5 | 35 | Bournemouth | 34 | Newcastle | 504 | FT |
| 1379016 | 2025-09-21T13:00:00+00:00 | Regular Season - 5 | 746 | Sunderland | 66 | Aston Villa | 589 | FT |
| 1379009 | 2025-09-21T15:30:00+00:00 | Regular Season - 5 | 42 | Arsenal | 50 | Manchester City | 494 | FT |
| 1379020 | 2025-09-27T11:30:00+00:00 | Regular Season - 6 | 55 | Brentford | 33 | Manchester United | 10503 | FT |
| 1379021 | 2025-09-27T14:00:00+00:00 | Regular Season - 6 | 49 | Chelsea | 51 | Brighton | 519 | FT |
| 1379025 | 2025-09-27T14:00:00+00:00 | Regular Season - 6 | 50 | Manchester City | 44 | Burnley | 555 | FT |
| 1379022 | 2025-09-27T14:00:00+00:00 | Regular Season - 6 | 52 | Crystal Palace | 40 | Liverpool | 525 | FT |
| 1379024 | 2025-09-27T14:00:00+00:00 | Regular Season - 6 | 63 | Leeds | 35 | Bournemouth | 546 | FT |
| 1379027 | 2025-09-27T16:30:00+00:00 | Regular Season - 6 | 65 | Nottingham Forest | 746 | Sunderland | 566 | FT |
| 1379028 | 2025-09-27T19:00:00+00:00 | Regular Season - 6 | 47 | Tottenham | 39 | Wolves | 593 | FT |
| 1379019 | 2025-09-28T13:00:00+00:00 | Regular Season - 6 | 66 | Aston Villa | 36 | Fulham | 495 | FT |
| 1379026 | 2025-09-28T15:30:00+00:00 | Regular Season - 6 | 34 | Newcastle | 42 | Arsenal | 562 | FT |
| 1379023 | 2025-09-29T19:00:00+00:00 | Regular Season - 6 | 45 | Everton | 48 | West Ham | 22033 | FT |
| 1379031 | 2025-10-03T19:00:00+00:00 | Regular Season - 7 | 35 | Bournemouth | 36 | Fulham | 504 | FT |
| 1379035 | 2025-10-04T11:30:00+00:00 | Regular Season - 7 | 63 | Leeds | 47 | Tottenham | 546 | FT |
| 1379036 | 2025-10-04T14:00:00+00:00 | Regular Season - 7 | 33 | Manchester United | 746 | Sunderland | 556 | FT |
| 1379029 | 2025-10-04T14:00:00+00:00 | Regular Season - 7 | 42 | Arsenal | 48 | West Ham | 494 | FT |
| 1379033 | 2025-10-04T16:30:00+00:00 | Regular Season - 7 | 49 | Chelsea | 40 | Liverpool | 519 | FT |
| 1379037 | 2025-10-05T13:00:00+00:00 | Regular Season - 7 | 34 | Newcastle | 65 | Nottingham Forest | 562 | FT |
| 1379038 | 2025-10-05T13:00:00+00:00 | Regular Season - 7 | 39 | Wolves | 51 | Brighton | 600 | FT |
| 1379034 | 2025-10-05T13:00:00+00:00 | Regular Season - 7 | 45 | Everton | 52 | Crystal Palace | 22033 | FT |
| 1379030 | 2025-10-05T13:00:00+00:00 | Regular Season - 7 | 66 | Aston Villa | 44 | Burnley | 495 | FT |
| 1379032 | 2025-10-05T15:30:00+00:00 | Regular Season - 7 | 55 | Brentford | 50 | Manchester City | 10503 | FT |
| 1379045 | 2025-10-18T11:30:00+00:00 | Regular Season - 8 | 65 | Nottingham Forest | 49 | Chelsea | 566 | FT |
| 1379040 | 2025-10-18T14:00:00+00:00 | Regular Season - 8 | 44 | Burnley | 63 | Leeds | 512 | FT |
| 1379044 | 2025-10-18T14:00:00+00:00 | Regular Season - 8 | 50 | Manchester City | 45 | Everton | 555 | FT |
| 1379039 | 2025-10-18T14:00:00+00:00 | Regular Season - 8 | 51 | Brighton | 34 | Newcastle | 508 | FT |
| 1379041 | 2025-10-18T14:00:00+00:00 | Regular Season - 8 | 52 | Crystal Palace | 35 | Bournemouth | 525 | FT |
| 1379046 | 2025-10-18T14:00:00+00:00 | Regular Season - 8 | 746 | Sunderland | 39 | Wolves | 589 | FT |
| 1379042 | 2025-10-18T16:30:00+00:00 | Regular Season - 8 | 36 | Fulham | 42 | Arsenal | 535 | FT |
| 1379047 | 2025-10-19T13:00:00+00:00 | Regular Season - 8 | 47 | Tottenham | 66 | Aston Villa | 593 | FT |
| 1379043 | 2025-10-19T15:30:00+00:00 | Regular Season - 8 | 40 | Liverpool | 33 | Manchester United | 550 | FT |
| 1379048 | 2025-10-20T19:00:00+00:00 | Regular Season - 8 | 48 | West Ham | 55 | Brentford | 598 | FT |
| 1379055 | 2025-10-24T19:00:00+00:00 | Regular Season - 9 | 63 | Leeds | 48 | West Ham | 546 | FT |
| 1379057 | 2025-10-25T14:00:00+00:00 | Regular Season - 9 | 34 | Newcastle | 36 | Fulham | 562 | FT |
| 1379053 | 2025-10-25T14:00:00+00:00 | Regular Season - 9 | 49 | Chelsea | 746 | Sunderland | 519 | FT |
| 1379056 | 2025-10-25T16:30:00+00:00 | Regular Season - 9 | 33 | Manchester United | 51 | Brighton | 556 | FT |
| 1379052 | 2025-10-25T19:00:00+00:00 | Regular Season - 9 | 55 | Brentford | 40 | Liverpool | 10503 | FT |
| 1379051 | 2025-10-26T14:00:00+00:00 | Regular Season - 9 | 35 | Bournemouth | 65 | Nottingham Forest | 504 | FT |
| 1379058 | 2025-10-26T14:00:00+00:00 | Regular Season - 9 | 39 | Wolves | 44 | Burnley | 600 | FT |
| 1379049 | 2025-10-26T14:00:00+00:00 | Regular Season - 9 | 42 | Arsenal | 52 | Crystal Palace | 494 | FT |
| 1379050 | 2025-10-26T14:00:00+00:00 | Regular Season - 9 | 66 | Aston Villa | 50 | Manchester City | 495 | FT |
| 1379054 | 2025-10-26T16:30:00+00:00 | Regular Season - 9 | 45 | Everton | 47 | Tottenham | 22033 | FT |
| 1379062 | 2025-11-01T15:00:00+00:00 | Regular Season - 10 | 36 | Fulham | 39 | Wolves | 535 | FT |
| 1379060 | 2025-11-01T15:00:00+00:00 | Regular Season - 10 | 44 | Burnley | 42 | Arsenal | 512 | FT |
| 1379059 | 2025-11-01T15:00:00+00:00 | Regular Season - 10 | 51 | Brighton | 63 | Leeds | 508 | FT |
| 1379061 | 2025-11-01T15:00:00+00:00 | Regular Season - 10 | 52 | Crystal Palace | 55 | Brentford | 525 | FT |
| 1379065 | 2025-11-01T15:00:00+00:00 | Regular Season - 10 | 65 | Nottingham Forest | 33 | Manchester United | 566 | FT |
| 1379067 | 2025-11-01T17:30:00+00:00 | Regular Season - 10 | 47 | Tottenham | 49 | Chelsea | 593 | FT |
| 1379063 | 2025-11-01T20:00:00+00:00 | Regular Season - 10 | 40 | Liverpool | 66 | Aston Villa | 550 | FT |
| 1379068 | 2025-11-02T14:00:00+00:00 | Regular Season - 10 | 48 | West Ham | 34 | Newcastle | 598 | FT |
| 1379064 | 2025-11-02T16:30:00+00:00 | Regular Season - 10 | 50 | Manchester City | 35 | Bournemouth | 555 | FT |
| 1379066 | 2025-11-03T20:00:00+00:00 | Regular Season - 10 | 746 | Sunderland | 45 | Everton | 589 | FT |
| 1379077 | 2025-11-08T12:30:00+00:00 | Regular Season - 11 | 47 | Tottenham | 33 | Manchester United | 593 | FT |
| 1379073 | 2025-11-08T15:00:00+00:00 | Regular Season - 11 | 45 | Everton | 36 | Fulham | 22033 | FT |
| 1379078 | 2025-11-08T15:00:00+00:00 | Regular Season - 11 | 48 | West Ham | 44 | Burnley | 598 | FT |
| 1379076 | 2025-11-08T17:30:00+00:00 | Regular Season - 11 | 746 | Sunderland | 42 | Arsenal | 589 | FT |
| 1379071 | 2025-11-08T20:00:00+00:00 | Regular Season - 11 | 49 | Chelsea | 39 | Wolves | 519 | FT |
| 1379072 | 2025-11-09T14:00:00+00:00 | Regular Season - 11 | 52 | Crystal Palace | 51 | Brighton | 525 | FT |
| 1379070 | 2025-11-09T14:00:00+00:00 | Regular Season - 11 | 55 | Brentford | 34 | Newcastle | 10503 | FT |
| 1379075 | 2025-11-09T14:00:00+00:00 | Regular Season - 11 | 65 | Nottingham Forest | 63 | Leeds | 566 | FT |
| 1379069 | 2025-11-09T14:00:00+00:00 | Regular Season - 11 | 66 | Aston Villa | 35 | Bournemouth | 495 | FT |
| 1379074 | 2025-11-09T16:30:00+00:00 | Regular Season - 11 | 50 | Manchester City | 40 | Liverpool | 555 | FT |
| 1379082 | 2025-11-22T12:30:00+00:00 | Regular Season - 12 | 44 | Burnley | 49 | Chelsea | 512 | FT |
| 1379080 | 2025-11-22T15:00:00+00:00 | Regular Season - 12 | 35 | Bournemouth | 48 | West Ham | 504 | FT |
| 1379083 | 2025-11-22T15:00:00+00:00 | Regular Season - 12 | 36 | Fulham | 746 | Sunderland | 535 | FT |
| 1379088 | 2025-11-22T15:00:00+00:00 | Regular Season - 12 | 39 | Wolves | 52 | Crystal Palace | 600 | FT |
| 1379085 | 2025-11-22T15:00:00+00:00 | Regular Season - 12 | 40 | Liverpool | 65 | Nottingham Forest | 550 | FT |
| 1379081 | 2025-11-22T15:00:00+00:00 | Regular Season - 12 | 51 | Brighton | 55 | Brentford | 508 | FT |
| 1379087 | 2025-11-22T17:30:00+00:00 | Regular Season - 12 | 34 | Newcastle | 50 | Manchester City | 562 | FT |
| 1379084 | 2025-11-23T14:00:00+00:00 | Regular Season - 12 | 63 | Leeds | 66 | Aston Villa | 546 | FT |
| 1379079 | 2025-11-23T16:30:00+00:00 | Regular Season - 12 | 42 | Arsenal | 47 | Tottenham | 494 | FT |
| 1379086 | 2025-11-24T20:00:00+00:00 | Regular Season - 12 | 33 | Manchester United | 45 | Everton | 556 | FT |
| 1379094 | 2025-11-29T15:00:00+00:00 | Regular Season - 13 | 50 | Manchester City | 63 | Leeds | 555 | FT |
| 1379090 | 2025-11-29T15:00:00+00:00 | Regular Season - 13 | 55 | Brentford | 44 | Burnley | 10503 | FT |
| 1379096 | 2025-11-29T15:00:00+00:00 | Regular Season - 13 | 746 | Sunderland | 35 | Bournemouth | 589 | FT |
| 1379093 | 2025-11-29T17:30:00+00:00 | Regular Season - 13 | 45 | Everton | 34 | Newcastle | 22033 | FT |
| 1379097 | 2025-11-29T20:00:00+00:00 | Regular Season - 13 | 47 | Tottenham | 36 | Fulham | 593 | FT |
| 1379092 | 2025-11-30T12:00:00+00:00 | Regular Season - 13 | 52 | Crystal Palace | 33 | Manchester United | 525 | FT |
| 1379098 | 2025-11-30T14:05:00+00:00 | Regular Season - 13 | 48 | West Ham | 40 | Liverpool | 598 | FT |
| 1379095 | 2025-11-30T14:05:00+00:00 | Regular Season - 13 | 65 | Nottingham Forest | 51 | Brighton | 566 | FT |
| 1379089 | 2025-11-30T14:05:00+00:00 | Regular Season - 13 | 66 | Aston Villa | 39 | Wolves | 495 | FT |
| 1379091 | 2025-11-30T16:30:00+00:00 | Regular Season - 13 | 49 | Chelsea | 42 | Arsenal | 519 | FT |
| 1379100 | 2025-12-02T19:30:00+00:00 | Regular Season - 14 | 35 | Bournemouth | 45 | Everton | 504 | FT |
| 1379103 | 2025-12-02T19:30:00+00:00 | Regular Season - 14 | 36 | Fulham | 50 | Manchester City | 535 | FT |
| 1379107 | 2025-12-02T20:15:00+00:00 | Regular Season - 14 | 34 | Newcastle | 47 | Tottenham | 562 | FT |
| 1379108 | 2025-12-03T19:30:00+00:00 | Regular Season - 14 | 39 | Wolves | 65 | Nottingham Forest | 600 | FT |
| 1379099 | 2025-12-03T19:30:00+00:00 | Regular Season - 14 | 42 | Arsenal | 55 | Brentford | 494 | FT |
| 1379102 | 2025-12-03T19:30:00+00:00 | Regular Season - 14 | 44 | Burnley | 52 | Crystal Palace | 512 | FT |
| 1379101 | 2025-12-03T19:30:00+00:00 | Regular Season - 14 | 51 | Brighton | 66 | Aston Villa | 508 | FT |
| 1379105 | 2025-12-03T20:15:00+00:00 | Regular Season - 14 | 40 | Liverpool | 746 | Sunderland | 550 | FT |
| 1379104 | 2025-12-03T20:15:00+00:00 | Regular Season - 14 | 63 | Leeds | 49 | Chelsea | 546 | FT |
| 1379106 | 2025-12-04T20:00:00+00:00 | Regular Season - 14 | 33 | Manchester United | 48 | West Ham | 556 | FT |
| 1379109 | 2025-12-06T12:30:00+00:00 | Regular Season - 15 | 66 | Aston Villa | 42 | Arsenal | 495 | FT |
| 1379116 | 2025-12-06T15:00:00+00:00 | Regular Season - 15 | 34 | Newcastle | 44 | Burnley | 562 | FT |
| 1379110 | 2025-12-06T15:00:00+00:00 | Regular Season - 15 | 35 | Bournemouth | 49 | Chelsea | 504 | FT |
| 1379112 | 2025-12-06T15:00:00+00:00 | Regular Season - 15 | 45 | Everton | 65 | Nottingham Forest | 22033 | FT |
| 1379117 | 2025-12-06T15:00:00+00:00 | Regular Season - 15 | 47 | Tottenham | 55 | Brentford | 593 | FT |
| 1379115 | 2025-12-06T15:00:00+00:00 | Regular Season - 15 | 50 | Manchester City | 746 | Sunderland | 555 | FT |
| 1379114 | 2025-12-06T17:30:00+00:00 | Regular Season - 15 | 63 | Leeds | 40 | Liverpool | 546 | FT |
| 1379111 | 2025-12-07T14:00:00+00:00 | Regular Season - 15 | 51 | Brighton | 48 | West Ham | 508 | FT |
| 1379113 | 2025-12-07T16:30:00+00:00 | Regular Season - 15 | 36 | Fulham | 52 | Crystal Palace | 535 | FT |
| 1379118 | 2025-12-08T20:00:00+00:00 | Regular Season - 15 | 39 | Wolves | 33 | Manchester United | 600 | FT |
| 1379124 | 2025-12-13T15:00:00+00:00 | Regular Season - 16 | 40 | Liverpool | 51 | Brighton | 550 | FT |
| 1379122 | 2025-12-13T15:00:00+00:00 | Regular Season - 16 | 49 | Chelsea | 45 | Everton | 519 | FT |
| 1379121 | 2025-12-13T17:30:00+00:00 | Regular Season - 16 | 44 | Burnley | 36 | Fulham | 512 | FT |
| 1379119 | 2025-12-13T20:00:00+00:00 | Regular Season - 16 | 42 | Arsenal | 39 | Wolves | 494 | FT |
| 1379128 | 2025-12-14T14:00:00+00:00 | Regular Season - 16 | 48 | West Ham | 66 | Aston Villa | 598 | FT |
| 1379123 | 2025-12-14T14:00:00+00:00 | Regular Season - 16 | 52 | Crystal Palace | 50 | Manchester City | 525 | FT |
| 1379126 | 2025-12-14T14:00:00+00:00 | Regular Season - 16 | 65 | Nottingham Forest | 47 | Tottenham | 566 | FT |
| 1379127 | 2025-12-14T14:00:00+00:00 | Regular Season - 16 | 746 | Sunderland | 34 | Newcastle | 589 | FT |
| 1379120 | 2025-12-14T16:30:00+00:00 | Regular Season - 16 | 55 | Brentford | 63 | Leeds | 10503 | FT |
| 1379125 | 2025-12-15T20:00:00+00:00 | Regular Season - 16 | 33 | Manchester United | 35 | Bournemouth | 556 | FT |
| 1379136 | 2025-12-20T12:30:00+00:00 | Regular Season - 17 | 34 | Newcastle | 49 | Chelsea | 562 | FT |
| 1379130 | 2025-12-20T15:00:00+00:00 | Regular Season - 17 | 35 | Bournemouth | 44 | Burnley | 504 | FT |
| 1379138 | 2025-12-20T15:00:00+00:00 | Regular Season - 17 | 39 | Wolves | 55 | Brentford | 600 | FT |
| 1379135 | 2025-12-20T15:00:00+00:00 | Regular Season - 17 | 50 | Manchester City | 48 | West Ham | 555 | FT |
| 1379131 | 2025-12-20T15:00:00+00:00 | Regular Season - 17 | 51 | Brighton | 746 | Sunderland | 508 | FT |
| 1379137 | 2025-12-20T17:30:00+00:00 | Regular Season - 17 | 47 | Tottenham | 40 | Liverpool | 593 | FT |
| 1379132 | 2025-12-20T20:00:00+00:00 | Regular Season - 17 | 45 | Everton | 42 | Arsenal | 22033 | FT |
| 1379134 | 2025-12-20T20:00:00+00:00 | Regular Season - 17 | 63 | Leeds | 52 | Crystal Palace | 546 | FT |
| 1379129 | 2025-12-21T16:30:00+00:00 | Regular Season - 17 | 66 | Aston Villa | 33 | Manchester United | 495 | FT |
| 1379133 | 2025-12-22T20:00:00+00:00 | Regular Season - 17 | 36 | Fulham | 65 | Nottingham Forest | 535 | FT |
| 1379145 | 2025-12-26T20:00:00+00:00 | Regular Season - 18 | 33 | Manchester United | 34 | Newcastle | 556 | FT |
| 1379146 | 2025-12-27T12:30:00+00:00 | Regular Season - 18 | 65 | Nottingham Forest | 50 | Manchester City | 566 | FT |
| 1379144 | 2025-12-27T15:00:00+00:00 | Regular Season - 18 | 40 | Liverpool | 39 | Wolves | 550 | FT |
| 1379139 | 2025-12-27T15:00:00+00:00 | Regular Season - 18 | 42 | Arsenal | 51 | Brighton | 494 | FT |
| 1379141 | 2025-12-27T15:00:00+00:00 | Regular Season - 18 | 44 | Burnley | 45 | Everton | 512 | FT |
| 1379148 | 2025-12-27T15:00:00+00:00 | Regular Season - 18 | 48 | West Ham | 36 | Fulham | 598 | FT |
| 1379140 | 2025-12-27T15:00:00+00:00 | Regular Season - 18 | 55 | Brentford | 35 | Bournemouth | 10503 | FT |
| 1379142 | 2025-12-27T17:30:00+00:00 | Regular Season - 18 | 49 | Chelsea | 66 | Aston Villa | 519 | FT |
| 1379147 | 2025-12-28T14:00:00+00:00 | Regular Season - 18 | 746 | Sunderland | 63 | Leeds | 589 | FT |
| 1379143 | 2025-12-28T16:30:00+00:00 | Regular Season - 18 | 52 | Crystal Palace | 47 | Tottenham | 525 | FT |
| 1379151 | 2025-12-30T19:30:00+00:00 | Regular Season - 19 | 44 | Burnley | 34 | Newcastle | 512 | FT |
| 1379158 | 2025-12-30T19:30:00+00:00 | Regular Season - 19 | 48 | West Ham | 51 | Brighton | 598 | FT |
| 1379152 | 2025-12-30T19:30:00+00:00 | Regular Season - 19 | 49 | Chelsea | 35 | Bournemouth | 519 | FT |
| 1379156 | 2025-12-30T19:30:00+00:00 | Regular Season - 19 | 65 | Nottingham Forest | 45 | Everton | 566 | FT |
| 1379155 | 2025-12-30T20:15:00+00:00 | Regular Season - 19 | 33 | Manchester United | 39 | Wolves | 556 | FT |
| 1379149 | 2025-12-30T20:15:00+00:00 | Regular Season - 19 | 42 | Arsenal | 66 | Aston Villa | 494 | FT |
| 1379154 | 2026-01-01T17:30:00+00:00 | Regular Season - 19 | 40 | Liverpool | 63 | Leeds | 550 | FT |
| 1379153 | 2026-01-01T17:30:00+00:00 | Regular Season - 19 | 52 | Crystal Palace | 36 | Fulham | 525 | FT |
| 1379150 | 2026-01-01T20:00:00+00:00 | Regular Season - 19 | 55 | Brentford | 47 | Tottenham | 10503 | FT |
| 1379157 | 2026-01-01T20:00:00+00:00 | Regular Season - 19 | 746 | Sunderland | 50 | Manchester City | 589 | FT |
| 1379159 | 2026-01-03T12:30:00+00:00 | Regular Season - 20 | 66 | Aston Villa | 65 | Nottingham Forest | 495 | FT |
| 1379168 | 2026-01-03T15:00:00+00:00 | Regular Season - 20 | 39 | Wolves | 48 | West Ham | 600 | FT |
| 1379161 | 2026-01-03T15:00:00+00:00 | Regular Season - 20 | 51 | Brighton | 44 | Burnley | 508 | FT |
| 1379160 | 2026-01-03T17:30:00+00:00 | Regular Season - 20 | 35 | Bournemouth | 42 | Arsenal | 504 | FT |
| 1379164 | 2026-01-04T12:30:00+00:00 | Regular Season - 20 | 63 | Leeds | 33 | Manchester United | 546 | FT |
| 1379166 | 2026-01-04T15:00:00+00:00 | Regular Season - 20 | 34 | Newcastle | 52 | Crystal Palace | 562 | FT |
| 1379162 | 2026-01-04T15:00:00+00:00 | Regular Season - 20 | 45 | Everton | 55 | Brentford | 22033 | FT |
| 1379167 | 2026-01-04T15:00:00+00:00 | Regular Season - 20 | 47 | Tottenham | 746 | Sunderland | 593 | FT |
| 1379163 | 2026-01-04T15:15:00+00:00 | Regular Season - 20 | 36 | Fulham | 40 | Liverpool | 535 | FT |
| 1379165 | 2026-01-04T17:30:00+00:00 | Regular Season - 20 | 50 | Manchester City | 49 | Chelsea | 555 | FT |
| 1379178 | 2026-01-06T20:00:00+00:00 | Regular Season - 21 | 48 | West Ham | 65 | Nottingham Forest | 598 | FT |
| 1379170 | 2026-01-07T19:30:00+00:00 | Regular Season - 21 | 35 | Bournemouth | 47 | Tottenham | 504 | FT |
| 1379175 | 2026-01-07T19:30:00+00:00 | Regular Season - 21 | 36 | Fulham | 49 | Chelsea | 535 | FT |
| 1379174 | 2026-01-07T19:30:00+00:00 | Regular Season - 21 | 45 | Everton | 39 | Wolves | 22033 | FT |
| 1379176 | 2026-01-07T19:30:00+00:00 | Regular Season - 21 | 50 | Manchester City | 51 | Brighton | 555 | FT |
| 1379173 | 2026-01-07T19:30:00+00:00 | Regular Season - 21 | 52 | Crystal Palace | 66 | Aston Villa | 525 | FT |
| 1379171 | 2026-01-07T19:30:00+00:00 | Regular Season - 21 | 55 | Brentford | 746 | Sunderland | 10503 | FT |
| 1379177 | 2026-01-07T20:15:00+00:00 | Regular Season - 21 | 34 | Newcastle | 63 | Leeds | 562 | FT |
| 1379172 | 2026-01-07T20:15:00+00:00 | Regular Season - 21 | 44 | Burnley | 33 | Manchester United | 512 | FT |
| 1379169 | 2026-01-08T20:00:00+00:00 | Regular Season - 21 | 42 | Arsenal | 40 | Liverpool | 494 | FT |
| 1379184 | 2026-01-17T12:30:00+00:00 | Regular Season - 22 | 33 | Manchester United | 50 | Manchester City | 556 | FT |
| 1379183 | 2026-01-17T15:00:00+00:00 | Regular Season - 22 | 40 | Liverpool | 44 | Burnley | 550 | FT |
| 1379187 | 2026-01-17T15:00:00+00:00 | Regular Season - 22 | 47 | Tottenham | 48 | West Ham | 593 | FT |
| 1379181 | 2026-01-17T15:00:00+00:00 | Regular Season - 22 | 49 | Chelsea | 55 | Brentford | 519 | FT |
| 1379182 | 2026-01-17T15:00:00+00:00 | Regular Season - 22 | 63 | Leeds | 36 | Fulham | 546 | FT |
| 1379186 | 2026-01-17T15:00:00+00:00 | Regular Season - 22 | 746 | Sunderland | 52 | Crystal Palace | 589 | FT |
| 1379185 | 2026-01-17T17:30:00+00:00 | Regular Season - 22 | 65 | Nottingham Forest | 42 | Arsenal | 566 | FT |
| 1379188 | 2026-01-18T14:00:00+00:00 | Regular Season - 22 | 39 | Wolves | 34 | Newcastle | 600 | FT |
| 1379179 | 2026-01-18T16:30:00+00:00 | Regular Season - 22 | 66 | Aston Villa | 45 | Everton | 495 | FT |
| 1379180 | 2026-01-19T20:00:00+00:00 | Regular Season - 22 | 51 | Brighton | 35 | Bournemouth | 508 | FT |
| 1379198 | 2026-01-24T12:30:00+00:00 | Regular Season - 23 | 48 | West Ham | 746 | Sunderland | 598 | FT |
| 1379195 | 2026-01-24T15:00:00+00:00 | Regular Season - 23 | 36 | Fulham | 51 | Brighton | 535 | FT |
| 1379192 | 2026-01-24T15:00:00+00:00 | Regular Season - 23 | 44 | Burnley | 47 | Tottenham | 512 | FT |
| 1379196 | 2026-01-24T15:00:00+00:00 | Regular Season - 23 | 50 | Manchester City | 39 | Wolves | 555 | FT |
| 1379190 | 2026-01-24T17:30:00+00:00 | Regular Season - 23 | 35 | Bournemouth | 40 | Liverpool | 504 | FT |
| 1379197 | 2026-01-25T14:00:00+00:00 | Regular Season - 23 | 34 | Newcastle | 66 | Aston Villa | 562 | FT |
| 1379193 | 2026-01-25T14:00:00+00:00 | Regular Season - 23 | 52 | Crystal Palace | 49 | Chelsea | 525 | FT |
| 1379191 | 2026-01-25T14:00:00+00:00 | Regular Season - 23 | 55 | Brentford | 65 | Nottingham Forest | 10503 | FT |
| 1379189 | 2026-01-25T16:30:00+00:00 | Regular Season - 23 | 42 | Arsenal | 33 | Manchester United | 494 | FT |
| 1379194 | 2026-01-26T20:00:00+00:00 | Regular Season - 23 | 45 | Everton | 63 | Leeds | 22033 | FT |
| 1379208 | 2026-01-31T15:00:00+00:00 | Regular Season - 24 | 39 | Wolves | 35 | Bournemouth | 600 | FT |
| 1379200 | 2026-01-31T15:00:00+00:00 | Regular Season - 24 | 51 | Brighton | 45 | Everton | 508 | FT |
| 1379202 | 2026-01-31T15:00:00+00:00 | Regular Season - 24 | 63 | Leeds | 42 | Arsenal | 546 | FT |
| 1379201 | 2026-01-31T17:30:00+00:00 | Regular Season - 24 | 49 | Chelsea | 48 | West Ham | 519 | FT |
| 1379203 | 2026-01-31T20:00:00+00:00 | Regular Season - 24 | 40 | Liverpool | 34 | Newcastle | 550 | FT |
| 1379204 | 2026-02-01T14:00:00+00:00 | Regular Season - 24 | 33 | Manchester United | 36 | Fulham | 556 | FT |
| 1379205 | 2026-02-01T14:00:00+00:00 | Regular Season - 24 | 65 | Nottingham Forest | 52 | Crystal Palace | 566 | FT |
| 1379199 | 2026-02-01T14:00:00+00:00 | Regular Season - 24 | 66 | Aston Villa | 55 | Brentford | 495 | FT |
| 1379207 | 2026-02-01T16:30:00+00:00 | Regular Season - 24 | 47 | Tottenham | 50 | Manchester City | 593 | FT |
| 1379206 | 2026-02-02T20:00:00+00:00 | Regular Season - 24 | 746 | Sunderland | 44 | Burnley | 589 | FT |
| 1379214 | 2026-02-06T20:00:00+00:00 | Regular Season - 25 | 63 | Leeds | 65 | Nottingham Forest | 546 | FT |
| 1379216 | 2026-02-07T12:30:00+00:00 | Regular Season - 25 | 33 | Manchester United | 47 | Tottenham | 556 | FT |
| 1379210 | 2026-02-07T15:00:00+00:00 | Regular Season - 25 | 35 | Bournemouth | 66 | Aston Villa | 504 | FT |
| 1379213 | 2026-02-07T15:00:00+00:00 | Regular Season - 25 | 36 | Fulham | 45 | Everton | 535 | FT |
| 1379218 | 2026-02-07T15:00:00+00:00 | Regular Season - 25 | 39 | Wolves | 49 | Chelsea | 600 | FT |
| 1379209 | 2026-02-07T15:00:00+00:00 | Regular Season - 25 | 42 | Arsenal | 746 | Sunderland | 494 | FT |
| 1379212 | 2026-02-07T15:00:00+00:00 | Regular Season - 25 | 44 | Burnley | 48 | West Ham | 512 | FT |
| 1379217 | 2026-02-07T17:30:00+00:00 | Regular Season - 25 | 34 | Newcastle | 55 | Brentford | 562 | FT |
| 1379211 | 2026-02-08T14:00:00+00:00 | Regular Season - 25 | 51 | Brighton | 52 | Crystal Palace | 508 | FT |
| 1379215 | 2026-02-08T16:30:00+00:00 | Regular Season - 25 | 40 | Liverpool | 50 | Manchester City | 550 | FT |
| 1379223 | 2026-02-10T19:30:00+00:00 | Regular Season - 26 | 45 | Everton | 35 | Bournemouth | 22033 | FT |
| 1379227 | 2026-02-10T19:30:00+00:00 | Regular Season - 26 | 47 | Tottenham | 34 | Newcastle | 593 | FT |
| 1379221 | 2026-02-10T19:30:00+00:00 | Regular Season - 26 | 49 | Chelsea | 63 | Leeds | 519 | FT |
| 1379228 | 2026-02-10T20:15:00+00:00 | Regular Season - 26 | 48 | West Ham | 33 | Manchester United | 598 | FT |
| 1379224 | 2026-02-11T19:30:00+00:00 | Regular Season - 26 | 50 | Manchester City | 36 | Fulham | 555 | FT |
| 1379222 | 2026-02-11T19:30:00+00:00 | Regular Season - 26 | 52 | Crystal Palace | 44 | Burnley | 525 | FT |
| 1379225 | 2026-02-11T19:30:00+00:00 | Regular Season - 26 | 65 | Nottingham Forest | 39 | Wolves | 566 | FT |
| 1379219 | 2026-02-11T19:30:00+00:00 | Regular Season - 26 | 66 | Aston Villa | 51 | Brighton | 495 | FT |
| 1379226 | 2026-02-11T20:15:00+00:00 | Regular Season - 26 | 746 | Sunderland | 40 | Liverpool | 589 | FT |
| 1379220 | 2026-02-12T20:00:00+00:00 | Regular Season - 26 | 55 | Brentford | 42 | Arsenal | 10503 | FT |
| 1379278 | 2026-02-18T20:00:00+00:00 | Regular Season - 31 | 39 | Wolves | 42 | Arsenal | 600 | FT |
| 1379231 | 2026-02-21T15:00:00+00:00 | Regular Season - 27 | 49 | Chelsea | 44 | Burnley | 519 | FT |
| 1379230 | 2026-02-21T15:00:00+00:00 | Regular Season - 27 | 55 | Brentford | 51 | Brighton | 10503 | FT |
| 1379229 | 2026-02-21T15:00:00+00:00 | Regular Season - 27 | 66 | Aston Villa | 63 | Leeds | 495 | FT |
| 1379238 | 2026-02-21T17:30:00+00:00 | Regular Season - 27 | 48 | West Ham | 35 | Bournemouth | 598 | FT |
| 1379234 | 2026-02-21T20:00:00+00:00 | Regular Season - 27 | 50 | Manchester City | 34 | Newcastle | 555 | FT |
| 1379232 | 2026-02-22T14:00:00+00:00 | Regular Season - 27 | 52 | Crystal Palace | 39 | Wolves | 525 | FT |
| 1379235 | 2026-02-22T14:00:00+00:00 | Regular Season - 27 | 65 | Nottingham Forest | 40 | Liverpool | 566 | FT |
| 1379236 | 2026-02-22T14:00:00+00:00 | Regular Season - 27 | 746 | Sunderland | 36 | Fulham | 589 | FT |
| 1379237 | 2026-02-22T16:30:00+00:00 | Regular Season - 27 | 47 | Tottenham | 42 | Arsenal | 593 | FT |
| 1379233 | 2026-02-23T20:00:00+00:00 | Regular Season - 27 | 45 | Everton | 33 | Manchester United | 22033 | FT |
| 1379248 | 2026-02-27T20:00:00+00:00 | Regular Season - 28 | 39 | Wolves | 66 | Aston Villa | 600 | FT |
| 1379240 | 2026-02-28T12:30:00+00:00 | Regular Season - 28 | 35 | Bournemouth | 746 | Sunderland | 504 | FT |
| 1379247 | 2026-02-28T15:00:00+00:00 | Regular Season - 28 | 34 | Newcastle | 45 | Everton | 562 | FT |
| 1379245 | 2026-02-28T15:00:00+00:00 | Regular Season - 28 | 40 | Liverpool | 48 | West Ham | 550 | FT |
| 1379242 | 2026-02-28T15:00:00+00:00 | Regular Season - 28 | 44 | Burnley | 55 | Brentford | 512 | FT |
| 1379244 | 2026-02-28T17:30:00+00:00 | Regular Season - 28 | 63 | Leeds | 50 | Manchester City | 546 | FT |
| 1379246 | 2026-03-01T14:00:00+00:00 | Regular Season - 28 | 33 | Manchester United | 52 | Crystal Palace | 556 | FT |
| 1379243 | 2026-03-01T14:00:00+00:00 | Regular Season - 28 | 36 | Fulham | 47 | Tottenham | 535 | FT |
| 1379241 | 2026-03-01T14:00:00+00:00 | Regular Season - 28 | 51 | Brighton | 65 | Nottingham Forest | 508 | FT |
| 1379239 | 2026-03-01T16:30:00+00:00 | Regular Season - 28 | 42 | Arsenal | 49 | Chelsea | 494 | FT |
| 1379250 | 2026-03-03T19:30:00+00:00 | Regular Season - 29 | 35 | Bournemouth | 55 | Brentford | 504 | FT |
| 1379252 | 2026-03-03T19:30:00+00:00 | Regular Season - 29 | 45 | Everton | 44 | Burnley | 22033 | FT |
| 1379254 | 2026-03-03T19:30:00+00:00 | Regular Season - 29 | 63 | Leeds | 746 | Sunderland | 546 | FT |
| 1379258 | 2026-03-03T20:15:00+00:00 | Regular Season - 29 | 39 | Wolves | 40 | Liverpool | 600 | FT |
| 1379253 | 2026-03-04T19:30:00+00:00 | Regular Season - 29 | 36 | Fulham | 48 | West Ham | 535 | FT |
| 1379255 | 2026-03-04T19:30:00+00:00 | Regular Season - 29 | 50 | Manchester City | 65 | Nottingham Forest | 555 | FT |
| 1379251 | 2026-03-04T19:30:00+00:00 | Regular Season - 29 | 51 | Brighton | 42 | Arsenal | 508 | FT |
| 1379249 | 2026-03-04T19:30:00+00:00 | Regular Season - 29 | 66 | Aston Villa | 49 | Chelsea | 495 | FT |
| 1379256 | 2026-03-04T20:15:00+00:00 | Regular Season - 29 | 34 | Newcastle | 33 | Manchester United | 562 | FT |
| 1379257 | 2026-03-05T20:00:00+00:00 | Regular Season - 29 | 47 | Tottenham | 52 | Crystal Palace | 593 | FT |
| 1379261 | 2026-03-14T15:00:00+00:00 | Regular Season - 30 | 44 | Burnley | 35 | Bournemouth | 512 | FT |
| 1379267 | 2026-03-14T15:00:00+00:00 | Regular Season - 30 | 746 | Sunderland | 51 | Brighton | 589 | FT |
| 1379259 | 2026-03-14T17:30:00+00:00 | Regular Season - 30 | 42 | Arsenal | 45 | Everton | 494 | FT |
| 1379262 | 2026-03-14T17:30:00+00:00 | Regular Season - 30 | 49 | Chelsea | 34 | Newcastle | 519 | FT |
| 1379268 | 2026-03-14T20:00:00+00:00 | Regular Season - 30 | 48 | West Ham | 50 | Manchester City | 598 | FT |
| 1379265 | 2026-03-15T14:00:00+00:00 | Regular Season - 30 | 33 | Manchester United | 66 | Aston Villa | 556 | FT |
| 1379263 | 2026-03-15T14:00:00+00:00 | Regular Season - 30 | 52 | Crystal Palace | 63 | Leeds | 525 | FT |
| 1379266 | 2026-03-15T14:00:00+00:00 | Regular Season - 30 | 65 | Nottingham Forest | 36 | Fulham | 566 | FT |
| 1379264 | 2026-03-15T16:30:00+00:00 | Regular Season - 30 | 40 | Liverpool | 47 | Tottenham | 550 | FT |
| 1379260 | 2026-03-16T20:00:00+00:00 | Regular Season - 30 | 55 | Brentford | 39 | Wolves | 10503 | FT |
| 1379270 | 2026-03-20T20:00:00+00:00 | Regular Season - 31 | 35 | Bournemouth | 33 | Manchester United | 504 | FT |
| 1379271 | 2026-03-21T12:30:00+00:00 | Regular Season - 31 | 51 | Brighton | 40 | Liverpool | 508 | FT |
| 1379273 | 2026-03-21T15:00:00+00:00 | Regular Season - 31 | 36 | Fulham | 44 | Burnley | 535 | FT |
| 1379272 | 2026-03-21T17:30:00+00:00 | Regular Season - 31 | 45 | Everton | 49 | Chelsea | 22033 | FT |
| 1379274 | 2026-03-21T20:00:00+00:00 | Regular Season - 31 | 63 | Leeds | 55 | Brentford | 546 | FT |
| 1379276 | 2026-03-22T12:00:00+00:00 | Regular Season - 31 | 34 | Newcastle | 746 | Sunderland | 562 | FT |
| 1379277 | 2026-03-22T14:15:00+00:00 | Regular Season - 31 | 47 | Tottenham | 65 | Nottingham Forest | 593 | FT |
| 1379269 | 2026-03-22T14:15:00+00:00 | Regular Season - 31 | 66 | Aston Villa | 48 | West Ham | 495 | FT |
| 1379288 | 2026-04-10T19:00:00+00:00 | Regular Season - 32 | 48 | West Ham | 39 | Wolves | 598 | FT |
| 1379279 | 2026-04-11T11:30:00+00:00 | Regular Season - 32 | 42 | Arsenal | 35 | Bournemouth | 494 | FT |
| 1379281 | 2026-04-11T14:00:00+00:00 | Regular Season - 32 | 44 | Burnley | 51 | Brighton | 512 | FT |
| 1379280 | 2026-04-11T14:00:00+00:00 | Regular Season - 32 | 55 | Brentford | 45 | Everton | 10503 | FT |
| 1379284 | 2026-04-11T16:30:00+00:00 | Regular Season - 32 | 40 | Liverpool | 36 | Fulham | 550 | FT |
| 1379283 | 2026-04-12T13:00:00+00:00 | Regular Season - 32 | 52 | Crystal Palace | 34 | Newcastle | 525 | FT |
| 1379286 | 2026-04-12T13:00:00+00:00 | Regular Season - 32 | 65 | Nottingham Forest | 66 | Aston Villa | 566 | FT |
| 1379287 | 2026-04-12T13:00:00+00:00 | Regular Season - 32 | 746 | Sunderland | 47 | Tottenham | 589 | FT |
| 1379282 | 2026-04-12T15:30:00+00:00 | Regular Season - 32 | 49 | Chelsea | 50 | Manchester City | 519 | FT |
| 1379285 | 2026-04-13T19:00:00+00:00 | Regular Season - 32 | 33 | Manchester United | 63 | Leeds | 556 | FT |
| 1379290 | 2026-04-18T11:30:00+00:00 | Regular Season - 33 | 55 | Brentford | 36 | Fulham | 10503 | FT |
| 1379296 | 2026-04-18T14:00:00+00:00 | Regular Season - 33 | 34 | Newcastle | 35 | Bournemouth | 562 | FT |
| 1379294 | 2026-04-18T14:00:00+00:00 | Regular Season - 33 | 63 | Leeds | 39 | Wolves | 546 | FT |
| 1379298 | 2026-04-18T16:30:00+00:00 | Regular Season - 33 | 47 | Tottenham | 51 | Brighton | 593 | FT |
| 1379291 | 2026-04-18T19:00:00+00:00 | Regular Season - 33 | 49 | Chelsea | 33 | Manchester United | 519 | FT |
| 1379293 | 2026-04-19T13:00:00+00:00 | Regular Season - 33 | 45 | Everton | 40 | Liverpool | 22033 | FT |
| 1379297 | 2026-04-19T13:00:00+00:00 | Regular Season - 33 | 65 | Nottingham Forest | 44 | Burnley | 566 | FT |
| 1379289 | 2026-04-19T13:00:00+00:00 | Regular Season - 33 | 66 | Aston Villa | 746 | Sunderland | 495 | FT |
| 1379295 | 2026-04-19T15:30:00+00:00 | Regular Season - 33 | 50 | Manchester City | 42 | Arsenal | 555 | FT |
| 1379292 | 2026-04-20T19:00:00+00:00 | Regular Season - 33 | 52 | Crystal Palace | 48 | West Ham | 525 | FT |
| 1379301 | 2026-04-21T19:00:00+00:00 | Regular Season - 34 | 51 | Brighton | 49 | Chelsea | 508 | FT |
| 1379300 | 2026-04-22T19:00:00+00:00 | Regular Season - 34 | 35 | Bournemouth | 63 | Leeds | 504 | FT |
| 1379302 | 2026-04-22T19:00:00+00:00 | Regular Season - 34 | 44 | Burnley | 50 | Manchester City | 512 | FT |
| 1379306 | 2026-04-24T19:00:00+00:00 | Regular Season - 34 | 746 | Sunderland | 65 | Nottingham Forest | 589 | FT |
| 1379303 | 2026-04-25T11:30:00+00:00 | Regular Season - 34 | 36 | Fulham | 66 | Aston Villa | 535 | FT |
| 1379308 | 2026-04-25T14:00:00+00:00 | Regular Season - 34 | 39 | Wolves | 47 | Tottenham | 600 | FT |
| 1379304 | 2026-04-25T14:00:00+00:00 | Regular Season - 34 | 40 | Liverpool | 52 | Crystal Palace | 550 | FT |
| 1379307 | 2026-04-25T14:00:00+00:00 | Regular Season - 34 | 48 | West Ham | 45 | Everton | 598 | FT |
| 1379299 | 2026-04-25T16:30:00+00:00 | Regular Season - 34 | 42 | Arsenal | 34 | Newcastle | 494 | FT |
| 1379305 | 2026-04-27T19:00:00+00:00 | Regular Season - 34 | 33 | Manchester United | 55 | Brentford | 556 | FT |
| 1379315 | 2026-05-01T19:00:00+00:00 | Regular Season - 35 | 63 | Leeds | 44 | Burnley | 546 | FT |
| 1379317 | 2026-05-02T14:00:00+00:00 | Regular Season - 35 | 34 | Newcastle | 51 | Brighton | 562 | NS |
| 1379318 | 2026-05-02T14:00:00+00:00 | Regular Season - 35 | 39 | Wolves | 746 | Sunderland | 600 | NS |
| 1379312 | 2026-05-02T14:00:00+00:00 | Regular Season - 35 | 55 | Brentford | 48 | West Ham | 10503 | NS |
| 1379309 | 2026-05-02T16:30:00+00:00 | Regular Season - 35 | 42 | Arsenal | 36 | Fulham | 494 | NS |
| 1379311 | 2026-05-03T13:00:00+00:00 | Regular Season - 35 | 35 | Bournemouth | 52 | Crystal Palace | 504 | NS |
| 1379316 | 2026-05-03T14:30:00+00:00 | Regular Season - 35 | 33 | Manchester United | 40 | Liverpool | 556 | NS |
| 1379310 | 2026-05-03T18:00:00+00:00 | Regular Season - 35 | 66 | Aston Villa | 47 | Tottenham | 495 | NS |
| 1379313 | 2026-05-04T14:00:00+00:00 | Regular Season - 35 | 49 | Chelsea | 65 | Nottingham Forest | 519 | NS |
| 1379314 | 2026-05-04T19:00:00+00:00 | Regular Season - 35 | 45 | Everton | 50 | Manchester City | 22033 | NS |
| 1379323 | 2026-05-09T11:30:00+00:00 | Regular Season - 36 | 40 | Liverpool | 49 | Chelsea | 550 | NS |
| 1379322 | 2026-05-09T14:00:00+00:00 | Regular Season - 36 | 36 | Fulham | 35 | Bournemouth | 535 | NS |
| 1379319 | 2026-05-09T14:00:00+00:00 | Regular Season - 36 | 51 | Brighton | 39 | Wolves | 508 | NS |
| 1379326 | 2026-05-09T14:00:00+00:00 | Regular Season - 36 | 746 | Sunderland | 33 | Manchester United | 589 | NS |
| 1379324 | 2026-05-09T16:30:00+00:00 | Regular Season - 36 | 50 | Manchester City | 55 | Brentford | 555 | NS |
| 1379320 | 2026-05-10T13:00:00+00:00 | Regular Season - 36 | 44 | Burnley | 66 | Aston Villa | 512 | NS |
| 1379321 | 2026-05-10T13:00:00+00:00 | Regular Season - 36 | 52 | Crystal Palace | 45 | Everton | 525 | NS |
| 1379325 | 2026-05-10T13:00:00+00:00 | Regular Season - 36 | 65 | Nottingham Forest | 34 | Newcastle | 566 | NS |
| 1379328 | 2026-05-10T15:30:00+00:00 | Regular Season - 36 | 48 | West Ham | 42 | Arsenal | 598 | NS |
| 1379327 | 2026-05-11T19:00:00+00:00 | Regular Season - 36 | 47 | Tottenham | 63 | Leeds | 593 | NS |
| 1379275 | 2026-05-13T19:00:00+00:00 | Regular Season - 31 | 50 | Manchester City | 52 | Crystal Palace | 555 | NS |
| 1379336 | 2026-05-17T11:30:00+00:00 | Regular Season - 37 | 33 | Manchester United | 65 | Nottingham Forest | 556 | NS |
| 1379330 | 2026-05-17T11:30:00+00:00 | Regular Season - 37 | 66 | Aston Villa | 40 | Liverpool | 495 | NS |
| 1379338 | 2026-05-17T14:00:00+00:00 | Regular Season - 37 | 39 | Wolves | 36 | Fulham | 600 | NS |
| 1379334 | 2026-05-17T14:00:00+00:00 | Regular Season - 37 | 45 | Everton | 746 | Sunderland | 22033 | NS |
| 1379332 | 2026-05-17T14:00:00+00:00 | Regular Season - 37 | 55 | Brentford | 52 | Crystal Palace | 10503 | NS |
| 1379335 | 2026-05-17T14:00:00+00:00 | Regular Season - 37 | 63 | Leeds | 51 | Brighton | 546 | NS |
| 1379337 | 2026-05-17T16:30:00+00:00 | Regular Season - 37 | 34 | Newcastle | 48 | West Ham | 562 | NS |
| 1379329 | 2026-05-18T19:00:00+00:00 | Regular Season - 37 | 42 | Arsenal | 44 | Burnley | 494 | NS |
| 1379331 | 2026-05-19T18:30:00+00:00 | Regular Season - 37 | 35 | Bournemouth | 50 | Manchester City | 504 | NS |
| 1379333 | 2026-05-19T19:15:00+00:00 | Regular Season - 37 | 49 | Chelsea | 47 | Tottenham | 519 | NS |
| 1379342 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 36 | Fulham | 34 | Newcastle | 535 | NS |
| 1379343 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 40 | Liverpool | 55 | Brentford | 550 | NS |
| 1379340 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 44 | Burnley | 39 | Wolves | 512 | NS |
| 1379347 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 47 | Tottenham | 45 | Everton | 593 | NS |
| 1379348 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 48 | West Ham | 63 | Leeds | 598 | NS |
| 1379344 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 50 | Manchester City | 66 | Aston Villa | 555 | NS |
| 1379339 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 51 | Brighton | 33 | Manchester United | 508 | NS |
| 1379341 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 52 | Crystal Palace | 42 | Arsenal | 525 | NS |
| 1379345 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 65 | Nottingham Forest | 35 | Bournemouth | 566 | NS |
| 1379346 | 2026-05-24T15:00:00+00:00 | Regular Season - 38 | 746 | Sunderland | 49 | Chelsea | 589 | NS |


## La Liga

| Champ | Valeur |
| --- | --- |
| league_id | 140 |
| api_name | La Liga |
| country | Spain |
| type | League |
| season | 2025 |
| season_start | 2025-08-15 |
| season_end | 2026-05-24 |


### Coverage

```json
{
  "fixtures": {
    "events": true,
    "lineups": true,
    "statistics_fixtures": true,
    "statistics_players": true
  },
  "standings": true,
  "players": true,
  "top_scorers": true,
  "top_assists": true,
  "top_cards": true,
  "injuries": true,
  "predictions": true,
  "odds": true
}
```

### Teams et stades

| team_id | name | code | country | national | venue_id | venue | city | capacity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 542 | Alaves | ALA | Spain | False | 1470 | Estadio de Mendizorroza | Vitoria-Gasteiz | 19840 |
| 531 | Athletic Club | BIL | Spain | False | 1460 | San Mamés Barria | Bilbao | 53289 |
| 530 | Atletico Madrid | ATM | Spain | False | 19217 | Estádio Cívitas Metropolitano | Madrid | 70460 |
| 529 | Barcelona | BAR | Spain | False | 19939 | Camp Nou | Barcelona | 55926 |
| 538 | Celta Vigo | CEL | Spain | False | 1467 | Abanca-Balaídos | Vigo | 31800 |
| 797 | Elche | ELC | Spain | False | 1473 | Estadio Manuel Martínez Valero | Elche | 36017 |
| 540 | Espanyol | ESP | Spain | False | 20421 | Stage Front Stadium | Cornella de Llobregat | 40423 |
| 546 | Getafe | GET | Spain | False | 20422 | Estadio Coliseum | Getafe | 17393 |
| 547 | Girona | GIR | Spain | False | 1478 | Estadi Municipal de Montilivi | Girona | 14500 |
| 539 | Levante | LEV | Spain | False | 1482 | Estadio Ciudad de Valencia | Valencia | 25534 |
| 798 | Mallorca | MAL | Spain | False | 19940 | Estadi Mallorca Son Moix | Palma de Mallorca | 23142 |
| 727 | Osasuna | OSA | Spain | False | 1486 | Estadio El Sadar | Iruñea | 23576 |
| 718 | Oviedo | OVI | Spain | False | 1490 | Estadio Nuevo Carlos Tartiere | Oviedo | 30500 |
| 728 | Rayo Vallecano | RAY | Spain | False | 1488 | Estadio de Vallecas | Madrid | 15500 |
| 543 | Real Betis | BET | Spain | False | 1489 | Estadio Benito Villamarín | Sevilla | 60721 |
| 541 | Real Madrid | REA | Spain | False | 1456 | Estadio Santiago Bernabéu | Madrid | 85454 |
| 548 | Real Sociedad | RSO | Spain | False | 1491 | Reale Arena | Donostia-San Sebastián | 40000 |
| 536 | Sevilla | SEV | Spain | False | 1494 | Estadio Ramón Sánchez Pizjuán | Sevilla | 48649 |
| 532 | Valencia | VAL | Spain | False | 1497 | Estadio de Mestalla | Valencia | 55000 |
| 533 | Villarreal | VIL | Spain | False | 1498 | Estadio de la Cerámica | Villarreal | 24500 |


### Rounds

- `Regular Season - 1`
- `Regular Season - 2`
- `Regular Season - 6`
- `Regular Season - 3`
- `Regular Season - 4`
- `Regular Season - 5`
- `Regular Season - 7`
- `Regular Season - 8`
- `Regular Season - 9`
- `Regular Season - 10`
- `Regular Season - 11`
- `Regular Season - 12`
- `Regular Season - 13`
- `Regular Season - 14`
- `Regular Season - 19`
- `Regular Season - 15`
- `Regular Season - 16`
- `Regular Season - 17`
- `Regular Season - 18`
- `Regular Season - 20`
- `Regular Season - 21`
- `Regular Season - 22`
- `Regular Season - 23`
- `Regular Season - 24`
- `Regular Season - 25`
- `Regular Season - 26`
- `Regular Season - 27`
- `Regular Season - 28`
- `Regular Season - 29`
- `Regular Season - 30`
- `Regular Season - 31`
- `Regular Season - 33`
- `Regular Season - 32`
- `Regular Season - 34`
- `Regular Season - 35`
- `Regular Season - 36`
- `Regular Season - 37`
- `Regular Season - 38`

### Standings

| rank | team_id | team | group | pts | played | W | D | L | GD | form |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 529 | Barcelona | Primera División | 85 | 33 | 28 | 1 | 4 | 57 | WWWWW |
| 2 | 541 | Real Madrid | Primera División | 74 | 33 | 23 | 5 | 5 | 37 | DWDLW |
| 3 | 533 | Villarreal | Primera División | 65 | 33 | 20 | 5 | 8 | 21 | WDWLW |
| 4 | 530 | Atletico Madrid | Primera División | 60 | 33 | 18 | 6 | 9 | 19 | WLLLL |
| 5 | 543 | Real Betis | Primera División | 50 | 33 | 12 | 14 | 7 | 8 | DWDDL |
| 6 | 546 | Getafe | Primera División | 44 | 33 | 13 | 5 | 15 | -6 | LWLWW |
| 7 | 538 | Celta Vigo | Primera División | 44 | 33 | 11 | 11 | 11 | 2 | LLLWL |
| 8 | 548 | Real Sociedad | Primera División | 43 | 33 | 11 | 10 | 12 | 0 | DLDWL |
| 9 | 727 | Osasuna | Primera División | 42 | 33 | 11 | 9 | 13 | -1 | WLDDW |
| 10 | 531 | Athletic Club | Primera División | 41 | 33 | 12 | 5 | 16 | -12 | LWLLW |
| 11 | 728 | Rayo Vallecano | Primera División | 39 | 33 | 9 | 12 | 12 | -8 | DWLWL |
| 12 | 532 | Valencia | Primera División | 39 | 33 | 10 | 9 | 14 | -11 | WDLLW |
| 13 | 540 | Espanyol | Primera División | 39 | 33 | 10 | 9 | 14 | -12 | DLLDL |
| 14 | 797 | Elche | Primera División | 38 | 33 | 9 | 11 | 13 | -6 | WWWLW |
| 15 | 798 | Mallorca | Primera División | 38 | 34 | 10 | 8 | 16 | -9 | WLDWW |
| 16 | 547 | Girona | Primera División | 38 | 34 | 9 | 11 | 14 | -15 | LLLDW |
| 17 | 542 | Alaves | Primera División | 36 | 33 | 9 | 9 | 15 | -11 | WLDDW |
| 18 | 536 | Sevilla | Primera División | 34 | 33 | 9 | 7 | 17 | -15 | LLWLL |
| 19 | 539 | Levante | Primera División | 33 | 33 | 8 | 9 | 16 | -13 | DWWLW |
| 20 | 718 | Oviedo | Primera División | 28 | 33 | 6 | 10 | 17 | -25 | LDWWL |


### Fixtures

| fixture_id | date | round | home_id | home | away_id | away | venue_id | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1390824 | 2025-08-15T17:00:00+00:00 | Regular Season - 1 | 547 | Girona | 728 | Rayo Vallecano |  | FT |
| 1390828 | 2025-08-15T19:30:00+00:00 | Regular Season - 1 | 533 | Villarreal | 718 | Oviedo | 1498 | FT |
| 1390825 | 2025-08-16T17:30:00+00:00 | Regular Season - 1 | 798 | Mallorca | 529 | Barcelona | 19940 | FT |
| 1390827 | 2025-08-16T19:30:00+00:00 | Regular Season - 1 | 532 | Valencia | 548 | Real Sociedad | 1497 | FT |
| 1390819 | 2025-08-16T19:30:00+00:00 | Regular Season - 1 | 542 | Alaves | 539 | Levante | 1470 | FT |
| 1390821 | 2025-08-17T15:00:00+00:00 | Regular Season - 1 | 538 | Celta Vigo | 546 | Getafe |  | FT |
| 1390820 | 2025-08-17T17:30:00+00:00 | Regular Season - 1 | 531 | Athletic Club | 536 | Sevilla |  | FT |
| 1390823 | 2025-08-17T19:30:00+00:00 | Regular Season - 1 | 540 | Espanyol | 530 | Atletico Madrid |  | FT |
| 1390822 | 2025-08-18T19:00:00+00:00 | Regular Season - 1 | 797 | Elche | 543 | Real Betis | 1473 | FT |
| 1390826 | 2025-08-19T19:00:00+00:00 | Regular Season - 1 | 541 | Real Madrid | 727 | Osasuna | 1456 | FT |
| 1390831 | 2025-08-22T19:30:00+00:00 | Regular Season - 2 | 543 | Real Betis | 542 | Alaves |  | FT |
| 1390833 | 2025-08-23T15:00:00+00:00 | Regular Season - 2 | 798 | Mallorca | 538 | Celta Vigo | 19940 | FT |
| 1390830 | 2025-08-23T17:30:00+00:00 | Regular Season - 2 | 530 | Atletico Madrid | 797 | Elche |  | FT |
| 1390832 | 2025-08-23T19:30:00+00:00 | Regular Season - 2 | 539 | Levante | 529 | Barcelona | 1482 | FT |
| 1390834 | 2025-08-24T15:00:00+00:00 | Regular Season - 2 | 727 | Osasuna | 532 | Valencia |  | FT |
| 1390838 | 2025-08-24T17:30:00+00:00 | Regular Season - 2 | 533 | Villarreal | 547 | Girona | 1498 | FT |
| 1390835 | 2025-08-24T17:30:00+00:00 | Regular Season - 2 | 548 | Real Sociedad | 540 | Espanyol |  | FT |
| 1390836 | 2025-08-24T19:30:00+00:00 | Regular Season - 2 | 718 | Oviedo | 541 | Real Madrid | 1490 | FT |
| 1390829 | 2025-08-25T17:30:00+00:00 | Regular Season - 2 | 531 | Athletic Club | 728 | Rayo Vallecano |  | FT |
| 1390837 | 2025-08-25T19:30:00+00:00 | Regular Season - 2 | 536 | Sevilla | 546 | Getafe | 1494 | FT |
| 1390871 | 2025-08-27T19:00:00+00:00 | Regular Season - 6 | 538 | Celta Vigo | 543 | Real Betis |  | FT |
| 1390842 | 2025-08-29T17:30:00+00:00 | Regular Season - 3 | 797 | Elche | 539 | Levante | 1473 | FT |
| 1390848 | 2025-08-29T19:30:00+00:00 | Regular Season - 3 | 532 | Valencia | 546 | Getafe | 1497 | FT |
| 1390839 | 2025-08-30T15:00:00+00:00 | Regular Season - 3 | 542 | Alaves | 530 | Atletico Madrid |  | FT |
| 1390847 | 2025-08-30T17:00:00+00:00 | Regular Season - 3 | 718 | Oviedo | 548 | Real Sociedad | 1490 | FT |
| 1390844 | 2025-08-30T17:30:00+00:00 | Regular Season - 3 | 547 | Girona | 536 | Sevilla |  | FT |
| 1390846 | 2025-08-30T19:30:00+00:00 | Regular Season - 3 | 541 | Real Madrid | 798 | Mallorca | 1456 | FT |
| 1390841 | 2025-08-31T15:00:00+00:00 | Regular Season - 3 | 538 | Celta Vigo | 533 | Villarreal |  | FT |
| 1390840 | 2025-08-31T17:00:00+00:00 | Regular Season - 3 | 543 | Real Betis | 531 | Athletic Club |  | FT |
| 1390843 | 2025-08-31T17:30:00+00:00 | Regular Season - 3 | 540 | Espanyol | 727 | Osasuna |  | FT |
| 1390845 | 2025-08-31T19:30:00+00:00 | Regular Season - 3 | 728 | Rayo Vallecano | 529 | Barcelona | 1488 | FT |
| 1390858 | 2025-09-12T19:00:00+00:00 | Regular Season - 4 | 536 | Sevilla | 797 | Elche | 1494 | FT |
| 1390854 | 2025-09-13T12:00:00+00:00 | Regular Season - 4 | 546 | Getafe | 718 | Oviedo |  | FT |
| 1390857 | 2025-09-13T14:15:00+00:00 | Regular Season - 4 | 548 | Real Sociedad | 541 | Real Madrid |  | FT |
| 1390849 | 2025-09-13T16:30:00+00:00 | Regular Season - 4 | 531 | Athletic Club | 542 | Alaves |  | FT |
| 1390850 | 2025-09-13T19:00:00+00:00 | Regular Season - 4 | 530 | Atletico Madrid | 533 | Villarreal |  | FT |
| 1390852 | 2025-09-14T12:00:00+00:00 | Regular Season - 4 | 538 | Celta Vigo | 547 | Girona |  | FT |
| 1390855 | 2025-09-14T14:15:00+00:00 | Regular Season - 4 | 539 | Levante | 543 | Real Betis | 1482 | FT |
| 1390856 | 2025-09-14T16:30:00+00:00 | Regular Season - 4 | 727 | Osasuna | 728 | Rayo Vallecano |  | FT |
| 1390851 | 2025-09-14T19:00:00+00:00 | Regular Season - 4 | 529 | Barcelona | 532 | Valencia |  | FT |
| 1390853 | 2025-09-15T19:00:00+00:00 | Regular Season - 4 | 540 | Espanyol | 798 | Mallorca |  | FT |
| 1390861 | 2025-09-19T19:00:00+00:00 | Regular Season - 5 | 543 | Real Betis | 548 | Real Sociedad |  | FT |
| 1390863 | 2025-09-20T12:00:00+00:00 | Regular Season - 5 | 547 | Girona | 539 | Levante |  | FT |
| 1390866 | 2025-09-20T14:15:00+00:00 | Regular Season - 5 | 541 | Real Madrid | 540 | Espanyol | 1456 | FT |
| 1390868 | 2025-09-20T16:30:00+00:00 | Regular Season - 5 | 533 | Villarreal | 727 | Osasuna | 1498 | FT |
| 1390859 | 2025-09-20T16:30:00+00:00 | Regular Season - 5 | 542 | Alaves | 536 | Sevilla | 1470 | FT |
| 1390867 | 2025-09-20T19:00:00+00:00 | Regular Season - 5 | 532 | Valencia | 531 | Athletic Club | 1497 | FT |
| 1390865 | 2025-09-21T12:00:00+00:00 | Regular Season - 5 | 728 | Rayo Vallecano | 538 | Celta Vigo | 1488 | FT |
| 1390864 | 2025-09-21T14:15:00+00:00 | Regular Season - 5 | 798 | Mallorca | 530 | Atletico Madrid | 19940 | FT |
| 1390862 | 2025-09-21T16:30:00+00:00 | Regular Season - 5 | 797 | Elche | 718 | Oviedo | 1473 | FT |
| 1390860 | 2025-09-21T19:00:00+00:00 | Regular Season - 5 | 529 | Barcelona | 546 | Getafe |  | FT |
| 1390869 | 2025-09-23T17:00:00+00:00 | Regular Season - 6 | 531 | Athletic Club | 547 | Girona |  | FT |
| 1390872 | 2025-09-23T17:00:00+00:00 | Regular Season - 6 | 540 | Espanyol | 532 | Valencia |  | FT |
| 1390878 | 2025-09-23T19:30:00+00:00 | Regular Season - 6 | 536 | Sevilla | 533 | Villarreal | 1494 | FT |
| 1390874 | 2025-09-23T19:30:00+00:00 | Regular Season - 6 | 539 | Levante | 541 | Real Madrid | 1482 | FT |
| 1390873 | 2025-09-24T17:00:00+00:00 | Regular Season - 6 | 546 | Getafe | 542 | Alaves |  | FT |
| 1390870 | 2025-09-24T19:30:00+00:00 | Regular Season - 6 | 530 | Atletico Madrid | 728 | Rayo Vallecano |  | FT |
| 1390876 | 2025-09-24T19:30:00+00:00 | Regular Season - 6 | 548 | Real Sociedad | 798 | Mallorca |  | FT |
| 1390875 | 2025-09-25T17:30:00+00:00 | Regular Season - 6 | 727 | Osasuna | 797 | Elche |  | FT |
| 1390877 | 2025-09-25T19:30:00+00:00 | Regular Season - 6 | 718 | Oviedo | 529 | Barcelona | 1490 | FT |
| 1390884 | 2025-09-26T19:00:00+00:00 | Regular Season - 7 | 547 | Girona | 540 | Espanyol |  | FT |
| 1390883 | 2025-09-27T12:00:00+00:00 | Regular Season - 7 | 546 | Getafe | 539 | Levante |  | FT |
| 1390879 | 2025-09-27T14:15:00+00:00 | Regular Season - 7 | 530 | Atletico Madrid | 541 | Real Madrid |  | FT |
| 1390885 | 2025-09-27T16:30:00+00:00 | Regular Season - 7 | 798 | Mallorca | 542 | Alaves | 19940 | FT |
| 1390888 | 2025-09-27T19:00:00+00:00 | Regular Season - 7 | 533 | Villarreal | 531 | Athletic Club | 1498 | FT |
| 1390886 | 2025-09-28T12:00:00+00:00 | Regular Season - 7 | 728 | Rayo Vallecano | 536 | Sevilla | 1488 | FT |
| 1390882 | 2025-09-28T14:15:00+00:00 | Regular Season - 7 | 797 | Elche | 538 | Celta Vigo | 1473 | FT |
| 1390880 | 2025-09-28T16:30:00+00:00 | Regular Season - 7 | 529 | Barcelona | 548 | Real Sociedad | 18630 | FT |
| 1390881 | 2025-09-28T19:00:00+00:00 | Regular Season - 7 | 543 | Real Betis | 727 | Osasuna |  | FT |
| 1390887 | 2025-09-30T18:00:00+00:00 | Regular Season - 7 | 532 | Valencia | 718 | Oviedo | 1497 | FT |
| 1390894 | 2025-10-03T19:00:00+00:00 | Regular Season - 8 | 727 | Osasuna | 546 | Getafe |  | FT |
| 1390897 | 2025-10-04T12:00:00+00:00 | Regular Season - 8 | 718 | Oviedo | 539 | Levante | 1490 | FT |
| 1390893 | 2025-10-04T14:15:00+00:00 | Regular Season - 8 | 547 | Girona | 532 | Valencia | 1478 | FT |
| 1390890 | 2025-10-04T16:30:00+00:00 | Regular Season - 8 | 531 | Athletic Club | 798 | Mallorca |  | FT |
| 1390895 | 2025-10-04T19:00:00+00:00 | Regular Season - 8 | 541 | Real Madrid | 533 | Villarreal | 1456 | FT |
| 1390889 | 2025-10-05T12:00:00+00:00 | Regular Season - 8 | 542 | Alaves | 797 | Elche | 1470 | FT |
| 1390898 | 2025-10-05T14:15:00+00:00 | Regular Season - 8 | 536 | Sevilla | 529 | Barcelona | 1494 | FT |
| 1390892 | 2025-10-05T16:30:00+00:00 | Regular Season - 8 | 540 | Espanyol | 543 | Real Betis |  | FT |
| 1390896 | 2025-10-05T16:30:00+00:00 | Regular Season - 8 | 548 | Real Sociedad | 728 | Rayo Vallecano |  | FT |
| 1390891 | 2025-10-05T19:00:00+00:00 | Regular Season - 8 | 538 | Celta Vigo | 530 | Atletico Madrid |  | FT |
| 1390906 | 2025-10-17T19:00:00+00:00 | Regular Season - 9 | 718 | Oviedo | 540 | Espanyol | 1490 | FT |
| 1390907 | 2025-10-18T12:00:00+00:00 | Regular Season - 9 | 536 | Sevilla | 798 | Mallorca | 1494 | FT |
| 1390901 | 2025-10-18T14:15:00+00:00 | Regular Season - 9 | 529 | Barcelona | 547 | Girona |  | FT |
| 1390908 | 2025-10-18T16:30:00+00:00 | Regular Season - 9 | 533 | Villarreal | 543 | Real Betis | 1498 | FT |
| 1390900 | 2025-10-18T19:00:00+00:00 | Regular Season - 9 | 530 | Atletico Madrid | 727 | Osasuna |  | FT |
| 1390903 | 2025-10-19T12:00:00+00:00 | Regular Season - 9 | 797 | Elche | 531 | Athletic Club | 1473 | FT |
| 1390902 | 2025-10-19T14:15:00+00:00 | Regular Season - 9 | 538 | Celta Vigo | 548 | Real Sociedad |  | FT |
| 1390905 | 2025-10-19T16:30:00+00:00 | Regular Season - 9 | 539 | Levante | 728 | Rayo Vallecano | 1482 | FT |
| 1390904 | 2025-10-19T19:00:00+00:00 | Regular Season - 9 | 546 | Getafe | 541 | Real Madrid | 20422 | FT |
| 1390899 | 2025-10-20T19:00:00+00:00 | Regular Season - 9 | 542 | Alaves | 532 | Valencia | 1470 | FT |
| 1390917 | 2025-10-24T19:00:00+00:00 | Regular Season - 10 | 548 | Real Sociedad | 536 | Sevilla |  | FT |
| 1390912 | 2025-10-25T12:00:00+00:00 | Regular Season - 10 | 547 | Girona | 718 | Oviedo | 1478 | FT |
| 1390911 | 2025-10-25T14:15:00+00:00 | Regular Season - 10 | 540 | Espanyol | 797 | Elche |  | FT |
| 1390909 | 2025-10-25T16:30:00+00:00 | Regular Season - 10 | 531 | Athletic Club | 546 | Getafe |  | FT |
| 1390918 | 2025-10-25T19:00:00+00:00 | Regular Season - 10 | 532 | Valencia | 533 | Villarreal | 1497 | FT |
| 1390913 | 2025-10-26T13:00:00+00:00 | Regular Season - 10 | 798 | Mallorca | 539 | Levante | 19940 | FT |
| 1390916 | 2025-10-26T15:15:00+00:00 | Regular Season - 10 | 541 | Real Madrid | 529 | Barcelona | 1456 | FT |
| 1390914 | 2025-10-26T17:30:00+00:00 | Regular Season - 10 | 727 | Osasuna | 538 | Celta Vigo |  | FT |
| 1390915 | 2025-10-26T20:00:00+00:00 | Regular Season - 10 | 728 | Rayo Vallecano | 542 | Alaves | 1488 | FT |
| 1390910 | 2025-10-27T20:00:00+00:00 | Regular Season - 10 | 543 | Real Betis | 530 | Atletico Madrid |  | FT |
| 1390923 | 2025-10-31T20:00:00+00:00 | Regular Season - 11 | 546 | Getafe | 547 | Girona | 20422 | FT |
| 1390928 | 2025-11-01T13:00:00+00:00 | Regular Season - 11 | 533 | Villarreal | 728 | Rayo Vallecano | 1498 | FT |
| 1390920 | 2025-11-01T15:15:00+00:00 | Regular Season - 11 | 530 | Atletico Madrid | 536 | Sevilla |  | FT |
| 1390926 | 2025-11-01T17:30:00+00:00 | Regular Season - 11 | 548 | Real Sociedad | 531 | Athletic Club |  | FT |
| 1390925 | 2025-11-01T20:00:00+00:00 | Regular Season - 11 | 541 | Real Madrid | 532 | Valencia | 1456 | FT |
| 1390924 | 2025-11-02T13:00:00+00:00 | Regular Season - 11 | 539 | Levante | 538 | Celta Vigo | 1482 | FT |
| 1390919 | 2025-11-02T15:15:00+00:00 | Regular Season - 11 | 542 | Alaves | 540 | Espanyol | 1470 | FT |
| 1390921 | 2025-11-02T17:30:00+00:00 | Regular Season - 11 | 529 | Barcelona | 797 | Elche |  | FT |
| 1390922 | 2025-11-02T20:00:00+00:00 | Regular Season - 11 | 543 | Real Betis | 798 | Mallorca |  | FT |
| 1390927 | 2025-11-03T20:00:00+00:00 | Regular Season - 11 | 718 | Oviedo | 727 | Osasuna | 1490 | FT |
| 1390932 | 2025-11-07T20:00:00+00:00 | Regular Season - 12 | 797 | Elche | 548 | Real Sociedad | 1473 | FT |
| 1390934 | 2025-11-08T13:00:00+00:00 | Regular Season - 12 | 547 | Girona | 542 | Alaves | 1478 | FT |
| 1390937 | 2025-11-08T15:15:00+00:00 | Regular Season - 12 | 536 | Sevilla | 727 | Osasuna | 1494 | FT |
| 1390930 | 2025-11-08T17:30:00+00:00 | Regular Season - 12 | 530 | Atletico Madrid | 539 | Levante |  | FT |
| 1390933 | 2025-11-08T20:00:00+00:00 | Regular Season - 12 | 540 | Espanyol | 533 | Villarreal |  | FT |
| 1390929 | 2025-11-09T13:00:00+00:00 | Regular Season - 12 | 531 | Athletic Club | 718 | Oviedo |  | FT |
| 1390936 | 2025-11-09T15:15:00+00:00 | Regular Season - 12 | 728 | Rayo Vallecano | 541 | Real Madrid | 1488 | FT |
| 1390938 | 2025-11-09T17:30:00+00:00 | Regular Season - 12 | 532 | Valencia | 543 | Real Betis | 1497 | FT |
| 1390935 | 2025-11-09T17:30:00+00:00 | Regular Season - 12 | 798 | Mallorca | 546 | Getafe | 19940 | FT |
| 1390931 | 2025-11-09T20:00:00+00:00 | Regular Season - 12 | 538 | Celta Vigo | 529 | Barcelona |  | FT |
| 1390947 | 2025-11-21T20:00:00+00:00 | Regular Season - 13 | 532 | Valencia | 539 | Levante | 1497 | FT |
| 1390939 | 2025-11-22T13:00:00+00:00 | Regular Season - 13 | 542 | Alaves | 538 | Celta Vigo | 1470 | FT |
| 1390940 | 2025-11-22T15:15:00+00:00 | Regular Season - 13 | 529 | Barcelona | 531 | Athletic Club | 19939 | FT |
| 1390945 | 2025-11-22T17:30:00+00:00 | Regular Season - 13 | 727 | Osasuna | 548 | Real Sociedad |  | FT |
| 1390948 | 2025-11-22T20:00:00+00:00 | Regular Season - 13 | 533 | Villarreal | 798 | Mallorca | 1498 | FT |
| 1390946 | 2025-11-23T13:00:00+00:00 | Regular Season - 13 | 718 | Oviedo | 728 | Rayo Vallecano | 1490 | FT |
| 1390941 | 2025-11-23T15:15:00+00:00 | Regular Season - 13 | 543 | Real Betis | 547 | Girona |  | FT |
| 1390944 | 2025-11-23T17:30:00+00:00 | Regular Season - 13 | 546 | Getafe | 530 | Atletico Madrid | 20422 | FT |
| 1390942 | 2025-11-23T20:00:00+00:00 | Regular Season - 13 | 797 | Elche | 541 | Real Madrid | 1473 | FT |
| 1390943 | 2025-11-24T20:00:00+00:00 | Regular Season - 13 | 540 | Espanyol | 536 | Sevilla |  | FT |
| 1390952 | 2025-11-28T20:00:00+00:00 | Regular Season - 14 | 546 | Getafe | 797 | Elche | 20422 | FT |
| 1390955 | 2025-11-29T13:00:00+00:00 | Regular Season - 14 | 798 | Mallorca | 727 | Osasuna | 19940 | FT |
| 1390950 | 2025-11-29T15:15:00+00:00 | Regular Season - 14 | 529 | Barcelona | 542 | Alaves | 19939 | FT |
| 1390954 | 2025-11-29T17:30:00+00:00 | Regular Season - 14 | 539 | Levante | 531 | Athletic Club | 1482 | FT |
| 1390949 | 2025-11-29T20:00:00+00:00 | Regular Season - 14 | 530 | Atletico Madrid | 718 | Oviedo |  | FT |
| 1390957 | 2025-11-30T13:00:00+00:00 | Regular Season - 14 | 548 | Real Sociedad | 533 | Villarreal |  | FT |
| 1390958 | 2025-11-30T15:15:00+00:00 | Regular Season - 14 | 536 | Sevilla | 543 | Real Betis | 1494 | FT |
| 1390951 | 2025-11-30T17:30:00+00:00 | Regular Season - 14 | 538 | Celta Vigo | 540 | Espanyol |  | FT |
| 1390953 | 2025-11-30T20:00:00+00:00 | Regular Season - 14 | 547 | Girona | 541 | Real Madrid | 1478 | FT |
| 1390956 | 2025-12-01T20:00:00+00:00 | Regular Season - 14 | 728 | Rayo Vallecano | 532 | Valencia | 1488 | FT |
| 1391000 | 2025-12-02T20:00:00+00:00 | Regular Season - 19 | 529 | Barcelona | 530 | Atletico Madrid | 19939 | FT |
| 1390999 | 2025-12-03T18:00:00+00:00 | Regular Season - 19 | 531 | Athletic Club | 541 | Real Madrid |  | FT |
| 1390966 | 2025-12-05T20:00:00+00:00 | Regular Season - 15 | 718 | Oviedo | 798 | Mallorca | 1490 | FT |
| 1390968 | 2025-12-06T13:00:00+00:00 | Regular Season - 15 | 533 | Villarreal | 546 | Getafe | 1498 | FT |
| 1390959 | 2025-12-06T15:15:00+00:00 | Regular Season - 15 | 542 | Alaves | 548 | Real Sociedad | 1470 | FT |
| 1390961 | 2025-12-06T17:30:00+00:00 | Regular Season - 15 | 543 | Real Betis | 529 | Barcelona |  | FT |
| 1390960 | 2025-12-06T20:00:00+00:00 | Regular Season - 15 | 531 | Athletic Club | 530 | Atletico Madrid |  | FT |
| 1390962 | 2025-12-07T13:00:00+00:00 | Regular Season - 15 | 797 | Elche | 547 | Girona | 1473 | FT |
| 1390967 | 2025-12-07T15:15:00+00:00 | Regular Season - 15 | 532 | Valencia | 536 | Sevilla | 1497 | FT |
| 1390963 | 2025-12-07T17:30:00+00:00 | Regular Season - 15 | 540 | Espanyol | 728 | Rayo Vallecano |  | FT |
| 1390965 | 2025-12-07T20:00:00+00:00 | Regular Season - 15 | 541 | Real Madrid | 538 | Celta Vigo | 1456 | FT |
| 1390964 | 2025-12-08T20:00:00+00:00 | Regular Season - 15 | 727 | Osasuna | 539 | Levante |  | FT |
| 1390977 | 2025-12-12T20:00:00+00:00 | Regular Season - 16 | 548 | Real Sociedad | 547 | Girona |  | FT |
| 1390970 | 2025-12-13T13:00:00+00:00 | Regular Season - 16 | 530 | Atletico Madrid | 532 | Valencia |  | FT |
| 1390975 | 2025-12-13T15:15:00+00:00 | Regular Season - 16 | 798 | Mallorca | 797 | Elche | 19940 | FT |
| 1390971 | 2025-12-13T17:30:00+00:00 | Regular Season - 16 | 529 | Barcelona | 727 | Osasuna | 19939 | FT |
| 1390973 | 2025-12-13T20:00:00+00:00 | Regular Season - 16 | 546 | Getafe | 540 | Espanyol | 20422 | FT |
| 1390978 | 2025-12-14T13:00:00+00:00 | Regular Season - 16 | 536 | Sevilla | 718 | Oviedo | 1494 | FT |
| 1390972 | 2025-12-14T15:15:00+00:00 | Regular Season - 16 | 538 | Celta Vigo | 531 | Athletic Club |  | FT |
| 1390969 | 2025-12-14T20:00:00+00:00 | Regular Season - 16 | 542 | Alaves | 541 | Real Madrid | 1470 | FT |
| 1390976 | 2025-12-15T20:00:00+00:00 | Regular Season - 16 | 728 | Rayo Vallecano | 543 | Real Betis | 1488 | FT |
| 1390987 | 2025-12-19T20:00:00+00:00 | Regular Season - 17 | 532 | Valencia | 798 | Mallorca | 1497 | FT |
| 1390986 | 2025-12-20T13:00:00+00:00 | Regular Season - 17 | 718 | Oviedo | 538 | Celta Vigo | 1490 | FT |
| 1390983 | 2025-12-20T15:15:00+00:00 | Regular Season - 17 | 539 | Levante | 548 | Real Sociedad | 1482 | FT |
| 1390984 | 2025-12-20T17:30:00+00:00 | Regular Season - 17 | 727 | Osasuna | 542 | Alaves |  | FT |
| 1390985 | 2025-12-20T20:00:00+00:00 | Regular Season - 17 | 541 | Real Madrid | 536 | Sevilla | 1456 | FT |
| 1390982 | 2025-12-21T13:00:00+00:00 | Regular Season - 17 | 547 | Girona | 530 | Atletico Madrid | 1478 | FT |
| 1390988 | 2025-12-21T15:15:00+00:00 | Regular Season - 17 | 533 | Villarreal | 529 | Barcelona | 1498 | FT |
| 1390981 | 2025-12-21T17:30:00+00:00 | Regular Season - 17 | 797 | Elche | 728 | Rayo Vallecano | 1473 | FT |
| 1390980 | 2025-12-21T20:00:00+00:00 | Regular Season - 17 | 543 | Real Betis | 546 | Getafe |  | FT |
| 1390979 | 2025-12-22T20:00:00+00:00 | Regular Season - 17 | 531 | Athletic Club | 540 | Espanyol |  | FT |
| 1390995 | 2026-01-02T20:00:00+00:00 | Regular Season - 18 | 728 | Rayo Vallecano | 546 | Getafe | 1488 | FT |
| 1390990 | 2026-01-03T13:00:00+00:00 | Regular Season - 18 | 538 | Celta Vigo | 532 | Valencia |  | FT |
| 1390994 | 2026-01-03T15:15:00+00:00 | Regular Season - 18 | 727 | Osasuna | 531 | Athletic Club |  | FT |
| 1390991 | 2026-01-03T17:30:00+00:00 | Regular Season - 18 | 797 | Elche | 533 | Villarreal | 1473 | FT |
| 1390992 | 2026-01-03T20:00:00+00:00 | Regular Season - 18 | 540 | Espanyol | 529 | Barcelona |  | FT |
| 1390998 | 2026-01-04T13:00:00+00:00 | Regular Season - 18 | 536 | Sevilla | 539 | Levante | 1494 | FT |
| 1390996 | 2026-01-04T15:15:00+00:00 | Regular Season - 18 | 541 | Real Madrid | 543 | Real Betis | 1456 | FT |
| 1390989 | 2026-01-04T17:30:00+00:00 | Regular Season - 18 | 542 | Alaves | 718 | Oviedo | 1470 | FT |
| 1390993 | 2026-01-04T17:30:00+00:00 | Regular Season - 18 | 798 | Mallorca | 547 | Girona | 19940 | FT |
| 1390997 | 2026-01-04T20:00:00+00:00 | Regular Season - 18 | 548 | Real Sociedad | 530 | Atletico Madrid |  | FT |
| 1391001 | 2026-01-09T20:00:00+00:00 | Regular Season - 19 | 546 | Getafe | 548 | Real Sociedad | 20422 | FT |
| 1391005 | 2026-01-10T13:00:00+00:00 | Regular Season - 19 | 718 | Oviedo | 543 | Real Betis | 1490 | FT |
| 1391008 | 2026-01-10T15:15:00+00:00 | Regular Season - 19 | 533 | Villarreal | 542 | Alaves | 1498 | FT |
| 1391002 | 2026-01-10T17:30:00+00:00 | Regular Season - 19 | 547 | Girona | 727 | Osasuna | 1478 | FT |
| 1391007 | 2026-01-10T20:00:00+00:00 | Regular Season - 19 | 532 | Valencia | 797 | Elche | 1497 | FT |
| 1391004 | 2026-01-11T13:00:00+00:00 | Regular Season - 19 | 728 | Rayo Vallecano | 798 | Mallorca | 1488 | FT |
| 1391003 | 2026-01-11T15:15:00+00:00 | Regular Season - 19 | 539 | Levante | 540 | Espanyol | 1482 | FT |
| 1391006 | 2026-01-12T20:00:00+00:00 | Regular Season - 19 | 536 | Sevilla | 538 | Celta Vigo | 1494 | FT |
| 1391013 | 2026-01-16T20:00:00+00:00 | Regular Season - 20 | 540 | Espanyol | 547 | Girona |  | FT |
| 1391017 | 2026-01-17T13:00:00+00:00 | Regular Season - 20 | 541 | Real Madrid | 539 | Levante | 1456 | FT |
| 1391015 | 2026-01-17T15:15:00+00:00 | Regular Season - 20 | 798 | Mallorca | 531 | Athletic Club | 19940 | FT |
| 1391016 | 2026-01-17T17:30:00+00:00 | Regular Season - 20 | 727 | Osasuna | 718 | Oviedo |  | FT |
| 1391010 | 2026-01-17T20:00:00+00:00 | Regular Season - 20 | 543 | Real Betis | 533 | Villarreal |  | FT |
| 1391014 | 2026-01-18T13:00:00+00:00 | Regular Season - 20 | 546 | Getafe | 532 | Valencia | 20422 | FT |
| 1391009 | 2026-01-18T15:15:00+00:00 | Regular Season - 20 | 530 | Atletico Madrid | 542 | Alaves |  | FT |
| 1391011 | 2026-01-18T17:30:00+00:00 | Regular Season - 20 | 538 | Celta Vigo | 728 | Rayo Vallecano |  | FT |
| 1391018 | 2026-01-18T20:00:00+00:00 | Regular Season - 20 | 548 | Real Sociedad | 529 | Barcelona |  | FT |
| 1391012 | 2026-01-19T20:00:00+00:00 | Regular Season - 20 | 797 | Elche | 536 | Sevilla | 1473 | FT |
| 1391023 | 2026-01-23T20:00:00+00:00 | Regular Season - 21 | 539 | Levante | 797 | Elche | 1482 | FT |
| 1391024 | 2026-01-24T13:00:00+00:00 | Regular Season - 21 | 728 | Rayo Vallecano | 727 | Osasuna | 1488 | FT |
| 1391027 | 2026-01-24T15:15:00+00:00 | Regular Season - 21 | 532 | Valencia | 540 | Espanyol | 1497 | FT |
| 1391026 | 2026-01-24T17:30:00+00:00 | Regular Season - 21 | 536 | Sevilla | 531 | Athletic Club | 1494 | FT |
| 1391028 | 2026-01-24T20:00:00+00:00 | Regular Season - 21 | 533 | Villarreal | 541 | Real Madrid | 1498 | FT |
| 1391020 | 2026-01-25T13:00:00+00:00 | Regular Season - 21 | 530 | Atletico Madrid | 798 | Mallorca |  | FT |
| 1391021 | 2026-01-25T15:15:00+00:00 | Regular Season - 21 | 529 | Barcelona | 718 | Oviedo | 19939 | FT |
| 1391025 | 2026-01-25T17:30:00+00:00 | Regular Season - 21 | 548 | Real Sociedad | 538 | Celta Vigo |  | FT |
| 1391019 | 2026-01-25T20:00:00+00:00 | Regular Season - 21 | 542 | Alaves | 543 | Real Betis | 1470 | FT |
| 1391022 | 2026-01-26T20:00:00+00:00 | Regular Season - 21 | 547 | Girona | 546 | Getafe | 1478 | FT |
| 1391032 | 2026-01-30T20:00:00+00:00 | Regular Season - 22 | 540 | Espanyol | 542 | Alaves |  | FT |
| 1391038 | 2026-01-31T13:00:00+00:00 | Regular Season - 22 | 718 | Oviedo | 547 | Girona | 1490 | FT |
| 1391036 | 2026-01-31T15:15:00+00:00 | Regular Season - 22 | 727 | Osasuna | 533 | Villarreal |  | FT |
| 1391034 | 2026-01-31T17:30:00+00:00 | Regular Season - 22 | 539 | Levante | 530 | Atletico Madrid | 1482 | FT |
| 1391031 | 2026-01-31T20:00:00+00:00 | Regular Season - 22 | 797 | Elche | 529 | Barcelona | 1473 | FT |
| 1391037 | 2026-02-01T13:00:00+00:00 | Regular Season - 22 | 541 | Real Madrid | 728 | Rayo Vallecano | 1456 | FT |
| 1391030 | 2026-02-01T15:15:00+00:00 | Regular Season - 22 | 543 | Real Betis | 532 | Valencia |  | FT |
| 1391033 | 2026-02-01T17:30:00+00:00 | Regular Season - 22 | 546 | Getafe | 538 | Celta Vigo | 20422 | FT |
| 1391029 | 2026-02-01T20:00:00+00:00 | Regular Season - 22 | 531 | Athletic Club | 548 | Real Sociedad |  | FT |
| 1391035 | 2026-02-02T20:00:00+00:00 | Regular Season - 22 | 798 | Mallorca | 536 | Sevilla | 19940 | FT |
| 1391043 | 2026-02-06T20:00:00+00:00 | Regular Season - 23 | 538 | Celta Vigo | 727 | Osasuna |  | FT |
| 1391042 | 2026-02-07T15:15:00+00:00 | Regular Season - 23 | 529 | Barcelona | 798 | Mallorca | 19939 | FT |
| 1391045 | 2026-02-07T20:00:00+00:00 | Regular Season - 23 | 548 | Real Sociedad | 797 | Elche |  | FT |
| 1391039 | 2026-02-08T13:00:00+00:00 | Regular Season - 23 | 542 | Alaves | 546 | Getafe | 1470 | FT |
| 1391040 | 2026-02-08T15:15:00+00:00 | Regular Season - 23 | 531 | Athletic Club | 539 | Levante |  | FT |
| 1391046 | 2026-02-08T15:15:00+00:00 | Regular Season - 23 | 536 | Sevilla | 547 | Girona | 1494 | FT |
| 1391041 | 2026-02-08T17:30:00+00:00 | Regular Season - 23 | 530 | Atletico Madrid | 543 | Real Betis |  | FT |
| 1391047 | 2026-02-08T20:00:00+00:00 | Regular Season - 23 | 532 | Valencia | 541 | Real Madrid | 1497 | FT |
| 1391048 | 2026-02-09T20:00:00+00:00 | Regular Season - 23 | 533 | Villarreal | 540 | Espanyol | 1498 | FT |
| 1391049 | 2026-02-13T20:00:00+00:00 | Regular Season - 24 | 797 | Elche | 727 | Osasuna | 1473 | FT |
| 1391050 | 2026-02-14T13:00:00+00:00 | Regular Season - 24 | 540 | Espanyol | 538 | Celta Vigo |  | FT |
| 1391051 | 2026-02-14T15:15:00+00:00 | Regular Season - 24 | 546 | Getafe | 533 | Villarreal | 20422 | FT |
| 1391058 | 2026-02-14T17:30:00+00:00 | Regular Season - 24 | 536 | Sevilla | 542 | Alaves | 1494 | FT |
| 1391056 | 2026-02-14T20:00:00+00:00 | Regular Season - 24 | 541 | Real Madrid | 548 | Real Sociedad | 1456 | FT |
| 1391057 | 2026-02-15T13:00:00+00:00 | Regular Season - 24 | 718 | Oviedo | 531 | Athletic Club | 1490 | FT |
| 1391055 | 2026-02-15T15:15:00+00:00 | Regular Season - 24 | 728 | Rayo Vallecano | 530 | Atletico Madrid | 1488 | FT |
| 1391053 | 2026-02-15T17:30:00+00:00 | Regular Season - 24 | 539 | Levante | 532 | Valencia | 1482 | FT |
| 1391054 | 2026-02-15T20:00:00+00:00 | Regular Season - 24 | 798 | Mallorca | 543 | Real Betis | 19940 | FT |
| 1391052 | 2026-02-16T20:00:00+00:00 | Regular Season - 24 | 547 | Girona | 529 | Barcelona | 1478 | FT |
| 1390974 | 2026-02-18T19:00:00+00:00 | Regular Season - 16 | 539 | Levante | 533 | Villarreal | 1482 | FT |
| 1391060 | 2026-02-20T20:00:00+00:00 | Regular Season - 25 | 531 | Athletic Club | 797 | Elche |  | FT |
| 1391067 | 2026-02-21T13:00:00+00:00 | Regular Season - 25 | 548 | Real Sociedad | 718 | Oviedo |  | FT |
| 1391063 | 2026-02-21T15:15:00+00:00 | Regular Season - 25 | 543 | Real Betis | 728 | Rayo Vallecano |  | FT |
| 1391066 | 2026-02-21T17:30:00+00:00 | Regular Season - 25 | 727 | Osasuna | 541 | Real Madrid |  | FT |
| 1391061 | 2026-02-21T20:00:00+00:00 | Regular Season - 25 | 530 | Atletico Madrid | 540 | Espanyol |  | FT |
| 1391065 | 2026-02-22T13:00:00+00:00 | Regular Season - 25 | 546 | Getafe | 536 | Sevilla | 20422 | FT |
| 1391062 | 2026-02-22T15:15:00+00:00 | Regular Season - 25 | 529 | Barcelona | 539 | Levante | 19939 | FT |
| 1391064 | 2026-02-22T17:30:00+00:00 | Regular Season - 25 | 538 | Celta Vigo | 798 | Mallorca |  | FT |
| 1391068 | 2026-02-22T20:00:00+00:00 | Regular Season - 25 | 533 | Villarreal | 532 | Valencia | 1498 | FT |
| 1391059 | 2026-02-23T20:00:00+00:00 | Regular Season - 25 | 542 | Alaves | 547 | Girona | 1470 | FT |
| 1391073 | 2026-02-27T20:00:00+00:00 | Regular Season - 26 | 539 | Levante | 542 | Alaves | 1482 | FT |
| 1391075 | 2026-02-28T13:00:00+00:00 | Regular Season - 26 | 728 | Rayo Vallecano | 531 | Athletic Club | 1488 | FT |
| 1391069 | 2026-02-28T15:15:00+00:00 | Regular Season - 26 | 529 | Barcelona | 533 | Villarreal | 19939 | FT |
| 1391074 | 2026-02-28T17:30:00+00:00 | Regular Season - 26 | 798 | Mallorca | 548 | Real Sociedad | 19940 | FT |
| 1391077 | 2026-02-28T20:00:00+00:00 | Regular Season - 26 | 718 | Oviedo | 530 | Atletico Madrid | 1490 | FT |
| 1391071 | 2026-03-01T13:00:00+00:00 | Regular Season - 26 | 797 | Elche | 540 | Espanyol | 1473 | FT |
| 1391078 | 2026-03-01T15:15:00+00:00 | Regular Season - 26 | 532 | Valencia | 727 | Osasuna | 1497 | FT |
| 1391070 | 2026-03-01T17:30:00+00:00 | Regular Season - 26 | 543 | Real Betis | 536 | Sevilla |  | FT |
| 1391072 | 2026-03-01T20:00:00+00:00 | Regular Season - 26 | 547 | Girona | 538 | Celta Vigo | 1478 | FT |
| 1391076 | 2026-03-02T20:00:00+00:00 | Regular Season - 26 | 541 | Real Madrid | 546 | Getafe | 1456 | FT |
| 1391044 | 2026-03-04T18:00:00+00:00 | Regular Season - 23 | 728 | Rayo Vallecano | 718 | Oviedo | 1488 | FT |
| 1391081 | 2026-03-06T20:00:00+00:00 | Regular Season - 27 | 538 | Celta Vigo | 541 | Real Madrid |  | FT |
| 1391085 | 2026-03-07T13:00:00+00:00 | Regular Season - 27 | 727 | Osasuna | 798 | Mallorca |  | FT |
| 1391084 | 2026-03-07T15:15:00+00:00 | Regular Season - 27 | 539 | Levante | 547 | Girona | 1482 | FT |
| 1391080 | 2026-03-07T17:30:00+00:00 | Regular Season - 27 | 530 | Atletico Madrid | 548 | Real Sociedad |  | FT |
| 1391079 | 2026-03-07T20:00:00+00:00 | Regular Season - 27 | 531 | Athletic Club | 529 | Barcelona |  | FT |
| 1391088 | 2026-03-08T13:00:00+00:00 | Regular Season - 27 | 533 | Villarreal | 797 | Elche | 1498 | FT |
| 1391083 | 2026-03-08T15:15:00+00:00 | Regular Season - 27 | 546 | Getafe | 543 | Real Betis | 20422 | FT |
| 1391086 | 2026-03-08T17:30:00+00:00 | Regular Season - 27 | 536 | Sevilla | 728 | Rayo Vallecano | 1494 | FT |
| 1391087 | 2026-03-08T20:00:00+00:00 | Regular Season - 27 | 532 | Valencia | 542 | Alaves | 1497 | FT |
| 1391082 | 2026-03-09T20:00:00+00:00 | Regular Season - 27 | 540 | Espanyol | 718 | Oviedo |  | FT |
| 1391089 | 2026-03-13T20:00:00+00:00 | Regular Season - 28 | 542 | Alaves | 533 | Villarreal | 1470 | FT |
| 1391093 | 2026-03-14T13:00:00+00:00 | Regular Season - 28 | 547 | Girona | 531 | Athletic Club | 1478 | FT |
| 1391090 | 2026-03-14T15:15:00+00:00 | Regular Season - 28 | 530 | Atletico Madrid | 546 | Getafe |  | FT |
| 1391098 | 2026-03-14T17:30:00+00:00 | Regular Season - 28 | 718 | Oviedo | 532 | Valencia | 1490 | FT |
| 1391096 | 2026-03-14T20:00:00+00:00 | Regular Season - 28 | 541 | Real Madrid | 797 | Elche | 1456 | FT |
| 1391094 | 2026-03-15T13:00:00+00:00 | Regular Season - 28 | 798 | Mallorca | 540 | Espanyol | 19940 | FT |
| 1391091 | 2026-03-15T15:15:00+00:00 | Regular Season - 28 | 529 | Barcelona | 536 | Sevilla | 19939 | FT |
| 1391092 | 2026-03-15T17:30:00+00:00 | Regular Season - 28 | 543 | Real Betis | 538 | Celta Vigo |  | FT |
| 1391097 | 2026-03-15T20:00:00+00:00 | Regular Season - 28 | 548 | Real Sociedad | 727 | Osasuna |  | FT |
| 1391095 | 2026-03-16T20:00:00+00:00 | Regular Season - 28 | 728 | Rayo Vallecano | 539 | Levante | 1488 | FT |
| 1391108 | 2026-03-20T20:00:00+00:00 | Regular Season - 29 | 533 | Villarreal | 548 | Real Sociedad | 1498 | FT |
| 1391102 | 2026-03-21T13:00:00+00:00 | Regular Season - 29 | 797 | Elche | 798 | Mallorca | 1473 | FT |
| 1391103 | 2026-03-21T15:15:00+00:00 | Regular Season - 29 | 540 | Espanyol | 546 | Getafe |  | FT |
| 1391104 | 2026-03-21T17:30:00+00:00 | Regular Season - 29 | 539 | Levante | 718 | Oviedo | 1482 | FT |
| 1391105 | 2026-03-21T17:30:00+00:00 | Regular Season - 29 | 727 | Osasuna | 547 | Girona |  | FT |
| 1391107 | 2026-03-21T20:00:00+00:00 | Regular Season - 29 | 536 | Sevilla | 532 | Valencia | 1494 | FT |
| 1391100 | 2026-03-22T13:00:00+00:00 | Regular Season - 29 | 529 | Barcelona | 728 | Rayo Vallecano | 19939 | FT |
| 1391101 | 2026-03-22T15:15:00+00:00 | Regular Season - 29 | 538 | Celta Vigo | 542 | Alaves |  | FT |
| 1391099 | 2026-03-22T17:30:00+00:00 | Regular Season - 29 | 531 | Athletic Club | 543 | Real Betis |  | FT |
| 1391106 | 2026-03-22T20:00:00+00:00 | Regular Season - 29 | 541 | Real Madrid | 530 | Atletico Madrid | 1456 | FT |
| 1391115 | 2026-04-03T19:00:00+00:00 | Regular Season - 30 | 728 | Rayo Vallecano | 797 | Elche | 1488 | FT |
| 1391116 | 2026-04-04T12:00:00+00:00 | Regular Season - 30 | 548 | Real Sociedad | 539 | Levante |  | FT |
| 1391114 | 2026-04-04T14:15:00+00:00 | Regular Season - 30 | 798 | Mallorca | 541 | Real Madrid | 19940 | FT |
| 1391111 | 2026-04-04T16:30:00+00:00 | Regular Season - 30 | 543 | Real Betis | 540 | Espanyol |  | FT |
| 1391110 | 2026-04-04T19:00:00+00:00 | Regular Season - 30 | 530 | Atletico Madrid | 529 | Barcelona |  | FT |
| 1391112 | 2026-04-05T12:00:00+00:00 | Regular Season - 30 | 546 | Getafe | 531 | Athletic Club | 20422 | FT |
| 1391118 | 2026-04-05T14:15:00+00:00 | Regular Season - 30 | 532 | Valencia | 538 | Celta Vigo | 1497 | FT |
| 1391117 | 2026-04-05T16:30:00+00:00 | Regular Season - 30 | 718 | Oviedo | 536 | Sevilla | 1490 | FT |
| 1391109 | 2026-04-05T19:00:00+00:00 | Regular Season - 30 | 542 | Alaves | 727 | Osasuna | 1470 | FT |
| 1391113 | 2026-04-06T19:00:00+00:00 | Regular Season - 30 | 547 | Girona | 533 | Villarreal | 1478 | FT |
| 1391126 | 2026-04-10T19:00:00+00:00 | Regular Season - 31 | 541 | Real Madrid | 547 | Girona | 1456 | FT |
| 1391127 | 2026-04-11T12:00:00+00:00 | Regular Season - 31 | 548 | Real Sociedad | 542 | Alaves |  | FT |
| 1391122 | 2026-04-11T14:15:00+00:00 | Regular Season - 31 | 797 | Elche | 532 | Valencia | 1473 | FT |
| 1391120 | 2026-04-11T16:30:00+00:00 | Regular Season - 31 | 529 | Barcelona | 540 | Espanyol | 19939 | FT |
| 1391128 | 2026-04-11T19:00:00+00:00 | Regular Season - 31 | 536 | Sevilla | 530 | Atletico Madrid | 1494 | FT |
| 1391125 | 2026-04-12T12:00:00+00:00 | Regular Season - 31 | 727 | Osasuna | 543 | Real Betis |  | FT |
| 1391124 | 2026-04-12T14:15:00+00:00 | Regular Season - 31 | 798 | Mallorca | 728 | Rayo Vallecano | 19940 | FT |
| 1391121 | 2026-04-12T16:30:00+00:00 | Regular Season - 31 | 538 | Celta Vigo | 718 | Oviedo |  | FT |
| 1391119 | 2026-04-12T19:00:00+00:00 | Regular Season - 31 | 531 | Athletic Club | 533 | Villarreal |  | FT |
| 1391123 | 2026-04-13T19:00:00+00:00 | Regular Season - 31 | 539 | Levante | 546 | Getafe | 1482 | FT |
| 1391139 | 2026-04-21T17:00:00+00:00 | Regular Season - 33 | 531 | Athletic Club | 727 | Osasuna |  | FT |
| 1391144 | 2026-04-21T17:00:00+00:00 | Regular Season - 33 | 798 | Mallorca | 532 | Valencia | 19940 | FT |
| 1391146 | 2026-04-21T19:30:00+00:00 | Regular Season - 33 | 541 | Real Madrid | 542 | Alaves | 1456 | FT |
| 1391142 | 2026-04-21T19:30:00+00:00 | Regular Season - 33 | 547 | Girona | 543 | Real Betis | 1478 | FT |
| 1391141 | 2026-04-22T17:00:00+00:00 | Regular Season - 33 | 797 | Elche | 530 | Atletico Madrid | 1473 | FT |
| 1391147 | 2026-04-22T18:00:00+00:00 | Regular Season - 33 | 548 | Real Sociedad | 546 | Getafe |  | FT |
| 1391140 | 2026-04-22T19:30:00+00:00 | Regular Season - 33 | 529 | Barcelona | 538 | Celta Vigo | 19939 | FT |
| 1391143 | 2026-04-23T17:00:00+00:00 | Regular Season - 33 | 539 | Levante | 536 | Sevilla | 1482 | FT |
| 1391145 | 2026-04-23T18:00:00+00:00 | Regular Season - 33 | 728 | Rayo Vallecano | 540 | Espanyol | 1488 | FT |
| 1391148 | 2026-04-23T19:30:00+00:00 | Regular Season - 33 | 718 | Oviedo | 533 | Villarreal | 1490 | FT |
| 1391131 | 2026-04-24T19:00:00+00:00 | Regular Season - 32 | 543 | Real Betis | 541 | Real Madrid |  | FT |
| 1391129 | 2026-04-25T12:00:00+00:00 | Regular Season - 32 | 542 | Alaves | 798 | Mallorca | 1470 | FT |
| 1391133 | 2026-04-25T14:15:00+00:00 | Regular Season - 32 | 546 | Getafe | 529 | Barcelona | 20422 | FT |
| 1391137 | 2026-04-25T16:30:00+00:00 | Regular Season - 32 | 532 | Valencia | 547 | Girona | 1497 | FT |
| 1391130 | 2026-04-25T19:00:00+00:00 | Regular Season - 32 | 530 | Atletico Madrid | 531 | Athletic Club |  | FT |
| 1391135 | 2026-04-26T12:00:00+00:00 | Regular Season - 32 | 728 | Rayo Vallecano | 548 | Real Sociedad | 1488 | FT |
| 1391136 | 2026-04-26T14:15:00+00:00 | Regular Season - 32 | 718 | Oviedo | 797 | Elche | 1490 | FT |
| 1391134 | 2026-04-26T16:30:00+00:00 | Regular Season - 32 | 727 | Osasuna | 536 | Sevilla |  | FT |
| 1391138 | 2026-04-26T19:00:00+00:00 | Regular Season - 32 | 533 | Villarreal | 538 | Celta Vigo | 1498 | FT |
| 1391132 | 2026-04-27T19:00:00+00:00 | Regular Season - 32 | 540 | Espanyol | 539 | Levante |  | FT |
| 1391154 | 2026-05-01T19:00:00+00:00 | Regular Season - 34 | 547 | Girona | 798 | Mallorca | 1478 | FT |
| 1391158 | 2026-05-02T12:00:00+00:00 | Regular Season - 34 | 533 | Villarreal | 539 | Levante | 1498 | NS |
| 1391157 | 2026-05-02T14:15:00+00:00 | Regular Season - 34 | 532 | Valencia | 530 | Atletico Madrid | 1497 | NS |
| 1391149 | 2026-05-02T16:30:00+00:00 | Regular Season - 34 | 542 | Alaves | 531 | Athletic Club | 1470 | NS |
| 1391155 | 2026-05-02T19:00:00+00:00 | Regular Season - 34 | 727 | Osasuna | 529 | Barcelona |  | NS |
| 1391151 | 2026-05-03T12:00:00+00:00 | Regular Season - 34 | 538 | Celta Vigo | 797 | Elche |  | NS |
| 1391153 | 2026-05-03T14:15:00+00:00 | Regular Season - 34 | 546 | Getafe | 728 | Rayo Vallecano |  | NS |
| 1391150 | 2026-05-03T16:30:00+00:00 | Regular Season - 34 | 543 | Real Betis | 718 | Oviedo |  | NS |
| 1391152 | 2026-05-03T19:00:00+00:00 | Regular Season - 34 | 540 | Espanyol | 541 | Real Madrid |  | NS |
| 1391156 | 2026-05-04T19:00:00+00:00 | Regular Season - 34 | 536 | Sevilla | 548 | Real Sociedad | 1494 | NS |
| 1391163 | 2026-05-08T19:00:00+00:00 | Regular Season - 35 | 539 | Levante | 727 | Osasuna | 1482 | NS |
| 1391162 | 2026-05-09T12:00:00+00:00 | Regular Season - 35 | 797 | Elche | 542 | Alaves | 1473 | NS |
| 1391168 | 2026-05-09T14:15:00+00:00 | Regular Season - 35 | 536 | Sevilla | 540 | Espanyol | 1494 | NS |
| 1391160 | 2026-05-09T16:30:00+00:00 | Regular Season - 35 | 530 | Atletico Madrid | 538 | Celta Vigo |  | NS |
| 1391166 | 2026-05-09T19:00:00+00:00 | Regular Season - 35 | 548 | Real Sociedad | 543 | Real Betis |  | NS |
| 1391164 | 2026-05-10T12:00:00+00:00 | Regular Season - 35 | 798 | Mallorca | 533 | Villarreal | 19940 | NS |
| 1391159 | 2026-05-10T14:15:00+00:00 | Regular Season - 35 | 531 | Athletic Club | 532 | Valencia |  | NS |
| 1391167 | 2026-05-10T16:30:00+00:00 | Regular Season - 35 | 718 | Oviedo | 546 | Getafe | 1490 | NS |
| 1391161 | 2026-05-10T19:00:00+00:00 | Regular Season - 35 | 529 | Barcelona | 541 | Real Madrid | 19939 | NS |
| 1391165 | 2026-05-11T19:00:00+00:00 | Regular Season - 35 | 728 | Rayo Vallecano | 547 | Girona |  | NS |
| 1391171 | 2026-05-12T17:00:00+00:00 | Regular Season - 36 | 538 | Celta Vigo | 539 | Levante |  | NS |
| 1391170 | 2026-05-12T18:00:00+00:00 | Regular Season - 36 | 543 | Real Betis | 797 | Elche |  | NS |
| 1391175 | 2026-05-12T19:30:00+00:00 | Regular Season - 36 | 727 | Osasuna | 530 | Atletico Madrid |  | NS |
| 1391178 | 2026-05-13T17:00:00+00:00 | Regular Season - 36 | 533 | Villarreal | 536 | Sevilla | 1498 | NS |
| 1391172 | 2026-05-13T17:00:00+00:00 | Regular Season - 36 | 540 | Espanyol | 531 | Athletic Club |  | NS |
| 1391169 | 2026-05-13T19:30:00+00:00 | Regular Season - 36 | 542 | Alaves | 529 | Barcelona |  | NS |
| 1391173 | 2026-05-13T19:30:00+00:00 | Regular Season - 36 | 546 | Getafe | 798 | Mallorca |  | NS |
| 1391177 | 2026-05-14T17:00:00+00:00 | Regular Season - 36 | 532 | Valencia | 728 | Rayo Vallecano | 1497 | NS |
| 1391174 | 2026-05-14T18:00:00+00:00 | Regular Season - 36 | 547 | Girona | 548 | Real Sociedad |  | NS |
| 1391176 | 2026-05-14T19:30:00+00:00 | Regular Season - 36 | 541 | Real Madrid | 718 | Oviedo | 1456 | NS |
| 1391181 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 529 | Barcelona | 543 | Real Betis | 19939 | NS |
| 1391180 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 530 | Atletico Madrid | 547 | Girona |  | NS |
| 1391179 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 531 | Athletic Club | 538 | Celta Vigo |  | NS |
| 1391188 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 536 | Sevilla | 541 | Real Madrid | 1494 | NS |
| 1391183 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 539 | Levante | 798 | Mallorca | 1482 | NS |
| 1391186 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 548 | Real Sociedad | 532 | Valencia |  | NS |
| 1391187 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 718 | Oviedo | 542 | Alaves | 1490 | NS |
| 1391184 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 727 | Osasuna | 540 | Espanyol |  | NS |
| 1391185 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 728 | Rayo Vallecano | 533 | Villarreal |  | NS |
| 1391182 | 2026-05-17T16:00:00+00:00 | Regular Season - 37 | 797 | Elche | 546 | Getafe | 1473 | NS |
| 1391197 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 532 | Valencia | 529 | Barcelona | 1497 | NS |
| 1391198 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 533 | Villarreal | 530 | Atletico Madrid | 1498 | NS |
| 1391191 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 538 | Celta Vigo | 536 | Sevilla |  | NS |
| 1391192 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 540 | Espanyol | 548 | Real Sociedad | 1474 | NS |
| 1391196 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 541 | Real Madrid | 531 | Athletic Club | 1456 | NS |
| 1391189 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 542 | Alaves | 728 | Rayo Vallecano | 1470 | NS |
| 1391190 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 543 | Real Betis | 539 | Levante |  | NS |
| 1391193 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 546 | Getafe | 727 | Osasuna | 20422 | NS |
| 1391194 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 547 | Girona | 797 | Elche | 1478 | NS |
| 1391195 | 2026-05-24T16:00:00+00:00 | Regular Season - 38 | 798 | Mallorca | 718 | Oviedo | 19940 | NS |


## Bundesliga

| Champ | Valeur |
| --- | --- |
| league_id | 78 |
| api_name | Bundesliga |
| country | Germany |
| type | League |
| season | 2025 |
| season_start | 2025-08-22 |
| season_end | 2026-05-16 |


### Coverage

```json
{
  "fixtures": {
    "events": true,
    "lineups": true,
    "statistics_fixtures": true,
    "statistics_players": true
  },
  "standings": true,
  "players": true,
  "top_scorers": true,
  "top_assists": true,
  "top_cards": true,
  "injuries": true,
  "predictions": true,
  "odds": true
}
```

### Teams et stades

| team_id | name | code | country | national | venue_id | venue | city | capacity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 180 | 1. FC Heidenheim | HEI | Germany | False | 723 | Voith-Arena | Heidenheim an der Brenz | 15000 |
| 192 | 1. FC Köln | KOL | Germany | False | 20736 | Cologne Stadium | Köln | 50076 |
| 167 | 1899 Hoffenheim | HOF | Germany | False | 724 | PreZero Arena | Sinsheim | 30164 |
| 168 | Bayer Leverkusen | BAY | Germany | False | 699 | BayArena | Leverkusen | 30210 |
| 157 | Bayern München | BAY | Germany | False | 20732 | Fußball Arena München | München | 75024 |
| 165 | Borussia Dortmund | DOR | Germany | False | 20733 | BVB Stadion Dortmund | Dortmund | 81365 |
| 163 | Borussia Mönchengladbach | MOE | Germany | False | 20471 | BORUSSIA-PARK | Mönchengladbach | 54057 |
| 169 | Eintracht Frankfurt | EIN | Germany | False | 20734 | Frankfurt Arena | Frankfurt am Main | 58000 |
| 170 | FC Augsburg | AUG | Germany | False | 698 | WWK Arena | Augsburg | 30662 |
| 186 | FC St. Pauli | PAU | Germany | False | 745 | Millerntor-Stadion | Hamburg | 29564 |
| 164 | FSV Mainz 05 | MAI | Germany | False | 11899 | MEWA ARENA | Mainz | 34034 |
| 175 | Hamburger SV | HAM | Germany | False | 720 | Volksparkstadion | Hamburg | 57030 |
| 173 | RB Leipzig | LEI | Germany | False | 20737 | Leipzig Stadium | Leipzig | 47069 |
| 160 | SC Freiburg | FRE | Germany | False | 12717 | Europa-Park Stadion | Freiburg im Breisgau | 34700 |
| 182 | Union Berlin | UNI | Germany | False | 748 | Stadion An der Alten Försterei | Berlin | 22467 |
| 172 | VfB Stuttgart | STU | Germany | False | 20739 | Stuttgart Arena | Stuttgart | 60469 |
| 161 | VfL Wolfsburg | WOL | Germany | False | 752 | Volkswagen Arena | Wolfsburg | 30000 |
| 162 | Werder Bremen | WER | Germany | False | 755 | wohninvest WESERSTADION | Bremen | 42358 |


### Rounds

- `Regular Season - 1`
- `Regular Season - 2`
- `Regular Season - 3`
- `Regular Season - 4`
- `Regular Season - 5`
- `Regular Season - 6`
- `Regular Season - 7`
- `Regular Season - 8`
- `Regular Season - 9`
- `Regular Season - 10`
- `Regular Season - 11`
- `Regular Season - 12`
- `Regular Season - 13`
- `Regular Season - 14`
- `Regular Season - 15`
- `Regular Season - 16`
- `Regular Season - 17`
- `Regular Season - 18`
- `Regular Season - 19`
- `Regular Season - 20`
- `Regular Season - 21`
- `Regular Season - 22`
- `Regular Season - 23`
- `Regular Season - 24`
- `Regular Season - 25`
- `Regular Season - 26`
- `Regular Season - 27`
- `Regular Season - 28`
- `Regular Season - 29`
- `Regular Season - 30`
- `Regular Season - 31`
- `Regular Season - 32`
- `Regular Season - 33`
- `Regular Season - 34`

### Standings

| rank | team_id | team | group | pts | played | W | D | L | GD | form |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 157 | Bayern München | Bundesliga  | 82 | 31 | 26 | 4 | 1 | 81 | WWWWW |
| 2 | 165 | Borussia Dortmund | Bundesliga  | 67 | 31 | 20 | 7 | 4 | 34 | WLLWW |
| 3 | 173 | RB Leipzig | Bundesliga  | 62 | 31 | 19 | 5 | 7 | 24 | WWWWW |
| 4 | 172 | VfB Stuttgart | Bundesliga  | 57 | 31 | 17 | 6 | 8 | 20 | DLWLW |
| 5 | 167 | 1899 Hoffenheim | Bundesliga  | 57 | 31 | 17 | 6 | 8 | 16 | WWDLL |
| 6 | 168 | Bayer Leverkusen | Bundesliga  | 55 | 31 | 16 | 7 | 8 | 20 | WLWWD |
| 7 | 169 | Eintracht Frankfurt | Bundesliga  | 43 | 31 | 11 | 10 | 10 | -2 | DLWDL |
| 8 | 160 | SC Freiburg | Bundesliga  | 43 | 31 | 12 | 7 | 12 | -8 | LWWLW |
| 9 | 170 | FC Augsburg | Bundesliga  | 37 | 31 | 10 | 7 | 14 | -16 | DWDDL |
| 10 | 164 | FSV Mainz 05 | Bundesliga  | 34 | 31 | 8 | 10 | 13 | -10 | LDLWW |
| 11 | 163 | Borussia Mönchengladbach | Bundesliga  | 32 | 31 | 7 | 11 | 13 | -14 | DDLDD |
| 12 | 162 | Werder Bremen | Bundesliga  | 32 | 31 | 8 | 8 | 15 | -18 | DWLLW |
| 13 | 182 | Union Berlin | Bundesliga  | 32 | 31 | 8 | 8 | 15 | -20 | LLLDL |
| 14 | 192 | 1. FC Köln | Bundesliga  | 31 | 31 | 7 | 10 | 14 | -8 | LDWDD |
| 15 | 175 | Hamburger SV | Bundesliga  | 31 | 31 | 7 | 10 | 14 | -16 | LLLDL |
| 16 | 186 | FC St. Pauli | Bundesliga  | 26 | 31 | 6 | 8 | 17 | -27 | LDLDL |
| 17 | 161 | VfL Wolfsburg | Bundesliga  | 25 | 31 | 6 | 7 | 18 | -25 | DWLLL |
| 18 | 180 | 1. FC Heidenheim | Bundesliga  | 22 | 31 | 5 | 7 | 19 | -31 | WLWDD |


### Fixtures

| fixture_id | date | round | home_id | home | away_id | away | venue_id | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1388308 | 2025-08-22T18:30:00+00:00 | Regular Season - 1 | 157 | Bayern München | 173 | RB Leipzig |  | FT |
| 1388312 | 2025-08-23T13:30:00+00:00 | Regular Season - 1 | 160 | SC Freiburg | 170 | FC Augsburg | 12717 | FT |
| 1388309 | 2025-08-23T13:30:00+00:00 | Regular Season - 1 | 168 | Bayer Leverkusen | 167 | 1899 Hoffenheim | 699 | FT |
| 1388311 | 2025-08-23T13:30:00+00:00 | Regular Season - 1 | 169 | Eintracht Frankfurt | 162 | Werder Bremen |  | FT |
| 1388313 | 2025-08-23T13:30:00+00:00 | Regular Season - 1 | 180 | 1. FC Heidenheim | 161 | VfL Wolfsburg | 723 | FT |
| 1388316 | 2025-08-23T13:30:00+00:00 | Regular Season - 1 | 182 | Union Berlin | 172 | VfB Stuttgart | 748 | FT |
| 1388315 | 2025-08-23T16:30:00+00:00 | Regular Season - 1 | 186 | FC St. Pauli | 165 | Borussia Dortmund | 745 | FT |
| 1388314 | 2025-08-24T13:30:00+00:00 | Regular Season - 1 | 164 | FSV Mainz 05 | 192 | 1. FC Köln | 11899 | FT |
| 1388310 | 2025-08-24T15:30:00+00:00 | Regular Season - 1 | 163 | Borussia Mönchengladbach | 175 | Hamburger SV | 20471 | FT |
| 1388320 | 2025-08-29T18:30:00+00:00 | Regular Season - 2 | 175 | Hamburger SV | 186 | FC St. Pauli | 720 | FT |
| 1388324 | 2025-08-30T13:30:00+00:00 | Regular Season - 2 | 162 | Werder Bremen | 168 | Bayer Leverkusen |  | FT |
| 1388321 | 2025-08-30T13:30:00+00:00 | Regular Season - 2 | 167 | 1899 Hoffenheim | 169 | Eintracht Frankfurt | 724 | FT |
| 1388323 | 2025-08-30T13:30:00+00:00 | Regular Season - 2 | 172 | VfB Stuttgart | 163 | Borussia Mönchengladbach |  | FT |
| 1388322 | 2025-08-30T13:30:00+00:00 | Regular Season - 2 | 173 | RB Leipzig | 180 | 1. FC Heidenheim |  | FT |
| 1388317 | 2025-08-30T16:30:00+00:00 | Regular Season - 2 | 170 | FC Augsburg | 157 | Bayern München | 698 | FT |
| 1388325 | 2025-08-31T13:30:00+00:00 | Regular Season - 2 | 161 | VfL Wolfsburg | 164 | FSV Mainz 05 | 752 | FT |
| 1388318 | 2025-08-31T15:30:00+00:00 | Regular Season - 2 | 165 | Borussia Dortmund | 182 | Union Berlin |  | FT |
| 1388319 | 2025-08-31T17:30:00+00:00 | Regular Season - 2 | 192 | 1. FC Köln | 160 | SC Freiburg |  | FT |
| 1388326 | 2025-09-12T18:30:00+00:00 | Regular Season - 3 | 168 | Bayer Leverkusen | 169 | Eintracht Frankfurt | 699 | FT |
| 1388329 | 2025-09-13T13:30:00+00:00 | Regular Season - 3 | 160 | SC Freiburg | 172 | VfB Stuttgart | 12717 | FT |
| 1388334 | 2025-09-13T13:30:00+00:00 | Regular Season - 3 | 161 | VfL Wolfsburg | 192 | 1. FC Köln | 752 | FT |
| 1388331 | 2025-09-13T13:30:00+00:00 | Regular Season - 3 | 164 | FSV Mainz 05 | 173 | RB Leipzig | 11899 | FT |
| 1388330 | 2025-09-13T13:30:00+00:00 | Regular Season - 3 | 180 | 1. FC Heidenheim | 165 | Borussia Dortmund | 723 | FT |
| 1388333 | 2025-09-13T13:30:00+00:00 | Regular Season - 3 | 182 | Union Berlin | 167 | 1899 Hoffenheim | 748 | FT |
| 1388327 | 2025-09-13T16:30:00+00:00 | Regular Season - 3 | 157 | Bayern München | 175 | Hamburger SV |  | FT |
| 1388332 | 2025-09-14T13:30:00+00:00 | Regular Season - 3 | 186 | FC St. Pauli | 170 | FC Augsburg | 745 | FT |
| 1388328 | 2025-09-14T15:30:00+00:00 | Regular Season - 3 | 163 | Borussia Mönchengladbach | 162 | Werder Bremen | 20471 | FT |
| 1388342 | 2025-09-19T18:30:00+00:00 | Regular Season - 4 | 172 | VfB Stuttgart | 186 | FC St. Pauli |  | FT |
| 1388343 | 2025-09-20T13:30:00+00:00 | Regular Season - 4 | 162 | Werder Bremen | 160 | SC Freiburg |  | FT |
| 1388340 | 2025-09-20T13:30:00+00:00 | Regular Season - 4 | 167 | 1899 Hoffenheim | 157 | Bayern München | 724 | FT |
| 1388335 | 2025-09-20T13:30:00+00:00 | Regular Season - 4 | 170 | FC Augsburg | 164 | FSV Mainz 05 | 698 | FT |
| 1388339 | 2025-09-20T13:30:00+00:00 | Regular Season - 4 | 175 | Hamburger SV | 180 | 1. FC Heidenheim | 720 | FT |
| 1388341 | 2025-09-20T16:30:00+00:00 | Regular Season - 4 | 173 | RB Leipzig | 192 | 1. FC Köln |  | FT |
| 1388338 | 2025-09-21T13:30:00+00:00 | Regular Season - 4 | 169 | Eintracht Frankfurt | 182 | Union Berlin |  | FT |
| 1388336 | 2025-09-21T15:30:00+00:00 | Regular Season - 4 | 168 | Bayer Leverkusen | 163 | Borussia Mönchengladbach | 699 | FT |
| 1388337 | 2025-09-21T17:30:00+00:00 | Regular Season - 4 | 165 | Borussia Dortmund | 161 | VfL Wolfsburg |  | FT |
| 1388344 | 2025-09-26T18:30:00+00:00 | Regular Season - 5 | 157 | Bayern München | 162 | Werder Bremen |  | FT |
| 1388352 | 2025-09-27T13:30:00+00:00 | Regular Season - 5 | 161 | VfL Wolfsburg | 173 | RB Leipzig | 752 | FT |
| 1388349 | 2025-09-27T13:30:00+00:00 | Regular Season - 5 | 164 | FSV Mainz 05 | 165 | Borussia Dortmund | 11899 | FT |
| 1388348 | 2025-09-27T13:30:00+00:00 | Regular Season - 5 | 180 | 1. FC Heidenheim | 170 | FC Augsburg | 723 | FT |
| 1388350 | 2025-09-27T13:30:00+00:00 | Regular Season - 5 | 186 | FC St. Pauli | 168 | Bayer Leverkusen | 745 | FT |
| 1388345 | 2025-09-27T16:30:00+00:00 | Regular Season - 5 | 163 | Borussia Mönchengladbach | 169 | Eintracht Frankfurt | 20471 | FT |
| 1388347 | 2025-09-28T13:30:00+00:00 | Regular Season - 5 | 160 | SC Freiburg | 167 | 1899 Hoffenheim | 12717 | FT |
| 1388346 | 2025-09-28T15:30:00+00:00 | Regular Season - 5 | 192 | 1. FC Köln | 172 | VfB Stuttgart |  | FT |
| 1388351 | 2025-09-28T17:30:00+00:00 | Regular Season - 5 | 182 | Union Berlin | 175 | Hamburger SV | 748 | FT |
| 1388359 | 2025-10-03T18:30:00+00:00 | Regular Season - 6 | 167 | 1899 Hoffenheim | 192 | 1. FC Köln | 724 | FT |
| 1388361 | 2025-10-04T13:30:00+00:00 | Regular Season - 6 | 162 | Werder Bremen | 186 | FC St. Pauli |  | FT |
| 1388356 | 2025-10-04T13:30:00+00:00 | Regular Season - 6 | 165 | Borussia Dortmund | 173 | RB Leipzig |  | FT |
| 1388354 | 2025-10-04T13:30:00+00:00 | Regular Season - 6 | 168 | Bayer Leverkusen | 182 | Union Berlin | 699 | FT |
| 1388353 | 2025-10-04T13:30:00+00:00 | Regular Season - 6 | 170 | FC Augsburg | 161 | VfL Wolfsburg | 698 | FT |
| 1388357 | 2025-10-04T16:30:00+00:00 | Regular Season - 6 | 169 | Eintracht Frankfurt | 157 | Bayern München |  | FT |
| 1388360 | 2025-10-05T13:30:00+00:00 | Regular Season - 6 | 172 | VfB Stuttgart | 180 | 1. FC Heidenheim |  | FT |
| 1388358 | 2025-10-05T15:30:00+00:00 | Regular Season - 6 | 175 | Hamburger SV | 164 | FSV Mainz 05 | 720 | FT |
| 1388355 | 2025-10-05T17:30:00+00:00 | Regular Season - 6 | 163 | Borussia Mönchengladbach | 160 | SC Freiburg | 20471 | FT |
| 1388369 | 2025-10-17T18:30:00+00:00 | Regular Season - 7 | 182 | Union Berlin | 163 | Borussia Mönchengladbach | 748 | FT |
| 1388370 | 2025-10-18T13:30:00+00:00 | Regular Season - 7 | 161 | VfL Wolfsburg | 172 | VfB Stuttgart | 752 | FT |
| 1388366 | 2025-10-18T13:30:00+00:00 | Regular Season - 7 | 164 | FSV Mainz 05 | 168 | Bayer Leverkusen | 11899 | FT |
| 1388367 | 2025-10-18T13:30:00+00:00 | Regular Season - 7 | 173 | RB Leipzig | 175 | Hamburger SV |  | FT |
| 1388365 | 2025-10-18T13:30:00+00:00 | Regular Season - 7 | 180 | 1. FC Heidenheim | 162 | Werder Bremen | 723 | FT |
| 1388363 | 2025-10-18T13:30:00+00:00 | Regular Season - 7 | 192 | 1. FC Köln | 170 | FC Augsburg |  | FT |
| 1388362 | 2025-10-18T16:30:00+00:00 | Regular Season - 7 | 157 | Bayern München | 165 | Borussia Dortmund |  | FT |
| 1388364 | 2025-10-19T13:30:00+00:00 | Regular Season - 7 | 160 | SC Freiburg | 169 | Eintracht Frankfurt | 12717 | FT |
| 1388368 | 2025-10-19T15:30:00+00:00 | Regular Season - 7 | 186 | FC St. Pauli | 167 | 1899 Hoffenheim | 745 | FT |
| 1388379 | 2025-10-24T18:30:00+00:00 | Regular Season - 8 | 162 | Werder Bremen | 182 | Union Berlin |  | FT |
| 1388373 | 2025-10-25T13:30:00+00:00 | Regular Season - 8 | 163 | Borussia Mönchengladbach | 157 | Bayern München | 20471 | FT |
| 1388377 | 2025-10-25T13:30:00+00:00 | Regular Season - 8 | 167 | 1899 Hoffenheim | 180 | 1. FC Heidenheim | 724 | FT |
| 1388375 | 2025-10-25T13:30:00+00:00 | Regular Season - 8 | 169 | Eintracht Frankfurt | 186 | FC St. Pauli |  | FT |
| 1388371 | 2025-10-25T13:30:00+00:00 | Regular Season - 8 | 170 | FC Augsburg | 173 | RB Leipzig | 698 | FT |
| 1388376 | 2025-10-25T13:30:00+00:00 | Regular Season - 8 | 175 | Hamburger SV | 161 | VfL Wolfsburg | 720 | FT |
| 1388374 | 2025-10-25T16:30:00+00:00 | Regular Season - 8 | 165 | Borussia Dortmund | 192 | 1. FC Köln |  | FT |
| 1388372 | 2025-10-26T14:30:00+00:00 | Regular Season - 8 | 168 | Bayer Leverkusen | 160 | SC Freiburg | 699 | FT |
| 1388378 | 2025-10-26T16:30:00+00:00 | Regular Season - 8 | 172 | VfB Stuttgart | 164 | FSV Mainz 05 |  | FT |
| 1388380 | 2025-10-31T19:30:00+00:00 | Regular Season - 9 | 170 | FC Augsburg | 165 | Borussia Dortmund | 698 | FT |
| 1388384 | 2025-11-01T14:30:00+00:00 | Regular Season - 9 | 164 | FSV Mainz 05 | 162 | Werder Bremen | 11899 | FT |
| 1388385 | 2025-11-01T14:30:00+00:00 | Regular Season - 9 | 173 | RB Leipzig | 172 | VfB Stuttgart |  | FT |
| 1388383 | 2025-11-01T14:30:00+00:00 | Regular Season - 9 | 180 | 1. FC Heidenheim | 169 | Eintracht Frankfurt | 723 | FT |
| 1388387 | 2025-11-01T14:30:00+00:00 | Regular Season - 9 | 182 | Union Berlin | 160 | SC Freiburg | 748 | FT |
| 1388386 | 2025-11-01T14:30:00+00:00 | Regular Season - 9 | 186 | FC St. Pauli | 163 | Borussia Mönchengladbach | 745 | FT |
| 1388381 | 2025-11-01T17:30:00+00:00 | Regular Season - 9 | 157 | Bayern München | 168 | Bayer Leverkusen |  | FT |
| 1388382 | 2025-11-02T14:30:00+00:00 | Regular Season - 9 | 192 | 1. FC Köln | 175 | Hamburger SV |  | FT |
| 1388388 | 2025-11-02T16:30:00+00:00 | Regular Season - 9 | 161 | VfL Wolfsburg | 167 | 1899 Hoffenheim | 752 | FT |
| 1388397 | 2025-11-07T19:30:00+00:00 | Regular Season - 10 | 162 | Werder Bremen | 161 | VfL Wolfsburg |  | FT |
| 1388394 | 2025-11-08T14:30:00+00:00 | Regular Season - 10 | 167 | 1899 Hoffenheim | 173 | RB Leipzig | 724 | FT |
| 1388389 | 2025-11-08T14:30:00+00:00 | Regular Season - 10 | 168 | Bayer Leverkusen | 180 | 1. FC Heidenheim | 699 | FT |
| 1388393 | 2025-11-08T14:30:00+00:00 | Regular Season - 10 | 175 | Hamburger SV | 165 | Borussia Dortmund | 720 | FT |
| 1388396 | 2025-11-08T14:30:00+00:00 | Regular Season - 10 | 182 | Union Berlin | 157 | Bayern München | 748 | FT |
| 1388390 | 2025-11-08T17:30:00+00:00 | Regular Season - 10 | 163 | Borussia Mönchengladbach | 192 | 1. FC Köln | 20471 | FT |
| 1388392 | 2025-11-09T14:30:00+00:00 | Regular Season - 10 | 160 | SC Freiburg | 186 | FC St. Pauli | 12717 | FT |
| 1388395 | 2025-11-09T16:30:00+00:00 | Regular Season - 10 | 172 | VfB Stuttgart | 170 | FC Augsburg |  | FT |
| 1388391 | 2025-11-09T18:30:00+00:00 | Regular Season - 10 | 169 | Eintracht Frankfurt | 164 | FSV Mainz 05 |  | FT |
| 1388403 | 2025-11-21T19:30:00+00:00 | Regular Season - 11 | 164 | FSV Mainz 05 | 167 | 1899 Hoffenheim | 11899 | FT |
| 1388399 | 2025-11-22T14:30:00+00:00 | Regular Season - 11 | 157 | Bayern München | 160 | SC Freiburg |  | FT |
| 1388406 | 2025-11-22T14:30:00+00:00 | Regular Season - 11 | 161 | VfL Wolfsburg | 168 | Bayer Leverkusen | 752 | FT |
| 1388400 | 2025-11-22T14:30:00+00:00 | Regular Season - 11 | 165 | Borussia Dortmund | 172 | VfB Stuttgart |  | FT |
| 1388398 | 2025-11-22T14:30:00+00:00 | Regular Season - 11 | 170 | FC Augsburg | 175 | Hamburger SV | 698 | FT |
| 1388402 | 2025-11-22T14:30:00+00:00 | Regular Season - 11 | 180 | 1. FC Heidenheim | 163 | Borussia Mönchengladbach | 723 | FT |
| 1388401 | 2025-11-22T17:30:00+00:00 | Regular Season - 11 | 192 | 1. FC Köln | 169 | Eintracht Frankfurt |  | FT |
| 1388404 | 2025-11-23T14:30:00+00:00 | Regular Season - 11 | 173 | RB Leipzig | 162 | Werder Bremen |  | FT |
| 1388405 | 2025-11-23T16:30:00+00:00 | Regular Season - 11 | 186 | FC St. Pauli | 182 | Union Berlin | 745 | FT |
| 1388409 | 2025-11-28T19:30:00+00:00 | Regular Season - 12 | 163 | Borussia Mönchengladbach | 173 | RB Leipzig | 20471 | FT |
| 1388408 | 2025-11-29T14:30:00+00:00 | Regular Season - 12 | 157 | Bayern München | 186 | FC St. Pauli |  | FT |
| 1388415 | 2025-11-29T14:30:00+00:00 | Regular Season - 12 | 162 | Werder Bremen | 192 | 1. FC Köln |  | FT |
| 1388413 | 2025-11-29T14:30:00+00:00 | Regular Season - 12 | 167 | 1899 Hoffenheim | 170 | FC Augsburg | 724 | FT |
| 1388414 | 2025-11-29T14:30:00+00:00 | Regular Season - 12 | 182 | Union Berlin | 180 | 1. FC Heidenheim | 748 | FT |
| 1388407 | 2025-11-29T17:30:00+00:00 | Regular Season - 12 | 168 | Bayer Leverkusen | 165 | Borussia Dortmund | 699 | FT |
| 1388412 | 2025-11-30T14:30:00+00:00 | Regular Season - 12 | 175 | Hamburger SV | 172 | VfB Stuttgart | 720 | FT |
| 1388410 | 2025-11-30T16:30:00+00:00 | Regular Season - 12 | 169 | Eintracht Frankfurt | 161 | VfL Wolfsburg |  | FT |
| 1388411 | 2025-11-30T18:30:00+00:00 | Regular Season - 12 | 160 | SC Freiburg | 164 | FSV Mainz 05 | 12717 | FT |
| 1388421 | 2025-12-05T19:30:00+00:00 | Regular Season - 13 | 164 | FSV Mainz 05 | 163 | Borussia Mönchengladbach | 11899 | FT |
| 1388424 | 2025-12-06T14:30:00+00:00 | Regular Season - 13 | 161 | VfL Wolfsburg | 182 | Union Berlin | 752 | FT |
| 1388416 | 2025-12-06T14:30:00+00:00 | Regular Season - 13 | 170 | FC Augsburg | 168 | Bayer Leverkusen | 698 | FT |
| 1388423 | 2025-12-06T14:30:00+00:00 | Regular Season - 13 | 172 | VfB Stuttgart | 157 | Bayern München |  | FT |
| 1388420 | 2025-12-06T14:30:00+00:00 | Regular Season - 13 | 180 | 1. FC Heidenheim | 160 | SC Freiburg | 723 | FT |
| 1388418 | 2025-12-06T14:30:00+00:00 | Regular Season - 13 | 192 | 1. FC Köln | 186 | FC St. Pauli |  | FT |
| 1388422 | 2025-12-06T17:30:00+00:00 | Regular Season - 13 | 173 | RB Leipzig | 169 | Eintracht Frankfurt |  | FT |
| 1388419 | 2025-12-07T14:30:00+00:00 | Regular Season - 13 | 175 | Hamburger SV | 162 | Werder Bremen | 720 | FT |
| 1388417 | 2025-12-07T16:30:00+00:00 | Regular Season - 13 | 165 | Borussia Dortmund | 167 | 1899 Hoffenheim |  | FT |
| 1388432 | 2025-12-12T19:30:00+00:00 | Regular Season - 14 | 182 | Union Berlin | 173 | RB Leipzig | 748 | FT |
| 1388427 | 2025-12-13T14:30:00+00:00 | Regular Season - 14 | 163 | Borussia Mönchengladbach | 161 | VfL Wolfsburg | 20471 | FT |
| 1388430 | 2025-12-13T14:30:00+00:00 | Regular Season - 14 | 167 | 1899 Hoffenheim | 175 | Hamburger SV | 724 | FT |
| 1388428 | 2025-12-13T14:30:00+00:00 | Regular Season - 14 | 169 | Eintracht Frankfurt | 170 | FC Augsburg |  | FT |
| 1388431 | 2025-12-13T14:30:00+00:00 | Regular Season - 14 | 186 | FC St. Pauli | 180 | 1. FC Heidenheim | 745 | FT |
| 1388425 | 2025-12-13T17:30:00+00:00 | Regular Season - 14 | 168 | Bayer Leverkusen | 192 | 1. FC Köln | 699 | FT |
| 1388429 | 2025-12-14T14:30:00+00:00 | Regular Season - 14 | 160 | SC Freiburg | 165 | Borussia Dortmund | 12717 | FT |
| 1388426 | 2025-12-14T16:30:00+00:00 | Regular Season - 14 | 157 | Bayern München | 164 | FSV Mainz 05 |  | FT |
| 1388433 | 2025-12-14T18:30:00+00:00 | Regular Season - 14 | 162 | Werder Bremen | 172 | VfB Stuttgart |  | FT |
| 1388435 | 2025-12-19T19:30:00+00:00 | Regular Season - 15 | 165 | Borussia Dortmund | 163 | Borussia Mönchengladbach |  | FT |
| 1388442 | 2025-12-20T14:30:00+00:00 | Regular Season - 15 | 161 | VfL Wolfsburg | 160 | SC Freiburg | 752 | FT |
| 1388434 | 2025-12-20T14:30:00+00:00 | Regular Season - 15 | 170 | FC Augsburg | 162 | Werder Bremen | 698 | FT |
| 1388441 | 2025-12-20T14:30:00+00:00 | Regular Season - 15 | 172 | VfB Stuttgart | 167 | 1899 Hoffenheim |  | FT |
| 1388437 | 2025-12-20T14:30:00+00:00 | Regular Season - 15 | 175 | Hamburger SV | 169 | Eintracht Frankfurt | 720 | FT |
| 1388436 | 2025-12-20T14:30:00+00:00 | Regular Season - 15 | 192 | 1. FC Köln | 182 | Union Berlin |  | FT |
| 1388440 | 2025-12-20T17:30:00+00:00 | Regular Season - 15 | 173 | RB Leipzig | 168 | Bayer Leverkusen |  | FT |
| 1388439 | 2025-12-21T14:30:00+00:00 | Regular Season - 15 | 164 | FSV Mainz 05 | 186 | FC St. Pauli | 11899 | FT |
| 1388438 | 2025-12-21T16:30:00+00:00 | Regular Season - 15 | 180 | 1. FC Heidenheim | 157 | Bayern München | 723 | FT |
| 1388446 | 2026-01-09T19:30:00+00:00 | Regular Season - 16 | 169 | Eintracht Frankfurt | 165 | Borussia Dortmund |  | FT |
| 1388447 | 2026-01-10T14:30:00+00:00 | Regular Season - 16 | 160 | SC Freiburg | 175 | Hamburger SV | 12717 | FT |
| 1388448 | 2026-01-10T14:30:00+00:00 | Regular Season - 16 | 180 | 1. FC Heidenheim | 192 | 1. FC Köln | 723 | FT |
| 1388450 | 2026-01-10T14:30:00+00:00 | Regular Season - 16 | 182 | Union Berlin | 164 | FSV Mainz 05 | 748 | FT |
| 1388443 | 2026-01-10T17:30:00+00:00 | Regular Season - 16 | 168 | Bayer Leverkusen | 172 | VfB Stuttgart | 699 | FT |
| 1388445 | 2026-01-11T14:30:00+00:00 | Regular Season - 16 | 163 | Borussia Mönchengladbach | 170 | FC Augsburg | 20471 | FT |
| 1388444 | 2026-01-11T16:30:00+00:00 | Regular Season - 16 | 157 | Bayern München | 161 | VfL Wolfsburg |  | FT |
| 1388459 | 2026-01-13T17:30:00+00:00 | Regular Season - 17 | 172 | VfB Stuttgart | 169 | Eintracht Frankfurt |  | FT |
| 1388457 | 2026-01-13T19:30:00+00:00 | Regular Season - 17 | 164 | FSV Mainz 05 | 180 | 1. FC Heidenheim | 11899 | FT |
| 1388453 | 2026-01-13T19:30:00+00:00 | Regular Season - 17 | 165 | Borussia Dortmund | 162 | Werder Bremen |  | FT |
| 1388460 | 2026-01-14T17:30:00+00:00 | Regular Season - 17 | 161 | VfL Wolfsburg | 186 | FC St. Pauli | 752 | FT |
| 1388456 | 2026-01-14T19:30:00+00:00 | Regular Season - 17 | 167 | 1899 Hoffenheim | 163 | Borussia Mönchengladbach | 724 | FT |
| 1388458 | 2026-01-14T19:30:00+00:00 | Regular Season - 17 | 173 | RB Leipzig | 160 | SC Freiburg |  | FT |
| 1388454 | 2026-01-14T19:30:00+00:00 | Regular Season - 17 | 192 | 1. FC Köln | 157 | Bayern München |  | FT |
| 1388452 | 2026-01-15T19:30:00+00:00 | Regular Season - 17 | 170 | FC Augsburg | 182 | Union Berlin | 698 | FT |
| 1388468 | 2026-01-16T19:30:00+00:00 | Regular Season - 18 | 162 | Werder Bremen | 169 | Eintracht Frankfurt |  | FT |
| 1388469 | 2026-01-17T14:30:00+00:00 | Regular Season - 18 | 161 | VfL Wolfsburg | 180 | 1. FC Heidenheim | 752 | FT |
| 1388462 | 2026-01-17T14:30:00+00:00 | Regular Season - 18 | 165 | Borussia Dortmund | 186 | FC St. Pauli |  | FT |
| 1388465 | 2026-01-17T14:30:00+00:00 | Regular Season - 18 | 167 | 1899 Hoffenheim | 168 | Bayer Leverkusen | 724 | FT |
| 1388464 | 2026-01-17T14:30:00+00:00 | Regular Season - 18 | 175 | Hamburger SV | 163 | Borussia Mönchengladbach | 720 | FT |
| 1388463 | 2026-01-17T14:30:00+00:00 | Regular Season - 18 | 192 | 1. FC Köln | 164 | FSV Mainz 05 |  | FT |
| 1388466 | 2026-01-17T17:30:00+00:00 | Regular Season - 18 | 173 | RB Leipzig | 157 | Bayern München |  | FT |
| 1388467 | 2026-01-18T14:30:00+00:00 | Regular Season - 18 | 172 | VfB Stuttgart | 182 | Union Berlin |  | FT |
| 1388461 | 2026-01-18T16:30:00+00:00 | Regular Season - 18 | 170 | FC Augsburg | 160 | SC Freiburg | 698 | FT |
| 1388477 | 2026-01-23T19:30:00+00:00 | Regular Season - 19 | 186 | FC St. Pauli | 175 | Hamburger SV | 745 | FT |
| 1388471 | 2026-01-24T14:30:00+00:00 | Regular Season - 19 | 157 | Bayern München | 170 | FC Augsburg |  | FT |
| 1388476 | 2026-01-24T14:30:00+00:00 | Regular Season - 19 | 164 | FSV Mainz 05 | 161 | VfL Wolfsburg | 11899 | FT |
| 1388470 | 2026-01-24T14:30:00+00:00 | Regular Season - 19 | 168 | Bayer Leverkusen | 162 | Werder Bremen | 699 | FT |
| 1388473 | 2026-01-24T14:30:00+00:00 | Regular Season - 19 | 169 | Eintracht Frankfurt | 167 | 1899 Hoffenheim |  | FT |
| 1388475 | 2026-01-24T14:30:00+00:00 | Regular Season - 19 | 180 | 1. FC Heidenheim | 173 | RB Leipzig | 723 | FT |
| 1388478 | 2026-01-24T17:30:00+00:00 | Regular Season - 19 | 182 | Union Berlin | 165 | Borussia Dortmund | 748 | FT |
| 1388472 | 2026-01-25T14:30:00+00:00 | Regular Season - 19 | 163 | Borussia Mönchengladbach | 172 | VfB Stuttgart | 20471 | FT |
| 1388474 | 2026-01-25T16:30:00+00:00 | Regular Season - 19 | 160 | SC Freiburg | 192 | 1. FC Köln | 12717 | FT |
| 1388451 | 2026-01-27T19:30:00+00:00 | Regular Season - 16 | 162 | Werder Bremen | 167 | 1899 Hoffenheim |  | FT |
| 1388449 | 2026-01-27T19:30:00+00:00 | Regular Season - 16 | 186 | FC St. Pauli | 173 | RB Leipzig | 745 | FT |
| 1388482 | 2026-01-30T19:30:00+00:00 | Regular Season - 20 | 192 | 1. FC Köln | 161 | VfL Wolfsburg |  | FT |
| 1388487 | 2026-01-31T14:30:00+00:00 | Regular Season - 20 | 162 | Werder Bremen | 163 | Borussia Mönchengladbach |  | FT |
| 1388484 | 2026-01-31T14:30:00+00:00 | Regular Season - 20 | 167 | 1899 Hoffenheim | 182 | Union Berlin | 724 | FT |
| 1388481 | 2026-01-31T14:30:00+00:00 | Regular Season - 20 | 169 | Eintracht Frankfurt | 168 | Bayer Leverkusen |  | FT |
| 1388479 | 2026-01-31T14:30:00+00:00 | Regular Season - 20 | 170 | FC Augsburg | 186 | FC St. Pauli | 698 | FT |
| 1388485 | 2026-01-31T14:30:00+00:00 | Regular Season - 20 | 173 | RB Leipzig | 164 | FSV Mainz 05 |  | FT |
| 1388483 | 2026-01-31T17:30:00+00:00 | Regular Season - 20 | 175 | Hamburger SV | 157 | Bayern München | 720 | FT |
| 1388486 | 2026-02-01T14:30:00+00:00 | Regular Season - 20 | 172 | VfB Stuttgart | 160 | SC Freiburg |  | FT |
| 1388480 | 2026-02-01T16:30:00+00:00 | Regular Season - 20 | 165 | Borussia Dortmund | 180 | 1. FC Heidenheim |  | FT |
| 1388495 | 2026-02-06T19:30:00+00:00 | Regular Season - 21 | 182 | Union Berlin | 169 | Eintracht Frankfurt | 748 | FT |
| 1388491 | 2026-02-07T14:30:00+00:00 | Regular Season - 21 | 160 | SC Freiburg | 162 | Werder Bremen | 12717 | FT |
| 1388496 | 2026-02-07T14:30:00+00:00 | Regular Season - 21 | 161 | VfL Wolfsburg | 165 | Borussia Dortmund | 752 | FT |
| 1388493 | 2026-02-07T14:30:00+00:00 | Regular Season - 21 | 164 | FSV Mainz 05 | 170 | FC Augsburg | 11899 | FT |
| 1388492 | 2026-02-07T14:30:00+00:00 | Regular Season - 21 | 180 | 1. FC Heidenheim | 175 | Hamburger SV | 723 | FT |
| 1388494 | 2026-02-07T14:30:00+00:00 | Regular Season - 21 | 186 | FC St. Pauli | 172 | VfB Stuttgart | 745 | FT |
| 1388489 | 2026-02-07T17:30:00+00:00 | Regular Season - 21 | 163 | Borussia Mönchengladbach | 168 | Bayer Leverkusen | 20471 | FT |
| 1388490 | 2026-02-08T14:30:00+00:00 | Regular Season - 21 | 192 | 1. FC Köln | 173 | RB Leipzig |  | FT |
| 1388488 | 2026-02-08T16:30:00+00:00 | Regular Season - 21 | 157 | Bayern München | 167 | 1899 Hoffenheim |  | FT |
| 1388499 | 2026-02-13T19:30:00+00:00 | Regular Season - 22 | 165 | Borussia Dortmund | 164 | FSV Mainz 05 |  | FT |
| 1388505 | 2026-02-14T14:30:00+00:00 | Regular Season - 22 | 162 | Werder Bremen | 157 | Bayern München |  | FT |
| 1388502 | 2026-02-14T14:30:00+00:00 | Regular Season - 22 | 167 | 1899 Hoffenheim | 160 | SC Freiburg | 724 | FT |
| 1388498 | 2026-02-14T14:30:00+00:00 | Regular Season - 22 | 168 | Bayer Leverkusen | 186 | FC St. Pauli | 699 | FT |
| 1388500 | 2026-02-14T14:30:00+00:00 | Regular Season - 22 | 169 | Eintracht Frankfurt | 163 | Borussia Mönchengladbach |  | FT |
| 1388501 | 2026-02-14T14:30:00+00:00 | Regular Season - 22 | 175 | Hamburger SV | 182 | Union Berlin | 720 | FT |
| 1388504 | 2026-02-14T17:30:00+00:00 | Regular Season - 22 | 172 | VfB Stuttgart | 192 | 1. FC Köln |  | FT |
| 1388497 | 2026-02-15T14:30:00+00:00 | Regular Season - 22 | 170 | FC Augsburg | 180 | 1. FC Heidenheim | 698 | FT |
| 1388503 | 2026-02-15T16:30:00+00:00 | Regular Season - 22 | 173 | RB Leipzig | 161 | VfL Wolfsburg |  | FT |
| 1388510 | 2026-02-20T19:30:00+00:00 | Regular Season - 23 | 164 | FSV Mainz 05 | 175 | Hamburger SV | 11899 | FT |
| 1388506 | 2026-02-21T14:30:00+00:00 | Regular Season - 23 | 157 | Bayern München | 169 | Eintracht Frankfurt |  | FT |
| 1388514 | 2026-02-21T14:30:00+00:00 | Regular Season - 23 | 161 | VfL Wolfsburg | 170 | FC Augsburg | 752 | FT |
| 1388513 | 2026-02-21T14:30:00+00:00 | Regular Season - 23 | 182 | Union Berlin | 168 | Bayer Leverkusen | 748 | FT |
| 1388507 | 2026-02-21T14:30:00+00:00 | Regular Season - 23 | 192 | 1. FC Köln | 167 | 1899 Hoffenheim |  | FT |
| 1388511 | 2026-02-21T17:30:00+00:00 | Regular Season - 23 | 173 | RB Leipzig | 165 | Borussia Dortmund |  | FT |
| 1388508 | 2026-02-22T14:30:00+00:00 | Regular Season - 23 | 160 | SC Freiburg | 163 | Borussia Mönchengladbach | 12717 | FT |
| 1388512 | 2026-02-22T16:30:00+00:00 | Regular Season - 23 | 186 | FC St. Pauli | 162 | Werder Bremen | 745 | FT |
| 1388509 | 2026-02-22T18:30:00+00:00 | Regular Season - 23 | 180 | 1. FC Heidenheim | 172 | VfB Stuttgart | 723 | FT |
| 1388515 | 2026-02-27T19:30:00+00:00 | Regular Season - 24 | 170 | FC Augsburg | 192 | 1. FC Köln | 698 | FT |
| 1388523 | 2026-02-28T14:30:00+00:00 | Regular Season - 24 | 162 | Werder Bremen | 180 | 1. FC Heidenheim |  | FT |
| 1388517 | 2026-02-28T14:30:00+00:00 | Regular Season - 24 | 163 | Borussia Mönchengladbach | 182 | Union Berlin | 20471 | FT |
| 1388521 | 2026-02-28T14:30:00+00:00 | Regular Season - 24 | 167 | 1899 Hoffenheim | 186 | FC St. Pauli | 724 | FT |
| 1388516 | 2026-02-28T14:30:00+00:00 | Regular Season - 24 | 168 | Bayer Leverkusen | 164 | FSV Mainz 05 | 699 | FT |
| 1388518 | 2026-02-28T17:30:00+00:00 | Regular Season - 24 | 165 | Borussia Dortmund | 157 | Bayern München |  | FT |
| 1388522 | 2026-03-01T14:30:00+00:00 | Regular Season - 24 | 172 | VfB Stuttgart | 161 | VfL Wolfsburg |  | FT |
| 1388519 | 2026-03-01T16:30:00+00:00 | Regular Season - 24 | 169 | Eintracht Frankfurt | 160 | SC Freiburg |  | FT |
| 1388520 | 2026-03-01T18:30:00+00:00 | Regular Season - 24 | 175 | Hamburger SV | 173 | RB Leipzig | 720 | FT |
| 1388455 | 2026-03-04T19:30:00+00:00 | Regular Season - 17 | 175 | Hamburger SV | 168 | Bayer Leverkusen | 720 | FT |
| 1388524 | 2026-03-06T19:30:00+00:00 | Regular Season - 25 | 157 | Bayern München | 163 | Borussia Mönchengladbach |  | FT |
| 1388526 | 2026-03-07T14:30:00+00:00 | Regular Season - 25 | 160 | SC Freiburg | 168 | Bayer Leverkusen | 12717 | FT |
| 1388532 | 2026-03-07T14:30:00+00:00 | Regular Season - 25 | 161 | VfL Wolfsburg | 175 | Hamburger SV | 752 | FT |
| 1388528 | 2026-03-07T14:30:00+00:00 | Regular Season - 25 | 164 | FSV Mainz 05 | 172 | VfB Stuttgart | 11899 | FT |
| 1388529 | 2026-03-07T14:30:00+00:00 | Regular Season - 25 | 173 | RB Leipzig | 170 | FC Augsburg |  | FT |
| 1388527 | 2026-03-07T14:30:00+00:00 | Regular Season - 25 | 180 | 1. FC Heidenheim | 167 | 1899 Hoffenheim | 723 | FT |
| 1388525 | 2026-03-07T17:30:00+00:00 | Regular Season - 25 | 192 | 1. FC Köln | 165 | Borussia Dortmund |  | FT |
| 1388530 | 2026-03-08T14:30:00+00:00 | Regular Season - 25 | 186 | FC St. Pauli | 169 | Eintracht Frankfurt | 745 | FT |
| 1388531 | 2026-03-08T16:30:00+00:00 | Regular Season - 25 | 182 | Union Berlin | 162 | Werder Bremen | 748 | FT |
| 1388534 | 2026-03-13T19:30:00+00:00 | Regular Season - 26 | 163 | Borussia Mönchengladbach | 186 | FC St. Pauli | 20471 | FT |
| 1388535 | 2026-03-14T14:30:00+00:00 | Regular Season - 26 | 165 | Borussia Dortmund | 170 | FC Augsburg |  | FT |
| 1388539 | 2026-03-14T14:30:00+00:00 | Regular Season - 26 | 167 | 1899 Hoffenheim | 161 | VfL Wolfsburg | 724 | FT |
| 1388533 | 2026-03-14T14:30:00+00:00 | Regular Season - 26 | 168 | Bayer Leverkusen | 157 | Bayern München | 699 | FT |
| 1388536 | 2026-03-14T14:30:00+00:00 | Regular Season - 26 | 169 | Eintracht Frankfurt | 180 | 1. FC Heidenheim |  | FT |
| 1388538 | 2026-03-14T17:30:00+00:00 | Regular Season - 26 | 175 | Hamburger SV | 192 | 1. FC Köln | 720 | FT |
| 1388541 | 2026-03-15T14:30:00+00:00 | Regular Season - 26 | 162 | Werder Bremen | 164 | FSV Mainz 05 |  | FT |
| 1388537 | 2026-03-15T16:30:00+00:00 | Regular Season - 26 | 160 | SC Freiburg | 182 | Union Berlin | 12717 | FT |
| 1388540 | 2026-03-15T18:30:00+00:00 | Regular Season - 26 | 172 | VfB Stuttgart | 173 | RB Leipzig |  | FT |
| 1388548 | 2026-03-20T19:30:00+00:00 | Regular Season - 27 | 173 | RB Leipzig | 167 | 1899 Hoffenheim |  | FT |
| 1388543 | 2026-03-21T14:30:00+00:00 | Regular Season - 27 | 157 | Bayern München | 182 | Union Berlin |  | FT |
| 1388550 | 2026-03-21T14:30:00+00:00 | Regular Season - 27 | 161 | VfL Wolfsburg | 162 | Werder Bremen | 752 | FT |
| 1388546 | 2026-03-21T14:30:00+00:00 | Regular Season - 27 | 180 | 1. FC Heidenheim | 168 | Bayer Leverkusen | 723 | FT |
| 1388545 | 2026-03-21T14:30:00+00:00 | Regular Season - 27 | 192 | 1. FC Köln | 163 | Borussia Mönchengladbach |  | FT |
| 1388544 | 2026-03-21T17:30:00+00:00 | Regular Season - 27 | 165 | Borussia Dortmund | 175 | Hamburger SV |  | FT |
| 1388547 | 2026-03-22T14:30:00+00:00 | Regular Season - 27 | 164 | FSV Mainz 05 | 169 | Eintracht Frankfurt | 11899 | FT |
| 1388549 | 2026-03-22T16:30:00+00:00 | Regular Season - 27 | 186 | FC St. Pauli | 160 | SC Freiburg | 745 | FT |
| 1388542 | 2026-03-22T18:30:00+00:00 | Regular Season - 27 | 170 | FC Augsburg | 172 | VfB Stuttgart | 698 | FT |
| 1388554 | 2026-04-04T13:30:00+00:00 | Regular Season - 28 | 160 | SC Freiburg | 157 | Bayern München | 12717 | FT |
| 1388559 | 2026-04-04T13:30:00+00:00 | Regular Season - 28 | 162 | Werder Bremen | 173 | RB Leipzig |  | FT |
| 1388552 | 2026-04-04T13:30:00+00:00 | Regular Season - 28 | 163 | Borussia Mönchengladbach | 180 | 1. FC Heidenheim | 20471 | FT |
| 1388556 | 2026-04-04T13:30:00+00:00 | Regular Season - 28 | 167 | 1899 Hoffenheim | 164 | FSV Mainz 05 | 724 | FT |
| 1388551 | 2026-04-04T13:30:00+00:00 | Regular Season - 28 | 168 | Bayer Leverkusen | 161 | VfL Wolfsburg | 699 | FT |
| 1388555 | 2026-04-04T13:30:00+00:00 | Regular Season - 28 | 175 | Hamburger SV | 170 | FC Augsburg | 720 | FT |
| 1388557 | 2026-04-04T16:30:00+00:00 | Regular Season - 28 | 172 | VfB Stuttgart | 165 | Borussia Dortmund |  | FT |
| 1388558 | 2026-04-05T13:30:00+00:00 | Regular Season - 28 | 182 | Union Berlin | 186 | FC St. Pauli | 748 | FT |
| 1388553 | 2026-04-05T15:30:00+00:00 | Regular Season - 28 | 169 | Eintracht Frankfurt | 192 | 1. FC Köln |  | FT |
| 1388560 | 2026-04-10T18:30:00+00:00 | Regular Season - 29 | 170 | FC Augsburg | 167 | 1899 Hoffenheim | 698 | FT |
| 1388568 | 2026-04-11T13:30:00+00:00 | Regular Season - 29 | 161 | VfL Wolfsburg | 169 | Eintracht Frankfurt | 752 | FT |
| 1388561 | 2026-04-11T13:30:00+00:00 | Regular Season - 29 | 165 | Borussia Dortmund | 168 | Bayer Leverkusen |  | FT |
| 1388565 | 2026-04-11T13:30:00+00:00 | Regular Season - 29 | 173 | RB Leipzig | 163 | Borussia Mönchengladbach |  | FT |
| 1388563 | 2026-04-11T13:30:00+00:00 | Regular Season - 29 | 180 | 1. FC Heidenheim | 182 | Union Berlin | 723 | FT |
| 1388566 | 2026-04-11T16:30:00+00:00 | Regular Season - 29 | 186 | FC St. Pauli | 157 | Bayern München | 745 | FT |
| 1388562 | 2026-04-12T13:30:00+00:00 | Regular Season - 29 | 192 | 1. FC Köln | 162 | Werder Bremen |  | FT |
| 1388567 | 2026-04-12T15:30:00+00:00 | Regular Season - 29 | 172 | VfB Stuttgart | 175 | Hamburger SV |  | FT |
| 1388564 | 2026-04-12T17:30:00+00:00 | Regular Season - 29 | 164 | FSV Mainz 05 | 160 | SC Freiburg | 11899 | FT |
| 1388575 | 2026-04-17T18:30:00+00:00 | Regular Season - 30 | 186 | FC St. Pauli | 192 | 1. FC Köln | 745 | FT |
| 1388577 | 2026-04-18T13:30:00+00:00 | Regular Season - 30 | 162 | Werder Bremen | 175 | Hamburger SV |  | FT |
| 1388574 | 2026-04-18T13:30:00+00:00 | Regular Season - 30 | 167 | 1899 Hoffenheim | 165 | Borussia Dortmund | 724 | FT |
| 1388569 | 2026-04-18T13:30:00+00:00 | Regular Season - 30 | 168 | Bayer Leverkusen | 170 | FC Augsburg | 699 | FT |
| 1388576 | 2026-04-18T13:30:00+00:00 | Regular Season - 30 | 182 | Union Berlin | 161 | VfL Wolfsburg | 748 | FT |
| 1388572 | 2026-04-18T16:30:00+00:00 | Regular Season - 30 | 169 | Eintracht Frankfurt | 173 | RB Leipzig |  | FT |
| 1388573 | 2026-04-19T13:30:00+00:00 | Regular Season - 30 | 160 | SC Freiburg | 180 | 1. FC Heidenheim | 12717 | FT |
| 1388570 | 2026-04-19T15:30:00+00:00 | Regular Season - 30 | 157 | Bayern München | 172 | VfB Stuttgart |  | FT |
| 1388571 | 2026-04-19T17:30:00+00:00 | Regular Season - 30 | 163 | Borussia Mönchengladbach | 164 | FSV Mainz 05 | 20471 | FT |
| 1388584 | 2026-04-24T18:30:00+00:00 | Regular Season - 31 | 173 | RB Leipzig | 182 | Union Berlin |  | FT |
| 1388586 | 2026-04-25T13:30:00+00:00 | Regular Season - 31 | 161 | VfL Wolfsburg | 163 | Borussia Mönchengladbach | 752 | FT |
| 1388583 | 2026-04-25T13:30:00+00:00 | Regular Season - 31 | 164 | FSV Mainz 05 | 157 | Bayern München | 11899 | FT |
| 1388578 | 2026-04-25T13:30:00+00:00 | Regular Season - 31 | 170 | FC Augsburg | 169 | Eintracht Frankfurt | 698 | FT |
| 1388582 | 2026-04-25T13:30:00+00:00 | Regular Season - 31 | 180 | 1. FC Heidenheim | 186 | FC St. Pauli | 723 | FT |
| 1388580 | 2026-04-25T13:30:00+00:00 | Regular Season - 31 | 192 | 1. FC Köln | 168 | Bayer Leverkusen |  | FT |
| 1388581 | 2026-04-25T16:30:00+00:00 | Regular Season - 31 | 175 | Hamburger SV | 167 | 1899 Hoffenheim | 720 | FT |
| 1388585 | 2026-04-26T13:30:00+00:00 | Regular Season - 31 | 172 | VfB Stuttgart | 162 | Werder Bremen |  | FT |
| 1388579 | 2026-04-26T15:30:00+00:00 | Regular Season - 31 | 165 | Borussia Dortmund | 160 | SC Freiburg |  | FT |
| 1388588 | 2026-05-02T13:30:00+00:00 | Regular Season - 32 | 157 | Bayern München | 180 | 1. FC Heidenheim |  | NS |
| 1388595 | 2026-05-02T13:30:00+00:00 | Regular Season - 32 | 162 | Werder Bremen | 170 | FC Augsburg |  | NS |
| 1388592 | 2026-05-02T13:30:00+00:00 | Regular Season - 32 | 167 | 1899 Hoffenheim | 172 | VfB Stuttgart | 724 | NS |
| 1388590 | 2026-05-02T13:30:00+00:00 | Regular Season - 32 | 169 | Eintracht Frankfurt | 175 | Hamburger SV |  | NS |
| 1388594 | 2026-05-02T13:30:00+00:00 | Regular Season - 32 | 182 | Union Berlin | 192 | 1. FC Köln | 748 | NS |
| 1388587 | 2026-05-02T16:30:00+00:00 | Regular Season - 32 | 168 | Bayer Leverkusen | 173 | RB Leipzig | 699 | NS |
| 1388593 | 2026-05-03T13:30:00+00:00 | Regular Season - 32 | 186 | FC St. Pauli | 164 | FSV Mainz 05 | 745 | NS |
| 1388589 | 2026-05-03T15:30:00+00:00 | Regular Season - 32 | 163 | Borussia Mönchengladbach | 165 | Borussia Dortmund |  | NS |
| 1388591 | 2026-05-03T17:30:00+00:00 | Regular Season - 32 | 160 | SC Freiburg | 161 | VfL Wolfsburg |  | NS |
| 1388597 | 2026-05-08T18:30:00+00:00 | Regular Season - 33 | 165 | Borussia Dortmund | 169 | Eintracht Frankfurt |  | NS |
| 1388600 | 2026-05-09T13:30:00+00:00 | Regular Season - 33 | 167 | 1899 Hoffenheim | 162 | Werder Bremen | 724 | NS |
| 1388596 | 2026-05-09T13:30:00+00:00 | Regular Season - 33 | 170 | FC Augsburg | 163 | Borussia Mönchengladbach | 698 | NS |
| 1388603 | 2026-05-09T13:30:00+00:00 | Regular Season - 33 | 172 | VfB Stuttgart | 168 | Bayer Leverkusen |  | NS |
| 1388602 | 2026-05-09T13:30:00+00:00 | Regular Season - 33 | 173 | RB Leipzig | 186 | FC St. Pauli |  | NS |
| 1388604 | 2026-05-09T16:30:00+00:00 | Regular Season - 33 | 161 | VfL Wolfsburg | 157 | Bayern München | 752 | NS |
| 1388599 | 2026-05-10T13:30:00+00:00 | Regular Season - 33 | 175 | Hamburger SV | 160 | SC Freiburg | 720 | NS |
| 1388598 | 2026-05-10T15:30:00+00:00 | Regular Season - 33 | 192 | 1. FC Köln | 180 | 1. FC Heidenheim |  | NS |
| 1388601 | 2026-05-10T17:30:00+00:00 | Regular Season - 33 | 164 | FSV Mainz 05 | 182 | Union Berlin | 11899 | NS |
| 1388606 | 2026-05-16T13:30:00+00:00 | Regular Season - 34 | 157 | Bayern München | 192 | 1. FC Köln |  | NS |
| 1388609 | 2026-05-16T13:30:00+00:00 | Regular Season - 34 | 160 | SC Freiburg | 173 | RB Leipzig |  | NS |
| 1388613 | 2026-05-16T13:30:00+00:00 | Regular Season - 34 | 162 | Werder Bremen | 165 | Borussia Dortmund |  | NS |
| 1388607 | 2026-05-16T13:30:00+00:00 | Regular Season - 34 | 163 | Borussia Mönchengladbach | 167 | 1899 Hoffenheim |  | NS |
| 1388605 | 2026-05-16T13:30:00+00:00 | Regular Season - 34 | 168 | Bayer Leverkusen | 175 | Hamburger SV | 699 | NS |
| 1388608 | 2026-05-16T13:30:00+00:00 | Regular Season - 34 | 169 | Eintracht Frankfurt | 172 | VfB Stuttgart |  | NS |
| 1388610 | 2026-05-16T13:30:00+00:00 | Regular Season - 34 | 180 | 1. FC Heidenheim | 164 | FSV Mainz 05 |  | NS |
| 1388612 | 2026-05-16T13:30:00+00:00 | Regular Season - 34 | 182 | Union Berlin | 170 | FC Augsburg | 748 | NS |
| 1388611 | 2026-05-16T13:30:00+00:00 | Regular Season - 34 | 186 | FC St. Pauli | 161 | VfL Wolfsburg | 745 | NS |


## Serie A

| Champ | Valeur |
| --- | --- |
| league_id | 135 |
| api_name | Serie A |
| country | Italy |
| type | League |
| season | 2025 |
| season_start | 2025-08-23 |
| season_end | 2026-05-24 |


### Coverage

```json
{
  "fixtures": {
    "events": true,
    "lineups": true,
    "statistics_fixtures": true,
    "statistics_players": true
  },
  "standings": true,
  "players": true,
  "top_scorers": true,
  "top_assists": true,
  "top_cards": true,
  "injuries": true,
  "predictions": true,
  "odds": true
}
```

### Teams et stades

| team_id | name | code | country | national | venue_id | venue | city | capacity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 489 | AC Milan | MIL | Italy | False | 907 | Stadio Giuseppe Meazza | Milano | 80018 |
| 497 | AS Roma | ROM | Italy | False | 910 | Stadio Olimpico | Roma | 68530 |
| 499 | Atalanta | ATA | Italy | False | 879 | Gewiss Stadium | Bergamo | 21300 |
| 500 | Bologna | BOL | Italy | False | 881 | Stadio Renato Dall'Ara | Bologna | 39279 |
| 490 | Cagliari | CAG | Italy | False | 12275 | Unipol Domus | Cagliari | 16416 |
| 895 | Como | COM | Italy | False | 892 | Stadio Giuseppe Sinigaglia | Como | 13602 |
| 520 | Cremonese | CRE | Italy | False | 894 | Stadio Giovanni Zini | Cremona | 20034 |
| 502 | Fiorentina | FIO | Italy | False | 902 | Stadio Artemio Franchi | Firenze | 43147 |
| 495 | Genoa | GEN | Italy | False | 905 | Stadio Comunale Luigi Ferraris | Genova | 36703 |
| 504 | Hellas Verona | VER | Italy | False | 890 | Stadio Marc'Antonio Bentegodi | Verona | 39211 |
| 505 | Inter | INT | Italy | False | 907 | Stadio Giuseppe Meazza | Milano | 80018 |
| 496 | Juventus | JUV | Italy | False | 909 | Allianz Stadium | Torino | 45666 |
| 487 | Lazio | LAZ | Italy | False | 910 | Stadio Olimpico | Roma | 68530 |
| 867 | Lecce | LEC | Italy | False | 911 | Stadio Comunale Via del Mare | Lecce | 33876 |
| 492 | Napoli | NAP | Italy | False | 11904 | Stadio Diego Armando Maradona | Napoli | 60240 |
| 523 | Parma | PAR | Italy | False | 921 | Stadio Ennio Tardini | Parma | 22885 |
| 801 | Pisa | PIS | Italy | False | 925 | Arena Garibaldi - Stadio Romeo Anconetani | Pisa | 17500 |
| 488 | Sassuolo | SAS | Italy | False | 935 | MAPEI Stadium - Città del Tricolore | Reggio Emilia | 23717 |
| 503 | Torino | TOR | Italy | False | 943 | Stadio Olimpico Grande Torino | Torino | 27958 |
| 494 | Udinese | UDI | Italy | False | 20416 | Bluenergy Stadium | Udine | 25952 |


### Rounds

- `Regular Season - 1`
- `Regular Season - 2`
- `Regular Season - 3`
- `Regular Season - 4`
- `Regular Season - 5`
- `Regular Season - 6`
- `Regular Season - 7`
- `Regular Season - 8`
- `Regular Season - 9`
- `Regular Season - 10`
- `Regular Season - 11`
- `Regular Season - 12`
- `Regular Season - 13`
- `Regular Season - 14`
- `Regular Season - 15`
- `Regular Season - 16`
- `Regular Season - 17`
- `Regular Season - 18`
- `Regular Season - 19`
- `Regular Season - 20`
- `Regular Season - 21`
- `Regular Season - 22`
- `Regular Season - 23`
- `Regular Season - 24`
- `Regular Season - 25`
- `Regular Season - 26`
- `Regular Season - 27`
- `Regular Season - 28`
- `Regular Season - 29`
- `Regular Season - 30`
- `Regular Season - 31`
- `Regular Season - 32`
- `Regular Season - 33`
- `Regular Season - 34`
- `Regular Season - 35`
- `Regular Season - 36`
- `Regular Season - 37`
- `Regular Season - 38`

### Standings

| rank | team_id | team | group | pts | played | W | D | L | GD | form |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 505 | Inter | Serie A | 79 | 34 | 25 | 4 | 5 | 49 | DWWWD |
| 2 | 492 | Napoli | Serie A | 69 | 34 | 21 | 6 | 7 | 19 | WLDWW |
| 3 | 489 | AC Milan | Serie A | 67 | 34 | 19 | 10 | 5 | 21 | DWLLW |
| 4 | 496 | Juventus | Serie A | 64 | 34 | 18 | 10 | 6 | 28 | DWWWD |
| 5 | 895 | Como | Serie A | 61 | 34 | 17 | 10 | 7 | 31 | WLLDW |
| 6 | 497 | AS Roma | Serie A | 61 | 34 | 19 | 4 | 11 | 19 | WDWLW |
| 7 | 499 | Atalanta | Serie A | 54 | 34 | 14 | 12 | 8 | 15 | LDLWW |
| 8 | 487 | Lazio | Serie A | 48 | 34 | 12 | 12 | 10 | 4 | DWLDW |
| 9 | 500 | Bologna | Serie A | 48 | 34 | 14 | 6 | 14 | 1 | LLWWL |
| 10 | 488 | Sassuolo | Serie A | 46 | 34 | 13 | 7 | 14 | -3 | DWLWD |
| 11 | 494 | Udinese | Serie A | 44 | 34 | 12 | 8 | 14 | -5 | DLWDW |
| 12 | 523 | Parma | Serie A | 42 | 34 | 10 | 12 | 12 | -15 | WWDDL |
| 13 | 503 | Torino | Serie A | 41 | 34 | 11 | 8 | 15 | -17 | DDWWL |
| 14 | 495 | Genoa | Serie A | 39 | 34 | 10 | 9 | 15 | -8 | LWWLL |
| 15 | 502 | Fiorentina | Serie A | 37 | 34 | 8 | 13 | 13 | -7 | DDWWD |
| 16 | 490 | Cagliari | Serie A | 36 | 34 | 9 | 9 | 16 | -13 | WLWLL |
| 17 | 867 | Lecce | Serie A | 32 | 35 | 8 | 8 | 19 | -23 | WDDLL |
| 18 | 520 | Cremonese | Serie A | 28 | 34 | 6 | 10 | 18 | -25 | LDLLW |
| 19 | 504 | Hellas Verona | Serie A | 19 | 34 | 3 | 10 | 21 | -33 | DLLLL |
| 20 | 801 | Pisa | Serie A | 18 | 35 | 2 | 12 | 21 | -38 | LLLLL |


### Fixtures

| fixture_id | date | round | home_id | home | away_id | away | venue_id | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1377872 | 2025-08-23T16:30:00+00:00 | Regular Season - 1 | 488 | Sassuolo | 492 | Napoli | 0 | FT |
| 1377867 | 2025-08-23T16:30:00+00:00 | Regular Season - 1 | 495 | Genoa | 867 | Lecce |  | FT |
| 1377870 | 2025-08-23T18:45:00+00:00 | Regular Season - 1 | 489 | AC Milan | 520 | Cremonese | 907 | FT |
| 1377871 | 2025-08-23T18:45:00+00:00 | Regular Season - 1 | 497 | AS Roma | 500 | Bologna |  | FT |
| 1377865 | 2025-08-24T16:30:00+00:00 | Regular Season - 1 | 490 | Cagliari | 502 | Fiorentina | 12275 | FT |
| 1377866 | 2025-08-24T16:30:00+00:00 | Regular Season - 1 | 895 | Como | 487 | Lazio | 892 | FT |
| 1377869 | 2025-08-24T18:45:00+00:00 | Regular Season - 1 | 496 | Juventus | 523 | Parma |  | FT |
| 1377864 | 2025-08-24T18:45:00+00:00 | Regular Season - 1 | 499 | Atalanta | 801 | Pisa | 879 | FT |
| 1377873 | 2025-08-25T16:30:00+00:00 | Regular Season - 1 | 494 | Udinese | 504 | Hellas Verona | 20416 | FT |
| 1377868 | 2025-08-25T18:45:00+00:00 | Regular Season - 1 | 505 | Inter | 503 | Torino | 907 | FT |
| 1377875 | 2025-08-29T16:30:00+00:00 | Regular Season - 2 | 520 | Cremonese | 488 | Sassuolo | 894 | FT |
| 1377879 | 2025-08-29T18:45:00+00:00 | Regular Season - 2 | 867 | Lecce | 489 | AC Milan |  | FT |
| 1377874 | 2025-08-30T16:30:00+00:00 | Regular Season - 2 | 500 | Bologna | 895 | Como | 881 | FT |
| 1377881 | 2025-08-30T16:30:00+00:00 | Regular Season - 2 | 523 | Parma | 499 | Atalanta | 921 | FT |
| 1377880 | 2025-08-30T18:45:00+00:00 | Regular Season - 2 | 492 | Napoli | 490 | Cagliari |  | FT |
| 1377882 | 2025-08-30T18:45:00+00:00 | Regular Season - 2 | 801 | Pisa | 497 | AS Roma | 925 | FT |
| 1377876 | 2025-08-31T16:30:00+00:00 | Regular Season - 2 | 495 | Genoa | 496 | Juventus |  | FT |
| 1377883 | 2025-08-31T16:30:00+00:00 | Regular Season - 2 | 503 | Torino | 502 | Fiorentina |  | FT |
| 1377878 | 2025-08-31T18:45:00+00:00 | Regular Season - 2 | 487 | Lazio | 504 | Hellas Verona |  | FT |
| 1377877 | 2025-08-31T18:45:00+00:00 | Regular Season - 2 | 505 | Inter | 494 | Udinese | 907 | FT |
| 1377885 | 2025-09-13T13:00:00+00:00 | Regular Season - 3 | 490 | Cagliari | 523 | Parma | 12275 | FT |
| 1377888 | 2025-09-13T16:00:00+00:00 | Regular Season - 3 | 496 | Juventus | 505 | Inter |  | FT |
| 1377887 | 2025-09-13T18:45:00+00:00 | Regular Season - 3 | 502 | Fiorentina | 492 | Napoli |  | FT |
| 1377891 | 2025-09-14T10:30:00+00:00 | Regular Season - 3 | 497 | AS Roma | 503 | Torino |  | FT |
| 1377884 | 2025-09-14T13:00:00+00:00 | Regular Season - 3 | 499 | Atalanta | 867 | Lecce | 879 | FT |
| 1377890 | 2025-09-14T13:00:00+00:00 | Regular Season - 3 | 801 | Pisa | 494 | Udinese | 925 | FT |
| 1377892 | 2025-09-14T16:00:00+00:00 | Regular Season - 3 | 488 | Sassuolo | 487 | Lazio | 0 | FT |
| 1377889 | 2025-09-14T18:45:00+00:00 | Regular Season - 3 | 489 | AC Milan | 500 | Bologna | 907 | FT |
| 1377893 | 2025-09-15T16:30:00+00:00 | Regular Season - 3 | 504 | Hellas Verona | 520 | Cremonese | 0 | FT |
| 1377886 | 2025-09-15T18:45:00+00:00 | Regular Season - 3 | 895 | Como | 495 | Genoa | 892 | FT |
| 1377899 | 2025-09-19T18:45:00+00:00 | Regular Season - 4 | 867 | Lecce | 490 | Cagliari |  | FT |
| 1377894 | 2025-09-20T13:00:00+00:00 | Regular Season - 4 | 500 | Bologna | 495 | Genoa | 881 | FT |
| 1377903 | 2025-09-20T16:00:00+00:00 | Regular Season - 4 | 504 | Hellas Verona | 496 | Juventus | 0 | FT |
| 1377902 | 2025-09-20T18:45:00+00:00 | Regular Season - 4 | 494 | Udinese | 489 | AC Milan | 20416 | FT |
| 1377898 | 2025-09-21T10:30:00+00:00 | Regular Season - 4 | 487 | Lazio | 497 | AS Roma |  | FT |
| 1377901 | 2025-09-21T13:00:00+00:00 | Regular Season - 4 | 503 | Torino | 499 | Atalanta |  | FT |
| 1377895 | 2025-09-21T13:00:00+00:00 | Regular Season - 4 | 520 | Cremonese | 523 | Parma | 894 | FT |
| 1377896 | 2025-09-21T16:00:00+00:00 | Regular Season - 4 | 502 | Fiorentina | 895 | Como |  | FT |
| 1377897 | 2025-09-21T18:45:00+00:00 | Regular Season - 4 | 505 | Inter | 488 | Sassuolo | 907 | FT |
| 1377900 | 2025-09-22T18:45:00+00:00 | Regular Season - 4 | 492 | Napoli | 801 | Pisa |  | FT |
| 1377905 | 2025-09-27T13:00:00+00:00 | Regular Season - 5 | 895 | Como | 520 | Cremonese | 892 | FT |
| 1377907 | 2025-09-27T16:00:00+00:00 | Regular Season - 5 | 496 | Juventus | 499 | Atalanta |  | FT |
| 1377904 | 2025-09-27T18:45:00+00:00 | Regular Season - 5 | 490 | Cagliari | 505 | Inter | 12275 | FT |
| 1377913 | 2025-09-28T10:30:00+00:00 | Regular Season - 5 | 488 | Sassuolo | 494 | Udinese | 0 | FT |
| 1377912 | 2025-09-28T13:00:00+00:00 | Regular Season - 5 | 497 | AS Roma | 504 | Hellas Verona |  | FT |
| 1377911 | 2025-09-28T13:00:00+00:00 | Regular Season - 5 | 801 | Pisa | 502 | Fiorentina | 925 | FT |
| 1377908 | 2025-09-28T16:00:00+00:00 | Regular Season - 5 | 867 | Lecce | 500 | Bologna |  | FT |
| 1377909 | 2025-09-28T18:45:00+00:00 | Regular Season - 5 | 489 | AC Milan | 492 | Napoli | 907 | FT |
| 1377910 | 2025-09-29T16:30:00+00:00 | Regular Season - 5 | 523 | Parma | 503 | Torino | 921 | FT |
| 1377906 | 2025-09-29T18:45:00+00:00 | Regular Season - 5 | 495 | Genoa | 487 | Lazio |  | FT |
| 1377923 | 2025-10-03T18:45:00+00:00 | Regular Season - 6 | 504 | Hellas Verona | 488 | Sassuolo | 0 | FT |
| 1377919 | 2025-10-04T13:00:00+00:00 | Regular Season - 6 | 487 | Lazio | 503 | Torino |  | FT |
| 1377921 | 2025-10-04T13:00:00+00:00 | Regular Season - 6 | 523 | Parma | 867 | Lecce | 921 | FT |
| 1377917 | 2025-10-04T16:00:00+00:00 | Regular Season - 6 | 505 | Inter | 520 | Cremonese | 907 | FT |
| 1377914 | 2025-10-04T18:45:00+00:00 | Regular Season - 6 | 499 | Atalanta | 895 | Como | 879 | FT |
| 1377922 | 2025-10-05T10:30:00+00:00 | Regular Season - 6 | 494 | Udinese | 490 | Cagliari | 20416 | FT |
| 1377915 | 2025-10-05T13:00:00+00:00 | Regular Season - 6 | 500 | Bologna | 801 | Pisa | 881 | FT |
| 1377916 | 2025-10-05T13:00:00+00:00 | Regular Season - 6 | 502 | Fiorentina | 497 | AS Roma |  | FT |
| 1377920 | 2025-10-05T16:00:00+00:00 | Regular Season - 6 | 492 | Napoli | 495 | Genoa |  | FT |
| 1377918 | 2025-10-05T18:45:00+00:00 | Regular Season - 6 | 496 | Juventus | 489 | AC Milan |  | FT |
| 1377931 | 2025-10-18T13:00:00+00:00 | Regular Season - 7 | 801 | Pisa | 504 | Hellas Verona | 925 | FT |
| 1377929 | 2025-10-18T13:00:00+00:00 | Regular Season - 7 | 867 | Lecce | 488 | Sassuolo |  | FT |
| 1377933 | 2025-10-18T16:00:00+00:00 | Regular Season - 7 | 503 | Torino | 492 | Napoli |  | FT |
| 1377932 | 2025-10-18T18:45:00+00:00 | Regular Season - 7 | 497 | AS Roma | 505 | Inter |  | FT |
| 1377926 | 2025-10-19T10:30:00+00:00 | Regular Season - 7 | 895 | Como | 496 | Juventus | 892 | FT |
| 1377925 | 2025-10-19T13:00:00+00:00 | Regular Season - 7 | 490 | Cagliari | 500 | Bologna | 12275 | FT |
| 1377928 | 2025-10-19T13:00:00+00:00 | Regular Season - 7 | 495 | Genoa | 523 | Parma | 905 | FT |
| 1377924 | 2025-10-19T16:00:00+00:00 | Regular Season - 7 | 499 | Atalanta | 487 | Lazio | 879 | FT |
| 1377930 | 2025-10-19T18:45:00+00:00 | Regular Season - 7 | 489 | AC Milan | 502 | Fiorentina | 907 | FT |
| 1377927 | 2025-10-20T18:45:00+00:00 | Regular Season - 7 | 520 | Cremonese | 494 | Udinese | 894 | FT |
| 1377937 | 2025-10-24T18:45:00+00:00 | Regular Season - 8 | 489 | AC Milan | 801 | Pisa | 907 | FT |
| 1377942 | 2025-10-25T13:00:00+00:00 | Regular Season - 8 | 494 | Udinese | 867 | Lecce | 20416 | FT |
| 1377939 | 2025-10-25T13:00:00+00:00 | Regular Season - 8 | 523 | Parma | 895 | Como | 921 | FT |
| 1377938 | 2025-10-25T16:00:00+00:00 | Regular Season - 8 | 492 | Napoli | 505 | Inter |  | FT |
| 1377934 | 2025-10-25T18:45:00+00:00 | Regular Season - 8 | 520 | Cremonese | 499 | Atalanta | 894 | FT |
| 1377941 | 2025-10-26T11:30:00+00:00 | Regular Season - 8 | 503 | Torino | 495 | Genoa |  | FT |
| 1377940 | 2025-10-26T14:00:00+00:00 | Regular Season - 8 | 488 | Sassuolo | 497 | AS Roma | 0 | FT |
| 1377943 | 2025-10-26T14:00:00+00:00 | Regular Season - 8 | 504 | Hellas Verona | 490 | Cagliari | 0 | FT |
| 1377935 | 2025-10-26T17:00:00+00:00 | Regular Season - 8 | 502 | Fiorentina | 500 | Bologna |  | FT |
| 1377936 | 2025-10-26T19:45:00+00:00 | Regular Season - 8 | 487 | Lazio | 496 | Juventus |  | FT |
| 1377951 | 2025-10-28T17:30:00+00:00 | Regular Season - 9 | 867 | Lecce | 492 | Napoli |  | FT |
| 1377944 | 2025-10-28T19:45:00+00:00 | Regular Season - 9 | 499 | Atalanta | 489 | AC Milan | 879 | FT |
| 1377950 | 2025-10-29T17:30:00+00:00 | Regular Season - 9 | 496 | Juventus | 494 | Udinese |  | FT |
| 1377953 | 2025-10-29T17:30:00+00:00 | Regular Season - 9 | 497 | AS Roma | 523 | Parma |  | FT |
| 1377947 | 2025-10-29T17:30:00+00:00 | Regular Season - 9 | 895 | Como | 504 | Hellas Verona | 892 | FT |
| 1377948 | 2025-10-29T19:45:00+00:00 | Regular Season - 9 | 495 | Genoa | 520 | Cremonese | 905 | FT |
| 1377945 | 2025-10-29T19:45:00+00:00 | Regular Season - 9 | 500 | Bologna | 503 | Torino | 881 | FT |
| 1377949 | 2025-10-29T19:45:00+00:00 | Regular Season - 9 | 505 | Inter | 502 | Fiorentina | 907 | FT |
| 1377946 | 2025-10-30T17:30:00+00:00 | Regular Season - 9 | 490 | Cagliari | 488 | Sassuolo | 12275 | FT |
| 1377952 | 2025-10-30T19:45:00+00:00 | Regular Season - 9 | 801 | Pisa | 487 | Lazio | 925 | FT |
| 1377962 | 2025-11-01T14:00:00+00:00 | Regular Season - 10 | 494 | Udinese | 499 | Atalanta | 20416 | FT |
| 1377958 | 2025-11-01T17:00:00+00:00 | Regular Season - 10 | 492 | Napoli | 895 | Como |  | FT |
| 1377954 | 2025-11-01T19:45:00+00:00 | Regular Season - 10 | 520 | Cremonese | 496 | Juventus | 894 | FT |
| 1377963 | 2025-11-02T11:30:00+00:00 | Regular Season - 10 | 504 | Hellas Verona | 505 | Inter | 0 | FT |
| 1377955 | 2025-11-02T14:00:00+00:00 | Regular Season - 10 | 502 | Fiorentina | 867 | Lecce |  | FT |
| 1377961 | 2025-11-02T14:00:00+00:00 | Regular Season - 10 | 503 | Torino | 801 | Pisa |  | FT |
| 1377959 | 2025-11-02T17:00:00+00:00 | Regular Season - 10 | 523 | Parma | 500 | Bologna | 921 | FT |
| 1377957 | 2025-11-02T19:45:00+00:00 | Regular Season - 10 | 489 | AC Milan | 497 | AS Roma | 907 | FT |
| 1377960 | 2025-11-03T17:30:00+00:00 | Regular Season - 10 | 488 | Sassuolo | 495 | Genoa | 0 | FT |
| 1377956 | 2025-11-03T19:45:00+00:00 | Regular Season - 10 | 487 | Lazio | 490 | Cagliari |  | FT |
| 1377972 | 2025-11-07T19:45:00+00:00 | Regular Season - 11 | 801 | Pisa | 520 | Cremonese | 925 | FT |
| 1377970 | 2025-11-08T14:00:00+00:00 | Regular Season - 11 | 867 | Lecce | 504 | Hellas Verona |  | FT |
| 1377966 | 2025-11-08T14:00:00+00:00 | Regular Season - 11 | 895 | Como | 490 | Cagliari | 892 | FT |
| 1377969 | 2025-11-08T17:00:00+00:00 | Regular Season - 11 | 496 | Juventus | 503 | Torino |  | FT |
| 1377971 | 2025-11-08T19:45:00+00:00 | Regular Season - 11 | 523 | Parma | 489 | AC Milan | 921 | FT |
| 1377964 | 2025-11-09T11:30:00+00:00 | Regular Season - 11 | 499 | Atalanta | 488 | Sassuolo | 879 | FT |
| 1377967 | 2025-11-09T14:00:00+00:00 | Regular Season - 11 | 495 | Genoa | 502 | Fiorentina | 905 | FT |
| 1377965 | 2025-11-09T14:00:00+00:00 | Regular Season - 11 | 500 | Bologna | 492 | Napoli | 881 | FT |
| 1377973 | 2025-11-09T17:00:00+00:00 | Regular Season - 11 | 497 | AS Roma | 494 | Udinese |  | FT |
| 1377968 | 2025-11-09T19:45:00+00:00 | Regular Season - 11 | 505 | Inter | 487 | Lazio | 907 | FT |
| 1377974 | 2025-11-22T14:00:00+00:00 | Regular Season - 12 | 490 | Cagliari | 495 | Genoa | 12275 | FT |
| 1377982 | 2025-11-22T14:00:00+00:00 | Regular Season - 12 | 494 | Udinese | 500 | Bologna | 20416 | FT |
| 1377976 | 2025-11-22T17:00:00+00:00 | Regular Season - 12 | 502 | Fiorentina | 496 | Juventus |  | FT |
| 1377979 | 2025-11-22T19:45:00+00:00 | Regular Season - 12 | 492 | Napoli | 499 | Atalanta |  | FT |
| 1377983 | 2025-11-23T11:30:00+00:00 | Regular Season - 12 | 504 | Hellas Verona | 523 | Parma | 0 | FT |
| 1377975 | 2025-11-23T14:00:00+00:00 | Regular Season - 12 | 520 | Cremonese | 497 | AS Roma | 894 | FT |
| 1377978 | 2025-11-23T17:00:00+00:00 | Regular Season - 12 | 487 | Lazio | 867 | Lecce |  | FT |
| 1377977 | 2025-11-23T19:45:00+00:00 | Regular Season - 12 | 505 | Inter | 489 | AC Milan | 907 | FT |
| 1377981 | 2025-11-24T17:30:00+00:00 | Regular Season - 12 | 503 | Torino | 895 | Como |  | FT |
| 1377980 | 2025-11-24T19:45:00+00:00 | Regular Season - 12 | 488 | Sassuolo | 801 | Pisa | 0 | FT |
| 1377986 | 2025-11-28T19:45:00+00:00 | Regular Season - 13 | 895 | Como | 488 | Sassuolo | 892 | FT |
| 1377987 | 2025-11-29T14:00:00+00:00 | Regular Season - 13 | 495 | Genoa | 504 | Hellas Verona | 905 | FT |
| 1377991 | 2025-11-29T14:00:00+00:00 | Regular Season - 13 | 523 | Parma | 494 | Udinese | 921 | FT |
| 1377988 | 2025-11-29T17:00:00+00:00 | Regular Season - 13 | 496 | Juventus | 490 | Cagliari |  | FT |
| 1377990 | 2025-11-29T19:45:00+00:00 | Regular Season - 13 | 489 | AC Milan | 487 | Lazio | 907 | FT |
| 1377989 | 2025-11-30T11:30:00+00:00 | Regular Season - 13 | 867 | Lecce | 503 | Torino |  | FT |
| 1377992 | 2025-11-30T14:00:00+00:00 | Regular Season - 13 | 801 | Pisa | 505 | Inter | 925 | FT |
| 1377984 | 2025-11-30T17:00:00+00:00 | Regular Season - 13 | 499 | Atalanta | 502 | Fiorentina | 879 | FT |
| 1377993 | 2025-11-30T19:45:00+00:00 | Regular Season - 13 | 497 | AS Roma | 492 | Napoli |  | FT |
| 1377985 | 2025-12-01T19:45:00+00:00 | Regular Season - 13 | 500 | Bologna | 520 | Cremonese | 881 | FT |
| 1378000 | 2025-12-06T14:00:00+00:00 | Regular Season - 14 | 488 | Sassuolo | 502 | Fiorentina | 0 | FT |
| 1377996 | 2025-12-06T17:00:00+00:00 | Regular Season - 14 | 505 | Inter | 895 | Como | 907 | FT |
| 1378003 | 2025-12-06T19:45:00+00:00 | Regular Season - 14 | 504 | Hellas Verona | 499 | Atalanta | 0 | FT |
| 1377995 | 2025-12-07T11:30:00+00:00 | Regular Season - 14 | 520 | Cremonese | 867 | Lecce | 894 | FT |
| 1377994 | 2025-12-07T14:00:00+00:00 | Regular Season - 14 | 490 | Cagliari | 497 | AS Roma | 12275 | FT |
| 1377997 | 2025-12-07T17:00:00+00:00 | Regular Season - 14 | 487 | Lazio | 500 | Bologna |  | FT |
| 1377998 | 2025-12-07T19:45:00+00:00 | Regular Season - 14 | 492 | Napoli | 496 | Juventus |  | FT |
| 1377999 | 2025-12-08T14:00:00+00:00 | Regular Season - 14 | 801 | Pisa | 523 | Parma | 925 | FT |
| 1378002 | 2025-12-08T17:00:00+00:00 | Regular Season - 14 | 494 | Udinese | 495 | Genoa | 20416 | FT |
| 1378001 | 2025-12-08T19:45:00+00:00 | Regular Season - 14 | 503 | Torino | 489 | AC Milan |  | FT |
| 1378008 | 2025-12-12T19:45:00+00:00 | Regular Season - 15 | 867 | Lecce | 801 | Pisa |  | FT |
| 1378012 | 2025-12-13T14:00:00+00:00 | Regular Season - 15 | 503 | Torino | 520 | Cremonese |  | FT |
| 1378010 | 2025-12-13T17:00:00+00:00 | Regular Season - 15 | 523 | Parma | 487 | Lazio | 921 | FT |
| 1378004 | 2025-12-13T19:45:00+00:00 | Regular Season - 15 | 499 | Atalanta | 490 | Cagliari | 879 | FT |
| 1378009 | 2025-12-14T11:30:00+00:00 | Regular Season - 15 | 489 | AC Milan | 488 | Sassuolo | 907 | FT |
| 1378013 | 2025-12-14T14:00:00+00:00 | Regular Season - 15 | 494 | Udinese | 492 | Napoli | 20416 | FT |
| 1378006 | 2025-12-14T14:00:00+00:00 | Regular Season - 15 | 502 | Fiorentina | 504 | Hellas Verona |  | FT |
| 1378007 | 2025-12-14T17:00:00+00:00 | Regular Season - 15 | 495 | Genoa | 505 | Inter | 905 | FT |
| 1378005 | 2025-12-14T19:45:00+00:00 | Regular Season - 15 | 500 | Bologna | 496 | Juventus | 881 | FT |
| 1378011 | 2025-12-15T19:45:00+00:00 | Regular Season - 15 | 497 | AS Roma | 895 | Como |  | FT |
| 1378020 | 2025-12-20T17:00:00+00:00 | Regular Season - 16 | 487 | Lazio | 520 | Cremonese |  | FT |
| 1378019 | 2025-12-20T19:45:00+00:00 | Regular Season - 16 | 496 | Juventus | 497 | AS Roma |  | FT |
| 1378014 | 2025-12-21T11:30:00+00:00 | Regular Season - 16 | 490 | Cagliari | 801 | Pisa | 12275 | FT |
| 1378022 | 2025-12-21T14:00:00+00:00 | Regular Season - 16 | 488 | Sassuolo | 503 | Torino | 0 | FT |
| 1378016 | 2025-12-21T17:00:00+00:00 | Regular Season - 16 | 502 | Fiorentina | 494 | Udinese |  | FT |
| 1378017 | 2025-12-21T19:45:00+00:00 | Regular Season - 16 | 495 | Genoa | 499 | Atalanta | 905 | FT |
| 1378029 | 2025-12-27T11:30:00+00:00 | Regular Season - 17 | 523 | Parma | 502 | Fiorentina | 921 | FT |
| 1378032 | 2025-12-27T14:00:00+00:00 | Regular Season - 17 | 503 | Torino | 490 | Cagliari |  | FT |
| 1378027 | 2025-12-27T14:00:00+00:00 | Regular Season - 17 | 867 | Lecce | 895 | Como |  | FT |
| 1378033 | 2025-12-27T17:00:00+00:00 | Regular Season - 17 | 494 | Udinese | 487 | Lazio | 20416 | FT |
| 1378030 | 2025-12-27T19:45:00+00:00 | Regular Season - 17 | 801 | Pisa | 496 | Juventus | 925 | FT |
| 1378028 | 2025-12-28T11:30:00+00:00 | Regular Season - 17 | 489 | AC Milan | 504 | Hellas Verona | 907 | FT |
| 1378026 | 2025-12-28T14:00:00+00:00 | Regular Season - 17 | 520 | Cremonese | 492 | Napoli | 894 | FT |
| 1378025 | 2025-12-28T17:00:00+00:00 | Regular Season - 17 | 500 | Bologna | 488 | Sassuolo | 881 | FT |
| 1378024 | 2025-12-28T19:45:00+00:00 | Regular Season - 17 | 499 | Atalanta | 505 | Inter | 879 | FT |
| 1378031 | 2025-12-29T19:45:00+00:00 | Regular Season - 17 | 497 | AS Roma | 495 | Genoa |  | FT |
| 1378035 | 2026-01-02T19:45:00+00:00 | Regular Season - 18 | 490 | Cagliari | 489 | AC Milan | 12275 | FT |
| 1378036 | 2026-01-03T11:30:00+00:00 | Regular Season - 18 | 895 | Como | 494 | Udinese | 892 | FT |
| 1378042 | 2026-01-03T14:00:00+00:00 | Regular Season - 18 | 488 | Sassuolo | 523 | Parma | 0 | FT |
| 1378038 | 2026-01-03T14:00:00+00:00 | Regular Season - 18 | 495 | Genoa | 801 | Pisa | 905 | FT |
| 1378040 | 2026-01-03T17:00:00+00:00 | Regular Season - 18 | 496 | Juventus | 867 | Lecce |  | FT |
| 1378034 | 2026-01-03T19:45:00+00:00 | Regular Season - 18 | 499 | Atalanta | 497 | AS Roma | 879 | FT |
| 1378041 | 2026-01-04T11:30:00+00:00 | Regular Season - 18 | 487 | Lazio | 492 | Napoli |  | FT |
| 1378037 | 2026-01-04T14:00:00+00:00 | Regular Season - 18 | 502 | Fiorentina | 520 | Cremonese |  | FT |
| 1378043 | 2026-01-04T17:00:00+00:00 | Regular Season - 18 | 504 | Hellas Verona | 503 | Torino | 0 | FT |
| 1378039 | 2026-01-04T19:45:00+00:00 | Regular Season - 18 | 505 | Inter | 500 | Bologna | 907 | FT |
| 1378051 | 2026-01-06T14:00:00+00:00 | Regular Season - 19 | 801 | Pisa | 895 | Como | 925 | FT |
| 1378047 | 2026-01-06T17:00:00+00:00 | Regular Season - 19 | 867 | Lecce | 497 | AS Roma |  | FT |
| 1378052 | 2026-01-06T19:45:00+00:00 | Regular Season - 19 | 488 | Sassuolo | 496 | Juventus | 0 | FT |
| 1378049 | 2026-01-07T17:30:00+00:00 | Regular Season - 19 | 492 | Napoli | 504 | Hellas Verona |  | FT |
| 1378044 | 2026-01-07T17:30:00+00:00 | Regular Season - 19 | 500 | Bologna | 499 | Atalanta | 881 | FT |
| 1378046 | 2026-01-07T19:45:00+00:00 | Regular Season - 19 | 487 | Lazio | 502 | Fiorentina |  | FT |
| 1378053 | 2026-01-07T19:45:00+00:00 | Regular Season - 19 | 503 | Torino | 494 | Udinese |  | FT |
| 1378050 | 2026-01-07T19:45:00+00:00 | Regular Season - 19 | 523 | Parma | 505 | Inter | 921 | FT |
| 1378045 | 2026-01-08T17:30:00+00:00 | Regular Season - 19 | 520 | Cremonese | 490 | Cagliari | 894 | FT |
| 1378048 | 2026-01-08T19:45:00+00:00 | Regular Season - 19 | 489 | AC Milan | 495 | Genoa | 907 | FT |
| 1378062 | 2026-01-10T14:00:00+00:00 | Regular Season - 20 | 494 | Udinese | 801 | Pisa | 20416 | FT |
| 1378055 | 2026-01-10T14:00:00+00:00 | Regular Season - 20 | 895 | Como | 500 | Bologna | 892 | FT |
| 1378061 | 2026-01-10T17:00:00+00:00 | Regular Season - 20 | 497 | AS Roma | 488 | Sassuolo |  | FT |
| 1378054 | 2026-01-10T19:45:00+00:00 | Regular Season - 20 | 499 | Atalanta | 503 | Torino | 879 | FT |
| 1378060 | 2026-01-11T11:30:00+00:00 | Regular Season - 20 | 867 | Lecce | 523 | Parma |  | FT |
| 1378056 | 2026-01-11T14:00:00+00:00 | Regular Season - 20 | 502 | Fiorentina | 489 | AC Milan |  | FT |
| 1378063 | 2026-01-11T17:00:00+00:00 | Regular Season - 20 | 504 | Hellas Verona | 487 | Lazio | 0 | FT |
| 1378058 | 2026-01-11T19:45:00+00:00 | Regular Season - 20 | 505 | Inter | 492 | Napoli | 907 | FT |
| 1378057 | 2026-01-12T17:30:00+00:00 | Regular Season - 20 | 495 | Genoa | 490 | Cagliari | 905 | FT |
| 1378059 | 2026-01-12T19:45:00+00:00 | Regular Season - 20 | 496 | Juventus | 520 | Cremonese |  | FT |
| 1378021 | 2026-01-14T17:30:00+00:00 | Regular Season - 16 | 492 | Napoli | 523 | Parma |  | FT |
| 1378018 | 2026-01-14T19:45:00+00:00 | Regular Season - 16 | 505 | Inter | 867 | Lecce | 907 | FT |
| 1378023 | 2026-01-15T17:30:00+00:00 | Regular Season - 16 | 504 | Hellas Verona | 500 | Bologna | 0 | FT |
| 1378015 | 2026-01-15T19:45:00+00:00 | Regular Season - 16 | 895 | Como | 489 | AC Milan | 892 | FT |
| 1378071 | 2026-01-16T19:45:00+00:00 | Regular Season - 21 | 801 | Pisa | 499 | Atalanta | 925 | FT |
| 1378073 | 2026-01-17T14:00:00+00:00 | Regular Season - 21 | 494 | Udinese | 505 | Inter | 20416 | FT |
| 1378069 | 2026-01-17T17:00:00+00:00 | Regular Season - 21 | 492 | Napoli | 488 | Sassuolo |  | FT |
| 1378065 | 2026-01-17T19:45:00+00:00 | Regular Season - 21 | 490 | Cagliari | 496 | Juventus | 12275 | FT |
| 1378070 | 2026-01-18T11:30:00+00:00 | Regular Season - 21 | 523 | Parma | 495 | Genoa | 921 | FT |
| 1378064 | 2026-01-18T14:00:00+00:00 | Regular Season - 21 | 500 | Bologna | 502 | Fiorentina | 881 | FT |
| 1378072 | 2026-01-18T17:00:00+00:00 | Regular Season - 21 | 503 | Torino | 497 | AS Roma |  | FT |
| 1378068 | 2026-01-18T19:45:00+00:00 | Regular Season - 21 | 489 | AC Milan | 867 | Lecce | 907 | FT |
| 1378066 | 2026-01-19T17:30:00+00:00 | Regular Season - 21 | 520 | Cremonese | 504 | Hellas Verona | 894 | FT |
| 1378067 | 2026-01-19T19:45:00+00:00 | Regular Season - 21 | 487 | Lazio | 895 | Como |  | FT |
| 1378078 | 2026-01-23T19:45:00+00:00 | Regular Season - 22 | 505 | Inter | 801 | Pisa | 907 | FT |
| 1378075 | 2026-01-24T14:00:00+00:00 | Regular Season - 22 | 895 | Como | 503 | Torino | 921 | FT |
| 1378076 | 2026-01-24T17:00:00+00:00 | Regular Season - 22 | 502 | Fiorentina | 490 | Cagliari |  | FT |
| 1378080 | 2026-01-24T19:45:00+00:00 | Regular Season - 22 | 867 | Lecce | 487 | Lazio |  | FT |
| 1378082 | 2026-01-25T11:30:00+00:00 | Regular Season - 22 | 488 | Sassuolo | 520 | Cremonese | 0 | FT |
| 1378077 | 2026-01-25T14:00:00+00:00 | Regular Season - 22 | 495 | Genoa | 500 | Bologna | 905 | FT |
| 1378074 | 2026-01-25T14:00:00+00:00 | Regular Season - 22 | 499 | Atalanta | 523 | Parma | 879 | FT |
| 1378079 | 2026-01-25T17:00:00+00:00 | Regular Season - 22 | 496 | Juventus | 492 | Napoli |  | FT |
| 1378081 | 2026-01-25T19:45:00+00:00 | Regular Season - 22 | 497 | AS Roma | 489 | AC Milan |  | FT |
| 1378083 | 2026-01-26T19:45:00+00:00 | Regular Season - 22 | 504 | Hellas Verona | 494 | Udinese | 0 | FT |
| 1378088 | 2026-01-30T19:45:00+00:00 | Regular Season - 23 | 487 | Lazio | 495 | Genoa |  | FT |
| 1378091 | 2026-01-31T14:00:00+00:00 | Regular Season - 23 | 801 | Pisa | 488 | Sassuolo | 925 | FT |
| 1378089 | 2026-01-31T17:00:00+00:00 | Regular Season - 23 | 492 | Napoli | 502 | Fiorentina |  | FT |
| 1378085 | 2026-01-31T19:45:00+00:00 | Regular Season - 23 | 490 | Cagliari | 504 | Hellas Verona | 12275 | FT |
| 1378092 | 2026-02-01T11:30:00+00:00 | Regular Season - 23 | 503 | Torino | 867 | Lecce |  | FT |
| 1378086 | 2026-02-01T14:00:00+00:00 | Regular Season - 23 | 895 | Como | 499 | Atalanta | 892 | FT |
| 1378087 | 2026-02-01T17:00:00+00:00 | Regular Season - 23 | 520 | Cremonese | 505 | Inter | 894 | FT |
| 1378090 | 2026-02-01T19:45:00+00:00 | Regular Season - 23 | 523 | Parma | 496 | Juventus | 921 | FT |
| 1378093 | 2026-02-02T19:45:00+00:00 | Regular Season - 23 | 494 | Udinese | 497 | AS Roma | 20416 | FT |
| 1378084 | 2026-02-03T19:45:00+00:00 | Regular Season - 23 | 500 | Bologna | 489 | AC Milan | 881 | FT |
| 1378103 | 2026-02-06T19:45:00+00:00 | Regular Season - 24 | 504 | Hellas Verona | 801 | Pisa | 0 | FT |
| 1378097 | 2026-02-07T17:00:00+00:00 | Regular Season - 24 | 495 | Genoa | 492 | Napoli | 905 | FT |
| 1378096 | 2026-02-07T19:45:00+00:00 | Regular Season - 24 | 502 | Fiorentina | 503 | Torino |  | FT |
| 1378095 | 2026-02-08T11:30:00+00:00 | Regular Season - 24 | 500 | Bologna | 523 | Parma | 881 | FT |
| 1378099 | 2026-02-08T14:00:00+00:00 | Regular Season - 24 | 867 | Lecce | 494 | Udinese |  | FT |
| 1378102 | 2026-02-08T17:00:00+00:00 | Regular Season - 24 | 488 | Sassuolo | 505 | Inter | 0 | FT |
| 1378098 | 2026-02-08T19:45:00+00:00 | Regular Season - 24 | 496 | Juventus | 487 | Lazio |  | FT |
| 1378094 | 2026-02-09T17:30:00+00:00 | Regular Season - 24 | 499 | Atalanta | 520 | Cremonese | 879 | FT |
| 1378101 | 2026-02-09T19:45:00+00:00 | Regular Season - 24 | 497 | AS Roma | 490 | Cagliari |  | FT |
| 1378111 | 2026-02-13T19:45:00+00:00 | Regular Season - 25 | 801 | Pisa | 489 | AC Milan | 925 | FT |
| 1378105 | 2026-02-14T14:00:00+00:00 | Regular Season - 25 | 895 | Como | 502 | Fiorentina | 892 | FT |
| 1378108 | 2026-02-14T17:00:00+00:00 | Regular Season - 25 | 487 | Lazio | 499 | Atalanta |  | FT |
| 1378107 | 2026-02-14T19:45:00+00:00 | Regular Season - 25 | 505 | Inter | 496 | Juventus | 907 | FT |
| 1378113 | 2026-02-15T11:30:00+00:00 | Regular Season - 25 | 494 | Udinese | 488 | Sassuolo | 20416 | FT |
| 1378106 | 2026-02-15T14:00:00+00:00 | Regular Season - 25 | 520 | Cremonese | 495 | Genoa | 894 | FT |
| 1378110 | 2026-02-15T14:00:00+00:00 | Regular Season - 25 | 523 | Parma | 504 | Hellas Verona | 921 | FT |
| 1378112 | 2026-02-15T17:00:00+00:00 | Regular Season - 25 | 503 | Torino | 500 | Bologna |  | FT |
| 1378109 | 2026-02-15T19:45:00+00:00 | Regular Season - 25 | 492 | Napoli | 497 | AS Roma |  | FT |
| 1378104 | 2026-02-16T19:45:00+00:00 | Regular Season - 25 | 490 | Cagliari | 867 | Lecce | 12275 | FT |
| 1378100 | 2026-02-18T19:45:00+00:00 | Regular Season - 24 | 489 | AC Milan | 895 | Como | 907 | FT |
| 1378123 | 2026-02-20T19:45:00+00:00 | Regular Season - 26 | 488 | Sassuolo | 504 | Hellas Verona | 0 | FT |
| 1378119 | 2026-02-21T14:00:00+00:00 | Regular Season - 26 | 496 | Juventus | 895 | Como |  | FT |
| 1378120 | 2026-02-21T17:00:00+00:00 | Regular Season - 26 | 867 | Lecce | 505 | Inter |  | FT |
| 1378116 | 2026-02-21T19:45:00+00:00 | Regular Season - 26 | 490 | Cagliari | 487 | Lazio | 12275 | FT |
| 1378118 | 2026-02-22T11:30:00+00:00 | Regular Season - 26 | 495 | Genoa | 503 | Torino | 905 | FT |
| 1378114 | 2026-02-22T14:00:00+00:00 | Regular Season - 26 | 499 | Atalanta | 492 | Napoli | 879 | FT |
| 1378121 | 2026-02-22T17:00:00+00:00 | Regular Season - 26 | 489 | AC Milan | 523 | Parma | 907 | FT |
| 1378122 | 2026-02-22T19:45:00+00:00 | Regular Season - 26 | 497 | AS Roma | 520 | Cremonese |  | FT |
| 1378117 | 2026-02-23T17:30:00+00:00 | Regular Season - 26 | 502 | Fiorentina | 801 | Pisa |  | FT |
| 1378115 | 2026-02-23T19:45:00+00:00 | Regular Season - 26 | 500 | Bologna | 494 | Udinese | 881 | FT |
| 1378127 | 2026-02-27T19:45:00+00:00 | Regular Season - 27 | 523 | Parma | 490 | Cagliari | 921 | FT |
| 1378124 | 2026-02-28T14:00:00+00:00 | Regular Season - 27 | 895 | Como | 867 | Lecce | 892 | FT |
| 1378133 | 2026-02-28T17:00:00+00:00 | Regular Season - 27 | 504 | Hellas Verona | 492 | Napoli | 0 | FT |
| 1378126 | 2026-02-28T19:45:00+00:00 | Regular Season - 27 | 505 | Inter | 495 | Genoa | 907 | FT |
| 1378125 | 2026-03-01T11:30:00+00:00 | Regular Season - 27 | 520 | Cremonese | 489 | AC Milan | 894 | FT |
| 1378130 | 2026-03-01T14:00:00+00:00 | Regular Season - 27 | 488 | Sassuolo | 499 | Atalanta | 0 | FT |
| 1378131 | 2026-03-01T17:00:00+00:00 | Regular Season - 27 | 503 | Torino | 487 | Lazio |  | FT |
| 1378129 | 2026-03-01T19:45:00+00:00 | Regular Season - 27 | 497 | AS Roma | 496 | Juventus |  | FT |
| 1378128 | 2026-03-02T17:30:00+00:00 | Regular Season - 27 | 801 | Pisa | 500 | Bologna | 925 | FT |
| 1378132 | 2026-03-02T19:45:00+00:00 | Regular Season - 27 | 494 | Udinese | 502 | Fiorentina | 20416 | FT |
| 1378143 | 2026-03-06T19:45:00+00:00 | Regular Season - 28 | 492 | Napoli | 503 | Torino |  | FT |
| 1378136 | 2026-03-07T14:00:00+00:00 | Regular Season - 28 | 490 | Cagliari | 895 | Como | 12275 | FT |
| 1378134 | 2026-03-07T17:00:00+00:00 | Regular Season - 28 | 499 | Atalanta | 494 | Udinese | 879 | FT |
| 1378139 | 2026-03-07T19:45:00+00:00 | Regular Season - 28 | 496 | Juventus | 801 | Pisa |  | FT |
| 1378141 | 2026-03-08T11:30:00+00:00 | Regular Season - 28 | 867 | Lecce | 520 | Cremonese |  | FT |
| 1378135 | 2026-03-08T14:00:00+00:00 | Regular Season - 28 | 500 | Bologna | 504 | Hellas Verona | 881 | FT |
| 1378137 | 2026-03-08T14:00:00+00:00 | Regular Season - 28 | 502 | Fiorentina | 523 | Parma |  | FT |
| 1378138 | 2026-03-08T17:00:00+00:00 | Regular Season - 28 | 495 | Genoa | 497 | AS Roma | 905 | FT |
| 1378142 | 2026-03-08T19:45:00+00:00 | Regular Season - 28 | 489 | AC Milan | 505 | Inter | 907 | FT |
| 1378140 | 2026-03-09T19:45:00+00:00 | Regular Season - 28 | 487 | Lazio | 488 | Sassuolo |  | FT |
| 1378151 | 2026-03-13T19:45:00+00:00 | Regular Season - 29 | 503 | Torino | 523 | Parma |  | FT |
| 1378146 | 2026-03-14T14:00:00+00:00 | Regular Season - 29 | 505 | Inter | 499 | Atalanta | 907 | FT |
| 1378148 | 2026-03-14T17:00:00+00:00 | Regular Season - 29 | 492 | Napoli | 867 | Lecce |  | FT |
| 1378152 | 2026-03-14T19:45:00+00:00 | Regular Season - 29 | 494 | Udinese | 496 | Juventus | 20416 | FT |
| 1378153 | 2026-03-15T11:30:00+00:00 | Regular Season - 29 | 504 | Hellas Verona | 495 | Genoa | 0 | FT |
| 1378150 | 2026-03-15T14:00:00+00:00 | Regular Season - 29 | 488 | Sassuolo | 500 | Bologna | 0 | FT |
| 1378149 | 2026-03-15T14:00:00+00:00 | Regular Season - 29 | 801 | Pisa | 490 | Cagliari | 925 | FT |
| 1378144 | 2026-03-15T17:00:00+00:00 | Regular Season - 29 | 895 | Como | 497 | AS Roma | 892 | FT |
| 1378147 | 2026-03-15T19:45:00+00:00 | Regular Season - 29 | 487 | Lazio | 489 | AC Milan |  | FT |
| 1378145 | 2026-03-16T19:45:00+00:00 | Regular Season - 29 | 520 | Cremonese | 502 | Fiorentina | 894 | FT |
| 1378156 | 2026-03-20T17:30:00+00:00 | Regular Season - 30 | 490 | Cagliari | 492 | Napoli | 12275 | FT |
| 1378159 | 2026-03-20T19:45:00+00:00 | Regular Season - 30 | 495 | Genoa | 494 | Udinese | 905 | FT |
| 1378162 | 2026-03-21T14:00:00+00:00 | Regular Season - 30 | 523 | Parma | 520 | Cremonese | 921 | FT |
| 1378161 | 2026-03-21T17:00:00+00:00 | Regular Season - 30 | 489 | AC Milan | 503 | Torino | 907 | FT |
| 1378160 | 2026-03-21T19:45:00+00:00 | Regular Season - 30 | 496 | Juventus | 488 | Sassuolo |  | FT |
| 1378157 | 2026-03-22T11:30:00+00:00 | Regular Season - 30 | 895 | Como | 801 | Pisa | 892 | FT |
| 1378154 | 2026-03-22T14:00:00+00:00 | Regular Season - 30 | 499 | Atalanta | 504 | Hellas Verona | 879 | FT |
| 1378155 | 2026-03-22T14:00:00+00:00 | Regular Season - 30 | 500 | Bologna | 487 | Lazio | 881 | FT |
| 1378163 | 2026-03-22T17:00:00+00:00 | Regular Season - 30 | 497 | AS Roma | 867 | Lecce |  | FT |
| 1378158 | 2026-03-22T19:45:00+00:00 | Regular Season - 30 | 502 | Fiorentina | 505 | Inter |  | FT |
| 1378171 | 2026-04-04T13:00:00+00:00 | Regular Season - 31 | 488 | Sassuolo | 490 | Cagliari | 0 | FT |
| 1378173 | 2026-04-04T16:00:00+00:00 | Regular Season - 31 | 504 | Hellas Verona | 502 | Fiorentina | 0 | FT |
| 1378167 | 2026-04-04T18:45:00+00:00 | Regular Season - 31 | 487 | Lazio | 523 | Parma |  | FT |
| 1378164 | 2026-04-05T13:00:00+00:00 | Regular Season - 31 | 520 | Cremonese | 500 | Bologna | 894 | FT |
| 1378170 | 2026-04-05T16:00:00+00:00 | Regular Season - 31 | 801 | Pisa | 503 | Torino | 925 | FT |
| 1378165 | 2026-04-05T18:45:00+00:00 | Regular Season - 31 | 505 | Inter | 497 | AS Roma | 907 | FT |
| 1378172 | 2026-04-06T10:30:00+00:00 | Regular Season - 31 | 494 | Udinese | 895 | Como | 20416 | FT |
| 1378168 | 2026-04-06T13:00:00+00:00 | Regular Season - 31 | 867 | Lecce | 499 | Atalanta |  | FT |
| 1378166 | 2026-04-06T16:00:00+00:00 | Regular Season - 31 | 496 | Juventus | 495 | Genoa |  | FT |
| 1378169 | 2026-04-06T18:45:00+00:00 | Regular Season - 31 | 492 | Napoli | 489 | AC Milan |  | FT |
| 1378182 | 2026-04-10T18:45:00+00:00 | Regular Season - 32 | 497 | AS Roma | 801 | Pisa |  | FT |
| 1378176 | 2026-04-11T13:00:00+00:00 | Regular Season - 32 | 490 | Cagliari | 520 | Cremonese | 12275 | FT |
| 1378183 | 2026-04-11T13:00:00+00:00 | Regular Season - 32 | 503 | Torino | 504 | Hellas Verona |  | FT |
| 1378180 | 2026-04-11T16:00:00+00:00 | Regular Season - 32 | 489 | AC Milan | 494 | Udinese | 907 | FT |
| 1378174 | 2026-04-11T18:45:00+00:00 | Regular Season - 32 | 499 | Atalanta | 496 | Juventus | 879 | FT |
| 1378179 | 2026-04-12T10:30:00+00:00 | Regular Season - 32 | 495 | Genoa | 488 | Sassuolo | 905 | FT |
| 1378181 | 2026-04-12T13:00:00+00:00 | Regular Season - 32 | 523 | Parma | 492 | Napoli | 921 | FT |
| 1378175 | 2026-04-12T16:00:00+00:00 | Regular Season - 32 | 500 | Bologna | 867 | Lecce | 881 | FT |
| 1378177 | 2026-04-12T18:45:00+00:00 | Regular Season - 32 | 895 | Como | 505 | Inter | 892 | FT |
| 1378178 | 2026-04-13T18:45:00+00:00 | Regular Season - 32 | 502 | Fiorentina | 487 | Lazio |  | FT |
| 1378191 | 2026-04-17T16:30:00+00:00 | Regular Season - 33 | 488 | Sassuolo | 895 | Como | 0 | FT |
| 1378185 | 2026-04-17T18:45:00+00:00 | Regular Season - 33 | 505 | Inter | 490 | Cagliari | 907 | FT |
| 1378192 | 2026-04-18T13:00:00+00:00 | Regular Season - 33 | 494 | Udinese | 523 | Parma | 20416 | FT |
| 1378188 | 2026-04-18T16:00:00+00:00 | Regular Season - 33 | 492 | Napoli | 487 | Lazio |  | FT |
| 1378190 | 2026-04-18T18:45:00+00:00 | Regular Season - 33 | 497 | AS Roma | 499 | Atalanta |  | FT |
| 1378184 | 2026-04-19T10:30:00+00:00 | Regular Season - 33 | 520 | Cremonese | 503 | Torino | 894 | FT |
| 1378193 | 2026-04-19T13:00:00+00:00 | Regular Season - 33 | 504 | Hellas Verona | 489 | AC Milan | 0 | FT |
| 1378189 | 2026-04-19T16:00:00+00:00 | Regular Season - 33 | 801 | Pisa | 495 | Genoa | 925 | FT |
| 1378186 | 2026-04-19T18:45:00+00:00 | Regular Season - 33 | 496 | Juventus | 500 | Bologna |  | FT |
| 1378187 | 2026-04-20T18:45:00+00:00 | Regular Season - 33 | 867 | Lecce | 502 | Fiorentina |  | FT |
| 1378200 | 2026-04-24T18:45:00+00:00 | Regular Season - 34 | 492 | Napoli | 520 | Cremonese |  | FT |
| 1378201 | 2026-04-25T13:00:00+00:00 | Regular Season - 34 | 523 | Parma | 801 | Pisa | 921 | FT |
| 1378194 | 2026-04-25T16:00:00+00:00 | Regular Season - 34 | 500 | Bologna | 497 | AS Roma | 881 | FT |
| 1378203 | 2026-04-25T18:45:00+00:00 | Regular Season - 34 | 504 | Hellas Verona | 867 | Lecce | 0 | FT |
| 1378196 | 2026-04-26T10:30:00+00:00 | Regular Season - 34 | 502 | Fiorentina | 488 | Sassuolo |  | FT |
| 1378197 | 2026-04-26T13:00:00+00:00 | Regular Season - 34 | 495 | Genoa | 895 | Como | 905 | FT |
| 1378202 | 2026-04-26T16:00:00+00:00 | Regular Season - 34 | 503 | Torino | 505 | Inter |  | FT |
| 1378199 | 2026-04-26T18:45:00+00:00 | Regular Season - 34 | 489 | AC Milan | 496 | Juventus | 907 | FT |
| 1378195 | 2026-04-27T16:30:00+00:00 | Regular Season - 34 | 490 | Cagliari | 499 | Atalanta | 12275 | FT |
| 1378198 | 2026-04-27T18:45:00+00:00 | Regular Season - 34 | 487 | Lazio | 494 | Udinese |  | FT |
| 1378210 | 2026-05-01T18:45:00+00:00 | Regular Season - 35 | 801 | Pisa | 867 | Lecce | 925 | FT |
| 1378213 | 2026-05-02T13:00:00+00:00 | Regular Season - 35 | 494 | Udinese | 503 | Torino | 20416 | NS |
| 1378206 | 2026-05-02T16:00:00+00:00 | Regular Season - 35 | 895 | Como | 492 | Napoli | 892 | NS |
| 1378204 | 2026-05-02T18:45:00+00:00 | Regular Season - 35 | 499 | Atalanta | 495 | Genoa | 879 | NS |
| 1378205 | 2026-05-03T10:30:00+00:00 | Regular Season - 35 | 500 | Bologna | 490 | Cagliari | 881 | NS |
| 1378212 | 2026-05-03T13:00:00+00:00 | Regular Season - 35 | 488 | Sassuolo | 489 | AC Milan | 0 | NS |
| 1378209 | 2026-05-03T16:00:00+00:00 | Regular Season - 35 | 496 | Juventus | 504 | Hellas Verona |  | NS |
| 1378208 | 2026-05-03T18:45:00+00:00 | Regular Season - 35 | 505 | Inter | 523 | Parma | 907 | NS |
| 1378207 | 2026-05-04T16:30:00+00:00 | Regular Season - 35 | 520 | Cremonese | 487 | Lazio | 894 | NS |
| 1378211 | 2026-05-04T18:45:00+00:00 | Regular Season - 35 | 497 | AS Roma | 502 | Fiorentina |  | NS |
| 1378222 | 2026-05-08T18:45:00+00:00 | Regular Season - 36 | 503 | Torino | 488 | Sassuolo |  | NS |
| 1378214 | 2026-05-09T13:00:00+00:00 | Regular Season - 36 | 490 | Cagliari | 494 | Udinese | 12275 | NS |
| 1378217 | 2026-05-09T16:00:00+00:00 | Regular Season - 36 | 487 | Lazio | 505 | Inter |  | NS |
| 1378218 | 2026-05-09T18:45:00+00:00 | Regular Season - 36 | 867 | Lecce | 496 | Juventus |  | NS |
| 1378223 | 2026-05-10T10:30:00+00:00 | Regular Season - 36 | 504 | Hellas Verona | 895 | Como | 0 | NS |
| 1378216 | 2026-05-10T13:00:00+00:00 | Regular Season - 36 | 502 | Fiorentina | 495 | Genoa |  | NS |
| 1378215 | 2026-05-10T13:00:00+00:00 | Regular Season - 36 | 520 | Cremonese | 801 | Pisa | 894 | NS |
| 1378221 | 2026-05-10T16:00:00+00:00 | Regular Season - 36 | 523 | Parma | 497 | AS Roma | 921 | NS |
| 1378219 | 2026-05-10T18:45:00+00:00 | Regular Season - 36 | 489 | AC Milan | 499 | Atalanta | 907 | NS |
| 1378220 | 2026-05-11T18:45:00+00:00 | Regular Season - 36 | 492 | Napoli | 500 | Bologna |  | NS |
| 1378232 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 488 | Sassuolo | 867 | Lecce | 0 | NS |
| 1378225 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 490 | Cagliari | 503 | Torino | 12275 | NS |
| 1378233 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 494 | Udinese | 520 | Cremonese |  | NS |
| 1378227 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 495 | Genoa | 489 | AC Milan |  | NS |
| 1378229 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 496 | Juventus | 502 | Fiorentina |  | NS |
| 1378231 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 497 | AS Roma | 487 | Lazio |  | NS |
| 1378224 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 499 | Atalanta | 500 | Bologna | 879 | NS |
| 1378228 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 505 | Inter | 504 | Hellas Verona | 907 | NS |
| 1378230 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 801 | Pisa | 492 | Napoli | 925 | NS |
| 1378226 | 2026-05-17T13:00:00+00:00 | Regular Season - 37 | 895 | Como | 523 | Parma | 892 | NS |
| 1378237 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 487 | Lazio | 801 | Pisa |  | NS |
| 1378239 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 489 | AC Milan | 490 | Cagliari | 907 | NS |
| 1378240 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 492 | Napoli | 494 | Udinese |  | NS |
| 1378234 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 500 | Bologna | 505 | Inter | 881 | NS |
| 1378236 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 502 | Fiorentina | 499 | Atalanta |  | NS |
| 1378242 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 503 | Torino | 496 | Juventus |  | NS |
| 1378243 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 504 | Hellas Verona | 497 | AS Roma | 0 | NS |
| 1378235 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 520 | Cremonese | 895 | Como | 894 | NS |
| 1378241 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 523 | Parma | 488 | Sassuolo | 921 | NS |
| 1378238 | 2026-05-24T13:00:00+00:00 | Regular Season - 38 | 867 | Lecce | 495 | Genoa |  | NS |


## FIFA World Cup 2026

| Champ | Valeur |
| --- | --- |
| league_id | 1 |
| api_name | World Cup |
| country | World |
| type | Cup |
| season | 2026 |
| season_start | 2026-06-11 |
| season_end | 2026-06-28 |


### Coverage

```json
{
  "fixtures": {
    "events": false,
    "lineups": false,
    "statistics_fixtures": false,
    "statistics_players": false
  },
  "standings": true,
  "players": false,
  "top_scorers": false,
  "top_assists": false,
  "top_cards": false,
  "injuries": false,
  "predictions": true,
  "odds": false
}
```

### Teams et stades

| team_id | name | code | country | national | venue_id | venue | city | capacity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1532 | Algeria | ALG | Algeria | True | 16 | Stade Mohamed-Hamlaoui | Constantine | 50000 |
| 26 | Argentina | ARG | Argentina | True | 46 | Estadio Alberto José Armando | Ciudad de Buenos Aires | 57200 |
| 20 | Australia | AUS | Australia | True | 18601 | CommBank Stadium | Sydney | 30000 |
| 775 | Austria | AUS | Austria | True | 1967 | Ernst-Happel-Stadion | Wien | 50865 |
| 1 | Belgium | BEL | Belgium | True | 173 | Stade Roi Baudouin | Brussel | 50093 |
| 1113 | Bosnia & Herzegovina | BOS | Bosnia | True | 2186 | Stadion Bilino Polje | Zenica | 15292 |
| 6 | Brazil | BRA | Brazil | True | 11531 | Neo Química Arena | São Paulo, São Paulo | 49205 |
| 5529 | Canada | CAN | Canada | True | 312 | BMO Field | Toronto, Ontario | 36045 |
| 1533 | Cape Verde Islands | CAP | Cape-Verde-Islands | True | 314 | Estádio Nacional de Cabo Verde | Praia | 15000 |
| 8 | Colombia | COL | Colombia | True | 366 | Estadio Metropolitano Roberto Meléndez | Barranquilla | 49612 |
| 1508 | Congo DR | CON | Congo-DR | True | 391 | Stade des Martyrs de la Pentecôte | Kinshasa | 100000 |
| 3 | Croatia | CRO | Croatia | True | 412 | Stadion Maksimir | Zagreb | 37168 |
| 5530 | Curaçao |  | Curacao | True | 11918 | PayPal Park | San Jose, California | 18000 |
| 770 | Czech Republic | CZE | Czech-Republic | True | 435 | Andrův stadion | Olomouc | 12566 |
| 2382 | Ecuador | ECU | Ecuador | True | 471 | Estadio Rodrigo Paz Delgado | Quito | 55104 |
| 32 | Egypt | EGY | Egypt | True | 477 | Cairo International Stadium | Cairo | 74100 |
| 10 | England | ENG | England | True | 566 | The City Ground | Nottingham, Nottinghamshire | 30576 |
| 2 | France | FRA | France | True | 20332 | Stade de France | Saint-Denis | 81338 |
| 25 | Germany | GER | Germany | True | 694 | Olympiastadion Berlin | Berlin | 74667 |
| 1504 | Ghana | GHA | Ghana | True | 21410 | Accra Sports Stadium | Accra | 35000 |
| 2386 | Haiti | HAI | Haiti | True | 22425 | Snapdragon Stadium | San Diego, California | 35000 |
| 22 | Iran | IRA | Iran | True | 22428 | Imam Reza Stadium | Mashhad | 25000 |
| 1567 | Iraq | IRA | Iraq | True | 20704 | Basra International Stadium | Basra | 65000 |
| 1501 | Ivory Coast | IVO | Ivory-Coast | True | 411 | Stade Félix Houphouët-Boigny | Abidjan | 45000 |
| 12 | Japan | JAP | Japan | True | 18623 | Panasonic Stadium Suita | Suita | 40322 |
| 1548 | Jordan | JOR | Jordan | True | 988 | Amman International Stadium | ʿAmmān (Amman) | 25000 |
| 16 | Mexico | MEX | Mexico | True | 22432 | Oakland-Alameda County Coliseum | Oakland, California | 63026 |
| 31 | Morocco | MOR | Morocco | True | 2260 | Complexe Sportif de Fès | Fès | 45000 |
| 1118 | Netherlands | NET | Netherlands | True | 1117 | Johan Cruijff ArenA | Amsterdam | 55885 |
| 4673 | New Zealand | ZEA | New-Zealand | True | 22451 | VFF Freshwater Stadium | Port Vila | 10000 |
| 1090 | Norway | NOR | Norway | True | 11603 | Ullevaal Stadion | Oslo | 27182 |
| 11 | Panama | PAN | Panama | True | 11535 | Estadio Rommel Fernández Gutiérrez | Ciudad de Panamá | 45000 |
| 2380 | Paraguay | PAR | Paraguay | True | 1213 | Estadio Antonio Aranda | Ciudad del Este | 28000 |
| 27 | Portugal | POR | Portugal | True | 1262 | Estádio Nacional | Jamor, Oeiras | 38000 |
| 1569 | Qatar | QAT | Qatar | True | 22430 | Khalifa International Stadium | Al Rayyan (Ar-Rayyan) | 45857 |
| 23 | Saudi Arabia | SAU | Saudi-Arabia | True | 22434 | EGO Stadium | Ad Dammām (Dammam) | 15000 |
| 1108 | Scotland | SCO | Scotland | True | 2617 | Hampden Park | Glasgow | 52500 |
| 13 | Senegal | SEN | Senegal | True | 22435 | Stade Me Abdoulaye Wade | Diamniadio | 50000 |
| 1531 | South Africa | SOU | South-Africa | True | 22436 | Peter Mokaba Stadium | Polokwane (Pietersburg) | 45264 |
| 17 | South Korea | SOU | South-Korea | True | 22429 | Yongin Mireu Stadium | Yongin | 37155 |
| 9 | Spain | SPA | Spain | True | 1456 | Estadio Santiago Bernabéu | Madrid | 85454 |
| 5 | Sweden | SWE | Sweden | True | 21411 | Strawberry Arena | Solna | 54329 |
| 15 | Switzerland | SWI | Switzerland | True | 1543 | kybunpark | St. Gallen | 20029 |
| 28 | Tunisia | TUN | Tunisia | True | 21412 | Stade olympique Hammadi-Agrebi | Radès | 65000 |
| 777 | Türkiye | TUR | Turkey | True | 22441 | Gürsel Aksel Stadyumu | İzmir | 30035 |
| 2384 | USA | USA | USA | True | 19357 | GEODIS Park | Nashville, Tennessee | 30109 |
| 7 | Uruguay | URU | Uruguay | True | 1624 | Estadio Centenario | Montevideo | 60235 |
| 1568 | Uzbekistan | UZB | Uzbekistan | True | 19547 | Paxtakor Markaziy Stadion | Toshkent (Tashkent) | 54170 |


### Rounds

- `Group Stage - 1`
- `Group Stage - 2`
- `Group Stage - 3`

### Standings

| rank | team_id | team | group | pts | played | W | D | L | GD | form |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 16 | Mexico | Group A | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 1531 | South Africa | Group A | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 17 | South Korea | Group A | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 770 | Czech Republic | Group A | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 5529 | Canada | Group B | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 1113 | Bosnia & Herzegovina | Group B | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 1569 | Qatar | Group B | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 15 | Switzerland | Group B | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 6 | Brazil | Group C | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 31 | Morocco | Group C | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 2386 | Haiti | Group C | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 1108 | Scotland | Group C | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 2384 | USA | Group D | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 2380 | Paraguay | Group D | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 20 | Australia | Group D | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 777 | Türkiye | Group D | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 25 | Germany | Group E | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 5530 | Curaçao | Group E | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 1501 | Ivory Coast | Group E | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 2382 | Ecuador | Group E | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 1118 | Netherlands | Group F | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 12 | Japan | Group F | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 5 | Sweden | Group F | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 28 | Tunisia | Group F | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 1 | Belgium | Group G | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 32 | Egypt | Group G | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 22 | Iran | Group G | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 4673 | New Zealand | Group G | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 9 | Spain | Group H | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 1533 | Cape Verde Islands | Group H | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 23 | Saudi Arabia | Group H | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 7 | Uruguay | Group H | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 2 | France | Group I | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 13 | Senegal | Group I | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 1567 | Iraq | Group I | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 1090 | Norway | Group I | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 26 | Argentina | Group J | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 1532 | Algeria | Group J | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 775 | Austria | Group J | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 1548 | Jordan | Group J | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 27 | Portugal | Group K | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 8 | Colombia | Group K | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 1568 | Uzbekistan | Group K | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 1508 | Congo DR | Group K | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 1 | 10 | England | Group L | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 2 | 3 | Croatia | Group L | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 3 | 1504 | Ghana | Group L | 0 | 0 | 0 | 0 | 0 | 0 |  |
| 4 | 11 | Panama | Group L | 0 | 0 | 0 | 0 | 0 | 0 |  |


### Fixtures

| fixture_id | date | round | home_id | home | away_id | away | venue_id | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1489369 | 2026-06-11T19:00:00+00:00 | Group Stage - 1 | 16 | Mexico | 1531 | South Africa |  | NS |
| 1538999 | 2026-06-12T02:00:00+00:00 | Group Stage - 1 | 17 | South Korea | 770 | Czech Republic |  | NS |
| 1539000 | 2026-06-12T19:00:00+00:00 | Group Stage - 1 | 5529 | Canada | 1113 | Bosnia & Herzegovina |  | NS |
| 1489370 | 2026-06-13T01:00:00+00:00 | Group Stage - 1 | 2384 | USA | 2380 | Paraguay |  | NS |
| 1489373 | 2026-06-13T19:00:00+00:00 | Group Stage - 1 | 1569 | Qatar | 15 | Switzerland |  | NS |
| 1489371 | 2026-06-13T22:00:00+00:00 | Group Stage - 1 | 6 | Brazil | 31 | Morocco |  | NS |
| 1489372 | 2026-06-14T01:00:00+00:00 | Group Stage - 1 | 2386 | Haiti | 1108 | Scotland |  | NS |
| 1539001 | 2026-06-14T04:00:00+00:00 | Group Stage - 1 | 20 | Australia | 777 | Türkiye |  | NS |
| 1489374 | 2026-06-14T17:00:00+00:00 | Group Stage - 1 | 25 | Germany | 5530 | Curaçao |  | NS |
| 1489376 | 2026-06-14T20:00:00+00:00 | Group Stage - 1 | 1118 | Netherlands | 12 | Japan |  | NS |
| 1489375 | 2026-06-14T23:00:00+00:00 | Group Stage - 1 | 1501 | Ivory Coast | 2382 | Ecuador |  | NS |
| 1539002 | 2026-06-15T02:00:00+00:00 | Group Stage - 1 | 5 | Sweden | 28 | Tunisia |  | NS |
| 1489380 | 2026-06-15T16:00:00+00:00 | Group Stage - 1 | 9 | Spain | 1533 | Cape Verde Islands |  | NS |
| 1489377 | 2026-06-15T19:00:00+00:00 | Group Stage - 1 | 1 | Belgium | 32 | Egypt |  | NS |
| 1489379 | 2026-06-15T22:00:00+00:00 | Group Stage - 1 | 23 | Saudi Arabia | 7 | Uruguay |  | NS |
| 1489378 | 2026-06-16T01:00:00+00:00 | Group Stage - 1 | 22 | Iran | 4673 | New Zealand |  | NS |
| 1489383 | 2026-06-16T19:00:00+00:00 | Group Stage - 1 | 2 | France | 13 | Senegal |  | NS |
| 1539016 | 2026-06-16T22:00:00+00:00 | Group Stage - 1 | 1567 | Iraq | 1090 | Norway |  | NS |
| 1489381 | 2026-06-17T01:00:00+00:00 | Group Stage - 1 | 26 | Argentina | 1532 | Algeria |  | NS |
| 1489382 | 2026-06-17T04:00:00+00:00 | Group Stage - 1 | 775 | Austria | 1548 | Jordan |  | NS |
| 1539003 | 2026-06-17T17:00:00+00:00 | Group Stage - 1 | 27 | Portugal | 1508 | Congo DR |  | NS |
| 1489384 | 2026-06-17T20:00:00+00:00 | Group Stage - 1 | 10 | England | 3 | Croatia |  | NS |
| 1489385 | 2026-06-17T23:00:00+00:00 | Group Stage - 1 | 1504 | Ghana | 11 | Panama |  | NS |
| 1489386 | 2026-06-18T02:00:00+00:00 | Group Stage - 1 | 1568 | Uzbekistan | 8 | Colombia |  | NS |
| 1539004 | 2026-06-18T16:00:00+00:00 | Group Stage - 2 | 770 | Czech Republic | 1531 | South Africa |  | NS |
| 1539005 | 2026-06-18T19:00:00+00:00 | Group Stage - 2 | 15 | Switzerland | 1113 | Bosnia & Herzegovina |  | NS |
| 1489387 | 2026-06-18T22:00:00+00:00 | Group Stage - 2 | 5529 | Canada | 1569 | Qatar |  | NS |
| 1489388 | 2026-06-19T01:00:00+00:00 | Group Stage - 2 | 16 | Mexico | 17 | South Korea |  | NS |
| 1489391 | 2026-06-19T19:00:00+00:00 | Group Stage - 2 | 2384 | USA | 20 | Australia |  | NS |
| 1489390 | 2026-06-19T22:00:00+00:00 | Group Stage - 2 | 1108 | Scotland | 31 | Morocco |  | NS |
| 1489389 | 2026-06-20T00:30:00+00:00 | Group Stage - 2 | 6 | Brazil | 2386 | Haiti |  | NS |
| 1539006 | 2026-06-20T03:00:00+00:00 | Group Stage - 2 | 777 | Türkiye | 2380 | Paraguay |  | NS |
| 1539007 | 2026-06-20T17:00:00+00:00 | Group Stage - 2 | 1118 | Netherlands | 5 | Sweden |  | NS |
| 1489393 | 2026-06-20T20:00:00+00:00 | Group Stage - 2 | 25 | Germany | 1501 | Ivory Coast |  | NS |
| 1489392 | 2026-06-21T00:00:00+00:00 | Group Stage - 2 | 2382 | Ecuador | 5530 | Curaçao |  | NS |
| 1489394 | 2026-06-21T04:00:00+00:00 | Group Stage - 2 | 28 | Tunisia | 12 | Japan |  | NS |
| 1489397 | 2026-06-21T16:00:00+00:00 | Group Stage - 2 | 9 | Spain | 23 | Saudi Arabia |  | NS |
| 1489395 | 2026-06-21T19:00:00+00:00 | Group Stage - 2 | 1 | Belgium | 22 | Iran |  | NS |
| 1489398 | 2026-06-21T22:00:00+00:00 | Group Stage - 2 | 7 | Uruguay | 1533 | Cape Verde Islands |  | NS |
| 1489396 | 2026-06-22T01:00:00+00:00 | Group Stage - 2 | 4673 | New Zealand | 32 | Egypt |  | NS |
| 1489399 | 2026-06-22T17:00:00+00:00 | Group Stage - 2 | 26 | Argentina | 775 | Austria |  | NS |
| 1539017 | 2026-06-22T21:00:00+00:00 | Group Stage - 2 | 2 | France | 1567 | Iraq |  | NS |
| 1489401 | 2026-06-23T00:00:00+00:00 | Group Stage - 2 | 1090 | Norway | 13 | Senegal |  | NS |
| 1489400 | 2026-06-23T03:00:00+00:00 | Group Stage - 2 | 1548 | Jordan | 1532 | Algeria |  | NS |
| 1489404 | 2026-06-23T17:00:00+00:00 | Group Stage - 2 | 27 | Portugal | 1568 | Uzbekistan |  | NS |
| 1489402 | 2026-06-23T20:00:00+00:00 | Group Stage - 2 | 10 | England | 1504 | Ghana |  | NS |
| 1489403 | 2026-06-23T23:00:00+00:00 | Group Stage - 2 | 11 | Panama | 3 | Croatia |  | NS |
| 1539008 | 2026-06-24T02:00:00+00:00 | Group Stage - 2 | 8 | Colombia | 1508 | Congo DR |  | NS |
| 1489408 | 2026-06-24T19:00:00+00:00 | Group Stage - 3 | 15 | Switzerland | 5529 | Canada |  | NS |
| 1539009 | 2026-06-24T19:00:00+00:00 | Group Stage - 3 | 1113 | Bosnia & Herzegovina | 1569 | Qatar |  | NS |
| 1489405 | 2026-06-24T22:00:00+00:00 | Group Stage - 3 | 31 | Morocco | 2386 | Haiti |  | NS |
| 1489406 | 2026-06-24T22:00:00+00:00 | Group Stage - 3 | 1108 | Scotland | 6 | Brazil |  | NS |
| 1539010 | 2026-06-25T01:00:00+00:00 | Group Stage - 3 | 770 | Czech Republic | 16 | Mexico |  | NS |
| 1489407 | 2026-06-25T01:00:00+00:00 | Group Stage - 3 | 1531 | South Africa | 17 | South Korea |  | NS |
| 1489410 | 2026-06-25T20:00:00+00:00 | Group Stage - 3 | 2382 | Ecuador | 25 | Germany |  | NS |
| 1489409 | 2026-06-25T20:00:00+00:00 | Group Stage - 3 | 5530 | Curaçao | 1501 | Ivory Coast |  | NS |
| 1539011 | 2026-06-25T23:00:00+00:00 | Group Stage - 3 | 12 | Japan | 5 | Sweden |  | NS |
| 1489412 | 2026-06-25T23:00:00+00:00 | Group Stage - 3 | 28 | Tunisia | 1118 | Netherlands |  | NS |
| 1539012 | 2026-06-26T02:00:00+00:00 | Group Stage - 3 | 777 | Türkiye | 2384 | USA |  | NS |
| 1489411 | 2026-06-26T02:00:00+00:00 | Group Stage - 3 | 2380 | Paraguay | 20 | Australia |  | NS |
| 1539074 | 2026-06-26T19:00:00+00:00 | Group Stage - 3 | 13 | Senegal | 1567 | Iraq |  | NS |
| 1489416 | 2026-06-26T19:00:00+00:00 | Group Stage - 3 | 1090 | Norway | 2 | France |  | NS |
| 1489417 | 2026-06-27T00:00:00+00:00 | Group Stage - 3 | 7 | Uruguay | 9 | Spain |  | NS |
| 1489413 | 2026-06-27T00:00:00+00:00 | Group Stage - 3 | 1533 | Cape Verde Islands | 23 | Saudi Arabia |  | NS |
| 1489414 | 2026-06-27T03:00:00+00:00 | Group Stage - 3 | 32 | Egypt | 22 | Iran |  | NS |
| 1489415 | 2026-06-27T03:00:00+00:00 | Group Stage - 3 | 4673 | New Zealand | 1 | Belgium |  | NS |
| 1489420 | 2026-06-27T21:00:00+00:00 | Group Stage - 3 | 3 | Croatia | 1504 | Ghana |  | NS |
| 1489422 | 2026-06-27T21:00:00+00:00 | Group Stage - 3 | 11 | Panama | 10 | England |  | NS |
| 1489419 | 2026-06-27T23:30:00+00:00 | Group Stage - 3 | 8 | Colombia | 27 | Portugal |  | NS |
| 1539013 | 2026-06-27T23:30:00+00:00 | Group Stage - 3 | 1508 | Congo DR | 1568 | Uzbekistan |  | NS |
| 1489418 | 2026-06-28T02:00:00+00:00 | Group Stage - 3 | 1532 | Algeria | 775 | Austria |  | NS |
| 1489421 | 2026-06-28T02:00:00+00:00 | Group Stage - 3 | 1548 | Jordan | 26 | Argentina |  | NS |


## Notes d'architecture

- `league_id` et `season` sont la cle de depart pour les championnats.
- `team_id` sert pour les stats equipe, squads, blessures par equipe et head-to-head.
- `fixture_id` est l'ID central d'un match. Il sert aux lineups, injuries, odds, events, statistics et predictions.
- `venue_id` est utile pour documenter le stade et detecter domicile/exterieur.
- Les IDs de bets prematch et live sont separes. Ne pas reutiliser un ID de `/odds/bets` dans `/odds/live`.
- Les squads et player IDs coutent beaucoup d'appels: lancer `--include-squads` seulement quand tu veux rafraichir cette reference.
