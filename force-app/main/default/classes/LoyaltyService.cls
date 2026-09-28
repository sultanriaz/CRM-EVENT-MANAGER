public with sharing class LoyaltyService {

    public static final Integer POINTS_PER_ATTENDANCE = 10;

    // Kept for backward compatibility
    public static void processLoyaltyPoints(Set<Id> contactIds, Integer pointsToAdd) {
        Map<Id, Integer> byContact = new Map<Id, Integer>();
        for (Id cid : contactIds) {
            byContact.put(cid, pointsToAdd);
        }
        awardPoints(byContact);
    }

    public static void awardPoints(Map<Id, Integer> pointsByContact) {
        if (pointsByContact == null || pointsByContact.isEmpty()) return;

        Map<Id, Loyalty_Points__c> existing = new Map<Id, Loyalty_Points__c>();
        for (Loyalty_Points__c lp : [
            SELECT Id, Contact__c, Total_Points__c, Points_Earned__c
            FROM Loyalty_Points__c
            WHERE Contact__c IN :pointsByContact.keySet()
            ORDER BY CreatedDate DESC
        ]) {
            if (!existing.containsKey(lp.Contact__c)) {
                existing.put(lp.Contact__c, lp);
            }
        }

        Map<Id, Contact> contacts = new Map<Id, Contact>([
            SELECT Id, Name FROM Contact WHERE Id IN :pointsByContact.keySet()
        ]);

        List<Loyalty_Points__c> toUpsert = new List<Loyalty_Points__c>();
        for (Id cid : pointsByContact.keySet()) {
            Integer add = pointsByContact.get(cid);
            Loyalty_Points__c lp = existing.get(cid);
            if (lp == null) {
                String nm = contacts.containsKey(cid) ? contacts.get(cid).Name : 'Member';
                lp = new Loyalty_Points__c(
                    Contact__c = cid,
                    Name = (nm + ' - Loyalty Points').left(80),
                    Total_Points__c = 0,
                    Points_Earned__c = 0
                );
            }
            Decimal total = (lp.Total_Points__c == null ? 0 : lp.Total_Points__c) + add;
            lp.Total_Points__c = total;
            lp.Points_Earned__c = (lp.Points_Earned__c == null ? 0 : lp.Points_Earned__c) + add;
            lp.Loyalty_Date__c = Date.today();
            lp.Tier__c = tierFor(total);
            toUpsert.add(lp);
        }
        upsert toUpsert;
    }

    public static String tierFor(Decimal points) {
        if (points >= 1000) return 'Platinum';
        if (points >= 500) return 'Gold';
        if (points >= 200) return 'Silver';
        return 'Bronze';
    }
}