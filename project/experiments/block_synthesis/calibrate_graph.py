"""Observe every runtime ONNX tensor of the actual full benchmark.

Uses converted checkpoint tensors, retains the complete graph, and does not
turn observed shapes/ranges into unverified hardware operations.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import numpy as np
import onnx
import onnxruntime as ort

from frontend import import_onnx


def main():
    p=argparse.ArgumentParser();p.add_argument('onnx',type=Path);p.add_argument('calibration',type=Path)
    p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(exist_ok=False)
    weights=json.loads(a.calibration.read_text());m=import_onnx(a.onnx)
    source=onnx.load(str(a.onnx));infos={v.name:v for v in list(source.graph.value_info)+list(source.graph.input)+list(source.graph.output)}
    names=list(dict.fromkeys(n for t in m['tasks'] for n in t['outputs']))
    del source.graph.output[:]
    source.graph.output.extend([deepcopy(infos[n]) for n in names])
    onnx.checker.check_model(source)
    path=a.output/'observed.onnx';onnx.save(source,str(path))
    opts=ort.SessionOptions();opts.intra_op_num_threads=int(os.environ.get('SLURM_CPUS_PER_TASK','4'));opts.inter_op_num_threads=1
    session=ort.InferenceSession(str(path),sess_options=opts,providers=['CPUExecutionProvider'])
    feed={}
    for value in session.get_inputs():
        if value.name=='input_ids':continue
        key=value.name.removeprefix('model.')
        entry=weights['parameters'][key]
        weight_path=Path(entry['file'])
        if not weight_path.is_absolute():weight_path=a.calibration.parent.parent/weight_path
        feed[value.name]=np.asarray(np.load(weight_path,mmap_mode='r'),dtype=np.float32)*math.ldexp(1.,entry['format']['exponent'])
    rows={};samples=[]
    for ids in ([[1,2]],[[3,4]],[[42,43]]):
        feed['input_ids']=np.array(ids,dtype=np.int64)
        arrays=session.run(names,feed)
        if not samples:np.savez(a.output/'first-runtime-values.npz',**dict(zip(names,arrays)))
        for name,array in zip(names,arrays):
            if array.dtype.kind!='f':continue
            if np.isnan(array).any() or np.isposinf(array).any():raise ValueError('unexpected nonfinite activation '+name)
            finite=array[np.isfinite(array)]
            maximum=float(np.abs(finite).max()) if finite.size else 0.
            row=rows.setdefault(name,{'shape':list(array.shape),'dtype':str(array.dtype),'max_abs':0.,'negative_infinity':0,'observations':0})
            row['max_abs']=max(row['max_abs'],maximum)
            row['negative_infinity']=max(row['negative_infinity'],int(np.isneginf(array).sum()))
            row['observations']+=1
        samples.append({'ids':ids,'runtime_outputs':len(arrays)})
        print('SAMPLE',ids,len(arrays),flush=True)
    for row in rows.values():
        row['symmetric_s16_exponent']=math.ceil(math.log2(row['max_abs']/32767)) if row['max_abs'] else 0
    result={'scope':'full ONNX runtime activation calibration with quantized/dequantized real weights',
        'source_sha256':m['sha256'],'weight_calibration_sha256':hashlib.sha256(a.calibration.read_bytes()).hexdigest(),
        'runtime_nodes':len(m['tasks']),'samples':samples,'values':rows,'onnxruntime':ort.__version__,
        'native_numeric_qualified':False}
    (a.output/'activation-calibration.json').write_text(json.dumps(result,indent=2)+'\n')
    print('ACTIVATION_CALIBRATION_PASS',len(rows),flush=True)


if __name__=='__main__':main()
