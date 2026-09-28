Class__c c = [SELECT Id FROM Class__c WHERE Name LIKE '[DEMO]%' ORDER BY Start_Date_Time__c DESC LIMIT 1];
Contact k = [SELECT Id, Email FROM Contact WHERE LastName LIKE '%[DEMO]' LIMIT 1];
System.debug('TEST contact email: ' + k.Email);
Savepoint sp = Database.setSavepoint();
try {
    insert new Class_Booking__c(Name = '[DEMO] flow test', Class__c = c.Id, Contact__c = k.Id, Status__c = 'Booked');
    System.debug('SINGLE INSERT OK');
} catch (Exception e) {
    System.debug('SINGLE INSERT FAILED: ' + e.getMessage());
}
Database.rollback(sp);