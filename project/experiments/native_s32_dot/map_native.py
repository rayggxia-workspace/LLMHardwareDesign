"""Map proven native32 variants with the original Nangate45 cells, on Slurm."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

LIB=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
LIB_SHA='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
DECK=LIB.parent.parent/'drc/FreePDK45.lydrc'
DECK_SHA='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
YOSYS=Path('/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys')
RTL=('project/rtl/native_s32_dot/dot_s32_core.sv','project/rtl/native_s32_dot/dot_s32_s128.sv')


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda:file.read(1<<20),b''):digest.update(chunk)
    return digest.hexdigest()


def main(args):
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))==10
    assert sha(LIB)==LIB_SHA and sha(DECK)==DECK_SHA
    known={name:digest for digest,name in (x.split('  ',1) for x in (args.proof/'source.sha256').read_text().splitlines())}
    assert all(sha(args.source/name)==known['source/'+name] for name in RTL)
    proven={}
    for seed in range(25201,25207):
        path=args.proof/f'seed-{seed}'/'result.json';result=json.loads(path.read_text())
        assert result['passed'] and result['real_s'] and result['seed']==seed
        assert {v['rows_capacity'] for v in result['variants']}=={1,2,4}
        proven[str(path)]=sha(path)
    args.out.mkdir(exist_ok=False,parents=True)
    cache=args.out/'cache';cache.mkdir();tmp=args.out/'tmp';tmp.mkdir()
    wrapper=Path(__file__).with_name('abc_batch.py');wrapper.chmod(0o755)
    assert sha(wrapper)=='bbf5c27e7370c18a12b2e9f6a9ef4ce20b3110a6c787b3f4c8eb60100765399e'
    files=' '.join(str(args.source/path) for path in RTL)
    script=(f'read_liberty -lib {LIB}\nread_verilog -sv {files}\n'
            f'hierarchy -check -top {args.top} -chparam ROWS {args.rows}\n'
            'proc\nopt\nwrite_json operators.json\n'
            f'flatten -noscopeinfo\nsynth -top {args.top} -noabc\ndfflibmap -liberty {LIB}\n'
            f'abc -exe {wrapper} -liberty {LIB}\nclean\ncheck -assert\n'
            f'stat -liberty {LIB}\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n')
    (args.out/'map.ys').write_text(script)
    receipt=dict(passed=False,top=args.top,rows=args.rows,physical_qualified=False,added_SRAM_B=0,
        source_commit=(args.source.parent/'source-commit.txt').read_text().strip(),
        rtl_sha256={name:sha(args.source/name) for name in RTL},rtl_proof_source_sha256=sha(args.proof/'source.sha256'),
        rtl_proof_receipts=proven,liberty_sha256=LIB_SHA,original_full_deck_sha256=DECK_SHA,
        yosys_sha256=sha(YOSYS),abc_batch_sha256=sha(wrapper),job=os.environ['SLURM_JOB_ID'],
        affinity=sorted(os.sched_getaffinity(0)),
        evidence_scope='Nangate45 original library mapping. Area includes all functional standard cells; placement, M10 pin access and 300MHz are unqualified.')
    try:
        env=dict(os.environ,ISSUE250_ABC_TRANSPORT_DIR=str(args.out),TMPDIR=str(tmp),XDG_CACHE_HOME=str(cache))
        with (args.out/'map.log').open('w') as log:
            subprocess.run([str(YOSYS),'-s',str(args.out/'map.ys')],cwd=args.out,env=env,check=True,
                           stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        module=json.loads((args.out/'mapped.json').read_text())['modules'][args.top]
        cells=Counter(c['type'] for c in module['cells'].values());assert not any(n.startswith('$') for n in cells)
        text=LIB.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',text));areas={}
        for i,match in enumerate(starts):
            body=text[match.end():starts[i+1].start() if i+1<len(starts) else len(text)]
            areas[match[1]]=float(re.search(r'\barea\s*:\s*([\d.eE+-]+)\s*;',body)[1])
        operators=json.loads((args.out/'operators.json').read_text())['modules'];op_counts=Counter()
        for name,record in operators.items():
            if name==args.top or 'dot_s32_core' in name:
                op_counts.update(c['type'] for c in record.get('cells',{}).values())
        dffs={name:count for name,count in cells.items() if name.startswith(('DFF','SDFF'))}
        ports={name:dict(direction=port['direction'],bits=len(port['bits'])) for name,port in module['ports'].items()}
        paths=('map.ys','mapped.v','mapped.json','operators.json','abc-liberty-conversion.json','abc-mapping.json','abc-generated.script')
        for item in ('abc-liberty-conversion.json','abc-mapping.json'):
            assert json.loads((args.out/item).read_text())['passed']
        receipt.update(passed=True,mapped_area_um2=sum(areas[name]*count for name,count in cells.items()),
            cells=dict(cells),cell_count=sum(cells.values()),logical_multiplier_lanes=args.rows*4,
            flop_count=sum(dffs.values()),flop_area_um2=sum(areas[name]*count for name,count in dffs.items()),
            port_bits=sum(p['bits'] for p in ports.values()),ports=ports,operators=dict(op_counts),
            artifacts={item:sha(args.out/item) for item in paths})
        print(json.dumps({k:receipt[k] for k in ('top','rows','mapped_area_um2','flop_count','port_bits')}))
    finally:(args.out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--proof',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--rows',type=int,choices=(1,2,4),required=True)
    p.add_argument('--top',choices=('dot_s32_core','dot_s32_s128'),required=True);main(p.parse_args())
