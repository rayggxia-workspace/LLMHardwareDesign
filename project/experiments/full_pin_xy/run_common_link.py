"""Native six-resource construction link with real matching Aopt physical views.

No placement/routing/freeze or M11/M12 mode implementation is claimed. This
independently checks generated Verilog aliases/buses/constants against the full
compiled terminal/component contract before costly parent physical work.
"""
from pathlib import Path
import datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import child_source,alias_view,tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(inputs,revision):
    inputs=ROOT/'inputs'/inputs;out=ROOT/'common_native_link'/revision;out.mkdir(parents=True,exist_ok=False)
    expected=json.loads((inputs/'topology_proof.json').read_text());assert expected['all_original_signal_pins']==24767 and not expected['frozen']
    rec={'scope':'SIX_RESOURCE_NATIVE_CONSTRUCTION_LINK_ONLY_NO_PHYSICAL_BASE_OR_FREEZE','full_qualification':False,
         'input_contract_files_SHA':{str(p):sha(p) for p in inputs.iterdir() if p.is_file()},'views':{},
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    lines=['read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef',
           'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef',
           'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib']
    for case in ['act','mxu','opentpu_aux','gemm','vector','llaccel_aux']:
        lef,physical,proof=child_source(case,'Aopt')
        model_dir=ROOT/'leaf_timing_models'/('r05' if case in ['opentpu_aux','vector','llaccel_aux'] else 'r03')/(case+'-Aopt')
        model=json.loads((model_dir/'execution.json').read_text())
        assert model['status']=='NATIVE_EXTRACTED_MODEL_EXPORTED_NOT_QUALIFIED' and model['exact_all_signal_pin_direction_match']
        assert model['clean_odb_sha256']==physical['clean_odb_sha256'] and model['source_clean_receipt_sha256']==sha(proof)
        assert sha(model_dir/'timing.lib')==model['generated_library_sha256']
        text=lef.read_text();masters=re.findall(r'^MACRO\s+(\S+)',text,re.M);assert len(masters)==1
        master=masters[0];alias='p126_'+case;dest=out/(alias+'.lef');alias_view(lef,dest,master,alias)
        lib=(model_dir/'timing.lib').read_text();lib,n=re.subn(r'cell\s*\(\s*"?'+re.escape(master)+r'"?\s*\)','cell ("'+alias+'")',lib);assert n==1,(case,'model master mismatch')
        lpath=out/(alias+'.lib');lpath.write_text(lib)
        lines+=['read_lef '+tcl(dest),'read_liberty '+tcl(lpath)]
        rec['views'][case]={'physical_receipt':str(proof),'physical_receipt_SHA':sha(proof),'source_LEF_SHA':sha(lef),'source_model_SHA':model['generated_library_sha256'],
                             'source_model_receipt_SHA':sha(model_dir/'execution.json'),'alias_LEF_SHA':sha(dest),'alias_model_SHA':sha(lpath)}
    lines+=['read_verilog '+tcl(inputs/'base_construction.v'),'link_design hpy_common_base_construction',
            'set b [ord::get_db_block];set f [open '+tcl(out/'native_endpoints.tsv')+' w]',
            'puts $f "kind\\tinstance\\tpin\\tnet\\tdirection\\tlayer"',
            '''foreach n [$b getNets] {
 foreach it [$n getITerms] {
  if {[$it getSigType] in {POWER GROUND}} {continue}
  set layers {};foreach box [[$it getMTerm] getMPins] {foreach r [$box getGeometry] {lappend layers [[$r getTechLayer] getName]}}
  puts $f [join [list ITERM [[$it getInst] getName] [[$it getMTerm] getName] [$n getName] [$it getIoType] [join [lsort -unique $layers] ,]] "\\t"]
 }
 foreach bt [$n getBTerms] {puts $f [join [list BTERM {} [$bt getName] [$n getName] [$bt getIoType] {}] "\\t"]}
}''','close $f','write_db '+tcl(out/'linked_unplaced_NOT_BASE.odb'),
            'exec python3 -B '+tcl(DRIVER/'verify_common_native.py')+' '+tcl(inputs)+' '+tcl(out/'native_endpoints.tsv')+' '+tcl(out/'graph_check.json')]
    script=out/'link.tcl';script.write_text('\n'.join(lines)+'\n')
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rec['native_returncode']=execute(common,script,out/'native.log',threads=1)
    rec['graph_check']=json.loads((out/'graph_check.json').read_text()) if (out/'graph_check.json').exists() else None
    rec['source_contract_unchanged']=all(sha(Path(p))==h for p,h in rec['input_contract_files_SHA'].items())
    rec['status']='NATIVE_CONSTRUCTION_LINK_GRAPH_PASSED_NOT_PHYSICAL_BASE' if rec['native_returncode']==0 and rec['graph_check'] and rec['source_contract_unchanged'] else 'NATIVE_CONSTRUCTION_LINK_FAILED_NOT_BASE'
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status'],flush=True)
    return 0 if rec['status'].startswith('NATIVE_CONSTRUCTION_LINK_GRAPH_PASSED') else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
