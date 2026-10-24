"""O*NET 31.0 software skills and job titles: the reference taxonomy a skill is checked against ("covered by O*NET").
Downloaded once into raw/onet/ (a release does not change). Licence: CC BY 4.0, O*NET Resource Center."""
from __future__ import annotations

import urllib.request

from .. import store, taxonomy as T

SOURCE = "onet"
RELEASE = "31.0"
URL = "https://www.onetcenter.org/dl_files/database/db_31_0_csv/{name}"
FILES = ("software_skills.csv", "job_titles.csv")


def fetch(pull: bool = True) -> dict:
    missing = [f for f in FILES if not store.path("raw", "onet", f).exists()]
    failed = []
    if pull:
        for f in missing:
            try:
                with urllib.request.urlopen(URL.format(name=f), timeout=120) as r:
                    T.save_onet({f: r.read()})
            except Exception as e:
                failed.append(f"{f}: {str(e)[:80]}")
    have = [f for f in FILES if store.path("raw", "onet", f).exists()]
    return {"source": SOURCE, "release": RELEASE, "status": "ok" if len(have) == len(FILES) else "missing",
            "files": have, "failed": failed}
