"""Override only the adaptive prefetch predicate's capacity reference."""
import hashlib
import json
from pathlib import Path

from generate_compare import generate as generate_compare,replace_once,BASE

HERE=Path(__file__).resolve().parent


def verify_sources(expected_lock=None):
    lock=json.loads((HERE/'source-policy.json').read_text(encoding='utf-8')) if expected_lock is None else expected_lock
    for field in ('dependency_sha256','source_sha256'):
        if not lock.get(field):raise ValueError('missing policy source lock '+field)
        for name,value in lock[field].items():
            if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=value:
                raise ValueError('policy source drift '+name)
    return lock


POLICY_RECEIPT=r'''
 void emit_policy(){
  std::cout<<",\"policy_study\":{\"requested_policy_KiB\":"<<cfg.adaptive_policy_bytes/1024
   <<",\"effective_policy_bytes\":"<<(cfg.adaptive_policy_bytes?cfg.adaptive_policy_bytes:cfg.pbytes)
   <<",\"actual_P_capacity_bytes\":"<<cfg.pbytes
   <<",\"scope\":\"adaptive prefetch predicate override only; actual residency, scratch budgets, context target and S port costs unchanged\"}";
 }
'''


def generate(out):
    verify_sources();source=generate_compare(out)
    source=replace_once(source,'struct Config {','struct Config {\n U adaptive_policy_bytes=0;')
    source=replace_once(source,'if(argc!=3&&argc!=4&&argc!=7&&argc!=10)',
        'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11)')
    source=replace_once(source,'if(argc==10){','if(argc>=10){')
    source=replace_once(source,'Study s("study",c,argv[1]);','''if(argc==11){
  try {
   const std::string value=argv[10];
   if(value.empty()||!std::all_of(value.begin(),value.end(),[](unsigned char ch){return ch>='0'&&ch<='9';}))throw std::invalid_argument("non-integer policy parameter");
   const int kib=std::stoi(value);
   if(kib!=0&&kib!=16){std::cerr<<"invalid adaptive policy reference\\n";return 2;}
   c.adaptive_policy_bytes=U(kib)*1024;
  }catch(const std::exception&){std::cerr<<"invalid adaptive policy parameter\\n";return 2;}
 }
 Study s("study",c,argv[1]);''')
    source=replace_once(source,' void emit_compare(){',POLICY_RECEIPT+' void emit_compare(){')
    source=replace_once(source,'emit_hardware();emit_compare();','emit_hardware();emit_compare();emit_policy();')
    path=out/'matrix.inc';matrix=path.read_text(encoding='utf-8')
    matrix=replace_once(matrix,
        'if(cfg.adaptive&&o.rows==1&&o.layout==0&&policy_a+policy_min_b+96+policy_workspace<=cfg.pbytes){',
        'if(cfg.adaptive&&o.rows==1&&o.layout==0&&policy_a+policy_min_b+96+policy_workspace<=(cfg.adaptive_policy_bytes?cfg.adaptive_policy_bytes:cfg.pbytes)){')
    path.write_bytes(matrix.encode());(out/'model.cpp').write_bytes(source.encode())
    return source
