# Phase 8 — Data Management & Deployment

**Status:** ✅ Complete — sample data provided; import is a manual Data Import Wizard walkthrough (it's a Setup wizard, not something scriptable from outside the org); deployment strategy documented (and already what this project has been using since Phase 3).

**Goal:** get realistic test data into the org, and be explicit about how this project deploys.

## Sample data

Two ready-to-import CSVs live in `data/`:

- **`data/sample-trainers.csv`** — 4 trainers (Emily Davis, David Chen, John Smith, Maria Lopez) covering 4 of the `Specialty__c` picklist values, so the booking UI's trainer variety is visible immediately.
- **`data/sample-classes.csv`** — 4 classes, each linked to one of those trainers by name, with near-future dates so they show up in the booking form right away (`ClassBookingController.getUpcomingClasses` only returns classes starting after "now").

> ⚠️ **Check the dates before importing.** The sample dates are set in October 2026. If you're importing this well after that, or want the classes to always look "a week out" regardless of when you deploy, bump the dates in `sample-classes.csv` first — Data Import Wizard won't do that for you.
>
> The date format (`10/15/2026 9:00 AM`) assumes a US-style locale. If your org's locale (set in Phase 2) uses day/month order or 24-hour time, adjust the CSV to match, or the Wizard will misread the dates.

## Importing (Data Import Wizard — manual, by design)

Data Import Wizard is a Setup-UI wizard with no metadata or CLI equivalent, so — like Phase 2's org settings — this stays a manual walkthrough rather than something I can package as a deploy step:

1. **Import Trainers first** (Classes reference them by name, so order matters):
   - [ ] Setup → Data Import Wizard → Launch Wizard.
   - [ ] What kind of data: **Custom objects** → **Trainer**.
   - [ ] What to do: **Add new records**.
   - [ ] Upload `data/sample-trainers.csv`.
   - [ ] Map fields (should auto-map: Trainer Name, Specialty, Years of Experience, Biography) → Next → Start Import.
   - [ ] Setup → Bulk Data Load Jobs → confirm 4 records created, 0 failed.

2. **Import Classes second:**
   - [ ] Setup → Data Import Wizard → Launch Wizard.
   - [ ] What kind of data: **Custom objects** → **Class**.
   - [ ] What to do: **Add new records**.
   - [ ] Upload `data/sample-classes.csv`.
   - [ ] When prompted "Which Trainer field in your file do you want to match against the Trainer lookup field?" → choose **Trainer Name**.
   - [ ] Map the remaining fields (Class Name, Start Date/Time, Capacity, Description) → Next → Start Import.
   - [ ] Setup → Bulk Data Load Jobs → confirm 4 records created, 0 failed. If any fail, it's almost always the date format (see the warning above) — check the job's error detail and re-upload just the failed row.

3. **Verify end-to-end:** open the public booking flow (Phase 4) and confirm all 4 classes appear with the right trainer names and seat counts.

## Not implemented (with reasoning, not silently skipped)

- **Data Loader & Duplicate Rules** — Data Import Wizard is sufficient at this data volume (a handful of records for testing/demo). Data Loader is the right tool once you're moving thousands of records or need scheduled/repeatable imports; Duplicate Rules would complement the Contact-matching-by-email logic already built into the booking flow (Phase 4) by catching duplicates created through *other* entry points (e.g. someone manually creating a Contact in Setup). Worth adding once there's more than one way for Contacts to enter the system.
- **Data Export & Backup** — genuinely a production concern (scheduled exports, backup retention), not a meaningful step for a Developer Edition project. Flagged here so it isn't forgotten if this ever moves toward a real rollout.

## Deployment & packaging strategy

This is worth being concrete about, because **this project already follows the recommended approach** — it isn't just theoretical:

- **What we've actually been doing (Phases 3, 4, 6):** SFDX source format (`force-app/`) + Salesforce CLI (`sf project deploy start`). This *is* the modern equivalent of Change Sets, and it's what lets this whole project live in a folder/zip/git repo instead of being trapped in one org. Every phase's delta zip you've received has been exactly this.
- **Change Sets** — the point-and-click alternative to SFDX, useful if you ever need to move metadata between two orgs you both have access to (e.g. a sandbox → production) without a CLI. Not used here since we've had CLI-deployable metadata since Phase 3, but worth knowing about if you ever hand this off to someone who prefers clicking over the command line.
- **Packaging for distribution:**
  - **Unmanaged Package** — the right choice if you hand this whole project to a client to run in their own org: they get fully editable, ownable components.
  - **Managed Package** — only relevant if this were ever going to be distributed commercially via AppExchange, with your org as the package's controlling namespace. Not applicable to a single-studio CRM like this one.
- **Recommendation for this project specifically:** keep using SFDX/CLI deploys as it's grown through Phases 3–6 (and will keep growing through 9). If this ever needs to go to a second org (staging → production, or client handoff), the existing `force-app/` + `manifest/package.xml` is already everything a Change Set or an Unmanaged Package would need — no rework required.

**Next:** Phase 9 (Reporting, Dashboards & Security Review) — reports, a dashboard, and a security/sharing re-check.
