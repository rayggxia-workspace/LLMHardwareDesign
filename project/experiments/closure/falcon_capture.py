"""Issue72 bounded parameter intake; run on server, no complete model load."""
import argparse, hashlib, json, shutil, platform
from pathlib import Path
import numpy as np

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def put(path,obj):path.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('weights','capture','out','binding'):ap.add_argument('--'+k,required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    binding=json.loads(Path(a.binding).read_text());assert binding['falcon_capture_sha256']==sha(__file__)
    source=Path(a.capture);man=json.loads((source/'manifest.json').read_text())
    for x in man['artifacts']:
        p=source/x['path'];assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256'],p
    cfg=json.loads((source/'config.json').read_text());assert cfg['model_type']=='falcon_h1' and cfg['mamba_n_groups']==1
    cap=np.load(source/'capture.npz',allow_pickle=False)
    required=['calibration.input','evaluation.input','calibration.attention','evaluation.attention','calibration.norm','evaluation.norm','calibration.projected','evaluation.projected','calibration.raw_scan','evaluation.raw_scan','calibration.scan_normed','evaluation.scan_normed','calibration.mamba','evaluation.mamba','calibration.pre_ff_input','evaluation.pre_ff_input','calibration.tokens','evaluation.tokens']
    data={k:cap[k] for k in required}
    data.update({k:cap[k] for k in cap.files if k.startswith('weight.')})
    weights=Path(a.weights);index=json.loads((weights/'model.safetensors.index.json').read_text())['weight_map']
    names={'input_gamma':'model.layers.0.input_layernorm.weight','next_gamma':'model.layers.0.pre_ff_layernorm.weight','in_weight':'model.layers.0.mamba.in_proj.weight','out_weight':'model.layers.0.mamba.out_proj.weight'}
    for k in ('in','out'):
        candidate='model.layers.0.mamba.'+k+'_proj.bias'
        if candidate in index:names[k+'_bias']=candidate
    from safetensors import safe_open
    shards={};receipts=[]
    for label,key in names.items():
        path=weights/index[key]
        if str(path) not in shards:shards[str(path)]={'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}
        with safe_open(path,framework='pt',device='cpu') as f:
            t=f.get_tensor(key);data['weight.'+label]=t.float().numpy();receipts.append({'name':key,'source_dtype':str(t.dtype),'shape':list(t.shape),'shard':path.name})
    # pre_ff norm output is independently reconstructed from complete true input/gamma.
    gamma=data['weight.next_gamma'].astype(np.float64)
    for split in ('calibration','evaluation'):
        x=data[split+'.pre_ff_input'].astype(np.float64)
        data[split+'.next_norm_reference']=(x/np.sqrt(np.mean(x*x,axis=-1,keepdims=True)+cfg['rms_norm_eps'])*gamma).astype(np.float32)
    np.savez_compressed(out/'capture.npz',**data);shutil.copyfile(source/'config.json',out/'config.json')
    put(out/'report.json',{'schema':'falcon-closure-capture-v1','source_manifest_sha256':sha(source/'manifest.json'),'source_capture_sha256':sha(source/'capture.npz'),'model_revision':'01087ec4c132d7f186908716b3530ea187f062a1','tensors':receipts,'shards':list(shards.values()),'boundary':'True layer0 input and external attention from Issue70; full Mamba weights plus both full norm gamma. FP32 reference only, not integer execution.','environment':{'python':platform.python_version(),'numpy':np.__version__}})
    put(out/'manifest.json',{'schema':'falcon-closure-capture-v1','status':'EXECUTED','source':binding,'artifacts':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()]})
    print(json.dumps({'out':str(out),'manifest_sha256':sha(out/'manifest.json')}))
if __name__=='__main__':main()
