# UVA PI / Co-PI Roster — Migration to a Standard Claude Chat

Prepared 2026-10-09. This hands off an in-progress project from Claude Code so verification can continue in a normal Claude chat.

## How to use this

1. Open a new Claude chat with **web search turned on**.
2. Upload three files from the `handoff/` folder:
   - this document (`MIGRATION.md`)
   - `possibles_to_verify.csv`, the 209 people still to resolve
   - `master_list.csv`, all 647 people, for reference
3. Paste the starter prompt from the end of this document.
4. Work in batches of about 20 people per message. When you finish a session, ask Claude for a CSV of updated rows.

## What the project is

We built a list of every PI and Co-PI on an active NIH or NSF award to the University of Virginia (Charlottesville). Then we checked whether each person is currently at UVA.

- **Sources:**
  - NIH RePORTER API: contact PIs and multiple PIs (Multi-PIs).
  - NSF Award API: PIs and Co-PIs.
  - Data pulled 2026-10-07.
- **Excluded:**
  - NIH F-series fellowships and K99/R00 awards.
  - NSF postdoc, fellowship and GRFP programs.
  - NSF Co-PIs marked "(Former)".
- **De-duplication:** people are matched on last name plus first given name. External collaborators are kept separate, so they never merge with a UVA person of the same name.
- **Roles:** Contact PI and Multi-PI are NIH roles; PI and Co-PI are NSF roles.

## Current status

| Status | Count | Meaning |
|---|---:|---|
| Confirmed | 361 | A current UVA profile, or UVA news from 2025–2026, names them, and nothing shows they left. |
| Possible | 209 | Unresolved: only pre-2025 UVA evidence, an ambiguous or common name, initials only, or nothing found. |
| Negative | 77 | Now at another institution, retired or emeritus, or an external collaborator. |
| **Total** | **647** | |

**Breakdown of the 77 Negatives:**
- **46 elsewhere, confirmed by search:** almost all are NIH Multi-PI co-leads based at another institution.
- **27 external collaborators:** NSF Co-PIs whose only email is at another institution.
- **4 retired or emeritus:** Kuhn, Laubach, Pace and Soffa.

## Verification method and rules

Each person got 1–2 web searches, for example `"First Last" University of Virginia`, plus a field word if needed. Direct access to virginia.edu was blocked in the old environment, so the evidence comes from search results. A standard chat may be able to open UVA pages directly, which should make checks stronger.

**Classification rules (keep these consistent):**
- **Confirmed:** a current UVA page (virginia.edu, med.virginia.edu, engineering.virginia.edu, uvahealth.com) or 2025–2026 UVA news or ORCID shows them at UVA, with no evidence they left. Don't confirm on a name match alone if the field doesn't fit.
- **Negative:** a source shows they're now mainly at another institution, retired, emeritus or deceased. **Never mark someone Negative from memory alone.** Without a source, they stay Possible.
- **Possible:** everything else.

**Judgment calls already made (the user can override these):**
- **Emeritus or retired faculty:** currently Negative. If emeritus people who still hold active grants should count as UVA, switch Kuhn, Laubach, Pace and Soffa to Confirmed.
- **Ken Ono:** Possible. He's on extended leave from UVA and working at Axiom Math since 2025.
- **Jane von Gaudecker:** Possible. A UVA Nursing page lists her, but Indiana University news from Sept–Oct 2025 still places her at IU.
- **Sasanka Ramanadham:** Possible. A claim that he's at the University of Alabama at Birmingham was never confirmed by a source.

**Weak Confirmeds, worth spot-checking:**
- **Matched through email only:** Preston → P. Thomas Fletcher; Kento → Kent Yagi; Roberto → R. Ariel Gomez.
- **Confirmed only from third-party payroll or course sites:** Gates, Forman, Timko, Vucelja, Lin Zhou, Whittaker.
- **Postdocs, who move often:** Bhowmick and Bonfand-Caldeira.

## What's left: the 209 Possibles

`possibles_to_verify.csv` is sorted into three groups, easiest first:

| Group | Count | What it is | Suggested search |
|---|---:|---|---|
| A: UVA email on grant | 63 | The NSF grant lists a virginia.edu email, so they're probably current. | `"First Last" UVA <department>`, or the email ID. |
| B: Other | 99 | Mostly NIH Contact PIs with only older UVA evidence, or none found. | Add a field word: `"First Last" UVA School of Medicine <specialty>`. |
| C: NIH Multi-PI only | 47 | Co-leads on UVA grants and often at other institutions, so they're probably Negative. | `"First Last" professor` to find where they are now. |

The `Evidence` column records what earlier searches found. Use it so the same dead ends aren't searched again.

## Files

| File | Contents |
|---|---|
| `master_list.csv` | All 647 people. Columns: #, Last, First, Role, Agency, Active awards, Email, Verification, Current affiliation, Evidence, Source. |
| `possibles_to_verify.csv` | The 209 Possibles, with a Group column added. |
| `UVA_PI_master_list.xlsx` | The formatted workbook (same data as `master_list.csv`) with color-coded status and a Notes tab. It lives in the repo root and isn't needed for the chat. |

All files are on GitHub in `windowdarkly/uva-pi`, branch `claude/uva-pi-roster-builder-eyxlmy`.

## Caveats

- This is triage, not proof of employment. UVA's Office of Sponsored Programs or HR is the authoritative source.
- NIH doesn't publish PI emails, and some NIH Multi-PIs are listed by initials only.
- Coverage is NIH and NSF only. DoD, DOE, NASA, USDA, industry and foundation awards aren't included.

## Starter prompt (paste into the new chat)

```
I'm continuing a verification project. Read the attached MIGRATION.md first. It explains the
project, the classification rules and what's left.

Task: verify whether each person in possibles_to_verify.csv is currently employed at the
University of Virginia. Use web search. Work through Group A first, then B, then C, about 20
people per batch.

For each person, give: #, Last, First, new status (Confirmed / Negative / Possible),
current affiliation, one-sentence evidence and a source URL.

Rules:
- Confirmed needs a current UVA page or a 2025-2026 source.
- Never mark someone Negative without a source. If unsure, keep them Possible.
- Don't confirm on a name match alone if the field doesn't fit.

After each batch, show a running count of how many moved to Confirmed or Negative. When I say
"export", give me one CSV of all updated rows with the same columns as the input, so I can
merge it into the master list.

Start with the first 20 people in Group A.
```
