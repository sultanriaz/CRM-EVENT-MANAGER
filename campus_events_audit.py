#!/usr/bin/env python3
"""Campus Events Manager: read-only Salesforce CLI + local Salesforce DX source audit.

Requirements are derived from CSC315 Assignment #2. Uses Python standard library and sf CLI.
No data modifications, deployments, flow activations, metadata overwrites, or org exports.
"""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = '{http://soap.sforce.com/2006/04/metadata}'
BASE = 'force-app/main/default/'
ORG_DEFAULT = 'superior7891_61lsg4rtgvkm@gmail.com'

class Source:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.zip = zipfile.ZipFile(self.root) if self.root.is_file() and zipfile.is_zipfile(self.root) else None
        if self.zip:
            roots = sorted(set(n.split('/')[0] for n in self.zip.namelist() if n.endswith('sfdx-project.json')))
            self.prefix = (roots[0] + '/') if roots else ''
            self.names = set(self.zip.namelist())
        else:
            if not (self.root / 'sfdx-project.json').is_file():
                matches = list(self.root.glob('*/sfdx-project.json'))
                if len(matches) == 1:
                    self.root = matches[0].parent
            if not (self.root / 'sfdx-project.json').is_file():
                raise FileNotFoundError('Provide the extracted Salesforce DX project root or its .zip file.')

    def has(self, rel):
        if not rel:
            return False
        p = BASE + rel
        return (self.prefix + p) in self.names if self.zip else (self.root / p).is_file()

    def read(self, rel):
        if not self.has(rel):
            return ''
        return (self.zip.read(self.prefix + BASE + rel).decode('utf-8-sig', errors='replace')
                if self.zip else (self.root / BASE / rel).read_text(encoding='utf-8-sig', errors='replace'))

    def has_any(self, prefix, suffix=''):
        prefix = BASE + prefix
        if self.zip:
            return any(n.startswith(self.prefix + prefix) and n.endswith(suffix) and not n.endswith('/') for n in self.names)
        return any(p.is_file() for p in (self.root / prefix).rglob('*'+suffix)) if (self.root / prefix).exists() else False


def xml_value(src, rel, tag):
    body = src.read(rel)
    if not body:
        return ''
    try:
        x = ET.fromstring(body)
        t = x.find('.//' + NS + tag)
        return '' if t is None or t.text is None else t.text.strip()
    except ET.ParseError:
        return ''


def check(src, rel, must_contain=None):
    if not src.has(rel):
        return 'MISSING'
    if must_contain is None:
        return 'PRESENT'
    body = src.read(rel)
    return 'PRESENT' if all(s in body for s in must_contain) else 'PARTIAL'


def req(task, item, path, mtype=None, member=None, needle=None, note=''):
    return dict(task=task, requirement=item, path=path, metadata_type=mtype or '', metadata_member=member or '', needle=needle, note=note)


