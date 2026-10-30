"""Verify eight-field records, source-native captures, links and exact figures.

This checks documentation/provenance only. It never asserts CAD qualification.
"""
from pathlib import Path
from html.parser import HTMLParser
import datetime,gzip,hashlib,json,re,sys,xml.etree.ElementTree as ET
from PIL import Image
from render import FIELDS
def check(out):
 out=Path(out).resolve();d=json.loads((out/'data/incidents.json').read_text(encoding='utf-8'))
 assert len(d['attempts'])==60 and not d['original_objective_complete'] and not d['deadline_met'] and d['PR_base_branch']=='main'
 ids=set();cad=0;local=0;observations=0
 for r in d['attempts']+d['remaining']:
  for key,label in FIELDS:assert r.get(key),(r.get('title'),key)
  assert r['remaining_estimate'] and r['analogy']
  for ev in r['evidence']:assert (out/ev['path']).is_file(),ev
 for r in d['attempts']:
  assert r['id'] not in ids;ids.add(r['id']);assert re.fullmatch('[0-9a-f]{64}',r['receipt_SHA256'])
  if r['time_kind'].startswith('流程'):observations+=1;assert r['driver_commit'].startswith('不适用')
  elif r['time_kind'].startswith('本地'):local+=1
  else:
   cad+=1
   path=next(out/e['path'] for e in r['evidence'] if '无损原生完整回执' in e['label']);raw=gzip.decompress(path.read_bytes());q=json.loads(raw)
   assert hashlib.sha256(raw).hexdigest()==r['receipt_SHA256']
   assert q.get('completed_utc') or q.get('finished_utc');assert not q.get('full_qualification',False)
   if q.get('driver_commit'):assert q['driver_commit']==r['driver_commit']
 assert (cad,local,observations)==(51,6,3)
 groups=0;nativefiles=0
 for cp in (out/'evidence').rglob('capture.json'):
  cap=json.loads(cp.read_text());assert cap['source_completed_utc'];groups+=1
  for rec in cap['records']:
   p=cp.parent/(rec['name']+'.gz');b=p.read_bytes();raw=gzip.decompress(b)
   assert hashlib.sha256(b).hexdigest()==rec['stored_sha256'] and hashlib.sha256(raw).hexdigest()==rec['sha256'];nativefiles+=1
 assert groups==51
 idx=json.loads((out/'data/evidence_manifest.json').read_text(encoding='utf-8'))
 for name,m in idx.items():
  p=out/name;assert p.is_file() and p.stat().st_size==m['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'],name
 class Links(HTMLParser):
  def __init__(self):super().__init__();self.refs=[];self.ids=[]
  def handle_starttag(self,tag,attrs):
   a=dict(attrs)
   if 'id' in a:self.ids.append(a['id'])
   for k in ['href','src']:
    if k in a:self.refs.append(a[k])
 h=Links();h.feed((out/'report.html').read_text(encoding='utf-8'));assert ids<=set(h.ids)
 for ref in h.refs:
  if ref.startswith('#'):assert ref[1:] in h.ids
  elif not ref.startswith(('https://','http://')):assert (out/ref.split('#')[0]).is_file(),ref
 md=(out/'README.md').read_text(encoding='utf-8')
 for id in ids:assert '<a id="'+id.lower()+'"></a>' in md
 with Image.open(out/'assets/llsys_actual_gap_residual6.png') as im:im.verify()
 ET.parse(out/'assets/llsys_actual_gap_residual6.svg')
 fig=json.loads((out/'data/llsys_actual_gap_residual6_figure.json').read_text());q=json.loads(gzip.decompress((out/'evidence/llsys100-gap-heal-r02/execution.json.gz').read_bytes()))
 assert fig['native_DRC_before_after']==[100,6] and q['fresh_DRC_count']==6 and fig['source_ODB_SHA256']==q['files']['routed.odb']['sha256']
 print('PASS_DOCUMENTATION_ONLY',len(ids),'eight-field records;',groups,'closed groups;',nativefiles,'raw native files;',len(idx),'artifact hashes; NOT hardware qualification')
if __name__=='__main__':check(sys.argv[1])
