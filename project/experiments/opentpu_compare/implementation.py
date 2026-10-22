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
