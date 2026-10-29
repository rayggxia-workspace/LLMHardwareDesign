"""Actual all-port access engineering: real preferred-layer stubs and pin XY.

Use the full native signal metal + PG/OBS, measured via5/6, actual track grids.
Reserve future first-hop footprints geometrically, but install only real leaf
M5/M6 stubs and original-sized pins. Independent native DRC, all-pin AP,
geometry, unchanged graph, RC/STA remain separate gates. No failure omitted.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,datetime,gzip,json,math,os,re,sqlite3,sys,traceback
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
    odb=source/'routed.odb';geo=source/'whole_access.tsv.gz';pins=source/'after.pins.tsv'
    for p in [odb,geo,pins]:assert sha(p)==q['files'][p.name]['sha256']
    audit=ROOT/'all_llsys_first_hop_audit/r01';ap=audit/'execution.json';a=json.loads(ap.read_text());assert a.get('completed_utc') and a['all_closed_sources_unchanged'] and a['source_SHA'][str(odb)]==sha(odb)
    table=audit/'all13507_actual_first_hop_risks.json';assert sha(table)==a['files'][table.name]['sha256']
    native=ROOT/'llsys_residual_access_preflight/r01';n=json.loads((native/'execution.json').read_text());assert n.get('completed_utc') and n['native_readonly_returncode']==0 and n['source_SHA'][str(odb)]==sha(odb)
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';model=json.loads((tech.parent/'model.json').read_text());assert model['original_M1_M10_and_via1_via9_layer_blocks_identical'] and sha(tech)==model['files'][tech.name]['sha256']
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    original=[rp,odb,geo,pins,ap,table,native/'execution.json',native/'actual_first_hop_vias.tsv',native/'actual_high_PG_OBS.tsv',native/'actual_die.tsv',tech,trial,sdc]
    for p in original:
        if p.parent==native and p.name!='execution.json':assert sha(p)==n['files'][p.name]['sha256']
    inputs={str(p):sha(p) for p in original};out=ROOT/'all_llsys_access_stubs'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ALL13507_CURRENT_PORT_REAL_M5_M6_STUB_AND_XY_ENGINEERING_NOT_FULL_SYSTEM_QUALIFICATION',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'source_SHA':inputs,
      'full_qualification':False,'original_signal_pins':13507,'all_original_port_layers_sizes_functions_directions_networks_constants_and_targets':'MUST_REMAIN_UNCHANGED',
      'new_functional_cells_sizing_or_protocol_changes':0,'original_allowed_layers':'signal M2-M8; clock M4-M8',
      'native_returncodes':{},'maximum_new_stub_L1_um':10.,'future_first_hop_vias':'PRESCREENED_FOOTPRINTS_NOT_INSTALLED_IN_LEAF',
      'not_checked_in_planner':['Full end-of-line/min-step/enclosure interactions','Entire access stack','Parent macro OBS ownership','Native all-pin AP','RC/STA and complete applicable GDS rules'],
      'original_clock_and_external_loads':'UNCHANGED','stubs_are_real_wires_not_LEF_or_plot_edits':True}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    for lib in old['libs']:
        if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    def run_native(label,body,threads=8):
        script=out/(label+'.tcl');script.write_text(helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')+'\n'+body+'\n')
        rc=execute(common,script,out/(label+'.log'),'PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=threads)
        rec['native_returncodes'][label]=rc;save();return rc
    try:
        ports=json.loads(table.read_text());assert len(ports)==13507 and len({p['pin'] for p in ports})==13507
        vias=a['actual_via_templates'];text=tech.read_text();rules={};maxgrow={};layers={'metal5':5,'metal6':6,'metal7':7,'via5':15,'via6':16}
        for layer in layers:
            block=re.search(r'^LAYER '+layer+r'\s.*?^END '+layer,text,re.M|re.S)[0]
            if layer.startswith('via'):rules[layer]=round(float(re.search(r'\bSPACING\s+([\d.]+)',block)[1])*2000);maxgrow[layer]=rules[layer];continue
            tablelines=re.search(r'SPACINGTABLE\s+PARALLELRUNLENGTH(.*?);',block,re.S)[1].splitlines();prls=[round(float(x)*2000) for x in tablelines[0].split()];rows=[]
            for line in tablelines[1:]:
                p=line.split()
                if p and p[0]=='WIDTH':rows.append((round(float(p[1])*2000),[round(float(x)*2000) for x in p[2:]]))
            assert rows and all(len(v)==len(prls) for w,v in rows);rules[layer]=(prls,rows);maxgrow[layer]=max(max(v) for w,v in rows)
        def spacing(layer,z,b):
            if layer.startswith('via'):return rules[layer]
            width=max(min(z[2]-z[0],z[3]-z[1]),min(b[2]-b[0],b[3]-b[1]));dx=max(z[0]-b[2],b[0]-z[2],0);dy=max(z[1]-b[3],b[1]-z[3],0)
            prl=max(0,min(z[3],b[3])-max(z[1],b[1])) if dx and not dy else max(0,min(z[2],b[2])-max(z[0],b[0])) if dy and not dx else 0
            ps,rs=rules[layer];col=max(i for i,v in enumerate(ps) if v<=prl);return max((r for r in rs if r[0]<=width),key=lambda r:r[0])[1][col]
        db=sqlite3.connect(':memory:');db.execute('CREATE VIRTUAL TABLE shapes USING rtree(id,x0,x1,y0,y1,l0,l1)');metadata=[None]
        def add(net,kind,layer,z):
            idx=len(metadata);metadata.append((sys.intern(net),sys.intern(kind)));level=layers[layer];db.execute('INSERT INTO shapes VALUES (?,?,?,?,?,?,?)',(idx,z[0],z[2],z[1],z[3],level,level))
        def consume(reader):
            for r in reader:
                if r['layer'] not in layers or r['kind']=='UNROUTED':continue
                add(r['net'],r['kind'],r['layer'],tuple(int(r[k]) for k in ['x0','y0','x1','y1']))
        with gzip.open(str(geo),'rt') as f:consume(csv.DictReader(f,delimiter='\t'))
        with (native/'actual_high_PG_OBS.tsv').open() as f:consume(csv.DictReader(f,delimiter='\t'))
        db.commit();rec['actual_high_geometry_rows_indexed']=len(metadata)-1;save();print('ACTUAL_METAL_INDEX_COMPLETE',len(metadata)-1,flush=True)
        def clear(net,layer,z):
            margin=maxgrow[layer];level=layers[layer]
            found=db.execute('SELECT id,x0,y0,x1,y1 FROM shapes WHERE x0<=? AND x1>=? AND y0<=? AND y1>=? AND l0<=? AND l1>=?',(z[2]+margin,z[0]-margin,z[3]+margin,z[1]-margin,level,level))
            for idx,x0,y0,x1,y1 in found:
                owner,kind=metadata[idx];b=tuple(round(v) for v in [x0,y0,x1,y1])
                if owner==net and not layer.startswith('via'):continue
                if owner==net and layer.startswith('via') and b==z:continue
                dx=max(z[0]-b[2],b[0]-z[2],0);dy=max(z[1]-b[3],b[1]-z[3],0);need=spacing(layer,z,b)
                if dx*dx+dy*dy<need*need:return False
            return True
        die=list(map(int,(native/'actual_die.tsv').read_text().split()));occupied=set();selected=[];counts=Counter();expected_extra=defaultdict(list)
        def proposal(r,x,y):
            cx,cy=r['center_DBU'];ly=r['original_layer'];path=[(cx,cy)]
            middle=(x,cy) if ly=='metal5' else (cx,y)
            if middle!=path[-1]:path.append(middle)
            if (x,y)!=path[-1]:path.append((x,y))
            stubs=[]
            for p,t in zip(path,path[1:]):stubs.append((ly,(min(p[0],t[0])-140,min(p[1],t[1])-140,max(p[0],t[0])+140,max(p[1],t[1])+140)))
            first=[(layer,(x+z[0],y+z[1],x+z[2],y+z[3])) for layer,z in vias[r['first_hop']].items()]
            return path,stubs,first
        # Existing clear/track-aligned ports get the first chance to keep XY.
        order=sorted(ports,key=lambda r:(bool(r['foreign_or_cut_spacing_risks']) or not(r['on_M6_X_grid'] and r['on_first_hop_Y_grid']),r['pin']))
        for number,r in enumerate(order):
            cx,cy=r['center_DBU'];ly=r['original_layer'];yp=560 if ly=='metal5' else 1600
            xs=range(math.floor((cx-190-20000)/560),math.ceil((cx-190+20000)/560)+1) if ly=='metal5' else range(round((cx-190)/560)-1,round((cx-190)/560)+2)
            ys=range(round((cy-140)/yp)-1,round((cy-140)/yp)+2) if ly=='metal5' else range(math.floor((cy-140-20000)/yp),math.ceil((cy-140+20000)/yp)+1)
            candidates=sorted((abs(x-cx)+abs(y-cy),int((y!=cy) if ly=='metal5' else (x!=cx)),x,y) for x in (190+ix*560 for ix in xs) for y in (140+iy*yp for iy in ys) if abs(x-cx)+abs(y-cy)<=20000)
            chosen=None
            for distance,perp,x,y in candidates:
                if (ly,x,y) in occupied or not(die[0]+140<=x<=die[2]-140 and die[1]+140<=y<=die[3]-140):continue
                path,stubs,first=proposal(r,x,y)
                if all(clear(r['net'],layer,z) for layer,z in stubs+first):chosen=(distance,x,y,path,stubs,first);break
            row=dict(r)
            if chosen:
                distance,x,y,path,stubs,first=chosen;row.update(target_center_DBU=[x,y],stub_path_DBU=path,stub_L1_um=distance/2000.,status='REAL_STUB_AND_XY_NATIVE_IMPLEMENTATION_REQUIRED' if distance else 'KEEP_ACTUAL_XY_FIRST_HOP_PRESCREEN_CLEAR_NOT_AP_PASS')
                occupied.add((ly,x,y))
                for layer,z in first:add(r['net'],'VIRTUAL_FUTURE_FIRST_HOP_NOT_INSTALLED',layer,z)
                for layer,z in stubs:add(r['net'],'NEW_STUB_TO_BE_IMPLEMENTED',layer,z);expected_extra[r['net']].append(('WIRE',layer)+z)
                if distance:selected.append(row)
            else:row.update(target_center_DBU=[cx,cy],stub_path_DBU=[[cx,cy]],stub_L1_um=0,status='KEEP_NO_SCREENED_STUB_WITHIN10UM_ORIGINAL_ACCESS_RISK_REMAINS');occupied.add((ly,cx,cy))
            r.update(row);counts[row['status']]+=1
            if number%500==0:print('FULL_PORT_ACCESS_STUB_PROGRESS',number,dict(counts),flush=True)
        db.close();rec['all13507_status_counts']=dict(counts);rec['actual_requested_XY_and_stub_count']=len(selected);rec['first_hop_footprints_not_installed_in_leaf']=True
        (out/'all13507_source_bound_access_stub_plan.json').write_text(json.dumps(ports,indent=2)+'\n');save()
        specs='set stub_specs {\n'+''.join('{'+tcl(r['pin'])+' '+tcl(r['net'])+' '+r['original_layer']+' {'+' '.join('{'+str(x)+' '+str(y)+'}' for x,y in r['stub_path_DBU'])+'}}\n' for r in selected)+'}\n'
        (out/'actual_stub_specs.tcl').write_text(specs)
        libs=['read_liberty '+tcl(p) for p in old['libs']]
        edit='\n'.join(libs+['read_db '+tcl(odb),'fingerprint '+tcl(out/'before'),'set b [ord::get_db_block];set tech [ord::get_db_tech];set original_obs [lsort [$b getObstructions]]','source '+tcl(out/'actual_stub_specs.tcl')])+r'''
if {![stage actual_all_selected_stubs_and_original_layer_pins {
 foreach spec $stub_specs {
  lassign $spec pin net layer points;set bt [$b findBTerm $pin]
  if {$bt eq "NULL" || [[$bt getNet] getName] ne $net} {error "Original bit peer changed"}
  set n [$bt getNet];set wire [$n getWire];if {$wire eq "NULL"} {error "Original routed conductor missing"}
  if {[$b findNet HPY_ACTUAL_ACCESS_STUB_STAGING] ne "NULL"} {error "Staging collision"}
  set temp [odb::dbNet_create $b HPY_ACTUAL_ACCESS_STUB_STAGING];set tw [odb::dbWire_create $temp];set enc [odb::dbWireEncoder]
  $enc begin $tw;$enc newPath [$tech findLayer $layer] ROUTED
  foreach point $points {lassign $point x y;$enc addPoint $x $y};$enc end;$wire append $tw;odb::dbNet_destroy $temp
  lassign [lindex $points end] x y;place_pin -pin_name $pin -layer $layer -location [list [expr {$x/2000.}] [expr {$y/2000.}]] -pin_size {.14 .14}
 }
}]} {close $stages;exit 1}
if {[lsort [$b getObstructions]] ne $original_obs} {error "Original block OBS changed"}
'''
        edit+='\n'+'\n'.join(['fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}','stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'source '+tcl(DRIVER/'export_access.tcl'),'close $stages'])
        assert run_native('actual_stub_edit',edit)==0
        targets={r['pin']:(r['original_layer'],[r['target_center_DBU'][0]-140,r['target_center_DBU'][1]-140,r['target_center_DBU'][0]+140,r['target_center_DBU'][1]+140]) for r in selected}
        rec['complete_pin_contract']=pin_contract(out,targets,13507)
        rec['all_cells_connections_PG_die_preserved']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']};assert all(rec['all_cells_connections_PG_die_preserved'].values())
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        before,total=routing_box_hashes(geo,725253,expected_extra);after,actual_total=routing_box_hashes(out/'whole_access.tsv.gz',725253)
        rec['all_original_WIRE_VIA_plus_exact_added_stub_rectangles']=before==after and total==actual_total;assert rec['all_original_WIRE_VIA_plus_exact_added_stub_rectangles']
        routing='set_routing_layers -signal metal2-metal8 -clock metal4-metal8'
        run_native('fresh_DRC','read_db '+tcl(out/'routed.odb')+'\n'+routing+'\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\nclose $stages',threads=1)
        if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        # Run all-pin native AP even if fresh DRC fails; retain both outcomes.
        run_native('native_all_pin_access','read_db '+tcl(out/'routed.odb')+'\n'+routing+'\nhelp pin_access\nif {![llength [info commands pin_access]]} {error "Native pin_access command unavailable"}\nstage all_signal_native_pin_access {pin_access}\nclose $stages')
        lines=libs+['read_db '+tcl(out/'routed.odb'),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']
        run_native('RC_STA','\n'.join(lines))
        for kind in ['setup','hold']:
            p=out/(kind+'.txt')
            if p.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',p.read_text())[1])
        rec['actual_added_stub_L1_um']=sum(r['stub_L1_um'] for r in selected);rec['not_block_area_saving']=True
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['native_stages']={p.name:{r['stage']:r['status'] for r in csv.DictReader(p.open(),delimiter='\t')} for p in out.glob('*stages.tsv')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or rec.get('fresh_DRC_count')!=0 or rec['native_stages'].get('native_all_pin_access.stages.tsv',{}).get('all_signal_native_pin_access')!='EXECUTED' or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
