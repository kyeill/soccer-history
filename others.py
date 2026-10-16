"""USMNT (competitive matches from 2010) and Atlanta United (everything but the
MLS regular season, from 2017) -> data/usmnt.json and data/atlanta.json.

Why the two teams are read differently (found 2026-09-21):

  USMNT    ESPN's team schedule is INCOMPLETE for national teams -- it drops
           whole rounds (the 2018 qualifiers before the Hex, the 2021 Nations
           League final) and the core API drops the same ones. Every match
           summary, though, carries the team's previous five matches, so the
           list is built by chaining back through summaries: complete,
           friendlies included (then dropped), about 75 calls for 2010 on.
  Atlanta  the per-competition team schedules are complete.

A finished match never changes, so each record is kept in data/ once played.
"""
import datetime as dt, json, re, sys
import requests
import harvest as h

USA, ATL = "660", "18418"

# ESPN league slug -> (code, name). Anything else a chain turns up that is not
# a friendly is reported, so a new competition cannot slip in or out silently.
US_COMPS = {
    "fifa.world": ("WC", "World Cup"),
    "fifa.worldq.concacaf": ("WCQ", "World Cup Qualifying"),
    "concacaf.gold": ("GC", "Gold Cup"),
    "concacaf.nations.league": ("NL", "Nations League"),
    "conmebol.america": ("CA", "Copa América"),
    "concacaf.confederations_playoff": ("CCUP", "CONCACAF Cup"),
    "fifa.confederations": ("CONF", "Confederations Cup"),
}
ATL_COMPS = {
    "usa.1": ("MLS", "MLS Cup Playoffs"),
    "concacaf.champions": ("CCL", "Champions Cup"),
    "concacaf.leagues.cup": ("LGC", "Leagues Cup"),
    "usa.open": ("USOC", "U.S. Open Cup"),
    "campeones.cup": ("CAMP", "Campeones Cup"),
}
US_FROM = "2010-01-01"
# ESPN LEAVES SOME ADDRESSES BLANK AND HAS ONE PLAINLY WRONG (2026-10-16).
# Every one of these is a stadium whose country is not in doubt. Toyota
# Stadium is ESPN's own error: its venue 5769 is the one in Frisco, Texas,
# and it files the address under Toyota, Japan -- which would have kept the
# 2015 Gold Cup group match out of the North American rule.
VENUE_FIX = {
    "RFK Memorial": ("Washington", "USA"),
    "Georgia Dome": ("Atlanta", "USA"),
    "Busch Stadium": ("St. Louis", "USA"),
    "Sporting Park": ("Kansas City", "USA"),
    "Livestrong Sporting Park": ("Kansas City", "USA"),
    "Toyota Stadium": ("Frisco", "USA"),
    "Arnos Vale Stadium": ("Arnos Vale", "St. Vincent and the Grenadines"),
}
# bumped whenever a record gains a field, so stored ones are made again from
# the summaries already on disk
RECORD_V = 3
ATL_FROM = 2017


def summary(eid, final):
    return h.fetch("%s/all/summary" % h.BASE, {"event": eid}, cacheable=final)


