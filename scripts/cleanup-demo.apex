delete [SELECT Id FROM Loyalty_Points__c WHERE Name LIKE '[DEMO]%'];
delete [SELECT Id FROM Payment__c WHERE Name LIKE '[DEMO]%'];
delete [SELECT Id FROM Class_Booking__c WHERE Name LIKE '[DEMO]%'];
delete [SELECT Id FROM Class__c WHERE Name LIKE '[DEMO]%'];
delete [SELECT Id FROM Trainer__c WHERE Name LIKE '[DEMO]%'];
delete [SELECT Id FROM Contact WHERE LastName LIKE '%[DEMO]'];
System.debug('DEMO data removed');