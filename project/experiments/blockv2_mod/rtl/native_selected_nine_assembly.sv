// Product RTL verification assembly: thirty independent functional macros and parent controls.
// Not a hard macro; no group exterior or these top-level ports define physical placement.
module native_selected_nine_assembly #(parameter logic [31:0] TOPOLOGY=18503, LC_IMAGE_ID=25001,
parameter integer unsigned SERVICE_STALL_LIMIT=100000000)(
input wire clk,
input wire reset,
input wire mc_release_valid_i,
input wire [31:0] mc_release_sequence_i,
input wire [31:0] mc_release_epoch_i,
input wire mc_deploy_valid_i,
input wire [31:0] mc_deploy_generation_i,
output wire mc_release_ready_o,
output wire mc_poison_o,
output wire mc_image_valid_o,
input wire mc_cfg_req_valid_i,
input wire [2:0] mc_cfg_req_op_i,
input wire [31:0] mc_cfg_req_generation_i,
input wire [13:0] mc_cfg_req_address_i,
input wire [127:0] mc_cfg_req_data_i,
input wire [15:0] mc_cfg_req_total_bytes_i,
input wire [31:0] mc_cfg_req_image_id_i,
input wire [31:0] mc_cfg_req_topology_id_i,
input wire [31:0] mc_cfg_req_abi_id_i,
input wire [31:0] mc_cfg_req_capacity_id_i,
input wire mc_cfg_req_proof_i,
input wire mc_cfg_rsp_ready_i,
output wire mc_cfg_req_ready_o,
output wire mc_cfg_rsp_valid_o,
output wire [15:0] mc_cfg_rsp_status_o,
output wire [127:0] mc_cfg_rsp_data_o,
output wire [31:0] mc_cfg_rsp_generation_o,
output wire [3:0] mc_life_o,
output wire [3:0] mc_seq_o,
output wire [31:0] mc_trace_pc_o,
output wire mc_trace_retire_o,
output wire [7:0] mc_trace_opcode_o,
output wire [1:0] mc_trace_pm_owner_o,
output wire mc_trace_ireg_valid_o,
input wire mc_start_valid_i,
input wire mc_start_credit_i,
input wire [31:0] mc_start_job_i,
input wire [31:0] mc_start_epoch_i,
input wire [31:0] mc_start_sequence_i,
input wire [31:0] mc_start_generation_i,
input wire [287:0] mc_local_image_ids_i,
input wire [8:0] mc_local_enabled_i,
output wire mc_start_ready_o,
output wire [31:0] mc_frame_fault_count,
output wire mc_result_valid_o,
input wire mc_result_ready_i,
output wire [31:0] mc_result_job_o,
output wire [31:0] mc_result_epoch_o,
output wire [31:0] mc_result_sequence_o,
output wire [15:0] mc_result_status_o,
output wire [31:0] mc_result_error_pc_o,
output wire [7:0] mc_result_source_o,
output wire [31:0] mc_result_child_error_pc_o,
output wire [31:0] mc_result_failed_task_sequence_o,
output wire [31:0] mc_result_confirmed_read_bytes_o,
output wire [31:0] mc_result_confirmed_write_bytes_o,
output wire mc_result_counter_overflow_o,
output wire mc_result_saturated_o,
output wire [15:0] mc_trace_live_tokens_o,
output wire [8:0] mc_trace_block_active_o,
output wire [8:0] mc_trace_terminal_full_o,
output wire [8:0] mc_trace_READY_full_o,
output wire mc_trace_aborting_o,
input wire mc_recover_valid_i,
output wire mc_recover_ready_o,
output wire [31:0] mc_protocol_fault_count_o,
output wire [3:0] memory_d_req_valid,
input wire [3:0] memory_d_req_ready,
output wire [255:0] memory_d_req_address,
output wire [255:0] memory_d_req_tag,
input wire [3:0] memory_d_rsp_valid,
output wire [3:0] memory_d_rsp_ready,
input wire [255:0] memory_d_rsp_tag,
input wire [2047:0] memory_d_rsp_data,
output wire memory_d_fence_valid,
input wire memory_d_fence_ready,
output wire [31:0] memory_d_fence_generation,
input wire memory_d_fence_done_valid,
output wire memory_d_fence_done_ready,
input wire [31:0] memory_d_fence_done_generation,
output wire memory_fault_valid,
input wire memory_fault_ready,
output wire [7:0] memory_fault_kind,
output wire [4:0] memory_fault_client,
output wire [31:0] memory_fault_local_tag,
output wire [63:0] memory_fault_global_tag,
output wire [11:0] memory_debug_beats,
output wire [11:0] memory_debug_descriptors,
output wire [31:0] memory_debug_generation,
output wire [3:0] memory_d_req_write,
output wire [2047:0] memory_d_req_data,
input wire [8:0] lc_session_valid,
output wire [8:0] lc_session_ready,
input wire [287:0] lc_session_generation,
input wire [287:0] lc_session_topology,
input wire [8:0] lc_cfg_valid,
output wire [8:0] lc_cfg_ready,
input wire [17:0] lc_cfg_op,
input wire [287:0] lc_cfg_generation,
input wire [287:0] lc_cfg_abi,
input wire [287:0] lc_cfg_capacity,
input wire [287:0] lc_cfg_crc,
input wire [143:0] lc_cfg_bytes,
input wire [125:0] lc_cfg_address,
input wire [1151:0] lc_cfg_data,
output wire [8:0] lc_cfg_rsp_valid,
input wire [8:0] lc_cfg_rsp_ready,
output wire [71:0] lc_cfg_status,
output wire [287:0] lc_cfg_actual_crc,
output wire [8:0] lc_certified,
output wire [8:0] lc_prepared,
output wire [7:0] observe_P0_source,
output wire [287:0] lc_protocol_fault_cycles,
output wire [8:0] lc_pm_trace_valid,
output wire [125:0] lc_pm_trace_address,
output wire [287:0] lc_retired_instructions,
output wire [7:0] observe_P1_source,
output wire [7:0] observe_P2_source,
output wire [7:0] observe_C0_source,
output wire [7:0] observe_U0_source,
output wire [7:0] observe_J0_source,
output wire [7:0] observe_F0_source,
output wire [7:0] observe_U1_source,
output wire [7:0] observe_J1_source
);
wire selected_0;
wire selected_1;
wire [63:0] selected_2;
wire [3:0] selected_3;
wire [3:0] selected_4;
wire [7:0] selected_5;
wire [2:0] selected_6;
wire selected_7;
wire selected_8;
wire [63:0] selected_9;
wire [3:0] selected_10;
wire selected_11;
wire selected_12;
wire selected_13;
wire selected_14;
wire [9:0] selected_15;
wire [127:0] selected_16;
wire selected_17;
wire selected_18;
wire [127:0] selected_19;
wire selected_20;
wire selected_21;
wire [63:0] selected_22;
wire [3:0] selected_23;
wire [3:0] selected_24;
wire [7:0] selected_25;
wire [2:0] selected_26;
wire selected_27;
wire selected_28;
wire [63:0] selected_29;
wire [3:0] selected_30;
wire selected_31;
wire selected_32;
wire selected_33;
wire selected_34;
wire [9:0] selected_35;
wire [127:0] selected_36;
wire selected_37;
wire selected_38;
wire [127:0] selected_39;
wire selected_40;
wire selected_41;
wire [63:0] selected_42;
wire [3:0] selected_43;
wire [3:0] selected_44;
wire [7:0] selected_45;
wire [2:0] selected_46;
wire selected_47;
wire selected_48;
wire [63:0] selected_49;
wire [3:0] selected_50;
wire selected_51;
wire selected_52;
wire selected_53;
wire selected_54;
wire [9:0] selected_55;
wire [127:0] selected_56;
wire selected_57;
wire selected_58;
wire [127:0] selected_59;
wire selected_60;
wire selected_61;
wire selected_62;
wire selected_63;
wire [127:0] selected_64;
wire selected_65;
wire selected_66;
wire selected_67;
wire selected_68;
wire [127:0] selected_69;
wire selected_70;
wire selected_71;
wire [255:0] selected_72;
wire [31:0] selected_73;
wire [2:0] selected_74;
wire selected_75;
wire selected_76;
wire [63:0] selected_77;
wire [63:0] selected_78;
wire selected_79;
wire [1:0] selected_80;
wire selected_81;
wire selected_82;
wire [63:0] selected_83;
wire [1:0] selected_84;
wire selected_85;
wire selected_86;
wire selected_87;
wire selected_88;
wire [9:0] selected_89;
wire [127:0] selected_90;
wire selected_91;
wire selected_92;
wire [127:0] selected_93;
wire selected_94;
wire selected_95;
wire selected_96;
wire selected_97;
wire [127:0] selected_98;
wire selected_99;
wire selected_100;
wire selected_101;
wire selected_102;
wire [127:0] selected_103;
wire selected_104;
wire selected_105;
wire [255:0] selected_106;
wire [31:0] selected_107;
wire [2:0] selected_108;
wire selected_109;
wire selected_110;
wire [63:0] selected_111;
wire [63:0] selected_112;
wire selected_113;
wire [1:0] selected_114;
wire selected_115;
wire selected_116;
wire [63:0] selected_117;
wire [1:0] selected_118;
wire selected_119;
wire selected_120;
wire selected_121;
wire selected_122;
wire [9:0] selected_123;
wire [127:0] selected_124;
wire selected_125;
wire selected_126;
wire [127:0] selected_127;
wire selected_128;
wire selected_129;
wire selected_130;
wire selected_131;
wire [127:0] selected_132;
wire selected_133;
wire selected_134;
wire selected_135;
wire selected_136;
wire [127:0] selected_137;
wire selected_138;
wire selected_139;
wire [255:0] selected_140;
wire [31:0] selected_141;
wire [2:0] selected_142;
wire selected_143;
wire selected_144;
wire selected_145;
wire [9:0] selected_146;
wire [127:0] selected_147;
wire selected_148;
wire selected_149;
wire [127:0] selected_150;
wire selected_151;
wire selected_152;
wire [31:0] selected_153;
wire [1:0] selected_154;
wire [9:0] selected_155;
wire [12:0] selected_156;
wire selected_157;
wire selected_158;
wire selected_159;
wire [31:0] selected_160;
wire selected_161;
wire selected_162;
wire [31:0] selected_163;
wire selected_164;
wire selected_165;
wire [11:0] selected_166;
wire selected_167;
wire selected_168;
wire selected_169;
wire [9:0] selected_170;
wire [127:0] selected_171;
wire selected_172;
wire selected_173;
wire [127:0] selected_174;
wire selected_175;
wire selected_176;
wire selected_177;
wire selected_178;
wire [9:0] selected_179;
wire [127:0] selected_180;
wire selected_181;
wire selected_182;
wire [127:0] selected_183;
wire selected_184;
wire selected_185;
wire [63:0] selected_186;
wire [31:0] selected_187;
wire selected_188;
wire [4:0] selected_189;
wire selected_190;
wire selected_191;
wire [31:0] selected_192;
wire [511:0] selected_193;
wire selected_194;
wire selected_195;
wire [31:0] selected_196;
wire selected_197;
wire selected_198;
wire [31:0] selected_199;
wire [8:0] selected_200;
wire selected_201;
wire selected_202;
wire [31:0] selected_203;
wire [8:0] selected_204;
wire selected_205;
wire selected_206;
wire [63:0] selected_207;
wire [31:0] selected_208;
wire selected_209;
wire [4:0] selected_210;
wire selected_211;
wire selected_212;
wire [31:0] selected_213;
wire [511:0] selected_214;
wire selected_215;
wire selected_216;
wire [31:0] selected_217;
wire selected_218;
wire selected_219;
wire [31:0] selected_220;
wire [8:0] selected_221;
wire selected_222;
wire selected_223;
wire [31:0] selected_224;
wire [8:0] selected_225;
wire selected_226;
wire selected_227;
wire [63:0] selected_228;
wire [31:0] selected_229;
wire selected_230;
wire [4:0] selected_231;
wire selected_232;
wire selected_233;
wire [31:0] selected_234;
wire [511:0] selected_235;
wire selected_236;
wire selected_237;
wire [31:0] selected_238;
wire selected_239;
wire selected_240;
wire [31:0] selected_241;
wire [8:0] selected_242;
wire selected_243;
wire selected_244;
wire [31:0] selected_245;
wire [8:0] selected_246;
native_nine_control_plane #(.TOPOLOGY(TOPOLOGY),.LC_IMAGE_ID(LC_IMAGE_ID),.SERVICE_STALL_LIMIT(SERVICE_STALL_LIMIT)) controls(.clk(clk),.reset(reset),.mc_release_valid_i(mc_release_valid_i),.mc_release_sequence_i(mc_release_sequence_i),.mc_release_epoch_i(mc_release_epoch_i),.mc_deploy_valid_i(mc_deploy_valid_i),.mc_deploy_generation_i(mc_deploy_generation_i),.mc_release_ready_o(mc_release_ready_o),.mc_poison_o(mc_poison_o),.mc_image_valid_o(mc_image_valid_o),.mc_cfg_req_valid_i(mc_cfg_req_valid_i),.mc_cfg_req_op_i(mc_cfg_req_op_i),.mc_cfg_req_generation_i(mc_cfg_req_generation_i),.mc_cfg_req_address_i(mc_cfg_req_address_i),.mc_cfg_req_data_i(mc_cfg_req_data_i),.mc_cfg_req_total_bytes_i(mc_cfg_req_total_bytes_i),.mc_cfg_req_image_id_i(mc_cfg_req_image_id_i),.mc_cfg_req_topology_id_i(mc_cfg_req_topology_id_i),.mc_cfg_req_abi_id_i(mc_cfg_req_abi_id_i),.mc_cfg_req_capacity_id_i(mc_cfg_req_capacity_id_i),.mc_cfg_req_proof_i(mc_cfg_req_proof_i),.mc_cfg_rsp_ready_i(mc_cfg_rsp_ready_i),.mc_cfg_req_ready_o(mc_cfg_req_ready_o),.mc_cfg_rsp_valid_o(mc_cfg_rsp_valid_o),.mc_cfg_rsp_status_o(mc_cfg_rsp_status_o),.mc_cfg_rsp_data_o(mc_cfg_rsp_data_o),.mc_cfg_rsp_generation_o(mc_cfg_rsp_generation_o),.mc_life_o(mc_life_o),.mc_seq_o(mc_seq_o),.mc_trace_pc_o(mc_trace_pc_o),.mc_trace_retire_o(mc_trace_retire_o),.mc_trace_opcode_o(mc_trace_opcode_o),.mc_trace_pm_owner_o(mc_trace_pm_owner_o),.mc_trace_ireg_valid_o(mc_trace_ireg_valid_o),.mc_start_valid_i(mc_start_valid_i),.mc_start_credit_i(mc_start_credit_i),.mc_start_job_i(mc_start_job_i),.mc_start_epoch_i(mc_start_epoch_i),.mc_start_sequence_i(mc_start_sequence_i),.mc_start_generation_i(mc_start_generation_i),.mc_local_image_ids_i(mc_local_image_ids_i),.mc_local_enabled_i(mc_local_enabled_i),.mc_start_ready_o(mc_start_ready_o),.mc_frame_fault_count(mc_frame_fault_count),.mc_result_valid_o(mc_result_valid_o),.mc_result_ready_i(mc_result_ready_i),.mc_result_job_o(mc_result_job_o),.mc_result_epoch_o(mc_result_epoch_o),.mc_result_sequence_o(mc_result_sequence_o),.mc_result_status_o(mc_result_status_o),.mc_result_error_pc_o(mc_result_error_pc_o),.mc_result_source_o(mc_result_source_o),.mc_result_child_error_pc_o(mc_result_child_error_pc_o),.mc_result_failed_task_sequence_o(mc_result_failed_task_sequence_o),.mc_result_confirmed_read_bytes_o(mc_result_confirmed_read_bytes_o),.mc_result_confirmed_write_bytes_o(mc_result_confirmed_write_bytes_o),.mc_result_counter_overflow_o(mc_result_counter_overflow_o),.mc_result_saturated_o(mc_result_saturated_o),.mc_trace_live_tokens_o(mc_trace_live_tokens_o),.mc_trace_block_active_o(mc_trace_block_active_o),.mc_trace_terminal_full_o(mc_trace_terminal_full_o),.mc_trace_READY_full_o(mc_trace_READY_full_o),.mc_trace_aborting_o(mc_trace_aborting_o),.mc_recover_valid_i(mc_recover_valid_i),.mc_recover_ready_o(mc_recover_ready_o),.mc_protocol_fault_count_o(mc_protocol_fault_count_o),.memory_d_req_valid(memory_d_req_valid),.memory_d_req_ready(memory_d_req_ready),.memory_d_req_address(memory_d_req_address),.memory_d_req_tag(memory_d_req_tag),.memory_d_rsp_valid(memory_d_rsp_valid),.memory_d_rsp_ready(memory_d_rsp_ready),.memory_d_rsp_tag(memory_d_rsp_tag),.memory_d_rsp_data(memory_d_rsp_data),.memory_d_fence_valid(memory_d_fence_valid),.memory_d_fence_ready(memory_d_fence_ready),.memory_d_fence_generation(memory_d_fence_generation),.memory_d_fence_done_valid(memory_d_fence_done_valid),.memory_d_fence_done_ready(memory_d_fence_done_ready),.memory_d_fence_done_generation(memory_d_fence_done_generation),.memory_fault_valid(memory_fault_valid),.memory_fault_ready(memory_fault_ready),.memory_fault_kind(memory_fault_kind),.memory_fault_client(memory_fault_client),.memory_fault_local_tag(memory_fault_local_tag),.memory_fault_global_tag(memory_fault_global_tag),.memory_debug_beats(memory_debug_beats),.memory_debug_descriptors(memory_debug_descriptors),.memory_debug_generation(memory_debug_generation),.memory_d_req_write(memory_d_req_write),.memory_d_req_data(memory_d_req_data),.lc_session_valid(lc_session_valid),.lc_session_ready(lc_session_ready),.lc_session_generation(lc_session_generation),.lc_session_topology(lc_session_topology),.lc_cfg_valid(lc_cfg_valid),.lc_cfg_ready(lc_cfg_ready),.lc_cfg_op(lc_cfg_op),.lc_cfg_generation(lc_cfg_generation),.lc_cfg_abi(lc_cfg_abi),.lc_cfg_capacity(lc_cfg_capacity),.lc_cfg_crc(lc_cfg_crc),.lc_cfg_bytes(lc_cfg_bytes),.lc_cfg_address(lc_cfg_address),.lc_cfg_data(lc_cfg_data),.lc_cfg_rsp_valid(lc_cfg_rsp_valid),.lc_cfg_rsp_ready(lc_cfg_rsp_ready),.lc_cfg_status(lc_cfg_status),.lc_cfg_actual_crc(lc_cfg_actual_crc),.lc_certified(lc_certified),.lc_prepared(lc_prepared),.observe_P0_source(observe_P0_source),.lc_protocol_fault_cycles(lc_protocol_fault_cycles),.lc_pm_trace_valid(lc_pm_trace_valid),.lc_pm_trace_address(lc_pm_trace_address),.lc_retired_instructions(lc_retired_instructions),.P0_service_resource_m_lc_valid(selected_60),.P0_service_resource_m_lc_ready(selected_61),.P0_service_resource_m_lc_sop(selected_62),.P0_service_resource_m_lc_eop(selected_63),.P0_service_resource_m_lc_data(selected_64),.P0_service_resource_m_lr_valid(selected_65),.P0_service_resource_m_lr_ready(selected_66),.P0_service_resource_m_lr_sop(selected_67),.P0_service_resource_m_lr_eop(selected_68),.P0_service_resource_m_lr_data(selected_69),.P0_service_resource_m_a_valid(selected_70),.P0_service_resource_m_a_ready(selected_71),.P0_service_resource_m_a_data(selected_72),.P0_service_resource_m_a_session(selected_73),.P0_service_resource_m_a_beat(selected_74),.P0_service_s_req_valid(selected_86),.P0_service_s_req_write(selected_87),.P0_service_s_req_ready(selected_88),.P0_service_s_req_address(selected_89),.P0_service_s_req_data(selected_90),.P0_service_s_rsp_valid(selected_91),.P0_service_s_rsp_ready(selected_92),.P0_service_s_rsp_data(selected_93),.P0_service_s_rsp_error('0),.P0_service_source_failed(),.P0_service_quarantine(),.P0_service_protocol_faults(),.P0_service_resource_g_in_valid(selected_75),.P0_service_resource_g_in_ready(selected_76),.P0_service_resource_g_in_gate(selected_77),.P0_service_resource_g_in_up(selected_78),.P0_service_resource_g_in_gated(selected_79),.P0_service_resource_g_in_mask(selected_80),.P0_service_resource_g_out_valid(selected_81),.P0_service_resource_g_out_ready(selected_82),.P0_service_resource_g_out_data(selected_83),.P0_service_resource_g_out_mask(selected_84),.P0_service_resource_g_out_error(selected_85),.observe_P1_source(observe_P1_source),.P1_service_resource_m_lc_valid(selected_94),.P1_service_resource_m_lc_ready(selected_95),.P1_service_resource_m_lc_sop(selected_96),.P1_service_resource_m_lc_eop(selected_97),.P1_service_resource_m_lc_data(selected_98),.P1_service_resource_m_lr_valid(selected_99),.P1_service_resource_m_lr_ready(selected_100),.P1_service_resource_m_lr_sop(selected_101),.P1_service_resource_m_lr_eop(selected_102),.P1_service_resource_m_lr_data(selected_103),.P1_service_resource_m_a_valid(selected_104),.P1_service_resource_m_a_ready(selected_105),.P1_service_resource_m_a_data(selected_106),.P1_service_resource_m_a_session(selected_107),.P1_service_resource_m_a_beat(selected_108),.P1_service_s_req_valid(selected_120),.P1_service_s_req_write(selected_121),.P1_service_s_req_ready(selected_122),.P1_service_s_req_address(selected_123),.P1_service_s_req_data(selected_124),.P1_service_s_rsp_valid(selected_125),.P1_service_s_rsp_ready(selected_126),.P1_service_s_rsp_data(selected_127),.P1_service_s_rsp_error('0),.P1_service_source_failed(),.P1_service_quarantine(),.P1_service_protocol_faults(),.P1_service_resource_g_in_valid(selected_109),.P1_service_resource_g_in_ready(selected_110),.P1_service_resource_g_in_gate(selected_111),.P1_service_resource_g_in_up(selected_112),.P1_service_resource_g_in_gated(selected_113),.P1_service_resource_g_in_mask(selected_114),.P1_service_resource_g_out_valid(selected_115),.P1_service_resource_g_out_ready(selected_116),.P1_service_resource_g_out_data(selected_117),.P1_service_resource_g_out_mask(selected_118),.P1_service_resource_g_out_error(selected_119),.observe_P2_source(observe_P2_source),.P2_service_resource_m_lc_valid(selected_128),.P2_service_resource_m_lc_ready(selected_129),.P2_service_resource_m_lc_sop(selected_130),.P2_service_resource_m_lc_eop(selected_131),.P2_service_resource_m_lc_data(selected_132),.P2_service_resource_m_lr_valid(selected_133),.P2_service_resource_m_lr_ready(selected_134),.P2_service_resource_m_lr_sop(selected_135),.P2_service_resource_m_lr_eop(selected_136),.P2_service_resource_m_lr_data(selected_137),.P2_service_resource_m_a_valid(selected_138),.P2_service_resource_m_a_ready(selected_139),.P2_service_resource_m_a_data(selected_140),.P2_service_resource_m_a_session(selected_141),.P2_service_resource_m_a_beat(selected_142),.P2_service_s_req_valid(selected_143),.P2_service_s_req_write(selected_144),.P2_service_s_req_ready(selected_145),.P2_service_s_req_address(selected_146),.P2_service_s_req_data(selected_147),.P2_service_s_rsp_valid(selected_148),.P2_service_s_rsp_ready(selected_149),.P2_service_s_rsp_data(selected_150),.P2_service_s_rsp_error('0),.P2_service_source_failed(),.P2_service_quarantine(),.P2_service_protocol_faults(),.P2_service_resource_g_in_valid(),.P2_service_resource_g_in_ready('0),.P2_service_resource_g_in_gate(),.P2_service_resource_g_in_up(),.P2_service_resource_g_in_gated(),.P2_service_resource_g_in_mask(),.P2_service_resource_g_out_valid('0),.P2_service_resource_g_out_ready(),.P2_service_resource_g_out_data('0),.P2_service_resource_g_out_mask('0),.P2_service_resource_g_out_error('0),.observe_C0_source(observe_C0_source),.C0_service_s_req_valid(selected_12),.C0_service_s_req_write(selected_13),.C0_service_s_req_ready(selected_14),.C0_service_s_req_address(selected_15),.C0_service_s_req_data(selected_16),.C0_service_s_rsp_valid(selected_17),.C0_service_s_rsp_ready(selected_18),.C0_service_s_rsp_data(selected_19),.C0_service_s_rsp_error('0),.C0_service_resource_e_in_valid(selected_0),.C0_service_resource_e_in_ready(selected_1),.C0_service_resource_e_in_data(selected_2),.C0_service_resource_e_in_op(selected_3),.C0_service_resource_e_in_mask(selected_4),.C0_service_resource_e_in_shift(selected_5),.C0_service_resource_e_in_minus(selected_6),.C0_service_resource_e_out_valid(selected_7),.C0_service_resource_e_out_ready(selected_8),.C0_service_resource_e_out_data(selected_9),.C0_service_resource_e_out_clipped(selected_10),.C0_service_resource_e_out_error(selected_11),.observe_U0_source(observe_U0_source),.U0_service_s_req_valid(selected_176),.U0_service_s_req_write(selected_177),.U0_service_s_req_ready(selected_178),.U0_service_s_req_address(selected_179),.U0_service_s_req_data(selected_180),.U0_service_s_rsp_valid(selected_181),.U0_service_s_rsp_ready(selected_182),.U0_service_s_rsp_data(selected_183),.U0_service_s_rsp_error('0),.U0_service_resource_n_cmd_valid(selected_151),.U0_service_resource_n_cmd_ready(selected_152),.U0_service_resource_n_cmd_tag(selected_153),.U0_service_resource_n_cmd_mode(selected_154),.U0_service_resource_n_cmd_base(selected_155),.U0_service_resource_n_cmd_count(selected_156),.U0_service_resource_n_cmd_committed(selected_157),.U0_service_resource_n_abort_valid(selected_158),.U0_service_resource_n_abort_ready(selected_159),.U0_service_resource_n_abort_tag(selected_160),.U0_service_resource_n_rsp_valid(selected_161),.U0_service_resource_n_rsp_ready(selected_162),.U0_service_resource_n_rsp_tag(selected_163),.U0_service_resource_n_rsp_error(selected_164),.U0_service_resource_n_rsp_aborted(selected_165),.U0_service_resource_n_rsp_writes(selected_166),.U0_service_resource_n_s_req_valid(selected_167),.U0_service_resource_n_s_req_write(selected_168),.U0_service_resource_n_s_req_ready(selected_169),.U0_service_resource_n_s_req_address(selected_170),.U0_service_resource_n_s_req_data(selected_171),.U0_service_resource_n_s_rsp_valid(selected_172),.U0_service_resource_n_s_rsp_ready(selected_173),.U0_service_resource_n_s_rsp_data(selected_174),.U0_service_resource_n_s_rsp_error(selected_175),.observe_J0_source(observe_J0_source),.J0_service_s_req_valid(selected_52),.J0_service_s_req_write(selected_53),.J0_service_s_req_ready(selected_54),.J0_service_s_req_address(selected_55),.J0_service_s_req_data(selected_56),.J0_service_s_rsp_valid(selected_57),.J0_service_s_rsp_ready(selected_58),.J0_service_s_rsp_data(selected_59),.J0_service_s_rsp_error('0),.J0_service_resource_e_in_valid(selected_40),.J0_service_resource_e_in_ready(selected_41),.J0_service_resource_e_in_data(selected_42),.J0_service_resource_e_in_op(selected_43),.J0_service_resource_e_in_mask(selected_44),.J0_service_resource_e_in_shift(selected_45),.J0_service_resource_e_in_minus(selected_46),.J0_service_resource_e_out_valid(selected_47),.J0_service_resource_e_out_ready(selected_48),.J0_service_resource_e_out_data(selected_49),.J0_service_resource_e_out_clipped(selected_50),.J0_service_resource_e_out_error(selected_51),.observe_F0_source(observe_F0_source),.F0_service_s_req_valid(selected_32),.F0_service_s_req_write(selected_33),.F0_service_s_req_ready(selected_34),.F0_service_s_req_address(selected_35),.F0_service_s_req_data(selected_36),.F0_service_s_rsp_valid(selected_37),.F0_service_s_rsp_ready(selected_38),.F0_service_s_rsp_data(selected_39),.F0_service_s_rsp_error('0),.F0_service_resource_e_in_valid(selected_20),.F0_service_resource_e_in_ready(selected_21),.F0_service_resource_e_in_data(selected_22),.F0_service_resource_e_in_op(selected_23),.F0_service_resource_e_in_mask(selected_24),.F0_service_resource_e_in_shift(selected_25),.F0_service_resource_e_in_minus(selected_26),.F0_service_resource_e_out_valid(selected_27),.F0_service_resource_e_out_ready(selected_28),.F0_service_resource_e_out_data(selected_29),.F0_service_resource_e_out_clipped(selected_30),.F0_service_resource_e_out_error(selected_31),.observe_U1_source(observe_U1_source),.U1_service_s_req_valid(),.U1_service_s_req_write(),.U1_service_s_req_ready('0),.U1_service_s_req_address(),.U1_service_s_req_data(),.U1_service_s_rsp_valid('0),.U1_service_s_rsp_ready(),.U1_service_s_rsp_data('0),.U1_service_s_rsp_error('0),.U1_service_resource_n_cmd_valid(),.U1_service_resource_n_cmd_ready('0),.U1_service_resource_n_cmd_tag(),.U1_service_resource_n_cmd_mode(),.U1_service_resource_n_cmd_base(),.U1_service_resource_n_cmd_count(),.U1_service_resource_n_cmd_committed(),.U1_service_resource_n_abort_valid(),.U1_service_resource_n_abort_ready('0),.U1_service_resource_n_abort_tag(),.U1_service_resource_n_rsp_valid('0),.U1_service_resource_n_rsp_ready(),.U1_service_resource_n_rsp_tag('0),.U1_service_resource_n_rsp_error('0),.U1_service_resource_n_rsp_aborted('0),.U1_service_resource_n_rsp_writes('0),.U1_service_resource_n_s_req_valid('0),.U1_service_resource_n_s_req_write('0),.U1_service_resource_n_s_req_ready(),.U1_service_resource_n_s_req_address('0),.U1_service_resource_n_s_req_data('0),.U1_service_resource_n_s_rsp_valid(),.U1_service_resource_n_s_rsp_ready('0),.U1_service_resource_n_s_rsp_data(),.U1_service_resource_n_s_rsp_error(),.observe_J1_source(observe_J1_source),.J1_service_s_req_valid(),.J1_service_s_req_write(),.J1_service_s_req_ready('0),.J1_service_s_req_address(),.J1_service_s_req_data(),.J1_service_s_rsp_valid('0),.J1_service_s_rsp_ready(),.J1_service_s_rsp_data('0),.J1_service_s_rsp_error('0),.J1_service_resource_e_in_valid(),.J1_service_resource_e_in_ready('0),.J1_service_resource_e_in_data(),.J1_service_resource_e_in_op(),.J1_service_resource_e_in_mask(),.J1_service_resource_e_in_shift(),.J1_service_resource_e_in_minus(),.J1_service_resource_e_out_valid('0),.J1_service_resource_e_out_ready(),.J1_service_resource_e_out_data('0),.J1_service_resource_e_out_clipped('0),.J1_service_resource_e_out_error('0),.P0_M_mc_req_valid(selected_184),.P0_M_mc_req_ready(selected_185),.P0_M_mc_req_address(selected_186),.P0_M_mc_req_tag(selected_187),.P0_M_mc_req_channel(selected_188),.P0_M_mc_req_record_beats(selected_189),.P0_M_mc_rsp_valid(selected_190),.P0_M_mc_rsp_ready(selected_191),.P0_M_mc_rsp_tag(selected_192),.P0_M_mc_rsp_data(selected_193),.P0_M_mc_close_valid(selected_194),.P0_M_mc_close_ready(selected_195),.P0_M_mc_close_tag_base(selected_196),.P0_M_mc_fence_req_valid(selected_197),.P0_M_mc_fence_req_ready(selected_198),.P0_M_mc_fence_req_cookie(selected_199),.P0_M_mc_fence_req_epoch(selected_200),.P0_M_mc_fence_done_valid(selected_201),.P0_M_mc_fence_done_ready(selected_202),.P0_M_mc_fence_done_cookie(selected_203),.P0_M_mc_fence_done_epoch(selected_204),.P1_M_mc_req_valid(selected_205),.P1_M_mc_req_ready(selected_206),.P1_M_mc_req_address(selected_207),.P1_M_mc_req_tag(selected_208),.P1_M_mc_req_channel(selected_209),.P1_M_mc_req_record_beats(selected_210),.P1_M_mc_rsp_valid(selected_211),.P1_M_mc_rsp_ready(selected_212),.P1_M_mc_rsp_tag(selected_213),.P1_M_mc_rsp_data(selected_214),.P1_M_mc_close_valid(selected_215),.P1_M_mc_close_ready(selected_216),.P1_M_mc_close_tag_base(selected_217),.P1_M_mc_fence_req_valid(selected_218),.P1_M_mc_fence_req_ready(selected_219),.P1_M_mc_fence_req_cookie(selected_220),.P1_M_mc_fence_req_epoch(selected_221),.P1_M_mc_fence_done_valid(selected_222),.P1_M_mc_fence_done_ready(selected_223),.P1_M_mc_fence_done_cookie(selected_224),.P1_M_mc_fence_done_epoch(selected_225),.P2_M_mc_req_valid(selected_226),.P2_M_mc_req_ready(selected_227),.P2_M_mc_req_address(selected_228),.P2_M_mc_req_tag(selected_229),.P2_M_mc_req_channel(selected_230),.P2_M_mc_req_record_beats(selected_231),.P2_M_mc_rsp_valid(selected_232),.P2_M_mc_rsp_ready(selected_233),.P2_M_mc_rsp_tag(selected_234),.P2_M_mc_rsp_data(selected_235),.P2_M_mc_close_valid(selected_236),.P2_M_mc_close_ready(selected_237),.P2_M_mc_close_tag_base(selected_238),.P2_M_mc_fence_req_valid(selected_239),.P2_M_mc_fence_req_ready(selected_240),.P2_M_mc_fence_req_cookie(selected_241),.P2_M_mc_fence_req_epoch(selected_242),.P2_M_mc_fence_done_valid(selected_243),.P2_M_mc_fence_done_ready(selected_244),.P2_M_mc_fence_done_cookie(selected_245),.P2_M_mc_fence_done_epoch(selected_246));
if(1)begin:P0
m_native_leaf_s32 M(.clk(clk),.reset(reset),.lc_valid(selected_60),.lc_ready(selected_61),.lc_sop(selected_62),.lc_eop(selected_63),.lc_data(selected_64),.lr_valid(selected_65),.lr_ready(selected_66),.lr_sop(selected_67),.lr_eop(selected_68),.lr_data(selected_69),.a_valid(selected_70),.a_ready(selected_71),.a_data(selected_72),.a_session(selected_73),.a_beat(selected_74),.mc_req_valid(selected_184),.mc_req_ready(selected_185),.mc_req_address(selected_186),.mc_req_tag(selected_187),.mc_req_channel(selected_188),.mc_req_record_beats(selected_189),.mc_close_valid(selected_194),.mc_close_ready(selected_195),.mc_close_tag_base(selected_196),.mc_rsp_valid(selected_190),.mc_rsp_ready(selected_191),.mc_rsp_tag(selected_192),.mc_rsp_data(selected_193),.mc_fence_req_valid(selected_197),.mc_fence_req_ready(selected_198),.mc_fence_req_cookie(selected_199),.mc_fence_req_epoch(selected_200),.mc_fence_done_valid(selected_201),.mc_fence_done_ready(selected_202),.mc_fence_done_cookie(selected_203),.mc_fence_done_epoch(selected_204),.fault_interrupt());
g_s32 G(.clk(clk),.reset(reset),.in_valid(selected_75),.in_ready(selected_76),.in_gate(selected_77),.in_up(selected_78),.in_gated(selected_79),.in_mask(selected_80),.out_valid(selected_81),.out_ready(selected_82),.out_data(selected_83),.out_mask(selected_84),.out_error(selected_85));
local_s_p S(.clk(clk),.reset(reset),.req_valid(selected_86),.req_write(selected_87),.req_addr(selected_89),.req_data(selected_90),.req_ready(selected_88),.rsp_valid(selected_91),.rsp_ready(selected_92),.rsp_data(selected_93),.load_valid('0),.load_bank('0),.load_a_wide('0),.load_b_wide('0),.load_reuse_b('0),.load_rows('0),.load_tiles('0),.load_a_base('0),.load_b_base('0),.load_ready(),.done_valid(),.done_error(),.done_take('0),.a_ready('0),.b_ready('0),.a_valid(),.a_bank(),.a_wide(),.b_valid(),.b_bank(),.b_wide(),.b_half(),.a_row(),.a_tile(),.b_tile(),.a_data(),.b_data());
end
if(1)begin:P1
m_native_leaf_s32 M(.clk(clk),.reset(reset),.lc_valid(selected_94),.lc_ready(selected_95),.lc_sop(selected_96),.lc_eop(selected_97),.lc_data(selected_98),.lr_valid(selected_99),.lr_ready(selected_100),.lr_sop(selected_101),.lr_eop(selected_102),.lr_data(selected_103),.a_valid(selected_104),.a_ready(selected_105),.a_data(selected_106),.a_session(selected_107),.a_beat(selected_108),.mc_req_valid(selected_205),.mc_req_ready(selected_206),.mc_req_address(selected_207),.mc_req_tag(selected_208),.mc_req_channel(selected_209),.mc_req_record_beats(selected_210),.mc_close_valid(selected_215),.mc_close_ready(selected_216),.mc_close_tag_base(selected_217),.mc_rsp_valid(selected_211),.mc_rsp_ready(selected_212),.mc_rsp_tag(selected_213),.mc_rsp_data(selected_214),.mc_fence_req_valid(selected_218),.mc_fence_req_ready(selected_219),.mc_fence_req_cookie(selected_220),.mc_fence_req_epoch(selected_221),.mc_fence_done_valid(selected_222),.mc_fence_done_ready(selected_223),.mc_fence_done_cookie(selected_224),.mc_fence_done_epoch(selected_225),.fault_interrupt());
g_s32 G(.clk(clk),.reset(reset),.in_valid(selected_109),.in_ready(selected_110),.in_gate(selected_111),.in_up(selected_112),.in_gated(selected_113),.in_mask(selected_114),.out_valid(selected_115),.out_ready(selected_116),.out_data(selected_117),.out_mask(selected_118),.out_error(selected_119));
local_s_p S(.clk(clk),.reset(reset),.req_valid(selected_120),.req_write(selected_121),.req_addr(selected_123),.req_data(selected_124),.req_ready(selected_122),.rsp_valid(selected_125),.rsp_ready(selected_126),.rsp_data(selected_127),.load_valid('0),.load_bank('0),.load_a_wide('0),.load_b_wide('0),.load_reuse_b('0),.load_rows('0),.load_tiles('0),.load_a_base('0),.load_b_base('0),.load_ready(),.done_valid(),.done_error(),.done_take('0),.a_ready('0),.b_ready('0),.a_valid(),.a_bank(),.a_wide(),.b_valid(),.b_bank(),.b_wide(),.b_half(),.a_row(),.a_tile(),.b_tile(),.a_data(),.b_data());
end
if(1)begin:P2
m_native_leaf_s32 M(.clk(clk),.reset(reset),.lc_valid(selected_128),.lc_ready(selected_129),.lc_sop(selected_130),.lc_eop(selected_131),.lc_data(selected_132),.lr_valid(selected_133),.lr_ready(selected_134),.lr_sop(selected_135),.lr_eop(selected_136),.lr_data(selected_137),.a_valid(selected_138),.a_ready(selected_139),.a_data(selected_140),.a_session(selected_141),.a_beat(selected_142),.mc_req_valid(selected_226),.mc_req_ready(selected_227),.mc_req_address(selected_228),.mc_req_tag(selected_229),.mc_req_channel(selected_230),.mc_req_record_beats(selected_231),.mc_close_valid(selected_236),.mc_close_ready(selected_237),.mc_close_tag_base(selected_238),.mc_rsp_valid(selected_232),.mc_rsp_ready(selected_233),.mc_rsp_tag(selected_234),.mc_rsp_data(selected_235),.mc_fence_req_valid(selected_239),.mc_fence_req_ready(selected_240),.mc_fence_req_cookie(selected_241),.mc_fence_req_epoch(selected_242),.mc_fence_done_valid(selected_243),.mc_fence_done_ready(selected_244),.mc_fence_done_cookie(selected_245),.mc_fence_done_epoch(selected_246),.fault_interrupt());
g_s32 G(.clk(clk),.reset(reset),.in_valid('0),.in_ready(),.in_gate('0),.in_up('0),.in_gated('0),.in_mask('0),.out_valid(),.out_ready('0),.out_data(),.out_mask(),.out_error());
local_s_p S(.clk(clk),.reset(reset),.req_valid(selected_143),.req_write(selected_144),.req_addr(selected_146),.req_data(selected_147),.req_ready(selected_145),.rsp_valid(selected_148),.rsp_ready(selected_149),.rsp_data(selected_150),.load_valid('0),.load_bank('0),.load_a_wide('0),.load_b_wide('0),.load_reuse_b('0),.load_rows('0),.load_tiles('0),.load_a_base('0),.load_b_base('0),.load_ready(),.done_valid(),.done_error(),.done_take('0),.a_ready('0),.b_ready('0),.a_valid(),.a_bank(),.a_wide(),.b_valid(),.b_bank(),.b_wide(),.b_half(),.a_row(),.a_tile(),.b_tile(),.a_data(),.b_data());
end
if(1)begin:U0
n_s32_mod N(.clk(clk),.reset(reset),.cmd_valid(selected_151),.cmd_ready(selected_152),.cmd_tag(selected_153),.cmd_mode(selected_154),.cmd_base(selected_155),.cmd_count(selected_156),.cmd_committed(selected_157),.abort_valid(selected_158),.abort_ready(selected_159),.abort_tag(selected_160),.rsp_valid(selected_161),.rsp_ready(selected_162),.rsp_tag(selected_163),.rsp_error(selected_164),.rsp_aborted(selected_165),.rsp_writes(selected_166),.s_req_valid(selected_167),.s_req_ready(selected_169),.s_req_write(selected_168),.s_req_address(selected_170),.s_req_data(selected_171),.s_rsp_valid(selected_172),.s_rsp_ready(selected_173),.s_rsp_data(selected_174),.s_rsp_error(selected_175));
block_v2_e_compact E(.clk(clk),.reset(reset),.in_valid('0),.in_ready(),.in_op('0),.in_shift('0),.in_data('0),.out_valid(),.out_ready('0),.out_data(),.out_error(),.out_saturated());
local_s_base S(.clk(clk),.reset(reset),.req_valid(selected_176),.req_write(selected_177),.req_addr(selected_179),.req_data(selected_180),.req_ready(selected_178),.rsp_valid(selected_181),.rsp_ready(selected_182),.rsp_data(selected_183));
end
if(1)begin:U1
n_s32_mod N(.clk(clk),.reset(reset),.cmd_valid('0),.cmd_ready(),.cmd_tag('0),.cmd_mode('0),.cmd_base('0),.cmd_count('0),.cmd_committed('0),.abort_valid('0),.abort_ready(),.abort_tag('0),.rsp_valid(),.rsp_ready('0),.rsp_tag(),.rsp_error(),.rsp_aborted(),.rsp_writes(),.s_req_valid(),.s_req_ready('0),.s_req_write(),.s_req_address(),.s_req_data(),.s_rsp_valid('0),.s_rsp_ready(),.s_rsp_data('0),.s_rsp_error('0));
block_v2_e_compact E(.clk(clk),.reset(reset),.in_valid('0),.in_ready(),.in_op('0),.in_shift('0),.in_data('0),.out_valid(),.out_ready('0),.out_data(),.out_error(),.out_saturated());
local_s_base S(.clk(clk),.reset(reset),.req_valid('0),.req_write('0),.req_addr('0),.req_data('0),.req_ready(),.rsp_valid(),.rsp_ready('0),.rsp_data());
end
if(1)begin:C0
r_stream_local R(.clk(clk),.reset(reset),.load_valid('0),.load_ready(),.load_target('0),.load_index('0),.load_data('0),.rd_bank('0),.rd_index('0),.rd_valid('0),.rd_ready(),.rd_rsp_valid(),.rd_rsp_ready('0),.rd_data(),.cmd_valid('0),.cmd_ready(),.cmd_op('0),.cmd_rows('0),.cmd_role('0),.cmd_clear('0),.cmd_mode('0),.rsp_valid(),.rsp_ready('0),.rsp_error(),.rsp_data());
block_v2_g G(.clk(clk),.reset(reset),.in_valid('0),.in_ready(),.in_fn('0),.in_gated('0),.in_x('0),.in_gate('0),.out_valid(),.out_ready('0),.out_data(),.out_error(),.out_saturated());
block_v2_e_compact E(.clk(clk),.reset(reset),.in_valid('0),.in_ready(),.in_op('0),.in_shift('0),.in_data('0),.out_valid(),.out_ready('0),.out_data(),.out_error(),.out_saturated());
e_s32_mac_ap64 E32(.clk(clk),.reset(reset),.in_valid(selected_0),.in_ready(selected_1),.in_data(selected_2),.in_op(selected_3),.in_mask(selected_4),.in_shift(selected_5),.in_minus(selected_6),.out_valid(selected_7),.out_ready(selected_8),.out_data(selected_9),.out_clipped(selected_10),.out_error(selected_11));
local_s_base S(.clk(clk),.reset(reset),.req_valid(selected_12),.req_write(selected_13),.req_addr(selected_15),.req_data(selected_16),.req_ready(selected_14),.rsp_valid(selected_17),.rsp_ready(selected_18),.rsp_data(selected_19));
end
if(1)begin:F0
block_v2_g G(.clk(clk),.reset(reset),.in_valid('0),.in_ready(),.in_fn('0),.in_gated('0),.in_x('0),.in_gate('0),.out_valid(),.out_ready('0),.out_data(),.out_error(),.out_saturated());
block_v2_e_compact E(.clk(clk),.reset(reset),.in_valid('0),.in_ready(),.in_op('0),.in_shift('0),.in_data('0),.out_valid(),.out_ready('0),.out_data(),.out_error(),.out_saturated());
e_s32_mac_ap64 E32(.clk(clk),.reset(reset),.in_valid(selected_20),.in_ready(selected_21),.in_data(selected_22),.in_op(selected_23),.in_mask(selected_24),.in_shift(selected_25),.in_minus(selected_26),.out_valid(selected_27),.out_ready(selected_28),.out_data(selected_29),.out_clipped(selected_30),.out_error(selected_31));
local_s_base S(.clk(clk),.reset(reset),.req_valid(selected_32),.req_write(selected_33),.req_addr(selected_35),.req_data(selected_36),.req_ready(selected_34),.rsp_valid(selected_37),.rsp_ready(selected_38),.rsp_data(selected_39));
end
if(1)begin:J0
e_s32_mac_ap64 E32(.clk(clk),.reset(reset),.in_valid(selected_40),.in_ready(selected_41),.in_data(selected_42),.in_op(selected_43),.in_mask(selected_44),.in_shift(selected_45),.in_minus(selected_46),.out_valid(selected_47),.out_ready(selected_48),.out_data(selected_49),.out_clipped(selected_50),.out_error(selected_51));
local_s_base S(.clk(clk),.reset(reset),.req_valid(selected_52),.req_write(selected_53),.req_addr(selected_55),.req_data(selected_56),.req_ready(selected_54),.rsp_valid(selected_57),.rsp_ready(selected_58),.rsp_data(selected_59));
transaction6k T(.clk(clk),.reset(reset),.begin_valid('0),.begin_ready(),.begin_owner('0),.begin_generation('0),.begin_words('0),.write_valid('0),.write_ready(),.write_index('0),.write_data('0),.commit_valid('0),.commit_ready(),.revoke_valid('0),.revoke_ready(),.read_valid(),.read_take('0),.read_index(),.read_data(),.read_last(),.owner(),.generation(),.word_count(),.release_valid('0),.release_ready(),.busy(),.sealed(),.committed(),.protocol_error(),.debug_state());
end
if(1)begin:J1
e_s32_mac_ap64 E32(.clk(clk),.reset(reset),.in_valid('0),.in_ready(),.in_data('0),.in_op('0),.in_mask('0),.in_shift('0),.in_minus('0),.out_valid(),.out_ready('0),.out_data(),.out_clipped(),.out_error());
local_s_base S(.clk(clk),.reset(reset),.req_valid('0),.req_write('0),.req_addr('0),.req_data('0),.req_ready(),.rsp_valid(),.rsp_ready('0),.rsp_data());
transaction6k T(.clk(clk),.reset(reset),.begin_valid('0),.begin_ready(),.begin_owner('0),.begin_generation('0),.begin_words('0),.write_valid('0),.write_ready(),.write_index('0),.write_data('0),.commit_valid('0),.commit_ready(),.revoke_valid('0),.revoke_ready(),.read_valid(),.read_take('0),.read_index(),.read_data(),.read_last(),.owner(),.generation(),.word_count(),.release_valid('0),.release_ready(),.busy(),.sealed(),.committed(),.protocol_error(),.debug_state());
end
endmodule
