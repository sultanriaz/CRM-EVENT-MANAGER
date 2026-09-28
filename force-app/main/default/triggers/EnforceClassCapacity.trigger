trigger EnforceClassCapacity on Class_Booking__c (before insert) {
    Set<Id> classIds = new Set<Id>();
    
    for (Class_Booking__c cb : Trigger.new) {
        if (cb.Class__c != null && cb.Status__c != 'Cancelled') {
            classIds.add(cb.Class__c);
        }
    }
    if (classIds.isEmpty()) return;

    Map<Id, Class__c> classes = new Map<Id, Class__c>([
        SELECT Id, Capacity__c FROM Class__c WHERE Id IN :classIds
    ]);

    AggregateResult[] results = [
        SELECT Class__c, COUNT(Id) total 
        FROM Class_Booking__c 
        WHERE Class__c IN :classIds AND Status__c != 'Cancelled' 
        GROUP BY Class__c
    ];

    Map<Id, Integer> bookingCounts = new Map<Id, Integer>();
    for (AggregateResult ar : results) {
        bookingCounts.put((Id)ar.get('Class__c'), (Integer)ar.get('total'));
    }

    for (Class_Booking__c cb : Trigger.new) {
        if (cb.Class__c != null && cb.Status__c != 'Cancelled') {
            Integer current = bookingCounts.containsKey(cb.Class__c) ? bookingCounts.get(cb.Class__c) : 0;
            Class__c cls = classes.get(cb.Class__c);
            
            if (cls != null && cls.Capacity__c != null && current >= cls.Capacity__c) {
                cb.addError('Booking failed: This class has reached its maximum capacity of ' + cls.Capacity__c + ' members.');
            }
        }
    }
}