"""Map the real C639 mother peripherals with existing core/LC/switch cut out.

The cuts expose actual child pins and prevent double-counting accepted v4
components. Captured RTL state residency is reported separately from TLM.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from control_gap_calibration import boundary, constants, header, change, power, LIB, PLATFORM

TOP='native_product_controller'
SCOPE='TOP/test_native_decode638_product_replay/controller'
CUT=('mother_control_native64','lc_native_scope_controller','lc_native_service_router','mc_lc_packet128_switch')
PARAMS=('LOCAL_COUNT','PROVIDERS','ROUTES','PORT_BITS','SERVICE_STALL_LIMIT','TOPOLOGY','ABI','MC_IMAGE_ID','MC_CAPACITY','LC_CAPACITY','LC_IMAGE_IDS','REBIND_TARGET','LOCAL_TARGET','ROUTE_ENABLE','ROUTE_SCHEMA','ROUTE_PROVIDER_ABI','ROUTE_OP','ROUTE_PORT')

def digest(p):return sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def run(args,log):
    with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True)

def stub(path):
    # The module headers contain no semicolon until the complete port list.
    text=path.read_text();start=text.index('module ');stop=text.index(');',start)+2
    return '(* blackbox *) '+text[start:stop]+'\nendmodule\n'

def residency(raw):
    with raw.open() as f:
        h=header(f)
        selected={name:e for name,e in h.items() if name.startswith(SCOPE+'/') and name.rsplit('/',1)[-1] in ('state','life','seq') and e[2]!='parameter'}
        ids={e[0] for e in selected.values()};values={};now=first=None;totals={k:{} for k in selected}
        for line in f:
            if line.startswith('#'):
                t=int(line[1:]);first=t if first is None else first
                if now is not None:
                    for name,e in selected.items():
                        if e[0] not in values:raise ValueError('missing state initialization')
                        v=values[e[0]];totals[name][v]=totals[name].get(v,0)+t-now
                now=t
            else:
                c=change(line)
                if c and c[0] in ids:
                    if set(c[1])-{'0','1'}:raise ValueError('unknown state')
                    values[c[0]]=c[1]
    if not totals or any(sum(v.values())!=now-first for v in totals.values()):raise ValueError('state residency failed')
    return {'source_window_ps':now-first,'clock_scale':3,'state_ps_at_300mhz':{k:{str(int(s,2)):v/3 for s,v in row.items()} for k,row in totals.items()},
            'scope':'exact within the captured C639 windows, not a full model state trace'}

def main():
    bundle,out=map(Path,sys.argv[1:]);out.mkdir()
    inputs=bundle/'c639-inputs';src=out/'source';src.mkdir()
    with tarfile.open(inputs/'source.tar') as tar:
        for m in tar.getmembers():
            if not m.isfile() or not m.name.startswith('project/') or not m.name.endswith(('.sv','.svh')):continue
            path=src/m.name
            if not path.resolve().is_relative_to(src.resolve()):raise ValueError('unsafe archive member')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(m).read())
    mc=src/'project/rtl/mother_control_native';lc=src/'project/experiments/shared_x_control/rtl';bl=src/'project/rtl/block_local_native'
    sources=[mc/(s+'.sv') for s in ('native_product_controller','native_three_lc_cohort','mother_control_native64_transport128','mc_packet128_bridge',
              'native_pm_image_stream','native_mc_image_install','native_lc_image_install','native_request_sequence','native_token_sequence','native_phase_page_sequence')]
    sources.extend(bl/(s+'.sv') for s in ('native_prompt_index','native_retired_token_index'))
    for name in CUT:
        original=(lc if name.startswith('lc_') else mc)/(name+'.sv')
        dest=out/(name+'-blackbox.sv');dest.write_text(stub(original));sources.append(dest)
    waves={}
    for mode in (0,1):
        for kind in ('startup','gate-up'):
            raw=out/('mode-%d-%s.vcd'%(mode,kind));fst=inputs/('mode-%d'%mode)/(kind+'.fst')
            run([inputs/'fst_scope_vcd',fst,raw,SCOPE],raw.with_suffix('.log'))
            waves['mode-%d-%s'%(mode,kind)]=(fst,raw)
    params=constants(waves['mode-0-startup'][1],SCOPE,PARAMS)
    for _,raw in waves.values():
        if constants(raw,SCOPE,PARAMS)!=params:raise ValueError('C639 parameter mismatch')
    options=' '.join('-G%s=%d\'h%x'%(n,w,v) for n,(w,v) in params.items())
    ys='read_slang --keep-hierarchy --top %s %s %s\nflatten\nproc\nwrite_json %s\n'%(TOP,options,' '.join(map(str,sources)),out/'elaborated.json')
    (out/'elaborate.ys').write_text(ys);run(['yosys','-l',out/'elaborate.log',out/'elaborate.ys'],out/'elaborate-stdout.log')
    design=json.loads((out/'elaborated.json').read_text());module=design['modules'][TOP];bindings={};cuts=[]
    for name,cell in list(module['cells'].items()):
        child=design['modules'].get(cell['type'],{})
        if int(child.get('attributes',{}).get('blackbox','0'),2)!=1:continue
        for port,info in child['ports'].items():
            bits=cell['connections'][port]
            if not bits:continue
            cut='cut_%04d'%len(bindings)
            direction='input' if info['direction']=='output' else 'output'
            if direction=='input' and any(isinstance(x,str) for x in bits):raise ValueError('constant child output cut')
            module['ports'][cut]={'direction':direction,'bits':bits}
            module['netnames'][cut]={'hide_name':0,'bits':bits,'attributes':{}}
            bindings[cut]=name.replace('.','/')+'/'+port
        del module['cells'][name];cuts.append({'instance':name,'type':cell['type']})
    if len(cuts)!=10:raise ValueError('expected mother + switch + four LC + four routers: '+str(cuts))
    design['modules']={TOP:module};save(out/'cut.json',design);save(out/'cut-bindings.json',bindings)
    ys='\n'.join(['read_json '+str(out/'cut.json'),'synth -top '+TOP+' -flatten -noabc -noshare',
       'dfflibmap -liberty '+str(LIB),'abc -liberty '+str(LIB),'clean','read_liberty -lib '+str(LIB),'check -assert',
       'stat -liberty '+str(LIB),'write_verilog -noattr -noexpr '+str(out/'mapped.v'),'write_json '+str(out/'mapped.json')])+'\n'
    (out/'map.ys').write_text(ys);run(['yosys','-l',out/'map.log',out/'map.ys'],out/'map-stdout.log')
    mapped=json.loads((out/'mapped.json').read_text())['modules'][TOP]
    if any(c['type'].startswith('$') for c in mapped['cells'].values()):raise ValueError('unmapped cells')
    windows={}
    for name,(fst,raw) in waves.items():
        p=out/name;p.mkdir();wave=p/'ports-300.vcd'
        timing=boundary(raw,wave,mapped,SCOPE,bindings,'clk')
        tcl='\n'.join(['read_liberty {'+str(LIB)+'}',
            'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.tech.lef')+'}',
            'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
            'read_verilog {'+str(out/'mapped.v')+'}','link_design '+TOP,
            'create_clock -name core -period 3.333333333333 [get_ports clk]',
            'set_input_transition 0.05 [all_inputs]','read_vcd -scope dut {'+str(wave)+'}',
            'report_activity_annotation','report_power -digits 9'])+'\n'
        row=power(tcl,p,timing['port_bits']);row.update(timing,source_fst_sha256=digest(fst),wave_sha256=digest(wave),residency=residency(raw))
        windows[name]=row
    save(out/'calibration.json',dict(top=TOP,clock_mhz=300,wire_parasitics_loaded=False,
       activity='real RTL boundary propagation; cut accepted core, LC, router and switch to avoid duplicate energy',
       windows=windows,cut_instances=cuts,parameters=params,cell_count=len(mapped['cells']),netlist_sha256=digest(out/'mapped.v'),
       source_tar_sha256=digest(inputs/'source.tar'),input_sha256={str(p):digest(p) for p in [Path(__file__),LIB,bundle/'control_gap_calibration.py']},
       integration_status='C639 peripheral calibration; per-model deployed control and exact whole-model RTL residency still require matching evidence'))
    print('CONTROL_PERIPHERY_CALIBRATION_PASS',flush=True)

if __name__=='__main__':main()
