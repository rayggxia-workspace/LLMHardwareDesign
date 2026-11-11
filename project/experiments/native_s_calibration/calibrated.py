"""Explicit, switchable corrections to frozen historical timing source.

Native M core costs are measured; guard/frame and whole-system E/N/dynamic M
services remain conditional. This script never changes tensor arithmetic.
"""
from pathlib import Path
import json


def replace(text, old, new):
    assert text.count(old) == 1, old[:120]
    return text.replace(old, new)


def apply(destination):
    root = destination / 'candidate'
    model = root / 'model.cpp'
    text = model.read_text()
    text = replace(text, '#include "detail.hpp"', '#include "native_quantizer_profile.hpp"\n#include "native_dot_profile.hpp"\n#include "ffn_replay_profile.hpp"\n#include "detail.hpp"')
    text = replace(text, '#include "matrix.inc"', '#include "native_s128_service.inc"\n#include "native_projection.inc"\n#include "native_stripe.inc"\n#include "native_dynamic.inc"\n#include "native_s32_dot.inc"\n#include "matrix.inc"')
    text = replace(text, 'read(trace);SC_THREAD(run);', 'ns_initialize();read(trace);SC_THREAD(run);')
    text = replace(text, 'U outstanding[2]={0,0},max_descriptors=0;',
        '''U outstanding[2]={0,0},max_descriptors=0;
 U ns_dot_landing_free[2][3]={},ns_dot_raw_client_free[3]={};
 U ns_dot_landing_peak[2]={},ns_dot_landing_wait=0,ns_dot_landing_bytes=0;''')
    text = replace(text, 'cfg.sq_stripe&&flow==detail::WEIGHT?int((address/2048)%2):channel(g)',
        '(cfg.sq_stripe&&flow==detail::WEIGHT)||(operand_bank==-2&&nv_int("NS_DOT_STAGE64",0))?int((address/2048)%2):channel(g)')
    text = replace(text, 'U issue=std::max(now(),issue_free);',
        '''const U first_offer=now()+((w==0&&b->flow==detail::WEIGHT&&nv_int("NS_M2_FIRST_W_OFFER",0))?C:0);
    U issue=std::max(first_offer,issue_free);''')
    text = replace(text, '}else ack=input_store.reserve(response,s_port_duration(cfg,b->group,cfg.beat));',
        '''}else if(b->operand_bank==-2){
      require(b->flow==detail::A||b->flow==detail::DYNAMIC_B,"typed raw-S staging source");
      require(b->bytes==32||b->bytes==64,"one finite raw64B return slot");
      if(nv_int("NS_DOT_STAGE64",0)){
       // Real stage102473, one held MC aperture/P. Model uses three landing
       // slots/channel and does not release the physical beat credit on capture.
       // Registered capture -> client visible +1, two true S owners with II1.
       // Delayed ACK holds a slot and constrains later same-client dispatch.
       const int ch=b->channel_id,g=b->group;
       require(ch==int((b->address/2048)%2)&&g>=0&&g<3,"typed DMA channel and P ownership");
       auto& slots=ns_dot_landing_free[ch];
       auto at=std::min_element(std::begin(slots),std::end(slots));
       const U captured=std::max(response,*at);
       ns_dot_landing_wait+=captured-response;
       bus_free=std::max(bus_free,captured); // bounded backend-return hold
       const U visible=std::max(captured+C,ns_dot_raw_client_free[g]);
       const bool pressure=nv_int("NS_DOT_STAGE_PRESSURE",0);
       const U fee=ns_dot_profile::stage_release[pressure][b->bytes==64];
       ack=input_store.reserve(visible,fee*C);
       ns_dot_raw_client_free[g]=ack+C;
       *at=ack+C;
       U live=0;for(U available:slots)live+=available>captured;
       ns_dot_landing_peak[ch]=std::max(ns_dot_landing_peak[ch],live);
       ns_dot_landing_bytes+=64;
      }else{
       // Old serial-per-word diagnostic; kept for exact comparison.
       ack=input_store.reserve(response+C,ceildiv(b->bytes,U(16))*3*C);
      }
     }else ack=input_store.reserve(response,s_port_duration(cfg,b->group,cfg.beat));''')
    text = replace(text, 'if(b->write)issue=store[b->group].reserve(issue,s_port_duration(cfg,b->group,cfg.beat));',
        '''if(b->write){
     if(b->operand_bank==-3){
      require(b->flow==detail::DOT_OUTPUT&&b->bytes==32&&beats==1,"typed native S32 export beat");
      issue=store[b->group].reserve(issue+C,6*C); // two true S128 reads, ACK then next request
     }else issue=store[b->group].reserve(issue,s_port_duration(cfg,b->group,cfg.beat));
    }''')
    text = replace(text, 'sx_emit();std::cout<<"}\\n";', 'sx_emit();ns_emit();ns_emit_measured_ffn();std::cout<<"}\\n";')
    text = replace(text, 'try{\n   for(size_t i=0;i<ops.size();)', 'try{\n   if(nv_int("NS_CHECK_QUANT",0)){ns_check_quantizer();passed=true;sc_stop();return;}\n   for(size_t i=0;i<ops.size();)')
    text = replace(text,
        '''read_range(source,offset*(input.bits/8),n*(input.bits/8));
    const U cost=2*ceildiv(n,4)+2;e_work+=cost*C;cycles(cost);sq_quant_values+=n;
    write_range(target,offset*(cfg.sq_abits/8),n*(cfg.sq_abits/8));''',
        '''if(nv_int("NS_QUANT",0)){
     require(n==128,"native quantizer frame size");touch(source,offset*(input.bits/8),n*(input.bits/8),false);
     ns_quantize(3,false);touch(target,offset*(cfg.sq_abits/8),n*(cfg.sq_abits/8),true);sq_quant_values+=n;
    }else{read_range(source,offset*(input.bits/8),n*(input.bits/8));
     const U cost=2*ceildiv(n,4)+2;e_work+=cost*C;cycles(cost);sq_quant_values+=n;
     write_range(target,offset*(cfg.sq_abits/8),n*(cfg.sq_abits/8));}''')
    model.write_text(text, newline='\n')
    (root / 'native_s128_service.inc').write_bytes(Path(__file__).with_name('native_s128_service.inc').read_bytes())
    (root / 'native_projection.inc').write_bytes(Path(__file__).with_name('native_projection.inc').read_bytes())
    (root / 'native_stripe.inc').write_bytes(Path(__file__).with_name('native_stripe.inc').read_bytes())
    (root / 'native_cl_service.inc').write_bytes(Path(__file__).with_name('native_cl_service.inc').read_bytes())
    (root / 'native_dynamic.inc').write_bytes(Path(__file__).with_name('native_dynamic.inc').read_bytes())
    (root / 'native_s32_dot.inc').write_bytes(Path(__file__).with_name('native_s32_dot.inc').read_bytes())
    dot = json.loads(Path(__file__).with_name('fixtures').joinpath('native-s32-fees-102419.json').read_text())
    assert dot['source_job']=='102419' and len(dot['profiles'])==12
    newer = json.loads(Path(__file__).with_name('fixtures').joinpath('native-s32-fees-102444.json').read_text())
    refill = json.loads(Path(__file__).with_name('fixtures').joinpath('native-s32-fees-102510.json').read_text())
    stage = json.loads(Path(__file__).with_name('fixtures').joinpath('native-s32-stage64-102473.json').read_text())
    checkpoint = json.loads(Path(__file__).with_name('fixtures').joinpath('native-s32-s80-102600.json').read_text())
    assert newer['source_job']=='102444' and len(newer['profiles'])==12
    assert refill['source_job']=='102510' and len(refill['profiles'])==12
    assert stage['job']=='102473' and stage['raw_release_cycles'][0]==[5,7]
    assert checkpoint['job']==102600 and checkpoint['trials']==144 and checkpoint['words']==[7,12,22]
    def dot_profile(profile,pressure,layout,rows):
        return next(p for p in profile['profiles'] if (p['pressure'],p['layout'],p['rows'])==(pressure,layout,rows))
    def c_array(values):
        return '{'+','.join(c_array(v) if isinstance(v,list) else str(v) for v in values)+'}'
    ffn = json.loads(Path(__file__).with_name('fixtures').joinpath('ffn-three-p-102563-102564.json').read_text())
    assert ffn['schema']=='paired-three-P-native-FFN/1' and [p['job'] for p in ffn['profiles']]==[102563,102564]
    programmed = json.loads(Path(__file__).with_name('fixtures').joinpath('ffn-programmed-102604-102603.json').read_text())
    assert programmed['schema']=='programmed-three-P-native-FFN/1' and [p['job'] for p in programmed['profiles']]==[102604,102603]
    ffn_profiles = ffn['profiles']+programmed['profiles']
    phases = []
    for profile in ffn_profiles:
        assert len(profile['trials'])==36
        current = []
        for mode in (0,1):
            rows=[r for r in profile['trials'] if r['mode']==mode]
            assert len(rows)==18
            ordered=sorted(rows,key=lambda r:(r['gate']+r['down'],r['seed'],r['initial']))
            current.append([[r['gate'],r['down'],r['seed'],r['initial']] for r in (rows[0],ordered[len(ordered)//2])])
        phases.append(current)
    (root / 'ffn_replay_profile.hpp').write_text('#pragma once\nnamespace ns_ffn_profile {\n'
        +'constexpr int jobs[]='+c_array([p['job'] for p in ffn_profiles])+';\n'
        +'constexpr int count=sizeof(jobs)/sizeof(jobs[0]);\n'
        +'constexpr int phases[count][2][2][4]='+c_array(phases)+';\n'
        +'constexpr int program[count][3]='+c_array([[p.get('program',{}).get(k,0) for k in ('calls','confirmed_reads','confirmed_writes')]
                                                  for p in ffn_profiles])+';\n}\n',newline='\n')
    def table(profile,field):
        return [[[dot_profile(profile,pressure,layout,rows)[field] if field=='begin_cycles' else
                  [f['cycles'] for f in dot_profile(profile,pressure,layout,rows)['frames']]
                  for rows in (1,2,4)] for layout in ('N-major','K-major')] for pressure in (False,True)]
    (root / 'native_dot_profile.hpp').write_text('#pragma once\nnamespace ns_dot_profile {\n'
        +'constexpr int begin[3][2][2][3]='+c_array([table(p,'begin_cycles') for p in (dot,newer,refill)])+';\n'
        +'constexpr int chunks[3][2][2][3][5]='+c_array([table(p,'frames') for p in (dot,newer,refill)])+';\n'
        +'constexpr int stage_release[2][2]='+c_array(stage['raw_release_cycles'])+';\n'
        +'constexpr int checkpoint[2][3][2]='+c_array(checkpoint['command_to_terminal_max_in_audited_trace'])+';\n}\n',newline='\n')
    quant = json.loads(Path(__file__).with_name('fixtures').joinpath('quantizer-102168.json').read_text())
    header = '#pragma once\n#include <vector>\nnamespace ns_quant_profile {\n'
    for frame in quant['frames']:
        name = 'known' if frame['known_producer_shift'] else 'fallback'
        header += 'const std::vector<U> '+name+'_requests{'+','.join(str(t['request_offset']) for t in frame['transactions'])+'};\n'
        header += 'const std::vector<U> '+name+'_writes{'+','.join(str(t['write']) for t in frame['transactions'])+'};\n'
    (root / 'native_quantizer_profile.hpp').write_text(header+'}\n', newline='\n')
    matrix = root / 'matrix.inc'
    text = matrix.read_text()
    text = replace(text,
                   'if(context_target(o)){context_matrix_worker(o,w,*done[w]);}else{matrix_worker(o,w,*done[w]);}',
                   'if(ns_dot_target(o)){ns_dot_worker(o,w,*done[w]);}else if(ns_dynamic_target(o)){ns_dynamic_worker(o,w,*done[w]);}else if(ns_target(o)){ns_matrix_worker(o,w,*done[w]);}else if(context_target(o)){context_matrix_worker(o,w,*done[w]);}else{matrix_worker(o,w,*done[w]);}')
    matrix.write_text(text, newline='\n')
    closure = root / 'closure_service.inc'
    text = closure.read_text()
    text = replace(text,
        'return (U(1)<<42)+U(weight)*(U(1)<<31)+(U(col/8)*(full_k/128)+U(kk/128))*record_bytes;',
        '''const U groups=tensors[weight].elements/U(full_k)/8;
  const U index=nv_int("NS_WEIGHT_LAYOUT",0)?U(kk/128)*groups+U(col/8):U(col/8)*(full_k/128)+U(kk/128);
  return (U(1)<<42)+U(weight)*(U(1)<<31)+index*record_bytes;''')
    text = replace(text, 'void cl_wave_worker(const std::vector<CLJob>& jobs,int worker){',
        'void cl_wave_worker(const std::vector<CLJob>& jobs,int worker){\n  if(nv_int("NS_PRODUCT",0)){ns_cl_wave_worker(jobs,worker);return;}')
    text = replace(text, 'void cl_ffn(size_t i){', 'void cl_ffn(size_t i){\n  if(nv_int("NS_NATIVE",0)>=4){ns_ffn_striped(i);return;}')
    text = replace(text,
        'b.free.wait();int bank=0;',
        '''b.free.wait();
    if(nv_int("NS_EARLY_W",0)){ns_buffers[worker]->record_free.wait();++ns_record_live[worker];
     ns_record_peak=std::max(ns_record_peak,ns_record_live[worker]);}
    int bank=0;''')
    text = replace(text,
        'const U start=now();U consumed=mem.weight_store',
        '''const bool early_W=nv_int("NS_EARLY_W",0)!=0;
   if(early_W){ns_buffers[worker]->command_free.wait();++ns_cl_results[worker];
    ns_result_peak=std::max(ns_result_peak,ns_cl_results[worker]);require(ns_cl_results[worker]<=2,"CL finite result ownership");}
   const U start=now();U consumed=mem.weight_store''')
    text = replace(text,
        'consumed=std::max(consumed,start+8*C);pause_until(consumed);',
        '''consumed=std::max(consumed,start+8*C);
   if(early_W){sc_spawn([&,t,consumed,this]{
    pause_until(consumed+C); // actual native M final-input ACK, exec+9
    require(b.live[t->bank]&&b.generation[t->bank]==t->generation,"CL early W identity");
    b.live[t->bank]=false;b.free.post();b.released.notify(SC_ZERO_TIME);
   });}
   pause_until(consumed);''')
    text = replace(text,
        '''sc_spawn([&,t,ack,this]{pause_until(ack);require(b.live[t->bank]&&b.generation[t->bank]==t->generation,"CL output ownership");
    b.live[t->bank]=false;b.free.post();b.released.notify(SC_ZERO_TIME);delete t;});''',
        '''sc_spawn([&,t,ack,early_W,this]{pause_until(ack);
    if(!early_W){require(b.live[t->bank]&&b.generation[t->bank]==t->generation,"CL output ownership");
     b.live[t->bank]=false;b.free.post();b.released.notify(SC_ZERO_TIME);
    }else{cycles(2);require(ns_cl_results[worker]>0,"CL orphan result terminal");
     --ns_cl_results[worker];ns_buffers[worker]->command_free.post();
     require(ns_record_live[worker]>0,"CL orphan record ticket");--ns_record_live[worker];ns_buffers[worker]->record_free.post();
     ns_cl_drain[worker].notify(SC_ZERO_TIME);}
    delete t;});''')
    text = replace(text,
        'require(producer.terminated(),"CL producer incomplete");',
        'while(ns_cl_results[worker])wait(ns_cl_drain[worker]);\n  require(producer.terminated(),"CL producer incomplete");')
    text = replace(text,
        'for(U off=0;off<2048;off+=128){read_range(gate.in[0],off*4,512);cycles(66);sio(3,256);if(sx_early())sx_early_valid(off/128);}',
        '''for(U off=0;off<2048;off+=128){
   if(nv_int("NS_QUANT",0)){touch(gate.in[0],off*4,512,false);ns_quantize(3,false);}
   else{read_range(gate.in[0],off*4,512);cycles(66);sio(3,256);}
   if(sx_early())sx_early_valid(off/128);
  }''')
    text = replace(text,
        'sio(0,nv_mid()==1?1536:2048);cycles(67+(nv_mid()==1?1:0));\n    cl_G_values+=128;cl_G_cycles+=67+(nv_mid()==1?1:0);',
        '''if(nv_int("NS_NATIVE",0)>=1){
     // Measured native G+single S128 frontend: 96B registers; 64 reads/32
     // writes, final true ACK at cycle107, clocked LC take at108. RNE to
     // stored Mid32 is already included. This replaces, not adds to 68.
     pause_until(store[0].reserve(now(),108*C));
    }else{sio(0,nv_mid()==1?1536:2048);cycles(67+(nv_mid()==1?1:0));}
    cl_G_values+=128;cl_G_cycles+=nv_int("NS_NATIVE",0)>=1?68:67+(nv_mid()==1?1:0);''')
    closure.write_text(text+'\n#include "native_cl_service.inc"\n', newline='\n')
    shared = root / 'shared_x_service.inc'
    text = shared.read_text()
    text = replace(text,
        'U ready=store[worker].reserve(now(),(ceildiv(U(256),U(sx_local_width()))+sx_local_latency()+sx_phase_cycles())*C);\n   pause_until(ready);',
        '''U ready=0;
   if(nv_int("NS_NATIVE",0)>=2){
    // Admit a second LOAD only once the first LOAD has completed. Two data
    // tiles still overlap M replay; there is ONE shared inflight S request.
    cycles(2);
    for(int word=0;word<16;++word){auto reply=ns_S_request(worker,now());pause_until(reply.ack);if(word!=15)cycles(2);}
    cycles(2);ready=now();
   }else{ready=store[worker].reserve(now(),(ceildiv(U(256),U(sx_local_width()))+sx_local_latency()+sx_phase_cycles())*C);}
   pause_until(ready);''')
    text = replace(text,
        'sx_x_valid.fill(false);sx_copy_workers.clear();\n  for(int worker=0;worker<3;++worker)',
        '''sx_x_valid.fill(false);sx_copy_workers.clear();
  if(nv_int("NS_NATIVE",0)>=2){
   sx_copy_workers.push_back(sc_spawn([this]{
    U next_request=now()+2*C,last_ACK=0;
    for(int chunk=0;chunk<16;++chunk){
     while(!sx_x_valid[chunk])wait(sx_x_valid_event);
     for(int word=0;word<16;++word){
      // One actual U128 source request, a response may wait in the existing
      // provider until all three finite16B destination holds have drained.
      const U source_end=store[3].reserve(std::max(now(),next_request),C);
      pause_until(std::max(source_end+C,last_ACK?last_ACK+C:U(0)));sx_copy_source_B+=16;
      U all_ACK=0;
      for(int p=0;p<3;++p){
       const U link_end=cl_links[p].reserve(now(),C);cl_link_bytes+=16;
       const U destination_ACK=store[p].reserve(link_end,C)+C;
       all_ACK=std::max(all_ACK,destination_ACK);sx_copy_dest_B+=16;
      }
      last_ACK=all_ACK;next_request=now()+2*C;
     }
    }
    pause_until(last_ACK);cycles(2); // committed prefix, done assertion/take
   }));
   return;
  }
  for(int worker=0;worker<3;++worker)''')
    shared.write_text(text, newline='\n')
