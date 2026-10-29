"""Heal measured same-net gaps after real9517 access edits, without pin moves.

Each proposed patch must touch at least two own actual shapes and clear real
foreign signal/PG/singleton pins plus all future first-hop caps. Added metal is
native wire geometry; all old wires/vias,13507 ports/cells/PG/die remain exact.
Independent native rules/AP/RC/STA decide the result, not the geometric screen.
"""
from pathlib import Path
from collections import defaultdict,Counter
from bisect import bisect_left,bisect_right
import csv,datetime,gzip,json,math,os,re,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from compare_native_route_representations import routing_box_hashes
from check_access import check
DRIVER=Path(__file__).resolve().parent

def run(revision):
    source=ROOT/'all_llsys_access_stubs/r03';rp=source/'execution.json';s=json.loads(rp.read_text());odb=source/'routed.odb';geo=source/'whole_access.tsv.gz';drc=source/'independent.drc';pins=source/'after.pins.tsv'
    assert s.get('completed_utc') and s['all_closed_sources_unchanged'] and s['fresh_DRC_count']==100 and s['whole_signal_geometry']['pass'] and all(s['all_cells_connections_PG_die_preserved'].values())
    for p in [odb,geo,drc,pins]:assert sha(p)==s['files'][p.name]['sha256']
    original=ROOT/'llsys_residual_access_preflight/r01';parent=ROOT/'parent_pg_llsys_local/r01';tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef'
    refs=[original/'actual_high_PG_OBS.tsv',parent/'actual_parent_PG_local.tsv']
    for folder in [original,parent]:
        q=json.loads((folder/'execution.json').read_text());assert q.get('completed_utc') and q['all_closed_sources_unchanged']
        for p in refs:
            if p.parent==folder:assert sha(p)==q['files'][p.name]['sha256']
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    inputs={str(p):sha(p) for p in [rp,odb,geo,drc,pins,tech,trial,sdc]+refs+[original/'execution.json',parent/'execution.json']}
    out=ROOT/'llsys_same_net_gap_heal'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_MEASURED100_SAME_NET_GAP_METAL_ECO_NO_PIN_OR_FUNCTION_CHANGE_NOT_FULL_SYSTEM','source_SHA':inputs,
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,
      'source_native_DRC_count':100,'original_13507_pins_and9517_access_edits':'RETAINED_EXACTLY','new_cells_sizes_or_vias':0,
      'original_allowed_layers':'signal M2-M8; clock M4-M8','native_returncodes':{},'native_rules_and_clock_load_constraints':'UNCHANGED',
      'not_checked_by_local_screen':['Complete end-of-line/min-step/enclosure rules','Whole parent access stack','Complete GDS/RTL/STA qualification']}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    try:
        entries=re.findall(r'violation type: ([^\n]+)\n\s*srcs: ([^\n]+)\n\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)',drc.read_text());assert len(entries)==100
        markers=[]
        for kind,names,a,c,d,e,layer in entries:
            nets=re.findall(r'net:(\S+)',names);assert kind=='Metal Spacing' and len(nets)==1 and layer in ['metal5','metal6']
            markers.append({'net':nets[0],'layer':layer,'native_marker_box_DBU':tuple(round(float(x)*2000) for x in [a,c,d,e]),'native_type':kind})
        text=tech.read_text();grid=round(float(re.search(r'\bMANUFACTURINGGRID\s+([\d.]+)',text)[1])*2000);assert grid>0
        rules={};maxspace={}
        for layer in ['metal5','metal6']:
            block=re.search(r'^LAYER '+layer+r'\s.*?^END '+layer,text,re.M|re.S)[0];assert round(float(re.search(r'\bWIDTH\s+([\d.]+)',block)[1])*2000)==280
            tab=re.search(r'SPACINGTABLE\s+PARALLELRUNLENGTH(.*?);',block,re.S)[1].splitlines();ps=[round(float(x)*2000) for x in tab[0].split()];rows=[]
            for line in tab[1:]:
                p=line.split()
                if p and p[0]=='WIDTH':rows.append((round(float(p[1])*2000),[round(float(x)*2000) for x in p[2:]]))
            rules[layer]=(ps,rows);maxspace[layer]=max(max(v) for w,v in rows)
        def spacing(layer,z,b):
            dx=max(z[0]-b[2],b[0]-z[2],0);dy=max(z[1]-b[3],b[1]-z[3],0);width=max(min(z[2]-z[0],z[3]-z[1]),min(b[2]-b[0],b[3]-b[1]));prl=max(0,min(z[3],b[3])-max(z[1],b[1])) if dx and not dy else max(0,min(z[2],b[2])-max(z[0],b[0])) if dy and not dx else 0
            ps,rs=rules[layer];col=max(i for i,v in enumerate(ps) if v<=prl);return max((r for r in rs if r[0]<=width),key=lambda r:r[0])[1][col]
        centers=sorted(((r['native_marker_box_DBU'][0]+r['native_marker_box_DBU'][2])//2,index) for index,r in enumerate(markers));xs=[r[0] for r in centers];local=defaultdict(list);broad=max(maxspace.values())+4000
        def consume(reader):
            for r in reader:
                ly=r['layer']
                if ly not in rules or r['kind']=='UNROUTED':continue
                b=tuple(int(r[k]) for k in ['x0','y0','x1','y1'])
                for cx,index in centers[bisect_left(xs,b[0]-broad):bisect_right(xs,b[2]+broad)]:
                    m=markers[index];z=m['native_marker_box_DBU']
                    if ly==m['layer'] and b[1]-broad<=z[3] and z[1]<=b[3]+broad:local[index].append((r['net'],ly,b,r['kind']))
        with gzip.open(str(geo),'rt') as f:consume(csv.DictReader(f,delimiter='\t'))
        for p in refs:
            with p.open() as f:consume(csv.DictReader(f,delimiter='\t'))
        pinrows=[]
        for line in pins.open():
            p=line.split()
            if len(p)==9 and p[2] not in ['POWER','GROUND']:pinrows.append({'net':p[3].strip('{}'),'layer':p[4],'x0':p[5],'y0':p[6],'x1':p[7],'y1':p[8],'kind':'ALL13507_ACTUAL_PIN'})
        assert len(pinrows)==13507;consume(pinrows)
        # Explicit future access reservations are not actual installed vias.
        templates=json.loads((ROOT/'all_llsys_first_hop_audit/r01/execution.json').read_text())['actual_via_templates']
        future=[]
        for p in pinrows:
            x,y=(int(p['x0'])+int(p['x1']))//2,(int(p['y0'])+int(p['y1']))//2
            for ly,z in templates['via5_0' if p['layer']=='metal5' else 'via6_0'].items():
                if ly in rules:future.append((p['net'],ly,(x+z[0],y+z[1],x+z[2],y+z[3]),'FUTURE_FIRST_HOP_NOT_INSTALLED'))
        def intersects(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
        selected=[];unresolved=[];new=[]
        for index,m in enumerate(markers):
            box=m['native_marker_box_DBU'];a,c,d,e=box;horizontal=d-a>=e-c;mid=(c+e)/2. if horizontal else (a+d)/2.
            choices=sorted(set([math.floor(mid/grid)*grid,math.ceil(mid/grid)*grid]),key=lambda v:abs(v-mid));chosen=None;rejections=Counter()
            for middle in choices:
                if horizontal:
                    lo,hi=a,d
                    if hi-lo<280:lo=math.floor(((a+d)/2.-140)/grid)*grid;hi=lo+280
                    z=(lo,middle-140,hi,middle+140);path=[(lo,middle),(hi,middle)]
                else:
                    lo,hi=c,e
                    if hi-lo<280:lo=math.floor(((c+e)/2.-140)/grid)*grid;hi=lo+280
                    z=(middle-140,lo,middle+140,hi);path=[(middle,lo),(middle,hi)]
                assert all(v%grid==0 for v in z)
                owners={b for net,ly,b,kind in local[index] if net==m['net'] and kind in ['WIRE','VIA'] and intersects(z,b)}
                if len(owners)<2:rejections['less_than_two_actual_own_metal_shapes']+=1;continue
                blockers=[]
                for net,ly,b,kind in local[index]+future+new:
                    if ly!=m['layer'] or net==m['net']:continue
                    dx=max(z[0]-b[2],b[0]-z[2],0);dy=max(z[1]-b[3],b[1]-z[3],0)
                    if dx>maxspace[ly] or dy>maxspace[ly]:continue
                    need=spacing(ly,z,b)
                    if dx*dx+dy*dy<need*need:blockers.append({'net':net,'layer':ly,'box_DBU':b,'kind':kind,'need_DBU':need})
                if blockers:rejections['actual_or_future_foreign_spacing_risk']+=1;continue
                chosen={'net':m['net'],'layer':m['layer'],'native_marker_box_DBU':box,'actual_new_patch_box_DBU':z,'path_DBU':path,'overlapping_actual_own_shapes':sorted(owners),'source_native_marker_index':index};break
            if chosen:selected.append(chosen);new.append((m['net'],m['layer'],chosen['actual_new_patch_box_DBU'],'NEW_HEALING_PATCH'))
            else:unresolved.append(dict(m,rejections=dict(rejections)))
        (out/'all100_local_actual_geometry.json').write_text(json.dumps({str(i):rows for i,rows in local.items()},indent=2)+'\n')
        (out/'source_bound_patch_plan.json').write_text(json.dumps({'selected':selected,'unresolved':unresolved,'source_native_markers':markers},indent=2)+'\n')
        rec.update(local_checked_native_markers=100,requested_actual_same_net_patches=len(selected),unresolved_markers=unresolved,manufacturing_grid_um=grid/2000.,patches_on_original_allowed_layers=True,
          added_rectangle_bbox_area_upper_bound_um2=sum((r['actual_new_patch_box_DBU'][2]-r['actual_new_patch_box_DBU'][0])*(r['actual_new_patch_box_DBU'][3]-r['actual_new_patch_box_DBU'][1])/4000000. for r in selected),not_block_area_saving=True)
        assert selected;save()
        specs='set patches {\n'+''.join('{'+tcl(r['net'])+' '+r['layer']+' {'+' '.join(map(str,r['actual_new_patch_box_DBU']))+'} {'+' '.join('{'+str(x)+' '+str(y)+'}' for x,y in r['path_DBU'])+'}}\n' for r in selected)+'}\n';(out/'patches.tcl').write_text(specs)
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        for prefix in ['/public/home/yuzelu/project-circuit','/public/home/yuzelu/PingyangHuang/issue-55']:common+=['--bind',prefix+':'+prefix+':ro']
        for lib in old['libs']:
            if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
        def native(label,body,threads=8):
            script=out/(label+'.tcl');script.write_text(helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')+'\n'+body+'\n');rc=execute(common,script,out/(label+'.log'),'PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=threads);rec['native_returncodes'][label]=rc;save();return rc
        edit='read_db '+tcl(odb)+'\nfingerprint '+tcl(out/'before')+'\nsource '+tcl(out/'patches.tcl')+r'''
set b [ord::get_db_block];set tech [ord::get_db_tech]
if {![stage actual_same_net_gap_metal {
 foreach r $patches {
  lassign $r net layer box points;set n [$b findNet $net];if {$n eq "NULL" || [$n getWire] eq "NULL"} {error "Actual existing signal wire missing"}
  if {[$b findNet HPY_GAP_HEAL_STAGING] ne "NULL"} {error "Staging name collision"}
  set temp [odb::dbNet_create $b HPY_GAP_HEAL_STAGING];set w [odb::dbWire_create $temp];set e [odb::dbWireEncoder];$e begin $w;$e newPath [$tech findLayer $layer] ROUTED
  foreach p $points {lassign $p x y;$e addPoint $x $y 0};$e end;[$n getWire] append $w;odb::dbNet_destroy $temp
 }
}]} {close $stages;exit 1}
'''
        edit+='\n'+'\n'.join(['fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}','stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}','source '+tcl(DRIVER/'export_access.tcl'),'close $stages'])
        assert native('actual_healing_edit',edit)==0
        rec['all_original_cells_ports_connections_pin_XY_layers_sizes_PG_and_die_exact']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pins','pdn','die']};assert all(rec['all_original_cells_ports_connections_pin_XY_layers_sizes_PG_and_die_exact'].values())
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        extra=defaultdict(list)
        for r in selected:extra[r['net']].append(('WIRE',r['layer'])+tuple(r['actual_new_patch_box_DBU']))
        a,ac=routing_box_hashes(geo,725253,extra);b,bc=routing_box_hashes(out/'whole_access.tsv.gz',725253);rec['all_original_WIRE_VIA_exact_plus_requested_patch_rectangles']=a==b and ac==bc;assert a==b and ac==bc
        routing='set_routing_layers -signal metal2-metal8 -clock metal4-metal8'
        native('fresh_DRC','read_db '+tcl(out/'routed.odb')+'\n'+routing+'\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\nclose $stages',threads=4)
        if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        native('native_all_pin_access','read_db '+tcl(out/'routed.odb')+'\n'+routing+'\nstage all_signal_native_pin_access {pin_access}\nclose $stages')
        libs=['read_liberty '+tcl(lib) for lib in old['libs']]
        native('RC_STA','\n'.join(libs+['read_db '+tcl(out/'routed.odb'),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']))
        for kind in ['setup','hold']:
            p=out/(kind+'.txt')
            if p.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',p.read_text())[1])
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['native_stages']={p.name:{r['stage']:r['status'] for r in csv.DictReader(p.open(),delimiter='\t')} for p in out.glob('*stages.tsv')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or rec.get('fresh_DRC_count')!=0 or not all(rec['native_stages'].get('actual_healing_edit.stages.tsv',{}).get(k)=='EXECUTED' for k in ['VDD','VSS']) or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
