"""Build Soccer History into docs/, which GitHub Pages serves.

The CSS is games-history's, trimmed to the Michigan card and the filter bar
it shares -- copied, not imported: the two apps share nothing at runtime.
"""
import json
import os
import shutil
import struct
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
SITE = os.path.join(HERE, "docs")

CSS = """
:root{
  --bg:#16161a; --card:#1e1e23; --ink:#ececea; --muted:#9a9a95;
  --line:#2b2b31; --rank:#8fb0d8; --accent:#e0834f;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:15px;line-height:1.45;-webkit-font-smoothing:antialiased;
  overscroll-behavior-y:none}
.wrap{max-width:1180px;margin:0 auto;padding:0 14px 90px}
header{display:flex;align-items:baseline;gap:9px;padding:18px 0 10px}
h1{font-size:22px;margin:0;letter-spacing:-.2px;font-weight:700;line-height:1.2}
.count{color:var(--muted);font-size:13.5px;font-variant-numeric:tabular-nums;
  line-height:1.2}
.spacer{flex:1}
.iconbtn{background:none;border:1px solid var(--line);color:var(--muted);
  border-radius:7px;padding:4px 9px;font:inherit;font-size:13px;cursor:pointer}
.iconbtn:hover{color:var(--ink);border-color:#3b3b43}
.iconbtn:focus-visible{outline:2px solid var(--rank);outline-offset:2px}

nav{position:sticky;top:0;z-index:6;background:var(--bg);display:flex;gap:2px;
  border-bottom:1px solid var(--line);margin-bottom:10px}
nav button{flex:1;background:none;border:0;border-bottom:2px solid transparent;
  color:var(--muted);font:inherit;font-size:14.5px;font-weight:600;
  padding:9px 4px;cursor:pointer}
nav button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent)}

/* the two views inside EPL/Rivals -- a segmented control, not more tabs */
.viewbar{display:inline-flex;gap:0;margin:0 0 12px;border:1px solid var(--line);
  border-radius:8px;overflow:hidden;background:var(--card)}
.viewbar button{background:none;border:0;color:var(--muted);font:inherit;
  font-size:13.5px;font-weight:600;padding:6px 16px;cursor:pointer;white-space:nowrap}
.viewbar button[aria-selected="true"]{background:#2e3a48;color:#cfe0f2}

/* A TWO-TEAM CARD (TV Windows, Rivals): away line over home line, the
   winner's line washed in its own colour */
.row.two .tl2{display:grid;grid-template-columns:22px minmax(0,1fr) auto;
  column-gap:8px;align-items:center;height:26px;padding:0 6px 0 7px;
  margin-left:-7px;border-radius:5px}
.row.two .tl2.won{background:var(--winwash)}
.row.two .tl2.won .nm{font-weight:600}
.row.two .tl2:not(.won) .nm{color:#a5a5a0}
.row.two .sc{font-size:15px;font-variant-numeric:tabular-nums;font-weight:600;
  min-width:18px;text-align:right}
.row.two .sport{justify-content:space-between;flex-wrap:nowrap;gap:8px}

.filters{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
.f{border:1px solid var(--line);background:var(--card);color:var(--muted);
  border-radius:999px;padding:3px 11px;font:inherit;font-size:13px;
  cursor:pointer;white-space:nowrap}
.f[aria-pressed="true"]{background:#2e3a48;border-color:#3f5064;color:#cfe0f2}
.f:focus-visible{outline:2px solid var(--rank);outline-offset:2px}
.fgroup{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.fsel{background:var(--card);border:1px solid var(--line);color:var(--ink);
  border-radius:999px;padding:4px 10px;font:inherit;font-size:13px;
  max-width:210px;cursor:pointer}
.fsel:focus-visible{outline:2px solid var(--rank);outline-offset:2px}
.flabel{font-size:11px;text-transform:uppercase;letter-spacing:.07em;
  color:var(--muted);font-weight:700;margin-right:2px}
.flabel:empty{margin-right:0}

#list{display:grid;grid-template-columns:1fr;gap:8px;align-content:start}
@media (min-width:900px){#list{grid-template-columns:1fr 1fr;gap:9px}}
@media (min-width:1240px){
  #list{grid-template-columns:repeat(3,1fr);gap:9px}
  #list .row{padding:10px 11px}
}
#list .empty{grid-column:1/-1}

/* THE CARD -- games-history's Michigan card */
.row{display:grid;background:var(--card);border:1px solid var(--line);
  border-radius:9px;padding:10px 13px;grid-template-columns:1fr;
  grid-template-areas:"sport" "teams" "tags";align-items:start;align-content:start}
.row.celebrate{border-color:var(--celeb,#ffcb05);
  box-shadow:0 0 0 1px var(--celebring,#ffcb0544)}
.row.predash{border-style:dashed;box-shadow:none}
.sport{grid-area:sport;display:flex;flex-wrap:wrap;row-gap:2px;align-items:baseline;
  gap:10px;font-size:13px;font-weight:400;letter-spacing:.05em;
  text-transform:uppercase;color:var(--muted);margin-bottom:5px}
.hdate{font-variant-numeric:tabular-nums}
.teams{grid-area:teams;display:flex;flex-direction:column;gap:3px}
.tl{display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:6px;
  align-items:center}
.crest{width:21px;height:21px;object-fit:contain;display:block}
.mstripe{display:grid;grid-template-columns:22px minmax(0,1fr);column-gap:7px;
  align-items:baseline;align-content:center;min-width:0;height:26px;
  padding:0 6px 0 7px;margin-left:-7px;border-radius:5px}
.mstripe .crest{align-self:center}
.tl.won .mstripe{background:var(--winwash)}
.nm{font-size:15.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tl.won .nm{font-weight:600}
.tl:not(.won) .nm{color:#a5a5a0}
.nm.mnm{display:flex;align-items:baseline;min-width:0}
.mn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
/* a loss strikes the opponent through, as a Michigan loss does */
.row.dimmed .mn{text-decoration:line-through;text-decoration-thickness:1.5px}
.mfin{flex:none;margin-left:6px;font-size:12px;font-weight:400;
  color:var(--muted);font-style:normal}
/* the league-phase position in front of the name */
.rkin{color:var(--rank);font-weight:600;font-variant-numeric:tabular-nums}
.row.dimmed .rkin{color:var(--muted)}
.sc.mbox{display:inline-flex;align-items:center;justify-content:center;
  box-sizing:border-box;height:26px;padding:0 8px;border-radius:4px;
  font-size:14.5px;font-weight:400;font-variant-numeric:tabular-nums;
  white-space:nowrap;min-width:calc(5.4ch + 16px)}
.sc.mbox.u{text-decoration:underline;text-underline-offset:3px}
.sc.mbox.l{font-style:italic}
/* two boxes, Spurs' then the opponent's (his call 2026-09-21), each sized for
   two digits so a 10-goal night does not jump the card */
.boxes{display:inline-flex;gap:4px}
.boxes .sc.mbox{min-width:calc(2ch + 16px);padding:0 6px}
/* his Shade column fills the whole card in the opponent's colour */
.row.mwash{background:var(--winwash)}
.row.mwash .tl.won .mstripe{background:transparent}
/* HE WAS THERE: a star under the crest, grey on a loss */
.tags.mdets{position:relative}
.mstar{position:absolute;left:0;top:50%;transform:translateY(-50%);width:22px;
  text-align:center;color:#f2f2f0;font-weight:700;font-size:16px;line-height:1}
.row.dimmed .mstar{color:#8a8a92}
.tags.mdets{grid-area:tags;display:flex;align-items:center;font-size:13px;
  letter-spacing:.05em;color:var(--muted);margin-top:5px}
.tags.mdets:empty{display:none}
.mdl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;min-width:0;
  padding-left:29px}
.msep{color:var(--muted)}
.hdow{text-transform:uppercase}

.empty{color:var(--muted);text-align:center;padding:44px 10px;font-size:14.5px}
@media (max-width:560px){h1{font-size:20px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

BODY = """
<div class="wrap">
<header>
  <h1>Soccer History</h1>
  <span class="count" id="count"></span>
  <span class="spacer"></span>
  <button class="iconbtn" id="clearbtn">Clear Filters</button>
