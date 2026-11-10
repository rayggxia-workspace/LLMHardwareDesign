"""Slurm-only finite-U queue and staged-region qualification."""
import argparse,hashlib,json,os,platform,re,signal,subprocess,time,traceback
from pathlib import Path
from prepare import prepare,sha
HERE=Path(__file__).resolve().parent
VERILATOR=Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
BANK=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
SOURCES=['project/rtl/'+p for p in [
 'block_local_s/block_local_s_arbiter.sv','s_sram/local_s_base.sv','s_sram/block_feed_s16k_sram.sv',
 'block_v2/block_v2_n.sv','block_v2/block_v2_n_group.sv','block_v2/block_v2_n_exp.svh',
 'block_v2/block_v2_e.sv','block_v2/block_v2_e_compact.sv','block_v2/block_v2_e_pipeline.sv',
 'pu_leaf_base/pu_u_group.sv','pu_leaf_base/ucf_s_compute_client.sv','pu_leaf_base/pu_compact_e_service.sv',
 'pu_leaf_base/pu_queued_e_service.sv','pu_leaf_base/pu_nexp_region.sv',
 'pu_leaf_base/pu_nexp_shared.sv','pu_leaf_base/nexp_batch_adapter.sv']]
SEEDS=[(1,247),(2,247),(2,248)]
def require(c,m):
    if not c:raise ValueError(m)
