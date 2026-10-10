if ([SELECT COUNT() FROM Society__c WHERE Name LIKE '%[DEMO]'] > 0) {
    throw new IllegalArgumentException('Campus demo data already exists.');
}
List<Contact> studs = [SELECT Id FROM Contact WHERE LastName LIKE '%[DEMO]' ORDER BY CreatedDate LIMIT 19];
if (studs.size() < 10) {
    throw new IllegalArgumentException('Fewer than 10 [DEMO] contacts found. Need the fitness-hub demo contacts first.');
}

List<Society__c> soc = new List<Society__c>{
 new Society__c(Name='Tech Society [DEMO]', Faculty_Advisor_Email__c='advisor.tech@cuisahiwal.edu.pk', Founded_Date__c=Date.newInstance(2018,9,1), Category__c='Technical', Active__c=true, Website__c='https://cuisahiwal.edu.pk/tech'),
 new Society__c(Name='Literary Society [DEMO]', Faculty_Advisor_Email__c='advisor.lit@cuisahiwal.edu.pk', Founded_Date__c=Date.newInstance(2016,2,15), Category__c='Literary', Active__c=true, Website__c='https://cuisahiwal.edu.pk/lit'),
 new Society__c(Name='Sports Society [DEMO]', Faculty_Advisor_Email__c='advisor.sports@cuisahiwal.edu.pk', Founded_Date__c=Date.newInstance(2015,8,20), Category__c='Sports', Active__c=true, Website__c='https://cuisahiwal.edu.pk/sports')
};
insert soc;

String[][] ev = new String[][]{
 new String[]{'AI Workshop','0','Lab Block','Workshop','30','500','-20','10'},
 new String[]{'Poetry Evening','1','Auditorium','Talk','100','300','-10','17'},
 new String[]{'Hackathon','0','Online','Live Stream','50','0','5','9'},
 new String[]{'Inter-Dept Cricket','2','Sports Complex','Tournament','40','200','7','14'},
 new String[]{'Book Fair Talk','1','Seminar Hall','Seminar','60','100','12','11'},
 new String[]{'Career Seminar','2','Auditorium','Seminar','200','0','3','10'}
};
List<Event__c> events = new List<Event__c>();
for (Integer i = 0; i < ev.size(); i++) {
  Datetime st = Datetime.newInstance(Date.today().addDays(Integer.valueOf(ev[i][6])), Time.newInstance(Integer.valueOf(ev[i][7]),0,0,0));
  events.add(new Event__c(Name=ev[i][0]+' [DEMO]', Society__c=soc[Integer.valueOf(ev[i][1])].Id, Venue__c=ev[i][2], Session_Type__c=ev[i][3],
    Capacity__c=Decimal.valueOf(ev[i][4]), Ticket_Price__c=Decimal.valueOf(ev[i][5]), Start_Date_Time__c=st, End_Date_Time__c=st.addHours(3),
    Status__c='Open for Registration', Description__c='Demo event for the Campus Events Manager assignment.'));
}
insert events;

String[] depts = new String[]{'CS','SE','EE','BBA','Math'};
String[] skills = new String[]{'Coding','Design;Photography','Public Speaking','Management;Coding','Photography'};
List<Registration__c> regs = new List<Registration__c>();
for (Integer k = 0; k < 20; k++) {
  Integer e = Math.mod(k,6);
  Boolean past = (e == 0 || e == 1);
  regs.add(new Registration__c(Event__c=events[e].Id, Student__c=studs[Math.mod(k,studs.size())].Id, Student_Department__c=depts[Math.mod(k,5)],
    Skills_of_Interest__c=skills[Math.mod(k,5)], Registration_Date__c=Date.today().addDays(-(k+1)), Attended__c=(past && Math.mod(k,4) != 0)));
}
insert regs;

// Now mark the first two events Completed (after registrations exist, so rule 4 doesn't block the inserts above)
events[0].Status__c = 'Completed';
events[1].Status__c = 'Completed';
update new List<Event__c>{events[0], events[1]};

System.debug('CAMPUS SEEDED societies=' + soc.size() + ' events=' + events.size() + ' registrations=' + regs.size());