"""Follow up observed M/feeder and S16 NExp bottlenecks; no RTL edits."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def once(text,before,after):
    if text.count(before)!=1:
        raise ValueError('followup source anchor '+repr(before))
    return text.replace(before,after)


def generate(repo,out,r1,r2,r4):
    repo,out=Path(repo),Path(out)
    base=load(repo/'project/experiments/optimization_sweep/generate.py','followup_base_generator')
    receipt=base.generate(repo,out,r1,r2,r4)
    p=out/'optimization.hpp';s=p.read_text(encoding='utf8')
    s=once(s,'bool nexp8=false;','bool nexp8=false,nexp_s16=false;U local_read_bytes=64,bridge_values=0,bridge_cycles=0,read_old=0,read_new=0;')
    s=once(s,' else return false;', ''' else if(name=="s16_n4")nexp_s16=true;
 else if(name=="s16_n8"){nexp_s16=true;nexp8=true;}
 else if(name=="vector16_s16_n4"){lanes=16;nexp_s16=true;}
 else if(name=="read128")local_read_bytes=128;
 else if(name=="m16_feed2_read128"){local_read_bytes=128;k_lanes=16;a_bytes=64;b_bytes=128;}
 else if(name=="balanced"){local_read_bytes=128;k_lanes=16;a_bytes=64;b_bytes=128;lanes=16;nexp_s16=true;}
 else return false;''')
    s=once(s,'U nexp_cost(U count,bool qualified,U old_cost){','U nexp_cost(U count,bool qualified,U old_cost,bool s16){')
    s=once(s,'const U cost=nexp8&&qualified?ceildiv(count,8)*7:old_cost;', '''U cost=nexp8&&qualified?ceildiv(count,8)*7:old_cost;
 if(nexp_s16&&s16){
  // Explicit conditional format bridge: one extra cycle per eight S16
  // values, then the 4/8-lane target service. Existing S read/write and
  // vector_region work remain. This is NOT a new measured RTL profile.
  const U bridge=ceildiv(count,8);bridge_values+=count;bridge_cycles+=bridge;
  cost=ceildiv(count,nexp8?8:4)*7+bridge;
 }''')
    s=once(s,'void emit(std::ostream& out){', '''U read_cost(U bytes){const U old_cost=ceildiv(bytes,64),cost=ceildiv(bytes,local_read_bytes);
 read_old+=old_cost;read_new+=cost;return cost*C;}
void emit(std::ostream& out){''')
    s=once(s,'<<",\\\"nexp8\\\":"<<(nexp8?"true":"false")',
           '<<",\\\"nexp8\\\":"<<(nexp8?"true":"false")\n'
           '    <<",\\\"nexp_S16_bridge\\\":"<<(nexp_s16?"true":"false")\n'
           '    <<",\\\"bridge_values\\\":"<<bridge_values<<",\\\"bridge_cycles\\\":"<<bridge_cycles\n'
           '    <<",\\\"M_read_bytes_per_cycle\\\":"<<local_read_bytes<<",\\\"M_read_old\\\":"<<read_old<<",\\\"M_read_new\\\":"<<read_new')
    p.write_bytes(s.encode())
    p=out/'model.cpp';s=p.read_text(encoding='utf8')
    s=once(s,'optimization::nexp_cost(o.elements,nexp_qualified,nexp_extra)',
           'optimization::nexp_cost(o.elements,nexp_qualified,nexp_extra,o.in.size()==1&&tensors[o.in[0]].bits==16&&tensors[o.out].bits==32)')
    p.write_bytes(s.encode())
    p=out/'shared_pool_methods.inc';s=p.read_text(encoding='utf8')
    s=once(s,'return store[worker].reserve(now(),s_port_duration(cfg,worker,bytes));',
           'return store[worker].reserve(now(),optimization::read_cost(bytes));')
    p.write_bytes(s.encode())
    result=dict(parent_generation=receipt,scope='S16 bridge and local-M-read width conditional sensitivity',
                generated_sha256={p.name:sha(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')})
    (out/'followup-generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result
