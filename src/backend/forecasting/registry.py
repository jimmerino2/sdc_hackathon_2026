"""Source registry: what each source measures, and which forecasting domains it may serve.

A source may be a *label* for a domain (it measures that domain's target directly), a *feature* for it (it
plausibly leads the target), or neither. contracts.check_sources() refuses any other use, so a source cannot
drift into a model just because it is available. That rule is what stops BTOS (a business survey) from being
used as an occupation-adoption label or as a skill-demand feature, as happened in the old ml/ai_adoption_* code.

Health (last vintage, last observed period, freshness) is computed from the vintage tables, not typed in.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

DOMAINS = ("ai_capability", "business_adoption", "occupation_adoption", "skill_demand")


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str
    measures: str  # the quantity, in its own unit
    unit: str
    coverage: str
    cadence_days: int  # expected gap between releases; freshness is judged against it
    retrieval: str
    auth: str
    licence: str
    label_for: tuple[str, ...] = ()
    feature_for: tuple[str, ...] = ()
    implemented: bool = False  # has a working adapter on this branch
    limitations: tuple[str, ...] = field(default_factory=tuple)


SOURCES: dict[str, Source] = {s.id: s for s in [
    Source("indeed_ai_tracker", "Indeed Hiring Lab AI Tracker", "https://github.com/hiring-lab/ai-tracker",
           "share of new job postings whose description mentions AI / GenAI terms", "percent of postings",
           "9-10 countries, national, daily from 2019-01", 31, "git history (one commit = one vintage)", "none",
           "CC-BY-4.0", label_for=("skill_demand",), implemented=True,
           limitations=("history is revised between vintages (mean 0.39 pp, max 1.6 pp)",
                        "first vintage 2024-04: earlier forecast origins use a reconstructed vintage",
                        "keyword-based: measures mentions, not hires or required skills",
                        "column names and date formats changed 4 times (schema_version kept)")),
    Source("indeed_postings", "Indeed Hiring Lab Job Postings Index",
           "https://github.com/hiring-lab/job_postings_tracker",
           "volume of job postings relative to 1 Feb 2020", "index, 1 Feb 2020 = 100", "11 countries, daily from 2020-02",
           7, "git history (month's last commit kept)", "none", "CC-BY-4.0",
           feature_for=("skill_demand",), implemented=True,
           limitations=("postings, not hires or employment",
                        "before mid-2021 published as % change, oldest schema not labelled seasonally adjusted")),
    Source("census_btos", "Census Business Trends and Outlook Survey", "https://www.census.gov/hfp/btos/data_downloads",
           "share of US businesses using AI in the last two weeks / expecting to in six months", "percent of firms",
           "US, national and NAICS sector, biweekly from 2023-09", 14, "xlsx download", "none", "public domain",
           label_for=("business_adoption",), implemented=True,
           limitations=("measures firms, not workers or occupations",
                        "question wording changed Nov 2025: a structural break, series not joined across it",
                        "US only; no transfer to other countries without separate evidence",
                        "estimates assumed unrevised once published; checked from now on via dated downloads",
                        "fortnights 202521-202523 not asked (published as '.')")),
    Source("rps_genai", "Real-Time Population Survey, GenAI adoption (Bick, Blandin & Deming)",
           "https://sites.google.com/view/covid-rps/data",
           "share of employed US adults using generative AI for their job", "percent of workers",
           "US, SOC major group, quarterly", 92, "FRED csv", "none", "see source",
           label_for=("occupation_adoption",), implemented=True,
           limitations=("self-reported use; small samples per group",
                        "9 quarters (2024-Q3 on): too short for a strong backtest",
                        "no historical vintages without FRED_API_KEY: availability dates assumed")),
    Source("adzuna", "Adzuna job-ads API", "https://developer.adzuna.com",
           "live job ads matching a query (counts and ad text)", "ads", "US/GB/..., live ads only", 7,
           "REST API, snapshots stored by date", "ADZUNA_APP_ID / ADZUNA_APP_KEY", "API terms",
           feature_for=("skill_demand",),
           limitations=("free tier only (25 calls/day): snapshots stay too thin to train or backtest on; "
                        "context only, by decision of 2026-10-24",)),
    Source("gdelt_doc", "GDELT DOC 2.0", "https://api.gdeltproject.org/api/v2/doc/doc",
           "news coverage matching a query; timeline volume is normalised by all monitored coverage",
           "share of monitored articles", "global, from 2017", 1, "REST API", "none", "GDELT terms",
           feature_for=("ai_capability", "business_adoption", "skill_demand"),
           limitations=("news volume is not capability, adoption or demand; context or candidate feature only",)),
    Source("anthropic_ei", "Anthropic Economic Index", "https://huggingface.co/datasets/Anthropic/EconomicIndex",
           "share of Claude conversations by O*NET task", "share of conversations", "global, release snapshots",
           180, "dataset download", "none", "CC-BY", feature_for=("occupation_adoption",),
           limitations=("task exposure on one platform, not adoption",)),
]}


def health(source_id: str, last_available_at: pd.Timestamp | None, last_period: str | None,
           now: pd.Timestamp) -> dict:
    """Freshness of a source: stale when nothing new has been published for 2 x its cadence."""
    if last_available_at is None or pd.isna(last_available_at):
        return {"source_id": source_id, "status": "no_data"}
    age = (now - last_available_at).days
    return {"source_id": source_id, "last_available_at": last_available_at.isoformat(),
            "last_complete_period": last_period, "age_days": age,
            "status": "stale" if age > 2 * SOURCES[source_id].cadence_days else "fresh"}


def vintage_health(source_id: str, vintages: pd.DataFrame, now: pd.Timestamp) -> dict:
    """health() for a vintage table (vintages.py layout)."""
    if vintages.empty:
        return health(source_id, None, None, now)
    last = vintages["available_at"].max()
    complete = vintages[(vintages["available_at"] == last) & ~vintages["is_partial"].astype(bool)]
    return health(source_id, last, complete["month"].max() if not complete.empty else None, now)
