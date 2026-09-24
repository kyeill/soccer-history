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
         "opp": str(them["team"]["id"]), "opp_name": them["team"].get("displayName") or ""}
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
        if date < US_FROM or "Friendly" in league or eid in done:
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
