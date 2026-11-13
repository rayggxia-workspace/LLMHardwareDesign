"""Non-force review publication, preserving main and the shared documents."""
import argparse
import base64
import json
import re
from pathlib import Path
import subprocess
import tempfile

from publish_branch import api

ROOT=Path(__file__).resolve().parents[3]
API='repos/rayggxia-workspace/LLMHardwareDesign/git'
BRANCH='task/219-general-block-search'
OLD='24e479cdf1614c408f4c3d3cbe2edc3ec760be1a'
BASE='6f6c467703ffa14159ace03fe0041612fa496e14'
COMMON='d7e477a978e236026177f5684c14160b386e7a95'
MAIN='c4d7b960599b9d292f27eb4429d5f226a7156c95'
DOCS=('docs/ARCHITECTURE.md','docs/STATUS.md','progress/YUZE-LU/STATUS.md','docs/decisions/README.md')
CACHE=ROOT.parent/'issue219-review-publication.json'


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def tree(commit):
    cache=ROOT.parent/('issue219-git-tree-'+commit+'.json')
    if cache.exists():return json.loads(cache.read_text())
    print('Reading Git tree '+commit,flush=True)
    t=api(API+'/trees/'+commit+'?recursive=1');assert not t.get('truncated')
    result={r['path']:r for r in t['tree'] if r['type']=='blob'}
    cache.write_text(json.dumps(result)+'\n');return result


def blob(row):return base64.b64decode(api(API+'/blobs/'+row['sha'])['content'])


def merge(ours,base,theirs,name):
    with tempfile.TemporaryDirectory(prefix='issue219-doc-') as tmp:
        paths=[Path(tmp)/n for n in ('ours','base','theirs')]
        for p,data in zip(paths,(ours,base,theirs)):p.write_bytes(data.replace(b'\r\n',b'\n'))
        r=subprocess.run(['git','merge-file','-p','--diff3',*map(str,paths)],capture_output=True)
        if r.returncode==1:
            # Reviewed shared-document conflicts are independent insertions
            # into an empty base hunk. Preserve both; never guess replacements.
            pattern=rb'^<<<<<<<[^\n]*\n(.*?)^\|\|\|\|\|\|\|[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*\n'
            def additive(m):
                left,base,right=m.groups()
                if base.strip():return m.group(0)
                return left if left==right else left.rstrip()+b'\n\n'+right.lstrip()
            resolved=re.sub(pattern,additive,r.stdout,flags=re.M|re.S)
            if b'<<<<<<<' not in resolved:return resolved
        if r.returncode:
            (ROOT.parent/(name.replace('/','-')+'.conflict')).write_bytes(r.stdout)
            raise RuntimeError('resolve document conflict: '+name)
        return r.stdout


def main():
    p=argparse.ArgumentParser();p.add_argument('--publish',action='store_true');a=p.parse_args()
    assert api(API+'/ref/heads/'+BRANCH)['object']['sha']==OLD
    assert api(API+'/ref/heads/main')['object']['sha']==MAIN
    old,common,up=tree(OLD),tree(COMMON),tree(MAIN)
    own={n for n in set(old)|set(common) if old.get(n,{}).get('sha')!=common.get(n,{}).get('sha')}
    overlap={n for n in own if up.get(n,{}).get('sha')!=common.get(n,{}).get('sha')}
    assert overlap<=set(DOCS),overlap
    if not a.publish:
        for name in DOCS:
            interim=merge(blob(old[name]),git('show',BASE+':'+name),(ROOT/name).read_bytes(),name)
            final=merge(interim,blob(common[name]),blob(up[name]),name)
            (ROOT/name).write_bytes(final)
        CACHE.write_text(json.dumps({'prepared':True,'main':MAIN,'remote_parent':OLD})+'\n')
        print(json.dumps({'prepared_docs':list(DOCS),'existing_own_paths':len(own)}));return
    assert json.loads(CACHE.read_text())['prepared']
    assert not git('status','--porcelain').strip(),'commit before publication'
    local=git('rev-parse','HEAD').decode().strip()
    changed=git('diff','--name-only',BASE,'HEAD').decode().splitlines()
    entries={n:({'path':n,'type':'blob','mode':old[n]['mode'],'sha':old[n]['sha']} if n in old else
                {'path':n,'type':'blob','mode':'100644','sha':None}) for n in own}
    for name in changed:
        assert name in DOCS or name.startswith(('project/experiments/block_synthesis/','work/YUZE-LU/219/')),name
        mode=git('ls-tree','HEAD','--',name).decode().split()[0];assert mode=='100644'
        entries[name]={'path':name,'mode':mode,'type':'blob','content':git('show','HEAD:'+name).decode('utf-8')}
    new=api(API+'/trees','POST',{'base_tree':api(API+'/commits/'+MAIN)['tree']['sha'],'tree':list(entries.values())})
    checked=tree(new['sha'])
    for name in changed:assert checked[name]['sha']==git('rev-parse','HEAD:'+name).decode().strip(),name
    for name,row in up.items():
        if name not in entries:assert checked[name]['sha']==row['sha'],name
    commit=api(API+'/commits','POST',{'message':'Fix static net legality and validate generated current MC/U64 programs\n\nSource implementation: '+local+'\nPreserve current main and shared docs. Refs #219.',
        'tree':new['sha'],'parents':[OLD,MAIN]})
    assert api(API+'/ref/heads/'+BRANCH)['object']['sha']==OLD
    assert api(API+'/ref/heads/main')['object']['sha']==MAIN
    api(API+'/refs/heads/'+BRANCH,'PATCH',{'sha':commit['sha'],'force':False})
    assert api(API+'/ref/heads/'+BRANCH)['object']['sha']==commit['sha']
    result={'head':commit['sha'],'tree':new['sha'],'local_implementation':local,'main':MAIN,
            'delta_files_verified':len(changed),'main_blobs_preserved':sum(n not in entries for n in up),
            'local_worktree_preserved':True}
    CACHE.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
