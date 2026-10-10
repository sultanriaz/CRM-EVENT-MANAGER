# Report and Dashboard Tests

- Event Attendance Rate: Metadata dry-run PASS; grouped by Event; percent formula is `SUM(Attended) / RowCount`; descending grouping direction.
- Registrations by Department: Metadata dry-run PASS; Summary grouping and vertical-column chart using record count.
- Society vs Event Status: Matrix metadata present and pre-stage PASS.
- Upcoming Events This Month: Tabular metadata present, current-month date interval, Cancelled exclusion, Seats Remaining column; pre-stage PASS.
- Upcoming Events Dashboard Table: Summary support report used only by the dashboard table; keeps the required assignment report tabular while avoiding nonportable REST-only Top-N settings.
- Student Affairs Dashboard: deployed with Gauge, Donut, Bar, Table, specified running user, and Society Category filter.
- Initial four-report + dashboard dry-run `0Afd5000009UYG6CAO` passed 5/5. Final analytics dry-run `0Afd5000009UVxICAW` and live deployment `0Afd5000009UbPxCAK` passed 6/6. The canonical filter mapping is `Event__c$Society_Category__c`. A REST refresh returned `DATA` for all four components with zero errors; visual rendering/filter interaction remains UNVERIFIED pending browser evidence.
