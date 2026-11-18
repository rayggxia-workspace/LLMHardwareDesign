"""Calibrate idle and captured active read DMA with retained RTL state nets.

Mapped internal combinational activities remain propagated estimates. This
strengthens a boundary-only estimate without claiming gate-level replay.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from dma_synth_power import SPECS, ports, LIB, PLATFORM, digest, save

def run(args,log):
    with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True)

def net_names(net):
    names={}
    with net.open() as f:
        for line in f:
            m=re.match(r'^\s*(wire|reg|input|output)\s+(?:signed\s+)?(?:\[(\d+):(\d+)\]\s+)?(\\?\S+)\s*;',line)
            if m:names[m[4].lstrip('\\')] = abs(int(m[2])-int(m[3]))+1 if m[2] else 1
    return names

def mapped_wave(raw,dest,known,scope,begin,end,*,prefix='',boundary=None,time_divisor=3):
    if time_divisor<1:raise ValueError('invalid time divisor')
    stack=[];selected={};states={};seen=set();started=False;now=None;clk=None
    with raw.open() as src,dest.open('w') as out:
        out.write('$timescale 1ps $end\n$scope module dut $end\n')
        names=set(); excluded_widths={}
        for line in src:
            p=line.split()
            if p[:1]==['$scope']:stack.append(p[2])
            elif p[:1]==['$upscope']:stack.pop()
            elif p[:1]==['$var'] and p[1] in ('wire','reg','integer','logic'):
                full='/'.join(stack+[p[4]])
                inside=full.startswith(scope+'/')
                if not inside and full not in (boundary or {}).values():continue
                relative=full[len(scope)+1:]
                candidates=[prefix+relative.replace('/','.')] if inside else []
                if boundary:
                    candidates += [n for n,actual in boundary.items() if actual==full]
                for name in candidates:
                    if name not in known or name in names:continue
                    if int(p[2])!=known[name]:
                        # Packed RTL array elements can collide with scalar
                        # Yosys flattened bit names. Never bind these by name.
                        if name in (boundary or {}):raise ValueError('boundary width mismatch '+name)
                        excluded_widths[name]=[int(p[2]),known[name]]
                        continue
                    names.add(name);selected.setdefault(p[3],[]).append(name)
                    if name=='clk':clk=p[3]
                    suffix=' [%d:0]'%(int(p[2])-1) if int(p[2])>1 else ''
                    out.write('$var wire %s %s %s%s $end\n'%(p[2],p[3],name,suffix))
            elif p[:1]==['$enddefinitions']:break
        if clk is None:raise ValueError('no mapped clock')
        out.write('$upscope $end\n$enddefinitions $end\n')
        for line in src:
            if line.startswith('#'):
                now=int(line[1:])
                if now>end:break
                if now>=begin:
                    if not started:
                        out.write('#0\n')
                        for ident,value in states.items():out.write('b%s %s\n'%(value,ident))
                        seen.update(states);started=True
                    out.write('#%d\n'%((now-begin+time_divisor//2)//time_divisor))
            else:
                p=line.split()
                if not p:continue
                if p[0][0] in 'bB' and len(p)==2:value,ident=p[0][1:],p[1]
                elif p[0][0] in '01xz':value,ident=p[0][0],p[0][1:]
                else:continue
                if ident not in selected:continue
                if set(value)-{'0','1'}:raise ValueError('unknown mapped state '+ident)
                states[ident]=value
                if started:out.write('b%s %s\n'%(value,ident));seen.add(ident)
        out.write('#%d\n'%((end-begin+time_divisor//2)//time_divisor))
    if not started or seen!=set(selected):raise ValueError('incomplete retained RTL activity')
    return {'nets':len(names),'bits':sum(known[n] for n in names),'window_ps':(end-begin+time_divisor//2)//time_divisor,
            'retained_names':sorted(names),'excluded_width_mismatches':excluded_widths,
            'wave_sha256':digest(dest),'source_sha256':digest(raw)}

def bench(top,boundary):
    s=['`timescale 1ps/1ps','module tb;']
    init=[]
    for name,p in boundary.items():
        width='[%d:0]'%(p['width']-1) if p['width']>1 else ''
        s.append('%s %s %s;'%('logic' if p['direction']=='input' else 'wire',width,name))
        if p['direction']=='input':init.append("%s='0;"%name)
    s+=['%s dut(.*);'%top,'always #5000 clk=~clk;','string wave; integer mode, timeout; bit checking=0;']
    prefixes=['phase0_','phase1_'] if 'owner' in boundary else ['']
    for prefix in prefixes:
        s+=['always @(posedge clk) begin',
            'if(reset) begin %sd_fence_done_valid<=0;%sd_fence_done_generation<=0;end'%(prefix,prefix),
            'else begin %sd_fence_done_valid<=%sd_fence_valid && %sd_fence_ready;'%(prefix,prefix,prefix),
            'if(%sd_fence_valid && %sd_fence_ready) %sd_fence_done_generation<=%sd_fence_generation;end end'%(prefix,prefix,prefix,prefix)]
    checks=[n for n,p in boundary.items() if p['direction']=='output' and any(n.endswith(k) for k in ('d_req_valid','d_fence_valid','c_rsp_valid','fault_valid','debug_beats','debug_descriptors'))]
    s+=['always @(posedge clk) if(checking) begin']
    for n in checks:s+=['if(%s!==0) $fatal(1,"idle output %s nonzero");'%(n,n)]
    s+=['end','initial begin',*init,'reset=1;',
        'if(!$value$plusargs("wave=%s",wave)||!$value$plusargs("mode=%d",mode)) $fatal(1,"arguments");',
        '$dumpfile(wave); $dumpvars(0,tb);']
    for prefix in prefixes:s+=['%sd_fence_ready=1; %sc_fence_done_ready=\'1;'%(prefix,prefix)]
    s+=['repeat(4) @(negedge clk); reset=0;','timeout=0;',
        'while(%sdebug_generation<2) begin @(negedge clk);timeout++;if(timeout>100)$fatal(1,"reset fence not completed");end'%prefixes[0]]
    for n,p in boundary.items():
        if p['direction']!='input':continue
        if n.endswith('p_mode_native64'):s+=["%s=(mode&1)?'1:'0;"%n]
        elif n.endswith(('p_mode_client_drained','p_mode_valid','c_rsp_ready','d_req_ready','fault_ready')):s+=["%s='1;"%n]
    s+=['#1;timeout=0;','while(!(&%sp_mode_ready))begin @(negedge clk);timeout++;if(timeout>100)$fatal(1,"mode change not accepted");end'%prefixes[0],
        '@(negedge clk);']
    for n,p in boundary.items():
        if p['direction']=='input' and n.endswith('p_mode_valid'):s+=["%s='0;"%n]
    s+=['repeat(20) @(negedge clk);']
    if 'owner' in boundary:s+=['owner=1\'(mode>>1);repeat(4) @(negedge clk);']
    selected='(owner?phase1_p_mode_active:phase0_p_mode_active)' if 'owner' in boundary else 'p_mode_active'
    generation='(owner?phase1_debug_generation:phase0_debug_generation)' if 'owner' in boundary else 'debug_generation'
    s+=['if(%s !== ((mode&1)?3\'b111:3\'b000)) $fatal(1,"wrong active native mode");'%selected,
        'if(%s<2)$fatal(1,"transport generation not initialized");'%generation,
        '$display("IDLE_TRANSPORT_READY generation=%%0d",%s);'%generation,
        'checking=1; $display("IDLE_BEGIN %0t",$time);',
        'repeat(8192) @(negedge clk); $display("IDLE_END %0t",$time);',
        '$display("DMA_IDLE_RTL_PASS"); #1; $finish; end','endmodule']
    return '\n'.join(s)+'\n'

def main():
    root,bundle,out=map(Path,sys.argv[1:4]);variant=sys.argv[4];out.mkdir()
    rel,top,expected=SPECS[variant];physical=root/rel;key=Path('nangate45')/top/'base'
    net=physical/'flow/results'/key/'1_2_yosys.v';sdc=physical/'flow/results'/key/'1_2_yosys.sdc'
    if digest(net)!=expected:raise ValueError('netlist changed')
    known=net_names(net);boundary=ports(net,top)
    rtl=physical.parent
    sources=[rtl/'mc_dma_fabric_typed_p.sv']
    if top!='mc_dma_fabric_typed_p':
        sources=[rtl/'native_typed_dma_port.sv',rtl/'native_typed_dma_phase_mux.sv',*sources,physical/'c639_dma_phase_ports.sv']
    tb=out/'tb.sv';tb.write_text(bench(top,boundary))
    verilator=root.parent.parent/'opt/verilator-5.042/bin/verilator'
    # root is .../LLMHardware/zenanyan/issue-280-bscc-t6-01.
    if not verilator.exists():raise ValueError('missing registered Verilator')
    run([verilator,'--binary','--timing','--trace','--trace-max-width','16384','--trace-max-array','256',
         '--top-module','tb','-Wno-fatal','-j','12','--Mdir',out/'obj',*sources,tb],out/'build.log')
    windows={}
    specs=[]
    for mode in range(4 if top!='mc_dma_fabric_typed_p' else 2):
        p=out/('idle-%d'%mode);p.mkdir();raw=p/'rtl.vcd'
        run([out/'obj/Vtb','+mode=%d'%mode,'+wave='+str(raw)],p/'replay.log')
        log=(p/'replay.log').read_text()
        if 'DMA_IDLE_RTL_PASS' not in log:raise ValueError('idle failed')
        begin,end=[int(re.search('IDLE_'+name+r' (\d+)',log)[1]) for name in ('BEGIN','END')]
        if end-begin!=81920000:raise ValueError('wrong idle extent')
        specs.append((p,raw,'tb/dut',begin,end,'',None))
    for mode in (0,1):
        p=out/('active-%d'%mode);p.mkdir()
        label='mode-%d-gate-up'%mode
        # Use the accepted expanded trace. The older C639 FST omits the
        # 6144-bit response bus and must not be patched with invented activity.
        stage=root/'read-port-preflight'
        accepted=json.loads((stage/'stage-38793408/result.json').read_text())['designs'][top][label]
        raw=root/'wave-audit/audit-38782228'/label/'dma.vcd'
        if digest(raw)!=accepted['raw_sha256']:raise ValueError('accepted expanded trace changed')
        scope='TOP/test_native_decode638_product_replay/typed_dma'
        if top=='mc_dma_fabric_typed_p':scope+='/dma'
        times=[]
        with raw.open() as f:
            for line in f:
                if line.startswith('#'):
                    t=int(line[1:]);times=[t,t] if not times else [times[0],t]
        if times[1]-times[0]!=81920000:raise ValueError('active window changed')
        bindings={}
        if top!='mc_dma_fabric_typed_p':
            declared=json.loads((stage/'binding.json').read_text())[top]['windows'][label]['ports']
            bindings={n:v['scope']+'/'+v['signal'] for n,v in declared.items()}
        specs.append((p,raw,scope,*times,'mux.' if top!='mc_dma_fabric_typed_p' else '',bindings))
    # Idle and activity must annotate exactly the same retained nets; otherwise
    # different fallback/default activity could masquerade as dynamic energy.
    available=[]
    for p,raw,scope,begin,end,prefix,bindings in specs:
        trial=mapped_wave(raw,p/'available-state-300.vcd',known,scope,begin,end,prefix=prefix,boundary=bindings)
        available.append(set(trial['retained_names']))
    common=set.intersection(*available)
    if not set(boundary)<=common:raise ValueError('not all boundary ports are traced in every sample: '+str(set(boundary)-common))
    selected={n:known[n] for n in common}
    for p,raw,scope,begin,end,prefix,bindings in specs:
        wave=p/'mapped-state-300.vcd';activity=mapped_wave(raw,wave,selected,scope,begin,end,prefix=prefix,boundary=bindings)
        if not set(boundary)<=set(activity['retained_names']):raise ValueError('missing boundary names')
        tcl='\n'.join(['read_liberty {'+str(LIB)+'}',
          'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.tech.lef')+'}',
          'read_lef {'+str(PLATFORM/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
          'read_verilog {'+str(net)+'}','link_design '+top,'read_sdc {'+str(sdc)+'}',
          'read_vcd -scope dut {'+str(wave)+'}','report_activity_annotation','report_power -digits 9'])+'\n'
        (p/'power.tcl').write_text(tcl);run(['openroad','-no_init','-threads','12','-exit',p/'power.tcl'],p/'power.log')
        log=(p/'power.log').read_text()
        ann=re.findall(r'Annotated (\d+) pin activities\.',log)
        row=re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',log)
        if len(ann)!=1 or len(row)!=1 or 'problem parsing bus' in log or re.search(r'(?m)^(Error:|\[ERROR)',log):raise ValueError('activity/power rejected')
        if int(ann[0])<sum(p['width'] for p in boundary.values()):raise ValueError('incomplete mapped annotation')
        result={'power_w':dict(zip(('internal','switching','leakage','total'),map(float,row[0]))),'annotated':int(ann[0]),'activity':activity,'log_sha256':digest(p/'power.log')}
        windows[p.name]=result;save(p/'receipt.json',result);print('DMA_STATE_WINDOW_PASS',variant,p.name,flush=True)
    save(out/'calibration.json',dict(variant=variant,windows=windows,clock_mhz=300,wire_parasitics_loaded=False,
        equal_annotation_names=True,common_retained_nets=len(common),candidate_retained_nets=[len(x) for x in available],
        activity=('boundary-only' if len(common)==len(boundary) else 'boundary plus retained internal RTL nets')+' mapped combinational propagation; not gate-level numerical replay',
        operational_idle='automatic reset fence completed, no pending requests/responses/fence; native mode verified',
        input_sha256={str(p):digest(p) for p in [net,sdc,LIB,Path(__file__),*sources]},
        integration_status='requires per-model read counts/active residency and phase/shared deduplication'))
    print('DMA_STATE_CALIBRATION_PASS',variant,flush=True)

if __name__=='__main__':main()
