"""Issue-15 physical implementations, with every attempt in a fresh directory."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from collections import Counter
from run import ROOT, PLATFORM, SOURCES, INPUTS, digest, track, result, run_tcl

def verified_copy(source, relative, destination):
    entries = {line[66:]:line[:64] for line in (source/'output-files.sha256').read_text().splitlines()}
    old=source/relative
    assert digest(old)==entries[relative], relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(old,destination)
    assert digest(destination)==entries[relative]
    track(old)

def repair(spec):
    source=SOURCES['merged']
    suffix=result(source).relative_to(source)
    dest=ROOT/suffix
    for name in ('4_cts.odb','4_cts.sdc'):
        verified_copy(source,(suffix/name).as_posix(),dest/name)
    for name in ('config.mk','boundary.sdc','boundary.sv','elab.v','elab.json','experiment.json'):
        verified_copy(source,name,ROOT/name)
    for path in (source/'memory-model').rglob('*'):
        if path.is_file(): verified_copy(source,path.relative_to(source).as_posix(),ROOT/path.relative_to(source))
    margin=int(spec.get('cap_margin',30))
    assert 0<=margin<100
    config=(ROOT/'config.mk').read_text().replace(str(source),str(ROOT))
    config,n=re.subn(r'^export CAP_MARGIN = \d+$','export CAP_MARGIN = '+str(margin),config,flags=re.M)
    assert n==1
    # Cell swaps are deliberately not dont_touch: the prior frozen BUF input
    # prevented InsertBufferBeforeLoads and caused RSZ-3006 in both margin runs.
    hook='set b [ord::get_db_block]\nset f [open {'+str(ROOT/'replacements.tsv')+'} w]\n'
    replacements=[('place15504','BUF_X1','BUF_X4'),('place15492','BUF_X1','BUF_X4'),('place15563','BUF_X1','BUF_X4')]
    for name,before,after in replacements:
        hook+='set inst [$b findInst {'+name+'}]\n'
        hook+='if {$inst eq "NULL" || [[$inst getMaster] getName] ne {'+before+'}} {error {Unexpected repair instance}}\n'
        hook+='if {![replace_cell {'+name+'} {'+after+'}]} {error {Cell replacement failed}}\n'
        hook+='puts $f {'+name+' '+before+' -> '+after+'}\n'
    hook+='close $f\ndetailed_placement_helper\ncheck_placement -verbose\n'
    (ROOT/'repair.tcl').write_text(hook)
    config+='export PRE_GLOBAL_ROUTE_TCL = '+str(ROOT/'repair.tcl')+'\n'
    (ROOT/'config.mk').write_text(config)
    meta=json.loads((ROOT/'experiment.json').read_text())
    meta.update(cap_margin=margin,repair=dict(checkpoint=str(source/'4_cts.odb'),
        freeze_cells=False,replacements=replacements,reason='Remove conflicting dont_touch; stronger buffer drive; unchanged logical functions and clock/IO budget'))
    (ROOT/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(ROOT/'config.mk'),
             'WORK_HOME='+str(ROOT/'flow'),'NUM_CORES='+str(spec['cores'])]
    for target in ('do-route','do-finish','do-generate_abstract'):
        with (ROOT/(target+'.log')).open('w') as f:
            subprocess.run(command+[target],stdout=f,stderr=subprocess.STDOUT,check=True)
    run_tcl('detail','read_db {'+str(dest/'6_final.odb')+'}\nwrite_abstract_lef -bloat_factor 0 {'+str(dest/'llhd_opentpu_act_mxu.detailed.lef')+'}\n')

def execute(spec):
    if spec['mode']=='repair': repair(spec)
    elif spec['mode']=='matched': matched(spec)
    elif spec['mode']=='top': top(spec)
    elif spec['mode']=='views': view_probe(spec)
    elif spec['mode']=='resume': resume(spec)
    else: raise ValueError('Not implemented: '+spec['mode'])

LINKS={'ren':'act_ren','r_use':'computing','r_blk':'act_blk','r_blk2':'act_blk2',
       'r_hi':'act_hi','r_grp':'act_grp','r_data':'act_data','r_scale':'act_scale'}

def ports(source):
    meta=json.loads(track(source/'experiment.json').read_text())
    return json.loads(track(source/'elab.json').read_text())['modules'][meta['top']]['ports']

def declaration(name,p):
    width=len(p['bits'])
    return p['direction']+' wire '+('[%d:0] '%(width-1) if width>1 else '')+name

def wrapper(name,ap,mp,split=True):
    ext={k:p for k,p in ap.items() if k not in LINKS}
    ext.update({k:p for k,p in mp.items() if k not in set(LINKS.values())-{'computing'}})
    assert len(ext)==40 and sum(len(p['bits']) for p in ext.values())==1662
    text='module '+name+'(\n'+',\n'.join(declaration(k,p) for k,p in ext.items())+');\n'
    if split:
        for k in LINKS.values():
            if k not in ext:
                w=len(mp[k]['bits']);text+='wire '+('[%d:0] '%(w-1) if w>1 else '')+k+';\n'
        for inst,module,ps,mapping in [('u_act','llhd_opentpu_act',ap,LINKS),('u_mxu','llhd_opentpu_mxu',mp,{})]:
            text+=module+' '+inst+'('+','.join('.'+k+'('+mapping.get(k,k)+')' for k in ps)+');\n'
    else:
        text+='llhd_match_merged u_merged('+','.join('.'+k+'('+k+')' for k in ext)+');\n'
    return text+'endmodule\n',ext

def boundary_sdc(top):
    return ('current_design '+top+'\ncreate_clock -name clk -period 2.5 [get_ports clk]\n'
        'set ni [lsearch -inline -all -not -exact [all_inputs] clk]\n'
        'set_input_delay 0.5 -clock clk $ni\nset_output_delay 0.5 -clock clk [all_outputs]\n'
        'set_driving_cell -lib_cell BUF_X4 -pin Z $ni\nset_input_transition 0.05 [get_ports clk]\n'
        'set_load 5.0 [all_outputs]\n')

def make_stages(config,spec,stages):
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(config),
             'WORK_HOME='+str(ROOT/'flow'),'NUM_CORES='+str(spec['cores'])]
    for stage in stages:
        with (ROOT/(stage+'.log')).open('w') as f:
            subprocess.run(command+[stage],stdout=f,stderr=subprocess.STDOUT,check=True)

def matched(spec):
    kind=spec['kind'];assert kind in ('act','mxu','merged')
    ap,mp=ports(SOURCES['act']),ports(SOURCES['mxu'])
    libs={p.name:p for src in (SOURCES['act'],SOURCES['mxu']) for p in (src/'memory-model/macros').glob('*.lib')}
    lefs={p.name:p for src in (SOURCES['act'],SOURCES['mxu']) for p in (src/'memory-model/macros').glob('*.lef')}
    for path in list(libs.values())+list(lefs.values()): track(path)
    commands=['read_liberty -lib '+json.dumps(str(track(PLATFORM/'lib/NangateOpenCellLibrary_typical.lib')))]
    commands+=['read_liberty -lib '+json.dumps(str(path)) for path in libs.values()]
    for name in ('act','mxu'):
        path=result(SOURCES[name])/'1_2_yosys.v'
        track(path)
        entries={line[66:]:line[:64] for line in (SOURCES[name]/'output-files.sha256').read_text().splitlines()}
        assert digest(path)==entries[path.relative_to(SOURCES[name]).as_posix()]
        commands+=['read_verilog '+json.dumps(str(path))]
    commands+=['write_json mapped-before.json']
    top='llhd_match_merged' if kind=='merged' else 'llhd_opentpu_'+kind
    if kind=='merged':
        text,ext=wrapper(top,ap,mp)
        (ROOT/'wrapper.v').write_text(text)
        commands+=['read_verilog wrapper.v']
    # flatten adds two $scopeinfo metadata records, not physical cells.
    commands+=['hierarchy -check -top '+top,'flatten','delete t:$scopeinfo','check -assert','write_json mapped-after.json',
               'write_verilog -noattr mapped.v']
    (ROOT/'assemble.ys').write_text('\n'.join(commands)+'\n')
    with (ROOT/'assemble.log').open('w') as f:
        subprocess.run(['yosys','-Q','-T','-s','assemble.ys'],stdout=f,stderr=subprocess.STDOUT,check=True)
    before=json.loads((ROOT/'mapped-before.json').read_text())['modules']
    after=json.loads((ROOT/'mapped-after.json').read_text())['modules'][top]
    count=lambda d:Counter(c['type'] for c in d['cells'].values())
    expected=sum((count(before['llhd_opentpu_'+n]) for n in ('act','mxu')),Counter()) if kind=='merged' else count(before[top])
    assert count(after)==expected, 'Assembly changed mapped resources'
    (ROOT/'resource-audit.json').write_text(json.dumps(dict(passed=True,kind=kind,starting_cells=expected,
        cells=sum(expected.values()),no_logic_optimization=True,no_added_state=True,
        qualification='Exact common mapped-cell inventory; subsequent CTS/repair costs recorded separately'),indent=2)+'\n')
    nickname='matched_opentpu_'+kind
    relative='flow/results/nangate45/'+nickname+'/base'
    dest=ROOT/relative;dest.mkdir(parents=True)
    shutil.copy2(ROOT/'mapped.v',dest/'1_2_yosys.v')
    (ROOT/'boundary.sdc').write_text(boundary_sdc(top))
    shutil.copy2(ROOT/'boundary.sdc',dest/'1_2_yosys.sdc')
    config=('export DESIGN_NICKNAME = '+nickname+'\nexport DESIGN_NAME = '+top+'\nexport PLATFORM = nangate45\n'
        'export VERILOG_FILES = '+str(ROOT/'mapped.v')+'\nexport SDC_FILE = '+str(ROOT/'boundary.sdc')+'\n'
        'export ADDITIONAL_LEFS = '+' '.join(map(str,lefs.values()))+'\nexport ADDITIONAL_LIBS = '+' '.join(map(str,libs.values()))+'\n'
        'export CORE_UTILIZATION = 35\nexport PLACE_DENSITY = 0.55\nexport TNS_END_PERCENT = 100\nexport LEC_CHECK = 0\n'
        'export MACRO_PLACE_HALO = 10 10\nexport RTLMP_MIN_CHANNEL_SIZE = 60 60\nexport CORE_MARGIN = 5\nexport CAP_MARGIN = 20\n'
        'export TAPCELL_TCL = '+str(SOURCES['act']/'source/asic/nangate45/tapcell.tcl')+'\n')
    # The merged unused-output cone otherwise loses 9 DFF and 126 logic
    # cells at the ODB import, unlike either split block. This is an
    # optimization, not a correctness check: disable it to hold resources.
    preserve=('if {[llength [info commands eliminate_dead_logic]] != 1} {error {Missing expected optimization command}}\n'
        'rename eliminate_dead_logic llhd_original_eliminate_dead_logic\n'
        'proc eliminate_dead_logic {} {puts {FIXED_RESOURCE: disabled dead-logic optimization; retain original mapped resources}}\n')
    (ROOT/'preserve-resources.tcl').write_text(preserve)
    config+='export PRE_SYNTH_TCL = '+str(ROOT/'preserve-resources.tcl')+'\n'
    (ROOT/'audit-synth.tcl').write_text('set f [open {'+str(ROOT/'synth-resources.tsv')+'} w]\n'
        'foreach i [[ord::get_db_block] getInsts] {puts $f "[$i getName]\\t[[$i getMaster] getName]"}\nclose $f\n')
    config+='export POST_SYNTH_TCL = '+str(ROOT/'audit-synth.tcl')+'\n'
    (ROOT/'config.mk').write_text(config)
    # Keep the common source port map in this attempt for later macro assembly.
    meta=dict(case='matched-'+kind,top=top,result_relative=relative,kind=kind,
        clock_ns=2.5,io_delay_ns=.5,input_driver='BUF_X4/Z',output_load_fF=5.,clock_transition_ns=.05,
        memory_model='Unchanged upstream synthetic fakeram; no SRAM GDS',
        source_commit='f237dab2f196855a59a083b1454786df8f01291f',phase_lec=False,
        source_rtl_modified=False,added_registers=0)
    (ROOT/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
    (ROOT/'elab.json').write_text(json.dumps({'modules':{top:after}})+'\n')
    (ROOT/'input-sha256.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
    make_stages(ROOT/'config.mk',spec,['do-1_synth'])
    actual=Counter(line.split()[-1] for line in (ROOT/'synth-resources.tsv').read_text().splitlines())
    assert actual==expected, 'Physical import changed fixed mapped resources'
    audit=json.loads((ROOT/'resource-audit.json').read_text())
    audit.update(actual_synth_cells=actual,physical_import_exact=True,dead_logic_optimization_disabled=True)
    (ROOT/'resource-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    make_stages(ROOT/'config.mk',spec,['do-floorplan','do-place','do-cts','do-route','do-finish','do-generate_abstract'])
    run_tcl('detail','read_db {'+str(dest/'6_final.odb')+'}\nwrite_abstract_lef -bloat_factor 0 {'+str(dest/(top+'.detailed.lef'))+'}\n')

def view_probe(spec):
    flow=Path('/OpenROAD-flow-scripts/flow')
    names=['scripts/io_placement.tcl','scripts/io_placement_util.tcl','scripts/synth_odb.tcl',
           'platforms/nangate45/config.mk','scripts/variables.yaml','scripts/cts.tcl','scripts/generate_abstract.tcl']
    (ROOT/'extra-flow-sources.json').write_text(json.dumps({n:(flow/n).read_text() for n in names if (flow/n).is_file()},indent=2)+'\n')
    run_tcl('help','help place_pin\nhelp read_spef\nhelp report_check_types\nhelp report_clock_min_period\n')
    for name,path in spec.get('audit_sources',{}).items():
        source=Path(path);r=result(source)
        run_tcl(name+'-resource','read_db {'+str(track(r/'1_synth.odb'))+'}\nset f [open {'+str(ROOT/(name+'-synth.tsv'))+'} w]\n'
            'foreach i [[ord::get_db_block] getInsts] {puts $f "[$i getName]\\t[[$i getMaster] getName]"}\nclose $f\n')
        meta=json.loads((source/'experiment.json').read_text())
        before=json.loads((source/'mapped-after.json').read_text())['modules'][meta['top']]['cells']
        old=Counter(c['type'] for c in before.values())
        rows=[line.split() for line in (ROOT/(name+'-synth.tsv')).read_text().splitlines()]
        actual=Counter(row[-1] for row in rows)
        (ROOT/(name+'-resource.json')).write_text(json.dumps(dict(before=old,after=actual,
            removed=old-actual,added=actual-old),indent=2)+'\n')
    if spec.get('audit_repair'):
        source=SOURCES['merged'];repair_source=Path(spec['audit_repair'])
        manifest={line[66:]:line[:64] for line in (source/'output-files.sha256').read_text().splitlines()}
        paths=[(result(source)/n).relative_to(source) for n in ('4_cts.odb','4_cts.sdc')]
        paths += [Path(n) for n in ('boundary.sdc','boundary.sv','elab.v','elab.json')]
        paths += [p.relative_to(source) for p in (source/'memory-model').rglob('*') if p.is_file()]
        pairs=[]
        for relative in paths:
            a,b=source/relative,repair_source/relative
            actual=digest(a)
            assert actual==manifest[relative.as_posix()]==digest(b)
            track(a);track(b)
            pairs.append(dict(original=str(a),copy=str(b),sha256=actual))
        (ROOT/'repair-input-audit.json').write_text(json.dumps(dict(passed=True,files=pairs,
            note='Post-run independent audit; original repair receipt had empty aggregate input JSON due to Python module aliasing. Original verified-copy checks executed; no old artifact is rewritten.'),indent=2)+'\n')
    for name,path in spec.get('final_resource_sources',{}).items():
        source=Path(path);r=result(source)
        run_tcl(name+'-final','read_db {'+str(track(r/'6_final.odb'))+'}\nset f [open {'+str(ROOT/(name+'-final.tsv'))+'} w]\n'
            'foreach i [[ord::get_db_block] getInsts] {puts $f "[$i getName]\\t[[$i getMaster] getName]"}\nclose $f\n')
        expected=json.loads((source/'resource-audit.json').read_text())['starting_cells']
        actual=Counter(line.split()[-1] for line in (ROOT/(name+'-final.tsv')).read_text().splitlines())
        def architectural(counts):
            out=Counter()
            for cell,count in counts.items():
                if cell.startswith(('fakeram','DFF','SDFF','DLH','DLL','LATCH')): out[re.sub(r'_X\d+$','',cell)]+=count
            return out
        before,after=architectural(expected),architectural(actual)
        (ROOT/(name+'-final-resource.json')).write_text(json.dumps(dict(passed=before==after,
            original_architectural_cells=before,final_architectural_cells=after,
            final_all_cells=actual,qualification='Memory and state elements retained; drive variants normalized, combinational and physical repair costs separate'),indent=2)+'\n')

def top(spec):
    import math
    from quality import evaluate
    sources={k:Path(v) for k,v in spec['sources'].items()}
    assert set(sources)=={'act','mxu','merged'}
    for source in sources.values():
        assert (source/'exit-code.txt').read_text().strip()=='0', 'Input flow not completed'
        meta=json.loads((source/'experiment.json').read_text())
        nick=Path(meta['result_relative']).parts[-2]
        logs=source/'flow/logs/nangate45'/nick/'base'
        reports=source/'flow/reports/nangate45'/nick/'base'
        row=dict(exit_code='0',metrics={n:json.loads((logs/n).read_text()) for n in ['6_report.json','5_2_route.json']},
                 final_report=(reports/'6_finish.rpt').read_text())
        assert evaluate(row)['passed'], 'Input block fails strict extracted budget: '+str(source)
        # Freeze and verify only selected new experiment artifacts on this compute node.
        expected={line[2:]:h for h,line in (r.split(None,1) for r in (source/'output.sha256').read_text().splitlines())}
        for relative in ['experiment.json','elab.json','resource-audit.json']:
            path=source/relative
            assert digest(path)==expected[relative]
    views={}
    (ROOT/'views').mkdir()
    for kind,source in sources.items():
        meta=json.loads(track(source/'experiment.json').read_text());name=meta['top'];r=result(source)
        view=ROOT/'views'/kind;view.mkdir()
        for suffix,old in [('.lef',r/(name+'.detailed.lef')),('.lib',r/(name+'_typ.lib'))]:
            expected={line[2:]:h for h,line in (r.split(None,1) for r in (source/'output.sha256').read_text().splitlines())}
            assert digest(old)==expected[old.relative_to(source).as_posix()]
            track(old);shutil.copy2(old,view/(name+suffix))
        text=(view/(name+'.lef')).read_text()
        size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text)
        assert size
        views[kind]=dict(name=name,size=list(map(float,size.groups())),view=str(view),source=str(source))
    aw,ah=views['act']['size'];mw,mh=views['mxu']['size'];cw,ch=views['merged']['size']
    side=math.ceil(max(aw+mw+240,ah+160,mh+160,cw+160,ch+160)/10)*10
    kind=spec['kind'];assert kind in ('split','merged')
    topname='llhd_top_'+kind
    ap,mp=ports(sources['act']),ports(sources['mxu'])
    text,ext=wrapper(topname,ap,mp,split=kind=='split')
    (ROOT/'top.v').write_text(text)
    selected=['act','mxu'] if kind=='split' else ['merged']
    locations={'u_act':[80,80],'u_mxu':[80+aw+80,80]} if kind=='split' else {'u_merged':[80,80]}
    instances=list(locations)
    (ROOT/'placement.tcl').write_text(''.join('place_macro -macro_name '+n+' -location {'+' '.join(map(str,xy))+'} -orientation R0 -exact\n' for n,xy in locations.items())+
        'set b [ord::get_db_block]\n'+''.join('[$b findInst '+n+'] setPlacementStatus FIRM\n' for n in instances))
    (ROOT/'boundary.sdc').write_text(boundary_sdc(topname))
    pdn=('add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power\n'
         'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground\nglobal_connect\n'
         'set_voltage_domain -name CORE -power VDD -ground VSS\n'
         'define_pdn_grid -name parent_grid -voltage_domains CORE -pins metal10\n'
         'add_pdn_stripe -grid parent_grid -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins\n'
         'add_pdn_stripe -grid parent_grid -layer metal4 -width 0.48 -pitch 56 -offset 2\n'
         'add_pdn_stripe -grid parent_grid -layer metal7 -width 1.40 -pitch 30 -offset 2\n'
         'add_pdn_stripe -grid parent_grid -layer metal10 -width 1.40 -pitch 30 -offset 2\n'
         'add_pdn_connect -grid parent_grid -layers {metal1 metal4}\n'
         'add_pdn_connect -grid parent_grid -layers {metal4 metal7}\n'
         'add_pdn_connect -grid parent_grid -layers {metal7 metal10}\n')
    for n in instances:
        pdn+='define_pdn_grid -name pg_'+n+' -voltage_domains CORE -macro -instances '+n+' -grid_over_pg_pins -halo {2 2 2 2}\n'
        pdn+='add_pdn_connect -grid pg_'+n+' -layers {metal7 metal10}\n'
    (ROOT/'pdn.tcl').write_text(pdn)
    setup='set llhd_macro_instances {'+' '.join(instances)+'}\nset ::env(LLHD_ATTEMPT) {'+str(ROOT)+'}\n'
    setup+='source {'+str(ROOT/'runner/filter_pg.tcl')+'}\nsource {'+str(ROOT/'runner/check_pg.tcl')+'}\n'
    (ROOT/'post-pdn.tcl').write_text(setup)
    # The external 1662 bit pins must have identical coordinates in both
    # parents. Apply after automatic placement, then explicitly save its ODB.
    pinlines=[];pin_contract={}
    names=[n if len(p['bits'])==1 else n+'['+str(i)+']' for n,p in ext.items() for i in range(len(p['bits']))]
    per_side=math.ceil(len(names)/4)
    for index,name in enumerate(names):
        edge=index%4;slot=index//4
        position=round((10+(side-20)*(slot+1)/(per_side+1))/0.14)*0.14
        x,y=[(0,position),(side,position),(position,0),(position,side)][edge]
        layer='metal3' if edge<2 else 'metal2'
        pinlines.append('place_pin -pin_name {'+name+'} -layer '+layer+' -location {'+str(x)+' '+str(y)+'} -force_to_die_boundary')
        pin_contract[name]=dict(layer=layer,xy=[x,y])
    pinlines+=['orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb',
               'write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl']
    (ROOT/'fixed-pins.tcl').write_text('\n'.join(pinlines)+'\n')
    (ROOT/'external-pin-contract.json').write_text(json.dumps(pin_contract,indent=2)+'\n')
    lefpaths=[str(Path(views[k]['view'])/(views[k]['name']+'.lef')) for k in selected]
    libpaths=[str(Path(views[k]['view'])/(views[k]['name']+'.lib')) for k in selected]
    nickname='opentpu_top_'+kind
    relative='flow/results/nangate45/'+nickname+'/base'
    config=('export DESIGN_NICKNAME = '+nickname+'\nexport DESIGN_NAME = '+topname+'\nexport PLATFORM = nangate45\n'
        'export VERILOG_FILES = '+str(ROOT/'top.v')+'\nexport SDC_FILE = '+str(ROOT/'boundary.sdc')+'\n'
        'export ADDITIONAL_LEFS = '+' '.join(lefpaths)+'\nexport ADDITIONAL_LIBS = '+' '.join(libpaths)+'\n'
        'export DIE_AREA = 0 0 '+str(side)+' '+str(side)+'\nexport CORE_AREA = 10 10 '+str(side-10)+' '+str(side-10)+'\n'
        'export MACRO_PLACEMENT_TCL = '+str(ROOT/'placement.tcl')+'\nexport PDN_TCL = '+str(ROOT/'pdn.tcl')+'\n'
        'export POST_PDN_TCL = '+str(ROOT/'post-pdn.tcl')+'\nexport PLACE_DENSITY = 0.30\nexport TNS_END_PERCENT = 100\n'
        'export POST_IO_PLACEMENT_TCL = '+str(ROOT/'fixed-pins.tcl')+'\n'
        'export CAP_MARGIN = 20\nexport LEC_CHECK = 0\nexport SYNTH_HIERARCHICAL = 0\n')
    (ROOT/'config.mk').write_text(config)
    (ROOT/'experiment.json').write_text(json.dumps(dict(top=topname,case=nickname,kind=kind,result_relative=relative,
        views=views,locations=locations,die_um=[0,0,side,side],external_bits=1662,extra_state=0,
        clock_ns=2.5,io_delay_ns=.5,input_driver='BUF_X4/Z',output_load_fF=5,
        pdn='H1 additional parent M10; original detailed macro geometry retained',
        full_hierarchical_sta='Required after routing; macro libraries alone do not qualify internal period'),indent=2)+'\n')
    (ROOT/'input-sha256.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
    make_stages(ROOT/'config.mk',spec,['finish'])
    (ROOT/'final-pg').mkdir()
    run_tcl('final-pg','read_db {'+str(ROOT/relative/'6_final.odb')+'}\n'+
        'set llhd_macro_instances {'+' '.join(instances)+'}\nset ::env(LLHD_ATTEMPT) {'+str(ROOT/'final-pg')+'}\n'
        'set ::env(LLHD_PG_FILTER_AUDIT) 2\nsource {'+str(ROOT/'runner/filter_pg.tcl')+'}\nsource {'+str(ROOT/'runner/check_pg.tcl')+'}\n')
    run_tcl('final-inventory','read_db {'+str(ROOT/relative/'6_final.odb')+'}\n'
        'set f [open {'+str(ROOT/'final-pins.tsv')+'} w]\n'
        'foreach term [[ord::get_db_block] getBTerms] {foreach pin [$term getBPins] {foreach box [$pin getBoxes] {'
        'puts $f "[$term getName]\\t[[$box getTechLayer] getName]\\t[$box xMin]\\t[$box yMin]\\t[$box xMax]\\t[$box yMax]"}}}\nclose $f\n')
    full_sta(ROOT,sources,kind)

def full_sta(parent,sources,kind):
    """Stitch real block SPEF at hierarchical pins, without boundary IO delays."""
    selected=['act','mxu'] if kind=='split' else ['merged']
    meta=json.loads((parent/'experiment.json').read_text())
    r=result(parent)
    libs={p.name:p for n in ('act','mxu') for p in (SOURCES[n]/'memory-model/macros').glob('*.lib')}
    text='read_liberty {'+str(track(PLATFORM/'lib/NangateOpenCellLibrary_typical.lib'))+'}\n'
    for path in libs.values(): text+='read_liberty {'+str(track(path))+'}\n'
    for n in selected: text+='read_verilog {'+str(track(result(sources[n])/'6_final.v'))+'}\n'
    text+='read_verilog {'+str(track(r/'6_final.v'))+'}\nlink_design '+meta['top']+'\n'
    text+='read_sdc {'+str(track(parent/'boundary.sdc'))+'}\n'
    text+='read_spef {'+str(track(r/'6_final.spef'))+'}\n'
    for n in selected:
        text+='read_spef -path u_'+n+' {'+str(track(result(sources[n])/'6_final.spef'))+'}\n'
    text+='set_propagated_clock [all_clocks]\nreport_parasitic_annotation -report_unannotated\n'
    text+='report_worst_slack -max -digits 6\nreport_worst_slack -min -digits 6\nreport_tns -digits 6\n'
    text+='report_clock_min_period -include_port_paths\n'
    text+='report_checks -path_delay max -group_path_count 10 -digits 6 -format full_clock_expanded\n'
    text+='report_checks -path_delay min -group_path_count 10 -digits 6 -format full_clock_expanded\n'
    text+='report_check_types -max_capacitance -max_count 20 -digits 6 -no_line_splits\n'
    text+='report_check_types -violators -max_slew -max_capacitance -max_fanout -max_delay -min_delay -recovery -removal -min_period -digits 6 -no_line_splits\n'
    text+='check_setup -verbose\n'
    run_tcl('full-hierarchy-sta',text)

def resume(spec):
    """New extracted-budget iteration from a sealed common-resource CTS DB."""
    source=Path(spec['source'])
    assert (source/'exit-code.txt').read_text().strip()=='0'
    manifest={line[2:]:h for h,line in (r.split(None,1) for r in (source/'output.sha256').read_text().splitlines())}
    meta=json.loads((source/'experiment.json').read_text());suffix=Path(meta['result_relative'])
    paths=[suffix/'4_cts.odb',suffix/'4_cts.sdc']+[Path(n) for n in
        ['config.mk','boundary.sdc','elab.json','resource-audit.json','mapped.v']]
    copies=[]
    for relative in paths:
        path=source/relative
        assert digest(path)==manifest[relative.as_posix()]
        dest=ROOT/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        track(path);copies.append(dict(source=str(path),copy=str(dest),sha256=digest(path)))
    margin=int(spec['cap_margin']);assert 0<=margin<100
    config=(ROOT/'config.mk').read_text().replace(str(source),str(ROOT))
    config,n=re.subn(r'^export CAP_MARGIN = \d+$','export CAP_MARGIN = '+str(margin),config,flags=re.M)
    assert n==1
    if spec.get('reserve_m10'):
        for variable in ['MAX_ROUTING_LAYER','MAX_CLK_ROUTING_LAYER']:
            assert not re.search(r'^export '+variable+r'\s*=',config,re.M)
            config+='export '+variable+' = metal9\n'
    (ROOT/'config.mk').write_text(config)
    meta.update(resume=dict(source=str(source),checkpoint='4_cts.odb',route_cap_margin=margin,
        clock_io_load_unchanged=True,logic_resources_unchanged=True,
        reserve_m10_for_parent=bool(spec.get('reserve_m10'))),cap_margin=margin)
    (ROOT/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
    (ROOT/'checkpoint-copies.json').write_text(json.dumps(copies,indent=2)+'\n')
    (ROOT/'input-sha256.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
    make_stages(ROOT/'config.mk',spec,['do-route','do-finish','do-generate_abstract'])
    dest=ROOT/suffix
    run_tcl('detail','read_db {'+str(dest/'6_final.odb')+'}\nwrite_abstract_lef -bloat_factor 0 {'+str(dest/(meta['top']+'.detailed.lef'))+'}\n')
