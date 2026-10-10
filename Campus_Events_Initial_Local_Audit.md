# Campus Events Manager — Salesforce CLI Audit

- Run time (local clock): 2026-10-08T19:09:45+00:00
- Source: `fitness-hub-crm.zip` (ZIP)
- Org username: `superior7891_61lsg4rtgvkm@gmail.com`
- Live org reachable: **NO**
- Local metadata checks: **64 present / 4 partial / 13 missing** of **81** checks.
- IMPORTANT: File existence is NOT evidence of deployed functionality, configured permissions, activation, or successful tests.
- Metadata API listing proves a component is discoverable, NOT its correctness. `NOT_LISTED` can also mean folder/API mismatch; review raw errors.
- Flow activation is independently checked using Tooling API where available. ACTIVE still does not prove runtime correctness.

## Data seeding thresholds (Task 1)

| Record type | Live count | Required | Result |
|---|---:|---:|---|
| Societies | Unknown | 3 | NOT VERIFIED |
| Events | Unknown | 6 | NOT VERIFIED |
| Registrations | Unknown | 20 | NOT VERIFIED |

## Other live data / health findings

| Query | Count or status |
|---|---|
| All live queries | Skipped (offline) |

## Local / org coverage per assignment task

| Task | Local present | Local partial | Local missing | Listed in org |
|---|---:|---:|---:|---:|
| 1 | 32 | 1 | 1 | 0 |
| 2 | 10 | 2 | 2 | 0 |
| 3 | 15 | 0 | 2 | 0 |
| 4 | 4 | 1 | 1 | 0 |
| 5 | 3 | 0 | 6 | 0 |
| 6 | 0 | 0 | 1 | 0 |

## Priority gaps / partial work (LOCAL snapshot)

These are source-level findings. Check the ORG column before choosing fixes.
- **Task 1 / MISSING** — Event layout Details / Schedule / Capacity sections. Org: UNVERIFIED; activation: N/A. Must include Registrations related list with Student, Department and Attended columns; layout name may differ.
- **Task 1 / PARTIAL** — My Society's Events properly scoped. Org: UNVERIFIED; activation: N/A. Current owner-only Mine filter does not establish same-society filtering; check intended access model.
- **Task 2 / PARTIAL** — Contact First + Last + Phone matching rule. Org: UNVERIFIED; activation: N/A.
- **Task 2 / MISSING** — Contact duplicate rule blocks identical email. Org: UNVERIFIED; activation: N/A. Check actual rule name in org; matching rules alone do not block duplicates.
- **Task 2 / MISSING** — Contact duplicate rule warns name + phone. Org: UNVERIFIED; activation: N/A. Rule name may differ; needs allow-with-alert behavior.
- **Task 2 / PARTIAL** — Lightning registration email template. Org: UNVERIFIED; activation: N/A. Present template is legacy Aloha/text; inspect Lightning Email Template requirement and merge fields.
- **Task 3 / MISSING** — Academic Event dedicated layout. Org: UNVERIFIED; activation: N/A. Check profile record-type layout assignments; names can differ.
- **Task 3 / MISSING** — Recreational Event dedicated layout. Org: UNVERIFIED; activation: N/A. Check profile record-type layout assignments; names can differ.
- **Task 4 / PARTIAL** — Report Event_Attendance_Rate. Org: UNVERIFIED; activation: N/A.
- **Task 4 / MISSING** — Student Affairs Dashboard (gauge, donut, bar, table; filter). Org: UNVERIFIED; activation: N/A. Verify four correct component types, dashboard filter and running user; file/name may differ.
- **Task 5 / MISSING** — Flow Quick_Event_Registration. Org: UNVERIFIED; activation: UNVERIFIED. Need active flow, correct trigger/timing/logic, fault paths and debug evidence.
- **Task 5 / MISSING** — Flow Registration_After_Save. Org: UNVERIFIED; activation: UNVERIFIED. Need active flow, correct trigger/timing/logic, fault paths and debug evidence.
- **Task 5 / MISSING** — Flow Registration_Before_Save. Org: UNVERIFIED; activation: UNVERIFIED. Need active flow, correct trigger/timing/logic, fault paths and debug evidence.
- **Task 5 / MISSING** — Flow Daily_Event_Closer. Org: UNVERIFIED; activation: UNVERIFIED. Need active flow, correct trigger/timing/logic, fault paths and debug evidence.
- **Task 5 / MISSING** — Flow Calculate_Society_Stats. Org: UNVERIFIED; activation: UNVERIFIED. Need active flow, correct trigger/timing/logic, fault paths and debug evidence.
- **Task 5 / MISSING** — Flow Venue_Emergency_Handler. Org: UNVERIFIED; activation: UNVERIFIED. Need active flow, correct trigger/timing/logic, fault paths and debug evidence.
- **Task 6 / MISSING** — Written assignment answers and screenshot evidence. Org: UNVERIFIED; activation: N/A. Five short answers + navigation, rollup and security explanations + proof screenshots; filename is illustrative.

## Required live / behavioral checks (not inferred from files)

- Validate picklist dependencies and record-type restrictions; inspect required Event layouts and related-list columns.
- Create deliberate negative test records **only in a safe test org and only after permission** for all five validation rules; preserve screenshots of errors.
- Verify both duplicate-rule behaviors by trying same email and same full name + phone.
- Verify permissions using the three scenario users, object/FLS/record access, and Login As screenshots; permission sets alone may not restrict already-granted profile permissions.
- Confirm template type, alert recipient, flow activation, 11 PM timezone and daily scheduled behavior, platform event cancellation and Chatter post.
- Confirm dashboard four component types, running user, society-category filter, and all report result calculations.
- Test registrations against full/closed events and concurrent sign-ups (not just validation-rule existence).
- Prepare Task 6 short answers and all screenshot evidence for submission.

## What to send back for diagnosis

`summary.md`, `requirements.csv`, and the specific failing `org_metadata/*.json` and `org_data/*.json` files.
Review files first; do not share authorization tokens, passwords, or unnecessary personal contact/user data.
