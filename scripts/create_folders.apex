Folder rf = new Folder(Name = 'Community Fitness Reports', DeveloperName = 'Community_Fitness_Reports', Type = 'Report', AccessType = 'Public');
insert rf;
Folder df = new Folder(Name = 'Community Fitness Dashboards', DeveloperName = 'Community_Fitness_Dashboards', Type = 'Dashboard', AccessType = 'Public');
insert df;
System.debug('Report Folder: ' + rf.Id + ', Dashboard Folder: ' + df.Id);
