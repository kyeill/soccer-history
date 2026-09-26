"""Arsenal's and Chelsea's bad results -> the Rivals view.

His rules (BRIEF.md, confirmed 2026-09-21):

  ARSENAL, every competition
    a season Arsenal finished TOP FOUR   every draw and every loss, except
                                         draws with Chelsea, Liverpool, Man
                                         City or Man United
    any other season                     losses only
    either way                           never a loss to Chelsea
  CHELSEA, cups and Europe only (no Premier League at all)
    every draw and every loss

A shootout counts as a win for whoever advanced, so a shootout exit is a loss
and belongs here. A season still being played has no final table yet, so it is
treated as top four -- the superset -- until it ends (his call).
"""
import datetime as dt
import requests
import harvest as h
import tv

ARSENAL, CHELSEA = "359", "363"
LIVERPOOL, MAN_UTD, MAN_CITY = "364", "360", "382"
# the draws a top-four Arsenal season does NOT count
ARSENAL_DRAW_EXEMPT = {CHELSEA, LIVERPOOL, MAN_CITY, MAN_UTD}
RIVALS = [ARSENAL, CHELSEA]


def keeps(rival, m, top_four):
    result = m.get("result")
    if result not in ("D", "L"):
        return False
    if rival == CHELSEA:
        return m["comp"] != "PL"
    if m["opp"] == CHELSEA and result == "L":
        return False
    if result == "D":
        return top_four and m["opp"] not in ARSENAL_DRAW_EXEMPT
    return True


def build(rival, e, season, teams, pl_table, mw_map):
    slug = e["league"]["slug"]
    code, _name = h.COMPS[slug]
    c = e["competitions"][0]
    status = c["status"]["type"]
    us = next(x for x in c["competitors"] if str(x["id"]) == rival)
    them = next(x for x in c["competitors"] if str(x["id"]) != rival)
    tid = str(them["id"])
    h.team_info(tid, teams)
    when = dt.datetime.strptime(e["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
    et = when.astimezone(h.ET)
    stage = h.norm_stage(code, (e.get("seasonType") or {}).get("name"), season,
                         h.is_qualifier(slug))
    notes = [n.get("text") for n in c.get("notes") or [] if n.get("text")]
    neutral = (stage == "Final" or code == "USC" or (code == "FAC" and stage == "Semifinals"))
    m = {"id": e["id"], "team": "rivals", "rival": rival, "season": season,
         "comp": code, "stage": stage, "qual": h.is_qualifier(slug),
         "date": et.strftime("%Y-%m-%d"), "time": et.strftime("%H:%M"),
         "dow": et.strftime("%a"),
         "where": "N" if neutral else ("H" if us.get("homeAway") == "home" else "A"),
         "home": us.get("homeAway") == "home", "opp": tid,
         "nets": [n.get("media", {}).get("shortName") for n in c.get("broadcasts") or []
                  if n.get("media", {}).get("shortName")]}
    if neutral:
        m["place"] = h.venue_place(c.get("venue"))
    if not status.get("completed"):
        return None                        # nothing to judge yet
    m["us"], m["them"] = h.score_of(us), h.score_of(them)
    if m["us"] is None or m["them"] is None:
        return None
    so = shootout(notes, us)
    # a drawn cup tie: the summary carries the shootout even when the note
    # does not (Chelsea's 2013 Super Cup)
    if so is None and m["us"] == m["them"] and code != "PL":
        so = h.pens_from_summary(e["id"], rival)
    if so is not None:
        m["pens"] = so[1]
        m["result"] = "W" if so[0] else "L"
    elif m["us"] > m["them"]:
        m["result"] = "W"
    elif m["us"] < m["them"]:
        m["result"] = "L"
    else:
        m["result"] = "D"
    if tid in pl_table:
        m["fin"] = h.ordinal(pl_table[tid])
    if code == "PL":
        home, away = (rival, tid) if m["home"] else (tid, rival)
        key = (h.flat(teams[home]["name"]), h.flat(teams[away]["name"]))
        if key in mw_map:
            m["mw"] = mw_map[key]
        if not m["nets"]:
            m["nets"] = tv.networks(season, teams[home]["name"], teams[away]["name"])
    if not m["nets"]:
        home, away = (rival, tid) if m["home"] else (tid, rival)
        m["nets"] = tv.networks_any(m["date"], teams[home]["name"], teams[away]["name"])
    return m


def shootout(notes, us):
    """Whose shootout it was, by the name in ESPN's note."""
    names = {us["team"].get("displayName"), us["team"].get("shortDisplayName"),
             us["team"].get("location"), us["team"].get("name")} - {None, ""}
    got = None
    for n in notes:
        import re
        mm = re.search(r"^(.*?) (?:advance|advances|win|wins) (\d+)-(\d+) on penalties", n or "")
        if mm:
            got = (mm.group(1).strip() in names, mm.group(2) + "-" + mm.group(3))
    return got


def collect(teams):
    """Every Arsenal and Chelsea match his rules keep, 2013-14 on."""
    this = h.current_season()
    out = []
    for season in range(h.FIRST_SEASON, this + 1):
        over = h.season_over(season)
        pl_table = h.league_table("eng.1", season)
        mw_map = h.matchweeks(season)
        for rival in RIVALS:
            h.team_info(rival, teams)
            try:
                events = h.fetch("%s/all/teams/%s/schedule" % (h.BASE, rival),
                                 {"season": season}, cacheable=over).get("events") or []
            except requests.RequestException as e:
                print("  WARN: %s %s: %s" % (rival, season, e))
                continue
            events = [e for e in events if (e.get("league") or {}).get("slug") in h.COMPS]
            # a season still being played has no final table: treat it as top
            # four, which is the wider rule, until it ends
            top_four = (not over) or pl_table.get(rival, 99) <= 4
            got = [build(rival, e, season, teams, pl_table, mw_map) for e in events]
            out += [m for m in got if m and keeps(rival, m, top_four)]
    tv.save()
    out.sort(key=lambda m: (m["date"], m["time"]))
    print("  rivals: %d results (%d Arsenal, %d Chelsea)"
          % (len(out), sum(1 for m in out if m["rival"] == ARSENAL),
             sum(1 for m in out if m["rival"] == CHELSEA)))
    return out
