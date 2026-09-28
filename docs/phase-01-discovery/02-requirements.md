# Functional Requirements

## Member Experience

- View available classes; filter by date, time, trainer, and class type.
- Book and cancel a class spot online, securely.
- Receive an automatic email confirmation on booking.
- Receive an automatic reminder email 24 hours before the class.
- Track current loyalty points.

## Operational Efficiency

- Staff/trainers can create, edit, and manage Class and Trainer records.
- Staff have a centralized daily view of bookings and attendance.
- Loyalty points are tracked automatically based on class attendance.

## Management & Reporting

- Dashboards showing KPIs: class attendance rate, total active members.
- Reports on class popularity, top-performing trainers, and member loyalty.

## Traceability

Each requirement above maps to a later phase, so nothing gets lost between "what we need" and "what we build":

| Requirement | Delivered in |
|---|---|
| Browse / filter / book / cancel classes | Phase 3 (data model) + Phase 4 (booking flow) |
| Confirmation + reminder emails | Phase 4 (email alert + flow) |
| Loyalty point tracking | Phase 3 (Loyalty Points object) + Phase 4 (automation) |
| Staff manage Class/Trainer records | Phase 3 (objects) + Phase 6 (UI/tabs) |
| Daily bookings/attendance view | Phase 6 (UI) + Phase 9 (reports) |
| KPI dashboards | Phase 9 |
| Popularity / top trainer / loyalty reports | Phase 9 |
