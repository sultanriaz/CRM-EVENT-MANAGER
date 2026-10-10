# Deployment Diagnostics

- `0Afd5000009UWdBCAW`: attendance formula + department chart dry-run, PASS (2/2).
- `0Afd5000009UZb3CAG`: production-valid Stage 1 FLS/email/UI foundation dry-run, PASS (12/12 components, 2/2 tests).
- `0Afd5000009UWuvCAG`: Campus Apex dry-run with tests, PASS (7 classes, 4/4 methods).
- `0Afd5000009UZMXCA4`: independent pre-stage package, PASS (62/62 components, 6/6 specified tests).
- `0Afd5000009UYlRCAW`: enterprise workspace Apex dry-run, PASS (2/2 tests, 92/99 lines).
- `0Afd5000009UXXdCAO`: scheduled/statistics Flow subset, PASS; informational activation prerequisites remain.
- `0Afd5000009Ua8vCAC`: live Stage 1 foundation deployment, PASS.
- `0Afd5000009UaAXCA0`: initial Stage 2 dry-run, correctly FAILED because Salesforce rejects custom-object `Tab` action overrides and the dashboard filter used Analytics API dot syntax instead of Metadata API report-column syntax.
- `0Afd5000009UYG6CAO`: corrected four-report + dashboard dry-run, PASS (5/5). The dashboard filter column is `Event__c$Society_Category__c` in Metadata API XML.
- `0Afd5000009UaLpCAK`: corrected complete Stage 2 dry-run, PASS.
- `0Afd5000009UaQfCAK`: live Stage 2 deployment, PASS (121/121 components, 6/6 tests, zero component or test errors).
- `0Afd5000009UVxICAW`: final analytics dry-run, PASS (five reports plus dashboard, 6/6 components).
- `0Afd5000009UbPxCAK`: final analytics live deployment, PASS (6/6 components). Runtime dashboard refresh completed with `DATA` for all four components and no error codes.
- `0Afd5000009UbUnCAK`: final repository-state Stage 2 dry-run, PASS (122/122 components, 6/6 tests, zero errors).

The failed `Tab` action-override design was replaced with the Salesforce-supported Lightning App Page + Custom Tab pattern. Post-deployment discovery confirmed 11 enterprise tabs, 11 enterprise workspace pages, four assignment reports plus one dashboard support report, and the Student Affairs dashboard. All six flows deployed as Draft and remain inactive pending the documented manual approval gate.
