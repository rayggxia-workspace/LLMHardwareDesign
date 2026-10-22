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
    make_stages(ROOT/'config.mk',spec,['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish','do-generate_abstract'])
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

def top(spec):
    import math
    sources={k:Path(v) for k,v in spec['sources'].items()}
    assert set(sources)=={'act','mxu','merged'}
    for source in sources.values():
        assert (source/'exit-code.txt').read_text().strip()=='0', 'Input flow not completed'
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
