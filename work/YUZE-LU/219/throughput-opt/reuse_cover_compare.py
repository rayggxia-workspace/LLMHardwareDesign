"""Same original pool and finite hardware: resident options with/without reuse."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from resident_cover_survey import run


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    a.output.mkdir(exist_ok=False);ir=json.loads(a.ir.read_text());timing=ir['resident_timing']
    source={k:v for k,v in ir.items() if not k.startswith('resident_')};del ir
    frozen=a.output/'source';frozen.mkdir();hashes={}
    for f in [Path(__file__),*Path('project/experiments/block_synthesis').glob('*.py')]:
        data=f.read_bytes();(frozen/f.name).write_bytes(data);hashes[f.as_posix()]=hashlib.sha256(data).hexdigest()
    (a.output/'source-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    # Serialization yields independent action pools without aliasing mutable
    # input dictionaries; all old tasks/capabilities are identical.
    raw=json.dumps(source,separators=(',',':'));(a.output/'original-ir.json').write_text(raw+'\n')
    reports={}
    for enabled in (False,True):
        name='conditional_reuse' if enabled else 'original_resident'
        reports[name]=run(json.loads(raw),timing,a.output/name,width=8,wire_budget=18,
                          continuation=True,value_reuse=enabled)
    result={'reports':reports,'input_sha256':hashlib.sha256(a.ir.read_bytes()).hexdigest(),
        'scope':'same finite nine-group hardware, unchanged original pool, maximal resident regions and charged cold/continuous choices; source-closed FFN only, not full model/system/energy/token/s'}
    (a.output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'phase':'comparison-complete','plans':{n:r['plans'] for n,r in reports.items()}}),flush=True)


if __name__=='__main__':main()
