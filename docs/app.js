/* Soccer History -- the whole app. site.py copies this in and fills
   20260921-145606. Modelled on games-history's Michigan view (michCard): one card
   per match, the opponent on a colour stripe, the score in a box. */
const BUILD = "20260921-145606";
const CARD = [0x1e, 0x1e, 0x23];
const SPURS = "367";
// the Top Six bar Spurs: they lead the Team filter
const TOP_SIX = ["359", "363", "364", "360", "382"];
let ALL = [], MATCHES = [], TEAMS = {}, CURRENT = null;
let FILT = {};
let SORT = "asc";
// the tab along the top: one view per team of his (2026-09-21)
let VIEW = "spurs";

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
};
// a European header wears its competition's colour, lightened to read on a
// card; the English cups stay plain
const COMP_COLOUR = { UCL: "#5b9bea", UEL: "#f68e1f", UECL: "#2fc27a", USC: "#5b9bea" };
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
function fmtTime(t) {
  if (!t || t === "TBD") return "TBD";
  const p = t.split(":"), h = +p[0] % 12 || 12;
  return h + ":" + p[1] + (+p[0] < 12 ? "am" : "pm");
}
function seasonLabel(y) { return y + "-" + String((y + 1) % 100).padStart(2, "0"); }

// ESPN lists the network beside its streams ("NBC, Peacock"); the TV channel
// wins, the stream only when there is nothing else
const NET_RANK = ["NBC", "CBS", "USA Net", "CNBC", "NBCSN", "ESPN", "ESPN2", "FS1",
                  "FOX", "TNT", "truTV", "CBSSN", "Telemundo", "Universo", "UniMás"];
