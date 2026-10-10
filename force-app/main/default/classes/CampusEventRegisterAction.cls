public with sharing class CampusEventRegisterAction {
    public class Input {
        @InvocableVariable(required=true) public Id eventId;
        @InvocableVariable(required=true) public Id studentId;
        @InvocableVariable(required=true) public String department;
        @InvocableVariable public String skills;
    }
    public class Result { @InvocableVariable public Id registrationId; }
    @InvocableMethod(label='Register Campus Student' description='Enforces event capacity using a row lock before creating a Registration.')
    public static List<Result> execute(List<Input> requests) {
        List<Result> out = new List<Result>();
        if(!Schema.sObjectType.Registration__c.isCreateable()
            || !Schema.sObjectType.Registration__c.fields.Event__c.isCreateable()
            || !Schema.sObjectType.Registration__c.fields.Student__c.isCreateable()
            || !Schema.sObjectType.Registration__c.fields.Student_Department__c.isCreateable()
            || !Schema.sObjectType.Registration__c.fields.Skills_of_Interest__c.isCreateable()) {
            throw new AuraHandledException('You do not have permission to create this registration.');
        }
        for(Input i: requests) {
            Event__c e = [SELECT Id, Status__c, Capacity__c, Total_Registrations__c
                          FROM Event__c WHERE Id = :i.eventId WITH USER_MODE FOR UPDATE];
            if(e.Status__c != 'Open for Registration' || e.Capacity__c == null || e.Total_Registrations__c >= e.Capacity__c)
                throw new AuraHandledException('Registration closed: no available seats.');
            Integer existing = [SELECT count() FROM Registration__c
                                WHERE Event__c = :e.Id AND Student__c = :i.studentId WITH USER_MODE];
            if(existing > 0) throw new AuraHandledException('Student already registered for this event.');
            Registration__c r = new Registration__c(Event__c=e.Id, Student__c=i.studentId,
                Student_Department__c=i.department, Skills_of_Interest__c=i.skills);
            Database.insert(r, AccessLevel.USER_MODE);
            Result v = new Result(); v.registrationId = r.Id; out.add(v);
        }
        return out;
    }
}
