from pathlib import Path
import subprocess,shlex,json,base64,hashlib,tarfile,re
q=r'''from pathlib import Path
import json,hashlib,base64,datetime
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');r=b/'block-v1-20261101-828';files={};large={}
for mode in ('final-source','drc'):
 p=r/'tasks'/('revision300-'+mode+'-r');receipt=json.loads((p/'receipt.json').read_text());assert receipt['passed'] or mode=='drc'
 for f in dict.fromkeys(list(p.iterdir())+[p/n for n in receipt['outputs']]):
  if not f.is_file():continue
  size=f.stat().st_size;h=hashlib.sha256()
  with f.open('rb')as stream:
   for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
  row=dict(bytes=size,sha256=h.hexdigest())
  name=str(f.relative_to(b))
  if size<3000000:row['base64']=base64.b64encode(f.read_bytes()).decode();files[name]=row
  else:large[name]=row
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,remote_large=large)))
'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]));dest=Path('work/YUZE-LU/121/review-20261028/r-828-drc-failure-850');assert not dest.exists();dest.mkdir()
for n,row in d['files'].items():
 raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=dest/n;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==raw,n
 else:p.write_bytes(raw)
with tarfile.open('.local/issue121/source827.tar')as tar:
 m=json.load(tar.extractfile('bundle-manifest.json'))
 for row in m['files']:assert tar.extractfile(row['path']).read()==subprocess.check_output(['git','cat-file','blob',row['git_blob']])
 for p in dest.glob('*/tasks/*/receipt.json'):
  receipt=json.loads(p.read_bytes());assert receipt['source_commit']==m['source_commit']
  for n,h in receipt['inputs'].items():
   if '/__pycache__/'not in n:assert hashlib.sha256(tar.extractfile(n).read()).hexdigest()==h,n
  for n,h in receipt['outputs'].items():
   path=(p.parent/n).relative_to(dest).as_posix();row=d['files'].get(path,d['remote_large'].get(path));assert row,(path,h)
   if row['sha256']!=h:
    assert n=='node-queue-child.log'and not receipt['passed'];d.setdefault('post_receipt_failure_log_append',{})[path]=dict(receipt_sha256=h,captured_sha256=row['sha256'])
p=dest/'block-v1-20261101-828/tasks';source=p/'revision300-final-source-r/receipt.json';source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
report=json.loads((p/'revision300-drc-r/five-macro-drc.json').read_bytes());dr=p/'revision300-drc-r';r=json.loads((dr/'receipt.json').read_bytes())
assert report['source_receipt_sha256']==source_hash and report['passed']==r['passed']
assert (dr/'native-whole-drc.rpt').read_text()==report['native_report']
import xml.etree.ElementTree as ET
xml=ET.parse(dr/'full-deck.lyrdb').getroot();counts=dict(categories=len(xml.findall('./categories/category')),items=len(xml.findall('./items/item')))
assert counts['items']==report['full_deck']['total_items']
assert report['deck_sha256']=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
if report['passed']:assert report['full_deck']['total_items']==0 and not report['native_report'].strip()
d.update(evidence_binding_passed=True,actual_drc_passed=report['passed'],source_commit=m['source_commit'],source_git_blobs_verified=len(m['files']),same_actual_final_source_receipt=True,native_records=report['native_report'].count('violation type:'),full_gds_report_counts=counts,full_deck=report['full_deck'],unmodified_deck_sha256=report['deck_sha256'],scope='Actual828 complete whole native DRC and complete unmodified FreePDK45 GDS deck terminal; all receipt inputs and actual stable outputs/source archive Git verified. Same source as838 physical/fresh whole signal geometry; no old404 qualification transfer. Does not by itself grant sixfile/fullview/interface acceptance.')
(dest/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(d['captured_utc'],len(d['files']),len(d['remote_large']),d['actual_drc_passed'],d['full_gds_report_counts'])
