#!/usr/bin/env python3
"""八模型配置/张量头只读审计；不实例化模型或伪造缺失检查点。"""
import pathlib,json,hashlib,os
from safetensors import safe_open
root=pathlib.Path('/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models')
root70=pathlib.Path('/public/home/yuzelu/RuizhiLiang/issue70-moe-hybrid-20261024/models-relay')
paths={'qwen25':root/'qwen25-3b-5defd279','qwen3':pathlib.Path('/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023/model'),
       'llama':None,'gemma':root/'gemma3-4b-093f9f38','phi':root/'phi4mini-cfbefacb','qwen35':root/'qwen35-4b-851bf6e8','granite':root70/'granite','falcon':root70/'falcon'}
result={}
for key,path in paths.items():
    if path is None:result[key]={'checkpoint_available':False,'reason':'old benchmark used documented config + seeded parameters; no real Llama checkpoint bound'};continue
    raw=(path/'config.json').read_bytes();config=json.loads(raw);headers=[]
    for p in sorted(path.glob('*.safetensors')):
        with safe_open(str(p),framework='pt',device='cpu') as f:
            keys=[k for k in f.keys() if '.layers.0.' in k]
            headers.extend({'name':k,'shape':list(f.get_slice(k).get_shape())} for k in keys)
    result[key]={'checkpoint_available':True,'path':str(path),'config_sha256':hashlib.sha256(raw).hexdigest(),'config':config,'layer0_headers':headers}
out=pathlib.Path(os.environ['ROOT'])/'bench_audit.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('BENCH_AUDIT',str(out),flush=True)
# 新transformers迁移到rope_parameters；建立独立新目录，不改运行中的旧输入。
for name in ('qwen3','qwen25'):
    source=pathlib.Path(os.environ['ROOT'])/(name+'-r1');target=pathlib.Path(os.environ['ROOT'])/(name+'-r2')
    target.mkdir(exist_ok=False);receipt=json.loads((source/'export_receipt.json').read_text());cfg=receipt['config']
    params=cfg.get('rope_parameters') or {};theta=params.get('rope_theta',cfg.get('rope_theta'))
    if theta is None:raise ValueError('rope theta missing')
    if params.get('rope_type','default')!='default':raise ValueError('unimplemented rope type')
    for f in source.iterdir():
        if f.name not in ('metadata.txt','export_receipt.json'):(target/f.name).symlink_to(f)
    lines=(source/'metadata.txt').read_text().splitlines()
    (target/'metadata.txt').write_text('\n'.join('theta '+str(theta) if s.startswith('theta ') else s for s in lines)+'\n')
    receipt['metadata_repair']={'original_directory':str(source),'reason':'rope_theta moved to rope_parameters in transformers','theta':theta}
    (target/'export_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print('ROPE_REPAIR',name,theta,flush=True)
