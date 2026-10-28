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


## openfootball has the matchweek; ESPN has the result (2026-10-12)

The TV Windows population is built from openfootball because it is the only
source with the official MATCHWEEK and the UK kickoff time, which is what
picks a window. Its RESULTS are another matter: on 12 October 2026 its
2026-27 file still had no score past 20 September, so the weekend's two cards
sat on the site blank while the Tottenham tab -- which reads ESPN -- had
Manchester United 1-1 Tottenham the same evening.

So a fixture whose kickoff has passed and which openfootball has no score for
now takes ESPN's, and only when ESPN calls it STATUS_FULL_TIME. openfootball
stays the authority wherever it does have the result, and a finished season
never needs this.

WHAT IS NOT WRONG, before anyone goes looking: the gap between MW5 on
20 September and MW6 on 10 October is real. ESPN has no Premier League match
on either weekend in between. And openfootball listing one fixture for most
of the later matchweeks is just a fixture list that is not published yet, not
data that has gone missing.


## A collapsed row group is invisible to gviz (2026-10-20)

games-history caught this on 2026-09-14; it reached this repo on 2026-10-20,
when his Tottenham tab read FORTY rows of 709 and the daily build published a
site stripped of every Footer, shade, border and kit he has ever written. He
had folded the old seasons away in the browser. Nothing was edited and
nothing was lost at his end -- gviz simply does not export a collapsed group.

THE FIX IS THE ONE games-history SETTLED ON (2026-10-19), mirrored here. Every
tab is remembered row by row in data/sheet-cache, and each build merges: a
date the LIVE read returns wins, and a date only the cache has stands in. So
he can work with the old seasons folded and the current one open, and the
daily build still picks up what he fills in.

  an edit needs the row OPEN THROUGH A BUILD, not merely while he types
  a new row in an open group is live from the first build that sees it
  a collapsed row keeps whatever it last said

THE CACHE CANNOT FORGET. A deleted row and a collapsed row are both simply
absent, so a deleted row stands in for ever. To retire one, BLANK ITS CELLS --
an edit, which wins. To drop it for real: expand everything and run
`python harvest.py --resnap`.

THE FLOORS ARE THE BACKSTOP, not the mechanism: Tottenham 600, USMNT 120,
Atlanta 45, well under the real counts. They catch a read that fails even
with the cache merged in, and abort rather than publish an empty site.

THE FLOOR COUNTS ROWS SEEN, NOT ROWS MARKED -- the first version of it
counted marked rows and aborted on the USMNT tab, which has 140 rows and no
annotations at all because he has not started on it. Every dated row is
cached, blank ones included; only the marked ones reach a card.

THE CACHE WAS SEEDED from the games.json of the last good build (19 October,
08:39), since his rows were collapsed at the time and a live read could not
have done it. 710 rows, carrying 207 Footers, 137 shades, 90 borders and 705
colour sets. `say` and `say_pre` were left out on purpose: they are worked
out FROM the footer during the build and were never cells of his.


## Extra time needs TWO sources, and the guard it sits in matters (2026-10-27)

He asked for the extra-time mark to be spot-checked, the same test having
been written twice -- once in harvest.py for his own cards and once in
rivals.py. Checking it against its own rule would have proved nothing, so all
194 knockouts on the two tabs were checked against ESPN'S OWN full-time
STATUS instead. Three things came out of it:

THE AUDIT'S FIRST RUN WAS ITSELF WRONG. It read STATUS_FINAL_PEN as "not
extra time" and reported nine Tottenham disagreements that were not. A
penalty shootout is past ninety minutes; the test had to say so.

ESPN'S STATUS IS NOT ENOUGH ON ITS OWN. It files the 2013 League Cup
quarterfinal against Sunderland as STATUS_FULL_TIME, and its own goal list
has the winner in the 118th minute. The goal list stays the first word.

NOR IS THE GOAL LIST. Chelsea against Real Madrid in 2022 had no goal list
stored at all -- an ESPN failure on some earlier run, left unread by design
rather than remembered as goalless -- so nothing marked a tie that went to
extra time. Both are asked now, and either is enough.

AND THE FLAG WAS IN THE WRONG PLACE. Set from the status, it first went
inside `if m["result"] in ("D", "L")`, the guard that looks for the
OPPONENT'S late goals. Chelsea WON that second leg 3-2 and went out on
aggregate, so the guard skipped it. Extra time is a fact about the match, not
about how it went for them.

Afterwards: Tottenham 129 knockouts, 0 disagreements; the rivals' 65, one --
the Sunderland tie, where ESPN is the one that is wrong.


## Everything, checked against an outside source (2026-10-28)

He asked for the whole archive to be audited the way the extra-time mark was.
Four checks, against sources the build does not use for the thing being
checked. ONE REAL ERROR in 1,297 league cards, and three false alarms that
were all the audit's own fault -- worth recording, because the same shapes
will come back.

SCORES: every Premier League card, on all three tabs, against the Premier
League's own fixtures feed -- 1,297 with a result, matched by (season, home,
away) so no date or timezone could confuse it. EVERY NAME MATCHED and NOT ONE
SCORE DISAGREED. That is the strongest guarantee this archive has.

KICKOFFS: one disagreed of 1,297. Tottenham v Southampton, 8 May 2016, which
ESPN files 90 minutes late at 15:00 BST; openfootball and the league both say
13:30. The card read 10:00am Eastern and now reads 8:30. It is in
harvest.KICKOFF_FIX, keyed by event id.

MATCHWEEKS: 42 disagreed, and OURS ARE RIGHT. The league's own "gameweek"
counts the round AS PLAYED -- 2013-14 runs to FORTY, and its weeks hold
anywhere from 3 to 17 fixtures. openfootball's matchday is the round a
fixture BELONGS to: 380 fixtures, 38 matchdays, exactly ten in each. This is
why BRIEF.md calls openfootball the only source with the official matchweek.
It also closes the one 2025-26 disagreement left hanging on 2026-10-12: with
the fixtures keyed properly there is none.

WHO WENT THROUGH: all 25 of his second legs and all 22 collapsed rival ties,
against whether they actually played a later round. Nothing contradicted.

THE TWO TV SOURCES: 41 Premier League cards where ESPN and the league's
listing both speak. No clash.

THE THREE FALSE ALARMS, all mine:

  the first run read STATUS_FINAL_PEN as "not extra time" and cried wolf on
  nine Tottenham knockouts. A shootout is past ninety minutes.

  the tie check ranked "Group Stage" below a qualifying round, so Tottenham
  reaching the 2021-22 Conference League GROUP STAGE from the playoff round
  looked like a side that had gone out.

  the TV check asked the PREMIER LEAGUE'S listing about League Cup, FA Cup
  and Europa League ties and found six "clashes". harvest only ever asks it
  about PL matches -- the gate is `if code == "PL"` -- and everything else
  goes to livesoccertv. Restricted properly: no clash at all.

THE LESSON, twice over now: when an audit disagrees with the data, suspect
the audit first. Three of the four alarms here were the checker, not the
checked.
