"""Semantic rejection, independent mutation detection and atomic CLI checks."""
from pathlib import Path
import argparse,copy,hashlib,json,subprocess,sys,tempfile,zlib
from compiler import compile_task,CompileError,decode,target as target_info
from audit import audit
from fixtures import example,TARGETS
from reference import evaluate
from host import replay_plan,word

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path);args=parser.parse_args();receipts=[]
    def passed(name):receipts.append(name)
    here=Path(__file__).resolve().parent
    schema=json.loads((here/'schema.json').read_text());registry=json.loads((here/'targets.json').read_text())
    assert schema['properties']['target']['enum']==TARGETS and schema['properties']['schema']['const']=='bounded-native-tasks/1'
    passed('metadata:shape-version-and-targets')
    assert registry['targets']==[target_info(n) for n in TARGETS] and registry['execution_capacity']==16
    passed('metadata:target-registry-binding')
    for target in TARGETS:
        for variant in range(3):
            task,inputs=example(target,variant);bundle=compile_task(task)
            assert bundle==compile_task(json.loads(json.dumps(task)))
            assert audit(task,bundle)['passed'];ref=evaluate(task,inputs);plan=replay_plan(task,bundle,inputs,ref)
            assert all(0<=word(c)<1<<1320 for c in plan)
            assert len([c for c in plan if c['op']==2])==sum(v['bytes']//16 for v in bundle['images'].values())
            passed('positive:'+target+':'+str(variant))
            for role in ('mother','local0','local1'):
                data=bytes.fromhex(bundle['images_hex'][role])
                for offset in sorted(set([8,10,12,20,24,52,60,64,68,84,127,128,135,len(data)-1])):
                    bad=copy.deepcopy(bundle);mutated=bytearray(data);mutated[offset]^=1
                    bad['images_hex'][role]=mutated.hex();bad['images'][role]['sha256']=hashlib.sha256(mutated).hexdigest();bad['images'][role]['crc32']=zlib.crc32(mutated)
                    try:audit(task,bad)
                    except ValueError:passed(f'mutation:{target}:{variant}:{role}:{offset}')
                    else:raise AssertionError('mutation escaped independent audit')
    def reject(name,edit,target='recovery/U'):
        task,_=example(target);edit(task)
        try:compile_task(task)
        except CompileError:passed('reject:'+name)
        else:raise AssertionError(name+' was accepted')
    def put(path,value):
        def mutate(task):
            x=task
            for k in path[:-1]:x=x[k]
            x[path[-1]]=value
        return mutate
    bad_values=[('schema','bad-version'),('name','../../outside'),('target','recovery/P'),('epoch',0),('epoch',True),('generation',-1),('job',1<<32),('sequence',0),('image_ids',[1,1,2]),('image_ids',[1,True,2]),('tokens',[2,2]),('tokens',[2,8]),('tokens',[True,3]),('call_order',[0]),('call_order',[0,0]),('call_order',[False,1]),('buffers',[]),('tasks',[])]
    for key,v in bad_values:reject(key+'='+str(v),put([key],v))
    reject('unknown-IR-field',lambda t:t.update(native_abi=1))
    for key,v in [('name','b0_eps'),('block',2),('base_bytes',1),('base_bytes',16384),('words',1025),('words',True),('format','FP16'),('space','T_OUTPUT'),('initial',1)]:
        reject('buffer-'+key,put(['buffers',1,key],v))
    reject('physical-overlap',put(['buffers',1,'base_bytes'],21*16))
    reject('uninitialized-source',put(['buffers',0,'initial'],False))
    reject('duplicate-task',put(['tasks',1,'block'],0))
    reject('unknown-semantic-op',put(['tasks',0,'operations',0],dict(op='magic')))
    reject('invalid-meta',put(['tasks',0,'operations',0,'meta'],15))
    reject('lane-not-string',put(['tasks',0,'operations',0,'lane'],[]))
    reject('native-arity',put(['tasks',0,'operations',0,'src'],[]))
    reject('foreign-buffer',put(['tasks',0,'operations',0,'src'],['b1_zero']))
    reject('native-order',lambda t:t['tasks'][0]['operations'].reverse())
    reject('unsupported-route',put(['transfers',0,'source'],'b1_recv'))
    reject('transfer-format',put(['transfers',0,'format'],'S16'))
    reject('transfer-size',put(['transfers',0,'words'],4))
    reject('missing-reservation-edge',put(['transfers'],[]))
    reject('extra-edge',lambda t:t['transfers'].append(copy.deepcopy(t['transfers'][0])))
    reject('execution-capacity',lambda t:t['tasks'][0]['operations'].extend([copy.deepcopy(t['tasks'][0]['operations'][-1])]*11))
    reject('homogeneous-route',lambda t:t.update(transfers=[dict(source='b0_out',destination='b1_out',words=1,format='RAW128')]),'five/F')
    reject('J-epoch-wrap',put(['epoch'],256),'five/J')
    reject('J-unreleased',lambda t:t['tasks'][0]['operations'].pop(),'five/J')
    reject('J-output-overflow',put(['buffers',2,'words'],5),'five/J')
    reject('J-tag-overflow',put(['tasks',0,'operations',0,'tag'],1<<24),'five/J')
    reject('P-context-order',lambda t:t['tasks'][0]['operations'].reverse(),'five/P')
    reject('P-gate-alias',put(['tasks',0,'operations',4,'dst'],'b0_gx'),'five/P')
    reject('P-feeder-alignment',put(['buffers',0,'base_bytes'],16),'five/P')
    try:decode('{"schema":"a","schema":"b"}')
    except CompileError:passed('reject:duplicate-json-key')
    else:raise AssertionError('duplicate JSON key')
    test_root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(dir=test_root) as td:
        p=Path(td);assert p.resolve().is_relative_to(test_root)
        inp=p/'bad.json';out=p/'bundle.json';inp.write_text('{"schema":"wrong"}');out.write_bytes(b'original-output')
        result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('compiler.py')),str(inp),'--output',str(out)],capture_output=True)
        assert result.returncode==2 and out.read_bytes()==b'original-output' and inp.read_text()=='{"schema":"wrong"}'
        passed('CLI:invalid-input-does-not-replace-output')
        task,_=example('recovery/J',1);bundle=compile_task(task)
        inp.write_text(json.dumps(task));out.write_text(json.dumps(bundle));emitted=p/'emitted'
        result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('emit.py')),str(inp),str(out),'--out',str(emitted)],capture_output=True)
        assert result.returncode==0,result.stderr
        for role,raw in bundle['images_hex'].items():assert (emitted/(role+'.bin')).read_bytes()==bytes.fromhex(raw)
        assert json.loads((emitted/'loader-plan.json').read_text())
        passed('CLI:emit-independent-audit-and-artifacts')
        bundle['images']['local0']['crc32']^=1;out.write_text(json.dumps(bundle));bad_output=p/'rejected'
        result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('emit.py')),str(inp),str(out),'--out',str(bad_output)],capture_output=True)
        assert result.returncode==2 and not bad_output.exists()
        passed('CLI:emit-corruption-creates-no-artifacts')
    summary={'schema':'bounded-native-compiler-software-tests/1','passed':len(receipts),'total':len(receipts),
             'positive':sum(x.startswith('positive:') for x in receipts),'mutations':sum(x.startswith('mutation:') for x in receipts),
             'rejections':sum(x.startswith('reject:') for x in receipts),'cli':sum(x.startswith('CLI:') for x in receipts),'metadata':sum(x.startswith('metadata:') for x in receipts),'receipts':receipts,
             'scope':'software semantics/bytes/host artifacts only, no local RTL simulation'}
    if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(summary,indent=2)+'\n')
    print('PASS compiler software',json.dumps({k:summary[k] for k in ('passed','positive','mutations','rejections','cli')}))
if __name__=='__main__':main()
