"""The paid bundle must never be a static URL.

2026-10-19: with outputDirectory "." four sibling products served their bundle at
/api/%5Ffull/<f>, /api/_full%2F<f> and /api/_full/<f>/ (curl, 200).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import deploy  # noqa: E402


def test_only_public_is_static_and_the_bundle_is_outside_it():
    assert json.loads((ROOT / "site/vercel.json").read_text())["outputDirectory"] == "public"
    src = (ROOT / "scripts/deploy.py").read_text()
    assert '"outputDirectory": "."' not in src and '"outputDirectory":"."' not in src
    rels = [str(rel) for rel, _ in deploy.collect()]
    full = [r for r in rels if "_full" in r]
    assert full and all(r.startswith("api/_full/") for r in full), full
    assert "public/index.html" in rels and "offer.json" in rels  # api/_lib.js requires it
    assert not any(r.startswith("public/api") for r in rels)
