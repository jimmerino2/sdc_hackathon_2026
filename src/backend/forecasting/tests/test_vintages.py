"""Ingestion: schema handling, missing data, point-in-time lookup, idempotence, failure safety."""
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


def test_write_replaces_atomically(tmp_path, monkeypatch, ai_v):
    monkeypatch.setattr(V, "OUT", tmp_path)
    V.write(ai_v, "t.csv")
    before = (tmp_path / "t.csv").read_text()
    with pytest.raises(Exception):
        V.write(ai_v.assign(available_at="not a date"), "t.csv")  # fails before the swap
    assert (tmp_path / "t.csv").read_text() == before
    assert np.isclose(V.load("t.csv")["value"].sum(), ai_v["value"].round(5).sum())
