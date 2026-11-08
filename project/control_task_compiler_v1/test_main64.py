"""Main64 admission, independent forgery rejection and complete-byte mutations."""
from pathlib import Path
import argparse,copy,hashlib,json,re,subprocess,sys,tempfile,zlib
from compiler import compile_task,decode
from audit import audit
from main64_compiler import CompileError
from main64_fixtures import PAIRS,example
from main64_reference import evaluate
from main64_host import replay_plan,word
HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();receipts=[]
    from main64_compiler import target
    schema=json.loads((HERE/'main64-schema.json').read_text())
    registry=json.loads((HERE/'main64-targets.json').read_text())
    names=['main64/'+a+'/'+b for a,b in PAIRS]
    assert schema['properties']['schema']['const']=='main64-native-tasks/1' and schema['properties']['target']['enum']==names
    assert schema['properties']['tasks']['items']['properties']['operations']['items']['oneOf'][0]['properties']['src']['maxItems']==3
    receipts.append('metadata:new-shape-and-source-arity')
    assert registry['targets']==[target(n) for n in names] and registry['execution_capacity']==16
    receipts.append('metadata:target-capability-and-route-binding')
    for pair in PAIRS:
        for variant in range(3):
            task,inputs=example(pair,variant);bundle=compile_task(task)
            assert bundle==compile_task(decode(json.dumps(task)))
            assert audit(task,bundle)['passed'];ref=evaluate(task,inputs);plan=replay_plan(task,bundle,inputs,ref)
            deploy=next(i for i,c in enumerate(plan) if c['op']==7)
            assert all(i<deploy for i,c in enumerate(plan) if c['op'] in (12,14))
            assert all(0<=word(c)<1<<1320 for c in plan)
            assert all(int.from_bytes(bytes.fromhex(v)[64:68],'little')==bundle['target']['topology'] for v in bundle['images_hex'].values())
            receipts.append('positive:'+task['name'])
            for role in ('mother','local0','local1'):
                data=bytes.fromhex(bundle['images_hex'][role])
                offsets=sorted(set([8,10,12,20,24,52,60,64,68,84,127,128,135,len(data)-1]+([len(data)-48,len(data)-44] if role!='mother' else [])))
                for off in offsets:
                    bad=copy.deepcopy(bundle);b=bytearray(data);b[off]^=1
                    bad['images_hex'][role]=b.hex();bad['images'][role]['sha256']=hashlib.sha256(b).hexdigest();bad['images'][role]['crc32']=zlib.crc32(b)
                    try:audit(task,bad)
                    except ValueError:receipts.append(f'mutation:{task["name"]}:{role}:{off}')
                    else:raise AssertionError('independent byte audit accepted forged image')
    def reject(label,change,pair=('U','P'),variant=0):
        t,_=example(pair,variant);change(t)
        try:compile_task(t)
        except ValueError:pass
        else:raise AssertionError('compiler accepted '+label)
        # For the independent IR gate, no compiler or manifest generation is used.
        from main64_audit import admit
        try:admit(t)
        except (ValueError,TypeError,KeyError):pass
        else:raise AssertionError('independent admission accepted '+label)
        receipts.append('reject:'+label)
    for f,v in [('schema','wrong'),('target','main64/U/F'),('name','../bad'),('epoch',True),('generation',0),('tokens',[2,2]),('image_ids',[1,1,2]),('call_order',[1,0])]:
        reject(f,lambda t,f=f,v=v:t.__setitem__(f,v))
    reject('U N three sources',lambda t:t['tasks'][0]['operations'][0].__setitem__('src',['b0_eps','b0_gamma','b0_raw']))
    reject('U E four sources',lambda t:t['tasks'][0]['operations'][-1].__setitem__('src',['b0_a']*4))
    reject('native lane',lambda t:t['tasks'][0]['operations'][0].__setitem__('lane','R'))
    reject('U high direct bit',lambda t:t['tasks'][0]['operations'][0].__setitem__('meta',(1<<63)|256))
    reject('unknown operation',lambda t:t['tasks'][0]['operations'].append(dict(op='arbitrary')))
    reject('overlap',lambda t:t['buffers'][1].__setitem__('base_bytes',t['buffers'][0]['base_bytes']))
    reject('partial source',lambda t:t['buffers'][0].__setitem__('initial',False))
    reject('misalignment',lambda t:t['buffers'][0].__setitem__('base_bytes',1))
    reject('RAW format',lambda t:t['transfers'][0].__setitem__('format','S16'))
    reject('unsupported route',lambda t:t['transfers'][0].__setitem__('words',4))
    reject('J wrap',lambda t:t.__setitem__('epoch',256),('J','J'))
    reject('J missing release',lambda t:t['tasks'][0]['operations'].pop(),('J','J'))
    reject('J overflowing lease',lambda t:t['buffers'][2].__setitem__('words',5),('J','J'))
    reject('CF missing producer',lambda t:t['tasks'][0]['operations'].pop(-2),('F','F'),1)
    reject('CF dangling direct',lambda t:t['tasks'][0]['operations'].pop(),('F','F'),1)
    reject('P missing route',lambda t:t['tasks'][0]['operations'].pop(-2),('P','P'),1)
    reject('paired N context',lambda t:t['tasks'][0]['operations'].pop(2),('U','U'),2)
    reject('paired alias',lambda t:t['tasks'][0]['operations'][-1].__setitem__('dst','b0_raw'),('U','U'),2)
    reject('N replay consumed twice',lambda t:t['tasks'][0]['operations'].append(copy.deepcopy(t['tasks'][0]['operations'][3])))
    reject('P context',lambda t:t['tasks'][0]['operations'].reverse(),('P','P'))
    with tempfile.TemporaryDirectory(dir=HERE) as tmp:
        d=Path(tmp);t,_=example(('U','P'),1);src=d/'task.json';out=d/'bundle.json'
        src.write_text(json.dumps(t));r=subprocess.run([sys.executable,'-B',str(HERE/'compiler.py'),str(src),'--output',str(out)],capture_output=True)
        assert r.returncode==0,r.stderr
        emitted=d/'emitted';r=subprocess.run([sys.executable,'-B',str(HERE/'emit.py'),str(src),str(out),'--out',str(emitted)],capture_output=True)
        assert r.returncode==0,r.stderr
        plan=json.loads((emitted/'loader-plan.json').read_text());assert not any(c['op']==7 for c in plan)
        receipts.append('CLI:main64-emits-prepared-not-deployed')
        original=out.read_bytes();src.write_text('{"schema":"main64-native-tasks/1"}')
        r=subprocess.run([sys.executable,'-B',str(HERE/'compiler.py'),str(src),'--output',str(out)],capture_output=True)
        assert r.returncode!=0 and out.read_bytes()==original
        receipts.append('CLI:bad-input-preserves-output')
    result={'schema':'main64-compiler-software/1','passed':len(receipts),'total':len(receipts),'receipts':receipts}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS main64 software',len(receipts))
if __name__=='__main__':main()

