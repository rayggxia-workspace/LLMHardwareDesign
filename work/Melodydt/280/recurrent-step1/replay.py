"""Replay the six captured 16-channel blocks per model against the eight-lane R."""
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import copy

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TMP = ROOT/'tmp/recurrent-step1'
sys.path.insert(0,str(HERE.parent))
from verify_arithmetic_capture import rounded
from verify_operator_capture import recompute

CAPTURES = {
    'qwen35': ['100eb342b158d2fe616e1abdf7d137edaea61c06ad21b098bb2be0627075c7f3',
               '9d30c1834f06f07b14301bfb35d5841a0673c2a18bf7dde299bda944c9b81733'],
    'falcon': ['7e98ddfc55dbf68a6ba851cb8547400f0797b88fd776f1cfe30f6381b01b0740',
               '32e68716c4671231458de0ac8d898f6751ed03db39fbe8ef37653e040937a898']}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def pack(values, bits):
    mask = (1 << bits)-1
    return sum((int(v)&mask) << (i*bits) for i,v in enumerate(values))


def fixed(values, frac):
    return np.rint(np.asarray(values,dtype=np.float64)*(1<<frac)).astype(np.int64)


def error(actual, expected):
    d = np.abs(np.asarray(actual)-np.asarray(expected))
    return dict(elements=d.size, mismatches=int(np.count_nonzero(d)), max_lsb=int(d.max()),
                abs_lsb_sum=int(d.sum()))


