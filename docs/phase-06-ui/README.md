# Phase 6 — User Interface Development

**Status:** ✅ Complete — Lightning App + tabs deployed as metadata; home page, utility bar, and record page layout are a manual Lightning App Builder checklist.

**Goal:** a professional internal UI for staff/trainers/management.

## Why this phase splits into "deployable" and "manual," and why that split is drawn here

Custom Objects, Fields, Flows, Apex, and — as of this phase — Lightning Apps and Tabs all have stable, well-documented metadata formats safe to hand-author and deploy sight-unseen. **Lightning Pages** (the metadata behind a Home Page, a Utility Bar, and a customized Record Page) are a different story: their XML is deeply nested, tied to exact component/region identifiers, and genuinely easy to get subtly wrong in a way that only surfaces as a deploy failure or a broken-looking page — with no way for me to visually verify it before you see it. Rather than hand you something that *looks* like a real deliverable but has a meaningful chance of not working, those three pieces are a manual Lightning App Builder checklist below, same as Phase 2's org-provisioning items. This isn't a scope cut — every one of them is still fully specified, just done by hand where "by hand" is the reliable path.

## What's deployed as metadata

### Lightning App — `Community Fitness & Wellness Hub`
- Branded with a custom header color (`#0071E3`, matching the booking UI's accent from Phase 4).
- Navigation includes: Home, Classes, Trainers, Class Bookings, Payments, Loyalty Points, Contacts, Reports, Dashboards.

### Custom Tabs
One tab per custom object — `Trainer__c`, `Class__c`, `Class_Booking__c`, `Payment__c`, `Loyalty_Points__c` — each with a distinct color so they're visually distinguishable in the app's nav bar.

## Manual checklist (Lightning App Builder)

### 1. Home Page
- [ ] Setup → App Builder → New → **Home Page** → name it "Studio Manager Home".
- [ ] Add a **Report Chart** component (or a **Dashboard** component once Phase 9's dashboard exists) showing class bookings/attendance at a glance.
- [ ] Activate it and assign it to the **System Administrator** profile (standing in for Studio Manager per the Phase 2 checklist) as the default for the Community Fitness & Wellness Hub app.

### 2. Utility Bar
- [ ] Setup → App Manager → Community Fitness & Wellness Hub → Edit → **Utility Items** → Add.
- [ ] Add **Notes** and **Recent Items** (or **List View** pinned to Class Bookings) as quick-access utilities for staff working a shift.
- [ ] Save — Salesforce wires the utility bar to the app automatically; no separate deploy step needed.

### 3. Record Pages (Class, Trainer)
- [ ] Setup → Object Manager → Class → Lightning Record Pages → New (or edit the org-default page) → add a **Related List – Single** component for Class Bookings, and a **Related Record** or **Detail Panel** for the Trainer field, so staff see who's teaching and who's booked without leaving the record.
- [ ] Repeat for Trainer → add a **Related List** for Classes, so a trainer's full schedule is visible from their own record.
- [ ] Activate each page as the org default for its object (or app-specific/profile-specific, if you want a different layout for members vs. staff later via Experience Cloud).

## Confirmed via the App itself (no extra work needed)
- Standard **Contacts**, **Reports**, and **Dashboards** tabs are already included in the app's navigation via metadata above — no separate access grant needed for internal (non-guest) users.

## Deploying this phase

```bash
sf project deploy start --source-dir force-app --target-org fitness-hub-dev
```

Then:
- [ ] Setup → App Manager → confirm **Community Fitness & Wellness Hub** appears and opens with all 9 nav items.
- [ ] Object Manager → confirm each custom object shows a colored tab consistent with the app nav.
- [ ] Work through the 3-item manual checklist above.

## Explicitly not implemented (unchanged from the original plan)
- **Lightning Web Components for general UI** (e.g. a graphical calendar view of classes) — the two LWCs that exist (Phase 4) are Flow-screen components for the public booking experience specifically, not general app UI. A calendar view remains a future enhancement.
- **Apex + LWC integration beyond the Flow screens, Events in LWC, Wire Adapters, imperative Apex calls, Navigation Service** — all still out of scope for this MVP, per the original Phase 6 scope.

**Next:** Phase 7 (Integration & External Access) — a roadmap/decision phase, not yet started.
