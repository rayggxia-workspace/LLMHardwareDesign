import hashlib
import json
import pathlib
import shutil
import sys
import tarfile
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--archive',required=True,type=pathlib.Path)
parser.add_argument('--extract',required=True,type=pathlib.Path)
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[3]
archive=args.archive.resolve()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='977ed2f099e4947b0cbbcf7b2b258027f7caf5d8ffbc5030a439d07f99e1fc08'
dst=args.extract.resolve()
dst.mkdir(parents=True,exist_ok=True)
with tarfile.open(str(archive),'r:gz') as tar:
    for m in tar.getmembers():
        p=(dst/m.name).resolve()
        assert dst in p.parents and (m.isfile() or m.isdir()),m.name
    tar.extractall(str(dst))
delivery=root
sys.path.insert(0,str(delivery/'project'/'control_rtl_min_v0_1'))
import run
report=json.loads((dst/'r005/results/report.json').read_text(encoding='utf-8'))
source=json.loads((dst/'r005/source.json').read_text(encoding='utf-8'))
assert len(report['results'])==10
for rel,digest in source['files'].items():
    assert hashlib.sha256((delivery/rel).read_bytes()).hexdigest()==digest,rel
assert report['dut_sha256']==source['files']['project/control_rtl_min_v0_1/lc_min_controller.sv']
assert hashlib.sha256((dst/'r005/results/compile.log').read_bytes()).hexdigest()==report['compile_log_sha256']
assert '%Warning' not in (dst/'r005/results/compile.log').read_text(encoding='utf-8')
checked=0
for result in report['results']:
    name=result['name']
    log=(dst/'r005/results'/(name+'.log')).read_bytes()
    assert hashlib.sha256(log).hexdigest()==result['log_sha256']
    if result['checker']['boundary_valid'] is True:
        trace=run.decode_trace(log.decode('utf-8'))
        run.check_cycles.check_trace(trace)
        assert run.observations(trace)==result['observations']
        for event in result['observations']['returns']:
            observed=event['packet']
            expected=run.codec.unpack_record('event_message',run.codec.pack_record('event_message',dict(
                kind=3 if result['status'] else 2,source_block=0,job_id=7,epoch=1,
                task_sequence=observed['task_sequence'],completion_token=0,event_id=255,status=result['status'],
                error_pc=0 if result['status'] else 0xffffffff)))
            assert observed==expected,(name,observed,expected)
        checked+=1
assert checked==5
assert (dst/'r005/results/report.json').read_bytes()==(delivery/'project/control_rtl_min_v0_1/run_report.json').read_bytes()
print(json.dumps(dict(source_commit=source['source_commit'],source_files_verified=len(source['files']),
    rtl_cases=10,independent_cycles=checked,total_cycles=sum(r['cycles'] for r in report['results']),
    execution_cycles=sum(r['cycles'] for r in report['results'] if r['checker']['boundary_valid'] is True),
    retired=sum(len(r['observations']['retired']) for r in report['results']),
    returns=sum(len(r['observations']['returns']) for r in report['results']),
    services=sum(len(r['observations']['services']) for r in report['results']))))
