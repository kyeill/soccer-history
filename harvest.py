"""Fetch every competitive Tottenham match from 2013-14 and write output/games.json.

Sources (see BRIEF.md "Research results"):
  ESPN        schedules, scores, venues, US TV, goal minutes, standings
  openfootball  the official Premier League MATCHWEEK -- ESPN has none, and
              FPL's gameweek renumbers postponed matches

Finished seasons never change, so what is slow to rebuild -- every match's goal
list, every opponent's finish -- is kept in data/ and committed. The daily
build then only asks ESPN for the current season and anything new.
"""
import collections, datetime as dt, hashlib, json, os, re, sys, time
import unicodedata
from zoneinfo import ZoneInfo
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")      # raw ESPN answers, local speed-up only
DATA = os.path.join(HERE, "data")        # committed: derived facts that never change
OUT = os.path.join(HERE, "output")
ET = ZoneInfo("America/New_York")
UK = ZoneInfo("Europe/London")
BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer"
OPENFOOTBALL = ("https://raw.githubusercontent.com/openfootball/england/master/"
                "%s/1-premierleague.txt")

SPURS = "367"
FIRST_SEASON = 2013
# Arsenal, Chelsea, Liverpool, Man United, Man City -- the Top Six bar Spurs,
# for late equalizers (BRIEF: only against these)
TOP_SIX = {"359", "363", "364", "360", "382"}

# ESPN league slug -> (competition code, name). Qualifying rounds file under
# their competition. Friendlies and preseason tournaments are simply absent.
COMPS = {
    "eng.1": ("PL", "Premier League"),
    "eng.fa": ("FAC", "FA Cup"),
    "eng.league_cup": ("LC", "League Cup"),
    "uefa.champions": ("UCL", "Champions League"),
    "uefa.champions_qual": ("UCL", "Champions League"),
    "uefa.europa": ("UEL", "Europa League"),
    "uefa.europa_qual": ("UEL", "Europa League"),
    "uefa.europa.conf": ("UECL", "Conference League"),
    "uefa.europa.conf_qual": ("UECL", "Conference League"),
    "uefa.super_cup": ("USC", "Super Cup"),
}
# the slug an opponent's run through a competition is read from
MAIN_SLUG = {"FAC": "eng.fa", "LC": "eng.league_cup", "UCL": "uefa.champions",
             "UEL": "uefa.europa", "UECL": "uefa.europa.conf"}
# a floor per finished season (a Premier League season alone; 2023-24 had no
# Europe and only 41): fewer means ESPN answered
# short, and a green run must not hide it (BRIEF: check counts)
MIN_MATCHES = 38


def current_season(today=None):
    today = today or dt.datetime.now(ET).date()
    return today.year if today.month >= 7 else today.year - 1


def season_over(y):
    # the last European final is in early June
    return dt.datetime.now(ET).date() >= dt.date(y + 1, 6, 20)


def season_label(y):
    return "%d-%02d" % (y, (y + 1) % 100)


# ---------------------------------------------------------------- fetching
def get_json(url, params=None, tries=4):
    """ESPN with retries on transient failures; a 4xx is real and raises."""
    wait = 2
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code >= 500:
                raise requests.HTTPError("%d" % r.status_code, response=r)
            r.raise_for_status()
            return r.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if attempt == tries - 1 or (status is not None and status < 500):
                raise
            print("  retry %d after %s" % (attempt + 1, e), file=sys.stderr)
            time.sleep(wait)
            wait *= 2


def fetch(url, params=None, cacheable=True):
    key = url + "?" + "&".join("%s=%s" % kv for kv in sorted((params or {}).items()))
    path = os.path.join(CACHE, hashlib.sha1(key.encode()).hexdigest()[:20] + ".json")
    if cacheable and os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    data = get_json(url, params)
    if cacheable:
        os.makedirs(CACHE, exist_ok=True)
        json.dump(data, open(path, "w", encoding="utf-8"))
    return data


