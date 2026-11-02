"""Fresh native extraction and strict STA on an actual fixed PG wrapper."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--wrapper',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--leaf',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    native=Path(__file__).resolve().parents[1]/'block_v1';sys.path.insert(0,str(native))
    r=dict(passed=False,job=os.environ['SLURM_JOB_ID'],inputs={},whole_system_qualified=False,native_leaf_qualified=False,
        scope='Fresh native M1-M10 PG-wrapper RC/STA only; original logical behavior, whole PG connectivity and upper interconnect remain separate evidence.')
    def bind(path,digest=None):
        actual=sha(path)
        if digest:assert actual==digest,path
        r['inputs'][str(path)]=actual
    def run(cmd,name,env=None):
        with (a.out/name).open('w') as f:q=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,cwd=a.out,env=env)
        assert q.returncode==0,name
    try:
        bind(a.wrapper/'receipt.json');w=json.loads((a.wrapper/'receipt.json').read_text())
        assert w['passed'] and w['native_drc_zero'] and w['full_deck']['total_items']==0
        for name,digest in w['outputs'].items():bind(a.wrapper/name,digest)
        assert sha(a.wrapper/'original.v')==sha(a.wrapper/'wrapper.v')
        bind(a.manifest);row=json.loads(a.manifest.read_text())['leaves'][a.leaf]
        bind(row['final_files']['6_final.odb']['path'],row['final_files']['6_final.odb']['sha256'])
        assert w['inputs'][row['final_files']['6_final.odb']['path']]==row['final_files']['6_final.odb']['sha256']
        platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
        lib=platform/'lib/NangateOpenCellLibrary_typical.lib';rules=platform/'rcx_patterns.rules';bind(lib);bind(rules)
        sdc=Path(row['final_files']['6_final.sdc']['path']);bind(sdc,row['final_files']['6_final.sdc']['sha256'])
        (a.out/'6_final.sdc').write_bytes(sdc.read_bytes());odb=a.wrapper/'wrapper.odb'
        text='set_thread_count 16\nread_liberty {'+str(lib)+'}\nread_db {'+str(odb)+'}\nread_sdc {'+str(sdc)+'}\n'
        text+='define_process_corner -ext_model_index 0 X\nset_extraction_rules_file {'+str(rules)+'}\nextract_parasitics\nwrite_spef {'+str(a.out/'6_final.spef')+'}\n'
        text+='set f [open passive-inventory.tsv w]\nforeach inst [[ord::get_db_block] getInsts] {set master [$inst getMaster];if {[$master getName] ne "ANTENNA_X1"} {continue};foreach term [$inst getITerms] {set def [$term getMTerm];if {[$def getSigType] in {POWER GROUND}} {continue};puts $f "[$inst getName]/[$def getName]\\t[$master getName]\\t[$master getType]\\t[$def getIoType]\\t[[$term getNet] getName]"}}\nclose $f\n'
        (a.out/'extract.tcl').write_text(text);run(['openroad','-no_init','-exit',a.out/'extract.tcl'],'extract.log')
        sta=native/'native_sta.tcl';bind(sta);bind(native/'native_annotation.tcl')
        env=dict(os.environ,BV1_ODB=str(odb),BV1_SDC=str(a.out/'6_final.sdc'),BV1_SPEF=str(a.out/'6_final.spef'),OMP_NUM_THREADS='16')
        run(['openroad','-no_init','-exit',sta],'sta.log',env)
        inventory={}
        for line in (a.out/'passive-inventory.tsv').read_text().splitlines():
            name,master,kind,direction,net=line.split('\t');assert name not in inventory
            inventory[name]=dict(master=master,type=kind,direction=direction,net=net,pin=name.rsplit('/',1)[1])
        from native_passive_endpoint import audit
        timing=audit(a.out,a.out/'typed-endpoints',lib.read_text(),inventory)
        (a.out/'typed-native-timing.json').write_text(json.dumps(timing,indent=2)+'\n')
        r.update(passed=timing['passed'],timing_passed=timing['passed'],fresh_native_extraction=True,
                 original_signal_netlist_identical=True,minimum_setup_ns=timing['timed_endpoints']['minimum_setup_ns'],minimum_hold_ns=timing['timed_endpoints']['minimum_hold_ns'])
    finally:
        r['outputs']={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    assert r['passed'],'Fresh fixed-PG native timing failed'

if __name__=='__main__':main()
