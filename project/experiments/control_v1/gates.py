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
    p.add_argument('--drc',type=Path,help='Same-sealed-source DRC retry; passed other gates are retained')
    p.add_argument('--native-s',action='store_true',help='Fresh user-authorized S layout; all four gates are rerun, including the independent S bench')
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
        producer=json.loads((a.producer/'receipt.json').read_text());assert producer['passed']
        if a.native_s:
            assert producer['top']=='block_feed_s_macro' and producer['native_pipeline_completed']
            assert producer['internal_drive_policy']['no_new_registers']
            assert producer['internal_drive_policy']['physical_owner']=='block_feed_s_macro M1-M10'
            for name,digest in producer['inputs'].items():assert sha(name)==digest
        else:
            assert producer['rtl_passed'] and len(producer['runs'])==3
            for name,digest in producer['source_sha256'].items():assert sha(source_root/name)==digest
        receipt['producer_receipt_sha256']=sha(a.producer/'receipt.json')
        top=producer['top'];assert (a.native_s and top=='block_feed_s_macro') or top in ('control_c','control_endpoint_queue','control_d','control_axil_bridge',
            'control_adapter_m','control_adapter_n','control_adapter_e','control_adapter_g','control_adapter_s','control_adapter_t',
            'control_route','control_s_arbiter','control_status','control_reset_distribution','control_link8')
        if a.operation=='seal':
            raw=a.producer if a.native_s else a.producer/'pnr';flow=json.loads((raw/'native-flow.json').read_text())
            assert flow['passed'] and flow['pipeline_completed'] and flow['top']==top
            if a.native_s:
                drive=flow['strong_output_driver_proof']
                assert flow['strong_output_drivers'] and drive['passed'] and drive['all_actual_drivers_BUF_X32']
                assert drive['output_count']==producer['internal_drive_policy']['output_bits']==788
                assert sha(drive['table'])==drive['table_sha256'] and sha(drive['odb'])==drive['odb_sha256']
                qualify.seal(raw,a.out)
                receipt['passed']=True
                return
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
        elif a.operation=='physical':
            import receive
            getattr(receive,a.operation)(source_root,a.out,16,run,'s',selected=lambda target,kind:qualify.source(a.sealed))
        elif a.operation=='drc':
            # The old issue130 copy-slot helper intentionally disallows this
            # task's directory. Keep that guard untouched; use this owned path
            # and the identical complete native/GDS checks instead.
            from native_drc import summarize
            owned=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162').resolve()
            assert owned in a.out.parents
            folder,r,flow,results=qualify.source(a.sealed)
            script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nwrite_def before.def\n'
            script+='if {[llength [info commands ::drt::check_drc_cmd]]!=1} {error "Missing whole-chip DRC API"}\n'
            script+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\nwrite_def after.def\n'
            (a.out/'native-drc.tcl').write_text(script);run(['openroad','-no_init','-exit',a.out/'native-drc.tcl'],'native-drc.log')
            assert sha(a.out/'before.def')==sha(a.out/'after.def')
            native=(a.out/'native-whole-drc.rpt').read_text();assert not native.strip(),'Final complete native DRC violations'
            nickname='bv1_'+top;target=a.out/'gds-flow/results/nangate45'/nickname/'base';target.mkdir(parents=True)
            for category in ('logs','reports','objects'):(a.out/'gds-flow'/category/'nangate45'/nickname/'base').mkdir(parents=True)
            shutil.copyfile(results/'6_final.def',target/'6_final.def')
            run(['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(folder/'config.mk'),
                 'WORK_HOME='+str(a.out/'gds-flow'),'NUM_CORES=16','do-gds'],'gds.log')
            gds=target/'6_final.gds';deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
            run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(a.out/'full-deck.lyrdb'),'-r',deck],'full-deck.log')
            summary=summarize(a.out/'full-deck.lyrdb');qualify.source(a.sealed)
            result=dict(passed=summary['total_items']==0,top=top,source_receipt_sha256=sha(folder/'receipt.json'),
                native_report=native,full_deck=summary,deck_sha256=sha(deck),
                gds=dict(path=str(gds),sha256=sha(gds),bytes=gds.stat().st_size))
            (a.out/'five-macro-drc.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']
        elif a.operation=='function':
            from native_signal_view import export
            folder,r,flow,results=qualify.source(a.sealed)
            lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
            netlist,proof=export(source_root,a.out,run,folder,r,results,top,lib)
            (a.out/'cells.ys').write_text(f'read_liberty -ignore_miss_func -ignore_miss_dir {lib}\nwrite_verilog -noattr cells.v\n')
            run(['yosys','-s',a.out/'cells.ys'],'cells.log')
            benches={'control_c':'test_c.cpp','control_endpoint_queue':'test_endpoint.cpp','control_d':'test_d.cpp','control_axil_bridge':'test_axil.cpp'}
            benches.update({'control_adapter_'+role:'test_adapter_'+role+'.cpp' for role in ('m','n','e','g','s','t')})
            benches.update(control_route='test_route.cpp',control_s_arbiter='test_s_arbiter.cpp',control_status='test_status.cpp',control_reset_distribution='test_reset.cpp')
            benches['control_link8']='test_link8.cpp'
            benches['block_feed_s_macro']='test_native_s.cpp'
            bench=source_root/'project/experiments/control_v1'/benches[top]
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
                d=a.drc if op=='drc' and a.drc else a.gates/op
                g=json.loads((d/'receipt.json').read_text());assert g['passed']
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
