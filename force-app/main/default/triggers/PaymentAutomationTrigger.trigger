trigger PaymentAutomationTrigger on Payment__c (after insert, after update, after delete, after undelete) {
    Set<Id> memberIds = new Set<Id>();

    List<Payment__c> records = Trigger.isDelete ? Trigger.old : Trigger.new;
    for (Payment__c p : records) {
        if (p.Member__c != null) {
            memberIds.add(p.Member__c);
        }
    }

    if (Trigger.isUpdate) {
        for (Payment__c oldP : Trigger.old) {
            if (oldP.Member__c != null) {
                memberIds.add(oldP.Member__c);
            }
        }
    }

    if (!memberIds.isEmpty()) {
        PaymentService.recalculateMemberMetrics(memberIds);
    }
}