def build_requirements():
    r=[]
    def add(*a, **kw):r.append(req(*a,**kw))
    add('1','Lightning app with Console navigation and six tabs','applications/Campus_Events_Manager.app-meta.xml','CustomApplication','Campus_Events_Manager',
        ['<navType>Console</navType>','<tabs>Society__c</tabs>','<tabs>Event__c</tabs>','<tabs>Registration__c</tabs>','<tabs>standard-Contact</tabs>','<tabs>standard-report</tabs>','<tabs>standard-Dashboard</tabs>'])
    for obj in ['Society__c','Event__c','Registration__c']:
        add('1',f'Custom object {obj}',f'objects/{obj}/{obj}.object-meta.xml','CustomObject',obj)
        add('1',f'Custom tab {obj}',f'tabs/{obj}.tab-meta.xml','CustomTab',obj)
    soc=['Faculty_Advisor_Email__c','Founded_Date__c','Category__c','Active__c','Website__c']
    event=['Start_Date_Time__c','End_Date_Time__c','Venue__c','Capacity__c','Ticket_Price__c','Status__c','Description__c']
    registration=['Student_Department__c','Registration_Date__c','Attended__c','Skills_of_Interest__c']
    for obj,fields in [('Society__c',soc),('Event__c',event),('Registration__c',registration)]:
        for field in fields:
            add('1',f'{obj}.{field}',f'objects/{obj}/fields/{field}.field-meta.xml','CustomField',f'{obj}.{field}')
    add('1','Global value set Campus_Departments','globalValueSets/Campus_Departments.globalValueSet-meta.xml','GlobalValueSet','Campus_Departments',
        ['<fullName>CS</fullName>','<fullName>SE</fullName>','<fullName>EE</fullName>','<fullName>BBA</fullName>','<fullName>Math</fullName>'])
    add('1','Student Department uses global value set','objects/Registration__c/fields/Student_Department__c.field-meta.xml','CustomField','Registration__c.Student_Department__c',['<valueSetName>Campus_Departments</valueSetName>'])
    add('1','Dependent Session Type controlled by Venue','objects/Event__c/fields/Session_Type__c.field-meta.xml','CustomField','Event__c.Session_Type__c',
        ['<controllingField>Venue__c</controllingField>','<valueSettings>'])
    add('1','Event to Society Lookup','objects/Event__c/fields/Society__c.field-meta.xml','CustomField','Event__c.Society__c',['<type>Lookup</type>','<referenceTo>Society__c</referenceTo>'])
    add('1','Registration to Event Master-Detail','objects/Registration__c/fields/Event__c.field-meta.xml','CustomField','Registration__c.Event__c',['<type>MasterDetail</type>','<referenceTo>Event__c</referenceTo>'])
    add('1','Registration to Contact Lookup','objects/Registration__c/fields/Student__c.field-meta.xml','CustomField','Registration__c.Student__c',['<type>Lookup</type>','<referenceTo>Contact</referenceTo>'])
    for field in ['Total_Registrations__c','Total_Attended__c']:
        add('1',f'Event {field} rollup',f'objects/Event__c/fields/{field}.field-meta.xml','CustomField',f'Event__c.{field}', ['<type>Summary</type>'])
    add('1','Event layout Details / Schedule / Capacity sections','layouts/Event__c-Event Layout.layout-meta.xml','Layout','Event__c-Event Layout',note='Must include Registrations related list with Student, Department and Attended columns; layout name may differ.')
    add('1','Upcoming Open Events list view','objects/Event__c/listViews/Upcoming_Open_Events.listView-meta.xml','ListView','Event__c.Upcoming_Open_Events')
    add('1',"My Society's Events properly scoped",'objects/Event__c/listViews/My_Societys_Events.listView-meta.xml','ListView','Event__c.My_Societys_Events',
        ['<filterScope>Everything</filterScope>'],note='Current owner-only Mine filter does not establish same-society filtering; check intended access model.')
    for f in ['Seats_Remaining__c','Event_Duration_Hours__c','Fill_Status__c']:
        add('2',f'Event formula {f}',f'objects/Event__c/fields/{f}.field-meta.xml','CustomField',f'Event__c.{f}',['<formula>'])
    for obj,n in [('Event__c','End_After_Start'),('Event__c','Capacity_Range'),('Event__c','Ticket_Price_Required'),('Registration__c','Event_Must_Be_Open'),('Society__c','Advisor_Email_Domain')]:
        add('2',f'Active validation rule {n}',f'objects/{obj}/validationRules/{n}.validationRule-meta.xml','ValidationRule',f'{obj}.{n}',['<active>true</active>','<errorMessage>'])
    add('2','Contact email matching rule','matchingRules/Contact.matchingRule-meta.xml','MatchingRules','Contact',['<fieldName>Email</fieldName>'])
    add('2','Contact First + Last + Phone matching rule','matchingRules/Contact.matchingRule-meta.xml','MatchingRules','Contact',['<fieldName>FirstName</fieldName>','<fieldName>LastName</fieldName>','<fieldName>Phone</fieldName>'])
    add('2','Contact duplicate rule blocks identical email','duplicateRules/Contact.Email_Block.duplicateRule-meta.xml','DuplicateRule','Contact.Email_Block',note='Check actual rule name in org; matching rules alone do not block duplicates.')
    add('2','Contact duplicate rule warns name + phone','duplicateRules/Contact.Name_Phone_Warn.duplicateRule-meta.xml','DuplicateRule','Contact.Name_Phone_Warn',note='Rule name may differ; needs allow-with-alert behavior.')
    add('2','Lightning registration email template','email/unfiled$public/Event_Registration_Confirmation.email-meta.xml','EmailTemplate','unfiled$public/Event_Registration_Confirmation',
        ['<uiType>SFX</uiType>'],note='Present template is legacy Aloha/text; inspect Lightning Email Template requirement and merge fields.')
    add('2','Registration email alert','workflows/Registration__c.workflow-meta.xml','Workflow','Registration__c',['<alerts>','<template>unfiled$public/Event_Registration_Confirmation</template>'])
    for f in ['Academic_Event','Recreational_Event']:
        add('3',f'Event record type {f}',f'objects/Event__c/recordTypes/{f}.recordType-meta.xml','RecordType',f'Event__c.{f}', ['<active>true</active>','<picklist>Session_Type__c</picklist>'])
    add('3','Academic Event dedicated layout','layouts/Event__c-Academic Event Layout.layout-meta.xml','Layout','Event__c-Academic Event Layout',note='Check profile record-type layout assignments; names can differ.')
    add('3','Recreational Event dedicated layout','layouts/Event__c-Recreational Event Layout.layout-meta.xml','Layout','Event__c-Recreational Event Layout',note='Check profile record-type layout assignments; names can differ.')
    add('3','Event feed tracking enabled','objects/Event__c/Event__c.object-meta.xml','CustomObject','Event__c',['<enableFeeds>true</enableFeeds>'])
    for f in ['Status__c','Capacity__c']:
        add('3',f'Event {f} feed tracking',f'objects/Event__c/fields/{f}.field-meta.xml','CustomField',f'Event__c.{f}',['<trackFeedHistory>true</trackFeedHistory>'])
    add('3','Registration Attended field history','objects/Registration__c/fields/Attended__c.field-meta.xml','CustomField','Registration__c.Attended__c',['<trackHistory>true</trackHistory>'])
    for f in ['Campus_Events_Admin','Society_President','Volunteer']:
        add('3',f'Permission set {f}',f'permissionsets/{f}.permissionset-meta.xml','PermissionSet',f)
    for f in ['Student_Affairs_Officer','Society_President','Volunteer']:
        add('3',f'Role {f}',f'roles/{f}.role-meta.xml','Role',f)
    add('3','Society OWD Public Read Only','objects/Society__c/Society__c.object-meta.xml','CustomObject','Society__c',['<sharingModel>Read</sharingModel>'])
    add('3','Event OWD Private','objects/Event__c/Event__c.object-meta.xml','CustomObject','Event__c',['<sharingModel>Private</sharingModel>'])
    add('3','Volunteer read sharing of Open Events','sharingRules/Event__c.sharingRules-meta.xml','SharingRules','Event__c',
        ['<fullName>Volunteers_Read_Open_Events</fullName>','<value>Open for Registration</value>','<accessLevel>Read</accessLevel>'])
    add('4','Report type outer join includes events with zero registrations','reportTypes/Events_with_Registrations.reportType-meta.xml','ReportType','Events_with_Registrations',['<outerJoin>true</outerJoin>'])
    for f,needle in [('Registrations_by_Department',['<format>Summary</format>','<chart>']),
        ('Event_Attendance_Rate',['<format>Summary</format>','<summaryFormula>']),
        ('Society_vs_Event_Status',['<format>Matrix</format>','<groupingsAcross>']),
        ('Upcoming_Events_This_Month',['<format>Tabular</format>','<value>THIS_MONTH</value>','<value>Cancelled</value>'])]:
        add('4',f'Report {f}',f'reports/Campus_Events/{f}.report-meta.xml','Report',f'Campus_Events/{f}',needle)
    add('4','Student Affairs Dashboard (gauge, donut, bar, table; filter)','dashboards/Campus_Events/Student_Affairs_Dashboard.dashboard-meta.xml','Dashboard','Campus_Events/Student_Affairs_Dashboard',
        ['<dashboardType>SpecifiedUser</dashboardType>'],note='Verify four correct component types, dashboard filter and running user; file/name may differ.')
    for f in ['Quick_Event_Registration','Registration_After_Save','Registration_Before_Save',
              'Daily_Event_Closer','Calculate_Society_Stats','Venue_Emergency_Handler']:
        add('5',f'Flow {f}',f'flows/{f}.flow-meta.xml','Flow',f, note='Need active flow, correct trigger/timing/logic, fault paths and debug evidence.')
    add('5','Platform event Venue_Alert__e','objects/Venue_Alert__e/Venue_Alert__e.object-meta.xml','CustomObject','Venue_Alert__e')
    for f in ['Venue__c','Message__c']:
        add('5',f'Platform alert field {f}',f'objects/Venue_Alert__e/fields/{f}.field-meta.xml','CustomField',f'Venue_Alert__e.{f}')
    add('6','Written assignment answers and screenshot evidence','docs/campus-events-assignment-report.md',note='Five short answers + navigation, rollup and security explanations + proof screenshots; filename is illustrative.')
    return r

