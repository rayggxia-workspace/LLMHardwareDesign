"""Read-only verifier for curated Issue247 fusion receipts.

Index paths are repository-relative, including collection_path (a JSON file).
No tools/jobs are launched and no files are created or rewritten.
"""
import sys
sys.dont_write_bytecode=True
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re

ENCODED_SUFFIX='.gz.b64'
MAX_LOG_BYTES=16*1024*1024


def require(condition,message):
    if not condition:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(base,name):
    require(isinstance(name,str) and '\\' not in name,'expected forward-slash relative path')
    p=PurePosixPath(name)
    require(name and not p.is_absolute() and ':' not in name and '..' not in p.parts,'unsafe relative path '+name)
    result=(base/Path(*p.parts)).resolve()
    require(result.is_relative_to(base.resolve()),'path escapes root '+name)
    return result


def read_json(path):return json.loads(path.read_text(encoding='utf-8'))


def sha_manifest(path):
    result={}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        match=re.fullmatch(r'([0-9a-f]{64})\s+[ *]?(.+)',line)
        require(match is not None,'invalid SHA manifest line in '+str(path))
        digest,name=match.groups();relative(path.parent,name)
        require(name not in result,'duplicate SHA manifest entry '+name)
        result[name]=digest
    require(bool(result),'empty SHA manifest '+str(path))
    return result


def indexed(repo,path,files):
    name=path.resolve().relative_to(repo.resolve()).as_posix()
    require(name in files,'required receipt absent from index.files '+name)
    require(path.is_file() and sha(path)==files[name],'file SHA mismatch '+name)
    return name


def original_bytes(repo,path,files):
    """Read indexed original or its indexed, lossless gzip/base64 substitute."""
    if path.is_file():
        indexed(repo,path,files)
        return path.read_bytes()
    encoded=path.with_name(path.name+ENCODED_SUFFIX)
    indexed(repo,encoded,files)
    # ASCII transport whitespace is permitted; all other bytes must be valid
    # base64. Bound decompression while reading, rather than after allocation.
    transport=encoded.read_bytes();transport.decode('ascii')
    packed=base64.b64decode(re.sub(rb'[ \t\r\n]',b'',transport),validate=True)
    with gzip.GzipFile(fileobj=io.BytesIO(packed),mode='rb') as stream:
        data=stream.read(MAX_LOG_BYTES+1)
    require(len(data)<=MAX_LOG_BYTES,'decoded original exceeds 16 MiB '+str(path))
    return data


def production_inputs(production_repo,mapping):
    checked=0
    require(isinstance(mapping,dict),'missing code/input SHA map')
    for name,digest in mapping.items():
        if not (name.startswith('project/rtl/') or name.startswith('project/experiments/pu_leaf_base/')):continue
        path=relative(production_repo,name)
        require(path.is_file() and sha(path)==digest,'current production input differs '+name)
        checked+=1
    require(checked>0,'no production input fingerprints supplied')
    return checked


