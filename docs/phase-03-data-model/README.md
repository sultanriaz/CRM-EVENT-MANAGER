# Phase 3 — Data Modeling & Relationships

**Status:** ✅ Complete — deployable metadata included in `force-app/main/default/`.

**Goal:** Build the data model everything else (automation, UI, reports) depends on.

## Objects

| Object | API Name | Purpose | Name field |
|---|---|---|---|
| Trainer | `Trainer__c` | Stores each trainer's profile | Trainer Name (Text) |
| Class | `Class__c` | A bookable class session | Class Name (Text) |
| Class Booking | `Class_Booking__c` | Junction object: one member's booking of one class | Class Booking Name (Text) |
| Payment | `Payment__c` | A payment tied to a booking | Payment Name (Text) |
| Loyalty Points | `Loyalty_Points__c` | Points earned by a member for a booking | Loyalty Points Name (Text) |
| Contact | *(standard)* | Represents the member | — |

## Fields

**Trainer__c**
- `Specialty__c` — Picklist (Yoga, Pilates, Cardio, Strength Training, Zumba, CrossFit, Spin, Other)
- `Years_of_Experience__c` — Number(3,0)
- `Biography__c` — Long Text Area (32,768)

**Class__c**
- `Trainer__c` — Lookup(Trainer__c)
- `Start_Date_Time__c` — Date/Time
- `Capacity__c` — Number(4,0)
- `Description__c` — Long Text Area (32,768)

**Class_Booking__c**
- `Class__c` — Lookup(Class__c)
- `Contact__c` — Lookup(Contact)
- `Status__c` — Picklist (Booked *default*, Attended, Cancelled, No-Show)

**Payment__c**
- `Class_Booking__c` — Lookup(Class_Booking__c)
- `Amount__c` — Currency(16,2)
- `Status__c` — Picklist (Pending *default*, Completed, Failed, Refunded)

**Loyalty_Points__c**
- `Class_Booking__c` — Lookup(Class_Booking__c)
- `Points_Earned__c` — Number(5,0)
- `Loyalty_Date__c` — Date

> The `Loyalty_Points__c → Class_Booking__c` lookup isn't spelled out as a separate step in the original phase notes, but it's required for loyalty points to show as a related list on a Class Booking record and for the Phase 4 loyalty automation to know which booking earned the points — so it's included here now rather than retrofitted later.

## Relationships (ERD)

```mermaid
erDiagram
    CONTACT ||--o{ CLASS_BOOKING : books
    CLASS ||--o{ CLASS_BOOKING : "is booked in"
    TRAINER ||--o{ CLASS : teaches
    CLASS_BOOKING ||--o{ PAYMENT : "is paid via"
    CLASS_BOOKING ||--o{ LOYALTY_POINTS : earns
```

All relationships are **Lookups**, not Master-Detail — a deliberate choice so related records can be linked without strict ownership requirements, avoiding cascading deletes and keeping the model flexible for the different business processes layered on in later phases.

`Class_Booking__c` is designed as a **junction object** connecting `Class__c` and `Contact`, so one member can book many classes and one class can have many members.

## Security model

- **Organization-Wide Defaults:** `Private` on all 5 custom objects (set via `<sharingModel>Private</sharingModel>` in each object's metadata).
- **Sharing Rule:** `force-app/main/default/sharingRules/Class__c.sharingRules-meta.xml` shares `Class__c` records owned by the `Trainer_Staff` role with that same role at **Edit** access, so trainers can see and manage the classes they're responsible for. ⚠️ Update the `role` value in that file if your org's "Trainer / Staff" role has a different API name (see Phase 2 checklist, item 7).
- **Permission Set:** `Studio_Staff_Permissions` grants Create/Read/Edit + view-all on all 5 custom objects (no Delete, no modify-all) — assign it to the Studio Staff/Trainer user(s) after deployment. Field-level security refinement is tracked for the Phase 9 security review, not done here.

## Deploying this phase

```bash
sf project deploy start --source-dir force-app --target-org fitness-hub-dev
```

Then in Setup:
- [ ] Confirm all 5 objects appear under Object Manager with the fields listed above.
- [ ] Assign the `Studio_Staff_Permissions` permission set to your Studio Staff / Trainer user(s): Setup → Permission Sets → Studio Staff Permissions → Manage Assignments → Add Assignment.
- [ ] Spot-check OWD: Setup → Sharing Settings → confirm all 5 custom objects show **Private**.
- [ ] Spot-check the sharing rule: Setup → Sharing Settings → Class Sharing Rules → confirm the new rule is listed and active.

**Next:** Phase 4 (Process Automation) — not yet started. Will add Flow Builder metadata (`force-app/main/default/flows/`) plus an email template and email alert.
