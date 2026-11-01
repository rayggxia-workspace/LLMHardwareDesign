#include "Vtxn_ctrl.h"
#include "verilated.h"
#include <array>
#include <iostream>
#include <stdexcept>
#include <random>
static void ck(bool b,const char*s){if(!b)throw std::runtime_error(s);}
struct Context{bool valid=false,role=false;uint32_t owner=0,epoch=0,pos=0;};
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);Vtxn_ctrl d;std::array<Context,24>contexts;bool active=false,aborting=false,failed=false,computed=false;unsigned current=0;uint32_t writes=0;std::mt19937_64 rng(157804);uint64_t checks=0;
 auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();};
 auto reset=[&](){d.reset=1;d.cmd_valid=0;d.rsp_ready=0;tick();d.reset=0;tick();contexts={};active=aborting=failed=computed=false;current=0;writes=0;};reset();
 auto command=[&](unsigned op,unsigned ctx,uint32_t own,uint32_t epoch,uint32_t pos,uint32_t next,bool idle){
  d.cmd_op=op;d.cmd_context=ctx;d.cmd_owner=own;d.cmd_epoch=epoch;d.cmd_position=pos;d.cmd_next=next;d.dma_idle=idle;d.cmd_valid=1;ck(d.cmd_ready,"txn input unavailable");bool error=ctx>=24;std::array<uint32_t,4>data{};
  if(!error){auto&c=contexts[ctx];bool id=c.valid&&c.owner==own&&c.epoch==epoch&&c.pos==pos;
   switch(op){
    case 0:error=active||!idle||own==0;if(!error)c={true,false,own,epoch,pos};break;
    case 1:error=active||!idle||!id;if(!error){active=true;current=ctx;aborting=failed=computed=false;writes=0;}break;
    case 2:error=!active||aborting||current!=ctx||writes==UINT32_MAX;if(!error)++writes;break;
    case 3:error=!active||current!=ctx||!writes;if(!error){--writes;if(aborting&&!writes){active=false;aborting=false;}}break;
    case 4:error=!active||aborting||current!=ctx;if(!error){computed=true;failed|=next&1;}break;
    case 5:error=!active||current!=ctx;if(!error){if(!writes){active=false;aborting=false;}else aborting=true;}break;
    case 6:error=!active||aborting||failed||!computed||writes||!id||current!=ctx||c.epoch==UINT32_MAX;if(!error){c.role=!c.role;++c.epoch;c.pos=next;active=false;}break;
    case 7:error=!c.valid;if(!error)data={uint32_t(c.role),c.epoch,c.pos,c.owner};break;
    default:error=true;
   }
  }
  tick();d.cmd_valid=0;ck(d.rsp_valid,"txn response missing");ck(bool(d.rsp_error)==error,"txn error mismatch");for(unsigned i=0;i<4;++i)ck(d.rsp_data[i]==data[i],"txn response data");ck(bool(d.pending)==active&&d.outstanding==writes&&bool(d.published_role)==contexts[current].role,"txn publication state");checks+=8;
  for(unsigned i=0;i<next%3;++i){tick();ck(d.rsp_valid,"txn held response");}
  d.rsp_ready=1;tick();d.rsp_ready=0;
 };
 // Directed late write/abort, failed commit, wrong identity, reset drain, epoch limit.
 for(unsigned ctx=0;ctx<24;++ctx){command(0,ctx,ctx+1,0,17,0,true);command(1,ctx,ctx+1,0,17,0,true);command(2,ctx,ctx+1,0,17,0,false);command(4,ctx,ctx+1,0,17,0,false);command(6,ctx,ctx+1,0,17,18,false);command(5,ctx,ctx+1,0,17,0,false);command(1,ctx,ctx+1,0,17,0,false);command(3,ctx,ctx+1,0,17,0,false);command(1,ctx,ctx+1,0,17,0,true);command(4,ctx,ctx+1,0,17,0,true);command(6,ctx,ctx+2,0,17,18,true);command(6,ctx,ctx+1,0,17,18,true);command(7,ctx,0,0,0,0,true);}
 reset();command(0,0,1,UINT32_MAX,17,0,true);command(1,0,1,UINT32_MAX,17,0,true);command(4,0,1,UINT32_MAX,17,0,true);command(6,0,1,UINT32_MAX,17,18,true);command(5,0,0,0,0,0,true);reset();command(0,0,1,0,0,0,false);
 for(unsigned t=0;t<20000;++t){if(t%1973==0)reset();unsigned ctx=rng()%32,op=rng()%16;uint32_t own=rng()%25,ep=rng()%3,pos=rng()%20;if(ctx<24&&t%2==0){own=contexts[ctx].owner;ep=contexts[ctx].epoch;pos=contexts[ctx].pos;}command(op,ctx,own,ep,pos,uint32_t(rng()),rng()%4!=0);}
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"random_commands\":20000}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
