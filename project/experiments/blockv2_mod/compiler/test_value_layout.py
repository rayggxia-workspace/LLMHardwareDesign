"""Compare every full-graph view element to independent NumPy operations."""
import json,sys
from pathlib import Path
from math import prod
import numpy as np
from value_layout import build,source_index,contiguous_runs
g=json.loads(Path(sys.argv[1]).read_text());layout=build(g);oracle={};checked=0;run_count=0;views=0
for t in g['tasks']:
    if t['kind']!='View':continue
    op=t['details']['operation'];src=op['inputs'][0];dst=op['outputs'][0]
    if src not in oracle:oracle[src]=np.arange(prod(g['values'][src]['shape'])).reshape(g['values'][src]['shape'])
    x=oracle[src];kind=op['op'];attr=op.get('attributes',{})
    def param(i):return g['values'][op['inputs'][i]]['constant']
    if kind=='Transpose':y=x.transpose(attr.get('perm'))
    elif kind in ('Reshape','Squeeze','Unsqueeze'):y=x.reshape(g['values'][dst]['shape'])
    elif kind=='Expand':y=np.broadcast_to(x,g['values'][dst]['shape'])
    elif kind=='Identity':y=x
    else:raise AssertionError('extend independent oracle for '+kind)
    oracle[dst]=y
    v=layout['values'][dst];actual=np.fromiter((source_index(v,i) for i in range(y.size)),dtype=np.int64)
    np.testing.assert_array_equal(actual,y.reshape(-1),err_msg=dst)
    runs=list(contiguous_runs(v));restored=[]
    for logical,physical,count in runs:
        assert logical==len(restored)
        restored.extend(range(physical,physical+count))
    np.testing.assert_array_equal(restored,y.reshape(-1),err_msg='transfer segments '+dst)
    checked+=y.size;views+=1;run_count+=len(runs)
out=Path(sys.argv[2]);out.mkdir()
(out/'value-layout.json').write_text(json.dumps(layout,indent=2)+'\n')
report={'passed':True,'views':views,'element_addresses_checked':checked,'source_contiguous_runs':run_count,
        'scope':'all graph view address transformations and transfer segments; not evidence that hardware has executed the transfers',
        'machine_package_complete':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
