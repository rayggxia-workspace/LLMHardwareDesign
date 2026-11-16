"""Submit one immutable, same-pool greedy-backbone ablation and diagnosis.

The 196 production modules must byte-match the already launched phase review.
Only the two named auxiliary files are added. Existing jobs are never touched.
"""
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile


def main():
    own=Path(__file__).resolve().parent;root=own.parents[3]
    cache=Path.home()/'AppData/Local/Codex';host='yuzelu@10.129.166.172'
    prior=json.loads((cache/'algorithm-fix-277-phased-tile-full.json').read_text())
    name='algorithm-fix-279-phase-greedy-backbone';directory=str(Path(prior['directory']).parent/name).replace('\\','/')
    files={}
    for file,expected in prior['source_sha256'].items():
        data=(root/'project/experiments/block_synthesis'/file).read_bytes().replace(b'\r\n',b'\n')
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('production snapshot changed '+file)
        files[file]=data
    for file in ('phase-backbone-review.sbatch','diagnose_tile_barriers.py'):
        if file in files:raise ValueError('auxiliary name collides with production source')
        files[file]=(own/file).read_bytes().replace(b'\r\n',b'\n')
    archive=cache/(name+'.tar')
    with tarfile.open(archive,'w') as tar:
        for file,data in sorted(files.items()):
            info=tarfile.TarInfo(file);info.size=len(data);info.mtime=0;tar.addfile(info,io.BytesIO(data))
    subprocess.run(['ssh',host,'mkdir '+shlex.quote(directory)],check=True,timeout=30)
    subprocess.run(['scp','-q',str(archive),host+':'+directory+'/source.tar'],check=True,timeout=60)
    subprocess.run(['ssh',host,'tar -xf '+shlex.quote(directory+'/source.tar')+' -C '+shlex.quote(directory)],check=True,timeout=30)
    inputs=[prior['directory']+'/generated/ir.json',prior['directory']+'/generated/greedy.json','18']
    cmd=['sbatch','--parsable','--output='+directory+'/slurm.log',directory+'/phase-backbone-review.sbatch',directory,*inputs]
    job=subprocess.check_output(['ssh',host,shlex.join(cmd)],timeout=30).decode().strip()
    receipt={'directory':directory,'job':job,'source_sha256':{f:hashlib.sha256(d).hexdigest() for f,d in files.items()},
        'production_snapshot':prior['directory'],'production_modules':len(prior['source_sha256']),
        'auxiliary_files':['phase-backbone-review.sbatch','diagnose_tile_barriers.py'],
        'scope':'same common pool and width8; strongest new greedy seed; diagnostics are not executable gains'}
    (cache/(name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
    print(json.dumps({'job':job,'directory':directory,'production_modules':receipt['production_modules']}))


if __name__=='__main__':main()
