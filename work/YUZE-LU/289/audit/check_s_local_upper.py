import pathlib,re,json,hashlib
root=pathlib.Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs')
old=pathlib.Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.def')
def upper(p):
 out=set();net=None;active=False
 for line in p.read_text().splitlines():
  if line.startswith('NETS '):active=True
  elif line.startswith('END NETS'):active=False
  if not active:continue
  m=re.match(r'\s*- (\S+)',line)
  if m:net=m[1]
  if re.search(r'\bmetal(?:9|10)\b|\bvia[89](?:_|\b)',line):out.add((net,line.strip()))
 return out
before=upper(old);results=[]
for mode in ['minimal','hold03','hold08']:
 path=root/f'candidate-S-{mode}-localv4/candidate.def';after=upper(path)
 added=sorted(after-before);removed=sorted(before-after)
 results.append(dict(mode=mode,before_count=len(before),after_count=len(after),identical=before==after,added=added,removed=removed,hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [old,path]}))
out=pathlib.Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/S-localv4-upper-route-diff.json');out.write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
