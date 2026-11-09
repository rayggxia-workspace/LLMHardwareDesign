"""Deterministic, SHA-guarded fork of PR241; no upstream worktree import/edit."""
import argparse
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_SHA = '84aa752da4afaece43947f9ba86e2ab3665b5b8e72dc0a4bbca208b85cffd6e5'


def generate():
    raw = (HERE/'upstream/model.cpp').read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise ValueError('frozen model drift')
    source = raw.decode()

    def change(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('patch anchor not unique: ' + old[:90])
        source = source.replace(old, new)

    change('struct Config {', '#include "detail.hpp"\nstruct Config {')
    change('std::string name;int k=32',
           'std::string name,variant="observe";bool prefix_cache=false,paircols=false,combine=false;'
           'int buffer_count=2,book_cycles=1;int k=32')
    change('std::vector<std::pair<U,U>> slots;U busy=0;',
           'std::vector<std::pair<U,U>> slots;U busy=0,queue_wait=0,calls=0;')
    change('busy+=duration;return start+duration;',
           'busy+=duration;queue_wait+=start-at;++calls;return start+duration;')
    change('Burst(int g,U a,U b,bool w):group(g),address(a),bytes(b),write(w){}',
           'detail::Flow flow;U enqueued;\n'
           '  Burst(int g,U a,U b,bool w,detail::Flow f):group(g),address(a),bytes(b),write(w),flow(f),enqueued(now()){}')
    change('std::shared_ptr<Burst> submit(int g,U address,U bytes,bool write){',
           'std::shared_ptr<Burst> submit(int g,U address,U bytes,bool write,detail::Flow flow=detail::OTHER){')
    change('auto& credit=ch?d1:d0;credit.wait();',
           'auto& credit=ch?d1:d0;U credit_at=now();credit.wait();'
           'detail::data.channels[ch].submit_credit_wait+=now()-credit_at;')
    change('std::make_shared<Burst>(g,address,bytes,write)', 'std::make_shared<Burst>(g,address,bytes,write,flow)')
    change('max_queue,q.num_available()+1);q.write(b.get());return b;',
           'max_queue,q.num_available()+1);U q_at=now();q.write(b.get());'
           'detail::data.channels[ch].submit_queue_wait+=now()-q_at;return b;')
    change('void transfer(int g,U address,U bytes,bool write){\n  if(bytes)await(submit(g,address,bytes,write));',
           'void transfer(int g,U address,U bytes,bool write,detail::Flow flow=detail::OTHER){\n'
           '   if(bytes)await(submit(g,address,bytes,write,flow));')
    change('Burst* b=q.read();++transactions;U final=now();',
           'Burst* b=q.read();++transactions;U final=now();auto& dc=detail::data.channels[channel(b->group)];'
           'dc.queue_wait+=now()-b->enqueued;')
    change('for(U w=0;w<beats;++w){',
           'dc.traffic.add(b->write,b->bytes,beats*cfg.beat);dc.flows[b->flow].add(b->write,b->bytes,beats*cfg.beat);'
           'dc.beats+=beats;\n    for(U w=0;w<beats;++w){')
    change('if(live.size()>=static_cast<size_t>(cfg.credits)){',
           'U before_credit=issue;\n     if(live.size()>=static_cast<size_t>(cfg.credits)){')
    change('if(b->write)issue=store[b->group].reserve',
           'dc.credit_wait+=issue-before_credit;\n     if(b->write)issue=store[b->group].reserve')
    change('row_misses+=miss;row[bank]=r;',
           'dc.bank_wait+=command-issue;dc.row_misses+=miss;row_misses+=miss;row[bank]=r;')
    change('last_direction=b->write;',
           'if(last_direction!=-1&&last_direction!=static_cast<int>(b->write)){++dc.turns;}\n    last_direction=b->write;')
    change('U response=std::max(bus_free,due)+beat_time;',
           'dc.bus_wait+=std::max(bus_free,due)-due;dc.bus_work+=beat_time;'
           'U response=std::max(bus_free,due)+beat_time;')
    change('Buffer():free(2),ready(2){}', 'explicit Buffer(int n):free(n),ready(n){}')
    change('buffers.emplace_back(new Buffer);', 'buffers.emplace_back(new Buffer(cfg.buffer_count));')
    change('mem.transfer(3,tensors[line.tensor].base+line.line*64,64,true);',
           'mem.transfer(3,tensors[line.tensor].base+line.line*64,64,true,detail::U_WRITE);')
    change('mem.transfer(3,tensors[t].base+line*64,64,false);',
           'mem.transfer(3,tensors[t].base+line*64,64,false,detail::U_READ);')
    change('mem.transfer(3,tensors[dest].base+(h*context+context-1)*head*4,head*4,true);',
           'mem.transfer(3,tensors[dest].base+(h*context+context-1)*head*4,head*4,true,detail::KV_WRITE);')
    start = source.index(' void matrix_worker(')
    end = source.index(' void copy(', start)
    source = source[:start] + '#include "matrix.inc"\n' + source[end:]
    change('end_ticks=now();passed=true;',
           'end_ticks=now();detail::validate(mem.logical_read,mem.logical_write,mem.bytes_read,mem.bytes_write,mem.transactions,cfg.mcount);'
           'require(mem.outstanding[0]==0&&mem.outstanding[1]==0,"outstanding ACKs at completion");passed=true;')
    change('std::cout<<"}}\\n";',
           'std::cout<<"},\\\"detail\\\":";'
           'for(size_t i=0;i<store.size();++i){detail::data.s_service[i]=store[i].busy;detail::data.s_wait[i]=store[i].queue_wait;detail::data.s_calls[i]=store[i].calls;}'
           'detail::emit(std::cout,end_ticks,cfg.mcount,cfg.variant);std::cout<<"}\\n";')
    change('if(argc!=3)', 'if(argc!=3&&argc!=4)')
    change('Study s("study",c,argv[1]);', '''if(argc==4){
  c.variant=argv[3];
  if(c.variant=="observe"){}
  else if(c.variant=="prefix")c.prefix_cache=true;
  else if(c.variant=="prefix_slow"){c.prefix_cache=true;c.book_cycles=3;}
  else if(c.variant=="pair")c.paircols=true;
  else if(c.variant=="combine")c.combine=true;
  else if(c.variant=="pair_combine"){c.paircols=true;c.combine=true;}
  else if(c.variant=="prefix_pair_combine"){c.prefix_cache=true;c.paircols=true;c.combine=true;}
  else if(c.variant=="queue_off")c.queued=false;
  else if(c.variant=="buffer1")c.buffer_count=1;
  else if(c.variant=="credits8")c.credits=8;
  else if(c.variant=="k64")c.k=64;
  else if(c.variant=="k128")c.k=128;
  else if(c.variant=="prefix_k64"){c.prefix_cache=true;c.k=64;}
  else if(c.variant=="prefix_k128"){c.prefix_cache=true;c.k=128;}
  else{std::cerr<<"unknown variant\\n";return 2;}
  if(c.variant!="observe"&&(!c.stream||c.m_mode!=2)){std::cerr<<"variant requires native streaming candidate\\n";return 2;}
 }
 Study s("study",c,argv[1]);''')
    return source


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(generate().encode())
