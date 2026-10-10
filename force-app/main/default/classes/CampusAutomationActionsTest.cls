@IsTest
private class CampusAutomationActionsTest {
    @IsTest
    static void calculatesSocietyStatsAndHandlesVenueAlert() {
        Society__c society = new Society__c(
            Name = 'Automation Society',
            Active__c = true,
            Category__c = 'Technical',
            Faculty_Advisor_Email__c = 'automation@cuisahiwal.edu.pk'
        );
        insert society;
        Event__c completedEvent = eventFor(society.Id, 'Completed Event', 'Online', System.now().addDays(-2));
        insert completedEvent;
        Contact student = new Contact(LastName = 'Automation Student');
        insert student;
        insert new Registration__c(
            Event__c = completedEvent.Id,
            Student__c = student.Id,
            Student_Department__c = 'SE',
            Registration_Date__c = Date.today(),
            Attended__c = true
        );
        completedEvent.Status__c = 'Completed';
        update completedEvent;

        CampusSocietyStatsAction.Input statsInput = new CampusSocietyStatsAction.Input();
        statsInput.societyId = society.Id;
        List<CampusSocietyStatsAction.Result> stats = CampusSocietyStatsAction.execute(
            new List<CampusSocietyStatsAction.Input>{statsInput}
        );
        System.assertEquals(1, stats[0].completedEvents);
        System.assertEquals(1, stats[0].totalAttendees);

        Event__c emergencyEvent = eventFor(society.Id, 'Emergency Event', 'Auditorium', System.now().addHours(2));
        emergencyEvent.Ticket_Price__c = 0;
        insert emergencyEvent;
        CampusVenueEmergencyAction.Input alert = new CampusVenueEmergencyAction.Input();
        alert.venue = 'Auditorium';
        alert.message = 'Venue closed for safety testing.';
        Test.startTest();
        CampusVenueEmergencyAction.execute(new List<CampusVenueEmergencyAction.Input>{alert});
        Test.stopTest();
        System.assertEquals('Cancelled', [SELECT Status__c FROM Event__c WHERE Id = :emergencyEvent.Id].Status__c);
        System.assertEquals(1, [SELECT COUNT() FROM FeedItem WHERE ParentId = :emergencyEvent.Id]);
    }

    private static Event__c eventFor(Id societyId, String name, String venue, Datetime startAt) {
        return new Event__c(
            Name = name,
            Society__c = societyId,
            Status__c = 'Open for Registration',
            Capacity__c = 20,
            Venue__c = venue,
            Session_Type__c = venue == 'Online' ? 'Webinar' : 'Seminar',
            Start_Date_Time__c = startAt,
            End_Date_Time__c = startAt.addHours(2)
        );
    }
}
