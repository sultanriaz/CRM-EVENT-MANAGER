# Campus Events Manager — Unified CLI Patch

This patch contains the previously supplied UI workspace switcher **plus** Campus app UI, event layouts, data quality, dashboard and six Flow definitions.

- **Safety:** Everything is staged locally; live-org deployment never occurs without `--deploy`.
- **Default Flow status:** Draft. Do not activate until Salesforce Flow Debug + user permissions are verified.
- **Prior Fitness Hub components:** preserved; no deletion of historical data or original Fitness Flows.
- **Validation:** `--validate` submits a Salesforce deploy check; schema and org-dependent errors can still occur.
- **Evidence:** check local audit CSV, `sf` validation output and the screenshot checklist.

## Manual verification remaining

- Salesforce org login, license/profile availability, creation and assignment of 3 scenario users and their record ownership.
- Lightning app activation and correct Home and Event Record page assignments; page metadata alone doesn't guarantee assignment.
- `My Society's Events` currently uses owner-scope, not true membership / society ownership; a user-to-society relation must be defined to scope this exactly.
- Report formulas, dashboard filter on Society Category, running user and email template merger field compatibility require org metadata validation.
- Scheduled flow 11 PM uses org timezone. Verify Company Information timezone before activation.
- Field permissions for the Volunteer rely on the profile not giving additional edit capabilities.
- Full safety tests: Salesforce org's duplicate management settings, Contact CRUD, concurrent registration, email send, Chatter, flows.
- Seed `scripts/seed-campus.apex` only after checking sandbox (never automatic; it creates records).
- Provide 5 short answers plus UI / rules / role / Flow debug screenshots for coursework submission.