def run(model, simulator, wide, stress_steps, calibration):
    assert not wide or model=='falcon', 'wide load format is a dedicated SSM candidate'
    tag=model+'-wide' if wide else model
    if stress_steps:
        tag+='-stress'+str(stress_steps)
    if calibration:
        tag+='-cal'
    t = TMP/tag
    t.mkdir(parents=True,exist_ok=True)
    is_ssm = model=='falcon'
    frac = 24 if wide else 11 if is_ssm else 14
    coeff_bits=32 if wide else 16
    coeff_lanes=128//coeff_bits
    depth = 256 if is_ssm else 128
    owner = 1
    rtl = HERE/'rtl/block_v1_r_qwen35.sv'
    assert digest(rtl)=='4032c5edcbee9d38e1a51dd9f9c533e414d5263dd2440d7104a1688e73ca382d'
    # Candidate changes only the SSM update and readout shifts; conv taps and GDN retain Q14.
    if is_ssm:
        text=rtl.read_text()
        replacements=[('rne(dot[l],14)',f'rne(dot[l],mode==1 ? {frac} : 14)'),
                      ('product[l]},14)',f'product[l]}},mode==1 ? {frac} : 14)')]
        if wide:
            # Dedicated load protocol for this isolated SSM experiment. Products stay 65-bit.
            replacements += [
                ('signed [15:0] key','signed [31:0] key'),
                ('reg [31:0] key_valid','reg [63:0] key_valid'),
                ('reg signed [63:0] dot','reg signed [71:0] dot'),
                ('key_valid[n/8]||!query_valid[n/8]','key_valid[n/4]||!query_valid[n/4]'),
                ('cmd_index>31||pending_state','cmd_index>63||pending_state'),
                ('for(i=0;i<8;i=i+1)if(cmd_op==2)key[cmd_index*8+i]<=cmd_data[16*i+:16];else query[cmd_index*8+i]<=cmd_data[16*i+:16]',
                 'for(i=0;i<4;i=i+1)if(cmd_op==2)key[cmd_index*4+i]<=cmd_data[32*i+:32];else query[cmd_index*4+i]<=cmd_data[32*i+:32]')]
            assert text.count('{{17{key[row][15]}},key[row]}')==2
            text=text.replace('{{17{key[row][15]}},key[row]}','{key[row][31],key[row]}')
            replacements.append(('{{17{query[row][15]}},query[row]}','{query[row][31],query[row]}'))
        for old,new in replacements:
            assert text.count(old)==1
            text=text.replace(old,new)
        rtl=t/'block_v1_r.sv'
        rtl.write_text(text)
    phases={}
    for phase,sha in zip(['prefill','decode'],CAPTURES[model]):
        p=TMP/f'{model}-{phase}.json'
        assert digest(p)==sha
        samples=[s for s in json.loads(p.read_bytes())['samples']
                 if s['kind']==('mamba_state' if is_ssm else 'gdn_state')]
        for s in samples:
            assert recompute(s)==s['outputs']
            phases.setdefault(s['window'],[]).append(s)
    assert {k:len(v) for k,v in phases.items()}=={'prefill':2,'first_token':2,'decode':2}
    commands=[]
    def cmd(op,idx=0,data=0,expected=0):
        commands.append(f'{op} {idx} {data:032x} {expected:032x}')
    records=[]
    segments=[]
    exec_count=0
    for group in range(2):
        chains=[[phases['prefill'][group]],[phases['first_token'][group],phases['decode'][group]]]
        if calibration:
            chains=[[phases[p][group]] for p in ('prefill','first_token','decode')]
        if stress_steps:
            chain=[]
            for i in range(stress_steps):
                sample=copy.deepcopy(phases['first_token' if i%2==0 else 'decode'][group])
                if chain:
                    sample['inputs']['state']=(np.asarray(chain[-1]['outputs']['state_q16'])/65536).tolist()
                sample['outputs']=recompute(sample)
                chain.append(sample)
            chains=[chain]
        for chain in chains:
            start=0 if len(chain)==1 else 512
            if len(chain)>=2:
                assert np.array_equal(np.array(chain[0]['outputs']['state_q16']) / 65536,
                                      chain[1]['inputs']['state'])
            for lane0 in (0,8):
                first_command=len(commands)
                lanes=slice(lane0,lane0+8)
                active=fixed(chain[0]['inputs']['state'],16)[lanes].tolist()
                cmd(0,data=depth+(owner<<9)+(start<<73))
                for row in range(depth):
                    for h in (0,1):
                        cmd(1,2*row+h,pack([active[l][row] for l in range(4*h,4*h+4)],32))
                for step,s in enumerate(chain):
                    a=s['inputs']
                    key=fixed(a['key'],frac).tolist()
                    query=fixed(a['query'],frac).tolist()
                    limit=1<<(coeff_bits-1)
                    assert all(-limit<=v<limit for v in key+query)
                    x=fixed(a['value'],16)[lanes].tolist()
                    decay=round(a['decay']*2**31)
                    beta=round(a.get('beta',0)*2**31) if not is_ssm else 0
                    assert 0<=decay<=2**31 and 0<=beta<=2**31
                    for i in range(0,depth,coeff_lanes):
                        cmd(2,i//coeff_lanes,pack(key[i:i+coeff_lanes],coeff_bits))
                        cmd(3,i//coeff_lanes,pack(query[i:i+coeff_lanes],coeff_bits))
                    cmd(5,data=decay+(beta<<32))
                    for h in (0,1):
                        cmd(4,h,pack(x[4*h:4*h+4],32))
                    if is_ssm:
                        inject=[rounded(v*round(a['delta']*65536),16) for v in x]
                        skip=round(a['skip']*65536)
                        for h in (0,1):
                            cmd(4,2+h,pack(inject[4*h:4*h+4],32))
                            cmd(5,1+h,pack([skip]*4,32))
                        for i in range(2*depth):
                            cmd(15,i,pack([decay]*4,32))
                    position=start+step
                    cmd(6,data=int(is_ssm)+(owner<<2)+(step<<34)+(position<<66))
                    exec_count+=1
                    states=[]; outputs=[]
                    for l,row in enumerate(active):
                        decayed=[rounded(v*decay,31) for v in row]
                        if is_ssm:
                            correction=inject[l]
                        else:
                            prediction=rounded(sum(v*k for v,k in zip(decayed,key)),frac)
                            correction=rounded((x[l]-prediction)*beta,31)
                        update=[v+rounded(correction*k,frac) for v,k in zip(decayed,key)]
                        value=rounded(sum(v*q for v,q in zip(update,query)),frac)
                        if is_ssm:
                            value+=rounded(x[l]*skip,16)
                        assert all(-2**31<=v<2**31 for v in update+[value])
                        states.append(update);outputs.append(value)
                    for h in (0,1):
                        cmd(12,h,expected=pack(outputs[4*h:4*h+4],32))
                    cmd(7,data=owner+(step<<32)+(position<<64)+((position+1)<<96))
                    for row in range(depth):
                        for h in (0,1):
                            cmd(11,2*row+h,expected=pack([states[l][row] for l in range(4*h,4*h+4)],32))
                    records.append(dict(window=s['window'],group=group,lane0=lane0,
                        state=error(states,np.asarray(s['outputs']['state_q16'])[lanes]),
                        output=error(outputs,fixed(s['outputs']['output'],16)[lanes])))
                    active=states
                segments.append(dict(window=chain[0]['window'],group=group,lane0=lane0,
                                     start_command=first_command,end_command=len(commands)-1))
    vector=t/'commands.txt'
    vector.write_text('\n'.join(commands)+'\n')
    (t/'segments.json').write_text(json.dumps(segments,indent=2)+'\n')
    toolroot=ROOT/'work/Melodydt/179/control-rtl-min-41777f1/tools/msys2/ucrt64'
    env=dict(os.environ,PATH=str(toolroot/'bin')+os.pathsep+os.environ['PATH'])
    def invoke(args):
        p=subprocess.run(args,cwd=t,env=env,capture_output=True,text=True)
        if p.returncode:
            raise RuntimeError(f'{p.returncode}: {p.stdout} {p.stderr}')
        return p.stdout
    if simulator=='modelsim':
        bin_dir=Path('D:/EDA/modeltech64_2020.4/win64')
        if not (t/'work').exists():
            invoke([bin_dir/'vlib.exe','work'])
        invoke([bin_dir/'vlog.exe','-sv',rtl,HERE/'replay_tb.sv'])
        log=invoke([bin_dir/'vsim.exe','-c','-do','onbreak {quit -code 1}; run -all; quit -f',
                    '-onfinish','exit','work.replay_tb','+vectors=commands.txt',f'+count={len(commands)}'])
        version='ModelSim SE-64 2020.4'
    else:
        invoke([toolroot/'bin/iverilog.exe','-B',toolroot/'lib/ivl','-g2012','-s','replay_tb',
                '-o','replay.vvp',rtl,HERE/'replay_tb.sv'])
        log=invoke([toolroot/'bin/vvp.exe','replay.vvp','+vectors=commands.txt',f'+count={len(commands)}'])
        version='Icarus Verilog 13.0'
    assert f'RTL_REPLAY_PASS commands={len(commands)} execs={exec_count}' in log,log
    data=dict(model=model,coefficient_bits=coeff_bits,coefficient_fraction_bits=frac,simulator=version,period_ns=5,
              source_commit_reference='f034be2b7c87137b92f7bfce274a5485647e512d',
              candidate_rtl_sha256=digest(rtl),capture_sha256=CAPTURES[model],
              testbench_sha256=digest(HERE/'replay_tb.sv'),driver_sha256=digest(Path(__file__)),
              commands_sha256=digest(vector),rtl_log=log,vs_frozen_tlm_q16=records,
              stress_steps=stress_steps,stress_input='alternating captured coefficients and values; reference state evolves with Q16 writeback' if stress_steps else None)
    (HERE/(tag+'-receipt.json')).write_text(json.dumps(data,indent=2)+'\n')
    print(model,log,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('model',choices=list(CAPTURES))
    parser.add_argument('--simulator',choices=['modelsim','iverilog'],default='modelsim')
    parser.add_argument('--wide-ssm',action='store_true')
    parser.add_argument('--stress-steps',type=int,default=0)
    parser.add_argument('--calibration',action='store_true')
    args=parser.parse_args()
    run(args.model,args.simulator,args.wide_ssm,args.stress_steps,args.calibration)
