"""Slurm-only native U bridge / E pipeline functional and cycle measurements."""
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
 'pu_leaf_base/pu_nexp_shared.sv','pu_leaf_base/nexp_batch_adapter.sv']]
SEEDS=[(1,247),(2,247),(2,248)]
def require(c,m):
    if not c:raise ValueError(m)
def fields(line):return {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();repo=root/'source';out=root/'results'
    cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
    require(bool(os.environ.get('SLURM_JOB_ID')) and 1<=cpus<=4,'Slurm 1..4 CPUs required')
    manifest=json.loads((root/'inputs.json').read_bytes())
    for name,digest in manifest['code_sha256'].items():require(sha(repo/name)==digest,'source drift '+name)
    for name,digest in manifest['input_sha256'].items():require(sha(root/name)==digest,'input drift '+name)
    require(set(SOURCES)<=set(manifest['code_sha256']),'unlocked source')
    require(sha(BANK)==BANK_SHA,'SRAM model changed')
    out.mkdir(exist_ok=False)
    r=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=sha(root/'inputs.json'),
       source_sha256=manifest['code_sha256'],commands=[],tests={},job=os.environ['SLURM_JOB_ID'],
       node=platform.node(),cpus=cpus,physical_clock_qualified=False,native_full_model_tokens_per_second=None)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    def execute(command,log,timeout=900):
        command=list(map(str,command));target=out/log;target.parent.mkdir(parents=True,exist_ok=True)
        start=time.monotonic()
        with target.open('wb') as stream:
            proc=subprocess.Popen(command,cwd=repo,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            try:code=proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=proc.returncode
        text=target.read_text(encoding='utf8',errors='replace')
        r['commands'].append(dict(command=command,log=log,exit_code=code,seconds=time.monotonic()-start,sha256=sha(target)));save()
        require(code==0,log+' failed '+text[-2400:])
        require(not re.search(r'%Warning-(PINMISSING|PINNOTFOUND)',text),'unconnected production pins '+log)
        return text
    def test(label,top,bench,sources,params,kind):
        obj=out/('obj-'+label)
        execute([VERILATOR,'--binary','--timing','--assert','--timescale','1ns/1ps','-Wno-fatal',
          '--x-initial','unique','--x-assign','unique','-j',cpus,'--top-module',top,'--Mdir',obj,
          '-I'+str(repo/'project/rtl/block_v2'),*params,bench,*sources],label+'-build.log')
        records=[];r['tests'][label]=dict(passed=False,parameters=params,runs=records)
        for mode,seed in SEEDS:
            log=f'{label}-{mode}-{seed}.log'
            text=execute([obj/('V'+top),'+verilator+rand+reset+'+str(mode),'+verilator+seed+'+str(seed),
                          '+VECTORS='+str(out/'generated/e-vectors.hex')],log,240)
            prefixes={'u':['NEXP_U_PASS','E_U_PASS'],'e':['E_PIPE_PASS'],'compute':['NEXP_COMPUTE_PASS']}[kind]
            checks={}
            for prefix in prefixes:
                lines=[s for s in text.splitlines() if s.startswith(prefix+' ')]
                require(len(lines)==1,'missing/duplicate pass '+prefix);checks[prefix]=fields(lines[0])
            if kind=='u' and '-GBRIDGE=1' in params:
                lines=[s for s in text.splitlines() if s.startswith('BRIDGE_PASS ')]
                require(len(lines)==1 and fields(lines[0])==dict(checks=21,invalid=5,contention=1,reset=1),'bridge coverage missing')
                checks['BRIDGE_PASS']=fields(lines[0])
            if kind=='e':require(checks['E_PIPE_PASS']['values']==65536,'vector coverage missing')
            if kind=='u':require(checks['E_U_PASS']['checks']==128,'natural/extra-source U coverage missing')
            if kind=='compute':require(checks['NEXP_COMPUTE_PASS']['values']>=65536,'entire S16 domain missing')
            measures=[dict(prefix=s.split()[0],**fields(s)) for s in text.splitlines() if s.startswith(('E_PIPE_MEASURE ','E_U_MEASURE ','NEXP_FULL_U ','NEXP_COMPUTE '))]
            observations=[s for s in text.splitlines() if re.match(r'^\s*\d+ (Reading|Writing) ',s) or s.startswith(('E_U_MEASURE ','NEXP_FULL_U ','NEXP_U_PASS ','NEXP_NATIVE_PATH ','E_U_PASS '))]
            records.append(dict(mode=mode,seed=seed,checks=checks,measurements=measures,log=log,log_sha256=sha(out/log),
                observable_sha256=hashlib.sha256(('\n'.join(observations)+'\n').encode()).hexdigest(),observable_lines=len(observations)))
            save()
        r['tests'][label]['passed']=True;save();print('NATIVE_PASS '+label,flush=True)
    try:
        r['tools']=dict(verilator=execute([VERILATOR,'--version'],'verilator-version.log',30).strip(),
                       verilator_sha256=sha(VERILATOR),gcc=execute(['g++','--version'],'gcc-version.log',30).splitlines()[0])
        r['generation']=prepare(repo,out/'generated');save()
        sources=[repo/p for p in SOURCES if not p.endswith('.svh')]
        locked=r['generation']['baseline']['files'];baseline=[HERE/'baseline'/locked[p.relative_to(repo).as_posix()]['snapshot'] if p.relative_to(repo).as_posix() in locked else p for p in sources]
        test('old-u','tb_nexp_u',out/'generated/tb_u_baseline.sv',baseline+[BANK],[],'u')
        test('default-u','tb_nexp_u',out/'generated/tb_u.sv',sources+[BANK],[],'u')
        for old,new in zip(r['tests']['old-u']['runs'],r['tests']['default-u']['runs']):
            require(all(old[k]==new[k] for k in ('mode','seed','checks','measurements','observable_sha256','observable_lines')),'default cycle/data incompatibility')
        r['default_exact_pairs']=len(SEEDS);save()
        test('bridge-u','tb_nexp_u',out/'generated/tb_u.sv',sources+[BANK],['-GBRIDGE=1'],'u')
        test('bridge-pipeline-u','tb_nexp_u',out/'generated/tb_u.sv',sources+[BANK],['-GBRIDGE=1','-GPIPE=1'],'u')
        compute=[repo/'project/rtl'/p for p in ('pu_leaf_base/pu_nexp_shared.sv','pu_leaf_base/nexp_batch_adapter.sv','block_v2/block_v2_n.sv','block_v2/block_v2_n_group.sv')]
        test('compute','tb_nexp_compute',out/'generated/tb_compute.sv',compute,[],'compute')
        e_sources=[repo/'project/rtl/block_v2/block_v2_e.sv',repo/'project/rtl/block_v2/block_v2_e_pipeline.sv']
        for pipe in (0,1):test('e'+str(pipe),'tb_e_pipeline',HERE/'tb_e_pipeline.sv',e_sources,['-GPIPE='+str(pipe)],'e')
        r['functional_passed']=True;save()
        from area import area
        r['area']=area(repo,out/'area',execute)
        r['passed']=True
    except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
    r['output_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'result.json' and not any(x.startswith('obj-') for x in p.relative_to(out).parts)}
    save();print(json.dumps({'passed':r['passed'],'tests':len(r['tests']),'error':r.get('error')}),flush=True)
    return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
