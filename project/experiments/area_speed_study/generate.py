"""SHA-locked register-context extension of the accepted Issue245 study."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'p_dma_study'
sys.path.insert(0,str(BASE))
import instrument


def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('non-unique anchor '+old[:90])
    return text.replace(old,new)


TYPES='''
 struct ContextTile {Tile tile;int slot=0,abank=0,bbank=0;U ageneration=0,bgeneration=0,group=0;};
 struct ContextABank {
  bool live=false,prefix=false;U generation=0,remaining=0,group=0,bytes=0;
  int batch=0,kk=0;std::vector<std::shared_ptr<Burst>> pending;sc_event released;
 };
 struct ContextBBank {bool live=false;U generation=0;};
 struct ContextBuffer {
  sc_semaphore free;sc_fifo<ContextTile*> ready;
  std::array<ContextABank,2> A;std::array<ContextBBank,2> B;
  ContextBuffer():free(2),ready(2){}
 };
 std::vector<std::unique_ptr<ContextBuffer>> context_buffers;
'''


def generate(out):
    lock=json.loads((HERE/'source.json').read_text(encoding='utf-8'))
    for name,value in lock['base_functional_sha256'].items():
        if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=value:
            raise ValueError('base source drift '+name)
    source=instrument.generate()
    source=replace_once(source,'#include "detail.hpp"','#include "detail.hpp"\n#include "context_detail.hpp"')
    source=replace_once(source,'int buffer_count=2,book_cycles=1;',
        'int buffer_count=2,book_cycles=1,contexts=1,context_switch_cycles=0;bool reuse_A=true;')
    source=replace_once(source,' std::vector<std::unique_ptr<Buffer>> buffers;',
        TYPES+' std::vector<std::unique_ptr<Buffer>> buffers;')
    source=replace_once(source,'buffers.emplace_back(new Buffer(cfg.buffer_count));read(trace);',
        'buffers.emplace_back(new Buffer(cfg.buffer_count));'
        'for(int w=0;w<cfg.mcount;++w)context_buffers.emplace_back(new ContextBuffer);read(trace);')
    source=replace_once(source,'if(argc!=3&&argc!=4)','if(argc!=3&&argc!=4&&argc!=7)')
    source=replace_once(source,'if(argc==4){','if(argc>=4){')
    source=replace_once(source,'Study s("study",c,argv[1]);','''if(argc==7){
  try {
   for(int arg=4;arg<7;++arg){const std::string value=argv[arg];if(value.empty()||!std::all_of(value.begin(),value.end(),[](unsigned char ch){return ch>='0'&&ch<='9';}))throw std::invalid_argument("non-integer context parameter");}
   c.contexts=std::stoi(argv[4]);c.context_switch_cycles=std::stoi(argv[5]);int reuse=std::stoi(argv[6]);
   if((c.contexts!=1&&c.contexts!=2&&c.contexts!=4&&c.contexts!=8&&c.contexts!=16)||
      (c.context_switch_cycles!=0&&c.context_switch_cycles!=1&&c.context_switch_cycles!=3&&c.context_switch_cycles!=8)||
      (reuse!=0&&reuse!=1)){std::cerr<<"invalid context configuration\\n";return 2;}
   c.reuse_A=reuse!=0;
   if(c.contexts>1&&(!c.stream||c.m_mode!=2)){std::cerr<<"contexts require native streaming candidate\\n";return 2;}
  }catch(const std::exception&){std::cerr<<"invalid context argument\\n";return 2;}
 }
 Study s("study",c,argv[1]);''')
    source=replace_once(source,'detail::emit(std::cout,end_ticks,cfg.mcount,cfg.variant);',
        'detail::emit(std::cout,end_ticks,cfg.mcount,cfg.variant);'
        'std::cout<<",\\\"context_study\\\":";'
        'context_detail::emit(std::cout,cfg.contexts,cfg.context_switch_cycles,cfg.reuse_A,cfg.mcount);')
    matrix=(BASE/'matrix.inc').read_text(encoding='utf-8')
    matrix=replace_once(matrix,' void matrix(const Op& o){','#include "context_worker.inc"\n void matrix(const Op& o){')
    matrix=replace_once(matrix,'matrix_worker(o,w,*done[w]);',
        'if(context_target(o)){context_matrix_worker(o,w,*done[w]);}else{matrix_worker(o,w,*done[w]);}')
    for name,text in [('model.cpp',source),('matrix.inc',matrix),
                      ('detail.hpp',(BASE/'detail.hpp').read_text(encoding='utf-8')),
                      ('context_worker.inc',(HERE/'context_worker.inc').read_text(encoding='utf-8')),
                      ('context_detail.hpp',(HERE/'context_detail.hpp').read_text(encoding='utf-8'))]:
        (out/name).write_bytes(text.encode())
    return source
