"""Source-bound Slurm-only unit RTL execution. No native AF qualification."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,platform,re,subprocess,sys
ALLOWED=Path('/public/home/yuzelu/Melodydt')
def fp(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--source-commit',required=True);ap.add_argument('--container-sha256',required=True);a=ap.parse_args()
    root=a.root.resolve();out=a.output.resolve();assert all(ALLOWED in p.parents for p in [root,out]) and not out.exists()
    assert os.environ.get('SLURM_JOB_ID','').isdigit() and os.environ.get('SLURM_JOB_NAME')=='zenanyan-w5-unit' and int(os.environ.get('SLURM_CPUS_PER_TASK','0'))>=8
    assert a.container_sha256=='c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df'
    out.mkdir(parents=True);(out/'logs').mkdir();(out/'results').mkdir()
    receipt=dict(status='RUNNING_W5_UNITS',started_utc=now(),source_commit=a.source_commit,root=str(root),output=str(out),node=platform.node(),python=sys.version,container_sha256=a.container_sha256,
                 Slurm={k:os.environ.get(k) for k in ['SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_CPUS_PER_TASK','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST']},commands=[],inputs=[],units=[],native_AF_tested=False,model_quality_accepted=False,physical_qualified=False)
    def save():(out/'results/run-receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
    def run(label,argv):
        log=out/'logs'/(label+'.log');start=now()
        with log.open('wb') as stream:r=subprocess.run(argv,cwd=root,stdout=stream,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(label=label,argv=argv,exit_code=r.returncode,started_utc=start,ended_utc=now(),**fp(log)));save()
        if r.returncode:raise RuntimeError(label+' exit '+str(r.returncode))
        return log.read_text(errors='replace')
    try:
        manifest=json.loads((root/'source-manifest.json').read_text());assert manifest['source_commit']==a.source_commit
        for row in manifest['files']:
            path=(root/row['path']).resolve();assert root in path.parents and fp(path)=={k:row[k] for k in ['bytes','sha256']},row['path'];receipt['inputs'].append(row)
        contract=json.loads((root/'work/Melodydt/151/h2/unit-contract.json').read_text())
        required=set(contract['reference_dependencies'])|{p for u in contract['units'] for p in u['compile_sources']}|{'work/Melodydt/151/h2/'+n for n in ['unit-contract.json','run_units.py','build_control_tables.py']}
        assert required=={r['path'] for r in manifest['files']}
        run('tables',['python3',str(root/'work/Melodydt/151/h2/build_control_tables.py'),'--root',str(root),'--output',str(out/'tables')])
        run('verilator-version',[contract['tool'],'--version']);run('compiler-version',['g++','--version'])
        for unit in contract['units']:
            assert fp(root/unit['compile_sources'][-1])['sha256']==unit['tb_sha256']
            obj=out/('obj_'+unit['id']);argv=[contract['tool'],'--binary','--timing','--assert','--threads','1','-j','8','-Wno-fatal','--top-module',unit['top'],'--Mdir',str(obj)]+unit['compile_sources']
            build=run('compile_'+unit['id'],argv)
            argv=[str(obj/('V'+unit['top']))]
            if unit['id']=='seq':argv+=['+rom='+str(out/'tables/g1_rom.hex'),'+meta='+str(out/'tables/g1_meta.hex')]
            text=run('simulate_'+unit['id'],argv);cases=re.findall(r'^CASE_PASS ([A-Z][A-Z0-9_]+)\s*$',text,re.M)
            assert cases==unit['cases'],(unit['id'],cases,unit['cases'])
            assert re.findall('^'+re.escape(unit['summary'])+'\s*$',text,re.M)==[unit['summary']]
            assert not re.search(r'FAIL_|%Error|%Fatal|Assertion failed|Aborting',text)
            receipt['units'].append(dict(id=unit['id'],cases=cases,scope=unit['scope'],warnings=re.findall(r'^%Warning[^\n]*',build,re.M),passed=True));save()
        for row in receipt['inputs']:assert fp(root/row['path'])=={k:row[k] for k in ['bytes','sha256']}
        receipt['generated_files']=[dict(path=str(p.relative_to(out)),**fp(p)) for d in ['tables','logs'] for p in sorted((out/d).rglob('*')) if p.is_file()]
        receipt['status']='PASS_W5_DMA_AND_SEQUENCER_UNITS_NOT_NATIVE_AF'
    except Exception as e:receipt['status']='FAIL';receipt['failure']=repr(e)
    finally:receipt['ended_utc']=now();save()
    print(json.dumps(dict(status=receipt['status'],receipt=str(out/'results/run-receipt.json'),failure=receipt.get('failure'),cases=sum(len(x['cases']) for x in receipt['units']))))
    return 0 if receipt['status'].startswith('PASS_') else 1
if __name__=='__main__':sys.exit(main())
