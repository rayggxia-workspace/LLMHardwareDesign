"""Actual M5 pin relocation on unchanged real wire, then fresh parent AP.

Source pin and selected destination must both be covered by pre-existing
same-net metal. No conductor, OBS, via, cell, rule, target or layer is deleted.
Fresh native LEF export is mandatory; a metadata-only LEF edit is forbidden.
The preliminary parent AP view is not a fresh extracted timing model.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,gzip,json,math,os,re,shutil,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_llsys_actual_tips import pin_contract
from run_common_integration import alias_stream
from coarsen_parent_low_obs import coarsen
from check_access import check
DRIVER=Path(__file__).resolve().parent


def def_nets_digest(path):
    import hashlib
    h=hashlib.sha256();active=False;done=False
    with Path(path).open('rb') as f:
        for line in f:
            if line.startswith(b'NETS '):active=True
            if active:h.update(line)
            if active and line.startswith(b'END NETS'):done=True;break
    assert done,'Native DEF NETS section absent'
    return h.hexdigest()


def run(revision):
    diagnosis=ROOT/'current_parent_failed_pin_diagnosis/r02';dp=diagnosis/'execution.json';d=json.loads(dp.read_text())
    assert d.get('completed_utc') and not d.get('actual_failure') and d['all_closed_sources_unchanged']
    assert d['actual_native_pin_and_R0_transform_match_exported_view'] and d['target']['pin']=='bit_1016'
    assert d['actual_adjacent_M6_OBS_intersections_at_same_size_first_cap'] and all(x['net']=='bit_1016' for x in d['actual_M6_metal_intersections_at_first_cap'])
    source=ROOT/'llsys_corner_fill/r01';sp=source/'execution.json';s=json.loads(sp.read_text())
    assert s.get('completed_utc') and s['fresh_DRC_count']==0 and s['all_closed_sources_unchanged']
    parent=ROOT/'common_checkpoint_def_import/corner-r01';pp=parent/'execution.json';p=json.loads(pp.read_text())
    assert p.get('completed_utc') and p['native_stages']['lower_route.stages.tsv']['lower_global_route']=='EXECUTED'
    assert p['native_stages']['lower_route.stages.tsv']['lower_detailed_route']=='FAIL'
    paths=[dp,sp,pp]+[source/n for n in ['routed.odb','routed.def','after.pins.tsv','after.cells.tsv','after.pdn.tsv','after.die.tsv']]
    paths +=[diagnosis/n for n in ['actual_local_signal_and_parent_OBS.json.gz','actual_complete_target_high_geometry.json.gz']]
    for f in paths:
        if f.parent==source and f.name!='execution.json':assert sha(f)==s['files'][f.name]['sha256']
        if f.parent==diagnosis and f.name!='execution.json':assert sha(f)==d['files'][f.name]['sha256']
    out=ROOT/'parent1016_actual_m5_repair'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(f):sha(f) for f in paths};r={'scope':'ACTUAL_SINGLE_PIN_M5_WIRE_SUPPORTED_RELOCATION_AND_FRESH_PARENT_AP_NOT_FULL_SYSTEM',
       'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
       'full_qualification':False,'native_returncodes':{},'new_cells_sizes_vias_wires_or_original_OBS_changes':0,
       'original13507_signal_pins_and_M5_M6_layers_sizes_function_networks':'MUST_REMAIN_EXCEPT_EXPLICIT_BIT1016_XY',
       'original_allowed_layers':'leaf signal M2-M8 / clock M4-M8; parent signal M2-M10 / clock M4-M10',
       'new_RC_STA_model':'NOT_EXECUTED; geometry-only parent AP, do not use old timing model as a newly extracted model',
       'historical_parent_targets':'PARTIAL_OR_UNKNOWN_RETAINED; no original target reassigned'}
    save=lambda:(out/'execution.json').write_text(json.dumps(r,indent=2)+'\n');save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    def native(label,body,threads=4):
        script=out/(label+'.tcl');script.write_text(helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')+'\n'+body+'\n')
        r['native_returncodes'][label]=execute(common,script,out/(label+'.log'),'PINXY_OUTPUT='+str(out),threads=threads);save()
        assert r['native_returncodes'][label]==0,label+' native failure'
    try:
        local=json.loads(gzip.decompress((diagnosis/'actual_local_signal_and_parent_OBS.json.gz').read_bytes()).decode())
        own=json.loads(gzip.decompress((diagnosis/'actual_complete_target_high_geometry.json.gz').read_bytes()).decode())
        oldbox=tuple(int(d['target'][k]) for k in ['x0','y0','x1','y1']);cx=(oldbox[0]+oldbox[2])//2;cy=(oldbox[1]+oldbox[3])//2
        contains=lambda a,b:a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3]
        supports=[x for x in own if x['layer']=='metal5' and x['kind'] in ['WIRE','VIA']]
        assert any(contains(x['box_DBU'],oldbox) for x in supports),'Old BPin material requires actual retention WIRE; do not silently erase it'
        # Bind reusable actual leaf/parent PG to byte-identical current PDN.
        oldleaf=ROOT/'llsys_wire_pin_retention/r01';assert sha(source/'after.pdn.tsv')==sha(oldleaf/'after.pdn.tsv')
        oldparent=ROOT/'common_checkpoint_def_import/r01';assert sha(parent/'after.pdn.tsv')==sha(oldparent/'after.pdn.tsv')
        assert sha(parent/'after.instances.tsv')==sha(oldparent/'after.instances.tsv')
        for folder,name in [('llsys_residual_access_preflight/r01','actual_high_PG_OBS.tsv'),('parent_pg_llsys_local/r01','actual_parent_PG_local.tsv')]:
            folder=ROOT/folder;qp=folder/'execution.json';qq=json.loads(qp.read_text());data=folder/name
            assert qq.get('completed_utc') and qq['all_closed_sources_unchanged'] and sha(data)==qq['files'][name]['sha256']
            original_odb=(oldparent/'imported_current_NOT_ROUTED_NOT_FROZEN.odb') if name=='actual_parent_PG_local.tsv' else oldleaf/'routed.odb'
            original_receipt=json.loads((original_odb.parent/'execution.json').read_text())
            assert qq['source_SHA'][str(original_odb)]==original_receipt['files'][original_odb.name]['sha256']
            inputs.update({str(f):sha(f) for f in [qp,data]})
            for x in csv.DictReader(data.open(),delimiter='\t'):
                b=tuple(int(x[k]) for k in ['x0','y0','x1','y1'])
                if b[0]<=cx+100000 and b[2]>=cx-100000 and b[1]<=cy+100000 and b[3]>=cy-100000:local.append({'net':x['net'],'layer':x['layer'],'kind':x['kind'],'box_DBU':b})
        viaq=ROOT/'all_llsys_first_hop_audit/r01/execution.json';v=json.loads(viaq.read_text());assert v.get('completed_utc') and v['all_closed_sources_unchanged'];vias=v['actual_via_templates'];inputs[str(viaq)]=sha(viaq)
        tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';inputs[str(tech)]=sha(tech);text=tech.read_text();rules={}
        for ly in ['metal5','metal6','via5']:
            block=re.search(r'^LAYER '+ly+r'\s.*?^END '+ly,text,re.M|re.S)[0]
            if ly=='via5':rules[ly]=round(float(re.search(r'\bSPACING\s+([\d.]+)',block)[1])*2000);continue
            table=re.search(r'SPACINGTABLE\s+PARALLELRUNLENGTH(.*?);',block,re.S)[1].splitlines();ps=[round(float(x)*2000) for x in table[0].split()];rows=[]
            for line in table[1:]:
                z=line.split()
                if z and z[0]=='WIDTH':rows.append((round(float(z[1])*2000),[round(float(x)*2000) for x in z[2:]]))
            rules[ly]=(ps,rows)
        for line in (source/'after.pins.tsv').open():
            z=line.split()
            if len(z)!=9 or z[2] in ['POWER','GROUND'] or z[0].strip('{}')=='bit_1016':continue
            b=tuple(map(int,z[5:9]));x=(b[0]+b[2])//2;y=(b[1]+b[3])//2
            if abs(x-cx)>102000 or abs(y-cy)>102000:continue
            local.append({'net':z[3].strip('{}'),'layer':z[4],'kind':'ACTUAL_ORIGINAL_BPIN','box_DBU':b})
            for ly,b in vias['via5_0' if z[4]=='metal5' else 'via6_0'].items():local.append({'net':z[3].strip('{}'),'layer':ly,'kind':'RESERVED_OTHER_FIRST_HOP_NOT_INSTALLED','box_DBU':tuple(v+(x if i%2==0 else y) for i,v in enumerate(b))})
        def blockers(x,y):
            hits=[]
            for ly,z in vias['via5_0'].items():
                a=tuple(v+(x if i%2==0 else y) for i,v in enumerate(z))
                for other in local:
                    if other['layer']!=ly or (ly=='metal5' and other['kind']=='ACTUAL_EXPORTED_MACRO_OBS'):continue
                    b=tuple(other['box_DBU']);same=other['net']=='bit_1016'
                    if same and (ly=='metal5' or (ly=='via5' and a==b)):continue
                    dx=max(a[0]-b[2],b[0]-a[2],0);dy=max(a[1]-b[3],b[1]-a[3],0)
                    if dx>3000 or dy>3000:continue
                    if ly=='via5':need=rules[ly]
                    else:
                        width=max(min(a[2]-a[0],a[3]-a[1]),min(b[2]-b[0],b[3]-b[1]));ps,rows=rules[ly]
                        prl=max(0,min(a[3],b[3])-max(a[1],b[1])) if dx and not dy else max(0,min(a[2],b[2])-max(a[0],b[0])) if dy and not dx else 0
                        need=max((p for p in rows if p[0]<=width),key=lambda p:p[0])[1][max(i for i,p in enumerate(ps) if p<=prl)]
                    if dx*dx+dy*dy<need*need:hits.append({'layer':ly,'net':other['net'],'kind':other['kind'],'box_DBU':b,'spacing_DBU':need})
            return hits
        candidates=set()
        for z in supports:
            b=z['box_DBU'];lo=max(b[0]+140,cx-100000);hi=min(b[2]-140,cx+100000);low=max(b[1]+140,cy-100000);high=min(b[3]-140,cy+100000)
            for ix in range(math.ceil((lo-190)/560),math.floor((hi-190)/560)+1):
                for iy in range(math.ceil((low-140)/560),math.floor((high-140)/560)+1):candidates.add((190+ix*560,140+iy*560))
        r['old_first_hop_blockers']=blockers(cx,cy);chosen=None;tested=[]
        for x,y in sorted(candidates,key=lambda xy:(abs(xy[0]-cx)+abs(xy[1]-cy),xy)):
            hits=blockers(x,y);tested.append({'center_DBU':[x,y],'blocking_pairs':len(hits)})
            if not hits:chosen=(x,y);break
        r['source_bound_own_M5_candidates_examined']=tested;save();assert chosen,'No strict parent-OBS-clear own M5 point within measured50um; do not invent a route'
        x,y=chosen;newbox=(x-140,y-140,x+140,y+140);assert chosen!=(cx,cy) and any(contains(z['box_DBU'],newbox) for z in supports)
        r['actual_requested_XY']={'pin':'bit_1016','layer':'metal5','original_box_DBU':oldbox,'new_box_DBU':newbox,'L1_um':(abs(x-cx)+abs(y-cy))/2000.,'old_and_new_BPin_fully_covered_by_preexisting_own_metal':True};save()
        shutil.copyfile(str(source/'after.pins.tsv'),str(out/'before.pins.tsv'))
        body='read_db '+tcl(source/'routed.odb')+'\nset ::env(PINXY_ACCESS_ALL) 0\nset ::env(PINXY_ACCESS_NET_NAMES) {bit_1016}\nset ::env(PINXY_ACCESS_OUT) '+tcl(out/'before_target.tsv.gz')+'\nsource '+tcl(DRIVER/'export_access.tcl')+'\n'
        body+='if {![stage actual_M5_pin_relocation {place_pin -pin_name bit_1016 -layer metal5 -location {'+str(x/2000.)+' '+str(y/2000.)+'} -pin_size {.14 .14}}]} {close $stages;exit 1}\n'
        body+='fingerprint '+tcl(out/'after')+'\nwrite_db '+tcl(out/'routed.odb')+'\nwrite_def '+tcl(out/'routed.def')+'\nset ::env(PINXY_ACCESS_OUT) '+tcl(out/'after_target.tsv.gz')+'\nsource '+tcl(DRIVER/'export_access.tcl')+'\nclose $stages'
        native('actual_edit',body)
        r['complete_pin_contract']=pin_contract(out,{'bit_1016':('metal5',list(newbox))},13507)
        r['all_cells_connections_PG_die_exact']={k:sha(source/('after.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']};assert all(r['all_cells_connections_PG_die_exact'].values())
        r['native_DEF_NETS_byte_identical']=def_nets_digest(source/'routed.def')==def_nets_digest(out/'routed.def');assert r['native_DEF_NETS_byte_identical']
        def conductors(path):
            with gzip.open(str(path),'rt') as f:return Counter(tuple(x[k] for k in ['net','layer','x0','y0','x1','y1','kind']) for x in csv.DictReader(f,delimiter='\t') if x['kind'] in ['WIRE','VIA'])
        r['actual_target_WIRE_VIA_exact']=conductors(out/'before_target.tsv.gz')==conductors(out/'after_target.tsv.gz');assert r['actual_target_WIRE_VIA_exact']
        r['actual_changed_net_geometry']=check(out/'after_target.tsv.gz',True);assert r['actual_changed_net_geometry']['pass']
        native('fresh_leaf_DRC','read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\nwrite_abstract_lef -bloat_factor 0 '+tcl(out/'detailed.lef')+'\nclose $stages')
        r['fresh_leaf_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M));assert r['fresh_leaf_DRC_count']==0
        r['conservative_parent_OBS']=coarsen(out/'detailed.lef',out/'parent.lef',requested=('metal1','metal2','metal3'))
        master=next(line.split()[1] for line in (out/'detailed.lef').open() if line.startswith('MACRO '));alias_stream(out/'parent.lef',out/'p126resume_llaccel_aux.lef',master,'p126resume_llaccel_aux')
        readlefs=[line for line in (parent/'fresh_import.tcl').read_text().splitlines() if line.startswith('read_lef ')]
        assert len(readlefs)==8;old='read_lef '+tcl(parent/'p126resume_llaccel_aux.lef');assert readlefs.count(old)==1
        readlefs=[('read_lef '+tcl(out/'p126resume_llaccel_aux.lef')) if line==old else line for line in readlefs]
        body='\n'.join(readlefs+['read_def '+tcl(parent/'current_fixed.def'),'set_routing_layers -signal metal2-metal10 -clock metal4-metal10',
            'stage full_parent_AP {pin_access}','close $stages'])
        # Native stage wrapper catches and preserves the actual first failure.
        native('fresh_parent_AP',body)
        text=(out/'fresh_parent_AP.log').read_text();r['parent_AP_no_access_counters']={k:int(v) for k,v in re.findall(r'^#(\w*NoAp)\s*=\s*(\d+)',text,re.M)}
        r['parent_AP_stage_executed']='STAGE_EXECUTED full_parent_AP' in text and bool(r['parent_AP_no_access_counters']) and not any(r['parent_AP_no_access_counters'].values())
        r['parent_AP_errors']=[line for line in text.splitlines() if '[ERROR ' in line or 'STAGE_FAIL full_parent_AP' in line]
    except Exception:r['actual_failure']=traceback.format_exc();traceback.print_exc()
    r['all_closed_sources_unchanged']=all(sha(Path(f))==v for f,v in inputs.items());r['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r['native_stages']={f.name:{x['stage']:x['status'] for x in csv.DictReader(f.open(),delimiter='\t')} for f in out.glob('*stages.tsv')}
    r['files']={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.iterdir() if f.is_file() and f.name!='execution.json'};save()
    return int(bool(r.get('actual_failure')) or not r['all_closed_sources_unchanged'] or not r.get('parent_AP_stage_executed'))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
