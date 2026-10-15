// GET /api/preview?clinic=<id>   -> that clinic's own rates per payer, plus four neighbours'
// GET /api/preview?for=<token>   -> the same, for the clinic a /for/<token>/ page was made for
// The free slice: anyone may see their own row against the market (site/data/market.json holds
// the market's aggregates). Every other clinic's rates stay in the paid table (/api/data).
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const DIR = process.env.FULL_DIR || path.join(__dirname, "_full");
const NEIGHBOURS = 4;
const CORE = ["97110", "97140", "97530", "97161"]; // site/index.html aboveYou()
let FULL = null, FOR = null, CLINICS = null;

function load() {
  FULL ??= JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(DIR, "full.json.gz"))));
  FOR ??= JSON.parse(fs.readFileSync(path.join(DIR, "for.json"), "utf8"));
  CLINICS ??= JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "clinics.json"), "utf8"));
}

// Nearest by the only geography every clinic has: same city first, then the closest zip,
// then the most payers in common (so the neighbour has rates to compare).
function neighbours(me) {
  const z = Number(me.zip) || 0;
  return CLINICS.filter((c) => c.id !== me.id && c.payers.some((p) => me.payers.includes(p)))
    .map((c) => [c.city === me.city ? 0 : 1, Math.abs((Number(c.zip) || 0) - z), -c.payers.filter((p) => me.payers.includes(p)).length, c])
    .sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2])
    .slice(0, NEIGHBOURS).map((x) => x[3].id);
}

module.exports = (req, res) => {
  try { load(); } catch (e) { console.error("[preview] load:", e.message); return res.status(500).json({ error: "data not loaded" }); }
  const token = String(req.query.for || "");
  const id = token ? FOR[token] : String(req.query.clinic || "");
  const me = CLINICS.find((c) => c.id === id);
  if (!me) return res.status(404).json({ error: token ? "no such page" : "no such clinic" });
  const nb = neighbours(me);
  const payers = {};
  for (const [slug, d] of Object.entries(FULL.payers)) {
    const clinics = {};
    for (const c of [me.id, ...nb]) if (d.clinics[c]) clinics[c] = d.clinics[c];
    const mine = d.clinics[me.id] || {};
    const k = CORE.find((c) => mine[c] != null && d.market[c]) || Object.keys(mine).find((c) => d.market[c]);
    const above = k ? { code: k, n: Object.values(d.clinics).filter((v) => v[k] != null && v[k] > mine[k]).length, of: d.market[k].n, max: d.market[k].max } : null;
    payers[slug] = { clinics, above };
  }
  res.setHeader("Cache-Control", "public, max-age=300");
  res.status(200).json({ clinic: me.id, token: token || null, neighbours: nb, payers });
};
