"""Make display labels unique, retaining every numerical ID and body byte.

The tile reader uses numeric IDs and discards these labels, so an existing
tile partition remains valid when its source body hash matches this receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from lower_relabel import read_header,make_header,sha

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene',type=Path,required=True);a=p.parse_args()
    out=Path(os.environ['LOWER_OUT']);out.mkdir();meta=json.loads((a.scene/'scene.json').read_text());files={};bodies={};fixed=0
    for filename in ['with-upper.bin','without-upper.bin']:
        source=a.scene/filename;whole=hashlib.sha256();body=hashlib.sha256();result=hashlib.sha256()
        with source.open('rb') as f,(out/filename).open('xb') as target:
            names,flags,count,eps,header=read_header(f);whole.update(header)
            new=['LOWER_ID_'+str(i) if i>=2502 else name for i,name in enumerate(names)]
            assert len(new)==len(set(new));fixed=max(fixed,len(names)-len(set(names)))
            h=make_header(new,flags,count,eps);target.write(h);result.update(h)
            for b in iter(lambda:f.read(8<<20),b''):whole.update(b);body.update(b);target.write(b);result.update(b)
        assert whole.hexdigest()==meta['files'][filename]['sha256']
        files[filename]=dict(sha256=result.hexdigest(),bytes=(out/filename).stat().st_size);bodies[filename]=body.hexdigest()
    targets=json.loads((a.scene/'targets.json').read_text())
    for t in targets:t['name']='LOWER_ID_'+str(t['id'])
    (out/'targets.json').write_text(json.dumps(targets,indent=2)+'\n')
    (out/'masters.txt').write_text('\n'.join(map(str,meta['master_ids']))+'\n')
    meta.update(files=files,targets_sha256=sha(out/'targets.json'),header_repair_source=str(a.scene),header_repair_source_metadata_sha256=sha(a.scene/'scene.json'),
        duplicate_display_labels_repaired=fixed,numerical_ids_and_all_body_bytes_unchanged=True,body_sha256=bodies)
    (out/'scene.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(dict(duplicate_display_labels_repaired=fixed,body_sha256=bodies,files=files)),flush=True)

if __name__=='__main__':main()
