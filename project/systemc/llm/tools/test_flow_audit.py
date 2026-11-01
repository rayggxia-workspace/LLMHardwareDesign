"""Integrity controls for the observer used to draw architectural conclusions."""
import csv,json,tempfile
from pathlib import Path
from analyze_flow import analyze

def fixture(root,mutation=None):
    fields='id,producer,birth,last_use,uses,elements,payload_bytes,scale_bytes,exponent,label'.split(',')
    values=[[1,0,1,1,1,4,8,4,-10,'host.external'],[2,1,1,2,1,4,8,4,-10,'M.linear']]
    events=[dict(op=1,label='M.linear',step=0,layer=0,inputs=[dict(value=1,offset=0,count=4,payload_bytes=8,scale_bytes=4)],output=2,macro_transactions=[5,0,0,0,0,0,0],weight_logical_read_bytes=32,host_state_io_bytes=0),
      dict(op=2,label='N.argmax',step=0,layer=0,inputs=[dict(value=2,offset=0,count=4,payload_bytes=8,scale_bytes=4)],macro_transactions=[0,2,0,0,0,0,0],weight_logical_read_bytes=0,host_state_io_bytes=0)]
    if mutation:mutation(values,events)
    with (root/'flow-values.csv').open('w',newline='')as f:
        w=csv.writer(f);w.writerow(fields);w.writerows(values)
    (root/'flow-events.jsonl').write_text(''.join(json.dumps(e)+'\n'for e in events))
    (root/'systemc_receipt.json').write_text(json.dumps(dict(transactions=dict(zip('MNEGRST',[5,2,0,0,0,0,0])))))

def main():
    with tempfile.TemporaryDirectory()as d:
        root=Path(d);fixture(root);assert analyze(root)['operations']==2
        for mutation in (lambda v,e:e[0]['inputs'][0].update(offset=7),
                         lambda v,e:v[0].__setitem__(1,1),
                         lambda v,e:e[0]['macro_transactions'].__setitem__(0,4),
                         lambda v,e:v[1].__setitem__(3,1),
                         lambda v,e:e[0]['inputs'][0].update(scale_bytes=6),
                         lambda v,e:e[0].update(weight_logical_read_bytes=-32)):
            fixture(root,mutation)
            try:analyze(root)
            except AssertionError:pass
            else:raise AssertionError('observer accepted corrupt provenance/accounting')
    print('FLOW_AUDIT_CONTROLS PASS: valid data; bad slice, dependency, macro count, lifetime, scale size and negative bytes rejected')
if __name__=='__main__':main()
