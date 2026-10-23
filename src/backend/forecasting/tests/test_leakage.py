"""No information from after a forecast origin may reach features, labels or fitted preprocessing."""
import numpy as np
import pandas as pd

from forecasting import evaluation as E, features as F
from forecasting.models import RidgeModel


def test_snapshot_uses_only_vintages_published_by_the_origin(ai_v, po_v):
    s = F.snapshot_real(ai_v, po_v, pd.Timestamp("2024-05-01", tz="UTC"))
    assert s.ai_vintage == "v1" and s.last_month == pd.Period("2024-03", freq="M")
    # v2 revised every value up by 1 pp: none of that revision may be visible at this origin
    v1 = ai_v[ai_v["vintage_id"] == "v1"].set_index(["geo", "month"])["value"]
    assert np.allclose(s.ai.set_index(["geo", "month"])["value"], v1.loc[s.ai.set_index(["geo", "month"]).index])
    assert set(s.postings["month"]) <= {str(m) for m in pd.period_range("2019-01", "2020-12", freq="M")}


def test_labels_never_reach_past_the_snapshot(ai_v, po_v):
    s = F.snapshot_real(ai_v, po_v, pd.Timestamp("2024-05-01", tz="UTC"))
    for h in E.HORIZONS:
        t = F.labelled(s, h)
        assert (t["month"] + h <= s.last_month).all()
        assert len(t) > 0


def test_label_is_the_logit_change_within_the_snapshot(ai_v, po_v):
    s = F.snapshot_real(ai_v, po_v, pd.Timestamp("2024-05-01", tz="UTC"))
    t = F.labelled(s, 3).set_index(["month", "geo"])
    v = s.ai.assign(month=pd.PeriodIndex(s.ai["month"], freq="M")).set_index(["month", "geo"])["value"]
    m, g = pd.Period("2022-01", freq="M"), "BB"
    assert np.isclose(t.loc[(m, g), "target"], F.logit(v[(m + 3, g)] / 100) - F.logit(v[(m, g)] / 100))


def test_reconstructed_snapshot_is_cut_and_flagged(ai_v, po_v):
    s = F.snapshot_reconstructed(ai_v, po_v, pd.Period("2022-06", freq="M"))
    assert s.kind == "reconstructed" and s.ai["month"].max() == "2022-06"
    assert s.origin > pd.Timestamp("2022-08-01", tz="UTC")  # waits out the publication lag
    assert (s.postings["month"] <= "2020-12").all()  # postings: only the real vintage of that time


def test_missing_months_stay_missing(ai_v, po_v):
    gap = ai_v[~((ai_v["geo"] == "AA") & (ai_v["month"] == "2023-06"))]
    s = F.snapshot_real(gap, po_v, pd.Timestamp("2024-05-01", tz="UTC"))
    p = F.panel(s).set_index(["month", "geo"])
    assert np.isnan(p.loc[(pd.Period("2023-06", freq="M"), "AA"), "lvl"])
    assert np.isnan(p.loc[(pd.Period("2023-09", freq="M"), "AA"), "d3"])


def test_preprocessing_is_fitted_on_training_rows_only(ai_v, po_v):
    s = F.snapshot_real(ai_v, po_v, pd.Timestamp("2024-05-01", tz="UTC"))
    train = F.labelled(s, 3)
    m = RidgeModel().fit(train, 3, F.ALL_FEATURES)
    imp = m.pipe.steps[0][1]
    assert np.allclose(imp.statistics_[0], train["lvl"].median())


def test_origins_are_chronological_and_selection_never_sees_holdout_outcomes(ai_v, po_v):
    snaps = E.origins(ai_v, po_v)
    assert all(a.origin < b.origin for a, b in zip(snaps, snaps[1:]))
    split = E.make_split(snaps, pd.Period("2024-05", freq="M"))
    for s in snaps:
        for h in E.HORIZONS:
            if E.in_selection(s, h, split):
                assert s.origin < split.holdout_start
                assert s.last_month + h <= split.holdout_last_month
