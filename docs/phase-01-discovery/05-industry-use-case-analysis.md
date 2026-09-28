# Industry-Specific Use Case Analysis

The fitness/wellness industry has a few requirements a generic CRM doesn't cover out of the box:

1. **Class capacity management** — the number of Class Booking records for a class must never exceed that class's Capacity. *(Flagged here for design; enforcement via Validation Rule or Flow fault path is tracked in the Phase 4 backlog.)*
2. **Member loyalty & retention** — Loyalty Points must be tracked and updated automatically when a member attends a class, to encourage repeat visits.
3. **B2C-first approach** — the primary booking interface is a public-facing form/portal built for a customer's convenience, not an internal admin screen.

These three constraints directly shape the Phase 3 data model (a `Capacity` field on Class, a dedicated Loyalty Points object) and the Phase 4 automation design (a public Screen Flow, not an internal-only form).
