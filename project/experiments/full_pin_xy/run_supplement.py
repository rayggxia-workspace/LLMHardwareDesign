from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,subprocess,gzip,hashlib
from run_exports import command,ROOT,sha

def one(item):
    c,s=item;assert sha(Path(s['odb']))==s['expected_sha256']
    with (ROOT/'logs'/f'{c}-supplement.log').open('x') as f:subprocess.run(command(c,s['odb'],'export_supplement.tcl'),stdout=f,stderr=subprocess.STDOUT,check=True)
    assert 'SUPPLEMENT_COMPLETE' in (ROOT/'logs'/f'{c}-supplement.log').read_text()
    for p in (ROOT/'supplement'/c).glob('*.tsv'):
        with p.open('rb') as src,p.with_suffix('.tsv.gz').open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as dst:
            for chunk in iter(lambda:src.read(4*1024*1024),b''):dst.write(chunk)
    print('SUPPLEMENT',c,flush=True)

if __name__=='__main__':
    cfg=json.loads((ROOT/'inputs/sources.json').read_text())
    with ThreadPoolExecutor(max_workers=2) as ex:list(ex.map(one,cfg['physical_blocks'].items()))
