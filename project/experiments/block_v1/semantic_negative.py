"""Exercise receiver semantics after immutable artifact authentication.

Each fault exists only in Path.read_text's return value for one selected run
artifact. Real files, hashes, binary and execution records stay unchanged. This
deliberately tests the mathematical/protocol checks beyond the hash guard;
injected observations are never labeled as actual simulation output.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    source,inp,run,out=map(Path,sys.argv[1:])
    out.mkdir(exist_ok=False)
    spec=importlib.util.spec_from_file_location('negative_receiver',source/'project/experiments/block_v1/receive121.py')
    sys.path.insert(0,str(source/'project/experiments/block_v1'))
    receiver=importlib.util.module_from_spec(spec);spec.loader.exec_module(receiver)
    original_read=Path.read_text
    rows=[json.loads(line)for line in original_read(run/'actual.jsonl').splitlines()]
    protocol=json.loads(original_read(run/'actual.jsonl.protocol.json'))
    records=[]
    def scenario(name,row_change=None,protocol_change=None,expect=None):
        r=copy.deepcopy(rows);p=copy.deepcopy(protocol)
        if row_change:row_change(r)
        if protocol_change:protocol_change(p)
        def read_text(path,*args,**kwargs):
            if path.resolve()==(run/'actual.jsonl').resolve():return '\n'.join(json.dumps(row)for row in r)+'\n'
            if path.resolve()==(run/'actual.jsonl.protocol.json').resolve():return json.dumps(p)+'\n'
            return original_read(path,*args,**kwargs)
        Path.read_text=read_text
        sys.argv=['receive121.py','--input',str(inp),'--run',str(run),'--out',str(out/name)]
        try:
            receiver.main()
            assert expect is None,'fault was accepted: '+name
            record=dict(name=name,expected_rejection=False,result='PASS_PRISTINE')
        except (ValueError,AssertionError) as error:
            assert expect and expect in str(error),'unexpected rejection for '+name+': '+str(error)
            record=dict(name=name,expected_rejection=True,result='REJECTED',message=str(error))
        finally:Path.read_text=original_read
        records.append(record)
    def selected(r,kind):return next(row for row in r if row['kind']==kind and row['status']==0 and row['sink_result_lines'])
    def flip(r,kind,key):
        row=selected(r,kind);row[key][0]^=1
    def root(r):
        row=selected(r,2);row['r_descriptor']=('1'if row['r_descriptor'][0]!='1'else'2')+row['r_descriptor'][1:]
    scenario('pristine')
    scenario('M-output',lambda r:flip(r,0,'out'),expect='independent M out')
    scenario('A-probability',lambda r:flip(r,1,'P'),expect='independent A P')
    scenario('R-state',lambda r:flip(r,2,'state'),expect='state and128Y independent')
    scenario('R-root',root,expect='external atomic root true bytes')
    scenario('G-output',lambda r:flip(r,3,'g_out'),expect='real candidate prefix')
    scenario('epoch',lambda r:r[0].__setitem__('epoch',r[0]['epoch']+1),expect='no-wrap epoch sequence')
    scenario('consumer-total',protocol_change=lambda p:p.__setitem__('consumer_lines',p['consumer_lines']+1),expect='every committed beat consumed exactly once')
    scenario('consumer-release',protocol_change=lambda p:p.__setitem__('consumer_releases',p['consumer_releases']+1),expect='each consumer lease explicitly released')
    report=dict(schema='block-v1-semantic-negative/1',receiver=str(spec.origin),
                receiver_sha256=hashlib.sha256(Path(spec.origin).read_bytes()).hexdigest(),run=str(run),
                run_manifest_sha256=hashlib.sha256((run/'manifest.json').read_bytes()).hexdigest(),
                fault_model='Declared in-memory post-authentication observation injection; no source/output file edits',tests=records)
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS_SEMANTIC_NEGATIVES',len(records)-1)


if __name__=='__main__':main()
