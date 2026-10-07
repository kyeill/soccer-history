/* Soccer History -- the whole app. site.py copies this in and fills
   __BUILD__. Modelled on games-history's Michigan view (michCard): one card
   per match, the opponent on a colour stripe, the score in a box. */
const BUILD = "__BUILD__";
const CARD = [0x1e, 0x1e, 0x23];
const SPURS = "367";
// the Top Six bar Spurs: they lead the Team filter
// Arsenal, Chelsea, Liverpool, Man City, Man United (his order 2026-10-02)
const TOP_SIX = ["359", "363", "364", "382", "360"];
// and the six WITH Spurs, who wear capitals on the EPL/Rivals cards and
// lead that tab's Team filter (his calls 2026-10-02)
const BIG_SIX = ["367", "359", "363", "364", "382", "360"];
let ALL = [], MATCHES = [], TEAMS = {}, CURRENT = null;
// "date|home|away" -> "NBC Saturday" / "Sky Sunday", built at load from
// the TV Windows population so his teams' cards agree with that view
let WINDOW_OF = {};
let FILT = {};
let SORT = "asc";
// the tab along the top: one view per team of his, plus EPL/Rivals, which
// holds two views of its own (2026-09-24)
let VIEW = "spurs";
let SUB = "tv";
// which population each tab reads out of the one file
function population() {
  return VIEW === "epl" ? (SUB === "tv" ? "windows" : "rivals") : VIEW;
}

const COMP = {
  PL: { name: "Premier League", short: "PL" },
  FAC: { name: "FA Cup", short: "FA Cup" },
  LC: { name: "League Cup", short: "League Cup" },
  UCL: { name: "Champions League", short: "UCL" },
  UEL: { name: "Europa League", short: "UEL" },
  UECL: { name: "Conference League", short: "UECL" },
  USC: { name: "Super Cup", short: "Super Cup" },
  // USMNT
  WC: { name: "World Cup", short: "World Cup" },
  WCQ: { name: "World Cup Qualifying", short: "WCQ" },
  GC: { name: "Gold Cup", short: "Gold Cup" },
  NL: { name: "Nations League", short: "Nations League" },
  CA: { name: "Copa América", short: "Copa América" },
  CCUP: { name: "CONCACAF Cup", short: "CONCACAF Cup" },
  CONF: { name: "Confederations Cup", short: "Confed Cup" },
  // Atlanta United
  MLS: { name: "MLS Cup Playoffs", short: "MLS Playoffs" },
  CCL: { name: "CONCACAF Champions League", short: "CCL" },
  LGC: { name: "Leagues Cup", short: "Leagues Cup" },
  USOC: { name: "U.S. Open Cup", short: "Open Cup" },
  CAMP: { name: "Campeones Cup", short: "Campeones Cup" },
};
/* EACH VIEW: its competitions in his order, its own score box until the Sheet
   colours it, and the clubs that lead its Team filter */
const VIEWS = {
  spurs: { team: SPURS, comps: ["PL", "FAC", "LC", "UCL", "UEL", "UECL", "USC"],
           box: "#132257", lead: TOP_SIX },
  // Mexico, then Canada
  usmnt: { team: "660", comps: ["WC", "WCQ", "GC", "NL", "CA", "CCUP", "CONF"],
           box: "#213065", lead: ["203", "206"] },
  atlanta: { team: "18418", comps: ["MLS", "CCL", "LGC", "USOC", "CAMP"],
             box: "#9d2235", lead: [] },
  // the two EPL/Rivals views draw two-team cards, so they need no box colour
  // both EPL/Rivals views lead with Tottenham, then the Top Six, and group
  // the rest as his own tab does (his call 2026-10-02)
  rivals: { comps: ["PL", "FAC", "LC", "UCL", "UEL", "UECL", "USC"], lead: BIG_SIX },
  windows: { comps: ["PL"], lead: BIG_SIX },
};
const ARSENAL = "359", CHELSEA = "363";
// these must read exactly as windows.py labels a match: the filter
// compares them, and an option that said "Super Sunday" while the
// matches said "Sky Super Sunday" found nothing (his catch 2026-10-02)
const WINDOWS = ["NBC Saturday", "Sky Sunday"];
// a European header wears its competition's colour, lightened to read on a
// card; the English cups stay plain
const COMP_COLOUR = { UCL: "#5b9bea", UEL: "#f68e1f", UECL: "#2fc27a", USC: "#d4af37",
                      FAC: "#d71921", LC: "#008f5e" };
// HIS CUP COLOURS (2026-10-06): BOTH domestic cups wear theirs only from the
// SEMIFINALS, where the ties move to Wembley -- the rounds before are league
// clubs against non-league ones and read plain grey. Europe wears its colour
// throughout, and the Super Cup has a gold of its own.
const WEMBLEY = ["FAC", "LC"];
function headColour(m) {
  if (WEMBLEY.indexOf(m.comp) > -1 && m.stage !== "Semifinals" && m.stage !== "Final") {
    return null;
  }
  return COMP_COLOUR[m.comp] || null;
}
const DAYS = { Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", Thu: "Thursday",
               Fri: "Friday", Sat: "Saturday", Sun: "Sunday" };

