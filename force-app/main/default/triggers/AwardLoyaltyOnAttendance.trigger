trigger AwardLoyaltyOnAttendance on Class_Booking__c (after update) {
    Map<Id, Integer> pointsByContact = new Map<Id, Integer>();
    for (Class_Booking__c cb : Trigger.new) {
        Class_Booking__c oldCb = Trigger.oldMap.get(cb.Id);
        if (cb.Status__c == 'Attended' && oldCb.Status__c != 'Attended' && cb.Contact__c != null) {
            Integer current = pointsByContact.containsKey(cb.Contact__c) ? pointsByContact.get(cb.Contact__c) : 0;
            pointsByContact.put(cb.Contact__c, current + LoyaltyService.POINTS_PER_ATTENDANCE);
        }
    }
    if (!pointsByContact.isEmpty()) {
        LoyaltyService.awardPoints(pointsByContact);
    }
}