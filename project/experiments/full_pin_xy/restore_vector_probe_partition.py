"""Restore the actual five-input source partition, keeping the strict proof.

First require the unchanged full directed-buffer relation on a simulated edit;
then edit the native checkpoint and require the same relation on a fresh full
native export. No verifier weakening, original input mutation or P&R claim.
"""
from pathlib import Path
import csv,datetime,hashlib,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from verify_mapped_eco import load,export_graph
from buffer_graph_contract import compare
from run_vector_resume import COST_PROC

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'vector_clone_probe/r03';rp=source/'execution.json';p=json.loads(rp.read_text())
    failed_path=ROOT/'vector_probe_equivalence/r01/execution.json';failed=json.loads(failed_path.read_text())
    diagnosis=ROOT/'vector_probe_partition_diagnosis/r01/execution.json';diag=json.loads(diagnosis.read_text())
    assert p.get('completed_utc') and diag['original_split_net_count']==1 and diag['new_actual_buffer_instances']==49
    assert diag['all_closed_sources_unchanged'] and failed['all_closed_sources_unchanged'] and not failed['relative_mapped_digital_contract_pass']
    checkpoint=source/'gate_repaired_NOT_LEGALIZED_OR_ROUTED.odb';reference=source/'source.tsv.gz';current=source/'repaired.tsv.gz'
    for f in [checkpoint,reference,current]:assert sha(f)==p['files'][f.name]['sha256']
    out=ROOT/'vector_partition_restore'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(f):sha(f) for f in [rp,failed_path,diagnosis,checkpoint,reference,current]}
    rec={'scope':'ACTUAL_SOURCE_PARTITION_RESTORE_AND_UNCHANGED_FULL_STRICT_MAPPED_RELATION_NOT_PNR_OR_RTL_QUALIFICATION',
      'source_SHA':inputs,'old_strict_failure_retained':True,'strict_verifier_changed':False,'new_cells_or_sizing_in_this_restore':0,
      'legality_route_RC_STA':'NOT_EXECUTED','full_qualification':False,'relative_mapped_digital_contract_pass':False,
      'native_returncodes':{},'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        raw=subprocess.check_output(common+[IMAGE,'cat',lib]);assert hashlib.sha256(raw).hexdigest()==failed['actual_Liberty_SHA256']
        a,at,ap=load(reference);b,bt,bp=load(current);assert ap==bp
        # Diagnosis identified exactly this real original net and its driver.
        net='net83166';driver=('place83184','Z');assert at[driver]==('OUTPUT',net) and bt[driver]==('OUTPUT',net)
        edits=[{'instance':n,'pin':pin,'before_net':bt[(n,pin)][1],'restored_source_net':net,
                'actual_candidate_master':b[n][0]} for (n,pin),(direction,nn) in at.items()
               if nn==net and bt[(n,pin)][1]!=net]
        assert len(edits)==5 and all(at[(r['instance'],r['pin'])][0]==bt[(r['instance'],r['pin'])][0]=='INPUT' for r in edits)
        proposed=dict(bt)
        for r in edits:proposed[(r['instance'],r['pin'])]=('INPUT',net)
        result=compare(a,at,ap,b,proposed,bp,raw.decode(),lib)
        rec['pre_native_simulated_strict_relation_pass']=True;rec['exact_five_input_restores']=edits;save()
        with (out/'exact_input_restores.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(edits[0]),lineterminator='\n');w.writeheader();w.writerows(edits)
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        lines=[helper,COST_PROC,'read_db '+tcl(checkpoint),'fingerprint '+tcl(out/'before'),'cell_cost '+tcl(out/'before.cell_cost.tsv'),
          'set b [ord::get_db_block];set original_driver [$b findInst {place83184}];set driver_term [$original_driver findITerm {Z}];set target [$driver_term getNet];if {[$target getName] ne {net83166} || [$target getSigType] ne {SIGNAL}} {error "Actual original driver net contract differs"}']
        for r in edits:
            lines+=['set i [$b findInst '+tcl(r['instance'])+'];if {$i eq "NULL" || [[$i getMaster] getName] ne '+tcl(r['actual_candidate_master'])+'} {error "Actual restore instance/master differs"}',
              'set it [$i findITerm '+tcl(r['pin'])+'];if {$it eq "NULL" || [$it getIoType] ne {INPUT} || [[$it getNet] getName] ne '+tcl(r['before_net'])+'} {error "Actual restore endpoint differs"};$it disconnect;$it connect $target']
        lines+=['fingerprint '+tcl(out/'after'),'cell_cost '+tcl(out/'after.cell_cost.tsv'),
          'write_db '+tcl(out/'partition_restored_NOT_LEGALIZED_OR_ROUTED.odb'),'write_verilog '+tcl(out/'partition_restored_NOT_QUALIFIED.v'),'close $stages']
        script=out/'restore.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncodes']['restore_original_five_inputs']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out),threads=1);save()
        assert rec['native_returncodes']['restore_original_five_inputs']==0
        rec['all_cell_instances_masters_poses_areas_unchanged']=sha(out/'before.cell_cost.tsv')==sha(out/'after.cell_cost.tsv')
        rec['all_original_pins_PG_die_unchanged']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        assert rec['all_cell_instances_masters_poses_areas_unchanged'] and all(rec['all_original_pins_PG_die_unchanged'].values())
        fixed=out/'partition_restored_NOT_LEGALIZED_OR_ROUTED.odb'
        rec['native_returncodes']['restored_full_graph']=export_graph(common,fixed,out,'restored');assert rec['native_returncodes']['restored_full_graph']==0
        c,ct,cp=load(out/'restored.tsv.gz');assert c==b and cp==bp
        changes=[key for key in set(bt)|set(ct) if bt.get(key)!=ct.get(key)]
        assert set(changes)=={(r['instance'],r['pin']) for r in edits}
        rec['actual_changed_signal_terminals_exactly_five_inputs']=True
        result=compare(a,at,ap,c,ct,cp,raw.decode(),lib)
        (out/'native_actual_strict_digital_relation.json').write_text(json.dumps(result,indent=2)+'\n')
        rec['relative_mapped_digital_contract_pass']=True
        rec['summary']={k:v for k,v in result.items() if k not in ['changed_original_master_contracts','new_buffer_master_contracts']}
        rec['source_actual_Liberty_SHA256']=hashlib.sha256(raw).hexdigest()
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.iterdir() if f.is_file() and f.name!='execution.json'};save()
    return 0 if rec['relative_mapped_digital_contract_pass'] and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
