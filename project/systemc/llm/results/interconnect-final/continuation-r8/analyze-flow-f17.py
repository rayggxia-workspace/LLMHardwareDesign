"""Audit observed logical tensor provenance; no inferred wire topology/timing."""
import argparse, csv, hashlib, json, re
from collections import Counter
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
    return h.hexdigest()
def group(label):
    return re.sub(r'model\.layers\.\d+\.', 'model.layers.*.', label)
def analyze(run):
    rows=list(csv.DictReader((run/'flow-values.csv').open()))
    values={int(r['id']):{k:(v if k=='label'else int(v))for k,v in r.items()}for r in rows}
    assert len(values)==len(rows)
    uses=Counter();edges={};ops=Counter();counts=[0]*7;read_bytes=scale_bytes=weight_bytes=state_bytes=0
    sweep=Counter();sequence=0;output_ids=set();last={}
    for line in (run/'flow-events.jsonl').open():
        a=json.loads(line);sequence+=1;assert a['op']==sequence
        label=group(a['label']);ops[label]+=1
        assert len(a['macro_transactions'])==7
        assert all(n>=0 for n in a['macro_transactions'])
        assert a['weight_logical_read_bytes']>=0 and a['host_state_io_bytes']>=0
        counts=[x+y for x,y in zip(counts,a['macro_transactions'])]
        weight_bytes+=a['weight_logical_read_bytes'];state_bytes+=a['host_state_io_bytes']
        for x in a['inputs']:
            v=values[x['value']];assert v['producer']<sequence
            assert 0<=x['offset']<=x['offset']+x['count']<=v['elements']
            assert x['payload_bytes']==x['count']*2
            assert x['scale_bytes'] in (4,4*x['count'])
            assert v['birth']<=sequence
            last[x['value']]=sequence
            uses[x['value']]+=1;read_bytes+=x['payload_bytes'];scale_bytes+=x['scale_bytes']
            key=group(v['label'])+' -> '+label
            e=edges.setdefault(key,dict(uses=0,payload_bytes=0,scale_bytes=0))
            e['uses']+=1;e['payload_bytes']+=x['payload_bytes'];e['scale_bytes']+=x['scale_bytes']
        if 'output'in a:
            v=values[a['output']];assert v['producer']==sequence and a['output']not in output_ids
            output_ids.add(a['output'])
    receipt=json.loads((run/'systemc_receipt.json').read_text())
    assert dict(zip(('M','N','E','G','R','S','T'),counts))==receipt['transactions'], 'unobserved macro commands'
    for i,v in values.items():
        assert v['uses']==uses[i] and v['birth']<=v['last_use']<=sequence
        assert v['last_use']==last.get(i,v['birth']), 'incorrect last-use lifetime'
        assert v['payload_bytes']==2*v['elements'] and v['scale_bytes'] in (4,4*v['elements'])
        assert v['producer']==0 or i in output_ids
        assert v['producer']==0 or v['birth']==v['producer']
        sweep[v['birth']]+=v['payload_bytes']+v['scale_bytes']
        sweep[v['last_use']+1]-=v['payload_bytes']+v['scale_bytes']
    live=peak=0
    for at in sorted(sweep):live+=sweep[at];peak=max(peak,live)
    assert live==0
    result={'scope':'logical operator-program edges mediated by host; composite labels are not physical wires; weights/R state separately accounted',
      'lifetime_unit':'ordered outer operation ordinal, not clock cycles; last use lower bound, not actual deallocation',
      'operations':sequence,'values':len(values),'input_payload_bytes':read_bytes,'input_scale_bytes':scale_bytes,
      'logical_weight_read_bytes':weight_bytes,'raw_R_state_read_write_bytes':state_bytes,
      'unique_logical_live_bytes_lower_bound_peak':peak,'values_reused':sum(v['uses']>1 for v in values.values()),
      'macro_transaction_totals':dict(zip(('M','N','E','G','R','S','T'),counts)),
      'operations_by_program':dict(ops),'edges':edges,
      'longest_lived_values':sorted(values.values(),key=lambda v:v['last_use']-v['birth'],reverse=True)[:12],
      'unmapped_host_sources':dict(Counter(v['label']for v in values.values()if not v['producer'])),
      'input_sha256':{p.name:sha(p)for p in [run/'flow-events.jsonl',run/'flow-values.csv',run/'systemc_receipt.json']}}
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('run',type=Path);a=ap.parse_args()
    r=analyze(a.run);(a.run/'flow-summary.json').write_text(json.dumps(r,indent=2)+'\n')
    print('FLOW_AUDIT',r['operations'],'operations',r['values'],'values; all macro totals reconciled')
if __name__=='__main__':main()
