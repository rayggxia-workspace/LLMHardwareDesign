"""Independent integer replay of the two actual attention samples in the selected Issue64 archive.
Run verify_delivery.py first; this checks sample arithmetic, not all 56 NPZs.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--input',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
if a.out.exists():raise FileExistsError(a.out)
repo=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('independent_attention_receiver',repo/'project/experiments/block_decisions/receive_attention.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
records={v['id']:v for v in r.read_json(a.input/'attention01/attention.json')}
samples=a.input/'receive01/samples'
tables={}
for grid in (128,256):
    table=np.fromfile(samples/('exp-grid%d.u32le.bin'%grid),dtype='<u4')
    r.equal(table,r.decimal_lut(grid),'Decimal50 LUT')
    tables[grid]=table
counts={k:0 for k in ('QK_I64_values','score_integer_values','score_Fraction_witnesses','exp_and_P15_values','PV_I64_values','diagnostic_metrics')}
results=[]
for name in ('qwen25.prefix128.l0.kv16.lut128','gemma.prefix4096.l0.kv16.lut128'):
    results.append(r.verify_case(samples/(name+'.npz'),records[name],tables[128],counts))
receipt={'status':'PASS','scope':'two selected actual samples; full server56-case receiver is separate','independent_receiver_sha256':r.sha(Path(r.__file__)),'numpy':np.__version__,'counts':counts,'cases':results,'Decimal50_LUT_entries':sum(len(x) for x in tables.values()),'hardware_performance_accepted':False,'full_model_quality_accepted':False}
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'status':'PASS','counts':counts}))
