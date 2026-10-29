"""Avoid macro swap crash: exact DEF checkpoint transfer into matched masters.

First validate geometry/graph/FIXED/PG readback. No route, freeze or success
inference from the import. Closed prior crash and all source files preserved.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_common_integration import CASES,SHARED_SNAPSHOT,verify_graph
DRIVER=Path(__file__).resolve().parent

def run(revision):
    prep=ROOT/'common_current_resume/r01';pq=json.loads((prep/'execution.json').read_text())
    assert pq.get('completed_utc') and pq['native_route_returncode']==-11 and pq['all_closed_sources_unchanged']
    assert pq['native_stage_status']['conservative_OBS_existing_PG_clear']=='EXECUTED'
    original=ROOT/'common_integration/deadline-current-r01/C';q=json.loads((original/'execution.json').read_text());odb=original/'fixed_prewires_NOT_FROZEN.odb'
    assert q.get('completed_utc') and sha(odb)==q['files'][odb.name]['sha256']
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef'
    inputs={str(p):sha(p) for p in [prep/'execution.json',original/'execution.json',odb,tech,original/'actual_shared_conductors.json']}
    out=ROOT/'common_checkpoint_def_import'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_CURRENT_COMMON_DEF_CHECKPOINT_READBACK_NOT_ROUTING_FREEZE_OR_TWO_FUNCTIONS',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'source_SHA':inputs,'full_qualification':False,'original_failure':'93539 native swapMaster SIGSEGV; root not yet proven, avoid by fresh DEF import rather than repeating swap',
      'previous_added_OBS_actual_PG_overlap_tests':3415950,'routing_RC_STA_functions':'NOT_EXECUTED_IMPORT_ONLY','native_returncodes':{}}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save();common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    helper=(DRIVER/'parent_trial.tcl').read_text().split('if {![stage load {',1)[0]
    shared=json.loads((original/'actual_shared_conductors.json').read_text());assert len(shared)==256
    sharedsetup='set common_shared_pads {'+' '.join(w['construction_pad'] for w in shared)+'}'
    def native(label,body):
        script=out/(label+'.tcl');script.write_text(helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')+'\n'+SHARED_SNAPSHOT+'\n'+sharedsetup+'\n'+body+'\n')
        rc=execute(common,script,out/(label+'.log'),'PINXY_PARENT_OUT='+str(out),threads=4);rec['native_returncodes'][label]=rc;save();assert rc==0,(label,rc)
    try:
        native('export_original','read_db '+tcl(odb)+'\nparent_contract '+tcl(out/'before')+'\ncommon_shared_snapshot '+tcl(out/'before.shared.tsv')+'\nwrite_def '+tcl(out/'original_fixed.def')+'\nclose $stages')
        replacements=Counter();inside=False
        with (out/'original_fixed.def').open() as f,(out/'current_fixed.def').open('x') as g:
            for line in f:
                if line.startswith('COMPONENTS '):inside=True
                elif line.startswith('END COMPONENTS'):inside=False
                if inside:
                    for case in CASES:
                        old='p126_'+case;new='p126resume_'+case
                        line,n=re.subn(r'^(\s*-\s+u_'+re.escape(case)+r'\s+)'+re.escape(old)+r'(?=\s)',lambda m:m[1]+new,line);replacements[case]+=n
                g.write(line)
        assert all(replacements[c]==1 for c in CASES)
        lines=['read_lef '+tcl(tech),'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef',
          'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib']
        for case in CASES:
            for suffix in ['.lef','.lib']:
                p=prep/('p126resume_'+case+suffix);assert sha(p)==pq['files'][p.name]['sha256'];inputs[str(p)]=sha(p)
                lines.append(('read_lef ' if suffix=='.lef' else 'read_liberty ')+tcl(p))
        lines+=['if {![stage import_exact_checkpoint {read_def '+tcl(out/'current_fixed.def')+'}]} {close $stages;exit 1}',
          'parent_contract '+tcl(out/'after'),'common_shared_snapshot '+tcl(out/'after.shared.tsv'),
          'write_db '+tcl(out/'imported_current_NOT_ROUTED_NOT_FROZEN.odb'),'write_def '+tcl(out/'imported_current.def'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}','close $stages']
        native('fresh_import','\n'.join(lines))
        counter=lambda p:Counter(tuple(line.split()) for line in p.read_text().splitlines()[1:])
        rec['original_parent_preserved']={k:counter(out/('before.'+k+'.tsv'))==counter(out/('after.'+k+'.tsv')) for k in ['pins','endpoints']}
        # PG file intentionally has no header.
        rec['original_parent_preserved']['pdn']=Counter((out/'before.pdn.tsv').read_text().splitlines())==Counter((out/'after.pdn.tsv').read_text().splitlines())
        assert all(rec['original_parent_preserved'].values())
        assert counter(out/'before.shared.tsv')==counter(out/'after.shared.tsv')
        rec['all256_shared_geometry_and_graph_preserved']=True
        a=list(csv.DictReader((out/'before.instances.tsv').open(),delimiter='\t'));b=list(csv.DictReader((out/'after.instances.tsv').open(),delimiter='\t'))
        for row in a:
            if row['instance'] in ['u_'+c for c in CASES]:row['master']='p126resume_'+row['instance'][2:]
        assert sorted(a,key=lambda r:r['instance'])==sorted(b,key=lambda r:r['instance']);rec['all_original_instance_poses_and_resources_preserved']=True
        assert len(re.findall(r'\+\s+FIXED\s+metal10\b',(out/'imported_current.def').read_text()))==256;rec['all256_native_FIXED_status_preserved']=True
        verify_graph(ROOT/'inputs/common-topology-r02',out/'after.endpoints.tsv',out/'all_original_graph_check.json');rec['full_compiled_endpoint_graph_verified']=True
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['native_stages']={p.name:{r['stage']:r['status'] for r in csv.DictReader(p.open(),delimiter='\t')} for p in out.glob('*stages.tsv')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'] or any(rec['native_stages'].get('fresh_import.stages.tsv',{}).get(k)!='EXECUTED' for k in ['VDD','VSS']))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
