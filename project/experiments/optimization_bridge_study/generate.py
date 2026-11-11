"""Test the smaller vector8/S16 option and a slower explicit bridge."""
import hashlib
import importlib.util
import json
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('bridge study anchor '+repr(old))
    return text.replace(old,new)


def generate(repo,out,r1,r2,r4):
    repo,out=Path(repo),Path(out)
    parent=load(repo/'project/experiments/optimization_followup/generate.py','bridge_parent_generator')
    receipt=parent.generate(repo,out,r1,r2,r4)
    p=out/'optimization.hpp';s=p.read_text(encoding='utf8')
    s=once(s,'double bandwidth=17.1e9;','U bridge_cost_per8=1;double bandwidth=17.1e9;')
    s=once(s,' else return false;', ''' else if(name=="vector8_s16_n4"){lanes=8;nexp_s16=true;}
 else if(name=="vector8_s16_n4_bridge8"){lanes=8;nexp_s16=true;bridge_cost_per8=8;}
 else return false;''')
    s=once(s,'const U bridge=ceildiv(count,8);','const U bridge=ceildiv(count,8)*bridge_cost_per8;')
    s=once(s,'<<",\\\"bridge_values\\\":"<<bridge_values',
           '<<",\\\"bridge_cost_per8\\\":"<<bridge_cost_per8<<",\\\"bridge_values\\\":"<<bridge_values')
    p.write_bytes(s.encode())
    result=dict(parent_generation=receipt,scope='vector8 plus S16 bridge cost sensitivity; no RTL implementation',
                generated_sha256={p.name:sha(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')})
    (out/'bridge-generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result
