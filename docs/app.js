/* Soccer History -- the whole app. site.py copies this in and fills
   20260921-130614. Modelled on games-history's Michigan view (michCard): one card
   per match, the opponent on a colour stripe, the score in a box. */
const BUILD = "20260921-130614";
const CARD = [0x1e, 0x1e, 0x23];
const SPURS = "367";
// the Top Six bar Spurs: they lead the Team filter
const TOP_SIX = ["359", "363", "364", "360", "382"];
let MATCHES = [], TEAMS = {}, CURRENT = null;
let FILT = {};
let SORT = "asc";

const COMP = {
  PL: { name: "Premier League", short: "PL" },
  FAC: { name: "FA Cup", short: "FA Cup" },
  LC: { name: "League Cup", short: "League Cup" },
  UCL: { name: "Champions League", short: "UCL" },
  UEL: { name: "Europa League", short: "UEL" },
  UECL: { name: "Conference League", short: "UECL" },
  USC: { name: "Super Cup", short: "Super Cup" },
};
const COMP_ORDER = ["PL", "FAC", "LC", "UCL", "UEL", "UECL", "USC"];
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
function isFinal(m) { return m.stage === "Final" || m.comp === "USC"; }
// the neutral-ground cards -- finals and FA Cup semi-finals -- lift the round
// and the PLACE into the header, like a Michigan tournament card
function bigStage(m) { return m.where === "N"; }

/* THE HEADER. The Premier League reads by MATCHWEEK; a cup match names its
   competition and round. A match off the weekend names its day. */
function stageText(m) {
  const c = COMP[m.comp];
  if (m.comp === "USC") return { full: "UEFA Super Cup", short: "Super Cup" };
  let st = m.stage || "";
  if (m.comp === "UCL" || m.comp === "UEL" || m.comp === "UECL") {
    const full = c.name + " " + st, short = c.short + " " + st;
    return { full: full, short: short };
  }
  return { full: c.name + " " + st, short: c.short + " " + st };
}
function cardHead(m) {
  const net = primaryNet(m.nets);
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
    return { head: m.date.slice(0, 4) + " " + lab + (m.place ? " | " + esc(m.place) : ""),
             date: null, tv: tv };
  }
  // a cup round is long enough on its own: the day and date lead the third row
  return { head: lab + " | " + tv, date: null, down: m.dow.toUpperCase() + " " + fmtDate(m.date) };
}

function card(m) {
  const opp = TEAMS[m.opp] || { card: m.opp };
  const up = upcoming(m);
  const L = lost(m), W = won(m);
  const h = cardHead(m);
  const where = m.where === "A" ? "at " : m.where === "N" ? "vs. " : "";
  // the league phase (2024-25 on): the opponent's position rides in front of
  // its name on a knockout card, as a conference-tournament seed does
  const seed = m.opp_lp ? '<span class="rkin">' + m.opp_lp + "</span> " : "";
  const fin = m.fin || "";
  // the score box: Spurs' score first. A loss is italic; extra time or a
  // shootout underlines it
  const u = !up && (m.aet || m.pens);
  const box = '<span class="sc mbox' + (u ? " u" : "") + (L ? " l" : "") +
    '" style="background:#132257;color:#ffffff">' +
    (up ? "" : m.us + "-" + m.them) + "</span>";
  const oppLine = '<div class="tl' + (W ? " won" : "") + '"><span class="mstripe">' +
    '<img class="crest" loading="lazy" src="' + esc(opp.logo || "") + '" alt="">' +
    '<span class="nm mnm"><span class="mn">' + esc(where) + seed + esc(opp.card || opp.name) +
    "</span>" + (fin ? '<span class="mfin">' + esc(fin) + "</span>" : "") +
    "</span></span>" + box + "</div>";

  // THE THIRD ROW: plain grey details, pipes between
  const parts = [];
  if (bigStage(m)) {
    parts.push(m.dow.toUpperCase() + " " + fmtDate(m.date));
    parts.push(h.tv.replace(/<[^>]+>/g, ""));
  } else if (h.down) {
    parts.push(h.down);
  }
  if (m.awarded) parts.push("Awarded");
  if (m.pens) parts.push((W ? "Won " : "Lost ") + m.pens + " on Pens");
  else if (m.aet) parts.push("AET");
  if (m.agg) parts.push("Agg. " + m.agg);
  if (m.late_win) parts.push("Late Winner " + m.late_win);
  if (m.late_eq) parts.push("Late Equalizer " + m.late_eq);
  if (m.status) parts.push("Postponed");
  // the date drops to the third row when there is nothing else to say
  const dateDown = !bigStage(m) && !parts.length;
  if (dateDown) parts.push((h.date || "").replace(/<[^>]+>/g, ""));
  const head = h.head + (!dateDown && h.date ? ' | <span class="hdate">' + h.date + "</span>" : "");

  // a FINAL wears a frame: grey, dashed on a loss, the competition's colour
  // when won -- as the Michigan bowls and title games do
  let cls = " mich" + (L ? " dimmed" : "");
  let ring = "";
  if (bigStage(m) && !up) {
    const c = W && isFinal(m) ? (COMP_COLOUR[m.comp] || "#e8e8e8") : "#8a8a92";
    cls += " celebrate" + (L ? " predash" : "");
    ring = ";--celeb:" + c + ";--celebring:" + c + "44";
  }
  const headCol = COMP_COLOUR[m.comp];
  return '<div class="row' + cls + '" data-id="' + m.id + '" style="--winwash:' +
    shade(teamColour(m.opp)) + ring + '">' +
    '<div class="sport"' + (headCol ? ' style="color:' + headCol + '"' : "") + "><span>" +
    head + "</span></div>" +
    '<div class="teams">' + oppLine + "</div>" +
    '<div class="tags mdets"><span class="mdl">' +
    parts.map(p => '<span class="mdet">' + esc(p) + "</span>").join('<span class="msep">|</span>') +
    "</span></div></div>";
}

