"""Transport existing local Git commits via REST; refuse any hash drift."""
import json,subprocess
repo='repos/rayggxia-workspace/LLMHardwareDesign'
branch='task/289-ab-x8'
def git(*args):return subprocess.check_output(['git',*args]).decode('utf-8').rstrip('\n')
def api(endpoint,data=None,method=None):
    args=['gh','api',repo+'/'+endpoint]
    if data is not None:args+=['--method',method or 'POST','--input','-']
    raw=subprocess.check_output(args,input=None if data is None else json.dumps(data,ensure_ascii=False).encode('utf-8'),timeout=60)
    return json.loads(raw)
remote=api('git/ref/heads/'+branch)['object']['sha']
head=git('rev-parse','HEAD')
subprocess.run(['git','merge-base','--is-ancestor',remote,head],check=True)
for commit in git('rev-list','--reverse',remote+'..'+head).splitlines():
    fields=git('show','-s','--format=%H%x00%P%x00%T%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%B',commit).split('\0',9)
    sha,parents,tree,an,ae,ad,cn,ce,cd,msg=fields
    assert len(parents.split())==1
    parent=parents.split()[0]
    entries=[]
    for path in git('diff-tree','--no-commit-id','--name-only','-r',parent,commit).splitlines():
        item=git('ls-tree',commit,'--',path)
        if not item:entries.append({'path':path,'mode':'100644','type':'blob','sha':None});continue
        mode,kind,blob=item.split('\t',1)[0].split()
        assert kind=='blob'
        content=subprocess.check_output(['git','cat-file','blob',blob]).decode('utf-8')
        entries.append({'path':path,'mode':mode,'type':'blob','content':content})
    created=api('git/trees',{'base_tree':git('rev-parse',parent+'^{tree}'),'tree':entries})
    assert created['sha']==tree,('tree hash mismatch',commit)
    message=subprocess.check_output(['git','cat-file','commit',commit]).split(b'\n\n',1)[1].decode('utf-8')
    created=api('git/commits',{'tree':tree,'parents':[parent],'message':message,'author':{'name':an,'email':ae,'date':ad},'committer':{'name':cn,'email':ce,'date':cd}})
    assert created['sha']==sha,('commit hash mismatch',commit,created['sha'])
    print('Verified commit',sha,flush=True)
updated=api('git/refs/heads/'+branch,{'sha':head,'force':False},'PATCH')
assert updated['object']['sha']==head
assert api('git/ref/heads/'+branch)['object']['sha']==head
print('Published and read back',head)
