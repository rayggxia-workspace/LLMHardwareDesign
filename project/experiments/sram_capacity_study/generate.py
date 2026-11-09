"""SHA-bound capacity/port extension; never edit the accepted Issue245 source."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'p_dma_study'
sys.path.insert(0,str(BASE))
import instrument

def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('non-unique anchor '+old[:80])
    return text.replace(old,new)

def generate(out):
    lock=json.loads((HERE/'source.json').read_text())
    for name,value in lock['base_functional_sha256'].items():
        if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=value:raise ValueError('source drift '+name)
    source=instrument.generate()
    source=replace_once(source,'int buffer_count=2,book_cycles=1;','U pbytes=16384;int buffer_count=2,book_cycles=1,pslat=0;')
    source=replace_once(source,'if(argc!=3&&argc!=4)','if(argc!=3&&argc!=4&&argc!=6)')
    source=replace_once(source,'if(argc==4){','if(argc>=4){')
    source=replace_once(source,'Study s("study",c,argv[1]);','''if(argc==6){
  c.pbytes=std::stoi(argv[4])*1024;c.pslat=std::stoi(argv[5]);
  if((c.pbytes!=16384&&c.pbytes!=32768&&c.pbytes!=44032&&c.pbytes!=49152&&c.pbytes!=65536&&c.pbytes!=131072)||c.pslat<1||c.pslat>2){std::cerr<<"invalid capacity/port cost\\n";return 2;}
 }
 Study s("study",c,argv[1]);''')
    old='ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C'
    assert source.count(old)==2
    source=source.replace(old,'ceildiv(cfg.beat,cfg.swidth)*((b->group<cfg.mcount&&cfg.pslat)?cfg.pslat:cfg.slat)*C')
    source=replace_once(source,'ceildiv(bytes,cfg.swidth)*cfg.slat*C','ceildiv(bytes,cfg.swidth)*((group<cfg.mcount&&cfg.pslat)?cfg.pslat:cfg.slat)*C')
    source=replace_once(source,'detail::emit(std::cout,end_ticks,cfg.mcount,cfg.variant);','detail::emit(std::cout,end_ticks,cfg.mcount,cfg.variant,cfg.pbytes,cfg.pslat?cfg.pslat:cfg.slat);')
    matrix=(BASE/'matrix.inc').read_text()
    assert matrix.count('16384')==8,matrix.count('16384')
    matrix=matrix.replace('16384','cfg.pbytes').replace('cfg.slat*C','(cfg.pslat?cfg.pslat:cfg.slat)*C')
    detail=(BASE/'detail.hpp').read_text()
    detail=replace_once(detail,'const std::string& variant){','const std::string& variant,int capacity,int port_cycles){')
    detail=replace_once(detail,'<<",\\\"end_subcycles\\\":"<<end','<<",\\\"P_capacity_bytes\\\":"<<capacity<<",\\\"P_service_cycles\\\":"<<port_cycles<<",\\\"end_subcycles\\\":"<<end')
    audit=(BASE/'audit.py').read_text()
    audit=replace_once(audit,'def check(row,path):','def check(row,path,capacity):')
    audit=replace_once(audit,"row['P_scratch_peak_bytes']<=16384","row['P_scratch_peak_bytes']<=capacity")
    for name,text in [('model.cpp',source),('matrix.inc',matrix),('detail.hpp',detail),('capacity_audit.py',audit)]:
        (out/name).write_bytes(text.encode())
    return source