META_TYPES=['CustomApplication','CustomObject','CustomTab','CustomField','GlobalValueSet','ValidationRule',
            'ListView','RecordType','Layout','FlexiPage','MatchingRules','DuplicateRule','EmailTemplate','Workflow',
            'PermissionSet','Role','SharingRules','ReportType','Report','Dashboard','Flow']

QUERIES={
 'societies_count': "SELECT COUNT() FROM Society__c",
 'events_count': "SELECT COUNT() FROM Event__c",
 'registrations_count': "SELECT COUNT() FROM Registration__c",
 'contacts_count': "SELECT COUNT() FROM Contact",
 'active_users_count': "SELECT COUNT() FROM User WHERE IsActive = true",
 'events_by_status': "SELECT Status__c, COUNT(Id) Total FROM Event__c GROUP BY Status__c",
 'events_by_venue': "SELECT Venue__c, COUNT(Id) Total FROM Event__c GROUP BY Venue__c",
 'registrations_by_department': "SELECT Student_Department__c, COUNT(Id) Total FROM Registration__c GROUP BY Student_Department__c",
 'attendance_totals': "SELECT Attended__c, COUNT(Id) Total FROM Registration__c GROUP BY Attended__c",
 'societies_by_category': "SELECT Category__c, COUNT(Id) Total FROM Society__c GROUP BY Category__c",
 'registrations_per_event': "SELECT Event__c, COUNT(Id) Total FROM Registration__c GROUP BY Event__c",
 'lightning_email_templates': "SELECT DeveloperName, Name, UiType, TemplateType FROM EmailTemplate WHERE Name = 'Event Registration Confirmation' LIMIT 10",
 'events_without_registrations': "SELECT COUNT() FROM Event__c WHERE Total_Registrations__c = 0",
 'events_over_capacity': "SELECT COUNT() FROM Event__c WHERE Seats_Remaining__c < 0",
 'events_date_audit': "SELECT Id, Start_Date_Time__c, End_Date_Time__c FROM Event__c LIMIT 2000",
 'events_invalid_capacity': "SELECT COUNT() FROM Event__c WHERE Capacity__c < 10 OR Capacity__c > 1000",
 'events_missing_ticket_price': "SELECT COUNT() FROM Event__c WHERE Venue__c != 'Online' AND Ticket_Price__c = null",
 'societies_with_stats': "SELECT Name, Completed_Events__c, Total_Attendees__c FROM Society__c LIMIT 200",
 'event_rollup_snapshot': "SELECT Name, Status__c, Capacity__c, Total_Registrations__c, Total_Attended__c, Seats_Remaining__c FROM Event__c LIMIT 200",
 'society_officer_users': "SELECT COUNT() FROM User WHERE IsActive = true AND UserRole.Name = 'Student Affairs Officer'",
 'society_president_users': "SELECT COUNT() FROM User WHERE IsActive = true AND UserRole.Name = 'Society President'",
 'volunteer_users': "SELECT COUNT() FROM User WHERE IsActive = true AND UserRole.Name = 'Volunteer'",
 'admin_permission_assignments': "SELECT COUNT() FROM PermissionSetAssignment WHERE PermissionSet.Name = 'Campus_Events_Admin'",
 'president_permission_assignments': "SELECT COUNT() FROM PermissionSetAssignment WHERE PermissionSet.Name = 'Society_President'",
 'volunteer_permission_assignments': "SELECT COUNT() FROM PermissionSetAssignment WHERE PermissionSet.Name = 'Volunteer'",
}

