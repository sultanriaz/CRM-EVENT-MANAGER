public with sharing class FitnessInsightsController {

    public class Insight {
        @AuraEnabled public String severity;
        @AuraEnabled public String title;
        @AuraEnabled public String detail;
    }

    public class TrainerStat implements Comparable {
        @AuraEnabled public String name;
        @AuraEnabled public Integer attended;
        @AuraEnabled public Integer total;
        @AuraEnabled public Decimal rate;
        public Integer compareTo(Object other) {
            TrainerStat o = (TrainerStat) other;
            if (attended == o.attended) return 0;
            return attended > o.attended ? -1 : 1;
        }
    }

    public class RetentionStats {
        @AuraEnabled public Integer priorActive;
        @AuraEnabled public Integer retained;
        @AuraEnabled public Integer atRisk;
        @AuraEnabled public Decimal retentionRate;
    }

    private static Set<Id> attendees(Datetime fromDt, Datetime toDt) {
        Set<Id> ids = new Set<Id>();
        for (AggregateResult ar : [
            SELECT Contact__c c FROM Class_Booking__c
            WHERE Status__c = 'Attended' AND Contact__c != null
            AND Class__r.Start_Date_Time__c >= :fromDt AND Class__r.Start_Date_Time__c < :toDt
            GROUP BY Contact__c
        ]) {
            ids.add((Id) ar.get('c'));
        }
        return ids;
    }

    @AuraEnabled(cacheable=true)
    public static RetentionStats getRetention() {
        Datetime nowDt = Datetime.now();
        Set<Id> recent = attendees(nowDt.addDays(-30), nowDt);
        Set<Id> prior = attendees(nowDt.addDays(-60), nowDt.addDays(-30));
        Set<Id> kept = new Set<Id>(prior);
        kept.retainAll(recent);
        RetentionStats r = new RetentionStats();
        r.priorActive = prior.size();
        r.retained = kept.size();
        r.atRisk = prior.size() - kept.size();
        r.retentionRate = prior.isEmpty() ? 0 : ((Decimal) kept.size() / prior.size()) * 100;
        return r;
    }

    @AuraEnabled(cacheable=true)
    public static List<TrainerStat> getTopTrainers() {
        Datetime nowDt = Datetime.now();
        Map<Id, Integer> attended = new Map<Id, Integer>();
        Map<Id, Integer> total = new Map<Id, Integer>();
        for (AggregateResult ar : [
            SELECT Class__r.Trainer__c t, Status__c s, COUNT(Id) n
            FROM Class_Booking__c
            WHERE Class__r.Start_Date_Time__c < :nowDt AND Class__r.Trainer__c != null
            AND Status__c != 'Cancelled'
            GROUP BY Class__r.Trainer__c, Status__c
        ]) {
            Id t = (Id) ar.get('t');
            Integer n = Integer.valueOf(ar.get('n'));
            total.put(t, (total.containsKey(t) ? total.get(t) : 0) + n);
            if ((String) ar.get('s') == 'Attended') attended.put(t, n);
        }
        Map<Id, Trainer__c> names = new Map<Id, Trainer__c>([
            SELECT Id, Name FROM Trainer__c WHERE Id IN :total.keySet()
        ]);
        List<TrainerStat> out = new List<TrainerStat>();
        for (Id t : total.keySet()) {
            TrainerStat s = new TrainerStat();
            s.name = names.containsKey(t) ? names.get(t).Name.replace('[DEMO] ', '') : 'Trainer';
            s.attended = attended.containsKey(t) ? attended.get(t) : 0;
            s.total = total.get(t);
            s.rate = s.total == 0 ? 0 : ((Decimal) s.attended / s.total) * 100;
            out.add(s);
        }
        out.sort();
        List<TrainerStat> top = new List<TrainerStat>();
        for (Integer i = 0; i < out.size() && i < 5; i++) top.add(out[i]);
        return top;
    }
    private static Decimal revenueBetween(Date fromD, Date toD) {
        AggregateResult ar = [
            SELECT SUM(Amount__c) t FROM Payment__c
            WHERE Status__c = 'Completed' AND Payment_Date__c >= :fromD AND Payment_Date__c < :toD
        ];
        return ar.get('t') == null ? 0 : (Decimal) ar.get('t');
    }

    private static String money(Decimal v) {
        return 'Rs. ' + Decimal.valueOf(Math.round(v)).format();
    }

    private static Insight make(String sev, String title, String detail) {
        Insight i = new Insight();
        i.severity = sev;
        i.title = title;
        i.detail = detail;
        return i;
    }

    @AuraEnabled(cacheable=true)
    public static List<Insight> getInsights() {
        List<Insight> out = new List<Insight>();

        // 1. Revenue month over month
        Date thisStart = Date.today().toStartOfMonth();
        Date lastStart = thisStart.addMonths(-1);
        Decimal cur = revenueBetween(thisStart, thisStart.addMonths(1));
        Decimal prev = revenueBetween(lastStart, thisStart);
        if (prev > 0) {
            Decimal pct = ((cur - prev) / prev * 100).setScale(1);
            if (pct >= 0) {
                out.add(make('good', 'Revenue is up ' + pct + '% this month',
                    money(cur) + ' so far vs ' + money(prev) + ' last month.'));
            } else {
                out.add(make('warn', 'Revenue is down ' + Math.abs(pct) + '% this month',
                    money(cur) + ' so far vs ' + money(prev) + ' last month.'));
            }
        }

        // 2. City leaders and laggards
        List<String> cities = new List<String>{'Lahore', 'Karachi', 'Sahiwal'};
        Map<String, Decimal> rev = new Map<String, Decimal>();
        Decimal all = 0;
        for (AggregateResult ar : [
            SELECT Member__r.MailingCity c, SUM(Amount__c) t FROM Payment__c
            WHERE Status__c = 'Completed' AND Member__r.MailingCity IN :cities
            GROUP BY Member__r.MailingCity
        ]) {
            Decimal v = (Decimal) ar.get('t');
            rev.put((String) ar.get('c'), v);
            all += v;
        }
        if (rev.size() > 1 && all > 0) {
            String topC; String lowC;
            for (String c : rev.keySet()) {
                if (topC == null || rev.get(c) > rev.get(topC)) topC = c;
                if (lowC == null || rev.get(c) < rev.get(lowC)) lowC = c;
            }
            Decimal share = (rev.get(topC) / all * 100).setScale(0);
            out.add(make('info', topC + ' leads the franchise',
                money(rev.get(topC)) + ' in revenue, ' + share + '% of the total.'));
            out.add(make('info', lowC + ' has the lowest revenue',
                money(rev.get(lowC)) + ', which is ' + money(rev.get(topC) - rev.get(lowC)) + ' behind ' + topC + '.'));
        }

        // 3. Members at risk
        RetentionStats r = getRetention();
        if (r.priorActive > 0) {
            if (r.atRisk > 0) {
                out.add(make('warn', r.atRisk + ' members are at risk of churning',
                    'They attended 31 to 60 days ago but not in the last 30. A win-back offer could help.'));
            } else {
                out.add(make('good', 'Every recently active member came back',
                    'All ' + r.priorActive + ' members from the prior window attended again.'));
            }
        }

        // 4. Class fill rates
        Datetime nowDt = Datetime.now();
        Datetime since = nowDt.addDays(-60);
        Map<Id, Class__c> cls = new Map<Id, Class__c>([
            SELECT Id, Name, Capacity__c FROM Class__c
            WHERE Start_Date_Time__c >= :since AND Capacity__c > 0
        ]);
        if (!cls.isEmpty()) {
            Map<Id, Integer> booked = new Map<Id, Integer>();
            for (AggregateResult ar : [
                SELECT Class__c c, COUNT(Id) n FROM Class_Booking__c
                WHERE Class__c IN :cls.keySet() AND Status__c != 'Cancelled'
                GROUP BY Class__c
            ]) {
                booked.put((Id) ar.get('c'), Integer.valueOf(ar.get('n')));
            }
            Id lowId; Id highId; Decimal lowR = 1000; Decimal highR = -1;
            for (Id cid : cls.keySet()) {
                Decimal fill = ((booked.containsKey(cid) ? booked.get(cid) : 0) / cls.get(cid).Capacity__c) * 100;
                if (fill < lowR) { lowR = fill; lowId = cid; }
                if (fill > highR) { highR = fill; highId = cid; }
            }
            if (lowId != null && lowR < 60) {
                out.add(make('warn', cls.get(lowId).Name.replace('[DEMO] ', '') + ' is only ' + lowR.setScale(0) + '% full',
                    'The emptiest class of the last 60 days. Consider promoting it or changing the slot.'));
            }
            if (highId != null && highR >= 60) {
                out.add(make('good', cls.get(highId).Name.replace('[DEMO] ', '') + ' is ' + highR.setScale(0) + '% full',
                    'The most popular class. A second session could capture more demand.'));
            }
        }

        // 5. Members close to a loyalty tier
        Integer near = [
            SELECT COUNT() FROM Loyalty_Points__c
            WHERE (Total_Points__c >= 150 AND Total_Points__c < 200)
            OR (Total_Points__c >= 450 AND Total_Points__c < 500)
            OR (Total_Points__c >= 950 AND Total_Points__c < 1000)
        ];
        if (near > 0) {
            out.add(make('info', near + ' members are within 50 points of a tier upgrade',
                'A small nudge could move them up a loyalty tier.'));
        }

        // 6. Pending payments
        AggregateResult pend = [
            SELECT SUM(Amount__c) t, COUNT(Id) n FROM Payment__c WHERE Status__c = 'Pending'
        ];
        if (pend.get('t') != null) {
            out.add(make('warn', money((Decimal) pend.get('t')) + ' in pending payments',
                Integer.valueOf(pend.get('n')) + (Integer.valueOf(pend.get('n')) == 1 ? ' payment is' : ' payments are') + ' awaiting collection.'));
        }

        return out;
    }
}