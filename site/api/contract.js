// GET /api/contract?for=<token> -> the slice a /contract/for/<token>/ page was made for.
// The recipient list lives in api/_full/contract.json (built by scripts/build_contract.py from the
// gitignored outreach/contract/ledger.csv). It is never a static file, so the list of who we wrote
// to cannot be read off the site; one token answers for one page only.
const fs = require("fs");
const path = require("path");

const DIR = process.env.FULL_DIR || path.join(__dirname, "_full");
let PAGES = null;

module.exports = (req, res) => {
  try { PAGES ??= JSON.parse(fs.readFileSync(path.join(DIR, "contract.json"), "utf8")); }
  catch (e) { console.error("[contract] load:", e.message); return res.status(500).json({ error: "data not loaded" }); }
  const token = String(req.query.for || "");
  const page = /^[a-z0-9]{6,16}$/.test(token) ? PAGES[token] : null;
  if (!page) return res.status(404).json({ error: "no such page" });
  res.setHeader("Cache-Control", "private, max-age=300");
  res.status(200).json({ token, ...page });
};
