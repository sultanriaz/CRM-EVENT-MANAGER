@IsTest
private class CampusEventRegisterActionTest {
 @IsTest static void rejectsClosedEvent(){
  Society__c s=new Society__c(Name='Test Society',Faculty_Advisor_Email__c='t@cuisahiwal.edu.pk',Active__c=true);insert s;
  Event__c e=new Event__c(Name='Closed Test',Society__c=s.Id,Status__c='Completed',Capacity__c=20,Venue__c='Online',
                          Start_Date_Time__c=System.now().addDays(-2),End_Date_Time__c=System.now().addDays(-1));insert e;
  Contact c=new Contact(LastName='Unit Test Student');insert c;
  CampusEventRegisterAction.Input input=new CampusEventRegisterAction.Input();input.eventId=e.Id;input.studentId=c.Id;input.department='SE';
  Test.startTest(); Boolean denied=false;
  try {CampusEventRegisterAction.execute(new List<CampusEventRegisterAction.Input>{input});}
  catch(Exception ex){denied=true;}
  Test.stopTest(); System.assertEquals(true,denied,'Closed events cannot accept registration');
 }

 @IsTest static void registersOpenEventAndRejectsDuplicate(){
  Society__c s=new Society__c(Name='Open Society',Faculty_Advisor_Email__c='open@cuisahiwal.edu.pk',Active__c=true);insert s;
  Event__c e=new Event__c(Name='Open Test',Society__c=s.Id,Status__c='Open for Registration',Capacity__c=20,Venue__c='Online',
                          Session_Type__c='Webinar',Start_Date_Time__c=System.now().addDays(1),End_Date_Time__c=System.now().addDays(1).addHours(2));insert e;
  Contact c=new Contact(LastName='Open Test Student');insert c;
  CampusEventRegisterAction.Input input=new CampusEventRegisterAction.Input();input.eventId=e.Id;input.studentId=c.Id;
  input.department='CS';input.skills='Coding;Design';
  Test.startTest();
  List<CampusEventRegisterAction.Result> result=CampusEventRegisterAction.execute(new List<CampusEventRegisterAction.Input>{input});
  Boolean duplicateDenied=false;
  try {CampusEventRegisterAction.execute(new List<CampusEventRegisterAction.Input>{input});}
  catch(Exception ex){duplicateDenied=true;}
  Test.stopTest();
  System.assertNotEquals(null,result[0].registrationId);
  System.assertEquals(true,duplicateDenied,'A student cannot register twice for one event');
 }
}
