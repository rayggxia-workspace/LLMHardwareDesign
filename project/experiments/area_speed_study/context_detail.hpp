#pragma once

namespace context_detail {
struct P {
 U enabled_calls=0,groups=0,A_groups=0,A_loaded_bytes=0,A_saved_bytes=0;
 U context_switches=0,switch_subcycles=0,psum_register_bytes_peak=0;
 U A_bank_peak=0,B_bank_peak=0,completed_contexts=0;
};
inline std::array<P,4> data;
void emit(std::ostream& s,int contexts,int switch_cycles,bool reuse_A,int count){
 s<<"{\"contexts\":"<<contexts<<",\"switch_cycles\":"<<switch_cycles
  <<",\"reuse_A\":"<<(reuse_A?"true":"false")
  <<",\"scope\":\"additional 96-bit register contexts; P S remains 16KiB; context selection charged per M command; local S reads retained\",\"P\":[";
 for(int i=0;i<count;++i){if(i)s<<",";const auto& p=data[i];
  s<<"{\"worker\":"<<i<<",\"enabled_calls\":"<<p.enabled_calls
   <<",\"groups\":"<<p.groups<<",\"A_groups\":"<<p.A_groups
   <<",\"A_loaded_bytes\":"<<p.A_loaded_bytes<<",\"A_saved_bytes\":"<<p.A_saved_bytes
   <<",\"context_switches\":"<<p.context_switches<<",\"switch_subcycles\":"<<p.switch_subcycles
   <<",\"psum_register_bytes_peak\":"<<p.psum_register_bytes_peak
   <<",\"A_bank_peak\":"<<p.A_bank_peak<<",\"B_bank_peak\":"<<p.B_bank_peak
   <<",\"completed_contexts\":"<<p.completed_contexts<<"}";
 }
 s<<"]}";
}
}
