# Soccer History — build brief

Written 2026-09-21 at the end of the games-history session, for the chat that
builds this app. Read all of it before writing code. Kyle's words are
paraphrased closely; where something is still open it says so.

## What it is

A separate app, **Soccer History**, in this folder, published the same way as
games-history (GitHub repo + GitHub Pages, `docs/` served from `main`, a 6am
Eastern daily build in Actions). It must not share code or data files with
games-history at runtime. Copying patterns and code from it is encouraged.

**Reference implementation:** `..\games-history\` (live at
https://kyeill.github.io/games-history/, repo github.com/kyeill/games-history).
The **Michigan views** there are the model for Tottenham — study `app.js`
(`michCard`, the filter bar, `highlightOf`, `JERSEYS`), `harvest.py`
(`load_sheet`, `SHEET_TABS`, the schedule harvests) and `site.py`. Its
`NOTES.md` records why things are the way they are.

It is **mostly history**. The only forward-looking parts are upcoming
Tottenham matches and the upcoming Premier League weekend windows.

## Scope

### 1. Tottenham Hotspur — the main event, from 2013-14

Every competitive match: score, date/time, US TV, competition details.
"Essentially mirror the features we have for Michigan."

- **Competition filter:** Premier League, FA Cup, League Cup, UCL, UEL, UECL.
- **Location:** home / away / neutral, with the city or venue on neutral
  ground and cup finals (Wembley etc.) — the way Michigan cards do it.
- **Late winners:** a filter for matches Spurs won with a goal in the **80th
  minute or later** (stoppage time included). Define it as the goal that put
  Spurs ahead for good.
- **Late equalizers:** 80'+ as well, but **only against the Top Six** (Arsenal,
  Chelsea, Liverpool, Man United, Man City).
- **Opponent's final placement**, like Michigan's final ranking / playoff
  finish after the opponent's name: for a Premier League opponent its final
  league position; for a cup opponent from another league, **how far it went
  in that competition**.
- **No rankings.** Soccer has no poll, so drop the rank column entirely and
  let the crest and name start further left. **The one exception:** the new
  (2024-25 on) league-phase format in the European competitions — in their
  knockout rounds, show the league-phase position **in line with the name**,
  the way conference-tournament seeds sit on Michigan basketball cards
  (`rankAfter` / `.rkaft` in games-history).
- Everything else Michigan has, adapted: Year and Team filters, Highlights,
  a Postseason-style button where it makes sense, Oldest/Newest First, Sheet-
  driven fills, borders, capitals, notes, footer colours, attended.

### 2. Rivals — Arsenal and Chelsea, from 2013-14

Their bad results, filtered by how their season went:

- **In a season Arsenal finished top four:** every draw and loss, EXCEPT
  draws against Chelsea, Liverpool, Man City or Man United, and EXCEPT losses
  to Chelsea.
- **In any other season:** losses only, EXCEPT losses to Chelsea.
- **In-season** nobody knows the final table, so include everything that
  could qualify until the season ends, then apply the rule.
- A loss to Spurs always counts (it's a Spurs win).
- **OPEN — confirm with Kyle:** he spelled the rule out for Arsenal only. The
  obvious mirror for Chelsea is the same rule with Arsenal and Chelsea swapped
  (draws vs Arsenal/Liverpool/City/United excused in a top-four season; losses
  to Arsenal excluded). Ask before building it.

### 3. Premier League TV windows

Two windows, **Eastern time**:

- **Saturday 12:30 pm** (the NBC match)
- **Sunday 11:30 am** (ideally Sky's Super Sunday in the UK; US network varies)

At most **one match per window**; some matchweeks have none (midweek rounds
especially). Include upcoming matches through the coming weekend, as
games-history's TV Windows does.

**Everything Premier League is organised by MATCHWEEK**, and matchweeks are
sometimes played out of order (postponements, cup clashes). ESPN's soccer feed
may not carry the matchweek at all — **research a source for it first.** Check
whether ESPN's event data has it; if not, look at the Fantasy Premier League
API (`fantasy.premierleague.com/api/fixtures/`, field `event`) for the current
season and a historical fixtures dataset for past ones.

**OPEN — confirm with Kyle:** for the few weeks each spring and autumn when
the UK and US change clocks on different dates, a 5:30 pm UK kickoff lands at
1:30 pm ET, not 12:30. Defining the windows by **UK kickoff time** (17:30
Saturday, 16:30 Sunday) avoids losing those weeks. Recommend that.

### 4. USMNT — every competitive match from 2010

Men only, **absolutely zero friendlies.** World Cup, World Cup qualifying,
Gold Cup, Nations League, Copa América. Always show which competition (and
round/stage) a match belongs to. Olympic teams are not the senior side — leave
them out unless he says otherwise.

### 5. Atlanta United — the unusual matches, from 2017

Everything EXCEPT MLS regular season: MLS Cup playoffs, CONCACAF Champions
League / Champions Cup, Leagues Cup, U.S. Open Cup, Campeones Cup.
**OPEN:** the 2020 "MLS is Back" tournament — ask whether it counts.

## Google Sheet

Kyle wants **a Sheet tab for each of his three teams — Tottenham, USMNT,
Atlanta United** — mirroring the Michigan tabs: the same columns (shade,
border, case/capitals, note, footer, attended, box colours) plus a **Kit**
column in place of Michigan's uniform columns. Columns are found by NAME,
never by position (see `load_sheet` in games-history).

**OPEN:** a new Google Sheet, or new tabs in the games-history one? Ask.
Then generate CSVs of every match for him to paste in, as was done for the
Detroit tabs (he pastes; you don't write to his Sheet).

## Data: ESPN, and its traps

ESPN's public API covers all of this:
`https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/...`
League slugs to verify: `eng.1` (Premier League), `eng.fa`, `eng.league_cup`,
`uefa.champions`, `uefa.europa`, `uefa.europa.conf`, `usa.1`,
`concacaf.champions`, `concacaf.leagues.cup`, `usa.open`, `campeones.cup`,
`fifa.world`, `fifa.worldq.concacaf`, `concacaf.gold`,
`concacaf.nations.league`, `conmebol.america`.
Team ids to verify: Tottenham 367, Arsenal 359, Chelsea 363, Liverpool 364,
Man United 360, Man City 382, Atlanta United 18418, USA men 660.
Goal minutes for late winners come from the match `summary` endpoint
(`keyEvents` / `scoringPlays`).

Traps already paid for (see memory `reference_espn_api_sept_2026.md`):

- A scoreboard **date range** answers HTTP 400 — walk ranges one day at a time.
- A scoreboard `limit` above ~500 silently returns 25 games — cap at 500.
- `seasontype` must be explicit on team schedules.
- A green CI run can hide an empty ESPN answer — check counts, don't trust
  exit codes.
- Cache past seasons (they never change); never cache the upcoming window.

## Build and publish habits (from games-history)

- `harvest.py` writes `output/`; `site.py` builds `docs/`; push deploys.
- **`output/` must not go stale:** if the cloud build has run since your last
  local harvest, re-harvest before building, or you will overwrite fresh live
  data with old data (this happened on 2026-09-21).
- The daily build: two UTC crons and a guard that only proceeds at 6am New
  York time (copy `games-history/.github/workflows/daily.yml`). Commit the
  caches it needs.
- Google Sheet via the gviz CSV endpoint. **An unknown tab name silently
  returns the FIRST tab** — detect and skip it.
- Write multi-line edit scripts to the scratchpad with the Write tool; bash
  heredocs mangle backslashes.
- Rebase before pushing — the daily build may have pushed first.

## How Kyle works (also in memory)

- **Verify at phone width (410 px) before every publish**, then commit, push,
  and poll the live site until the change is really there.
- End every reply with a **Questions** section.
- He has no coding background: spell out his action items plainly (paste this
  CSV into that tab, etc.).
- He iterates fast, one card detail at a time — keep each change small,
  publish it, and report what changed in a sentence or two.
- He makes the design calls; when a rule is ambiguous, ask rather than guess.

## Decisions (Kyle, 2026-09-21)

- **Chelsea:** no Premier League tracking at all — only Chelsea's European and
  domestic cup matches (FA Cup, League Cup, UCL/UEL/UECL). The Arsenal rule
  above stays as written. **Chelsea's draws and losses all count.** A match
  settled on penalties counts as a win for whoever advanced (a shootout exit
  is a loss, and it counts).
- **TV windows** go back to **2013-14**, not just the current season.
- **Repo:** public `kyeill/soccer-history`, Pages at kyeill.github.io/soccer-history.
- **TV windows:** defined by **UK kickoff time** — Saturday 17:30, Sunday
  16:30 UK.
- **Atlanta United:** the 2020 "MLS is Back" tournament is **out**.
- **Google Sheet:** a **new** Sheet for Soccer History, not the games-history
  one. Kyle creates it and shares the link.

## Research results (2026-09-21)

- **All 16 ESPN league slugs above are valid** (a bad slug answers HTTP 400,
  so a 200 is real). All 8 team ids are correct.
- **ESPN has no matchweek** on schedule events (no `week` field anywhere).
- **Don't use FPL's `event` as the matchweek.** It's the fantasy gameweek,
  and FPL moves postponed matches into it: Man City v Arsenal 2019-20 (played
  17 June 2020) is FPL event **39**.
- **Use openfootball** instead:
  `raw.githubusercontent.com/openfootball/england/master/{YYYY-YY}/1-premierleague.txt`.
  It covers every season from 2013-14, keeps the official matchweek
  (that match is under "Matchday 28"), and gives **UK local** kickoff times.
  It auto-updates weekly, and 2026-27 is current. Parse it for `(matchday,
  home, away)`. Take the date and time from ESPN, and join on the teams
  (each home/away pairing happens once a season). Club names need a mapping
  ("Arsenal FC" vs ESPN "Arsenal").

## Built so far (2026-09-21)

Tottenham view, 737 matches 2013-14 to the current fixtures: Year /
Competition / Team / Highlights (Late Winners, Late Equalizers) filters, a
Finals button, Oldest/Newest. Qualifiers and the 2025 Super Cup are included
(pending Kyle's OK). Not yet: the Sheet, rivals, TV windows, USMNT, Atlanta,
the daily build.

## Suggested order

1. Confirm the OPEN items above with Kyle.
2. Verify ESPN league slugs and team ids; find the matchweek source.
3. Harvest Tottenham 2013-14 onward; build the Tottenham view to parity with
   Michigan football; publish.
4. Generate the Sheet CSVs; wire the Sheet in.
5. Rivals, then Premier League TV windows, then USMNT, then Atlanta United.
6. The daily build.
