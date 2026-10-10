"""The two Premier League TV windows, 2013-14 on -> the TV Windows view.

HIS WINDOWS ARE UK KICKOFF TIMES (his call 2026-09-21), not Eastern ones:
Saturday 17:30 and Sunday 16:30 in England. That keeps the few weeks each
spring and autumn when the two countries change their clocks on different
dates and the match lands at 1:30pm ET instead of 12:30.

The fixtures come from openfootball, which is the only source with the
official MATCHWEEK (see BRIEF.md). ESPN supplies the US network, which it
only really has from 2024-25 on, and the ESPN ids behind the crests.
"""
import datetime as dt
import re
import harvest as h
import tv

# SATURDAY is 17:30 UK in every season. SUNDAY MOVED: the late Sky game was
# 16:00 UK to 2018-19 and 16:30 from 2019-20, so the window is read per era --
# with the other time accepted when a matchweek has no match at the usual one
# (2016-18 used both).
SATURDAY, SUNDAY_LATE, SUNDAY_EARLY = "17:30", "16:30", "16:00"


def sunday_time(season):
    return SUNDAY_LATE if season >= 2019 else SUNDAY_EARLY


def dow(f):
    return dt.date(*map(int, f["date"].split("-"))).strftime("%a")


# THE LAST DAY HAS NO WINDOW (his call 2026-10-09): all ten matches kick off
# together, so neither broadcaster has a game of its own that afternoon.
LAST_MD = 38

# WHICH GAME WAS THE SHOWCASE, when the clock cannot say: the one the biggest
# US channel took. Only used to break a tie in the Sunday fallback below.
CHANNEL = ["NBC", "USA Network", "NBCSN"]


def channel_rank(nets):
    for i, c in enumerate(CHANNEL):
        if c in nets:
            return len(CHANNEL) - i
    return 0
# ESPN carries next to no US broadcast before this (3-11 matches a season), so
# the older windows are not worth a call a day for
TV_FROM = 2024
MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def parse(season):
    """Every match of a Premier League season from openfootball:
    {md, date, uk (HH:MM), home, away, hs, as}. Three layouts, see
    harvest.matchweeks for the same file."""
    text = h.openfootball_text(season)
    SCORE = r"(\d+)-(\d+)(?:\s*\(\d+-\d+\))?"
    out, md, date = [], None, None
    for line in text.splitlines():
        m = re.search(r"(?:Matchday|Regular Season -)\s+(\d+)", line)
        if m:
            md = int(m.group(1))
            continue
        # a date header: "Sat Aug 17" or "Fri Aug 16 2024"
        m = re.match(r"^\s*[A-Z][a-z]{2}\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$", line)
        if m:
            mon, day, year = MONTHS[m.group(1)], int(m.group(2)), m.group(3)
            year = int(year) if year else (season if mon >= 7 else season + 1)
            date = "%04d-%02d-%02d" % (year, mon, day)
            continue
        body = line.strip()
        if not body or body.startswith("(") or not date or md is None:
            continue
        m = re.match(r"^(\d{1,2})[:.](\d{2})\s+(.+)$", body)
        if not m:
            continue
        uk = "%02d:%s" % (int(m.group(1)), m.group(2))
        rest = m.group(3)
        # "Home FC  v Away FC  1-0" or "Home FC  1-0 (1-0)  Away FC"
        g = re.match(r"^(.+?)\s+v\s+(.+?)(?:\s{2,}" + SCORE + r".*)?$", rest)
        if g:
            home, away, hs, as_ = g.group(1), g.group(2), g.group(3), g.group(4)
        else:
            g = re.match(r"^(.+?)\s{2,}" + SCORE + r"\s{2,}(.+?)$", rest)
            if not g:
                continue
            home, hs, as_, away = g.group(1), g.group(2), g.group(3), g.group(4)
        out.append({"md": md, "date": date, "uk": uk,
                    "home": home.strip(), "away": away.strip(),
                    "hs": int(hs) if hs else None, "as": int(as_) if as_ else None})
    return out


