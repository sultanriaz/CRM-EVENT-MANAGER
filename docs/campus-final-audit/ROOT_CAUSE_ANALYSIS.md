# Root Cause Analysis

## Society Category

`FieldDefinition` proves `Event__c.Society_Category__c` exists as a Formula (Text) field, while normal Event describe and SOQL hide it. `FieldPermissions` showed read access only through unrelated permission set `sfdc_slack`; the authenticated user is assigned `Campus_Events_Admin`, which lacked this field. The root cause is therefore missing FLS, not a failed field deployment or wrong API name.

The smallest correction adds read-only FLS for this formula to `Campus_Events_Admin`. Edit access remains false. Prior speculative Society Category columns were removed from all four reports; the field remains only in the dashboard-filter mapping.

## Report failures

The canonical Salesforce-generated Event Attendance report correctly groups by Event. It lacked the required custom summary formula. A Metadata API-valid `aggregates` entry now computes `Registration__c.Attended__c:SUM / RowCount` as a percentage. The department report now contains a validated vertical-column chart.
