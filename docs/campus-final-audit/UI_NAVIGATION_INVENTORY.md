# UI Navigation Inventory

## Campus Events Manager

Home, Societies, Events, Registrations, Contacts, Reports, Dashboards. Home uses `Campus_Events_Home`. Societies, Events, Registrations, and Contacts use deployed Lightning App Page custom tabs backed by `enterpriseObjectWorkspace`. Event records retain `Campus_Event_Record_Page` and the registration Flow. Reports and Dashboards deliberately remain native Salesforce analytics.

## Community Fitness & Wellness Hub

Home, Classes, Trainers, Class Bookings, Payments, Loyalty Points, Contacts, Reports, Dashboards, Lab Students, Lab Classes. Home uses the existing Fitness dashboard and insights components. Every listed data destination uses a deployed Lightning App Page custom tab backed by the reusable enterprise workspace. Reports and Dashboards remain native.

Both apps reference utility FlexiPages containing `workspaceSwitcher`, which uses `standard__app` navigation in both directions. The supported App Page/custom-tab architecture replaced the rejected `Tab` action-override attempt. Production verification found all 11 enterprise tabs and all 11 corresponding workspace pages.
