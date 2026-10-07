"""
UVA S&T PI / Co-PI roster builder
---------------------------------
Pulls every ACTIVE award to the University of Virginia (Charlottesville) from:
  - NIH RePORTER API  (api.reporter.nih.gov)
  - NSF Award API     (api.nsf.gov)
Extracts every PI and Co-PI, drops postdoc/fellowship awards, de-duplicates
people across awards and agencies, and writes UVA_PI_roster.xlsx.

Run:   pip install requests pandas openpyxl
       python uva_pi_list.py
"""
import re
import time
from datetime import date

import pandas as pd
import requests

TODAY = date.today()
OUTFILE = "UVA_PI_roster.xlsx"

# Postdoc / trainee award types to exclude
NIH_POSTDOC_CODES = re.compile(r"^(F\d\d|K99|R00)$")  # F = NRSA fellowships, K99/R00 = Pathway to Independence
NSF_POSTDOC_PROGRAMS = re.compile(r"POSTDOC|FELLOWSHIP|GRFP|ASCEND", re.I)
# NSF directorates that are not science/technology (kept in the file, flagged)
NSF_NON_ST_DIRS = {"SBE", "EDU", "EHR"}


# ---------------------------------------------------------------- helpers
def norm_name(first, last):
    """Key for de-duplication: lowercase last name + first given name."""
    first = re.sub(r"[^a-z ]", "", (first or "").lower()).split()
    last = re.sub(r"[^a-z\- ]", "", (last or "").lower()).strip()
    return f"{last}|{first[0] if first else ''}"


def get_json(method, url, **kw):
    for attempt in range(5):
        try:
            r = requests.request(method, url, timeout=60, **kw)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == 4:
                raise
            time.sleep(3 * (attempt + 1))


# ---------------------------------------------------------------- NIH
def fetch_nih():
    url = "https://api.reporter.nih.gov/v2/projects/search"
    rows, offset, limit = [], 0, 500
    while True:
        body = {
            "criteria": {
                "org_names": ["UNIVERSITY OF VIRGINIA"],
                "include_active_projects": True,
                "fiscal_years": [TODAY.year - 1, TODAY.year],
            },
            "offset": offset,
            "limit": limit,
        }
        data = get_json("POST", url, json=body)
        results = data.get("results", [])
        rows.extend(results)
        total = data.get("meta", {}).get("total", 0)
        print(f"  NIH: {len(rows)}/{total}")
        offset += limit
        if not results or offset >= total or offset > 14500:
            break
        time.sleep(1)
    return rows


def parse_nih(projects):
    awards, people = {}, []
    for p in projects:
        org = p.get("organization") or {}
        if not (org.get("org_name") or "").upper().startswith("UNIVERSITY OF VIRGINIA"):
            continue
        if (org.get("org_city") or "").upper() != "CHARLOTTESVILLE":
            continue
        end = (p.get("project_end_date") or "")[:10]
        if end and end < TODAY.isoformat():
            continue
        code = p.get("activity_code") or ""
        if NIH_POSTDOC_CODES.match(code):
            continue
        core = p.get("core_project_num") or p.get("project_num")
        if core in awards:
            continue
        awards[core] = {
            "Source": "NIH", "Award ID": core, "Activity code": code,
            "Institute": (p.get("agency_ic_admin") or {}).get("abbreviation"),
            "Title": p.get("project_title"), "Dept": org.get("dept_type"),
            "End date": end,
        }
        pis = p.get("principal_investigators") or []
        for pi in pis:
            people.append({
                "key": norm_name(pi.get("first_name"), pi.get("last_name")),
                "First": (pi.get("first_name") or "").title(),
                "Last": (pi.get("last_name") or "").title(),
                "Email": None,
                "Role": "Contact PI" if pi.get("is_contact_pi") else ("PI" if len(pis) == 1 else "Multi-PI"),
                "Source": "NIH", "Award ID": core, "Field": org.get("dept_type"),
                "S&T": True,
            })
    return list(awards.values()), people


# ---------------------------------------------------------------- NSF
NSF_FIELDS = ["id", "title", "piFirstName", "piLastName", "piEmail", "coPDPI",
              "startDate", "expDate", "awardeeName", "awardeeCity",
              "fundProgramName", "dirAbbr", "divAbbr"]


def fetch_nsf():
    url = "https://api.nsf.gov/services/v1/awards.json"
    fields = list(NSF_FIELDS)
    rows, offset = [], 1
    while True:
        params = {
            "awardeeName": "University of Virginia",
            "expDateStart": TODAY.strftime("%m/%d/%Y"),
            "printFields": ",".join(fields),
            "offset": offset,
            "rpp": 25,
        }
        try:
            data = get_json("GET", url, params=params)
        except requests.HTTPError:
            if "dirAbbr" in fields:  # fall back if these fields aren't supported
                fields = [f for f in fields if f not in ("dirAbbr", "divAbbr")]
                continue
            raise
        batch = (data.get("response") or {}).get("award", [])
        rows.extend(batch)
        if offset % 250 == 1:
            print(f"  NSF: {len(rows)}")
        if len(batch) < 25:
            break
        offset += 25
        time.sleep(0.5)
    print(f"  NSF: {len(rows)} total")
    return rows


