"""An isolated extension of #247 R4. Frozen generators are never rewritten."""
from pathlib import Path
import shutil


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('nonunique extension anchor: ' + old[:100])
    return text.replace(old, new)


SERVICE = r'''
 U sq_weight_read_bytes=0,sq_weight_write_bytes=0,sq_quant_values=0;
 std::map<int,int> sq_quantized;U sq_quant_base=U(1)<<39;
 Op sq_lower(const Op& original){
  Op lowered=original;
  if(!cfg.sq_abits||!cfg.sq_alower||original.layout!=0||original.rows!=1)return lowered;
  const int source=original.in[0];auto found=sq_quantized.find(source);
  if(found==sq_quantized.end()){
   const Tensor input=tensors[source];const int target=static_cast<int>(tensors.size());
   const U nbytes=ceildiv(input.elements*cfg.sq_abits,8);
   tensors.push_back(Tensor{input.elements,sq_quant_base,cfg.sq_abits,false});last_use.push_back(-1);
   sq_quant_base+=ceildiv(nbytes,1024)*1024+4096;
   // Two passes establish one common activation scale over the whole K row.
   // Reduction and conversion use the same finite U cache/port and E candidate.
   for(U offset=0;offset<input.elements;offset+=64){
    const U n=std::min<U>(64,input.elements-offset);read_range(source,offset*(input.bits/8),n*(input.bits/8));
    const U cost=ceildiv(n,4)+5;e_work+=cost*C;cycles(cost);
   }
   for(U offset=0;offset<input.elements;offset+=64){
    const U n=std::min<U>(64,input.elements-offset);read_range(source,offset*(input.bits/8),n*(input.bits/8));
    const U cost=ceildiv(n,4)*3+5;e_work+=cost*C;cycles(cost);sq_quant_values+=n;
    write_range(target,offset*(cfg.sq_abits/8),n*(cfg.sq_abits/8));
   }
   flush(target);matrix_backed.insert(target);sq_quantized[source]=target;found=sq_quantized.find(source);
  }
  lowered.in[0]=found->second;return lowered;
 }
 int sq_cache_tensor=-1,sq_keep=0,sq_saved_k=0,sq_saved_contexts=0;
 U sq_cache_bytes=0,sq_saved_pbytes=0,sq_cache_hit_bytes=0,sq_plan_ops=0;
 bool sq_plan_initialized=false,sq_planned=false;std::ifstream sq_plan;
 bool sq_A_skip(const Op& o,U address,U bytes){
  if(o.in[0]!=sq_cache_tensor)return false;
  const auto& t=tensors[o.in[0]];
  if(address<t.base||bytes>sq_cache_bytes||address-t.base>sq_cache_bytes-bytes)return false;
  sq_cache_hit_bytes+=bytes;return true;
 }
 void sq_begin(const Op& o){
  if(!sq_plan_initialized){
   sq_plan_initialized=true;const char* path=std::getenv("SQ_PLAN");
   if(path){sq_plan.open(path);require(bool(sq_plan),"missing SQ plan");sq_planned=true;}
  }
  if(!sq_planned)return;
  int k,ctx,keep;sq_plan>>k>>ctx>>keep;
  require(bool(sq_plan)&&(k==64||k==128||k==256)&&(ctx==1||ctx==8)&&keep>=0&&keep<=2,"invalid SQ plan action");
  sq_saved_k=cfg.k;sq_saved_contexts=cfg.contexts;sq_saved_pbytes=cfg.pbytes;
  cfg.k=k;cfg.contexts=ctx;sq_keep=keep;
  if(sq_cache_tensor!=o.in[0]){
   require(sq_cache_bytes<cfg.pbytes,"persistent cache exceeds S");cfg.pbytes-=sq_cache_bytes;
  }
  ++sq_plan_ops;
 }
 void sq_end(const Op& o){
  if(!sq_planned)return;
  if(sq_keep==0){sq_cache_tensor=-1;sq_cache_bytes=0;}
  if(sq_keep==2){
   const U bytes=size(o.in[0]);
   require(o.layout==0&&o.rows==1&&o.batches==1&&bytes+2*ceildiv(U(8)*cfg.k,64)*64+1632<=cfg.pbytes,"cannot retain nonresident A");
   sq_cache_tensor=o.in[0];sq_cache_bytes=bytes;
  }
  if(sq_keep)cycles(1); // explicit retention descriptor service
  cfg.k=sq_saved_k;cfg.contexts=sq_saved_contexts;cfg.pbytes=sq_saved_pbytes;
 }
 void sq_service(const Op& o,Tile* p,int worker){
  const bool weight=o.layout==0;
  const bool direct=cfg.sq_direct&&weight;
  const bool quant=cfg.sq_abits&&weight&&o.rows==1;
  if(quant&&!cfg.sq_alower){
   // Requantization is an explicit candidate, NOT bitwise legacy S32 semantics.
   // Raw A remains S32 in DDR/S. A finite 16-element conversion register feeds M.
   const U count=U(p->r)*p->k;
   sq_quant_values+=count;
   cycles(ceildiv(count,4)*3); // four-lane scale/RNE/clamp candidate, not RTL-qualified
  }
  U start=now();
  U send=store[worker].reserve(start,s_port_duration(cfg,worker,p->abytes+(direct?0:p->bbytes)));
  if(direct){
   require(p->bank>=0&&p->bank<2,"operand bank id");
   send=std::max(send,mem.weight_store[2*worker+p->bank].reserve(start,ceildiv(p->bbytes,cfg.sq_bread)*C));
   sq_weight_read_bytes+=p->bbytes;
  }
  const U adapt=std::max(ceildiv(p->abytes,32),ceildiv(p->bbytes,direct?cfg.sq_bread:64));
  const U compute=U(p->r)*ceildiv(p->k,quant?cfg.sq_core_k:8);
  const U tail=4+(p->ki==0?14:0)+(p->last?8+ceildiv(U(p->r)*p->n,4)*2:0);
  adapter_work+=adapt*C;m_work+=(compute+tail)*C;++m_tiles;++m_commands;
  pause_until(std::max(send,start+std::max(adapt,compute)*C)+tail*C);
 }
'''