def espn_ids(season):
    """{flat club name: ESPN id} for that season, from the league table."""
    table = h.league_table("eng.1", season)
    out = {}
    for tid in table:
        info = h.team_info(tid, h.load_data("teams.json", {}))
        if info.get("name"):
            out[h.flat(info["name"])] = tid
    return out


def nets_for(date, home_id, away_id):
    """The US broadcast, from ESPN's scoreboard for that day."""
    try:
        d = h.fetch("%s/eng.1/scoreboard" % h.BASE,
                    {"dates": date.replace("-", ""), "limit": 500},
                    cacheable=date < dt.date.today().isoformat())
    except Exception:
        return [], None
    for e in d.get("events") or []:
        c = e["competitions"][0]
        ids = {str(x["id"]) for x in c["competitors"]}
        if {home_id, away_id} <= ids:
            # the SCOREBOARD names them in "names"; a team schedule uses
            # "media.shortName". Take whichever is there.
            nets = []
            for b in c.get("broadcasts") or []:
                nets += b.get("names") or []
                if (b.get("media") or {}).get("shortName"):
                    nets.append(b["media"]["shortName"])
            return nets, e
    return [], None


def us_nets(season, f, ids):
    """The US broadcast of one fixture: ESPN for the newest seasons, the
    Premier League's own listing for 2016-17 to 2023-24 (see tv.py)."""
    nets = []
    if season >= TV_FROM:
        nets, _ = nets_for(f["date"], ids.get(h.flat(f["home"])),
                           ids.get(h.flat(f["away"])))
    if not nets:
        nets = tv.networks(season, f["home"], f["away"])
    return tv.clean(nets)