const STREAMERS = ["Peacock", "Paramount+", "ESPN+", "Max", "HBO Max", "fuboTV"];
function primaryNet(nets) {
  if (!nets || !nets.length) return "";
  const rank = n => NET_RANK.indexOf(n) > -1 ? NET_RANK.indexOf(n)
    : STREAMERS.indexOf(n) > -1 ? 900 + STREAMERS.indexOf(n) : 500;
  let best = nets[0];
  nets.forEach(n => { if (rank(n) < rank(best)) best = n; });
  return best === "USA Net" ? "USA" : best;
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
  if (m.comp === "USC") return { full: "UEFA Super Cup", short: "Super Cup" };
  // a one-match event is its own name: MLS Cup, the Campeones Cup
  if (m.stage === "MLS Cup") return { full: "MLS Cup", short: "MLS Cup" };
  if (m.comp === "CAMP" || m.comp === "CCUP") return { full: c.name, short: c.short };
  let st = m.stage || "";
  if (m.comp === "UCL" || m.comp === "UEL" || m.comp === "UECL") {
    const full = c.name + " " + st, short = c.short + " " + st;
    return { full: full, short: short };
  }
  return { full: c.name + " " + st, short: c.short + " " + st };
}
function cardHead(m) {
  // USMNT and Atlanta carry no TV -- day, date and time only (his call)
  const net = m.team === "spurs" ? primaryNet(m.nets) : "";
  const tv = (net ? esc(net) + " " : "") + fmtTime(m.time);
  if (m.comp === "PL") {
    const wk = m.mw != null ? "Matchweek " + m.mw : "Premier League";
    const day = (m.dow !== "Sat" && m.dow !== "Sun") ? " (" + esc(m.dow) + ")" : "";
    return { head: wk + day + " | " + tv, date: fmtDate(m.date) };
  }
  const s = stageText(m);
  const lab = s.full !== s.short
    ? '<span class="hstage" data-short="' + esc(s.short) + '">' + esc(s.full) + "</span>"
    : esc(s.full);
  if (bigStage(m)) {
    // the year leads a final, as it does a Michigan tournament card
    return { head: m.date.slice(0, 4) + " " + lab + (m.place ? " | " + esc(cityOf(m)) : ""),
             date: null, tv: tv };
  }
  // a cup round is long enough on its own: the day and date lead the third row
  if (m.team !== "spurs") {
    // USMNT and Atlanta: the round alone up top; day, date, time and -- on
    // neutral ground -- the city below
    return { head: lab, date: null, down: m.dow.toUpperCase() + " " + fmtDate(m.date) +
             "|" + fmtTime(m.time) + (m.where === "N" && m.place ? "|" + cityOf(m) : "") };
  }
  return { head: lab + " | " + tv, date: null, down: m.dow.toUpperCase() + " " + fmtDate(m.date) };
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
function paintBox(bg, fg) {
  return ' style="background:' + bg + ";color:" + (fg || inkFor(bg)) + '"';
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
  // THE BOXES READ HOME THEN AWAY (his call 2026-09-21) -- on neutral ground
  // too, in the order ESPN lists the sides.
  // ITALICS on both: any loss, and a Premier League draw with a club outside
  // the Top Six.
  // An UNDERLINE marks only the WINNER'S box when it took extra time or
  // penalties.
  const italic = !up && (L || (m.comp === "PL" && m.result === "D" &&
    TOP_SIX.indexOf(m.opp) < 0));
  const lineUs = !up && (m.aet || m.pens) && W;
  const lineThem = !up && (m.aet || m.pens) && L;
  const boxCls = line => "sc mbox" + (line ? " u" : "") + (italic ? " l" : "");
  const usBg = colourOf(mx.team_bg) || VIEWS[m.team].box;
  const themBg = colourOf(mx.opp_bg) || "#" + teamColour(m.opp).replace("#", "");
  const usBox = '<span class="' + boxCls(lineUs) + '"' +
    paintBox(usBg, colourOf(mx.team_font) || (mx.team_bg ? null : "#ffffff")) + ">" +
    (up ? "" : m.us) + "</span>";
  const themBox = '<span class="' + boxCls(lineThem) + '"' +
    paintBox(themBg, colourOf(mx.opp_font)) + ">" + (up ? "" : m.them) + "</span>";
  // a record from before the field existed falls back to the card's own side
  const usHome = m.home != null ? m.home : m.where !== "A";
  const boxes = '<span class="boxes">' + (usHome ? usBox + themBox : themBox + usBox) +
    "</span>";
  const oppLine = '<div class="tl' + (W ? " won" : "") + '"><span class="mstripe">' +
    // a club ESPN keeps no crest for (Dnipro, dissolved) leaves a blank, not
    // a broken-image icon
    '<img class="crest" loading="lazy" src="' + esc(opp.logo || "") +
      '" alt="" onerror="this.style.visibility=&quot;hidden&quot;">' +
    '<span class="nm mnm"><span class="mn">' + esc(where) + seed + esc(name) +
    "</span>" + (fin ? '<span class="mfin">' + esc(fin) + "</span>" : "") +
    "</span></span>" + boxes + "</div>";

  // THE THIRD ROW: plain grey details, pipes between
  const parts = [];
  if (bigStage(m)) {
    parts.push(m.dow.toUpperCase() + " " + fmtDate(m.date));
    parts.push(h.tv.replace(/<[^>]+>/g, ""));
  } else if (h.down) {
    h.down.split("|").forEach(p => parts.push(p));
  }
  if (m.awarded) parts.push("Awarded");
  if (m.pens) parts.push((W ? "Won " : "Lost ") + m.pens + " on Pens");
  else if (m.aet) parts.push("AET");
  if (m.agg) parts.push("Agg. " + m.agg);
  if (m.late_win) parts.push("Late Winner " + m.late_win);
  if (m.late_eq) parts.push("Late Equalizer " + m.late_eq);
  if (m.status) parts.push("Postponed");
  // his Notes, and a Footer phrase that is its own text ("Pink Out")
  if (mx.note) parts.push(mx.note);
  const footer = String(mx.footer || "").trim();
  if (footer.indexOf(" ") > -1 && parts.indexOf(footer) < 0) parts.push(footer);
  // the date drops to the third row when there is nothing else to say
  const dateDown = !bigStage(m) && !parts.length;
  if (dateDown) parts.push((h.date || "").replace(/<[^>]+>/g, ""));
  const head = h.head + (!dateDown && h.date ? ' | <span class="hdate">' + h.date + "</span>" : "");
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
  const headCol = COMP_COLOUR[m.comp];
  return '<div class="row' + cls + '" data-id="' + m.id + '" style="--winwash:' +
    shade(teamColour(m.opp)) + ring + '">' +
    '<div class="sport"' + (headCol ? ' style="color:' + headCol + '"' : "") + "><span>" +
    head + "</span></div>" +
    '<div class="teams">' + oppLine + "</div>" +
    '<div class="tags mdets">' + (mx.attended ? '<span class="mstar">*</span>' : "") +
    '<span class="mdl"' + (footCol ? ' style="color:' + footCol + '"' : "") + ">" +
    parts.map(p => '<span class="mdet">' + esc(p) + "</span>").join('<span class="msep">|</span>') +
    "</span></div></div>";
}

/* ---------- filters ------------------------------------------------------ */
function defaults() {
  // Spurs open on the current season; USMNT and Atlanta on their latest year
  // with a match (the national team plays in only some years)
  const years = MATCHES.map(m => m.season);
  const open = VIEW === "spurs" ? CURRENT : (years.length ? Math.max.apply(null, years) : null);
  return { season: open, comp: null, team: null, hl: null, ko: false };
}
function yearLabel(y) { return VIEW === "spurs" ? seasonLabel(y) : String(y); }
function passes(m, skip) {
  if (skip !== "season" && FILT.season != null && m.season !== FILT.season) return false;
  if (skip !== "comp" && FILT.comp && m.comp !== FILT.comp) return false;
  if (skip !== "team" && FILT.team && m.opp !== FILT.team) return false;
  if (FILT.ko && !isKnockout(m)) return false;
  if (skip !== "hl" && FILT.hl) {
    if (FILT.hl === "late_win" && !m.late_win) return false;
    if (FILT.hl === "late_eq" && !m.late_eq) return false;
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
  const comps = new Set(MATCHES.filter(m => passes(m, "comp")).map(m => m.comp));
  h += group("Competition", select("comp", "All Competitions",
    VIEWS[VIEW].comps.filter(c => comps.has(c) || c === FILT.comp).map(c => [COMP[c].name, c]),
    FILT.comp));
  // TEAM: Spurs list the Top Six, then the other English clubs, then everyone
  // abroad -- a club counts as English if it ever met Spurs in an English
  // competition. USMNT leads with Mexico and Canada; Atlanta is alphabetical.
  const lead = VIEWS[VIEW].lead;
  const seen = new Set(MATCHES.filter(m => passes(m, "team")).map(m => m.opp));
  if (FILT.team) seen.add(FILT.team);
  const english = VIEW === "spurs"
    ? new Set(MATCHES.filter(m => ["PL", "FAC", "LC"].indexOf(m.comp) > -1).map(m => m.opp))
    : new Set(MATCHES.map(m => m.opp));
  const nameOf = id => (TEAMS[id] || {}).card || id;
  const alpha = ids => ids.sort((a, b) => nameOf(a).localeCompare(nameOf(b)))
    .map(id => [nameOf(id), id]);
  const ids = Array.from(seen);
  const groups = [lead.filter(id => seen.has(id)).map(id => [nameOf(id), id]),
                  alpha(ids.filter(id => lead.indexOf(id) < 0 && english.has(id))),
                  alpha(ids.filter(id => !english.has(id)))].filter(g => g.length);
  h += group("Team", select("team", "All Teams",
    [].concat.apply([], groups.map((g, i) => (i ? [BAR] : []).concat(g))), FILT.team));
  const HL = [["Late Winners", "late_win"], ["Late Equalizers", "late_eq"]];
  // the late goals are read for Spurs only
  if (VIEW === "spurs") h += group("Highlights", select("hl", "All Matches", HL, FILT.hl));
  h += group("", '<button class="f" data-act="ko" aria-pressed="' + !!FILT.ko +
    '">Knockouts</button><button class="f" data-act="sort">' +
    (SORT === "asc" ? "Oldest First" : "Newest First") + "</button>");
  return h;
}

/* A header too long for the phone gives up its competition's full name --
   "Champions League Round of 16" -> "UCL Round of 16" -- only when it wraps */
function trimHeads() {
  document.querySelectorAll(".row .sport").forEach(head => {
    const s = head.querySelector("[data-short]");
    if (!s) return;
    if (s.dataset.full) s.textContent = s.dataset.full;
    const lh = parseFloat(getComputedStyle(head).lineHeight) || 19;
    if (head.getBoundingClientRect().height > lh * 1.5) {
      s.dataset.full = s.dataset.full || s.textContent;
      s.textContent = s.dataset.short;
    }
  });
}

function draw() {
  document.getElementById("filters").innerHTML = filterBar();
  const list = visible();
  const n = list.filter(m => !upcoming(m)).length;
  const w = list.filter(won).length, d = list.filter(m => m.result === "D").length,
    l = list.filter(lost).length;
  document.getElementById("count").textContent = n
    ? w + "-" + d + "-" + l : list.length + " upcoming";
  document.getElementById("list").innerHTML = list.length
    ? list.map(card).join("") : '<div class="empty">No matches.</div>';
  trimHeads();
}

async function init() {
  const r = await fetch("games.json?v=" + BUILD).then(x => x.json());
  ALL = r.matches; TEAMS = r.teams; CURRENT = r.current;
  MATCHES = ALL.filter(m => m.team === VIEW);
  FILT = defaults();
  draw();
  document.querySelector("nav").addEventListener("click", e => {
    const b = e.target.closest("button[data-top]");
    if (!b || b.dataset.top === VIEW) return;
    VIEW = b.dataset.top;
    document.querySelectorAll("nav button").forEach(x =>
      x.setAttribute("aria-selected", String(x === b)));
    MATCHES = ALL.filter(m => m.team === VIEW);
    FILT = defaults();
    SORT = "asc";
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
    FILT = { season: null, comp: null, team: null, hl: null, ko: false };
    draw();
    window.scrollTo({ top: 0 });
  });
  let t = null;
  window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(trimHeads, 120); });
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => { });
}
init();
