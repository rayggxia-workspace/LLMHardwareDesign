"""Generate a finite shared-A research model over the immutable R4 generator."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def once(source, old, new, count=1):
    if source.count(old) != count:
        raise ValueError('shared-pool anchor count ' + repr(old[:130]) + ' actual=' + str(source.count(old)))
    return source.replace(old, new)

def generate(repo, out, r1_calibration, r2_calibration, r4_calibration):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('shared-pool output must be empty')
    command = [sys.executable, '-B', str(repo/'project/experiments/iterative_speed/round04/generate_round4.py'),
        '--repo', str(repo), '--out', str(out), '--r1-calibration', str(Path(r1_calibration).resolve()),
        '--r2-calibration', str(Path(r2_calibration).resolve()), '--calibration', str(Path(r4_calibration).resolve())]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('frozen R4 generation failed: '+result.stderr)
    previous = json.loads(result.stdout)
    source = (out/'model.cpp').read_text(encoding='utf8')
    source = once(source, 'struct Burst {', '#include "shared_pool.hpp"\nstruct Burst {\n bool pool_fill=false;U pool_offset=0;')
    source = once(source, 'bool write,detail::Flow flow=detail::OTHER){\n  int ch=',
        'bool write,detail::Flow flow=detail::OTHER,bool pool_fill=false,U pool_offset=0){\n  int ch=')
    source = once(source, 'auto b=std::make_shared<Burst>(g,address,bytes,write,flow);',
        'auto b=std::make_shared<Burst>(g,address,bytes,write,flow);b->pool_fill=pool_fill;b->pool_offset=pool_offset;')
    source = once(source, 'U ack=b->write?response:input_store.reserve(response,s_port_duration(cfg,b->group,cfg.beat));', '''U ack;
    if(b->pool_fill){
     require(!b->write,"shared fill must be DDR read");
     const U lo=std::max(a,b->address),hi=std::min(a+U(cfg.beat),b->address+b->bytes);
     require(hi>lo,"empty shared fill beat");
     ack=shared_pool::pool.write(response,b->pool_offset+lo-b->address,hi-lo);
    }else ack=b->write?response:input_store.reserve(response,s_port_duration(cfg,b->group,cfg.beat));''')
    source = once(source, '#include "matrix.inc"', '#include "shared_pool_methods.inc"\n#include "matrix.inc"')
    source = once(source, 'emit_hardware();emit_compare();', 'emit_hardware();shared_pool::pool.emit(std::cout);emit_compare();')
    source = once(source, '&&argc!=14)', '&&argc!=14&&argc!=18)')
    source = once(source, 'if(argc==14){', 'if(argc>=14){')
    source = once(source, 'Study s("study",c,argv[1]);', '''if(argc==18){
  const std::string cap=argv[14],depth=argv[15],delay=argv[16],port=argv[17];
  if((cap!="0"&&cap!="32"&&cap!="48"&&cap!="96")||(depth!="1"&&depth!="2"&&depth!="4"&&depth!="8")||
     (port!="1"&&port!="2"&&port!="4")||delay.empty()||delay.find_first_not_of("0123456789")!=std::string::npos||delay.size()>2||std::stoi(delay)>16){
   std::cerr<<"invalid shared pool parameters\\n";return 2;
  }
  shared_pool::pool.configure(U(std::stoul(cap))*1024,std::stoul(depth),std::stoul(delay),std::stoul(port));
 }
 Study s("study",c,argv[1]);''')
    matrix = (out/'matrix.inc').read_text(encoding='utf8')
    matrix = once(matrix, 'for(int t:o.in)flush(t);', 'for(int t:o.in)flush(t);\n  pool_begin(o);')
    matrix = once(matrix, 'matrix_backed.insert(o.out);', 'shared_pool::pool.end();\n  matrix_backed.insert(o.out);')
    matrix = once(matrix, 'mem.transfer(worker,a.base+(U(batch)*o.rows+rr)*o.k*(a.bits/8),full_a,false,detail::A);',
        'a_load(worker,a.base+(U(batch)*o.rows+rr)*o.k*(a.bits/8),full_a,nullptr);')
    matrix = once(matrix, 'resident_saved+=full_a*(selected_columns.size()-1);',
        'resident_saved+=pool_local_bytes(a.base+(U(batch)*o.rows+rr)*o.k*(a.bits/8),full_a)*(selected_columns.size()-1);')
    matrix = once(matrix, 'for(int row=0;row<r;++row)mem.transfer(worker,\n      a.base+(U(batch)*o.rows+rr+row)*o.k*(a.bits/8),U(cache_k)*(a.bits/8),false,detail::A);',
        '''U local_prefix_bytes=0;
     for(int row=0;row<r;++row){const U address=a.base+(U(batch)*o.rows+rr+row)*o.k*(a.bits/8),bytes=U(cache_k)*(a.bits/8);
      a_load(worker,address,bytes,nullptr);local_prefix_bytes+=pool_local_bytes(address,bytes);}''')
    matrix = once(matrix, 'stats.prefix_loaded+=prefix_bytes;stats.prefix_saved+=prefix_bytes*(selected_columns.size()-1);',
        'stats.prefix_loaded+=local_prefix_bytes;stats.prefix_saved+=local_prefix_bytes*(selected_columns.size()-1);')
    matrix = once(matrix, 'auto load=[&](U address,U bytes,detail::Flow flow){',
        'auto load=[&](U address,U bytes,detail::Flow flow){\n      if(flow==detail::A){a_load(worker,address,bytes,cfg.queued?&pending:nullptr);return;}')
    context = (out/'context_worker.inc').read_text(encoding='utf8')
    context = once(context, '// Native S32/96-bit full-K arithmetic, streaming work and local S reads are\n   // identical to the original worker. Selection is additional service above.',
        '// Native S32/96-bit full-K arithmetic and work counts remain unchanged.\n   // Shared A bypasses its local S read; uncovered A and B retain local service.')
    context = once(context, 'mem.transfer(worker,a.base+U(batch)*o.k*(a.bits/8),prefix_bytes,false,detail::A);',
        'a_load(worker,a.base+U(batch)*o.k*(a.bits/8),prefix_bytes,nullptr);\n     const U local_prefix_bytes=pool_local_bytes(a.base+U(batch)*o.k*(a.bits/8),prefix_bytes);')
    context = once(context, 'stats.prefix_loaded+=prefix_bytes;stats.prefix_saved+=prefix_bytes*(selected.size()-1);',
        'stats.prefix_loaded+=local_prefix_bytes;stats.prefix_saved+=local_prefix_bytes*(selected.size()-1);')
    context = once(context, 'extra.A_loaded_bytes+=prefix_bytes;', 'extra.A_loaded_bytes+=local_prefix_bytes;')
    context = once(context, 'if(cfg.queued)as.pending.push_back(mem.submit(worker,address,abytes,false,detail::A));\n         else mem.transfer(worker,address,abytes,false,detail::A);\n         extra.A_loaded_bytes+=abytes;\n         if(cfg.reuse_A)extra.A_saved_bytes+=abytes*U(count-1);',
        '''a_load(worker,address,abytes,cfg.queued?&as.pending:nullptr);
         const U local_bytes=pool_local_bytes(address,abytes);
         extra.A_loaded_bytes+=local_bytes;
         if(cfg.reuse_A)extra.A_saved_bytes+=local_bytes*U(count-1);''')
    for name, content in [('matrix.inc',matrix),('context_worker.inc',context)]:
        content = once(content, 'U start=now(),send=store[worker].reserve(start,s_port_duration(cfg,worker,p->abytes+p->bbytes));',
            'U start=now(),send=pool_input_service(o,worker,p);')
        content = once(content, 'pause_until(std::max(send,start+std::max(adapt,compute)*C)+tail*C);',
            'const U feed_end=pool_feed(o,worker,p,send);\n   pause_until(std::max(feed_end,std::max(send,start+std::max(adapt,compute)*C))+tail*C);')
        (out/name).write_bytes(content.encode())
    (out/'model.cpp').write_bytes(source.encode())
    for name in ['shared_pool.hpp','shared_pool_methods.inc']:
        (out/name).write_bytes((HERE/name).read_bytes())
    protected = {name:digest for name,digest in previous['generated_sha256'].items() if name not in ('model.cpp','matrix.inc','context_worker.inc')}
    for name,digest in protected.items():
        if sha(out/name)!=digest: raise ValueError('shared pool changed protected source '+name)
    output = dict(scope='shared A SRAM -> finite per-P FIFO -> A feeder conditional timing model',schema=1,
        round4_generated_sha256=previous['generated_sha256'],unchanged_generated_sha256=protected,
        frozen_generator_command=command,R1_calibration=previous['R1_calibration'],R2_calibration=previous['R2_calibration'],R4_calibration=previous['R4_calibration'],
        shared_generator_sources_sha256={name:sha(HERE/name) for name in ['generate_shared_pool.py','shared_pool.hpp','shared_pool_methods.inc']},
        generated_sha256={p.name:sha(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')})
    (out/'generation.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf8')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--r1-calibration',type=Path,required=True);p.add_argument('--r2-calibration',type=Path,required=True);p.add_argument('--r4-calibration',type=Path,required=True)
    a=p.parse_args();print(json.dumps(generate(a.repo,a.out,a.r1_calibration,a.r2_calibration,a.r4_calibration),indent=2))
