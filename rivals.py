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


def build(rival, e, season, teams, pl_table, mw_map, goal_store):
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
    if any("extra time" in (n or "").lower() or "aet" in (n or "").lower()
           for n in notes):
        m["aet"] = True
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
    m["nets"] = tv.clean(m["nets"])
    # THE GOAL THAT DID FOR THEM (his call 2026-10-09): the opponent's goals
    # from the 80th, when the last of them won the match or levelled it.
    # late_flags is read from the OPPONENT's side here, so the rival is the
    # club it checks against -- and Arsenal and Chelsea are both Top Six, so
    # its equalizer rule lets them through.
    if m["result"] in ("D", "L"):
        goals = goal_store.get(e["id"])
        if goals is None:
            try:
                goals = h.goals_of(slug, e["id"], rival,
                                   {rival: m["us"], tid: m["them"]})
            except requests.RequestException as err:
                # ESPN answers 502 now and then over a few hundred summaries;
                # an unread match is left unread, not remembered as goalless
                print("  WARN: goals for %s: %s" % (e["id"], err))
                goals = None
            else:
                goal_store[e["id"]] = goals
        if goals and goals != "awarded":
            w, q = h.late_flags(goals, tid, rival,
                                "W" if m["result"] == "L" else "D")
            if w:
                m["late_win"] = w
            if q:
                m["late_eq"] = q
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


EURO = ("UCL", "UEL", "UECL")


def collapse(ms):
    """A European knockout tie they went OUT of reads as ONE card: the second
    leg, with the AGGREGATE as the score and both legs in the header, the
    rival's score second in each -- "(1-0, 2-2)". The first leg settled
    nothing on its own, so it goes (his call 2026-10-09).
    """
    ties = {}
    for m in ms:
        if m["comp"] not in EURO:
            continue
        if m["stage"] in ("Group Stage", "League Phase", "Final"):
            continue
        ties.setdefault((m["season"], m["comp"], m["stage"], m["opp"]), []).append(m)
    gone = []
    for legs in ties.values():
        if len(legs) != 2:
            continue
        legs.sort(key=lambda x: x["date"])
        ours = sum(x["us"] for x in legs)
        theirs = sum(x["them"] for x in legs)
        if ours != theirs:
            through = ours > theirs
        elif legs[1].get("pens"):
            through = legs[1]["result"] == "W"
        else:
            away = next((x for x in legs if not x["home"]), None)
            home = next((x for x in legs if x["home"]), None)
            if legs[1]["season"] <= 2020 and away and home and \
                    away["us"] != home["them"]:
                through = away["us"] > home["them"]
            else:
                through = None
        if through is not False:
            continue
        second = legs[1]
        second["legs"] = ["%d-%d" % (x["them"], x["us"]) for x in legs]
        second["us"], second["them"] = ours, theirs
        second["agg"] = True
        if second.get("aet"):
            second["legs_aet"] = True
        gone.append(id(legs[0]))
    return [m for m in ms if id(m) not in gone]


def collect(teams):
    """Every Arsenal and Chelsea match his rules keep, 2013-14 on."""
    this = h.current_season()
    goal_store = h.load_data("rival-goals.json", {})
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
            got = [build(rival, e, season, teams, pl_table, mw_map, goal_store)
                   for e in events]
            got = collapse([m for m in got if m])
            # a tie they went out of is kept whatever the second leg's own
            # result was: it is the tie the card is about
            out += [m for m in got if m.get("agg") or keeps(rival, m, top_four)]
    tv.save()
    h.save_data("rival-goals.json", goal_store)
    out.sort(key=lambda m: (m["date"], m["time"]))
    print("  rivals: %d results (%d Arsenal, %d Chelsea)"
          % (len(out), sum(1 for m in out if m["rival"] == ARSENAL),
             sum(1 for m in out if m["rival"] == CHELSEA)))
    return out
