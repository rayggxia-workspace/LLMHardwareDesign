"""Preflight actual first-hop geometry for all87 remaining unaligned ports.

Uses current complete real metal, native PG/block OBS, actual peer terminals,
and actual via5/6 dimensions. This only prepares an actual87-net reroute; it
does not call candidate coordinates a physical implementation or parent AP.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,datetime,gzip,json,math,os,re,shutil,subprocess,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
DRIVER=Path(__file__).resolve().parent

def run(revision,native_reuse=None,target_set='residual87'):
    assert target_set in ['residual87','parent_failed1011']
    source=ROOT/'llsys_wire_pin_retention/r01';rp=source/'execution.json';q=json.loads(rp.read_text());assert q.get('completed_utc') and q['fresh_DRC_count']==0 and q['whole_signal_geometry']['pass'] and q['all_closed_sources_unchanged']
    odb=source/'routed.odb';geo=source/'whole_access.tsv.gz';pins=source/'after.pins.tsv';deffile=source/'routed.def'
    for p in [odb,geo,pins,deffile]:assert sha(p)==q['files'][p.name]['sha256']
    audit=ROOT/'all_llsys_actual_access_caps/r02';ap=audit/'execution.json';aq=json.loads(ap.read_text());table=audit/'all13507_actual_own_via_candidates.tsv';assert aq.get('completed_utc') and aq['all_closed_sources_unchanged'] and sha(table)==aq['files'][table.name]['sha256']
    inventory=list(csv.DictReader(table.open(),delimiter='\t'))
    selected=[r for r in inventory if r['status']=='KEEP_NO_BOUNDED_OWN_VIA_FOUND'];assert len(selected)==87
    if target_set=='parent_failed1011':
        parent=ROOT/'common_integration/deadline-current-r01/C';pq=json.loads((parent/'execution.json').read_text());assert pq.get('completed_utc') and pq['native_final_stage_status']['lower_detailed_route']=='FAIL' and pq['all_sources_unchanged']
        assert 'No access point for u_llaccel_aux/bit_1011' in (parent/'lower_route.log').read_text()
        selected=[r for r in inventory if r['pin']=='bit_1011'];assert len(selected)==1
    actual={}
    for line in pins.open():
        p=line.split()
        if len(p)==9 and p[2] not in ['POWER','GROUND']:actual[p[0].strip('{}')]=p
    assert len(actual)==13507
    for r in selected:
        p=actual[r['pin']];assert p[3].strip('{}')==r['net'] and p[4]==r['layer'] and p[5:]==[r[k] for k in ['x0','y0','x1','y1']]
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';model=json.loads((tech.parent/'model.json').read_text());assert model['original_M1_M10_and_via1_via9_layer_blocks_identical'] and sha(tech)==model['files'][tech.name]['sha256']
    inputs={str(p):sha(p) for p in [rp,odb,geo,pins,deffile,ap,table,tech]}
    if target_set!='residual87':inputs.update({str(p):sha(p) for p in [parent/'execution.json',parent/'lower_route.log']})
    out=ROOT/('llsys_residual_access_preflight' if target_set=='residual87' else 'llsys_parent_failed_pin_preflight')/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ALL87_REAL_FIRST_HOP_PRESCREEN_FOR_ACTUAL_LEAF_REROUTE_NOT_PHYSICAL_IMPLEMENTATION_OR_PARENT_ACCESS','source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'original_signal_pins':13507,'residual_signal_pins':87,'native_edit_route_RC_STA':'NOT_EXECUTED_PREPARATION_ONLY','new_candidate_maximum_L1_um':1.12,'not_checked':['Full applicable rule interactions and complete access stack','Actual leaf reroute and parent AP','RC/STA or function qualification']}
    rec['target_set']=target_set;rec['selected_signal_pins']=len(selected)
    if target_set!='residual87':rec['scope']='ACTUAL_PARENT_FAILED_DRAM_RDATA329_M5_FIRST_HOP_DIAGNOSIS_NOT_IMPLEMENTATION';rec['residual_signal_pins']=1
    try:
        names=' '.join(tcl(r['pin']) for r in selected)
        body='''set b [ord::get_db_block];set seen [dict create]
foreach inst [$b getInsts] {set m [$inst getMaster];dict set seen [$m getName] $m}
set f [open MASTERS w];puts $f "master\\ttype\\thighest_routing_geometry_level"
dict for {name m} $seen {
 set high 0;foreach z [$m getObstructions] {set high [expr {max($high,[[$z getTechLayer] getRoutingLevel])}]}
 foreach mt [$m getMTerms] {foreach p [$mt getMPins] {foreach z [$p getGeometry] {set high [expr {max($high,[[$z getTechLayer] getRoutingLevel])}]}}}
 puts $f [join [list $name [$m getType] $high] "\\t"]
 if {$high>=5 || [$m getType] eq "BLOCK"} {error "Real high-layer master geometry needs explicit transformed export; never assume it empty"}
};close $f
set f [open PEERS w];puts $f "pin\\tnet\\tinstance\\tmaster\\tinstance_pin"
foreach name {NAMES} {set bt [$b findBTerm $name];set n [$bt getNet];if {[llength [$n getBTerms]]!=1 || [llength [$n getITerms]]!=1} {error "Residual real endpoint contract changed"};set it [lindex [$n getITerms] 0];set i [$it getInst];puts $f [join [list $name [$n getName] [$i getName] [[$i getMaster] getName] [[$it getMTerm] getName]] "\\t"]};close $f
set ::env(PINXY_ACCESS_OUT) PGOUT
set pf [open PGOUT w];puts $pf "net\\tlayer\\tx0\\ty0\\tx1\\ty1\\tkind\\tlink"
foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {continue};foreach sw [$n getSWires] {foreach z [$sw getWires] {
 if {[$z isVia]} {set v [$z getTechVia];if {$v eq "NULL"} {set v [$z getBlockVia]};lassign [$z getViaXY] x y;foreach a [$v getBoxes] {set layer [[$a getTechLayer] getName];if {$layer in {metal5 metal6 metal7 via5 via6}} {puts $pf [join [list [$n getName] $layer [expr {$x+[$a xMin]}] [expr {$y+[$a yMin]}] [expr {$x+[$a xMax]}] [expr {$y+[$a yMax]}] PG_VIA {}] "\\t"]}}} else {set layer [[$z getTechLayer] getName];if {$layer in {metal5 metal6 metal7}} {puts $pf [join [list [$n getName] $layer [$z xMin] [$z yMin] [$z xMax] [$z yMax] PG_WIRE {}] "\\t"]}}
}}}
foreach ob [$b getObstructions] {set z [$ob getBBox];set layer [[$z getTechLayer] getName];if {$layer in {metal5 metal6 metal7 via5 via6}} {puts $pf [join [list __BLOCK_OBS__ $layer [$z xMin] [$z yMin] [$z xMax] [$z yMax] OBS {}] "\\t"]}};close $pf
set f [open VIAS w];puts $f "via\\tlayer\\tx0\\ty0\\tx1\\ty1"
foreach name {via5_0 via6_0} {set v [[ord::get_db_tech] findVia $name];if {$v eq "NULL"} {error "Actual original first-hop via missing"};foreach z [$v getBoxes] {puts $f [join [list $name [[$z getTechLayer] getName] [$z xMin] [$z yMin] [$z xMax] [$z yMax]] "\\t"]}};close $f
set r [$b getDieArea];set f [open DIE w];puts $f [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]];close $f
'''
        for k,p in [('MASTERS',out/'actual_used_master_high_layers.tsv'),('PEERS',out/'all87_actual_peers.tsv'),('PGOUT',out/'actual_high_PG_OBS.tsv'),('VIAS',out/'actual_first_hop_vias.tsv'),('DIE',out/'actual_die.tsv')]:body=body.replace(k,tcl(p))
        body=body.replace('NAMES',names);script=out/'native_readonly.tcl';script.write_text('read_db '+tcl(odb)+'\n'+body)
        common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
        if native_reuse:
            assert native_reuse=='r01';previous=ROOT/'llsys_residual_access_preflight'/native_reuse;proof=json.loads((previous/'execution.json').read_text())
            assert proof.get('completed_utc') and proof['native_readonly_returncode']==0 and proof['all_closed_sources_unchanged'] and proof['source_SHA'][str(odb)]==sha(odb)
            inputs[str(previous/'execution.json')]=sha(previous/'execution.json')
            for name in ['actual_used_master_high_layers.tsv','all87_actual_peers.tsv','actual_high_PG_OBS.tsv','actual_first_hop_vias.tsv','actual_die.tsv']:
                p=previous/name;assert sha(p)==proof['files'][name]['sha256'];inputs[str(p)]=sha(p);shutil.copyfile(str(p),str(out/('cached87_peers_NOT_CURRENT_TARGET.tsv' if target_set!='residual87' and name=='all87_actual_peers.tsv' else name)))
            rec['native_readonly_returncode']=0;rec['reused_native_readonly_phase']=str(previous);rec['new_native_readonly_script_not_executed']=True
        else:rec['native_readonly_returncode']=execute(common,script,out/'native_readonly.log',threads=1)
        assert rec['native_readonly_returncode']==0
        via={}
        for r in csv.DictReader((out/'actual_first_hop_vias.tsv').open(),delimiter='\t'):via.setdefault(r['via'],[]).append((r['layer'],tuple(int(r[k]) for k in ['x0','y0','x1','y1'])))
        assert set(via)=={'via5_0','via6_0'}
        for v,rows in via.items():
            assert len(rows)==3 and {ly for ly,z in rows}==({'metal5','via5','metal6'} if v=='via5_0' else {'metal6','via6','metal7'})
            assert all(z[0]<z[2] and z[1]<z[3] for ly,z in rows)
        rec['corrected_failed_r01_assumption']='Actual via6 M7 landing is0.4x0.4um; pin stays0.14x0.14um. Use measured rectangles, not one uniform via footprint.'
        text=tech.read_text();rules={};cutspaces={}
        for layer in ['metal5','metal6','metal7','via5','via6']:
            block=re.search(r'^LAYER '+layer+r'\s.*?^END '+layer,text,re.M|re.S).group(0)
            if layer.startswith('via'):cutspaces[layer]=round(float(re.search(r'\bSPACING\s+([\d.]+)',block)[1])*2000);continue
            t=re.search(r'SPACINGTABLE\s+PARALLELRUNLENGTH(.*?);',block,re.S);assert t
            lines=t[1].splitlines();prls=[round(float(x)*2000) for x in lines[0].split()];rows=[]
            for line in lines[1:]:
                p=line.split()
                if p and p[0]=='WIDTH':rows.append((round(float(p[1])*2000),[round(float(x)*2000) for x in p[2:]]))
            assert rows and all(len(v)==len(prls) for w,v in rows);rules[layer]=(prls,rows)
        def spacing(layer,a,b):
            width=max(min(a[2]-a[0],a[3]-a[1]),min(b[2]-b[0],b[3]-b[1]));dx=max(a[0]-b[2],b[0]-a[2],0);dy=max(a[1]-b[3],b[1]-a[3],0)
            prl=max(0,min(a[3],b[3])-max(a[1],b[1])) if dx and not dy else max(0,min(a[2],b[2])-max(a[0],b[0])) if dy and not dx else 0
            ps,rs=rules[layer];index=max(i for i,v in enumerate(ps) if v<=prl);row=max((r for r in rs if r[0]<=width),key=lambda r:r[0]);return row[1][index]
        local=defaultdict(list);centers={r['pin']:((int(r['x0'])+int(r['x1']))//2,(int(r['y0'])+int(r['y1']))//2) for r in selected};windows={n:(x-3500,y-3500,x+3500,y+3500) for n,(x,y) in centers.items()}
        selected_native_terms=[]
        def consume(reader):
            for r in reader:
                if target_set!='residual87' and r['net']=='bit_1011' and r['kind'] in ['ITERM','BTERM']:selected_native_terms.append(dict(r))
                if r['layer'] not in ['metal5','metal6','metal7','via5','via6'] or r['kind']=='UNROUTED':continue
                z=tuple(int(r[k]) for k in ['x0','y0','x1','y1'])
                for n,w in windows.items():
                    if z[0]<=w[2] and z[2]>=w[0] and z[1]<=w[3] and z[3]>=w[1]:local[n].append((r['net'],r['layer'],z,r['kind']))
        with gzip.open(str(geo),'rt') as f:consume(csv.DictReader(f,delimiter='\t'))
        consume(csv.DictReader((out/'actual_high_PG_OBS.tsv').open(),delimiter='\t'))
        if target_set!='residual87':
            assert len({r['link'] for r in selected_native_terms if r['kind']=='ITERM'})==1 and len({r['link'] for r in selected_native_terms if r['kind']=='BTERM'})==1
            (out/'actual_selected_native_terminals.json').write_text(json.dumps(selected_native_terms,indent=2)+'\n')
        tracks={}
        for line in deffile.open():
            m=re.match(r'TRACKS ([XY]) (\d+) DO (\d+) STEP (\d+) LAYER (metal[567]) ;',line)
            if m:tracks[m[5],m[1]]=(int(m[2]),int(m[4]))
            if line.startswith('COMPONENTS'):break
        assert len(tracks)==6;die=list(map(int,(out/'actual_die.tsv').read_text().split()));occupied={(p[4],(int(p[5])+int(p[7]))//2,(int(p[6])+int(p[8]))//2) for p in actual.values()};newshapes=[];output=[];counts=Counter()
        for r in selected:
            name=r['pin'];cx,cy=centers[name];xo,xp=tracks['metal6','X'];yo,yp=tracks['metal5' if r['layer']=='metal5' else 'metal7','Y'];ix=round((cx-xo)/float(xp));iy=round((cy-yo)/float(yp));candidates=sorted((abs(xo+i*xp-cx)+abs(yo+j*yp-cy),xo+i*xp,yo+j*yp) for i in range(ix-4,ix+5) for j in range(iy-4,iy+5));chosen=None;reject=Counter();vname='via5_0' if r['layer']=='metal5' else 'via6_0'
            for distance,x,y in candidates:
                if distance>2240:continue
                if (r['layer'],x,y) in occupied:reject['duplicate_actual_signal_point']+=1;continue
                tile=(x-140,y-140,x+140,y+140)
                if not (die[0]<=tile[0] and die[1]<=tile[1] and tile[2]<=die[2] and tile[3]<=die[3]):reject['outside_original_die']+=1;continue
                placed=[(ly,(x+z[0],y+z[1],x+z[2],y+z[3])) for ly,z in via[vname]];bad=False
                for layer,z in placed:
                    for net,ly,p,kind in local[name]+newshapes:
                        if ly!=layer or (net==r['net'] and not layer.startswith('via')):continue
                        if layer.startswith('via') and net==r['net'] and p==z:continue
                        dx=max(z[0]-p[2],p[0]-z[2],0);dy=max(z[1]-p[3],p[1]-z[3],0);need=cutspaces[layer] if layer.startswith('via') else spacing(layer,z,p)
                        if dx*dx+dy*dy<need*need:bad=True;reject[kind+':'+layer]+=1;break
                    if bad:break
                if not bad:chosen=(distance,x,y,placed);break
            row=dict(r);row['first_hop_via']=vname;row['candidate_rejection_counts']=dict(reject)
            if target_set!='residual87':
                original_blockers=[]
                for layer,relative in via[vname]:
                    z=(cx+relative[0],cy+relative[1],cx+relative[2],cy+relative[3])
                    for net,ly,p,kind in local[name]:
                        if ly!=layer or (net==r['net'] and not layer.startswith('via')) or (layer.startswith('via') and net==r['net'] and p==z):continue
                        dx=max(z[0]-p[2],p[0]-z[2],0);dy=max(z[1]-p[3],p[1]-z[3],0);need=cutspaces[layer] if layer.startswith('via') else spacing(layer,z,p)
                        if dx*dx+dy*dy<need*need:original_blockers.append({'net':net,'layer':ly,'kind':kind,'actual_box_DBU':p,'required_spacing_DBU':need})
                row['actual_original_first_hop_blockers']=original_blockers
                row['original_x_on_first_hop_grid']=(cx-xo)%xp==0;row['original_y_on_first_hop_grid']=(cy-yo)%yp==0
                if not original_blockers and row['original_x_on_first_hop_grid'] and row['original_y_on_first_hop_grid']:
                    chosen=None;row['first_hop_clear_does_not_explain_parent_NoAP']=True
            if chosen:
                distance,x,y,placed=chosen;row.update(status='PRESCREENED_REAL_FIRST_HOP_POINT_REQUIRES_ACTUAL_REROUTE',target_x_DBU=x,target_y_DBU=y,target_L1_um=distance/2000.);occupied.add((r['layer'],x,y));newshapes.extend((r['net'],ly,z,'OTHER_NEW_CANDIDATE') for ly,z in placed)
            else:row['status']='KEEP_FIRST_HOP_CLEAR_PARENT_NOAP_NEEDS_STACK_OR_OBS_DIAGNOSIS' if row.get('first_hop_clear_does_not_explain_parent_NoAP') else 'KEEP_NO_PRESCREENED_POINT_WITHIN_BOUND_NOT_PHYSICAL_INFEASIBILITY'
            output.append(row);counts[row['status']]+=1
        (out/('all'+str(len(selected))+'_first_hop_targets_NOT_IMPLEMENTED.json')).write_text(json.dumps(output,indent=2)+'\n');rec['status_counts']=dict(counts);rec['all_selected_actual_original_pin_contracts_verified']=True;rec['original_M5_M6_0p14_size_and_layer_preserved']=True;rec['actual_first_hop_templates']=via;rec['actual_per_layer_cut_spacing_DBU']=cutspaces;rec['native_no_high_layer_master_geometry_omitted']=True
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(*sys.argv[1:]))
