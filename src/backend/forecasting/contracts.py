"""Prediction targets, one per domain, and the source rules every model must pass before it is fitted.

The four quantities are related but different, and must never stand in for each other:
  ai_capability        what frontier models can do (benchmarks, task horizons)
  business_adoption    share of firms using AI (BTOS)
  occupation_adoption  share of workers in an occupation using AI (RPS); task exposure is NOT adoption
  skill_demand         share of job postings asking for a skill; NOT adoption, NOT employment
Only skill_demand has a working model on this branch; the others are declared so their rules are enforced
from the start, and their status says so.
"""
from __future__ import annotations

from dataclasses import dataclass

from .registry import DOMAINS, SOURCES


@dataclass(frozen=True)
class Target:
    id: str
    domain: str
    definition: str
    unit: str
    grain: str
    label_source: str
    horizons_months: tuple[int, ...]
    status: str  # implemented | planned


TARGETS: dict[str, Target] = {t.id: t for t in [
    Target("ai_mention_share", "skill_demand",
           "monthly mean of the daily share of new Indeed postings whose description mentions AI terms",
           "percent of postings", "country x month", "indeed_ai_tracker", (1, 3, 6), "implemented"),
    Target("btos_ai_use_rate", "business_adoption",
           "share of US businesses that used AI in the last two weeks, within one question wording",
           "percent of firms", "US sector x fortnight", "census_btos", (3, 6), "planned"),
    Target("worker_genai_use_rate", "occupation_adoption",
           "share of employed US adults in a SOC major group using generative AI for their job",
           "percent of workers", "SOC major group x quarter", "rps_genai", (3, 6), "planned"),
    Target("frontier_capability_index", "ai_capability",
           "benchmark-based capability measure of the best available model (definition pending)",
           "benchmark score", "month", "", (6, 12), "planned"),
]}

# Substitutions the spec forbids, as (source, domain) -> reason. Checked on top of the registry, so a later
# registry edit cannot quietly allow them.
FORBIDDEN_LABEL = {
    ("census_btos", "occupation_adoption"): "business-level use is not worker or occupation adoption",
    ("anthropic_ei", "occupation_adoption"): "task exposure is not adoption",
    ("indeed_ai_tracker", "business_adoption"): "AI skill demand in postings is not AI adoption",
    ("indeed_ai_tracker", "occupation_adoption"): "AI skill demand in postings is not AI adoption",
    ("indeed_postings", "skill_demand"): "posting volume is not employment or skill demand",
    ("gdelt_doc", "ai_capability"): "news volume is not capability",
}
FORBIDDEN_FEATURE = {
    ("census_btos", "occupation_adoption"): "a firm survey cannot be spread over occupations without a crosswalk "
                                            "model that is itself validated",
    ("census_btos", "skill_demand"): "business AI use does not measure postings asking for a skill",
}


class SourceNotAllowed(ValueError):
    pass


def check_sources(target_id: str, label: str, features: set[str]) -> None:
    """Raise unless `label` measures the target's domain and every feature source is registered for it."""
    t = TARGETS[target_id]
    assert t.domain in DOMAINS
    why = FORBIDDEN_LABEL.get((label, t.domain))
    if why or label != t.label_source or t.domain not in SOURCES[label].label_for:
        raise SourceNotAllowed(f"{label} is not a label for {t.domain}: {why or 'not registered'}")
    for f in features - {label}:  # the target's own history is always allowed
        why = FORBIDDEN_FEATURE.get((f, t.domain))
        if why or t.domain not in SOURCES[f].feature_for:
            raise SourceNotAllowed(f"{f} may not feed {t.domain}: {why or 'not registered for this domain'}")
