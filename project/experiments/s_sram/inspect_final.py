"""Read-only reception of actual routed S, with real SRAM timing and geometry.

Run only in an allocated job, in a fresh output folder. Reports failure without
changing producer data. Timing, native DRC, PG and pins are separate checks;
this script does not award macro transistor LVS or functional qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
HELP=ROOT/'project/experiments/block_v1'
sys.path.insert(0,str(HELP))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--physical',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();assert os.environ.get('SLURM_JOB_ID')
    folder=a.physical.resolve();out=a.out.resolve();out.mkdir(exist_ok=False,parents=True)
    result=dict(passed=False,qualified=False,commands=[],checks={},inputs={})
    def save():(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(argv,log):
        argv=list(map(str,argv))
        with (out/log).open('w') as f:
            p=subprocess.run(argv,cwd=out,stdout=f,stderr=subprocess.STDOUT)
        result['commands'].append(dict(argv=argv,returncode=p.returncode,log=log,sha256=sha(out/log)));save()
        assert p.returncode==0,(log,p.returncode)
    try:
        pr=json.loads((folder/'receipt.json').read_text())
        assert pr['passed'] and pr['pipeline_completed']
        files={n:Path(v['path']) for n,v in pr['final_files'].items()}
        for n,p in files.items():assert sha(p)==pr['final_files'][n]['sha256']
        gen=[Path(p) for p in pr['inputs'] if p.endswith('/generation.json')]
        assert len(gen)==1 and sha(gen[0])==pr['inputs'][str(gen[0])]
        g=json.loads(gen[0].read_text())
        lib=Path(g['views']['lib']['path']);assert sha(lib)==g['views']['lib']['sha256']
        std=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
        for p in [folder/'receipt.json',folder/'input.sdc',folder/'pins.json',folder/'pins.tcl',lib,std,*files.values()]:
            result['inputs'][str(p)]=sha(p)
        # STA uses the original, exact 300MHz boundary, never a relaxed
        # constraint or macro analytical approximation. Retain raw flow SDC.
        prefix=f'set ::env(BV1_ODB) {{{files["6_final.odb"]}}}\n'
        prefix+=f'set ::env(BV1_SDC) {{{folder/"input.sdc"}}}\n'
        prefix+=f'set ::env(BV1_SPEF) {{{files["6_final.spef"]}}}\n'
        # Standard library first preserves the project's ns/fF STA units.
        prefix+=f'read_liberty {{{std}}}\nread_liberty {{{lib}}}\n'
        prefix+='rename write_sdc original_write_sdc\nproc write_sdc {args} {uplevel 1 [list original_write_sdc -digits 12 {*}$args]}\n'
        for name in ('sta','physical'):
            original=HELP/('native_'+name+'.tcl')
            body=original.read_text()
            body=body.replace('source [file join [file dirname [info script]] native_annotation.tcl]',
                              'source {'+str(HELP/'native_annotation.tcl')+'}')
            (out/(name+'.tcl')).write_text(prefix+body)
            result['inputs'][str(original)]=sha(original)
            run(['openroad','-no_init','-exit',out/(name+'.tcl')],name+'.log')
        from native_passive_endpoint import audit
        from native_annotation import inspect
        from pin_contract import inspect as pin_audit
        from revision300_constraint_readback import audit as constraint_audit
        from revision300_constraints_control import control
        inventory={}
        for line in (out/'passive-inventory.tsv').read_text().splitlines():
            name,master,typ,direction,net=line.split('\t')
            inventory[name]=dict(master=master,type=typ,direction=direction,net=net,pin=name.rsplit('/',1)[1])
        result['timing']=audit(out,out/'timed-endpoints',std.read_text(),inventory)
        result['annotation']=inspect(out)
        plan=json.loads((folder/'pins.json').read_text())
        result['pins']=pin_audit(plan,(folder/'pins.tcl').read_text(),(out/'physical-pins.tsv').read_text(),2000)
        # Same-tool native reference plus independently wrong period/load/delay
        # controls; never construct a reference from the result being judged.
        controls=out/'boundary-control';controls.mkdir()
        control(ROOT,controls,16,lambda cmd,log:run(cmd,'boundary-'+log))
        reference=json.loads((controls/'revision300-constraints-control.json').read_text())
        assert reference['passed'] and reference['budget']==pr['budget']
        result['boundary']=constraint_audit((out/'constraints-readback.sdc').read_text(),
                                           plan['pins'],pr['budget'],reference['serialization'])
        result['approved_input_sdc_sha256']=sha(folder/'input.sdc')
        summary={}
        for line in (out/'physical-summary.tsv').read_text().splitlines():
            k,*v=line.split('\t');assert k not in summary;summary[k]=v
        result['physical_summary']=summary
        script=f'read_db {{{files["6_final.odb"]}}}\nwrite_def before.def\n'
        script+='drt::check_drc_cmd native-drc.rpt 0 0 0 0 native_whole_drc\nwrite_def after.def\n'
        (out/'drc.tcl').write_text(script)
        run(['openroad','-no_init','-exit',out/'drc.tcl'],'drc.log')
        assert sha(out/'before.def')==sha(out/'after.def')
        result['checks']=dict(timing=result['timing']['passed'],rc=result['annotation']['passed'],
            pins=result['pins']['passed'],native_drc=not (out/'native-drc.rpt').read_text().strip(),
            whole_gds_drc=pr['whole_gds_drc']['clean'],all_placed=summary['unplaced']==['0'],
            pg_iterms=summary['incorrect_pg_iterms']==['0'] and int(summary['pg_iterm_count'][0])>0,
            pg_vdd=summary['pg_VDD']==['1'],pg_vss=summary['pg_VSS']==['1'],
            signal_inputs_connected=summary['open_signal_inputs']==['0'],
            native_dbu=summary['dbu']==['2000'],
            ten_layers=summary['routing_layers']==[','.join('metal'+str(i) for i in range(1,11))])
        assert all(sha(p)==h for p,h in result['inputs'].items())
        result['passed']=all(result['checks'].values())
        save();assert result['passed'],result['checks']
    except Exception as e:
        result['failure']=repr(e);raise
    finally:save()

if __name__=='__main__':main()
