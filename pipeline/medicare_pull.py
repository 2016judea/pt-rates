"""Pull Medicare Part B 'by Provider and Service' rows for Minnesota physical therapists.

Source: CMS, Medicare Physician & Other Practitioners - by Provider and Service, 2024
(data.cms.gov dataset 92396110-2aed-4d63-a6a2-5d6207d46a29). Keyless.
Writes pipeline/cache/medicare_mn_pt_2024.json (every row, all codes).
"""
import json, pathlib, urllib.parse, urllib.request

DS = "92396110-2aed-4d63-a6a2-5d6207d46a29"
OUT = pathlib.Path(__file__).parent / "cache" / "medicare_mn_pt_2024.json"


def page(offset, size=5000):
    q = urllib.parse.urlencode({
        "size": size, "offset": offset,
        "filter[Rndrng_Prvdr_State_Abrvtn]": "MN",
        "filter[Rndrng_Prvdr_Type]": "Physical Therapist in Private Practice",
    })
    with urllib.request.urlopen(f"https://data.cms.gov/data-api/v1/dataset/{DS}/data?{q}", timeout=120) as r:
        return json.load(r)


rows, off = [], 0
while True:
    p = page(off)
    rows += p
    print(off, len(p))
    if len(p) < 5000:
        break
    off += 5000
OUT.write_text(json.dumps(rows))
print(len(rows), "rows ->", OUT)
