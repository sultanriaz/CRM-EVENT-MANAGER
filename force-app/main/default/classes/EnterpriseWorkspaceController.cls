public with sharing class EnterpriseWorkspaceController {
    private static final Map<String, List<String>> WORKSPACE_FIELDS = new Map<String, List<String>>{
        'Contact' => new List<String>{'Name', 'Email', 'Phone', 'Title', 'Account.Name'},
        'Society__c' => new List<String>{'Name', 'Category__c', 'Active__c', 'Faculty_Advisor_Email__c', 'Completed_Events__c', 'Total_Attendees__c'},
        'Event__c' => new List<String>{'Name', 'Society__r.Name', 'Start_Date_Time__c', 'Venue__c', 'Status__c', 'Capacity__c', 'Seats_Remaining__c', 'Fill_Status__c', 'Ticket_Price__c'},
        'Registration__c' => new List<String>{'Name', 'Student__r.Name', 'Event__r.Name', 'Student_Department__c', 'Registration_Date__c', 'Attended__c'},
        'Class__c' => new List<String>{'Name', 'Trainer__r.Name', 'Start_Date_Time__c', 'Capacity__c', 'Description__c'},
        'Trainer__c' => new List<String>{'Name', 'Specialty__c', 'Years_of_Experience__c', 'Biography__c'},
        'Class_Booking__c' => new List<String>{'Name', 'Contact__r.Name', 'Class__r.Name', 'Status__c'},
        'Payment__c' => new List<String>{'Name', 'Member__r.Name', 'Class_Booking__r.Name', 'Amount__c', 'Payment_Date__c', 'Status__c'},
        'Loyalty_Points__c' => new List<String>{'Name', 'Contact__r.Name', 'Points_Earned__c', 'Total_Points__c', 'Tier__c', 'Loyalty_Date__c'},
        'Lab_Student__c' => new List<String>{'Name', 'Student_ID__c', 'Class__r.Name', 'Age__c', 'Gender__c', 'City__c', 'Country__c'},
        'Lab_Class__c' => new List<String>{'Name', 'Class_Name__c', 'Max_Strength__c'}
    };

    public class WorkspacePage {
        @AuraEnabled public List<Map<String, Object>> rows;
        @AuraEnabled public List<String> visibleFields;
        @AuraEnabled public Integer totalRecords;
        @AuraEnabled public Integer pageNumber;
        @AuraEnabled public Integer pageSize;
        @AuraEnabled public Boolean createable;
        @AuraEnabled public Boolean updateable;
        @AuraEnabled public String objectLabel;
    }

    @AuraEnabled(cacheable=true)
    public static WorkspacePage getPage(
        String objectApiName,
        String searchTerm,
        String filterField,
        String filterValue,
        String sortBy,
        String sortDirection,
        Integer pageSize,
        Integer pageNumber
    ) {
        if (!WORKSPACE_FIELDS.containsKey(objectApiName)) {
            throw new AuraHandledException('This workspace is not configured for the requested object.');
        }

        Schema.SObjectType objectType = Schema.getGlobalDescribe().get(objectApiName);
        Schema.DescribeSObjectResult objectDescribe = objectType == null ? null : objectType.getDescribe();
        if (objectDescribe == null || !objectDescribe.isAccessible()) {
            throw new AuraHandledException('You do not have access to this workspace.');
        }

        List<String> visibleFields = new List<String>();
        for (String fieldPath : WORKSPACE_FIELDS.get(objectApiName)) {
            if (isPathAccessible(objectType, fieldPath)) {
                visibleFields.add(fieldPath);
            }
        }
        if (!visibleFields.contains('Name')) {
            throw new AuraHandledException('Record names are not available for this workspace.');
        }

        Integer safePageSize = pageSize == null ? 20 : Math.max(5, Math.min(50, pageSize));
        Integer safePageNumber = pageNumber == null ? 1 : Math.max(1, pageNumber);
        Integer rowOffset = (safePageNumber - 1) * safePageSize;
        if (rowOffset > 1950) {
            rowOffset = 1950;
            safePageNumber = (rowOffset / safePageSize) + 1;
        }

        List<String> predicates = new List<String>();
        Map<String, Object> binds = new Map<String, Object>();
        if (!String.isBlank(searchTerm)) {
            predicates.add('Name LIKE :searchPattern');
            binds.put('searchPattern', '%' + searchTerm.trim() + '%');
        }
        if (!String.isBlank(filterField) && !String.isBlank(filterValue)
                && visibleFields.contains(filterField) && !filterField.contains('.')) {
            predicates.add(filterField + ' = :selectedFilter');
            binds.put('selectedFilter', coerceFilterValue(objectType, filterField, filterValue));
        }

        String whereClause = predicates.isEmpty() ? '' : ' WHERE ' + String.join(predicates, ' AND ');
        String safeSort = visibleFields.contains(sortBy) ? sortBy : 'Name';
        String safeDirection = 'DESC'.equalsIgnoreCase(sortDirection) ? 'DESC' : 'ASC';
        String countSoql = 'SELECT COUNT(Id) totalRows FROM ' + objectApiName + whereClause;
        AggregateResult countResult = (AggregateResult)Database.queryWithBinds(countSoql, binds, AccessLevel.USER_MODE)[0];
        Integer totalRecords = (Integer)countResult.get('totalRows');

        String dataSoql = 'SELECT Id, ' + String.join(visibleFields, ', ') +
            ' FROM ' + objectApiName + whereClause + ' ORDER BY ' + safeSort + ' ' + safeDirection +
            ' NULLS LAST LIMIT ' + safePageSize + ' OFFSET ' + rowOffset;
        List<SObject> records = Database.queryWithBinds(dataSoql, binds, AccessLevel.USER_MODE);

        List<Map<String, Object>> rows = new List<Map<String, Object>>();
        for (SObject record : records) {
            Map<String, Object> row = new Map<String, Object>{
                'Id' => record.Id,
                'recordUrl' => '/' + record.Id
            };
            for (String fieldPath : visibleFields) {
                row.put(flattenKey(fieldPath), readPath(record, fieldPath));
            }
            rows.add(row);
        }

        WorkspacePage page = new WorkspacePage();
        page.rows = rows;
        page.visibleFields = visibleFields;
        page.totalRecords = totalRecords;
        page.pageNumber = safePageNumber;
        page.pageSize = safePageSize;
        page.createable = objectDescribe.isCreateable();
        page.updateable = objectDescribe.isUpdateable();
        page.objectLabel = objectDescribe.getLabelPlural();
        return page;
    }

    private static Boolean isPathAccessible(Schema.SObjectType rootType, String fieldPath) {
        Schema.SObjectType currentType = rootType;
        List<String> parts = fieldPath.split('\\.');
        for (Integer index = 0; index < parts.size(); index++) {
            Map<String, Schema.SObjectField> fields = currentType.getDescribe().fields.getMap();
            if (index == parts.size() - 1) {
                Schema.SObjectField fieldToken = fields.get(parts[index]);
                return fieldToken != null && fieldToken.getDescribe().isAccessible();
            }
            Schema.SObjectType nextType;
            for (Schema.SObjectField fieldToken : fields.values()) {
                Schema.DescribeFieldResult fieldDescribe = fieldToken.getDescribe();
                if (fieldDescribe.getRelationshipName() == parts[index] && !fieldDescribe.getReferenceTo().isEmpty()) {
                    nextType = fieldDescribe.getReferenceTo()[0];
                    break;
                }
            }
            if (nextType == null || !nextType.getDescribe().isAccessible()) {
                return false;
            }
            currentType = nextType;
        }
        return false;
    }

    private static Object readPath(SObject record, String fieldPath) {
        List<String> parts = fieldPath.split('\\.');
        SObject current = record;
        for (Integer index = 0; index < parts.size() - 1; index++) {
            current = current == null ? null : current.getSObject(parts[index]);
        }
        return current == null ? null : current.get(parts[parts.size() - 1]);
    }

    private static Object coerceFilterValue(Schema.SObjectType objectType, String fieldName, String value) {
        Schema.SObjectField fieldToken = objectType.getDescribe().fields.getMap().get(fieldName);
        if (fieldToken != null && fieldToken.getDescribe().getType() == Schema.DisplayType.Boolean) {
            return 'true'.equalsIgnoreCase(value);
        }
        return value;
    }

    private static String flattenKey(String fieldPath) {
        return fieldPath.replace('.', '_');
    }
}
