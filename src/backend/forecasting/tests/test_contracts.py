"""Source rules: BTOS and other sources may only inform the targets they measure."""
import dataclasses

import pytest

from forecasting import contracts as C, features as F, registry as R


def test_skill_demand_model_passes_its_own_contract():
    C.check_sources("ai_mention_share", "indeed_ai_tracker", set(F.GROUP_SOURCE.values()))


def test_btos_is_not_a_skill_demand_feature():
    with pytest.raises(C.SourceNotAllowed, match="census_btos"):
        C.check_sources("ai_mention_share", "indeed_ai_tracker", {"census_btos"})


def test_btos_is_not_an_occupation_adoption_label():
    with pytest.raises(C.SourceNotAllowed):
        C.check_sources("worker_genai_use_rate", "census_btos", set())


def test_forbidden_rules_survive_a_registry_edit(monkeypatch):
    loose = dataclasses.replace(R.SOURCES["census_btos"], label_for=("business_adoption", "occupation_adoption"),
                                feature_for=("skill_demand",))
    monkeypatch.setitem(R.SOURCES, "census_btos", loose)
    with pytest.raises(C.SourceNotAllowed):
        C.check_sources("worker_genai_use_rate", "census_btos", set())
    with pytest.raises(C.SourceNotAllowed):
        C.check_sources("ai_mention_share", "indeed_ai_tracker", {"census_btos"})


@pytest.mark.parametrize("label,target", [
    ("anthropic_ei", "worker_genai_use_rate"),        # task exposure is not adoption
    ("indeed_ai_tracker", "btos_ai_use_rate"),         # AI skill demand is not adoption
    ("indeed_ai_tracker", "worker_genai_use_rate"),
    ("indeed_postings", "ai_mention_share"),           # posting growth is not skill demand / employment
    ("gdelt_doc", "frontier_capability_index"),        # news volume is not capability
])
def test_invalid_substitutions_are_refused(label, target):
    with pytest.raises(C.SourceNotAllowed):
        C.check_sources(target, label, set())


def test_every_feature_group_names_a_registered_source():
    for g in F.FEATURE_GROUPS:
        assert F.GROUP_SOURCE[g] in R.SOURCES
    assert set(F.ALL_FEATURES) == {f for cols in F.FEATURE_GROUPS.values() for f in cols}


def test_stale_source_is_not_reported_fresh(ai_v):
    import pandas as pd
    h = R.health("indeed_ai_tracker", ai_v, pd.Timestamp("2026-01-01", tz="UTC"))
    assert h["status"] == "stale"
