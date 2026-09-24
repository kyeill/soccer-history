# Soccer History — how it works

Live: https://kyeill.github.io/soccer-history/ · repo: kyeill/soccer-history

Four tabs: **Tottenham**, **EPL/Rivals** (TV Windows and Rivals), **USMNT**,
**Atlanta**. `harvest.py` writes `output/games.json`, `site.py` builds `docs/`,
and GitHub Pages serves `docs/` from `main`. A GitHub Actions job rebuilds it
every day at 6am Eastern.

## The pieces

| file | what it does |
| --- | --- |
| `harvest.py` | Tottenham 2013-14 on, plus the shared helpers (ESPN fetch + cache, stage names, matchweeks, standings, his Google Sheet) |
| `others.py` | USMNT from 2010 and Atlanta United from 2017 |
| `rivals.py` | Arsenal's and Chelsea's bad results |
| `windows.py` | the two Premier League TV windows |
| `tv.py` | US networks for Premier League matches |
| `site.py` | builds `docs/` (CSS, HTML shell, icons, service worker) |
| `app.js` | the whole page |
| `sheet_csv.py` | writes `sheet/*.csv`, the files he imports as Sheet tabs |

`data/` is committed and holds what is slow to rebuild and never changes: goal
lists, opponent finishes, team details, the USMNT chain, TV listings.
`cache/` is raw ESPN answers and is NOT committed (Actions caches it).

## Traps already paid for

- **Matchweeks come from openfootball, not ESPN** (ESPN has none) and not from
  the Fantasy Premier League API, which renumbers a postponed match into the
  gameweek it was played in. openfootball has three line layouts across the
  years, and its round headings read either "Matchday 5" or "Regular Season - 5".
- **The Sunday TV window moved**: 16:00 UK to 2018-19, 16:30 from 2019-20.
  Saturday has been 17:30 UK throughout. The windows are defined by UK kickoff
  time so the clock-change weeks are not lost.
- **US networks**: ESPN has none before 2024-25 anywhere (public API, core API,
  scoreboards). The Premier League's own service has every match from 2016-17.
  Nothing has 2013-14 to 2015-16.
- **Shootouts**: read `shootoutScore` from the match summary. ESPN's text note
  is missing on some matches (Chelsea's 2013 Super Cup) and names Spurs
  inconsistently ("Spurs win 8-7 on penalties").
- **ESPN marks no match neutral**, not even finals. Neutral is decided here:
  finals, FA Cup semi-finals, the Super Cup, and every USMNT tournament match.
- **ESPN's team schedule is incomplete for national teams** — whole rounds are
  missing (2015-16 qualifiers, the 2021 Nations League final), and its core API
  drops the same ones. `others.py` chains back through match summaries instead.
- **A few summaries list every goal twice** (Barnsley 2017, West Ham 2018), and
  Rennes 2021 was awarded 3-0 without being played.
- **An unknown Google Sheet tab returns the FIRST tab**, so a tab is accepted
  only when its dates match that team's matches — comparing bodies breaks now
  that Tottenham is the first tab.
- **`output/` must not go stale**: if the daily build has run since your last
  local harvest, re-harvest before building, or a build will overwrite fresh
  data with old.
