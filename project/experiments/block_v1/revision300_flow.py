"""Fresh review-source native P&R at 300MHz with real 2um M10 landings.

Flow completion is a checkpoint, never independent final acceptance.
"""
import copy,json,math,re,shutil
from pathlib import Path


def implement(root,out,cpus,run,kind):
    from io_slots import file_sha,slot
    from constraints import generate as constraints
    from revision300_ports import generate,independent
    from pin_contract import script as pin_script
    from structural_view import unsigned,compare
    from native_reroute import config_suffix
    assert cpus==16 and kind in ('s','t','m','v','r')
    folder=root/'project/experiments/block_v1';base=out.parents[2]
    mapped=out.parent/('revision300-map-'+kind);tested=out.parent/('revision300-test-'+kind)
    records=[]
    for source,name in [(mapped,'revision300-rtl-map.json'),(tested,'revision300-rtl-test.json')]:
        receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
        assert file_sha(source/name)==receipt['outputs'][name]
        report=json.loads((source/name).read_text());assert report['passed']is True
        for path,digest in report['rtl_sha256'].items():assert file_sha(root/path)==digest
        records.append(report)
    mapping,test=records;top=mapping['top'];assert top==test['top']and mapping['rtl_sha256']==test['rtl_sha256']
    assert file_sha(mapped/'mapped.v')==mapping['mapped_sha256']
    flow=Path('/OpenROAD-flow-scripts/flow');platform=flow/'platforms/nangate45'
    lib=platform/'lib/NangateOpenCellLibrary_typical.lib';assert file_sha(lib)==mapping['liberty_sha256']
    expected=json.loads((mapped/'mapped.json').read_text())
    has_signed=any(v.get('signed')for m in expected['modules'].values()for k in ('ports','netnames')for v in m.get(k,{}).values())
    metadata=unsigned(expected)if has_signed else dict(removed_signed_metadata=[])
    (out/'unsigned.json').write_text(json.dumps(expected)+'\n')
    script='read_json '+str(out/'unsigned.json')+'\nhierarchy -check -top '+top+'\n'
    script+='write_verilog -noattr -noexpr -norename structural.v\nwrite_json structural.json\n'
    script+='design -reset\nread_liberty -lib '+str(lib)+'\nread_verilog structural.v\n'
    script+='hierarchy -check -top '+top+'\nwrite_json reparsed.json\n'
    (out/'structural.ys').write_text(script);run(['yosys','-s',out/'structural.ys'],'structural.log')
    expected=json.loads((out/'structural.json').read_text());observed=json.loads((out/'reparsed.json').read_text())
    proof=compare(expected,observed);negative=copy.deepcopy(observed)
    cell=next(iter(negative['modules'][top]['cells'].values()));values=next(v for v in cell['connections'].values()if v)
    values[0]='1'if values[0]!='1'else'0'
    rejected=False
    try:compare(expected,negative)
    except AssertionError:rejected=True
    assert rejected;proof.update(metadata=metadata,single_pin_bit_negative_rejected=True)
    (out/'structural-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    technology=json.loads((folder/'technology-2um-v1.json').read_text())
    native=platform/'lef/NangateOpenCellLibrary.tech.lef';assert file_sha(native)==technology['native_tech_sha256']
    text=lib.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',text));areas={}
    for i,m in enumerate(starts):
        chunk=text[m.end():starts[i+1].start()if i+1<len(starts)else len(text)]
        areas[m.group(1)]=float(re.search(r'\barea\s*:\s*([\d.eE+-]+)\s*;',chunk).group(1))
    active=sum(areas[name]*count for name,count in mapping['cells'].items())
    side=max(400,math.ceil((math.sqrt(active/.4)+40)/10)*10);area_side=side
    while True:
        try:plan,fixture,geometry=generate(mapping['ports'],side,technology);break
        except AssertionError as e:
            if not e.args or not isinstance(e.args[0],tuple)or e.args[0][0]!='Insufficient full-port tracks; enlarge native footprint':raise
            side+=10
            assert side<5000,'Unexpected port capacity requirement'
    (out/'pins.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'pins.tcl').write_text(pin_script(plan))
    coarse=independent(root,out,fixture,run)
    budget=json.loads((folder/'physical-budget-300mhz.json').read_text())
    sdc=re.sub(r'create_clock -name core -period [^ ]+','create_clock -name core -period %.12g'%budget['clock_ns'],constraints(budget))
    (out/'input.sdc').write_text(sdc)
    with slot(base):shutil.copyfile(out/'structural.v',out/'input.v')
    input_sha=file_sha(out/'input.v');nickname='bv1_'+top
    config='export PLATFORM = nangate45\nexport DESIGN_NAME = '+top+'\nexport DESIGN_NICKNAME = '+nickname+'\n'
    config+='export VERILOG_FILES = '+str(out/'input.v')+'\nexport SDC_FILE = '+str(out/'input.sdc')+'\n'
    config+='export DIE_AREA = 0 0 %g %g\nexport CORE_AREA = 20 20 %g %g\n'%(side,side,side-20,side-20)
    config+='export PLACE_DENSITY = 0.45\nexport FOOTPRINT_TCL = '+str(out/'pins.tcl')+'\nexport KEEP_VARS = 1\n'
    config+='override export MIN_ROUTING_LAYER = metal1\noverride export MAX_ROUTING_LAYER = metal10\n'
    # Include clock protection as well; previous V/R evidence required it.
    hook=(folder/'native_input_diodes.tcl').read_text().replace('  if {[$port getName] eq "clk"} {continue}\n','')
    (out/'input-diodes.tcl').write_text(hook)
    config+=config_suffix(40,.005,out/'input-diodes.tcl','metal10')
    config+='\nexport HOLD_SLACK_MARGIN = 0.020\n'
    (out/'config.mk').write_text(config)
    results=out/'flow/results/nangate45'/nickname/'base';results.mkdir(parents=True)
    for suffix in ('v','sdc'):
        p=results/('1_2_yosys.'+suffix);shutil.copyfile(out/('input.'+suffix),p);p.chmod(0o444)
    command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    wanted=dict(MIN_ROUTING_LAYER='metal1',MAX_ROUTING_LAYER='metal10',KEEP_VARS='1',LEC_CHECK='1',SEC_CHECK='0',
                TECH_LEF=str(native),RCX_RULES=str(platform/'rcx_patterns.rules'),CAP_MARGIN='40',HOLD_SLACK_MARGIN='0.020')
    actual={}
    for key,value in wanted.items():
        log='variable-'+key+'.log';run(command+['print-'+key],log)
        actual[key]=re.search(r'(?m)^'+key+r': (.+)$',(out/log).read_text()).group(1).strip()
        assert actual[key]==value,(key,actual[key],value)
    result=dict(schema='revision300-native-flow/1',passed=False,top=top,implementation_count=1,
                source_mapping_receipt_sha256=file_sha(mapped/'receipt.json'),source_function_receipt_sha256=file_sha(tested/'receipt.json'),
                rtl_sha256=mapping['rtl_sha256'],mapped_area_um2=active,die_um=[side,side],area_derived_side_um=area_side,
                footprint_rule='ceil10(sqrt(mapped_area/0.40)+40), min400; enlarge by10um only until complete coarse tracks fit',
                config_sha256=file_sha(out/'config.mk'),pins_sha256=file_sha(out/'pins.json'),budget=budget,actual_variables=actual,
                planned_complete_escape=geometry,planned_independent_gds=coarse,stages=[],final_files={},qualified_hard_macro=False,
                scope='Fresh native M1-M10 flow and declared full-port coarse geometry; complete actual native/upper readback, independent STA/DRC/function/LEC remain separate')
    def save():(out/'revision300-native-flow.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    for number,stage in enumerate(('do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish')):
        run(command+[stage],'%02d-%s.log'%(number,stage));result['stages'].append(stage)
        assert file_sha(out/'input.v')==input_sha;save()
    for suffix in ('v','sdc','def','odb','spef'):
        p=results/('6_final.'+suffix);assert p.is_file()
        result['final_files'][p.name]=dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)
    result['passed']=True;result['pipeline_completed']=True;save()
