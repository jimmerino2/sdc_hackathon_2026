"""One module per forecast target. Each exposes SPEC, which tells the shared engine how to load, cut and score it.

  skill_demand          ai_mention_share       Indeed: % of job ads mentioning AI, country x month
  business_adoption     btos_ai_use_rate       Census BTOS: % of firms using AI, sector x fortnight, per wording
  occupation_adoption   worker_genai_use_rate  RPS: % of workers using GenAI, SOC major group x quarter
  capability_metr       frontier_time_horizon  METR 50% time horizon of the best model, per suite version x month
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from ..features import PERCENT, Scale


@dataclass(frozen=True)
class TargetSpec:
    id: str  # key of contracts.TARGETS
    horizons: tuple[int, ...]  # in periods
    period_unit: str  # month | fortnight | quarter
    unit_kind: str  # what a unit is: country, sector x wording, SOC major group
    trend_steps: int  # window of the `trend` column used by drift-type baselines
    feature_groups: dict[str, list[str]]
    group_source: dict[str, str]  # feature group -> source id (contracts.check_sources)
    load: Callable[[], dict]  # -> data used by the functions below
    origins: Callable[[dict], list]  # -> list[Snapshot], strictly increasing in time
    truth: Callable[[dict], pd.Series]  # (period, unit) -> latest percent
    panel: Callable  # Snapshot -> features per period x unit
    health: Callable[[dict, pd.Timestamp], dict]  # source id -> registry.health(...)
    ingest: Callable[[bool], None]  # (pull) -> refresh this target's point-in-time tables
    label: Callable[[object], str] = str  # period -> text for outputs
    segment: Callable[[str], str] = lambda unit: ""  # measurement segment of a unit (e.g. BTOS wording)
    min_selection_origins: int = 12
    min_holdout: int = 6
    holdout_share: float = 0.2
    history_warning: str = ""  # added to every forecast row when the evidence is thin by design
    scale: Scale = PERCENT  # modelling scale; errors are reported on the value scale in scale.unit
    value_unit: str = "percent"  # unit of forecast values
    regimes: bool = False  # also report P(acceleration / stable / slowdown) per forecast (capability targets)
    errors_on_model_scale: bool = False  # score errors on the modelling scale (e.g. doublings for exponential growth)

    @property
    def error_unit(self) -> str:
        return self.scale.unit if self.errors_on_model_scale or self.scale.unit == "pp" else self.value_unit

    @property
    def features(self) -> list[str]:
        return [f for g in self.feature_groups.values() for f in g]


def all_specs() -> dict[str, TargetSpec]:
    from . import business_adoption, capability_metr, occupation_adoption, skill_demand
    return {m.SPEC.id: m.SPEC for m in (skill_demand, business_adoption, occupation_adoption, capability_metr)}