def native_result(repo,path,data,files):
    """Reparse original logs; do not trust a copied checks.passed field alone."""
    is_overlap='isolated FIFO/scheduler' in data.get('scope','')
    is_pair='fair RMS->ADD S/direct' in data.get('scope','')
    if not (is_overlap or is_pair):return dict(kind='non_native_result',passed=data.get('passed') is True)
    # Reuse the published parsers, with their full count/marker checks.
    sys.path.insert(0,str(repo/'project/experiments/u_fusion_study'))
    if is_overlap:
        import run_overlap as parser_module
        binary='Vtb_overlap_native';expected={(d,m,s) for d in (1,2,4) for m,s in ((1,143),(2,143),(2,144))}
    else:
        import run_native as parser_module
        binary='Vtb_fusion_native';expected={(m,s) for m,s in ((1,143),(2,143),(2,144))}
    parser_path=Path(parser_module.__file__)
    require(sha(parser_path)==data.get('study_sha256',{}).get(parser_path.name),'published native parser differs from original study SHA')
    check_log=parser_module.check_log
    runs=data.get('runs',[]);seen=set();commands=data.get('commands',[]);measurements=0
    runtime=[c for c in commands if c.get('command') and Path(c['command'][0]).name==binary]
    require(len(runtime)==len(expected),'missing/duplicate native runtime commands')
    for record in runs:
        key=(record['depth'],record['reset_mode'],record['seed']) if is_overlap else (record['reset_mode'],record['seed'])
        require(key in expected and key not in seen,'missing/duplicate native random/depth case');seen.add(key)
        mode=record['reset_mode'];seed=record['seed']
        suffix=f'overlap-depth{record["depth"]}-{mode}-{seed}.log' if is_overlap else f'native-{mode}-{seed}.log'
        cmd=[c for c in runtime if c.get('log')==suffix]
        require(len(cmd)==1 and cmd[0].get('exit_code')==0,'native execution receipt mismatch '+suffix)
        require(f'+verilator+rand+reset+{mode}' in cmd[0]['command'] and f'+verilator+seed+{seed}' in cmd[0]['command'],
                'native random CLI receipt mismatch '+suffix)
        log=relative(path.parent,suffix);raw=original_bytes(repo,log,files)
        digest=hashlib.sha256(raw).hexdigest()
        require(digest==cmd[0].get('log_sha256'),'native log command SHA mismatch '+suffix)
        require(digest==data.get('output_sha256',{}).get(suffix),'native original log output SHA mismatch '+suffix)
        text=raw.decode('utf-8')
        parsed=check_log(text,record['depth']) if is_overlap else check_log(text)
        require(record.get('checks',{}).get('passed') is True and parsed['cases']==record['checks'].get('cases'),
                'native parsed counts differ from result JSON '+suffix)
        measurements+=len(parsed['cases'])
    require(seen==expected,'incomplete native runtime matrix')
    require(all(c.get('exit_code')==0 for c in commands),'native tool/build command failed')
    return dict(kind='native_S16_FIFO_overlap' if is_overlap else 'native_S16_stored_direct',passed=True,
                executions=len(runs),measurements=measurements)