def collect(teams):
    this = h.current_season()
    out = []
    ids = {}
    for season in range(h.FIRST_SEASON, this + 1):
        table = h.league_table("eng.1", season)
        for tid in table:
            info = h.team_info(tid, teams)
            ids[h.flat(info["name"])] = tid
        missing = set()
        # one match per window per matchweek: the usual time for that era, or
        # the other Sunday time when the week has nothing at the usual one
        sun_pref = sunday_time(season)
        sun_other = SUNDAY_EARLY if sun_pref == SUNDAY_LATE else SUNDAY_LATE
        fixtures = parse(season)
        sundays = {}
        for f in fixtures:
            if dow(f) != "Sun":
                continue
            if f["uk"] in (sun_pref, sun_other):
                have = sundays.get(f["md"])
                if not have or (have["uk"] != sun_pref and f["uk"] == sun_pref):
                    sundays[f["md"]] = f
        saturdays = {}
        for f in fixtures:
            if dow(f) == "Sat" and f["uk"] == SATURDAY:
                saturdays.setdefault(f["md"], []).append(f)
        # A WEEK WHOSE SHOWCASE MOVED STILL HAS ONE (his call 2026-10-09).
        # 2025-26 slid the late Sunday game to 15:30 twice and to 17:30 twice,
        # and one Saturday to 16:30 -- Liverpool v Fulham in MW32, which NBC
        # duly showed at 11:30 ET. So a matchweek with nothing at the usual
        # time falls back.
        #
        # SATURDAY falls back by the clock alone, to the last kickoff from
        # 16:00 up to 17:30. Saturday night (20:00) is its own slot.
        #
        # SUNDAY HAS NO FLOOR AND NO CEILING (his call 2026-10-09): a week cut
        # back to one early game -- a League Cup final weekend, Christmas Eve
        # -- still has a Sunday window, and so does one whose late game went
        # to 18:00 or the evening. The clock cannot rank those, so the US
        # CHANNEL does: the biggest one took the showcase, and the latest
        # kickoff breaks a tie. That is what picks Tottenham v Forest on
        # 7 April 2024, on USA Network, over the 17:30 that was on cable; and
        # what keeps Villa v Chelsea, on NBC, over the Boxing Day 20:00 of
        # 2021. Before 2016-17 nothing lists a channel, so it is the clock.
        mds = {f["md"] for f in fixtures}
        for md in mds - set(sundays):
            sun = [f for f in fixtures if f["md"] == md and dow(f) == "Sun"]
            if sun:
                sundays[md] = max(sun, key=lambda f: (
                    channel_rank(us_nets(season, f, ids)), f["uk"]))
        for md in mds - set(saturdays):
            late = [f for f in fixtures if f["md"] == md and dow(f) == "Sat"
                    and "16:00" <= f["uk"] < SATURDAY]
            if late:
                saturdays[md] = [max(late, key=lambda f: f["uk"])]
        for f in fixtures:
            if f["md"] == LAST_MD:
                continue
            if dow(f) == "Sat" and any(x is f for x in saturdays.get(f["md"], ())):
                label = "NBC Saturday"
            elif dow(f) == "Sun" and sundays.get(f["md"]) is f:
                label = "Sky Sunday"
            else:
                continue
            home, away = ids.get(h.flat(f["home"])), ids.get(h.flat(f["away"]))
            if not home or not away:
                missing.add(f["home"] if not home else f["away"])
                continue
            # the UK kickoff, converted to Eastern for the card
            naive = dt.datetime.strptime(f["date"] + " " + f["uk"], "%Y-%m-%d %H:%M")
            uk_dt = naive.replace(tzinfo=h.UK)
            et = uk_dt.astimezone(h.ET)
            m = {"team": "windows", "season": season, "comp": "PL", "stage": "",
                 "window": label, "mw": f["md"],
                 "date": et.strftime("%Y-%m-%d"), "time": et.strftime("%H:%M"),
                 "dow": et.strftime("%a"), "uk": f["uk"],
                 "home": home, "away": away, "hs": f["hs"], "as": f["as"],
                 "id": "w%s-%s-%s" % (f["date"], home, away)}
            # ESPN for the newest seasons, the Premier League's own listing
            # for 2016-17 to 2023-24 (see tv.py). Nothing before that exists.
            nets = us_nets(season, f, ids)
            if not nets:
                # 2013-14 to 2015-16, which nothing else has
                nets = tv.clean(tv.networks_any(m["date"], f["home"], f["away"]))
            if nets:
                m["nets"] = nets
            # AN NBC SATURDAY IS ON NBC (his call 2026-10-06). The 17:30 UK
            # kickoff went to USA Network, NBCSN or Peacock often enough --
            # 89 of 385 -- and a window named for a network it was not on is
            # no window of his. A match whose US network is simply unknown
            # stays, since nothing says it was not NBC.
            # ESPN AND THE LEAGUE'S OWN LISTING DISAGREE ONCE (2026-10-09):
            # Everton v Fulham on 26 October 2024, which ESPN calls USA
            # Network and the Premier League calls NBC. NBC from EITHER keeps
            # the match -- the rule is only meant to turn away a window that
            # demonstrably was not on NBC, and one source saying it was is
            # not that. It is the only such disagreement in either season
            # ESPN covers.
            if label == "NBC Saturday" and nets and "NBC" not in nets:
                if "NBC" not in tv.clean(tv.networks(season, f["home"], f["away"])):
                    continue
            out.append(m)
        if missing:
            print("  WARN: %s clubs not matched to ESPN: %s"
                  % (h.season_label(season), ", ".join(sorted(missing))))
    # upcoming only through the COMING SUNDAY (as games-history's TV Windows
    # does): the rest of the fixture list is not a TV listing yet
    today = dt.datetime.now(h.ET).date()
    horizon = (today + dt.timedelta(days=(6 - today.weekday()) % 7)).isoformat()
    out = [m for m in out if m["hs"] is not None or m["date"] <= horizon]
    tv.save()
    out.sort(key=lambda m: (m["date"], m["time"]))
    played = [m for m in out if m["hs"] is not None]
    print("  windows: %d matches (%d played)" % (len(out), len(played)))
    return out
