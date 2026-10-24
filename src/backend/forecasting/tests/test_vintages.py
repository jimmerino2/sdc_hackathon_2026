"""Ingestion: schema handling, missing data, point-in-time lookup, idempotence, failure safety."""
import os
import subprocess

import numpy as np
import pandas as pd
import pytest

from forecasting import vintages as V


def test_day_first_dates_are_detected():
    s = pd.Series(["1/3/24", "2/3/24", "3/3/24"])  # 1-3 March, day first: month-first would jump a month
    d = V.parse_dates(s, pd.Series(["US"] * 3))
    assert list(d.dt.strftime("%Y-%m-%d")) == ["2024-03-01", "2024-03-02", "2024-03-03"]


def test_unparseable_dates_are_not_guessed():
    assert V.parse_dates(pd.Series(["2024-01-01", "garbage"])).isna().all()


def test_monthly_keeps_gaps_and_flags_partial_months():
    daily = pd.DataFrame({"geo": "US", "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-03-01"]),
                          "value": [1.0, 3.0, 5.0]})
    m = V.monthly(daily)
    assert list(m["month"]) == ["2024-01", "2024-03"]  # February is missing, not zero
    assert m["value"].iloc[0] == 2.0 and m["is_partial"].all()
    assert m["numerator"].isna().all()  # no published counts -> blank, never 0


def test_as_of_never_returns_a_later_vintage(ai_v):
    before = V.as_of(ai_v, pd.Timestamp("2024-05-01", tz="UTC"))
    assert set(before["vintage_id"]) == {"v1"}
    assert V.as_of(ai_v, pd.Timestamp("2024-01-01", tz="UTC")).empty
    assert set(V.as_of(ai_v, pd.Timestamp("2030-01-01", tz="UTC"))["vintage_id"]) == {"v2"}


def test_as_of_single_vintage_drops_countries_the_latest_file_dropped(ai_v):
    v = ai_v[~((ai_v["vintage_id"] == "v2") & (ai_v["geo"] == "CC"))]
    now = pd.Timestamp("2030-01-01", tz="UTC")
    assert "CC" not in set(V.as_of(v, now)["geo"])
    assert set(V.as_of(v, now, per_geo=True).query("geo == 'CC'")["vintage_id"]) == {"v1"}


def test_validate_rejects_duplicates_and_bad_values(ai_v):
    with pytest.raises(ValueError):
        V.validate(pd.concat([ai_v, ai_v.head(1)]), 0, 100)
    with pytest.raises(ValueError):
        V.validate(ai_v.assign(value=-1.0), 0, 100)
    V.validate(ai_v, 0, 100)


def _git(repo, *a, when="2024-06-01T00:00:00Z"):
    env = {**os.environ, "GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when}
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, env=env)


@pytest.fixture
def ai_repo(tmp_path):
    """A throwaway git repo with three commits shaped like hiring-lab/ai-tracker (synthetic values)."""
    r = tmp_path / "ait"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t"); _git(r, "config", "user.name", "t")
    days = pd.date_range("2024-01-01", "2024-02-29")
    old = pd.DataFrame({"modified_date": [f"{d.day}/{d.month}/{d:%y}" for d in days],  # day-first, as in 2024
                        "jobcountry": "US", "% of job postings": 2.0})
    old.to_csv(r / "AI_posting_2024-02-29_clean.csv", index=False)
    _git(r, "add", "-A"); _git(r, "commit", "-q", "-m", "v1", when="2024-03-05T00:00:00Z")
    new = pd.DataFrame({"date": days.strftime("%Y-%m-%d"), "jobcountry": "US", "AI_share_postings": 3.0})
    (r / "AI_posting_2024-02-29_clean.csv").unlink()
    new.to_csv(r / "AI_posting.csv", index=False)
    _git(r, "add", "-A"); _git(r, "commit", "-q", "-m", "v2")
    _git(r, "commit", "-q", "--allow-empty", "-m", "readme only")
    return r


def test_build_reads_every_schema_and_keeps_each_vintage(ai_repo):
    out = V.build_ai_share(ai_repo)
    assert out["vintage_id"].nunique() == 2
    first = out[out["available_at"] == out["available_at"].min()]
    assert set(first["value"]) == {2.0} and set(out["value"]) == {2.0, 3.0}
    assert first["schema_version"].iloc[0] == "modified_date|jobcountry|% of job postings"


def test_build_is_idempotent(ai_repo):
    pd.testing.assert_frame_equal(V.build_ai_share(ai_repo), V.build_ai_share(ai_repo))


def test_unknown_schema_fails_loudly(ai_repo):
    pd.DataFrame({"date": ["2024-03-01"], "jobcountry": ["US"], "new_metric": [1]}).to_csv(ai_repo / "AI_posting.csv",
                                                                                          index=False)
    _git(ai_repo, "commit", "-qam", "schema change")
    with pytest.raises(ValueError, match="unexpected columns"):
        V.build_ai_share(ai_repo)


def test_failed_fetch_keeps_local_history(ai_repo, monkeypatch, capsys):
    monkeypatch.setattr(V, "RAW", ai_repo.parent)
    monkeypatch.setitem(V.REPOS, "ait", "https://invalid.invalid/none.git")
    V.pull("ait")  # no remote: must warn, not raise or delete
    assert "warning" in capsys.readouterr().out
    assert V.build_ai_share(ai_repo)["vintage_id"].nunique() == 2


def test_write_replaces_atomically(tmp_path, monkeypatch, ai_v):
    monkeypatch.setattr(V, "OUT", tmp_path)
    V.write(ai_v, "t.csv")
    before = (tmp_path / "t.csv").read_text()
    with pytest.raises(Exception):
        V.write(ai_v.assign(available_at="not a date"), "t.csv")  # fails before the swap
    assert (tmp_path / "t.csv").read_text() == before
    assert np.isclose(V.load("t.csv")["value"].sum(), ai_v["value"].round(5).sum())
