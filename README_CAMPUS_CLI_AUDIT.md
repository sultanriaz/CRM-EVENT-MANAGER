# Campus Events Manager — CLI-only discovery audit

This package audits **CSC315 Assignment #2** against the uploaded Salesforce DX ZIP and, if authenticated, the live Salesforce org. It does **not** deploy metadata, insert/change/delete records, activate Flows, or overwrite the original Salesforce DX project.

## Prerequisites

- Windows PowerShell or another terminal
- `py -3 --version` (Python 3, standard library only)
- `sf --version` (Salesforce CLI)
- Internet connection and Salesforce authorization for the target org
- The downloaded `fitness-hub-crm.zip` and `campus_events_audit.py` in the same directory

If Salesforce CLI is missing, install with `npm install --global @salesforce/cli` and reopen the terminal.

## PowerShell — first check the org

```powershell
sf --version
sf org list
```

If your Salesforce username is not authenticated, initiate a browser-based authorization from CLI, then return to the terminal:

```powershell
sf org login web --alias campus-org --instance-url https://login.salesforce.com
sf org list
```

Use the authenticated alias `campus-org` or the actual username below. The old ZIP contains a historical `fitness-trial` alias; it does **not** guarantee your current PC is authenticated.

## Run the full read-only audit

From the folder containing the files:

```powershell
py -3 .\campus_events_audit.py --source .\fitness-hub-crm.zip --org 'superior7891_61lsg4rtgvkm@gmail.com'
```

OR use the existing alias:

```powershell
py -3 .\campus_events_audit.py --source .\fitness-hub-crm.zip --org campus-org
```

OR audit extracted project source:

```powershell
py -3 .\campus_events_audit.py --source 'C:\path\to\fitness-hub-crm' --org campus-org
```

To inspect only the local ZIP (no login):

```powershell
py -3 .\campus_events_audit.py --source .\fitness-hub-crm.zip --offline
```

## Outputs

The script creates a timestamped `campus_audit_YYYYMMDD_HHMMSS` folder containing:

- `summary.md` — readable coverage per assignment task and data thresholds
- `requirements.csv` — 81 individual requirements/evidence checkpoints: LOCAL `PRESENT/PARTIAL/MISSING`, ORG `PRESENT/NOT_LISTED/UNVERIFIED`, and flow activation state
- `audit.json` — structured results of all checks
- `org_metadata/*.json` — Salesforce Metadata API listing for objects, fields, validation rules, record types, layouts, permission sets, flows, reports, and dashboards
- `org_data/*.json` — SOQL counts for societies/events/registrations, distribution, capacity, attendance, permission assignments and Tooling API Flow active version lookup

Do not send the old project's `.sf` session folder or Salesforce login/auth output. Review org results for private records before sharing.

## Useful single-shot Salesforce CLI checks

```powershell
$org = 'superior7891_61lsg4rtgvkm@gmail.com'

# Live record counts
sf data query --target-org $org --query 'SELECT COUNT() FROM Society__c'
sf data query --target-org $org --query 'SELECT COUNT() FROM Event__c'
sf data query --target-org $org --query 'SELECT COUNT() FROM Registration__c'

# Database totals by event status and department
sf data query --target-org $org --query 'SELECT Status__c, COUNT(Id) Total FROM Event__c GROUP BY Status__c'
sf data query --target-org $org --query 'SELECT Student_Department__c, COUNT(Id) Total FROM Registration__c GROUP BY Student_Department__c'

# Org metadata existence
sf org list metadata --target-org $org --metadata-type CustomApplication
sf org list metadata --target-org $org --metadata-type Flow
sf org list metadata --target-org $org --metadata-type ValidationRule
sf org list metadata --target-org $org --metadata-type DuplicateRule
sf org list metadata --target-org $org --metadata-type Report --folder Campus_Events
sf org list metadata --target-org $org --metadata-type Dashboard --folder Campus_Events

# Tooling API: identify active and inactive flows
sf data query --target-org $org --use-tooling-api --query 'SELECT DeveloperName, ActiveVersionId, LatestVersionId FROM FlowDefinition'
```

## Interpretation and limitations

- Local presence does **not** prove deployment. A metadata item listed in the org does **not** prove correct logic or successful execution. Missing local source might already exist directly in the org.
- `NOT_LISTED` is not definitive if the API returns a filtered set or cannot enumerate a type/folder; inspect JSON errors and retrieve particular metadata to confirm.
- Assignment Task 5 describes **six actual flows** (the "Registration Before Save" flow is separate), despite grouping them into five subsections.
- Assignment Task 6 requires written answers. Validation-rule failures, Login As, report/dashboard behavior, and Flow Debug tests require deliberate testing and screenshot evidence in an appropriate sandbox/trial org. This audit does not generate screenshots or execute business-altering tests.
- Check user profiles and inherited permissions: permission sets add access; a Volunteer permission set does not automatically revoke access granted by a profile.

## Next round

Share `summary.md` and `requirements.csv`, plus any relevant failing `org_metadata` / `org_data` JSON. We can then patch only the genuinely missing or incomplete components from CLI, and repeat the audit after each deployment.
