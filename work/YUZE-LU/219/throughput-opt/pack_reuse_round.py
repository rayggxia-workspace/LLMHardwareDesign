"""Package explicit task evidence without derived simulator binaries."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def main():
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);a=p.parse_args();root=a.runtime
    here=Path(__file__).resolve().parent;out=here/'results/resident-round18-v2';out.mkdir(exist_ok=False)
    files={}
    def add(f,name):
        if name in files:raise ValueError('duplicate evidence name')
        files[name]=f
    for sub in ('actual-boundaries-v1','actual-boundaries-v2','cover-compare-v1','reuse-rtl-v2'):
        for f in sorted((root/sub).rglob('*')):
            if f.is_file() and f.suffix not in ('.vvp','.pyc'):add(f,(Path(sub)/f.relative_to(root/sub)).as_posix())
    for f in sorted(root.glob('*.log')):add(f,'runtime/'+f.name)
    add(root/'independent-audit.json','runtime/independent-audit.json')
    add(root/'tail-fix-evidence.json','runtime/tail-fix-evidence.json')
    add(root/'tail-fix-evidence.py','runtime/tail-fix-evidence.py')
    add(root/'job-replacement.json','runtime/job-replacement.json')
    add(root/'final-source-match.json','runtime/final-source-match.json')
    add(root/'check_final_source.py','runtime/check_final_source.py')
    full=here/'results/resident-full-selected-terminal-r18'
    for f in sorted(full.rglob('*')):
        if f.is_file():add(f,(Path('old-full-selected-terminal')/f.relative_to(full)).as_posix())
    cancelled=here/'results/resident-reuse-cancelled-r18'
    for f in sorted(cancelled.rglob('*')):
        if f.is_file():add(f,(Path('cancelled-known-tail-bug')/f.relative_to(cancelled)).as_posix())
    launch=Path('D:/Data/电路实验/issue219-runtime-round15')
    for name in ('algorithm-fix-291-resident-reuse-full','algorithm-fix-292-resident-reuse-full-tailfix'):
        for suffix in ('.json','.tar'):
            f=launch/(name+suffix);add(f,'new-full-job/'+f.name)
    source=Path('project/experiments/block_synthesis')
    for f in sorted(source.iterdir()):
        if f.suffix in ('.py','.sv','.svh','.cpp','.hpp','.sbatch','.md'):add(f,'current-source/'+f.name)
    for name in ('reuse_boundaries.py','reuse_cover_compare.py','run_reuse_probe.py','audit_reuse_round.py','pack_reuse_round.py'):
        add(here/name,'drivers/'+name)
    entries={name:{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for name,f in files.items()}
    archive=out/'evidence.tar.gz'
    with archive.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        for name,f in files.items():
            info=tar.gettarinfo(str(f),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
            with f.open('rb') as data:tar.addfile(info,data)
    # Independently inspect member names and content, without extracting.
    with tarfile.open(archive,'r:gz') as tar:
        if set(tar.getnames())!=set(entries):raise ValueError('archive member coverage differs')
        for m in tar.getmembers():
            if not m.isfile() or m.name.startswith('/') or '..' in Path(m.name).parts:raise ValueError('unsafe evidence member')
            data=tar.extractfile(m).read();expected=entries[m.name]
            if len(data)!=expected['bytes'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:raise ValueError('archive SHA differs')
    audit=json.loads((root/'independent-audit.json').read_text());(out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    manifest={'kind':'issue219-resident-reuse-round18-evidence-v1','local_parent':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
        'archive':{'name':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},
        'members':entries,'passed_archive_sha256':True,
        'notes':['v1 boundary source and results precede the mandatory recompute bound; v2 is the revised result',
                 'reuse-rtl-v1 prepare failed for missing alias-commit negative coverage; raw prepare log retained; generator at that failure was not frozen',
                 'old full selected report is round15 cold resident pool, not the new conditional-reuse full-model result',
                 'new full job receipt/source is submission evidence only; terminal qualification remains pending']}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'archive':manifest['archive'],'members':len(entries)}))


if __name__=='__main__':main()
