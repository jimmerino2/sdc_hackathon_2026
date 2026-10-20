"""Helpers for reading the O*NET text database (tab-separated .txt files)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def find_onet_file(onet_dir: Path, name: str) -> Path:
    """Find e.g. 'Occupation Data.txt' anywhere under onet_dir (the zip unpacks into a subfolder)."""
    norm = lambda s: s.lower().replace("_", " ").replace("-", " ").strip()
    hits = [p for p in onet_dir.rglob("*") if norm(p.stem) == norm(name) and p.suffix.lower() in {".txt", ".csv"}]
    if not hits:
        raise FileNotFoundError(f"'{name}' not found under {onet_dir}")
    return hits[0]


def read_onet_table(onet_dir: Path, name: str) -> pd.DataFrame:
    p = find_onet_file(onet_dir, name)
    sep = "\t" if p.suffix.lower() == ".txt" else ","
    return pd.read_csv(p, sep=sep, dtype=str, encoding="utf-8", encoding_errors="replace")