/* ---------- colour: the same wash maths as games-history ---------------- */
function shade(hex, lighten, strength) {
  lighten = lighten === undefined ? 0.42 : lighten;
  strength = strength === undefined ? 0.34 : strength;
  hex = (hex || "6a6a70").replace("#", "");
  if (hex.length !== 6) hex = "6a6a70";
  const p = [0, 2, 4].map(i => parseInt(hex.slice(i, i + 2), 16))
    .map(c => Math.round(c + (255 - c) * lighten));
  return "#" + p.map((c, i) => Math.round(CARD[i] + (c - CARD[i]) * strength)
    .toString(16).padStart(2, "0")).join("");
}
function teamColour(id) {
  const t = TEAMS[id] || {};
  return t.color || t.alt || "6a6a70";
}
function esc(s) {
  return String(s).replace(/[&<>"]/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function fmtDate(d) {
  return String(+d.slice(5, 7)) + "/" + String(+d.slice(8, 10)) + "/" + d.slice(0, 4);
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/* THE DATES HE SPELLS OUT (2026-10-06): one match of his own -- City away,
   19 February 2022 -- and EVERY WIN ON 21 SEPTEMBER, whatever the year. */
const SPELLED = ["2022-02-19"];
function spelled(m) {
  return SPELLED.indexOf(m.date) > -1 ||
    (m.date.slice(5) === "09-21" && m.result === "W");
}
function dateOf(m) {
  if (!spelled(m)) return fmtDate(m.date);
  return MONTHS[+m.date.slice(5, 7) - 1] + " " + (+m.date.slice(8, 10)) +
    ", " + m.date.slice(0, 4);
}
function fmtTime(t) {
  if (!t || t === "TBD") return "TBD";
  const p = t.split(":"), h = +p[0] % 12 || 12;
  return h + ":" + p[1] + (+p[0] < 12 ? "am" : "pm");
}
function seasonLabel(y) { return y + "-" + String((y + 1) % 100).padStart(2, "0"); }

// ESPN lists the network beside its streams ("NBC, Peacock"); the TV channel
// wins, the stream only when there is nothing else
const NET_RANK = ["NBC", "CBS", "USA Network", "CNBC", "MSNBC", "NBCSN",
                  "ESPN", "ESPN2", "FS1",
                  "FOX", "TNT", "truTV", "CBSSN", "Telemundo", "Universo", "UniMás"];
const STREAMERS = ["Peacock", "Paramount+", "ESPN+", "Max", "HBO Max", "fuboTV"];
function primaryNet(nets, season) {
  if (!nets || !nets.length) return "";
  // PEACOCK WINS OVER NBCSN FROM 2021-22 (his call 2026-10-06), the season
  // NBCSN closed -- a listing naming it after that is the feed's memory, not
  // where he watched
  if (season >= 2021 && nets.indexOf("Peacock") > -1 &&
      nets.indexOf("NBCSN") > -1) {
    return "Peacock";
  }
  const rank = n => NET_RANK.indexOf(n) > -1 ? NET_RANK.indexOf(n)
    : STREAMERS.indexOf(n) > -1 ? 900 + STREAMERS.indexOf(n) : 500;
  let best = nets[0];
  nets.forEach(n => { if (rank(n) < rank(best)) best = n; });
  // every source's spelling of the channel reads as he says it (2026-10-02)
  return best === "USA Net" || best === "USA" ? "USA Network" : best;
}

// HIS OWN TWO MARKS (2026-10-06), both read straight off his Sheet: a WHITE
// border makes a night SPECIAL, and any shade or border at all makes it
// MEMORABLE -- so every special night is a memorable one too.
function borderWord(m) {
  return String(((m.mx || {}).border || "")).trim();
}
function isSpecial(m) {
  // EVERY TROPHY IS SPECIAL (his call 2026-10-06), border or no border --
  // which today means the 2025 Europa League and nothing else
  if (isFinal(m) && m.result === "W") return true;
  const w = borderWord(m);
  return !!w && colourOf(w) === "#ffffff";
}
function isMemorable(m) {
  return !!(m.mx || {}).shade || !!borderWord(m);
}
/* A NETWORK'S SHORT NAME, kept for last (his call 2026-10-06). It is used
   only when his line still wraps with the full one -- "Paramount+ 3:00pm |
   Solanke 15', 54', Kulusevski 46', Son 88'" is the one card that needs it
   today, and it reads "P+ 3:00pm" there and nowhere else. */
// CBS All Access and FOX Soccer Plus are spelled out whatever happens, as he
// asked (2026-10-06), so they are not in here
const NET_SHORT = { "Paramount+": "P+", "NBC Sports Gold": "NBC Gold",
  "NBC Sports App": "NBC App", "PL Extra Time": "PL Extra",
  "CBS Sports Golazo": "CBS Golazo" };
function shortNets(s) {
  let out = String(s);
  Object.keys(NET_SHORT).forEach(k => { out = out.split(k).join(NET_SHORT[k]); });
  return out;
}
function upcoming(m) { return !!m.upcoming || !!m.status; }
function won(m) { return m.result === "W"; }
function lost(m) { return m.result === "L"; }
function isFinal(m) {
  return m.stage === "Final" || m.stage === "MLS Cup" || m.comp === "USC" || m.comp === "CAMP";
}
/* KNOCKOUTS (his call 2026-09-21): every European knockout round -- not the
   group stage or league phase, and not qualifying -- plus the semi-finals and
   finals of the FA Cup and the League Cup, and the Super Cup */
function isKnockout(m) {
  // USMNT and Atlanta: every round that is not a group, a league phase or
  // qualifying
  if (m.team !== "spurs") {
    return m.comp !== "WCQ" && !/^(Group|League)/.test(m.stage || "");
  }
  if (m.comp === "USC") return true;
  if (m.comp === "FAC" || m.comp === "LC") return /^(Semifinals|Final)/.test(m.stage || "");
  if (m.comp === "UCL" || m.comp === "UEL" || m.comp === "UECL") {
    return !m.qual && ["Group Stage", "League Phase", "Playoff Round", ""]
      .indexOf(m.stage || "") < 0;
  }
  return false;
}
// the neutral-ground cards -- finals and FA Cup semi-finals -- lift the round
// and the PLACE into the header, like a Michigan tournament card
function bigStage(m) {
  // ...for USMNT and Atlanta only a FINAL: every tournament match of the
  // national team is neutral, and a frame on all of them would say nothing
  return m.team === "spurs" ? m.where === "N" : m.where === "N" && isFinal(m);
}
// "Inglewood, California" -> "Inglewood"
function cityOf(m) { return (m.place || "").split(",")[0]; }

/* THE HEADER. The Premier League reads by MATCHWEEK; a cup match names its
   competition and round. A match off the weekend names its day. */
function stageText(m) {
  const c = COMP[m.comp];
  // HOW IT ENDED, at the end of the header (his calls 2026-10-06):
  //     FA Cup Quarterfinals (4-3 Pen)
  //     League Cup Fourth Round (ET)
  //     UEL Round of 16 (2nd Leg: 3-3 agg, 4-3 Pen)
  // A shootout always follows extra time, so ET is said only when there was
  // no shootout. The first leg settles nothing, so it says only which leg.
  const how = m.pens ? m.pens + " Pen" : (m.aet ? "ET" : "");
  let tail;
  if (m.leg === 1) tail = "1st Leg";
  else if (m.leg === 2) {
    const inner = [];
    if (m.agg) inner.push(m.agg + " agg");
    if (how) inner.push(how);
    tail = "2nd Leg" + (inner.length ? ": " + inner.join(", ") : "");
  } else tail = how;
  // IT IS HANDED BACK SEPARATELY (his call 2026-10-06), because it belongs at
  // the very END of the header -- after a final's city: "2025 UEFA Super Cup |
  // Udine (4-3 Pen)".
  const end = tail ? " (" + tail + ")" : "";
  if (m.comp === "USC") return { full: "UEFA Super Cup", short: "Super Cup", end: end };
  // a one-match event is its own name: MLS Cup, the Campeones Cup
  if (m.stage === "MLS Cup") return { full: "MLS Cup", short: "MLS Cup", end: end };
  if (m.comp === "CAMP" || m.comp === "CCUP") return { full: c.name, short: c.short,
                                                       end: end };
  let st = (m.stage || "").replace(/ Replay$/, " (Replay)");
  // Europe reads SHORT and without its season (his call 2026-10-06): "UEL
  // Group Stage", not "2015-16 Europa League: Group Stage". A FINAL is spelled
  // out and keeps its year, which cardHead puts in front: "2019 Champions
  // League Final".
  const euro = m.comp === "UCL" || m.comp === "UEL" || m.comp === "UECL";
  const name = euro && !isFinal(m) ? c.short : c.name;
  // a round shortens further only if the header would wrap: "League Cup Third
  // Round" -> "League Cup R3" (his overflow check 2026-10-02)
  const ROUND_SHORT = { "First Round": "R1", "Second Round": "R2",
    "Third Round": "R3", "Fourth Round": "R4", "Fifth Round": "R5",
    "Sixth Round": "R6", "Quarterfinals": "QF", "Semifinals": "SF",
    "Round of 32": "R32", "Round of 16": "R16", "League Phase": "Lg Phase" };
  let shortSt = st;
  Object.keys(ROUND_SHORT).forEach(k => {
    if (shortSt.indexOf(k) === 0) shortSt = ROUND_SHORT[k] + shortSt.slice(k.length);
  });
  return { full: name + " " + st, short: c.short + " " + shortSt, end: end };
}
/* HIS HEADER AND HIS LINES BELOW (2026-10-02).

   A PREMIER LEAGUE match spells its day out and keeps the date and network
   underneath:
       [MW1] Sunday 9:00 AM
       4/12/2026 | USA Network
   and when the card has something of its own to say, those move up beside a
   shortened day, leaving the bottom line to him:
       [MW1] SUN 9:00 AM | 4/12/2026 | USA Network
       Son 12', Kane 64'
   A CUP OR A EUROPEAN NIGHT names the round up top, so its day, date and
   network already have a line to themselves -- and anything else takes a
   FOURTH line (his call 2026-10-02):
       2018-19 CHAMPIONS LEAGUE: SEMIFINALS (2ND LEG)
       Ajax 2  3
       WED 5/8/2019 | TNT 3:00pm
       Llorente 87', Moura 90'+5 */
const DAY_FULL = { SUN: "Sunday", MON: "Monday", TUE: "Tuesday",
  WED: "Wednesday", THU: "Thursday", FRI: "Friday", SAT: "Saturday" };
function windowOf(m) {
  if (m.team !== "spurs" || m.comp !== "PL") return null;
  const home = m.home ? SPURS : m.opp, away = m.home ? m.opp : SPURS;
  return WINDOW_OF[m.date + "|" + home + "|" + away] || null;
}
function cardHead(m) {
  // USMNT and Atlanta carry no TV -- day, date and time only (his call)
  const net = m.team === "spurs" ? primaryNet(m.nets, m.season) : "";
  const tv = (net ? net + " " : "") + fmtTime(m.time);
  const dow = m.dow.toUpperCase();
  // the day spells itself out while it has the line to itself, and shortens
  // when the date and network move up beside it
  const dayTime = { long: (DAY_FULL[dow] || dow) + " " + fmtTime(m.time),
                    short: dow + " " + fmtTime(m.time) };
  const win = windowOf(m);
  if (m.comp === "PL") {
    const wk = m.mw != null ? "[MW" + m.mw + "]" : "Premier League";
    if (win) {
      // HIS WINDOW SHAPE (2026-10-02):
      //     [MW9] Sky Sunday 12:30pm
      //     10/26/2025 | USA Network
      // The window names the day, so the time is all the header needs; the
      // date and network read below, where every other league card puts them,
      // and his details take a line under that. Saturday's window already
      // says NBC, so it does not say it twice.
      return { head: wk + " " + (win === "NBC Saturday" ? esc(win)
                 : '<span class="hstage" data-short="' +
                   esc(win.replace("Sky ", "")) + '">' + esc(win) + "</span>") +
                 " " + fmtTime(m.time),
               down: [dateOf(m)].concat(
                 net && net !== "NBC" ? [net] : []) };
    }
    return { head: wk, dayTime: dayTime,
             tail: [dateOf(m)].concat(net ? [net] : []) };
  }
  const s = stageText(m);
  const lab = s.full !== s.short
    ? '<span class="hstage" data-short="' + esc(s.short) + '">' + esc(s.full) + "</span>"
    : esc(s.full);
  const big = bigStage(m);
  // how it ended reads LAST, after a final's city (his call 2026-10-06)
  const end = esc(s.end || "");
  // the year leads a final, as it does a Michigan tournament card -- in Europe
  // too, now that the label no longer carries the season: "2019 UCL Final".
  // The city of a final rides up there with it.
  const head = (!big ? lab
    : m.date.slice(0, 4) + " " + lab + (m.place ? " | " + esc(cityOf(m)) : "")) + end;
  // EVERY CUP -- the domestic ones, Europe, and his other teams' tournaments --
  // carries nothing but the round up top, so the day, date, network and time
  // have a line of their own below the score.
  const down = [dow + " " + dateOf(m), tv];
  if (!big && m.team !== "spurs" && m.where === "N" && m.place) down.push(cityOf(m));
  return { head: head, down: down };
}

/* ---------- colour words from his Sheet --------------------------------- */
const COLOUR_WORDS = { white: "#ffffff", black: "#111114", navy: "#132257",
  blue: "#1d4ed8", "light blue": "#6cabdd", "sky blue": "#6cabdd", red: "#c8102e",
  yellow: "#fdd20e", gold: "#c28c19", grey: "#8a8a92", gray: "#8a8a92",
  green: "#1d7a3a", orange: "#f68e1f", purple: "#5b2a86", pink: "#fd1272",
  lilac: "#b7a4d6", teal: "#0f8b8d", maroon: "#7a1f2b", silver: "#c0c0c0",
  claret: "#7a263a", cream: "#f3ead3" };
function colourOf(v) {
  const s = String(v || "").trim();
  if (/^#?[0-9a-f]{6}$/i.test(s)) return "#" + s.replace("#", "");
  return COLOUR_WORDS[s.toLowerCase()] || null;
}
function lum(hex) {
  const v = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map(x => x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4));
  return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
}
// white or near-black, whichever reads on the box
function inkFor(bg) { return lum(bg) > 0.4 ? "#111114" : "#ffffff"; }
function contrast(a, b) {
  const x = lum(a), y = lum(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}
/* INK THAT VANISHES INTO A LIGHT BOX (his call 2026-10-06). His European
   kits put a near-white number on the white shirt -- #d9d9d9 on #ffffff reads
   at 1.4:1 and simply is not there on a phone. On a LIGHT box only, the ink
   is darkened a step at a time until it can be seen, which leaves it silver
   rather than navy. A dark box is left alone: Palace's red on blue and City's
   white on sky are his kits and his business. */
function visibleInk(bg, fg) {
  if (!fg || fg.length !== 7 || !bg || bg.length !== 7) return fg;
  if (lum(bg) <= 0.6 || contrast(bg, fg) >= 2.4) return fg;
  let p = [1, 3, 5].map(i => parseInt(fg.slice(i, i + 2), 16));
  const hex = q => "#" + q.map(c => c.toString(16).padStart(2, "0")).join("");
  for (let n = 0; n < 40 && contrast(bg, hex(p)) < 2.4; n++) {
    p = p.map(c => Math.max(0, Math.round(c * 0.94) - 1));
  }
  return hex(p);
}
function paintBox(bg, fg) {
  return ' style="background:' + bg + ";color:" +
    visibleInk(bg, fg || inkFor(bg)) + '"';
}
function bright(hex, floor) {
  // an opponent's colour made bright enough to read as a border
  let h = hex.replace("#", "");
  if (h.length !== 6) return "#8a8a92";
  let p = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
  const top = Math.max.apply(null, p);
  if (top < floor) p = p.map(c => Math.min(255, Math.round(c + (floor - top))));
  return "#" + p.map(c => c.toString(16).padStart(2, "0")).join("");
}

function card(m) {
  const opp = TEAMS[m.opp] || { card: m.opp };
  const mx = m.mx || {};
  const up = upcoming(m);
  const L = lost(m), W = won(m);
  const h = cardHead(m);
  const where = m.where === "A" ? "at " : m.where === "N" ? "vs. " : "";
  // the league phase (2024-25 on): the opponent's position rides in front of
  // its name on a knockout card, as a conference-tournament seed does
  const seed = m.opp_lp ? '<span class="rkin">' + m.opp_lp + "</span> " : "";
  const fin = m.fin || "";
  let name = opp.card || opp.name;
  // his Case column: "UPPER" puts the opponent in capitals
  if (String(mx.case || "").trim().toUpperCase() === "UPPER") name = name.toUpperCase();
  // TWO SCORE BOXES (his call 2026-09-21): Spurs', then the opponent's, each
  // coloured from his Sheet. Until he gives colours, Spurs is navy and white
  // and the opponent wears its own colour. A loss is italic; extra time or a
  // shootout underlines both.
  // HIS TEAM'S BOX ALWAYS COMES FIRST (his call 2026-10-05), home or away or
  // on neutral ground -- the card is read down his column, not the fixture's.
  // It read home-then-away from 2026-09-21 until then.
  // ITALICS on both: any loss, and a Premier League draw with a club outside
  // the Top Six.
  // An UNDERLINE marks only the WINNER'S box when it took extra time or
  // penalties.
  // A NIGHT INSIDE A TIE HE WON IS NOT A DEFEAT (his call 2026-10-06): City
  // 2019 was beaten 4-3 and the score stands upright, like the card around it
  const italic = !up && m.through !== true && (L || (m.comp === "PL" &&
    m.result === "D" && TOP_SIX.indexOf(m.opp) < 0));
  const lineUs = !up && (m.aet || m.pens) && W;
  const lineThem = !up && (m.aet || m.pens) && L;
  const boxCls = line => "sc mbox" + (line ? " u" : "") + (italic ? " l" : "");
  // NO KIT, NO COLOUR (his call 2026-10-06): a match still to come wears plain
  // grey boxes, and so does a Tottenham match he has not given a kit. USMNT
  // and Atlanta keep their own colours for the matches they have played,
  // since he has coloured nothing there yet.
  const GREY = "#6a6a70";
  const plain = up || (m.team === "spurs" && !mx.team_bg);
  const usBg = plain ? GREY : (colourOf(mx.team_bg) || VIEWS[m.team].box);
  const themBg = plain ? GREY
    : (colourOf(mx.opp_bg) || "#" + teamColour(m.opp).replace("#", ""));
  const usBox = '<span class="' + boxCls(lineUs) + '"' +
    paintBox(usBg, plain ? null
      : (colourOf(mx.team_font) || (mx.team_bg ? null : "#ffffff"))) + ">" +
    (up ? "" : m.us) + "</span>";
  const themBox = '<span class="' + boxCls(lineThem) + '"' +
    paintBox(themBg, plain ? null : colourOf(mx.opp_font)) + ">" +
    (up ? "" : m.them) + "</span>";
  // NOTHING RIDES BESIDE THE BOXES any more: the header carries the aggregate
  // and the shootout both (his calls 2026-10-06).
  // AN AWARDED MATCH SHOWS NO SCORE AT ALL (his call 2026-10-06): Rennes at
  // home in 2021 was never played -- UEFA gave it to them 3-0 -- so a score
  // on the card would say it was.
  const boxes = m.awarded ? "" :
    '<span class="boxes">' + usBox + themBox + "</span>";
  // HIS LEG RULES (2026-10-06). A two-legged tie is one result, so the TIE
  // decides how each night reads, not the night's own score:
  //   WON the tie   leg 1 lost  -- grey, but NOT struck through
  //                 leg 1 level -- the colour bar, not bold
  //                 leg 2       -- always coloured; bold only if it was a win
  //   LOST the tie  leg 1 won   -- coloured, never bold
  //                 leg 1 lost  -- grey and struck, as any defeat
  //                 leg 2 won   -- no colour, but not struck either
  //                 leg 2 else  -- struck
  // A level first leg of a LOST tie settled nothing either way: grey, plain.
  let bar = W, bold = W, struck = L;
  if (m.leg && m.through === true) {
    struck = false;
    if (m.leg === 2) bar = true;
    else bar = W || m.result === "D";
  } else if (m.leg && m.through === false) {
    if (m.leg === 2) { bar = false; bold = false; struck = m.result !== "W"; }
    else bold = false;
  }
  const oppLine = '<div class="tl' + (bar ? " won" : "") + (bold ? " bold" : "") +
    (struck ? " struck" : "") + '"><span class="mstripe">' +
    // a club ESPN keeps no crest for (Dnipro, dissolved) leaves a blank, not
    // a broken-image icon
    '<img class="crest" loading="lazy" src="' + esc(opp.logo || "") +
      '" alt="" onerror="this.style.visibility=&quot;hidden&quot;">' +
    '<span class="nm mnm"><span class="mn">' + esc(where) + seed + esc(name) +
    "</span>" + (fin ? '<span class="mfin">' + esc(fin) + "</span>" : "") +
    "</span></span>" + boxes + "</div>";

  // THE LINES BELOW THE SCORE: plain grey details, pipes between. What the
  // card has of its own goes in parts; the day, date and network find their
  // place around it (see cardHead's note).
  const parts = [];
  // the scorer and minute, already worded by the harvest ("Kane 86'")
  if (m.late_win && !m.scorers) parts.push(m.late_win);
  if (m.late_eq && !m.scorers) parts.push(m.late_eq);
  // every Tottenham scorer, on a win or a draw with the Top Six -- always the
  // whole list, in order, even when one of them won or saved it late (his
  // calls 2026-10-02), so the late line is left off those cards
  if (m.scorers) parts.push(m.scorers.join(", "));
  if (m.status) parts.push("Postponed");
  // his Notes, and a Footer phrase that is its own text ("Pink Out")
  if (mx.note) parts.push(mx.note);
  const footer = String(mx.footer || "").trim();
  // "Scorers" and "Late Winner" are instructions to the harvest, not phrases
  // to print (2026-10-07)
  const ASKS = ["scorers", "late winner"];
  if (footer.indexOf(" ") > -1 && ASKS.indexOf(footer.toLowerCase()) < 0 &&
      parts.indexOf(footer) < 0) {
    parts.push(footer);
  }
  // HIS SHAPES (2026-10-02). A cup's day/date/network line is always there and
  // his own details take a fourth; a league match keeps the day up top and
  // sends the date and network below -- unless it needs that line for him.
  // NO CARD REACHES A FOURTH LINE (his call 2026-10-06). Whatever he has to
  // say -- scorers, a late winner, a note -- is the THIRD line and nothing
  // else, so the date goes up to the end of the header and the network goes
  // with it. When the header cannot hold the network, trimHeads drops it back
  // down in front of his line, where it loses nothing by being.
  const rows = [];
  let head = h.head;
  const dateUp = d => ' | <span class="hdate">' + esc(d) + "</span>";
  const tvUp = c => '<span class="htv"> | ' + esc(c.join(" | ")) + "</span>";
  if (h.down) {
    if (parts.length) {
      const chunk = h.down.slice(1);
      head += dateUp(h.down[0]) + (chunk.length ? tvUp(chunk) : "");
      rows.push({ items: chunk.concat(parts), tv: chunk.length });
    } else {
      rows.push({ items: h.down, tv: 0 });
    }
  } else if (parts.length) {
    const tail = h.tail || [];
    head += (h.dayTime ? " " + h.dayTime.short : "") +
      (tail.length ? dateUp(tail[0]) : "");
    const chunk = tail.slice(1);
    if (chunk.length) head += tvUp(chunk);
    rows.push({ items: chunk.concat(parts), tv: chunk.length });
  } else {
    head += h.dayTime ? " " + h.dayTime.long : "";
    rows.push({ items: h.tail || [], tv: 0 });
  }
  // his Footer column: a colour word paints the whole third row
  const footCol = colourOf(footer.split(/\s+/)[0]);

  // a FINAL wears a frame: grey, dashed on a loss, the competition's colour
  // when won -- as the Michigan bowls and title games do. HIS BORDER COLUMN
  // wins over it: a colour word, a hex, or "Opponent" for their colour.
  let cls = " mich" + (L ? " dimmed" : "") + (mx.shade ? " mwash" : "");
  let ring = "";
  let bc = null;
  const bword = String(mx.border || "").trim().toLowerCase();
  if (bword === "opponent") bc = bright("#" + teamColour(m.opp), 130);
  else if (bword) bc = colourOf(bword) || COMP_COLOUR[bword.toUpperCase()] || null;
  if (!bc && bigStage(m) && !up) {
    bc = W && isFinal(m) ? (COMP_COLOUR[m.comp] || "#e8e8e8") : "#8a8a92";
    if (L) cls += " predash";
  }
  if (bc) {
    cls += " celebrate";
    ring = ";--celeb:" + bc + ";--celebring:" + bc + "44";
  }
  const headCol = headColour(m);
  return '<div class="row' + cls + '" data-id="' + m.id + '" style="--winwash:' +
    shade(teamColour(m.opp)) + ring + '">' +
    '<div class="sport"' + (headCol ? ' style="color:' + headCol + '"' : "") + "><span>" +
    head + "</span></div>" +
    '<div class="teams">' + oppLine + "</div>" +
    '<div class="tags mdets">' + (mx.attended ? '<span class="mstar">*</span>' : "") +
    // his Footer colour word paints the line his own details sit on
    rows.map((r, i) => '<span class="mdl"' +
      (footCol && i === rows.length - 1 ? ' style="color:' + footCol + '"' : "") + ">" +
      // the network's own pieces carry .mtv: hidden here while the header
      // holds them, shown when trimHeads sends them down
      r.items.map((p, j) =>
        // the bar in FRONT of a hidden piece goes with it, so a line never
        // opens with a stray one (caught on his cards 2026-10-06)
        (j ? '<span class="msep' + (j <= r.tv ? " mtv" : "") + '">|</span>' : "") +
        '<span class="mdet' + (j < r.tv ? " mtv" : "") + '"' +
          (shortNets(p) !== p ? ' data-net="' + esc(p) + '" data-net-short="' +
            esc(shortNets(p)) + '"' : "") + ">" + esc(p) + "</span>")
        .join("") + "</span>").join("") +
    "</div></div>";
}

/* A TWO-TEAM CARD, for the matches that are nobody's of his: the TV windows
   and the rivals' results. Away line then home line, as games-history's cards
   read, the winner's line washed in its own colour. */
// THE TOP SIX IN CAPITALS on these cards (his call 2026-10-02) -- the five
// without Spurs, who read in plain case like everyone else (his call
// 2026-10-05). BIG_SIX still leads that tab's Team filter.
function bigName(id, t) {
  const n = (t || TEAMS[id] || {}).card || (t || {}).name || id;
  return TOP_SIX.indexOf(id) > -1 ? n.toUpperCase() : n;
}
function twoCard(m) {
  const wins = m.team === "windows";
  const homeId = wins ? m.home : (m.home ? m.rival : m.opp);
  const awayId = wins ? m.away : (m.home ? m.opp : m.rival);
  const hs = wins ? m.hs : (m.home ? m.us : m.them);
  const as = wins ? m.as : (m.home ? m.them : m.us);
  const up = hs === null || hs === undefined;
  // a shootout decides who won: the RESULT knows it, the score does not
  const rivalWon = !wins && m.result === "W", rivalLost = !wins && m.result === "L";
  const winId = up ? null
    : wins ? (hs > as ? homeId : as > hs ? awayId : null)
    : rivalWon ? m.rival : rivalLost ? m.opp : null;
  // HIS TWO CLUBS ARE NEVER IN BOLD (2026-10-02): a win of Arsenal's or
  // Chelsea's is washed like any other, but their name and score stay plain
  const line = (id, score, other) => {
    const t = TEAMS[id] || {};
    const win = !up && (winId ? id === winId : score > other);
    return '<div class="tl2' + (win ? " won" : "") +
      (win && (id === "359" || id === "363") ? " nobold" : "") + '">' +
      '<img class="crest" loading="lazy" src="' + esc(t.logo || "") +
      '" alt="" onerror="this.style.visibility=&quot;hidden&quot;">' +
      '<span class="nm">' + esc(bigName(id, t)) + "</span>" +
      '<span class="sc">' + (up ? "" : score) + "</span></div>";
  };
  // THE HEADER, IN PIECES so a phone breaks it between fields and never in
  // the middle of a channel's name (410px, 2026-10-02)
  const segs = [];
  if (wins) {
    // HIS WINDOW HEADER (2026-10-02). The window, the time and the date, and
    // NO NETWORK -- naming it as well was what pushed a phone to two lines:
    //     [MW1] NBC Saturday 12:30pm | 8/22/2026
    //     [MW1] Sky Sunday 11:30am | 8/23/2026
    // Saturday's window still says NBC, since it is part of the window's name.
    segs.push("[MW" + m.mw + "] " + '<span class="hstage" data-short="' +
      esc(m.window.replace("Sky ", "")) + '">' + esc(m.window) + "</span> " +
      fmtTime(m.time));
    segs.push('<span class="hdate">' + fmtDate(m.date) + "</span>");
  } else {
    const st = stageText(m);
    segs.push(m.comp === "PL"
      ? (m.mw != null ? "[MW" + m.mw + "] " + fmtTime(m.time)
                      : "Premier League " + fmtTime(m.time))
      : '<span class="hstage" data-short="' + esc(st.short) + '">' + esc(st.full) +
        "</span>" + esc(st.end || "") + " " + fmtTime(m.time));
    segs.push('<span class="hdate">' + fmtDate(m.date) + "</span>");
  }
  const winner = winId;
  // the shootout is in the round's own label now ("League Cup Final (4-3
  // Pen)"), so this card no longer says it twice (2026-10-06)
  // HIS TOTTENHAM MARKS (2026-10-02), the way Michigan's TV windows read: a
  // white border on a Tottenham win or a draw with the Top Six, a dashed grey
  // one on a loss or a draw with anyone else, and a win over the Top Six
  // fills the card in Spurs' own colour. Cards without Spurs wear nothing.
  let cls = "", ring = "";
  let wash = winner ? shade(teamColour(winner)) : "transparent";
  if (wins && !up && (m.home === SPURS || m.away === SPURS)) {
    const usHome = m.home === SPURS;
    const us = usHome ? hs : as, them = usHome ? as : hs;
    const big = TOP_SIX.indexOf(usHome ? m.away : m.home) > -1;
    if (us > them || (us === them && big)) {
      cls = " celebrate";
      ring = ";--celeb:#ffffff;--celebring:#ffffff22";
      // ESPN paints Tottenham WHITE, which washes out to a flat grey, so a
      // filled card wears the navy instead (his call 2026-10-02)
      if (us > them && big) { cls += " mwash"; wash = shade(VIEWS.spurs.box); }
    } else {
      cls = " celebrate predash";
      ring = ";--celeb:#8a8a92";
    }
  }
  // the bar belongs to the field it introduces, so a wrap never leaves one
  // dangling at the end of a line
  const head = segs.map((x, i) => "<span>" +
    (i ? '<span class="msep">|</span> ' : "") + x + "</span>").join("");
  const headCol = headColour(m);
  return '<div class="row two' + cls + '" data-id="' + m.id +
    '" style="--winwash:' + wash + ring + '">' +
    '<div class="sport"' + (headCol ? ' style="color:' + headCol + '"' : "") + ">" +
    head + "</div>" +
    '<div class="teams">' + line(awayId, as, hs) + line(homeId, hs, as) + "</div>" +
    "</div>";
}

/* ---------- filters ------------------------------------------------------ */
function isEpl() { return VIEW === "epl"; }
function defaults() {
  // Spurs open on the current season; USMNT and Atlanta on their latest year
  // with a match (the national team plays in only some years)
  const years = MATCHES.map(m => m.season);
  // RIVALS opens on every year, newest first -- their bad results are a list
  // to browse, not a season to follow (as in games-history)
  const open = VIEW === "epl" && SUB === "rivals" ? null
    : VIEW === "spurs" ? CURRENT
    : (years.length ? Math.max.apply(null, years) : null);
  return { season: open, comp: null, team: null, hl: null, ko: false,
           window: null, rival: null, net: null };
}
// a Premier League year is a season: 2026-27, not 2026 (his call
// 2026-10-02). USMNT and Atlanta play calendar years, so they keep theirs.
function yearLabel(y) {
  return VIEW === "spurs" || isEpl() ? seasonLabel(y) : String(y);
}
function passes(m, skip) {
  if (skip !== "season" && FILT.season != null && m.season !== FILT.season) return false;
  if (skip !== "comp" && FILT.comp && m.comp !== FILT.comp) return false;
  if (skip !== "team" && FILT.team) {
    const ids = m.team === "windows" ? [m.home, m.away] : [m.opp];
    if (ids.indexOf(FILT.team) < 0) return false;
  }
  if (skip !== "net" && FILT.net && primaryNet(m.nets, m.season) !== FILT.net) {
    return false;
  }
  if (skip !== "window" && FILT.window && m.window !== FILT.window) return false;
  if (skip !== "rival" && FILT.rival && m.rival !== FILT.rival) return false;
  if (FILT.ko && !isKnockout(m)) return false;
  if (skip !== "hl" && FILT.hl) {
    // the equalizers sit under Late Winners, loose label and all (his call
    // 2026-10-06)
    if (FILT.hl === "late_win" && !m.late_win && !m.late_eq) return false;
    if (FILT.hl === "special" && !isSpecial(m)) return false;
    if (FILT.hl === "memorable" && !isMemorable(m)) return false;
  }
  return true;
}
function visible() {
  const out = MATCHES.filter(m => passes(m));
  out.sort((a, b) => (a.date + a.time < b.date + b.time ? -1 : 1));
  if (SORT === "desc") out.reverse();
  return out;
}
function select(kind, allLabel, pairs, current) {
  return '<select class="fsel" data-kind="' + kind + '">' +
    '<option value="">' + allLabel + "</option>" +
    pairs.map(p => p[1] === null
      ? "<option disabled>" + esc(p[0]) + "</option>"
      : '<option value="' + esc(p[1]) + '"' +
        (String(current) === String(p[1]) ? " selected" : "") + ">" + esc(p[0]) +
        "</option>").join("") + "</select>";
}
function group(label, inner) {
  return '<div class="fgroup"><span class="flabel">' + label + "</span>" + inner + "</div>";
}
const BAR = ["─".repeat(12), null];
function filterBar() {
  // each list offers only what the OTHER filters leave, so a choice can never
  // return nothing
  const seasons = Array.from(new Set(MATCHES.filter(m => passes(m, "season"))
    .map(m => m.season))).sort((a, b) => b - a);
  let h = group("Year", select("season", "All Years",
    seasons.map(y => [yearLabel(y), y]), FILT.season));
  // TV Windows picks a window instead of a competition; Rivals picks the club
  if (VIEW === "epl" && SUB === "tv") {
    h += group("Window", select("window", "Both Windows",
      WINDOWS.map(w => [w, w]), FILT.window));
  }
  if (VIEW === "epl" && SUB === "rivals") {
    h += group("Rival", select("rival", "Both Rivals",
      [[(TEAMS[ARSENAL] || {}).card || "Arsenal", ARSENAL],
       [(TEAMS[CHELSEA] || {}).card || "Chelsea", CHELSEA]], FILT.rival));
  }
  const comps = new Set(MATCHES.filter(m => passes(m, "comp")).map(m => m.comp));
  if (!(VIEW === "epl" && SUB === "tv")) h += group("Competition", select("comp", "All Competitions",
    VIEWS[population()].comps.filter(c => comps.has(c) || c === FILT.comp).map(c => [COMP[c].name, c]),
    FILT.comp));
  // TEAM: Spurs list the Top Six, then the other English clubs, then everyone
  // abroad -- a club counts as English if it ever met Spurs in an English
  // competition. USMNT leads with Mexico and Canada; Atlanta is alphabetical.
  const lead = VIEWS[population()].lead;
  const seen = new Set();
  MATCHES.filter(m => passes(m, "team")).forEach(m => {
    if (m.team === "windows") { seen.add(m.home); seen.add(m.away); }
    else seen.add(m.opp);
  });
  if (FILT.team) seen.add(FILT.team);
  // a TV Windows match names no opponent -- it names two clubs, and both are
  // English, so they are read off the card itself (2026-10-02)
  const english = VIEW === "spurs" || isEpl()
    ? new Set([].concat.apply([], MATCHES
        .filter(m => ["PL", "FAC", "LC"].indexOf(m.comp) > -1)
        .map(m => m.team === "windows" ? [m.home, m.away] : [m.opp])))
    : new Set(MATCHES.map(m => m.opp));
  const nameOf = id => (TEAMS[id] || {}).card || id;
  const alpha = ids => ids.sort((a, b) => nameOf(a).localeCompare(nameOf(b)))
    .map(id => [nameOf(id), id]);
  const ids = Array.from(seen);
  // ...then the clubs of Spain, France, Italy and Germany together, and
  // everyone else last (his call 2026-10-02)
  const euro4 = id => ((TEAMS[id] || {}).grp === "euro4");
  // his order at the head of that group (2026-10-02)
  const EURO_LEAD = ["Atlético Madrid", "Barcelona", "Real Madrid", "Bayern Munich",
                     "Borussia Dortmund", "Milan", "Inter Milan", "Juventus",
                     "Paris Saint-Germain"];
  // the English clubs split in two (his call 2026-10-02): those Spurs have met
  // in the PREMIER LEAGUE at least once, then the cup-only ones. Read off the
  // whole archive, not the current view, so the lists do not shuffle.
  const inPL = new Set(ALL.filter(m => m.team === "spurs" && m.comp === "PL").map(m => m.opp));
  const groups = [lead.filter(id => seen.has(id)).map(id => [nameOf(id), id]),
                  alpha(ids.filter(id => lead.indexOf(id) < 0 && english.has(id) && inPL.has(id))),
                  alpha(ids.filter(id => lead.indexOf(id) < 0 && english.has(id) && !inPL.has(id))),
                  (() => {
                    const mine = ids.filter(id => !english.has(id) && euro4(id));
                    const lead4 = EURO_LEAD.map(n => mine.find(id => nameOf(id) === n))
                      .filter(Boolean);
                    return lead4.map(id => [nameOf(id), id])
                      .concat(alpha(mine.filter(id => lead4.indexOf(id) < 0)));
                  })(),
                  alpha(ids.filter(id => !english.has(id) && !euro4(id)))]
    .filter(g => g.length);
  h += group("Team", select("team", "All Teams",
    [].concat.apply([], groups.map((g, i) => (i ? [BAR] : []).concat(g))), FILT.team));
  // HIS OWN MARKS LEAD (2026-10-06); the late goals the harvest found follow
  const HL = [["Special", "special"], ["Memorable", "memorable"],
              ["Late Winners", "late_win"]];
  if (isEpl()) {
    return h + group("", '<button class="f" data-act="sort">' +
      (SORT === "asc" ? "Oldest First" : "Newest First") + "</button>");
  }
  // HIS NETWORKS (2026-10-06): the six he watches lead, then a bar, then
  // whatever else a match in view was on, alphabetically. Only his own cards
  // show a network, so only his own tab offers the filter.
  if (VIEW === "spurs") {
    const NET_LEAD = ["NBC", "USA Network", "Peacock", "NBCSN", "Paramount+",
                      "ESPN+"];
    const seenNet = new Set();
    MATCHES.filter(x => passes(x, "net")).forEach(x => {
      const n = primaryNet(x.nets, x.season);
      if (n) seenNet.add(n);
    });
    if (FILT.net) seenNet.add(FILT.net);
    const lead = NET_LEAD.filter(n => seenNet.has(n));
    // alphabetical as he would read it, so beIN sits with the Bs
    const rest = Array.from(seenNet).filter(n => NET_LEAD.indexOf(n) < 0)
      .sort((a, b) => a.localeCompare(b, "en", { sensitivity: "base" }));
    const opts = lead.map(n => [n, n])
      .concat(lead.length && rest.length ? [BAR] : [])
      .concat(rest.map(n => [n, n]));
    h += group("Network", select("net", "All Networks", opts, FILT.net));
  }
  // the late goals are read for Spurs only
  if (VIEW === "spurs") h += group("Highlights", select("hl", "All Matches", HL, FILT.hl));
  h += group("", '<button class="f" data-act="ko" aria-pressed="' + !!FILT.ko +
    '">Knockouts</button><button class="f" data-act="sort">' +
    (SORT === "asc" ? "Oldest First" : "Newest First") + "</button>");
  return h;
}

/* A HEADER TOO LONG FOR THE PHONE gives things up in order (2026-10-06):
   first the network, which only moves down a line and loses nothing, then
   the competition's full name -- "Champions League Round of 16" -> "UCL
   Round of 16". Both are restored first, so a wider window gets them back. */
function trimHeads() {
  document.querySelectorAll(".row").forEach(row => {
    const head = row.querySelector(".sport");
    if (!head) return;
    const s = head.querySelector("[data-short]");
    row.classList.remove("tvdown");
    if (s && s.dataset.full) s.textContent = s.dataset.full;
    const lh = parseFloat(getComputedStyle(head).lineHeight) || 19;
    const tall = () => head.getBoundingClientRect().height > lh * 1.5;
    if (!tall()) return;
    if (head.querySelector(".htv")) row.classList.add("tvdown");
    if (tall() && s) {
      s.dataset.full = s.dataset.full || s.textContent;
      s.textContent = s.dataset.short;
    }
  });
  // LAST OF ALL, the network gives up its full name -- but only on a line
  // that still wraps with it (his call 2026-10-06)
  document.querySelectorAll(".row .mdl").forEach(row => {
    row.querySelectorAll("[data-net]").forEach(el => {
      el.textContent = el.dataset.net;
    });
    const lh = parseFloat(getComputedStyle(row).lineHeight) || 18;
    if (row.getBoundingClientRect().height > lh * 1.5) {
      row.querySelectorAll("[data-net-short]").forEach(el => {
        el.textContent = el.dataset.netShort;
      });
    }
  });
}

function viewBar() {
  const bar = document.getElementById("viewbar");
  if (VIEW !== "epl") { bar.innerHTML = ""; bar.style.display = "none"; return; }
  bar.style.display = "";
  bar.innerHTML = [["tv", "TV Windows"], ["rivals", "Rivals"]].map(v =>
    '<button data-sub="' + v[0] + '" aria-selected="' + (SUB === v[0]) + '">' +
    v[1] + "</button>").join("");
}
function draw() {
  viewBar();
  document.getElementById("filters").innerHTML = filterBar();
  const list = visible();
  const n = list.filter(m => !upcoming(m)).length;
  const w = list.filter(won).length, d = list.filter(m => m.result === "D").length,
    l = list.filter(lost).length;
  document.getElementById("count").textContent = VIEW === "epl"
    ? list.length + (list.length === 1 ? " match" : " matches")
    : (n ? w + "-" + d + "-" + l : list.length + " upcoming");
  const render = VIEW === "epl" ? twoCard : card;
  document.getElementById("list").innerHTML = list.length
    ? list.map(render).join("") : '<div class="empty">No matches.</div>';
  trimHeads();
}

async function init() {
  const r = await fetch("games.json?v=" + BUILD).then(x => x.json());
  ALL = r.matches; TEAMS = r.teams; CURRENT = r.current;
  ALL.forEach(m => {
    if (m.team === "windows") WINDOW_OF[m.date + "|" + m.home + "|" + m.away] = m.window;
  });
  MATCHES = ALL.filter(m => m.team === population());
  FILT = defaults();
  draw();
  document.querySelector("nav").addEventListener("click", e => {
    const b = e.target.closest("button[data-top]");
    if (!b || b.dataset.top === VIEW) return;
    VIEW = b.dataset.top;
    document.querySelectorAll("nav button").forEach(x =>
      x.setAttribute("aria-selected", String(x === b)));
    MATCHES = ALL.filter(m => m.team === population());
    FILT = defaults();
    SORT = VIEW === "epl" && SUB === "rivals" ? "desc" : "asc";
    draw();
    window.scrollTo({ top: 0 });
  });
  document.getElementById("viewbar").addEventListener("click", e => {
    const b = e.target.closest("button[data-sub]");
    if (!b || b.dataset.sub === SUB) return;
    SUB = b.dataset.sub;
    MATCHES = ALL.filter(m => m.team === population());
    FILT = defaults();
    SORT = SUB === "rivals" ? "desc" : "asc";
    draw();
    window.scrollTo({ top: 0 });
  });
  document.getElementById("filters").addEventListener("change", e => {
    const k = e.target.dataset && e.target.dataset.kind;
    if (!k) return;
    const v = e.target.value;
    FILT[k] = v === "" ? null : (k === "season" ? +v : v);
    draw();
  });
  document.getElementById("filters").addEventListener("click", e => {
    const b = e.target.closest("button.f[data-act]");
    if (!b) return;
    if (b.dataset.act === "sort") SORT = SORT === "asc" ? "desc" : "asc";
    else if (b.dataset.act === "ko") {
      FILT.ko = !FILT.ko;
      // every knockout ever, not just this season's
      if (FILT.ko) FILT.season = null;
    }
    draw();
  });
  document.getElementById("clearbtn").addEventListener("click", () => {
    FILT = { season: null, comp: null, team: null, hl: null, ko: false,
             window: null, rival: null };
    draw();
    window.scrollTo({ top: 0 });
  });
  let t = null;
  window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(trimHeads, 120); });
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => { });
}
init();
