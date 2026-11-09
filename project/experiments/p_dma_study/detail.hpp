#pragma once
#include <array>
#include <sstream>

// U, now(), C and require() come from the frozen model before this include.
namespace detail {
enum Flow { OTHER, A, WEIGHT, DYNAMIC_B, DOT_OUTPUT, U_READ, U_WRITE, KV_WRITE, FLOWS };
constexpr const char* names[FLOWS]={"other","A","weight","dynamic_B","dot_output","U_read","U_write","KV_write"};
struct Traffic {
 U logical_read=0,logical_write=0,bus_read=0,bus_write=0,descriptors=0;
 void add(bool write,U logical,U bus){
  ++descriptors;if(write){logical_write+=logical;bus_write+=bus;}else{logical_read+=logical;bus_read+=bus;}
 }
};
Traffic difference(const Traffic& a,const Traffic& b){
 return {a.logical_read-b.logical_read,a.logical_write-b.logical_write,
         a.bus_read-b.bus_read,a.bus_write-b.bus_write,a.descriptors-b.descriptors};
}
void accumulate(Traffic& a,const Traffic& b){
 a.logical_read+=b.logical_read;a.logical_write+=b.logical_write;
 a.bus_read+=b.bus_read;a.bus_write+=b.bus_write;a.descriptors+=b.descriptors;
}
void print_traffic(std::ostream& s,const Traffic& t){
 s<<"{\"logical_read\":"<<t.logical_read<<",\"logical_write\":"<<t.logical_write
  <<",\"bus_read\":"<<t.bus_read<<",\"bus_write\":"<<t.bus_write<<",\"descriptors\":"<<t.descriptors<<"}";
}
struct Channel {
 Traffic traffic;std::array<Traffic,FLOWS> flows;
 U bus_work=0,credit_wait=0,submit_credit_wait=0,queue_wait=0,submit_queue_wait=0;
 U bank_wait=0,bus_wait=0,turns=0,row_misses=0,beats=0;
};
struct P {
 U ready=0,ack=0,service=0,output=0,elapsed=0,producer_free_wait=0;
 U tiles=0,prefix_loaded=0,prefix_saved=0,prefix_peak=0,write_buffer_peak=0;
};
struct Shape {
 U calls=0,wall=0,tiles=0,commands=0;std::array<Traffic,FLOWS> flows;
};
struct Data {
 std::array<Channel,2> channels;std::array<P,4> p;
 std::array<U,4> s_service{},s_wait{},s_calls{};
 std::map<std::string,Shape> shapes;
};
inline Data data;
std::array<Traffic,FLOWS> flow_totals(){
 std::array<Traffic,FLOWS> out;
 for(const auto& c:data.channels)for(int f=0;f<FLOWS;++f)accumulate(out[f],c.flows[f]);
 return out;
}
std::vector<int> columns(int n,int worker,int count,bool pairs){
 std::vector<int> out;
 if(pairs){for(int base=worker*16;base<n;base+=count*16)for(int c=base;c<std::min(base+16,n);c+=8)out.push_back(c);}
 else for(int c=worker*8;c<n;c+=count*8)out.push_back(c);
 return out;
}
struct WriteBuffer {bool valid=false;U base=0,lo=0,bytes=0;};
void validate(U lr,U lw,U br,U bw,U descriptors,int mcount){
 Traffic total;
 for(const auto& c:data.channels){
  Traffic sum;for(const auto& f:c.flows)accumulate(sum,f);
  require(sum.logical_read==c.traffic.logical_read&&sum.logical_write==c.traffic.logical_write&&
          sum.bus_read==c.traffic.bus_read&&sum.bus_write==c.traffic.bus_write&&
          sum.descriptors==c.traffic.descriptors,"flow/channel conservation");
  accumulate(total,c.traffic);
 }
 require(total.logical_read==lr&&total.logical_write==lw&&total.bus_read==br&&total.bus_write==bw&&total.descriptors==descriptors,
         "detail/legacy traffic conservation");
 for(int i=0;i<mcount;++i){const auto& p=data.p[i];
  require(p.ready+p.ack+p.service+p.output==p.elapsed,"consumer wall-stage conservation");
  require(p.write_buffer_peak<=512,"write buffer capacity");
 }
}
void emit(std::ostream& s,U end,int mcount,const std::string& variant){
 s<<"{\"variant\":\""<<variant<<"\",\"subcycles_per_core_cycle\":"<<C
  <<",\"end_subcycles\":"<<end<<",\"wait_scope\":\"memory waits overlap; only each P consumer stages sum to its own elapsed time\",\"channels\":[";
 for(int i=0;i<2;++i){if(i)s<<",";const auto& c=data.channels[i];s<<"{\"channel\":"<<i<<",\"traffic\":";
  print_traffic(s,c.traffic);s<<",\"flows\":{";
  for(int f=0;f<FLOWS;++f){if(f)s<<",";s<<"\""<<names[f]<<"\":";print_traffic(s,c.flows[f]);}
  s<<"},\"bus_work_subcycles\":"<<c.bus_work<<",\"credit_wait_subcycles\":"<<c.credit_wait
   <<",\"submit_credit_wait_subcycles\":"<<c.submit_credit_wait<<",\"queue_wait_subcycles\":"<<c.queue_wait
   <<",\"submit_queue_wait_subcycles\":"<<c.submit_queue_wait<<",\"bank_wait_subcycles\":"<<c.bank_wait
   <<",\"bus_wait_subcycles\":"<<c.bus_wait<<",\"direction_changes\":"<<c.turns
   <<",\"row_misses\":"<<c.row_misses<<",\"beats\":"<<c.beats<<"}";
 }
 s<<"],\"P\":[";
 for(int i=0;i<mcount;++i){if(i)s<<",";const auto& p=data.p[i];
  s<<"{\"worker\":"<<i<<",\"consumer_ready_wait_subcycles\":"<<p.ready<<",\"input_ACK_wait_subcycles\":"<<p.ack
   <<",\"service_subcycles\":"<<p.service<<",\"output_subcycles\":"<<p.output<<",\"elapsed_subcycles\":"<<p.elapsed
   <<",\"producer_free_wait_subcycles\":"<<p.producer_free_wait<<",\"tiles\":"<<p.tiles
   <<",\"prefix_A_loaded_bytes\":"<<p.prefix_loaded<<",\"prefix_A_saved_bytes\":"<<p.prefix_saved
   <<",\"prefix_peak_bytes\":"<<p.prefix_peak<<",\"write_buffer_peak_bytes\":"<<p.write_buffer_peak<<"}";
 }
 s<<"],\"S_calendars\":[";
 for(int i=0;i<4;++i){if(i)s<<",";s<<"{\"group\":"<<i<<",\"service_subcycles\":"<<data.s_service[i]
  <<",\"scheduled_wait_subcycles\":"<<data.s_wait[i]<<",\"reservations\":"<<data.s_calls[i]<<"}";}
 s<<"],\"matrix_shapes\":[";bool first=true;
 for(const auto& item:data.shapes){if(!first)s<<",";first=false;const auto& sh=item.second;
  s<<"{\"key\":\""<<item.first<<"\",\"calls\":"<<sh.calls<<",\"wall_subcycles\":"<<sh.wall
   <<",\"tiles\":"<<sh.tiles<<",\"commands\":"<<sh.commands<<",\"flows\":{";
  for(int f=0;f<FLOWS;++f){if(f)s<<",";s<<"\""<<names[f]<<"\":";print_traffic(s,sh.flows[f]);}
  s<<"}}";
 }
 s<<"]}";
}
}