ENV = r'''
 auto sq_integer=[](const char* name,int fallback){
  const char* value=std::getenv(name);if(!value)return fallback;
  const std::string s=value;
  if(s.empty()||!std::all_of(s.begin(),s.end(),[](unsigned char ch){return ch>='0'&&ch<='9';}))throw std::invalid_argument(name);
  return std::stoi(s);
 };
 try{
  c.sq_direct=sq_integer("SQ_DIRECT",0);c.sq_abits=sq_integer("SQ_ABITS",0);c.sq_alower=sq_integer("SQ_ALOWER",1);
  c.sq_bread=sq_integer("SQ_BREAD",64);c.sq_core_k=sq_integer("SQ_CORE_K",16);
  const int bw=sq_integer("SQ_BW_MB",17100),pc=sq_integer("SQ_PCOUNT",2),beat=sq_integer("SQ_BEAT",64);
  if((c.sq_direct!=0&&c.sq_direct!=1)||(c.sq_abits!=0&&c.sq_abits!=8&&c.sq_abits!=16)||
    (c.sq_bread!=64&&c.sq_bread!=128)||(c.sq_core_k!=8&&c.sq_core_k!=16)||(c.sq_alower!=0&&c.sq_alower!=1)||
    (bw!=17100&&bw!=51200&&bw!=102400)||(pc!=2&&pc!=3)||(beat!=64&&beat!=256)||c.weight_bits!=8)
    throw std::invalid_argument("unsupported SQ resource or precision contract");
  c.bandwidth=double(bw)*1e6;c.mcount=pc;c.beat=beat;
 }catch(const std::exception& e){std::cerr<<"invalid SQ configuration "<<e.what()<<"\n";return 2;}
'''


