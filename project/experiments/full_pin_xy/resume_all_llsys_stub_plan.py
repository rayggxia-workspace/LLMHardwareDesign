"""Reuse closed all-port plan; prove and retain single-terminal declarations.

The previous actual edit stopped on a net without dbWire. Do not invent a
logical peer or delete that port. Native inventory first; retain those original
pins, check every new conductor/first-hop against their actual metal, then
perform real native edits and independent complete checks. No repeated search.
"""
from pathlib import Path
from collections import Counter,defaultdict
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_llsys_actual_tips import pin_contract
from compare_native_route_representations import routing_box_hashes
from check_access import check
DRIVER=Path(__file__).resolve().parent

def run(revision,plan_revision='r02'):
    prior=ROOT/'all_llsys_access_stubs'/plan_revision;pp=prior/'execution.json';p=json.loads(pp.read_text())
    assert p.get('completed_utc') and p['all_closed_sources_unchanged']
    assert p['native_returncodes'].get('actual_stub_edit')==1 and 'Original routed conductor missing' in (prior/'actual_stub_edit.log').read_text()
    plan=prior/'all13507_source_bound_access_stub_plan.json';template=prior/'actual_stub_edit.tcl'
    for f in [plan,template]:assert sha(f)==p['files'][f.name]['sha256']
    source=ROOT/'llsys_wire_pin_retention/r01';sp=source/'execution.json';s=json.loads(sp.read_text());odb=source/'routed.odb';geo=source/'whole_access.tsv.gz'
    assert s.get('completed_utc') and s['fresh_DRC_count']==0 and s['whole_signal_geometry']['pass'] and s['all_closed_sources_unchanged']
    for f in [odb,geo]:assert sha(f)==s['files'][f.name]['sha256']==p['source_SHA'][str(f)]
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    inputs={str(f):sha(f) for f in [pp,plan,template,sp,odb,geo,trial,sdc]};out=ROOT/'all_llsys_access_stubs'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_ALL_PORT_STUB_PLAN_RESUMPTION_WITH_NATIVE_SINGLETON_ROLE_PROOF_NOT_FULL_SYSTEM',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'source_SHA':inputs,
      'full_qualification':False,'original_signal_pins':13507,'source_plan_reused_without_repeated_geometry_search':str(prior),
      'native_returncodes':{},'original_allowed_layers':'signal M2-M8; clock M4-M8','original_clock_and_loads':'UNCHANGED',
      'new_functional_cells_or_sizes':0,'future_first_hop_vias':'NOT_INSTALLED_IN_LEAF','original_full_parent_or_leaf_AP_failures':'RETAINED_NOT_DELETED_OR_WAIVED'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    for prefix in ['/public/home/yuzelu/project-circuit','/public/home/yuzelu/PingyangHuang/issue-55']:common+=['--bind',prefix+':'+prefix+':ro']
    for lib in old['libs']:
        if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
    def native(label,body,threads=8):
        script=out/(label+'.tcl');script.write_text(helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')+'\n'+body+'\n')
        rc=execute(common,script,out/(label+'.log'),'PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=threads);rec['native_returncodes'][label]=rc;save();return rc
    try:
        body=r'''
set b [ord::get_db_block];set f [open INVENTORY w];puts $f "pin\tnet\tdirection\tuse\titerms\tbterms\tordinary_wire\tlayer\tx0\ty0\tx1\ty1"
foreach bt [$b getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} {continue}
 set n [$bt getNet];set boxes {};foreach bp [$bt getBPins] {foreach z [$bp getBoxes] {lappend boxes $z}};if {[llength $boxes]!=1} {error "Original signal is not one rectangle"};set z [lindex $boxes 0]
 puts $f [join [list [$bt getName] [$n getName] [$bt getIoType] [$bt getSigType] [llength [$n getITerms]] [llength [$n getBTerms]] [expr {[$n getWire] ne "NULL"}] [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\t"]
};close $f
'''
        assert native('original_all13507_native_roles','read_db '+tcl(odb)+'\n'+body.replace('INVENTORY',tcl(out/'all13507_original_native_roles.tsv'))+'\nclose $stages',threads=1)==0
        roles={r['pin']:r for r in csv.DictReader((out/'all13507_original_native_roles.tsv').open(),delimiter='\t')};assert len(roles)==13507
        ports=json.loads(plan.read_text());assert len(ports)==13507 and set(roles)=={r['pin'] for r in ports}
        singleton={name:r for name,r in roles.items() if r['ordinary_wire']=='0' and r['iterms']=='0' and r['bterms']=='1'}
        for name,r in roles.items():
            if r['ordinary_wire']=='0':assert name in singleton,('Unrouted port has a real peer; cannot waive it',name,r)
        rec['native_proven_single_terminal_without_internal_peer_or_wire']=len(singleton)
        rec['singleton_semantics']='Native current-netlist role only; no fabricated RTL unused/constant semantics. Preserve original declaration, function/direction/net/layer/size and XY.'
        via=json.loads((ROOT/'all_llsys_first_hop_audit/r01/execution.json').read_text())['actual_via_templates']
        tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';inputs[str(tech)]=sha(tech);rules={};text=tech.read_text()
        for layer in ['metal5','metal6']:
            block=re.search(r'^LAYER '+layer+r'\s.*?^END '+layer,text,re.M|re.S)[0];tab=re.search(r'SPACINGTABLE\s+PARALLELRUNLENGTH(.*?);',block,re.S)[1].splitlines();prls=[round(float(x)*2000) for x in tab[0].split()];rows=[]
            for line in tab[1:]:
                z=line.split()
                if z and z[0]=='WIDTH':rows.append((round(float(z[1])*2000),[round(float(x)*2000) for x in z[2:]]))
            rules[layer]=(prls,rows)
        def collision(layer,z,other):
            if layer!=other['layer']:return False
            b=tuple(int(other[k]) for k in ['x0','y0','x1','y1']);dx=max(z[0]-b[2],b[0]-z[2],0);dy=max(z[1]-b[3],b[1]-z[3],0)
            if dx>10000 or dy>10000:return False
            width=max(min(z[2]-z[0],z[3]-z[1]),min(b[2]-b[0],b[3]-b[1]));prl=max(0,min(z[3],b[3])-max(z[1],b[1])) if dx and not dy else max(0,min(z[2],b[2])-max(z[0],b[0])) if dy and not dx else 0
            ps,rs=rules[layer];col=max(i for i,v in enumerate(ps) if v<=prl);need=max((r for r in rs if r[0]<=width),key=lambda r:r[0])[1][col]
            return dx*dx+dy*dy<need*need
        extras=defaultdict(list);selected=[];counts=Counter();new_singleton_conflicts=[]
        die=[0,0,4200010,4200000]  # Replaced below by source-bound native die.
        die=list(map(int,(source/'after.die.tsv').read_text().split()));assert sha(source/'after.die.tsv')==s['files']['after.die.tsv']['sha256'];inputs[str(source/'after.die.tsv')]=sha(source/'after.die.tsv')
        for r in ports:
            original=roles[r['pin']];assert original['net']==r['net'] and original['layer']==r['original_layer'] and [int(original[k]) for k in ['x0','y0','x1','y1']]==r['box_DBU']
            if r['pin'] in singleton:
                r.update(target_center_DBU=r['center_DBU'],stub_path_DBU=[],stub_L1_um=0,status='KEEP_NATIVE_SINGLETERM_NO_INTERNAL_PEER_OR_WIRE_ORIGINAL_XY')
            cx,cy=r['center_DBU'];x,y=r['target_center_DBU'];assert die[0]+140<=x<=die[2]-140 and die[1]+140<=y<=die[3]-140
            if (x,y)!=(cx,cy):
                if r['access_method']=='OWN_EXISTING_METAL_EXACT_OLD_PIN_RETENTION':new=[(r['original_layer'],tuple(r['box_DBU']))]
                else:new=[(r['original_layer'],(min(a[0],b[0])-140,min(a[1],b[1])-140,max(a[0],b[0])+140,max(a[1],b[1])+140)) for a,b in zip(r['stub_path_DBU'],r['stub_path_DBU'][1:])]
                first=[(ly,(x+z[0],y+z[1],x+z[2],y+z[3])) for ly,z in via[r['first_hop']].items() if ly in rules]
                blockers=[o['pin'] for o in singleton.values() if o['net']!=r['net'] and any(collision(ly,z,o) for ly,z in new+first)]
                if blockers:
                    new_singleton_conflicts.append({'pin':r['pin'],'actual_original_singleton_blockers':blockers});r.update(target_center_DBU=r['center_DBU'],stub_path_DBU=[],stub_L1_um=0,status='KEEP_ORIGINAL_XY_ACTUAL_SINGLETON_METAL_BLOCKS_PLANNED_ACCESS')
                else:
                    selected.append(r)
                    for ly,z in new:extras[r['net']].append(('WIRE',ly)+z)
            counts[r['status']]+=1
        rec.update(all13507_status_counts=dict(counts),actual_requested_XY_and_stub_count=len(selected),actual_singleton_metal_additional_blocked_plans=new_singleton_conflicts,
          first_hop_footprints_not_installed_in_leaf=True)
        (out/'all13507_source_bound_access_stub_plan.json').write_text(json.dumps(ports,indent=2)+'\n')
        specs='set stub_specs {\n'+''.join('{'+tcl(r['pin'])+' '+tcl(r['net'])+' '+r['original_layer']+' {'+' '.join('{'+str(x)+' '+str(y)+'}' for x,y in r['stub_path_DBU'])+'} '+' '.join(map(str,r['target_center_DBU']))+' '+r['access_method']+' {'+' '.join(map(str,r['box_DBU']))+'}}\n' for r in selected)+'}\n'
        (out/'actual_stub_specs.tcl').write_text(specs);save()
        # Reuse the measured implementation body, changing only private output
        # and corrected spec paths. No historical source or driver is edited.
        script=out/'actual_stub_edit.tcl';body=template.read_text().replace(str(prior),str(out));assert str(prior) not in body;script.write_text(body)
        rc=execute(common,script,out/'actual_stub_edit.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=8);rec['native_returncodes']['actual_stub_edit']=rc;save();assert rc==0
        targets={r['pin']:(r['original_layer'],[r['target_center_DBU'][0]-140,r['target_center_DBU'][1]-140,r['target_center_DBU'][0]+140,r['target_center_DBU'][1]+140]) for r in selected}
        rec['complete_pin_contract']=pin_contract(out,targets,13507)
        rec['all_cells_connections_PG_die_preserved']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']};assert all(rec['all_cells_connections_PG_die_preserved'].values())
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        a,ac=routing_box_hashes(geo,725253,extras);b,bc=routing_box_hashes(out/'whole_access.tsv.gz',725253);rec['all_original_WIRE_VIA_plus_exact_added_stub_rectangles']=a==b and ac==bc;assert a==b and ac==bc
        routing='set_routing_layers -signal metal2-metal8 -clock metal4-metal8'
        native('fresh_DRC','read_db '+tcl(out/'routed.odb')+'\n'+routing+'\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\nclose $stages',threads=1)
        if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        native('native_all_pin_access','read_db '+tcl(out/'routed.odb')+'\n'+routing+'\nstage all_signal_native_pin_access {pin_access}\nclose $stages')
        libs=['read_liberty '+tcl(lib) for lib in old['libs']]
        native('RC_STA','\n'.join(libs+['read_db '+tcl(out/'routed.odb'),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']))
        for kind in ['setup','hold']:
            f=out/(kind+'.txt')
            if f.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',f.read_text())[1])
        rec['actual_added_stub_L1_um']=sum(r['stub_L1_um'] for r in selected);rec['not_block_area_saving']=True
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['native_stages']={f.name:{r['stage']:r['status'] for r in csv.DictReader(f.open(),delimiter='\t')} for f in out.glob('*stages.tsv')}
    rec['all_closed_sources_unchanged']=all(sha(Path(f))==v for f,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.iterdir() if f.is_file() and f.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or rec.get('fresh_DRC_count')!=0 or rec['native_stages'].get('native_all_pin_access.stages.tsv',{}).get('all_signal_native_pin_access')!='EXECUTED' or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(*sys.argv[1:]))
