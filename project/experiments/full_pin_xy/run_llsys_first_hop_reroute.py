"""Actually move and reroute74 residual ports plus measured parent-failed1011.

All13507 ports remain inventoried, including13 bounded-search failures. This
is an incremental native leaf experiment, not a parent access/full system pass.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_llsys_actual_tips import pin_contract
from compare_native_route_representations import routing_box_hashes
from check_access import check
DRIVER=Path(__file__).resolve().parent

def run(revision):
    source=ROOT/'llsys_wire_pin_retention/r01';rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['fresh_DRC_count']==0 and q['whole_signal_geometry']['pass'] and q['all_closed_sources_unchanged']
    odb=source/'routed.odb';geo=source/'whole_access.tsv.gz'
    for p in [odb,geo]:assert sha(p)==q['files'][p.name]['sha256']
    inputs={str(p):sha(p) for p in [rp,odb,geo]};rows=[];unmoved=[]
    for folder,name in [('llsys_residual_access_preflight/r02','all87_first_hop_targets_NOT_IMPLEMENTED.json'),('llsys_parent_failed_pin_preflight/r02','all1_first_hop_targets_NOT_IMPLEMENTED.json')]:
        f=ROOT/folder;p=f/'execution.json';proof=json.loads(p.read_text());target=f/name
        assert proof.get('completed_utc') and not proof.get('actual_failure') and proof['all_closed_sources_unchanged'] and proof['source_SHA'][str(odb)]==sha(odb)
        assert sha(target)==proof['files'][target.name]['sha256'];inputs.update({str(x):sha(x) for x in [p,target]})
        for r in json.loads(target.read_text()):
            if r['status']=='PRESCREENED_REAL_FIRST_HOP_POINT_REQUIRES_ACTUAL_REROUTE':rows.append(r)
            else:unmoved.append(r)
    assert len(rows)==75 and len({r['pin'] for r in rows})==75 and len(unmoved)==13
    # Never silently create a new candidate-to-candidate first-hop conflict.
    for index,a in enumerate(rows):
        for b in rows[index+1:]:
            assert abs(a['target_x_DBU']-b['target_x_DBU'])>=2000 or abs(a['target_y_DBU']-b['target_y_DBU'])>=2000,'Nearby candidate first hops require explicit coupled re-screen'
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());guide=trial.parent/'route.guide';sdc=Path(old['source_sdc'])
    assert sha(guide)==old['outputs'][guide.name]['sha256'] and sha(sdc)==old['input_sha256'][str(sdc)]
    for p in [trial,guide,sdc]:inputs[str(p)]=sha(p)
    out=ROOT/'llsys_first_hop_reroute'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL75_PORT_FIRST_HOP_PIN_XY_EDIT_AND_SELECTED_NATIVE_REROUTE_NOT_FULL_SYSTEM',
      'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'full_qualification':False,'source_signal_pins':13507,'selected_real_reroute_ports':75,'unmoved_residual_ports':unmoved,
      'unchanged_current_internal_C_other_pins':13432,'new_functional_cells_or_sizing':0,
      'allowed_layers':'UNCHANGED signal M2-M8; clock M4-M8','parent_targets':'UNCHANGED/PARTIALLY_UNKNOWN historical; no reassignment',
      'original_clock_and_loads':'UNCHANGED','parent_access':'NOT_YET_CHECKED','native_returncodes':{},
      'source_failure':'Common parent NoAP bit_1011: foreign net257248 M6 wire above original M5 pin; verified target0.28um away'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save();(out/'all_selected_targets.json').write_text(json.dumps(rows,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    for lib in old['libs']:
        if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    targets={r['pin']:(r['layer'],[r['target_x_DBU']-140,r['target_y_DBU']-140,r['target_x_DBU']+140,r['target_y_DBU']+140]) for r in rows}
    try:
        # Native guides are hints; expand only selected net windows around both
        # old and new access. Original guides of every other net remain exact.
        extra={r['net']:(min(int(r['x0']),r['target_x_DBU']-140)-4480,min(int(r['y0']),r['target_y_DBU']-140)-4480,max(int(r['x1']),r['target_x_DBU']+140)+4480,max(int(r['y1']),r['target_y_DBU']+140)+4480) for r in rows}
        actual=out/'route.guide';current=None;seen=set()
        with guide.open() as f,actual.open('x') as g:
            for line in f:
                p=line.split()
                if len(p)==1 and p[0] not in ['(',')']:current=p[0].strip('{}')
                if p==[')'] and current in extra:
                    z=extra[current]
                    for layer in range(2,9):g.write(' '.join(map(str,z))+' metal'+str(layer)+'\n')
                    seen.add(current)
                g.write(line)
        assert seen==set(extra)
        lines=[helper]+['read_liberty '+tcl(p) for p in old['libs']]+['read_db '+tcl(odb),
          'set_routing_layers -signal metal2-metal8 -clock metal4-metal8','fingerprint '+tcl(out/'before'),
          'set b [ord::get_db_block];set original_obs [lsort [$b getObstructions]];set selected_names {}',
          'if {![stage actual75_pin_edits {']
        for r in rows:
            lines+=['set bt [$b findBTerm '+tcl(r['pin'])+'];if {$bt eq "NULL" || [[$bt getNet] getName] ne '+tcl(r['net'])+'} {error "Actual pin peer net changed"}',
              'place_pin -pin_name '+tcl(r['pin'])+' -layer '+r['layer']+' -location {'+str(r['target_x_DBU']/2000.)+' '+str(r['target_y_DBU']/2000.)+'} -pin_size {.14 .14}',
              'lappend selected_names '+tcl(r['net'])]
        lines+=['}]} {close $stages;exit 1}','fingerprint '+tcl(out/'moved'),
          'read_guides '+tcl(actual),'set_nets_to_route $selected_names',
          'if {![stage selected75_actual_detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {catch {write_db '+tcl(out/'failed_route.odb')+'};close $stages;exit 1}',
          'if {[lsort [$b getObstructions]] ne $original_obs} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'source '+tcl(DRIVER/'export_access.tcl'),'close $stages']
        script=out/'route.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncodes']['edit_selected_route_export']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=8);save()
        if (out/'moved.pins.tsv').exists():
            # Validate the actual edit before post-route checks, even on failure.
            import shutil
            if not (out/'after.pins.tsv').exists():
                shutil.copyfile(str(out/'moved.pins.tsv'),str(out/'edit_only.pins.tsv'))
                rec['edit_only_pin_inventory_saved_not_route_success']=True
        assert rec['native_returncodes']['edit_selected_route_export']==0
        rec['complete_pin_contract']=pin_contract(out,targets,13507)
        rec['all_original_functional_cells_connections_PG_die_preserved']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']};assert all(rec['all_original_functional_cells_connections_PG_die_preserved'].values())
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        a,_=routing_box_hashes(geo,725253);b,_=routing_box_hashes(out/'whole_access.tsv.gz',725253)
        changed=[n for n in a if a[n]!=b[n]];rec['actually_changed_route_networks']=changed;rec['unselected_route_geometry_preserved']=all(n in extra for n in changed);assert rec['unselected_route_geometry_preserved']
        script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'fresh.log',threads=1)
        if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        lines=[helper]+['read_liberty '+tcl(p) for p in old['libs']]+['read_db '+tcl(out/'routed.odb'),'read_sdc '+tcl(sdc),
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']
        script=out/'RC_STA.tcl';script.write_text('\n'.join(lines).replace('$out/stages.tsv','$out/RC_STA_stages.tsv')+'\n')
        rec['native_returncodes']['RC_STA']=execute(common,script,out/'RC_STA.log','PINXY_OUTPUT='+str(out),threads=8)
        for kind in ['setup','hold']:
            p=out/(kind+'.txt')
            if p.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',p.read_text())[1])
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['native_stages']={p.name:{r['stage']:r['status'] for r in csv.DictReader(p.open(),delimiter='\t')} for p in out.glob('*stages.tsv')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or rec.get('fresh_DRC_count')!=0 or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