def fields(line):return {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);root=p.parse_args().root.resolve()
    repo=root/'source';out=root/'results';out.mkdir(exist_ok=False)
    cpus=int(os.environ.get('SLURM_CPUS_PER_TASK',0));require(os.environ.get('SLURM_JOB_ID') and 1<=cpus<=4,'Slurm 1..4 required')
    manifest=json.loads((root/'inputs.json').read_bytes())
    for key,base in [('code_sha256',repo),('input_sha256',root)]:
        for n,h in manifest[key].items():require(sha(base/n)==h,'input drift '+n)
    require(sha(BANK)==BANK_SHA,'SRAM model drift')
    r=dict(passed=False,source_commit=manifest['source_commit'],source_sha256=manifest['code_sha256'],manifest_sha256=sha(root/'inputs.json'),
        job=os.environ['SLURM_JOB_ID'],node=platform.node(),cpus=cpus,commands=[],tests={},native_full_model_tokens_per_second=None,physical_clock_qualified=False)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def execute(command,log,timeout=1200):
        command=list(map(str,command));target=out/log;target.parent.mkdir(parents=True,exist_ok=True);start=time.monotonic()
        with target.open('wb') as stream:
            proc=subprocess.Popen(command,cwd=str(repo),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            try:code=proc.wait(timeout)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=proc.returncode
        text=target.read_text(errors='replace');r['commands'].append(dict(command=command,log=log,exit_code=code,seconds=time.monotonic()-start,sha256=sha(target)));save()
        require(code==0,log+' failed '+text[-3000:]);require(not re.search(r'%Warning-(PINMISSING|PINNOTFOUND|LATCH)',text),'bad production wiring/latch '+log)
        return text
    def build(label,top,params,baseline=False):
        obj=out/('obj-'+label);include=HERE;sources=[repo/x for x in SOURCES if not x.endswith('.svh')]
        if baseline:
            sources=[HERE/'baseline/pu_u_group.sv' if x.name=='pu_u_group.sv' else x for x in sources]
            include=out/'baseline-include';include.mkdir();s=(HERE/'tb_u_ports.svh').read_text().replace(',.E_QUEUE_DEPTH(DEPTH)','');(include/'tb_u_ports.svh').write_text(s)
        execute([VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wno-fatal','--x-initial','unique','--x-assign','unique',
            '-j',cpus,'--top-module',top,'--Mdir',obj,'-I'+str(include),'-I'+str(repo/'project/rtl/block_v2'),*params,HERE/(top+'.sv'),*sources,BANK],label+'-build.log')
        return obj/('V'+top)
    try:
        frozen=json.loads((HERE/'baseline/source.json').read_bytes());require(sha(HERE/'baseline/pu_u_group.sv')==frozen['sha256'],'baseline drift')
        r['tools']=dict(verilator=execute([VERILATOR,'--version'],'verilator-version.log',30).strip(),verilator_sha256=sha(VERILATOR),gcc=execute(['g++','--version'],'gcc-version.log',30).splitlines()[0])
        r['generation']=prepare(root,out/'generated');save()
        for label,depth,pipe,baseline in [('reference',0,0,True),('q0p0',0,0,False),('q0p1',0,1,False),('q2p0',2,0,False),('q2p1',2,1,False),('q4p0',4,0,False),('q4p1',4,1,False)]:
            exe=build(label,'tb_u_queue',['-GDEPTH='+str(depth),'-GPIPE='+str(pipe)],baseline);runs=[];r['tests'][label]=dict(passed=False,runs=runs)
            for case in r['generation']['cases']:
                for mode,seed in SEEDS:
                    key=f'{label}-{case["name"]}-{mode}-{seed}';prefix=out/'generated'/case['name'];log=key+'.log'
                    text=execute([exe,'+verilator+rand+reset+'+str(mode),'+verilator+seed+'+str(seed),'+NAME='+case['name'],
                      '+COUNT='+str(case['count']),'+STRESS='+str(case['stress']),'+CONTENTION='+str(case['contention']),
                      '+INIT='+str(prefix)+'-initial.hex','+FINAL='+str(prefix)+'-final.hex','+COMMANDS='+str(prefix)+'-commands.hex'],log,240)
                    lines=[s for s in text.splitlines() if s.startswith(('QUEUE_MEASURE ','QUEUE_PASS '))];require(len(lines)==2,'queue proof missing')
                    m,c=map(fields,lines);require(c==dict(values=case['count']*8,memory_words=1024,reset_cuts=3),'coverage mismatch')
                    require(m['reads']==case['traffic']['reads'] and m['writes']==case['traffic']['writes'],'independent traffic mismatch')
                    require(m['peak']<=(depth or 1),'finite queue');require(m['peak']==(depth or 1) if case['name']=='binary_s16' else True,'queue not exercised')
                    summary=key+'.summary.log';(out/summary).write_text('\n'.join(lines)+'\n')
                    runs.append(dict(case=case['name'],mode=mode,seed=seed,measurements=m,checks=c,log=log,log_sha256=sha(out/log),summary=summary,summary_sha256=sha(out/summary)));save()
            r['tests'][label]['passed']=True;save();print('QUEUE_CONFIG_PASS '+label,flush=True)
        for old,new in zip(r['tests']['reference']['runs'],r['tests']['q0p0']['runs']):
            require(all(old[k]==new[k] for k in ['case','mode','seed','measurements','checks']),'default mismatch')
        r['default_exact_pairs']=len(r['tests']['q0p0']['runs']);save()
        for format16 in (0,1):
            label='region'+str(format16);exe=build(label,'tb_nexp_region',['-GFORMAT16='+str(format16)]);runs=[];r['tests'][label]=dict(passed=False,runs=runs)
            for mode,seed in SEEDS:
                key=f'{label}-{mode}-{seed}';log=key+'.log';text=execute([exe,'+verilator+rand+reset+'+str(mode),'+verilator+seed+'+str(seed),'+VALUES='+str(out/'generated/nexp-values.hex')],log,240)
                lines=[s for s in text.splitlines() if s.startswith(('REGION_TILE ','REGION_MEASURE ','REGION_PASS '))]
                ms=[fields(s) for s in lines if s.startswith('REGION_MEASURE ')];cs=[fields(s) for s in lines if s.startswith('REGION_PASS ')]
                require(len(ms)==len(cs)==1 and cs[0]==dict(valid_cases=365,invalid_cases=6,values=24409,reset_cuts=1),'region coverage')
                require(ms[0]['reads']==(2752 if format16 else 5504) and ms[0]['writes']==5504,'region traffic')
                summary=key+'.summary.log';(out/summary).write_text('\n'.join(lines)+'\n')
                runs.append(dict(mode=mode,seed=seed,measurements=ms[0],checks=cs[0],tiles=[fields(s) for s in lines if s.startswith('REGION_TILE ')],log=log,log_sha256=sha(out/log),summary=summary,summary_sha256=sha(out/summary)));save()
            r['tests'][label]['passed']=True;save();print('REGION_CONFIG_PASS '+label,flush=True)
        r['functional_passed']=True;save()
        from area import area
        r['area']=area(repo,out/'area',execute);r['passed']=True
    except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
    r['output_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'result.json' and not any(x.startswith('obj-') for x in p.relative_to(out).parts)}
    save();print(json.dumps({'passed':r['passed'],'tests':len(r['tests']),'error':r.get('error')}),flush=True)
    return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
