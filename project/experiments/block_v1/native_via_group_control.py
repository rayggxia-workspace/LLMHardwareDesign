"""Portable subprocess controls for group scheduling; no Slurm or EDA claim."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import native_via_route_group as group


def verify(destination):
    assert not destination.exists()
    stub='''import hashlib,json,sys,time
from pathlib import Path
mode=sys.argv[2];started=time.time();time.sleep(.7)
name='native-physical-receiver.json'if '-receive-'in mode else'native-final-function.json'
passed=mode!=FAIL_MODE
path=Path(name);path.write_text(json.dumps(dict(passed=passed)))
r=dict(mode=mode,cpus=int(sys.argv[3]),passed=passed,started=started,finished=time.time(),outputs={name:hashlib.sha256(path.read_bytes()).hexdigest()})
Path('receipt.json').write_text(json.dumps(r))
sys.exit(0 if passed else 1)
'''
    original=group.memory_snapshot;results={}
    try:
        with tempfile.TemporaryDirectory()as temporary:
            base=Path(temporary)
            for name,failure,available,parallel in [('positive',None,500,4),('failed-peer','native-viaonly-receive-transaction6k-c',500,4),('memory-guard',None,100,2)]:
                root=base/name/'src';worker=root/'project/experiments/block_v1/worker.py';worker.parent.mkdir(parents=True)
                worker.write_text('FAIL_MODE='+repr(failure)+'\n'+stub)
                out=base/name/'tasks/native-via-qualification-group';out.mkdir(parents=True)
                group.memory_snapshot=lambda:dict(MemTotal=512*1024**3,MemAvailable=available*1024**3)
                rejected=False
                try:group.verify(root,out,64,qualify=True)
                except AssertionError:rejected=True
                record=json.loads((out/'native-via-qualification-group.json').read_text());children=record['children']
                assert len(children)==4 and record['passed']==(failure is None)and rejected==(failure is not None)
                assert record['maximum_concurrent_cpu_ceilings']==parallel*16
                receipts=[json.loads((Path(row['folder'])/'receipt.json').read_text())for row in children]
                overlap=max(sum(r['started']<=instant<r['finished']for r in receipts)for instant in [r['started']for r in receipts])
                assert overlap==parallel and all(row['receipt_sha256']and row['proof_sha256']for row in children)
                assert sum(row['passed']for row in children)==(4 if failure is None else 3)
                results[name]=dict(passed=True,parent_rejected=rejected,retained_child_receipts=len(children),
                                   actual_stub_process_overlap=overlap,maximum_concurrent_cpu_ceilings=parallel*16)
    finally:group.memory_snapshot=original
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(dict(passed=True,controls=results,
        source_sha256=hashlib.sha256(Path(group.__file__).read_bytes()).hexdigest(),
        stub_sha256=hashlib.sha256(stub.encode()).hexdigest(),
        scope='Actual declared-stub subprocess scheduling and injected memory snapshots; no real allocation, CPU utilization, peak memory or EDA gate proof'),indent=2)+'\n')
    print(json.dumps(dict(passed=True,controls=len(results))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('out',type=Path);args=parser.parse_args();verify(args.out)
