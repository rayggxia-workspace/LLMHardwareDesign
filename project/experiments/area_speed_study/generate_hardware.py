"""SHA-bound independent P-port, P-count and vector-lane sensitivities."""
import hashlib
import json
from pathlib import Path

from generate import generate, HERE, BASE, replace_once


HARDWARE_RECEIPT=r'''
 void p_result_store(int group,U bytes){
  auto& port=(cfg.split_P_ports&&group<cfg.mcount)?write_store[group]:store[group];
  if(bytes)pause_until(port.reserve(now(),ceildiv(bytes,cfg.swidth)*cfg.slat*C));
 }
 void emit_hardware(){
  std::cout<<",\"hardware_study\":{\"P_count\":"<<cfg.mcount
   <<",\"P_S_bytes\":16384,\"U_S_bytes\":16384,\"total_private_S_bytes\":"<<U(cfg.mcount+1)*16384
   <<",\"aggregate_bandwidth_B_s\":"<<cfg.bandwidth
   <<",\"S_port_bytes\":"<<cfg.swidth<<",\"S_port_cycles\":"<<cfg.slat<<",\"DDR_beat_bytes\":"<<cfg.beat
   <<",\"split_P_read_write_ports\":"<<(cfg.split_P_ports?"true":"false")
   <<",\"vector_lanes\":"<<cfg.vector_lanes
   <<",\"scope\":\"conditional extra P 1R1W port / third native-S32 P / wider vector pipe; no physical or numeric qualification\""
   <<",\"port_contract\":\"P store is read-or-unified; split P DMA input and M-result writes use write_store; DMA output reads and M supply keep store; U3 stays unified; each port retains original width and latency\""
   <<",\"P_ports\":[";
  for(int i=0;i<cfg.mcount;++i){if(i)std::cout<<",";
   std::cout<<"{\"worker\":"<<i<<",\"DDR_channel\":"<<mem.channel(i)
    <<",\"read_or_unified_service_subcycles\":"<<store[i].busy
    <<",\"read_or_unified_wait_subcycles\":"<<store[i].queue_wait
    <<",\"read_or_unified_reservations\":"<<store[i].calls
    <<",\"write_service_subcycles\":"<<write_store[i].busy
    <<",\"write_wait_subcycles\":"<<write_store[i].queue_wait
    <<",\"write_reservations\":"<<write_store[i].calls<<"}";
  }
  std::cout<<"],\"U_service_subcycles\":"<<store[3].busy
   <<",\"U_wait_subcycles\":"<<store[3].queue_wait
   <<",\"U_reservations\":"<<store[3].calls<<"}";
 }
'''


def verify_sources():
    lock=json.loads((HERE/'source.json').read_text(encoding='utf-8'))
    for field in ('hardware_base_sha256','hardware_source_sha256'):
        if not lock.get(field):raise ValueError('missing source lock '+field)
        for name,value in lock[field].items():
            if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=value:
                raise ValueError('hardware source drift '+name)
    return lock


def generate_hardware(out,pcount=2,dual=False,lanes=4):
    """Defaults preserve all stage1 behavior, adding only hardware_study JSON."""
    if pcount not in (2,3) or not isinstance(dual,bool) or lanes not in (4,8,16):
        raise ValueError('invalid hardware contract')
    verify_sources()
    source=generate(out)
    source=replace_once(source,'struct Config {',
        'struct Config {\n int vector_lanes=4;bool split_P_ports=false;')
    source=replace_once(source,'sc_fifo<Burst*> q0,q1;std::vector<Calendar>& store;',
        'sc_fifo<Burst*> q0,q1;std::vector<Calendar>& store;std::vector<Calendar>& write_store;')
    source=replace_once(source,
        'Memory(sc_module_name n,Config c,std::vector<Calendar>& s):sc_module(n),cfg(c),q0(32),q1(32),store(s),d0(32),d1(32){',
        'Memory(sc_module_name n,Config c,std::vector<Calendar>& s,std::vector<Calendar>& w):sc_module(n),cfg(c),q0(32),q1(32),store(s),write_store(w),d0(32),d1(32){')
    source=replace_once(source,'std::vector<Calendar> store;Memory mem;',
        'std::vector<Calendar> store,write_store;Memory mem;')
    source=replace_once(source,'cfg(c),store(4),mem("memory",c,store){',
        'cfg(c),store(4),write_store(4),mem("memory",c,store,write_store){')
    source=replace_once(source,
        'U ack=b->write?response:store[b->group].reserve(response,ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C);',
        'auto& input_store=(cfg.split_P_ports&&b->group<cfg.mcount)?write_store[b->group]:store[b->group];'
        'U ack=b->write?response:input_store.reserve(response,ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C);')
    # Change only the two vector-pipeline arithmetic packet counts. Scalar NExp,
    # reductions, S transfers, non-vecpipe arithmetic and all M costs stay fixed.
    source=replace_once(source,
        'cfg.vecpipe?(ceildiv(n,4)+5)*micro:ceildiv(n,4)*cfg.ewise*micro',
        'cfg.vecpipe?(ceildiv(n,cfg.vector_lanes)+5)*micro:ceildiv(n,4)*cfg.ewise*micro')
    source=replace_once(source,
        'U packets=ceildiv(n,4),cost=cfg.vecpipe?packets+5:packets*cfg.ewise;',
        'U packets=ceildiv(n,4),cost=cfg.vecpipe?ceildiv(n,cfg.vector_lanes)+5:packets*cfg.ewise;')
    source=replace_once(source,' void run(){',HARDWARE_RECEIPT+' void run(){')
    source=replace_once(source,
        'context_detail::emit(std::cout,cfg.contexts,cfg.context_switch_cycles,cfg.reuse_A,cfg.mcount);',
        'context_detail::emit(std::cout,cfg.contexts,cfg.context_switch_cycles,cfg.reuse_A,cfg.mcount);emit_hardware();')
    source=replace_once(source,'Study s("study",c,argv[1]);',
        f'c.mcount={pcount};c.split_P_ports={str(dual).lower()};c.vector_lanes={lanes};'
        'Study s("study",c,argv[1]);')
    # The original output sio is a local M-result write, followed by a DMA read
    # of that result. Route only the former to the extra write port. U accesses
    # continue using the unchanged generic sio(3,...).
    for name in ('matrix.inc','context_worker.inc'):
        path=out/name
        text=replace_once(path.read_text(encoding='utf-8'),
            'U bytes=U(p->r)*p->n*4;sio(worker,bytes);',
            'U bytes=U(p->r)*p->n*4;p_result_store(worker,bytes);')
        path.write_bytes(text.encode())
    (out/'model.cpp').write_bytes(source.encode())
    return source
