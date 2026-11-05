from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');h=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-63';assert not out.exists()
code=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
required=['r256-directional-bidir-regression-635','r256-pattern-scale-regression-655','r256-default-scale-regression-671','r256-directional-bidirectional-active-pool-audit-650','r256-final-chain-binding-audit-651','r256-directional-bidir-source-invariance-652','r256-directional-bidirectional-active-pool-audit-674','r256-final-chain-binding-audit-675']
for name in required:
 assert json.loads((b/name/'receipt.json').read_text())['passed'];files+=list((b/name).rglob('*'))
for p in (b/'route-selection-102').iterdir():
 if any(p.name.startswith('sready'+str(n)+'-')for n in [635,637,640,643,644,655,657,658,671,673]):files+=list(p.rglob('*'))
for n in [633,653,668]:files += [b/('source-'+str(n))/'source-manifest.json',b/('source-'+str(n))/'freeze-import.json']
for p in b.iterdir():
 if any(p.name.endswith('-'+str(n))for n in [642,654,664]):files+=list(p.rglob('*'))
for folder,seeds in [('dynamic-03/node5',[6360]),('dynamic-02/node6',[6361,6720]),('dynamic-05/node2',[6560]),('dynamic-02/node3',[6561]),('dynamic-04/node25',[6562]),('dynamic-05/node4',[6563])]:
 for section in ['commands','pending']:
  for p in (b/folder/section).glob('*.json'):
   if any(p.stem.endswith('-'+str(seed))for seed in seeds):files.append(p)
files += [b/'r256-composition-453'/('acceptance-'+str(n)+'.json')for n in [6360,6361,6560,6561,6562,6563,6720]]
rows=[]
for p in sorted(set(files)):
 if not p.is_file():continue
 raw=p.read_bytes();copy=p.suffix in ['.json','.txt','.log','.cpp','.h']and len(raw)<2000000
 row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=copy)
 if copy:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
compile(code,'remote-proof676','exec')
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(code)],timeout=60));out.mkdir()
for row in d['rows']:
 if row['copied']:
  raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
d['helpers']=[]
numbers={630,631,633,635,637,640,642,643,644,645,647,650,651,652,654,655,657,658,662,664,668,671,673,674,675,676}
items={}
for p in h.glob('control162-*.py'):
 if any(p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote')for n in numbers):items['helpers/'+p.name]=p
for n in [634,659,670]:items['helpers/publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for directory in ['control162-watch660','control162-watch662']:
 fs=sorted((h/directory).glob('*.json'))
 for p in [fs[0],fs[-1]]:items['selected-running-snapshots/'+directory+'/'+p.name]=p
for p in h.glob('control162-online630-*.json'):items['online-readback/'+p.name]=p
for name,p in items.items():
 raw=p.read_bytes();t=out/name;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['metadata_failures']=dict(guard637='Source identity mismatch before cancellation; raw failure retained.',guard640='Stale fixed-pool assertion rejected actual dynamic64 before cancellation; full actual spec642 read and corrected643/644 guards used.',prepare674_shell='PowerShell parser rejected inline generator before execution; standalone prepare674 then completed. No remote task or receipt affected.',config675_preparation='Record name corrected locally to actual sready655-congestion-scale-controls before execution; successful audit675 executed once.')
d['scope']='Actual635 eighteen directional cases/six exact default replays and independent oracles; actual655 fifteen global-scale cases plus671 eighteen including0/default256;80 actual input/PID/memory checks674;35 final-chain immutable specs675; source633/653/668 manifests and retained failed identity guards followed by exact own-step reallocations. Selected runtime snapshots are not full waveform or convergence proof. No full physical route or system qualification inherited.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
