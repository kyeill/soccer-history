"""Write the three CSVs Kyle imports into his Sheet, one per tab:
sheet/Tottenham.csv, sheet/USMNT.csv, sheet/Atlanta United.csv.

Every match, oldest first, with his columns empty. Importing a CSV with
"Insert new sheet" names the tab after the file, which is exactly the tab name
harvest.py reads. Run after harvest.py and others.py.
"""
import csv, json, os
import harvest as h

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "sheet")


def mdy(d):
    return "%d/%d/%s" % (int(d[5:7]), int(d[8:10]), d[2:4])


def write(name, rows):
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, name + ".csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(h.SHEET_COLS)
        for r in rows:
            w.writerow(r + [""] * (len(h.SHEET_COLS) - len(r)))
    print("  %s  %d rows" % (path, len(rows)))


def spurs():
    g = json.load(open(os.path.join(HERE, "output", "games.json"), encoding="utf-8"))
    names = {"PL": "Premier League", "FAC": "FA Cup", "LC": "League Cup",
             "UCL": "Champions League", "UEL": "Europa League", "UECL": "Conference League",
             "USC": "Super Cup"}
    rows = []
    for m in (m for m in g["matches"] if m.get("team", "spurs") == "spurs"):
        t = g["teams"].get(m["opp"], {})
        comp = names[m["comp"]] + (" MW %d" % m["mw"] if m.get("mw") else
                                   (" " + m["stage"] if m.get("stage") else ""))
        rows.append([h.season_label(m["season"]), mdy(m["date"]), t.get("card") or t.get("name"),
                     comp])
    return rows


def other(store_file, names):
    ms = sorted(h.load_data(store_file, {}).get("matches", {}).values(), key=lambda m: m["date"])
    return [[str(m["year"]), mdy(m["date"]), m["opp_name"],
             (names[m["comp"]] + " " + m["stage"].strip()).strip()] for m in ms]


if __name__ == "__main__":
    import others
    write("Tottenham", spurs())
    write("USMNT", other("usmnt.json", dict(others.US_COMPS.values())))
    write("Atlanta United", other("atlanta.json", dict(others.ATL_COMPS.values())))
