"""Prefabricated finite interface/relay macros; accepted M/S/T stay immutable."""
import json
from pathlib import Path
import re
import shutil
from interconnect_spef import sha as file_sha

PLATFORM=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')


def generate(root,out,kind):
    from interconnect_pin_profiles import profiles
    p=profiles(root);sources={}
    for pair,macro in [('mt','m'),('ts','t')]:
        rows=p['pairs'][pair]['placements']['east']['rows']
        sources[macro]={r['source'][1]:r['source_xy_um'] for r in rows if r['source'][0]=='left'}
    full=json.loads((root/'work/YUZE-LU/121/delivery-300mhz/M/interface/actual-escape.json').read_text())
    scale=full['dbu_per_um'];origin=full['macro_box_dbu']
    sources['m'].update({r['net']:[(r['source_m10_dbu'][i]-origin[i])/scale for i in (0,1)] for r in full['ports']})
    if kind=='bridge':
        top='linkclose_bridge_fixed';size=[740,160]
        inputs=dict(clk=1,reset=1,command_valid=1,command_ready=1,command_capture=1,
                    response_valid=1,response_data=128,response_error=1,response_saturated=1,
                    begin_valid=1,begin_ready=1,write_enable=1,write_ready=1)
        outputs=dict(response_ready=1,write_valid=1,write_index=10,write_data=128,
                     occupancy=2,observed_error=1,observed_saturation=1)
        decl=[];args=[];buffers=[]
        for direction,ports in [('input',inputs),('output',outputs)]:
            for port,n in ports.items():
                width='' if n==1 else '[%d:0] '%(n-1)
                decl.append(direction+' wire '+width+port)
                if direction=='output':
                    decl.append('wire '+width+'core_'+port)
                    args.append('.'+port+'(core_'+port+')')
                    strength='BUF_X16' if port in ('response_ready','write_valid','write_index','write_data') else 'BUF_X2'
                    for i in range(n):
                        index='' if n==1 else '[%d]'%i
                        buffers.append('%s drive_%s_%d(.A(core_%s%s),.Z(%s%s));'%(strength,port,i,port,index,port,index))
                else:args.append('.'+port+'('+port+')')
        ports_decl=[d for d in decl if not d.startswith('wire ')]
        body='module '+top+'('+','.join(ports_decl)+');\n'+';\n'.join(d for d in decl if d.startswith('wire '))+';\n'
        body+='linkclose_bridge core('+','.join(args)+');\n'+'\n'.join(buffers)+'\nendmodule\n'
        primary=[root/'project/rtl/block_v1/linkclose_bridge.sv']
    else:
        count=140 if kind=='bank' else 1
        top='linkclose_buffer'+str(count);size=[1040,160] if kind=='bank' else [64,64]
        inputs=dict(clk=1,reset=1,i=count);outputs=dict(o=count,canary=1)
        b='[%d:0] '%(count-1) if count>1 else ''
        body='module '+top+'(input wire clk,reset,input wire '+b+'i,output wire '+b+'o,output reg canary);\n'
        body+='always @(posedge clk)canary<=reset?0:~canary;\n'
        for i in range(count):
            bit='[%d]'%i if count>1 else ''
            body+='BUF_X16 relay_%d(.A(i%s),.Z(o%s));\n'%(i,bit,bit)
        body+='endmodule\n';primary=[]
    (out/'candidate.sv').write_text(body)
    pins=[];used=set()
    def add(name,direction,x,y):
        # A2um via landing exactly fills the native2um pad. Specialized rows
        # must have the same0.07um Y phase as native pins and custom tracks;
        # otherwise routing would need forbidden extra native M10 metal.
        if abs(y-round(y))<1e-9:y+=.07
        assert (x,y) not in used,(name,x,y)
        used.add((x,y));pins.append(dict(pin=name,layer='metal10',size_um=[2.,2.],xy_um=[x,y],direction=direction))
    deferred=[]
    for direction,ports in [('input',inputs),('output',outputs)]:
        for port,n in ports.items():
            for i in range(n):
                name=port if n==1 else port+'[%d]'%i
                if kind=='bridge' and port in ('response_data','write_data'):
                    xy=sources['m']['rsp_data[%d]'%i]
                    ys=sorted({v[1] for k,v in sources['m'].items() if k.startswith('rsp_data[')})
                    y=(136 if direction=='input' else 32)+8*ys.index(xy[1])
                    add(name,direction,xy[0],y)
                elif kind=='bridge' and port in ('response_valid','response_error','response_saturated','command_ready'):
                    native={'response_valid':'rsp_valid','response_error':'rsp_error','response_saturated':'rsp_saturated','command_ready':'cmd_ready'}[port]
                    xy=sources['m'][native]
                    # Separate scalar signals from both complete data rows.
                    y={'response_valid':112,'response_error':104,'response_saturated':96,'command_ready':88}[port]
                    add(name,direction,xy[0],y)
                elif kind=='bank' and port in ('i','o') and i<139:
                    native='read_data[%d]'%i if i<128 else 'read_index[%d]'%(i-128) if i<138 else 'read_valid'
                    if native not in sources['t']:
                        full_t=json.loads((root/'work/YUZE-LU/121/delivery-300mhz/T/interface/actual-escape.json').read_text())
                        sources['t'].update({r['net']:[(r['source_m10_dbu'][j]-full_t['macro_box_dbu'][j])/full_t['dbu_per_um'] for j in (0,1)]for r in full_t['ports']})
                    xy=sources['t'][native]
                    ys=sorted({v[1] for k,v in sources['t'].items() if k.startswith('read_data[')})
                    y=(16 if direction=='input' else 136)+8*ys.index(xy[1])
                    add(name,direction,xy[0],y)
                else:deferred.append((name,direction))
    slots=[(x+.095,y+.07) for y in range(16,int(size[1])-8,8) for x in range(24,int(size[0])-16,8)]
    for name,direction in deferred:
        x,y=next(xy for xy in slots if xy not in used)
        add(name,direction,x,y)
    plan=dict(schema='linkclose-fixed-interface-pins/1',pins=pins,die_um=size)
    (out/'pins.json').write_text(json.dumps(plan,indent=2)+'\n')
    return top,size,primary+[out/'candidate.sv'],plan


