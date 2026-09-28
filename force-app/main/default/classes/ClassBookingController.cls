/**
 * Read-only support for the public Class Booking screen (Phase 4).
 * Scope is deliberately narrow: list upcoming classes with live seat
 * availability, so the custom booking UI can render a card grid without
 * over-booking a class. No record creation happens here — Flow Builder
 * still owns writing Class Booking / Contact records, per the project's
 * "automation lives in Flow" approach. This is the one Apex exception
 * needed purely to power a hand-built UI; the larger Apex use cases
 * (payment gateway callouts, lead scoring, batch cleanup) remain
 * deferred to Phase 5.
 */
public with sharing class ClassBookingController {

    @AuraEnabled(cacheable=true)
    public static List<ClassOption> getUpcomingClasses() {
        Map<Id, Integer> bookedCountByClass = new Map<Id, Integer>();

        for (AggregateResult ar : [
            SELECT Class__c cls, COUNT(Id) cnt
            FROM Class_Booking__c
            WHERE Status__c = 'Booked'
            GROUP BY Class__c
        ]) {
            bookedCountByClass.put((Id) ar.get('cls'), (Integer) ar.get('cnt'));
        }

        List<ClassOption> options = new List<ClassOption>();

        for (Class__c c : [
            SELECT Id, Name, Start_Date_Time__c, Capacity__c, Description__c, Trainer__r.Name
            FROM Class__c
            WHERE Start_Date_Time__c >= :Datetime.now()
            ORDER BY Start_Date_Time__c ASC
            LIMIT 50
        ]) {
            Integer capacity = c.Capacity__c != null ? Integer.valueOf(c.Capacity__c) : 0;
            Integer booked = bookedCountByClass.containsKey(c.Id) ? bookedCountByClass.get(c.Id) : 0;
            Integer available = capacity - booked;

            ClassOption opt = new ClassOption();
            opt.id = c.Id;
            opt.className = c.Name;
            opt.trainerName = c.Trainer__r != null ? c.Trainer__r.Name : 'TBA';
            opt.startDateTime = c.Start_Date_Time__c;
            opt.description = c.Description__c;
            opt.capacity = capacity;
            opt.seatsBooked = booked;
            opt.seatsAvailable = available;
            opt.isFull = available <= 0;
            options.add(opt);
        }

        return options;
    }

    public class ClassOption {
        @AuraEnabled public Id id;
        @AuraEnabled public String className;
        @AuraEnabled public String trainerName;
        @AuraEnabled public Datetime startDateTime;
        @AuraEnabled public String description;
        @AuraEnabled public Integer capacity;
        @AuraEnabled public Integer seatsBooked;
        @AuraEnabled public Integer seatsAvailable;
        @AuraEnabled public Boolean isFull;
    }
}