</header>
<nav>
  <button data-top="spurs" aria-selected="true">Tottenham</button>
  <button data-top="epl" aria-selected="false">EPL/Rivals</button>
  <button data-top="usmnt" aria-selected="false">USMNT</button>
  <button data-top="atlanta" aria-selected="false">Atlanta</button>
</nav>
<div class="viewbar" id="viewbar" style="display:none"></div>
<div class="filters" id="filters"></div>
<div id="list"></div>
</div>
"""

MANIFEST = {
    "name": "Soccer History", "short_name": "Soccer",
    "start_url": ".", "scope": ".", "display": "standalone",
    "background_color": "#16161a", "theme_color": "#16161a",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png",
         "purpose": "any maskable"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png",
         "purpose": "any maskable"},
    ],
}

# Bumped on every build so a redeploy is never served from the old cache.
SW = """
const CACHE="soccer-history-__BUILD__";
const ASSETS=["./","./index.html","./manifest.webmanifest"];
self.addEventListener("install",e=>{
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(
    ASSETS.map(u=>new Request(u,{cache:"reload"})))).catch(()=>{}));
});
self.addEventListener("activate",e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(
    ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>
      self.clients.claim()));
});
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);
  if(u.host!==location.host) return;
  if(e.request.mode==="navigate"){
    e.respondWith(fetch(e.request,{cache:"no-store"})
      .catch(()=>caches.match("./index.html")));
    return;
  }
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
});
"""


def png(size):
    """The app icon: a card with one winning line, washed Spurs navy on white.
    Full bleed, every mark inside the maskable safe circle (radius 0.4)."""
    bg, card = (0x16, 0x16, 0x1A), (0x1E, 0x1E, 0x23)
    white, navy = (0xF2, 0xF2, 0xF0), (0x13, 0x22, 0x57)
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            u, v = x / size, y / size
            if 0.20 <= u < 0.80 and 0.30 <= v < 0.70:
                if 0.24 <= u < 0.58 and 0.42 <= v < 0.58:
                    c = white                      # the stripe
                elif 0.61 <= u < 0.76 and 0.42 <= v < 0.58:
                    c = navy                       # the score box
                else:
                    c = card
            else:
                c = bg
            row += bytes(c)
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def build():
    data = json.load(open(os.path.join(OUT, "games.json"), encoding="utf-8"))
    os.makedirs(SITE, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    js = open(os.path.join(HERE, "app.js"), encoding="utf-8").read().replace("__BUILD__", stamp)
    html = ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,"
            "initial-scale=1,viewport-fit=cover\">\n"
            "<title>Soccer History</title>\n"
            "<meta name=\"theme-color\" content=\"#16161a\">\n"
            "<link rel=\"manifest\" href=\"manifest.webmanifest\">\n"
            "<link rel=\"icon\" href=\"icon-192.png\">\n"
            "<link rel=\"apple-touch-icon\" href=\"icon-180.png\">\n"
            "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n"
            "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n"
            "<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/"
            "css2?family=Source+Sans+3:wght@400;600;700&display=swap\">\n"
            "<style>%s</style>\n</head>\n<body>%s\n"
            "<script src=\"app.js?v=%s\"></script>\n</body>\n</html>\n"
            % (CSS, BODY, stamp))
    open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(html)
    open(os.path.join(SITE, "app.js"), "w", encoding="utf-8").write(js)
    open(os.path.join(SITE, "sw.js"), "w", encoding="utf-8").write(SW.replace("__BUILD__", stamp))
    json.dump(MANIFEST, open(os.path.join(SITE, "manifest.webmanifest"), "w",
                             encoding="utf-8"), indent=1)
    shutil.copyfile(os.path.join(OUT, "games.json"), os.path.join(SITE, "games.json"))
    for size in (180, 192, 512):
        open(os.path.join(SITE, "icon-%d.png" % size), "wb").write(png(size))
    total = sum(os.path.getsize(os.path.join(SITE, f)) for f in os.listdir(SITE))
    print("docs/  %d matches, %.0f KB total, build %s"
          % (len(data["matches"]), total / 1024, stamp))


if __name__ == "__main__":
    build()
