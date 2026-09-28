# Phase 5 — Apex Programming (Developer)

**Status:** ✅ Complete — this phase is a decision record, not new code.

**Question this phase answers:** does the platform need Apex beyond what's already been written?

## Decision: no additional Apex needed

Every core requirement from Phase 1 is met without writing more code than what already exists:

| Requirement | How it's met | Apex involved? |
|---|---|---|
| Book / cancel a class online | `Class_Booking_Flow` (Screen Flow) | No |
| Booking confirmation + reminder emails | Record-triggered Flow + Email Alert | No |
| Loyalty points on attendance | Record-triggered Flow | No |
| Live seat availability in the booking UI | `ClassBookingController.getUpcomingClasses` (Phase 4) | **Yes — the one exception** |

That one exception was scoped and justified back in Phase 4: a custom, Apple-style booking UI needs a data query richer than what a declarative-only component can express (seat counts computed from a related-record aggregate). It's read-only, ~50 lines, and fully covered by tests. Everything else — all the actual business process automation — is Flow Builder, matching the project's stated principle of using the least complex tool that does the job correctly.

**Why not more Apex, generally:** Flow is faster to build, easier for anyone maintaining this project later to read, and less prone to the kind of subtle bugs custom code can introduce, for anything Flow is actually capable of expressing. Reaching for Apex by default — instead of only when declarative tools structurally can't do something — would make this project harder to maintain, not more impressive.

## Where Apex *would* earn its place — future phases

These are still deferred, exactly as scoped in the original plan, but sketched out further here so "future enhancement" means something concrete rather than a vague bullet point:

### 1. Member engagement / lead-scoring
- **What:** a scheduled batch (`MemberEngagementScoringBatch implements Database.Batchable<SObject>, Schedulable`) that scans Contacts with `Class_Booking__c` history, scores each member on attendance frequency, recency, and accumulated loyalty points, and writes the result to a new `Contact.Engagement_Score__c` field.
- **Why Apex:** aggregating and scoring across a member's entire booking history, on a nightly schedule, across potentially thousands of Contacts, is squarely batch-processing territory — not something Flow handles well at scale.
- **Depends on:** a new roll-up-style field on Contact (not yet created), and a defined scoring formula (a product/business decision, not just a technical one).

### 2. Payment gateway integration
- **What:** a `PaymentGatewayService` class making an outbound HTTP callout (via a Named Credential, e.g. to Stripe or a similar processor) when a `Payment__c` record is created or updated, updating `Status__c` based on the gateway's response. Likely invoked from a Queueable (`PaymentGatewayQueueable`) so the callout doesn't block the triggering transaction.
- **Why Apex:** Flow can make HTTP callouts too (via an HTTP action), but a real payment integration needs retry logic, webhook handling for async payment confirmation, and careful error handling that's much more maintainable in code.
- **Depends on:** choosing an actual payment processor, a Named Credential + Remote Site Setting, and — importantly — this touches real money, so it needs its own security/compliance review before being built, not just a technical spec.

### 3. Batch data cleanup
- **What:** a scheduled batch (`StaleClassBookingCleanupBatch`) that finds `Class_Booking__c` records older than a configurable window with `Status__c` in `Cancelled`/`No-Show`, and either archives or deletes them.
- **Why Apex:** bulk, scheduled, conditional record cleanup across potentially large data volumes is exactly what Batch Apex is for; Flow's scheduled paths aren't built for bulk maintenance jobs at this scale.
- **Depends on:** a decision on retention policy (how long to keep cancelled/no-show records) — again, a business decision to make before writing code.

None of the three above is built in this project yet. They're recorded here so the reasoning ("why isn't X built") is traceable, and so a future session can pick any of them up as a scoped, standalone task rather than starting from a blank page.

**Next:** Phase 6 (User Interface Development) — the Lightning App, tabs, and record page work.
