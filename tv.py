"""US networks for Premier League matches, from the Premier League's own data.

ESPN has no broadcast at all before 2024-25 (checked: its public API, its core
API and its scoreboards are all empty), so the networks come from
footballapi.pulselive.com -- what premierleague.com itself lists. That has the
US listing for every match from 2016-17 on; 2013-14 to 2015-16 have none
anywhere I could find.

One call per match, kept in data/tv.json for good: a finished match's network
never changes. Premier League only -- the cups and Europe are not in it.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
import harvest as h

API = "https://footballapi.pulselive.com/football"
HEADERS = {"Origin": "https://www.premierleague.com",
           "Referer": "https://www.premierleague.com/",
           "User-Agent": "Mozilla/5.0", "Account": "premierleague"}
FIRST = 2016                       # the first season with US listings
# their abbreviations -> the names the cards use
NAMES = {"NBC": "NBC", "USANBCSN": "NBCSN", "USANET": "USA", "USACNBC": "CNBC",
         "USPEA": "Peacock", "NBCGOLD": "NBC Sports Gold", "USASYFY": "Syfy",
         "UNIVERSO": "Universo", "TELEMUND": "Telemundo", "USATELEXITOS": "TeleXitos"}

_seasons = {}
_index = {}
_store = None


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def season_id(season):
    """Their compSeason id for "2016/17"."""
    if not _seasons:
        for page in range(6):
            try:
                d = get("%s/competitions/1/compseasons?page=%d&pageSize=10" % (API, page))
            except Exception as e:
                print("  WARN: Premier League seasons: %s" % e, file=sys.stderr)
                break
            for c in d.get("content") or []:
                _seasons[c["label"]] = int(c["id"])
            if page + 1 >= (d.get("pageInfo") or {}).get("numPages", 0):
                break
    return _seasons.get("%d/%d" % (season, (season + 1) % 100))


def fixtures(season):
    """{(home flat, away flat): fixture id} for a season."""
    if season in _index:
        return _index[season]
    out = {}
    sid = season_id(season)
    if sid:
        for page in range(6):
            url = ("%s/fixtures?comps=1&compSeasons=%d&page=%d&pageSize=100&sort=asc"
                   "&statuses=C,U" % (API, sid, page))
            try:
                d = get(url)
            except Exception as e:
                print("  WARN: Premier League fixtures %s: %s" % (season, e), file=sys.stderr)
                break
            for f in d.get("content") or []:
                teams = [t["team"]["name"] for t in f.get("teams") or []]
                if len(teams) == 2:
                    out[(h.flat(teams[0]), h.flat(teams[1]))] = int(f["id"])
            if page + 1 >= (d.get("pageInfo") or {}).get("numPages", 0):
                break
    _index[season] = out
    return out


def store():
    global _store
    if _store is None:
        _store = h.load_data("tv.json", {})
    return _store


def save():
    if _store is not None:
        h.save_data("tv.json", _store)


def networks(season, home_name, away_name, final=True):
    """["NBC", "Universo"] for one Premier League match, or []."""
    if season < FIRST:
        return []
    key = "%d|%s|%s" % (season, h.flat(home_name), h.flat(away_name))
    st = store()
    if key in st:
        return st[key]
    fid = fixtures(season).get((h.flat(home_name), h.flat(away_name)))
    if not fid:
        return []
    try:
        d = get("%s/broadcasting-schedule/fixtures/%d?countryCode=USA" % (API, fid))
    except Exception:
        return []
    nets = []
    for b in d.get("broadcasters") or []:
        name = NAMES.get(b.get("abbreviation"), b.get("abbreviation"))
        if name and name not in nets:
            nets.append(name)
    if final:                      # a played match keeps its listing for good
        st[key] = nets
    return nets


# ---------------------------------------------------------------- 2013-16
# The Premier League's own data starts at 2016-17, and ESPN at 2024-25, so the
# first three seasons -- and the older cup and European matches -- come from
# livesoccertv's daily schedule pages, which list the US channels per match
# (his suggestion 2026-09-26). One page per DATE, cached in cache/ as raw HTML
# and the result kept in data/tv.json like everything else.
import html as html_lib
import os
import re as _re
import unicodedata

LSTV = "https://www.livesoccertv.com/schedules/%s/"
LSTV_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
# what to keep off a row, in the order a card should prefer: the networks
# first, then the overflow streams. Radio (SiriusXM, TalkSport), club sites
# and the carriers that only sold the overflow package are dropped.
# livesoccertv writes a channel a dozen ways -- "Fox Sports 2 USA", "NBCSN
# (United States)", "ESPN3 USA" -- so a name is cleaned first (country tails
# removed) and then looked up. Radio (SiriusXM, TalkSport, Westwood One),
# carriers and aggregators (DIRECTV, fuboTV, beIN SPORTS CONNECT), club sites
# and regional channels are simply absent from the table, so they are dropped.
LSTV_NAMES = {
    "nbc": "NBC", "nbcsn": "NBCSN", "nbc sports network": "NBCSN",
    "nbc sports": "NBCSN", "usa network": "USA", "cnbc": "CNBC", "syfy": "Syfy",
    "peacock": "Peacock", "nbc sports gold": "NBC Sports Gold",
    "premier league extra time": "PL Extra Time",
    "nbc sports app": "NBC Sports App", "nbc sports live extra": "NBC Sports App",
    "fox sports 1": "FS1", "fs1": "FS1", "fox sports 2": "FS2", "fs2": "FS2",
    "fox soccer plus": "FOX Soccer Plus", "fox": "FOX", "fox sports": "FOX",
    "espn": "ESPN", "espn2": "ESPN2", "espnews": "ESPNEWS", "espn3": "ESPN3",
    "espn+": "ESPN+", "espn plus": "ESPN+", "espn app": "ESPN App",
    "cbs": "CBS", "cbs sports network": "CBSSN", "cbssn": "CBSSN",
    "paramount+": "Paramount+", "cbs sports golazo": "CBS Sports Golazo",
    "bein sports": "beIN", "goltv": "GOLTV",
    "tnt": "TNT", "b/r live": "B/R Live", "bleacher report live": "B/R Live",
    "bleacher report app": "B/R Live", "univision now": "Univision",
    "unimas": "UniMas", "galavision": "Galavision", "tudn app": "TUDN",
    "tudn.com": "TUDN", "tudnxtra": "TUDN", "universo now": "Universo",
    "telemundo deportes en vivo": "Telemundo",
    "cbs all access": "CBS All Access", "watch espn": "ESPN App",
    "fox sports go": "FOX Sports GO", "fox sports plus": "FOX Soccer Plus",
    "univision deportes network": "UDN", "udn": "UDN", "galavision": "Galavisión",
    "espn deportes+": "ESPN Deportes", "telemundo deportes": "Telemundo",
    "telemundo": "Telemundo", "universo": "Universo", "telexitos": "TeleXitos",
    "univision": "Univision", "unimas": "UniMas", "tudn": "TUDN",
    "fox deportes": "FOX Deportes", "espn deportes": "ESPN Deportes",
    "azteca america": "Azteca America",
}
# what a card prefers when a match was on several: the networks he watches
# first, the streams next, Spanish last
LSTV_ORDER = ["NBC", "NBCSN", "USA", "CNBC", "Syfy", "FS1", "FS2", "FOX",
              "FOX Soccer Plus", "ESPN", "ESPN2", "ESPNEWS", "CBS", "CBSSN",
              "beIN", "GOLTV", "Peacock", "Paramount+", "ESPN+", "ESPN3",
              "ESPN App", "CBS Sports Golazo", "NBC Sports Gold", "TNT",
              "B/R Live", "CBS All Access", "FOX Sports GO",
              "PL Extra Time", "NBC Sports App", "Telemundo", "Universo",
              "TeleXitos", "Univision", "UniMas", "TUDN", "Galavision",
              "FOX Deportes",
              "ESPN Deportes", "Azteca America"]


def lstv_channel(title):
    """"Fox Sports 2 USA" -> "FS2"; a radio station or carrier -> None.
    Accents are folded, so "UniMas" matches "UniMas"."""
    t = _re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
    t = _re.sub(r"\s+(?:U\.?S\.?A\.?|United States)$", "", t, flags=_re.I).strip()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return LSTV_NAMES.get(t.lower())


def lstv_page(date):
    """That day's schedule page, cached on disk -- a past day never changes.

    Retries: fetching hundreds of pages in a row draws the odd refusal, and a
    failure that is taken for "no TV" would be cached for good (it was, on the
    first run: 657 matches came out blank that do have a network).
    """
    path = os.path.join(h.CACHE, "lstv-%s.html" % date)
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    wait = 2
    for attempt in range(4):
        try:
            req = urllib.request.Request(LSTV % date,
                                         headers={"User-Agent": LSTV_UA,
                                                  "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read().decode("utf-8", "replace")
            os.makedirs(h.CACHE, exist_ok=True)
            open(path, "w", encoding="utf-8").write(body)
            time.sleep(0.4)               # their site, their pace
            return body
        except Exception as e:
            if attempt == 3:
                raise
            print("  retry %d for livesoccertv %s (%s)" % (attempt + 1, date, e),
                  file=sys.stderr)
            time.sleep(wait)
            wait *= 2


_days = {}


def lstv_day(date):
    """{(home flat, away flat): [networks]} for one date."""
    if date in _days:
        return _days[date]
    out = {}
    try:
        body = lstv_page(date)
    except Exception as e:
        # a page that could not be read is NOT "no TV": leave it unknown so
        # the next run tries again
        print("  WARN: livesoccertv %s: %s" % (date, e), file=sys.stderr)
        return None
    # some rows carry class="matchrow" and some an empty class, so the row is
    # found by its kickoff attribute instead
    for row in _re.findall(r'<tr[^>]*data-ko="[^"]*".*?</tr>', body, _re.S):
        m = _re.search(r'title="([^"]+?) vs ([^"]+?)"', row)
        if not m:
            continue
        home, away = html_lib.unescape(m.group(1)), html_lib.unescape(m.group(2))
        # class="homech" marks the channels of the country asked from, which
        # is the US
        names = {html_lib.unescape(x) for x in
                 _re.findall(r'<a href="/channels/[^"]*"\s+title="([^"]+)"\s+class="homech"', row)}
        got = {lstv_channel(n) for n in names} - {None}
        nets = [n for n in LSTV_ORDER if n in got]
        if nets:
            out[(h.flat(home), h.flat(away))] = nets
    _days[date] = out
    return out


def networks_any(date, home_name, away_name, final=True):
    """A US network for any match, from livesoccertv, by date and clubs."""
    key = "d%s|%s|%s" % (date, h.flat(home_name), h.flat(away_name))
    st = store()
    if key in st:
        return st[key]
    day = lstv_day(date)
    if day is None:
        return []                     # unknown, not empty -- nothing is stored
    nets = day.get((h.flat(home_name), h.flat(away_name)), [])
    if final:
        st[key] = nets
    return nets


# ---------------------------------------------------------------- one list
# Every source spells a channel its own way -- ESPN says "USA Net" and "Tele",
# the Premier League "USANBC", livesoccertv "Fox Sports 2 USA" -- so every
# list of networks passes through here before it reaches a card.
CANON = {
    "USA Net": "USA", "USA Network": "USA", "USANET": "USA",
    "USANBC": "NBC", "USANBCSN": "NBCSN", "NBC Sports Network": "NBCSN",
    "USACNBC": "CNBC", "USPEA": "Peacock", "NBCGOLD": "NBC Sports Gold",
    "Tele": "Telemundo", "TELEMUND": "Telemundo", "UNIVERSO": "Universo",
    "Fox Sports 1": "FS1", "Fox Sports 2": "FS2",
}
# SPANISH-LANGUAGE AND FOREIGN CHANNELS ARE DROPPED (his call 2026-09-26)
HIDE = {"Telemundo", "Universo", "TeleXitos", "Univision", "UniMas", "TUDN",
        "Galavision", "FOX Deportes", "ESPN Deportes", "Azteca America",
        "Disney+", "UniMás"}
# what a card prefers when a match was on more than one
ORDER = ["NBC", "NBCSN", "USA", "CNBC", "Syfy", "FOX", "FS1", "FS2",
         "FOX Soccer Plus", "CBS", "CBSSN", "ESPN", "ESPN2", "ESPNEWS", "TNT",
         "beIN", "GOLTV", "Peacock", "Paramount+", "ESPN+", "B/R Live",
         "CBS All Access", "NBC Sports Gold", "ESPN3", "PL Extra Time",
         "NBC Sports App", "ESPN App", "FOX Sports GO", "CBS Sports Golazo"]


def clean(nets):
    """Canonical names, the hidden ones dropped, in the order a card wants."""
    got = []
    for n in nets or []:
        n = CANON.get(n, n)
        if n and n not in HIDE and n not in got:
            got.append(n)
    known = [n for n in ORDER if n in got]
    return known + [n for n in got if n not in ORDER]
