# Community Fitness & Wellness Hub CRM

A Salesforce CRM for a multi-location fitness studio: online class booking, automated member communication, loyalty tracking, and management reporting.

## Status: All 10 phases complete (with 4 known gaps recorded honestly in Phase 10 — see below)

| Phase | Name | Status |
|---|---|---|
| 1 | Problem Understanding & Industry Analysis | ✅ Done |
| 2 | Org Setup & Configuration | ✅ Done (manual checklist) |
| 3 | Data Modeling & Relationships | ✅ Done (deployable metadata) |
| 4 | Process Automation | ✅ Done (flows, LWCs, email + a scoped Apex controller) |
| 5 | Apex Programming | ✅ Done (decision record — no additional Apex needed) |
| 6 | User Interface Development | ✅ Done (Lightning App + tabs deployed; home page/utility bar/record pages manual) |
| 7 | Integration & External Access | ✅ Done (roadmap record — payment gateway, SMS, calendar sync, all deferred with reasoning) |
| 8 | Data Management & Deployment | ✅ Done (sample data + Data Import Wizard walkthrough + deployment strategy) |
| 9 | Reporting, Dashboards & Security Review | ✅ Done (field-security hardening + Report/Dashboard walkthrough) |
| 10 | Final Presentation & Demo Day | ✅ Done (demo script, presentation summary, honest requirements check) |

**Before you call this finished:** Phase 10's traceability check found 2 real requirement gaps (no member-facing booking cancellation, no 24-hour reminder email) and 2 partial items (no member-facing loyalty view, dashboard doesn't include a literal attendance-rate KPI). None were silently dropped — `docs/phase-10-demo/README.md` has the full table and a prioritized list of the fastest ones to close.

## Repo layout

- `docs/phase-01-discovery/` — problem statement, requirements, stakeholder analysis, process maps, industry analysis, AppExchange notes.
- `docs/phase-02-org-setup/` — manual Setup checklist (company profile, business hours, fiscal year, users, roles, My Domain, email deliverability, Experience Cloud). Nothing here is deployable metadata — it's Setup-UI configuration, done by hand in the org.
- `docs/phase-03-data-model/` — data model overview (ERD, field list, relationships) and deploy instructions for the metadata below.
- `docs/phase-04-automation/` — booking/email/loyalty automation design, the UI-driven scope call on Apex, and post-deploy guest-access checklist.
- `docs/phase-05-apex-decision/` — why no further Apex was needed, and a concrete (unbuilt) sketch of the 3 future use cases that would justify it.
- `docs/phase-06-ui/` — the Lightning App/tabs delivered as metadata, plus a manual checklist for the Home Page, Utility Bar, and record page layout (and why those three stay manual).
- `docs/phase-07-integration-roadmap/` — payment gateway, SMS, and calendar-sync integration designs, all deliberately deferred, with reasoning.
- `docs/phase-08-data-deployment/` — Data Import Wizard walkthrough for `data/`'s sample CSVs, plus this project's deployment/packaging strategy.
- `docs/phase-09-reporting-security/` — field-level security finding (and its limits), Sharing Settings re-check, and the Custom Report Type / Report / Dashboard walkthrough.
- `docs/phase-10-demo/` — the honest requirements-traceability check (4 known gaps), a presentation summary, a demo script, and a publishing checklist.
- `data/` — sample Trainer/Class CSVs for populating a fresh org via Data Import Wizard.
- `force-app/main/default/` — the actual Salesforce metadata (SFDX source format): 5 custom objects + fields, 1 permission set (with explicit field-level grants), 1 sharing rule, 2 Apex classes, 2 Lightning Web Components, 3 Flows, 1 workflow email alert, 1 email template, 1 Lightning App, 5 custom tabs.
- `manifest/package.xml` — manifest listing everything currently deployable.
- `sfdx-project.json` — SFDX project definition.

## Where this stands

All 10 phases have a deliverable — see the gaps called out above and detailed in `docs/phase-10-demo/README.md` before treating this as launch-ready. If any of those get built later, they slot in as their own dated addition under `force-app/main/default/` and a new or updated `docs/` folder, following the same pattern every phase here has used.

## Deploying the project

Requires [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) and an authenticated org (Developer Edition, matching the reference build).

```bash
# Authenticate to your Developer org (opens a browser login)
sf org login web --alias fitness-hub-dev

# Deploy everything under force-app
sf project deploy start --source-dir force-app --target-org fitness-hub-dev

# ...or deploy from the manifest instead
sf project deploy start --manifest manifest/package.xml --target-org fitness-hub-dev
```

> **Before deploying:** complete the Phase 2 manual checklist first (`docs/phase-02-org-setup/README.md`). In particular, create the **Trainer / Staff** role — the Phase 3 sharing rule (`force-app/main/default/sharingRules/Class__c.sharingRules-meta.xml`) references its API name as `Trainer_Staff`. If your org generates a different API name for that role, update the sharing rule file before deploying, or that one component will fail while everything else succeeds.
>
> **After deploying Phase 4:** the booking flow isn't reachable by real members until it's exposed publicly (Flow distribution or an Experience Cloud page) and the Guest User profile is granted the right object access — see the checklist at the bottom of `docs/phase-04-automation/README.md`.

## Reference

Original reference build/documentation: `Phase1-10_All_Phases_.pdf` (all 10 phases, screenshots, Salesforce Developer Edition).
