"""Actual three-pin native routing ECO on complete internal C; all gates retained."""
from pathlib import Path
from collections import Counter
import csv,datetime,gzip,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check
from compare_native_route_representations import routing_box_hashes

DRIVER=Path(__file__).resolve().parent
TARGETS={'bit_1382013':('metal5',[3647330,1367520,3647610,1367800]),
         'bit_6907':('metal6',[2954610,1366400,2954890,1366680]),
         'bit_1389626':('metal6',[3713970,1161600,3714250,1161880])}


def pin_contract(out,targets=TARGETS):
    def load(path):
        result={}
        for line in path.read_text().splitlines():
            r=line.split();assert len(r)==9
            if r[2] in ['POWER','GROUND']:continue
            assert r[0] not in result;result[r[0]]=r
        assert len(result)==13507
        return result
    a=load(out/'before.pins.tsv');b=load(out/'after.pins.tsv');assert set(a)==set(b)
    changes=[];data=[]
    for name in sorted(a):
        x,y=a[name],b[name];assert x[:5]==y[:5]
        old,new=list(map(int,x[5:])),list(map(int,y[5:]))
        assert old[2]-old[0]==new[2]-new[0]==280 and old[3]-old[1]==new[3]-new[1]==280
        if old!=new:
            changes.append(name);layer,want=targets[name];assert y[4]==layer and new==want
        row=dict(zip(['pin','direction','use','net','layer'],x[:5]))
        for prefix,box in [('source',old),('actual',new)]:
            for key,value in zip(['x0_um','y0_um','x1_um','y1_um'],box):row[prefix+'_'+key]=value/2000.
        row['changed_from_complete_PG_C']=old!=new;data.append(row)
    assert set(changes)==set(targets)
    with (out/'all_13507_actual_pin_correspondence.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    # PG terminal shapes are checked separately, never treated as signal pins.
    pg=lambda p:[s for s in p.read_text().splitlines() if s.split()[2] in ['POWER','GROUND']]
    assert pg(out/'before.pins.tsv')==pg(out/'after.pins.tsv')
    return {'all_signal_pins':13507,'only_changed_XY_pins':sorted(changes),
            'all_functions_directions_networks_layers_sizes_and_PG_preserved':True,
            'full_internal_C_retained':'Complete 13184-move internal C retained; only explicitly listed existing internal points corrected',
            'source_or_target_parent_layers':'Historical mapping still partial/unknown; no new target layer assigned'}


def run(revision,profile='three_pin'):
    assert profile in ['three_pin','parent_noap'];noap=profile=='parent_noap'
    targets={'bit_1025':('metal5',[706770,2129120,707050,2129400])} if noap else TARGETS
    edit_stage='actual_one_net_pin_and_route_edit' if noap else 'actual_three_net_pin_and_route_edit'
    source=ROOT/('llsys_actual_via_tips/r02' if noap else 'finalized/llsys-pg-r03/llaccel_aux-C');prior=json.loads((source/'execution.json').read_text())
    diagnosis=ROOT/('llsys_noap_context/r01/execution.json' if noap else 'llsys_DRC_diagnosis/r01/execution.json');diag=json.loads(diagnosis.read_text())
    if noap:
        assert prior['native_returncodes']['actual_edit_and_analysis']==prior['native_returncodes']['fresh_DRC']==0 and prior['fresh_DRC_count']==0
        assert diag['native_read_only_returncode']==0 and diag['candidate_own_actual_via_cap_DBU']==targets['bit_1025'][1]
    else:assert prior['independent_DRC_returncode']==0 and prior['independent_DRC_count']==4
    assert diag['all_closed_sources_unchanged'] and all(sha(Path(p))==s for p,s in diag['source_SHA'].items())
    odb=source/('routed.odb' if noap else 'clean.odb');geometry=source/'whole_access.tsv.gz'
    for p in [odb,geometry]:assert sha(p)==prior['files'][p.name]['sha256']
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    inputs={str(p):sha(p) for p in [source/'execution.json',diagnosis,odb,geometry,trial,sdc]}
    out=ROOT/('llsys_parent_access_tip' if noap else 'llsys_actual_via_tips')/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_INTERNAL_C_PIN_VIA_TIP_ROUTE_ECO_NOT_FULL_QUALIFICATION','profile':profile,
         'source_SHA':inputs,'source_native_DRC_count':0 if noap else 4,'native_returncodes':{},
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'source_kind':'Complete 13507-pin PG-only C alternative; does not replace active full-window 92690/92691',
         'edit':'Move only source-bound listed M5/M6 pins onto existing same-net via landings; remove exactly three bit_1025 terminal wire rectangles.' if noap else 'Move three M5/M6 pins onto actual same-net original via landings; remove exactly eight terminal wire rectangles; preserve every original via definition and location.',
         'new_cells_or_sizes':0,'GRT_or_DRT_search_reexecuted':False,
         'actual_implementation':'Native OpenDB wire encoder; not final LEF/plot editing',
         'full_qualification':False,'historical_parent_target_layers':'PARTIAL_OR_UNKNOWN_UNCHANGED',
         'new_parent_access_GDS_RTL':'NOT_EXECUTED'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
            '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
            '--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        rec['original_container_library_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',lib]).decode().split()[0]
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        contracts=(DRIVER/'output_chain_placement.tcl').read_text().split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
        lines=[helper,contracts]+['read_liberty '+tcl(p) for p in old['libs']]
        lines+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set_routing_layers -signal metal2-metal8 -clock metal4-metal8','fingerprint '+tcl(out/'before'),
          'set original_obs [obs_snapshot]',
          'if {![stage '+edit_stage+' {source '+tcl(DRIVER/('llsys_move_noap_to_actual_tip.tcl' if noap else 'llsys_move_to_actual_via_tips.tcl'))+'}]} {catch {write_db '+tcl(out/'failed_edit.odb')+'};close $stages;exit 1}',
          'if {[obs_snapshot] ne $original_obs} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
          'write_verilog '+tcl(out/'mapped.v'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}',
          'close $stages']
        script=out/'edit.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['actual_edit_and_analysis']=execute(common,script,out/'native.log',env,threads=4);save()
        if (out/'routed.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():
            rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
            a,_=routing_box_hashes(geometry,725253);b,_=routing_box_hashes(out/'whole_access.tsv.gz',725253)
            assert set(a)==set(b);changed={n for n in a if a[n]!=b[n]};assert changed==set(targets)
            rec['all_other_multiterminal_route_box_multisets_identical']=True
            rec['unchanged_multiterminal_nets']=725253-len(targets)
            if not noap:rec['all_other_725250_multiterminal_route_box_multisets_identical']=True
            # Via geometry multiplicities on all edited nets must be exactly
            # unchanged; wire segmentation/link IDs are not a geometry proof.
            def material(path):
                result=Counter()
                with gzip.open(path,'rt') as f:
                    for r in csv.DictReader(f,delimiter='\t'):
                        if r['net'] in targets and r['kind'] in ['WIRE','VIA']:result[tuple(r[k] for k in ['net','kind','layer','x0','y0','x1','y1'])]+=1
                return result
            before=material(geometry);after=material(out/'whole_access.tsv.gz')
            removed=[('bit_1382013','metal5',3628710,1367380,3629690,1367660),
                     ('bit_1382013','metal5',3629410,1367380,3629690,1367800),
                     ('bit_1382013','metal5',3629410,1367520,3647610,1367800),
                     ('bit_6907','metal6',2956570,1367520,2956850,1368280),
                     ('bit_6907','metal6',2954610,1368000,2956850,1368280),
                     ('bit_6907','metal6',2954610,1366400,2954890,1368280),
                     ('bit_1389626','metal6',3713830,1161300,3714250,1161580),
                     ('bit_1389626','metal6',3713970,1161300,3714250,1161880)]
            if noap:removed=[('bit_1025','metal5',707330,2128980,707750,2129260),('bit_1025','metal5',707330,2128980,707610,2129400),('bit_1025','metal5',706770,2129120,707610,2129400)]
            want=Counter((r[0],'WIRE',r[1])+tuple(map(str,r[2:])) for r in removed)
            assert not after-before and before-after==want
            rec['exact_expected_actual_WIRE_rectangles_removed_no_added_wire_or_via_material']=len(removed)
            if not noap:rec['exactly_eight_actual_WIRE_rectangles_removed_no_added_wire_or_via_material']=True
            rec['all_actual_target_via_rectangle_multisets_preserved']=True
        if (out/'after.pins.tsv').exists():rec['complete_pin_contract']=pin_contract(out,targets)
        rec['all_cells_signal_connections_PG_die_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']}
        for kind in ['setup','hold']:
            p=out/(kind+'.txt')
            if p.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text())[1])
        if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
        if (out/'stages.tsv').exists():
            with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
        rec['container_library_unchanged']=subprocess.check_output(common+[IMAGE,'sha256sum',lib]).decode().split()[0]==rec['original_container_library_SHA256']
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    passed=('actual_failure' not in rec and rec['native_returncodes'].get('actual_edit_and_analysis')==0 and rec.get('fresh_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and all(rec.get('all_cells_signal_connections_PG_die_unchanged',{}).values()) and rec.get('all_other_multiterminal_route_box_multisets_identical') and rec.get('all_actual_target_via_rectangle_multisets_preserved') and rec.get('complete_pin_contract') and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and rec.get('container_library_unchanged') and rec['all_closed_sources_unchanged'] and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['VDD','VSS','rcx','sta','whole_signal_geometry']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
