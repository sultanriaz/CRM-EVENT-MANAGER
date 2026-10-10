#!/usr/bin/env python3
"""Campus Events Manager single-file Salesforce DX patcher.

Includes prior workspace dropdown and Campus metadata candidates.
Default action stages locally with backups. No org modification unless --deploy AND --confirm-deploy.
See --help. Python standard library only; Salesforce CLI required for --validate/--validate-ui/--deploy/live --audit.

For eligible trial orgs, use --validate-ui or --validate --test-level NoTestRun to isolate metadata errors.
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
    def save(self,path,new,mode='safe',rel=None):
        path.parent.mkdir(parents=True,exist_ok=True)
        identifier=str(path.relative_to(self.root))
        if path.is_file():
            old=path.read_bytes()
            if old==new:self.unchanged.append(identifier);return
            # Existing files are upgraded only if they match the supplied reference ZIP exactly.
            if mode=='baseline' and rel and sha(old)==ORIGINAL_HASHES.get(rel):pass
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
            else:self.save(dest,raw,mode='baseline' if key in ORIGINAL_HASHES else 'safe',rel=key)
        for app,utility in APPS.items():self.merge_application(app,utility)
        self.dashboard_html()
        self.make_manifest()
        self.make_summary()
    def member_for(self,rel):
        p=Path(rel);a=p.parts
        if p.suffix=='.cls' or p.name.endswith('.cls-meta.xml'):return 'ApexClass',p.name.split('.')[0]
        if a[0]=='lwc':return 'LightningComponentBundle',a[1]
        singular={'applications':'CustomApplication','flexipages':'FlexiPage','layouts':'Layout','flows':'Flow',
          'duplicateRules':'DuplicateRule','matchingRules':'MatchingRules','reportTypes':'ReportType',
          'reports':'Report','dashboards':'Dashboard','email':'EmailTemplate',
          'roles':'Role','permissionsets':'PermissionSet','workflows':'Workflow'}
        if a[0]=='objects':
            if len(a)==3 and a[2].endswith('.object-meta.xml'):return 'CustomObject',a[1]
            if len(a)==4 and a[2]=='fields':return 'CustomField',a[1]+'.'+a[3].split('.')[0]
            if len(a)==4 and a[2]=='validationRules':return 'ValidationRule',a[1]+'.'+a[3].split('.')[0]
        if a[0]=='email':
            if p.name.endswith('.emailFolder-meta.xml'):return 'EmailTemplate',p.name.split('.')[0]
            if p.name.endswith('.email') or p.name.endswith('.email-meta.xml'):return 'EmailTemplate',a[1]+'/'+a[2].split('.')[0]
        if a[0] in singular:
            name=p.name.split('.')[0]
            if a[0]=='duplicateRules':name=p.name.removesuffix('.duplicateRule-meta.xml')
            if a[0] in ['reports','dashboards'] and len(a)>=3:name=a[1]+'/'+name
            return singular[a[0]],name
        return None
    def make_manifest(self):
        components={}
        for rel in dict.fromkeys(self.created+self.updated+self.unchanged):
            if not rel.startswith('force-app/main/default/'):continue
            tail=rel[len('force-app/main/default/'):]
            result=self.member_for(tail)
            if result:
                typ,member=result;components.setdefault(typ,set()).add(member)
        pack=ET.Element(NS+'Package')
        for typ,members in sorted(components.items()):
            ts=ET.SubElement(pack,NS+'types')
            for member in sorted(members):ET.SubElement(ts,NS+'members').text=member
            ET.SubElement(ts,NS+'name').text=typ
        ET.SubElement(pack,NS+'version').text='61.0'
        self.manifest=self.run/'campus_patch.xml';self.manifest.write_bytes(xml_string(pack))
        self.count=sum(map(len,components.values()))
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
            print('No resolved metadata members; refusing empty validation manifest.')
            return False
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
a+Ne5tXD+vfZz+pKMLzrgjVKZrrvLEHJcWleNTmHX5wnL0Odnn1UVCvf8ovZ7AefXfKWstQyy0owhlLlUmHp/rhEMYsb69Ub8pPoyHoIJZFOWUMUpS3kNW2zWLTSWDAJpI0k9Q4ivZiUKZKuYUWWVIbcENC2RMtI
cOtdLnJ1ER1FGGpKKprQVxG3sg1dgsWGXE6gDnzQx/mhkU7bIoX8Yxbqjwb9k1k1/SEJbI/n1fLptfSz3gUSQxvIJ9FDTqnRA2Iv9nize9wPO6QcwdLFF4UZmnRdjNuQyLEj5OO1yPcW/ZVPZA8Ww7heWOVOl8lh
LPZOZegDRdnPm8aVXfc2Ip9Aptj3FPx36MOmJ8SPb2AiNiU+QAwTqS6avFse9rVw+/e6amQcrEzITziYitwyaorivIDjhSH/9B0E+w9QSwMEFAAAAAgAZ5xIXUfsWKmQAQAAWgMAAE8AAABkdXBsaWNhdGVSdWxl
cy9Db250YWN0Lldhcm5fRHVwbGljYXRlX1N0dWRlbnRfTmFtZV9QaG9uZS5kdXBsaWNhdGVSdWxlLW1ldGEueG1sjVPBjtMwEL37K0a5E5cVQgi5Xi3LIiEBRW1XHCvXGYhRYlv2JG3/nsluGkoJEhfLnvfmPc+M
rW6PbQM9puyCXxYvy0UB6G2onP+xLB63H168KW61UO+72DhrCNddg8A5Pi+Lmii+lTIHE8v8PSSLpQ2tvFksXsvFK9kimcqQKbQQylhih5X/6DMm0ndNEw5KXkUn1mPkRLxmjVFlGiZv8cgycB88MQ4HRzVQjZBN
i+CHxfgKYh08Ah5dplzCGnuHB9gjX3Zg9lxlyfqTnlAVZptcHAz1vWljl+GhR08Z7OhUnVsBNTs0LKHkZZaqLnv12ZCth03Wqj3vN6v9T7S0PUXUYwFKzqLPOewxAPpJbPfutPvC9e2+DrWNeWcGX+Uf7kK5fMeN
7FFT6jhvOrJHJkyfzB4b/c0kD9O0YUNdxdXDYAiT4W+6UCFiMkPh+WK4vCo5g8yx1xjD/9CnN/GX+PldzMTmxEdIqIy2S45Oq+fBPfinN7ypTRrbmZW84qjMcqtUYdI3DE4HoeQfX0SLX1BLAwQUAAAACABnnEhd
I/59isQAAABfAQAASQAAAGVtYWlsL0NhbXB1c19FdmVudF9FbWFpbHMvRXZlbnRfUmVnaXN0cmF0aW9uX0NvbmZpcm1hdGlvbl9MaWdodG5pbmcuZW1haWyFkMEKwjAQRO9+RT5AmruEgqigFw+tCp5CbLZ1IU3K
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
mFWfc0H3hBnkBAdGn5zmohjXasa1mrXX1pG8FP/eqdnYw5FDeVSZf/MBeb12BfL2M1X9AFBLAQIUAxQAAAAIAGecSF08YavioQIAALwGAAAlAAAAAAAAAAAAAACkgQAAAABjbGFzc2VzL0NhbXB1c0V2ZW50UmVn
aXN0ZXJBY3Rpb24uY2xzUEsBAhQDFAAAAAgAZ5xIXVUVpEKFAAAApQAAAC4AAAAAAAAAAAAAAKSB5AIAAGNsYXNzZXMvQ2FtcHVzRXZlbnRSZWdpc3RlckFjdGlvbi5jbHMtbWV0YS54bWxQSwECFAMUAAAACABn
nEhdb9y4RNcBAACpAwAAKQAAAAAAAAAAAAAApIG1AwAAY2xhc3Nlcy9DYW1wdXNFdmVudFJlZ2lzdGVyQWN0aW9uVGVzdC5jbHNQSwECFAMUAAAACABnnEhdVRWkQoUAAAClAAAAMgAAAAAAAAAAAAAApIHTBQAA
Y2xhc3Nlcy9DYW1wdXNFdmVudFJlZ2lzdGVyQWN0aW9uVGVzdC5jbHMtbWV0YS54bWxQSwECFAMUAAAACABnnEhdQk1bWLMBAADZAwAAJAAAAAAAAAAAAAAApIGoBgAAY2xhc3Nlcy9DYW1wdXNTb2NpZXR5U3Rh
dHNBY3Rpb24uY2xzUEsBAhQDFAAAAAgAZ5xIXVUVpEKFAAAApQAAAC0AAAAAAAAAAAAAAKSBnQgAAGNsYXNzZXMvQ2FtcHVzU29jaWV0eVN0YXRzQWN0aW9uLmNscy1tZXRhLnhtbFBLAQIUAxQAAAAIAGecSF2+
2u9S+gEAAEEEAAAmAAAAAAAAAAAAAACkgW0JAABjbGFzc2VzL0NhbXB1c1ZlbnVlRW1lcmdlbmN5QWN0aW9uLmNsc1BLAQIUAxQAAAAIAGecSF1VFaRChQAAAKUAAAAvAAAAAAAAAAAAAACkgasLAABjbGFzc2Vz
L0NhbXB1c1ZlbnVlRW1lcmdlbmN5QWN0aW9uLmNscy1tZXRhLnhtbFBLAQIUAxQAAAAIAGecSF35FcuEegIAALMJAABFAAAAAAAAAAAAAACkgX0MAABkYXNoYm9hcmRzL0NhbXB1c19FdmVudHMvU3R1ZGVudF9B
ZmZhaXJzX0Rhc2hib2FyZC5kYXNoYm9hcmQtbWV0YS54bWxQSwECFAMUAAAACABnnEhdxZr9ru8DAAA/BwAAIQAAAAAAAAAAAAAApIFaDwAAZG9jcy9DQU1QVVNfU0lOR0xFX1BBVENIX05PVEVTLm1kUEsBAhQD
FAAAAAgAZ5xIXeqT7UTEBQAAxgsAACcAAAAAAAAAAAAAAKSBiBMAAGRvY3MvY2FtcHVzLWV2ZW50cy1hc3NpZ25tZW50LXJlcG9ydC5tZFBLAQIUAxQAAAAIAGecSF0K8XH8gwEAAEYDAABLAAAAAAAAAAAAAACk
gZEZAABkdXBsaWNhdGVSdWxlcy9Db250YWN0LkJsb2NrX0R1cGxpY2F0ZV9TdHVkZW50X0VtYWlsLmR1cGxpY2F0ZVJ1bGUtbWV0YS54bWxQSwECFAMUAAAACABnnEhdR+xYqZABAABaAwAATwAAAAAAAAAAAAAA
pIF9GwAAZHVwbGljYXRlUnVsZXMvQ29udGFjdC5XYXJuX0R1cGxpY2F0ZV9TdHVkZW50X05hbWVfUGhvbmUuZHVwbGljYXRlUnVsZS1tZXRhLnhtbFBLAQIUAxQAAAAIAGecSF0j/n2KxAAAAF8BAABJAAAAAAAA
AAAAAACkgXodAABlbWFpbC9DYW1wdXNfRXZlbnRfRW1haWxzL0V2ZW50X1JlZ2lzdHJhdGlvbl9Db25maXJtYXRpb25fTGlnaHRuaW5nLmVtYWlsUEsBAhQDFAAAAAgAZ5xIXQev2AgeAQAA6QEAAFIAAAAAAAAA
AAAAAKSBpR4AAGVtYWlsL0NhbXB1c19FdmVudF9FbWFpbHMvRXZlbnRfUmVnaXN0cmF0aW9uX0NvbmZpcm1hdGlvbl9MaWdodG5pbmcuZW1haWwtbWV0YS54bWxQSwECFAMUAAAACABnnEhd6p9dv4MAAAClAAAA
LgAAAAAAAAAAAAAApIEzIAAAZW1haWwvQ2FtcHVzX0V2ZW50X0VtYWlscy5lbWFpbEZvbGRlci1tZXRhLnhtbFBLAQIUAxQAAAAIAGecSF2Hdv2ZkwEAANMEAAA2AAAAAAAAAAAAAACkgQIhAABmbGV4aXBhZ2Vz
L0NhbXB1c19FdmVudF9SZWNvcmRfUGFnZS5mbGV4aXBhZ2UtbWV0YS54bWxQSwECFAMUAAAACABnnEhd3FDh+xoBAAAeAgAAMAAAAAAAAAAAAAAApIHpIgAAZmxleGlwYWdlcy9DYW1wdXNfRXZlbnRzX0hvbWUu
ZmxleGlwYWdlLW1ldGEueG1sUEsBAhQDFAAAAAgAZ5xIXePutPqzAQAAWQgAAD0AAAAAAAAAAAAAAKSBUSQAAGZsZXhpcGFnZXMvQ2FtcHVzX0V2ZW50c19Xb3Jrc3BhY2VfVXRpbGl0eS5mbGV4aXBhZ2UtbWV0
YS54bWxQSwECFAMUAAAACABnnEhdluzGJrYBAABgCAAAOwAAAAAAAAAAAAAApIFfJgAAZmxleGlwYWdlcy9GaXRuZXNzX0h1Yl9Xb3Jrc3BhY2VfVXRpbGl0eS5mbGV4aXBhZ2UtbWV0YS54bWxQSwECFAMUAAAA
CABnnEhdXBD3aU4CAACUBgAAKwAAAAAAAAAAAAAApIFuKAAAZmxvd3MvQ2FsY3VsYXRlX1NvY2lldHlfU3RhdHMuZmxvdy1tZXRhLnhtbFBLAQIUAxQAAAAIAGecSF2XJUmsHQQAAHEOAAAmAAAAAAAAAAAAAACk
gQUrAABmbG93cy9EYWlseV9FdmVudF9DbG9zZXIuZmxvdy1tZXRhLnhtbFBLAQIUAxQAAAAIAGecSF1t03t84QYAAPwdAAAsAAAAAAAAAAAAAACkgWYvAABmbG93cy9RdWlja19FdmVudF9SZWdpc3RyYXRpb24u
Zmxvdy1tZXRhLnhtbFBLAQIUAxQAAAAIAGecSF1UGRdOvwMAAJELAAArAAAAAAAAAAAAAACkgZE2AABmbG93cy9SZWdpc3RyYXRpb25fQWZ0ZXJfU2F2ZS5mbG93LW1ldGEueG1sUEsBAhQDFAAAAAgAZ5xIXUMZ
Bm1pAgAAPQYAACwAAAAAAAAAAAAAAKSBmToAAGZsb3dzL1JlZ2lzdHJhdGlvbl9CZWZvcmVfU2F2ZS5mbG93LW1ldGEueG1sUEsBAhQDFAAAAAgAZ5xIXWAKKG41AgAA2AQAACsAAAAAAAAAAAAAAKSBTD0AAGZs
b3dzL1ZlbnVlX0VtZXJnZW5jeV9IYW5kbGVyLmZsb3ctbWV0YS54bWxQSwECFAMUAAAACABnnEhdfYM1cPcBAAAkCQAANgAAAAAAAAAAAAAApIHKPwAAbGF5b3V0cy9FdmVudF9fYy1BY2FkZW1pYyBFdmVudCBM
YXlvdXQubGF5b3V0LW1ldGEueG1sUEsBAhQDFAAAAAgAZ5xIXX2DNXD3AQAAJAkAAC0AAAAAAAAAAAAAAKSBFUIAAGxheW91dHMvRXZlbnRfX2MtRXZlbnQgTGF5b3V0LmxheW91dC1tZXRhLnhtbFBLAQIUAxQA
AAAIAGecSF19gzVw9wEAACQJAAA6AAAAAAAAAAAAAACkgVdEAABsYXlvdXRzL0V2ZW50X19jLVJlY3JlYXRpb25hbCBFdmVudCBMYXlvdXQubGF5b3V0LW1ldGEueG1sUEsBAhQDFAAAAAgAZ5xIXSsKrWtMAAAA
UAAAACkAAAAAAAAAAAAAAKSBpkYAAGx3Yy9jYW1wdXNFdmVudHNIb21lL2NhbXB1c0V2ZW50c0hvbWUuY3NzUEsBAhQDFAAAAAgAZ5xIXUu8pmw/AgAAIgUAACoAAAAAAAAAAAAAAKSBOUcAAGx3Yy9jYW1wdXNF
dmVudHNIb21lL2NhbXB1c0V2ZW50c0hvbWUuaHRtbFBLAQIUAxQAAAAIAGecSF12hRxWlgEAAHgDAAAoAAAAAAAAAAAAAACkgcBJAABsd2MvY2FtcHVzRXZlbnRzSG9tZS9jYW1wdXNFdmVudHNIb21lLmpzUEsB
AhQDFAAAAAgAZ5xIXaX5207OAAAAUAEAADEAAAAAAAAAAAAAAKSBnEsAAGx3Yy9jYW1wdXNFdmVudHNIb21lL2NhbXB1c0V2ZW50c0hvbWUuanMtbWV0YS54bWxQSwECFAMUAAAACABnnEhdjZZ++WsAAACBAAAA
KwAAAAAAAAAAAAAApIG5TAAAbHdjL3dvcmtzcGFjZVN3aXRjaGVyL3dvcmtzcGFjZVN3aXRjaGVyLmNzc1BLAQIUAxQAAAAIAGecSF2Kd7vBlgEAAHcDAAAsAAAAAAAAAAAAAACkgW1NAABsd2Mvd29ya3NwYWNl
U3dpdGNoZXIvd29ya3NwYWNlU3dpdGNoZXIuaHRtbFBLAQIUAxQAAAAIAGecSF3xq55HjgEAAM8CAAAqAAAAAAAAAAAAAACkgU1PAABsd2Mvd29ya3NwYWNlU3dpdGNoZXIvd29ya3NwYWNlU3dpdGNoZXIuanNQ
SwECFAMUAAAACABnnEhdRqC4+5IBAABtAwAAMwAAAAAAAAAAAAAApIEjUQAAbHdjL3dvcmtzcGFjZVN3aXRjaGVyL3dvcmtzcGFjZVN3aXRjaGVyLmpzLW1ldGEueG1sUEsBAhQDFAAAAAgAZ5xIXfNiRCgcAQAA
EAQAACsAAAAAAAAAAAAAAKSBBlMAAG1hdGNoaW5nUnVsZXMvQ29udGFjdC5tYXRjaGluZ1J1bGUtbWV0YS54bWxQSwECFAMUAAAACABnnEhdKWR0Jg4BAAC1AQAAOgAAAAAAAAAAAAAApIFrVAAAb2JqZWN0cy9F
dmVudF9fYy9maWVsZHMvU29jaWV0eV9DYXRlZ29yeV9fYy5maWVsZC1tZXRhLnhtbFBLAQIUAxQAAAAIAGecSF0jVV8ASQEAABcCAABdAAAAAAAAAAAAAACkgdFVAABvYmplY3RzL1JlZ2lzdHJhdGlvbl9fYy92
YWxpZGF0aW9uUnVsZXMvTm9fT3ZlcmJvb2tlZF9Pcl9DbG9zZWRfRXZlbnQudmFsaWRhdGlvblJ1bGUtbWV0YS54bWxQSwECFAMUAAAACABnnEhdeUU21xUCAACCEAAAOQAAAAAAAAAAAAAApIGVVwAAcmVwb3J0
VHlwZXMvRXZlbnRzX3dpdGhfUmVnaXN0cmF0aW9ucy5yZXBvcnRUeXBlLW1ldGEueG1sUEsBAhQDFAAAAAgAZ5xIXZe4F4mQAQAAPwMAADsAAAAAAAAAAAAAAKSBAVoAAHJlcG9ydHMvQ2FtcHVzX0V2ZW50cy9F
dmVudF9BdHRlbmRhbmNlX1JhdGUucmVwb3J0LW1ldGEueG1sUEsBAhQDFAAAAAgAZ5xIXZBrIT2bKQAAWoIAACQAAAAAAAAAAAAAAKSB6lsAAHRvb2xzL2NhbXB1c19ldmVudHNfYXVkaXRfd2l0aF91aS5weVBL
AQIUAxQAAAAIAGecSF0XUwDyJAEAAOYBAAArAAAAAAAAAAAAAACkgceFAAB3b3JrZmxvd3MvUmVnaXN0cmF0aW9uX19jLndvcmtmbG93LW1ldGEueG1sUEsFBgAAAAAsACwAixAAADSHAAAAAA==
"""
if __name__=='__main__':sys.exit(main())
