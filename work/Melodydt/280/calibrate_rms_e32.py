"""Paired no-wire E32 boundary-activity power using bounded real RMS samples."""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from calibrate_rms_n import clip_ports
from verify_arithmetic_capture import rounded as rne

root,bundle,out,mapped=map(Path,sys.argv[1:5]); captures=list(map(Path,sys.argv[5:]))
out.mkdir(); mapping=json.loads((mapped/'receipt.json').read_text())
def digest(p): return sha256(p.read_bytes()).hexdigest()
for p,h in mapping['inputs_sha256'].items():
    if digest(Path(p))!=h: raise ValueError('mapped input changed')
if mapping['exit_code'] or digest(mapped/'mapped.v')!=mapping['outputs_sha256']['mapped.v']:
    raise ValueError('unaccepted or changed mapping')
platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
lib=platform/'lib/NangateOpenCellLibrary_typical.lib'
if digest(lib)!=mapping['liberty_sha256']: raise ValueError('liberty changed')
ports=json.loads((mapped/'mapped.json').read_text())['modules']['e_s32_ap64']['ports']
rtl=root/'m-product/wide-38792112/source/project/rtl/w8a16_v1'
sources=[rtl/'e_s32_native.sv',rtl/'e_s32_ap64.sv',bundle/'tb_rms_e32_activity.sv']
mapped_hashes={Path(p).name:h for p,h in mapping['inputs_sha256'].items()}
for p in sources[:2]:
    if digest(p)!=mapped_hashes[p.name]: raise ValueError('RTL and netlist source differ')
verilator=Path.home()/'LLMHardware/opt/verilator-5.042/bin/verilator'
with (out/'build.log').open('w') as log:
    subprocess.run([str(verilator),'--binary','--timing','--trace','--trace-depth','2','-Wno-fatal','-j','12',
                    '--top-module','tb_rms_e32_activity','--Mdir',str(out/'obj')]+list(map(str,sources)),
                   stdout=log,stderr=subprocess.STDOUT,check=True)
results=[]
def beats(values):
    if any(not -2**31<=v<2**31 for v in values): raise ValueError('S32 overflow')
    return [sum((v&0xffffffff)<<(32*j) for j,v in enumerate(values[i:i+2])) for i in (0,2)]
for capture in captures:
    if not json.loads(capture.with_name('arithmetic-capture-check.json').read_text())['passed']:
        raise ValueError('capture not accepted')
    for sample in json.loads(capture.read_text())['samples']:
        work=out/('sample-%03d'%len(results)); work.mkdir(); lines=[]
        shift=13+sample['extra'] if sample['shifted_format'] else 13
        for i in range(0,len(sample['source']),4):
            x=[v<<sample['shift'] for v in sample['source'][i:i+4]]; factor=[sample['factor']]*4
            gamma=sample['gamma'][i:i+4]; mid=[rne(v*f,shift) for v,f in zip(x,factor)]
            final=[rne(v*g,17+sample['output_shift']) for v,g in zip(mid,gamma)]
            if final!=sample['expected'][i:i+4]: raise ValueError('RMS mismatch')
            for sh,a,b,y in ((shift,x,factor,mid),(17+sample['output_shift'],mid,gamma,final)):
                lines.append(str(sh)+' '+' '.join('{:016x}'.format(v) for vec in (a,b,y) for v in beats(vec)))
        (work/'vectors.txt').write_text('\n'.join(lines)+'\n')
        raw=work/'rtl.vcd'
        run=subprocess.run([str(out/'obj/Vtb_rms_e32_activity'),'+vectors='+str(work/'vectors.txt'),'+wave='+str(raw)],capture_output=True,text=True)
        (work/'rtl.log').write_text(run.stdout+run.stderr); run.check_returncode()
        accepted=re.search(r'RMS_E32_PASS cases=(\d+)',run.stdout)
        match=re.search(r'E32_ACTIVITY_PASS active_start=(\d+) active_end=(\d+) idle_end=(\d+)',run.stdout)
        if not accepted or int(accepted[1])!=len(lines) or not match: raise ValueError('RTL acceptance absent')
        start,end,idle=map(int,match.groups())
        if end-start!=idle-end: raise ValueError('unequal paired windows')
        powers={}
        for name,lo,hi in (('active',start,end),('idle',end,idle)):
            wave=work/(name+'.vcd');clip_ports(raw,wave,ports,lo,hi,testbench='tb_rms_e32_activity',time_divisor=1)
            script=work/(name+'.tcl')
            script.write_text('\n'.join(['read_liberty {'+str(lib)+'}',
                'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
                'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
                'read_verilog {'+str(mapped/'mapped.v')+'}','link_design e_s32_ap64',
                'create_clock -name core -period 3.334 [get_ports clk]','set_input_transition 0.05 [all_inputs]',
                'read_vcd -scope dut {'+str(wave)+'}','report_activity_annotation','report_power -digits 9'])+'\n')
            with (work/(name+'.log')).open('w') as log:
                subprocess.run(['openroad','-no_init','-threads','4','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT,check=True)
            text=(work/(name+'.log')).read_text()
            totals=re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',text)
            annotations=re.findall(r'Annotated (\d+) pin activities\.',text)
            if len(totals)!=1 or len(annotations)!=1 or re.search(r'(?m)^(Error:|\[ERROR)',text) or 'problem parsing bus' in text:
                raise ValueError('power annotation failure')
            if int(annotations[0])<sum(len(p['bits']) for p in ports.values()): raise ValueError('incomplete boundary activity')
            powers[name]=dict(power_w=dict(zip(('internal','switching','leakage','total'),map(float,totals[0]))),
                              annotated=int(annotations[0]),wave_sha256=digest(wave),power_log_sha256=digest(work/(name+'.log')))
        result=dict(signature=sample['signature'],words=sample['words'],packets=len(lines),window_ps=end-start,power=powers,
                    incremental_nj=(powers['active']['power_w']['total']-powers['idle']['power_w']['total'])*(end-start)/1000,
                    capture=str(capture),capture_sha256=digest(capture),vectors_sha256=digest(work/'vectors.txt'),rtl_log_sha256=digest(work/'rtl.log'))
        (work/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result)
        print('RMS_E32_POWER_SAMPLE_PASS',len(results),sample['signature'],flush=True)
result=dict(scope='E32 factor and gamma products only; SRAM/N/scan/apply/wait residency excluded',
    activity='RTL boundary VCD propagated through mapped cells; no internal gate replay',wire_parasitics_loaded=False,timing_signoff=False,
    nominal_clock_mhz=300,period_ps=3334,scheduler_latency_reconciled=False,
    mapped_netlist_sha256=digest(mapped/'mapped.v'),liberty_sha256=digest(lib),
    sources_sha256={str(p):digest(p) for p in sources},verilator_sha256=digest(verilator),
    samples=results)
(out/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
print('RMS_E32_POWER_PASS',len(results),flush=True)
