public with sharing class CampusSocietyStatsAction {
    public class Input { @InvocableVariable(required=true) public Id societyId; }
    public class Result {
        @InvocableVariable public Decimal completedEvents;
        @InvocableVariable public Decimal totalAttendees;
    }
    @InvocableMethod(label='Campus Society Statistics')
    public static List<Result> execute(List<Input> inputs){
        List<Result> results = new List<Result>();
        for(Input item: inputs){
            Result r = new Result(); r.completedEvents = 0; r.totalAttendees = 0;
            for(AggregateResult ar : [SELECT COUNT(Id) c, SUM(Total_Attended__c) s FROM Event__c
                WHERE Society__c=:item.societyId AND Status__c='Completed']) {
                r.completedEvents=Decimal.valueOf(String.valueOf(ar.get('c')));
                if(ar.get('s') != null)r.totalAttendees=(Decimal) ar.get('s');
            }
            results.add(r);
        }
        return results;
    }
}
