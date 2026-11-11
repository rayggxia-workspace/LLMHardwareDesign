#define SC_INCLUDE_DYNAMIC_PROCESSES
#include <systemc>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
#include <memory>
#include <queue>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
using namespace sc_core;
using U=uint64_t;
constexpr U C=1000; // 1000 abstract subcycle units per core cycle.
U now(){return sc_time_stamp().value();}
U ceildiv(U a,U b){return (a+b-1)/b;}
void pause_until(U t){if(t>now())wait(sc_time::from_value(t-now()));}
void cycles(U n){if(n)wait(sc_time::from_value(n*C));}
void require(bool v,const char* s){if(!v)throw std::runtime_error(s);}

struct Config {
 std::string name;int k=32,credits=4,beat=16,swidth=16,slat=3,ewise=6,m_mode=0,weight_bits=16,mcount=2;
 bool fuse=true,stream=false,resident=false,queued=false,vecpipe=false;double bandwidth=16e9;
};
struct Tensor{U elements,base;int bits;bool initial;};
struct Op{int out;std::string kind;U elements;int rows,cols,k,batches,shift,layout;std::vector<int> in;};
struct Calendar {
 std::vector<std::pair<U,U>> slots;U busy=0;
 U reserve(U at,U duration){
  auto z=std::remove_if(slots.begin(),slots.end(),[](auto p){return p.second<=now();});slots.erase(z,slots.end());
  U start=at;size_t i=0;
  for(;i<slots.size();++i){if(start+duration<=slots[i].first)break;start=std::max(start,slots[i].second);}
  slots.insert(slots.begin()+static_cast<long>(i),{start,start+duration});busy+=duration;return start+duration;
 }
};
struct Burst {
 int group;U address,bytes;bool write;sc_event done;bool complete=false;
 Burst(int g,U a,U b,bool w):group(g),address(a),bytes(b),write(w){}
};
struct Memory:sc_module {
 Config cfg;sc_fifo<Burst*> q0,q1;std::vector<Calendar>& store;
 sc_semaphore d0,d1;U outstanding[2]={0,0},max_descriptors=0;
 U bytes_read=0,bytes_write=0,logical_read=0,logical_write=0,transactions=0,row_misses=0;
 U max_live=0,max_queue=0,bus_work=0;
 Memory(sc_module_name n,Config c,std::vector<Calendar>& s):sc_module(n),cfg(c),q0(32),q1(32),store(s),d0(32),d1(32){SC_THREAD(channel0);SC_THREAD(channel1);}
 int channel(int group)const{return group==0?0:group==1?1:group==2?0:1;}
 std::shared_ptr<Burst> submit(int g,U address,U bytes,bool write){
  int ch=channel(g);auto& credit=ch?d1:d0;credit.wait();
  auto b=std::make_shared<Burst>(g,address,bytes,write);auto& q=ch?q1:q0;
  max_descriptors=std::max(max_descriptors,++outstanding[ch]);
  max_queue=std::max<U>(max_queue,q.num_available()+1);q.write(b.get());return b;
 }
 void await(const std::shared_ptr<Burst>& b){while(!b->complete)wait(b->done);}
 void transfer(int g,U address,U bytes,bool write){
  if(bytes)await(submit(g,address,bytes,write));
 }
 void retire(Burst* b,U final){
  pause_until(final);int ch=channel(b->group);--outstanding[ch];(ch?d1:d0).post();b->complete=true;b->done.notify(SC_ZERO_TIME);
 }
 void channel0(){serve(q0);}
 void channel1(){serve(q1);}
 void serve(sc_fifo<Burst*>& q){
  U issue_free=0,bus_free=0;std::vector<U> bank_free(4,0);std::vector<int64_t> row(4,-1);
  std::priority_queue<U,std::vector<U>,std::greater<U>> live;int last_direction=-1;
  const U beat_time=static_cast<U>(std::ceil(cfg.beat*300e6*C/(cfg.bandwidth/2)));
  while(true){
   Burst* b=q.read();++transactions;U final=now();
   const U beats=ceildiv((b->address%cfg.beat)+b->bytes,cfg.beat);
   if(b->write){logical_write+=b->bytes;bytes_write+=beats*cfg.beat;}else{logical_read+=b->bytes;bytes_read+=beats*cfg.beat;}
   for(U w=0;w<beats;++w){
    U issue=std::max(now(),issue_free);
    while(!live.empty()&&live.top()<=issue)live.pop();
    if(live.size()>=static_cast<size_t>(cfg.credits)){
     issue=std::max(issue,live.top());while(!live.empty()&&live.top()<=issue)live.pop();
    }
    if(b->write)issue=store[b->group].reserve(issue,ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C);
    U a=(b->address/cfg.beat+w)*cfg.beat;int bank=(a/64)%4;int64_t r=a/1024;
    U command=std::max(issue,bank_free[bank]);bool miss=row[bank]!=r;
    row_misses+=miss;row[bank]=r;bank_free[bank]=command+1200;
    U due=command+12000+(miss?3600:0);
    if(last_direction!=-1&&last_direction!=static_cast<int>(b->write))bus_free+=2400;
    last_direction=b->write;
    U response=std::max(bus_free,due)+beat_time;bus_free=response;bus_work+=beat_time;
    U ack=b->write?response:store[b->group].reserve(response,ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C);
    live.push(ack);max_live=std::max<U>(max_live,live.size());require(live.size()<=static_cast<size_t>(cfg.credits),"credit overflow");
    final=std::max(final,ack);issue_free=issue+C;
   }
   // Each queued descriptor retires only after all its data/S-write ACKs.
   // Requests inside a burst overlap up to the declared finite credit.
   if(cfg.queued)sc_spawn([this,b,final]{retire(b,final);});
   else retire(b,final);
  }
 }
};
struct Line {int tensor;U line,stamp;bool dirty;};

