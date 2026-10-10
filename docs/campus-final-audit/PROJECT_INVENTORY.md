# Project Inventory

- Salesforce DX API: 61.0; target alias `fitness-trial`; verified org ID `00Dd500000L2GcTEAV` (Neuronix).
- Applications: `Campus_Events_Manager` (Console) and `Community_Fitness_Wellness_Hub` (Standard).
- Campus model: Society, Event, Registration, Venue Alert platform event, 30+ custom fields, two Event record types, three layouts.
- Automation: six Campus Flow files, five new/updated production Apex classes, and four focused Campus/UI test classes.
- Analytics: one custom report type, four assignment reports, one dashboard-only support report, one dashboard, and report/dashboard folders.
- UI: Campus and Fitness dashboards, insights panel, workspace switcher, reusable enterprise object workspace, 11 Lightning App Page custom tabs, and app Home/Event/utility FlexiPages.
- Deployment: `manifest/campus-final-package.xml` plus staged manifests and `scripts/deploy-campus-final.ps1`; live Stage 2 deployment `0Afd5000009UaQfCAK` succeeded.
- Existing uncommitted user work was preserved; backups for files changed in this run are under `backup/campus-final-20261009/`.
