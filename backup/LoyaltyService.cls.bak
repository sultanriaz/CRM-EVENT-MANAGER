public with sharing class LoyaltyService {
    public static void processLoyaltyPoints(Set<Id> contactIds, Integer pointsToAdd) {
        if (contactIds.isEmpty()) return;

        Map<Id, Loyalty_Points__c> existingLoyaltyMap = new Map<Id, Loyalty_Points__c>();
        for (Loyalty_Points__c lp : [
            SELECT Id, Contact__c, Total_Points__c, Tier__c 
            FROM Loyalty_Points__c 
            WHERE Contact__c IN :contactIds
        ]) {
            existingLoyaltyMap.put(lp.Contact__c, lp);
        }

        List<Loyalty_Points__c> toUpsert = new List<Loyalty_Points__c>();

        for (Id contactId : contactIds) {
            Loyalty_Points__c lp = existingLoyaltyMap.containsKey(contactId) 
                ? existingLoyaltyMap.get(contactId) 
                : new Loyalty_Points__c(Contact__c = contactId, Total_Points__c = 0);

            Decimal currentPoints = lp.Total_Points__c != null ? lp.Total_Points__c : 0;
            Decimal newPoints = currentPoints + pointsToAdd;
            lp.Total_Points__c = newPoints;

            // Tier Calculation Logic
            if (newPoints >= 1000) {
                lp.Tier__c = 'Platinum';
            } else if (newPoints >= 500) {
                lp.Tier__c = 'Gold';
            } else if (newPoints >= 200) {
                lp.Tier__c = 'Silver';
            } else {
                lp.Tier__c = 'Bronze';
            }

            toUpsert.add(lp);
        }

        if (!toUpsert.isEmpty()) {
            upsert toUpsert;
        }
    }
}