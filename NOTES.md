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
- **US networks**, in three layers (`tv.py`): ESPN from 2024-25; the Premier
  League's own service (footballapi.pulselive.com) for league matches from
  2016-17; and livesoccertv's daily schedule pages for everything else,
  including 2013-16 and the older cup and European nights. livesoccertv
  refuses a plain fetcher, needs a browser User-Agent, and writes a channel a
  dozen ways ("Fox Sports 2 USA", "NBCSN (United States)"), so names are
  cleaned and looked up in a table; radio, carriers and club sites are
  dropped. Its rows carry `class="matchrow"` OR an empty class, so rows are
  found by `data-ko`. NEVER cache a failed page as "no TV" -- that silently
  blanked 657 matches on the first run.
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

## livesoccertv names clubs its own way (2026-10-05)

Its day pages carried a US channel for 38 Tottenham cup and European nights
that were reading as "no TV", under a name the harvest did not recognise:
their Sheriff is our Sheriff Tiraspol, their CSKA Moskva our CSKA Moscow,
their Crvena Zvezda our Red Star Belgrade, their Ajax our Ajax Amsterdam,
their Skendija 79 our KF Shkendija. Matching both club names will always lose
that race, so lstv_find falls back to ONE side: a club plays at most one
senior match a day, so a row whose home is ours or whose away is ours names
the match, as long as exactly one row does. A youth side keeps its U19 and so
never matches.

TWO TRAPS while fixing it:
- A STORED ANSWER THAT CLEANED TO NOTHING was never recomputed. Three FA Cup
  ties held ["FOX Deportes"] from an earlier run, which his hidden list drops,
  so the card stayed blank even after "FOX Network" was taught to the channel
  table. Entries whose clean() is empty have to be dropped, not just the
  empty ones.
- A DAY PAGE THAT FAILED TO FETCH stays missing, since nothing is stored for
  it. 2015-12-10 had been missing since the first run and came down on the
  first retry.

71 -> 33 (95.3% of his 704 played matches carry a network). What is left is
his own doing or genuinely nothing: 15 list only a channel he removed (beIN,
FOX Deportes, FOX Soccer Plus, TUDN, Univision), 8 carry no US channel at
all, 8 only a carrier or a regional network, 2 only SiriusXM radio.

## A blank header used to hide every column after it (2026-10-06)

load_sheet read only the block BEFORE the first headerless column, so working
columns he keeps in the middle of his sheet would have hidden his kit colours
to their right. Every column is read by its NAME now and a headerless one is
skipped; where a name repeats, the leftmost wins. 10 marked rows became 135.

## The two clocks are already handled -- do not "fix" them (2026-10-09)

A window is chosen on the UK clock and only then converted to Eastern, which
is the whole point of reading UK times (his call 2026-09-21). So the few weeks
each year when the two countries' clocks are out of step need no special case
at all: the match is found, and the card simply reads an hour later.

  NBC Saturday  286 cards at 12:30 ET and  11 at 1:30pm -- same 17:30 UK
  Sky Sunday    208 cards at 11:30am and   15 at 12:30pm -- same 16:30 UK
                123 cards at 11:00am and   13 at 12:00pm -- same 16:00 UK

All 39 of the late ones fall in the two annual gaps and nowhere else: 8-23
March (the US springs forward on the second Sunday, the UK on the last) and
25 October - 6 November (the UK falls back on the last Sunday of October, the
US on the first of November). Nothing has ever been lost to this.

WHAT LOOKS LIKE CLOCK DRIFT AND IS NOT: a kickoff that simply moved. The five
windows missing from 2025-26 were at 15:30, 15:30, 17:30, 16:30 and 17:30 UK,
and on every one of those days the OTHER matches were at textbook times --
14:00, 15:00, 12:30 -- so no date was ever stored in the wrong zone. A whole
day shifts together or not at all; that is the test to run before believing a
timezone bug.
