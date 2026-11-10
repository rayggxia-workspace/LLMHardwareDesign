"""State/timing ablations only; never change the frozen generator or RTL.

Release 0: original output-ACK/input-bank coupling. 1: after M service.
Release 2: after S/B reads AND adapter/core input consumption, before fixed tail.
Accumulator/result ownership is deliberately not released by these callbacks.
"""
from pathlib import Path
from generate import once


def extend(folder):
    folder = Path(folder)
    p = folder/'model.cpp'
    s = p.read_text()
    s = once(s, '#include <cstdlib>', '#include <cstdlib>\n#include <functional>')
    s = once(s, 'int sq_direct=0,', 'int bn_release=0;\n int sq_direct=0,')
    s = once(s, 'c.sq_direct=sq_integer(', 'c.bn_release=sq_integer("BN_RELEASE",0);\n  if(c.bn_release<0||c.bn_release>2)throw std::invalid_argument("BN_RELEASE");\n  c.sq_direct=sq_integer(')
    s = once(s, 'void sq_service(const Op& o,Tile* p,int worker){',
             'void sq_service(const Op& o,Tile* p,int worker,const std::function<void()>& release={}){')
    s = once(s, 'pause_until(std::max(send,start+std::max(adapt,compute)*C)+tail*C);',
             'const U consumed=std::max(send,start+std::max(adapt,compute)*C);\n'
             '  const U finish=consumed+tail*C;\n'
             '  if(cfg.bn_release==2){require(bool(release),"missing input release");pause_until(consumed);release();}\n'
             '  pause_until(finish);')
    p.write_bytes(s.encode())
    p = folder/'matrix.inc';s = p.read_text()
    s = once(s, '   before=now();\n   const int abits=',
             '   bool released=false;auto release=[&]{require(!released,"duplicate input release");released=true;buffer.free.post();};\n'
             '   before=now();\n   const int abits=')
    s = once(s, 'sq_service(o,p,worker);', 'sq_service(o,p,worker,release);\n    if(cfg.bn_release==1)release();')
    s = once(s, 'stats.output+=now()-before;buffer.free.post();delete p;',
             'stats.output+=now()-before;if(cfg.bn_release==0)release();require(released,"input bank leak");delete p;')
    p.write_bytes(s.encode())
    p = folder/'context_worker.inc';s = p.read_text()
    begin = s.index('   require(as.live&&as.generation==task->ageneration&&as.remaining>0,"A release tag mismatch");')
    end = s.index('delete task;', begin)
    release = s[begin:end]
    s = s[:begin]+'   if(cfg.bn_release==0){release();}\n   require(released,"context input leak");'+s[end:]
    s = once(s, '   before=now();++extra.context_switches;',
             '   bool released=false;auto release=[&]{require(!released,"duplicate context input release");released=true;\n'+release+'\n   };\n'
             '   before=now();++extra.context_switches;')
    s = once(s, 'sq_service(o,p,worker);', 'sq_service(o,p,worker,release);\n   if(cfg.bn_release==1)release();')
    p.write_bytes(s.encode())
    return folder
