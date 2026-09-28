public with sharing class FitnessDashboardController {

    public class DashboardMetrics {
        @AuraEnabled public Decimal totalRevenue;
        @AuraEnabled public Integer activeMembers;
        @AuraEnabled public Decimal attendanceRate;
        @AuraEnabled public Integer totalClasses;
        @AuraEnabled public Integer totalTrainers;
        @AuraEnabled public Integer vipMembers;
        @AuraEnabled public Decimal averageMemberValue;
        @AuraEnabled public Integer todaysBookings;
    }

    public class MonthlyRevenue {
        @AuraEnabled public String label;
        @AuraEnabled public Decimal revenue;
        @AuraEnabled public Integer payments;
    }

    public class CityPerformance {
        @AuraEnabled public String city;
        @AuraEnabled public Decimal revenue;
        @AuraEnabled public Integer members;
        @AuraEnabled public Integer bookings;
    }

    public class MemberGrowth {
        @AuraEnabled public String label;
        @AuraEnabled public Integer newMembers;
        @AuraEnabled public Integer totalMembers;
    }

    @AuraEnabled(cacheable=true)
    public static DashboardMetrics getDashboardMetrics() {
        DashboardMetrics metrics = new DashboardMetrics();

        AggregateResult revenue = [
            SELECT SUM(Amount__c) total, AVG(Amount__c) avgValue
            FROM Payment__c
            WHERE Status__c = 'Completed'
        ];
        metrics.totalRevenue = revenue.get('total') == null ? 0 : (Decimal) revenue.get('total');
        metrics.averageMemberValue = revenue.get('avgValue') == null ? 0 : (Decimal) revenue.get('avgValue');

        metrics.activeMembers = [SELECT COUNT() FROM Contact];
        metrics.totalClasses = [SELECT COUNT() FROM Class__c];
        metrics.totalTrainers = [SELECT COUNT() FROM Trainer__c];

        metrics.vipMembers = [
            SELECT COUNT() FROM Loyalty_Points__c
            WHERE Tier__c IN ('Gold','Platinum')
        ];

        Integer totalBookings = [SELECT COUNT() FROM Class_Booking__c];
        if (totalBookings > 0) {
            Integer attended = [SELECT COUNT() FROM Class_Booking__c WHERE Status__c = 'Attended'];
            metrics.attendanceRate = ((Decimal) attended / totalBookings) * 100;
        } else {
            metrics.attendanceRate = 0;
        }

        metrics.todaysBookings = [
            SELECT COUNT() FROM Class_Booking__c
            WHERE Class__r.Start_Date_Time__c = TODAY
            AND Status__c != 'Cancelled'
        ];

        return metrics;
    }
    @AuraEnabled(cacheable=true)
    public static List<MonthlyRevenue> getMonthlyRevenue() {
        Date startMonth = Date.today().addMonths(-5).toStartOfMonth();
        Map<Integer, AggregateResult> byMonth = new Map<Integer, AggregateResult>();
        for (AggregateResult ar : [
            SELECT CALENDAR_YEAR(Payment_Date__c) y, CALENDAR_MONTH(Payment_Date__c) m,
                   SUM(Amount__c) total, COUNT(Id) n
            FROM Payment__c
            WHERE Status__c = 'Completed' AND Payment_Date__c >= :startMonth
            GROUP BY CALENDAR_YEAR(Payment_Date__c), CALENDAR_MONTH(Payment_Date__c)
        ]) {
            byMonth.put(Integer.valueOf(ar.get('y')) * 100 + Integer.valueOf(ar.get('m')), ar);
        }
        List<MonthlyRevenue> result = new List<MonthlyRevenue>();
        for (Integer i = 0; i < 6; i++) {
            Date d = startMonth.addMonths(i);
            MonthlyRevenue row = new MonthlyRevenue();
            row.label = Datetime.newInstance(d.year(), d.month(), 1).format('MMM yyyy');
            AggregateResult ar = byMonth.get(d.year() * 100 + d.month());
            row.revenue = (ar == null || ar.get('total') == null) ? 0 : (Decimal) ar.get('total');
            row.payments = ar == null ? 0 : Integer.valueOf(ar.get('n'));
            result.add(row);
        }
        return result;
    }

    @AuraEnabled(cacheable=true)
    public static List<CityPerformance> getCityPerformance() {
        List<String> cities = new List<String>{'Lahore', 'Karachi', 'Sahiwal'};
        Map<String, Decimal> revenue = new Map<String, Decimal>();
        Map<String, Integer> members = new Map<String, Integer>();
        Map<String, Integer> bookings = new Map<String, Integer>();
        for (AggregateResult ar : [
            SELECT Member__r.MailingCity c, SUM(Amount__c) total
            FROM Payment__c
            WHERE Status__c = 'Completed' AND Member__r.MailingCity IN :cities
            GROUP BY Member__r.MailingCity
        ]) {
            revenue.put((String) ar.get('c'), (Decimal) ar.get('total'));
        }
        for (AggregateResult ar : [
            SELECT MailingCity c, COUNT(Id) n
            FROM Contact
            WHERE MailingCity IN :cities
            GROUP BY MailingCity
        ]) {
            members.put((String) ar.get('c'), Integer.valueOf(ar.get('n')));
        }
        for (AggregateResult ar : [
            SELECT Contact__r.MailingCity c, COUNT(Id) n
            FROM Class_Booking__c
            WHERE Status__c != 'Cancelled' AND Contact__r.MailingCity IN :cities
            GROUP BY Contact__r.MailingCity
        ]) {
            bookings.put((String) ar.get('c'), Integer.valueOf(ar.get('n')));
        }
        List<CityPerformance> result = new List<CityPerformance>();
        for (String city : cities) {
            CityPerformance row = new CityPerformance();
            row.city = city;
            row.revenue = revenue.containsKey(city) ? revenue.get(city) : 0;
            row.members = members.containsKey(city) ? members.get(city) : 0;
            row.bookings = bookings.containsKey(city) ? bookings.get(city) : 0;
            result.add(row);
        }
        return result;
    }

    @AuraEnabled(cacheable=true)
    public static List<MemberGrowth> getMemberGrowth() {
        Date startMonth = Date.today().addMonths(-5).toStartOfMonth();
        Integer running = [SELECT COUNT() FROM Contact WHERE Member_Since__c < :startMonth];
        Map<Integer, Integer> byMonth = new Map<Integer, Integer>();
        for (AggregateResult ar : [
            SELECT CALENDAR_YEAR(Member_Since__c) y, CALENDAR_MONTH(Member_Since__c) m, COUNT(Id) n
            FROM Contact
            WHERE Member_Since__c >= :startMonth
            GROUP BY CALENDAR_YEAR(Member_Since__c), CALENDAR_MONTH(Member_Since__c)
        ]) {
            byMonth.put(Integer.valueOf(ar.get('y')) * 100 + Integer.valueOf(ar.get('m')), Integer.valueOf(ar.get('n')));
        }
        List<MemberGrowth> result = new List<MemberGrowth>();
        for (Integer i = 0; i < 6; i++) {
            Date d = startMonth.addMonths(i);
            Integer key = d.year() * 100 + d.month();
            Integer added = byMonth.containsKey(key) ? byMonth.get(key) : 0;
            running += added;
            MemberGrowth row = new MemberGrowth();
            row.label = Datetime.newInstance(d.year(), d.month(), 1).format('MMM yyyy');
            row.newMembers = added;
            row.totalMembers = running;
            result.add(row);
        }
        return result;
    }
}