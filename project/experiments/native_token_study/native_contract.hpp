#pragma once
#include <array>
namespace native_model {
constexpr U narrow_cycles=6,wrapper_cycles=4,split_width=4,merge_pair_cycles=3,rne_pair_cycles=3;
struct Counts {
 U dma_input_words=0,dma_output_words=0,local_read_words=0,local_write_words=0;
 U wide_reads=0,A_beats=0,B_beats=0,loads=0,B_only_loads=0;
 U packed_A_bytes=0,packed_B_bytes=0,raw_A_conversion_read_bytes=0,raw_B_conversion_read_bytes=0;
 U split_cycles=0,merge_cycles=0,final_rne_cycles=0;
 U scale_commands=0,MAC_commands=0,raw_commands=0,RNE_commands=0,release_commands=0;
 U leaf_cycles=0,wrapper_control_cycles=0,load_cycles=0;
 U static_groups=0,dynamic_groups=0,context_groups=0,context_outputs=0;
 U S96_terms=0,S96_clear_words=0,resident_A_bytes=0,peak_S_bytes=0,useful_MACs=0;
 U static_S32_MAC_commands=0,dynamic_MAC_commands=0;
 U scalar_row_terms=0,S8_bitpass_issues=0,source_A_DDR_bytes=0,source_B_DDR_bytes=0,output_DDR_bytes=0;
 std::array<U,4> bank_operations{};
};
inline std::array<Counts,2> data;
inline U S32_Dot_calls=0,S32_Dot_input_occurrences=0,all_Dot_calls=0,non_Dot_candidate_ops=0;
inline void word_operations(Counts& s,U begin,U words){for(U i=0;i<words;++i)++s.bank_operations[(begin+i)%4];}
// One finite 16-byte fragment register per direction assembles an unaligned
// descriptor. Only valid words are committed/read; padded DDR bus bytes do not
// become fictitious extra S data. A descriptor ACK includes its last S write.
inline U dma_service(int worker,U address,U bytes,U beat_index,U beat,bool write){
 const U base=address/beat*beat,lo=std::max(address,base+beat_index*beat);
 const U hi=std::min(address+bytes,base+(beat_index+1)*beat);
 const U before=lo-address,after=hi-address;const bool last=after==bytes;
 U first=write?ceildiv(before,16):before/16;
 U end=write?ceildiv(after,16):(last?ceildiv(after,16):after/16);
 require(end>=first,"native DMA word interval");U words=end-first;auto& s=data[worker];
 (write?s.dma_output_words:s.dma_input_words)+=words;word_operations(s,first,words);
 return words*narrow_cycles*C;
}
// Exact unloaded leaf recurrence derived from ISSUE, two partial banks and
// ordered four-pair scale pipeline. It is not a percentage fit.
inline U leaf_latency(int rows,int tiles,bool aw,bool bw){
 require(rows>=1&&rows<=8&&tiles>=1&&tiles<=4,"native M shape");
 U q=U(tiles)*(aw?3:1)*(bw?3:1);std::array<U,8> s{},f{};s[0]=1;
 for(int r=0;r<rows;++r){
  if(r)s[r]=std::max(s[r-1]+q+1,r>=2?f[r-2]+5:U(0));
  f[r]=std::max(s[r]+q+2,r?f[r-1]+4:U(0));
 }
 return f[rows-1]+8;
}
inline U loader_done(int rows,int tiles,bool bw,bool reuse_b=false){
 require((rows==0||rows==1||rows==3)&&tiles>=1&&tiles<=4,"native loader shape");
 if(rows==0)return U(tiles)*(bw?4:2)+5;
 if(reuse_b)return U(tiles)*(rows==3?6:2)+5;
 if(rows==3)return U(tiles)*6+(bw?9:7);
 return U(tiles)*(bw?6:4)+5;
}
inline void emit(std::ostream& out,bool context,int contexts,int weight_bits){
 out<<",\"native_study\":{\"qualification\":\"conditional native-P control model plus paid unimplemented S32/S96 adapter and frozen candidate U; not native LLM generation\""
  <<",\"clock_hz\":300000000,\"aggregate_DDR_bytes_per_second\":17100000000,\"P_count\":2,\"U_count\":1"
  <<",\"P_private_S_bytes\":16384,\"physical_banks\":4,\"ports_per_bank\":\"1RW\",\"ordinary_word_bytes\":16"
  <<",\"native_existing_result_RF_bytes\":512,\"native_existing_operand_partial_result_payload_bytes\":2704"
  <<",\"conditional_conversion_tile_register_bytes\":2560,\"conditional_DMA_register_bytes\":128"
  <<",\"conditional_merge_register_bytes\":24,\"extra_adapter_register_bytes_per_P\":2712"
  <<",\"context_control_added_bits\":"<<(context?325:0)
  <<",\"native_context\":"<<(context?"true":"false")<<",\"requested_contexts\":"<<contexts<<",\"weight_bits\":"<<weight_bits
  <<",\"same_P_async_controller\":false,\"consumer_priority_cycle_gain\":0,\"independent_bank_cycle_gain\":0"
  <<",\"loader_dispatch_gap_cycles\":2,\"loader_gap_scope\":\"deliberate conservative serial-controller ACK/dispatch wait; not minimum cross-resource issue latency\""
  <<",\"before_program\":\"legacy op10 three digit rows and paid final S96 merge; no op13/14\""
  <<",\"after_program\":\"op13 mathematical S64 contexts with three source rows and explicit scale/RNE/release\""
  <<",\"raw_A_cache\":\"full raw A if capacity permits, common policy; no prefix\""
  <<",\"S32_Dot_calls\":"<<S32_Dot_calls<<",\"S32_Dot_input_occurrences\":"<<S32_Dot_input_occurrences
  <<",\"all_Dot_calls\":"<<all_Dot_calls<<",\"non_Dot_candidate_ops\":"<<non_Dot_candidate_ops
  <<",\"native_admitted\":false,\"P\":[";
 for(int w=0;w<2;++w){if(w)out<<",";const auto& s=data[w];out<<"{\"worker\":"<<w;
#define NATIVE_EMIT(field) out<<",\"" #field "\":"<<s.field
  NATIVE_EMIT(dma_input_words);NATIVE_EMIT(dma_output_words);NATIVE_EMIT(local_read_words);NATIVE_EMIT(local_write_words);
  NATIVE_EMIT(wide_reads);NATIVE_EMIT(A_beats);NATIVE_EMIT(B_beats);NATIVE_EMIT(loads);NATIVE_EMIT(B_only_loads);
  NATIVE_EMIT(packed_A_bytes);NATIVE_EMIT(packed_B_bytes);NATIVE_EMIT(raw_A_conversion_read_bytes);NATIVE_EMIT(raw_B_conversion_read_bytes);
  NATIVE_EMIT(split_cycles);NATIVE_EMIT(merge_cycles);NATIVE_EMIT(final_rne_cycles);
  NATIVE_EMIT(scale_commands);NATIVE_EMIT(MAC_commands);NATIVE_EMIT(raw_commands);NATIVE_EMIT(RNE_commands);NATIVE_EMIT(release_commands);
  NATIVE_EMIT(leaf_cycles);NATIVE_EMIT(wrapper_control_cycles);NATIVE_EMIT(load_cycles);
  NATIVE_EMIT(static_groups);NATIVE_EMIT(dynamic_groups);NATIVE_EMIT(context_groups);NATIVE_EMIT(context_outputs);
  NATIVE_EMIT(S96_terms);NATIVE_EMIT(S96_clear_words);NATIVE_EMIT(resident_A_bytes);NATIVE_EMIT(peak_S_bytes);NATIVE_EMIT(useful_MACs);
  NATIVE_EMIT(static_S32_MAC_commands);NATIVE_EMIT(dynamic_MAC_commands);
  NATIVE_EMIT(scalar_row_terms);NATIVE_EMIT(S8_bitpass_issues);NATIVE_EMIT(source_A_DDR_bytes);NATIVE_EMIT(source_B_DDR_bytes);NATIVE_EMIT(output_DDR_bytes);
#undef NATIVE_EMIT
  out<<",\"bank_operations\":[";for(int b=0;b<4;++b)out<<(b?",":"")<<s.bank_operations[b];out<<"]}";
 }
 out<<"]}";
}
}
