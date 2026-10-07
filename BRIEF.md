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
- **Qualifiers and the Super Cup are in.**
- **Two score boxes**, his team's and the opponent's, each coloured from the
  Sheet (Team BG / Team Font / Opp BG / Opp Font). No rank box.
- **Knockouts** (not Finals): European knockout rounds, plus FA Cup and
  League Cup semis and finals.
- **USMNT and Atlanta cards need no TV** -- day, date and time only.
- **Sheet:** `1sDNdbA0dlk7BBIoURKhwau4VJM7BXYxdUMo9aPdpfjo`, tabs Tottenham,
  USMNT, Atlanta United, columns as in harvest.SHEET_COLS. **No Kit column**
  (he dropped it). He deleted the Michigan tabs, so Tottenham is the FIRST
  tab -- a missing tab is detected by its dates not matching, not by body.
- **USMNT home/away:** every tournament match is neutral; only World Cup
  qualifying and the Nations League group games and two-legged
  quarterfinals keep home and away.
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

Tabs for Tottenham (737 matches), USMNT (140) and Atlanta (56). Tottenham: Year /
Competition / Team / Highlights (Late Winners, Late Equalizers) filters, a
Finals button, Oldest/Newest. Qualifiers and the 2025 Super Cup are included
(confirmed). Not yet: rivals, TV windows,
the daily build.

## EPL/Rivals tab (built 2026-09-24)

Second tab, two views (a segmented bar, as in games-history):

- **TV Windows** -- every Saturday and Sunday window match since 2013-14,
  748 of them, by matchweek. Fixtures and UK kickoff times from openfootball;
  ESPN gives the US network (2024-25 on) and the crests. THE SUNDAY WINDOW
  MOVED: 16:00 UK to 2018-19, 16:30 from 2019-20 -- read per season, with the
  other time taken when a matchweek has nothing at the usual one (2016-18 used
  both). Saturday is 17:30 UK throughout. Upcoming only to the coming Sunday.
- **Rivals** -- 281 results: Arsenal 203, Chelsea 78, opening on every year,
  newest first. Arsenal's rule is applied across ALL competitions.

Both draw a TWO-TEAM card (away line over home line, the winner washed), not
his one-opponent card. A shootout decides the winner, and the header says
"Pens 5-4".

## Suggested order

1. Confirm the OPEN items above with Kyle.
2. Verify ESPN league slugs and team ids; find the matchweek source.
3. Harvest Tottenham 2013-14 onward; build the Tottenham view to parity with
   Michigan football; publish.
4. Generate the Sheet CSVs; wire the Sheet in.
5. Rivals, then Premier League TV windows, then USMNT, then Atlanta United.
6. The daily build.

## Card shapes (Kyle, 2026-10-02)

The matchweek sits in BRACKETS and loses its bar: `[MW1] Sunday 9:00 AM`.
The channel is spelled out: USA is **USA Network**.

A LEAGUE match keeps the day up top and the rest below:

    [MW1] Sunday 9:00 AM
    4/12/2026 | USA Network

and when the card has something of its own to say, the date and network move
up beside a shortened day so the bottom line is his alone:

    [MW1] SUN 9:00 AM | 4/12/2026 | USA Network
    Son 12', Kane 64'

A CUP OR A EUROPEAN NIGHT names the round up top, so its day, date and network
already have a line to themselves -- and a SCORER LIST takes a FOURTH line:

    UCL SEMIFINALS (2ND LEG: 3-3 AGG)
    at Ajax  3  2
    WED 5/8/2019 | TNT 3:00pm
    Llorente 87', Moura 90'+5

A LONE LATE WINNER IS NOT WORTH THAT FOURTH LINE (2026-10-06): its date goes
up to the end of the header and the line below opens with the network --

    UEL GROUP STAGE | THU 11/5/2015
    Anderlecht  2  1
    ESPN3 3:05pm | Dembele 87'

A TV WINDOW keeps that shape, the window standing in for the day:

    [MW9] Sky Super Sunday 12:30pm
    10/26/2025 | USA Network

and his details take a third line below. Saturday's window already says NBC,
so its line below says the network only when it was somewhere else.

THE TV WINDOWS AND RIVALS CARDS put it all in the header instead, since they
have nothing below the two clubs: `[MW1] NBC Saturday 12:30pm | 8/22/2026`,
`[MW1] Sky Super Sunday 11:30am | 8/23/2026`. NO NETWORK on these -- naming it
too was what pushed 126 of the 748 onto a second line at 410px, and he would
rather lose the network than the one line (his call 2026-10-02). Saturday's
window still says NBC, since that is the window's name. The header is built as
separate fields, so where one does wrap it breaks between them and the bar
leads the line it continues onto.

`[MW1] Sky Sunday 11:30am | 8/23/2026`: the Sunday window is called SKY SUNDAY
(his call 2026-10-02). The filter's options must read exactly as windows.py
labels a match -- an option saying "Super Sunday" while the matches said "Sky
Super Sunday" found nothing, which is how he caught it.

HIS TEAM'S SCORE BOX ALWAYS COMES FIRST (his call 2026-10-05), home, away or
on neutral ground. The cards read home-then-away from 2026-09-21 until then.

THE EPL/RIVALS TAB (his calls 2026-10-02): its Year menu reads seasons,
2026-27, as his own tab does; the Top Six AND TOTTENHAM wear capitals on the
cards; and the Team menu is grouped exactly as the Tottenham tab's, Tottenham
at the head of the Top Six. A TV Windows match names two clubs rather than an
opponent, so the English set reads both off the card.

