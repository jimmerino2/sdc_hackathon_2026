"""Local storage for the occupational forecasting domain. The one module that knows where files live.

Everything goes under data/occupational_forecasting/ (override with OCC_DATA_DIR, e.g. in tests):
  raw/          source downloads, gitignored (hn/, adzuna/, so_survey/, onet/)
  taxonomy/     occupations.json, curated_skills.csv, geo.json (hand-written inputs); skill_registry.json (built)
  normalized/   ads.csv.gz (one row per ad, no text), ads_text.csv.gz (text, gitignored), ad_skills.csv.gz
  datasets/     demand panel (counts per month x country x occupation x skill) and emerging-skill candidates
  adoption/     worker AI usage observations and employer-side indicators
  runs/<id>/    one model run: backtest, evaluation.json, forecast, model.json
  latest/       the run currently served (copied from runs/ when a run is promoted)
  manifest.json dataset version, latest observation, served run

A future database can replace this module: callers only use read_table / write_table / read_json / write_json.
Writes are atomic, and an empty table never replaces a non-empty one unless allow_empty=True, so a failed
update keeps the last good data.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]


def root() -> Path:
    return Path(os.environ.get("OCC_DATA_DIR") or REPO / "data" / "occupational_forecasting")


def path(*parts: str) -> Path:
    return root().joinpath(*parts)


class EmptyUpdate(RuntimeError):
    """Refused to replace existing data with an empty table."""


def _atomic(target: Path, write) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    os.close(fd)
    try:
        write(Path(tmp))
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def write_table(rel: str, df: pd.DataFrame, allow_empty: bool = False) -> Path:
    p = path(rel)
    if df.empty and not allow_empty and p.exists() and p.stat().st_size > 0:
        raise EmptyUpdate(f"refusing to replace {rel} with an empty table")
    comp = "gzip" if p.suffix == ".gz" else None
    # mtime=0 in the gzip header so identical data gives identical bytes (and a stable dataset hash)
    _atomic(p, lambda t: df.to_csv(t, index=False, compression={"method": "gzip", "mtime": 0} if comp else None))
    return p


def read_table(rel: str, **kw) -> pd.DataFrame:
    p = path(rel)
    if not p.exists():
        raise FileNotFoundError(f"{p} (run `python -m occupational.run` from src/backend)")
    try:
        return pd.read_csv(p, **kw)
    except pd.errors.EmptyDataError:  # an empty table written with no columns
        return pd.DataFrame()


def exists(rel: str) -> bool:
    return path(rel).exists()


def write_json(rel: str, obj) -> Path:
    p = path(rel)
    _atomic(p, lambda t: t.write_text(json.dumps(obj, indent=2, default=str, ensure_ascii=False), encoding="utf-8"))
    return p


def read_json(rel: str, default=None):
    p = path(rel)
    if not p.exists():
        if default is not None:
            return default
        raise FileNotFoundError(str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def file_hash(*rels: str) -> str:
    h = hashlib.sha256()
    for rel in rels:
        p = path(rel)
        h.update(p.read_bytes() if p.exists() else b"-")
    return h.hexdigest()[:12]
