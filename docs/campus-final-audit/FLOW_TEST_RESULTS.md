# Flow Test Results

| Flow | Metadata validation | Runtime Debug |
|---|---|---|
| Quick Event Registration | PASS | UNVERIFIED |
| Registration Before Save | PASS | UNVERIFIED |
| Registration After Save | PASS after Stage 1 alert deployment | UNVERIFIED |
| Daily Event Closer | PASS | UNVERIFIED |
| Calculate Society Stats | PASS | Apex action test PASS |
| Venue Emergency Handler | PASS | Apex action test PASS |

All Flow source remains `Draft`; no activation occurred. A post-deployment Tooling API query confirmed `ActiveVersionId = null` for all six definitions. Before activating Daily Event Closer, set the org Default Workflow User, activate Calculate Society Stats first, then debug the scheduled flow.

Targeted Metadata API dry-run `0Afd5000009UXXdCAO` passed (3/3 components, 0 errors); complete Stage 2 validation `0Afd5000009UaLpCAK` and live deployment `0Afd5000009UaQfCAK` also passed. The only messages were informational prerequisites for the Default Workflow User and the inactive subflow version.
