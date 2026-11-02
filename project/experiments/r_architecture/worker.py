"""Isolated phased experiments; complete equivalence is a hard synthesis dependency."""
from pathlib import Path
import subprocess,os,json,time,hashlib,argparse,concurrent.futures,resource,re,threading
ROOT=Path(__file__).resolve().parents[3];INPUT=ROOT/'work/YUZE-LU/157'
LIB=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
local=threading.local()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,out,name,timeout=14400):
    with (out/(name+'.log')).open('w')as f:
        command=['taskset','-c',local.cpuset]+list(map(str,cmd))
        p=subprocess.run(command,cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    assert p.returncode==0,(name,p.returncode)
def task(name,out,slot):
    cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=96
    local.cpuset=','.join(map(str,cpus[slot*16:(slot+1)*16]))
    out.mkdir(parents=True,exist_ok=False);start=time.time();result=dict(task=name,passed=False,started=start,physical_qualified=False,cpuset=local.cpuset)
    try:
        if name=='controls':
            for negative in (False,True):
                folder=out/('negative'if negative else'positive');folder.mkdir()
                # Exhaustive symbolic toy includes both banks and all addresses, not a full R proof.
                src='''module control(input [511:0] a,b,input [3:0] addr,input role,output mismatch);
wire [511:0] joined=role?b:a;
wire [31:0] first=a[addr*32+:32],second=b[addr*32+:32];
wire [31:0] got=role?second:first;
assign mismatch=|(got ^ joined[addr*32+:32]);
endmodule\n'''
                if negative:src=src.replace('got=role?second:first','got=role?first:second')
                (folder/'control.sv').write_text(src)
                (folder/'control.ys').write_text('read_verilog -sv control.sv\nprep -top control\nsat -verify -prove mismatch 0 -show-inputs\n')
                with (folder/'solver.log').open('w')as f:p=subprocess.run(['taskset','-c',local.cpuset,'yosys','-s','control.ys'],cwd=folder,stdout=f,stderr=subprocess.STDOUT)
                text=(folder/'solver.log').read_text()
                assert (p.returncode==0 and 'SUCCESS!'in text)if not negative else(p.returncode!=0 and 'proof did fail'in text)
            result.update(scope='small symbolic selection positive and real wrong-polarity rejection; NOT full R equivalence')
        else:
            kind,operation=name.split('-');source=INPUT/'candidates'/kind/'block_v1_r.sv';result['rtl_sha256']=sha(source)
            if operation=='rtl':
                verilator='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
                os.environ['VERILATOR_ROOT']='/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator'
                run([verilator,'--cc','--exe','--build','-j','16','--output-groups','0','-Wno-fatal','--top-module','block_v1_r','-CFLAGS','-O1','--Mdir',out/'obj',source,INPUT/'inputs/test_recurrent_macro.cpp'],out,'build')
                results={}
                for init,seed,label in [(1,157,'all-ones'),(2,157,'random-157'),(2,158,'random-158')]:
                    run([out/'obj/Vblock_v1_r','+verilator+rand+reset+'+str(init),'+verilator+seed+'+str(seed)],out,label)
                    rows=[json.loads(line)for line in (out/(label+'.log')).read_text().splitlines()if line.startswith('{')];assert len(rows)==1 and rows[0]['passed'];results[label]=rows[0]
                result.update(initial_runs=results,scope='complete frozen RTL bench three initializations; no sequential equivalence claim')
            elif operation=='formal':
                assert kind in ('A1','A2')
                # Complete state and external equivalence, no narrowed state or excluded outputs.
                script=''
                for module,src in [('gold',INPUT/'candidates/A0/block_v1_r.sv'),('gate',source)]:
                    script+=f'read_verilog -sv {src}\nhierarchy -check -top block_v1_r\nproc\nmemory_map\nopt\nflatten\nopt_clean\nrename block_v1_r {module}\ndesign -stash {module}\n'
                script+='design -copy-from gold -as gold gold\ndesign -copy-from gate -as gate gate\nequiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple -seq 1\nequiv_induct -seq 2\nequiv_status -assert\nstat\n'
                (out/'complete.ys').write_text(script);run(['yosys','-s',out/'complete.ys'],out,'complete',timeout=21600)
                text=(out/'complete.log').read_text();assert 'Equivalence successfully proven!'in text and re.search(r'(?:0 are unproven|Found 0 unproven \$equiv cells)',text)
                result.update(complete_sequential_equivalence=True,all_state_and_external_outputs=True,scope='Yosys full design equiv_status -assert; generic memory lowering is proof preparation, not standard-cell synthesis')
            elif operation=='map':
                if kind!='A0':
                    proof=json.loads((out.parent/(kind+'-formal')/'receipt.json').read_text());assert proof['passed']and proof['complete_sequential_equivalence']and proof['rtl_sha256']==sha(source)
                script=(Path('DUMMY'))
                original=(INPUT/'inputs/map.ys').read_text()
                original=original.replace('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-342/src/project/rtl/block_library_v1/block_v1_r.sv',str(source)).replace('-I/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-342/src/project/rtl/block_library_v1','-I'+str(source.parent))
                assert sha(LIB)=='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
                (out/'map.ys').write_text(original);run(['yosys','-s',out/'map.ys'],out,'map',timeout=21600)
                assert (out/'mapped.json').is_file();result.update(liberty_sha256=sha(LIB),mapped_json_sha256=sha(out/'mapped.json'))
            else:raise AssertionError(operation)
        result['passed']=True
    except Exception as e:result['error']=repr(e)
    result.update(finished=time.time(),seconds=time.time()-start,maxrss_children_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    tasks={'controls':[],'A0-rtl':[],'A1-rtl':[],'A2-rtl':[],'A1-formal':['A0-rtl','A1-rtl','controls'],'A2-formal':['A0-rtl','A2-rtl','controls'],'A0-map':['A0-rtl'],'A1-map':['A1-formal'],'A2-map':['A2-formal']}
    states={k:'PENDING'for k in tasks};running={};slots={};done={}
    def save():(a.out/'queue-state.json').write_text(json.dumps(dict(tasks=states,results=done),indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
        while any(s in ('PENDING','RUNNING')for s in states.values()):
            for k,deps in tasks.items():
                if states[k]!='PENDING':continue
                if any(states[d]in ('FAILED','BLOCKED')for d in deps):states[k]='BLOCKED'
                elif all(states[d]=='PASSED'for d in deps)and len(running)<6 and (sum(128 if x.endswith(('-formal','-map'))else 24 for x in running.values())+(128 if k.endswith(('-formal','-map'))else 24))*1.2+16<=480:
                    # At most two generic full proofs; memory protected by whole-node allocation.
                    slot=next(s for s in range(6)if s not in slots.values());slots[k]=slot
                    states[k]='RUNNING';running[pool.submit(task,k,a.out/k,slot)]=k
            save()
            if not running:continue
            ready,_=concurrent.futures.wait(running,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
            for f in ready:
                k=running.pop(f);slots.pop(k)
                try:done[k]=f.result();states[k]='PASSED'if done[k]['passed']else'FAILED'
                except Exception as e:done[k]={'error':repr(e)};states[k]='FAILED'
                print(k,states[k],flush=True)
        save()
if __name__=='__main__':main()