HIS TOTTENHAM MARKS on the TV Windows cards, as Michigan's TV windows read:
a WHITE border on a Tottenham win or a draw with the Top Six, a DASHED GREY
one on a loss or a draw with anyone else, and a win over the Top Six FILLS
the card. ESPN paints Tottenham white, which washes out to a flat grey, so
the fill uses the navy. Cards without Spurs wear nothing.

SCORERS: every Tottenham goal, on a WIN OR A DRAW with the Top Six (65 cards).
Not on a loss. ARSENAL AND CHELSEA ARE NEVER IN BOLD -- a win of theirs is
washed like anyone's, but their name and score stay plain.

## European cards and two-legged ties (Kyle, 2026-10-06)

Europe reads SHORT, with no season and no colon: `UEL Group Stage`,
`UCL Round of 16 (1st Leg)`. Only a FINAL keeps a year, and a single one:
`2019 UCL Final | Madrid`.

HOW IT ENDED GOES AT THE END OF THE HEADER (2026-10-06), so nothing rides
beside the score boxes any more:

    FA Cup Quarterfinals (4-3 Pen)
    FA Cup Fifth Round (ET)
    UEL Round of 16 (2nd Leg: 3-3 agg, 4-3 Pen)
    2025 UEFA Super Cup (4-3 Pen) | Udine

A shootout always follows extra time, so ET is said only when there was no
shootout, and it reads LAST -- after a final's city, as the Super Cup shows.

HEADER COLOURS (2026-10-06): both domestic cups wear theirs only from the
SEMIFINALS, where the ties move to Wembley -- the FA Cup #d71921, the League
Cup #008f5e -- and read plain grey before that. Europe wears its colour
throughout: UCL #5b9bea, UEL #f68e1f, UECL #2fc27a, and the Super Cup a gold
of its own, #d4af37. A EUROPEAN FINAL spells its
competition out -- `2019 Champions League Final | Madrid` -- where every other
European night is short. A NIGHT INSIDE A TIE HE WON IS NOT A DEFEAT, so its score is not
italic either -- City 2019 stands upright at 3-4.

A TIE IS ONE RESULT, so the tie decides how each night reads, not the night's
own score. Three marks, set separately: the colour bar, the bold name, the
strike through it.

| tie   | leg | that night | bar | bold | struck |
|-------|-----|------------|-----|------|--------|
| won   | 1   | won        | yes | yes  | no     |
| won   | 1   | level      | yes | no   | no     |
| won   | 1   | lost       | no  | no   | **no** |
| won   | 2   | won        | yes | yes  | no     |
| won   | 2   | level/lost | yes | no   | no     |
| lost  | 1   | won        | yes | **no** | no   |
| lost  | 1   | level      | no  | no   | no     |
| lost  | 1   | lost       | no  | no   | yes    |
| lost  | 2   | won        | no  | no   | no     |
| lost  | 2   | level/lost | no  | no   | yes    |

A level first leg of a LOST tie settled nothing either way, so it reads plain
grey -- he did not rule on that one.

WHO WON THE TIE is worked out in two_legged(): the aggregate, then a shootout,
then away goals (Europe only, to 2020-21), and BOTH legs carry the answer. A
SHOOTOUT AFTER THE SECOND LEG settles the tie and not the match, so it is
never read while the match is built -- the 2019 League Cup semi was a 1-2
defeat on the night, 2-2 over the two, and Chelsea took it 4-2 on penalties.
That was the last tie whose outcome was unknown; all 25 are now settled.

## Highlights: his own two marks (Kyle, 2026-10-06)

The Highlights menu leads with his own two marks and follows with the late
goals the harvest found: SPECIAL, MEMORABLE, LATE WINNERS -- the equalizers
sit under the winners too, loose label and all (2026-10-06). A LATE GOAL
INSIDE A TIE counts only on the second leg of a tie he went through: it
settles nothing in a first leg, and nothing in a second leg he went out of.
A NETWORK menu sits beside them on his own tab, his six first, then a bar,
then the rest alphabetically.
Special is a WHITE border in his sheet OR a trophy won -- 9 nights, the
trophy being the 2025 Europa League. Memorable is any shade or border at all,
62. Every special night is memorable too. Both read live off the Border and
Shade columns, so colouring a row in the sheet is all it takes to add one.

TWO DATES ARE SPELLED OUT (2026-10-06): City away on `Feb 19, 2022`, and
every WIN on 21 September whatever the year -- `Sep 21, 2016`, `Sep 21,
2024`. Everything else stays 9/22/2013.

INK THAT VANISHES INTO A LIGHT BOX is darkened until it can be seen: his
European kits put #d9d9d9 on #ffffff, which reads at 1.4:1 and is simply not
there on a phone, and comes out around #a6a6a6. A DARK box is left alone --
Palace's red on blue and City's white on sky are his kits and his business.

## His Footer column asks for a line (Kyle, 2026-10-07)

FOOTER = "Scorers" puts the whole Tottenham list on a card the Top Six rule
would not give one: every West Ham meeting, the 5-4 at Leicester, the 4-0 at
Villa. FOOTER = "Late Winner" puts the late goals there, as on the 2-2 at
Sheffield United that won the tie but was no win on the night. Neither word
is printed -- it is an instruction, not a note. A Footer value that is a
COLOUR WORD still paints the line, and one that is a PHRASE still prints.

Every match therefore keeps its scorer list and its late goals through the
harvest, under _scorers and _late, dropped before the file is written.
