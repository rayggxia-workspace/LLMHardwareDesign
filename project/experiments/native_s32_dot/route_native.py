"""Use the original main physical engine on a same-source native S32 map."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from map_native import LIB,LIB_SHA,DECK,DECK_SHA,sha

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/block_v2'))
from physical import implement
import pins
from native_pins import generate

TOP='dot_s32_s128'


def main(args):
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))==10
    assert sha(LIB)==LIB_SHA and sha(DECK)==DECK_SHA
    mapped=args.mapping/f'map-{TOP}-{args.rows}'
    source=json.loads((mapped/'result.json').read_text())
    assert source['passed'] and source['top']==TOP and source['rows']==args.rows
    for name,digest in source['rtl_sha256'].items():assert sha(ROOT/name)==digest
    artifacts={str(mapped/name):source['artifacts'][name] for name in ('mapped.json','mapped.v')}
    for name,digest in artifacts.items():assert sha(name)==digest
    area=source['mapped_area_um2'];signals=source['port_bits']
    # Conservative geometric precheck; the original independent pin fixture
    # still proves each rectangle/access shape. Do not inflate a leaf just
    # to make edge pins fit, or count filler as effective occupation.
    side=args.side or math.ceil(max(math.sqrt(area/.43),signals+60)/10)*10
    assert area/side**2>=.3518744201641808,('Below main M outline occupation',side,area,signals)
    assert area/(side-40)**2>=.3847459650503328,('Below main M core occupation',side,area)
    pins.generate=generate
    args.out.mkdir(parents=True,exist_ok=False)
    adapted=args.out/'mapping-adapter'/TOP;adapted.mkdir(parents=True)
    mapper=dict(passed=True,mapped=True,top=TOP,source_sha256=source['rtl_sha256'],
        liberty_sha256=LIB_SHA,cell_counts=source['cells'],ports=source['ports'],
        reused_artifacts=dict(artifacts=artifacts),map_result_sha256=sha(mapped/'result.json'))
    (adapted/'receipt.json').write_text(json.dumps(mapper,indent=2)+'\n')
    engine=argparse.Namespace(top=TOP,mapping=adapted.parent,out=args.out,side=side,
        pin_bands=2,core_margin=20,density=args.density,cpus=10,grow_to_fit=False,
        upper_adjustment=None,r_compact_floorplan=False,r_strong_clock=False,
        remove_abc_buffers=False,placement_mode='timing',fanout_mode='original',
        refine_partition_placement=False,placement_hold_margin=None,input_receivers=True,
        hold_repair_margin=.02)
    receipt=dict(passed=False,top=TOP,rows=args.rows,port_bits=signals,side_um=side,
        source_commit=(ROOT.parent/'source-commit.txt').read_text().strip(),
        source_manifest_sha256=sha(ROOT.parent/'source.sha256'),
        exact_mapping_receipt_sha256=mapper['map_result_sha256'],
        affinity=sorted(os.sched_getaffinity(0)),job=os.environ['SLURM_JOB_ID'],
        commands=[],start_unix=time.time(),physical_qualified=False,
        scope='Original TT300MHz constraints and M1–M10 route. Completion alone is not physical/electrical/DRC/LEC acceptance.')
    def run(command,log):
        command=list(map(str,command));at=time.time()
        with (args.out/log).open('w') as stream:
            result=subprocess.run(command,cwd=args.out,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=command,log=log,returncode=result.returncode,
            sha256=sha(args.out/log),seconds=time.time()-at))
        assert result.returncode==0,(log,result.returncode)
    try:
        implement(engine,run);receipt['passed']=True
    finally:
        receipt['end_unix']=time.time()
        receipt['outputs']={p.relative_to(args.out).as_posix():sha(p) for p in args.out.rglob('*') if p.is_file()}
        (args.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mapping',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--rows',type=int,choices=(1,2,4),default=4);p.add_argument('--side',type=int,default=0)
    p.add_argument('--density',type=float,default=.48);args=p.parse_args();assert 0<args.density<=1
    main(args)
