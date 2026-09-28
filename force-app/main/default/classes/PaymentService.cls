public with sharing class PaymentService {
    public static void recalculateMemberMetrics(Set<Id> memberIds) {
        if (memberIds.isEmpty()) return;

        Map<Id, AggregateResult> paymentTotals = new Map<Id, AggregateResult>();
        for (AggregateResult ar : [
            SELECT Member__c memberId, SUM(Amount__c) totalAmount, COUNT(Id) totalCount
            FROM Payment__c
            WHERE Member__c IN :memberIds AND Status__c = 'Completed'
            GROUP BY Member__c
        ]) {
            paymentTotals.put((Id)ar.get('memberId'), ar);
        }

        List<Contact> contactsToUpdate = new List<Contact>();
        for (Id memberId : memberIds) {
            Decimal totalPaid = 0;
            Integer completedPayments = 0;

            if (paymentTotals.containsKey(memberId)) {
                AggregateResult ar = paymentTotals.get(memberId);
                totalPaid = (Decimal)ar.get('totalAmount');
                completedPayments = (Integer)ar.get('totalCount');
            }

            // Dynamically assign VIP status based on lifetime value (> 100,000 PKR)
            String vipLevel = (totalPaid >= 100000) ? 'Gold VIP Member' : 'Standard Member';
            
            contactsToUpdate.add(new Contact(
                Id = memberId,
                Description = 'Lifetime Value: PKR ' + totalPaid + ' | Completed Transactions: ' + completedPayments + ' | Level: ' + vipLevel
            ));
        }

        if (!contactsToUpdate.isEmpty()) {
            update contactsToUpdate;
        }
    }
}