"""Source-bound residual T/S/E slice validation; run only in own Slurm job."""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

ALLOWED=Path('/public/home/yuzelu/Melodydt').resolve()


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def fp(path):
    h=hashlib.sha256();size=0
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):
            size+=len(block);h.update(block)
    return dict(bytes=size,sha256=h.hexdigest())


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--source-commit',required=True)
    ap.add_argument('--container-sha256',required=True);args=ap.parse_args()
    root=args.root.resolve();out=args.output.resolve()
    assert all(ALLOWED in p.parents for p in [root,out]) and not out.exists()
    assert os.environ.get('SLURM_JOB_ID','').isdigit()
    assert os.environ.get('SLURM_JOB_NAME')=='zenanyan-atsp'
    assert int(os.environ.get('SLURM_CPUS_PER_TASK','0'))>=8
    assert args.container_sha256=='c742bf99ea498fb4da5135bc83fd1677abcebe0e64470e6a115f2baecb3905df'
    out.mkdir(parents=True);(out/'logs').mkdir();(out/'results').mkdir()
    receipt=dict(status='RUNNING_ATSP',source_commit=args.source_commit,started_utc=now(),node=platform.node(),
        root=str(root),output=str(out),container_sha256=args.container_sha256,python=sys.version,
        Slurm={k:os.environ.get(k) for k in ['SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_CPUS_PER_TASK','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST']},
        commands=[],inputs=[],dump_checks=[],full_Attention_implemented=False,model_quality_accepted=False,physical_qualified=False)
    def save():(out/'results/run-receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode('utf8'))
    def run(label,argv):
        log=out/'logs'/(label+'.log');started=now()
        with log.open('wb') as stream:r=subprocess.run(argv,cwd=str(root),stdout=stream,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(label=label,argv=argv,exit_code=r.returncode,started_utc=started,ended_utc=now(),**fp(log)))
        save()
        if r.returncode:raise RuntimeError(label+' exit '+str(r.returncode))
        return log.read_text(errors='replace')
    try:
        source=json.loads((root/'source-manifest.json').read_text());assert source['source_commit']==args.source_commit
        for row in source['files']:
            p=(root/row['path']).resolve();assert root in p.parents
            assert fp(p)=={k:row[k] for k in ['bytes','sha256']},row['path']
            receipt['inputs'].append(row)
        helper=root/'work/Melodydt/151/atsp'
        contract=json.loads((helper/'atsp-tb-contract.json').read_text())
        fixtures=json.loads((helper/'fixture-contract.json').read_text())
        source_paths=[x['path'] for x in source['files']]
        required=set(contract['compile_sources'])|set('work/Melodydt/151/atsp/'+name for name in ['atsp-tb-contract.json','fixture-contract.json','build_atsp_vectors.py','run_atsp_job.py'])
        assert len(source_paths)==len(set(source_paths)) and set(source_paths)==required
        assert len(contract['compile_sources'])==len(set(contract['compile_sources']))
        for path in contract['compile_sources']+contract.get('include_dirs',[]):
            assert not Path(path).is_absolute()
            target=(root/path).resolve();assert target==root or root in target.parents,path
        dump_contract=[dict(actual_file=x['filename'],golden_file=x['golden_relative_path'],bytes=x['expected_bytes'],sha256=x['expected_sha256']) for x in contract['binary_dumps']]
        assert all(x['bytes']==4096 for x in dump_contract)
        dump_pairs=[(x['actual_file'],x['golden_file']) for x in dump_contract]
        fixture_pairs=[(x['actual_dump'],x['golden_file']) for name in fixtures['fixture_ids'] for x in fixtures['fixtures'][name]['binary_dumps']]
        assert len(dump_pairs)==len(set(dump_pairs))==9 and set(dump_pairs)==set(fixture_pairs)
        assert len(set(x[0] for x in dump_pairs))==9
        tb=root/'project/tb/block_connection_w4/block_w4_atsp_tb.sv'
        assert fp(tb)['sha256']==contract['tb_sha256']
        expected=contract['expected_case_ids'];assert len(expected)>15 and len(expected)==len(set(expected))
        run('vectors',['python3',str(helper/'build_atsp_vectors.py'),'--output',str(out/'vectors'),'--self-check','--source-commit',args.source_commit])
        receipt['vector_index']=fp(out/'vectors/fixture-index.json')
        vector_files=[]
        for name in fixtures['fixture_ids']:
            for filename,expected_file in fixtures['fixtures'][name]['files'].items():
                path=(out/'vectors'/name/filename).resolve()
                assert (out/'vectors').resolve() in path.parents
                assert fp(path)==expected_file,(str(path),fp(path),expected_file)
                vector_files.append(dict(path=str(path),**expected_file))
        receipt['vector_files']=vector_files
        run('verilator-version',['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--version'])
        run('compiler-version',['g++','--version'])
        obj=out/'obj_atsp';top=contract['top']
        argv=['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--binary','--timing','--assert','--threads','1','-j','8','-Wno-fatal','--top-module',top,'--Mdir',str(obj)]
        argv+=['-I'+str(root/p) for p in contract.get('include_dirs',[])]+contract['compile_sources']
        build=run('compile',argv);receipt['warnings']=re.findall(r'^%Warning[^\n]*',build,re.M)
        dumpdir=out/'results/dumps';dumpdir.mkdir()
        text=run('simulate',[str(obj/('V'+top)),'+vectors='+str(out/'vectors'),'+dump_dir='+str(dumpdir)])
        observed=re.findall(r'^CASE_PASS ([A-Z][A-Z0-9_]+)\s*$',text,re.M)
        summaries=re.findall(r'^PASS_ATSP cases=(\d+)\s*$',text,re.M)
        assert observed==expected,(observed,expected)
        assert summaries==[str(len(expected))],summaries
        assert not re.search(r'FAIL_|%Error|%Fatal|Assertion failed|Aborting',text)
        receipt['observed_case_ids']=observed
        # Each dump contract binds real output bytes, rather than a TB PASS label.
        for row in dump_contract:
            actual=(dumpdir/row['actual_file']).resolve();golden=(out/'vectors'/row['golden_file']).resolve()
            assert dumpdir.resolve() in actual.parents and (out/'vectors').resolve() in golden.parents
            assert fp(actual)['bytes']==4096 and fp(golden)['bytes']==4096
            assert fp(actual)=={k:row[k] for k in ['bytes','sha256']}
            assert fp(actual)==fp(golden),(str(actual),fp(actual),fp(golden))
            receipt['dump_checks'].append(dict(actual_file=str(actual),golden_file=str(golden),passed=True,**fp(actual)))
        assert len(receipt['dump_checks'])==9
        assert set(p.name for p in dumpdir.iterdir() if p.is_file())==set(x[0] for x in dump_pairs)
        for row in vector_files:
            assert fp(Path(row['path']))=={k:row[k] for k in ['bytes','sha256']},row['path']
        for row in receipt['inputs']:
            assert fp(root/row['path'])=={k:row[k] for k in ['bytes','sha256']},row['path']
        receipt['status']='PASS_ATSP_RESIDUAL_SLICE_NOT_FULL_ATTENTION'
    except Exception as error:
        receipt['status']='FAIL';receipt['failure']=repr(error)
    finally:
        receipt['ended_utc']=now();save()
    print(json.dumps(dict(status=receipt['status'],receipt=str(out/'results/run-receipt.json'),failure=receipt.get('failure'),cases=len(receipt.get('observed_case_ids',[])),dumps=len(receipt['dump_checks']))))
    return 0 if receipt['status'].startswith('PASS_') else 1


if __name__=='__main__':sys.exit(main())
