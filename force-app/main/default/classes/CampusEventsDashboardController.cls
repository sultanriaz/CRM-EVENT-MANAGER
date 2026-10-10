public with sharing class CampusEventsDashboardController {
    public class MetricItem {
        @AuraEnabled public String label { get; set; }
        @AuraEnabled public Integer value { get; set; }
        public MetricItem(String label, Integer value) {
            this.label = label;
            this.value = value;
        }
    }

    public class EventItem {
        @AuraEnabled public Id id { get; set; }
        @AuraEnabled public String name { get; set; }
        @AuraEnabled public Datetime startsAt { get; set; }
        @AuraEnabled public String venue { get; set; }
        @AuraEnabled public String status { get; set; }
        @AuraEnabled public Decimal seatsRemaining { get; set; }
    }

    public class RegistrationItem {
        @AuraEnabled public Id id { get; set; }
        @AuraEnabled public String registrationNumber { get; set; }
        @AuraEnabled public String studentName { get; set; }
        @AuraEnabled public String eventName { get; set; }
        @AuraEnabled public Date registeredOn { get; set; }
        @AuraEnabled public Boolean attended { get; set; }
    }

    public class DashboardData {
        @AuraEnabled public Integer totalSocieties { get; set; }
        @AuraEnabled public Integer activeSocieties { get; set; }
        @AuraEnabled public Integer totalEvents { get; set; }
        @AuraEnabled public Integer upcomingEvents { get; set; }
        @AuraEnabled public Integer openEvents { get; set; }
        @AuraEnabled public Integer totalRegistrations { get; set; }
        @AuraEnabled public Integer totalAttendees { get; set; }
        @AuraEnabled public Decimal attendanceRate { get; set; }
        @AuraEnabled public List<EventItem> upcoming { get; set; }
        @AuraEnabled public List<RegistrationItem> recentRegistrations { get; set; }
        @AuraEnabled public List<MetricItem> eventsByStatus { get; set; }
        @AuraEnabled public List<MetricItem> registrationsByDepartment { get; set; }
    }

    @AuraEnabled(cacheable=true)
    public static DashboardData getDashboardData() {
        assertReadable();
        DashboardData data = new DashboardData();
        data.totalSocieties = [SELECT COUNT() FROM Society__c WITH USER_MODE];
        data.activeSocieties = [SELECT COUNT() FROM Society__c WHERE Active__c = true WITH USER_MODE];
        data.totalEvents = [SELECT COUNT() FROM Event__c WITH USER_MODE];
        data.upcomingEvents = [SELECT COUNT() FROM Event__c WHERE Start_Date_Time__c >= TODAY AND Status__c != 'Cancelled' WITH USER_MODE];
        data.openEvents = [SELECT COUNT() FROM Event__c WHERE Status__c = 'Open for Registration' WITH USER_MODE];
        data.totalRegistrations = [SELECT COUNT() FROM Registration__c WITH USER_MODE];
        data.totalAttendees = [SELECT COUNT() FROM Registration__c WHERE Attended__c = true WITH USER_MODE];
        data.attendanceRate = data.totalRegistrations == 0
            ? 0
            : (Decimal.valueOf(data.totalAttendees) * 100 / data.totalRegistrations).setScale(1);

        data.upcoming = new List<EventItem>();
        for (Event__c eventRecord : [
            SELECT Id, Name, Start_Date_Time__c, Venue__c, Status__c, Seats_Remaining__c
            FROM Event__c
            WHERE Start_Date_Time__c >= TODAY AND Status__c != 'Cancelled'
            WITH USER_MODE
            ORDER BY Start_Date_Time__c ASC
            LIMIT 6
        ]) {
            EventItem item = new EventItem();
            item.id = eventRecord.Id;
            item.name = eventRecord.Name;
            item.startsAt = eventRecord.Start_Date_Time__c;
            item.venue = eventRecord.Venue__c;
            item.status = eventRecord.Status__c;
            item.seatsRemaining = eventRecord.Seats_Remaining__c;
            data.upcoming.add(item);
        }

        data.recentRegistrations = new List<RegistrationItem>();
        for (Registration__c registration : [
            SELECT Id, Name, Student__r.Name, Event__r.Name, Registration_Date__c, Attended__c
            FROM Registration__c
            WITH USER_MODE
            ORDER BY CreatedDate DESC
            LIMIT 6
        ]) {
            RegistrationItem item = new RegistrationItem();
            item.id = registration.Id;
            item.registrationNumber = registration.Name;
            item.studentName = registration.Student__r == null ? 'Student not assigned' : registration.Student__r.Name;
            item.eventName = registration.Event__r == null ? 'Event not assigned' : registration.Event__r.Name;
            item.registeredOn = registration.Registration_Date__c;
            item.attended = registration.Attended__c;
            data.recentRegistrations.add(item);
        }

        data.eventsByStatus = new List<MetricItem>();
        for (AggregateResult result : [
            SELECT Status__c status, COUNT(Id) total
            FROM Event__c
            WITH USER_MODE
            GROUP BY Status__c
            ORDER BY COUNT(Id) DESC
        ]) {
            data.eventsByStatus.add(new MetricItem((String) result.get('status'), (Integer) result.get('total')));
        }

        data.registrationsByDepartment = new List<MetricItem>();
        for (AggregateResult result : [
            SELECT Student_Department__c department, COUNT(Id) total
            FROM Registration__c
            WITH USER_MODE
            GROUP BY Student_Department__c
            ORDER BY COUNT(Id) DESC
        ]) {
            String department = (String) result.get('department');
            data.registrationsByDepartment.add(new MetricItem(
                String.isBlank(department) ? 'Not specified' : department,
                (Integer) result.get('total')
            ));
        }
        return data;
    }

    private static void assertReadable() {
        if (!Schema.sObjectType.Society__c.isAccessible()
            || !Schema.sObjectType.Event__c.isAccessible()
            || !Schema.sObjectType.Registration__c.isAccessible()) {
            throw new AuraHandledException('You do not have access to Campus Events dashboard data.');
        }
    }
}
