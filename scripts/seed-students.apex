List<Lab_Class__c> cl = new List<Lab_Class__c>{
    new Lab_Class__c(Class_Name__c='Mathematics', Max_Strength__c=30),
    new Lab_Class__c(Class_Name__c='Computer Science', Max_Strength__c=25),
    new Lab_Class__c(Class_Name__c='Physics', Max_Strength__c=20)
};
insert cl;
String[][] d = new String[][]{
 new String[]{'Ali Raza','Male','Lahore','Pakistan','2004'},
 new String[]{'Ayesha Khan','Female','Karachi','Pakistan','2005'},
 new String[]{'Hamza Butt','Male','Sahiwal','Pakistan','2003'},
 new String[]{'Sara Malik','Female','Delhi','India','2005'},
 new String[]{'Omar Sheikh','Male','Dubai','United Arab Emirates','2004'},
 new String[]{'Zainab Iqbal','Female','Karachi','Pakistan','2007'}
};
List<Lab_Student__c> st = new List<Lab_Student__c>();
for (Integer i = 0; i < d.size(); i++) {
    st.add(new Lab_Student__c(Name=d[i][0], Gender__c=d[i][1], City__c=d[i][2],
        Country__c=d[i][3], Year_of_Birth__c=Decimal.valueOf(d[i][4]), Class__c=cl[Math.mod(i,3)].Id));
}
insert st;
System.debug('SEEDED classes=' + cl.size() + ' students=' + st.size());