def record(team, eid, s, comps, stage_raw=None):
    """One match from its summary, in the shape the cards use."""
    hd = s["header"]
    c = hd["competitions"][0]
    slug = (hd.get("league") or {}).get("slug")
    code, name = comps[slug]
    us = next(x for x in c["competitors"] if str(x["team"]["id"]) == team)
    them = next(x for x in c["competitors"] if str(x["team"]["id"]) != team)
    when = dt.datetime.strptime(c["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
    et = when.astimezone(h.ET)
    status = (c.get("status") or {}).get("type") or {}
    # "2018 World Cup Qualifying - Concacaf, Fourth Round" -> "Fourth Round"
    season_name = (hd.get("season") or {}).get("name") or ""
    stage = stage_raw or (season_name.split(", ", 1)[1] if ", " in season_name else "")
    venue = (s.get("gameInfo") or {}).get("venue") or {}
    m = {"id": eid, "comp": code, "stage": stage, "year": et.year,
         "date": et.strftime("%Y-%m-%d"), "time": et.strftime("%H:%M"), "dow": et.strftime("%a"),
         "where": "N" if c.get("neutralSite") else ("H" if us.get("homeAway") == "home" else "A"),
         # the side ESPN lists as home, kept even on neutral ground: the score
         # boxes always read home then away (his call 2026-09-21)
         "home": us.get("homeAway") == "home",
         "venue": venue.get("fullName") or "",
         "city": (venue.get("address") or {}).get("city") or "",
         # WHERE IT WAS PLAYED (his call 2026-10-16): the card names the
         # ground for anything in North America, and ESPN's address is the
         # only thing that tells the three countries apart -- "city" alone is
         # sometimes a stadium name.
         "country": (venue.get("address") or {}).get("country") or "",
         "opp": str(them["team"]["id"]), "opp_name": them["team"].get("displayName") or ""}
    # THE NATIONS LEAGUE READS BY THE YEAR OF ITS FINAL (his call
    # 2026-10-16): a quarterfinal played in November 2023 belongs to the
    # edition settled in March 2024, so its card says 2024. ESPN's season
    # name carries the edition -- "2023-24 Concacaf Nations League" -- and
    # the ending year is when the final is played, with ONE exception: the
    # 2019-20 final was put off to June 2021 by the pandemic.
    if code == "NL":
        ed = re.match(r"(\d{4})-(\d{2})", season_name)
        if ed:
            m["cycle"] = 2021 if ed.group(1) == "2019"                 else int(ed.group(1)[:2] + ed.group(2))
    fix = VENUE_FIX.get(m["venue"])
    if fix:
        m["city"], m["country"] = fix
    elif not m["country"] and m["where"] == "H":
        # a match the United States played AT HOME was in the United States,
        # which is the only thing the blank addresses need
        m["country"] = "USA"
    if team == USA:
        m["v"] = RECORD_V
    if not status.get("completed"):
        m["upcoming"] = True
        return m
    try:
        m["us"], m["them"] = int(us.get("score")), int(them.get("score"))
    except (TypeError, ValueError):
        m["upcoming"] = True
        return m
    notes = [n.get("text") or n.get("headline") or "" for n in c.get("notes") or []]
    so = h.shootout_of(notes) if team == h.SPURS else shootout_for(notes, us["team"])
    if not so and m["us"] == m["them"]:
        so = h.pens_from_summary(eid, team)
    if so:
        m["pens"], m["result"] = so[1], ("W" if so[0] else "L")
    else:
        m["result"] = "W" if m["us"] > m["them"] else "L" if m["us"] < m["them"] else "D"
    # WHO SCORED (his call 2026-10-16), kept on every record they did not
    # lose, so which cards show them can change without a refetch.
    if team == USA and m["result"] in ("W", "D"):
        try:
            goals = h.goals_of(slug, eid, USA,
                               {USA: m["us"], m["opp"]: m["them"]})
        except Exception:
            goals = None
        if goals and goals != "awarded":
            order, mins = [], {}
            for mn, add, tid, who in goals:
                if tid != USA:
                    continue
                who = who or "Goal"
                if who not in mins:
                    order.append(who)
                    mins[who] = []
                mins[who].append("%d'%s" % (mn, "+%d" % add if add else ""))
            if order:
                m["scorers"] = ["%s %s" % (w, ", ".join(mins[w])) for w in order]
    return m


def shootout_for(notes, team):
    """ESPN's note names the side that advanced, by any of its names."""
    names = {team.get("displayName"), team.get("shortDisplayName"), team.get("location"),
             team.get("name"), team.get("abbreviation")} - {None, ""}
    for n in notes:
        mm = re.search(r"^(.*?) (?:advance|advances|win|wins) (\d+)-(\d+) on penalties", n or "")
        if mm:
            return mm.group(1).strip() in names, mm.group(2) + "-" + mm.group(3)
    return None


# ---------------------------------------------------------------- USMNT
def usmnt(store):
    """store: {"chain": {id: [date, league name]}, "matches": {id: record}}."""
    chain = store.setdefault("chain", {})
    done = store.setdefault("matches", {})
    # the newest played match, and the fixtures ahead, from the team schedule
    sched = []
    for q in ({}, {"fixture": "true"}):
        try:
            sched += h.fetch("%s/all/teams/%s/schedule" % (h.BASE, USA), q,
                             cacheable=False).get("events") or []
        except requests.RequestException:
            pass
    played = sorted((e for e in sched if e["competitions"][0]["status"]["type"].get("completed")),
                    key=lambda e: e["date"])
    ahead = [e for e in sched if not e["competitions"][0]["status"]["type"].get("completed")]
    # chain back until a match already known -- or 2010 on a cold start
    cur = played[-1]["id"] if played else None
    hops = 0
    while cur and hops < 200:
        hops += 1
        s = summary(cur, True)
        five = next((t["events"] for t in s.get("lastFiveGames") or []
                     if str(t["team"]["id"]) == USA), [])
        new = False
        for e in five:
            if e["id"] not in chain:
                chain[e["id"]] = [e["gameDate"][:10], e.get("leagueName") or ""]
                new = True
        oldest = min(five, key=lambda e: e["gameDate"]) if five else None
        if not oldest or oldest["id"] == cur or oldest["gameDate"][:10] < US_FROM:
            break
        # a cached run stops as soon as it meets the part of the chain it has
        if not new and oldest["id"] in done:
            break
        cur = oldest["id"]
    unknown = set()
    for eid, (date, league) in chain.items():
        # a record made before the country and the scorers existed is made
        # again; its summary is on disk, so this costs no call (2026-10-16)
        # a record made before a field existed is made again; its summary is
        # on disk, so this costs no call (2026-10-16)
        if date < US_FROM or "Friendly" in league or                 (eid in done and done[eid].get("v") == RECORD_V):
            continue
        s = summary(eid, True)
        slug = (s["header"].get("league") or {}).get("slug")
        if slug not in US_COMPS:
            unknown.add((slug, league))
            continue
        m = record(USA, eid, s, US_COMPS)
        if not m.get("upcoming"):
            done[eid] = m
    for slug, league in sorted(unknown, key=str):
        print("  WARN: USMNT competition not handled: %s (%s)" % (slug, league), file=sys.stderr)
    upcoming = []
    for e in ahead:
        slug = (e.get("league") or {}).get("slug")
        if slug in US_COMPS:
            upcoming.append(record(USA, e["id"], summary(e["id"], False), US_COMPS))
    return sorted(list(done.values()) + upcoming, key=lambda m: m["date"])


# ---------------------------------------------------------------- Atlanta
def atlanta(store):
    done = store.setdefault("matches", {})
    this = dt.datetime.now(h.ET).year
    out = dict(done)
    for slug in ATL_COMPS:
        for y in range(ATL_FROM, this + 1):
            final_year = y < this
            for q in ({"season": y},) + (({"season": y, "fixture": "true"},) if not final_year else ()):
                try:
                    d = h.fetch("%s/%s/teams/%s/schedule" % (h.BASE, slug, ATL), q,
                                cacheable=final_year)
                except requests.RequestException:
                    continue
                for e in d.get("events") or []:
                    st = (e.get("seasonType") or {}).get("name") or ""
                    # everything but the MLS regular season -- and the 2020 MLS
                    # is Back tournament, which ESPN files in it (his call)
                    if slug == "usa.1" and (st == "Regular Season" or "MLS is Back" in st):
                        continue
                    if e["id"] in done:
                        continue
                    stage = re.sub(r"^\d{4} ", "", st)
                    m = record(ATL, e["id"], summary(e["id"], final_year),
                               ATL_COMPS, stage)
                    out[e["id"]] = m
                    if not m.get("upcoming"):
                        done[e["id"]] = m
    return sorted(out.values(), key=lambda m: m["date"])


def tidy_stage(code, s):
    """One spelling per round, as for Spurs."""
    s = (s or "").strip()
    s = s.replace("Quarter-finals", "Quarterfinals").replace("Semi-finals", "Semifinals")
    if re.match(r"^(3rd-Place|Third Place)", s):
        return "Third Place"
    if code == "MLS":
        # ESPN has renamed the rounds almost every year
        if s == "Final":
            return "MLS Cup"
        s = re.sub(r"^Eastern Conference Playoffs - ", "", s)
        s = re.sub(r" - Eastern Conf$", "", s)
        return {"Knockout": "Knockout Round", "First Round": "Round One",
                "Semifinals": "Conference Semifinals", "Finals": "Conference Final",
                "Wild Card": "Wild Card"}.get(s, s)
    return s


def neutral_for_usmnt(m):
    """HIS CALL (2026-09-21): a tournament match is NEUTRAL wherever it is
    played -- ESPN calls a Gold Cup match in Houston a US home game. Home and
    away stay only where they are real: World Cup qualifying, and the Nations
    League's group games and two-legged quarterfinals."""
    if m["comp"] == "WCQ":
        return False
    if m["comp"] == "NL" and (m["stage"].startswith("League") or m["stage"] == "Quarterfinals"):
        return False
    return True


# THE ONLY TIE THEY PLAY OVER TWO LEGS (his call 2026-10-16) is the Nations
# League quarterfinal. Everything else that LOOKS like a pair -- the Third and
# Fourth Rounds of Concacaf qualifying -- is a group played home and away,
# where an aggregate means nothing: the United States met Jamaica twice in
# 2012 and twice again in 2013 with four other sides in the same table.
TWO_LEGGED = {("NL", "Quarterfinals")}


def mark_legs(ms):
    """leg, agg and through on a genuine two-legged tie, as harvest.py does
    for Tottenham -- minus away goals, which CONCACAF has never used."""
    ties = {}
    for m in ms:
        if (m["comp"], m["stage"]) in TWO_LEGGED:
            ties.setdefault((m["year"], m["comp"], m["stage"], m["opp"]), []).append(m)
    for legs in ties.values():
        legs.sort(key=lambda m: m["date"])
        if len(legs) != 2 or not all("us" in m for m in legs):
            continue
        ours = sum(m["us"] for m in legs)
        theirs = sum(m["them"] for m in legs)
        legs[1]["agg"] = "%d-%d" % (ours, theirs)
        legs[0]["leg"], legs[1]["leg"] = 1, 2
        # the aggregate first, then the second leg's own shootout -- which
        # settles the TIE, not the night, so it is read here and not when the
        # match was built
        if ours != theirs:
            legs[1]["through"] = ours > theirs
        elif legs[1].get("pens"):
            legs[1]["through"] = legs[1]["result"] == "W"
        else:
            so = h.pens_from_summary(legs[1]["id"], USA)
            if so:
                legs[1]["pens"], legs[1]["through"] = so[1], so[0]
        if "through" in legs[1]:
            legs[0]["through"] = legs[1]["through"]


def tidy(team_key, ms):
    """The records as the page reads them."""
    out = []
    for m in ms:
        m = dict(m)
        m["team"] = team_key
        m["season"] = m["year"]
        m["stage"] = tidy_stage(m["comp"], m["stage"])
        if team_key == "usmnt" and neutral_for_usmnt(m):
            m["where"] = "N"
        if m["where"] == "N" and m.get("city"):
            m["place"] = m["city"]
        out.append(m)
    if team_key == "usmnt":
        mark_legs(out)
    return out


def main():
    us_store = h.load_data("usmnt.json", {})
    us = usmnt(us_store)
    h.save_data("usmnt.json", us_store)
    atl_store = h.load_data("atlanta.json", {})
    atl = atlanta(atl_store)
    h.save_data("atlanta.json", atl_store)
    for name, ms, floor in (("USMNT", us, 130), ("Atlanta", atl, 50)):
        played = [m for m in ms if not m.get("upcoming")]
        print("  %s  %d matches (%d played)" % (name, len(ms), len(played)))
        if len(played) < floor:
            raise SystemExit("ABORT: %s has only %d played matches" % (name, len(played)))
    return us, atl


if __name__ == "__main__":
    main()
