import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');now=time.time();seen=set()
for family in ['s-escape-gates-01','s-escape-gates-02']:
 root=b/family/'1350'
 for op in ['physical','drc','function','formal']:
  p=root/op
  if not p.exists():continue
  if family=='s-escape-gates-01'and op=='function'and(b/'route-selection-102/s1350-default-retire-after136/cancelled.json').exists():
   print('old default compilation retired after exact new function/formal passed');continue
  if p.resolve()in seen:continue
  seen.add(p.resolve())
  receipt=p/'receipt.json'
  if receipt.exists():print(family,op,'receipt',json.loads(receipt.read_text())['passed']);continue
  logs=sorted(p.glob('*.log'),key=lambda f:f.stat().st_mtime,reverse=True)
  if logs:
   f=logs[0]
   with f.open('rb')as stream:stream.seek(max(0,f.stat().st_size-110));tail=stream.read().decode(errors='replace')
   print(family,op,f.name,'age',round(now-f.stat().st_mtime),tail)
  obj=p/'obj'
  if obj.exists():print('compiled_objects',len(list(obj.glob('*.o'))),'cpp_units',len(list(obj.glob('*.cpp'))))
 for op in ['function','formal']:
  if family=='s-escape-gates-01'and op=='function':continue
  f=root/op/('physical-functional-proof.json'if op=='function'else'formal.json')
  if f.exists():
   d=json.loads(f.read_text());print(family,op,'proof',d.get('passed'))
   if op=='function':
    prior=json.loads((b/'s-internal-gates-01/1181/function/physical-functional-proof.json').read_text())
    print('same_full_logical_view_as_1181',d['full_view_sha256']==prior['full_view_sha256'])
for family,node in [('dynamic-05',2),('dynamic-05',4)]:
 f=b/family/('node'+str(node))/'queue-state.json'
 if f.exists():
  s=json.loads(f.read_text());print('node',node,'active',s['active'],'memory_rejections',[r for r in s['memory_admissions']if not r['admitted']][:2])
p=b/'s-escape-pg-compute-01/1350/wrapper';receipt=p/'receipt.json'
if receipt.exists():print('early_pg_computation',json.loads(receipt.read_text())['passed'])
elif p.exists():
 logs=sorted(p.glob('*.log'),key=lambda f:f.stat().st_mtime,reverse=True)
 if logs:
  f=logs[0]
  with f.open('rb')as stream:stream.seek(max(0,f.stat().st_size-140));print('early_pg_computation',f.name,'age',round(now-f.stat().st_mtime),stream.read().decode(errors='replace'))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
