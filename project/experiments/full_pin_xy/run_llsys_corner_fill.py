"""Fill three measured same-net M5 notches; keep all13507 pins and9517 edits.

Reuse SHA-bound local geometry and exact prior100 additions. Native DRC runs
before costly all-net/RC checks. Nine overlapping0.14um native WIRE strips fill
three0.42x0.35um boxes. No new pin, via, cell, rule or connection target.
"""
from pathlib import Path
from collections import defaultdict
import csv,datetime,gzip,json,math,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from compare_native_route_representations import routing_box_hashes
from check_access import check
DRIVER=Path(__file__).resolve().parent

def run(revision):
 source=ROOT/'llsys_same_net_gap_heal/r02';rp=source/'execution.json';q=json.loads(rp.read_text())
 assert q.get('completed_utc') and q['fresh_DRC_count']==6 and q['all_closed_sources_unchanged'] and q['whole_signal_geometry']['pass']
 assert all(q['all_original_cells_ports_connections_pin_XY_layers_sizes_PG_and_die_exact'].values()) and q['all_original_WIRE_VIA_exact_plus_requested_patch_rectangles']
 names=['routed.odb','whole_access.tsv.gz','after.cells.tsv','after.pins.tsv','after.pdn.tsv','after.die.tsv','independent.drc','source_bound_patch_plan.json','all100_local_actual_geometry.json']
 inputs={str(rp):sha(rp)}
 for name in names:
  p=source/name;assert sha(p)==q['files'][name]['sha256'];inputs[str(p)]=sha(p)
 tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';inputs[str(tech)]=sha(tech)
 trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
 inputs.update({str(trial):sha(trial),str(sdc):sha(sdc)})
 out=ROOT/'llsys_corner_fill'/revision;out.mkdir(parents=True,exist_ok=False)
 rec={'scope':'ACTUAL_THREE_M5_NOTCH_FILLS_NOT_COMPLETE_SYSTEM_QUALIFICATION','full_qualification':False,'source_SHA':inputs,
  'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'native_returncodes':{},
  'source_native_DRC_count':6,'original13507_pins_and9517_XY_access_edits':'RETAINED_EXACTLY','new_cells_sizes_vias_or_pin_edits':0,
  'original_allowed_layers':'signal M2-M8; clock M4-M8','clock_loads_and_rules':'UNCHANGED','historical_parent_targets':'PARTIAL_OR_UNKNOWN_UNCHANGED',
  'first_hop_reservations':'Existing controlled-parent via5 footprint only, not installed; no recovered historical handoff assumed',
  'full_GDS_RTL_and_parent_access':'NOT_QUALIFIED','not_block_area_saving':True}
 save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
 try:
  markers=[]
  for net,a,c,d,e in re.findall(r'srcs: net:(\S+)\s+bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer metal5',(source/'independent.drc').read_text()):markers.append((net,tuple(round(float(v)*2000) for v in [a,c,d,e])))
  assert len(markers)==6 and set(n for n,b in markers)=={'bit_7059','bit_1382043','bit_1383573'}
  text=tech.read_text();layer=re.search(r'^LAYER metal5\s.*?^END metal5',text,re.M|re.S)[0]
  grid=round(float(re.search(r'MANUFACTURINGGRID\s+([\d.]+)',text)[1])*2000);width=round(float(re.search(r'^\s*WIDTH\s+([\d.]+)\s*;',layer,re.M)[1])*2000);assert grid==10 and width==280
  tab=re.search(r'SPACINGTABLE\s+PARALLELRUNLENGTH(.*?);',layer,re.S)[1].splitlines();ps=[round(float(v)*2000) for v in tab[0].split()];rules=[]
  for line in tab[1:]:
   p=line.split()
   if p and p[0]=='WIDTH':rules.append((round(float(p[1])*2000),[round(float(v)*2000) for v in p[2:]]))
  maxspace=max(max(v) for w,v in rules);broad=maxspace+4000
  prior=json.loads((source/'source_bound_patch_plan.json').read_text());local=json.loads((source/'all100_local_actual_geometry.json').read_text())
  # Prior receipt proves these are the only real WIRE additions after this
  # complete local export (which already includes leaf/parent PG and BPins).
  prior_patches=[(r['net'],r['layer'],r['actual_new_patch_box_DBU'],'ACTUAL_PRIOR100_PATCH') for r in prior['selected']];assert len(prior_patches)==100
  future=[]
  for line in (source/'after.pins.tsv').open():
   p=line.split()
   if len(p)==9 and p[2] not in ['POWER','GROUND'] and p[4]=='metal5':future.append((p[3].strip('{}'),'metal5',tuple(map(int,p[5:9])),'RESERVED_VIA5_CAP_NOT_INSTALLED'))
  selected=[];proof=[]
  for net in sorted(set(n for n,b in markers)):
   boxes=[b for n,b in markers if n==net];z=(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes));assert (z[2]-z[0],z[3]-z[1])==(840,700)
   indices=[i for i,m in enumerate(prior['source_native_markers']) if m['net']==net];assert len(indices)==2
   coverage=[]
   for i in indices:
    b=prior['source_native_markers'][i]['native_marker_box_DBU'];cx=(b[0]+b[2])//2
    coverage.append(cx-broad<=z[0]-maxspace and z[2]+maxspace<=cx+broad and b[1]-broad<=z[1]-maxspace and z[3]+maxspace<=b[3]+broad)
   assert all(coverage),'Cached native geometry does not cover every required-spacing neighbor'
   rows={tuple([n,ly,tuple(b),kind]) for i in indices for n,ly,b,kind in local[str(i)]};rows.update((n,ly,tuple(b),kind) for n,ly,b,kind in prior_patches)
   blockers=[]
   for n,ly,b,kind in list(rows)+future:
    if ly!='metal5' or n==net:continue
    dx=max(z[0]-b[2],b[0]-z[2],0);dy=max(z[1]-b[3],b[1]-z[3],0)
    if dx>maxspace or dy>maxspace:continue
    w=max(min(z[2]-z[0],z[3]-z[1]),min(b[2]-b[0],b[3]-b[1]));prl=max(0,min(z[3],b[3])-max(z[1],b[1])) if dx and not dy else max(0,min(z[2],b[2])-max(z[0],b[0])) if dy and not dx else 0
    need=max((r for r in rules if r[0]<=w),key=lambda r:r[0])[1][max(i for i,v in enumerate(ps) if v<=prl)]
    if dx*dx+dy*dy<need*need:blockers.append({'net':n,'box_DBU':b,'kind':kind,'need_DBU':need})
   proof.append({'net':net,'actual_fill_envelope_DBU':z,'all_required_spacing_neighbors_covered_by_SHA_bound_export':True,'foreign_metal_PG_pin_or_reserved_via_blockers':blockers})
   assert not blockers,(net,blockers)
   # Three overlapping default-width WIREs cover exactly the full envelope.
   strips=[]
   for y in [z[1]+140,z[1]+350,z[1]+560]:
    b=(z[0],y-140,z[2],y+140);assert all(v%grid==0 for v in b)
    r={'net':net,'layer':'metal5','box_DBU':b,'points_DBU':[(z[0],y),(z[2],y)],'horizontal_center_on_preferred_M5_track':(y-140)%560==0};selected.append(r);strips.append(b)
   assert strips[0][1]==z[1] and strips[-1][3]==z[3] and all(strips[i+1][1]<=strips[i][3] for i in [0,1])
  (out/'local_geometry_and_patch_proof.json').write_text(json.dumps({'regions':proof,'actual_new_default_width_WIRE_strips':selected,'manufacturing_grid_um':grid/2000.,'track_note':'Metal-fill strips may be off preferred route-track centers; pin/via centers unchanged. Manufacturing grid screened; native/full-rule scopes remain independent.'},indent=2)+'\n')
  rec.update(actual_regions=3,actual_new_WIRE_strips=9,local_foreign_PG_and_first_hop_screen='NO_BLOCKER_IN_MEASURED_SCOPE',manufacturing_grid_um=grid/2000.,preferred_track_centers=sum(r['horizontal_center_on_preferred_M5_track'] for r in selected));save()
  helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
  common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
  for prefix in ['/public/home/yuzelu/project-circuit','/public/home/yuzelu/PingyangHuang/issue-55']:common+=['--bind',prefix+':'+prefix+':ro']
  for lib in old['libs']:
   if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
  def native(label,body,threads=8,env=''):
   script=out/(label+'.tcl');script.write_text(helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')+'\n'+body+'\n');rc=execute(common,script,out/(label+'.log'),'PINXY_OUTPUT='+str(out)+env,threads=threads);rec['native_returncodes'][label]=rc;save();return rc
  specs='set fills {\n'+''.join('{'+tcl(r['net'])+' {'+' '.join('{'+str(x)+' '+str(y)+'}' for x,y in r['points_DBU'])+'}}\n' for r in selected)+'}\n';(out/'fills.tcl').write_text(specs)
  body='read_db '+tcl(source/'routed.odb')+'\nsource '+tcl(out/'fills.tcl')+r'''
set b [ord::get_db_block];set ly [[ord::get_db_tech] findLayer metal5]
if {[$ly getWidth]!=280} {error "Original M5 width changed"}
if {![stage actual_three_corner_fills {
 foreach r $fills {
  lassign $r name points;set n [$b findNet $name];if {$n eq "NULL" || [$n getWire] eq "NULL"} {error "Original signal WIRE missing"}
  if {[$b findNet HPY_CORNER_FILL_STAGING] ne "NULL"} {error "Staging name collision"}
  set temp [odb::dbNet_create $b HPY_CORNER_FILL_STAGING];set w [odb::dbWire_create $temp];set e [odb::dbWireEncoder];$e begin $w;$e newPath $ly ROUTED
  foreach p $points {lassign $p x y;$e addPoint $x $y 0};$e end;[$n getWire] append $w;odb::dbNet_destroy $temp
 }
}]} {close $stages;exit 1}
'''
  body+='\n'+'\n'.join(['fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
   'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}','stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
   'set ::env(PINXY_ACCESS_ALL) 0','set ::env(PINXY_ACCESS_NET_NAMES) {bit_7059 bit_1382043 bit_1383573}','set ::env(PINXY_ACCESS_OUT) '+tcl(out/'target_access.tsv.gz'),'source '+tcl(DRIVER/'export_access.tcl'),'close $stages'])
  assert native('actual_fill_edit',body)==0
  rec['all_original_cells_ports_connections_pin_XY_layers_sizes_PG_and_die_exact']={k:sha(source/('after.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pins','pdn','die']};assert all(rec['all_original_cells_ports_connections_pin_XY_layers_sizes_PG_and_die_exact'].values())
  rec['three_changed_nets_actual_geometry']=check(out/'target_access.tsv.gz',True);assert rec['three_changed_nets_actual_geometry']['pass']
  routing='set_routing_layers -signal metal2-metal8 -clock metal4-metal8'
  assert native('fresh_DRC','read_db '+tcl(out/'routed.odb')+'\n'+routing+'\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\nclose $stages',4)==0
  rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M));save()
  assert rec['fresh_DRC_count']==0,'Residual native DRC; stop before costly all-net/RC replay'
  body='read_db '+tcl(out/'routed.odb')+'\n'+routing+'\nsource '+tcl(DRIVER/'export_access.tcl')+'\nstage native_all_pin_access {pin_access}\nclose $stages'
  assert native('all_geometry_and_AP',body,env=',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'))==0
  extra=defaultdict(list)
  for r in selected:extra[r['net']].append(('WIRE',r['layer'])+tuple(r['box_DBU']))
  a,ac=routing_box_hashes(source/'whole_access.tsv.gz',725253,extra);b,bc=routing_box_hashes(out/'whole_access.tsv.gz',725253)
  rec['all_original_WIRE_VIA_exact_plus_requested_patch_rectangles']=a==b and ac==bc;assert a==b and ac==bc
  rec['whole_signal_geometry']={'pass':True,'scope':'Actual725253-net geometry multiset/terminal invariants against a source with all-net connectivity pass; all3 changed nets checked explicitly. Not a fresh725253-net BFS or GDS LVS.','source_checked_nets':725253,'new_explicit_changed_nets':3,'exact_other_nets':725250}
  libs=['read_liberty '+tcl(lib) for lib in old['libs']]
  assert native('RC_STA','\n'.join(libs+['read_db '+tcl(out/'routed.odb'),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
   'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
   'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']))==0
  for kind in ['setup','hold']:rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',(out/(kind+'.txt')).read_text())[1])
 except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
 rec['native_stages']={p.name:{r['stage']:r['status'] for r in csv.DictReader(p.open(),delimiter='\t')} for p in out.glob('*stages.tsv')}
 rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
 return int(bool(rec.get('actual_failure')) or rec.get('fresh_DRC_count')!=0 or not rec['all_closed_sources_unchanged'] or any(rec['native_stages'].get('actual_fill_edit.stages.tsv',{}).get(k)!='EXECUTED' for k in ['VDD','VSS']))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