def load_data(name, default):
    path = os.path.join(DATA, name)
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def save_data(name, obj):
    os.makedirs(DATA, exist_ok=True)
    json.dump(obj, open(os.path.join(DATA, name), "w", encoding="utf-8"),
              indent=0, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------- stages
ORDINAL = {"1st": "First", "2nd": "Second", "3rd": "Third", "4th": "Fourth",
           "5th": "Fifth", "6th": "Sixth"}
NUMBER = {"1": "First", "2": "Second", "3": "Third", "4": "Fourth", "5": "Fifth",
          "6": "Sixth"}


def norm_stage(comp, raw, season, qual=False):
    """ESPN spells one round several ways ('Round 3', '3rd Round', 'Football
    League Cup - Third Round', 'Quarter-finals'). One spelling each here."""
    s = (raw or "").strip()
    if comp == "PL":
        return ""
    if qual:
        # a qualifying league's "Second Round" is the second QUALIFYING round
        s = s.replace("Play-off", "Playoff")
        if s.startswith("Playoff"):
            return "Playoff Round"
        return re.sub(r"^(\w+) Round$", r"\1 Qualifying Round", s)
    s = re.sub(r"^Football League Cup - ", "", s)
    s = s.replace("Quarter-finals", "Quarterfinals").replace("Semi-finals", "Semifinals")
    s = s.replace("Play-off Round", "Playoff Round").replace("Playoff", "Playoff Round") \
         .replace("Playoff Round Round", "Playoff Round")
    m = re.match(r"^(\d)(?:st|nd|rd|th) Round$", s)
    if m:
        s = NUMBER[m.group(1)] + " Round"
    m = re.match(r"^Round (\d)$", s)
    if m:
        s = NUMBER[m.group(1)] + " Round"
    # the Europa League of 2013-16, which ESPN names by its own numbering:
    # "2013 First Round" is the group stage, then the knockouts
    if comp == "UEL" and season <= 2015:
        if re.match(r"^\d{4} First Round$", s):
            s = "Group Stage"
        elif s == "Second Round":
            s = "Round of 32"
        elif s == "Third Round":
            s = "Round of 16"
    if re.match(r"^\d{4} ", s):          # "2025 UEFA Super Cup"
        s = ""
    return s


def is_qualifier(slug):
    return slug.endswith("_qual")


# ---------------------------------------------------------------- goals
def minute_of(clock):
    """"90'+3'" -> (90, 3); "83'" -> (83, 0)."""
    m = re.match(r"^\s*(\d+)'?(?:\s*\+\s*(\d+))?", clock or "")
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)


def goals_of(slug, eid, home_id, final):
    """[(minute, added, team_id)] in order, from the match summary. Checked
    against the final score: a mismatch returns None rather than a wrong flag."""
    s = fetch("%s/%s/summary" % (BASE, slug), {"event": eid})
    out = []
    for k in s.get("keyEvents") or []:
        if not k.get("scoringPlay") or k.get("shootout"):
            continue
        if (k.get("period") or {}).get("number") == 5:
            continue
        tid = str((k.get("team") or {}).get("id") or "")
        mn, add = minute_of((k.get("clock") or {}).get("displayValue"))
        out.append([mn, add, tid])
    out.sort(key=lambda g: (g[0], g[1]))
    adds_up = lambda gs: [collections.Counter(g[2] for g in gs).get(t, 0)
                          for t in final] == list(final.values())
    if adds_up(out):
        return out
    # ESPN lists every goal TWICE on a few old matches (Barnsley 2017, West
    # Ham 2018) -- the same minute and team back to back
    once = [g for i, g in enumerate(out) if i == 0 or g != out[i - 1]]
    if adds_up(once):
        return once
    # a match AWARDED without being played (Rennes 2021, the Covid forfeit)
    # has a 3-0 score and no goals at all
    if not out and sorted(final.values()) == [0, 3]:
        return "awarded"
    return None


