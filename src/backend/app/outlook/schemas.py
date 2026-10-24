from pydantic import BaseModel, Field


class HorizonStatus(BaseModel):
    h: int
    model: str = Field(description="Model served for this horizon")
    chosen_model: str | None = Field(None, description="Model selection chose; differs only if the baseline was retained")
    status: str = Field(description="validated | baseline | not_demonstrably_better | baseline_retained")
    holdout_mase_vs_naive: float | None = Field(None, description="Holdout error / naive's (below 1 = better)")
    run_id: str
    made_at: str


class TargetSummary(BaseModel):
    """One forecast target: what it measures, how far ahead, and how much to trust it."""

    target: str
    domain: str = Field(description="skill_demand | business_adoption | occupation_adoption | ai_capability")
    definition: str
    label_source: str
    unit_kind: str
    value_unit: str
    period_unit: str
    error_unit: str = Field(description="Unit of the reported errors (pp, or doublings for time horizons)")
    horizons: list[int] = Field(description="Horizons the model supports; only promoted ones are served")
    promoted: list[HorizonStatus]
    history_warning: str = ""
    source_health: dict
    has_regimes: bool = Field(description="Forecast rows carry P(acceleration / stable / slowdown)")


class OutlookRow(BaseModel):
    """One forecast: a unit (country, sector x wording, SOC group or METR suite) at one horizon."""

    target: str
    unit: str
    unit_kind: str
    segment: str | None = None
    h: int
    period_unit: str
    last_observed_period: str
    last_observed: float
    target_period: str
    value_unit: str
    forecast: float
    low: float | None = Field(None, description="10th percentile of the empirical range")
    high: float | None = Field(None, description="90th percentile of the empirical range")
    model: str
    chosen_model: str | None = None
    status: str
    holdout_mae: float | None = None
    naive_holdout_mae: float | None = None
    p_acceleration: float | None = None
    p_stable: float | None = None
    p_slowdown: float | None = None
    warnings: list[str] = Field(default_factory=list)
    data_as_of: str
    run_id: str
    made_at: str


class MethodScore(BaseModel):
    method: str = Field(description="naive = no change; drift, damped_drift, pooled_mean, local_trend, ridge, lightgbm")
    mae: float = Field(description="Average absolute error on the held-back test data, in error_unit")
    bias: float = Field(description="Average error (forecast minus outcome); negative = forecasts were too low")
    pct_off: float = Field(description="Average % the forecast was off from the actual value")
    accuracy_pct: float = Field(description="Average of smaller/larger of forecast and actual, in % (100 = exact)")
    avg_miss: float = Field(description="Average |forecast - actual| in the value's own unit (pp, or minutes)")
    n: int = Field(description="Number of held-back test forecasts")


class UnitAccuracy(BaseModel):
    """How each method did on the held-back test data for one unit (country, sector or group) at one horizon."""

    h: int
    unit: str
    served_model: str = Field(description="Method behind the published forecast")
    chosen_model: str | None = None
    error_unit: str
    n_test_points: int
    served_mae: float | None
    naive_mae: float | None
    beats_naive: bool | None = Field(None, description="Published method more accurate than no change for this unit; "
                                                       "null when the published method is no change itself")
    methods: list[MethodScore] = Field(description="Every method, this unit only, most accurate first")
    all_units: list[MethodScore] = Field(description="Every method, all units pooled (what the model was chosen on)")
    run_id: str
