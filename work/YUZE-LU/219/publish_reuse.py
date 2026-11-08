"""Publish only this supplement atop the current PR tree; never force push."""
import argparse
import json
from pathlib import Path
import subprocess
from publish_branch import api

ROOT=Path(__file__).resolve().parents[3]
API='repos/rayggxia-workspace/LLMHardwareDesign/git'
BRANCH='task/219-general-block-search'
PARENT='052fe2479f155a818ac2cbd73daea690b85c7b96'
LOCAL_BASE='2bee7097dbd42f4d38a60af69baa73854ac5d03a'
DOCS={'docs/ARCHITECTURE.md','docs/STATUS.md','progress/YUZE-LU/STATUS.md','docs/decisions/0010-qualified-block-planner.md'}


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def main():
    p=argparse.ArgumentParser();p.add_argument('--publish',action='store_true');a=p.parse_args()
    assert api('user')['login']=='YUZE-LU'
    assert api(API+'/ref/heads/'+BRANCH)['object']['sha']==PARENT,'PR advanced: preserve concurrent work'
    remote=api(API+'/trees/'+PARENT+'?recursive=1');assert not remote.get('truncated')
    before={r['path']:r for r in remote['tree'] if r['type']=='blob'}
    changed=git('diff','--name-only',LOCAL_BASE,'HEAD').decode().splitlines()
    entries=[]
    for name in changed:
        assert name in DOCS or name.startswith(('project/experiments/block_synthesis/','work/YUZE-LU/219/')),name
        exists=subprocess.run(['git','cat-file','-e',LOCAL_BASE+':'+name],cwd=ROOT,capture_output=True).returncode==0
        base=git('rev-parse',LOCAL_BASE+':'+name).decode().strip() if exists else None
        assert before.get(name,{}).get('sha')==base,('remote file differs from local base',name)
        assert git('ls-tree','HEAD','--',name).decode().split()[0]=='100644'
        entries.append({'path':name,'mode':'100644','type':'blob','content':git('show','HEAD:'+name).decode('utf-8')})
    assert entries and not git('status','--porcelain').strip(),'commit the reviewed supplement first'
    if not a.publish:
        print(json.dumps({'parent':PARENT,'delta_files':len(entries),'unmodified_blobs':len(before)-sum(n in before for n in changed)}));return
    created=api(API+'/trees','POST',{'base_tree':api(API+'/commits/'+PARENT)['tree']['sha'],'tree':entries})
    tree=api(API+'/trees/'+created['sha']+'?recursive=1');assert not tree.get('truncated')
    after={r['path']:r for r in tree['tree'] if r['type']=='blob'}
    for name in changed:assert after[name]['sha']==git('rev-parse','HEAD:'+name).decode().strip(),name
    for name,row in before.items():
        if name not in changed:assert after[name]['sha']==row['sha'],name
    local=git('rev-parse','HEAD').decode().strip()
    commit=api(API+'/commits','POST',{'message':'Add finite on-chip Dot stripes to whole-model synthesis and independently replay real 3B\n\nSource implementation: '+local+'\nRefs #219. Preserve prior PR and main evidence.',
        'tree':created['sha'],'parents':[PARENT]})
    assert api(API+'/ref/heads/'+BRANCH)['object']['sha']==PARENT
    api(API+'/refs/heads/'+BRANCH,'PATCH',{'sha':commit['sha'],'force':False})
    assert api(API+'/ref/heads/'+BRANCH)['object']['sha']==commit['sha']
    result={'head':commit['sha'],'parent':PARENT,'tree':created['sha'],'local_implementation':local,
        'delta_files_verified':len(changed),'prior_blobs_preserved':sum(n not in changed for n in before)}
    (ROOT.parent/'issue219-reuse-publication.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
