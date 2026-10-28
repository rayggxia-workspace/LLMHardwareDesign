"""Whole native mapped graph identity with real, non-driving ANTENNA_X1 loads."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_escape_fixture import execute
from verify_mapped_eco import export_graph,load
from cell_semantics import contract,groups
from run_parent_trial import tcl

DRIVER=Path(__file__).resolve().parent


def run(revision):
    implementation=ROOT/'antenna_diode_eco/r01/gemm-C';ip=implementation/'execution.json'
    observed=ip.read_bytes();j=json.loads(observed)
    assert j['native_returncodes'].get('implementation')==0,'Require the native implementation process to be closed'
    before=ROOT/'eco_views/r02/gemm-C/clean.odb';after=implementation/'routed.odb'
    assert sha(before)==j['source_SHA'][str(before)]
    assert sha(implementation/'before.original.tsv')==sha(implementation/'after.original.tsv')
    out=ROOT/'passive_load_equivalence'/revision/'gemm';out.mkdir(parents=True,exist_ok=False)
    (out/'observed_implementation_receipt.json').write_bytes(observed)
    inputs={str(q):sha(q) for q in [before,after,implementation/'before.original.tsv',implementation/'after.original.tsv',implementation/'diode_placed.tsv',ROOT/'antenna_netmap/r02/unique_correlated_native_nets.json']}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    rec={'scope':'WHOLE_MAPPED_GRAPH_IDENTITY_WITH_PROVEN_NON_DRIVING_REAL_DIODE_LOADS',
      'source_SHA':inputs,'observed_implementation_receipt_SHA':hashlib.sha256(observed).hexdigest(),
      'observed_implementation_receipt_terminal':bool(j.get('completed_utc')),
      'source_receipt_may_advance_independent_DRC_not_a_geometry_mutation':True,
      'digital_scope':'Same hard-memory contracts; original instances, all original terminals, directions, networks and ports unchanged. Added cells only single-input non-driving diode loads.',
      'RTL_formal_equivalence':'NOT_EXECUTED','RC_timing_analog_equivalence':'NOT_CLAIMED',
      'full_qualification':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        codes=[export_graph(common,p,out,label) for p,label in [(before,'reference'),(after,'real_diodes')]]
        rec['native_export_codes']=codes;assert codes==[0,0]
        a,at,ap=load(out/'reference.tsv.gz');b,bt,bp=load(out/'real_diodes.tsv.gz')
        assert set(a)<=set(b) and all(a[n]==b[n] for n in a),'Original functional instances/masters changed'
        assert ap==bp,'Original ports/directions/networks changed'
        original={k:v for k,v in bt.items() if k[0] in a}
        assert at==original,'Original signal terminals/directions/networks changed'
        added=set(b)-set(a);assert len(added)==636
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        raw=subprocess.check_output(common+[IMAGE,'cat',lib]);text=raw.decode();model=contract(text,'ANTENNA_X1')
        assert model['state']==[] and model['pins']==[('A',[('direction','input')])],model
        bodies=[body for name,body in groups(text,'cell') if name=='ANTENNA_X1'];assert len(bodies)==1
        pin=dict(groups(bodies[0],'pin'))['A'];cap=float(re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)',pin).group(1));assert cap>0
        target=set(json.loads((ROOT/'antenna_netmap/r02/unique_correlated_native_nets.json').read_text()))
        added_terms={k:v for k,v in bt.items() if k[0] in added};nets=[]
        for name in sorted(added):
            assert b[name]==('ANTENNA_X1','CORE_ANTENNACELL')
            terms={p:v for (i,p),v in added_terms.items() if i==name}
            assert len(terms)==1 and terms.get('A',(None,))[0]=='INPUT'
            assert terms['A'][1]!='NULL';nets.append(terms['A'][1])
        assert len(set(nets))==636 and set(nets)==target
        rec['relative_mapped_digital_contract_pass']=True
        rec['summary']={'original_nonfiller_instances':len(a),'actual_nonfiller_instances':len(b),
          'original_signal_terminals':len(at),'top_ports':len(ap),'added_real_diode_cells':len(added),
          'added_non_driving_input_loads':len(added_terms),'each_target_native_net_exactly_one_real_diode':True,
          'original_all_signal_terminal_and_port_graph_exactly_equal':True,
          'actual_single_input_no_output_or_state_contract':model,'actual_input_capacitance':cap,
          'actual_typical_Liberty_SHA256':hashlib.sha256(raw).hexdigest()}
        # Diagnose the new physical electrical failures against actual native
        # master identities; do not guess drive-strength substitutions.
        audit=out/'electrical_targets.tcl'
        audit.write_text('read_db '+tcl(after)+'\nset f [open '+tcl(out/'electrical_targets.tsv')+' w]\nputs $f "instance\\tmaster\\toutput_pin\\tnet\\tload_ITerms\\tports\\tlocation_dbu"\nforeach name {_328822_ _332783_} {set i [[ord::get_db_block] findInst $name];if {$i eq "NULL"} {error "Missing actual violating cell"};set t [$i findITerm ZN];set n [$t getNet];puts $f [join [list $name [[$i getMaster] getName] ZN [$n getName] [llength [$n getITerms]] [llength [$n getBTerms]] [$i getLocation]] "\\t"]};close $f\n')
        rec['electrical_target_export_returncode']=execute(common,audit,out/'electrical_targets.log',threads=1)
    except Exception:
        rec['relative_mapped_digital_contract_pass']=False;rec['actual_failure']=traceback.format_exc()
    rec['all_stable_geometry_and_source_files_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec.get('relative_mapped_digital_contract_pass') and rec['all_stable_geometry_and_source_files_unchanged'] and rec.get('electrical_target_export_returncode')==0 else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
