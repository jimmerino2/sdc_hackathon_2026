"""No information from after a forecast origin may reach features, labels or fitted preprocessing."""
import numpy as np
import pandas as pd

from forecasting import evaluation as E, features as F
from forecasting.models import RidgeModel
from forecasting.targets import skill_demand as SD

SPEC = SD.SPEC
ORIGIN = pd.Timestamp("2024-05-01", tz="UTC")


def test_snapshot_uses_only_vintages_published_by_the_origin(ai_v, po_v):
    s = SD.snapshot_real(ai_v, po_v, ORIGIN)
    assert s.vintage == "v1" and s.last == pd.Period("2024-03", freq="M")
    # v2 revised every value up by 1 pp: none of that revision may be visible at this origin
    v1 = ai_v[ai_v["vintage_id"] == "v1"].assign(period=lambda d: pd.PeriodIndex(d["month"], freq="M"))
    got = s.values.merge(v1.rename(columns={"geo": "unit"}), on=["unit", "period"])
    assert len(got) == len(s.values) and np.allclose(got["value_x"], got["value_y"])
    assert (s.extras["postings"]["period"] <= pd.Period("2020-12", freq="M")).all()


def test_labels_never_reach_past_the_snapshot(ai_v, po_v):
    s = SD.snapshot_real(ai_v, po_v, ORIGIN)
    for h in SPEC.horizons:
        t = F.labelled(SPEC, s, h)
        assert len(t) > 0 and (t["period"] + h <= s.last).all()


def test_label_is_the_logit_change_within_the_snapshot(ai_v, po_v):
    s = SD.snapshot_real(ai_v, po_v, ORIGIN)
    t = F.labelled(SPEC, s, 3).set_index(["period", "unit"])
    v = s.values.set_index(["period", "unit"])["value"]
    m, u = pd.Period("2022-01", freq="M"), "BB"
    assert np.isclose(t.loc[(m, u), "target"], F.logit(v[(m + 3, u)] / 100) - F.logit(v[(m, u)] / 100))


def test_reconstructed_snapshot_is_cut_and_flagged(ai_v, po_v):
    s = SD.snapshot_reconstructed(ai_v, po_v, pd.Period("2022-06", freq="M"))
    assert s.kind == "reconstructed" and s.values["period"].max() == pd.Period("2022-06", freq="M")
    assert s.origin > pd.Timestamp("2022-08-01", tz="UTC")  # waits out the publication lag
    assert (s.extras["postings"]["period"] <= pd.Period("2020-12", freq="M")).all()  # postings: real vintage only


def test_missing_months_stay_missing(ai_v, po_v):
    gap = ai_v[~((ai_v["geo"] == "AA") & (ai_v["month"] == "2023-06"))]
    p = SPEC.panel(SD.snapshot_real(gap, po_v, ORIGIN)).set_index(["period", "unit"])
    assert np.isnan(p.loc[(pd.Period("2023-06", freq="M"), "AA"), "lvl"])
    assert np.isnan(p.loc[(pd.Period("2023-09", freq="M"), "AA"), "d3"])


def test_preprocessing_is_fitted_on_training_rows_only(ai_v, po_v):
    train = F.labelled(SPEC, SD.snapshot_real(ai_v, po_v, ORIGIN), 3)
    m = RidgeModel().fit(train, 3, SPEC.features, SPEC.trend_steps)
    assert np.allclose(m.pipe.steps[0][1].statistics_[0], train["lvl"].median())


def test_origins_are_chronological_and_selection_never_sees_holdout_outcomes(ai_v, po_v):
    snaps = SD.origins({"ai": ai_v, "postings": po_v})
    E.check_chronological(snaps)
    split = E.make_split(SPEC, snaps, pd.Period("2024-05", freq="M"))
    for s in snaps:
        for h in SPEC.horizons:
            if E.role(s, h, split) == "selection":
                assert s.origin < split.holdout_start and s.last + h <= split.holdout_last


def test_backtest_scores_against_truth_and_marks_unavailable(ai_v, po_v):
    d = {"ai": ai_v, "postings": po_v}
    snaps = SD.origins(d)
    y = SD.truth(d)
    split = E.make_split(SPEC, snaps, y.index.get_level_values(0).max())
    bt = E.backtest(SPEC, snaps[-3:], y, split, candidates=["naive", "ridge"])
    late = bt[bt["target_period"] > "2024-05"]
    assert late["actual"].isna().all() and late["error"].isna().all()  # not yet published: unavailable, not 0
    assert (bt["n_train"] > 0).all()
