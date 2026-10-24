"""Skill-emergence signals on SYNTHETIC package downloads and job-ad panels: missing data, low volume, staleness,
source failures, no look-ahead, and that the job-ad baseline is untouched."""
import numpy as np
import pandas as pd
import pytest

from occupational import models as M, signals as SG
from occupational.sources import packages as P

from .test_models import _panel

CFG = {"version": "test", "reference": {"pypi": ["ref"], "npm": []},
       "skills": {"python": {"pypi": ["pkg"], "related": ["rust", "django"]}, "rust": {"pypi": ["tiny"]}},
       "sources": {}}


def _dl(months, pkg_growth=0.0, gap=None, tiny=False):
    """SYNTHETIC monthly downloads: a reference basket growing 3%/month and a package growing pkg_growth faster."""
    rows = []
    for i, m in enumerate(months):
        ref = 1e6 * 1.03 ** i
        rows.append({"source": "pypi", "package": "ref", "month": str(m), "downloads": ref})
        if gap is None or not (gap[0] <= i < gap[1]):
            rows.append({"source": "pypi", "package": "pkg", "month": str(m), "downloads": 2e5 * 1.03 ** i * np.exp(pkg_growth * i)})
        rows.append({"source": "pypi", "package": "tiny", "month": str(m), "downloads": 50.0 * (i + 1) if tiny else 5e4})
    return pd.DataFrame(rows)


def test_growth_is_relative_to_the_reference_basket():
    p = _panel()
    a = SG.adoption(_dl(p.months), CFG, ["python", "rust"], p.months)
    assert np.nanmax(np.abs(a["g6"][0])) < 1e-9  # grows exactly like the ecosystem: no signal
    b = SG.adoption(_dl(p.months, pkg_growth=0.02), CFG, ["python", "rust"], p.months)
    assert np.nanmin(b["g6"][0]) == pytest.approx(0.12, abs=1e-6)  # 2%/month faster: log growth 0.12 in 6 months


def test_missing_months_are_missing_not_zero():
    p = _panel()
    a = SG.adoption(_dl(p.months, gap=(40, 42)), CFG, ["python", "rust"], p.months)
    g = a["g6"][0]
    assert np.isnan(g[40:44]).all()  # windows touching the gap have no value
    assert np.isnan(g[46:50]).all()  # nor windows compared with them
    assert np.isfinite(g[52])
    m = pd.DataFrame({"source": "npm", "package": "x", "month": ["2024-02", "2024-03"], "downloads": [10, 10],
                      "days": [29, 12], "retrieved_at": "t"})
    assert list(P.monthly(m)["month"]) == ["2024-02"]  # an incomplete month is dropped, not kept as a low count


def test_tiny_packages_are_not_evidence():
    p = _panel()
    a = SG.adoption(_dl(p.months, tiny=True), CFG, ["python", "rust"], p.months)
    assert np.isnan(a["g6"][1]).all()  # 50 -> 300 downloads a month is a large % but below MIN_DOWNLOADS_3M


def test_related_skills_exclude_the_skill_itself(data_dir):
    rel = SG.related_map(["python", "rust", "django"], {"skills": {"python": {"related": ["python", "rust", "nope"]}}})
    assert rel["python"] == ["rust"]
    assert "rust" not in rel["rust"]  # category fallback (both are languages) never lists the skill


def test_features_do_not_look_ahead():
    p = _panel()
    t = 40
    sg = SG.Signals(p, _dl(p.months, pkg_growth=0.01), CFG)
    before = {k: v[:, t].copy() for k, v in sg.F.items()}
    q = _panel()
    q.K[:, t + 1:] = q.N[:, t + 1:]
    q.f = M.features(q.K, q.N, q.f["skill"], q.f["occ"], q.f["n_occ"])
    dl = _dl(q.months, pkg_growth=0.01)
    later = pd.PeriodIndex(dl["month"], freq="M") > q.months[t]
    dl.loc[later, "downloads"] *= 50  # the future explodes
    sg2 = SG.Signals(q, dl, CFG)
    for k, v in before.items():
        np.testing.assert_allclose(sg2.F[k][:, t], v, err_msg=k)


def test_corrections_without_information_leave_the_baseline_alone(monkeypatch):
    monkeypatch.setattr(SG.B, "MIN_RIDGE_ROWS", 20)
    p = _panel()
    sg = SG.Signals(p, pd.DataFrame(columns=P.COLS), CFG)  # no package data at all
    for k in sg.F:
        sg.F[k] = np.zeros_like(sg.F[k], dtype=float)
    rng = np.random.default_rng(0)
    rows = pd.DataFrame({"series": np.tile(np.arange(len(p.series)), 40), "origin_idx": np.repeat(np.arange(30, 70), len(p.series))})
    rows["baseline"] = 0.2
    rows["actual_n"] = 100.0
    rows["actual"] = rng.binomial(100, 0.2, len(rows)) / 100
    rows["actual_k"] = rows["actual"] * 100
    f, _ = SG.corrections(sg, rows, SG.OWN + SG.EXT, 100.0)
    assert np.allclose(f, 0.2, atol=0.01)  # no features, unbiased target: no invented uplift


def test_source_failure_keeps_the_cache(data_dir, monkeypatch):
    store_rows = pd.DataFrame({"source": ["pypi"], "package": ["pandas"], "month": ["2024-01"], "downloads": [5.0],
                               "days": [31], "retrieved_at": ["t"]})
    from occupational import store
    store.write_json("taxonomy/skill_signals.json", CFG)
    store.write_table(P.CACHE, store_rows)

    def boom(*a, **k):
        raise OSError("network down")
    monkeypatch.setattr(P, "_http", boom)
    h = P.fetch(True)
    assert h["status"] in ("partial", "missing") and h["failed"]
    assert P.load().equals(store.read_table(P.CACHE, dtype={"month": str}))
    assert len(P.load()) == 1


def test_stale_indicator_is_flagged():
    p = _panel()
    dl = _dl(p.months)
    dl = dl[~((dl["package"] == "pkg") & (pd.PeriodIndex(dl["month"], freq="M") > p.months[-4]))]
    sg = SG.Signals(p, dl, CFG)
    ind = SG.indicators(sg, dl, CFG, str(p.months[-1])).set_index("package")
    assert not ind.loc["pkg", "fresh"] and ind.loc["pkg", "latest_month"] == str(p.months[-4])
    assert np.isnan(ind.loc["pkg", "downloads_3m"])  # no current value is invented


def test_signal_labels():
    f = pd.DataFrame({"adoption_g6": [0.3, 0.3, np.nan, -0.3, np.nan], "related_g6": [0.2, -0.2, 0.2, -0.2, np.nan]})
    assert list(SG._signal_label(f)) == ["accelerating", "contradictory", "some_acceleration", "slowing", "no_signal"]
