"""Full native leaf flow for the five-macro architecture; not an acceptance waiver."""
import json
import math
from pathlib import Path
import re
import shutil


def implement(root,out,cpus,run,kind):
    from io_slots import file_sha,slot
    from pin_plan import generate
    from constraints import generate as constraints
    from native_reroute import config_suffix
    assert cpus==16 and kind in ('m','s','v','r')
    base=out.parents[2]
    top='block_v1_s16k' if kind=='s' else 'block_v1_'+kind
    label=dict(m='matrix',s='store',r='recurrent',v='vector')[kind]
    task_root=out.parent
    mapped=(base/'block-v1-20261027-187/tasks/five-macro-matrix-map' if kind=='m'
            else task_root/'five-macro-store-flatten' if kind=='s'
            else base/('block-v1-20261027-'+('195' if kind=='r' else '196')+'/tasks/five-macro-'+label+'-map'))
    tested=base/('block-v1-20261027-'+('186' if kind in ('m','s') else '195' if kind=='r' else '196')+'/tasks/five-macro-'+label+'-test')
    for source,name in [(mapped,'five-macro-'+label+'-map.json'),(tested,'five-macro-'+label+'-test.json')]:
        receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed'] is True
        assert file_sha(source/name)==receipt['outputs'][name]
        assert json.loads((source/name).read_text())['passed'] is True
    original=json.loads((tested/('five-macro-'+label+'-test.json')).read_text())
    rtl=root/('project/rtl/block_library_v1/'+top+'.sv')
    if kind in ('m','r'):assert file_sha(rtl)==original['source_sha256']
    elif kind=='s':assert file_sha(rtl)==original['source_sha256'][str(rtl.relative_to(root))]
    else:
        for name,digest in original['source_sha256'].items():assert file_sha(rtl.parent/name)==digest
    if kind=='s':assert file_sha(root/'project/rtl/norm_service/store82.sv')==original['source_sha256']['project/rtl/norm_service/store82.sv']
    mapping=json.loads((mapped/('five-macro-'+label+'-map.json')).read_text())
    assert file_sha(mapped/'mapped.v')==mapping['mapped_sha256']
    flow=Path('/OpenROAD-flow-scripts/flow')
    platform=flow/'platforms/nangate45'
    lib=platform/'lib/NangateOpenCellLibrary_typical.lib'
    assert file_sha(lib)==mapping['liberty_sha256']
    structural_source=mapped/'mapped.v'
    if kind!='s':
        # Reuse the existing signed-metadata adapter. OpenSTA's gate reader
        # rejects `wire signed`; do not change any cell or pin connection.
        import copy
        from structural_view import unsigned,compare
        mapped_json=mapped/'mapped.json'
        mapped_receipt=json.loads((mapped/'receipt.json').read_text())
        assert file_sha(mapped_json)==mapped_receipt['outputs']['mapped.json']
        expected=json.loads(mapped_json.read_text());metadata=unsigned(expected)
        (out/'unsigned.json').write_text(json.dumps(expected)+'\n')
        script='read_json '+str(out/'unsigned.json')+'\nhierarchy -check -top '+top+'\n'
        script+='write_verilog -noattr -noexpr -norename structural.v\nwrite_json structural.json\n'
        script+='design -reset\nread_liberty -lib '+str(lib)+'\nread_verilog structural.v\n'
        script+='hierarchy -check -top '+top+'\nwrite_json reparsed.json\n'
        (out/'structural.ys').write_text(script);run(['yosys','-s',str(out/'structural.ys')],'structural.log')
        expected=json.loads((out/'structural.json').read_text())
        observed=json.loads((out/'reparsed.json').read_text());proof=compare(expected,observed)
        negative=copy.deepcopy(observed);cell=next(iter(negative['modules'][top]['cells'].values()))
        values=next(v for v in cell['connections'].values() if v)
        values[0]='1' if values[0]!='1' else '0'
        rejected=False
        try:compare(expected,negative)
        except AssertionError:rejected=True
        assert rejected
        proof.update(metadata=metadata,single_pin_bit_negative_rejected=True)
        (out/'structural-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        structural_source=out/'structural.v'
    native=platform/'lef/NangateOpenCellLibrary.tech.lef'
    technology=json.loads((root/'project/experiments/block_v1/technology.json').read_text())
    assert file_sha(native)==technology['native_tech_sha256']
    # Footprint derives once from complete mapped area and a declared density.
    # It is not an alternate margin candidate; all later repairs retain it.
    text=lib.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',text));areas={}
    for i,m in enumerate(starts):
        chunk=text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
        areas[m.group(1)]=float(re.search(r'\barea\s*:\s*([\d.eE+-]+)\s*;',chunk).group(1))
    active=sum(areas[name]*count for name,count in mapping['cells'].items())
    side=max(400,math.ceil((math.sqrt(active/.4)+40)/10)*10)
    budget=json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text())
    leaf=dict(die_um=[side,side],core_margin_um=20)
    track_file=platform/'make_tracks.tcl'
    tracks={}
    for metal in ('metal9','metal10'):
        line=re.search(r'(?m)^make_tracks '+metal+r' (.+)$',track_file.read_text()).group(1).split()
        tracks[metal]={line[i]:float(line[i+1]) for i in range(0,len(line),2)}
    assert tracks['metal9']==tracks['metal10']
    via9=re.search(r'(?ms)^LAYER via9\s*\n(.*?)^END via9\s*$',native.read_text()).group(1)
    def cut(key):return float(re.search(r'\b'+key+r'\s+([\d.]+)\s*;',via9).group(1))
    t=tracks['metal10']
    grid=dict(pitch_x=t['-x_pitch'],pitch_y=t['-y_pitch'],offset_x=t['-x_offset'],offset_y=t['-y_offset'],
              width=.8,cut_width=cut('WIDTH'),cut_spacing=cut('SPACING'),
              track_file_sha256=file_sha(track_file),native_tech_sha256=file_sha(native))
    bits=[]
    for name,p in mapping['ports'].items():
        for i in range(p['bits']):bits.append(dict(port=name,index=i,direction=p['direction'],role='clock' if name=='clk' else 'signal'))
    plan=generate(bits,leaf,'C',grid)
    (out/'pins.json').write_text(json.dumps(plan,indent=2)+'\n')
    from pin_contract import script as pin_script
    pins=pin_script(plan)
    (out/'pins.tcl').write_text(pins)
    (out/'input.sdc').write_text(constraints(budget))
    with slot(base):shutil.copyfile(structural_source,out/'input.v')
    input_sha=file_sha(out/'input.v')
    nickname='bv1_'+top
    config='export PLATFORM = nangate45\nexport DESIGN_NAME = '+top+'\nexport DESIGN_NICKNAME = '+nickname+'\n'
    config+='export VERILOG_FILES = '+str(out/'input.v')+'\nexport SDC_FILE = '+str(out/'input.sdc')+'\n'
    config+='export DIE_AREA = 0 0 %g %g\nexport CORE_AREA = 20 20 %g %g\n'%(side,side,side-20,side-20)
    config+='export PLACE_DENSITY = 0.45\nexport FOOTPRINT_TCL = '+str(out/'pins.tcl')+'\nexport KEEP_VARS = 1\n'
    config+='override export MIN_ROUTING_LAYER = metal1\noverride export MAX_ROUTING_LAYER = metal10\n'
    hook=(root/'project/experiments/block_v1/native_input_diodes.tcl').read_text()
    if kind in ('r','v'):
        skip='  if {[$port getName] eq "clk"} {continue}\n';assert hook.count(skip)==1;hook=hook.replace(skip,'')
    (out/'input-diodes.tcl').write_text(hook)
    config+=config_suffix(40,.005,out/'input-diodes.tcl','metal10')
    if kind in ('r','v'):config+='\nexport HOLD_SLACK_MARGIN = 0.020\n'
    (out/'config.mk').write_text(config)
    results=out/'flow/results/nangate45'/nickname/'base';results.mkdir(parents=True)
    for suffix in ('v','sdc'):
        p=results/('1_2_yosys.'+suffix);shutil.copyfile(out/('input.'+suffix),p);p.chmod(0o444)
    command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES='+str(cpus)]
    expected=dict(MIN_ROUTING_LAYER='metal1',MAX_ROUTING_LAYER='metal10',KEEP_VARS='1',LEC_CHECK='1',SEC_CHECK='0',
                  TECH_LEF=str(native),RCX_RULES=str(platform/'rcx_patterns.rules'),CAP_MARGIN='40',HOLD_SLACK_MARGIN='0.020' if kind in ('r','v') else '0.005')
    actual={}
    for key,value in expected.items():
        log='variable-'+key+'.log';run(command+['print-'+key],log)
        actual[key]=re.search(r'(?m)^'+key+r': (.+)$',(out/log).read_text()).group(1).strip()
        assert actual[key]==value,(key,actual[key],value)
    result=dict(schema='five-macro-native-flow/1',passed=False,top=top,implementation_count=1,
                source_mapping_receipt_sha256=file_sha(mapped/'receipt.json'),
                source_function_receipt_sha256=file_sha(tested/'receipt.json'),
                mapped_area_um2=active,die_um=[side,side],footprint_rule='ceil10(sqrt(mapped_area/0.40)+40), min400um',
                config_sha256=file_sha(out/'config.mk'),pins_sha256=file_sha(out/'pins.json'),actual_variables=actual,
                stages=[],final_files={},qualified_hard_macro=False,independent_physical_acceptance=False,
                scope='Full native M1-M10 implementation; independent full-deck/STA/PG/final-netlist acceptance still required')
    def save():(out/'five-macro-native-flow.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    for number,stage in enumerate(('do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish')):
        run(command+[stage],'%02d-%s.log'%(number,stage));result['stages'].append(stage)
        assert file_sha(out/'input.v')==input_sha;save()
    for suffix in ('v','sdc','def','odb','spef'):
        p=results/('6_final.'+suffix);assert p.is_file()
        result['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    result['passed']=True;result['pipeline_completed']=True;save()
