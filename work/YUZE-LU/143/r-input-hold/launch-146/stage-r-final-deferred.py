import hashlib,io,json,subprocess,sys,tarfile
from pathlib import Path
seq=sys.argv[1];assert seq=='146'
runtime=Path(__file__).parent;host='yuzelu@10.129.166.172';base='/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030'
for job,source_seq in [(94507,'139'),(94509,'141')]:
 control=subprocess.check_output(['ssh',host,'scontrol show job '+str(job)+' -o'],text=True,timeout=60)
 fields=dict(v.split('=',1) for v in control.split() if '=' in v)
 assert fields['UserId']=='yuzelu(10011)' and fields['JobState'] in ('RUNNING','COMPLETED')
 assert fields['Command'].startswith(base+'/snapshots/'+source_seq+'/')
partition=subprocess.check_output(['ssh',host,'sinfo -p c96 -h -o "%N"'],text=True,timeout=60).strip()
assert partition=='node[13-26]',partition
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
roots=['project/rtl/block_v2','project/experiments/block_v2','work/YUZE-LU/143','project/experiments/block_v1','project/experiments/block_feed_v1','project/rtl/block_feed_v1','project/rtl/block_library_v1','project/rtl/block_v1']
data=subprocess.check_output(['git','-c','core.autocrlf=false','-c','core.eol=lf','archive','--format=tar',commit,*roots])
with tarfile.open(fileobj=io.BytesIO(data)) as t:files={v.name:t.extractfile(v).read() for v in t.getmembers() if v.isfile()}
objects={}
for line in subprocess.check_output(['git','ls-tree','-r',commit],text=True).splitlines():
 meta,name=line.split('\t',1);objects[name]=meta.split()[2]
for n,b in files.items():assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==objects[n]
m=dict(issue=143,commit=commit,native_producer='139',deferred_gates=True,scope='Queued final gates depend on94507/94509 actual completion and runtime receipt/native-zero recheck; no qualification yet',dependencies=[94507,94509],formal_computation='144',function_candidates=['145','143'],allowed_nodes=['node13','node14','node15','node16','node17','node18','node25','node26'],files={n:dict(sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)) for n,b in files.items()})
files['source-manifest.json']=(json.dumps(m,indent=2)+'\n').encode();archive=runtime/('source-'+seq+'.tar.gz');assert not archive.exists()
with tarfile.open(archive,'w:gz') as t:
 for n,b in files.items():
  member=tarfile.TarInfo(n);member.size=len(b);t.addfile(member,io.BytesIO(b))
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
s=f'''#!/bin/bash
set -euo pipefail
base={base}
root=$base/snapshots/{seq}
archive=/public/home/yuzelu/project-circuit/source-issue143-{seq}.tar.gz
test "$(sha256sum "$archive" | cut -d' ' -f1)" = {digest}
test ! -e "$root"
mkdir "$root"
tar -xzf "$archive" -C "$root"
python3 - "$root" <<'PY'
import hashlib,json,sys
from pathlib import Path
r=Path(sys.argv[1]);m=json.loads((r/'source-manifest.json').read_text())
for name,row in m['files'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==row['sha256']
print(json.dumps(dict(source_verified=True,commit=m['commit'])))
PY
bash -n "$root/project/experiments/block_v2/remote_r_deferred_gates.sh"
bash -n "$root/project/experiments/block_v2/remote_r_final_gates.sh"
sbatch --parsable --nodes=1 --dependency=afterok:94507:94509 --exclude=node[19-24] --output="$base/run{seq}-%j.out" --error="$base/run{seq}-%j.err" "$root/project/experiments/block_v2/remote_r_deferred_gates.sh" "$root" "$base/outputs/{seq}"
'''
stage=runtime/('stage-'+seq+'.sh');stage.write_bytes(s.encode())
print(json.dumps(dict(sequence=seq,commit=commit,archive_sha256=digest,files=len(m['files']))))
for path,name in ((archive,'source-issue143-'+seq+'.tar.gz'),(stage,'stage-issue143-'+seq+'.sh')):subprocess.run(['scp','-q',str(path),host+':/public/home/yuzelu/project-circuit/'+name],check=True,timeout=60)
subprocess.run(['ssh',host,'bash /public/home/yuzelu/project-circuit/stage-issue143-'+seq+'.sh'],check=True,timeout=60)
