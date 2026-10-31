"""No information from after a forecast origin may reach features, labels or fitted preprocessing.

Runs on worker adoption with synthetic releases: the first publishes through 2025Q4; the second, later, revises all
history up by 1 pp and adds two quarters. A forecast made between them must not see any of that.
"""
import numpy as np
import pandas as pd
import pytest

from forecasting import evaluation as E, features as F
from forecasting.models import RidgeModel
from forecasting.targets import occupation_adoption as OA

SPEC = OA.SPEC
UNITS = ["00", "11", "13"]
FIRST = pd.Timestamp("2026-02-01", tz="UTC")
SECOND = pd.Timestamp("2026-08-01", tz="UTC")
LAST_OF_FIRST = pd.Period("2025Q4", freq="Q")
LAST_OF_SECOND = pd.Period("2026Q2", freq="Q")


def _release(last: pd.Period, when: pd.Timestamp, revision: float) -> pd.DataFrame:
    rows = [{"unit": u, "quarter": q, "value_pct": 20 + 5 * ui + 1.5 * i + 0.3 * (i % 3) + revision, "available_at": when, "availability_basis": "alfred"}
            for ui, u in enumerate(UNITS) for i, q in enumerate(pd.period_range("2022Q1", last, freq="Q"))]
    return pd.DataFrame(rows)


@pytest.fixture
def obs():
    return pd.concat([_release(LAST_OF_FIRST, FIRST, 0.0), _release(LAST_OF_SECOND, SECOND, 1.0)], ignore_index=True)


def _real_first(obs):
    return next(s for s in OA.origins({"obs": obs}) if s.origin == FIRST)


def test_snapshot_uses_only_releases_published_by_the_origin(obs):
    s = _real_first(obs)
    assert s.kind == "real" and s.last == LAST_OF_FIRST
    # the second release revised every value up by 1 pp: none of that revision may be visible at this origin
    first = obs[obs["available_at"] == FIRST]
    got = s.values.merge(first, left_on=["unit", "period"], right_on=["unit", "quarter"])
    assert len(got) == len(s.values) and np.allclose(got["value"], got["value_pct"])


def test_labels_never_reach_past_the_snapshot(obs):
    s = _real_first(obs)
    for h in SPEC.horizons:
        t = F.labelled(SPEC, s, h)
        assert len(t) > 0 and (t["period"] + h <= s.last).all()


def test_label_is_the_logit_change_within_the_snapshot(obs):
    s = _real_first(obs)
    t = F.labelled(SPEC, s, 1).set_index(["period", "unit"])
    v = s.values.set_index(["period", "unit"])["value"]
    q, u = pd.Period("2024Q1", freq="Q"), "11"
    assert np.isclose(t.loc[(q, u), "target"], F.logit(v[(q + 1, u)] / 100) - F.logit(v[(q, u)] / 100))


def test_reconstructed_snapshot_is_cut_and_flagged(obs):
    s = next(s for s in OA.origins({"obs": obs}) if s.kind == "reconstructed")
    assert s.values["period"].max() == s.last == OA.FIRST_LAST
    assert s.origin > s.last.end_time.tz_localize("UTC")  # waits out the publication lag
    assert s.origin < FIRST  # dated before the release it was cut from, so it must carry nothing later than its quarter


def test_missing_quarters_stay_missing(obs):
    gap = obs[~((obs["unit"] == "11") & (obs["quarter"] == pd.Period("2024Q2", freq="Q")))]
    p = SPEC.panel(_real_first(gap)).set_index(["period", "unit"])
    assert np.isnan(p.loc[(pd.Period("2024Q2", freq="Q"), "11"), "lvl"])
    assert np.isnan(p.loc[(pd.Period("2025Q2", freq="Q"), "11"), "d4"])


def test_preprocessing_is_fitted_on_training_rows_only(obs):
    train = F.labelled(SPEC, _real_first(obs), 1)
    m = RidgeModel().fit(train, 1, SPEC.features, SPEC.trend_steps)
    assert np.allclose(m.pipe.steps[0][1].statistics_[0], train["lvl"].median())


def test_origins_are_chronological_and_selection_never_sees_holdout_outcomes(obs):
    snaps = OA.origins({"obs": obs})
    E.check_chronological(snaps)
    split = E.make_split(SPEC, snaps, LAST_OF_SECOND)
    for s in snaps:
        for h in SPEC.horizons:
            if E.role(s, h, split) == "selection":
                assert s.origin < split.holdout_start and s.last + h <= split.holdout_last


def test_backtest_scores_against_truth_and_marks_unavailable(obs):
    d = {"obs": obs}
    snaps = OA.origins(d)
    y = OA.truth(d)
    split = E.make_split(SPEC, snaps, y.index.get_level_values(0).max())
    bt = E.backtest(SPEC, snaps[-3:], y, split, candidates=["naive", "ridge"])
    late = bt[bt["target_period"] > str(LAST_OF_SECOND)]
    assert len(late) and late["actual"].isna().all() and late["error"].isna().all()  # not yet published: unavailable, not 0
    assert (bt["n_train"] > 0).all()
