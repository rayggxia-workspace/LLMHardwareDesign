// Binary functional oracle using the same pinned integer N/G reference engines
// already compared against native RTL. No cycle or RTL system qualification.
#include "n.hpp"
#include "g.hpp"
#include <iostream>
#include <vector>
#include <stdexcept>
using namespace blocks;
template<class T> void read_values(T* p,size_t n){
 if(!std::cin.read(reinterpret_cast<char*>(p),sizeof(T)*n))throw std::runtime_error("short input");
}
int main(){try{
 uint32_t head[3];
 while(std::cin.read(reinterpret_cast<char*>(head),sizeof(head))){
  const unsigned kind=head[0],n=head[1],parameter=head[2];
  if(n==0||n>65535)throw std::runtime_error("invalid vector length");
  std::vector<int16_t> x(n),gamma(n),out(n);read_values(x.data(),n);
  if(kind==0)read_values(gamma.data(),n);
  if(kind==2){GEngine g;
   for(unsigned j=0;j<n;j+=2){GCommand c;c.function=GCommand::Function(parameter);
    for(unsigned i=0;i<2&&j+i<n;++i)c.x[i]=x[j+i];
    auto r=g.execute(c);if(r.error)throw std::runtime_error("G error");
    for(unsigned i=0;i<2&&j+i<n;++i)out[j+i]=int16_t(r.lane[i]);}
  }else if(kind==4||kind==6){
   NEngine engine;NCommand c;c.mode=kind==4?NCommand::Mode::RMS:NCommand::Mode::L2;c.epsilon=parameter;engine.execute(c);
   for(unsigned j=0;j<n;j+=8){c=NCommand{};c.op=NCommand::Op::Stats;c.count=std::min(8u,n-j);
    for(unsigned i=0;i<c.count;++i)c.data[i]=uint16_t(x[j+i]);
    engine.execute(c);}
   c=NCommand{};c.op=NCommand::Op::Finalize;auto r=engine.execute(c);if(r.error)throw std::runtime_error("factor finalize");
   c=NCommand{};c.op=NCommand::Op::ReadFactor;r=engine.execute(c);if(r.error)throw std::runtime_error("factor read");
   uint32_t factor=uint32_t(r.lane[0]);std::cout.write(reinterpret_cast<char*>(&factor),4);std::cout.flush();continue;
  }else if(kind==3||kind==5){
   std::vector<uint32_t> wide(n);
   for(unsigned j=0;j<n;++j){NEngine engine;NCommand c;engine.execute(c);
    c.op=NCommand::Op::Stats;c.count=2;c.data[0]=uint16_t(x[j]);c.data[1]=0;engine.execute(c);
    c=NCommand{};c.op=NCommand::Op::Finalize;engine.execute(c);
    c=NCommand{};c.op=NCommand::Op::Exp;c.count=1;c.data[0]=uint16_t(x[j]);auto r=engine.execute(c);
    if(r.error)throw std::runtime_error("N relative EXP error");
    // E op13 can reinterpret the U16 response as a positive S32 slot,
    // then RNE-right-shift by one into signed Q1.14.
    out[j]=int16_t(rne(Wide(r.lane[0]),1));
    wide[j]=uint32_t(r.lane[0]);
   }
   if(kind==5){std::cout.write(reinterpret_cast<char*>(wide.data()),wide.size()*4);std::cout.flush();continue;}
  }else if(kind<=1){NEngine engine;NCommand c;
   auto execute=[&](NCommand command){auto r=engine.execute(command);if(r.error)throw std::runtime_error("N error");return r;};
   c.mode=kind==0?NCommand::Mode::RMS:NCommand::Mode::Softmax;c.epsilon=parameter;execute(c);
   for(unsigned j=0;j<n;j+=8){c=NCommand{};c.op=NCommand::Op::Stats;c.count=std::min(8u,n-j);
    for(unsigned i=0;i<c.count;++i)c.data[i]=uint16_t(x[j+i]);
    execute(c);}
   c=NCommand{};c.op=NCommand::Op::Finalize;execute(c);
   std::vector<uint16_t> exps(n);
   if(kind==1){for(unsigned j=0;j<n;j+=8){c=NCommand{};c.op=NCommand::Op::Exp;c.count=std::min(8u,n-j);
     for(unsigned i=0;i<c.count;++i)c.data[i]=uint16_t(x[j+i]);
     auto r=execute(c);
     for(unsigned i=0;i<c.count;++i)exps[j+i]=uint16_t(r.lane[i]);}
    c=NCommand{};c.op=NCommand::Op::FinishExp;execute(c);}
   for(unsigned j=0;j<n;j+=8){c=NCommand{};c.op=kind==0?NCommand::Op::NormReplay:NCommand::Op::SoftReplay;c.count=std::min(8u,n-j);
    for(unsigned i=0;i<c.count;++i){c.data[i]=kind==0?uint16_t(x[j+i]):exps[j+i];c.gamma[i]=gamma[j+i];}
    auto r=execute(c);for(unsigned i=0;i<c.count;++i)out[j+i]=int16_t(r.lane[i]);}
  }else throw std::runtime_error("unknown request");
  std::cout.write(reinterpret_cast<char*>(out.data()),out.size()*sizeof(int16_t));std::cout.flush();
 }
 return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
