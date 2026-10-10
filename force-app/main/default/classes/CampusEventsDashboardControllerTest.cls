@IsTest
private class CampusEventsDashboardControllerTest {
    @TestSetup
    static void setupData() {
        Society__c society = new Society__c(
            Name = 'Dashboard Society',
            Active__c = true,
            Category__c = 'Technical',
            Faculty_Advisor_Email__c = 'dashboard@cuisahiwal.edu.pk'
        );
        insert society;

        Event__c eventRecord = new Event__c(
            Name = 'Dashboard Event',
            Society__c = society.Id,
            Status__c = 'Open for Registration',
            Capacity__c = 20,
            Venue__c = 'Online',
            Session_Type__c = 'Webinar',
            Start_Date_Time__c = System.now().addDays(2),
            End_Date_Time__c = System.now().addDays(2).addHours(2)
        );
        insert eventRecord;

        Contact student = new Contact(LastName = 'Dashboard Student');
        insert student;
        insert new Registration__c(
            Event__c = eventRecord.Id,
            Student__c = student.Id,
            Student_Department__c = 'CS',
            Registration_Date__c = Date.today(),
            Attended__c = true
        );
    }

    @IsTest
    static void returnsRealAggregateAndRecentData() {
        Test.startTest();
        CampusEventsDashboardController.DashboardData result =
            CampusEventsDashboardController.getDashboardData();
        Test.stopTest();

        System.assert(result.totalSocieties >= 1);
        System.assert(result.activeSocieties >= 1);
        System.assert(result.totalEvents >= 1);
        System.assert(result.openEvents >= 1);
        System.assert(result.totalRegistrations >= 1);
        System.assert(result.totalAttendees >= 1);
        System.assert(result.attendanceRate > 0);
        System.assert(!result.upcoming.isEmpty());
        System.assert(!result.recentRegistrations.isEmpty());
        System.assert(!result.eventsByStatus.isEmpty());
        System.assert(!result.registrationsByDepartment.isEmpty());
    }
}
