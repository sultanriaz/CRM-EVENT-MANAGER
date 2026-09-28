List<Contact> toUpdate = new List<Contact>();
for (AggregateResult ar : [
    SELECT Member__c m, MIN(Payment_Date__c) firstPay
    FROM Payment__c WHERE Name LIKE '[DEMO]%' AND Member__c != null
    GROUP BY Member__c]) {
    toUpdate.add(new Contact(Id = (Id) ar.get('m'), Member_Since__c = (Date) ar.get('firstPay')));
}
update toUpdate;
System.debug('MEMBER_SINCE set on ' + toUpdate.size() + ' contacts');