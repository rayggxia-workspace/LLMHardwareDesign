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

def run(revision,profile='original'):
    assert profile in ['original','parent_owned_only']
    source=ROOT/('parent1016_actual_m5_repair/r01' if profile=='parent_owned_only' else 'llsys_wire_pin_retention/r01');rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['all_closed_sources_unchanged']
    geometry_source=source
    if profile=='parent_owned_only':
        assert q['fresh_leaf_DRC_count']==0 and q['native_DEF_NETS_byte_identical'] and q['actual_target_WIRE_VIA_exact'] and q['actual_changed_net_geometry']['pass']
        assert not q['parent_AP_stage_executed'] and any('bit_1071' in x for x in q['parent_AP_errors'])
        geometry_source=ROOT/'llsys_corner_fill/r01'
    else:assert q['fresh_DRC_count']==0 and q['whole_signal_geometry']['pass']
    gq=json.loads((geometry_source/'execution.json').read_text());assert gq.get('completed_utc') and gq['all_closed_sources_unchanged']
    odb=source/'routed.odb';geo=geometry_source/'whole_access.tsv.gz';pins=source/'after.pins.tsv'
    for p in [odb,pins]:assert sha(p)==q['files'][p.name]['sha256']
    assert sha(geo)==gq['files'][geo.name]['sha256']
    audit=ROOT/'all_llsys_first_hop_audit/r01';ap=audit/'execution.json';a=json.loads(ap.read_text());assert a.get('completed_utc') and a['all_closed_sources_unchanged']
    if profile=='original':assert a['source_SHA'][str(odb)]==sha(odb)
    table=audit/'all13507_actual_first_hop_risks.json';assert sha(table)==a['files'][table.name]['sha256']
    native=ROOT/'llsys_residual_access_preflight/r01';n=json.loads((native/'execution.json').read_text());assert n.get('completed_utc') and n['native_readonly_returncode']==0
    if profile=='original':assert n['source_SHA'][str(odb)]==sha(odb)
    else:
        oldleaf=ROOT/'llsys_wire_pin_retention/r01';oldq=json.loads((oldleaf/'execution.json').read_text())
        assert n['source_SHA'][str(oldleaf/'routed.odb')]==oldq['files']['routed.odb']['sha256']
        assert all(sha(source/('after.'+k+'.tsv'))==sha(oldleaf/('after.'+k+'.tsv')) for k in ['cells','pdn','die'])
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';model=json.loads((tech.parent/'model.json').read_text());assert model['original_M1_M10_and_via1_via9_layer_blocks_identical'] and sha(tech)==model['files'][tech.name]['sha256']
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    original=[rp,odb,geo,pins,ap,table,native/'execution.json',native/'actual_first_hop_vias.tsv',native/'actual_high_PG_OBS.tsv',native/'actual_die.tsv',tech,trial,sdc]
    for p in original:
        if p.parent==native and p.name!='execution.json':assert sha(p)==n['files'][p.name]['sha256']
    inputs={str(p):sha(p) for p in original};out=ROOT/'all_llsys_access_stubs'/revision;out.mkdir(parents=True,exist_ok=False)
    parent_pg=None
    if revision!='r01':
        parent=ROOT/'parent_pg_llsys_local/r01';pr=json.loads((parent/'execution.json').read_text());parent_pg=parent/'actual_parent_PG_local.tsv'
        assert pr.get('completed_utc') and pr['native_readonly_returncode']==0 and pr['all_closed_sources_unchanged'] and sha(parent_pg)==pr['files'][parent_pg.name]['sha256']
        inputs.update({str(p):sha(p) for p in [parent/'execution.json',parent_pg]})
    rec={'scope':'ALL13507_CURRENT_PORT_REAL_M5_M6_STUB_AND_XY_ENGINEERING_NOT_FULL_SYSTEM_QUALIFICATION',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'source_SHA':inputs,
      'full_qualification':False,'original_signal_pins':13507,'all_original_port_layers_sizes_functions_directions_networks_constants_and_targets':'MUST_REMAIN_UNCHANGED',
      'new_functional_cells_sizing_or_protocol_changes':0,'original_allowed_layers':'signal M2-M8; clock M4-M8',
      'native_returncodes':{},'maximum_new_stub_L1_um':10.,'future_first_hop_vias':'PRESCREENED_FOOTPRINTS_NOT_INSTALLED_IN_LEAF',
      'not_checked_in_planner':['Full end-of-line/min-step/enclosure interactions','Entire access stack','Parent macro OBS ownership','Native all-pin AP','RC/STA and complete applicable GDS rules'],
      'original_clock_and_external_loads':'UNCHANGED','stubs_are_real_wires_not_LEF_or_plot_edits':True}
    rec['profile']=profile
    if profile=='parent_owned_only':
        rec.update(scope='ALL13507_ACTUAL_WIRE_SUPPORTED_XY_WITH_STRICT_EXPORTED_UPPER_OBS_AND_FRESH_PARENT_AP_NOT_SYSTEM_QUALIFICATION',
                   maximum_new_stub_L1_um=0.,new_WIRE_or_VIA_objects_requested=0,
                   geometry_reference='Actual1bd4aa52 WIRE/VIA/ITerm geometry; current native DEF NETS byte identity proved, all BTerm locations refreshed',
                   first_hop_policy='Controlled parent upward via5/via6 access; historical targets remain partial/unknown')
        inputs[str(geometry_source/'execution.json')]=sha(geometry_source/'execution.json')
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
        if profile=='parent_owned_only':
            current={}
            for line in pins.open():
                z=line.split()
                if len(z)==9 and z[2] not in ['POWER','GROUND']:current[z[0].strip('{}')]=z
            assert len(current)==13507
            for p in ports:
                z=current[p['pin']];assert p['net']==z[3].strip('{}') and p['original_layer']==z[4]
                b=list(map(int,z[5:9]));x=(b[0]+b[2])//2;y=(b[1]+b[3])//2
                p.update(box_DBU=b,center_DBU=[x,y],direction=z[1],actual_use=z[2],historical_c494_foreign_risks=p.pop('foreign_or_cut_spacing_risks'),foreign_or_cut_spacing_risks=None,
                         on_M6_X_grid=(x-190)%560==0,on_first_hop_Y_grid=(y-140)%(560 if z[4]=='metal5' else 1600)==0)
        port_layers=defaultdict(set)
        for p in ports:port_layers[p['net']].add(p['original_layer'])
        own_metal=defaultdict(list)
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
                if profile=='parent_owned_only' and r['kind']=='BTERM':continue
                z=tuple(int(r[k]) for k in ['x0','y0','x1','y1']);add(r['net'],r['kind'],r['layer'],z)
                if r['layer'] in port_layers.get(r['net'],()) and r['kind'] in ['WIRE','VIA']:own_metal[r['net'],r['layer']].append((z,r['kind']))
        with gzip.open(str(geo),'rt') as f:consume(csv.DictReader(f,delimiter='\t'))
        with (native/'actual_high_PG_OBS.tsv').open() as f:consume(csv.DictReader(f,delimiter='\t'))
        if parent_pg:
            with parent_pg.open() as f:consume(csv.DictReader(f,delimiter='\t'))
            rec['actual_common_parent_PG_included_with_native_R0_transform']=True
        if profile=='parent_owned_only':
            parent=ROOT/'common_checkpoint_def_import/corner-r01';oldparent=ROOT/'common_checkpoint_def_import/r01'
            assert all(sha(parent/('after.'+k+'.tsv'))==sha(oldparent/('after.'+k+'.tsv')) for k in ['pdn','instances'])
            for p in ports:add(p['net'],'ACTUAL_CURRENT_BPIN',p['original_layer'],tuple(p['box_DBU']))
            obsfile=source/'parent.lef';assert sha(obsfile)==q['files'][obsfile.name]['sha256'];inputs[str(obsfile)]=sha(obsfile)
            inside=False;ly=None;obs_count=0
            for line in obsfile.open():
                z=line.split()
                if z==['OBS']:inside=True
                elif inside and z and z[0]=='LAYER':ly=z[1]
                elif inside and z and z[0]=='RECT' and ly in ['metal6','metal7']:
                    box=tuple(round(float(v)*2000) for v in z[1:5]);add('__EXPORTED_PARENT_OBS__','PARENT_ABSTRACT_OBS',ly,box);obs_count+=1
                elif inside and z==['END']:inside=False
            rec['actual_exported_upper_parent_OBS_indexed']=obs_count
        db.commit();rec['actual_high_geometry_rows_indexed']=len(metadata)-1;save();print('ACTUAL_METAL_INDEX_COMPLETE',len(metadata)-1,flush=True)
        def clear(net,layer,z,contact_layer=None):
            margin=maxgrow[layer];level=layers[layer]
            found=db.execute('SELECT id,x0,y0,x1,y1 FROM shapes WHERE x0<=? AND x1>=? AND y0<=? AND y1>=? AND l0<=? AND l1>=?',(z[2]+margin,z[0]-margin,z[3]+margin,z[1]-margin,level,level))
            for idx,x0,y0,x1,y1 in found:
                owner,kind=metadata[idx];b=tuple(round(v) for v in [x0,y0,x1,y1])
                if profile=='parent_owned_only' and kind=='PARENT_ABSTRACT_OBS' and layer==contact_layer:continue
                if owner==net and not layer.startswith('via') and (profile=='original' or layer==contact_layer):continue
                if owner==net and layer.startswith('via') and b==z:continue
                dx=max(z[0]-b[2],b[0]-z[2],0);dy=max(z[1]-b[3],b[1]-z[3],0);need=spacing(layer,z,b)
                if dx*dx+dy*dy<need*need:return False
            return True
        die=list(map(int,(native/'actual_die.tsv').read_text().split()));occupied=set();selected=[];counts=Counter();expected_extra=defaultdict(list)
        if profile=='parent_owned_only':
            occupied={(p['original_layer'],p['center_DBU'][0],p['center_DBU'][1]) for p in ports};assert len(occupied)==13507
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
        order=sorted(ports,key=(lambda r:(r['pin']!='bit_2' and r.get('actual_use')!='CLOCK',r['pin'])) if profile=='parent_owned_only' else (lambda r:(bool(r['foreign_or_cut_spacing_risks']) or not(r['on_M6_X_grid'] and r['on_first_hop_Y_grid']),r['pin'])))
        for number,r in enumerate(order):
            cx,cy=r['center_DBU'];ly=r['original_layer'];yp=560 if ly=='metal5' else 1600
            if profile=='parent_owned_only':
                occupied.remove((ly,cx,cy));source_pin_box=r['box_DBU']
                covered=any(b[0]<=source_pin_box[0] and b[1]<=source_pin_box[1] and b[2]>=source_pin_box[2] and b[3]>=source_pin_box[3] for b,kind in own_metal[r['net'],ly])
                if not covered or r['pin']=='bit_2' or r.get('actual_use')=='CLOCK':
                    r.update(target_center_DBU=[cx,cy],stub_path_DBU=[],stub_L1_um=0,status='KEEP_DECLARED_CLOCK_OR_NO_EXISTING_METAL_SUPPORT',retention_reason='Original clock point retained for clock-specific validation' if covered else 'No actual own WIRE/VIA covers old pin; no invented endpoint or metal deletion')
                    occupied.add((ly,cx,cy));counts[r['status']]+=1
                    for layer,z in vias[r['first_hop']].items():add(r['net'],'VIRTUAL_FUTURE_FIRST_HOP_NOT_INSTALLED',layer,tuple(v+(cx if j%2==0 else cy) for j,v in enumerate(z)))
                    continue
            xs=range(math.floor((cx-190-20000)/560),math.ceil((cx-190+20000)/560)+1) if ly=='metal5' else range(round((cx-190)/560)-1,round((cx-190)/560)+2)
            ys=range(round((cy-140)/yp)-1,round((cy-140)/yp)+2) if ly=='metal5' else range(math.floor((cy-140-20000)/yp),math.ceil((cy-140+20000)/yp)+1)
            candidates=sorted((abs(x-cx)+abs(y-cy),int((y!=cy) if ly=='metal5' else (x!=cx)),x,y) for x in (190+ix*560 for ix in xs) for y in (140+iy*yp for iy in ys) if abs(x-cx)+abs(y-cy)<=20000)
            chosen=None
            support=None
            # A straight new stub may be blocked along the way. Prefer a
            # destination on already connected same-net actual metal; this
            # changes the access XY without inventing a connecting route.
            if revision!='r01':
                owned={}
                for box,kind in own_metal[r['net'],ly]:
                    xlo=max(box[0]+140,cx-100000);xhi=min(box[2]-140,cx+100000);ylo=max(box[1]+140,cy-100000);yhi=min(box[3]-140,cy+100000)
                    for ix in range(math.ceil((xlo-190)/560),math.floor((xhi-190)/560)+1):
                        for iy in range(math.ceil((ylo-140)/yp),math.floor((yhi-140)/yp)+1):
                            x,y=190+ix*560,140+iy*yp;distance=abs(x-cx)+abs(y-cy)
                            if distance<=100000:owned.setdefault((distance,x,y),(box,kind))
                for (distance,x,y),evidence in sorted(owned.items()):
                    if (ly,x,y) in occupied:continue
                    path,unused,first=proposal(r,x,y)
                    if all(clear(r['net'],layer,z,ly) for layer,z in first):
                        # Preserve the old BPin material as an exact real WIRE
                        # square, using the already native/GDS-tested encoding.
                        stubs=[] if distance==0 or profile=='parent_owned_only' else [(ly,tuple(r['box_DBU']))]
                        chosen=(distance,x,y,[],stubs,first);support=evidence;break
            for distance,perp,x,y in ([] if profile=='parent_owned_only' else candidates):
                if chosen:break
                if (ly,x,y) in occupied or not(die[0]+140<=x<=die[2]-140 and die[1]+140<=y<=die[3]-140):continue
                path,stubs,first=proposal(r,x,y)
                if all(clear(r['net'],layer,z,ly) for layer,z in stubs+first):chosen=(distance,x,y,path,stubs,first);break
            row=dict(r)
            if chosen:
                distance,x,y,path,stubs,first=chosen;row.update(target_center_DBU=[x,y],stub_path_DBU=path,stub_L1_um=0 if support else distance/2000.,XY_L1_um=distance/2000.,status='REAL_STUB_AND_XY_NATIVE_IMPLEMENTATION_REQUIRED' if distance else 'KEEP_ACTUAL_XY_FIRST_HOP_PRESCREEN_CLEAR_NOT_AP_PASS')
                row['access_method']='OWN_EXISTING_METAL_EXACT_OLD_PIN_RETENTION' if support else 'NEW_CONNECTED_SAME_LAYER_STUB'
                if profile=='parent_owned_only':row['access_method']='OWN_EXISTING_METAL_NO_NEW_WIRE'
                if support:row['actual_own_metal_support']={'box_DBU':support[0],'kind':support[1],'layer':ly,'net':r['net']}
                occupied.add((ly,x,y))
                for layer,z in first:add(r['net'],'VIRTUAL_FUTURE_FIRST_HOP_NOT_INSTALLED',layer,z)
                for layer,z in stubs:add(r['net'],'NEW_STUB_TO_BE_IMPLEMENTED',layer,z);expected_extra[r['net']].append(('WIRE',layer)+z)
                if distance:selected.append(row)
            else:
                row.update(target_center_DBU=[cx,cy],stub_path_DBU=[[cx,cy]],stub_L1_um=0,status='KEEP_NO_SCREENED_OWN50UM_ACCESS_ORIGINAL_RISK_REMAINS');occupied.add((ly,cx,cy))
                if profile=='parent_owned_only':
                    for layer,z in vias[r['first_hop']].items():add(r['net'],'VIRTUAL_FUTURE_FIRST_HOP_NOT_INSTALLED',layer,tuple(v+(cx if j%2==0 else cy) for j,v in enumerate(z)))
            r.update(row);counts[row['status']]+=1
            if number%500==0:print('FULL_PORT_ACCESS_STUB_PROGRESS',number,dict(counts),flush=True)
        db.close();rec['all13507_status_counts']=dict(counts);rec['actual_requested_XY_and_stub_count']=len(selected);rec['first_hop_footprints_not_installed_in_leaf']=True
        (out/'all13507_source_bound_access_stub_plan.json').write_text(json.dumps(ports,indent=2)+'\n');save()
        specs='set stub_specs {\n'+''.join('{'+tcl(r['pin'])+' '+tcl(r['net'])+' '+r['original_layer']+' {'+' '.join('{'+str(x)+' '+str(y)+'}' for x,y in r['stub_path_DBU'])+'} '+' '.join(map(str,r['target_center_DBU']))+' '+r['access_method']+' {'+' '.join(map(str,r['box_DBU']))+'}}\n' for r in selected)+'}\n'
        (out/'actual_stub_specs.tcl').write_text(specs)
        libs=['read_liberty '+tcl(p) for p in old['libs']]
        edit='\n'.join(libs+['read_db '+tcl(odb),'fingerprint '+tcl(out/'before'),'set b [ord::get_db_block];set tech [ord::get_db_tech];set original_obs [lsort [$b getObstructions]]','source '+tcl(out/'actual_stub_specs.tcl')])+r'''
if {![stage actual_all_selected_stubs_and_original_layer_pins {
 foreach spec $stub_specs {
  lassign $spec pin net layer points tx ty method oldbox;set bt [$b findBTerm $pin]
  if {$bt eq "NULL" || [[$bt getNet] getName] ne $net} {error "Original bit peer changed"}
  set n [$bt getNet];set wire [$n getWire];if {$wire eq "NULL"} {error "Original routed conductor missing"}
  if {$method ne "OWN_EXISTING_METAL_NO_NEW_WIRE"} {
  if {[$b findNet HPY_ACTUAL_ACCESS_STUB_STAGING] ne "NULL"} {error "Staging collision"}
  set temp [odb::dbNet_create $b HPY_ACTUAL_ACCESS_STUB_STAGING];set tw [odb::dbWire_create $temp];set enc [odb::dbWireEncoder]
  $enc begin $tw;$enc newPath [$tech findLayer $layer] ROUTED
  if {$method eq "OWN_EXISTING_METAL_EXACT_OLD_PIN_RETENTION"} {
   lassign $oldbox a c d e
   if {$layer eq "metal5"} {set cy [expr {($c+$e)/2}];$enc addPoint $a $cy 0;$enc addPoint $d $cy 0} else {set cx [expr {($a+$d)/2}];$enc addPoint $cx $c 0;$enc addPoint $cx $e 0}
  } else {foreach point $points {lassign $point x y;$enc addPoint $x $y}}
  $enc end;$wire append $tw;odb::dbNet_destroy $temp
  }
  place_pin -pin_name $pin -layer $layer -location [list [expr {$tx/2000.}] [expr {$ty/2000.}]] -pin_size {.14 .14}
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
        if profile=='parent_owned_only' and rec.get('fresh_DRC_count')==0:
            from probe_ll_parent_after_leaf_edit import probe
            rec['actual_full_parent_AP']=probe(out,run_native);save()
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
    return int(bool(rec.get('actual_failure')) or rec.get('fresh_DRC_count')!=0 or rec['native_stages'].get('native_all_pin_access.stages.tsv',{}).get('all_signal_native_pin_access')!='EXECUTED' or not rec['all_closed_sources_unchanged'] or (profile=='parent_owned_only' and not rec.get('actual_full_parent_AP',{}).get('pass')))
if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
