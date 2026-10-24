"""Adoption targets: BTOS wording break, publication dates and missing codes; RPS vintages and short history."""
import numpy as np
import pandas as pd
import pytest

from forecasting import btos, features as F, rps
from forecasting.targets import business_adoption as BA, occupation_adoption as OA


def test_census_codes_are_kept_apart_and_never_zero():
    assert btos.parse_pct("12.5%") == (12.5, "ok")
    assert btos.parse_pct("S") == (None, "suppressed")
    assert btos.parse_pct(".") == (None, "not_asked")
    assert btos.parse_pct(np.nan) == (None, "missing")


def _btos_obs():
    """Synthetic BTOS observations (not real data): old wording periods 0-9, new wording 13-22, published 18 days
    after each fortnight; the new level starts much higher, as the real break did."""
    rows = []
    for wording, periods, base in (("old", range(0, 10), 5.0), ("new", range(13, 23), 17.0)):
        for unit in ("US", "54"):
            for p in periods:
                for measure, bump in (("current_use", 0.0), ("expected_use", 3.0)):
                    rows.append({"measure": measure, "wording": wording, "unit": unit, "period": p,
                                 "estimate_pct": base + 0.2 * p + bump, "se_pct": 0.2, "status": "ok",
                                 "available_at": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=14 * p + 18)})
    return pd.DataFrame(rows)


@pytest.fixture
def btos_data():
    obs = _btos_obs()
    return {"use": BA._series(obs, "current_use"), "expect": BA._series(obs, "expected_use"), "obs": obs}


def test_btos_series_never_cross_the_wording_break(btos_data):
    s = BA.origins(btos_data)[-1]
    p = BA.panel(s).set_index(["period", "unit"])
    assert {u.split("|")[1] for u in p.index.get_level_values(1)} == {"old", "new"}
    first_new = p.loc[(13, "US|new")]
    assert np.isnan(first_new["d1"]) and np.isnan(first_new["trend"])  # no change measured across the break
    for h in BA.SPEC.horizons:
        t = F.labelled(BA.SPEC, s, h)
        assert not ((t["period"] <= 9) & (t["period"] + h >= 13)).any()  # no label spans the break


def test_btos_origin_sees_only_published_fortnights(btos_data):
    for s in BA.origins(btos_data):
        published = btos_data["use"][btos_data["use"]["available_at"] <= s.origin]
        assert len(s.values) == len(published) and s.last == published["period"].max()
        assert (s.extras["expect"]["period"] <= s.last).all()


def test_btos_expectation_gap_uses_the_same_unit_and_fortnight(btos_data):
    p = BA.panel(BA.origins(btos_data)[-1]).set_index(["period", "unit"])
    r = p.loc[(15, "54|new")]
    use = 17.0 + 0.2 * 15
    assert np.isclose(r["exp_gap"], F.logit((use + 3) / 100) - F.logit(use / 100))


def test_real_btos_table_keeps_the_break_and_publication_dates():
    obs = btos.load()
    btos.validate(obs.drop(columns="available_at"))
    ok = obs[obs["status"] == "ok"]
    assert ok.groupby(["measure", "unit", "smpdt"])["wording"].nunique().max() == 1
    assert (ok.loc[ok["wording"] == "old", "smpdt"].max() < ok.loc[ok["wording"] == "new", "smpdt"].min())
    assert (ok["available_at"] > ok["ref_end"].dt.tz_localize("UTC")).all()  # published after the fortnight ends
    assert (obs.loc[obs["status"] != "ok", "estimate_pct"].isna()).all()


def test_alfred_vintages_parse_with_their_own_dates():
    payload = {"observations": [
        {"realtime_start": "2025-02-10", "realtime_end": "2025-05-01", "date": "2024-10-01", "value": "31.0"},
        {"realtime_start": "2025-05-02", "realtime_end": "9999-12-31", "date": "2024-10-01", "value": "31.4"},
        {"realtime_start": "2025-05-02", "realtime_end": "9999-12-31", "date": "2025-01-01", "value": "."}]}
    d = rps.parse_alfred("X", payload, "f.json", pd.Timestamp("2026-10-24", tz="UTC"))
    assert len(d) == 2 and set(d["availability_basis"]) == {"alfred"}  # "." is no value, not 0
    early = OA._as_of(d.assign(unit="00"), pd.Timestamp("2025-03-01", tz="UTC"))
    assert early["value_pct"].item() == 31.0  # the revision published later is not seen


def test_assumed_rps_availability_is_never_after_the_fetch(tmp_path):
    f = tmp_path / "X.csv"
    pd.DataFrame({"observation_date": ["2026-07-01"], "X": [40.0]}).to_csv(f, index=False)
    d = rps.parse_csv("X", f, pd.Timestamp("2026-10-22", tz="UTC"))
    assert d["available_at"].item() == pd.Timestamp("2026-10-21", tz="UTC")  # quarter end + 21 days
    assert d["availability_basis"].item() == "assumed"


def test_occupation_origins_are_flagged_and_point_in_time():
    d = OA.load()
    snaps = OA.origins(d)
    assert all(s.kind in ("current_only", "real", "reconstructed") for s in snaps)
    for s in snaps:
        assert s.values["period"].max() == s.last
        if s.kind == "real":  # real origins only see what FRED had published by then
            assert (d["obs"].loc[d["obs"]["quarter"] <= s.last, "available_at"].min() <= s.origin)
    assert OA.SPEC.history_warning and OA.SPEC.min_selection_origins < 12


def test_alfred_origins_use_each_release_and_flag_earlier_ones():
    def row(q, value, when):
        return {"unit": "00", "quarter": pd.Period(q, freq="Q"), "value_pct": value,
                "available_at": pd.Timestamp(when, tz="UTC"), "availability_basis": "alfred"}
    obs = pd.DataFrame([row("2025Q1", 30.0, "2026-06-18"), row("2025Q2", 31.0, "2026-06-18"),
                        row("2025Q3", 32.0, "2026-06-18"), row("2025Q3", 32.5, "2026-10-16"),
                        row("2025Q4", 33.0, "2026-10-16")])  # synthetic: one revision, one new quarter
    snaps = OA.origins({"obs": obs})
    kinds = [(str(s.last), s.kind) for s in snaps]
    assert kinds == [("2025Q1", "reconstructed"), ("2025Q2", "reconstructed"), ("2025Q3", "real"), ("2025Q4", "real")]
    first_real = snaps[2].values.set_index("period")["value"]
    assert first_real[pd.Period("2025Q3", freq="Q")] == 32.0  # the later revision (32.5) is not visible yet
    assert snaps[3].values.set_index("period")["value"][pd.Period("2025Q3", freq="Q")] == 32.5
