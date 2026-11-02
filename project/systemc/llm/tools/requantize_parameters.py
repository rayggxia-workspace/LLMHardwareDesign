"""Preserve learned matrix exports; re-encode identified wide-range static vectors.

Gemma effective norm gamma and Falcon offline A_exp get one S16 exponent per
element. No activations, labels or calibration choose these exponents.
"""
import argparse,hashlib,json,math,shutil
from pathlib import Path
import numpy as np
import torch
from safetensors import safe_open
from model_support import canonical
from export_checkpoint import sha

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('checkpoint',type=Path);ap.add_argument('output',type=Path)
    a=ap.parse_args();torch.set_num_threads(1);report=json.loads((a.checkpoint/'export_receipt.json').read_text())
    family=report['config']['model_type'];assert family in ('gemma3_text','falcon_h1')
    for row in report['source_files']:
        p=Path(row['path']);assert p.stat().st_size==row['bytes']and sha(p)==row['sha256']
    assert sha(a.checkpoint/'weights.bin')==report['weights_sha256']
    if (a.checkpoint/'weights.scales').exists():assert sha(a.checkpoint/'weights.scales')==report['weight_scales_sha256']
    index=[l.split()for l in (a.checkpoint/'weights.index').read_text().splitlines()];by_name={r[0]:r for r in index}
    a.output.mkdir(exist_ok=False);shutil.copyfile(a.checkpoint/'weights.bin',a.output/'weights.bin')
    offset=(a.output/'weights.bin').stat().st_size;scales=[];stats=[]
    with (a.output/'weights.bin').open('ab')as out:
        for path in sorted(Path(report['model_path']).glob('*.safetensors')):
            with safe_open(str(path),framework='pt',device='cpu')as src:
                for original in src.keys():
                    name=canonical(original,family)
                    if name is None:continue
                    if family=='gemma3_text'and name.endswith('norm.weight'):
                        value=src.get_tensor(original).float()+1
                    elif family=='falcon_h1'and name.endswith('.A_log'):
                        name=name[:-len('A_log')]+'A_exp';value=src.get_tensor(original).float().exp()
                    else:continue
                    row=by_name[name];rows,cols=map(int,row[1:3]);assert value.numel()==rows*cols and (rows==1 or cols==1)
                    value=value.flatten();peak=value.abs()
                    exps=torch.where(peak>0,torch.ceil(torch.log2(peak/16383)),torch.full_like(peak,-14)).int()
                    q=torch.round(torch.ldexp(value,-exps));assert not bool(((q< -32768)|(q>32767)).any())
                    raw=q.to(torch.int16).numpy().astype('<i2',copy=False).tobytes();out.write(raw)
                    row[3]=str(int(exps.max()));row[4]=str(offset);offset+=len(raw)
                    es=exps.tolist();scales.append(name+' '+str(len(es))+' 1 '+str(len(es))+' '+' '.join(map(str,es)))
                    reconstructed=torch.ldexp(q,exps);error=(reconstructed-value).double()
                    stats.append(dict(name=name,elements=len(es),group_elements=1,min_exponent=min(es),max_exponent=max(es),
                                      clipped=0,max_absolute_error=float(error.abs().max()),relative_l2_error=float(error.norm()/(value.double().norm()+1e-30))))
                    for tensor in report['tensors']:
                        if tensor['name']==name:tensor.update(exponent=int(exps.max()),parameter_group_elements=1,parameter_exponent_file='parameters.scales')
    assert stats
    expected={name for name in by_name if (family=='gemma3_text'and name.endswith('norm.weight'))or(family=='falcon_h1'and name.endswith('.A_exp'))}
    assert {s['name']for s in stats}==expected,'missing selected static parameters'
    (a.output/'weights.index').write_text('\n'.join(' '.join(r)for r in index)+'\n')
    (a.output/'parameters.scales').write_text('\n'.join(scales)+'\n')
    if (a.checkpoint/'weights.scales').exists():(a.output/'weights.scales').symlink_to((a.checkpoint/'weights.scales').resolve())
    md=dict(l.split()for l in (a.checkpoint/'metadata.txt').read_text().splitlines());md['parameter_groups_version']='1'
    (a.output/'metadata.txt').write_text('\n'.join(k+' '+v for k,v in md.items())+'\n')
    for n in ('prompt.txt','reference_hidden.bin','reference_logits.bin'):(a.output/n).symlink_to((a.checkpoint/n).resolve())
    report.update(previous_export=str(a.checkpoint.resolve()),previous_receipt_sha256=sha(a.checkpoint/'export_receipt.json'),
                  reference_reused_from=str(a.checkpoint.resolve()),weights_sha256=sha(a.output/'weights.bin'),
                  parameter_scales_sha256=sha(a.output/'parameters.scales'),parameter_scale_policy='identified static vectors: one S16 exponent per element; no calibration',
                  static_parameter_groups=stats,parameter_exporter_sha256=sha(Path(__file__)))
    (a.output/'export_receipt.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('STATIC_PARAMETER_EXPORT',family,len(stats),'vectors',sum(s['elements']for s in stats),'elements',flush=True)

if __name__=='__main__':main()