def generate(baseline, out):
    baseline, out = Path(baseline), Path(out)
    shutil.copytree(baseline, out)
    model = (out / 'model.cpp').read_text(encoding='utf8')
    model = once(model, '#include <systemc>', '#include <systemc>\n#include <cstdlib>')
    model = once(model, 'struct Config {', 'struct Config {\n int sq_direct=0,sq_abits=0,sq_bread=64,sq_core_k=16,sq_alower=1;')
    model = once(model, 'int group;U address,bytes;', 'int group;int operand_bank=-1;U address,bytes;')
    model = once(model, 'U max_live=0,max_queue=0,bus_work=0;',
                 'U max_live=0,max_queue=0,bus_work=0,sq_direct_bytes=0;std::array<Calendar,6> weight_store;')
    for method in ('submit', 'transfer'):
        start = model.index(' ' + ('std::shared_ptr<Burst> ' if method == 'submit' else 'void ') + method + '(')
        end = model.index('{', start)
        signature = model[start:end]
        model = once(model, signature, signature.replace('detail::OTHER)', 'detail::OTHER,int operand_bank=-1)'))
    model = once(model, 'auto b=std::make_shared<Burst>(g,address,bytes,write,flow);',
                 'auto b=std::make_shared<Burst>(g,address,bytes,write,flow);b->operand_bank=operand_bank;')
    model = once(model, 'await(submit(g,address,bytes,write,flow));', 'await(submit(g,address,bytes,write,flow,operand_bank));')
    model = once(model, 'U ack=b->write?response:input_store.reserve(response,s_port_duration(cfg,b->group,cfg.beat));', r'''U ack=response;
    if(!b->write){
     if(cfg.sq_direct&&b->flow==detail::WEIGHT){
      require(b->operand_bank>=0&&b->operand_bank<2,"weight DMA missing operand ownership");
      ack=weight_store[2*b->group+b->operand_bank].reserve(response,ceildiv(cfg.beat,64)*C);
      sq_direct_bytes+=cfg.beat;
     }else ack=input_store.reserve(response,s_port_duration(cfg,b->group,cfg.beat));
    }''')
    model = once(model, ' void run(){', SERVICE + '\n void run(){')
    model = once(model, 'if(o.kind=="Dot"){matrix(o);++i;}',
                 'if(o.kind=="Dot"){const Op lowered=sq_lower(o);matrix(lowered);++i;}')
    model = once(model, 'Study s("study",c,argv[1]);', ENV + '\n Study s("study",c,argv[1]);')
    model = once(model, 'iteration4::emit_all(std::cout,cfg.iteration1_nexp,cfg.iteration2_nexp,cfg.iteration4_nexp);',
                 r'''iteration4::emit_all(std::cout,cfg.iteration1_nexp,cfg.iteration2_nexp,cfg.iteration4_nexp);
    std::cout<<",\"sq_study\":{\"direct\":"<<cfg.sq_direct<<",\"activation_bits\":"<<cfg.sq_abits
      <<",\"weight_read_B_cycle\":"<<cfg.sq_bread<<",\"core_K\":"<<cfg.sq_core_k
      <<",\"direct_weight_bus_bytes\":"<<mem.sq_direct_bytes<<",\"weight_bank_read_bytes\":"<<sq_weight_read_bytes
      <<",\"requantized_values\":"<<sq_quant_values<<",\"lowered_activation_objects\":"<<sq_quantized.size()<<",\"persistent_A_hit_bytes\":"<<sq_cache_hit_bytes<<",\"plan_operations\":"<<sq_plan_ops
      <<",\"conversion_register_bytes_per_P\":"<<(cfg.sq_abits?16*cfg.sq_abits/8:0)
      <<",\"native_full_model_tokens_per_second\":null,\"quality_verified\":false}";''')
    (out / 'model.cpp').write_bytes(model.encode())
    for name in ('matrix.inc', 'context_worker.inc'):
        text = (out / name).read_text(encoding='utf8')
        if name == 'matrix.inc':
            text = once(text, 'const auto& a=tensors[o.in[0]];const auto& b=', 'const auto& a=tensors[o.in[0]];const auto& b=')
            text = once(text, 'auto load=[&](U address,U bytes,detail::Flow flow){',
                        'auto load=[&](U address,U bytes,detail::Flow flow){\n      if(flow==detail::A&&sq_A_skip(o,address,bytes))return;')
            text = once(text, 'mem.transfer(worker,a.base+(U(batch)*o.rows+rr)*o.k*(a.bits/8),full_a,false,detail::A);',
                        'if(!sq_A_skip(o,a.base+(U(batch)*o.rows+rr)*o.k*(a.bits/8),full_a))mem.transfer(worker,a.base+(U(batch)*o.rows+rr)*o.k*(a.bits/8),full_a,false,detail::A);')
            text = once(text, 'for(int row=0;row<r;++row)mem.transfer(worker,', 'for(int row=0;row<r;++row)if(!sq_A_skip(o,a.base+(U(batch)*o.rows+rr+row)*o.k*(a.bits/8),U(cache_k)*(a.bits/8)))mem.transfer(worker,')
            text = once(text, ' void matrix(const Op& o){', ' void matrix(const Op& o){\n  sq_begin(o);')
            text = once(text, 'cfg.queued=previous_queued;mem.cfg.queued=previous_queued;',
                        'cfg.queued=previous_queued;mem.cfg.queued=previous_queued;sq_end(o);')
            text = once(text, 'mem.submit(worker,address,bytes,false,flow)',
                        'mem.submit(worker,address,bytes,false,flow,flow==detail::WEIGHT?seq%2:-1)')
            text = once(text, 'mem.transfer(worker,address,bytes,false,flow)',
                        'mem.transfer(worker,address,bytes,false,flow,flow==detail::WEIGHT?seq%2:-1)')
        else:
            for method in ('submit', 'transfer'):
                text = once(text, 'mem.'+method+'(worker,address,bbytes,false,detail::WEIGHT)',
                            'mem.'+method+'(worker,address,bbytes,false,detail::WEIGHT,bbank)')
        begin = text.index('U start=now(),send=store[worker].reserve(')
        end = text.index('pause_until(', begin)
        end = text.index(';', end) + 1
        text = text[:begin] + 'sq_service(o,p,worker);' + text[end:]
        (out / name).write_bytes(text.encode())
    return out
