"""Source rules: BTOS and other sources may only inform the targets they measure."""
import dataclasses

import pytest

from forecasting import contracts as C, registry as R
from forecasting.targets import all_specs


def test_every_implemented_target_passes_its_own_contract():
    for tid, spec in all_specs().items():
        C.check_sources(tid, C.TARGETS[tid].label_source, set(spec.group_source.values()))
        assert C.TARGETS[tid].status == "implemented" and C.TARGETS[tid].horizons == spec.horizons


def test_adoption_models_use_no_cross_domain_source():
    specs = all_specs()
    assert set(specs["worker_genai_use_rate"].group_source.values()) == {"rps_genai"}  # no BTOS, no exposure
    assert set(specs["btos_ai_use_rate"].group_source.values()) == {"census_btos"}
    assert "census_btos" not in set(specs["ai_mention_share"].group_source.values())


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
    ("gdelt_doc", "frontier_time_horizon"),        # news volume is not capability
])
def test_invalid_substitutions_are_refused(label, target):
    with pytest.raises(C.SourceNotAllowed):
        C.check_sources(target, label, set())


def test_every_feature_group_names_a_registered_source():
    for spec in all_specs().values():
        assert set(spec.feature_groups) == set(spec.group_source)
        assert all(src in R.SOURCES for src in spec.group_source.values())


def test_stale_source_is_not_reported_fresh(ai_v):
    import pandas as pd
    h = R.vintage_health("indeed_ai_tracker", ai_v, pd.Timestamp("2026-01-01", tz="UTC"))
    assert h["status"] == "stale"
    assert R.health("census_btos", None, None, pd.Timestamp("2026-01-01", tz="UTC"))["status"] == "no_data"
