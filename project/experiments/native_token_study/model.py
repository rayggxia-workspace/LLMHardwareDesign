"""Generate an isolated conditional native-P / frozen-candidate-U SystemC model."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('native token source anchor: '+repr(old[:100]))
    return text.replace(old,new,1)


def generate(repo,out):
    repo,out=Path(repo).resolve(),Path(out).resolve()
    spec=importlib.util.spec_from_file_location('frozen_p_dma_instrument',repo/'project/experiments/p_dma_study/instrument.py')
    instrument=importlib.util.module_from_spec(spec);spec.loader.exec_module(instrument)
    source=instrument.generate()
    source=once(source,'#include "detail.hpp"','#include "detail.hpp"\n#include "native_contract.hpp"')
    source=once(source,'struct Config {','struct Config {\n bool native_context=false;int native_contexts=1;')
    # Real native P ordinary ingress/egress is 128 bit, one finite external
    # transaction at a time. U retains the frozen 64-byte candidate service.
    old='if(b->write)issue=store[b->group].reserve(issue,ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C);'
    new='''if(b->write)issue=store[b->group].reserve(issue,b->group<2?native_model::dma_service(b->group,b->address,b->bytes,w,cfg.beat,true):ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C);'''
    source=once(source,old,new)
    source=once(source,'store[b->group].reserve(response,ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C)',
        'store[b->group].reserve(response,b->group<2?native_model::dma_service(b->group,b->address,b->bytes,w,cfg.beat,false):ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C)')
    source=once(source,'live.push(ack);',
        'if(b->group<2&&!b->write)bus_free=std::max(bus_free,ack); // one finite64B RX buffer, conservative return backpressure\n    live.push(ack);')
    source=once(source,'read(trace);SC_THREAD(run);',
        'read(trace);for(const auto& op:ops)if(op.kind!="Dot")++native_model::non_Dot_candidate_ops;SC_THREAD(run);')
    source=once(source,'#include "matrix.inc"','#include "native_worker.inc"')
    source=once(source,'detail::emit(std::cout,end_ticks,cfg.mcount,cfg.variant);',
        'detail::emit(std::cout,end_ticks,cfg.mcount,cfg.variant);native_model::emit(std::cout,cfg.native_context,cfg.native_contexts,cfg.weight_bits);')
    source=source[:source.index('int sc_main(')]+r'''
int sc_main(int argc,char**argv){
 if(argc!=3){std::cerr<<"usage: model TRACE native_legacy_w8|native_legacy_w16|native_ctx8_w8|native_ctx8_w16|native_ctx1_w8|native_ctx1_w16\n";return 2;}
 sc_set_time_resolution(1,SC_PS);Config c;c.name=argv[2];
 const std::string name=argv[2];
 if(name=="native_legacy_w8"||name=="native_legacy_w16"){}
 else if(name=="native_ctx8_w8"||name=="native_ctx8_w16"){c.native_context=true;c.native_contexts=8;}
 else if(name=="native_ctx1_w8"||name=="native_ctx1_w16"){c.native_context=true;c.native_contexts=1;}
 else{std::cerr<<"invalid native timing profile\n";return 2;}
 c.weight_bits=name.substr(name.size()-3)=="w16"?16:8;
 c.k=32;c.mcount=2;c.credits=32;c.slat=1;c.swidth=64;c.beat=64;c.bandwidth=17.1e9;
 c.m_mode=2;c.stream=false;c.resident=true;c.queued=true;c.vecpipe=true;c.variant="native_serial_controller";
 Study s("study",c,argv[1]);sc_start();return s.passed?0:1;
}
'''
    # A conditional number must not masquerade under the original generic key.
    source=source.replace('tokens_per_second', 'conditional_tokens_per_second')
    out.mkdir(parents=True,exist_ok=False)
    (out/'model.cpp').write_bytes(source.encode())
    for name in ('native_contract.hpp','native_worker.inc'):
        (out/name).write_bytes((HERE/name).read_bytes())
    (out/'detail.hpp').write_bytes((repo/'project/experiments/p_dma_study/detail.hpp').read_bytes())
    result=dict(clock_hz=300000000,source_sha256={p.relative_to(repo).as_posix():sha(p) for p in (
        repo/'project/experiments/p_dma_study/instrument.py',repo/'project/experiments/p_dma_study/upstream/model.cpp',
        repo/'project/experiments/p_dma_study/detail.hpp',repo/'project/rtl/block_v2/block_v2_m.sv',
        repo/'project/rtl/block_v2/block_v2_m_context.sv')},
        study_sha256={p.name:sha(p) for p in (HERE/'model.py',HERE/'native_contract.hpp',HERE/'native_worker.inc',HERE/'contract.json')},
        generated_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()},
        qualification='Conditional native P timing + unimplemented paid adapter + frozen candidate U; not actual generation')
    (out/'generation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(generate(a.repo,a.out)))
