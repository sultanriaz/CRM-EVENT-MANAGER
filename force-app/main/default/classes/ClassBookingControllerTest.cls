@isTest
private class ClassBookingControllerTest {

    @testSetup
    static void setup() {
        Trainer__c trainer = new Trainer__c(Name = 'Test Trainer', Specialty__c = 'Yoga');
        insert trainer;

        Class__c upcomingClass = new Class__c(
            Name = 'Test Yoga Class',
            Trainer__c = trainer.Id,
            Start_Date_Time__c = Datetime.now().addDays(2),
            Capacity__c = 2,
            Description__c = 'A relaxing test class.'
        );
        insert upcomingClass;

        Contact member = new Contact(
            FirstName = 'Test',
            LastName = 'Member',
            Email = 'test.member@example.com'
        );
        insert member;

        Class_Booking__c booking = new Class_Booking__c(
            Name = 'Test Member',
            Class__c = upcomingClass.Id,
            Contact__c = member.Id,
            Status__c = 'Booked'
        );
        insert booking;
    }

    @isTest
    static void testGetUpcomingClasses_returnsSeatAvailability() {
        Test.startTest();
        List<ClassBookingController.ClassOption> options = ClassBookingController.getUpcomingClasses();
        Test.stopTest();

        System.assertEquals(1, options.size(), 'Expected exactly one upcoming class.');
        ClassBookingController.ClassOption option = options[0];
        System.assertEquals('Test Yoga Class', option.className);
        System.assertEquals('Test Trainer', option.trainerName);
        System.assertEquals(2, option.capacity);
        System.assertEquals(1, option.seatsBooked);
        System.assertEquals(1, option.seatsAvailable);
        System.assertEquals(false, option.isFull);
    }

    @isTest
    static void testGetUpcomingClasses_marksClassFullWhenNoSeatsRemain() {
        Class__c fullClass = [SELECT Id FROM Class__c LIMIT 1];
        fullClass.Capacity__c = 1;
        update fullClass;

        Test.startTest();
        List<ClassBookingController.ClassOption> options = ClassBookingController.getUpcomingClasses();
        Test.stopTest();

        System.assertEquals(1, options.size());
        System.assertEquals(true, options[0].isFull);
        System.assertEquals(0, options[0].seatsAvailable);
    }

    @isTest
    static void testGetUpcomingClasses_excludesPastClasses() {
        Class__c pastClass = new Class__c(
            Name = 'Past Class',
            Start_Date_Time__c = Datetime.now().addDays(-5),
            Capacity__c = 10
        );
        insert pastClass;

        Test.startTest();
        List<ClassBookingController.ClassOption> options = ClassBookingController.getUpcomingClasses();
        Test.stopTest();

        for (ClassBookingController.ClassOption opt : options) {
            System.assertNotEquals('Past Class', opt.className, 'Past classes should not be returned.');
        }
    }
}
