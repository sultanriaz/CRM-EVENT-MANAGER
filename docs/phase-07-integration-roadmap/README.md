# Phase 7 — Integration & External Access

**Status:** ✅ Complete — this phase is a roadmap record, not new code, by design (same as Phase 5).

**Goal:** name the integration points a real rollout of this platform would eventually need, and be explicit about why none of them are built for this MVP.

## Decision: stay native for now

The project's stated focus throughout has been a robust solution built entirely inside Salesforce, within MVP time constraints. Three integration points came up in earlier phases as things a *production* version of this platform would want — each is recorded here with enough detail to pick up as a scoped task later, rather than left as a vague "integrate with X" bullet.

### 1. Payment gateway integration
- **What:** members pay for classes/memberships directly from the booking flow, instead of `Payment__c` being a manually-entered record.
- **How it would be built:** an Apex Callout (`PaymentGatewayService`, sketched in the Phase 5 decision doc) to a processor like Stripe, authenticated via a **Named Credential** (never hardcode API keys in Apex or Flow), with a **Remote Site Setting** or newer External Credential for the callout endpoint. Webhook confirmation (async) would update `Payment__c.Status__c` on completion, most likely via a public-facing Apex REST endpoint (`@RestResource`) that the payment processor calls back.
- **Why deferred:** this touches real money — it needs a business decision on which processor, a compliance/security review, and a webhook-handling design, none of which are technical scope calls I should make unilaterally on your behalf.

### 2. SMS notifications
- **What:** an SMS reminder alongside (or instead of) the email reminder, for members who'd rather get a text than an email.
- **How it would be built:** a third-party SMS API (e.g. Twilio) called from a Flow HTTP action or a small Apex class, triggered from the same point in `Send_Booking_Confirmation_Email`'s logic (or a new sibling flow keyed off the same trigger), storing the member's phone number as a new field on Contact.
- **Why deferred:** needs a phone number field/collection step added to the booking form (a UI decision), plus a chosen SMS provider and its associated cost — not purely technical.

### 3. External calendar sync
- **What:** a booked class shows up automatically in the member's own calendar (Google Calendar, Outlook, iCal), instead of relying on the confirmation email alone.
- **How it would be built:** Salesforce **Platform Events** published when a `Class_Booking__c` is created, consumed by an external subscriber (a small middleware service) that calls the relevant calendar provider's API — or, more simply, generate and attach a `.ics` file to the confirmation email, which needs no external integration at all and is a much lighter first step toward the same outcome.
- **Why deferred:** full two-way calendar sync is a real integration project; the `.ics`-attachment version is genuinely low-effort and worth considering as a "Phase 4.5" addition if calendar visibility turns out to matter more than expected once real members are booking.

## What stays native (no plans to change this)

Everything built in Phases 3–6 — the data model, booking flow, confirmation/loyalty automation, and the Lightning App — has no external dependency and won't need to change if/when any of the above gets built. That's a direct benefit of having kept the MVP native: these three integrations are additive, not architectural rework.

**Next:** Phase 8 (Data Management & Deployment) — sample data for testing, and the deployment/packaging strategy this project already follows.
