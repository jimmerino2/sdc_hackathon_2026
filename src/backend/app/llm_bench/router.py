from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.llm_bench import service
from llm_bench import openrouter as OR, runner as R

router = APIRouter(prefix="/llm-bench", tags=["llm-bench"])


class BenchRequest(BaseModel):
    benchmark: Literal["skills", "capability"] = "skills"
    horizons: list[Literal[3, 6, 12]] = [3]
    n_series: int = Field(100, ge=1, le=1000)
    n_origins: int = Field(4, ge=1, le=12)
    cap_roles: list[Literal["holdout", "selection"]] = ["holdout"]
    modes: list[Literal["zero", "few", "zero_named", "few_named"]] = ["zero", "few"]
    model: str | None = None
    batch_size: int = Field(10, ge=1, le=50)
    max_spend_usd: float = Field(2.0, ge=0, le=10)
    few_shot_k: int = Field(4, ge=0, le=10)
    max_examples: int = Field(10, ge=0, le=30)
    max_requests: int = Field(0, ge=0)
    reasoning: Literal["off", "low", "default"] | None = None
    concurrency: int = Field(1, ge=1, le=16)
    dry_run: bool = False
    confirm: bool = False  # live runs only: the user has seen the estimate

    def run_config(self) -> R.RunConfig:
        return R.RunConfig(benchmark=self.benchmark, horizons=sorted(set(self.horizons)), n_series=self.n_series,
                           n_origins=self.n_origins, cap_roles=sorted(set(self.cap_roles)), modes=list(dict.fromkeys(self.modes)),
                           model=self.model or "", batch_size=self.batch_size, max_spend_usd=self.max_spend_usd,
                           few_shot_k=self.few_shot_k, max_examples=self.max_examples, dry_run=self.dry_run,
                           max_requests=self.max_requests, reasoning=self.reasoning or "", concurrency=self.concurrency)


def _guard(fn, *args):
    try:
        return fn(*args)
    except service.Busy as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (service.Refused, OR.ConfigError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"not found: {e}")


@router.get("/info")
def get_info():
    """Configured models and their listed prices, whether a key is set (never the key), benchmarks, modes."""
    return service.info()


@router.post("/estimate")
def post_estimate(body: BenchRequest):
    """Fixed sample, request count and cost estimate for a run. Sends nothing to the LLM."""
    return _guard(service.estimate, body.run_config())


@router.post("/runs")
def post_run(body: BenchRequest):
    """Start a run in the background. Live runs need confirm=true and OPENROUTER_BENCH_API_KEY."""
    return _guard(service.start, body.run_config(), body.confirm)


@router.get("/summary")
def get_summary(benchmark: Literal["skills", "capability"] = Query(...)):
    """Completed live LLM runs vs the existing model and "no change" on the same cases (primary, anonymous modes)."""
    return service.summary(benchmark)


@router.get("/runs")
def get_runs():
    return service.runs()


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    """Progress, spend and the comparison report (existing model, naive, each LLM mode on paired cases)."""
    return _guard(service.detail, run_id)


@router.get("/runs/{run_id}/cases")
def get_cases(run_id: str, mode: str | None = Query(None), status: str | None = Query(None, description="ok, invalid, missing, unparseable, request_failed, skipped_budget, not_attempted, or failed (= anything but ok)"),
              limit: int = Query(500, le=5000)):
    """Per case: existing model, naive, actual and each mode's LLM value with its status."""
    return _guard(service.cases, run_id, mode, status, limit)


@router.post("/runs/{run_id}/stop")
def post_stop(run_id: str):
    return service.stop(run_id)


@router.post("/runs/{run_id}/resume")
def post_resume(run_id: str, confirm: bool = Query(False)):
    return _guard(service.resume, run_id, confirm)
