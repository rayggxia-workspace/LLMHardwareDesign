from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');record=b/'route-selection-102/sready494-supported-profile-transfer';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();old=b/'dynamic-04/node25/pending/00-e-sready490-bounded-search-profile.json';state=json.loads((old.parent.parent/'queue-state.json').read_text());assert old.stem not in state['active']and old.is_file();spec=json.loads(old.read_text());assert spec['script']=='system_upper.py'and spec['source_root']==str(b/'source-489');oldsha=sha(old);record.mkdir()
spec['args'][spec['args'].index('--out')+1]=str(b/'r256-search-phase-profile-494');p=b/'dynamic-02/node6/pending/00-f-sready494-supported-search-profile.json';assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p)
assert sha(old)==oldsha;old.rename(record/'withdrawn-unstarted-490-spec.json')
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=[dict(path=str(p),sha256=sha(p),spec=spec)],withdrawn_unstarted=dict(path=str(old),sha256=oldsha,retained=str(record/'withdrawn-unstarted-490-spec.json')),whole_system_qualified=False,scope='Transfer never-started owned490 diagnostic spec to node6 after exact active-state/hash check; preserve original byte-identical spec. Replace only obsolete235instance no-R own2090 step after independent UID/job/cmd/graph guards; all current345instance searches and foreign/R tasks remain untouched. Bounded diagnostic not physical qualification; no scheduler whitelist or original search source change.'),indent=2));print('queued494;490unstarted spec retained')
'''
compile(q,'queue494','exec');Path(__file__).with_name('control162-queue494-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
