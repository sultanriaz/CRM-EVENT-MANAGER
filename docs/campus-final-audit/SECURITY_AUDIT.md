# Security Audit

- Event OWD Private; Society Public Read Only; Registration Controlled by Parent.
- Roles exist for Student Affairs Officer, Society President, and Volunteer; one active user exists in each role.
- Permission assignments exist: Campus Admin 2, Society President 1, Volunteer 1.
- Campus Admin has CRUD on all three objects and View All Events. Society President has create/edit Events and Registrations, read Society, and Ticket Price hidden. Volunteer has read Events and edit Registration with Attended field permission.
- Open Events criteria sharing to Volunteer role is present.
- Registration Apex uses `with sharing`, field-create checks, user-mode reads/DML, row locking, capacity check, and duplicate check.
- Enterprise workspace Apex uses `with sharing`, an object/field allowlist, describe-based FLS pruning, bind variables, user-mode dynamic SOQL, and permission-derived create/edit controls.
- Effective profile + permission + sharing behavior remains UNVERIFIED until Login As tests are captured.
