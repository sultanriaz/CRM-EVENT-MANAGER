Class_Booking__c cb = [SELECT Id, Contact__c FROM Class_Booking__c WHERE Name LIKE '[DEMO]%' AND Status__c = 'Booked' LIMIT 1];
List<Loyalty_Points__c> b = [SELECT Total_Points__c, Tier__c FROM Loyalty_Points__c WHERE Contact__c = :cb.Contact__c];
System.debug('LOYALTY BEFORE: ' + JSON.serialize(b));
Savepoint sp = Database.setSavepoint();
try {
    cb.Status__c = 'Attended';
    update cb;
    List<Loyalty_Points__c> a = [SELECT Total_Points__c, Tier__c, Loyalty_Date__c FROM Loyalty_Points__c WHERE Contact__c = :cb.Contact__c];
    System.debug('LOYALTY AFTER: ' + JSON.serialize(a));
} catch (Exception e) {
    System.debug('LOYALTY TEST FAILED: ' + e.getMessage());
}
Database.rollback(sp);