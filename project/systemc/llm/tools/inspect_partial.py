#!/usr/bin/env python3
"""只读比较已flush的逐层trace，供完整作业尚未结束时定位第一处分叉。"""
import pathlib,sys,numpy as np
from validate_inference import tensors,metric
a=tensors(pathlib.Path(sys.argv[1]))
b=np.fromfile(sys.argv[2],dtype='<f4').reshape(-1,int(sys.argv[3]))
for i,(x,y) in enumerate(zip(a,b)):
    print(i,metric(x,y),'norms',float(np.linalg.norm(x)),float(np.linalg.norm(y)))
    if i>=int(sys.argv[4] if len(sys.argv)>4 else 28):break
