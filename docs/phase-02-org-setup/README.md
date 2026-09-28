# Phase 2 — Org Setup & Configuration

**Status:** ✅ Complete (manual Setup-UI configuration — nothing here deploys as metadata).

**Goal:** Establish the foundational environment and security model before building the data model.

Almost everything in this phase is a Salesforce **Setup UI** action rather than something safely expressible as deployable metadata (company info, business hours, user creation, and My Domain registration are all org-provisioning actions best done by hand). Work through this checklist directly in your Developer Edition org.

## Checklist

### 1. Salesforce Edition
- [ ] Confirm you're working in a **Developer Edition** org (Setup → Company Information → Organization Edition).

### 2. Company Profile
- [ ] Setup → Company Information → Edit.
- [ ] Set Organization Name → "Community Fitness & Wellness Hub".
- [ ] Set default locale, currency, time zone, language.
- [ ] Set primary contact details.

### 3. Business Hours & Holidays
- [ ] Setup → Business Hours → New.
- [ ] Name it "Studio Business Hours"; set open/close time per weekday (e.g. 5:30 AM–9:00/9:30 PM).
- [ ] Mark it Active and set as the default business hours.
- [ ] Setup → Business Hours → Holidays → Add: Christmas Day, Diwali (or whichever holidays apply to your studio).

### 4. Fiscal Year
- [ ] Setup → Fiscal Year → confirm **Standard fiscal year**, starting January. No customization needed.

### 5. User Setup & Licenses
- [ ] Setup → Users → New User.
- [ ] Create a user for **Studio Manager** (Salesforce license; System Administrator profile for now — access gets scoped down via the Trainer/Staff role + permission set once Phase 3's objects exist).
- [ ] Create a user for **Studio Staff** (Salesforce license; Standard User profile).

### 6. Profiles
- [ ] Use the **standard profiles** (System Administrator, Standard User) as the baseline — no custom profile needed. Granular access is layered on via Permission Sets (Phase 3), not custom profiles.

### 7. Roles
- [ ] Setup → Roles → Set Up Roles.
- [ ] Create role **Studio Owner** (top of this project's hierarchy — nest it under your org's existing hierarchy if one already exists).
- [ ] Under Studio Owner, create role **Studio Manager**.
- [ ] Under Studio Manager, create role **Trainer / Staff**.
- [ ] Assign the Studio Manager user to the "Studio Manager" role, and the Studio Staff user to the "Trainer / Staff" role.
- [ ] ⚠️ **Note the exact API name** Salesforce generates for the "Trainer / Staff" role. The Phase 3 sharing rule (`force-app/main/default/sharingRules/Class__c.sharingRules-meta.xml`) references it as `Trainer_Staff` — update that file before deploying if your org generates a different API name.

### 8. Permission Sets
- [ ] No action needed here. A finished permission set (`Studio_Staff_Permissions`) is deployed as part of Phase 3, once the custom objects exist to grant access to.

### 9. Org-Wide Defaults (OWD) & Sharing Rules
- [ ] Deferred to Phase 3 — OWD needs the custom objects to exist first.

### 10. My Domain
- [ ] Setup → My Domain → Register a domain name → Deploy to Users.

### 11. Login Access Policies
- [ ] Leave at default (fine for a single-developer org). Revisit before any production rollout.

### 12. Email Configuration
- [ ] Setup → Deliverability → Access to Send Email: **All Email**.
- [ ] Setup → Organization-Wide Email Addresses → add and verify an address to send booking confirmations from.

### 13. Experience Cloud
- [ ] Setup → Digital Experiences → Settings → enable Digital Experiences.
- [ ] Create a basic site (exploratory only — a full public member portal is a future enhancement, not built in this project's current scope).

### 14. Sandbox Usage
- [ ] Not applicable on Developer Edition (no sandboxes available). Noted here for completeness: a real rollout would use a sandbox for build/test before deploying to production.

### 15. Dev Org & Deployment Basics
- [ ] Confirm all development happens in this Developer org.
- [ ] Recommended: connect this project folder to the org with Salesforce CLI (`sf org login web`) so Phase 3's metadata can be deployed directly — see the root `README.md`.

**Next:** Phase 3 (Data Modeling & Relationships) — see `../phase-03-data-model/README.md`.