/* ---------- filters ------------------------------------------------------ */
function defaults() {
  return { season: CURRENT, comp: null, team: null, hl: null, finals: false };
}
function passes(m, skip) {
  if (skip !== "season" && FILT.season != null && m.season !== FILT.season) return false;
  if (skip !== "comp" && FILT.comp && m.comp !== FILT.comp) return false;
  if (skip !== "team" && FILT.team && m.opp !== FILT.team) return false;
  if (FILT.finals && !isFinal(m)) return false;
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
    seasons.map(y => [seasonLabel(y), y]), FILT.season));
  const comps = new Set(MATCHES.filter(m => passes(m, "comp")).map(m => m.comp));
  h += group("Competition", select("comp", "All Competitions",
    COMP_ORDER.filter(c => comps.has(c) || c === FILT.comp).map(c => [COMP[c].name, c]),
    FILT.comp));
  // TEAM: the Top Six, then the other English clubs, then everyone abroad --
  // a club counts as English if it ever met Spurs in an English competition
  const seen = new Set(MATCHES.filter(m => passes(m, "team")).map(m => m.opp));
  if (FILT.team) seen.add(FILT.team);
  const english = new Set(MATCHES.filter(m => ["PL", "FAC", "LC"].indexOf(m.comp) > -1)
    .map(m => m.opp));
  const nameOf = id => (TEAMS[id] || {}).card || id;
  const alpha = ids => ids.sort((a, b) => nameOf(a).localeCompare(nameOf(b)))
    .map(id => [nameOf(id), id]);
  const ids = Array.from(seen);
  const groups = [TOP_SIX.filter(id => seen.has(id)).map(id => [nameOf(id), id]),
                  alpha(ids.filter(id => TOP_SIX.indexOf(id) < 0 && english.has(id))),
                  alpha(ids.filter(id => !english.has(id)))].filter(g => g.length);
  h += group("Team", select("team", "All Teams",
    [].concat.apply([], groups.map((g, i) => (i ? [BAR] : []).concat(g))), FILT.team));
  const HL = [["Late Winners", "late_win"], ["Late Equalizers", "late_eq"]];
  h += group("Highlights", select("hl", "All Matches", HL, FILT.hl));
  h += group("", '<button class="f" data-act="finals" aria-pressed="' + !!FILT.finals +
    '">Finals</button><button class="f" data-act="sort">' +
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
  MATCHES = r.matches; TEAMS = r.teams; CURRENT = r.current;
  FILT = defaults();
  draw();
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
    else if (b.dataset.act === "finals") {
      FILT.finals = !FILT.finals;
      // every final ever, not this season's none
      if (FILT.finals) FILT.season = null;
    }
    draw();
  });
  document.getElementById("clearbtn").addEventListener("click", () => {
    FILT = { season: null, comp: null, team: null, hl: null, finals: false };
    draw();
    window.scrollTo({ top: 0 });
  });
  let t = null;
  window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(trimHeads, 120); });
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => { });
}
init();
