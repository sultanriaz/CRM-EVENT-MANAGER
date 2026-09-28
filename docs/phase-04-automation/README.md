# Phase 4 — Process Automation

**Status:** ✅ Complete — deployable metadata included in `force-app/main/default/`.

**Goal:** Automate class booking, member confirmation, and loyalty tracking.

## What's here, and why it goes slightly beyond the original reference plan

The reference build's Phase 4 used stock Screen Flow input fields (plain text boxes) for the public booking form. You asked for the booking experience itself to feel sleek and modern, Apple-website-grade — that isn't achievable with stock Lightning Screen Flow fields, which are functional but visually generic. So this phase makes one deliberate scope call:

> **The public booking screen and the confirmation screen are custom Lightning Web Components, not stock Flow fields.** Everything else — the fact that Flow Builder owns the actual record creation and business logic — is unchanged from the original plan.

This does pull in a small amount of Apex earlier than planned (Phase 5 in the original plan). It's scoped to exactly one read-only method (`ClassBookingController.getUpcomingClasses`) that powers the class picker with live seat counts — nothing about payments, scoring, or batch jobs. Phase 5's original future-use-cases list (lead scoring, payment gateway REST callouts, batch cleanup) is untouched and still deferred.

## What was built

### 1. Public Class Booking Flow — `Class_Booking_Flow`
A Screen Flow with two screens:

1. **Booking Form** — renders the custom `c:classBookingForm` component: name/email inputs plus a card grid of upcoming classes (date, trainer, live seats-remaining), built with an Apple-inspired visual language — generous whitespace, SF-Pro-style system font stack, soft shadows, a single blue accent (#0071e3), 12–18px rounded corners, subtle hover/selection states, and a shimmering skeleton loading state.
2. Behind the scenes, the flow then:
   - Looks up an existing **Contact** by the email entered (`Get_Existing_Contact`).
   - If none exists, **creates** one (splitting the entered name into first/last).
   - **Creates the `Class_Booking__c` record** (`Status__c = Booked`), linked to the selected Class and the Contact.
   - Re-fetches the class's details for a clean confirmation message.
3. **Confirmation** — renders `c:classBookingConfirmation`: a checkmark, "You're booked, {first name}", and a card recapping the class name + formatted date/time.

This flow is a **Screen Flow**, meant to be exposed publicly (a Flow URL, or embedded in the Experience Cloud site enabled in Phase 2) — see the deploy/activation checklist below.

### 2. Booking Confirmation Email — `Send_Booking_Confirmation_Email`
A Record-Triggered Flow on `Class_Booking__c` (fires on **Create**) that invokes the `Send_Booking_Confirmation` Email Alert, which uses the `Booking Confirmation` HTML email template — styled to match the booking form (same fonts/colors/rounded card layout), sent to the Contact on the booking.

### 3. Loyalty Points Automation — `Award_Loyalty_Points_on_Attendance`
A Record-Triggered Flow on `Class_Booking__c` (fires on **Update**, entry condition: `Status__c` just changed **to** `Attended`) that creates a `Loyalty_Points__c` record (10 points, dated today, linked back to the booking). Gating on "just changed to Attended" means it fires exactly once per booking — no duplicate-check step needed.

> Marking a booking `Attended` is a manual staff action for now (there's no attendance-taking UI yet — that's Phase 6).

## New components in this phase

| Type | Name | Purpose |
|---|---|---|
| Apex Class | `ClassBookingController` | Read-only: lists upcoming classes with live seat availability |
| Apex Class | `ClassBookingControllerTest` | Unit tests (seat math, full-class handling, past-class exclusion) |
| LWC | `classBookingForm` | The public booking screen (name/email + class picker) |
| LWC | `classBookingConfirmation` | The "you're booked" confirmation screen |
| Flow | `Class_Booking_Flow` | Public screen flow — the booking experience end-to-end |
| Flow | `Send_Booking_Confirmation_Email` | Record-triggered: sends the confirmation email on create |
| Flow | `Award_Loyalty_Points_on_Attendance` | Record-triggered: awards points when status → Attended |
| Workflow (Email Alert) | `Class_Booking__c.Send_Booking_Confirmation` | The email alert the confirmation flow invokes |
| Email Template | `unfiled$public/Booking Confirmation` | HTML template, same visual language as the LWCs |

## Design notes / things to know before deploying

- **Sender address:** the email alert uses `senderType = CurrentUser` rather than the org-wide address configured in Phase 2, purely so this deploys cleanly with zero dependency on the exact org-wide address string in your org. Once your org-wide address is verified (Phase 2, item 12), you can switch this to `OrgWideEmailAddress` + that address in Setup → Email Alerts for a more "sent by the studio" feel.
- **Fixed loyalty points value:** `Points_Earned__c` is hard-coded to `10` per attendance. If you want variable points (e.g., by class type or a promo), that's a one-field change in the flow's Create Records step.
- **Capacity is enforced in the UI, not yet in data:** the booking form disables/greys out a class once `getUpcomingClasses` reports zero seats left, but nothing yet stops two people from submitting at the exact same instant and both getting through (a true race-condition guard would need a validation rule or a record-triggered Flow fault path on `Class_Booking__c` checking count vs. capacity server-side). Flagged here rather than silently skipped — a good candidate for a small addition alongside Phase 9's security review, or now if you'd rather harden it immediately.
- **The public flow still needs to be made reachable by members** — Screen Flows aren't public by default:
  - [ ] Setup → Flows → `Class_Booking_Flow` → **Distribute** → get the public Flow URL (site guest access required), **or**
  - [ ] Embed it as a Lightning component on the Experience Cloud site page created in Phase 2.
  - [ ] Either way, grant the **Guest User** profile for that site Read access to `Class__c` (to browse) and Create access to `Contact__c` / `Class_Booking__c` (to book) — Setup → Digital Experiences → your site → Administration → Guest User Profile.

## Deploying this phase

```bash
sf project deploy start --source-dir force-app --target-org fitness-hub-dev
```

Then:
- [ ] Setup → Object Manager → confirm `ClassBookingController`, both LWCs, and all three flows deployed and are **Active**.
- [ ] Open `Class_Booking_Flow` in Flow Builder → **Run** to test the full path end-to-end with a sample class.
- [ ] Create a test `Class_Booking__c` manually and confirm the confirmation email sends.
- [ ] Edit that booking's `Status__c` to `Attended` and confirm a `Loyalty_Points__c` record is created.
- [ ] Run Apex tests: `sf apex run test --class-names ClassBookingControllerTest --target-org fitness-hub-dev` — should be 100% pass, well above the 75% org coverage threshold Salesforce requires for deploying Apex.
- [ ] Complete the guest-access checklist above before sharing the public booking link with real members.

**Next:** Phase 5 (Apex Programming) — the "no additional Apex needed" decision write-up, unaffected by the small controller added here; still tracks lead-scoring, payment-gateway callouts, and batch cleanup as the deferred future use cases.
