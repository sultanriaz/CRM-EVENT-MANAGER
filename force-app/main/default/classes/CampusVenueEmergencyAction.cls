public with sharing class CampusVenueEmergencyAction {
    public class Input { @InvocableVariable(required=true) public String venue; @InvocableVariable(required=true) public String message; }
    @InvocableMethod(label='Campus Venue Emergency Handler')
    public static void execute(List<Input> requests){
        Date today=Date.today(); DateTime lower=DateTime.newInstance(today,Time.newInstance(0,0,0,0));
        DateTime upper=lower.addDays(1);
        List<Event__c> affected=new List<Event__c>(); List<FeedItem> posts=new List<FeedItem>();
        for(Input i:requests){
            for(Event__c e:[SELECT Id, Status__c FROM Event__c WHERE Venue__c=:i.venue
              AND Start_Date_Time__c>=:lower AND Start_Date_Time__c<:upper
              AND Status__c IN ('Open for Registration','Planned')]){
                e.Status__c='Cancelled'; affected.add(e);
                FeedItem post = new FeedItem(ParentId=e.Id, Body=i.message); posts.add(post);
            }
        }
        if(!affected.isEmpty()) update affected;
        if(!posts.isEmpty()) insert posts;
    }
}
