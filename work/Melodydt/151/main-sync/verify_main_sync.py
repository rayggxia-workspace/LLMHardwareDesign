# -*- coding: utf-8 -*-
"""Read-only source/evidence integration checks; never simulates or submits jobs."""
from pathlib import Path
import argparse
import ast
import datetime
import hashlib
import json
import re
import subprocess
import sys


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--baseline-package',type=Path)
    ap.add_argument('--main-context',type=Path)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args();root=args.root.resolve();prefix='work/Melodydt/151/main-sync/'
    def load(path):return json.loads((root/path).read_text(encoding='utf8'))
    sources=load(prefix+'source-comparison.json');plan=load(prefix+'merge-plan.json');roadmap=load(prefix+'roadmap.json')
    for row in sources['core_rows']:
        raw=(root/row['path']).read_bytes()
        assert len(raw)==row['bytes'] and sha(raw)==row['sha256'] and blob(raw)==row['research_blob_sha1'],row['path']
        if row['main_blob_sha1']:assert blob(raw)==row['main_blob_sha1']
    assert len(sources['core_rows'])==14 and sum(bool(x['main_blob_sha1']) for x in sources['core_rows'])==12
    assert sum(x['main_status']=='qualified_leaf_source' for x in sources['core_rows'])==11
    assert len(sources['runtime_files_unchanged'])==46 and sources['R_qualified'] is False
    for row in sources['runtime_files_unchanged']:
        raw=(root/row['path']).read_bytes();assert sha(raw)==row['sha256'] and blob(raw)==row['git_blob_sha1']
    assert len(plan['automatic_actions'])==4 and len(plan['resolved_shared_files'])==8
    assert plan['parents']==[sources['research_input'],sources['main_input']]
    assert [x['id'] for x in roadmap['lines']]==['L'+str(i) for i in range(1,9)]
    assert roadmap['current_primary']=='L4' and roadmap['next_execution']['id']=='L4-A-TSP'
    assert roadmap['next_execution']['status']=='planned_not_implemented'
    assert roadmap['basis']['accepted_leaf_macros']==['M','N','E','G','S','T']
    historical=[]
    if args.baseline_package:
        before=args.baseline_package.resolve()
        for name in ['seven-stage-roadmap.json','island-sync-plan.json','phase2-source-lock.json','w0-source-lock.json','w5-if-source-lock.json','af16-model-admission.json']:
            path='work/Melodydt/151/'+name;raw=(root/path).read_bytes();assert raw==(before/path).read_bytes(),path
            historical.append(dict(path=path,sha256=sha(raw)))
        for folder in ['project/rtl','project/tb']:
            for p in (before/folder).rglob('*'):
                if p.is_file():assert (root/p.relative_to(before)).read_bytes()==p.read_bytes(),str(p)
    context=None
    if args.main_context:
        raw=args.main_context.read_bytes();ctx=json.loads(raw.decode('utf8'));context=dict(path=str(args.main_context.resolve()),sha256=sha(raw))
        for path in ['docs/BLOCK_V2.md','docs/BLOCK_V2_RESULTS.md']:
            raw=(root/path).read_bytes();assert blob(raw)==ctx['mainFiles'][path]['sha'],path
        for row in ctx['releaseTree']['tree']:
            if row['type']=='blob':
                path='work/YUZE-LU/143/release-six/'+row['path'];assert blob((root/path).read_bytes())==row['sha'],path
    commands=[]
    specs=[('management',['scripts/check_project.py'],0),('release',['project/experiments/block_v2/check_release.py'],0),('W5_IF',['scripts/check_w5_if.py'],0),('admission',['scripts/check_af_model_admission.py','--root','.'],0),('qwen_AF16_rejection',['scripts/check_af_model_admission.py','--root','.','--model','qwen3','--target','AF16'],2),('range_tool_self_check',['work/Melodydt/151/qnum/fetch_qwen3_layer0.py','--self-check'],0)]
    for label,argv,expected in specs:
        cmd=[sys.executable,'-B','-X','utf8']+argv;r=subprocess.run(cmd,cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert r.returncode==expected,(label,r.returncode,r.stderr.decode('utf8',errors='replace'))
        row=dict(label=label,argv=cmd,exit_code=r.returncode,stdout_bytes=len(r.stdout),stdout_sha256=sha(r.stdout),stderr_bytes=len(r.stderr),stderr_sha256=sha(r.stderr))
        if label in ['release','W5_IF','admission','qwen_AF16_rejection']:
            d=json.loads(r.stdout.decode('utf8'))
            if label=='release':
                assert d['passed'] and d['accepted']==['M','N','E','G','S','T'] and d['R']=='unfinished' and d['repository_files_checked']==420 and d['local_members_checked']==0
                row['summary']=d
            elif label=='W5_IF':
                assert d['checks_passed']==465 and d['unchanged_source_locks_verified']==22
                row['summary']={k:d[k] for k in ['status','kind','checks_passed','models','profiles','unchanged_source_locks_verified']}
            elif label=='admission':
                assert d['models']==8 and len(d['real_model_results'])==24 and all(x['decision']=='GAP' for x in d['real_model_results'])
                row['summary']=dict(status=d['status'],models=d['models'],real_targets=24,decisions='24 GAP',source_files_verified=d['source_files_verified'],conformance_examples=len(d['conformance_examples']))
            else:
                assert d['decision']=='GAP' and d['actual_H']==1024
                row['summary']=dict(decision='GAP',actual_H=d['actual_H'],expected_exit=2)
        else:row['stdout']=r.stdout.decode('utf8')
        commands.append(row)
    files=[];links=[]
    explicit=['README.md','docs/ARCHITECTURE.md','docs/STATUS.md','docs/COARSE_BLOCK_RESEARCH_PROGRESS.md','docs/MAIN_SYNC_AND_RESEARCH_ROADMAP.md','docs/decisions/2026-11-02-main-six-leaf-research-baseline.md','docs/handoffs/2026-11-02-issue-151-main-sync.md','progress/Melodydt/STATUS.md','work/Melodydt/151/README.md']
    explicit += [p.relative_to(root).as_posix() for p in (root/prefix).glob('*') if p.is_file() and p.name!='verification.json']
    for path in sorted(set(explicit)):
        p=root/path;raw=p.read_bytes();text=raw.decode('utf8')
        assert not raw.startswith(b'\xef\xbb\xbf') and b'\r' not in raw,path
        assert all(line==line.rstrip() for line in text.splitlines()),path
        assert not re.search(r'^(<<<<<<<|=======|>>>>>>>)',text,re.M),path
        if p.suffix=='.json':json.loads(text)
        if p.suffix=='.py':ast.parse(text,filename=path)
        if p.suffix=='.md':
            old=set()
            if args.baseline_package and (args.baseline_package/path).is_file():old=set(re.findall(r'\]\(([^)]+)\)',(args.baseline_package/path).read_text(encoding='utf8')))
            for target in re.findall(r'\]\(([^)]+)\)',text):
                if target in old or '://' in target or target.startswith('#'):continue
                local=target.split('#',1)[0]
                if local:assert (p.parent/local).resolve().is_file(),path+':'+target
                links.append(dict(file=path,target=target))
        files.append(dict(path=path,bytes=len(raw),sha256=sha(raw),git_blob_sha1=blob(raw)))
    result=dict(status='PASS_MAIN_SYNC_SOURCE_EVIDENCE_AND_STATIC_GATES_NOT_SIMULATION',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),runtime=dict(python=sys.version,platform=sys.platform),research_input=sources['research_input'],main_input=sources['main_input'],main_context=context,commands=commands,common_native=12,qualified_leaf_sources=11,R_qualified=False,legacy_retained=2,unchanged_runtime=46,historical_indices_preserved=historical,new_files_checked=files,new_links_checked=links,not_run=['new RTL simulation: no runtime logic changed','server jobs: none submitted this round','check_release --local-artifacts: indexed large data absent in this package','EDA/physical implementation/system qualification','new numerical quality/inference'],registry='pending',board=dict(observed='unverified',synchronization='pending',reason='no config/board.json and no Projects item/field tool; not proven permission denial'))
    if args.output:args.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps(dict(status=result['status'],commands=len(commands),common_native=12,unchanged_runtime=46,new_files=len(files),links=len(links),real_model_targets='24 GAP',new_simulation_runs=0)))


if __name__=='__main__':main()
