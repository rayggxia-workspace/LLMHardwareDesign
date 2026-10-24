import hashlib,json,re,subprocess
from pathlib import Path
from urllib.parse import urlparse
root=Path('D:/Projects/LLMHardwareDesign-scale-state');work=root/'work/Liangruizhi/66'
def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
origin=git('config','--get','remote.origin.url');u=urlparse(origin)
if u.hostname!='github.com'or u.password or u.username not in(None,'Liangruizhi')or u.path.strip('/')not in('rayggxia-workspace/LLMHardwareDesign','rayggxia-workspace/LLMHardwareDesign.git'):raise ValueError('wrong target/auth URL')
if git('branch','--show-current')!='task/66-scale-state':raise ValueError('branch')
if git('rev-parse','origin/task/64-block-v2')!='ec3008c665709fa3126d55719ad084d33af44428':raise ValueError('stacked base changed')
base='ec3008c665709fa3126d55719ad084d33af44428'
files=sorted(set(git('diff','--name-only',base).splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))
fixed={'AGENTS.md','README.md','docs/ARCHITECTURE.md','docs/BLOCK_MINIMAL_EXPERIMENTS_V1.md','docs/BLOCK_PARTITION_V2.md','docs/STATUS.md','docs/experiments/issue-66-scale-state.md','docs/decisions/2026-10-24-consumer-scale-and-integer-state.md','docs/handoffs/2026-10-24-issue-66-scale-state.md','progress/Liangruizhi/STATUS.md'}
records=[];rx=re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|hf_[A-Za-z0-9]{30,}')
for name in files:
 if name not in fixed and not name.startswith(('project/experiments/scale_state/','work/Liangruizhi/66/')):raise ValueError('outside scope '+name)
 p=root/name
 if not p.is_file():raise ValueError('unexpected deletion '+name)
 if p.stat().st_size>25<<20:raise ValueError('large unapproved repository file '+name)
 data=p.read_bytes()
 if p.suffix!='.zip' and rx.search(data):raise ValueError('credential pattern '+name)
 if name!='work/Liangruizhi/66/preflight.json':records.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
# Current normative Python modules must match their actual runtime binding, not document HEAD.
for phase in ['phase3','phase4','phase8','phase9','phase10','phase11','phase13','phase14','phase15']:
 b=json.loads((work/(phase+'-binding.json')).read_text())
 for name,digest in b['sources'].items():
  if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:raise ValueError('runtime source changed '+name)
result={'status':'PASS','checked_origin':'https://github.com/rayggxia-workspace/LLMHardwareDesign.git','branch':git('branch','--show-current'),'base_commit':base,'files':records,'excluded_self':'work/Liangruizhi/66/preflight.json', 'scope':'allowlisted full PR scope, source/runtime SHA, exact target and basic secret patterns; self receipt excluded from its own inventory; not review or security certification'}
(work/'preflight.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({'status':'PASS','files':len(records),'bytes':sum(x['bytes']for x in records)}))
