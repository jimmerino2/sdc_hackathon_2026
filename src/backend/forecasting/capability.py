"""Epoch AI capability data as point-in-time vintages, for the AI-capability targets.

Epoch's Capabilities Index (ECI) is fitted jointly over all models and benchmarks and refitted with every update,
so a model's score today includes information from models released later. A backtest must use the scores as they
were published. Those come from Wayback Machine captures of https://epoch.ai/data/benchmark_data.zip: each capture
is one vintage, available from its capture time. That time is an upper bound on when Epoch published it, so using
it can only make a forecaster know less, never more.

Raw    data/raw/epoch/snapshots/<capture timestamp>/benchmark_data.zip   (+ "current" download, dated)
Output data/processed/forecasting/capability_vintages.csv   (columns in data/documentation/STRUCTURE.md section 12)

Usage:
    python -m forecasting.capability             # fetch new captures (the month's last) + current file, rebuild
    python -m forecasting.capability --no-pull
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from .vintages import OUT, ROOT

RAW = ROOT / "data" / "raw" / "epoch" / "snapshots"
FILE_URL = "https://epoch.ai/data/benchmark_data.zip"
CDX = "http://web.archive.org/cdx/search/cdx?url=epoch.ai/data/benchmark_data.zip&output=json&fl=timestamp,statuscode,digest"
CAPTURE = "http://web.archive.org/web/{}id_/https://epoch.ai/data/benchmark_data.zip"  # id_ = the raw file
GAP_S = 4  # be polite to the Wayback Machine
UA = {"User-Agent": "Mozilla/5.0 (sdc-hackathon-2026 research pipeline)"}


def _get(url: str, timeout: int = 120, headers: dict | None = None) -> bytes:
    """Body of `url`, gunzipped when the archive serves it gzip-encoded. Response headers go into `headers`."""
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        body = r.read()
        if headers is not None:
            headers.update(r.headers.items())
    return gzip.decompress(body) if body[:2] == bytes([0x1F, 0x8B]) else body


def _store(ts: str, body: bytes, headers: dict, source: str) -> None:
    """Keep the file and when it was available: Epoch's Last-Modified if the archive recorded it, else the capture
    time. Both are upper bounds on publication, so neither lets a backtest see a file early."""
    dst = RAW / ts / "benchmark_data.zip"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(body)
    lm = headers.get("x-archive-orig-last-modified") or headers.get("Last-Modified")
    meta = {"source": source, "retrieved_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "capture_time": pd.Timestamp(ts, tz="UTC").isoformat(), "last_modified": lm,
            "sha256": hashlib.sha256(body).hexdigest()}
    (dst.parent / "meta.json").write_text(json.dumps(meta, indent=2))


def captures() -> pd.DataFrame:
    rows = json.loads(_get(CDX))[1:]
    d = pd.DataFrame(rows, columns=["timestamp", "status", "digest"])
    d = d[d["status"] == "200"].drop_duplicates("digest")
    d["when"] = pd.to_datetime(d["timestamp"], format="%Y%m%d%H%M%S", utc=True)
    d["month"] = d["when"].dt.strftime("%Y-%m")
    return d.sort_values("when", ascending=False)  # per month, later captures are tried first


def pull() -> None:
    """Download missing monthly captures and today's file. A failure keeps what is already stored."""
    try:
        caps = captures()
    except OSError as e:
        print(f"warning: Wayback index unavailable ({e}); keeping stored captures")
        caps = pd.DataFrame(columns=["timestamp"])
    have = {p.parent.name[:6] for p in RAW.glob("*/benchmark_data.zip")}  # months already stored (YYYYMM)
    for month, group in caps.groupby("month", sort=True) if len(caps) else []:
        if month.replace("-", "") in have:
            continue
        for ts in group["timestamp"]:  # the month's last capture first; older ones if it is not a zip
            hdr: dict = {}
            try:
                body = _get(CAPTURE.format(ts), headers=hdr)
                zipfile.ZipFile(io.BytesIO(body))  # must be a readable zip, not an error page
            except (OSError, zipfile.BadZipFile) as e:
                print(f"warning: capture {ts} not usable ({e})")
                time.sleep(GAP_S)
                continue
            _store(ts, body, hdr, CAPTURE.format(ts))
            print(f"capture {ts}: {len(body):,} bytes, last modified {hdr.get('x-archive-orig-last-modified')}")
            time.sleep(GAP_S)
            break
    try:
        hdr = {}
        body = _get(FILE_URL, headers=hdr)
        zipfile.ZipFile(io.BytesIO(body))
        ts = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d%H%M%S")
        latest = sorted(RAW.glob("*/benchmark_data.zip"))
        if not latest or hashlib.sha256(latest[-1].read_bytes()).digest() != hashlib.sha256(body).digest():
            _store(ts, body, hdr, FILE_URL)
    except (OSError, zipfile.BadZipFile) as e:
        print(f"warning: current file not downloaded ({e})")


