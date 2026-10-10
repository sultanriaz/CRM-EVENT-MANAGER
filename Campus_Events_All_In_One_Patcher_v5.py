#!/usr/bin/env python3
"""Campus Events Manager single-file Salesforce DX patcher.

Includes prior workspace dropdown and Campus metadata candidates.
Default action stages locally with backups. No org modification unless --deploy AND --confirm-deploy.
See --help. Python standard library only; Salesforce CLI required for --validate/--validate-ui/--deploy/live --audit.

For eligible trial orgs, use --validate-ui or --validate --test-level NoTestRun to isolate metadata errors.
V5: fixes 11 Salesforce validation failures (including dependent platform event manifest),
     safely upgrades exact v4-staged source, and runs pre-deploy metadata integrity checks.
     A dry-run success is required before any live deployment.
NoTestRun does NOT replace Apex coverage testing or live functional/UI tests.
"""
import argparse, base64, csv, datetime, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

API_NS='http://soap.sforce.com/2006/04/metadata'
NS='{'+API_NS+'}'
ET.register_namespace('', API_NS)
DEFAULT_ORG='superior7891_61lsg4rtgvkm@gmail.com'
APPS={'Community_Fitness_Wellness_Hub':'Fitness_Hub_Workspace_Utility',
      'Campus_Events_Manager':'Campus_Events_Workspace_Utility'}
# Original snapshot SHA256s for files we need to upgrade; modified user files are not blindly overwritten.
ORIGINAL_AUDITOR_SHA256 = 'ba307bb020841045d3a05296ae49721c67feafca42172a91fc4c5829c82a1a1b'
TRUSTED_V4_SHA256 = {'dashboards/Campus_Events/Student_Affairs_Dashboard.dashboard-meta.xml': '820ccdd4b311f796a87a86f146d02064a9f525c0b109ef7a2913b5ee86f9d000', 'duplicateRules/Contact.Block_Duplicate_Student_Email.duplicateRule-meta.xml': '5def76aa554b7ba7fde6bba98b268e26d6e66ceac3306a101c9235ad4c319482', 'flows/Daily_Event_Closer.flow-meta.xml': '87b333f2afce7eff3fcefbceacbbea94e5b46d69f406c59d662cfc869643026b', 'layouts/Event__c-Academic Event Layout.layout-meta.xml': '0b407c8fd93abd18600a06b3a3be7a18ab7a0ec3295b40ac3c5c0f95a5511e7e', 'layouts/Event__c-Event Layout.layout-meta.xml': '0b407c8fd93abd18600a06b3a3be7a18ab7a0ec3295b40ac3c5c0f95a5511e7e', 'layouts/Event__c-Recreational Event Layout.layout-meta.xml': '0b407c8fd93abd18600a06b3a3be7a18ab7a0ec3295b40ac3c5c0f95a5511e7e', 'objects/Event__c/fields/Society_Category__c.field-meta.xml': '90f3dbb265989a347fcc8ba8477c48b0658e798c383aaf8a19cdb8b583af5dbb', 'reports/Campus_Events/Event_Attendance_Rate.report-meta.xml': '6f677c0820fe9714f4cf9664a65aed0f3ea5f7d0a2474c9a0c06914709b1bb97', 'objects/Venue_Alert__e/Venue_Alert__e.object-meta.xml': 'e40b1e73dfe2ea3ca3e84d9896bfbbc7bda439cd8c75ca7690c6caa79940a3ba'}
ORIGINAL_HASHES = {
    'reports/Campus_Events/Event_Attendance_Rate.report-meta.xml':'350abb2297f9ba7ac1ab567546b4caa08d24eb75ad658dd255dd7441116ec4a1',
    'reportTypes/Events_with_Registrations.reportType-meta.xml':'4b19c5e0cb2a2dcd529482c943b05a19b78a8fda047f14c906583b6a220fa1fe',
    'workflows/Registration__c.workflow-meta.xml':'31b6da16ce1e611ba3de3cb981976852cb079990b0ca55f48135f2018c611814',
}


def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
def xml_string(element):
    try:ET.indent(element,space='    ')
    except AttributeError:pass
    return ET.tostring(element,encoding='utf-8',xml_declaration=True)

def data_assets():
    compressed=base64.b64decode(ASSET_PAYLOAD.replace('\n',''))
    with zipfile.ZipFile(io.BytesIO(compressed),'r') as z:
        for item in z.infolist():
            if item.is_dir():continue
            relative=Path(item.filename)
            if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe embedded asset path')
            yield relative,z.read(item)

def salesforce_executable(is_windows=None):
    """Resolve Windows Salesforce CLI batch launcher (sf.cmd) before spawning subprocess."""
    if is_windows is None:
        is_windows = os.name == 'nt'
    candidates = ('sf.cmd', 'sf.exe', 'sf') if is_windows else ('sf',)
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError('Salesforce CLI not found on PATH. Open a terminal with `sf --version` working.')

