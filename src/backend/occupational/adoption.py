"""Occupational AI adoption: what is measured, what is a proxy, and what is only exposure. Kept apart throughout.

A. Worker AI usage (measured)
   - Stack Overflow Developer Survey 2023-2025, per occupation x country (sources/so_survey.py).
   - Context: Real-Time Population Survey, % of employed US adults in SOC major group 15 (Computer and
     mathematical, which contains all four occupations) using generative AI for work, quarterly. Read from the
     raw-source table data/processed/forecasting/rps_observations.csv (observations, not the industry models'
     predictions). Broader than any one occupation, so shown as context only.
   No forecast is published: three annual survey readings, with the question and occupation categories changing
   in 2025, cannot identify a trend, and the RPS group is not an occupation.
B. Employer deployment by occupational function
   - No source measures it directly (BTOS and similar surveys are firm-level: a firm using AI somewhere says nothing
     about which occupations use it).
   - Proxy shown instead, labelled as such: share of the occupation's ads that expect the hire to use AI tools in
     their own work (skill ai_assisted_dev: Copilot, Cursor, Claude Code, "AI-assisted development", ...). It is
     an employer requirement signal, not a deployment rate, and is never converted into one.
C. Task exposure (neither adoption nor deployment)
   - Anthropic Economic Index: where the occupation sits among all occupations by observed Claude work usage
     (percentile). Labelled exposure; never shown as a percentage of workers.
"""
from __future__ import annotations

import pandas as pd

from . import store, taxonomy as T
from .sources import so_survey

RPS = store.REPO / "data" / "processed" / "forecasting" / "rps_observations.csv"
EXPOSURE = store.REPO / "data" / "processed" / "ai_exposure.csv"
EMPLOYER_SKILL = "ai_assisted_dev"


def worker_usage() -> pd.DataFrame:
    return so_survey.build()


def rps_context() -> pd.DataFrame:
    if not RPS.exists():
        return pd.DataFrame()
    r = pd.read_csv(RPS, dtype={"unit": str})
    r = r[r["unit"].isin(["15", "00"])]
    return pd.DataFrame({
        "quarter": r["quarter"], "group": r["unit"].map({"15": "SOC 15 Computer and mathematical", "00": "All workers"}),
        "share_using": r["value_pct"] / 100, "available_at": r["available_at"],
        "population": "Employed US adults (Real-Time Population Survey)", "country": "US",
        "occupation_scope": r["unit"].map({"15": "Contains all four occupations; not occupation-specific",
                                            "00": "All occupations"}),
        "measure_type": "observed", "source": "rps", "source_url": "https://www.realtimepopulationsurvey.com/"})


def task_exposure() -> pd.DataFrame:
    if not EXPOSURE.exists():
        return pd.DataFrame()
    e = pd.read_csv(EXPOSURE, dtype=str)
    rows = []
    for o in T.occupations():
        for code in o.onet_codes:
            m = e[e["onet_code"] == code]
            if len(m):
                r = m.iloc[0]
                rows.append({"occupation": o.id, "onet_code": code, "onet_title": r["title"],
                             "usage_percentile": float(r["exposure"]),
                             "automation_share_of_usage": float(r["automation_share"]) if r["automation_share"] else None,
                             "as_of": r["as_of_date"], "measure_type": "exposure_index",
                             "definition": "Percentile rank among all occupations of the share of Claude work "
                                           "conversations about this occupation's tasks (Anthropic Economic Index). "
                                           "Not the share of workers using AI.",
                             "source": "anthropic_economic_index"})
    return pd.DataFrame(rows)


def employer_signal(totals: pd.DataFrame, counts: pd.DataFrame) -> pd.DataFrame:
    """Monthly HN counts of ads expecting AI-tool use, per country x occupation (3-month pooled share added)."""
    t = totals[~totals["is_partial"].astype(bool)]
    c = counts[counts["skill_id"] == EMPLOYER_SKILL][["month", "country", "occupation", "n_ads_skill"]]
    d = t.merge(c, on=["month", "country", "occupation"], how="left").fillna({"n_ads_skill": 0})
    d = d.sort_values(["country", "occupation", "month"])
    g = d.groupby(["country", "occupation"])
    d["share_3m"] = g["n_ads_skill"].transform(lambda s: s.rolling(3).sum()) / g["n_ads"].transform(lambda s: s.rolling(3).sum())
    d["measure_type"] = "proxy"
    d["definition"] = ("Share of the occupation's eligible HN job ads that expect the hire to use AI tools in their "
                       "own work. An employer requirement signal, not a deployment rate.")
    return d.drop(columns=["is_partial"])


SOURCES = [
    {"id": "so_dev_survey", "target": "worker_ai_usage", "measure_type": "observed",
     "name": "Stack Overflow Developer Survey (2023, 2024, 2025)",
     "population": "Employed survey respondents; self-selected, developer-heavy; not a probability sample",
     "definition": "Uses AI tools in the development process (2025: daily, weekly or monthly/infrequently)",
     "period": "Annual, fielded May-June", "geography": "Global, with country breakdowns",
     "licence": "ODbL", "url": "https://survey.stackoverflow.co/"},
    {"id": "rps", "target": "worker_ai_usage", "measure_type": "observed",
     "name": "Real-Time Population Survey (St. Louis Fed / FRED)",
     "population": "Employed US adults", "definition": "Used generative AI for work",
     "period": "Quarterly", "geography": "US",
     "limitation": "Smallest occupation unit is SOC major group 15 (all computer and mathematical occupations)",
     "url": "https://www.realtimepopulationsurvey.com/"},
    {"id": "hn_whoishiring", "target": "employer_deployment_proxy", "measure_type": "proxy",
     "name": "HN 'Who is hiring?' ads expecting AI-tool use",
     "population": "Tech companies posting on Hacker News", "definition": "Ad expects the hire to use AI tools",
     "period": "Monthly", "geography": "Countries parsed from ad locations",
     "limitation": "What employers ask for, not whether they deployed AI in the occupation's work"},
    {"id": "anthropic_economic_index", "target": "task_exposure", "measure_type": "exposure_index",
     "name": "Anthropic Economic Index (release 2026-06-26)", "population": "Claude conversations",
     "definition": "Percentile of observed Claude work usage for the occupation's tasks", "period": "Apr-May 2026",
     "geography": "Global usage", "limitation": "Exposure, not adoption: never shown as a share of workers"},
]

NOT_FOUND = {
    "employer_deployment_by_occupation": (
        "No source found that measures whether employers deploy AI in a given occupation's work. Firm surveys "
        "(Census BTOS, OECD ICT surveys) report whether a firm uses AI at all, which cannot be split by occupation "
        "without assumptions. The page shows an ads-based proxy instead and labels it as such."),
    "worker_usage_forecast": (
        "Not published. Three annual Stack Overflow readings (wording and occupation categories changed in 2025) "
        "cannot identify a trend; the quarterly RPS series covers a whole occupation group, not one occupation."),
}
