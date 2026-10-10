# CSC315 Assignment #2 — Written Report and Evidence Checklist

## Required explanations

### Standard versus Console navigation

I would choose Standard navigation when users move through mostly independent pages and want a familiar single-page workspace. Console navigation is better when users repeatedly compare related records because primary tabs and subtabs keep context open. Campus Events uses Console navigation so an officer can keep an Event open while reviewing its Registrations and Contact records. Fitness Hub keeps Standard navigation because its modules are commonly completed as separate tasks.

### Why Society cannot use a native Registration roll-up

`Event__c` relates to `Society__c` through a Lookup, while `Registration__c` is the master-detail child of `Event__c`. A native roll-up summary can summarize only direct master-detail children, so Society cannot directly roll up Registration records through Event. The design can either change Event-to-Society to master-detail, if every Event must have one Society, or preserve the optional Lookup and use Flow/Apex aggregation. This implementation preserves the assignment’s optional relationship and uses `Calculate Society Stats`.

### Object-, field-, and record-level security

Object permissions decide whether a user can create, read, edit, or delete Society, Event, and Registration records at all. Field-level security narrows that access; for example, Society Presidents cannot read Ticket Price and Volunteers can edit only Attended. Record-level security then determines which particular Event rows are visible: Event OWD is Private and a criteria sharing rule exposes open events read-only to Volunteers. All three layers apply together, so a visible button never replaces server-side authorization.

## Task 6 short answers

### 1. Salesforce Classic versus Lightning Experience

Classic uses the older page model and is mainly retained for legacy workflows, while Lightning provides the component-based interface, responsive layouts, and modern administration tools. This app uses Lightning Console navigation with tabs and subtabs, plus Lightning Web Components for the Campus dashboard and workspace switcher. It also embeds a Screen Flow on the Event Lightning record page. Those component-driven page and flow experiences are the reason Lightning is the appropriate interface here.

### 2. Lookup versus master-detail deletion behavior

Registration is a master-detail child of Event, so deleting an Event deletes its dependent Registrations as part of the same ownership relationship. Event uses an optional Lookup to Society because an event can be university-wide or co-hosted. Deleting a Society therefore does not automatically delete its Events under the current lookup configuration; Salesforce applies the lookup field’s configured deletion behavior. This keeps events from disappearing merely because a Society record changes.

### 3. Validation rule versus Flow

Use a validation rule when invalid data must be rejected immediately and the requirement can be expressed as a deterministic record formula. Date order, capacity range, required ticket price, closed-event registration, and advisor email domain are good examples. Use Flow when a valid save must trigger work such as sending an email, updating a parent Event, running nightly processing, or handling a platform event. Validation protects the transaction; Flow orchestrates business activity.

### 4. Profiles versus Permission Sets

Profiles provide the user’s baseline login and platform settings, but they become difficult to maintain when every job combination needs a new profile. Permission sets add small, reusable capabilities and can be grouped, assigned, and audited without cloning profiles repeatedly. In this app the base profile stays conservative while Campus Admin, Society President, and Volunteer permission sets grant scenario-specific access. This supports least privilege and makes role changes easier to manage.

### 5. Reminder 24 hours before an event

I would use a record-triggered Flow on Event with a scheduled path set for 24 hours before `Start_Date_Time__c`. The path is tied to each Event and Salesforce recalculates it when the start time changes. At execution, the Flow would retrieve current Registrations and send the reminder to each related Contact. A daily schedule-triggered Flow is an alternative, but it needs a time window and duplicate-send protection.

## Screenshot and demonstration checklist

- [ ] App navigation, object fields, dependent picklist, layouts, related list, list views, and live counts.
- [ ] Each of the five validation errors with formula and field-level message.
- [ ] Contact duplicate block and duplicate warning behaviors.
- [ ] Record type layouts, feed/history tracking, three users, roles, permission assignments, and Login As proof.
- [ ] Four report results and Student Affairs Dashboard with gauge, donut, bar, table, running user, and Society Category filter.
- [ ] Successful and fault Flow Debug runs for all six Flow metadata files; scheduled 11 PM behavior; venue Chatter post.
- [ ] Campus/Fitness workspace switching, responsive states, keyboard focus, and browser console.

Screenshots are intentionally not fabricated; unchecked items require post-deployment UI evidence.
