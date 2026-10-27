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
    assert cpus==16 and kind in ('m','s')
    base=out.parents[2]
    top='block_v1_m' if kind=='m' else 'block_v1_s16k'
    label='matrix' if kind=='m' else 'store'
    task_root=out.parent
    mapped=(base/'block-v1-20261027-187/tasks/five-macro-matrix-map' if kind=='m'
            else task_root/'five-macro-store-flatten')
    tested=base/'block-v1-20261027-186/tasks'/('five-macro-'+label+'-test')
    for source,name in [(mapped,'five-macro-'+label+'-map.json'),(tested,'five-macro-'+label+'-test.json')]:
        receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed'] is True
        assert file_sha(source/name)==receipt['outputs'][name]
        assert json.loads((source/name).read_text())['passed'] is True
    original=json.loads((tested/('five-macro-'+label+'-test.json')).read_text())
    rtl=root/('project/rtl/block_library_v1/'+top+'.sv')
    assert file_sha(rtl)==(original['source_sha256'] if kind=='m' else original['source_sha256'][str(rtl.relative_to(root))])
    if kind=='s':assert file_sha(root/'project/rtl/norm_service/store82.sv')==original['source_sha256']['project/rtl/norm_service/store82.sv']
    mapping=json.loads((mapped/('five-macro-'+label+'-map.json')).read_text())
    assert file_sha(mapped/'mapped.v')==mapping['mapped_sha256']
    flow=Path('/OpenROAD-flow-scripts/flow')
    platform=flow/'platforms/nangate45'
    lib=platform/'lib/NangateOpenCellLibrary_typical.lib'
    assert file_sha(lib)==mapping['liberty_sha256']
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
    pins='set planned_pins [dict create]\n'
    for p in plan['pins']:
        assert not any(c in p['pin'] for c in '{}\\\n\r')
        pins+='dict set planned_pins {'+p['pin']+'} 1\n'
        pins+='place_pin -pin_name {%s} -layer metal10 -location {%g %g} -pin_size {.8 .8}\n'%tuple([p['pin']]+p['xy_um'])
    pins+='set actual_pins {}\nforeach p [[ord::get_db_block] getBTerms] {if {[$p getSigType] ni {POWER GROUND}} {lappend actual_pins [$p getName]}}\n'
    pins+='if {[lsort $actual_pins] ne [lsort [dict keys $planned_pins]]} {error "Exact macro pin inventory mismatch"}\n'
    (out/'pins.tcl').write_text(pins)
    (out/'input.sdc').write_text(constraints(budget))
    with slot(base):shutil.copyfile(mapped/'mapped.v',out/'input.v')
    nickname='bv1_'+top
    config='export PLATFORM = nangate45\nexport DESIGN_NAME = '+top+'\nexport DESIGN_NICKNAME = '+nickname+'\n'
    config+='export VERILOG_FILES = '+str(out/'input.v')+'\nexport SDC_FILE = '+str(out/'input.sdc')+'\n'
    config+='export DIE_AREA = 0 0 %g %g\nexport CORE_AREA = 20 20 %g %g\n'%(side,side,side-20,side-20)
    config+='export PLACE_DENSITY = 0.45\nexport FOOTPRINT_TCL = '+str(out/'pins.tcl')+'\nexport KEEP_VARS = 1\n'
    config+='override export MIN_ROUTING_LAYER = metal1\noverride export MAX_ROUTING_LAYER = metal10\n'
    shutil.copyfile(root/'project/experiments/block_v1/native_input_diodes.tcl',out/'input-diodes.tcl')
    config+=config_suffix(40,.005,out/'input-diodes.tcl','metal10')
    (out/'config.mk').write_text(config)
    results=out/'flow/results/nangate45'/nickname/'base';results.mkdir(parents=True)
    for suffix in ('v','sdc'):
        p=results/('1_2_yosys.'+suffix);shutil.copyfile(out/('input.'+suffix),p);p.chmod(0o444)
    command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES='+str(cpus)]
    expected=dict(MIN_ROUTING_LAYER='metal1',MAX_ROUTING_LAYER='metal10',KEEP_VARS='1',LEC_CHECK='1',SEC_CHECK='0',
                  TECH_LEF=str(native),RCX_RULES=str(platform/'rcx_patterns.rules'),CAP_MARGIN='40',HOLD_SLACK_MARGIN='0.005')
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
        assert file_sha(out/'input.v')==mapping['mapped_sha256'];save()
    for suffix in ('v','sdc','def','odb','spef'):
        p=results/('6_final.'+suffix);assert p.is_file()
        result['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    result['passed']=True;result['pipeline_completed']=True;save()
