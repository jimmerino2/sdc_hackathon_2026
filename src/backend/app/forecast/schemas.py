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
    model_range: Range = Field(description="Likely range of model_change_pct, in percent")
    reliability: Reliability


class HistoryPoint(BaseModel):
    """What actually happened to a job's postings in one past month, as a percent change relative to the latest month."""

    month: str = Field(description="YYYY-MM")
    change_pct: float = Field(description="Postings then vs the latest month, in percent (0 at the latest month, so a past dip is negative)")


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
    history: list[HistoryPoint] = Field(description="The job's sector postings over the past year, oldest first, ending at forecast_from")
    outlook: list[JobHorizon] = Field(description="One entry per horizon, shortest first")


class DataSource(BaseModel):
    """Where a trend number comes from, and how fresh it is."""

    id: str
    name: str = Field(description="Dataset name, e.g. 'Indeed Job Postings Index'")
    publisher: str
    url: str
    license: str
    used_for: str = Field(description="What on screen this source drives")
    as_of: str | None = Field(None, description="Date the data was last published, YYYY-MM-DD (from the data, not hard-coded)")
    latest_month: str | None = Field(None, description="Latest month of data the forecast uses, YYYY-MM")
    is_proxy_for_malaysia: bool = Field(False, description="True when the data is for another country standing in for Malaysia")


class QuarterInfo(BaseModel):
    """One quarter of data the model can be trained on."""

    quarter: str = Field(description="e.g. 2026-Q3")
    months: int = Field(description="Months of data in it so far (3 once the quarter is complete)")
    first_month: str
    last_month: str
    has_outcome: bool = Field(description="False while its outcome is still unknown, so the model can't learn from it yet; leaving it out only moves where the forecast starts")


class Quarters(BaseModel):
    quarters: list[QuarterInfo] = Field(description="Oldest first")
    latest_quarter: str
    source: Literal["supabase", "csv"] = Field(description="Where the series are read from")
    refresh_enabled: bool = Field(description="True when POST /forecast/refresh is allowed")
    default_trained_rows: int | None = Field(None, description="Rows the 12-month model learns from with all the data")


class RetrainRequest(BaseModel):
    onet_code: str = Field(description="O*NET code of the job to forecast, e.g. 15-1252.00")
    excluded_quarters: list[str] = Field(default_factory=list, description="Quarters to leave out, e.g. ['2020-Q1', '2026-Q3']. Empty = use all the data")


class RetrainOut(BaseModel):
    """A job's forecast from a model retrained without some quarters."""

    excluded_quarters: list[str] = Field(description="The quarters left out, oldest first")
    forecast_from: str = Field(description="The month the forecast starts from, YYYY-MM: the latest month whose inputs are all kept")
    trained_rows: int = Field(description="Rows the 12-month model learned from")
    default_trained_rows: int | None = Field(None, description="The same with all the data, when known")
    holdout_origins: list[str] = Field(description="First and last month used to test the 12-month model")
    model_status: Literal["indicative", "validated"]
    source: Literal["supabase", "csv"]
    seconds: float = Field(description="How long the retrain took")
    cached: bool = Field(description="True if it had been done already, so this answer was instant")
    forecasts: list[JobForecast] = Field(description="The job's three scenarios, like GET /forecast/jobs")
