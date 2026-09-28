if ([SELECT COUNT() FROM Trainer__c WHERE Name LIKE '[DEMO]%'] > 0) {
    throw new IllegalArgumentException('DEMO data already exists. Run cleanup-demo.apex first.');
}

// ---------- Members: 8 Lahore, 6 Karachi, 5 Sahiwal ----------
List<List<String>> people = new List<List<String>>{
    new List<String>{'Ali','Raza','Lahore'}, new List<String>{'Ayesha','Siddiqui','Lahore'},
    new List<String>{'Hamza','Butt','Lahore'}, new List<String>{'Fatima','Noor','Lahore'},
    new List<String>{'Usman','Sheikh','Lahore'}, new List<String>{'Sana','Malik','Lahore'},
    new List<String>{'Bilal','Chaudhry','Lahore'}, new List<String>{'Hira','Javed','Lahore'},
    new List<String>{'Ahmed','Memon','Karachi'}, new List<String>{'Zainab','Qureshi','Karachi'},
    new List<String>{'Faizan','Ansari','Karachi'}, new List<String>{'Mariam','Hashmi','Karachi'},
    new List<String>{'Danish','Baig','Karachi'}, new List<String>{'Rabia','Khan','Karachi'},
    new List<String>{'Imran','Cheema','Sahiwal'}, new List<String>{'Nadia','Gill','Sahiwal'},
    new List<String>{'Kamran','Warraich','Sahiwal'}, new List<String>{'Sidra','Bhatti','Sahiwal'},
    new List<String>{'Tahir','Rana','Sahiwal'}
};
String[] codes = new String[]{'00','21','33','45','01'};
List<Contact> members = new List<Contact>();
for (Integer i = 0; i < people.size(); i++) {
    String phone = '03' + codes[Math.mod(i, 5)] + '-' + String.valueOf(3100000 + i * 7311);
    members.add(new Contact(
        FirstName = people[i][0], LastName = people[i][1] + ' [DEMO]',
        MailingCity = people[i][2], Phone = phone, MobilePhone = phone,
        Email = people[i][0].toLowerCase() + '.' + people[i][1].toLowerCase() + '.demo' + i + '@example.invalid'));
}
insert members;

// ---------- Trainers ----------
List<List<String>> tdata = new List<List<String>>{
    new List<String>{'Ayesha Tariq','Yoga','8'}, new List<String>{'Hassan Ali','Strength Training','12'},
    new List<String>{'Sara Iqbal','Zumba','5'}, new List<String>{'Omar Farooq','CrossFit','9'},
    new List<String>{'Maha Zafar','Pilates','6'}, new List<String>{'Rizwan Ahmed','Spin','7'}
};
List<Trainer__c> trainers = new List<Trainer__c>();
for (List<String> t : tdata) {
    trainers.add(new Trainer__c(
        Name = '[DEMO] ' + t[0], Specialty__c = t[1],
        Years_of_Experience__c = Decimal.valueOf(t[2]),
        Biography__c = 'Certified ' + t[1] + ' coach with ' + t[2] + ' years of experience.'));
}
insert trainers;

// ---------- Classes: 12 past (last ~6 months) + 3 upcoming ----------
Integer[] offsets = new Integer[]{-170,-155,-140,-125,-110,-95,-80,-65,-50,-35,-20,-6,2,5,9};
Integer[] hours = new Integer[]{6,7,9,17,18,19};
Integer[] caps = new Integer[]{15,20,25,30};
List<Class__c> classes = new List<Class__c>();
for (Integer i = 0; i < offsets.size(); i++) {
    Trainer__c tr = trainers[Math.mod(i, trainers.size())];
    classes.add(new Class__c(
        Name = '[DEMO] ' + tdata[Math.mod(i, 6)][1] + ' ' + (i + 1),
        Trainer__c = tr.Id,
        Capacity__c = caps[Math.mod(i, 4)],
        Description__c = 'Demo class for dashboard testing.',
        Start_Date_Time__c = Datetime.newInstance(Date.today().addDays(offsets[i]),
                                                  Time.newInstance(hours[Math.mod(i, 6)], 0, 0, 0))));
}
insert classes;

// ---------- Bookings (6-11 per class, always under capacity) ----------
List<Class_Booking__c> bookings = new List<Class_Booking__c>();
Integer bn = 0;
for (Integer i = 0; i < classes.size(); i++) {
    Integer n = 6 + Math.mod(i * 3, 6);
    for (Integer j = 0; j < n; j++) {
        Integer k = Math.mod(i + j, 8);
        String st = offsets[i] > 0 ? 'Booked' : (k == 0 ? 'No-Show' : (k == 1 ? 'Cancelled' : 'Attended'));
        bn++;
        bookings.add(new Class_Booking__c(
            Name = '[DEMO] Booking ' + bn, Class__c = classes[i].Id,
            Contact__c = members[Math.mod(i * 3 + j, members.size())].Id, Status__c = st));
    }
}
insert bookings;

// ---------- Payments: members join gradually, 5 plan sizes (PKR) ----------
Integer[] plans = new Integer[]{5000, 8000, 12000, 25000, 45000};
List<Payment__c> payments = new List<Payment__c>();
Integer pn = 0;
for (Integer m = 0; m < members.size(); m++) {
    for (Integer k = Math.mod(m, 6); k < 6; k++) {
        Date d = Date.today().addMonths(k - 5).toStartOfMonth().addDays(2 + Math.mod(m * 3, 24));
        if (d > Date.today()) { d = Date.today(); }
        Integer s = Math.mod(m * 7 + k * 3, 17);
        String status = s == 0 ? 'Failed' : (s == 1 ? 'Refunded' : ((s == 2 && k == 5) ? 'Pending' : 'Completed'));
        pn++;
        payments.add(new Payment__c(
            Name = '[DEMO] Payment ' + pn, Member__c = members[m].Id,
            Amount__c = plans[Math.mod(m, 5)], Status__c = status, Payment_Date__c = d));
    }
}
insert payments;

// ---------- Loyalty (same thresholds as LoyaltyService) ----------
List<Loyalty_Points__c> loyalty = new List<Loyalty_Points__c>();
for (Integer m = 0; m < members.size(); m++) {
    Integer pts = Math.mod(m * 173, 1300) + 30;
    loyalty.add(new Loyalty_Points__c(
        Name = '[DEMO] Loyalty ' + (m + 1), Contact__c = members[m].Id,
        Total_Points__c = pts, Points_Earned__c = pts,
        Loyalty_Date__c = Date.today().addDays(-Math.mod(m * 11, 60)),
        Tier__c = pts >= 1000 ? 'Platinum' : (pts >= 500 ? 'Gold' : (pts >= 200 ? 'Silver' : 'Bronze'))));
}
insert loyalty;

System.debug('SEEDED members=' + members.size() + ' trainers=' + trainers.size() +
    ' classes=' + classes.size() + ' bookings=' + bookings.size() +
    ' payments=' + payments.size() + ' loyalty=' + loyalty.size());