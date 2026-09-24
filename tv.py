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