def run_sf(args, timeout=100):
    try:
        p = subprocess.run(['sf'] + args + ['--json'], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as ex:
        return {'status': 1, 'error': f'{type(ex).__name__}: {ex}', 'result': None}
    try:
        payload = json.loads(p.stdout)
    except json.JSONDecodeError:
        payload = {'status': p.returncode or 1,'error': (p.stderr or p.stdout)[-1200:], 'result': None}
    if p.returncode and not payload.get('error'):
        payload['error'] = payload.get('message', p.stderr[-1000:])
    return payload

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + '\n', encoding='utf-8')

def files_from_meta(res):
    val = res.get('result')
    if isinstance(val, list):
        records=val
    elif isinstance(val, dict):
        records=val.get('metadataObjects') or val.get('components') or val.get('records') or []
        if isinstance(records, dict):records=[records]
    else:records=[]
    return sorted(set(str(x.get('fullName','')) for x in records if isinstance(x,dict) and x.get('fullName')))

def count_from_query(data):
    try:
        records=data.get('result',{}).get('records',[])
        if not records:return None
        row=records[0]
        for key in ('expr0','countVal','total'):
            if isinstance(row.get(key), (int,float)):return int(row[key])
        for k,v in row.items():
            if k!='attributes' and isinstance(v,(int,float)):return int(v)
    except (AttributeError,TypeError,ValueError):pass
    return None

