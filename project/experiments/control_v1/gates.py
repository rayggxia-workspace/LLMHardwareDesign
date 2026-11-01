"""Independent all-final gates for the new control tops; no old macro edits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['seal','physical','drc','function','formal','deliver'])
    p.add_argument('--producer',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--sealed',type=Path);p.add_argument('--gates',type=Path)
    a=p.parse_args();assert os.environ.get('SLURM_JOB_ID')
    assert len(os.sched_getaffinity(0))<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    source_root=a.source_root.resolve()
    for folder in ['block_v2','block_v1','block_feed_v1']:sys.path.insert(0,str(source_root/'project/experiments'/folder))
    import qualify
    qualify.ROOT=source_root
    receipt=dict(passed=False,operation=a.operation,producer=str(a.producer),source_root=str(source_root),
                 affinity=sorted(os.sched_getaffinity(0)),job=os.environ['SLURM_JOB_ID'],commands=[],inputs={})
    receipt['gate_runner_sha256']=sha(Path(__file__))
    for folder in ['block_v1','block_feed_v1','block_v2']:
        for f in (source_root/'project/experiments'/folder).rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts:receipt['inputs'][str(f.relative_to(source_root))]=sha(f)
    def run(command,log):
        command=list(map(str,command));start=time.time()
        with (a.out/log).open('w') as f:q=subprocess.run(command,cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=command,log=log,sha256=sha(a.out/log),returncode=q.returncode,seconds=time.time()-start))
        assert q.returncode==0,(log,q.returncode)
    try:
        producer=json.loads((a.producer/'receipt.json').read_text());assert producer['passed'] and producer['rtl_passed']
        assert len(producer['runs'])==3
        for name,digest in producer['source_sha256'].items():assert sha(source_root/name)==digest
        receipt['producer_receipt_sha256']=sha(a.producer/'receipt.json')
        top=producer['top'];assert top in ('control_c','control_endpoint_queue')
        if a.operation=='seal':
            raw=a.producer/'pnr';flow=json.loads((raw/'native-flow.json').read_text())
            assert flow['passed'] and flow['pipeline_completed'] and flow['top']==top
            commands=[]
            for item in producer['commands']:
                if item['log'].startswith('pnr/'):
                    c=dict(item);c['log']=c['log'][4:];assert c['returncode']==0 and sha(raw/c['log'])==c['sha256'];commands.append(c)
            for name,row in flow['final_files'].items():assert sha(row['path'])==row['sha256']
            # Adding this index never edits/replaces a producer artifact. Bind
            # the actual successful producer, not an inferred native success.
            index=raw/'receipt.json';assert not index.exists()
            index.write_text(json.dumps(dict(passed=True,commands=commands,
                inputs=producer['source_sha256'],producer_receipt_sha256=sha(a.producer/'receipt.json'),
                outputs={str(f.relative_to(raw)):sha(f) for f in raw.rglob('*') if f.is_file()}),indent=2)+'\n')
            qualify.seal(raw,a.out)
        elif a.operation in ('physical','drc'):
            import receive
            getattr(receive,a.operation)(source_root,a.out,16,run,'s',selected=lambda target,kind:qualify.source(a.sealed))
        elif a.operation=='function':
            from native_signal_view import export
            folder,r,flow,results=qualify.source(a.sealed)
            lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
            netlist,proof=export(source_root,a.out,run,folder,r,results,top,lib)
            (a.out/'cells.ys').write_text(f'read_liberty -ignore_miss_func -ignore_miss_dir {lib}\nwrite_verilog -noattr cells.v\n')
            run(['yosys','-s',a.out/'cells.ys'],'cells.log')
            bench=source_root/'project/experiments/control_v1'/('test_c.cpp' if top=='control_c' else 'test_endpoint.cpp')
            compiler='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
            run([compiler,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module',top,'--Mdir',a.out/'obj',
                 '--output-split','12000','--output-split-cfuncs','150','--x-initial','unique','--x-assign','unique',
                 '-CFLAGS','-std=c++17 -O1',netlist,a.out/'cells.v',bench],'build.log')
            runs={}
            for label,mode,seed in [('all-ones',1,162),('random-162',2,162),('random-163',2,163)]:
                log=label+'.log';run([a.out/'obj'/('V'+top),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
                result=json.loads((a.out/log).read_text());assert result['passed'];runs[label]=dict(result=result,log_sha256=sha(a.out/log))
            assert all(v['result']==runs['all-ones']['result'] for v in runs.values())
            (a.out/'final-function.json').write_text(json.dumps(dict(passed=True,top=top,source_receipt_sha256=sha(a.sealed/'receipt.json'),
                full_final_netlist=proof,bench_sha256=sha(bench),initial_runs=runs),indent=2)+'\n')
        elif a.operation=='formal':
            qualify.final_formal(a.sealed,a.out,run,a.gates/'function')
        else:
            folder,r,flow,results=qualify.source(a.sealed)
            reports={'physical':'five-macro-physical.json','drc':'five-macro-drc.json','function':'final-function.json','formal':'formal.json'}
            proofs={};gate_receipts={}
            for op,name in reports.items():
                d=a.gates/op;g=json.loads((d/'receipt.json').read_text());assert g['passed']
                assert sha(d/name)==g['outputs'][name]
                report=json.loads((d/name).read_text());assert report['passed'] and report['source_receipt_sha256']==sha(a.sealed/'receipt.json')
                proofs[op]=report;gate_receipts[op]=dict(path=str(d/'receipt.json'),sha256=sha(d/'receipt.json'),report_sha256=sha(d/name))
            assert all(proofs['physical']['checks'].values()) and proofs['drc']['full_deck']['total_items']==0
            assert not proofs['drc']['native_report'].strip() and all(proofs['formal']['strict_native_lec']['checks'].values())
            assert proofs['formal']['function_receipt_sha256']==gate_receipts['function']['sha256']
            files={}
            for source in [results/('6_final.'+s) for s in ('v','sdc','def','odb','spef')]+[Path(proofs['drc']['gds']['path'])]:
                target=a.out/source.name;shutil.copyfile(source,target);assert sha(target)==sha(source)
                files[target.name]=dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size)
            shutil.copyfile(a.sealed/'pins.json',a.out/'pins.json')
            text='import pya\nv=pya.LayoutView()\nv.load_layout('+repr(str(a.out/'6_final.gds'))+',0)\nv.max_hier()\nv.add_missing_layers()\nv.zoom_fit()\nv.save_image('+repr(str(a.out/'layout.png'))+',1600,1600)\n'
            (a.out/'render.py').write_text(text);run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',a.out/'render.py'],'render.log')
            assert (a.out/'layout.png').stat().st_size>1000
            (a.out/'delivery.json').write_text(json.dumps(dict(passed=True,native_leaf_accepted=True,top=top,
                source_receipt_sha256=sha(a.sealed/'receipt.json'),gate_receipts=gate_receipts,final_files=files,
                active_area_um2=proofs['physical']['active_area_um2'],die_um=flow['die_um'],
                image_sha256=sha(a.out/'layout.png'),pins_sha256=sha(a.out/'pins.json'),
                complete_system_qualified=False,m11_m12_system_qualified=False),indent=2)+'\n')
        receipt['passed']=True
    finally:
        receipt['outputs']={str(f.relative_to(a.out)):sha(f) for f in a.out.rglob('*') if f.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