def verify_run(repo,production_repo,entry,files):
    run=entry['run'];commit=entry['source_commit']
    require(re.fullmatch(r'[0-9a-f]{40}',commit) is not None,'not a real source commit '+str(run))
    collection_path=relative(repo,entry['collection_path']);indexed(repo,collection_path,files)
    collection=read_json(collection_path);base=collection_path.parent
    require(collection.get('schema_version')==1 and collection.get('run')==run,'collection identity '+run)
    require(collection.get('source_commit')==commit and collection.get('collection_succeeded') is True,'collection/source receipt '+run)
    inputs=base/'inputs.json';indexed(repo,inputs,files)
    require(sha(inputs)==collection.get('input_manifest_sha256'),'inputs SHA differs from collection '+run)
    inputs_data=read_json(inputs);require(inputs_data.get('source_commit')==commit,'inputs source commit '+run)
    production_count=production_inputs(production_repo,inputs_data.get('code_sha256'))
    source_manifest=base/'source-files.sha256';indexed(repo,source_manifest,files)
    source_hashes=sha_manifest(source_manifest)
    for name,digest in inputs_data['code_sha256'].items():
        require(source_hashes.get(name)==digest,'input/source SHA manifests disagree '+name)
    job=collection['job'];state=job.get('state');exit_code=job.get('exit_code')
    terminal={'COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'}
    require(state in terminal,'job not terminal '+run)
    sacct=base/'sacct.txt';indexed(repo,sacct,files)
    records=[line.split('|') for line in sacct.read_text(encoding='utf-8').splitlines() if line.strip()]
    matching=[r for r in records if len(r)>=6 and r[0]==str(job['job_id'])]
    require(len(matching)==1,'missing/duplicate primary sacct job '+run)
    require(matching[0][1:6]==[job['job_name'],state,exit_code,job['elapsed'],job['nodes']],'sacct/collection mismatch '+run)
    whole=collection.get('whole_run_passed');main=collection.get('main_result')
    complete=state=='COMPLETED' and exit_code=='0:0' and isinstance(main,dict) and main.get('passed') is True
    require(whole is complete,'whole-run flag contradicts job/main receipt '+run)
    expected_class='complete_pass' if complete else 'partial_or_failed_run'
    require(collection.get('classification')==expected_class,'collection classification mismatch '+run)
    output_path=base/collection.get('all_results_sha256_manifest','output-files.sha256');indexed(repo,output_path,files)
    output_hashes=sha_manifest(output_path);selected=0
    for name,digest in files.items():
        path=relative(repo,name)
        if path.is_relative_to(base/'results'):
            original=path.with_name(path.name[:-len(ENCODED_SUFFIX)]) if path.name.endswith(ENCODED_SUFFIX) else path
            local=original.relative_to(base).as_posix()
            original_digest=hashlib.sha256(original_bytes(repo,original,files)).hexdigest()
            require(output_hashes.get(local)==original_digest,'selected original output differs from server SHA '+local)
            selected+=1
    require(selected>0,'no original result artifacts selected '+run)
    receipts=list(collection.get('component_receipts',[]))
    if main and not any(r.get('path')==main.get('path') for r in receipts):receipts.append(main)
    require(receipts,'no component/main result receipt '+run)
    results=[];paths=set()
    for receipt in receipts:
        path=relative(base,receipt['path']);paths.add(path)
        raw_result=original_bytes(repo,path,files)
        require(hashlib.sha256(raw_result).hexdigest()==receipt.get('sha256'),'component result SHA '+run)
        data=json.loads(raw_result)
        require(data.get('source_commit')==commit and receipt.get('source_commit')==commit,'component source commit '+run)
        require(data.get('passed') is True and receipt.get('passed') is True,'selected component did not pass '+run)
        # Preserve the runner's original output and command hashes even when
        # the publication stores only a lossless encoded transport file.
        for name,digest in data.get('output_sha256',{}).items():
            original=relative(path.parent,name)
            candidates=(original,original.with_name(original.name+ENCODED_SUFFIX))
            if any(p.relative_to(repo).as_posix() in files for p in candidates):
                require(hashlib.sha256(original_bytes(repo,original,files)).hexdigest()==digest,'component original output SHA '+name)
        for command in data.get('commands',[]):
            if 'log' not in command or 'log_sha256' not in command:continue
            original=relative(path.parent,command['log'])
            candidates=(original,original.with_name(original.name+ENCODED_SUFFIX))
            if any(p.relative_to(repo).as_posix() in files for p in candidates):
                require(hashlib.sha256(original_bytes(repo,original,files)).hexdigest()==command.get('log_sha256'),
                        'component original command log SHA '+command['log'])
        if 'source_sha256' in data:production_inputs(production_repo,data['source_sha256'])
        if 'source_lock' in data:
            study=production_repo/'project/experiments/u_fusion_study'
            for group in ('source_sha256','dependency_sha256'):
                for name,digest in data['source_lock'][group].items():
                    target=(study/name).resolve()
                    require(target.is_relative_to(production_repo.resolve()),'model source escapes repository')
                    require(target.is_file() and sha(target)==digest,'current model differs from measured source '+name)
        check=native_result(repo,path,data,files)
        results.append(dict(path=path.relative_to(repo).as_posix(),**check))
    if 'result_path' in entry:
        require(relative(repo,entry['result_path']) in paths,'index.result_path is not a registered result '+run)
    if complete:
        require(relative(base,main['path']) in paths,'complete run missing original main result '+run)
    return dict(run=run,source_commit=commit,job_id=job['job_id'],job_state=state,
                classification=expected_class,whole_run_passed=complete,production_inputs_verified=production_count,
                selected_original_outputs_verified=selected,components=results)


def verify(repo,index_path):
    index=read_json(index_path)
    require(index.get('schema_version')==1,'unsupported fusion index schema')
    files=index.get('files');require(isinstance(files,dict) and files,'empty index.files')
    for name,digest in files.items():
        require(isinstance(digest,str) and re.fullmatch(r'[0-9a-f]{64}',digest),'invalid file SHA '+name)
        indexed(repo,relative(repo,name),files)
    runs=index.get('runs',[])
    require(runs and len({r['run'] for r in runs})==len(runs),'missing/duplicate run entries')
    return dict(passed=True,scope='curated receipt integrity/classification and original native S16 revalidation; no rerun/physical qualification',
                files_verified=len(files),runs=[verify_run(repo,repo,r,files) for r in runs])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--index',type=Path,default=Path('work/Melodydt/247/fusion/index.json'))
    args=parser.parse_args();repo=args.repo.resolve()
    path=args.index.resolve() if args.index.is_absolute() else relative(repo,args.index.as_posix())
    try:result=verify(repo,path)
    except (ValueError,KeyError,TypeError,OSError,ImportError,EOFError) as error:
        print(json.dumps(dict(passed=False,error=type(error).__name__+': '+str(error)),ensure_ascii=False,indent=2))
        raise SystemExit(1)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
