"""Install the closed 209-output CEC slice in the actual VECTOR ODB.

This stage produces an explicitly NOT_ROUTED checkpoint. It preserves every
old state/clock cell, outside-cone connection and original pin rectangle. The
extra combinational gates are a separately costed ECO, never a pure XY gain.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,datetime,gzip,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_vector_resume import COST_PROC
from run_current_driver_sizing import read_cells
from verify_mapped_eco import load,export_graph
from cell_semantics import groups

DRIVER=Path(__file__).resolve().parent
LIB='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'


def run(revision):
    src=ROOT/'vector_resume/r01';odb=src/'routed.odb'
    assert sha(odb)=='243c1025646eb8b41b00e8257b78484b458d4eff250fa0b09ce32bc3fe7682d9'
    ce=ROOT/'vector_slice_map_CEC/r01';cq=json.loads((ce/'execution.json').read_text())
    assert cq.get('completed_utc') and not cq.get('actual_failure') and cq['all_closed_sources_unchanged']
    assert cq['relative_combinational_equivalence'].startswith('PASS_ALL209')
    mapped=ROOT/'vector_critical_cone_remap/r03';mq=json.loads((mapped/'execution.json').read_text())
    paths=[mapped/n for n in ['boundary_binding.json.gz','remapped.json','reference.blif','remapped.v']]
    for p in paths:assert sha(p)==mq['files'][p.name]['sha256']
    ref=ROOT/'vector_clone_probe/r03';rq=json.loads((ref/'execution.json').read_text())
    assert rq['source_SHA'][str(odb)]==sha(odb) and rq['native_returncodes']['source_graph']==0
    paths += [ref/n for n in ['source.tsv.gz','before.cell_cost.tsv','before.cells.tsv','before.pins.tsv','before.pdn.tsv','before.die.tsv']]
    for p in paths[4:]:assert sha(p)==rq['files'][p.name]['sha256']
    paths += [odb,src/'execution.json',ce/'execution.json',mapped/'execution.json',ref/'execution.json']
    inputs={str(p):sha(p) for p in paths}
    out=ROOT/'vector_verified_slice_install'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_VERIFIED_COMBINATIONAL_SLICE_INSTALL_AND_LEGALIZATION_NOT_ROUTED_OR_STA_QUALIFIED',
         'source_SHA':inputs,'scheduler_job':os.environ['SLURM_JOB_ID'],
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'relative_CEC_receipt':str(ce/'execution.json'),'native_returncodes':{},
         'full_qualification':False,'route_RC_STA':'NOT_EXECUTED',
         'pipeline_protocol_cache_state_and_interface_change':False,
         'costs':'Additional gate mapping and identity buffers recorded separately from pin XY',
         'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        binding=json.loads(gzip.open(str(mapped/'boundary_binding.json.gz'),'rt').read())
        assert not binding['arbitrary_original_floating_inputs_modeled_as_independent_inputs']
        selected=set(binding['all_selected_original_instances']);protected=set(binding['all_original_state_instances_and_clock_cone_instances_protected'])
        assert len(selected)==351 and not selected&protected
        masters,terms,ports=load(ref/'source.tsv.gz');before,bt=read_cells(ref/'before.cells.tsv')
        assert selected<=set(masters) and protected<=set(masters)
        mod=json.loads((mapped/'remapped.json').read_text())['modules']['hpy_vector_cut']
        ci,co=mod['ports']['CI'],mod['ports']['CO'];ins=binding['input_bits_to_original_net'];outs=binding['output_bits_to_original_net']
        assert ci['direction']=='input' and co['direction']=='output' and len(ci['bits'])==len(ins)==396 and len(co['bits'])==len(outs)==209
        assert len(set(ci['bits']))==396 and len(set(ins))==396 and len(set(outs))==209
        raw=subprocess.check_output(common+[IMAGE,'cat',LIB]);models=dict(groups(raw.decode(),'cell'))
        import hashlib
        assert hashlib.sha256(raw).hexdigest()=='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
        bits=dict(zip(ci['bits'],ins));cells={};alias=[]
        for bit,net in zip(co['bits'],outs):
            if bit not in bits:bits[bit]=net
            elif bits[bit]!=net:alias.append((bits[bit],net))
        hardware={n:c for n,c in mod['cells'].items() if c['type']!='$scopeinfo'}
        metadata={n:c for n,c in mod['cells'].items() if c['type']=='$scopeinfo'}
        assert len(hardware)==cq['actual_mapped_hardware_cells']==612 and len(metadata)==351
        assert all(not c.get('connections') and not c.get('port_directions') for c in metadata.values())
        all_net_names={net for direction,net in terms.values()}|{net for direction,net in ports.values()}
        for c in hardware.values():
            assert c['type'] in models and not list(groups(models[c['type']],'ff')) and not list(groups(models[c['type']],'latch'))
            for bb in c['connections'].values():
                assert len(bb)==1 and isinstance(bb[0],int),'Constant handling requires explicit real tie cell; no fabricated ties'
                bit=bb[0]
                if bit not in bits:bits[bit]='HPY_VEC_MAP_NET_'+str(bit)
        for net in bits.values():
            if net.startswith('HPY_VEC_MAP_NET_'):assert net not in all_net_names
        for k,c in enumerate(sorted(hardware.values(),key=lambda c:(c['type'],str(c['connections'])))):
            name='HPY_VEC_MAP_GATE_%04d'%k;assert name not in masters
            cells[name]={'master':c['type'],'ports':{p:bits[v[0]] for p,v in c['connections'].items()},'directions':c['port_directions']}
        # Alias outputs retain separate original boundary net objects via real
        # identity gates. This avoids accidentally merging other cone fanouts.
        netdriver={}
        for (inst,pin),(direction,net) in terms.items():
            if direction=='OUTPUT':netdriver[net]=inst
        for k,(a,z) in enumerate(alias):
            oldmaster=masters[netdriver[z]][0];strength=int(oldmaster.rsplit('_X',1)[1])
            family=sorted((int(n.rsplit('_X',1)[1]),n) for n in models if n.startswith('BUF_X'))
            candidates=[n for st,n in family if st>=strength];assert candidates
            name='HPY_VEC_MAP_ALIAS_%04d'%k;assert name not in masters
            cells[name]={'master':candidates[0],'ports':{'A':a,'Z':z},'directions':{'A':'input','Z':'output'}}
            buf=dict(groups(models[candidates[0]],'pin'))['Z'];assert 'function' in buf and '"A"' in buf
        expected={}
        for n,c in cells.items():
            for p,net in c['ports'].items():expected[(n,p)]=(c['directions'][p].upper(),net)
        touched={net for (inst,pin),(direction,net) in terms.items() if inst in selected and net!='NULL'}
        touched.update(net for c in cells.values() for net in c['ports'].values())
        assert 'bit_2' not in touched,'Never remap native original clock'
        # Actual external drivers/sinks anchor a local barycentric placement.
        costs={r['instance']:r for r in csv.DictReader((ref/'before.cell_cost.tsv').open(),delimiter='\t')}
        xy={n:(float(r['x_dbu']),float(r['y_dbu'])) for n,r in costs.items()}
        selected_center=tuple(sum(xy[n][i] for n in selected)/len(selected) for i in [0,1])
        ext=defaultdict(list)
        for (inst,pin),(direction,net) in terms.items():
            if inst not in selected and inst in xy and net in touched:ext[net].append(xy[inst])
        netcells=defaultdict(set)
        for n,c in cells.items():
            for net in c['ports'].values():netcells[net].add(n)
        poses={n:selected_center for n in cells}
        for _ in range(80):
            updated={}
            for n,c in cells.items():
                anchors=[]
                for net in c['ports'].values():anchors.extend(ext[net]);anchors.extend(poses[j] for j in netcells[net] if j!=n)
                updated[n]=tuple(sum(v[i] for v in anchors)/len(anchors) for i in [0,1]) if anchors else poses[n]
            poses=updated
        plan={'source_ODB':str(odb),'selected_old_instances':sorted(selected),'protected_instances':sorted(protected),
              'new_cells':cells,'initial_location_DBU':poses,'original_boundary_inputs':ins,'original_boundary_outputs':outs,
              'alias_identity_buffer_count':len(alias),'all_touched_signal_nets':sorted(touched)}
        (out/'actual_install_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        rec.update({'selected_old_cells':len(selected),'new_combinational_cells':len(hardware),'new_identity_buffers':len(alias),'new_total_cells':len(cells),'touched_nets':len(touched)});save()
        # Replayable edit body for an incremental router starting from the
        # original routed checkpoint, not a final-LEF-only modification.
        body=['set b [ord::get_db_block];set old_statuses [dict create];set filler_masters {}',
              'foreach i [$b getInsts] {if {[[$i getMaster] getType] eq "CORE_SPACER"} {lappend filler_masters [[$i getMaster] getName]} else {dict set old_statuses [$i getName] [$i getPlacementStatus]}}',
              'set filler_masters [lsort -unique $filler_masters];remove_fillers']
        for n in sorted(selected):
            body+=['set i [$b findInst '+tcl(n)+'];if {$i eq "NULL" || [[$i getMaster] getName] ne '+tcl(masters[n][0])+'} {error "Source cone cell mismatch"};odb::dbInst_destroy $i']
        boundary=set(ins)|set(outs)
        for net in sorted(touched):
            if net in boundary:continue
            body+=['set nn [$b findNet '+tcl(net)+'];if {$nn ne "NULL" && ![llength [$nn getITerms]] && ![llength [$nn getBTerms]]} {odb::dbNet_destroy $nn}']
        newnets=sorted({net for c in cells.values() for net in c['ports'].values()})
        for net in newnets:body+=['set nn [$b findNet '+tcl(net)+'];if {$nn eq "NULL"} {set nn [odb::dbNet_create $b '+tcl(net)+'];$nn setSigType SIGNAL}']
        for n,c in sorted(cells.items()):
            body+=['set m [[ord::get_db] findMaster '+tcl(c['master'])+'];if {$m eq "NULL" || [$b findInst '+tcl(n)+'] ne "NULL"} {error "New master missing or name collision"};set i [odb::dbInst_create $b $m '+tcl(n)+']']
            for pin,net in sorted(c['ports'].items()):body+=['set tt [$i findITerm '+tcl(pin)+'];if {$tt eq "NULL"} {error "Mapped pin absent"};$tt connect [$b findNet '+tcl(net)+']']
        body+=['add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power','add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground','global_connect']
        (out/'replay_install.tcl').write_text('\n'.join(body)+'\n')
        place=body+['dict for {name status} $old_statuses {set i [$b findInst $name];if {$i ne "NULL"} {$i setPlacementStatus LOCKED}}','set rows [$b getRows];if {![llength $rows]} {error "No real placement rows"}']
        for n,(x,y) in sorted(poses.items()):
            place+=['set best {};set distance 1e30;foreach row $rows {lassign [$row getOrigin] rx ry;set dd [expr {abs($ry-'+str(round(y))+')}];if {$dd<$distance} {set distance $dd;set best $row}};lassign [$best getOrigin] rx ry;set sw [[$best getSite] getWidth];set xx [expr {$rx+round(('+str(round(x))+'-$rx)/double($sw))*$sw}];set i [$b findInst '+tcl(n)+'];$i setOrient [$best getOrient];$i setLocation $xx $ry;$i setPlacementStatus PLACED']
        place+=['if {![stage actual_slice_legalization {detailed_placement -use_diamond_legalizer;check_placement -verbose}]} {catch {write_db '+tcl(out/'failed_install.odb')+'};close $stages;exit 1}',
                'dict for {name status} $old_statuses {set i [$b findInst $name];if {$i ne "NULL"} {$i setPlacementStatus $status}}',
                'set f [open '+tcl(out/'verified_new_cell_poses.tcl')+' w];puts $f {set mapped_replay {}}']
        for n in sorted(cells):place+=['set i [$b findInst '+tcl(n)+'];lassign [$i getLocation] x y;puts $f [list lappend mapped_replay [list [$i getName] [[$i getMaster] getName] $x $y [$i getPlacementStatus] [$i getOrient]]]']
        place+=['close $f','fingerprint '+tcl(out/'placed'),'cell_cost '+tcl(out/'placed.cell_cost.tsv'),
                'write_db '+tcl(out/'placed_NOT_ROUTED.odb'),'write_def '+tcl(out/'placed_NOT_ROUTED.def'),'write_verilog '+tcl(out/'placed_NOT_ROUTED.v'),'close $stages']
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        script=out/'install.tcl';script.write_text(helper+'\n'+COST_PROC+'\nread_db '+tcl(odb)+'\n'+'\n'.join(place)+'\n')
        rec['native_returncodes']['actual_install_and_legalization']=execute(common,script,out/'install.log','PINXY_OUTPUT='+str(out),threads=4);save()
        assert rec['native_returncodes']['actual_install_and_legalization']==0
        rec['native_returncodes']['fresh_actual_installed_graph']=export_graph(common,out/'placed_NOT_ROUTED.odb',out,'installed');save();assert rec['native_returncodes']['fresh_actual_installed_graph']==0
        am,at,ap=load(out/'installed.tsv.gz')
        unselected=set(masters)-selected
        assert set(am)==unselected|set(cells)
        assert all(am[n]==masters[n] for n in unselected)
        assert {k:v for k,v in at.items() if k[0] in unselected}=={k:v for k,v in terms.items() if k[0] in unselected}
        assert {k:v for k,v in at.items() if k[0] in cells}==expected
        assert ap==ports and all(am[n][0]==c['master'] for n,c in cells.items())
        after,a_terms=read_cells(out/'placed.cells.tsv')
        assert all(after[n]==before[n] for n in unselected),'Old nonfiller master/location/orientation/status changed'
        preserved={k:sha(ref/('before.'+k+'.tsv'))==sha(out/('placed.'+k+'.tsv')) for k in ['pins','pdn','die']};assert all(preserved.values())
        actualcost={r['instance']:r for r in csv.DictReader((out/'placed.cell_cost.tsv').open(),delimiter='\t')}
        rec['relative_actual_graph_matches_closed_CEC_plus_identity_buffers']=True
        rec['all_original_interfaces_PG_die_unchanged']=preserved
        rec['all_old_unselected_state_clock_instances_connections_and_poses_preserved']=True
        rec['separate_mapping_cost']={'removed_cells':len(selected),'new_cells':len(cells),'net_added_cells':len(cells)-len(selected),
          'removed_master_area_um2':sum(float(costs[n]['area_um2']) for n in selected),
          'new_master_area_um2':sum(float(actualcost[n]['area_um2']) for n in cells),'old_unselected_cells_moved':0,'block_outline_unchanged':True}
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'])


if __name__=='__main__':sys.exit(run(sys.argv[1]))
