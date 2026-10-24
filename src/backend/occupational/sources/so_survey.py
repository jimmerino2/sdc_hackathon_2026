"""Stack Overflow Developer Survey microdata (2023-2025): share of employed respondents in an occupation who say they
use AI tools in their development work. A direct, occupation-level measurement of worker AI usage.

Population: people who answer the Stack Overflow survey (self-selected, developer-heavy). Not a probability sample
of workers, so shares describe respondents, not every worker in the occupation. Each row keeps its sample size and
a 95% Wilson interval.
Question (AISelect): 2023-2024 "Do you currently use AI tools in your development process?" Yes / No, but I plan to /
No, and I don't plan to. 2025 split Yes into daily / weekly / monthly or infrequently; all three count as using.
Occupation = DevType mapped in occupations.json (categories changed between years; notes say where).
Licence: Open Database License (ODbL). Files: github.com/StackExchange/Survey packages/archive/<year>/results.csv.
A finished year never changes, so each file is downloaded once.
"""
from __future__ import annotations

import math
import urllib.request

import pandas as pd

from .. import store, taxonomy as T

SOURCE = "so_dev_survey"
URL = "https://github.com/StackExchange/Survey/raw/refs/heads/main/packages/archive/{year}/results.csv"
YEARS = {
    2023: {"fielded": "2023-05", "published": "2023-06-13",
           "wording": "Do you currently use AI tools in your development process? (Yes)"},
    2024: {"fielded": "2024-05/2024-06", "published": "2024-07-24",
           "wording": "Do you currently use AI tools in your development process? (Yes)"},
    2025: {"fielded": "2025-05/2025-06", "published": "2025-07-29",
           "wording": "Do you currently use AI tools in your development process? (Yes: daily, weekly, or monthly/infrequently)"},
}
COUNTRY = {"United States of America": "US", "United Kingdom of Great Britain and Northern Ireland": "GB",
           "Canada": "CA", "Germany": "DE", "Netherlands": "NL", "France": "FR", "Australia": "AU", "India": "IN"}
MIN_N = 30  # below this a country x occupation share is not published


def _raw(year: int):
    return store.path("raw", "so_survey", f"{year}.csv")


def fetch(pull: bool = True) -> dict:
    have, failed = [], []
    for y in YEARS:
        p = _raw(y)
        if not p.exists() and pull:
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".part")
                urllib.request.urlretrieve(URL.format(year=y), tmp)
                tmp.replace(p)
            except Exception as e:
                failed.append(f"{y}: {str(e)[:80]}")
        if p.exists():
            have.append(y)
    return {"source": SOURCE, "status": "ok" if len(have) == len(YEARS) else ("partial" if have else "missing"),
            "years": have, "failed": failed}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def build() -> pd.DataFrame:
    """year x occupation x country (and ALL respondents) usage shares."""
    rows = []
    occs = T.occupations()
    for y, meta in YEARS.items():
        p = _raw(y)
        if not p.exists():
            continue
        d = pd.read_csv(p, usecols=["Employment", "DevType", "Country", "AISelect"], low_memory=False)
        d = d[d["Employment"].fillna("").str.contains("Employed") & d["AISelect"].notna()]
        d["using"] = d["AISelect"].str.startswith("Yes")
        d["planning"] = d["AISelect"].str.startswith("No, but I plan")
        d["geo"] = d["Country"].map(COUNTRY)
        for o in occs:
            types = o.so_devtypes.get(str(y))
            if not types:
                continue
            sub = d[d["DevType"].isin(types)]
            for geo, g in [("ALL", sub), *[(c, sub[sub["geo"] == c]) for c in sorted(set(COUNTRY.values()))]]:
                n, k = len(g), int(g["using"].sum())
                lo, hi = wilson(k, n)
                rows.append({
                    "year": y, "occupation": o.id, "country": geo, "n_respondents": n, "n_using": k,
                    "share_using": k / n if n else math.nan, "ci_low": lo, "ci_high": hi,
                    "share_planning": float(g["planning"].mean()) if n else math.nan,
                    "published_ok": n >= MIN_N, "devtypes": "; ".join(types), "wording": meta["wording"],
                    "fielded": meta["fielded"], "published": meta["published"],
                    "population": "Employed Stack Overflow survey respondents (self-selected; not a probability sample)",
                    "comparability_note": o.so_note, "source": SOURCE, "source_url": URL.format(year=y),
                    "measure_type": "observed"})
    return pd.DataFrame(rows)
