#pragma once
#include <cstdlib>
// Timing sensitivities only. No new arithmetic or RTL qualification is implied.
namespace optimization {
std::string name="base";
U lanes=4,k_lanes=8,a_bytes=32,b_bytes=64,write_bytes=64;
bool nexp8=false;
double bandwidth=17.1e9;
U vector_old=0,vector_new=0,nexp_old=0,nexp_new=0;
U compute_old=0,compute_new=0,tail_cycles=0,adapt_old=0,adapt_new=0;
U result_bytes=0,result_old=0,result_new=0;
bool configure(){
 const char* value=std::getenv("OPTIMIZATION_CASE");name=value?value:"base";
 if(name=="base"||name=="pool48"||name=="pool96"){}
 else if(name=="vector8")lanes=8;
 else if(name=="vector16")lanes=16;
 else if(name=="nexp8")nexp8=true;
 else if(name=="m16")k_lanes=16;
 else if(name=="feed2"){a_bytes=64;b_bytes=128;}
 else if(name=="ddr25p6")bandwidth=25.6e9;
 else if(name=="ddr34p2")bandwidth=34.2e9;
 else if(name=="write16")write_bytes=16;
 else if(name=="m16_feed2"){k_lanes=16;a_bytes=64;b_bytes=128;}
 else if(name=="vector16_nexp8"){lanes=16;nexp8=true;}
 else if(name=="compute_bundle"){k_lanes=16;a_bytes=64;b_bytes=128;lanes=16;nexp8=true;}
 else return false;
 return true;
}
U vector_cost(U old_cost,U new_cost){vector_old+=old_cost;vector_new+=new_cost;return new_cost;}
U nexp_cost(U count,bool qualified,U old_cost){
 // Candidate: one group of up to eight values per seven cycles. Preserve
 // S/cache/vector work and unsupported-format fallback. NOT RTL calibrated.
 const U cost=nexp8&&qualified?ceildiv(count,8)*7:old_cost;
 nexp_old+=old_cost;nexp_new+=cost;return cost;
}
U compute(U rows,U k,U tail){
 const U old_cost=rows*ceildiv(k,8),new_cost=rows*ceildiv(k,k_lanes);
 compute_old+=old_cost;compute_new+=new_cost;tail_cycles+=tail;return new_cost;
}
U adapt(U a,U b){
 const U old_cost=std::max(ceildiv(a,32),ceildiv(b,64));
 const U cost=std::max(ceildiv(a,a_bytes),ceildiv(b,b_bytes));
 adapt_old+=old_cost;adapt_new+=cost;return cost;
}
U write_cost(U bytes){
 const U old_cost=ceildiv(bytes,64),cost=ceildiv(bytes,write_bytes);
 result_bytes+=bytes;result_old+=old_cost;result_new+=cost;return cost*C;
}
void emit(std::ostream& out){
 out<<",\"optimization_sweep\":{\"case\":\""<<name<<"\",\"timing_sensitivity_only\":true"
    <<",\"candidate_RTL_calibrated\":false,\"native_full_model_tokens_per_second\":null"
    <<",\"reference_profile_ledgers_are_not_candidate_calibration\":true"
    <<",\"vector_lanes\":"<<lanes<<",\"K_lanes\":"<<k_lanes
    <<",\"A_bytes_per_cycle\":"<<a_bytes<<",\"B_bytes_per_cycle\":"<<b_bytes
    <<",\"M_write_bytes_per_cycle\":"<<write_bytes<<",\"DDR_B_s\":"<<bandwidth
    <<",\"nexp8\":"<<(nexp8?"true":"false")
    <<",\"vector_old\":"<<vector_old<<",\"vector_new\":"<<vector_new
    <<",\"nexp_old\":"<<nexp_old<<",\"nexp_new\":"<<nexp_new
    <<",\"compute_old\":"<<compute_old<<",\"compute_new\":"<<compute_new
    <<",\"tail_cycles\":"<<tail_cycles<<",\"adapt_old\":"<<adapt_old<<",\"adapt_new\":"<<adapt_new
    <<",\"result_bytes\":"<<result_bytes<<",\"result_old\":"<<result_old<<",\"result_new\":"<<result_new<<"}";
}
}