class Patcher:
    def __init__(self,root):
        self.root=root.resolve(); self.base=self.root/'force-app/main/default';self.created=[];self.updated=[];self.unchanged=[];self.skipped=[]
        stamp=now()
        self.run=self.root/'campus_patch_runs'/stamp
        suffix=0
        while self.run.exists():suffix+=1;self.run=self.root/'campus_patch_runs'/f'{stamp}_{suffix}'
        self.backup=self.run/'backups';self.run.mkdir(parents=True,exist_ok=False)
    def backup_file(self,path):
        if not path.is_file():return
        rel=path.relative_to(self.root)
        dest=self.backup/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,dest)
    @staticmethod
    def equivalent_without_dup_sort(first,second):
        """Compare two DuplicateRule components ignoring ONLY target-specific execution order."""
        try:
            x=ET.fromstring(first);y=ET.fromstring(second)
            def normalized(node):
                return (node.tag,tuple(sorted(node.attrib.items())),(node.text or '').strip(),
                        tuple(normalized(child) for child in node if child.tag!=NS+'sortOrder'))
            return normalized(x)==normalized(y)
        except ET.ParseError:return False

    def save(self,path,new,mode='safe',rel=None):
        path.parent.mkdir(parents=True,exist_ok=True)
        identifier=str(path.relative_to(self.root))
        if path.is_file():
            old=path.read_bytes()
            if old==new:self.unchanged.append(identifier);return
            if mode!='merge' and path.parent.name=='duplicateRules' and self.equivalent_without_dup_sort(old,new):
                self.unchanged.append(identifier);return
            # Existing files are upgraded only if they match the supplied reference ZIP exactly.
            if mode=='baseline' and rel and sha(old) in (ORIGINAL_HASHES.get(rel), TRUSTED_V4_SHA256.get(rel)):pass
            elif mode!='merge':
                self.skipped.append((identifier,'Existing divergent file; preserved. Compare manually.'))
                return
            self.backup_file(path);path.write_bytes(new);self.updated.append(identifier)
        else:
            path.write_bytes(new);self.created.append(identifier)
    def merge_application(self,app_name,utility):
        p=self.base/'applications'/f'{app_name}.app-meta.xml'
        if not p.is_file():raise FileNotFoundError('Original app missing: '+str(p))
        current=p.read_bytes();x=ET.fromstring(current)
        utility_elem=x.find(NS+'utilityBar')
        if utility_elem is not None and (utility_elem.text or '').strip() not in ('',utility):
            self.skipped.append((str(p.relative_to(self.root)), 'Existing different utility bar; no overwrite.'))
            return
        changed=False
        if utility_elem is None:utility_elem=ET.SubElement(x,NS+'utilityBar');utility_elem.text=utility;changed=True
        if app_name=='Campus_Events_Manager':
            all_tabs=[t.text for t in x.findall(NS+'tabs')]
            if 'standard-home' not in all_tabs:
                # Put Home first so Campus workspace page can be activated in Lightning App Builder.
                tab=ET.Element(NS+'tabs');tab.text='standard-home'
                before=next((i for i,n in enumerate(list(x)) if n.tag==NS+'tabs'),len(x))
                x.insert(before,tab);changed=True
        if app_name=='Campus_Events_Manager':
            existing={(e.findtext(NS+'actionName'),e.findtext(NS+'pageOrSobjectType')):
                      e for e in x.findall(NS+'actionOverrides')}
            assignments=[('Tab','standard-home','Campus_Events_Home'),
                         ('View','Event__c','Campus_Event_Record_Page')]
            for action,scope,page in assignments:
                previous=existing.get((action,scope))
                if previous is not None:
                    if previous.findtext(NS+'content') not in (None,page):
                        self.skipped.append((str(p.relative_to(self.root)),
                            'Existing app page assignment for '+scope+' preserved.'))
                    continue
                entry=ET.Element(NS+'actionOverrides')
                for tag,value in [('actionName',action),('content',page),('formFactor','Large'),
                                   ('pageOrSobjectType',scope),('type','Flexipage')]:
                    ET.SubElement(entry,NS+tag).text=value
                # Put action overrides ahead of app branding/description per Metadata API ordering.
                x.insert(len(x.findall(NS+'actionOverrides')),entry)
                changed=True
        if changed:self.save(p,xml_string(x),mode='merge')
        else:self.unchanged.append(str(p.relative_to(self.root)))
    def merge_contact_matching(self,expected):
        path=self.base/'matchingRules/Contact.matchingRule-meta.xml'
        if not path.is_file():self.save(path,expected);return
        original=ET.fromstring(path.read_bytes());candidate=ET.fromstring(expected)
        keys={v.findtext(NS+'fullName') for v in original.findall(NS+'matchingRules')}
        changed=False
        for v in candidate.findall(NS+'matchingRules'):
            key=v.findtext(NS+'fullName')
            if key not in keys:original.append(v);changed=True
        if changed:self.save(path,xml_string(original),mode='merge')
        else:self.unchanged.append(str(path.relative_to(self.root)))
    def dashboard_html(self):
        path=self.base/'lwc/fitnessHubDashboard/fitnessHubDashboard.html'
        if not path.is_file():self.skipped.append((str(path.relative_to(self.root)),'Fitness dashboard not found; utility bar remains.'));return
        old=path.read_text(encoding='utf-8-sig')
        if '<c-workspace-switcher' in old:self.unchanged.append(str(path.relative_to(self.root)));return
        marker='<button class="refresh-btn"'
        if old.count(marker)!=1:self.skipped.append((str(path.relative_to(self.root)),'Dashboard markup differs; utility bar still works.'));return
        insert='<c-workspace-switcher current-app="c__Community_Fitness_Wellness_Hub"></c-workspace-switcher>\n            '
        self.save(path,old.replace(marker,insert+marker).encode('utf-8'),mode='merge')
    def patch(self):
        if not (self.root/'sfdx-project.json').is_file():raise RuntimeError('Directory must contain sfdx-project.json')
        for app in APPS:
            if not (self.base/'applications'/f'{app}.app-meta.xml').is_file():raise FileNotFoundError('Required original Salesforce app '+app+' missing')
        for rel,raw in data_assets():
            # Non-Salesforce helper files live outside default metadata directory.
            if rel.parts[0]=='tools':
                dest=self.root/'tools'/Path(*rel.parts[1:])
                if dest.exists() and rel.as_posix()=='tools/campus_events_audit_with_ui.py' and sha(dest.read_bytes())==ORIGINAL_AUDITOR_SHA256:
                    self.save(dest,raw,mode='merge')
                else:
                    self.save(dest,raw)
                continue
            if rel.parts[0]=='docs':dest=self.root/'docs'/rel.name;self.save(dest,raw);continue
            key=rel.as_posix();dest=self.base/rel
            if key=='matchingRules/Contact.matchingRule-meta.xml':self.merge_contact_matching(raw)
            else:self.save(dest,raw,mode='baseline' if key in ORIGINAL_HASHES or key in TRUSTED_V4_SHA256 else 'safe',rel=key)
        for app,utility in APPS.items():self.merge_application(app,utility)
        self.dashboard_html()
        self.metadata_preflight()
        self.make_manifest()
        self.make_summary()
    def member_for(self,rel):
        """Return a Metadata API member from a local SFDX path, not a change event."""
        p=Path(rel);a=p.parts
        if not a:return None
        if a[0]=='classes' and (p.name.endswith('.cls') or p.name.endswith('.cls-meta.xml')):
            return 'ApexClass',p.name.split('.')[0]
        if a[0]=='lwc' and len(a)>=3:
            return 'LightningComponentBundle',a[1]
        singular={'applications':'CustomApplication','flexipages':'FlexiPage',
          'layouts':'Layout','flows':'Flow','duplicateRules':'DuplicateRule',
          'matchingRules':'MatchingRules','reportTypes':'ReportType',
          'reports':'Report','dashboards':'Dashboard','roles':'Role',
          'permissionsets':'PermissionSet','workflows':'Workflow',
          'tabs':'CustomTab','globalValueSets':'GlobalValueSet',
          'sharingRules':'SharingRules'}
        if a[0]=='objects':
            if len(a)==3 and a[2].endswith('.object-meta.xml'):
                return 'CustomObject',a[1]
            if len(a)==4 and a[2]=='fields':
                return 'CustomField',a[1]+'.'+a[3].removesuffix('.field-meta.xml')
            if len(a)==4 and a[2]=='validationRules':
                return 'ValidationRule',a[1]+'.'+a[3].removesuffix('.validationRule-meta.xml')
        if a[0]=='email':
            if p.name.endswith('.emailFolder-meta.xml'):
                src=self.base/p
                if src.is_file():
                    try:
                        root=ET.parse(src).getroot().tag.rsplit('}',1)[-1]
                        if root in ('EmailTemplateFolder','EmailFolder'):
                            return root,p.name.removesuffix('.emailFolder-meta.xml')
                    except ET.ParseError:pass
                return None
            if len(a)>=3 and (p.name.endswith('.email') or p.name.endswith('.email-meta.xml')):
                return 'EmailTemplate',a[1]+'/'+a[2].split('.')[0]
        if a[0]=='reports' and p.name.endswith('.reportFolder-meta.xml'):
            return 'ReportFolder',p.name.removesuffix('.reportFolder-meta.xml')
        if a[0]=='dashboards' and p.name.endswith('.dashboardFolder-meta.xml'):
            return 'DashboardFolder',p.name.removesuffix('.dashboardFolder-meta.xml')
        if a[0] in singular:
            typ=singular[a[0]]
            name=p.name.split('.')[0]
            if a[0]=='duplicateRules':name=p.name.removesuffix('.duplicateRule-meta.xml')
            if a[0] in ('reports','dashboards') and len(a)>=3:name=a[1]+'/'+name
            return typ,name
        return None

    def make_manifest(self):
        """Rebuild from staged source; unchanged files MUST remain deployable.

        V3 incorrectly used self.created + self.updated + self.unchanged (run deltas).
        On a repeated invocation the resulting package could contain zero members.
        A verified, on-disk inventory provides a stable package for every invocation.
        """
        verified=set()
        missing=[]
        for rel,raw in data_assets():
            if rel.parts[0] in ('tools','docs'):continue
            dest=self.base/rel
            if not dest.is_file():
                missing.append(rel.as_posix());continue
            # Never select divergent user files that were deliberately preserved.
            key=rel.as_posix()
            if dest.read_bytes()!=raw:
                if key.startswith('duplicateRules/Contact.') and self.equivalent_without_dup_sort(dest.read_bytes(),raw):
                    verified.add(key)
                    continue
                if key=='matchingRules/Contact.matchingRule-meta.xml':
                    # Contact matching rules are intentionally merged into existing metadata.
                    try:
                        existing=ET.parse(dest).getroot()
                        proposed=ET.fromstring(raw)
                        old={e.findtext(NS+'fullName') for e in existing.findall(NS+'matchingRules')}
                        expected={e.findtext(NS+'fullName') for e in proposed.findall(NS+'matchingRules')}
                        if not expected.issubset(old):
                            missing.append(key+' (matching rules not merged)');continue
                    except ET.ParseError:
                        missing.append(key+' (invalid XML)');continue
                else:
                    missing.append(key+' (local content differs from packaged candidate)')
                    continue
            verified.add(key)
        for app,bar in APPS.items():
            path=self.base/'applications'/f'{app}.app-meta.xml'
            if not path.is_file():
                missing.append('applications/'+path.name);continue
            try:
                x=ET.parse(path).getroot()
                if x.findtext(NS+'utilityBar')==bar:
                    verified.add('applications/'+path.name)
                else:missing.append('applications/'+path.name+' (expected utility bar not assigned)')
            except ET.ParseError:missing.append('applications/'+path.name+' (invalid XML)')
        dashboard='lwc/fitnessHubDashboard/fitnessHubDashboard.html'
        if (self.base/dashboard).is_file() and '<c-workspace-switcher' in (self.base/dashboard).read_text(encoding='utf-8-sig'):
            verified.add(dashboard)
        else:missing.append(dashboard+' (dropdown absent)')
        # Existing Campus report/dashboard folder definitions are deployment dependencies.
        for folder in ('reports/Campus_Events.reportFolder-meta.xml',
                       'dashboards/Campus_Events.dashboardFolder-meta.xml'):
            if (self.base/folder).is_file():verified.add(folder)
            else:missing.append(folder)
        components={}
        for rel in sorted(verified):
            member=self.member_for(rel)
            if member:
                typ,name=member;components.setdefault(typ,set()).add(name)
        required={
            'CustomObject':{'Venue_Alert__e'},
            'CustomField':{'Event__c.Society_Category__c','Venue_Alert__e.Venue__c','Venue_Alert__e.Message__c'},
            'LightningComponentBundle':{'workspaceSwitcher','campusEventsHome','fitnessHubDashboard'},
            'CustomApplication':set(APPS),
            'Flow':{'Calculate_Society_Stats','Daily_Event_Closer',
                    'Quick_Event_Registration','Registration_After_Save',
                    'Registration_Before_Save','Venue_Emergency_Handler'},
            'FlexiPage':{'Campus_Events_Workspace_Utility','Fitness_Hub_Workspace_Utility',
                        'Campus_Events_Home','Campus_Event_Record_Page'},
        }
        unmet={typ:sorted(names-components.get(typ,set()))
               for typ,names in required.items() if names-components.get(typ,set())}
        self.manifest=self.run/'campus_patch.xml'
        pack=ET.Element(NS+'Package')
        for typ,members in sorted(components.items()):
            ts=ET.SubElement(pack,NS+'types')
            for member in sorted(members):ET.SubElement(ts,NS+'members').text=member
            ET.SubElement(ts,NS+'name').text=typ
        ET.SubElement(pack,NS+'version').text='61.0'
        self.manifest.write_bytes(xml_string(pack))
        self.count=sum(len(v) for v in components.values())
        inventory={'component_count':self.count,
            'components':{k:sorted(v) for k,v in sorted(components.items())},
            'excluded_files':missing,'missing_required':unmet,
            'manifest_path':str(self.manifest),
            'note':'Offline metadata inventory. No live org deployment was executed.'}
        (self.run/'MANIFEST_INVENTORY.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
        if unmet:
            raise RuntimeError('Campus metadata incomplete; refusing validation/deployment: '
                               +json.dumps(unmet,sort_keys=True)+'; inspect MANIFEST_INVENTORY.json')
        if self.count<25:
            raise RuntimeError(f'Only {self.count} metadata members resolved; '
                               'refusing suspiciously incomplete deployment manifest')
        print('DEPLOYMENT MANIFEST:',self.count,'members in',len(components),'types; '
              'excluded/missing:',len(missing))

    def metadata_preflight(self):
        """Refuse invalid metadata known from last dry-run, before asking Salesforce to validate."""
        issues=[]
        def get(path):
            p=self.base/path
            try:return ET.parse(p).getroot()
            except (ET.ParseError,OSError) as e:
                issues.append(f'{path}: {e}');return None
        r=get('reports/Campus_Events/Event_Attendance_Rate.report-meta.xml')
        if r is not None:
            for agg in r.findall(NS+'aggregates'):
                if not (agg.findtext(NS+'developerName') or '').startswith('FORMULA'):
                    issues.append('Attendance summary developerName does not start with FORMULA')
        r=get('dashboards/Campus_Events/Student_Affairs_Dashboard.dashboard-meta.xml')
        if r is not None:
            for c in r.iter(NS+'components'):
                if c.findtext(NS+'componentType') in ('Gauge','Table','Metric'):
                    for attr in ('indicatorLowColor','indicatorMiddleColor','indicatorHighColor'):
                        if c.find(NS+attr) is None:issues.append('Dashboard missing '+attr)
        r=get('duplicateRules/Contact.Block_Duplicate_Student_Email.duplicateRule-meta.xml')
        if r is not None:
            if r.findtext(NS+'actionOnInsert')=='Block':
                if r.findall(NS+'operationsOnInsert') or r.findall(NS+'operationsOnUpdate'):
                    issues.append('Block rule has operationsOn... fields')
        for name in ('Event__c-Event Layout','Event__c-Academic Event Layout','Event__c-Recreational Event Layout'):
            r=get(f'layouts/{name}.layout-meta.xml')
            if r is not None:
                for field in r.iter(NS+'layoutItems'):
                    if field.findtext(NS+'field')=='Name' and field.findtext(NS+'behavior')!='Required':
                        issues.append(f'{name} must mark Name as required')
        r=get('objects/Event__c/fields/Society_Category__c.field-meta.xml')
        if r is not None and r.find(NS+'formula') is not None and r.find(NS+'length') is not None:
            issues.append('Society_Category formula field includes prohibited length')
        r=get('flows/Daily_Event_Closer.flow-meta.xml')
        if r is not None:
            indices=[i for i,e in enumerate(r) if e.tag==NS+'recordUpdates']
            if indices and indices != list(range(indices[0],indices[0]+len(indices))):
                issues.append('Daily_Event_Closer recordUpdates elements not contiguous')
        r=get('objects/Venue_Alert__e/Venue_Alert__e.object-meta.xml')
        if r is not None and r.findtext(NS+'eventType')!='HighVolume':
            issues.append('Venue_Alert__e eventType must be HighVolume')
        for field in ('Venue__c','Message__c'):
            get(f'objects/Venue_Alert__e/fields/{field}.field-meta.xml')
        if issues:
            (self.run/'PREFLIGHT_ISSUES.txt').write_text('\n'.join(issues),encoding='utf-8')
            raise RuntimeError('Local metadata preflight FAILED: '+'; '.join(issues))
        print('METADATA PREFLIGHT: all known validation-error patterns corrected')

    def reconcile_contact_duplicate_order(self,org):
        """Read target-org Contact DuplicateRules in an isolated directory (no org writes).

        Keep existing org rules untouched. Append new Campus rules AFTER those rules,
        retaining positions for Campus rules if they already exist in the org.
        The only auto-editable XML tag is sortOrder; user-authored modifications
        unrelated to sortOrder are preserved and reported as blockers.
        """
        loc=self.run/'org_reference'; loc.mkdir(exist_ok=True)
        log=self.run/'CONTACT_DUPLICATE_RULE_ORDER_LOG.txt'
        cmd=[salesforce_executable(),'project','retrieve','start',
             '--target-org',org,'--metadata','DuplicateRule:Contact.*',
             '--output-dir',str(loc),'--json','--wait','10']
        try:
            result=subprocess.run(cmd,cwd=self.root,stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',text=True)
        except OSError as exc:
            log.write_text(f'Retrieval could not start: {exc}',encoding='utf-8')
            print('WARNING: Contact duplicate-order retrieve unavailable; see',log)
            return
        log.write_text(result.stdout,encoding='utf-8')
        if result.returncode!=0:
            print('WARNING: Cannot determine existing Contact duplicate-rule sequence from org; '
                  'will use local order 1,2. Check',log)
            return
        files=sorted(loc.rglob('Contact.*.duplicateRule-meta.xml'))
        actual={}
        for f in files:
            try:
                root=ET.parse(f).getroot()
                n=f.name.removeprefix('Contact.').removesuffix('.duplicateRule-meta.xml')
                order=int(root.findtext(NS+'sortOrder'))
                actual[n]=order
            except (ET.ParseError,TypeError,ValueError):
                raise RuntimeError('Cannot read Salesforce duplicate-rule order in '+str(f))
        if len(set(actual.values()))!=len(actual):
            raise RuntimeError('Target org Contact duplicate rules have conflicting sort orders; '
                               'manual reconciliation is needed before deployment')
        existing=sorted(actual.values())
        if existing and existing!=list(range(1,len(existing)+1)):
            raise RuntimeError('Existing Contact duplicate rule order in org has gaps; '
                               'refusing to change existing org rules')
        order_max=max(existing,default=0)
        our_names=['Block_Duplicate_Student_Email','Warn_Duplicate_Student_Name_Phone']
        additions={}
        for name in our_names:
            if name not in actual:
                order_max+=1;additions[name]=order_max
            else:additions[name]=actual[name]
        for name,expected in additions.items():
            key=f'duplicateRules/Contact.{name}.duplicateRule-meta.xml'
            local=self.base/key
            embedded=dict(data_assets()).get(Path(key))
            if embedded is None or not local.is_file():
                raise RuntimeError('Expected duplicate metadata missing: '+key)
            old=local.read_bytes()
            if not self.equivalent_without_dup_sort(old,embedded):
                raise RuntimeError('Contact duplicate rule differs from packaged version '
                                   'beyond sortOrder: '+key+'. Manual review required.')
            xml=ET.fromstring(old)
            field=xml.find(NS+'sortOrder')
            if field is None:raise RuntimeError('Missing sortOrder: '+key)
            if field.text!=str(expected):
                field.text=str(expected)
                self.save(local,xml_string(xml),mode='merge',rel=key)
        report={'existing_org_contact_rules':actual,'campus_rule_order':additions,
                'note':'Org inspected read-only. Only local sortOrder values were updated.'}
        (self.run/'CONTACT_DUPLICATE_RULE_ORDER.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('CONTACT DUPLICATE RULE ORDER:',', '.join(f'{k}={v}' for k,v in additions.items()))
        self.make_manifest()
        self.make_summary()

    def make_summary(self):
        log={"project":str(self.root),"created":self.created,"updated":self.updated,"unchanged_count":len(self.unchanged),
             "skipped":self.skipped,"deploy_manifest":str(self.manifest),"components_in_manifest":self.count,
             "no_org_deployment_performed":True,"backup_directory":str(self.backup)}
        (self.run/'patch_result.json').write_text(json.dumps(log,indent=2),encoding='utf-8')
        lines=['# Campus all-in-one patch run','',f'- Project: `{self.root}`',
          f'- Created metadata files: {len(self.created)}',f'- Updated existing files: {len(self.updated)}',
          f'- Unchanged files: {len(self.unchanged)}',f'- Skipped conflicts: {len(self.skipped)}',
          f'- Manifest components: {self.count}',
          '- Org deployment: **NOT YET EXECUTED**','',
          '## Remaining org/visual checks','',
          'All six Flows are **Draft**; debug and activate only after successful org deployment and tests.',
          'Verify app/home/record page activation, user permissions/profile assignments, contact duplicate rules, email, report aggregation and dashboard filter.',
          'The app is not declared complete until live org validation, security tests, seeded record counts, and actual UI screenshots pass.','',
          '## Conflicts (not overwritten)','']
        lines += [f'- `{name}`: {why}' for name,why in self.skipped] or ['- None']
        lines+=['','## Changed files','']+[f'- `{s}`' for s in self.created+self.updated]
        (self.run/'PATCH_SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    def run_command(self,cmd,filename):
        try:
            p=subprocess.run(cmd,cwd=self.root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                             text=True,encoding='utf-8',errors='replace')
        except OSError as exc:
            error=f'Unable to start CLI command {cmd[0]!r}: {exc}\n'
            (self.run/filename).write_text(error,encoding='utf-8')
            print('CLI launch failed. Saved:',self.run/filename)
            print(error)
            return False
        (self.run/filename).write_text(p.stdout,encoding='utf-8')
        print('Exit code:',p.returncode,'Saved:',self.run/filename)
        if p.returncode:
            print(p.stdout[-4500:])
            return False
        return True
    def validate_ui(self, org):
        """Check only the new LWCs without running unrelated legacy Fitness Hub tests.

        NoTestRun is supported only for eligible nonproduction orgs; Salesforce decides.
        This validates components, not UI browser behavior or app assignments.
        """
        components = [self.base/'lwc'/'workspaceSwitcher', self.base/'lwc'/'campusEventsHome']
        absent = [str(p) for p in components if not p.is_dir()]
        if absent:
            print('Missing expected workspace UI components:', absent)
            return False
        cmd=[salesforce_executable(), 'project','deploy','start','--dry-run',
             '--target-org',org,'--test-level','NoTestRun','--wait','30']
        for p in components: cmd += ['--source-dir',str(p)]
        return self.run_command(cmd,'UI_VALIDATION_LOG.txt')
    def validate(self,org,test_level='RunLocalTests'):
        if not self.count:
            raise RuntimeError('Empty deployment manifest; refusing to validate')
        cmd=[salesforce_executable(),'project','deploy','start','--dry-run','--target-org',org,
             '--manifest',str(self.manifest),'--test-level',test_level,'--wait','30']
        return self.run_command(cmd,'VALIDATION_LOG.txt')
    def deploy(self,org,test_level='RunLocalTests'):
        cmd=[salesforce_executable(),'project','deploy','start','--target-org',org,
             '--manifest',str(self.manifest),'--test-level',test_level,'--wait','30']
        return self.run_command(cmd,'DEPLOYMENT_LOG.txt')
    def audit(self,org,offline):
        script=self.root/'tools/campus_events_audit_with_ui.py'
        if not script.is_file():raise RuntimeError('Auditor not staged')
        cmd=[sys.executable,str(script),'--source',str(self.root),'--out',str(self.run/'audit')]
        if offline:cmd+=['--offline']
        else:cmd+=['--org',org]
        return self.run_command(cmd,'AUDIT_LOG.txt')

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project',required=True,help='Extracted Salesforce DX root directory with sfdx-project.json')
    ap.add_argument('--org',default=DEFAULT_ORG,help='Salesforce CLI authenticated username/alias')
    ap.add_argument('--audit',action='store_true',help='Run built-in 94-check audit, including org read-only queries if available')
    ap.add_argument('--offline',action='store_true',help='When auditing, skip Salesforce org queries')
    ap.add_argument('--validate',action='store_true',help='Validate full patch against org (no org metadata commit)')
    ap.add_argument('--validate-ui',action='store_true',help='Dry-run just workspace switcher and Campus home LWCs with NoTestRun (eligible development/trial orgs only)')
    ap.add_argument('--test-level',choices=['NoTestRun','RunSpecifiedTests','RunLocalTests','RunAllTestsInOrg'],default='RunLocalTests',help='Apex test level for full validation/deployment. NoTestRun only works for eligible development/sandbox/trial orgs; default RunLocalTests.')
    ap.add_argument('--deploy',action='store_true',help='Deploy only after validation passes and --confirm-deploy is provided')
    ap.add_argument('--confirm-deploy',action='store_true',help='Explicit approval to write Salesforce org metadata')
    args=ap.parse_args()
    if args.deploy and not args.confirm_deploy:ap.error('--deploy requires --confirm-deploy')
    root=Path(args.project).expanduser()
    if not root.is_dir():ap.error('--project must be an extracted Salesforce DX directory')
    patcher=Patcher(root)
    try:
        patcher.patch()
        print('STAGED:',len(patcher.created),'created,',len(patcher.updated),'updated,',len(patcher.skipped),'conflicts preserved')
        print('PATCH REPORT:',patcher.run/'PATCH_SUMMARY.md')
        print('MANIFEST:',patcher.manifest)
        valid=None
        if args.validate or args.deploy:
            patcher.reconcile_contact_duplicate_order(args.org)
        if args.validate_ui:
            print('Validating only workspace UI LWC components (NoTestRun) ...')
            if not patcher.validate_ui(args.org):
                raise RuntimeError('Workspace LWC dry-run failed; inspect UI_VALIDATION_LOG.txt')
        if args.validate or args.deploy:
            print('Checking live org with sf CLI (deploy dry-run) ...')
            valid=patcher.validate(args.org,args.test_level)
        if args.validate and not valid:raise RuntimeError('Salesforce dry-run validation failed; inspect VALIDATION_LOG.txt')
        if args.deploy:
            if not valid:raise RuntimeError('Refused deployment because validation failed')
            print('Explicitly deploying only manifest components to:',args.org)
            if not patcher.deploy(args.org,args.test_level):raise RuntimeError('Salesforce deployment failed; inspect DEPLOYMENT_LOG.txt')
        if args.audit:
            if not patcher.audit(args.org,args.offline):raise RuntimeError('Audit failed; inspect AUDIT_LOG.txt')
            if not args.offline:
                summary=patcher.run/'audit/summary.md'
                if summary.is_file() and 'Live org reachable: **NO**' in summary.read_text(encoding='utf-8'):
                    raise RuntimeError('Offline-only audit result; Salesforce org unavailable. See AUDIT_LOG.txt and summary.md')
        print('COMPLETE. Live functionality must still be verified in Salesforce UI.')
        return 0
    except Exception as e:
        print('ERROR:',e,file=sys.stderr)
        print('RUN FOLDER:',patcher.run,file=sys.stderr)
        return 1

ASSET_PAYLOAD = """
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
YjJD4fliuLwqOYPMsdcYw//Qpzfxl/j5XczE5sRHSKiMtkuOTqvnwT34pze8qU0a25mVvOKozHKrVGHSNwxOB6HkH19Ei19QSwMEFAAAAAgAAAAhUOqfXb+DAAAApQAAAC4AAABlbWFpbC9DYW1wdXNfRXZlbnRfRW1haWxzLmVtYWlsRm9s
ZGVyLW1ldGEueG1sbY1BDsIgEADvfQXhbheNMcYAPZj2BfUBG7oqCQsEsPH5Nj17nsyMHr4cxEql+hSNPPZKCoouLT6+jHzM0+EqB9vpkdGHmTgHbDSlsFARmxmrke/W8g2gJsx9fabiqHeJ4aTUBdQZmBou2FBulYhM9o6cP1WMK8Um9m7V
sJNOw5+P7X5QSwMEFAAAAAgAAAAhUCP+fYrEAAAAXwEAAEkAAABlbWFpbC9DYW1wdXNfRXZlbnRfRW1haWxzL0V2ZW50X1JlZ2lzdHJhdGlvbl9Db25maXJtYXRpb25fTGlnaHRuaW5nLmVtYWlshZDBCsIwEETvfkU+QJq7hIKooBcPrQqe
Qmy2dSFNyiZVpPTfTWM9efC4O29m2RH30Jpc3Jx+5aLL92CMY8MwFFBhh2BDdlQtjOO4FLybiKvricEjKoygQR9IBXSWoWeVszVSCzqb2EWERZSdbfLdxK8En8fPAaMC6JPLkiglfS+JG/HontkyKAr+rzdhchvX8oQtSFn9JF3A9vA3KFGz
ff6igEaR9ssUtzkfWKnu+FSGlaHXUxHrulZIPjXEP1Xy1OviDVBLAwQUAAAACAAAACFQB6/YCB4BAADpAQAAUgAAAGVtYWlsL0NhbXB1c19FdmVudF9FbWFpbHMvRXZlbnRfUmVnaXN0cmF0aW9uX0NvbmZpcm1hdGlvbl9MaWdodG5pbmcu
ZW1haWwtbWV0YS54bWxtkcFOwzAQRO/+Cit34oAQQtXWPVTtBcGhBIlb5DrbYhTbkb2JiKL+O25aRCu47Vi7M29kWHzZhvcYovFunt3mRcbRaV8bt59nb+X65jFbSAYrq0xTom0bRcjTjYvz7IOonQkRvWrzuPNBY669FXdF8SCKe2GRVK1I
ZZIxUH0yUNsGJYUOQfxqqDHqYFpKBHKDexMpqKPg2rudCfYkkj9fKtt2ka96dBT5s3JqjwHEpQH80D/hICd+EJdPDJyyKCcLfpW2vEgDMW1BwGPfeuXI0FAOLV4BVpUG8XcFIg2pl/Mu9TzNDGK3/URN/xbEesbHcdycnEqfT3RVFfKXRHE4
HJLN+RzomKC7SN6CmAR0Zop9Xb+DOM8MxNWPSfYNUEsDBBQAAAAIAAAAIVCHdv2ZkwEAANMEAAA2AAAAZmxleGlwYWdlcy9DYW1wdXNfRXZlbnRfUmVjb3JkX1BhZ2UuZmxleGlwYWdlLW1ldGEueG1stVTLTsMwELznK6LcqQtCCFVuOPAQ
SBUqqJwjN9m2Br9kb1v4e9YJaUOpeAkOkeLNzM7srBV+9qxVugIfpDXD7LDXz1Iwpa2kmQ+zh8nVwWl2lif8SsGzHIs5pIQ3YZgtEN2AsWCF64WZ9SX0SqvZUb9/wvrHTAOKSqDI8iThs5Z8D3OSCTmXCPrGBBSmBDoS01kDBttap3QrNOS1
wGAh5wtFD4axMKA4ew/isqJXOZPgG0LxgdBBdNhbVbZjzMS+CxAVeM7qA8cXB3kzCGf1gbMPA/7dzBUFKdU3530H/umsv/PnQQmEaiQDnltD8iZG9ZXR/ax/dNyWxt468Cg3y50pu44m2/WuhFpCfreU5VNxuSJmERcY0AusN95832Ov23kn
KJLwS5pMw0AaBL+SsP40oy2h6BB+dXk1ZfvDq6tFIM2RmILKz4V2y5DWSaT3UFpfpRHNWRfFg50+QomT2LNJrSg561Y5eXNx6ZvcSddRJ7pBseu11TB5g1xAeELrWttsS32bIBIaF3Uh4Wzzf8qTV1BLAwQUAAAACAAAACFQ3FDh+xoBAAAe
AgAAMAAAAGZsZXhpcGFnZXMvQ2FtcHVzX0V2ZW50c19Ib21lLmZsZXhpcGFnZS1tZXRhLnhtbGWQT0/DMAzF7/0UVe/MBSGEJi87ABNICKFpnCcvdbuI5o+abBrfnrRradludt579s/B5UnX6ZEbr6xZZLezPEvZSFsoUy2yr83q5jFbigRX
NZ/UJ1WcRr/xi2wfgpsDeEtu5kvbSJ5Jq+Euzx8gvwfNgQoKlIkkwXIIr7mKa7xAFVi/GR/ISI5tTDpr2IThbfL0QZqFJO0O/uUYe/9qNSP811EVsVSl4kbI7bV7Ik+i4za4ANK2YLFmV5OM6a5D0y4K1iF0FYYf13raixC6BuHq0gQ1+cDN
O+24Fk8dWHomS89oUx0dNVH6+2yxj5bttmD/HRc/c0mHOiBcujDCR9QwQLapeR/a9NJADaO3Y24h2iH9CQnCODf5BVBLAwQUAAAACAAAACFQ4+60+rMBAABZCAAAPQAAAGZsZXhpcGFnZXMvQ2FtcHVzX0V2ZW50c19Xb3Jrc3BhY2VfVXRp
bGl0eS5mbGV4aXBhZ2UtbWV0YS54bWzFlk1P4zAQhu/9FRGXnrbOsoAQcoP2AyQkQAgW7bEanElj4diWPSnw7zExLUmbXWlRpOSUZN6x32cyyYSfPlcqWaHz0uj59OssnSaohcmlXs6nNRVfjqen2YSfK3yWN7DEJOi1n++VRPaEMW/Aznxh
nMCZMBXbT9Mjlh6wCglyINjLJkk4eLHOv8Vl2MnH201IElYX2hNoga37TSwsaY1GTWtBN96vuXHGoiO5vdomQ0OFGQYzjrPmvF9GLxazHIVxQCZIm+t+6QpUjVkByiNn8WLXKPsvp5/lKlEuSxoWbP/gcGwsKYweFgqs9WNTKXhANSzW3ZMk
USZ/jHv0FsTo/eiFMypwKhyWk1w9OtuTzKkcFuvbUTo2laidC0nfrf0nWjQpFoufUNnaL85WIckvrkDHL+vQENdNxddtHdv8bZ+uYHcBmYeYLCS6YLYnvxXvDp9do62pxf4ytmIJa5JK0stF0PjtIsaeiHOw3RCc9Q9JXoEndJdvn4os1jqJ
tf54yZP7uCFnbXFMDx6sAsJtj4Hs5N3nD3C/31W/0D+S6Tz5YLKzRAS436SuITjb/CVkk1dQSwMEFAAAAAgAAAAhUJbsxia2AQAAYAgAADsAAABmbGV4aXBhZ2VzL0ZpdG5lc3NfSHViX1dvcmtzcGFjZV9VdGlsaXR5LmZsZXhpcGFnZS1t
ZXRhLnhtbMWWW0vDMBTH3/cpii97cqnzgoys4gVREBEv+DhierqGpUlITr18e2OzzXarglJon9Ke/0n/v8NpTunJeyGjV7BOaDUd7o3iYQSK61So+XRYYrZ7PDxJBvRSwru4Y3OIvF656U6OaCaEOM3MyGXachhxXZBxHB+R+IAUgCxlyHaS
QeQvmq3y72Hu3+TC4yokEIpr5ZApDrXnVcxvabQChStBM96uubPagEWxuds6Q7ECEvBmLCXVul2GHwaSFLi2DLWXVvft0lcmS0gyJh1QEm62jZI/Of0vVw5inmO3YOODw76xBNeqWyhmjOubSrIXkN1iPbwJ5Hn0rO3CGcZ770fHrZaeU0K3
nGjL3tneRIp5t1j7R3HfVLy01iedGvMrWjDJZ7NzXRSlEvgxuxSowLnZM0hZLa7Kl+5pbqvSr/o79PvXUd4UbG8gUh8TmQDrXbfk1+LNKbRttDa+yA/zK9SyRCF9Za69xm1WMzRHGIj1zqCkfVrSgjkEe/N1ZiTLUke+wt/fevQUXkdJXRqS
vQMjGcKmQ881Wbo8Y/ZxqboAt0DdaABvsbFFsP+0Tl0hULL+WUgGn1BLAwQUAAAACAAAACFQXBD3aU4CAACUBgAAKwAAAGZsb3dzL0NhbGN1bGF0ZV9Tb2NpZXR5X1N0YXRzLmZsb3ctbWV0YS54bWzFVE1v00AQvedXGIsr2aSCgtBmqyql
UqVSUBMQPaHJetJaWu9au+O0FeK/M147jus0qOLCyZqvN2/mjVeePBQm2aAPubOzdDqepAla7bLc3s7Sb8vzNx/SEzWS58bdJ5xqwyy9Iyo/ChEclOOwdl7jWLtCHE0mx2LyVhRIkAFBymVQ5t8bbHXM2FL0HDLDoH1eUm1co8Z8gyGBZOF0
jvSYXGQJ2CxxFZUVhYRblAYJswQ3aCnGgAhtBlZjQo7AhLEUfVSZW0K/yfH+ElZo1ByMrgwQdk0WBIz969XresDxvPKesc84Y5kX+FuKAYA0f8ORognL0juNISwfS1SnFblLqKy+w6xuIkU/yivSNVVGNEFJCwWquass/WyRpYi+vcaDdYTe
PhB3TIzTUOP/UNP3x+ztzC5yo6ZHk13kRrWMriIVKMoqtFTijKcxyELuktqCOA+U+LANRodc88xLDzY0zs8uq+doFt3zS/FsIivI6n8Fz41Yie2KQsPoItuuZwOm4g8aLBj3GtfI+PpJ4l5MirZK7DVpjq7vgRDyW7t0u/JOgU9RAJ56L6Uh
u5fYUBb7TV7SNh766U7oQ12HeQebiv4FjmQg8NQ/nHeTA3fz9Gq0sxY1Oa8kI9xib9GDgx6GpejVirb/BnwOK4MHFa+fmHhhC/L8WPGPv3XIPMydMRjHUmt+FpAl7vs446KWXJGvYqyx2P0lrmdX1Nr1qXR8htQO6NvxuaqKFfp/I9gFhwy3
zF9C8PlT+G/84o1RFdSZhzVFxWtrJEX9PqrRH1BLAwQUAAAACAAAACFQRJthLXIEAACeFAAAJgAAAGZsb3dzL0RhaWx5X0V2ZW50X0Nsb3Nlci5mbG93LW1ldGEueG1szVhtb9s2EP6eX8EVBfIppuxmXhcoCgInwwKkXpF4xbovBi2dFG2U
qJJUWm/Yfx9f9C7ZTmKjSOAP0fHR8e54z91R7sW3hKJH4CJm6fnxeOQcI0h9FsRpdH6cy/Dk/fGFd+T+QtlXpKCpOH/zIGV2hrFgJBuJkHEfRj5L8MRxptg5xQlIEhBJ3nhHSP25JIs/Wf3eVOl3cUNgEQEIn8eZ1JIrEtM1Go/Rxw8oThHj
EQogJDmVSMYJ/MNSOEM+ZQIEyoiQCB4hlQKRNEB5pvZVcsH8GOQakSjiEGnRyMXNTey2cSqBP8bw9ZasgBY7X2t1aKY34OjfH95qx0eznHMlvlKqFsqI/1zcedcqpBv0uJg2UBlnPgixWGfgXeaS3ZI89R8g0Du5uLlq8Rx8xoPfrW9WZuQp
ScD7QPjfyxlLMgoSAhcbYY2x+2qQjRPya2jDJotlPtHR+cMb/zRVy9VjH/LZG0+cGvK5AfFZmoIvGa9lRi4Jj0DeQQgqkj54vxKxvLfn5OLuYq0OD+hzw5iq6IvODmEMNPBulGf2v/Yqy4ATreb6S07ogrm4krSBj4Tm0JYZOVBIVARrI9/e
mYMZ6R17i22duKNUm9hxQWVjlstLIeIo1aqGvbuXROZiufSHndxku5Bc8fmTWW0kS1O8y+DN5rls9Zc6Ic9kvDGtENj0xQP5uz2nrbjOjsGc/qgriKJ/yXWRJwnha2TCIvbM7tP3G7L7dWVeESET8++VgVX6LM15Pz8Xe4ZWJckqfIErW3Lz
ST4tmCR0eSklpAHAAVySWmGl77AeFeRqnv1uvgXgx7rh9rjWKsODRLsDqhQFFdEyDkKZdLEnxSanGyhWdPtZWfdtg52z0gDdyYcQtQaeU+getHGtjJk6GaI7btdjg1QNJ4i1Ubcsin1PzRWmCTVlG14QA6lBIZSmwG5n7wCsr6sqGzdinlO6
qY7YGMTRgxyo7BVgxRgFklpISKgAF7dkfZ14k9JGgLpx3zAOmLVu158RSpe6w4ktE0G13+CUYVPyvpz/qnPupipu5IhOqBY7XJGvQjWM9cjSNHCQKwrg55ouqDShQO9FlXfTPWetbkN97rilYjEv/LfularKYFSIJxdeE76C0TfDRPy+7XBb
xc3lVl+IWVmwLS2tDxkIR++tTo7hLYa8wMhuk3qSjd2XnmiimjVbnFITKeFykBA/Orv4sCcbulemA14+doznVb2eM/nSYbA1yhNlL6XPHeX7k99r8ull15Pn+XSdBkt9mV/q2/xu1271hfyBpAeY3Ic+JxxkeN96CbNR1q1Qtb1uRDh8ydWm
a/vhQumuBG2goay22Zs4k+nJ2DlxftaHVEoH0No7b/LuzHHUb+Q4zp/FC2ah4U/fNlcdfhQBNx9C7otlzdaGuCwtdS1RJ8FjsqL9S+Wu4qq/WBml8zxZ6U82laDR08SMKbr55htSMTO1ZE3ojW4oNco+NgG/mVJZI4rno/LIW45sdmxHRX7t
fglTXrwrTkJpjlI/HblYE8X7H1BLAwQUAAAACAAAACFQbdN7fOEGAAD8HQAALAAAAGZsb3dzL1F1aWNrX0V2ZW50X1JlZ2lzdHJhdGlvbi5mbG93LW1ldGEueG1szVltb9s2EP6eX8EFw7ABqZW0Tdq1qorUcbYAadrFWbF+MhjpbHOhRZWk
nGTD/vuOL5Ip+T1t0X4oah7Je33uqLvEr+8mnExBKibyV7sHnf1dAnkqMpaPXu3+eXX66Pnu62QnPuXiluDRXL3aHWtdvIgiJWjRUUMhU+ikYhI93t8/ivafRhPQNKOa7uI1WrAPjndyhLzjKCDEGahUskKbxdVYAjzCNUBOYAq5JhJGTGlJ
zT65Zf9QmeF/ekxSLhRk0bDkPBrSkmtSUD1WhOYZoQRv5Iqm5hblJKUFTZm+J+kY0ptOHIVCY5ZrkFMGt+f0GnjyR8nSG9Kz0i9D6f/+8KNxQKdbSombJ1TDFZvAf3HU4hDzlYziyO3HhRQpKHV1X0BiOMdRSNlB16TMOEklcU4nkFhWg3cF
IAtL8ILOVNNNBcgJ0xqy17UoLlK791dy8OwIqfWy3vmYHBzuz3Y+mshYv3ZFnkOqhUxiTeUI9CUMAR2QQtK1MRhYveKovWvc3ObQpjiHOT5ESGLCOX/Pu1WWHCpfGC8MjvNscDylDI3kUPkkFXnGjAnnYsTSBPEQRy3a7Ayy4zDUHygvIbDL
RdgZ1ulrqks1GKTonfmzsUB3U2Nc71NJ+ZWIo5oSSzYauwtJjOHBdHILoz3BpGnhIjwSR+HlKNR4O+2BajW4hAllOTJfb8ZvEm+AvBrTfJkpeTm5BukWiJlwuVrtpUAaC0TAoK/LbAmUgssO0kHcPcYjj49oljc7sYRUyOxciJuyqLDTcFAz
lc4FzXzlybCCMa62SqHnzQyiSrFRfoGYtv5QZ8MLcWkVUqeizLNkSLlCA9aeW+W7sCqs9NuQcYyrMj+AZ8kZ5oX7tRLCUxdJ4DBBOTPWzrGGydxWHPlLUS0StTplUmln1buc3ydalmj6go1YXP+NKnvDDF49AVNISHhX6qLUx6UWE/RzSnnN
a+k2QqMBg53YvTE1IFrwCxFx0CF9tDDVRLltgi7V+LRsBYzHz1rI4Fjv39D0xqs+W7utU0xWNa7xEZDc/ntaKmhsO8oqoIS1ZoAmM3xqVkNmx0GlcpP3z6BbOcD5Ce40uhKZXpjlEHWRZa7xZXzBrb8RIY0Tjql947piUogceZ7lSlMU7yFp
N/Fhxki+pxIvORRZeQ4MxwUzzCodpvM1tmGuQVGzulYQnROyWKpVa73QykWfLc9ia70gUsfis6RJ+FQyCVlL4LUQHGjumDqgNkgr5Dw8VT3kMEfHCHohkF91aUawm78DzRqbnoALn97tRF+cAmG6P+40P/oe8go8+fXbJzviYsjkZKv8PoGC
Sj0JSqBLRkzfGm+zM+Tnbn+P9Ht7pIf/3rw53iNv8Qv8lyqFza0g1U+kKDJxm78Rd40kN02C/dW3AMbXuyLEqQ1QrboyCmL16aMJ7Z0lZ/u9zc/2tjiL1m5+2Hhl0WmmLn3aeVwEhCANmiX4hnGuFoTH0okYkjPTi4DC8CgTKvyUc/2SgglL
BcevomUROjM5fGqWmwYoUNijc7EJXyGTa3yHyfukQzy90RBtlbyHB98+eV0FArnhB3EDId4BAxPdeZz8xPXL4qeRftnlpjm9QBrRwnzSWK/N99zo0ap5Zsr1z9ip0RF2E+QasIUBougUcdExrCPLe1kFYKrg9N4pFgCswslXL/j9MjXddRMz
jWqf4vcIxxcs2woyzw6XQSYM+zxmAkBtBplmKXDWrAv0R1HKRbOUMVUYQGxDMXyQfZ/Ra84Xwqi5qQoisszpXCM4C9LTsCHb8IP8a8bMG7QmZA1ImqyrxyN6DD6WSDazkg55j59jCjAzTQtDaC7wjA/49xnURkr2pBRyZUKWPCNoFGLVIXWr
KH+bzLRGbRXkIUIYk5B0TX31Efa4ZtzUXjPVVLYNRSD4RnTPwCEnWt67evy9hNuNXbvonmbIw/csDHgfw9qe85oBb/XuFBLlp1s/5EdPWrG3LGwH2qWTolS2hlSqHXsBwSl/w7qIFnBXbfqP0w0b7frRWf2Er5m0LkqaeYZtLqYXv5pNwt+K
zAxb3fQroOPFRQeX9IoWnWftVvFh86EN21MP+PVCWxOKzpdUIpvrjpZpEfZRX8D4xif/Usv9qW3kRWGmYplGQOkwtw6XldVmYq3qQpuT1pUpEHn5UyqZec5ns4kqhs4DK/uRruDc1YpZRxLQ8ITtcuqGy62Q7GYRs0t+bbxXq+NauKBbds2o
/7OD3bQVd9ahugK8QuMFkx1ze/Ewp5a/QBHT6c4pMmt/H6KIub29Ir1FivQ+S5HegxSxPfqcJkHn/hBV7PXtdXEjgDllwsnAQ7Rx91erY/Nalyo5kXRo54R2tRNH5k+Oyc7/UEsDBBQAAAAIAAAAIVBUGRdOvwMAAJELAAArAAAAZmxvd3Mv
UmVnaXN0cmF0aW9uX0FmdGVyX1NhdmUuZmxvdy1tZXRhLnhtbM1WwW7jNhC9+ytUY681nTTNLgpGgeGNiwXcuHC8i+7JYKiRzZYSVZJyNi367x2SkkU5jt3cerI5Mxy+efM0JL39VshkB9oIVd4ML0bjYQIlV5koNzfDz6vZ9x+Gt+mAzqR6
SjC0NDfDrbXVT4QYxaqRyZXmMOKqIJfj8TUZX5ECLMuYZUPcxirxJeROrzE3JZGBZmC4FpV1iwcoM5NAwYRMuCpzoQvmHAkrs4RLZcAknFWMC/ucPG2hTGAHpU0MMGsSDYxvk79AqxElcVoqSgt6J+Bpzh5BpkvYCGN1SD3J0Zc8sB0kf3/3
zlU4mtZaY9qPzMJKFPAPJQcJqDyVh5LgppVWHIxZPVeQTmqr5qwu+RYydwglsRc54i7LlElpUlqyAjwZ62nEAiXe3hzu3E35OsbBezsaJFJxb/gtvXh/jdb9cu/5ml5cjjvP17RBdO+OjAtdr/nIQ+sZ+zijrU0aX6Vv7ESCtm2IN1OEXAK3
SqfUMr0Bu4QcsAMc0p/Bru9ckZQcuiiJ9uVI6Uqz0oS8v6gMy276GNkpORqIAqlq+yvTiBi7uO/A4vF3zL9UT5+ylvwdkzX+gIQCU3do3i2BK52NXOQLJyXNNnL0oAfYuPg30xzvbRkNChpQ7eHMlfqjrtp6IjJjJS2BtUpqP643Cefy6kA4
xohNeV9L+cVVbT7l9yqwY2aqLrM0Z9LgV3I27pQwHtwnv777tmW1sZCdk4eQge5cgMxS16Twj6oKkFuMufuzZnKlKNlbzvbac4mNOtnx/dGIbia0sWHzopTPqdU18nDEQZVXXtqd0BioQWSwqC3KyI0UJwWOLW9zveqmpK+IAQ5eLtwI7ubN
AaOxRu7VfsjiR1zivXD7Jo38cN3XSAY5q6Wdti2aNzOtO8KN8GMxVNcSWsyBnxlKqIWLTc+EO2SuNoKneHF4IcS2LgbTSMitl9+RmTMKlCzbkn0jjmzoRDR3A33LyoU+IictNtuwFdHXxSPosEBm4iV2KgokMdj/DtwyW5vzeM+gxLmDZYfF
osLrFu/5JB5ITnBdyGnkr3/JbQdPfsJBbBMpGyE+opCdShsRkkYWpJN1OwQ/V/gQgU7mfcG0t6lt3xKeusSqJES9QeRXH/oi/z9MHX/hTPykdbF7MJFCGky7lz0PDPRb3LvJeolfnVmk34cBnsG0jTn9cfwKpX1CT6roxWvppJwabAdXboc5
QF6hoDeg/TNliu9LC20xsYfaaBG65F+D4TEYOx2ZrnRPAfKfftQst97qVgNK3NswHfwLUEsDBBQAAAAIAAAAIVBDGQZtaQIAAD0GAAAsAAAAZmxvd3MvUmVnaXN0cmF0aW9uX0JlZm9yZV9TYXZlLmZsb3ctbWV0YS54bWyVVMFOGzEQvecr
thHXxgFRWlUTIwpFQqIcIEXlFDneycaV117Z3lBU8e8drxPiJJC2p8Qz4zdv3xsPnP6qdbFA55U1o/7hYNgv0EhbKlON+t/Hl+8/9U95Dy61fSyo1PhRfx5C85kxb0Uz8DPrJA6krdnRcHjChsesxiBKEUSfrolG3SdsfkLYwLIAlOilU02I
hwuciVYHX9xipXxwIkaLCxGwoF/pMAWmSP2wCHMsHErrykL5gprXKgQsB8ByTFAmoFsofLwWU9R8A/pLQroTCyx+vzuI3zc4b51DE2LXsarxGdgWAui9QMBSHhpnJXo/fmqQn7XBXovWyDmWsQuwPEsSea8qU1Nfz8GIGvkdhkneYhIJAety
SwZLuUiEjEnZlS0paCu76A9++PGEoi/Hl8wDPzoerjMPPKNyFbD2q8DY3uIMSRmJ/OC2k32ww28ykeTuTj3YBqnKOn7W5YC9BGAhdEsVqDG2zHpsmwFspwbY8jbbIc1yRXs0ZVLFeVupe4NY/lXeOHc0WbUiKFOd/peqh0ebqpbJq3NrDEr6
8DRKZ5pmunwqfNs0WmEZR/e1OnCtxhX3TuivdROeVnylNaWKja5tpSQXhoC2YusagtE4C/dRuX+19JULa0+v/E2rde6pU9U81XOYWqtRmHQKriWRN0LA8mqW05QrETgE4SrMnH/jdWyXdXgrjOTet+Tm5jthS33Zek564Akt5G5/GL5h9qbV
e2i/NXZ7edvpT/q3sW86U5ZxSDtwTDJW6Lp9ch43JcHuZiBkh2R5Wl1pc+VZYEmATojQen7hxCx00XjqAYsvlPf+AFBLAwQUAAAACAAAACFQYAoobjUCAADYBAAAKwAAAGZsb3dzL1ZlbnVlX0VtZXJnZW5jeV9IYW5kbGVyLmZsb3ctbWV0
YS54bWyVVE1v2zAMvedXaEGvjZJiy4ZNURGkLXZoh6LIivUUsDKdeJAlQ6LTFkP/+2g5cd2PDdspFh/5nvhIRR3fl1ZsMcTCu9lwMhoPBTrjs8KtZ8Pvy7PDT8NjPVBn1t8JTnVxNtwQVZ+ljB6qUcx9MDgyvpRH4/FUjt/LEgkyIBhyGVTF
dcutp8ytZC+gMowmFBU1h9MtOjqkUKzXGDATBpxBa6EBBWuIyoJzDPCnr9AJbAqiABK0QQF5joYY5miNgnwGD19EHTGKeYX3onBbb+DWcqbpKBcbIMIgcuTCykeKIyX7l1KFY3xb4N053KLV14n8tMSwZo8exFdwmWWCX+8OGn9GizoEvtUJ
EC6LEh+VfEGg7N94lGxhVQVvMMblQ4V6XpM/h9qZDWaNiJJ9lB1O/SzA2qiVgxJ1y7aaMyMpmUI73UUyVZRAZsPz7Tx0bfudIc5TYbC7jmXrGpEfevJxytHu2CE3enI0fkJu9O5a3xrxBZRVHVPPXcvzBPM6PKXtSlJbwDPbgymgcm59GcDF
Nnjhs6af1u9eXMk3E3mQVU2XEFiIG9w7lZZlb9EWbM0/aLFkzivMeQ/ZLn1whcaHbJQaWK2Mkq9SlNwVy1c6bwuXPD9Y/7P0RZv+3+KyvxwDFQkC9cf5YfyHaT6fpfH88gz5oBUzrLEn/nzXXqJK9kr97U/+ane/LVit2IFdWO2efpr2Jb97
fqBl+lNg2h6kZNtF6obqqE8C5JSizWmgZPNI9OA3UEsDBBQAAAAIAAAAIVCfwejJJgIAAOINAAA2AAAAbGF5b3V0cy9FdmVudF9fYy1BY2FkZW1pYyBFdmVudCBMYXlvdXQubGF5b3V0LW1ldGEueG1s7VdNj9owEL3zK9BeOBXTqqqqKmS1
BSoq0dWKRL1Gxh421jp2ao/Zzb+vk/ARlm0LlbbJoUhIaObZ88a8eU6C66dM9jdgrNBqPHg7HA36oJjmQt2PBw7Xbz4OrsNesKCFdtj3YGXHVyli/okQq2k+tGttGAyZzsi70egDGb0nGSDlFOlV2Ov7TyCrxREw9EVsHawSzFnU2YKuQIZo
HASkGTnguN9QyDnQktYWeRw7YIELPEY2IwecrGpMq11sQOSzkjXniZYua1Ju5L4iZM8yVXYFKd0IbcIl/HDCAA/IPnSKXguQPLylmSda/z6uRX5Z7FwaM9/+GRQizQRgkSSsbSJI0dn2eXwH5aB9GhHYcjaTuMg7wGYKlhmRl4N8IZld+GSk
jketTxoZi4WEMH7U22Ss81h/1ugtIiB1stfc+9hiuuw7EUuBOwmvYjznD5rBZEoRklhkHRDXTPF/Qmfp/xStZHEOpQ0of0bO0Eryc+3Mpdb0X/i7bssaE5pTJrBoU/g7Du0rPhbsATC5M4J1RPCxRiqTJdwLi7XoX/MqvpjYDSIoDrwbnCKg
aP1hZVQoL/ZukPoipEz+6iGqBacyIL3h84VXW7NexdmGtzffZtsGXshG6Hjpzvsmf4OZQu4vu+xP8FN5NUENsmFzQjx6WF8U5bImatv6aZeBTfXjzOtGTlJgDyv9FK6ptN48TxOHBXNxn0r/RXtH1d7CX8r0AlK/soU/AVBLAwQUAAAACAAA
ACFQn8HoySYCAADiDQAALQAAAGxheW91dHMvRXZlbnRfX2MtRXZlbnQgTGF5b3V0LmxheW91dC1tZXRhLnhtbO1XTY/aMBC98yvQXjgV06qqqipktQUqKtHVikS9RsYeNtY6dmqP2c2/r5PwEZZtC5W2yaFISGjm2fPGvHlOguunTPY3YKzQ
ajx4OxwN+qCY5kLdjwcO128+Dq7DXrCghXbY92Blx1cpYv6JEKtpPrRrbRgMmc7Iu9HoAxm9Jxkg5RTpVdjr+08gq8URMPRFbB2sEsxZ1NmCrkCGaBwEpBk54LjfUMg50JLWFnkcO2CBCzxGNiMHnKxqTKtdbEDks5I154mWLmtSbuS+ImTP
MlV2BSndCG3CJfxwwgAPyD50il4LkDy8pZknWv8+rkV+WexcGjPf/hkUIs0EYJEkrG0iSNHZ9nl8B+WgfRoR2HI2k7jIO8BmCpYZkZeDfCGZXfhkpI5HrU8aGYuFhDB+1NtkrPNYf9boLSIgdbLX3PvYYrrsOxFLgTsJr2I85w+awWRKEZJY
ZB0Q10zxf0Jn6f8UrWRxDqUNKH9GztBK8nPtzKXW9F/4u27LGhOaUyawaFP4Ow7tKz4W7AEwuTOCdUTwsUYqkyXcC4u16F/zKr6Y2A0iKA68G5wioGj9YWVUKC/2bpD6IqRM/uohqgWnMiC94fOFV1uzXsXZhrc332bbBl7IRuh46c77Jn+D
mULuL7vsT/BTeTVBDbJhc0I8elhfFOWyJmrb+mmXgU3148zrRk5SYA8r/RSuqbTePE8ThwVzcZ9K/0V7R9Xewl/K9AJSv7KFPwFQSwMEFAAAAAgAAAAhUJ/B6MkmAgAA4g0AADoAAABsYXlvdXRzL0V2ZW50X19jLVJlY3JlYXRpb25hbCBF
dmVudCBMYXlvdXQubGF5b3V0LW1ldGEueG1s7VdNj9owEL3zK9BeOBXTqqqqKmS1BSoq0dWKRL1Gxh421jp2ao/Zzb+vk/ARlm0LlbbJoUhIaObZ88a8eU6C66dM9jdgrNBqPHg7HA36oJjmQt2PBw7Xbz4OrsNesKCFdtj3YGXHVyli/okQ
q2k+tGttGAyZzsi70egDGb0nGSDlFOlV2Ov7TyCrxREw9EVsHawSzFnU2YKuQIZoHASkGTnguN9QyDnQktYWeRw7YIELPEY2IwecrGpMq11sQOSzkjXniZYua1Ju5L4iZM8yVXYFKd0IbcIl/HDCAA/IPnSKXguQPLylmSda/z6uRX5Z7Fwa
M9/+GRQizQRgkSSsbSJI0dn2eXwH5aB9GhHYcjaTuMg7wGYKlhmRl4N8IZld+GSkjketTxoZi4WEMH7U22Ss81h/1ugtIiB1stfc+9hiuuw7EUuBOwmvYjznD5rBZEoRklhkHRDXTPF/Qmfp/xStZHEOpQ0of0bO0Eryc+3Mpdb0X/i7bssa
E5pTJrBoU/g7Du0rPhbsATC5M4J1RPCxRiqTJdwLi7XoX/MqvpjYDSIoDrwbnCKgaP1hZVQoL/ZukPoipEz+6iGqBacyIL3h84VXW7NexdmGtzffZtsGXshG6Hjpzvsmf4OZQu4vu+xP8FN5NUENsmFzQjx6WF8U5bImatv6aZeBTfXjzOtG
TlJgDyv9FK6ptN48TxOHBXNxn0r/RXtH1d7CX8r0AlK/soU/AVBLAwQUAAAACAAAACFQKwqta0wAAABQAAAAKQAAAGx3Yy9jYW1wdXNFdmVudHNIb21lL2NhbXB1c0V2ZW50c0hvbWUuY3Nz0yvJzEmtTkpMzk4vyi/NS7FSTrNIS0xLtk7K
L0pJLdItSkzJLC22MtAzK0rNtc5IzUzPKLEyNDBQhSlIzs/JL7JSTk5KMU01rOUCAFBLAwQUAAAACAAAACFQS7ymbD8CAAAiBQAAKgAAAGx3Yy9jYW1wdXNFdmVudHNIb21lL2NhbXB1c0V2ZW50c0hvbWUuaHRtbI1UTW/bMAy991cQPlcN
mmyXwglQDLttu3TAjgYtMbYWWTIkOWlX+L+PtuLU7ge2UxKGfHx8fFQeqWkNRtpdQW50VUerbSUkegVRR0Pb7As2bRfg65FsDPAdLVbkM9DSWWGx4QzZheiau/TxeZMxFuRKH0EaDGGbBaOCaAV611lVNKR014xJb7MqrxWM304eW7jECmRy
VoTWE54TGlG6yA0XgCPiLq/XC9RIj1HUXMmzXdIfYqd4JLjf71H7AL+cP4QWJeWrep3AIG/f4khnnC9OhAfGcFJT1BSugUZ9rsFTpUP0GLWzgFYBxkhWoR2A212+GggmqlKcpp4inHSUNXmQnfeMJLBtWdmiSPIXSf5ikp9x3qtOol5a/J+8
HRP0YdJvMgTsnb8jlPX2OWpDoR8Dmv/eZkMgmyQaehzoKaXduPI3ydgvurJiqVXQf6i4FW4vbs87HHcxi69T3KCvaBb+9GrloUFjJgaQo49aGlo0Ld0jJJ4zXw+mnTk3UR5+9zA049IEnK+WNVMnyOvNx84aiyem0bUTzdRmPKeezbV5QXvH
XqVTT0ukIw3joVnCKQqyHxx1AXuhXPJKeVCDJZnzkCgHQ/agMKJIS3q1MWel0fKwfa7cT/eNPdwvZEiYF8lXZ80nF8xsvZq9KQs3/uOY7mXs0EBD0WsZgLk7W0F08IDsP3afJL6u1nl+hobDUhjq0vFLFW7ghwNFjbOXy9vrqvPEiZ6djCUj
MiEFfCN0c1ZtYjafcnj4dlfzEf4CUEsDBBQAAAAIAAAAIVB2hRxWlgEAAHgDAAAoAAAAbHdjL2NhbXB1c0V2ZW50c0hvbWUvY2FtcHVzRXZlbnRzSG9tZS5qc3WSS2vrMBCF9/4Vs1MCIXfvcBe3pdBFW0rbXSlGkafOXGzJaEZ5EPzfK78a
J2lXRppz5nw6mKraeYEjPFCxEUu2uCuxQivQwKd3FahyZ9QqoVH3pLdUaCFnH2lP9iQb/X/styL6cN/5cvzUoRQwpWaGW13Vge+2MYbvXYWAe0Gb8+Xy2SXUHI4JCJXI8BfeE4g8QlJiql6dIRRCVosc2cQLxJgW1gza5hAsbdEzyQH4pHTr
/2hkNB+yzKgFGWdTxRJd2udp4V2oo1SblipVN97tGCdLmsUUo3/TyPBcatvFV9rqIj6znQKbDeahnAJ0tp/iO8dVOvYp59EvWBCL79r7JnjBLeEOWELeWjoYLW3Z2ho8AUzNP3HEk0SIrIyqKxx/lnxO9Tokj0CPfRMDEAx74wrjfD5p5LYf
/AZyxTDcx/gEPlYJFO7NPUSqGc5bmA3x+8XPtRzO+DGLgkONp5Qs6zGeI6patIV5WgdBTo/94F9NT7rCFJcmeB8f8qZ9gbLMtWiO3141MHZK1TXXQDNfQZM0yRdQSwMEFAAAAAgAAAAhUKX5207OAAAAUAEAADEAAABsd2MvY2FtcHVzRXZl
bnRzSG9tZS9jYW1wdXNFdmVudHNIb21lLmpzLW1ldGEueG1sdVBLSwNBDL7Prxjm7mYVKSKzU7RUPPTgQb2WuJtuB3YeTLKlP98RW6ygtyTfK4ldHsOkD1TYp9iZ66Y1mmKfBh/Hzry9Pl3dmaVTduPHvcQ6XKWQU6Qoj3McJtJVHrkze5F8
D8AJc8O7VHpq+hTgpm0X0N5CIMEBBY1TymL279+BblEDLVwMrOf1MSemwUmZycJPbwOyUNngB01uhSHPrNeHugnr5xQq9RJXVrCMJOxOhZvOF2y3Dzm/4FgVJ+gPypfjbw6cDZWF/77h1CdQSwMEFAAAAAgAAAAhUI2WfvlrAAAAgQAAACsA
AABsd2Mvd29ya3NwYWNlU3dpdGNoZXIvd29ya3NwYWNlU3dpdGNoZXIuY3Nz0yvPL8ouLkhMTtUtLs8sSc5ILVKo5lIAgqTE5Oz0ovzSvBQrhbLEIg1d3ZzyZN3k/Jz8Iie4lGNOiY6CchoYaFpD9OUXpaQW6RYlpmSWFlspGOiZFqXmQqRy
Eyt0yzNTSjKsFIwswKK1XABQSwMEFAAAAAgAAAAhUIp3u8GWAQAAdwMAACwAAABsd2Mvd29ya3NwYWNlU3dpdGNoZXIvd29ya3NwYWNlU3dpdGNoZXIuaHRtbHVTPW/cMAzd8ysE76r3wj6gCFp065Cho0HLrE84WhIk2ndJkP8e+utsX1AP
siSS75FPZMHYBQLG05OSr0ho2HqnDEFKZXb18ZICGNTpatmcMapETdJBQ/S9a6rUAVGmIFrQBDVSmb1MnuoFCNM/Hw2qO0o2s0xMjR1WlgmyjbZR9101YGRrgDSQbZ026Hgl73TtmX1X3fRMv6FOyBJwZmddq62RUsZFO+iwzHq2ZPn1O4SQ
MpXsm9ytIApIGBywHVAz3rjM/q55i/M+1U7HkWLjL/Ij50NCguEOACO8ZsuEVe2pyU6LZnfCIh9jdmrlItfuuNEZ39W+9rcD41ztJvvBuDzTjxBIBB5f+2gfgHos300fo4gubh8Hsw9jSCrfRcQ/8/7BwZkzuFYg5NcQPk+njwcOaRgnEk/J
6MRgLtjs2yP/WuLOGr7KWfvmdW5HtV0aTz5WV4TL2jrsw3/6ZnmDGvmK6NQvyw5TUr/7Wkkd6hm60Cf1cxBRkhLfs+9ZTaVKksrHNn3bpR+WgcqXiTo9Ffk2a59QSwMEFAAAAAgAAAAhUPGrnkeOAQAAzwIAACoAAABsd2Mvd29ya3NwYWNl
U3dpdGNoZXIvd29ya3NwYWNlU3dpdGNoZXIuanNtUtFq6kAQffcr5j4lgqTvinCLKC3Utlxb+iAS1mSMQzebZXfWWmygH9Ev7JfcdRNjkc5LNjvnzJxzWCp1ZRgOIDQN4I6KLStSxVRiiYqhho2pSojkWxaNenQC34sdFYKpUnPakzrDTvwr
1SE8L6uUZZjdPt1PFwsYQ5Sl6aQqS6eI39MZsUJr0xeUMhxu3LojTa7nj88dR5Ta2XS689JsOhdKFGg8FPdBV44b4SRDJoW18FKZV6tFhos34myLBnDPqHJ7qT6+dN2HQw98/fWZQOaM8XfXWnsRrYVRaAutH/RxivWdZbg61gGkWKMcQtQa
A+8Hvj+/YPJvHg1gJ6TDYZdGPfiF2RiFxiicjHbcNpQ6MFeNmq1QucSJ/xQY4+6HjWM1YbIwBbJXG/pJjixIJmHoqIPSBuI/y1beoN21Skhl0uVo42ZIHz4+unnjMfCWbHLOqg8G2Rl1HnsELC+ST9p/XMUH4HftrUWWvRFh8jT1+XrLgtnQ
2jHaYXil+iksHZ6W11D3my11r+79B1BLAwQUAAAACAAAACFQRqC4+5IBAABtAwAAMwAAAGx3Yy93b3Jrc3BhY2VTd2l0Y2hlci93b3Jrc3BhY2VTd2l0Y2hlci5qcy1tZXRhLnhtbI1TXU/jMBB8769Y+Zmry+mEEEqCoAJxEichAcdjtE22
qXX+kr0B+u9x4xaCygF+yu7O7k5m7OL02Wh4pBCVs6U4nM4EkG1cq2xXivu7yx/H4rSaFNeqW7FNybkz3lmyfN7bVhOkdhtLsWL2J1JGh34aly40NG2ckT9nsyM5+yUNMbbIKKoJpFOgV3/zzuoo7SzkKJERKl48exeprTj0VMi3ONcNRqZw
jQvS1YML/6LHhuD2SXGzolDIcT13tBSboDxvdmQcLIifiCxcKrYUI1z1C0DbwhyN7yNcPKb/jPAHLXYUpoUcj8hDGUNHHHM0ylR6J1hd37PSitfnmGhtq5/Br5yhm7TwW+Az7/exuyi+Izl3dqm6fao5D9uWUnzI/OADggf7PMTb9GGDD85T
4DVYNFSKpg8hSZrAAnjtU+aWQ+oXoDdGlWKeAYDew9nN76FNwEj2dCcjQVPX6R6a3iZy9da8+oG0Hj42LrowgAYf6+xjvfVxM2+JvebE56s5AuRILzkW7L3Ur+IW8n9PpZq8AFBLAwQUAAAACAAAACFQ82JEKBwBAAAQBAAAKwAAAG1hdGNo
aW5nUnVsZXMvQ29udGFjdC5tYXRjaGluZ1J1bGUtbWV0YS54bWzNkltLw0AQhd/zK5a8240iIrLZ0kALgi3i7TVMk6lZ3EvJTmL7702atjYiotCCb7vfmTlzmF0xXBnNaiy9cjYOzwdRyNBmLlf2NQ6fnyZn1+FQBmIKlBUNe6g0etb0WB+H
BdHyhnPvYDnwC1dmOMic4RdRdMWjS26QIAeCUAaBMIcGUiwqrWdgUG6M02Sdjg0oLfheEBrmqDudJWu21Tvas7slNI3lXIN9ewFdYYIF1MqVctaaORpp7d4xF/ybErFQqPPNxF2CPdhPmSIVLpfjFWQk+Bf6CQ7ClM3xkYAqL0cZqRoFP0D9
Fi9/sZ72lt4XzuIPO2ohA5uzbWEnByfZ1kSVntrTcTZ2mpB38P8z7h71KAH/+u/4tA8+AFBLAwQUAAAACAAAACFQdszYNQsBAADCAQAAOgAAAG9iamVjdHMvRXZlbnRfX2MvZmllbGRzL1NvY2lldHlfQ2F0ZWdvcnlfX2MuZmllbGQtbWV0
YS54bWxVkU1PwzAMQO/9FdEuhQNNQQghlGYaE0hcuNAD4lJ5ibtVpEmVuGj990Trh7qcLPvZflbE9twa9oc+NM4W6X2WpwytcrqxxyLtqb57TrcyEfs+kGvfGzSaxQ4bis2JqHvhPDjoslA7rzBTruUPef7E80feIoEGgo1MWHyi7o35hBbl
l1MN0lDtgfDo/FBVSvClOsIag/JNR1Fq5pmaeBZ3MY+d8xQlGVjNNITTwYHXrG4MxWMEX08YZ+I5ViyYDy1rMAEFX2UmR+fb3oAs377Lm9mz8tlK9Ta6TtRVT+kR6NWA/Q27IC/BLvygdwt/TYzNBg5olgvnNYKP+ZGhoUNZRlfBL2Ei+Oo3
5D9QSwMEFAAAAAgAAAAhUCNVXwBJAQAAFwIAAF0AAABvYmplY3RzL1JlZ2lzdHJhdGlvbl9fYy92YWxpZGF0aW9uUnVsZXMvTm9fT3ZlcmJvb2tlZF9Pcl9DbG9zZWRfRXZlbnQudmFsaWRhdGlvblJ1bGUtbWV0YS54bWyNkVFPwjAUhd/3
K5o9EEhwncYYI2WEAEuIOggoPi6X7cIau3a2Hcq/t8DEkPjg22l6vnNPe9ngqxRkh9pwJfv+dRD6BGWmci63ff/1Jb669weRx1YgeA7WmRa1QOIgafp+YW31QKlRUAVmo3SGQaZKehOGdzS8pSVacBD4keexTS1EAiVGiUpnbuBaqXfM05lO
R0IZpyY7lJbRs49BZvkOI6trZLQ5eAy1VnqkZM4PbWKly1pANEzG7ekymby1O10yWzg9n44eV8On9jE2TXWwtGBrk6ZZl7Q+amV7sZt0Uo75DzAXICXmZ+bXiWBNusASuHQf5xDSErbXJ2Gnw+jfjZuXjLmpBOxjjiKPmsCsYS7uTvZnNAa2
GC1wy43Vx40QboiqUBIlxZ58Fk7ZAgkewkgBhsAOuIC125s5FA2a+J8sj9HL9UbeN1BLAwQUAAAACAAAACFQsDnehNQAAABSAQAANQAAAG9iamVjdHMvVmVudWVfQWxlcnRfX2UvVmVudWVfQWxlcnRfX2Uub2JqZWN0LW1ldGEueG1sZZDB
SsQwEIbvfYqwl57sVBERSbOs68GDoKDsPW2n20iSCcmkuG9vMYLLOrf5/u+fw8jtl7NiwZgM+a6+btpaoB9oNP7Y1Zmnq/t6qyq5z4nJvfafOLBYKz51m5k5PAAk0qFJE8UBm4Ec3LTtHbS34JD1qFlvVCXWkSMGSyeHnt9Zc07q6QfgKOFf
VBq4rOTjFFA9m+N8IJsdSvijxbK6R6sO6DOKncXIEgoqcbA5avtyKSUJ58mvm3tr0vyIs14MRfVW9t3EGPfknFlvXzqVhPPnqG9QSwMEFAAAAAgAAAAhUHWokrizAAAAAAEAADcAAABvYmplY3RzL1ZlbnVlX0FsZXJ0X19lL2ZpZWxkcy9N
ZXNzYWdlX19jLmZpZWxkLW1ldGEueG1sTY9LD4IwEITv/Iqmd1kkYowp5WDCTU94JhWWR9IHtsXgv5dYNe5pZuebTZYVi5LkgdaNRud0GyeUoG5MO+o+p9eq3BxowSN2mp03qhxRtmRtaJfTwfvpCOCMmGLXGdtg3BgFaZLsIdmBQi9a4QXl
EVmHdbOUF6GQn9E50WNdNwx+y8BIcUP5BRgEGyL/nJBXuHgGb/kpoO79wNMsW+mgQ2DxPo8WW94J6dZTPx8x+PuFvwBQSwMEFAAAAAgAAAAhUHHjLbSuAAAA+wAAADUAAABvYmplY3RzL1ZlbnVlX0FsZXJ0X19lL2ZpZWxkcy9WZW51ZV9f
Yy5maWVsZC1tZXRhLnhtbE2PyQrCMBCG732KkrudKCJF0vQg9Oipei2xnS6QpWaR+vYWI8U5/cs3A8PKRcn0hdZNRhdkn1GSom5NN+mhILe62uWk5Am7BOeNqiaUXbpuaFeQ0fv5DOCMmDPXG9ti1hoFB0pPQI+g0ItOeEF4kq7D+iDlVSjk
d9QBm6ZlsEWRkOKBMtYMoomFf8/Ia1w8g6/84agHP/KcrnCUMbf4DJPFjvdCuvXS5hMGf2/wD1BLAwQUAAAACAAAACFQeUU21xUCAACCEAAAOQAAAHJlcG9ydFR5cGVzL0V2ZW50c193aXRoX1JlZ2lzdHJhdGlvbnMucmVwb3J0VHlwZS1t
ZXRhLnhtbNWYUW/TMBDH3/sporxTF4QQQmkmWDcBQoDawKvlOpfGm2NH9mWQb49Td0vSAuqEJpy8JHc++352kvM/SS5+VjK6A2OFVsv4+XwRR6C4zoXaLeNv2fWz1/FFOkvWUGuDWVtD5Doou4xLxPoNIVazem4LbTjMua7Ii8XiFVm8JBUg
yxmyOJ1F7ki2zMKX7Q1wTK/uQCGlPCEDp4/iDGGnTZtqLMEk5MH2zTnUUreQp2gaSMiDed9quRE1upn4HDb6IbCMtNmfdYORgZ2waFgXY7sB+h5+jBstDpd70/UB87Hz+Yy93ccYkH68UtTpepiAUjeFUbNPQvosiWRbkCPc9ZjRB/hg61aq
8w6ycy2baujx3hL4LeTv2hUUrJF4wD9xj3sVAmSefmaVC/XX43ZkWwmD2+ftnoWcwJyLVzBpz+XbaC4A2z1BwJTIsLHhQxqkK/eS0UxUEDjtlconw/odVBM64yWrGRfBv0mZcDFIvxrBQ1/RDTC0dA0VE8ptoIHT+vyrxm819L1uTOgF61pI
SSdRWjONTNIjOTAB4reIoHLIA4fdgO0UK+0U6VOgnk93pEouD4p1APUHjt+lr5h1AvNTrwkTMnQd5ONYBv6DKnzMip8rC+enEvh/iZsmv1/xCWKvoHbirJrgDIYcXrBNbAKPrIHBcG9u3fZoqS7oB+VqBtinfXSGlenoo/WvRSsh/d+EdPYL
UEsDBBQAAAAIAAAAIVBj0NTLpwEAANADAAA7AAAAcmVwb3J0cy9DYW1wdXNfRXZlbnRzL0V2ZW50X0F0dGVuZGFuY2VfUmF0ZS5yZXBvcnQtbWV0YS54bWyNU9uK2zAQfc9XmH1JC93ICaWUoCgE0pRCsgvpLuxbUOWJI9DFSOOk+fuO7Wzs
XFhq/KA5OjM6czTi07/WJHsIUXs36Q8HaT8Bp3ymXT7pl7h9/N6fih5fQ+EDJkR2cfKwQyzGjEUvi0Hc+qBgoLxlozT9xtKvzALKTKJ8EL2EPi7zPEAuEWID1KCSRpWGwGzhg6WV+LX49GMPDjcbNXjxKM1mDbmOGCSSuEjweDV7SyZJ+qX6
r7gzRHAZZO80dk24V+wzZ7c6Wo1VE3gsQBRAPTrk7Ix0SLAH44nxJC2IxfN69bqcDYl6gbd8HWcK9R4EhhI4O4ctw8qIEJbyDxjRtCWdgmRNIjnrbrYpkdoAMeKsWTS+s2vjuauk1L4kN4XdWSYP9W2/VH3W5Lg5aNzdOMhZh9hk0jBYieJ3
aa0MR85OcbOZB18WNFhx7g/u0mb4GaQj84PGo3jyDmqrL9CWv9VgMnG+3spfOqkGO46QsOeQQRBziCS1jU/m3FHDlTeldfHmrG7nd4+kOeqm/nehztR+WC/u/GFOz0qbeJqbLtLjrHmg4h9QSwMEFAAAAAgAAAAhUJBrIT2bKQAAWoIAACQA
AAB0b29scy9jYW1wdXNfZXZlbnRzX2F1ZGl0X3dpdGhfdWkucHm9fWlz40ay4Hf9ihp5HSBbINhte/xm1c2OZetwa56ukaju8egp0BBQJGGBAI1Dh2VF7I/YX7i/ZPOoAgoHqZbX8zpmLKJQR1ZmVl5VlfjmL8MiS4fXYTyU8a1YPuTzJP5+
Y3Nzc8dbLItM7N3KOM/EkRd7M5lui1R6wSCJowdx7kUymyapL8XO4YHYElHie5FZvPtPkSUF/vKKIMydjY0z+WsRpnJBfXqpFIFMw1sZiGmaLMTO+c73b/4qxlkWzmKsI775zhEXmczEKQEmstyLAy8NRBRep176IOBRZFMEwNk4TkTg5Z5Y
JEE4DX0vD5M4s2GIZZQ80JC2mEbJnfD8PLzVrxcy96hZcivTuzTMJRQmKfxvJuT9MknzzEF8bIQLfACoZ0svzaR+9rNb/RO6kXm4gOlmIsh16S9ZEuvfSbZBM116+RymIFTxKTzqKtm8yMOofCqul2niyywrSx7Kn/eLyJF5KqWzFxFOJ/Ab
B9+b6Cq/hctpGMmNjeNzMRLW4zzPl9vDYZZ4S4ep5PjJYvjd69c/Dl//MNTIeLI2PozP97AJVRp4y+Vw4QGXBHLqFVE+tDZOzn5yd/f2xxeHE6yXFUugZZL+x9/+5xv3xzdRNvshzWe3N4v/NYOGEQ5jbWz4kZdl4py4YntDwD/oULhuGIe5
6/YyGU1tkSZJ3ue3+A8LHSyDYRBTPXrvAHGA+kUm017fSWWWRLey16+3gulDI4UE51/hch/+9soO+yKcVt07YeZivV6f2Eq3glL102woo0yK4ySW5YC6K6hcwY7/sEEGYGRAEBlAJ3kvdrJlFOY9a2j1L19fCUCyiEUYlz04sbeQUZjlPYIx
dmQcZHchTN7KpsH9AJjiF+nnDjKX1e/3awNSJ8tUTsN7GJbQleEoWwLHw/4YJJqDZbXb4uAEMYDaAVE1GvZQnywCC5SqUCWGogvkCtn19vhv4eX+nACg8SoCzaLkume9GnahoNULQBLJuKc664vRSLxpj9VkMFUd0OXAMoc19afPLvVCQDsy
4nGS7ydFHOylaZL2rNM0uQ0DKfK5BMmTpyCmQDLW5akahgiIUioEMhKXE6ta/Y1yTc29TC8nGRlgqClAYYNLZV6ksdj3gKTlC1w9JAi2sMFGo27PZLQtseyXHMwMZKwI5rUa3pYGliqwUb+sg5t6wLnV3xpQGQxdgxN5uOy9grqaXt8JpJ8E
smcV+XTwtwFoIcsWEomTjawU1IjnS6uT0dZMk/ofcv84vJsDbXsyhpHCeDZaP1adnq4XPyjcMPg26Icp/B1ZloGLcuWrqfHzV8gpxhYOAvIp90DzkcRpUJl+sIg0xBIDooph4qbEQqFTl3DEH/0mnXDkpSGFsc0S29T5hgFwUiUNrC01Nkm2
zqryHuRI1lNSm1l8YwOxCirUvfWiAmR76hPL2SL3Zgqb10nwgGIw9ZlzkIgbBjPi++3mLBT/5anxCqmxN3FQ92d5CnTvYdMKASh57p1pGAc9yxkOLcAzKOwtAqXdPw6fizAj/YNSIHeQqcoSmiWXOTjcUqlFee/LZY6AnKIFQ2KnC3xGDYhB
/8ZAy6LIctdP4hzMgBGOo5CkFyYgqb0udadHB+fnB8c/WbqF2ZmGu93q9GzvfO94Yq0nRrM29u9FUS9D1qFWyEj0ZA6ruME6HZ9NDsaHetqp/LWXe9mNDbJVLmwy1WDy+cNS0qzRYlxcy1Q9xFIGkX4DeJDVWlRwBaGfU48j7jatbOBRNcRI
jaMMMJfGo1GRwJZlvFLj8x/9VsHBfxQk+J++mtZ1EUaBa4ydad2Uji6vSinjBUHvlWeLV69u7vrbqQN2H6zjHiIFiqmUkY4VrTeWbR2Gs3keA0sLqCtwwYsdMKyTSIrYuw1nZGeznQ7yI/euM2gEVSNtoQ/Z03DZ03CVp4EjD3DKDixRaLED
lEsW46odlnU1tOySjS6tdwDCBHD4XoH0bqgLoPk7BOb9eeKHMn9wXf/dkArKN9RvR/mZnIE4SQmKjtfaRxnsIJ/5+cr3IOXBIlz5etfL5tcJ/NI1rhjzyMzJ9S/IzpdWBT10oAGGnw0YratqcWnKTRVOsTM0KR7h7xMW83M2pAL+r8NlbYKc
ULllw/v+6hEA/qp7nIzqFX62u5x410Z/WeKPLq19zwen48EdB7chmNHuHroUPFOyoGTg7oLzxSU78GuWpAopY3T21JvP8joLuRqzvESMQf/nqO24iwk4cAqdcdAs+iTjohxl6fmhRv0k9G9k7p6moa/eQ5c5MCf93pWZD2K4JIYSDxWJCIQi
QPLtSrA780U3JatJjvNc0rx5sJswijI3mboHcS7BGcqrcRS/2NNQRgFJwctejW8AxX27Z3APYQWLmlxkmzD3DZ7CMah/7J4HqtsWFUsw5R+pUge7ceOheu/QnzaP7GNxu7eGaPoJDAQvEqTf0ZcRSmBUKEZZNKNan7DSucxLcWRUcupVTHB+
qr2pZFJtCFMgTYsoOgbr5/3O+bth+YCrv3w431v1Zm/lmw8fxqteHYFiMd9dNbCkGE9UIIsCQy6zBvagqiZVgy800TpZ+BkSNnnMWbEOAHW3CsuMvhae3w1rFVrzhKq4YmB65zLLUCmhIhBoDaRJFIGrdf0gaIEbM9WLopwiN3Wx6VdMTjd3
Gu3qPKFBACVKDd9rMfNu2HqFpNXzzKE0a0+UBhV5ItQiF4dJclMs182qlAZfPyFDgMAU0FB5z+OAutIKFsxvEEaxLydJTc+a5S3wTYbAWfB0jrwMBNtgFwALo+dZsYTzhdxXCUE9KR6Yx10xtcpQeNHElH3QJs8zy+uPr6mvJlZpunRNqCbs
L61JknuRaw6ptB6/MBVVpxXC9FUiXCCzIzKmK5n1a1VDyQKlrhF67ufFYuGlD3ry3Qso8h6SAsUiUj4Db/IcPKKgALt2KLTyB7no04yhFdev4B1wN4dU7PBbE1x+YaypWgPLZmfiCCYFePYjoKCoIRm9Mg8jRBgkY8Nb0dk2ZTla3poGIOyi
YhFnb/Xk0A8XC+8BnJQpENppatCLpZ8s0LY/Admp9wJovNtQ3nVJFHz5Cd5lQ93WxbbKSHf06xoiVJkpXroaN4DbPHrQEs4q9ymWabKUaQSE8eFHsLkWwqMHV3WQvRS+dtOGmg8jkBrnCASKh/Qhn8NsQA0b5daVovFOkWKkUSR3MYg42lw5
CsGP58oiSEAbo4sNZp13DRDORQZ0G2RKvHM16P4t++zALorcno87B7ghIiNNW1q9ynmQHvhNZxID+4hrw4nYLZT0+JgUqVrP+2BjupVZ21zM31WLGcZYFJEHi/pp/Up+0Sp+IuGl+m66Q3asLFvDCUIDfjwF3Lhk31t1K7ey4M+8eCabb2sW
vdq3CqxOq1g1w6XqfpDEslSx5pzVXZfdBJFu9TuRyC4LWl5hwNoiRbHzGHfYy1WlM6gDpfGTUy8zkfup9sYwoGNGLu2Myfd5WoCrrB5QN1Bg8gh4CTzsurz8DhGpFBkyUsQRdJQZKQ1h6WeGT9V1zFITwiOzdtU3kx6Zgg3hBWnjqmAlTPth
CtJqC6Qq/TmdY4DsvwNEGhh/1cC0zSoI0/oaBO5XzTMoODIimVeuo8S/AWcP1UGI27JEG6hf1qvP9QPWh1WvXrraYiBEO7VGJip2zRcVNA4zOXWqFdkOiSZ4WQA0BCMpH1i0SQqSq0aSTHgR0ilIOMyK/VQzzGpqag0S7rwU1CQNsyWWiMrV
CPgMdTvmj0h3iQovR0LV1sXeNSLOyrlXivctxe9w2lFyN0BdPvAimcLU5dy7DZO0NeUq7Gb65GoJ5nKxRNsA6lFBLcTGNNXSuCbMAPJpmC74oRzBoT7MGVMPk2qQ/6/u64qzCCk8d77/z3dD9bvUk6epzMi1USNj4DiSM89/EOMomXtDjHi/
BZbKlhjQqlBEIAkNsBmBJfNoIdOZVGGLFqLP2ugl0sCruyS9wQMFLYvd0W9MpH1WZR3RORK92KmKAypA3xcx7oQE/2NZgNr3n0MpmLO6Yc1UZ2U/9r1ALkKfqURA+KmkhmClc2FTG31fqfRU+kkaCApIr1LrXAdpxrq9ejbxcFaWtvW7WKOD
lqCQ0Tx73/Cl3w3LNzXp+D0F/3jSyokEm4gWaqDs3y6rvdHkBeZ7Z8u6+APzFCmqsDkgbCpT3CtPvYB5zvunvhd3GebfN4j3gsl1NHvBBFe2/jdNUhmTIBkF7obf4FKWMZjAMuhyPUpWei5YbZh5wG/c4z7KX8V0ZknHSjIju2YUeM3qAeau
z+NPN4upYwT5IyyEJH1QU2kVt5ZITb6VjiL793Nu9HxownDyXxqbqAWy9UQ6JtGcgEGQ+j7QOADHEeOayvpGrUF2ENq/4P+CcyTTbmKdynQRcmwQw8VKzi3L0gzjw0ieWpE516oHCgdPO5iHDYvxdOqBheieTKfgYKR/DN4z3GVTUKZJpMVu
UrdPsFYJSkl3HRw8+bwrTkm/iDPpBeIE3E+D4JUPY0YJn11hjfBgNvfQQT1CR/Q9DvNuWCtqcSUvG4ItxbN6nTHZP7jgayOr7p+DpyQEHVARqrJIpmZkBOqpF2xblvCZpSaU50Z5DcrOHYMSBvTZvcAMjTRi/xQgfk+QIeuZS05FyakahwcO
5W1JFLOkhoMfaOXSkULeky4wMvFLgrv3HJzKeDMt40jUbzJNapYpzo83PNk+UIsVK9djh05Vq2416FKNqK7GRF+C7e8AmhIf1XNNdti8V67CBvX45fWDsbNQhh28vIocqmdEow9UJNujIpuOJLBw82IMIRATr+8p47L9KsRhdqnX1K22tFkR
mZ2Ca5qG97U+Z2lSLHGjYOynSZY1Oy0DbQqnE5D57hF4MHOz34l3DQCltY6ZjyYfD87do5PjyUeTs/jXDk4cd1bKV1etgMcPJMeYs7Qko6fGuQBlUOKbNlvQVnOztqUI3OBivd2lBLAot9lFb+YVM2mD1xkXuS2uvRTPAoEl8FaF2ProPurq
Tfiagr3s1ymb1JxGXdhwn9Z0VBcLZa/sL4HHE4LmDS4yCWSqvywdqE8yDad4HKZIBdhmKXpJQP4luKgxL2w8L10iRMUf0UVKi5g8KTxuS+iQwxWxY0PX/aMAw9xtey1NK0DF6Lxb2XzzQUJ3Ur1qHLwDFIbRg+p+J0oy0qI7XuQXEbnwarng
KkHpw5tqe+Tsxf6D+xHmFXVo1r8iN+3jOXHFj+zikVXWcOn2yZ2b6oM/x5JirhS8w6p2iWRYlbOZTId5iGttGCWz0LcFnaSm0z8ZITmQ1wVYuHgIFBZOzRz+K9oWMC1cfyxoeavSHaPb6Lqmfqy/aDw+rysb/baoapyBUBHBLuOXsFhCzMEM
Niob3mMD2hfYwI2JYb8Gxn5ElzsNUQAbbgfgObsDDcoHksCdkXE2x9C6Qjqu8MTPhj4tyQGrtEHVXh3acRaB9nn2kdrQR1r1vWWcfLLVjhYPKP0ixW0jeQ9+eqz2cfBMZQKWRAVOxkuMA2SZCKEDXhK3JVd8I3ZQnA+Mk1Ti4sAMbWTbMB7o
MIx40KUDPFesrlikxXWKHAj0wwAhuHN5glAEBTDrxT+dCo0XBxT5z2PcSPhYXNMprxT3xGJgdrXrpC5lVLO2mke8ksWiiNFPUl25n0Ex0A/os3HWq2Sk7kNfa7sipaXPeGnAOk597eA9BOPwlmnr0JTr11/ak26fcWvN+SuOtT0z1e7zbV91
rK15eK01QQxHZeC8ShGkyTJI7mJx+HnHUAd/9269czq2hJGEO394p1ucAwb8OYizVonzi7kPVgUpd3SvHwoUuip2VmuK8zoukXkU3oexo56xvj4W57qAwZousHzXfY4pqE4nNr8WLyk6qammPmDpOrlO7l+AmXleJ/hLcRPp+gNj8CQG4zOe
ydHjnLTZDj09fdWs2NYPwb4Rt6En8NYRiiYwe15E705ufunkgGdBK+fvy0m67gXD8wGtTvUWmTvM9u6XoOsDZdxXz6ZxDzxi6wmxff8sh+hieHJLbGkorH7T+qj+9Vat00Z5R6dNpYmkmlqPAP2TKE9egEdVEk/NqSlqrC143LJWCZdVAgax
dDm13hUlqt8/qt9P74ZGqUZtJ6Aaz+pYdYY/puGswMWSlTQGK0reh0vADIKr2gDIZfFKwPexxinUsDRJbTozpRiLnN4WU+HJKbNCy3rs+IdiFar6vBsPmHpHNm6H7DT1YWUuB2EGWv0hg+XEy6qiWyYjMHbwvk4s5uBp144p02KbcpfQY2nv
d5UpMbJugXW0ahw3G5SADTSBhJo12hOjzWcl6uZ6nMwTMFwqxND1C/QeUJAucRMnvaUQ7ssn/lUiphMD6qCSOEObjs74qW32IzpHn7Vn9CEBSY+av4r2DTAsSORlng/kFG8uquM4bB9Ay0bEsCM+uTKCWE2wEUrsjnLifkm1pN93SqJ3Q7PK
esrVp2tOdfX0TMk5JqXyB2bX7qQ9ubUs2T1LdQcj3dg42puM3cnPp3vno8t1zNNpiNU9JOOceiO43ToO3DxwURdtxskic1es2noxZF/r2EFz27m5KVvtN9YHbWKew8PNWGQt3qajLLWoBTm/Vxsb/7jYOzsArD5uCIuPJIUyc/2kiHNrW2ye
7x3u7UzEzsnF8aTXF/tnJ0eiig5vAnAWe1nrm2h7lhrUAovr2zW2G6i5zxv0z7RU2/jUgp16F6Mfz7TC+Iv4/HHvbE8cZErCjATaKuZUrx/cjIN3VTfltpKtejwI+oJlVg0D4qezk4tT8eHnqkWjaxZwVc/aY//qjnWDDmRD90EVGTWh7zi2
vWLABk3MCXV0wgSoAqk5dmQizthBeumARlMapuJfmKev7pGYpK6ulqwYqmLtahSjVQdGQVa6RDtjHE2Sl86ntkoqY5qOLbj6dICJu10M9eORSbSSbMH/vaBzF3Z5YILOyTOrmDJGsTm2wQQAvGVT2040TydY4vDg6GAi3rw2uRW9KRB1bn2r
4BkZoAbuPngMoNRGwLQOQErepv3KntsHI8W7eq+Y6sGlrBZGlweBLdo3iWzRvEjUGJPx8t3r17URwpiO8b0UdGNDGmB+81qcnNXK3kNZfSBSBjDJnA88LvHA41cOpuWE+AvQ/ySOwD6wxPh4VzSuQwFN4iKKGkuMtm8yis5WwzEHolqOZA4L
U5kyiMbaeXKZlYg0llyJymqCLsff3Cz2lhhba41lyt0KUfYK9mqAwUKng19WkNhAwYOb8N4vq5WXKxTCNL5GDe7oZdjc39AbzLWRl3qP+U8eW+0pV1vYNOqt3rj8c0erNsdZRaBF7FaWp2scNlk1ZM0WMvLOMBS1t+WwXXY4AVAh9d8PRPuw
QAPT/34Qauh/4lvG2dSV99IvaNtMXzD2vThAI5gyemD+EsfH8DkmznCgNv/ivCRJRqkBMFeHBXNS6RTwtV0Fd8r+0JuuOjevj1MymABvi1M2HeduHvrzXlm3imZgLhRVuzMZgn5pOhOU9UVdFi9iN5v2vHSW2QJT/4AuG4GAVTOv5QDAXBpV
Oh8HmvYuG/iiy9wwWUzVgn3Cn0trMKCcIlc2zHUJAEgXBlnCOBNYGTCqvFc/10U4GvkmOnJNVPCrv7WcAb2Tc0oXYJtTmHDFvfslno3vY+Yhed+6xf9olabuGyA1jQu/p9Yjbjj25H3fcV2kuus+bYtHeY/nAAGsrIhQWCO2nzqw6T1EiYck
Ruw4+DvrLZ0sD5qg0/u/n58c71J2j0bWg6ofA05MFIKwY32kyRu7BJvHgCcsL8e7HLwB4b591Q04MFmtR50jQ43tzGTeUwP0W5BdqjdXAGKtwYI33wBZGiSA4jVCUXN9VRu1Pj3wYhAhPU43gNeseUR8VhlvnMVNEKY9fsgUm1EMx01u6LFf
NaGMWZzThBAdFItl1sMLGbA6UTCNvoPGcYZ862V+GI4o/Qam5aLtzxEo1z5mJvqvGJmywaZ9Bhs3wzIXN7FcjCX0AMcKbLCRAC/wzDhRyC+TdIRg2eDOgS97UNOmq0u17BTodGcjeMccE3W0wfwN3W00HTgvA4cHMotWcfm2DEM2X6h+uFRl
YGhDrWppKPTgl+qHusWOWZjKV1cm9Y2cU4Do3j2PrQ8LgRdv9TnPyj0KU9VHA4Z7mwYntm12gKmnOFsIOsVMol8LmT70ECVdYlDDie9rRLMfn/p11NiXVzVJzXmL6N22KYvLrpO7kXp/+brCKE7vRtJGACyz+2X6GjeEEN5PHsZSyaG0GsmE
GmRI7gg06KZvi14Y5/YUVlXe72tAoAhrXUINA2ga2r4l3EIXmO4ja+aEgpFu/jJCDzcNrwt0zwjTJhvaq0a8rQvpse6DZTX6bfyLIlL0s7+9BHugrc449QmGeTjlS5LObDzlBZIA/k6naNvz0i2zm1Q7zaOu7CKlvoaZM3MZW9OIKosSBlpX
oyrTDBWjXAF1R7/5CI+O5uFSGz2yUEUuC2WgH5O4gpCZLknw1rRLpzd0LcVEaj5myiTEpnX5ZvjDlaBTzBiubmQ4RKqUoWw8wgH8RKcB8cZe33EcC0hUZHNDRBpjdppGjfHx5+fx2fHB8U/bKq0hwxuL0/HkowOGNW7R4/icWJEvC3J2RSMz
VTstG54AGylr5dLCtQeMTwsV/g4GvME2AKJbNlIeivTL0rdlS/EknXlx+Bv798qjB2Jp2+E/XtfzYymy9HB8XtxKyfZHo0ZVTZu4Tpp1KAJgRBF7t14YIVZRkmIXXpHPkzT8DWw6y0axV42ulSZJ3apYKd/+5fb3f319VaqPJiyaTb5DNjlU
nICJIsskkr3y1/j0AG/13OIFTspAma1mEVwleMtXVEHqOgK+MXmxHEIdlOOzQ+W5NMqrOU0isAgGfAvWqZOE8pCAosCFf9UkQc5isiPi298uW9Z9IKvdyWjUCEcbbeuXWhqN6ZwRwU43w7hRmxnQOIauiF8tVOrwR6NlFUPr93QhwbLzq1av
ADmPvY39b43Q9uYCIBv9bbdh5TUyHIF2gjjQCaO8VYrwkLoYPVrJjbXNPbUWCZiUdFHC2u6wgqDBmp1p+Kft1p7Ze20RmC/UMuCcUn3lHLWA0nkjn1oDV+Yla44hUsgtCTNEm/+JUyTaCvoV63xKC/0x337ztyfxSHkcNbouNwkfm1f97R+e
wGIElYc7FsC0PUMW9C0tUKqGiOYrDX2/cyUaUqZUA8aJPgHLmXa1RD5Pk2I2FxNWM7jcVy5vgnf0p5+H7DwA2cTnHzkQWfbxa5GA9TiCug4e9e5tWptb91vw38pkbGTym/46srpDyxzQ+cT4w0jpITrteVnA6gU3lXbLTVUVf6j1JA6OgdRb
DNqW1a+yPSKB3Pp6/DpVV2RyoMyFgbcMLUP9TX81rLlu9mbWplOibpVZWHG5AVPNIjDKWyt+uyURwailxErNRmst57bUrJlE6EJwoxp6ySVAX9Ma70wOPu1ZLAVU1QYRS1lwcKxqrzNBqqW1X8/CLHjyrLtLZQ5OC2p0RvCwC7190+bRuvl7
1M3/QOqRmYYr97oAWxp3uLEnm84w0zln0AW/Fh7tbmPEC0zHtRoawJKRTYyB1FD7nt1G/R9hQ/WS/lzVBaMydi8JhOcUhqU2KFsumeLDVXId2pIpYdUjhBZOljpwiuUSsy1zLb3pZBHdWnXKBMnrT9789ymodasXFBOhdp1yMvjX2qLaW9Y2
/CTHuk6gS0WCKwJxxTs82YuYq1J2WsjxGKnCXq2T/7S6Whs67OJ4/Gl8cDj+cLgHtmsn3+I/TISMjcEoa+9e8en+rxFExNboS321BGo1r5mxZ3vnE1SbFHeEURfLDJem8AQeevCTWeot55i7ALO5gDFKQuFigkcxl3wRnCVB24zjnbNRVix6
b1h+KgecIhspA9qR8o8ZW71vZf9rT8f8Ry0v262uxLsRvugYrgNBmtjNTUCdWd7NPNwYs7QIoNicXu+qchmrnPJ9XBmwAYXz7z+pywM60tOLwkWY0+Zjv8OgM3h+PUTgaJXD40XfZGrZ5aAtzqwrh5pXdWJ6U9lNCNIkEP/3f/8fcrLVJwbU
RwXw5vA15rsHeQ62wEplgF3WVECt3zhhJYFRCkJk1tXx2mBGOSx4FiMKW9TSuFpXbzFe1njD6VsNYwv1yIiOSiH/QcNWCAHKtIuLHXL+b7kwMwGTKIYy5mFgkaZeQhhQ6VyNQHx8Ag22f7C3u05tTzG/5ojGw8t+0PelckjqzhCsbTz1Z/q/
mQ4x8U1vtdev841ycmYop+y8dEBScoKBzGnKL5oyAkLrDPGwykttnoPqMIN4RpzmOi3z8NtvMIp/NaKptsurBNY1FPRXYtfMRsygs9A+Ppm4hwfnExPruh0bOLi8a6YaERPBsk2akW5BjhvxUSzd/3Bc69hZJsuejqPZlLeZA2a0ieT62e1I
60OTqR14wf3QgfeqtgOWYtyz7vB63R0FdyzL7kpnTvtB03mFf5V8DBwhTIRM90HL8dCNp2igrZz6+gqyW+vG5jChbeEtHG5VYq8c8W6EAO+Gfo43gcAsmc45DSp7ZAqg/ts73sbgk7m98hmFV89EipIDJCZGkbe4Djx07re13NYx4kodsmhW
+yVKKP1AQUbKpEDpW2BeqNrU5U/i8Jm3pL2KTnvU14cjDA133xRKyBz3VYi14ke9d5PitZ+X9aASZatYLB8beVEPOgs494DMg9zwjej81gxJ50YIdkw2i40Zr82FN7UG4qyIyZIAlUZKwsekQf1t8RjkjlZWTpzc9fqOl+HDb7AUevgNgoQv
tfbIDllKf7SZgXaMg2yz/9QeR327RHx5pEzk+FkK5KanL6L3uPmvg9NNSrAPr8rPAWw+8zGHzad+exgKbYL+wb5xMODvpy/taoeoujACCWzkz5GPtsWrV4+bP++db1YRTAXH8cnm06tXHZ0QwkrJTeH4jPopWe1JKJtLDMWjYp4nzUVYptjh
SfPFq1d4OR66ICvAXEMAghrCqYMCkBwcnZ6cTcbHk236QAaH2/ESBOm4k0l5Tw8757AqJqsoYp+zkuDlAPP+gXEO2TYcTvrAT1bQMWOQqwIDER3QHBm6jJYjrlcg2i0mqDJuSgFsQZj5eNIMKWATpPhlDnX9Ew0PR3ypJP8XMjHA30wA616s
oo5DHAbApVRYb4GimGNRpN6d2qtvA9j0o/GuYBzoPLdgL/nKAETrZ2bGqsTdXKay8rYdwQ48uOIhaPoy5SDNFo850NIy59MABhflN9+IXTKvQNngOPkceGaeYNbp3gREvnjTb69d63dxZuQW+p1ZmuSmwFeceI9+oqshfscufh8MBvj/7fI/
vxvZrvMwByqgHE51czPrNYULW0eV7e/LBID4unYm2f6xmfeP0xm0TyHb3702b/WARTyiF7RzWBaT5NO59aeAgUcC+Qlm+Yg72rBw6U/TQdy8iG9AhMWbVFNPjh42T8fnvOSbLVGfYNn7UYkN7uzD3uHJZzEZn/20N+lsqaXGRGijAwc2pTfG
yAETQPiTHG+RkCVNS2aI91wisBzwoxaYfgADSzZMlUIzAPEOURjXIQd/fse3iqwmMdX2qdawrWhLG5c3jMfLTcL85hVNzXhqzfDkP0UvUGleOR8dx5z6m6ppcrOpfO5NjPr8LPbB7d7bxQu2RojKQI4yWRXQ2zUYAcQxLDFCFVeAyYtz5ZL0
1N5kfxWiWVgPSeizyJlJlHPmJWdlXxG+aeH9rpppIV4+KwGun5XwplWY5bxucKAVi079x1x6fEccc8di8jRMnYJJF/D6Ol7IvjgwL4pnxXUm89Hl/VrzgSYD1oOxYdOxfojmaIvcX26SAbAJTTaV0WPEq3nM/orqbOF8bXVlzqyvDuh7FpRu
Sp/i59QwOAnWIOYf1sTC21uid3iyMz4U+lRrn8hdc0asyVxiOAXEvNosjjDQWy5Ih3c46Fr4ydlPyjwHxxe3GEBzJAmxAvlojkHitR4wfVus2tr/S2V31v2wBgUHYCkQoz5i600k+ebVE9oV9KxQjpYDGoVcaAAArxxR/45Z7d/UAnNqW7Uj
gjy9NfSm8Ub5ENzhFh9BQAfjyqCQ2BqJy3IwE+1ItYsDAPvin7hTVH6FUPTwwzMYU0BLg5dVZQqa1l+tt4EYL5flHcryoqX2+fU1wwS/csNX1XgvuLyJ6XHgD3Pbl9d+yZ3T9fUOq1MfVt8IwyTlbJrDL11ofNWF7hEq4wLZCNMSmzYuig4E
SN/5y6rzE3T8pz4q8Ku+hmhcnWQIcb7K+sBwoI4WgBWDu8SScpOgBUw3f1VKItq7w600zJSNx+bqwzUOStuidXqZYK8yP5Gwp/MWiGiY7wMtruq0AWKJb1W/NW/OKYVTJn+4RhLSZ6q6sV5dnPQ9OvtFCYYy/HLQFA0qcV3kORqx46W8Z22L
gF4nCW1XllkpoT4eSDfMY4UOvjPeJLqidMfHexDBmVBnx4dkGQ1rWUcxxYAKJJMlB5INi95W3+s0emOogG3U3fUmXShtVXkSLS7J+paXFBi16DrLIdiYOSXzHrLu1oaOzplMRrNQWwnUE7KoXjQXB41hVW6cRXKNyW0Az2DcZ7R7pFKwKpM5
K5ZLOlRno+vPdKJVhl8XTfwis/mTEuBk2gLZDhO+ECxDuVjiVlPOOWxro5+xsW9mns/sKtM6EZ8/N0q8QHMl618lDcHpXRxQIhrxC8oa7c01xildGor+U6gTm/gSVMv0gTKHp2q/u5q3itsho0tKJ4xL7xqjI+C0gLzTTtlbM4WJVhB18jaE
ZWnekzU0LMdE/51cRNHjzaUpYFB/JpbOQawSmpqazAdgGancoEK7RT7aWxWvcnpK/GJOGnIq/yqBbGkv18iiGlPu/QF1reJIThsMivLgV26j8FpSJpZYziiPC2mCks1fvSLBAkQE78mbqrdafLLQoaVbObSgCynTQYQavZ0tHKahpW6NKuA3
d3qTxhIg5VBmOx5wPmlFmAylV857qyTtVUZcTG6DjxQnNjMurx7G8M0NFYI+I0IsYw/MH71XyyHj4f7huUoyq+SsTSMf0lm8cVbPoLOsJXPUKaUxYRWfI2WKQzFG4B4Gs9SLka919lIDvC7C8s22KhVxTjfmOM8RgBguQ4kfYmh8b9gWb96I
0yOh40/q6FZIHyzgr0sEJa5tsaxnfPI5n1r1RbWdOd6LBK5IsnwNkEZGL8781cj4ZSb3srWcH+jrjyoNGKMa2U1JIt76A6D4fMkKRE2Yzc3vVngzlP+8hzH08dxKoHMHKutFWwHo0AyKpZICJNcqNmfGLCNE/Y7BQZPjKXb2gX5sZGnS0+nI
AsVbEsW1YoBWzyrY8RnQjzofXCqgmge2NLYLQm8Wg+2cdZjkX1SQ11kEX2zxpRlw/8JIJlOKE7r5AowTCtp8MY9SDV/RRvUXqv6l9EB1KUnIFtRKx9BL+G+a5W91hnVMUFlZMvoLNTcSw2Z4XviOD6HD7IBVJK48jFTDEsnIrFAXqofIQNqy
Ayyxz1But1dzt/rmvQE8+s/ni8i87jd3E5R31N6/53OvvGP/aLGTY23jdrwOzfZ5O2GbTlhwLBQe6O9XJAQRtR0RPHBRPdl0pMNVDry1rVx9Y6OCp0svseyptgnwX/H4YvcAz1gcnR7uTfZqWwRT61ztcKpIbEcc1m6HYe12FLa+86CDxdtI
HaBZTEa01YwTW2QRqMjh0DxgW++Od98y6I0JUn2EW390Eg09HatZjvSX051xOisQifQV0rQXVF/HG1lmwL9zV6D6AD2TX+Bn36tPvCOPkoHDn3LXm8JLxwsC11MD96wBn7zRl1CMb5nbcxkta3DoMDx2Xfov2ZTVcxR62coxFEuWw1iwLrj7
i/g3jves+bzzyRkMEYJqgxX2r4NTWrirp4P5Ispx9DC0X6I27/S52p6qJTjHHZ8DcX+Gf0dHu7vux49HR+fn/dUDcXzKsj2fKYZpmWElp5hThUc9YVuGjSjejQH4h2pyNm2/s8WnzrjjIY/y8z54tHfpEKfgwPomAV4igWU94qVBJ20dxm/9
DkTrw9q2vrqmP+j+wQvUl+BbV9YUZ6vlR4YSsLe8t7HhKHvI1E2r/lu1s/2d3ksd0ZfpCSq8ELbi6/T0aVpVhxcbNnP8u6DXH/asGkWsrfbOFci2KT72rG9//nbxbeB++/Hbo2/P9efPMZF7x+WtjrtbxlUPhgcEJLRWDyoEqWrSRF9vbADs
+qLeaGS5Lq5u11WBHcQNjJP3eM33N/4fUEsDBBQAAAAIAAAAIVAXUwDyJAEAAOYBAAArAAAAd29ya2Zsb3dzL1JlZ2lzdHJhdGlvbl9fYy53b3JrZmxvdy1tZXRhLnhtbHVRTU/DMAy991dEvbMMhBBCXnaYxmniwDZxrKLU3aLlS7E74N+T
dhv0wtHvPT8/27D88k6cMZONYVHfz+a1wGBia8NhUe93r3fP9VJV8BHzqXPxUxR5oEV9ZE4vUlLUaUZdzAZnJnr5MJ8/yfmj9Mi61axrVVWgHWYmBV3v3Jv2qLYY2uYdD5Y4ay6Dm1UMnc1+LED+CqFFMtmmAR67SKy0Tz2J9RkDkzCTPsFR
8BEFcd8WcuBYGwY5Nakg5choGFvVaUcI8g+AjMYmOziXtBZdq7YXs6YxJdaIAH8nVFfzTYynPoEcMZCT/gqo5MW8G5hVn3NB94QZ5AQHRp+c5qIY12rGtZq119aRvBT/3qnZ2MORQ3lUmX/zAXm9dgXy9jNV/QBQSwECFAMUAAAACAAAACFQ
PGGr4qECAAC8BgAAJQAAAAAAAAAAAAAAgAEAAAAAY2xhc3Nlcy9DYW1wdXNFdmVudFJlZ2lzdGVyQWN0aW9uLmNsc1BLAQIUAxQAAAAIAAAAIVBVFaRChQAAAKUAAAAuAAAAAAAAAAAAAACAAeQCAABjbGFzc2VzL0NhbXB1c0V2ZW50UmVn
aXN0ZXJBY3Rpb24uY2xzLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUG/cuETXAQAAqQMAACkAAAAAAAAAAAAAAIABtQMAAGNsYXNzZXMvQ2FtcHVzRXZlbnRSZWdpc3RlckFjdGlvblRlc3QuY2xzUEsBAhQDFAAAAAgAAAAhUFUVpEKFAAAA
pQAAADIAAAAAAAAAAAAAAIAB0wUAAGNsYXNzZXMvQ2FtcHVzRXZlbnRSZWdpc3RlckFjdGlvblRlc3QuY2xzLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUEJNW1izAQAA2QMAACQAAAAAAAAAAAAAAIABqAYAAGNsYXNzZXMvQ2FtcHVzU29j
aWV0eVN0YXRzQWN0aW9uLmNsc1BLAQIUAxQAAAAIAAAAIVBVFaRChQAAAKUAAAAtAAAAAAAAAAAAAACAAZ0IAABjbGFzc2VzL0NhbXB1c1NvY2lldHlTdGF0c0FjdGlvbi5jbHMtbWV0YS54bWxQSwECFAMUAAAACAAAACFQvtrvUvoBAABB
BAAAJgAAAAAAAAAAAAAAgAFtCQAAY2xhc3Nlcy9DYW1wdXNWZW51ZUVtZXJnZW5jeUFjdGlvbi5jbHNQSwECFAMUAAAACAAAACFQVRWkQoUAAAClAAAALwAAAAAAAAAAAAAAgAGrCwAAY2xhc3Nlcy9DYW1wdXNWZW51ZUVtZXJnZW5jeUFj
dGlvbi5jbHMtbWV0YS54bWxQSwECFAMUAAAACAAAACFQ3MfrPe8CAADADwAARQAAAAAAAAAAAAAAgAF9DAAAZGFzaGJvYXJkcy9DYW1wdXNfRXZlbnRzL1N0dWRlbnRfQWZmYWlyc19EYXNoYm9hcmQuZGFzaGJvYXJkLW1ldGEueG1sUEsB
AhQDFAAAAAgAAAAhUMWa/a7vAwAAPwcAACEAAAAAAAAAAAAAAIABzw8AAGRvY3MvQ0FNUFVTX1NJTkdMRV9QQVRDSF9OT1RFUy5tZFBLAQIUAxQAAAAIAAAAIVDqk+1ExAUAAMYLAAAnAAAAAAAAAAAAAACAAf0TAABkb2NzL2NhbXB1cy1l
dmVudHMtYXNzaWdubWVudC1yZXBvcnQubWRQSwECFAMUAAAACAAAACFQ691ACGMBAADJAgAASwAAAAAAAAAAAAAAgAEGGgAAZHVwbGljYXRlUnVsZXMvQ29udGFjdC5CbG9ja19EdXBsaWNhdGVfU3R1ZGVudF9FbWFpbC5kdXBsaWNhdGVS
dWxlLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUEfsWKmQAQAAWgMAAE8AAAAAAAAAAAAAAIAB0hsAAGR1cGxpY2F0ZVJ1bGVzL0NvbnRhY3QuV2Fybl9EdXBsaWNhdGVfU3R1ZGVudF9OYW1lX1Bob25lLmR1cGxpY2F0ZVJ1bGUtbWV0YS54
bWxQSwECFAMUAAAACAAAACFQ6p9dv4MAAAClAAAALgAAAAAAAAAAAAAAgAHPHQAAZW1haWwvQ2FtcHVzX0V2ZW50X0VtYWlscy5lbWFpbEZvbGRlci1tZXRhLnhtbFBLAQIUAxQAAAAIAAAAIVAj/n2KxAAAAF8BAABJAAAAAAAAAAAAAACA
AZ4eAABlbWFpbC9DYW1wdXNfRXZlbnRfRW1haWxzL0V2ZW50X1JlZ2lzdHJhdGlvbl9Db25maXJtYXRpb25fTGlnaHRuaW5nLmVtYWlsUEsBAhQDFAAAAAgAAAAhUAev2AgeAQAA6QEAAFIAAAAAAAAAAAAAAIAByR8AAGVtYWlsL0NhbXB1
c19FdmVudF9FbWFpbHMvRXZlbnRfUmVnaXN0cmF0aW9uX0NvbmZpcm1hdGlvbl9MaWdodG5pbmcuZW1haWwtbWV0YS54bWxQSwECFAMUAAAACAAAACFQh3b9mZMBAADTBAAANgAAAAAAAAAAAAAAgAFXIQAAZmxleGlwYWdlcy9DYW1wdXNf
RXZlbnRfUmVjb3JkX1BhZ2UuZmxleGlwYWdlLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUNxQ4fsaAQAAHgIAADAAAAAAAAAAAAAAAIABPiMAAGZsZXhpcGFnZXMvQ2FtcHVzX0V2ZW50c19Ib21lLmZsZXhpcGFnZS1tZXRhLnhtbFBLAQIU
AxQAAAAIAAAAIVDj7rT6swEAAFkIAAA9AAAAAAAAAAAAAACAAaYkAABmbGV4aXBhZ2VzL0NhbXB1c19FdmVudHNfV29ya3NwYWNlX1V0aWxpdHkuZmxleGlwYWdlLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUJbsxia2AQAAYAgAADsAAAAA
AAAAAAAAAIABtCYAAGZsZXhpcGFnZXMvRml0bmVzc19IdWJfV29ya3NwYWNlX1V0aWxpdHkuZmxleGlwYWdlLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUFwQ92lOAgAAlAYAACsAAAAAAAAAAAAAAIABwygAAGZsb3dzL0NhbGN1bGF0ZV9T
b2NpZXR5X1N0YXRzLmZsb3ctbWV0YS54bWxQSwECFAMUAAAACAAAACFQRJthLXIEAACeFAAAJgAAAAAAAAAAAAAAgAFaKwAAZmxvd3MvRGFpbHlfRXZlbnRfQ2xvc2VyLmZsb3ctbWV0YS54bWxQSwECFAMUAAAACAAAACFQbdN7fOEGAAD8
HQAALAAAAAAAAAAAAAAAgAEQMAAAZmxvd3MvUXVpY2tfRXZlbnRfUmVnaXN0cmF0aW9uLmZsb3ctbWV0YS54bWxQSwECFAMUAAAACAAAACFQVBkXTr8DAACRCwAAKwAAAAAAAAAAAAAAgAE7NwAAZmxvd3MvUmVnaXN0cmF0aW9uX0FmdGVy
X1NhdmUuZmxvdy1tZXRhLnhtbFBLAQIUAxQAAAAIAAAAIVBDGQZtaQIAAD0GAAAsAAAAAAAAAAAAAACAAUM7AABmbG93cy9SZWdpc3RyYXRpb25fQmVmb3JlX1NhdmUuZmxvdy1tZXRhLnhtbFBLAQIUAxQAAAAIAAAAIVBgCihuNQIAANgE
AAArAAAAAAAAAAAAAACAAfY9AABmbG93cy9WZW51ZV9FbWVyZ2VuY3lfSGFuZGxlci5mbG93LW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUJ/B6MkmAgAA4g0AADYAAAAAAAAAAAAAAIABdEAAAGxheW91dHMvRXZlbnRfX2MtQWNhZGVtaWMg
RXZlbnQgTGF5b3V0LmxheW91dC1tZXRhLnhtbFBLAQIUAxQAAAAIAAAAIVCfwejJJgIAAOINAAAtAAAAAAAAAAAAAACAAe5CAABsYXlvdXRzL0V2ZW50X19jLUV2ZW50IExheW91dC5sYXlvdXQtbWV0YS54bWxQSwECFAMUAAAACAAAACFQ
n8HoySYCAADiDQAAOgAAAAAAAAAAAAAAgAFfRQAAbGF5b3V0cy9FdmVudF9fYy1SZWNyZWF0aW9uYWwgRXZlbnQgTGF5b3V0LmxheW91dC1tZXRhLnhtbFBLAQIUAxQAAAAIAAAAIVArCq1rTAAAAFAAAAApAAAAAAAAAAAAAACAAd1HAABs
d2MvY2FtcHVzRXZlbnRzSG9tZS9jYW1wdXNFdmVudHNIb21lLmNzc1BLAQIUAxQAAAAIAAAAIVBLvKZsPwIAACIFAAAqAAAAAAAAAAAAAACAAXBIAABsd2MvY2FtcHVzRXZlbnRzSG9tZS9jYW1wdXNFdmVudHNIb21lLmh0bWxQSwECFAMU
AAAACAAAACFQdoUcVpYBAAB4AwAAKAAAAAAAAAAAAAAAgAH3SgAAbHdjL2NhbXB1c0V2ZW50c0hvbWUvY2FtcHVzRXZlbnRzSG9tZS5qc1BLAQIUAxQAAAAIAAAAIVCl+dtOzgAAAFABAAAxAAAAAAAAAAAAAACAAdNMAABsd2MvY2FtcHVz
RXZlbnRzSG9tZS9jYW1wdXNFdmVudHNIb21lLmpzLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUI2WfvlrAAAAgQAAACsAAAAAAAAAAAAAAIAB8E0AAGx3Yy93b3Jrc3BhY2VTd2l0Y2hlci93b3Jrc3BhY2VTd2l0Y2hlci5jc3NQSwECFAMU
AAAACAAAACFQine7wZYBAAB3AwAALAAAAAAAAAAAAAAAgAGkTgAAbHdjL3dvcmtzcGFjZVN3aXRjaGVyL3dvcmtzcGFjZVN3aXRjaGVyLmh0bWxQSwECFAMUAAAACAAAACFQ8aueR44BAADPAgAAKgAAAAAAAAAAAAAAgAGEUAAAbHdjL3dv
cmtzcGFjZVN3aXRjaGVyL3dvcmtzcGFjZVN3aXRjaGVyLmpzUEsBAhQDFAAAAAgAAAAhUEaguPuSAQAAbQMAADMAAAAAAAAAAAAAAIABWlIAAGx3Yy93b3Jrc3BhY2VTd2l0Y2hlci93b3Jrc3BhY2VTd2l0Y2hlci5qcy1tZXRhLnhtbFBL
AQIUAxQAAAAIAAAAIVDzYkQoHAEAABAEAAArAAAAAAAAAAAAAACAAT1UAABtYXRjaGluZ1J1bGVzL0NvbnRhY3QubWF0Y2hpbmdSdWxlLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUHbM2DULAQAAwgEAADoAAAAAAAAAAAAAAIABolUAAG9i
amVjdHMvRXZlbnRfX2MvZmllbGRzL1NvY2lldHlfQ2F0ZWdvcnlfX2MuZmllbGQtbWV0YS54bWxQSwECFAMUAAAACAAAACFQI1VfAEkBAAAXAgAAXQAAAAAAAAAAAAAAgAEFVwAAb2JqZWN0cy9SZWdpc3RyYXRpb25fX2MvdmFsaWRhdGlv
blJ1bGVzL05vX092ZXJib29rZWRfT3JfQ2xvc2VkX0V2ZW50LnZhbGlkYXRpb25SdWxlLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhULA53oTUAAAAUgEAADUAAAAAAAAAAAAAAIAByVgAAG9iamVjdHMvVmVudWVfQWxlcnRfX2UvVmVudWVf
QWxlcnRfX2Uub2JqZWN0LW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUHWokrizAAAAAAEAADcAAAAAAAAAAAAAAIAB8FkAAG9iamVjdHMvVmVudWVfQWxlcnRfX2UvZmllbGRzL01lc3NhZ2VfX2MuZmllbGQtbWV0YS54bWxQSwECFAMUAAAA
CAAAACFQceMttK4AAAD7AAAANQAAAAAAAAAAAAAAgAH4WgAAb2JqZWN0cy9WZW51ZV9BbGVydF9fZS9maWVsZHMvVmVudWVfX2MuZmllbGQtbWV0YS54bWxQSwECFAMUAAAACAAAACFQeUU21xUCAACCEAAAOQAAAAAAAAAAAAAAgAH5WwAA
cmVwb3J0VHlwZXMvRXZlbnRzX3dpdGhfUmVnaXN0cmF0aW9ucy5yZXBvcnRUeXBlLW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUGPQ1MunAQAA0AMAADsAAAAAAAAAAAAAAIABZV4AAHJlcG9ydHMvQ2FtcHVzX0V2ZW50cy9FdmVudF9BdHRl
bmRhbmNlX1JhdGUucmVwb3J0LW1ldGEueG1sUEsBAhQDFAAAAAgAAAAhUJBrIT2bKQAAWoIAACQAAAAAAAAAAAAAAIABZWAAAHRvb2xzL2NhbXB1c19ldmVudHNfYXVkaXRfd2l0aF91aS5weVBLAQIUAxQAAAAIAAAAIVAXUwDyJAEAAOYB
AAArAAAAAAAAAAAAAACAAUKKAAB3b3JrZmxvd3MvUmVnaXN0cmF0aW9uX19jLndvcmtmbG93LW1ldGEueG1sUEsFBgAAAAAvAC8AthEAAK+LAAAAAA==
"""
if __name__=='__main__':sys.exit(main())
