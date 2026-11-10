// Conditional timing model, not production RTL. Included after Calendar.
#include <array>
#include <functional>
#include <deque>
namespace shared_pool {
struct Consumed {
 int worker; U epoch,row,source_address,pool_address,bytes,tile_id,ready_at,consumed_at;
};
struct Issued {int worker;U epoch,pool_address,bytes,tile_id,issued_at,ready_at,credit_release_at,outstanding;};
struct Worker {
 U reads=0,read_bytes=0,read_bus_bytes=0,consumed_bytes=0,fifo_peak=0;
 U credit_wait=0,port_wait=0,latency_subcycles=0,feed_subcycles=0;
 U local_A_bytes=0,bypassed_local_A_bytes=0,local_read_saved=0;
 U avoided_DDR_bytes=0,avoided_DDR_bus_bytes=0,avoided_local_write=0;
 long long avoided_DDR_descriptors=0;
 U active=0,completed_tiles=0;
};
struct Pool {
 U capacity=0,depth=4,latency=2,port_cycles=1;
 U base=0,rows=0,K=0,element_bytes=0,prefix_k=0,stride=0,epoch=0;
 bool active=false,valid=false;
 Calendar port; std::array<Calendar,4> banks; std::array<Worker,2> workers;
 std::vector<unsigned char> initialized;
 U calls=0,full_calls=0,partial_calls=0,peak_bytes=0,fill_payload_bytes=0;
 U fill_descriptors=0,fill_peak_descriptors=0,fill_DDR_bus_bytes=0,write_beats=0,write_bus_bytes=0;
 U read_beats=0,read_bus_bytes=0,fill_subcycles=0,write_wait=0;
 U fill_start=0,live_workers=0,max_live_workers=0,completed_epochs=0,epoch_written_bytes=0,last_write_ack=0;
 std::function<void(const Consumed&)> on_consume;
 std::function<void(const Issued&)> on_issue;
 // Optional deterministic probe-only consumer stall. The return value is an
 // absolute completion time, never earlier than the proposed completion.
 std::function<U(const Consumed&)> consumer_ready_at;
 void configure(U cap,U fifo,U delay,U cycles_per_port){
  require(!active,"pool configure while live");
  require(fifo>=1&&fifo<=8&&delay<=16&&cycles_per_port>=1&&cycles_per_port<=4,"pool parameters");
  capacity=cap;depth=fifo;latency=delay;port_cycles=cycles_per_port;
 }
 U cached_k()const{return prefix_k;}
 U cached_bytes()const{return rows*stride;}
 bool begin(U source,U row_count,U columns,U elem,U grain){
  require(!active&&live_workers==0,"pool overwrite before consumers drained");
  base=source;rows=row_count;K=columns;element_bytes=elem;prefix_k=0;stride=0;
  require(rows&&K&&element_bytes&&grain,"invalid pool shape");
  if(!capacity)return false;
  const U whole=ceildiv(K*element_bytes,64)*64;
  if(rows*whole<=capacity)prefix_k=K;
  else{prefix_k=std::min(K,((capacity/rows)/element_bytes/grain)*grain);
   while(prefix_k&&rows*ceildiv(prefix_k*element_bytes,64)*64>capacity)prefix_k-=grain;}
  if(!prefix_k)return false;
  stride=ceildiv(prefix_k*element_bytes,64)*64;
  require(rows*stride<=capacity,"pool padded capacity overflow");
  active=true;valid=false;epoch_written_bytes=0;last_write_ack=0;initialized.assign(rows*stride,0);++epoch;++calls;
  if(prefix_k==K)++full_calls;else ++partial_calls;
  peak_bytes=std::max(peak_bytes,rows*stride);fill_start=now();return true;
 }
 U covered(U address,U bytes)const{
  if(!active||!bytes)return 0;
  require(address>=base&&address+bytes<=base+rows*K*element_bytes,"A request outside generation");
  U hit=0;
  for(U r=0;r<rows;++r){U lo=base+r*K*element_bytes,hi=lo+prefix_k*element_bytes;
   U start=std::max(address,lo),end=std::min(address+bytes,hi);if(end>start)hit+=end-start;
  }return hit;
 }
 std::vector<std::pair<U,U>> remaining(U address,U bytes)const{
  if(!active)return {{address,bytes}};
  (void)covered(address,bytes);std::vector<std::pair<U,U>> out;
  for(U r=0;r<rows;++r){U lo=base+(r*K+prefix_k)*element_bytes,hi=base+(r+1)*K*element_bytes;
   U start=std::max(address,lo),end=std::min(address+bytes,hi);if(end>start)out.push_back({start,end-start});
  }return out;
 }
 // A 64B access uses four 128-bit 1RW lane banks in lockstep. The
 // 64B/cycle fabric and every lane bank retain fixed width at every capacity.
 U reserve(U at,bool write){
  const U duration=port_cycles*C,end=port.reserve(at,duration),start=end-duration;
  for(auto& b:banks){const U e=b.reserve(start,duration);require(e==end,"lane bank schedule differs from fabric");}
  if(write){++write_beats;write_bus_bytes+=64;write_wait+=start-at;}
  else{++read_beats;read_bus_bytes+=64;}
  return end;
 }
 U write(U at,U address,U bytes=64){
  require(active&&!valid&&address+bytes<=rows*stride,"pool write lifecycle/range");
  require(bytes&&address%stride+bytes<=prefix_k*element_bytes,"pool write includes row padding/crosses row");
  for(U i=address;i<address+bytes;++i){require(!initialized[i],"duplicate pool fill byte");initialized[i]=1;}
  U end=at;for(U p=address/64;p<ceildiv(address+bytes,64);++p)end=reserve(end,true);
  epoch_written_bytes+=bytes;last_write_ack=std::max(last_write_ack,end);
  return end;
 }
 void filled(){require(active&&!valid,"duplicate pool fill");require(epoch_written_bytes==rows*prefix_k*element_bytes&&now()>=last_write_ack,"pool fill before all write ACKs");valid=true;fill_subcycles+=now()-fill_start;}
 U feed(int worker,U row,U row_count,U ki,U count,U tile_id=0,U local_ready_at=0){
  if(!active)return 0;
  require(valid&&worker>=0&&worker<2&&row+row_count<=rows&&ki+count<=K,"invalid pool read generation/range");
  auto& w=workers[worker];require(!w.active,"overlapping FIFO use by one P");w.active=1;
  ++live_workers;max_live_workers=std::max(max_live_workers,live_workers);
  const U started=now(),generation=epoch;U consumer=now(),hit=0,next_issue=now();
  // Entries include issued, in-flight and returned beats until the last
  // valid byte is consumed. No next-tile prefetch; depth is not a hint.
  std::deque<U> credit_release;
  for(U r=row;r<row+row_count;++r){
   const U shared_k=ki<prefix_k?std::min(count,prefix_k-ki):0;
   U position=ki*element_bytes,left=shared_k*element_bytes;
   while(left){
    pause_until(next_issue);
    while(!credit_release.empty()&&credit_release.front()<=now())credit_release.pop_front();
    if(credit_release.size()>=depth){U before=now();pause_until(credit_release.front());w.credit_wait+=now()-before;
     while(!credit_release.empty()&&credit_release.front()<=now())credit_release.pop_front();}
    const U address=r*stride+position,take=std::min(left,64-address%64),issued=now();
    const U end=reserve(issued,false),ready=end+latency*C;
    w.port_wait+=end-port_cycles*C-issued;w.latency_subcycles+=latency*C;
    ++w.reads;w.read_bytes+=take;w.read_bus_bytes+=64;hit+=take;
    consumer=std::max(consumer,ready);
    for(U offset=0;offset<take;offset+=32){const U n=std::min<U>(32,take-offset);consumer+=C;w.consumed_bytes+=n;
     Consumed event{worker,generation,r,base+r*K*element_bytes+position+offset,address+offset,n,tile_id,ready,consumer};
     if(consumer_ready_at){consumer=std::max(consumer,consumer_ready_at(event));event.consumed_at=consumer;}
     if(on_consume)on_consume(event);}
    credit_release.push_back(consumer);w.fifo_peak=std::max<U>(w.fifo_peak,credit_release.size());
    require(w.fifo_peak<=depth,"FIFO capacity exceeded");
    if(on_issue)on_issue(Issued{worker,generation,address,take,tile_id,issued,ready,consumer,U(credit_release.size())});
    position+=take;left-=take;
    // At most one request per P per core cycle. Credit and shared 1RW
    // service can impose larger gaps, including when two P run together.
    next_issue=issued+C;
   }
   // A mixed tile cannot consume its local suffix before that tile's local
   // combined A/B SRAM read completes. Full-local tiles keep the legacy
   // overlap contract; this conservative join applies only to mixed tiles.
   if(shared_k&&shared_k<count)consumer=std::max(consumer,local_ready_at);
   consumer+=ceildiv((count-shared_k)*element_bytes,32)*C;
  }
  pause_until(consumer);require(epoch==generation&&active&&valid,"stale generation consumed");
  require(credit_release.empty()||credit_release.back()<=now(),"FIFO not drained");
  w.feed_subcycles+=now()-started;++w.completed_tiles;w.active=0;--live_workers;return hit;
 }
 void end(){
  if(!active)return;
  require(valid&&!live_workers,"pool release before readers drain");for(const auto& w:workers)require(!w.active,"live P FIFO");
  active=false;valid=false;++completed_epochs;
 }
 void emit(std::ostream& out)const{
  out<<",\"shared_pool_study\":{\"schema\":1,\"enabled\":"<<(capacity?"true":"false")
   <<",\"scope\":\"conditional SystemC timing; no RTL or physical qualification\""
   <<",\"capacity_bytes\":"<<capacity<<",\"fifo_beats_per_P\":"<<depth<<",\"fifo_beat_bytes\":64"
   <<",\"read_latency_cycles\":"<<latency<<",\"port_cycles\":"<<port_cycles
   <<",\"banks\":4,\"bank_width_bits\":128,\"bank_mode\":\"1RW lockstep lanes\",\"fabric_bytes\":64,\"A_feeder_bytes_per_cycle\":32"
   <<",\"broadcast\":false,\"fill_descriptor_max_bytes\":1024,\"fill_descriptor_limit\":2"
   <<",\"calls\":"<<calls<<",\"full_calls\":"<<full_calls<<",\"partial_calls\":"<<partial_calls
   <<",\"peak_bytes\":"<<peak_bytes<<",\"fill_payload_bytes\":"<<fill_payload_bytes
   <<",\"fill_descriptors\":"<<fill_descriptors<<",\"fill_peak_descriptors\":"<<fill_peak_descriptors
   <<",\"fill_DDR_bus_bytes\":"<<fill_DDR_bus_bytes
   <<",\"write_beats\":"<<write_beats<<",\"write_bus_bytes\":"<<write_bus_bytes
   <<",\"read_beats\":"<<read_beats<<",\"read_bus_bytes\":"<<read_bus_bytes
   <<",\"fill_subcycles\":"<<fill_subcycles<<",\"write_wait_subcycles\":"<<write_wait
   <<",\"port_service_subcycles\":"<<port.busy<<",\"port_wait_subcycles\":"<<port.queue_wait
   <<",\"max_live_workers\":"<<max_live_workers<<",\"live_workers\":"<<live_workers
   <<",\"completed_epochs\":"<<completed_epochs<<",\"live_epoch\":"<<(active?1:0)<<",\"P\":[";
  for(int i=0;i<2;++i){if(i)out<<",";const auto& w=workers[i];out<<"{\"worker\":"<<i
   <<",\"reads\":"<<w.reads<<",\"read_bytes\":"<<w.read_bytes<<",\"read_bus_bytes\":"<<w.read_bus_bytes
   <<",\"consumed_bytes\":"<<w.consumed_bytes<<",\"fifo_peak\":"<<w.fifo_peak
   <<",\"credit_wait_subcycles\":"<<w.credit_wait<<",\"port_wait_subcycles\":"<<w.port_wait
   <<",\"latency_subcycles\":"<<w.latency_subcycles<<",\"feed_subcycles\":"<<w.feed_subcycles
   <<",\"local_A_read_bytes\":"<<w.local_A_bytes<<",\"bypassed_local_A_read_bytes\":"<<w.bypassed_local_A_bytes
   <<",\"avoided_local_read_subcycles\":"<<w.local_read_saved
   <<",\"avoided_A_DDR_bytes\":"<<w.avoided_DDR_bytes<<",\"avoided_A_DDR_bus_bytes\":"<<w.avoided_DDR_bus_bytes
   <<",\"avoided_A_DDR_descriptors\":"<<w.avoided_DDR_descriptors
   <<",\"avoided_local_write_subcycles\":"<<w.avoided_local_write
   <<",\"completed_tiles\":"<<w.completed_tiles<<",\"active\":"<<w.active<<"}";}
  out<<"],\"bank_service_subcycles\":[";for(int i=0;i<4;++i){if(i)out<<",";out<<banks[i].busy;}out<<"]}";
 }
};
Pool pool;
}
