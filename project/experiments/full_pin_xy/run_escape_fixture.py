"""Real fixed-layer access fixture around an unchanged ACT/GEMM macro.

All original macro ports/layers/rectangles stay unchanged. The 256 read-bus
bits selected by the common-prewire contract gain distinct PARENT M10 landing
ports through actual M2-M10 routing. Other parent ports overlap the unchanged
macro access rectangles. This is not a complete common base or a changed leaf
pin-layer definition. Independent native/whole geometry/PG gates are separate.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import csv, datetime, gzip, json, math, os, re, subprocess, sys, traceback
from run_exports import ROOT, IMAGE, BIN, sha
from run_parent_trial import child_source, tcl
from lef_view_contract import verify as verify_lef
from inventory import load, owner, pin_names
from check_access import check

DRIVER = Path(__file__).resolve().parent


def execute(common, script, log, env=None, threads=4):
    cmd = common + (['--env', env] if env else []) + [IMAGE, BIN, '-threads', str(threads), '-no_init', '-exit', str(script)]
    with log.open('x') as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    return r.returncode


def one(case, variant, revision):
    assert case in ['act', 'gemm', 'mxu'] and variant in ['Aopt', 'C']
    kind=os.environ.get('PINXY_CHILD_VIEW_KIND','legacy_verified')
    assert kind in ['legacy_verified','real_diode658']
    if kind=='real_diode658':
        assert (case,variant)==('gemm','C')
        model_dir=ROOT/'diode_views/r01/gemm-C';source=model_dir/'abstract.lef';proof_path=model_dir/'execution.json'
        proof=json.loads(proof_path.read_text());odb=model_dir/'clean.odb'
        assert proof.get('completed_utc') and proof['native_export_returncode']==proof['fresh_model_read_returncode']==0
        assert proof['matching_all_signal_model_pins']==3753 and proof['all_original_signal_and_PG_pins_and_size_exactly_preserved']
        assert proof['SPEF_replay_matches_source'] and proof['all_sources_and_pre_RCX_geometry_unchanged']
        for p in [odb,source,model_dir/'timing.lib',model_dir/'pins.tsv']:assert sha(p)==proof['files'][p.name]['sha256']
        assert sha(odb)==proof['source_geometry_sha256']
        actual_receipt=Path(proof['source_receipt']);assert sha(actual_receipt)==proof['source_receipt_SHA256']
        actual=json.loads(actual_receipt.read_text())
        assert actual.get('completed_utc') and actual['actual_total_real_diodes']==658 and actual['fresh_DRC_count']==0 and actual['whole_signal_geometry']['pass']
        # The original access windows are still valid only because every original
        # pin/PG rectangle was verified unchanged in this actual new view.
        access_trial_receipt=ROOT/'trials/access-r03/gemm-C/execution.json'
    else:
        source, proof, proof_path = child_source(case, variant)
        odb = source.parent/'clean.odb'
        model_revision=('r02' if variant == 'C' else 'r03')
        if variant=='C':model_revision=os.environ.get('PINXY_'+case.upper()+'_C_MODEL_REVISION',model_revision)
        model_dir = ROOT/'leaf_timing_models'/model_revision/(case+'-'+variant)
        model = json.loads((model_dir/'execution.json').read_text())
        assert model['status']=='NATIVE_EXTRACTED_MODEL_EXPORTED_NOT_QUALIFIED' and model['exact_all_signal_pin_direction_match']
        assert sha(model_dir/'timing.lib')==model['generated_library_sha256']
        assert model['source_clean_receipt_sha256'] == sha(proof_path)
        assert model['clean_odb_sha256'] == sha(odb) == proof['clean_odb_sha256']
        access_trial_receipt=Path(proof['legacy_RC_STA_receipt'])
    source_view_hashes={str(p):sha(p) for p in [odb,source,proof_path,model_dir/'execution.json',model_dir/'timing.lib',source.parent/'pins.tsv',access_trial_receipt]}
    if kind=='real_diode658':source_view_hashes[str(actual_receipt)]=sha(actual_receipt)
    out = ROOT/'escape_fixtures'/revision/(case+'-'+variant)
    out.mkdir(parents=True, exist_ok=False)
    rec = {'scope': 'REAL_256BIT_PARENT_M10_ESCAPE_FIXTURE; unchanged original leaf pins; NOT common-base/full system qualification',
           'case': case, 'variant': variant, 'source_clean_receipt': str(proof_path), 'source_clean_receipt_SHA': sha(proof_path),
           'source_clean_ODB_SHA': sha(odb), 'matching_research_model_SHA': sha(model_dir/'timing.lib'),
           'driver_commit': (DRIVER/'driver_commit.txt').read_text().strip(), 'scheduler_job': os.environ['SLURM_JOB_ID'],
           'full_qualification': False, 'source_leaf_STA_and_complete_rules': 'Inherited independent leaf reports remain mandatory; do not hide their failures',
           'new_parent_M10_ports_not_redefinitions_of_leaf_M5_M6': True}
    rec['source_view_kind']=kind;rec['closed_source_view_SHA256']=source_view_hashes
    rec['original_access_windows_receipt_only_not_current_leaf_STA_source']=str(access_trial_receipt)
    if kind=='real_diode658':rec['actual_658_leaf_receipt_SHA256']=sha(actual_receipt)
    common = ['singularity', 'exec', '--cleanenv', '--bind', str(ROOT/'tmp')+':/tmp', '--home', str(ROOT/'home'), '--pwd', str(out)]
    export = out/'export.tcl'
    export.write_text('read_db '+tcl(odb)+'\nwrite_abstract_lef -bloat_factor 0 '+tcl(out/'leaf_detail.lef')+'\n')
    assert execute(common, export, out/'export.log', threads=1) == 0
    rec['leaf_abstract_contract'] = verify_lef(source, out/'leaf_detail.lef')
    lef = (out/'leaf_detail.lef').read_text()
    master = re.findall(r'^MACRO\s+(\S+)', lef, re.M)
    assert len(master) == 1
    master = master[0]
    size = re.findall(r'^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', lef, re.M)
    assert len(size) == 1
    width, height = map(float, size[0])
    assert re.search(r'cell\s*\(\s*"?'+re.escape(master)+r'"?\s*\)', (model_dir/'timing.lib').read_text()), 'Native model/master mismatch'
    design = 'opentpu' if case in ['act','mxu'] else 'llaccel'
    graph = load(ROOT/'inputs/partition-r02'/(design+'_partition_graph.json.gz'))
    cell = next(c for inst,c in graph['top_module']['cells'].items() if owner(inst,design) == case)
    ports = graph['frontier'][cell['type']]['ports']
    bus = {'act':'r_data','mxu':'act_data','gemm':'gemm_a_rdata'}[case]
    selected = {bus+'['+str(i)+']' for i in range(256)}
    with (source.parent/'pins.tsv').open() as f:
        pins = {q['pin'].replace('\\',''): q for q in csv.DictReader(f,delimiter='\t') if q['use'] not in ['POWER','GROUND']}
    assert selected <= set(pins)
    assert {p for n,q in ports.items() for p in pin_names(n,q)} == set(pins)
    declarations = []
    for name,p in ports.items():
        assert not p.get('upto',0)
        n, off = len(p['bits']), p.get('offset',0)
        declarations.append(p['direction']+' wire '+('['+str(off+n-1)+':'+str(off)+'] ' if n>1 else '')+name)
    text = 'module escape_fixture(\n'+',\n'.join(declarations)+'\n);\n\\'+master+'  u_macro(\n'
    text += ',\n'.join('.'+n+'('+n+')' for n in ports)+'\n);\nendmodule\n'
    (out/'fixture.v').write_text(text)
    dx = dy = 89.6  # 8x11.2um preserves the real M4-M10 track phases.
    rec['parent_R0_translation_um']=[dx,dy]
    rec['track_phase_policy']='11.2um is the LCM of actual 0.28/0.8/1.6um M4-M10 tracks; original leaf geometry remains unchanged'
    die_w, die_h = math.ceil((width+2*dx)/.005)*.005, math.ceil((height+2*dy)/.005)*.005
    setup = [
        'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef',
        'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef',
        'read_lef '+tcl(out/'leaf_detail.lef'),
        'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
        'read_liberty '+tcl(model_dir/'timing.lib'), 'read_verilog '+tcl(out/'fixture.v'), 'link_design escape_fixture',
        'initialize_floorplan -die_area {0 0 '+str(die_w)+' '+str(die_h)+'} -core_area {10 10 '+str(die_w-10)+' '+str(die_h-10)+'} -site FreePDK45_38x28_10R_NP_162NW_34O',
        'source /OpenROAD-flow-scripts/flow/platforms/nangate45/make_tracks.tcl',
        'place_macro -macro_name u_macro -location {'+str(dx)+' '+str(dy)+'} -orientation R0 -exact',
        'cut_rows -halo_width_x 2 -halo_width_y 2',
        'add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power',
        'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground', 'global_connect',
        'set_voltage_domain -name CORE -power VDD -ground VSS',
        'define_pdn_grid -name parent_grid -voltage_domains CORE -pins metal10',
        'add_pdn_stripe -grid parent_grid -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins',
        'add_pdn_stripe -grid parent_grid -layer metal4 -width 0.48 -pitch 56 -offset 2',
        'add_pdn_stripe -grid parent_grid -layer metal7 -width 1.40 -pitch 30 -offset 2',
        'add_pdn_stripe -grid parent_grid -layer metal10 -width 1.40 -pitch 30 -offset 2',
        'add_pdn_connect -grid parent_grid -layers {metal1 metal4}', 'add_pdn_connect -grid parent_grid -layers {metal4 metal7}',
        'add_pdn_connect -grid parent_grid -layers {metal7 metal10}',
        'define_pdn_grid -name macro_pg -voltage_domains CORE -macro -instances u_macro -grid_over_pg_pins -halo {2 2 2 2}',
        'add_pdn_connect -grid macro_pg -layers {metal7 metal10}', 'pdngen -failed_via_report '+tcl(out/'failed_vias.rpt'),
        'set llhd_macro_instances {u_macro}', 'source '+tcl(DRIVER/'filter_parent_pg.tcl'),
        'check_power_grid -net VDD -error_file '+tcl(out/'VDD.initial.rpt'),
        'check_power_grid -net VSS -error_file '+tcl(out/'VSS.initial.rpt'),
        'write_db '+tcl(out/'placed.odb'),
        'set f [open '+tcl(out/'parent_M10_PG.tsv')+' w]', 'puts $f "x0\\ty0\\tx1\\ty1"',
        'foreach n [[ord::get_db_block] getNets] {foreach sw [$n getSWires] {foreach s [$sw getWires] {',
        'if {[$s isVia]} {set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getBlockVia]};lassign [$s getViaXY] x y;foreach b [$v getBoxes] {if {[[$b getTechLayer] getName] eq "metal10"} {puts $f [join [list [expr {[$b xMin]+$x}] [expr {[$b yMin]+$y}] [expr {[$b xMax]+$x}] [expr {[$b yMax]+$y}]] "\\t"]}}} elseif {[[$s getTechLayer] getName] eq "metal10"} {puts $f [join [list [$s xMin] [$s yMin] [$s xMax] [$s yMax]] "\\t"]}',
        '}}}', 'close $f']
    (out/'setup.tcl').write_text('\n'.join(setup)+'\n')
    reservation_input=os.environ.get('PINXY_PARENT_ACCESS_RESERVATIONS') or (os.environ.get('PINXY_ACT_ACCESS_RESERVATIONS') if case=='act' else None)
    if variant=='C' and reservation_input:
        reservations=Path(reservation_input)
        leaf_trial=json.loads(access_trial_receipt.read_text())
        assert leaf_trial['input_sha256'][str(reservations)]==sha(reservations),'Parent keepouts must be the exact accepted leaf access windows'
        before_pdn=[
            'set prior_parent_block_obs [lsort [[ord::get_db_block] getObstructions]]',
            'set temporary_parent_access_obs {};set access_reservations {};source '+tcl(reservations),
            'set u [[ord::get_db_block] getDbUnitsPerMicron]',
            'foreach row $access_reservations {lassign $row layer x0 y0 x1 y1;set ly [[ord::get_db_tech] findLayer $layer];set coords {};foreach v [list $x0 $y0 $x1 $y1] offset [list '+str(dx)+' '+str(dy)+' '+str(dx)+' '+str(dy)+'] {lappend coords [expr {round(($v+$offset)*$u)}]};lappend temporary_parent_access_obs [odb::dbObstruction_create [ord::get_db_block] $ly {*}$coords]}']
        after_pdn=[
            'foreach ob $temporary_parent_access_obs {odb::dbObstruction_destroy $ob}',
            'if {[lsort [[ord::get_db_block] getObstructions]] ne $prior_parent_block_obs} {error "Original parent block OBS changed"}',
            'puts "NEW_PARENT_PG_AVOIDED_TEMPORARY_ACCESS_WINDOWS; original block/master OBS retained"']
        position=next(i for i,s in enumerate(setup) if s.startswith('pdngen '))
        setup[position:position]=before_pdn
        position+=len(before_pdn)
        setup[position+1:position+1]=after_pdn
        (out/'setup.tcl').write_text('\n'.join(setup)+'\n')
        rec['parent_PG_access_window_SHA']=sha(reservations)
        rec['parent_PG_access_policy']='Exclude only newly generated parent PG from exact leaf access windows; remove only new temporary keepouts after PDN; source leaf PG/metal/OBS unchanged'
    assert execute(common, out/'setup.tcl', out/'setup.log', 'PINXY_PARENT_OUT='+str(out)) == 0, 'Actual setup/PG failed; source untouched'
    obstacles = []
    in_obs, layer = False, None
    for line in lef.splitlines():
        s = line.strip()
        if s == 'OBS': in_obs = True
        elif in_obs and s.startswith('LAYER '): layer = s.split()[1]
        elif in_obs and s.startswith('RECT ') and layer == 'metal10':
            x0,y0,x1,y1 = map(float,s.split()[1:5]);obstacles.append((x0+dx,y0+dy,x1+dx,y1+dy))
        elif in_obs and s.startswith('POLYGON ') and layer == 'metal10':
            raise RuntimeError('Need exact polygon handling for actual M10 obstruction; do not approximate empty')
        elif in_obs and s == 'END': in_obs = False
    with (out/'parent_M10_PG.tsv').open() as f:
        obstacles += [tuple(float(r[k])/2000 for k in ['x0','y0','x1','y1']) for r in csv.DictReader(f,delimiter='\t')]
    landing, old_rects = {}, []
    offsets = sorted((abs(i)+abs(j),i,j) for i in range(-36,37) for j in range(-36,37))
    for pin in sorted(selected, key=lambda p:int(p.split('[')[1].split(']')[0])):
        p = pins[pin];x = (int(p['x0'])+int(p['x1']))/4000+dx;y = (int(p['y0'])+int(p['y1']))/4000+dy
        sx, sy = .095+round((x-.095)/3.2)*3.2, .07+round((y-.07)/3.2)*3.2
        chosen = None
        for _,i,j in offsets:
            px,py = round(sx+i*3.2,6),round(sy+j*3.2,6)
            b = (px-.4,py-.4,px+.4,py+.4)
            if min(b[:2])<10 or b[2]>die_w-10 or b[3]>die_h-10:continue
            if any(b[0]-1.5<q[2] and b[2]+1.5>q[0] and b[1]-1.5<q[3] and b[3]+1.5>q[1] for q in obstacles+old_rects):continue
            chosen = (px,py);old_rects.append(b);break
        assert chosen, (pin,'No actual M10 OBS/PG-screened landing')
        landing[pin] = chosen
    if kind=='real_diode658':
        # Reuse the old successful repair as a proposal, screening it against
        # this actual new child's M10 OBS, new PG and all other landings again.
        deltafile=ROOT/'inputs/gemm-actual-landing-r01/landing_delta.json';delta=json.loads(deltafile.read_text())
        assert delta['net']=='gemm_a_rdata[128]' and delta['parent_layer']=='metal10' and delta['parent_size_um']==[.8,.8]
        px,py=delta['new_parent_xy_um'];b=(px-.4,py-.4,px+.4,py+.4)
        others=[(x-.4,y-.4,x+.4,y+.4) for p,(x,y) in landing.items() if p!=delta['net']]
        assert min(b[:2])>=10 and b[2]<=die_w-10 and b[3]<=die_h-10
        assert not any(b[0]-1.5<q[2] and b[2]+1.5>q[0] and b[1]-1.5<q[3] and b[3]+1.5>q[1] for q in obstacles+others)
        landing[delta['net']]=(px,py);source_view_hashes[str(deltafile)]=sha(deltafile)
        rec['reused_prior_parent_repair_as_proposal']={'source_delta_SHA256':sha(deltafile),'pin':delta['net'],'new_parent_M10_xy_um':[px,py],
          'screened_against_this_new_actual_M10_OBS_PG_and_all_other_landing_rectangles':True,
          'new_native_route_DRC_and_access_not_inferred_from_old_fixture':True}
    commands = ['read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
                'read_liberty '+tcl(model_dir/'timing.lib'), 'read_db '+tcl(out/'placed.odb')]
    landing_rows = []
    for pin,p in pins.items():
        if pin in landing:
            x,y = landing[pin];layer,w,h = 'metal10',.8,.8
        else:
            x,y = (int(p['x0'])+int(p['x1']))/4000+dx,(int(p['y0'])+int(p['y1']))/4000+dy
            layer,w,h = p['layer'],(int(p['x1'])-int(p['x0']))/2000,(int(p['y1'])-int(p['y0']))/2000
        commands.append('place_pin -pin_name '+tcl(pin)+' -layer '+layer+' -location {'+str(x)+' '+str(y)+'} -pin_size {'+str(w)+' '+str(h)+'}')
        landing_rows.append({'pin':pin,'leaf_original_layer':p['layer'],'parent_layer':layer,'parent_x_um':x,'parent_y_um':y,'selected_M10_escape':pin in selected})
    allow_overflow=os.environ.get('PINXY_ALLOW_CONGESTED_GUIDES')=='1'
    rec['GRT_overflow_allowed_for_guide_only']=allow_overflow
    rec['GRT_overflow_not_a_physical_pass']=True
    commands += ['set_routing_layers -signal metal2-metal10 -clock metal4-metal10',
                 'global_route '+('-allow_congestion ' if allow_overflow else '')+'-guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt'),
                 'write_db '+tcl(out/'global.odb'),
                 'detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1',
                 'write_db '+tcl(out/'routed.odb'),
                 'check_power_grid -net VDD -error_file '+tcl(out/'VDD.final.rpt'),
                 'check_power_grid -net VSS -error_file '+tcl(out/'VSS.final.rpt'),
                 'source '+tcl(DRIVER/'export_access.tcl'),
                 'write_abstract_lef -bloat_factor 0 '+tcl(out/'wrapper.lef')]
    (out/'route.tcl').write_text('\n'.join(commands)+'\n')
    with (out/'landing_ports.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(landing_rows[0]));w.writeheader();w.writerows(landing_rows)
    env = 'PINXY_DRIVER={},PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT={}'.format(DRIVER,out/'whole_access.tsv.gz')
    rec['native_route_returncode'] = execute(common,out/'route.tcl',out/'route.log',env)
    rec['source_unchanged'] = sha(odb)==rec['source_clean_ODB_SHA']
    rec['all_closed_source_views_unchanged']=all(sha(Path(p))==v for p,v in source_view_hashes.items())
    if rec['native_route_returncode']==0:
        fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['independent_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        report=out/'independent.drc'
        rec['independent_DRC_count']=len(re.findall(r'^violation type:',report.read_text(),re.M)) if rec['independent_DRC_returncode']==0 and report.exists() else None
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
    rec['all_signal_pins']=len(pins);rec['actual_parent_M10_landing_ports']=len(landing)
    rec['RC_STA']='Not yet executed; requires accepted native/PG/whole geometry and exact leaf model source; never infer timing from successful routing'
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file()}
    rec['status']='FIXED_LAYER_ESCAPE_ACCESS_GATES_PASSED_NOT_SYSTEM_QUALIFIED' if rec.get('independent_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and rec['native_route_returncode']==0 and rec['source_unchanged'] and rec['all_closed_source_views_unchanged'] else 'ACTUAL_ESCAPE_FIXTURE_FAILED_OR_INCOMPLETE'
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('ESCAPE_FIXTURE',case,variant,rec['status'],flush=True)
    return rec['status']=='FIXED_LAYER_ESCAPE_ACCESS_GATES_PASSED_NOT_SYSTEM_QUALIFIED'


def safe(args):
    out=ROOT/'escape_fixtures'/args[2]/(args[0]+'-'+args[1])
    if out.exists():
        print('REFUSE_EXISTING_ESCAPE_DIRECTORY_UNCHANGED',out,flush=True)
        return False
    try:return one(*args)
    except Exception:
        traceback.print_exc()
        out=ROOT/'escape_fixtures'/args[2]/(args[0]+'-'+args[1]);out.mkdir(parents=True,exist_ok=True)
        with (out/'driver_failure.json').open('x') as f:f.write(json.dumps({'status':'FAILED_NOT_PHYSICAL_QUALIFICATION','traceback':traceback.format_exc()},indent=2)+'\n')
        return False


if __name__=='__main__':
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    case,revision=sys.argv[1:3]
    variants=sys.argv[3:] or ['Aopt','C']
    assert len(set(variants))==len(variants) and set(variants)<=set(['Aopt','C'])
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(safe,[(case,v,revision) for v in variants]))
    sys.exit(0 if all(results) else 1)