def report(src, org, outdir, offline=False):
    requirements=build_requirements()
    for row in requirements:row['local']=check(src,row['path'],row['needle'])
    meta={}
    queried={}
    online=False
    tooling_flows={}
    if not offline:
        print('[1/4] Checking Salesforce CLI and existing login (read only)...',flush=True)
        if not shutil.which('sf'):
            print('    WARNING: sf CLI not on PATH. Producing source-only audit.')
        else:
            ping=run_sf(['data','query','--target-org',org,'--query','SELECT Id FROM Organization LIMIT 1'],timeout=70)
            online=(ping.get('status')==0)
            if not online:
                print('    WARNING: Org unavailable or not authorized:',str(ping.get('message') or ping.get('error'))[:350])
    if online:
        print('[2/4] Listing org metadata (metadata API; never deploys)...',flush=True)
        for t in META_TYPES:
            # Salesforce metadata reports and dashboards are folder-scoped.
            options=[None]
            if t in ('Report','Dashboard'):options=['Campus_Events']
            if t=='EmailTemplate':options=['unfiled$public']
            for folder in options:
                args=['org','list','metadata','--target-org',org,'--metadata-type',t]
                if folder:args+=['--folder',folder]
                result=run_sf(args)
                key=t
                meta[key]={'ok':result.get('status')==0, 'names':files_from_meta(result),
                           'error':(result.get('message') or result.get('error') or '') if result.get('status') else ''}
                save_json(outdir/'org_metadata'/f'{t}.json',result)
                print(f'    {t:18} {len(meta[key]["names"]):4} entries', ('(unavailable)' if not meta[key]['ok'] else ''),flush=True)
        print('    Checking active flow versions through Tooling API...',flush=True)
        names=['Quick_Event_Registration','Registration_After_Save','Registration_Before_Save','Daily_Event_Closer',
               'Calculate_Society_Stats','Venue_Emergency_Handler']
        quoted=','.join("'"+x+"'" for x in names)
        fq='SELECT DeveloperName, ActiveVersionId, LatestVersionId FROM FlowDefinition WHERE DeveloperName IN ('+quoted+')'
        flow_result=run_sf(['data','query','--target-org',org,'--use-tooling-api','--query',fq])
        save_json(outdir/'org_data'/'flow_activation.json',flow_result)
        if flow_result.get('status')==0:
            for rec in flow_result.get('result',{}).get('records',[]):
                tooling_flows[rec.get('DeveloperName','')] = 'ACTIVE' if rec.get('ActiveVersionId') else 'INACTIVE'
        else:
            print('    Flow activation status not available (see org_data/flow_activation.json).')
        print('[3/4] Querying live business data, users, data-quality signals...',flush=True)
        for label,query in QUERIES.items():
            result=run_sf(['data','query','--target-org',org,'--query',query])
            queried[label]={'ok':result.get('status')==0,'count':count_from_query(result) if result.get('status')==0 and 'SELECT COUNT()' in query.upper() and 'GROUP BY' not in query.upper() else None,
                            'error':(result.get('message') or result.get('error') or '') if result.get('status') else ''}
            save_json(outdir/'org_data'/f'{label}.json',result)
            print('    '+label+': '+(str(queried[label]['count']) if queried[label]['count'] is not None else 'see JSON '+('OK' if queried[label]['ok'] else 'UNAVAILABLE')),flush=True)
            if label=='events_date_audit' and result.get('status')==0:
                rows=result.get('result',{}).get('records',[])
                # Salesforce REST API timestamps use a lexicographically sortable UTC representation.
                invalid=sum(1 for r in rows if r.get('Start_Date_Time__c') and r.get('End_Date_Time__c')
                            and r['End_Date_Time__c'] <= r['Start_Date_Time__c'])
                queried['events_invalid_datetime_sample']={'ok':True,'count':invalid,'error':f'Checked {len(rows)} event records (limit 2000)'}
                print('    events_invalid_datetime_sample:',invalid,'out of',len(rows),flush=True)
    else:
        print('[2/4] Org metadata skipped — only local source can be asserted.')
        print('[3/4] Org business data skipped — no live row counts can be asserted.')

    for row in requirements:
        typ=row['metadata_type'];full=row['metadata_member']
        item=meta.get(typ)
        if not typ or not full or item is None or not item.get('ok'):
            row['org']='UNVERIFIED'
        else:
            found=full in item['names']
            # Some metadata APIs return names without object prefixes for selected types.
            if not found and typ in ('Report','Dashboard','EmailTemplate'):
                found=any(n.rsplit('/',1)[-1]==full.rsplit('/',1)[-1] for n in item['names'])
            row['org']='PRESENT' if found else 'NOT_LISTED'
        row['org_active']=tooling_flows.get(full,'UNVERIFIED') if typ=='Flow' else 'N/A'
        row.pop('needle',None)
    output_csv=outdir/'requirements.csv'
    with output_csv.open('w',newline='',encoding='utf-8-sig') as fh:
        columns=['task','requirement','local','org','metadata_type','metadata_member','path','note','org_active']
        w=csv.DictWriter(fh,fieldnames=columns);w.writeheader();w.writerows(requirements)

    count=lambda key: queried.get(key,{}).get('count')
    print('[4/4] Creating readable summary and gap list...',flush=True)
    completed=sum(1 for x in requirements if x['local']=='PRESENT')
    partial=sum(1 for x in requirements if x['local']=='PARTIAL')
    missing=sum(1 for x in requirements if x['local']=='MISSING')
    lines=['# Campus Events Manager — Salesforce CLI Audit', '',
           f'- Run time (local clock): {dt.datetime.now().astimezone().isoformat(timespec="seconds")}',
           f'- Source: `{src.root.name}` ({"ZIP" if src.zip else "extracted Salesforce DX project"})',
           f'- Org username: `{org}`',
           f'- Live org reachable: **{"YES" if online else "NO"}**',
           f'- Local metadata checks: **{completed} present / {partial} partial / {missing} missing** of **{len(requirements)}** checks.',
           '- IMPORTANT: File existence is NOT evidence of deployed functionality, configured permissions, activation, or successful tests.',
           '- Metadata API listing proves a component is discoverable, NOT its correctness. `NOT_LISTED` can also mean folder/API mismatch; review raw errors.',
           '- Flow activation is independently checked using Tooling API where available. ACTIVE still does not prove runtime correctness.',
           '', '## Data seeding thresholds (Task 1)', '',
           '| Record type | Live count | Required | Result |', '|---|---:|---:|---|']
    for title,key,required in [('Societies','societies_count',3),('Events','events_count',6),('Registrations','registrations_count',20)]:
        val=count(key)
        lines.append(f'| {title} | {val if val is not None else "Unknown"} | {required} | {"PASS" if val is not None and val >=required else "BELOW TARGET" if val is not None else "NOT VERIFIED"} |')
    lines+=['','## Other live data / health findings','','| Query | Count or status |','|---|---|']
    for k,v in queried.items():
        lines.append(f'| {k} | {v["count"] if v["count"] is not None else "OK (details in org_data/)" if v["ok"] else "QUERY FAILED: see org_data/"} |')
    if not queried:lines.append('| All live queries | Skipped (offline) |')
    lines+=['','## Local / org coverage per assignment task','','| Task | Local present | Local partial | Local missing | Listed in org |', '|---|---:|---:|---:|---:|']
    for t in '123456':
        subset=[x for x in requirements if x['task']==t]
        lines.append(f'| {t} | {sum(x["local"]=="PRESENT" for x in subset)} | {sum(x["local"]=="PARTIAL" for x in subset)} | {sum(x["local"]=="MISSING" for x in subset)} | {sum(x["org"]=="PRESENT" for x in subset)} |')
    lines+=['','## Priority gaps / partial work (LOCAL snapshot)','',
            'These are source-level findings. Check the ORG column before choosing fixes.']
    for row in requirements:
        if row['local']!='PRESENT':
            lines.append(f'- **Task {row["task"]} / {row["local"]}** — {row["requirement"]}. '
                         f'Org: {row["org"]}; activation: {row["org_active"]}. '+row['note'])
    lines+=['','## Required live / behavioral checks (not inferred from files)','',
            '- Validate picklist dependencies and record-type restrictions; inspect required Event layouts and related-list columns.',
            '- Create deliberate negative test records **only in a safe test org and only after permission** for all five validation rules; preserve screenshots of errors.',
            '- Verify both duplicate-rule behaviors by trying same email and same full name + phone.',
            '- Verify permissions using the three scenario users, object/FLS/record access, and Login As screenshots; permission sets alone may not restrict already-granted profile permissions.',
            '- Confirm template type, alert recipient, flow activation, 11 PM timezone and daily scheduled behavior, platform event cancellation and Chatter post.',
            '- Confirm dashboard four component types, running user, society-category filter, and all report result calculations.',
            '- Test registrations against full/closed events and concurrent sign-ups (not just validation-rule existence).',
            '- Prepare Task 6 short answers and all screenshot evidence for submission.',
            '', '## What to send back for diagnosis','',
            '`summary.md`, `requirements.csv`, and the specific failing `org_metadata/*.json` and `org_data/*.json` files.',
            'Review files first; do not share authorization tokens, passwords, or unnecessary personal contact/user data.', '']
    (outdir/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
    save_json(outdir/'audit.json',{'source':str(src.root),'org':org,'online':online,
                                  'requirements':requirements,'data_queries':queried,'metadata_summaries':meta})
    print('\nAUDIT COMPLETE')
    print(f'Source checks: {completed} present, {partial} partial, {missing} missing')
    print('Live org:', 'connected' if online else 'not checked / unavailable')
    print('Reports:',outdir.resolve())


def main():
    p=argparse.ArgumentParser(description='Salesforce Campus Events Manager read-only audit. No deployments or data writes.')
    p.add_argument('--org',default=ORG_DEFAULT,help='Salesforce username or existing sf org alias')
    p.add_argument('--source',default='.',help='Unzipped Salesforce DX project root OR original ZIP file')
    p.add_argument('--out',default='',help='Audit output folder (default campus_audit_YYYYMMDD_HHMMSS)')
    p.add_argument('--offline',action='store_true',help='Only inspect local ZIP/project, skip live sf CLI calls')
    args=p.parse_args()
    try:src=Source(args.source)
    except (FileNotFoundError,OSError,zipfile.BadZipFile) as ex:
        print('Source error:',ex,file=sys.stderr);return 2
    out=Path(args.out).expanduser().resolve() if args.out else Path.cwd()/('campus_audit_'+dt.datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True,exist_ok=True)
    report(src,args.org,out,args.offline)
    return 0

if __name__=='__main__':
    sys.exit(main())