def implement(root,out,cpus,run,kind):
    from constraints import generate as constraints
    from pin_contract import script as pin_script
    from native_reroute import config_suffix
    assert cpus==16 and kind in ('bridge','bank','booster')
    top,size,sources,plan=generate(root,out,kind)
    lib=PLATFORM/'lib/NangateOpenCellLibrary_typical.lib'
    script='read_liberty -lib '+str(lib)+'\nread_verilog -sv '+' '.join(map(str,sources))+'\n'
    script+='hierarchy -check -top '+top+'\nsynth -top '+top+' -flatten -noabc\ndfflibmap -liberty '+str(lib)+'\nabc -liberty '+str(lib)+'\nclean\n'
    script+='write_verilog -noattr -noexpr structural.v\nwrite_json mapped.json\nstat -liberty '+str(lib)+'\n'
    (out/'map.ys').write_text(script);run(['yosys','-s',out/'map.ys'],'map.log')
    mapped=json.loads((out/'mapped.json').read_text())['modules'][top]
    count=sum(c['type']=='BUF_X16' for c in mapped['cells'].values())
    assert count==(140 if kind in ('bridge','bank') else 1),(kind,count)
    assert {p['pin'] for p in plan['pins']}=={name if len(p['bits'])==1 else '%s[%d]'%(name,i) for name,p in mapped['ports'].items() for i in range(len(p['bits']))}
    (out/'pins.tcl').write_text(pin_script(plan))
    budget=json.loads((root/'project/experiments/block_v1/physical-budget-300mhz.json').read_text())
    sdc=re.sub(r'create_clock -name core -period [^ ]+','create_clock -name core -period %.12g'%budget['clock_ns'],constraints(budget))
    # The standard place flow removes feed-through buffers then rebuilds weak
    # ones for its50fF boundary. These particular drivers are fixed resources.
    (out/'input.sdc').write_text(sdc)
    nickname='bv1_'+top
    cfg='export PLATFORM = nangate45\nexport DESIGN_NAME = '+top+'\nexport DESIGN_NICKNAME = '+nickname+'\n'
    cfg+='export VERILOG_FILES = '+str(out/'structural.v')+'\nexport SDC_FILE = '+str(out/'input.sdc')+'\n'
    cfg+='export DIE_AREA = 0 0 %g %g\nexport CORE_AREA = 12 12 %g %g\n'%(size[0],size[1],size[0]-12,size[1]-12)
    cfg+='export PLACE_DENSITY = 0.45\nexport FOOTPRINT_TCL = '+str(out/'pins.tcl')+'\nexport KEEP_VARS = 1\n'
    cfg+='override export MIN_ROUTING_LAYER = metal1\noverride export MAX_ROUTING_LAYER = metal10\n'
    protect='set block [ord::get_db_block]\n'
    protect+='foreach cell [get_cells '+('drive_*' if kind=='bridge' else 'relay_*')+'] {\n'
    protect+=' set inst [$block findInst [get_full_name $cell]]\n foreach t [$inst getITerms] {\n  set typ [[$t getMTerm] getSigType]\n  if {$typ ni {POWER GROUND}} {continue}\n  set name [expr {$typ eq "POWER" ? "VDD" : "VSS"}]\n  set net [$block findNet $name]\n  if {$net eq "NULL"} {set net [odb::dbNet_create $block $name];$net setSigType $typ}\n  $t connect $net\n }\n set_dont_touch $cell\n}\n'
    (out/'fixed-drivers-before-protection.tcl').write_text(protect)
    cfg+='export PRE_SYNTH_TCL = '+str(out/'fixed-drivers-before-protection.tcl')+'\n'
    hook=root/'project/experiments/block_v1/native_input_diodes.tcl'
    if kind=='bridge':
        # The independent unmodified deck identified an antenna on the long
        # clock root (867 >300). Protect this actual input before CTS too.
        text=hook.read_text();needle='  if {[$port getName] eq "clk"} {continue}\n'
        assert text.count(needle)==1
        hook=out/'clock-and-input-diodes.tcl';hook.write_text(text.replace(needle,''))
    cfg+=config_suffix(40,.005,hook,'metal10')
    (out/'config.mk').write_text(cfg)
    target=out/'flow/results/nangate45'/nickname/'base';target.mkdir(parents=True)
    for name,source in [('1_2_yosys.v',out/'structural.v'),('1_2_yosys.sdc',out/'input.sdc')]:shutil.copyfile(source,target/name)
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    record=dict(passed=False,kind=kind,top=top,die_um=size,fixed_buf_x16=count,stages=[],budget=budget,
                sources={str(p):file_sha(p) for p in sources},scope='Independent prefabricated finite interface candidate; accepted M/S/T unchanged. Native completion still requires independent STA/DRC/function/LEC before acceptance.')
    def save():(out/'linkclose-physical.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    for stage in ('do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish'):
        run(command+[stage],stage+'.log');record['stages'].append(stage);save()
    record['files']={p.name:dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size) for p in target.glob('6_final.*') if p.is_file()}
    record['passed']=True;save()


