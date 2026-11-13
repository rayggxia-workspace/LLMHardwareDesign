"""Restore indexed duplicate files and exact IR overlays in an extracted pack.

Only writes missing files inside the supplied extraction root. Never deletes
or overwrites an existing file; every reconstructed byte is SHA-checked.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil


def main():
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('extracted',type=Path)
    p.add_argument('round18_ir',type=Path);a=p.parse_args();m=json.loads(a.manifest.read_text());root=a.extracted.resolve()
    def dest(name):
        value=(root/name).resolve()
        if not value.is_relative_to(root):raise ValueError('evidence path escapes extraction root')
        return value
    def check(file,sha):
        if hashlib.sha256(file.read_bytes()).hexdigest()!=sha:raise ValueError('evidence differs: '+str(file))
    for name,original in m['aliases'].items():
        source=dest(original);target=dest(name);expected=m['restored_members'][name]['sha256']
        check(source,expected)
        if target.exists():check(target,expected);continue
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);check(target,expected)
    for overlay in m['ir_overlays']:
        check(a.round18_ir,overlay['base_sha256']);base=json.loads(a.round18_ir.read_text())
        delta_file=a.manifest.parent/overlay['delta']
        delta=json.loads(gzip.decompress(delta_file.read_bytes()) if delta_file.suffix=='.gz' else delta_file.read_bytes())
        for key,value in delta.items():base[key]=value
        data=(json.dumps(base,separators=(',',':'))+'\n').encode()
        if hashlib.sha256(data).hexdigest()!=overlay['result_sha256']:raise ValueError('IR overlay differs')
        target=dest(overlay['target'])
        if target.exists():check(target,overlay['result_sha256']);continue
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print(json.dumps({'passed':True,'aliases':len(m['aliases']),'ir_overlays':len(m['ir_overlays'])}))


if __name__=='__main__':main()