struct Study:sc_module {
 struct Tile {int r,n,k,batch,row,col,ki,bank;bool last;U abytes,bbytes;std::vector<std::shared_ptr<Burst>> pending;};
 struct Buffer {sc_semaphore free;sc_fifo<Tile*> ready;Buffer():free(2),ready(2){}};
 std::vector<std::unique_ptr<Buffer>> buffers;
 Config cfg;std::vector<Tensor> tensors;std::vector<Op> ops;int tokens=0;
 std::vector<Calendar> store;Memory mem;std::map<std::pair<int,int>,int> m_ticks;bool rtl_profile=false;
 std::map<std::pair<int,U>,Line> cache;U stamp=0,cache_peak=0,cache_hits=0,cache_misses=0,cache_spills=0,discarded=0;
 std::vector<int> last_use;std::set<std::pair<int,U>> backing;std::set<int> matrix_backed;
 U m_commands=0,m_work=0,e_work=0,adapter_work=0,m_tiles=0,scratch_peak=0,kv_write=0,resident_saved=0;
 std::map<std::string,U> spans;U end_ticks=0;bool passed=false;
 Study(sc_module_name n,Config c,const std::string& trace):sc_module(n),cfg(c),store(4),mem("memory",c,store){for(int w=0;w<cfg.mcount;++w)buffers.emplace_back(new Buffer);read(trace);SC_THREAD(run);}
 void read(const std::string& path){
  std::ifstream f(path);size_t nt,no;f>>nt>>no>>tokens;require(bool(f),"bad trace header");tensors.resize(nt);
  U base=4096;
  for(size_t i=0;i<nt;++i){int id,init;U elements;int bits;f>>id>>elements>>bits>>init;require(id==static_cast<int>(i),"tensor ID mismatch");
   tensors[i]={elements,base,bits,init!=0};base+=ceildiv(elements*bits,8*1024)*1024+4096;
  }
  for(size_t i=0;i<no;++i){Op o;int ni;f>>o.out>>o.kind>>o.elements>>o.rows>>o.cols>>o.k>>o.batches>>o.shift>>o.layout>>ni;for(int j=0;j<ni;++j){int v;f>>v;require(v>=0&&v<o.out,"non-topological input");o.in.push_back(v);}ops.push_back(o);}
   require(bool(f),"truncated trace");last_use.assign(nt,-1);
  for(auto& o:ops)if(o.kind=="Constant")tensors[o.out].initial=true;
  for(size_t i=0;i<ops.size();++i)for(int x:ops[i].in)last_use[x]=static_cast<int>(i);
  std::ifstream p("m-profile.log");std::string s;
  while(std::getline(p,s)){int r,k,t;if(sscanf(s.c_str(),"M_PROFILE rows=%d k=%d ticks=%d",&r,&k,&t)==3)m_ticks[{r,k}]=t;}
  rtl_profile=m_ticks.count({1,1})&&m_ticks.count({2,32});
  if(!rtl_profile&&cfg.m_mode!=2)throw std::runtime_error("native M timing profile missing; run RTL bench first");
 }
 U size(int t)const{return ceildiv(tensors[t].elements*tensors[t].bits,8);}
 void sio(int group,U bytes){if(bytes)pause_until(store[group].reserve(now(),ceildiv(bytes,cfg.swidth)*cfg.slat*C));}
 void remove_line(std::map<std::pair<int,U>,Line>::iterator it,bool discard=false){
  auto line=it->second;if(line.dirty&&!discard){mem.transfer(3,tensors[line.tensor].base+line.line*64,64,true);backing.insert({line.tensor,line.line});++cache_spills;}
  if(discard)++discarded;
  cache.erase(it);
 }
 void touch(int t,U offset,U bytes,bool write){
  if(!bytes)return;
  require(offset+bytes<=size(t)+15,"tensor access out of bounds");
  U first=offset/64,last=(offset+bytes-1)/64;
  for(U line=first;line<=last;++line){auto key=std::make_pair(t,line);auto it=cache.find(key);
   if(it==cache.end()){
    while(cache.size()>=192){auto victim=std::min_element(cache.begin(),cache.end(),[](auto a,auto b){return a.second.stamp<b.second.stamp;});remove_line(victim);}
    if(!write){require(tensors[t].initial||matrix_backed.count(t)||backing.count({t,line}),"read before producer write/ACK");mem.transfer(3,tensors[t].base+line*64,64,false);++cache_misses;}
    it=cache.emplace(key,Line{t,line,++stamp,write}).first;
   }else{++cache_hits;it->second.stamp=++stamp;if(write)it->second.dirty=true;}
   cache_peak=std::max<U>(cache_peak,cache.size()*64);require(cache.size()*64+4096<=16384,"U private S overflow");
  }
 }
 void read_range(int t,U offset,U bytes){touch(t,offset,bytes,false);sio(3,bytes);}
 void write_range(int t,U offset,U bytes){sio(3,bytes);touch(t,offset,bytes,true);}
 void discard_range(int t,U offset,U bytes){
  if(!bytes)return;
  U a=offset/64,b=(offset+bytes-1)/64;
  for(U l=a;l<=b;++l){auto it=cache.find({t,l});if(it!=cache.end())remove_line(it,true);}
 }
 void flush(int t){for(auto it=cache.begin();it!=cache.end();){if(it->first.first!=t){++it;continue;}auto cur=it++;remove_line(cur);}}
 void flush_all(){while(!cache.empty())remove_line(cache.begin());}
 static bool elementwise(const Op& o){return o.kind=="Add"||o.kind=="Sub"||o.kind=="Product"||o.kind=="Convert"||o.kind=="Compare"||o.kind=="Select"||o.kind=="Maximum"||o.kind=="Minimum"||o.kind=="MaskZero"||o.kind=="MaskFloor"||o.kind=="Mask";}
 void canonical(const Op& o,size_t index){
  // Explicit candidate local services for structural decode projections.
  // Each micro-op costs an E32 packet, and intermediate S accesses count.
  const U micro=o.kind=="SiLU"?41:o.kind=="RoPE"?3:128;
  for(U off=0;off<o.elements;off+=64){U n=std::min<U>(64,o.elements-off);
   int input=o.in[0];read_range(input,off*(tensors[input].bits/8),n*(tensors[input].bits/8));
   if(o.in.size()>1){int t=o.in[1];U take=std::min<U>(n,tensors[t].elements);read_range(t,0,take*(tensors[t].bits/8));}
   U cost=cfg.vecpipe?(ceildiv(n,4)+5)*micro:ceildiv(n,4)*cfg.ewise*micro;e_work+=cost*C;cycles(cost);
   // Candidate 16 packet contexts hold dependent intermediates locally.
   // Input/output remain in S; internal register area must be implemented.
   if(!cfg.vecpipe)sio(3,(micro-1)*n*4*3);
   write_range(o.out,off*4,n*4);
   if(last_use[input]==static_cast<int>(index))discard_range(input,off*(tensors[input].bits/8),n*(tensors[input].bits/8));
  }
 }
 void kv_store(const Op& o){
  require(o.in.size()==4,"KV write contract");
  const U head=128,heads=2,context=o.k;
  for(int which=0;which<2;++which){int input=o.in[which],dest=o.in[which+2];
   require(tensors[input].elements==head*heads&&tensors[dest].elements==head*heads*context,"KV extent mismatch");
   for(U h=0;h<heads;++h){read_range(input,h*head*4,head*4);
    mem.transfer(3,tensors[dest].base+(h*context+context-1)*head*4,head*4,true);kv_write+=head*4;
   }
  }
 }
 void vector_region(size_t begin,size_t end){
  const U count=ops[begin].elements;
  for(U offset=0;offset<count;offset+=64){U n=std::min<U>(64,count-offset);
   for(size_t i=begin;i<end;++i){const auto& o=ops[i];if(o.kind=="Constant")continue;
    for(int t:o.in){U total=tensors[t].elements;U b=tensors[t].bits/8;U start=total==1?0:offset%total;U take=std::min<U>(n,total-start);read_range(t,start*b,take*b);if(take<n&&total>1)read_range(t,0,std::min<U>(n-take,total)*b);}
    U packets=ceildiv(n,4),cost=cfg.vecpipe?packets+5:packets*cfg.ewise;e_work+=cost*C;cycles(cost);
    write_range(o.out,offset*(tensors[o.out].bits/8),n*(tensors[o.out].bits/8));
    for(int t:o.in)if(last_use[t]==static_cast<int>(i)&&(tensors[t].elements==count||offset+n==count)){
     U b=tensors[t].bits/8;discard_range(t,tensors[t].elements==count?offset*b:0,std::min<U>(n,tensors[t].elements)*b);
    }
   }
  }
 }
 void reduce(const Op& o,size_t index){
  require(!o.in.empty(),"reduction input missing");int input=o.in[0];U total=tensors[input].elements;
  for(U offset=0;offset<total;offset+=64){U n=std::min<U>(64,total-offset);read_range(input,offset*(tensors[input].bits/8),n*(tensors[input].bits/8));
   U cost=o.kind=="NFactor"?n*6:ceildiv(n,4)*cfg.ewise;e_work+=cost*C;cycles(cost);
   if(last_use[input]==static_cast<int>(index))discard_range(input,offset*(tensors[input].bits/8),n*(tensors[input].bits/8));
  }
  U tail=o.elements*(o.kind=="NFactor"?64:3);e_work+=tail*C;cycles(tail);write_range(o.out,0,size(o.out));
 }
 void matrix_worker(const Op& o,int worker,sc_event& done){
  auto& buffer=*buffers[worker];
  const int row_limit=8;
  auto producer=sc_spawn([&,this]{int seq=0;
   for(int batch=0;batch<o.batches;++batch)for(int rr=0;rr<o.rows;rr+=row_limit){
    int r=std::min(row_limit,o.rows-rr);
    const auto& a=tensors[o.in[0]];const auto& b=tensors[o.in[1]];int bbits=o.layout==0?cfg.weight_bits:b.bits;
    int cap=(16384-U(r)*8*12-1024)/(2*(r*(a.bits/8)+8*(bbits/8)));
    int limit=std::min(cfg.k,std::max(8,(cap/8)*8));
    const U full_a=U(r)*o.k*(a.bits/8);
    if(cfg.resident&&full_a+U(r)*8*12+1024<16384){
     int resident_cap=(16384-full_a-U(r)*8*12-1024)/(2*8*(bbits/8));
     if(resident_cap>=8)limit=std::min(limit,(resident_cap/8)*8);
    }
    bool resident=cfg.resident&&worker*8<o.cols&&full_a+2*ceildiv(U(8)*limit*bbits/8,cfg.beat)*cfg.beat+U(r)*8*12+1024<=16384;
    if(cfg.resident){buffer.free.wait();buffer.free.wait();buffer.free.post();buffer.free.post();}
    if(resident){
     mem.transfer(worker,a.base+(U(batch)*o.rows+rr)*o.k*(a.bits/8),full_a,false);
     U columns=ceildiv(o.cols-worker*8,cfg.mcount*8);
     resident_saved+=full_a*(columns-1);
    }
    for(int col=worker*8;col<o.cols;col+=cfg.mcount*8){int n=std::min(8,o.cols-col);
    for(int kk=0;kk<o.k;kk+=limit){buffer.free.wait();int k=std::min(limit,o.k-kk);
     std::vector<std::shared_ptr<Burst>> pending;
     auto load=[&](U address,U bytes){
      if(cfg.queued)pending.push_back(mem.submit(worker,address,bytes,false));
      else mem.transfer(worker,address,bytes,false);
     };
     U abytes=ceildiv(U(r)*k*a.bits,8),bbytes=ceildiv(U(n)*k*bbits,8);
     U scratch=2*(ceildiv(abytes,cfg.beat)*cfg.beat+ceildiv(bbytes,cfg.beat)*cfg.beat)+U(r)*n*12+1024;
     if(resident)scratch=full_a+2*ceildiv(bbytes,cfg.beat)*cfg.beat+U(r)*n*12+1024;
     scratch_peak=std::max(scratch_peak,scratch);require(scratch<=16384,"P private S overflow");
     // Activations are runtime strided rows. Every row is an actual burst.
     if(!resident)for(int row=0;row<r;++row)load(a.base+(U(batch)*o.rows+rr+row)*o.k*(a.bits/8)+U(kk)*(a.bits/8),U(k)*(a.bits/8));
     if(o.layout==0){
      U addr=b.base+(U(batch)*o.cols*o.k+U(col)*o.k+U(kk)*n)*bbits/8;
      load(addr,bbytes); // immutable B tiled offline
     }else if(o.layout==1){
      for(int c=0;c<n;++c)load(b.base+(U(batch)*o.cols*o.k+U(col+c)*o.k+kk)*(bbits/8),U(k)*(bbits/8));
     }else{
      for(int row=0;row<k;++row)load(b.base+(U(batch)*o.k*o.cols+U(kk+row)*o.cols+col)*(bbits/8),U(n)*(bbits/8));
     }
     buffer.ready.write(new Tile{r,n,k,batch,rr,col,kk,seq++%2,kk+k==o.k,abytes,bbytes,std::move(pending)});
    }
   }}buffer.ready.write(nullptr);
  });
  while(true){Tile* p=buffer.ready.read();if(!p)break;
   for(auto& request:p->pending)mem.await(request);
   const int abits=tensors[o.in[0]].bits,bbits=o.layout==0?cfg.weight_bits:tensors[o.in[1]].bits;
   // Explicit P-local pack/transpose adapter, bounded by the S reservation.
   // A candidate 96-bit P-local combiner keeps full-K partials. Existing
   // M alone does not provide the proposed S32xS32 accumulation contract.
   int ac=abits==32?3:1,bc=bbits==32?3:1;
   if(cfg.m_mode==2)ac=bc=1; // candidate native S32xS16/S32 service
   if(cfg.stream){
    // Candidate native S32 accumulator, A256/B512 ports, full-K context.
    // S reads, packing and MAC execute as a finite streaming pipeline.
    U start=now(),send=store[worker].reserve(start,ceildiv(p->abytes+p->bbytes,cfg.swidth)*cfg.slat*C);
    U adapt=std::max(ceildiv(p->abytes,32),ceildiv(p->bbytes,64));
    U compute=U(p->r)*ceildiv(p->k,8);
    U tail=4+(p->ki==0?14:0)+(p->last?8+ceildiv(U(p->r)*p->n,4)*2:0);
    adapter_work+=adapt*C;m_work+=(compute+tail)*C;++m_tiles;++m_commands;
    pause_until(std::max(send,start+std::max(adapt,compute)*C)+tail*C);
   }else{
   sio(worker,p->abytes+p->bbytes);
   U adapt=ceildiv(p->abytes+p->bbytes,16);adapter_work+=adapt*C;cycles(adapt);
   int kt=p->k<=1?1:p->k<=8?8:32;
   int native=m_ticks.count({p->r,kt})?m_ticks.at({p->r,kt}):p->r*((kt+7)/8)*9+14+p->r;
   int issue_groups=((abits==8?1:3)*(bbits==8?1:3));
   if(cfg.m_mode==1)issue_groups=1;
   if(cfg.m_mode==2)native=14+p->r*((p->k+7)/8)+p->r;
   else if(issue_groups!=9)native=14+p->r*((p->k+7)/8)*issue_groups+p->r;
   U ticks=U(ac)*bc*(native+1+ceildiv(U(p->r)*p->k,8)+ceildiv(U(p->r)*p->n,2)*2);
   m_commands+=U(ac)*bc;m_work+=ticks*C;++m_tiles;cycles(ticks);
   U merge=U(ac)*bc*ceildiv(U(p->r)*p->n,4)*3;
   adapter_work+=merge*C;cycles(merge);sio(worker,U(p->r)*p->n*12*2);
   }
   if(p->last){U output=U(p->r)*p->n*4;sio(worker,output);
    for(int row=0;row<p->r;++row)mem.transfer(worker,tensors[o.out].base+((U(p->batch)*o.rows+p->row+row)*o.cols+p->col)*4,U(p->n)*4,true);
   }
   buffer.free.post();delete p;
  }
  require(producer.terminated(),"matrix producer unfinished");done.notify(SC_ZERO_TIME);
 }
 void matrix(const Op& o){
  for(int t:o.in)flush(t); // no invented direct cross-group link
  std::vector<std::unique_ptr<sc_event>> done;std::vector<sc_process_handle> workers;
  for(int w=0;w<cfg.mcount;++w){done.emplace_back(new sc_event);workers.push_back(sc_spawn([&,w,this]{matrix_worker(o,w,*done[w]);}));}
  for(auto& w:workers)if(!w.terminated())wait(w.terminated_event());
  matrix_backed.insert(o.out);
 }
 void copy(const Op& o,size_t index){
  if(o.kind=="Constant")return;
  if(o.kind=="Gather"){
   require(!o.in.empty(),"gather input missing");int t=o.in[0];
   for(U off=0;off<o.elements;off+=64){U n=std::min<U>(64,o.elements-off);mem.transfer(3,tensors[t].base+off*(tensors[t].bits/8),ceildiv(n*tensors[t].bits,8),false);
    cycles(ceildiv(n,4)*cfg.ewise);write_range(o.out,off*(tensors[o.out].bits/8),n*(tensors[o.out].bits/8));}
   return;
  }
  if(o.kind=="View"){
   require(o.in.size()==1,"view input count");int t=o.in[0];
   // Conservatively materialize runtime reshape/transpose/broadcast with an
   // explicit bounded gather adapter; never claim a free activation layout.
   for(U off=0;off<o.elements;off+=64){U n=std::min<U>(64,o.elements-off);U take=std::min<U>(n,tensors[t].elements);
    U start=off%tensors[t].elements;take=std::min<U>(take,tensors[t].elements-start);
    read_range(t,start*(tensors[t].bits/8),take*(tensors[t].bits/8));cycles(ceildiv(n,4));write_range(o.out,off*(tensors[o.out].bits/8),n*(tensors[o.out].bits/8));
   }return;
  }
  U wanted=o.elements*(tensors[o.out].bits/8),written=0;
  for(int input:o.in){U amount=std::min(wanted-written,size(input));
   for(U off=0;off<amount;off+=256){U b=std::min<U>(256,amount-off);read_range(input,off,b);cycles(ceildiv(b,16));write_range(o.out,written+off,b);if(last_use[input]==static_cast<int>(index))discard_range(input,off,b);}
   written+=amount;if(written==wanted)break;
  }
  require(written==wanted,"copy shape coverage mismatch");
 }
 void run(){
  try{
   for(size_t i=0;i<ops.size();){auto& o=ops[i];U start=now();std::string family=o.kind;
    if(o.kind=="Dot"){matrix(o);++i;}
    else if(o.kind=="KVWrite"){kv_store(o);++i;family="KV_store";}
    else if(o.kind=="SiLU"||o.kind=="RoPE"||o.kind=="Reciprocal"){canonical(o,i);++i;family="canonical";}
    else if(elementwise(o)){
     size_t end=i+1;if(cfg.fuse)while(end<ops.size()&&((elementwise(ops[end])&&ops[end].elements==o.elements)||ops[end].kind=="Constant"))++end;
     vector_region(i,end);i=end;family="vector";
    }else if(o.kind=="NFactor"||o.kind=="SquareSum"||o.kind=="Sum"||o.kind=="Max"){reduce(o,i);++i;family="reduce";}
    else if(o.kind=="NExp"){
     // Existing scalar N service with explicit packed-input adapter. No free FP32 exp.
     vector_region(i,i+1);e_work+=o.elements*16*C;cycles(o.elements*16);++i;family="NExp";
    }else{copy(o,i);++i;family="copy";}
    spans[family]+=now()-start;
   }
   U before=now();flush_all();spans["final_flush"]+=now()-before;end_ticks=now();passed=true;
   require(mem.max_live<=static_cast<U>(cfg.credits)&&mem.max_queue<=32,"memory limit failure");
   std::cout<<std::setprecision(12)<<"RESULT {\"profile\":\""<<cfg.name<<"\",\"tokens\":"<<tokens<<",\"ticks\":"<<ceildiv(end_ticks,C)<<",\"seconds\":"<<double(end_ticks)/C/300e6
    <<",\"tokens_per_second\":"<<double(tokens)*300e6*C/end_ticks<<",\"read_bus_bytes\":"<<mem.bytes_read<<",\"write_bus_bytes\":"<<mem.bytes_write
    <<",\"logical_read_bytes\":"<<mem.logical_read<<",\"logical_write_bytes\":"<<mem.logical_write<<",\"dma_descriptors\":"<<mem.transactions
    <<",\"max_outstanding_beats\":"<<mem.max_live<<",\"max_descriptor_queue\":"<<mem.max_queue<<",\"max_outstanding_descriptors\":"<<mem.max_descriptors<<",\"U_cache_peak_bytes\":"<<cache_peak<<",\"P_scratch_peak_bytes\":"<<scratch_peak
    <<",\"cache_hits\":"<<cache_hits<<",\"cache_misses\":"<<cache_misses<<",\"dirty_evictions\":"<<cache_spills<<",\"dead_lines_discarded\":"<<discarded
    <<",\"M_commands\":"<<m_commands<<",\"M_tiles\":"<<m_tiles<<",\"KV_state_write_bytes\":"<<kv_write<<",\"resident_A_saved_bytes\":"<<resident_saved<<",\"M_work_ticks\":"<<ceildiv(m_work,C)<<",\"vector_work_ticks\":"<<ceildiv(e_work,C)<<",\"adapter_work_ticks\":"<<ceildiv(adapter_work,C)<<",\"spans_ticks\":{";
   bool first=true;for(auto& p:spans){if(!first)std::cout<<",";first=false;std::cout<<"\""<<p.first<<"\":"<<ceildiv(p.second,C);}std::cout<<"}}\n";
  }catch(const std::exception& e){std::cerr<<"MODEL_FAILURE "<<e.what()<<"\n";}
  sc_stop();
 }
};
int sc_main(int argc,char** argv){
 if(argc!=3){std::cerr<<"usage: model TRACE PROFILE\n";return 2;}
 sc_set_time_resolution(1,SC_PS);Config c;c.name=argv[2];
 if(c.name=="packed_k1")c.k=1;
 else if(c.name=="packed_k32"){}
 else if(c.name=="local_stream"){c.credits=32;c.slat=1;}
 else if(c.name=="native32"){c.credits=32;c.slat=1;c.m_mode=2;}
 else if(c.name=="native32_w8"){c.credits=32;c.slat=1;c.m_mode=2;c.weight_bits=8;}
 else if(c.name=="reference_io"){c.credits=32;c.slat=1;c.swidth=64;c.beat=64;c.bandwidth=17.1e9;c.m_mode=2;}
 else if(c.name=="reference_io_w8"){c.credits=32;c.slat=1;c.swidth=64;c.beat=64;c.bandwidth=17.1e9;c.m_mode=2;c.weight_bits=8;}
 else if(c.name=="reference_io_k256"){c.credits=32;c.slat=1;c.swidth=64;c.beat=64;c.bandwidth=17.1e9;c.m_mode=2;c.k=256;}
 else if(c.name=="reference_io_w8_k256"){c.credits=32;c.slat=1;c.swidth=64;c.beat=64;c.bandwidth=17.1e9;c.m_mode=2;c.weight_bits=8;c.k=256;}
 else if(c.name=="stream_p"||c.name=="stream_p_resident"||c.name=="stream_p_w8"||c.name=="stream_p_w8_resident"||c.name=="queued_p_w8"||c.name=="queued_pipe_w8"||c.name=="queued_pipe_w16"){
  c.credits=32;c.slat=1;c.swidth=64;c.beat=64;c.bandwidth=17.1e9;c.m_mode=2;c.k=256;c.stream=true;
  c.resident=c.name!="stream_p"&&c.name!="stream_p_w8";
  c.queued=c.name=="queued_p_w8"||c.name=="queued_pipe_w8"||c.name=="queued_pipe_w16";
  c.vecpipe=c.name=="queued_pipe_w8"||c.name=="queued_pipe_w16";
  if(c.name=="stream_p_w8"||c.name=="stream_p_w8_resident"||c.name=="queued_p_w8"||c.name=="queued_pipe_w8")c.weight_bits=8;
 }
 else if(c.name=="unfused"){c.fuse=false;}
 else if(c.name=="slow_vector"){c.ewise=12;}
 else{std::cerr<<"unknown profile\n";return 2;}
 Study s("study",c,argv[1]);sc_start();return s.passed?0:1;
}