def late_flags(goals, us, them_id, result):
    """(late winner minute, late equalizer minute) as display strings or None.

    Late winner: Spurs won, and the goal that put them ahead FOR GOOD came in
    the 80th minute or later (stoppage and extra time included).
    Late equalizer: the match ended level after play, Spurs scored last, at
    80'+, levelling it -- and only against the Top Six."""
    if goals is None:
        return None, None
    lead, ahead_since = 0, None
    for mn, add, tid in goals:
        before = lead
        lead += 1 if tid == us else -1
        if lead > 0 and before <= 0:
            ahead_since = (mn, add)
        if lead <= 0:
            ahead_since = None
    fmt = lambda m: "%d'" % m[0] + ("+%d" % m[1] if m[1] else "")
    winner = eq = None
    if result == "W" and lead > 0 and ahead_since and ahead_since[0] >= 80:
        winner = fmt(ahead_since)
    if lead == 0 and goals and them_id in TOP_SIX:
        mn, add, tid = goals[-1]
        if tid == us and mn >= 80:
            eq = fmt((mn, add))
    return winner, eq


# ---------------------------------------------------------------- matchweeks
def flat(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", "and")
    s = re.sub(r"\b(fc|afc)\b", "", s)
    s = re.sub(r"[^a-z]", "", s)
    return {"wolverhamptonwanderers": "wolves", "brightonandhovealbion": "brighton",
            "manchesterunited": "manutd", "manchestercity": "mancity",
            "tottenhamhotspur": "tottenham", "westhamunited": "westham",
            "newcastleunited": "newcastle", "leicestercity": "leicester",
            "leedsunited": "leeds", "norwichcity": "norwich", "stokecity": "stoke",
            "swanseacity": "swansea", "cardiffcity": "cardiff", "hullcity": "hull",
            "westbromwichalbion": "westbrom", "huddersfieldtown": "huddersfield",
            "ipswichtown": "ipswich", "lutontown": "luton", "sheffieldunited": "sheffutd",
            "queensparkrangers": "qpr", "boltonwanderers": "bolton",
            "wiganathletic": "wigan", "bournemouth": "bournemouth",
            "coventrycity": "coventry"}.get(s, s)


def openfootball_text(season):
    """That season's openfootball file. It is plain text, not JSON, so it has
    its own tiny cache; a finished season is never re-fetched."""
    path = os.path.join(CACHE, "of-%d.txt" % season)
    if season_over(season) and os.path.exists(path):
        return open(path, encoding="utf-8").read()
    r = requests.get(OPENFOOTBALL % season_label(season), timeout=60)
    r.raise_for_status()
    text = r.content.decode("utf-8")
    os.makedirs(CACHE, exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    return text


def matchweeks(season):
    """{(home flat, away flat): matchweek} from openfootball."""
    text = openfootball_text(season)
    # Two layouts. To 2023-24 the score sits between the clubs:
    #     15:00  Arsenal FC               1-3 (1-1)  Aston Villa
    # From 2024-25 a "v" does, and the score trails:
    #     15:00  Arsenal FC              v Wolverhampton Wanderers FC  2-0 (1-0)
    SCORE = r"\d+-\d+(?:\s*\(\d+-\d+\))?"
    out, md = {}, None
    for line in text.splitlines():
        # "Matchday 1", or "Regular Season - 1" in 2025-26
        m = re.search(r"(?:Matchday|Regular Season -) (\d+)", line)
        if m:
            md = int(m.group(1))
            continue
        if not md or not line.startswith(" "):
            continue
        body = re.sub(r"^\s+(?:\d{1,2}[:.]\d{2}\s+)?", "", line).rstrip()
        body = re.sub(r"\s*@.*$", "", body)
        m = re.match(r"^(.+?)\s+v\s+(.+?)(?:\s{2,}" + SCORE + r".*)?$", body)
        if not m:
            m = re.match(r"^(.+?)\s{2,}" + SCORE + r"\s{2,}(.+?)$", body)
        if m:
            out[(flat(m.group(1).strip()), flat(m.group(2).strip()))] = md
    return out


# ---------------------------------------------------------------- teams
# THE NAME ON A CARD: ESPN's full name, except where it is long or not what
# anyone says. ESPN's own short names read worse ("Boro", "C Palace",
# "Lokomotiv Pl"), so they are not used.
CARD_NAME = {
    "Manchester United": "Man United", "Manchester City": "Man City",
    "Brighton & Hove Albion": "Brighton", "Wolverhampton Wanderers": "Wolves",
    "AFC Bournemouth": "Bournemouth", "West Bromwich Albion": "West Brom",
    "Queens Park Rangers": "QPR", "Paris Saint-Germain": "PSG",
    "Internazionale": "Inter Milan", "F.C. København": "FC Copenhagen",
    "Dnipro Dnipropetrovsk": "Dnipro", "Anzhi Makhachkala": "Anzhi",
    "Ludogorets Razgrad": "Ludogorets", "Apoel Nicosia": "APOEL",
    "AEL": "AEL Limassol", "Ajax Amsterdam": "Ajax", "Stade Rennais": "Rennes",
    "TSG Hoffenheim": "Hoffenheim", "KAA Gent": "Gent", "IF Elfsborg": "Elfsborg",
    "NS Mura": "Mura", "FK Qarabag": "Qarabag", "Tromso": "Tromsø",
    "Bodo/Glimt": "Bodø/Glimt", "Partizan Belgrade": "Partizan",
}


def team_info(tid, teams):
    """Name, short name, colour and crest, fetched once per team ever."""
    if tid in teams:
        return teams[tid]
    info = {"name": tid, "short": tid, "color": "", "logo": ""}
    try:
        t = fetch("%s/all/teams/%s" % (BASE, tid)).get("team", {})
        info = {"name": t.get("displayName") or tid,
                "short": t.get("shortDisplayName") or t.get("displayName") or tid,
                "abbr": t.get("abbreviation") or "",
                "color": t.get("color") or "", "alt": t.get("alternateColor") or "",
                "logo": ((t.get("logos") or [{}])[0]).get("href") or ""}
    except requests.RequestException as e:
        print("  WARN: team %s: %s" % (tid, e), file=sys.stderr)
        return info
    teams[tid] = info
    return info


# ---------------------------------------------------------------- finishes
def ordinal(n):
    n = int(n)
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def league_table(slug, season):
    """{team id: position}. A finished season is cached for good."""
    try:
        d = fetch("%s/%s/standings" % (STANDINGS, slug), {"season": season},
                  cacheable=season_over(season))
    except requests.RequestException:
        return {}
    out = {}
    for ch in d.get("children") or []:
        for e in (ch.get("standings") or {}).get("entries") or []:
            rank = next((s.get("value") for s in e.get("stats") or [] if s.get("name") == "rank"), None)
            if rank:
                out[str(e["team"]["id"])] = int(rank)
    return out


STAGE_SHORT = {"Final": "Final", "Semifinals": "SF", "Quarterfinals": "QF",
               "Round of 16": "R16", "Round of 32": "R32", "Group Stage": "Group",
               "League Phase": "League", "Knockout Round Playoffs": "KO PO",
               "Playoff Round": "PO", "Fifth Round": "R5", "Fourth Round": "R4",
               "Third Round": "R3", "Second Round": "R2", "First Round": "R1",
               "Sixth Round": "R6", "Second Qualifying Round": "Q2",
               "Third Qualifying Round": "Q3"}
QUAL_SLUG = {"UCL": "uefa.champions_qual", "UEL": "uefa.europa_qual",
             "UECL": "uefa.europa.conf_qual"}


def cup_run(code, season, tid, finishes):
    """How far a club went in a competition that season: "Winner", "Final",
    "SF"... Kept in data/finishes.json once the season is over."""
    key = "%s|%d|%s" % (code, season, tid)
    if key in finishes:
        return finishes[key]
    # the main competition first; a club that never reached it went out in
    # qualifying, which ESPN files under a league of its own
    ev, qual = [], False
    for slug in (MAIN_SLUG[code], QUAL_SLUG.get(code)):
        if not slug:
            continue
        try:
            d = fetch("%s/%s/teams/%s/schedule" % (BASE, slug, tid),
                      {"season": season}, cacheable=season_over(season))
        except requests.RequestException:
            return ""
        ev = sorted((e for e in d.get("events") or []
                     if e["competitions"][0]["status"]["type"].get("completed")),
                    key=lambda e: e["date"])
        if ev:
            qual = slug == QUAL_SLUG.get(code)
            break
    if not ev:
        return ""
    last = ev[-1]
    stage = norm_stage(code, (last.get("seasonType") or {}).get("name"), season, qual)
    me = next(c for c in last["competitions"][0]["competitors"] if str(c["id"]) == str(tid))
    out = "Winner" if stage == "Final" and me.get("winner") else STAGE_SHORT.get(stage, stage)
    if season_over(season):
        finishes[key] = out
    return out


# ---------------------------------------------------------------- matches
def score_of(c):
    s = c.get("score")
    if isinstance(s, dict):
        s = s.get("displayValue") if s.get("displayValue") is not None else s.get("value")
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def shootout_of(notes):
    """ESPN only says it in words: "Tottenham Hotspur advance 5-4 on penalties."
    -> (winner is Spurs, "5-4"). The name varies -- Hull 2013 reads "Spurs win
    8-7 on penalties" -- so Spurs is recognised by either word."""
    for n in notes:
        m = re.search(r"^(.*?) (?:advance|advances|win|wins) (\d+)-(\d+) on penalties", n or "")
        if m:
            ours = bool(re.search(r"Tottenham|Spurs", m.group(1)))
            return ours, m.group(2) + "-" + m.group(3)
    return None


def pens_from_summary(eid, team):
    """The shootout, from the match summary: {team: score} on the competitors.
    ESPN's NOTE is not always there -- the 2013 Super Cup has none -- but the
    summary carries shootoutScore whenever penalties were taken. Returns
    (this team won it, "5-4") or None."""
    try:
        s = fetch("%s/all/summary" % BASE, {"event": eid})
    except requests.RequestException:
        return None
    comps = ((s.get("header") or {}).get("competitions") or [{}])[0].get("competitors") or []
    got = {str(c["team"]["id"]): c.get("shootoutScore") for c in comps
           if c.get("team") and c.get("shootoutScore") is not None}
    if len(got) != 2 or str(team) not in got:
        return None
    mine = got[str(team)]
    theirs = next(v for k, v in got.items() if k != str(team))
    if mine == theirs:
        return None
    return mine > theirs, "%d-%d" % (max(mine, theirs), min(mine, theirs))


def venue_place(venue):
    """A neutral ground is named by city -- except Wembley, which is the story."""
    name = (venue or {}).get("fullName") or ""
    if "Wembley" in name:
        return "Wembley"
    return ((venue or {}).get("address") or {}).get("city") or name


def build_match(e, season, teams, goal_store, finishes, pl_table, mw_map, lp_tables):
    slug = e["league"]["slug"]
    code, comp_name = COMPS[slug]
    c = e["competitions"][0]
    status = c["status"]["type"]
    us = next(x for x in c["competitors"] if str(x["id"]) == SPURS)
    them = next(x for x in c["competitors"] if str(x["id"]) != SPURS)
    tid = str(them["id"])
    info = team_info(tid, teams)
    when = dt.datetime.strptime(e["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
    et, uk = when.astimezone(ET), when.astimezone(UK)
    stage = norm_stage(code, (e.get("seasonType") or {}).get("name"), season,
                       is_qualifier(slug))
    notes = [n.get("text") for n in c.get("notes") or [] if n.get("text")]
    neutral = (stage == "Final" or code == "USC" or
               (code == "FAC" and stage == "Semifinals"))
    upcoming = not status.get("completed")
    postponed = status.get("name") in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_ABANDONED")
    m = {
        "id": e["id"], "season": season, "comp": code, "stage": stage,
        "qual": is_qualifier(slug),
        "date": et.strftime("%Y-%m-%d"), "time": et.strftime("%H:%M") if e.get("timeValid", True) else "TBD",
        "dow": et.strftime("%a"), "uk": uk.strftime("%H:%M"), "ukdow": uk.strftime("%a"),
        "where": "N" if neutral else ("H" if us.get("homeAway") == "home" else "A"),
        # the side ESPN lists as home, kept even on neutral ground: the score
        # boxes always read home then away (his call 2026-09-21)
        "home": us.get("homeAway") == "home",
        "venue": (c.get("venue") or {}).get("fullName") or "",
        "opp": tid,
        "nets": [n.get("media", {}).get("shortName") for n in c.get("broadcasts") or []
                 if n.get("media", {}).get("shortName")],
    }
    if neutral:
        m["place"] = venue_place(c.get("venue"))
    if postponed:
        m["status"] = status.get("name")
        return m
    if upcoming:
        m["upcoming"] = True
    else:
        m["us"], m["them"] = score_of(us), score_of(them)
        so = shootout_of(notes)
        # a drawn CUP tie was settled somehow: ask the summary, which carries
        # the shootout even when the note does not
        if not so and m["us"] == m["them"] and code != "PL":
            so = pens_from_summary(e["id"], SPURS)
        if so:
            m["pens"] = so[1]
            m["result"] = "W" if so[0] else "L"
        elif m["us"] > m["them"]:
            m["result"] = "W"
        elif m["us"] < m["them"]:
            m["result"] = "L"
        else:
            m["result"] = "D"
        if any("extra time" in (n or "").lower() or "aet" in (n or "").lower() for n in notes):
            m["aet"] = True
        # goals, kept forever once read
        if e["id"] not in goal_store:
            g = goals_of(slug, e["id"], SPURS, {SPURS: m["us"], tid: m["them"]})
            goal_store[e["id"]] = g
        goals = goal_store.get(e["id"])
        if goals == "awarded":
            m["awarded"] = True
            goals = None
        elif goals is None:
            m["goals_bad"] = True
        elif any(g[0] > 90 for g in goals):
            m["aet"] = True
        w, q = late_flags(goals, SPURS, tid, m["result"])
        if w:
            m["late_win"] = w
        if q:
            m["late_eq"] = q
    # the opponent's finish: its Premier League position that season, or how
    # far it went in THIS competition when it is not a Premier League club
    if tid in pl_table:
        m["fin"] = ordinal(pl_table[tid])
    elif code in MAIN_SLUG:
        m["fin"] = cup_run(code, season, tid, finishes)
    # the league phase (2024-25 on): both clubs' positions, on knockout cards
    if code in ("UCL", "UEL", "UECL") and season >= 2024 and stage not in ("League Phase", ""):
        t = lp_tables.get(code) or {}
        if tid in t:
            m["opp_lp"] = t[tid]
        if SPURS in t:
            m["us_lp"] = t[SPURS]
    if code == "PL":
        home, away = (SPURS, tid) if m["home"] else (tid, SPURS)
        key = (flat(teams[home]["name"]), flat(teams[away]["name"]))
        if key in mw_map:
            m["mw"] = mw_map[key]
        # ESPN has no US network before 2024-25; the Premier League's own
        # listing has one for every match from 2016-17 (see tv.py)
        if not m["nets"] and not upcoming:
            import tv
            m["nets"] = tv.networks(season, teams[home]["name"], teams[away]["name"])
    return m


def two_legged(matches):
    """The second leg of a two-legged tie carries the aggregate, Spurs first."""
    ties = collections.defaultdict(list)
    for m in matches:
        if m["comp"] in ("PL", "USC") or m["stage"] in ("Final", "Group Stage", "League Phase", ""):
            continue
        if m["comp"] == "FAC":
            continue                      # FA Cup draws went to replays, not legs
        ties[(m["season"], m["comp"], m["stage"], m["opp"])].append(m)
    for legs in ties.values():
        legs.sort(key=lambda m: m["date"])
        if len(legs) == 2 and all("us" in m for m in legs):
            legs[1]["agg"] = "%d-%d" % (sum(m["us"] for m in legs), sum(m["them"] for m in legs))
            legs[0]["leg"], legs[1]["leg"] = 1, 2


def replays(matches):
    """An FA Cup tie played twice: the second is the replay."""
    seen = collections.defaultdict(list)
    for m in matches:
        if m["comp"] == "FAC":
            seen[(m["season"], m["stage"], m["opp"])].append(m)
    for ms in seen.values():
        ms.sort(key=lambda m: m["date"])
        for m in ms[1:]:
            m["stage"] += " Replay"


# ---------------------------------------------------------------- his Sheet
SHEET_ID = "1sDNdbA0dlk7BBIoURKhwau4VJM7BXYxdUMo9aPdpfjo"
# his columns, in the order the CSVs give them. Read by NAME, never position.
SHEET_COLS = ["Year", "Date", "Opponent", "Comp", "Case", "Attended", "Shade",
              "Border", "Footer", "Notes", "Team BG", "Team Font", "Opp BG", "Opp Font"]


def sheet_date(s):
    """His Date column, M/D/YY."""
    try:
        mo, d, y = (s or "").strip().split("/")
        y = "20" + y if len(y) == 2 else y
        return "%s-%02d-%02d" % (y, int(mo), int(d))
    except (ValueError, AttributeError):
        return None


def load_sheet(tab, dates):
    """{date: his row} from one tab, via the gviz CSV export.

    A TAB THAT DOES NOT EXIST IS NOT AN ERROR TO GVIZ: it silently answers
    with the FIRST tab. Comparing against a made-up tab's answer is no test,
    because the first tab is itself one he asks for (Tottenham, since he
    deleted the Michigan tabs 2026-09-21). So the tab must PROVE itself: most
    of its dates must be dates this team actually played (`dates`)."""
    import csv, io
    url = ("https://docs.google.com/spreadsheets/d/%s/gviz/tq?tqx=out:csv&headers=1&sheet=%s"
           % (SHEET_ID, "%s"))
    try:
        r = requests.get(url % requests.utils.quote(tab), timeout=60)
        r.raise_for_status()
        body = r.content.decode("utf-8-sig")
    except requests.RequestException as e:
        print("  WARN: could not read the %s tab (%s)" % (tab, e), file=sys.stderr)
        return {}
    rows = list(csv.reader(io.StringIO(body)))
    if not rows:
        return {}
    head = rows[0]
    # only the block before the first BLANK header is his
    stop = next((i for i, x in enumerate(head) if not (x or "").strip()), len(head))
    col = {}
    for i, x in enumerate(head[:stop]):
        k = (x or "").strip().lower()
        if k and k not in col:
            col[k] = i
    if "date" not in col:
        print("  WARN: the %s tab has no Date column" % tab, file=sys.stderr)
        return {}
    found = [sheet_date(r[col["date"]]) for r in rows[1:] if col["date"] < len(r)]
    found = [d for d in found if d]
    hits = sum(1 for d in found if d in dates)
    if not found or hits < 0.5 * len(found):
        print("  WARN: the %s tab is missing (Google sent another tab: %d of %d dates match)"
              " -- skipped" % (tab, hits, len(found)), file=sys.stderr)
        return {}
    out = {}
    for raw in rows[1:]:
        cell = lambda k: (raw[col[k]] or "").strip() if k in col and col[k] < len(raw) else ""
        d = sheet_date(cell("date"))
        if not d:
            continue
        mx = {"case": cell("case"), "attended": bool(cell("attended")),
              "shade": bool(cell("shade")), "border": cell("border"), "footer": cell("footer"),
              "note": cell("notes") or cell("note"),
              "team_bg": cell("team bg"), "team_font": cell("team font"),
              "opp_bg": cell("opp bg"), "opp_font": cell("opp font")}
        mx = {k: v for k, v in mx.items() if v}
        if mx:
            out[d] = mx
    print("  sheet: %s tab, %d rows marked" % (tab, len(out)))
    return out


def main():
    this = current_season()
    teams = load_data("teams.json", {})
    goal_store = load_data("goals.json", {})
    finishes = load_data("finishes.json", {})
    team_info(SPURS, teams)
    matches = []
    for season in range(FIRST_SEASON, this + 1):
        over = season_over(season)
        events = fetch("%s/all/teams/%s/schedule" % (BASE, SPURS), {"season": season},
                       cacheable=over).get("events") or []
        if season == this:
            more = fetch("%s/all/teams/%s/schedule" % (BASE, SPURS),
                         {"season": season, "fixture": "true"}, cacheable=False).get("events") or []
            ids = {e["id"] for e in events}
            events += [e for e in more if e["id"] not in ids]
        events = [e for e in events if (e.get("league") or {}).get("slug") in COMPS]
        pl_table = league_table("eng.1", season)
        mw_map = matchweeks(season)
        lp_tables = {}
        if season >= 2024:
            for code, slug in (("UCL", "uefa.champions"), ("UEL", "uefa.europa"),
                               ("UECL", "uefa.europa.conf")):
                if any(COMPS[e["league"]["slug"]][0] == code for e in events):
                    lp_tables[code] = league_table(slug, season)
        got = [build_match(e, season, teams, goal_store, finishes, pl_table, mw_map, lp_tables)
               for e in events]
        played = [m for m in got if "us" in m]
        missing_mw = [m for m in got if m["comp"] == "PL" and "mw" not in m]
        print("  %s  %d matches (%d played)%s" % (
            season_label(season), len(got), len(played),
            ("  NO MATCHWEEK: %d" % len(missing_mw)) if missing_mw else ""))
        if over and len(played) < MIN_MATCHES:
            raise SystemExit("ABORT: %s has only %d played matches -- ESPN answered short"
                             % (season_label(season), len(played)))
        matches += got
    replays(matches)
    two_legged(matches)
    matches.sort(key=lambda m: (m["date"], m["time"]))
    # his Sheet, matched on the date (Spurs never play twice in a day)
    marks = load_sheet("Tottenham", {m["date"] for m in matches})
    for m in matches:
        m["team"] = "spurs"
        if m["date"] in marks:
            m["mx"] = marks[m["date"]]
    # USMNT and Atlanta United (others.py), each with its own Sheet tab
    import others
    us, atl = others.main()
    for key, tab, ms in (("usmnt", "USMNT", us), ("atlanta", "Atlanta United", atl)):
        ms = others.tidy(key, ms)
        marks = load_sheet(tab, {m["date"] for m in ms})
        for m in ms:
            team_info(m["opp"], teams)
            m.pop("opp_name", None)
            if m["date"] in marks:
                m["mx"] = marks[m["date"]]
        matches += ms
    for t in (others.USA, others.ATL):
        team_info(t, teams)
    # the EPL/Rivals tab: Arsenal and Chelsea's bad results, and the two
    # Premier League TV windows
    import rivals, windows
    matches += rivals.collect(teams)
    matches += windows.collect(teams)

    bad = [m["id"] for m in matches if m.get("goals_bad")]
    if bad:
        print("  WARN: %d matches whose goal list does not add up: %s" % (len(bad), bad[:10]))
    # a goal list that failed to add up is not stored as final -- retry next run
    for k in bad:
        goal_store.pop(k, None)
    import tv
    tv.save()
    save_data("teams.json", teams)
    save_data("goals.json", goal_store)
    save_data("finishes.json", finishes)

    used = ({m["opp"] for m in matches if m.get("opp")} |
            {m["home"] for m in matches if m.get("team") == "windows"} |
            {m["away"] for m in matches if m.get("team") == "windows"} |
            {m["rival"] for m in matches if m.get("team") == "rivals"} |
            {SPURS, others.USA, others.ATL})
    for t in used:
        if t in teams:
            teams[t]["card"] = CARD_NAME.get(teams[t]["name"], teams[t]["name"])
            # a few clubs (PSG) come back with no logo link; ESPN's crest is
            # still at its usual address
            if not teams[t].get("logo"):
                teams[t]["logo"] = "https://a.espncdn.com/i/teamlogos/soccer/500/%s.png" % t
    os.makedirs(OUT, exist_ok=True)
    out = {"built": dt.datetime.now(ET).strftime("%Y-%m-%d %H:%M"),
           "current": this,
           "teams": {t: teams[t] for t in sorted(used) if t in teams},
           "matches": matches}
    json.dump(out, open(os.path.join(OUT, "games.json"), "w", encoding="utf-8"),
              separators=(",", ":"), ensure_ascii=False)
    lw = sum(1 for m in matches if m.get("late_win"))
    le = sum(1 for m in matches if m.get("late_eq"))
    print("output/games.json  %d matches, %d opponents, %d late winners, %d late equalizers"
          % (len(matches), len(used) - 1, lw, le))


if __name__ == "__main__":
    main()
