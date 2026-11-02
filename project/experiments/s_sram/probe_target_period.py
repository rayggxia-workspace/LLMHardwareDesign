"""Independent target-period SPICE diagnosis; not physical qualification.

Uses unchanged upstream waveform-generator functions and proves they reproduce
the original 5ns inputs before generating 300MHz inputs with the same 40ps slew.
The transistor circuit, load, measurement names and solver tolerances stay fixed.
"""
import argparse,ast,hashlib,io,json,os,re,subprocess,time
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class Check:
    @staticmethod
    def check(value,message):
        assert value,message

def main():
    ap=argparse.ArgumentParser()
    for key in ('source','stimuli','out'):
        ap.add_argument('--'+key,type=Path,required=True)
    a=ap.parse_args();assert os.environ.get('SLURM_JOB_ID')
    src=a.source.resolve();out=a.out.resolve();out.mkdir(exist_ok=False)
    old=json.loads((src/'receipt.json').read_text());assert old['passed'] and old['stages']==49
    record=dict(passed=False,qualified=False,scope='SPICE-only 49-stage candidate at 300MHz; no matching physical qualification',period_ns=10/3,slew_ns=0.04,inputs={})
    def save():(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    for p in [src/'receipt.json',a.stimuli,*[src/n for n in ('trimmed.sp','sram.sp','delay_meas.sp','delay_stim.sp')]]:
        record['inputs'][str(p)]=sha(p)
    tree=ast.parse(a.stimuli.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='stimuli')
    functions=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('gen_pwl','gen_pulse')];assert len(functions)==2
    namespace={'np':np,'debug':Check};exec(compile(ast.Module(body=functions,type_ignores=[]),str(a.stimuli),'exec'),namespace)
    class Wave:
        voltage=1.1
    def generated(method,*args):
        obj=Wave();obj.sf=io.StringIO();namespace[method](obj,*args);return obj.sf.getvalue().rstrip('\n')
    def numbers(s):return [float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',s)]
    def pwl_numbers(s):return numbers(s[s.index('PWL (')+5:])
    stimulus=(src/'delay_stim.sp').read_text();ratio=2/3;count=0
    def pwl(m):
        nonlocal count
        cycles=ast.literal_eval(m.group(1));times,values=map(list,zip(*cycles));assert times==[i*5.0 for i in range(len(times))]
        original=generated('gen_pwl',m.group(3),times,values,5.0,0.04,0.05)
        assert np.allclose(pwl_numbers(original),pwl_numbers(m.group(2)),rtol=0,atol=1e-12)
        count+=1
        return generated('gen_pwl',m.group(3),[i*record['period_ns'] for i in range(len(times))],values,record['period_ns'],0.04,0.05)
    stimulus=re.sub(r'(?m)^\* \(time, data\): (\[.*\])\n(V(\S+)\s+.*?PWL \(.*\))$',pwl,stimulus)
    assert count==138,count
    pulse=re.search(r'(?m)^\* PULSE: period=5.0\n(VCLK0 .*PULSE \(.*\))$',stimulus);assert pulse
    original=generated('gen_pulse','CLK0',0,1.1,5.0,5.0,0.04,0.04)
    assert numbers(original.split('PULSE (')[1])==numbers(pulse.group(1).split('PULSE (')[1])
    replacement=generated('gen_pulse','CLK0',0,1.1,record['period_ns'],record['period_ns'],0.04,0.04)
    stimulus=stimulus[:pulse.start()]+replacement+stimulus[pulse.end():]
    # Remove only the three faulty-name *additional* diagnostic probes. Every
    # original functional/timing measurement in delay_meas.sp remains present.
    stimulus,n=re.subn(r'(?m)^\.meas tran (?:wen_start|wen_end|wl_start) .*\n','',stimulus);assert n==3
    stimulus,n=re.subn(r'(?m)^\.TRAN 10p 75\.0n 0n 10p UIC$',f'.TRAN 10p {15*record["period_ns"]}n 0n 10p UIC',stimulus);assert n==1
    stimulus=stimulus.replace('period of 5.0n','period of '+str(record['period_ns'])+'n').replace(str(src),str(out))
    (out/'delay_stim.sp').write_text(stimulus)
    measures=(src/'delay_meas.sp').read_text()
    measures=re.sub(r'(?i)((?:TD|AT|from|to)=)([\d.]+)n',lambda m:m.group(1)+str(float(m.group(2))*ratio)+'n',measures)
    (out/'delay_meas.sp').write_text('* Original cycle-comment times refer to 5ns; actual measurement times are scaled to 300MHz.\n'+measures)
    for name in ('trimmed.sp','sram.sp'):
        data=(src/name).read_bytes();(out/name).write_bytes(data);assert sha(out/name)==sha(src/name)
    (out/'.spiceinit').write_text('set ngbehavior=hsa\noption klu\nset num_threads=8\n')
    record.update(native_waveforms_reproduced_at_5ns=count,unchanged_slew_ns=0.04,setup_fraction=0.05,unchanged_timestep_ps=10,outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()});save()
    cmd=['/public/home/yuzelu/opt/eda/issue155-sram/bin/ngspice','-b','-o',str(out/'timing.lis'),str(out/'delay_stim.sp')]
    start=time.monotonic()
    with (out/'stdout.log').open('w') as f:r=subprocess.run(cmd,cwd=out,stdout=f,stderr=subprocess.STDOUT)
    log=(out/'timing.lis').read_text();values={}
    for m in re.finditer(r'(?mi)^([a-z0-9_]+)\s*=\s*([-+\d.e]+)',log):values[m.group(1)]=float(m.group(2))
    checks={}
    for key,value in values.items():
        if key.startswith(('v_q_','v_qbar_')) and any(x in key for x in ('read_zero','read_one','write_zero','write_one')):
            high=('_one' in key)!=key.startswith('v_qbar_');checks[key]=value>0.99 if high else value<0.11
    checks['output_read_one']=values.get('v_delay_lh0',-1)>0.99
    checks['output_read_zero']=0<=values.get('v_delay_hl0',2)<0.11
    assert all(sha(Path(p))==digest for p,digest in record['inputs'].items())
    record.update(returncode=r.returncode,seconds=time.monotonic()-start,measurements=values,checks=checks,log_sha256=sha(out/'timing.lis'))
    record['passed']=r.returncode in (0,1) and len(checks)==10 and all(checks.values());save();print(json.dumps(record,indent=2))

if __name__=='__main__':main()
