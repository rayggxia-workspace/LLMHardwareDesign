"""Package the frozen model closure on its authorized source server.

Model bytes remain on the two authorized servers. A separate native scp -3
transfers each remote tar archive directly to BSCC; only metadata is printed.
"""
import argparse
import base64
from pathlib import Path
import shlex
import subprocess
from frozen_model_manifest import REMOTE


PACKAGE = r'''
import tarfile
dest=Path('/public/home/yuzelu/Melodydt/runs/issue-280/six-energy-transfer-01')
dest.mkdir(parents=True,exist_ok=True)
receipt=dict(model=model,baseline=stages,source_root=str(root),baseline_commit='fbff1bd0e455739f28d9b7dd00b97216fe7bb847',files=rows)
(dest/(model+'-transfer.json')).write_text(json.dumps(receipt,indent=2)+'\n')
archive=dest/(model+'.tar')
if not archive.exists():
    partial=dest/(model+'.tar.part')
    with tarfile.open(str(partial),'w') as tf:
        for row in rows:
            tf.add(row['source'],arcname=str(Path(row['source']).relative_to('/public/home/yuzelu')),recursive=False)
    partial.rename(archive)
h=hashlib.sha256()
with archive.open('rb') as f:
    for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
(dest/(model+'.tar.sha256')).write_text(h.hexdigest()+'  '+model+'.tar\n')
print(json.dumps(dict(model=model,files=len(rows),archive=str(archive),bytes=archive.stat().st_size,sha256=h.hexdigest())),flush=True)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('models',nargs='+',choices=('llama','granite','phi','gemma','qwen35','falcon'))
    a=p.parse_args()
    root=Path(__file__).resolve().parents[3]
    ssh=['ssh','-i','C:/Users/Administrator/.ssh/id_ed25519_server_ops_20261030',
         '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=15',
         '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(root/'tmp/energy-054-ddr-host.pub'),
         'yuzelu@10.129.166.172']
    body=REMOTE[:REMOTE.rindex('print(json.dumps(')] + PACKAGE
    script="import base64;exec(base64.b64decode({!r}))".format(base64.b64encode(body.encode()).decode())
    for model in a.models:
        subprocess.run(ssh+['python3 -c '+shlex.quote(script)+' '+model],check=True)


if __name__=='__main__':main()