COLUMNS = ["vintage_id", "available_at", "availability_basis", "measure", "metr_version", "model", "release_date",
           "release_date_source", "value", "ci_low", "ci_high", "source_file", "zip_sha256"]


def _availability(snap: Path) -> tuple[pd.Timestamp, str]:
    """Epoch's Last-Modified when recorded and not after the capture; else the capture time."""
    cap = pd.Timestamp(snap.name, tz="UTC")
    meta = snap / "meta.json"
    if meta.exists():
        lm = json.loads(meta.read_text()).get("last_modified")
        if lm:
            t = pd.Timestamp(pd.to_datetime(lm, utc=True))
            if t <= cap:
                return t, "last_modified"
    return cap, "capture_time"


def _metr(z: zipfile.ZipFile) -> tuple[str, pd.DataFrame] | None:
    names = [n for n in z.namelist() if "metr" in n.lower() and n.endswith(".csv")]
    if not names:
        return None
    d = pd.read_csv(z.open(names[0]))
    out = pd.DataFrame({"model": d["Model version"], "value": d["Time horizon"], "ci_low": d.get("CI_low"),
                        "ci_high": d.get("CI_high"),
                        "release_date": pd.to_datetime(d["Release date"]) if "Release date" in d else pd.NaT,
                        # unlabelled rows are METR's original (v1.0) suite; v1.1 re-measured models from Mar 2026
                        "metr_version": d["METR version"].fillna("METR-Horizon-v1.0") if "METR version" in d
                        else "METR-Horizon-v1.0"})
    return names[0], out


def _eci(z: zipfile.ZipFile) -> tuple[str, pd.DataFrame] | None:
    names = [n for n in z.namelist() if n.endswith("eci_scores.csv")]
    if not names:
        return None
    d = pd.read_csv(z.open(names[0]))
    return names[0], pd.DataFrame({"model": d["Model"], "value": d["eci"], "ci_low": d["eci_ci_low"],
                                   "ci_high": d["eci_ci_high"], "release_date": pd.to_datetime(d["date"]),
                                   "metr_version": None})


def build() -> pd.DataFrame:
    parts = []
    for zp in sorted(RAW.glob("*/benchmark_data.zip")):
        when, basis = _availability(zp.parent)
        z = zipfile.ZipFile(zp)
        digest = hashlib.sha256(zp.read_bytes()).hexdigest()
        for measure, reader in (("metr_h50_minutes", _metr), ("eci", _eci)):
            got = reader(z)
            if got is None:
                continue
            name, d = got
            parts.append(d.assign(vintage_id=zp.parent.name, available_at=when, availability_basis=basis,
                                  measure=measure, source_file=name, zip_sha256=digest[:16]))
    d = pd.concat(parts, ignore_index=True)
    d["release_date_source"] = d["release_date"].notna().map({True: "file", False: None})
    # Early METR files have no release dates: a release date is public at release and says nothing about later
    # capability, so it is filled from any vintage that has it for the same model name (flagged "joined").
    known = d.dropna(subset=["release_date"]).groupby("model")["release_date"].first()
    miss = d["release_date"].isna()
    d.loc[miss, "release_date"] = d.loc[miss, "model"].map(known)
    d.loc[miss & d["release_date"].notna(), "release_date_source"] = "joined"
    dropped = d["release_date"].isna()
    if dropped.any():
        print(f"capability: {int(dropped.sum())} rows without a release date dropped "
              f"({sorted(d.loc[dropped, 'model'].unique())[:8]}...)")
    d = d[~dropped & d["value"].notna()]
    return d[COLUMNS].sort_values(["measure", "vintage_id", "model"]).reset_index(drop=True)


def validate(d: pd.DataFrame) -> None:
    if (d["value"] <= 0).any() and (d["measure"] == "metr_h50_minutes").any():
        if (d.loc[d["measure"] == "metr_h50_minutes", "value"] <= 0).any():
            raise ValueError("non-positive METR time horizon")
    if d.duplicated(["vintage_id", "measure", "metr_version", "model"]).any():
        raise ValueError("duplicate capability rows within a vintage")


def load() -> pd.DataFrame:
    d = pd.read_csv(OUT / "capability_vintages.csv", dtype={"vintage_id": str})
    d["available_at"] = pd.to_datetime(d["available_at"], utc=True, format="ISO8601")
    d["release_date"] = pd.to_datetime(d["release_date"])
    return d


def ingest(pull_first: bool) -> None:
    if pull_first:
        pull()
    d = build()
    validate(d)
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / ".capability_vintages.csv.tmp"
    d.to_csv(tmp, index=False)
    tmp.replace(OUT / "capability_vintages.csv")
    g = d.groupby("measure")["vintage_id"].agg(["nunique", "min", "max"])
    print(f"capability: {len(d):,} rows")
    print(g.to_string())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true")
    ingest(not ap.parse_args().no_pull)


if __name__ == "__main__":
    main()