def parse_nsf(awards_raw):
    awards, people = [], []
    for a in awards_raw:
        if (a.get("awardeeCity") or "").upper() != "CHARLOTTESVILLE":
            continue
        prog = a.get("fundProgramName") or ""
        if NSF_POSTDOC_PROGRAMS.search(prog):
            continue
        d = a.get("dirAbbr")
        st = d not in NSF_NON_ST_DIRS
        awards.append({
            "Source": "NSF", "Award ID": a.get("id"), "Activity code": None,
            "Institute": d, "Title": a.get("title"), "Dept": prog,
            "End date": a.get("expDate"),
        })
        people.append({
            "key": norm_name(a.get("piFirstName"), a.get("piLastName")),
            "First": a.get("piFirstName"), "Last": a.get("piLastName"),
            "Email": a.get("piEmail"), "Role": "PI", "Source": "NSF",
            "Award ID": a.get("id"), "Field": prog, "S&T": st,
        })
        for co in a.get("coPDPI") or []:
            name = co.split("~")[0].strip()
            parts = name.split()
            if len(parts) < 2:
                continue
            people.append({
                "key": norm_name(parts[0], parts[-1]),
                "First": parts[0], "Last": parts[-1], "Email": None,
                "Role": "Co-PI", "Source": "NSF", "Award ID": a.get("id"),
                "Field": prog, "S&T": st,
            })
    return awards, people


# ---------------------------------------------------------------- roster
def build_roster(people):
    df = pd.DataFrame(people)
    if df.empty:
        return df, df
    roster = (
        df.groupby("key")
        .agg(**{
            "First": ("First", "first"),
            "Last": ("Last", "first"),
            "Email": ("Email", lambda s: next((x for x in s if isinstance(x, str) and x), None)),
            "Roles": ("Role", lambda s: ", ".join(sorted(set(s)))),
            "Agencies": ("Source", lambda s: ", ".join(sorted(set(s)))),
            "Active awards": ("Award ID", "nunique"),
            "Award IDs": ("Award ID", lambda s: "; ".join(sorted(set(map(str, s))))),
            "Fields": ("Field", lambda s: "; ".join(sorted({x for x in s if x}))),
            "S&T": ("S&T", "max"),
        })
        .reset_index(drop=True)
        .sort_values(["Last", "First"])
    )
    roster["S&T"] = roster["S&T"].map({True: "Yes", False: "Review"})
    return roster, df


def write_excel(roster, awards):
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    with pd.ExcelWriter(OUTFILE, engine="openpyxl") as xw:
        summary = pd.DataFrame({"Metric": [
            "Unique PIs / Co-PIs (all)",
            "Unique PIs / Co-PIs flagged S&T",
            "Active awards counted",
            "Data pulled on",
        ]})
        summary.to_excel(xw, sheet_name="Summary", index=False)
        roster.to_excel(xw, sheet_name="Unique PIs", index=False)
        pd.DataFrame(awards).to_excel(xw, sheet_name="Awards", index=False)
        notes = pd.DataFrame({"Notes": [
            "Sources: NIH RePORTER API and NSF Award API, active awards to University of Virginia, Charlottesville.",
            "PIs include NIH contact PIs and multiple PIs, and NSF PIs and Co-PIs.",
            "Excluded: NIH F-series fellowships and K99/R00 (postdoc), NSF fellowship/postdoc/GRFP programs.",
            "S&T = 'Review' when a person's only NSF awards come from SBE or EDU directorates.",
            "De-duplication matches last name + first given name; check near-duplicates and same-name collisions.",
            "Not covered: DoD, DOE, NASA, USDA, industry and foundation awards (no public PI-level API).",
        ]})
        notes.to_excel(xw, sheet_name="Notes", index=False)

        ws = xw.sheets["Summary"]
        n = len(roster) + 1
        ws["B1"] = "Value"
        ws["B2"] = f"=COUNTA('Unique PIs'!A2:A{n})"
        sc = get_column_letter(list(roster.columns).index("S&T") + 1)
        ws["B3"] = f"=COUNTIF('Unique PIs'!{sc}2:{sc}{n},\"Yes\")"
        ws["B4"] = f"=COUNTA(Awards!B2:B{len(awards) + 1})"
        ws["B5"] = TODAY.isoformat()

        for sheet in xw.sheets.values():
            for row in sheet.iter_rows():
                for c in row:
                    c.font = Font(name="Arial", bold=(c.row == 1))
            for col in sheet.columns:
                width = max(len(str(c.value or "")) for c in col[:200])
                sheet.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 60)
            sheet.freeze_panes = "A2"


def main():
    print("Pulling NIH...")
    nih_awards, nih_people = parse_nih(fetch_nih())
    print("Pulling NSF...")
    nsf_awards, nsf_people = parse_nsf(fetch_nsf())
    roster, _ = build_roster(nih_people + nsf_people)
    write_excel(roster, nih_awards + nsf_awards)
    st = (roster["S&T"] == "Yes").sum() if len(roster) else 0
    print(f"\nDone: {len(roster)} unique PIs/Co-PIs ({st} S&T) across "
          f"{len(nih_awards) + len(nsf_awards)} active awards -> {OUTFILE}")


if __name__ == "__main__":
    main()
