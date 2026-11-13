"""Fresh original-Liberty area account of accepted dynamic components.

These are LC-owned standard-cell services, not arbitrary new hardmacro
boundaries. Mapping is a resource measurement, not a300MHz/P&R certificate.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
LIB=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
LIB_SHA='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
YOSYS=Path('/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys')
NAMES=['dynamic_s32_merge','dynamic_s32_packer','dynamic_s32_weight_source']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main(args):
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=10
    assert sha(LIB)==LIB_SHA
    assert str(args.proof).startswith('/public/home/yuzelu/project-circuit/issue250-dynamic-')
    expected={path:digest for line in (args.proof/'source.sha256').read_text().splitlines()
              for digest,path in [line.split('  ',1)]}
    required=['dynamic_s32_packer'] if args.top=='dynamic_s32_weight_source' else []
    names=[args.top]+required
    for seed in range(25001,25007):
        report=json.loads((args.proof/f'rtl-{seed}/result.json').read_text())
        assert report['passed'] and report['local_source_records']==30
        for initial in range(3):
            assert 'held_cancel=1 quarantine=1' in (args.proof/f'rtl-{seed}/weight-source-{initial}.log').read_text()
    args.out.mkdir(exist_ok=False,parents=True)
    paths=[ROOT/'project/rtl/w8a16_v1'/f'{n}.sv' for n in names]
    for path in paths:
        rel='source/'+path.relative_to(ROOT).as_posix();assert sha(path)==expected[rel]
    wrapper=Path(__file__).with_name('abc_batch.py');wrapper.chmod(0o755)
    script=f'read_liberty -lib {LIB}\nread_verilog -sv '+ ' '.join(str(p) for p in paths)+'\n'
    script+=f'hierarchy -check -top {args.top}\nsynth -top {args.top} -noabc\n'
    script+=f'dfflibmap -liberty {LIB}\nabc -exe {wrapper} -liberty {LIB}\nflatten -noscopeinfo\n'
    script+=f'clean\ncheck -assert\nstat -liberty {LIB}\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n'
    (args.out/'map.ys').write_text(script)
    receipt=dict(passed=False,top=args.top,source_sha256={p.name:sha(p) for p in paths},
                 liberty_sha256=sha(LIB),proof_source_commit=(args.proof/'source-commit.txt').read_text().strip(),
                 affinity=sorted(os.sched_getaffinity(0)),physical_qualified=False,added_sram_bytes=0)
    try:
        with (args.out/'map.log').open('w') as log:
            proc=subprocess.run([str(YOSYS),'-s',str(args.out/'map.ys')],cwd=args.out,stdin=subprocess.DEVNULL,
                                env=dict(os.environ,ISSUE250_ABC_TRANSPORT_DIR=str(args.out)),stdout=log,stderr=subprocess.STDOUT)
        assert proc.returncode==0
        assert json.loads((args.out/'abc-mapping.json').read_text())['passed']
        # Yosys may reuse the merged SCL generated from the same frozen
        # Liberty in this container. Preserve the actual consumed SCL bytes
        # and hash rather than pretending every mapping invokes read_lib.
        generated=(args.out/'abc-generated.script').read_text()
        scl=Path(re.search(r'\bread_scl\s+([^;\s]+)',generated).group(1).strip('"'))
        assert scl.is_file()
        (args.out/'consumed.scl').write_bytes(scl.read_bytes())
        conversion=args.out/'abc-liberty-conversion.json'
        assert conversion.exists() or 'using cached merged SCL:' in (args.out/'map.log').read_text()
        if conversion.exists():
            assert json.loads(conversion.read_text())['passed']
        receipt.update(consumed_scl_sha256=sha(scl),consumed_scl_path=str(scl),
                       liberty_conversion_invoked=conversion.exists())
        module=json.loads((args.out/'mapped.json').read_text())['modules'][args.top]
        cells=collections.Counter(v['type'] for v in module['cells'].values())
        assert not module.get('memories') and all(not n.startswith('$') for n in cells)
        text=LIB.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',text));areas={}
        for i,m in enumerate(starts):
            body=text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
            areas[m.group(1)]=float(re.search(r'\barea\s*:\s*([\d.eE+-]+)\s*;',body).group(1))
        receipt.update(passed=True,mapped_area_um2=sum(areas[n]*v for n,v in cells.items()),
                       cell_counts=dict(cells),mapped_dff_count=sum(v for n,v in cells.items() if n.startswith(('DFF','SDFF'))),
                       top_interface_bits=sum(len(v['bits']) for v in module['ports'].values()),
                       hierarchical_memories=module.get('memories',{}),
                       scope='Standalone LC service area, original Liberty. No P&R/300MHz/integrated-control qualification.')
    finally:
        (args.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--proof',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--top',choices=NAMES,required=True)
    main(p.parse_args())
