"""Download pinned official WikiText-2 raw splits and verify LFS file SHA256."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import requests

FILES = {
    'train': (6357543, 'e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7'),
    'test': (732610, '5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91'),
}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    cfg=json.loads(Path(__file__).with_name('protocol.json').read_text(encoding='utf-8'))
    a.out.mkdir(parents=True,exist_ok=True)
    def download(split):
        name=f'{cfg["configuration"]}/{split}-00000-of-00001.parquet'
        path=a.out/f'{split}.parquet'; size,digest=FILES[split]
        if not path.exists():
            tmp=path.with_suffix('.partial')
            with requests.get(f'https://huggingface.co/datasets/{cfg["dataset"]}/resolve/{cfg["revision"]}/{name}',stream=True,timeout=(30,90)) as r:
                r.raise_for_status()
                with tmp.open('wb') as f:
                    for block in r.iter_content(1<<20): f.write(block)
            tmp.replace(path)
        actual=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
        assert path.stat().st_size==size and actual==digest,split
        return split,{'source_file':name,'bytes':size,'sha256':actual}
    with ThreadPoolExecutor(max_workers=2) as pool: files=dict(pool.map(download,FILES))
    r=requests.get(f'https://huggingface.co/datasets/{cfg["dataset"]}/resolve/{cfg["revision"]}/README.md',timeout=60)
    r.raise_for_status(); (a.out/'README.md').write_bytes(r.content)
    (a.out/'manifest.json').write_text(json.dumps({'dataset':cfg['dataset'],'revision':cfg['revision'],'files':files},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(files))

if __name__=='__main__': main()
