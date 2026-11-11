"""Isolated, locked P-capacity x port x register-context comparison generator."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
AREA=HERE.parent/'area_speed_study'
sys.path.insert(0,str(AREA))
from generate_hardware import generate_hardware
from generate import BASE,replace_once


def verify_sources(expected_lock=None):
    """Validate the actual source lock, or a copied lock for a refusal test."""
    lock=json.loads((HERE/'source.json').read_text(encoding='utf-8')) if expected_lock is None else expected_lock
    for field in ('dependency_sha256','source_sha256'):
        if not lock.get(field):raise ValueError('missing compare source lock '+field)
        for name,value in lock[field].items():
            if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=value:
                raise ValueError('compare source drift '+name)
    return lock


COMPARE_RECEIPT=r'''
 void emit_compare(){
  std::cout<<",\"compare_study\":{\"P_capacity_bytes\":"<<cfg.pbytes
   <<",\"P_port_quarter_cycles\":"<<(cfg.p_port_quarters?cfg.p_port_quarters:cfg.slat*4)
   <<",\"P_port_subcycles\":"<<s_port_duration(cfg,0,cfg.swidth)
   <<",\"P_count\":"<<cfg.mcount<<",\"U_capacity_bytes\":16384"
   <<",\"U_port_subcycles\":"<<s_port_duration(cfg,3,cfg.swidth)
   <<",\"dual_ports\":"<<(cfg.split_P_ports?"true":"false")
   <<",\"scope\":\"P SRAM capacity and per-64B port occupancy sensitivity only; U16KiB/2P/4-vector-lanes/DDR/core clock fixed; no physical frequency or energy qualification\"}";
 }
'''


def generate(out):
    verify_sources()
    source=generate_hardware(out,pcount=2,dual=False,lanes=4)
    source=replace_once(source,'struct Config {',
        'struct Config {\n U pbytes=16384;int p_port_quarters=0;')
    source=replace_once(source,'struct Tensor{','''U s_port_duration(const Config& cfg,int group,U bytes){
 const U unit=(group<cfg.mcount&&cfg.p_port_quarters)?U(cfg.p_port_quarters)*C/4:U(cfg.slat)*C;
 return ceildiv(bytes,cfg.swidth)*unit;
}
struct Tensor{''')
    source=replace_once(source,'if(argc!=3&&argc!=4&&argc!=7)','if(argc!=3&&argc!=4&&argc!=7&&argc!=10)')
    source=replace_once(source,'if(argc==7){','if(argc>=7){')
    source=replace_once(source,'Study s("study",c,argv[1]);','''if(argc==10){
  try {
   for(int arg=7;arg<10;++arg){const std::string value=argv[arg];if(value.empty()||!std::all_of(value.begin(),value.end(),[](unsigned char ch){return ch>='0'&&ch<='9';}))throw std::invalid_argument("non-integer compare parameter");}
   const int kib=std::stoi(argv[7]),dual=std::stoi(argv[8]),quarters=std::stoi(argv[9]);
   if((c.name!="queued_pipe_w8"&&c.name!="queued_pipe_w16")||
      (kib!=16&&kib!=48&&kib!=64)||(dual!=0&&dual!=1)||
      (quarters!=4&&quarters!=5&&quarters!=6&&quarters!=8)||(c.contexts!=1&&c.contexts!=8)){
    std::cerr<<"invalid capacity/port comparison configuration\\n";return 2;
   }
   c.pbytes=U(kib)*1024;c.split_P_ports=dual!=0;c.p_port_quarters=quarters;
  }catch(const std::exception&){std::cerr<<"invalid comparison parameter\\n";return 2;}
 }
 Study s("study",c,argv[1]);''')
    old='ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C'
    if source.count(old)!=2:raise ValueError('memory duration anchor count')
    source=source.replace(old,'s_port_duration(cfg,b->group,cfg.beat)')
    old='ceildiv(bytes,cfg.swidth)*cfg.slat*C'
    if source.count(old)!=2:raise ValueError('generic/output S duration anchor count')
    source=source.replace(old,'s_port_duration(cfg,group,bytes)')
    source=replace_once(source,
        r'<<",\"P_S_bytes\":16384,\"U_S_bytes\":16384,\"total_private_S_bytes\":"<<U(cfg.mcount+1)*16384',
        r'<<",\"P_S_bytes\":"<<cfg.pbytes<<",\"U_S_bytes\":16384,\"total_private_S_bytes\":"<<(U(cfg.mcount)*cfg.pbytes+16384)')
    source=replace_once(source,r'<<",\"S_port_cycles\":"<<cfg.slat',
        r'<<",\"S_port_cycles\":"<<double(s_port_duration(cfg,0,cfg.swidth))/C')
    source=replace_once(source,'detail::emit(std::cout,end_ticks,cfg.mcount,cfg.variant);',
        'detail::emit(std::cout,end_ticks,cfg.mcount,cfg.variant,cfg.pbytes,double(s_port_duration(cfg,0,cfg.swidth))/C);')
    source=replace_once(source,' void emit_hardware(){',COMPARE_RECEIPT+' void emit_hardware(){')
    source=replace_once(source,'cfg.reuse_A,cfg.mcount);emit_hardware();',
        'cfg.reuse_A,cfg.mcount);emit_hardware();emit_compare();')
    for name,count in (('matrix.inc',8),('context_worker.inc',6)):
        path=out/name;text=path.read_text(encoding='utf-8')
        if text.count('16384')!=count:raise ValueError('P-only capacity anchor count '+name)
        text=text.replace('16384','cfg.pbytes')
        text=replace_once(text,'ceildiv(p->abytes+p->bbytes,cfg.swidth)*cfg.slat*C',
            's_port_duration(cfg,worker,p->abytes+p->bbytes)')
        path.write_bytes(text.encode())
    path=out/'detail.hpp';detail=path.read_text(encoding='utf-8')
    detail=replace_once(detail,'const std::string& variant){',
        'const std::string& variant,int capacity,double port_cycles){')
    detail=replace_once(detail,r'<<",\"end_subcycles\":"<<end',
        r'<<",\"P_capacity_bytes\":"<<capacity<<",\"P_service_cycles\":"<<port_cycles<<",\"end_subcycles\":"<<end')
    path.write_bytes(detail.encode())
    (out/'model.cpp').write_bytes(source.encode())
    return source
