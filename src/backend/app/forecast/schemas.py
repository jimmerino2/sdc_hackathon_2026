from typing import Literal

from pydantic import BaseModel, Field


class Range(BaseModel):
    low: float = Field(description="Lower end of the likely range (10th percentile of past errors)")
    high: float = Field(description="Upper end of the likely range (90th percentile of past errors)")


class Projection(BaseModel):
    """One forecast of the sector's postings index 12 months ahead."""

    method: str = Field(description="How the number was produced")
    index: float = Field(description="Predicted job-postings index (1 Feb 2020 = 100)")
    change_pct: float = Field(description="Change from the current index, in percent")
    range: Range


class Reliability(BaseModel):
    status: Literal["indicative", "validated"] = Field(
        description="'indicative' = the ML model did not beat simple baselines in testing"
    )
    note: str


class HorizonOutlook(BaseModel):
    """The forecast for one horizon (3, 6, 9 or 12 months ahead)."""

    horizon_months: int = Field(description="How many months ahead: 3, 6, 9 or 12")
    forecast_for: str | None = Field(None, description="Month being forecast, YYYY-MM")
    trend: Literal["growing", "stable", "shrinking"] = Field(
        description="'growing' above +2%, 'shrinking' below -2%, otherwise 'stable' (scaled to the horizon)"
    )
    forecast: Projection = Field(description="Main forecast: last year's pace repeats, shifted by the scenario")
    model_forecast: Projection = Field(description="Machine-learning (LightGBM) forecast, for comparison")
    average_change_index: float | None = Field(
        None, description="Reference: the index if this sector moved by the average past change (same % for every sector)"
    )
    reliability: Reliability


class ForecastRow(BaseModel):
    """A sector's outlook under one AI scenario, at every horizon (from forecast_output.csv)."""

    sector: str
    scenario: Literal["Slow", "Baseline", "Rapid AI"] = Field(
        description="What-if AI adoption pace. An assumption, not a tested result"
    )
    country: str = Field(description="Country the data comes from")
    is_proxy_for_malaysia: bool = Field(description="True when the US data stands in for Malaysia")
    forecast_from: str = Field(description="Latest month of data used, YYYY-MM")
    current_index: float = Field(description="Sector job-postings index now (1 Feb 2020 = 100)")
    ai_exposure: float | None = Field(None, description="0-1, how much AI is already used in the sector's jobs. Null if unmapped")
    data_as_of: str | None = None
    outlook: list[HorizonOutlook] = Field(description="One entry per horizon, shortest first")


class JobHorizon(BaseModel):
    """A job's forecast at one horizon, as a percent change from today."""

    horizon_months: int = Field(description="3, 6, 9 or 12")
    forecast_for: str = Field(description="Month being forecast, YYYY-MM")
    trend: Literal["growing", "stable", "shrinking"]
    change_pct: float = Field(description="Main forecast: expected change in postings, in percent")
    range: Range = Field(description="Likely range of change_pct, in percent")
    model_change_pct: float = Field(description="Machine-learning (LightGBM) forecast, for comparison")
    reliability: Reliability


class JobForecast(BaseModel):
    """A job's outlook, inherited from its sector(s), under one AI scenario."""

    onet_code: str
    title: str
    scenario: Literal["Slow", "Baseline", "Rapid AI"]
    sectors: str = Field(description="Sector(s) the job's trend comes from, with each share, e.g. 'Construction (50%), ...'")
    country: str
    is_proxy_for_malaysia: bool
    forecast_from: str
    ai_exposure: float | None = Field(None, description="0-1, how much AI is already used in this job")
    automation_share: float | None = Field(None, description="Share of AI use that automates the work. Null if unknown")
    augmentation_share: float | None = Field(None, description="Share of AI use that assists the worker. Null if unknown")
    ai_exposure_low_sample: bool = Field(description="True if the exposure figure rests on little data")
    note: str = Field(description="How to read this number")
    data_as_of: str | None = None
    outlook: list[JobHorizon] = Field(description="One entry per horizon, shortest first")