def repair_pg(root,out,cpus,run,kind):
    """Keep actual cell placement/signal routes; repair PG before fresh finish."""
    assert cpus==16 and kind in ('bridge','booster')
    original=out.parents[2]/'block-v1-20261029-913/tasks'/('linkclose-physical-'+kind)
    receipt=json.loads((original/'receipt.json').read_text());assert receipt['passed']
    record=json.loads((original/'linkclose-physical.json').read_text())
    assert file_sha(original/'linkclose-physical.json')==receipt['outputs']['linkclose-physical.json']
    target=out/'flow/results/nangate45'/('bv1_'+record['top'])/'base';target.mkdir(parents=True)
    for suffix in ('v','sdc'):
        source=Path(record['files']['6_final.'+suffix]['path'])
        assert file_sha(source)==record['files'][source.name]['sha256']
    source=Path(record['files']['6_final.odb']['path']);assert file_sha(source)==record['files'][source.name]['sha256']
    for name in ('structural.v','pins.json','pins.tcl','input.sdc','config.mk'):
        assert file_sha(original/name)==receipt['outputs'][name]
        text=(original/name).read_text().replace(str(original),str(out))
        if name=='input.sdc':text='\n'.join(line for line in text.splitlines() if not line.startswith('set_dont_touch'))+'\n'
        (out/name).write_text(text)
    for name in ('1_synth_lec.v','bv1-input-diodes.tsv'):
        path=source.parent/name;assert file_sha(path)==receipt['outputs'][str(path.relative_to(original))]
        shutil.copyfile(path,target/name)
    script='read_liberty {'+str(PLATFORM/'lib/NangateOpenCellLibrary_typical.lib')+'}\nread_db {'+str(source)+'}\nwrite_def before.def\nset block [ord::get_db_block]\nset f [open pg-repair.tsv w]\n'
    script+='''foreach inst [$block getInsts] {
 foreach term [$inst getITerms] {
  set typ [[$term getMTerm] getSigType]
  if {$typ ni {POWER GROUND}} {continue}
  set name [expr {$typ eq "POWER" ? "VDD" : "VSS"}]
  set net [$block findNet $name]
  if {$net eq "NULL"} {error "Original supply missing"}
  if {[$term getNet] ne $net} {
   puts $f "[$inst getName]\\t[[$term getMTerm] getName]\\t$name"
   set protected_before [$inst isDoNotTouch]
   $inst setDoNotTouch false
   $term connect $net
   $inst setDoNotTouch $protected_before
  }
 }
}
close $f
write_def after.def
'''
    script+='write_db {'+str(target/'5_route.odb')+'}\n'
    (out/'pg-repair.tcl').write_text(script);run(['openroad','-no_init','-exit',out/'pg-repair.tcl'],'pg-repair.log')
    # Exact logical supply connection edits only; the entire DEF outside the
    # SPECIALNETS association list, including all instance locations, pin boxes
    # and native signal wires, remains byte-identical.
    def geometry(path):
        # OpenDB writes the same supply in SPECIALNETS and NETS. Remove only
        # supply terminal associations, retaining every PG and signal wire,
        # placement, via, boundary and pin token for exact comparison.
        text=re.sub(r'\(\s+\S+\s+(?:VDD|VSS)\s+\)','',path.read_text())
        return text.split()
    assert geometry(out/'before.def')==geometry(out/'after.def'),'PG fix changed non-PG DEF content'
    shutil.copyfile(out/'input.sdc',target/'5_route.sdc')
    record.update(passed=False,source_pg_repair_receipt_sha256=file_sha(original/'receipt.json'),
        source_pg_repair_files=record.pop('files'),inherited_exact_placement_and_signal_routing=True,
        pg_repaired_terms=len((out/'pg-repair.tsv').read_text().splitlines()),stages=['do-1_synth','do-floorplan','do-place','do-cts','do-route'])
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    run(command+['do-finish'],'do-finish.log');record['stages'].append('do-finish')
    record['files']={p.name:dict(path=str(p),sha256=file_sha(p),bytes=p.stat().st_size)for p in target.glob('6_final.*')if p.is_file()}
    assert file_sha(source)==record['source_pg_repair_files']['6_final.odb']['sha256']
    record['passed']=True
    (out/'linkclose-physical.json').write_text(json.dumps(record,indent=2)+'\n')
