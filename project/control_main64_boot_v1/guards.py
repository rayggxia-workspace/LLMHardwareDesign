"""Supplement the matrix with preserved post-deployment BEGIN guards."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from contract import ROOT,HERE,PAIRS
from images import generate


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--pair',type=int,choices=range(9),required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);pair=PAIRS[a.pair]
    images=out/'images';generate(pair,images)
    text=(HERE/'tb_main64_boot.sv').read_text().replace('module tb_main64_boot;','module tb_main64_guards;',1)
    task='''    task automatic check_deployed_guards;
        reg [255:0] bad;
        for(integer who=0;who<3;who++)begin
            bad=manifest(who,epoch+1);bad[143:112]^=1;bad[79:48]^=32'h10000000;
            request(1,2'(who),0,bad,3);
            if(image_valid_o!=7)$fatal(1,"rejected ABI BEGIN revoked deployment");
            bad=manifest(who,epoch+1);bad[111:80]^=1;
            request(1,2'(who),0,bad,3);
            if(image_valid_o!=7)$fatal(1,"rejected topology BEGIN revoked deployment");
        end
        request(8,3,0,{128'b0,epoch+1,32'd1,epoch,32'd7},16'h107);
        request(12,1,0,0,KIND0==4 ? 16'd4 : 16'h106);
        request(12,2,0,0,KIND1==4 ? 16'd4 : 16'h106);
    endtask
'''
    anchor='    task automatic load_case';assert text.count(anchor)==1;text=text.replace(anchor,task+anchor)
    anchor='if(image_valid_o!=7)$fatal(1,"main64 deploy");run_job'
    assert text.count(anchor)==2;text=text.replace(anchor,'if(image_valid_o!=7)$fatal(1,"main64 deploy");if(mode==4)check_deployed_guards();run_job')
    text=text.replace('PASS main64-boot','PASS main64-guards')
    bench=out/'tb_main64_guards.sv';bench.write_text(text)
    data=json.loads((a.stage/'sources.json').read_text());sources=list(map(Path,data['sources']))
    cmd=['/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator','--binary','--timing','--assert','--timescale-override','1ns/1ps',
         '--x-initial','unique','--x-assign','unique','-Wno-fatal','--top-module','tb_main64_guards',f'-GKIND0={pair[0]}',f'-GKIND1={pair[1]}',
         '-j',os.environ.get('SLURM_CPUS_PER_TASK','4'),'--Mdir',str(out/'obj'),*['-I'+s for s in data['include_dirs']],data['waiver'],*map(str,sources),str(bench)]
    def run(cmd,name):
        with (out/name).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError(name+': '+str(r.returncode))
    run(cmd,'compile.log');results=[]
    for reset,seed in ((1,143),(2,143),(2,144)):
        log=f'guards-init-{reset}-{seed}.log'
        run([str(out/'obj/Vtb_main64_guards'),'+ROOT='+str(images),'+MODE=4','+verilator+rand+reset+'+str(reset),'+verilator+seed+'+str(seed)],log)
        assert 'PASS main64-guards' in (out/log).read_text()
        results.append({'reset_mode':reset,'seed':seed,'log_sha256':sha(out/log)})
        print('PASS R8.2 deployed guards',a.pair,log,flush=True)
    (out/'result.json').write_text(json.dumps({'schema':'main64-deployment-guards/1','passed':True,'pair':list(pair),'results':results,
        'source_sha256':{str(s):sha(s) for s in sources},'bench_sha256':sha(bench),
        'scope':'rejected ABI/topology BEGIN preserves old deployment, stale START and post-deploy ordinary writes rejected; same DUT RTL as primary matrix'},indent=2)+'\n')


if __name__=='__main__':main()
