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
        # SATURDAY IS ALWAYS EXACTLY 17:30 UK, AND ALWAYS ONE MATCH (his
        # calls 2026-10-09). A matchweek split over two weekends -- 2019-20
        # MW26, 2023-24 MW21 -- has two of them, and the window is the FIRST.
        # A week with no 17:30 at all simply has no NBC Saturday: in fourteen
        # seasons the 16:00-17:29 fallback that used to stand in had produced
        # two cards, Newcastle v Leicester in 2014-15 MW8 with no channel
        # listed anywhere, and Liverpool v Fulham in 2025-26 MW32, which NBC
        # did show at 11:30 ET.
        saturdays = {}
        for f in sorted(fixtures, key=lambda f: (f["date"], f["uk"])):
            if dow(f) == "Sat" and f["uk"] == SATURDAY:
                saturdays.setdefault(f["md"], f)
        # NEITHER SLOT FALLS BACK (his calls 2026-10-09). A window is its
        # own kickoff time or it is nothing: 17:30 UK on a Saturday, 16:30 on
        # a Sunday (16:00 to 2018-19). A weekend whose schedule never reached
        # that time simply had no window, and inventing one from whatever
        # else was on that day was the wrong answer.
        #
        # It costs 66 weekends of 419 across the thirteen completed seasons,
        # about five a year: 58 of them had Sunday football at some other
        # hour, 8 had no Sunday fixture at all. The fallbacks that used to
        # fill them stood from earlier the same day until he saw the count.
        for f in fixtures:
            if f["md"] == LAST_MD:
                continue
            if dow(f) == "Sat" and saturdays.get(f["md"]) is f:
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
            # AN NBC SATURDAY MUST SAY NBC (his call 2026-10-09, tightening
            # 2026-10-06). It is not enough that nothing contradicts NBC: a
            # source has to name it, or the window is not his. ESPN and the
            # league's own listing disagree exactly once -- Everton v Fulham
            # on 26 October 2024, USA Network to one and NBC to the other --
            # and NBC from EITHER is enough. Today this turns away nothing
            # extra: all 297 surviving cards name NBC and not one is unknown.
            if label == "NBC Saturday":
                said = set(nets) | set(tv.clean(
                    tv.networks(season, f["home"], f["away"])))
                if "NBC" not in said:
                    continue
                m["nets"] = sorted(said)
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
