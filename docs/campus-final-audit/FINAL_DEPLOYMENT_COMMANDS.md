# Final Deployment Commands

Deployment to `fitness-trial` completed successfully on 2026-10-09. Stage 1 deployment `0Afd5000009Ua8vCAC` and Stage 2 deployment `0Afd5000009UaQfCAK` both succeeded. The commands below are retained for a repeatable validation or idempotent redeployment.

Validation only (safe, default):

```powershell
Set-Location 'C:\black_paper\Projects\fitness-hub-crm'
.\scripts\deploy-campus-final.ps1 -Org fitness-trial
```

After explicit approval, staged deployment:

```powershell
.\scripts\deploy-campus-final.ps1 -Org fitness-trial -Deploy
```

The script verifies org identity, retrieves a backup, validates Stage 1 and the independent package, then—only with `-Deploy`—deploys the FLS/email/UI foundation, validates Stage 2 (including supported Lightning App Page custom tabs) with specified tests, and deploys Stage 2. It stops on every nonzero Salesforce CLI exit code.

Post-deployment checks passed: final complete-package validation `0Afd5000009UbUnCAK` passed 122/122 components and 6/6 tests; 11 enterprise tabs, 11 enterprise workspace pages, four assignment reports plus one dashboard-only support report, and the Student Affairs dashboard are present. A runtime refresh returned `DATA` for all four dashboard components. All six flows intentionally remain inactive. Manual work is limited to browser evidence, setting the Default Workflow User, Flow Debug, and separately approved activation.
