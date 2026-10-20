"""Build data/processed/my_vacancies.csv and onet_to_my_group.csv from the DOSM
Job Market Insights workbook (data/raw/dosm_jmi/jmi_q2_2026.xlsx,
downloaded automatically from DOSM if it is not there).

Reshapes the wide Excel report (annual, quarterly and monthly column blocks;
Table 1 = economic activity, Table 2 = major occupation group) into one tidy table.
"""
import csv
import re
import subprocess
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "dosm_jmi" / "jmi_q2_2026.xlsx"
DOWNLOAD_URL = "https://www.dosm.gov.my/portal-main/release-document-log?release_document_id=20742"
OUT = ROOT / "data" / "processed"
SOURCE = "DOSM Big Data Analytics: Job Market Insights (online job vacancies), Q2 2026 release"
SOURCE_URL = "https://www.dosm.gov.my/portal-main/release-content/big-data-analytics-job-market-insights-q22026"
AS_OF = "2026-08-18"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def column_periods(year_row, label_row):
    """Map each column index to (freq, period) using the year and label header rows."""
    cols, year = {}, None
    for j, label in enumerate(label_row):
        if j < 2 or label is None and year_row[j] is None:
            continue
        if year_row[j] is not None:
            year = int(year_row[j])
        if label is None:  # annual block: the year row is the label
            cols[j] = ("year", f"{year}")
        elif label in MONTHS:
            cols[j] = ("month", f"{year}-{MONTHS.index(label) + 1:02d}")
        elif re.fullmatch(r"Q[1-4]", str(label)):
            cols[j] = ("quarter", f"{year}-{label}")
    return cols


def main():
    if not SRC.exists():
        SRC.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {DOWNLOAD_URL}")
        # curl, not urllib: DOSM's certificate chain fails Python's verification but works with the OS store
        subprocess.run(["curl", "-fsSL", "-o", str(SRC), DOWNLOAD_URL], check=True)  # follows the redirect to the .xlsx
    ws = openpyxl.load_workbook(SRC, read_only=True, data_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    tables = [(i, "industry" if "Economic Activity" in r[1] else "occupation")
              for i, r in enumerate(rows) if r[1] and str(r[1]).startswith("Table")]
    out = []
    for start, group_type in tables:
        year_row, label_row = rows[start + 2], rows[start + 3]
        cols = column_periods(year_row, label_row)
        for r in rows[start + 4:]:
            name = r[1]
            if name is None or str(name).startswith("Source"):
                break
            for j, (freq, period) in cols.items():
                v = r[j] if j < len(r) else None
                if v is None:
                    continue
                if isinstance(v, str):  # DOSM writes "-" for nil
                    v = 0 if v.strip() in ("-", "") else float(v.replace(",", ""))
                out.append({"freq": freq, "period": period, "group_type": group_type,
                            "group": "Total" if name == "Jumlah" else str(name).strip(),
                            "vacancies": int(v)})
    # the latest year/quarter is only complete up to the last published month
    last_month = max(o["period"] for o in out if o["freq"] == "month")
    last_q = max(o["period"] for o in out if o["freq"] == "quarter" and o["vacancies"] > 0)
    out = [o for o in out if not (o["freq"] == "quarter" and o["period"] > last_q)]  # unpublished quarters are blank "-"
    last_year = last_month[:4]
    for o in out:
        o["is_partial"] = (o["freq"] == "year" and o["period"] == last_year and last_month[5:] != "12") or \
                          (o["freq"] == "quarter" and o["period"] == last_q and int(last_month[5:]) % 3 != 0)
        o["source"], o["source_url"], o["as_of_date"] = SOURCE, SOURCE_URL, AS_OF
    out.sort(key=lambda o: (o["group_type"], o["group"], o["freq"], o["period"]))
    cols = ["freq", "period", "group_type", "group", "vacancies", "is_partial", "source", "source_url", "as_of_date"]
    with open(OUT / "my_vacancies.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(out)

    # validate and write the job -> occupation-group map
    groups = {o["group"] for o in out if o["group_type"] == "occupation"}
    roles = list(csv.DictReader(open(OUT / "onet_roles.csv", encoding="utf-8")))
    src = {r["onet_code"]: r for r in csv.DictReader(open(Path(__file__).parent / "jmi_group_map_source.csv", encoding="utf-8"))}
    assert set(src) == {r["onet_code"] for r in roles}, "map must cover exactly the jobs in onet_roles.csv"
    bad = {r["my_occupation_group"] for r in src.values()} - groups
    assert not bad, f"unknown occupation groups: {bad}"
    with open(OUT / "onet_to_my_group.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["onet_code", "title", "my_occupation_group", "rationale"])
        for r in roles:
            s = src[r["onet_code"]]
            w.writerow([r["onet_code"], r["title"], s["my_occupation_group"], s["rationale"]])
    print(f"my_vacancies.csv: {len(out)} rows; onet_to_my_group.csv: {len(roles)} rows; last month {last_month}")


if __name__ == "__main__":
    main()
