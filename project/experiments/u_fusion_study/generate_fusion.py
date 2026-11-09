"""Locked adjacent-E forwarding and observation; no concurrent DDR fiction."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
COMPARE=HERE.parent/'sram_port_compare'
sys.path.insert(0,str(COMPARE))
from generate_policy import generate as generate_policy
from generate_compare import BASE,replace_once


def verify_sources(expected_lock=None):
    lock=json.loads((HERE/'source.json').read_text(encoding='utf-8')) if expected_lock is None else expected_lock
    for field in ('dependency_sha256','source_sha256'):
        if not lock.get(field):raise ValueError('missing fusion source lock '+field)
        for name,value in lock[field].items():
            if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=value:
                raise ValueError('fusion source drift '+name)
    return lock


def generate(out):
    verify_sources();source=generate_policy(out)
    source=replace_once(source,'#include <systemc>','#include <systemc>\n#include <cstdlib>\n#include <sstream>')
    source=replace_once(source,'struct Config {','struct Config {\n bool u_fusion=false;int u_forward_fee=0;')
    source=replace_once(source,'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11)',
        'if(argc!=3&&argc!=4&&argc!=7&&argc!=10&&argc!=11&&argc!=13)')
    source=replace_once(source,'if(argc==11){','if(argc>=11){')
    source=replace_once(source,'Study s("study",c,argv[1]);','''if(argc==13){
  try {
   for(int arg=11;arg<13;++arg){const std::string value=argv[arg];if(value.empty()||!std::all_of(value.begin(),value.end(),[](unsigned char ch){return ch>='0'&&ch<='9';}))throw std::invalid_argument("non-integer fusion parameter");}
   const int enabled=std::stoi(argv[11]),fee=std::stoi(argv[12]);
   if((enabled!=0&&enabled!=1)||(fee!=0&&fee!=1&&fee!=3)){std::cerr<<"invalid fusion configuration\\n";return 2;}
   c.u_fusion=enabled!=0;c.u_forward_fee=fee;
  }catch(const std::exception&){std::cerr<<"invalid fusion argument\\n";return 2;}
 }
 Study s("study",c,argv[1]);''')
    source=replace_once(source,'read(trace);SC_THREAD(run);','read(trace);u_init(trace);SC_THREAD(run);')
    source=replace_once(source,' void vector_region(size_t begin,size_t end){',
        '#include "u_vector_region.inc"\n void vector_region_legacy(size_t begin,size_t end){')
    source=replace_once(source,'emit_hardware();emit_compare();emit_policy();',
        'emit_hardware();emit_compare();emit_policy();emit_u_fusion();')
    (out/'u_vector_region.inc').write_bytes((HERE/'u_vector_region.inc').read_bytes())
    (out/'model.cpp').write_bytes(source.encode())
    return source
