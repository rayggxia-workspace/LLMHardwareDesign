# -*- coding: utf-8 -*-
"""Build/check Step1 static-family research artifacts. No RTL/model/network execution."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT_COMMIT = 'e44c4f5f492b2ef0fef12846dd25c1b1ea637664'
MODEL_IDS = ('qwen25', 'qwen3', 'llama', 'gemma', 'phi', 'qwen35', 'granite', 'falcon')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


CAPABILITIES = {
 'C01_MATRIX': ('M', '分块投影/QK/PV/跨K累加，单结果上下文'),
 'C02_RMS': ('N', '完整范围RMS、gamma/原值回放'),
 'C03_SOFTMAX': ('N', '完整行统计、EXP保存及概率回放'),
 'C04_VECTOR': ('E', '偏置/残差/缩放/选择等S16基础算术'),
 'C05_ROPE': ('E+常量/布局', '相邻pair旋转、部分范围与频率来源'),
 'C06_PACK': ('外侧适配+E子集', '四S32/八S16/两S16等载体拆拼和tail'),
 'C07_LAYOUT': ('外侧适配', 'M n-major、Slice/Transpose/Repeat/有界Gather'),
 'C08_REPLAY': ('S/临时存储服务', '原值/EXP/gamma/分支结果物化与回放'),
 'C09_STATIC_CONTROL': ('共同预制控制', '固定ROM/共享局部FSM/有界循环及事件等待'),
 'C10_SILU_GATE': ('G', '两lane SiLU及紧邻门乘'),
 'C11_GELU_GATE': ('G', 'GELU_tanh及门乘'),
 'C12_QK_NORM': ('N', '按真实头维度分别归一化'),
 'C13_RMS0_PARAMS': ('参数/外侧适配', 'gamma=1+weight，不能冒充N新mode'),
 'C14_SIGMOID_GATE': ('G', 'Sigmoid输出门，绑定gated/ungated尺度'),
 'C15_CONV4': ('R', '四tap深度卷积、history候选与保存'),
 'C16_GDN': ('R', 'GDN key/query/update/readout'),
 'C17_SSM': ('R', 'SSM状态、逐元素decay载入、inject/skip'),
 'C18_COEFF': ('新增数值能力待确定', '负指数/dt/decay/inject及范围/精度'),
 'C19_ROUTER': ('N+外侧索引', '40选8 ID、selected score及专家数据索引'),
 'C20_WIDE_MERGE': ('新增宽算术待确定', '八专家共同单位加权归并和gain'),
 'C21_STATE_VERSION': ('R外侧状态控制', '多tile状态/history/位置版本与发布'),
 'C22_FORK_JOIN': ('外侧有限保持', '固定分支配对/生存期/不同完成延迟'),
 'C23_CONV_BIAS': ('新增或已证明分解待确定', 'Falcon卷积bias在SiLU前正确加到共同单位'),
 'C24_LONG_SOFTMAX': ('新增算法/资源方案待确定', '若接收超过65535的完整逻辑行，原N计数不足'),
 'C25_WIDE_CONVERT': ('条件化复用/专用分解/额外能力待定', '若某合法角色路线确需宽转换，优先复用M.op5等已有操作；不能以E13冒充S64，也不强制独立通用单元'),
 'C26_FULL_MODEL_BOUNDARY': ('待补全产品工作流', 'embedding/位置mask/末Norm/LM head/采样边界'),
 'C27_MUP': ('参数+数值链', 'Falcon分段MuP/K与分支输入输出独立缩放'),
 'C28_SOFTPLUS': ('G+后续数值链', 'QwenGDN/Falcon的dt Softplus，后续decay不由G直接提供'),
}


GRAMMARS = {
 'DENSE_ATTN_FFN': ['input_norm', 'fork_qkv', 'qkv_project_and_optional_bias',
   'optional_qk_head_norm', 'rope_and_layout', 'kv_data_boundary', 'full_D_qk',
   'score_scale_mask', 'full_row_softmax', 'pv', 'optional_context_sigmoid_gate',
   'out_project', 'optional_post_attention_norm', 'residual1', 'pre_ffn_norm',
   'gate_up_project', 'activation_times_up', 'all_K_down_project',
   'optional_post_ffn_norm', 'residual2'],
 'GDN_FFN': ['input_rms0', 'qkv_z_a_b_project', 'conv_history_step_and_save',
   'conv_cast_silu_split', 'repeat_qk16to32', 'qk_L2_full128', 'query_only_scale',
   'coefficients', 'state_update_tiles', 'save_full_value_head',
   'rms128_per_value_head', 'silu_z_times_normalized_readout', 'out_project',
   'residual1', 'pre_ffn_rms0', 'gate_up_silu_down', 'residual2'],
 'ATTN_MOE': ['input_rms', 'qkv_rope_qk', 'config_score_scale_mask',
   'full_row_softmax_pv_out', 'attention_gain022', 'residual1', 'pre_moe_rms',
   'router40', 'top8_ID', 'gather_selected_logits', 'routing_softmax8',
   'expert_rank_loop8_same_M_G', 'wide_weighted_merge', 'moe_gain022', 'residual2'],
 'ATTN_SSM_FFN': ['input_rms', 'fork_attention_ssm',
   'attention_qkv_Kscale_rope_qk_softmax_pv_out_scale',
   'ssm_project8736_and_mup', 'conv4608_bias_then_silu',
   'B_C_group_broadcast_and_coefficients', 'state_update_tiles',
   'silu_z_times_readout', 'global_rms4096', 'ssm_out_project_scale',
   'join_same_token_attention_ssm', 'residual1', 'pre_ffn_rms',
   'gate_up_silu_down_with_distinct_mup', 'residual2'],
}


ELISION_PROOFS = [
 ('P01_ROLE', ['generic_role_id'],
  '每个静态节点的源op/目的operand、阶段及唯一owner已由完整程序证明；只允许已接收产品入口。',
  ['native_opcode', 'local_phase', 'payload_ready_valid', 'error'],
  '删除独立role_id字段；原生op和局部状态仍选择实际端口/响应解释。'),
 ('P02_TYPE', ['generic_dtype_id', 'generic_frac_bits_header'],
  '逐边logical/carrier格式、尺度、转换和所有producer/consumer已编译；该边不使用动态重定标。',
  ['native_wide_half_flags', 'native_shift', 'saturation_policy', 'dynamic_numeric_epoch_if_required'],
  '格式/shift来自固定ROM/常量选择；不是运行时通用类型解释器。'),
 ('P03_LAYOUT', ['per_packet_layout_id', 'per_packet_shape_descriptor'],
  'shape/布局/别名与循环覆盖已离线证明，目标缓冲/尾字独占，只有受界定长度可变。',
  ['address_or_index_counter', 'actual_valid_count', 'native_tail_count', 'write_ack_wait'],
  '固定寻址模板和计数器替代通用layout标签；实际地址/进度不能消失。'),
 ('P04_ORDER', ['per_packet_task_id'],
  '每资源单一owner、响应按序且归属唯一，复位/取消后已排空；不存在未归属迟到响应。',
  ['outstanding_or_phase_state', 'accepted_vs_completed_count', 'drain_state', 'epoch_if_stale_possible'],
  '用当前调用/少量本地在途状态归属响应；外存协议未确定时不能宣称全系统tag可删。'),
 ('P05_BUFFER', ['generic_handle_id', 'generic_refcount_table'],
  '本产品固定buffer图已证明生命周期，fork消费者集合/数目固定，无外部共享别名或提前覆盖。',
  ['buffer_occupied_or_phase', 'pending_consumer_bits_if_needed', 'last_consumer_release', 'write_visibility'],
  '可用固定槽/已编译释放事件代替任意handle表；分支保持与释放条件仍必须实现。'),
 ('P06_ROUTER_RANGE', ['ID_type_tag', 'redundant_ID_range_check_if_formally_proven'],
  'N.TOP_LOAD的ID只由固定0..39序列产生；TopK只复制这些ID，来源路径及地址公式已证明。',
  ['selected_expert_ID_values', 'rank', 'rank_completion_mask', 'expert_data_ready'],
  '可去掉重复类型/范围判断，但动态ID及其数据选择、rank完整性不能变成编译常量。'),
 ('P07_OWNER', ['per_packet_model_id', 'general_runtime_resource_dispatch_table'],
  '产品由永久选择锁定，原生端口唯一owner，完整静态时间/事件顺序不发生多源竞争。',
  ['native_owner_fields_where_required', 'local_request_hold', 'resource_busy_or_validity', 'event_wait'],
  '永久入口/常量和固定状态转移代替每包模型标签；不能删除R原生owner/epoch/position编码。'),
 ('P08_JOIN', ['general_join_key_comparator_if_unnecessary'],
  '两分支始终由同一静态调用产生，位置/迭代归属由本地索引与排空证明，缓冲不会混代。',
  ['per_branch_arrival_bits', 'stable_operand_storage', 'iteration_or_position', 'failure_drain'],
  '固定双/三槽和到齐状态可替代任意key匹配器；不能只把valid相与。'),
]


def build(input_root):
    data_root = input_root / 'work/Melodydt/151'
    family = read_json(data_root / 'family-spec.json')
    sources = read_json(data_root / 'family-source-index.json')
    obligations = read_json(data_root / 'sample-connection-obligations.json')
    layers = {t['layer_type_id']: t for t in family['layer_types']}
    source_models = {m['model_id']: m for m in family['models']}
    caps = [{'id': k, 'logical_location': v[0], 'function': v[1],
             'requirement_origin': 'all_legal_data_plane_target' if k == 'C25_WIDE_CONVERT' else 'whole_product_workflow_to_be_completed' if k == 'C26_FULL_MODEL_BOUNDARY' else 'source_algorithm_or_selected_mapping_requirement',
             'common_base_required_if_selected_product_uses_it': True,
             'new_system_implementation_or_qualification_claim': False}
            for k, v in CAPABILITIES.items()]
    products = []
    for ordinal, mid in enumerate(MODEL_IDS):
        m = source_models[mid]
        req = set(['C01_MATRIX', 'C02_RMS', 'C03_SOFTMAX', 'C04_VECTOR',
                   'C05_ROPE', 'C06_PACK', 'C07_LAYOUT', 'C08_REPLAY',
                   'C09_STATIC_CONTROL', 'C22_FORK_JOIN',
                   'C26_FULL_MODEL_BOUNDARY'])
        req.add('C11_GELU_GATE' if mid == 'gemma' else 'C10_SILU_GATE')
        if mid in ('qwen3', 'gemma', 'qwen35'):
            req.add('C12_QK_NORM')
        if mid in ('gemma', 'qwen35'):
            req.add('C13_RMS0_PARAMS')
        if mid == 'qwen35':
            req.update(['C14_SIGMOID_GATE', 'C15_CONV4', 'C16_GDN',
                        'C18_COEFF', 'C21_STATE_VERSION', 'C28_SOFTPLUS'])
        if mid == 'falcon':
            req.update(['C15_CONV4', 'C17_SSM', 'C18_COEFF', 'C21_STATE_VERSION',
                        'C23_CONV_BIAS', 'C27_MUP', 'C28_SOFTPLUS'])
        if mid == 'granite':
            req.update(['C19_ROUTER', 'C20_WIDE_MERGE'])
        prods_layers = []
        for lid in m['layer_type_ids']:
            l = layers[lid]
            grammar = ('GDN_FFN' if 'gdn' in l else 'ATTN_SSM_FFN' if 'ssm' in l
                       else 'ATTN_MOE' if 'moe' in l else 'DENSE_ATTN_FFN')
            a = l.get('attention')
            prods_layers.append({
              'layer_type_id': lid, 'grammar_id': grammar,
              'source_normalization_sites': copy.deepcopy(l['normalization_sites']),
              'source_attention': copy.deepcopy(a),
              'source_recurrent_or_expert': copy.deepcopy(l.get('gdn') or l.get('ssm') or l.get('moe')),
              'structural_options_are_permanent_not_runtime_graph_choices': True,
              'native_graph_optimization_status': 'not_applied_or_proven_by_this_specification',
            })
        dynamic = ['token_values', 'request_length_and_current_position_within_accepted_limits',
                   'prefill_or_decode_branch_of_fixed_program', 'KV_contents_and_legal_window_progress',
                   'quantization_scale_if_data_dependent_scheme_is_accepted',
                   'ready_valid_latency_and_completion_errors', 'local_counters_and_buffer_occupancy']
        if mid == 'granite':
            dynamic += ['top8_expert_ID_values', 'rank_probability_values', 'expert_completion_progress']
        if mid in ('qwen35', 'falcon'):
            dynamic += ['state_history_values', 'recurrent_owner_epoch_position',
                        'candidate_commit_or_revoke_result', 'numeric_epoch_or_F_if_adaptive_rescale_is_accepted']
        uncertainties = ['NUMERIC_PER_EDGE', 'WHOLE_MODEL_BOUNDARY', 'COMPLETE_PROGRAM',
                         'PROGRAM_STORAGE', 'MEMORY_INTEGRATION', 'SYSTEM_IMPLEMENTATION']
        if m['source_max_position_embeddings'] > 65535:
            uncertainties.append('LONG_CONTEXT_N')
        if mid == 'llama':
            uncertainties.append('LLAMA_CHECKPOINT')
        if mid == 'granite':
            uncertainties += ['GRANITE_ALIAS', 'MOE_WIDE_NUMERIC']
        if mid == 'qwen35':
            uncertainties += ['GDN_L2_EPSILON', 'RECURRENT_NUMERIC', 'R_QUALIFICATION']
        if mid == 'falcon':
            uncertainties += ['CONV_BIAS_NUMERIC', 'RECURRENT_NUMERIC', 'R_QUALIFICATION']
        products.append({
          'model_id': mid, 'source_name': m['repository_sample_name'],
          'source_model_identity_status': m['model_identity_status'],
          'selector_ordinal_for_catalog_only': ordinal,
          'selector_physical_encoding': None,
          'source_dimensions': {'H': m['hidden_size'], 'I': m['ffn_intermediate_size'],
             'I_semantics': m['ffn_intermediate_semantics'],
             'layers': m['num_layers'], 'attention': copy.deepcopy(m['attention_configuration']),
             'source_max_position_embeddings': m['source_max_position_embeddings']},
          'source_layer_sequence': list(m['layer_sequence']),
          'source_layer_type_counts': dict(m['layer_type_counts']),
          'layer_grammar_bindings': prods_layers,
          'required_common_capabilities': sorted(req),
          'required_capabilities_status': 'logical_source_functions_and_candidate_mapping; not a compiled physical unit lower bound',
          'conditional_capability_obligations': [
             {'id': 'C25_WIDE_CONVERT',
              'trigger': 'chosen legal source-role route and accepted numeric range need conversion not covered by a selected existing operation',
              'domain': 'all_legal_role_domain_not_model_geometry_alone',
              'model_lowering_proved_necessary': False,
              'dedicated_generic_unit_mandatory': False,
              'allowed_realizations': ['reuse_M_op5_for_its_own_result_with_proved_range',
                 'proven_static_bit_extract_pack_or_specialized_decomposition',
                 'reuse_E13_only_for_its_S32_toS16_subset',
                 'add_actual_missing_numeric_ability_if_still_required']},
             {'id': 'C24_LONG_SOFTMAX',
              'trigger': 'permanently_admitted_full_score_row_length_exceeds65535',
              'source_position_bound_exceeds_native_count': m['source_max_position_embeddings'] > 65535,
              'accepted_runtime_bound_frozen': False,
              'model_lowering_proved_necessary': False,
              'dedicated_generic_unit_mandatory': False,
              'allowed_realizations': ['declare_and_accept_actual_workload_bounds_without_changing_source_configuration_facts',
                 'design_and_prove_additional_large_row_algorithm_resources_if_required']}
          ],
          'permanent_parameters': {
             'model_identity_and_config_binding': m['evidence'],
             'layer_sequence_and_structural_features': 'source_layer_sequence + layer_grammar_bindings',
             'H_I_head_and_projection_geometry': 'source_dimensions + layer_grammar_bindings',
             'normalization_and_activation_modes': 'source normalization sites and layer grammar',
             'rope_parameters': copy.deepcopy(m['rope_parameters']),
             'rms_norm_eps_source_value': m['rms_norm_eps_config'],
             'integer_epsilon_gamma_and_scale_tables': None,
             'weight_layout_schema_and_accepted_identity': None,
             'buffer_layout_and_route_template': None,
             'admitted_batch_query_context_bounds': None,
             'note': 'Source limits retained; actual accepted workload/quantization/addresses not fabricated. Physical memory address relocation policy is deferred with the memory interface.'},
          'runtime_variables': dynamic,
          'compile_time_proof_ids_applicable_conditionally': [r[0] for r in ELISION_PROOFS if r[0] != 'P06_ROUTER_RANGE' or mid == 'granite'],
          'runtime_generic_type_system_required': False,
          'program_binding': {
             'method': 'permanent_M11_M12_selection_of_prefabricated_ROM_and_parameter_space',
             'resynthesize_controller_per_product': False,
             'runtime_program_upload': False,
             'unknown_model_automatically_accepted': False,
             'all_product_programs_must_be_accepted_before_common_base_freeze': True,
             'complete_program_compiled': False, 'complete_program_accepted': False,
             'program_words': None, 'ROM_offset': None, 'accepted_parameter_extent': None},
          'sample_obligation_ids': [e['id'] for e in obligations['obligations'] if e['model_id'] == mid],
          'sample_obligations_are_complete_program': False,
          'unresolved_gate_ids': uncertainties,
          'source_evidence': copy.deepcopy(m['evidence']),
          'source_export_boundary': {'B': 1, 'S': 2, 'dtype': 'FP32',
             'cached_decode_validated': False, 'whole_network_validated': False},
        })
    gates = {
     'NUMERIC_PER_EDGE': '每边整数格式/舍入/范围/误差和模型质量未接收；不能把FP32层导出当定点通过。',
     'WHOLE_MODEL_BOUNDARY': '当前为代表decoder层图；embedding/频率mask/末Norm/LM head/采样等工作流边界待补齐。',
     'COMPLETE_PROGRAM': '未把完整八产品图降到共享控制ISA/原生命令；96义务只作输入，不是完整程序。',
     'PROGRAM_STORAGE': 'ROM/表容量与地址尚无完整编译结果，不估造程序字数。',
     'MEMORY_INTEGRATION': '系统有外存；其接口/调度/完成及数据可见性本轮不研究，全模型接收仍依赖后续闭合。',
     'SYSTEM_IMPLEMENTATION': '新增适配/控制/数值与连接RTL、活性和组合物理资格未完成。',
     'LONG_CONTEXT_N': '若要求达到源配置的全局context上限，当前N的65535计数不足；不能隐式截长。',
     'LLAMA_CHECKPOINT': '图册Llama为文档配置重建/随机参数，不能冒充原检查点整模型。',
     'GRANITE_ALIAS': '图册Granite-3.3B与报告Granite-3.1-3B-A800M-Instruct别名须绑定具体config/权重。',
     'MOE_WIDE_NUMERIC': '共同单位专家输出、Q14概率、宽归并/gain及误差尚未模型接收。',
     'GDN_L2_EPSILON': '所选图JSON省略常量payload，L2 epsilon未知；不得借RMS epsilon。',
     'RECURRENT_NUMERIC': 'beta/decay/dt/inject/state单位、重定标及恢复语义未形成已接收整链。',
     'R_QUALIFICATION': '当前跟踪R候选尚无最终资格，不能转用原R4032数据库。',
     'CONV_BIAS_NUMERIC': 'Falcon有conv bias，R mode2无bias口；需真实宽度/尺度正确的数值路径。',
    }
    inputs = []
    for name in ['family-spec.json', 'family-source-index.json', 'sample-connection-obligations.json']:
        path = data_root / name
        inputs.append({'repository_path': 'work/Melodydt/151/' + name,
                       'sha256': sha(path), 'bytes': path.stat().st_size})
    return {
      'schema_version': 1, 'issue': 151, 'owner': 'Melodydt', 'input_commit': INPUT_COMMIT,
      'upstream_family_source_ref': family['source_evidence']['ref'],
      'RTL_source': family['RTL_source'], 'status': 'candidate_research_not_compiled_hardware',
      'scope': {'declared_model_ids': list(MODEL_IDS), 'model_count': 8, 'layer_type_count': 10,
        'finite_means_explicit_existing_samples_not_unknown_models': True,
        'original_shapes_and_limits_preserved': True, 'source_small_export_not_runtime_upper_bound': True,
        'roles_are_mainly_compile_time_contracts': True, 'mandatory_universal_runtime_type_system': False,
        'common_M1_M10_active_base': True, 'permanent_M11_M12_model_binding': True,
        'bootload_control_program': False, 'per_product_controller_resynthesis': False},
      'memory_boundary': {'system_has_external_memory': True,
        'external_memory_interface_studied_this_round': False,
        'external_memory_scheduling_studied_this_round': False,
        'storage_treated_as_free_or_infinite': False,
        'current_S_capacity_not_full_model_architecture_limit': True,
        'future_interface_and_completion_dependency_retained': True},
      'common_base_fixed_items': [
        {'id': 'BASE_LEAVES', 'fixed': 'M/N/E/G/R/S/T数量、pin、几何、时序边界及额外数值能力；当前参考一类一个不等于数量已经最终冻结'},
        {'id': 'BASE_CONTROL', 'fixed': '统一顺序器/共享局部FSM/原生op译码/循环与等待/错误取消逻辑；不随产品重新综合'},
        {'id': 'BASE_ROM', 'fixed': '覆盖全部已接收产品的ROM/常量读取和参数选择能力；实际内容/容量在完整编译后接收'},
        {'id': 'BASE_DATA', 'fixed': '所需转换/拆拼/布局/固定路由选择/有限缓冲/时钟复位与驱动，均是预制有源逻辑'},
        {'id': 'BASE_MEMORY_BOUNDARY', 'fixed': '片上暂存及未来外存接入所需有源范围需在底座冻结前闭合；本轮不设计该接口'},
      ],
      'common_capability_catalog': caps, 'finite_layer_grammars': GRAMMARS,
      'all_legal_role_domain_numeric_obligation': 'Preserve legal wide-role conversions as conditional gaps; reuse existing ops or proved specialized lowering where sufficient. No per-model standalone generic converter is inferred.',
      'grammar_is_compiled_native_program': False, 'product_bindings': products,
      'compile_time_field_elision_candidates': [
        {'id': p[0], 'candidate_elided_fields': p[1], 'required_proof': p[2],
         'must_retain': p[3], 'hardware_consequence': p[4],
         'status': 'proof_obligation_not_completed', 'automatically_elided_by_this_report': False}
        for p in ELISION_PROOFS],
      'freeze_acceptance': {
         'required_products': list(MODEL_IDS), 'complete_programs_compiled': [],
         'complete_programs_accepted': [], 'all_products_before_base_freeze': True,
         'program_length_estimates': None, 'unknown_model_fallback_program': False,
         'required_gates': ['exact_source_and_numeric_identity', 'full_product_workflow_boundary',
           'per_edge_numeric_acceptance', 'complete_native_program_compilation',
           'control_ROM_and_parameter_range_proof', 'resource_and_memory_completion_closure',
           'functional_liveness_and_error_acceptance', 'common_base_and_M11_M12_physical_acceptance'],
         'new_system_RTL_verified': False, 'full_model_inference_accepted': False},
      'unresolved_gates': gates,
      'provenance': {'input_files': inputs,
         'source_index_entries': len(sources['sources']),
         'source_index_original_ref_preserved': True,
         'remote_operations_this_round': False,
         'nineteen_source_snapshots_rehashed_this_round': False,
         'source_pointer_hashes_are_prior_evidence_not_new_model_execution': True},
    }


def validate(contract, input_root):
    data_root = input_root / 'work/Melodydt/151'
    f = read_json(data_root / 'family-spec.json')
    obligations = read_json(data_root / 'sample-connection-obligations.json')['obligations']
    sources = read_json(data_root / 'family-source-index.json')['sources']
    pointer_keys = ('id', 'repository_path', 'ref', 'git_blob_sha', 'sha256', 'bytes')
    assert len(sources) == 19
    assert {tuple(e.get(k) for k in pointer_keys) for e in sources} == {
        tuple(e.get(k) for k in pointer_keys) for e in f['source_index_entries']}
    models = {m['model_id']: m for m in f['models']}
    products = contract['product_bindings']
    assert [p['model_id'] for p in products] == list(MODEL_IDS)
    assert len({g['layer_type_id'] for p in products for g in p['layer_grammar_bindings']}) == 10
    assert contract['input_commit'] == INPUT_COMMIT
    assert contract['memory_boundary']['system_has_external_memory'] is True
    assert contract['memory_boundary']['external_memory_interface_studied_this_round'] is False
    assert contract['scope']['mandatory_universal_runtime_type_system'] is False
    assert contract['scope']['per_product_controller_resynthesis'] is False
    assert contract['scope']['bootload_control_program'] is False
    cap_ids = {c['id'] for c in contract['common_capability_catalog']}
    all_ids = []
    for p in products:
        src = models[p['model_id']]
        d = p['source_dimensions']
        assert (d['H'], d['I'], d['layers'], d['source_max_position_embeddings']) == (
            src['hidden_size'], src['ffn_intermediate_size'], src['num_layers'], src['source_max_position_embeddings'])
        assert d['attention'] == src['attention_configuration']
        assert p['source_layer_sequence'] == src['layer_sequence']
        assert p['source_layer_type_counts'] == src['layer_type_counts']
        assert len(p['source_layer_sequence']) == d['layers']
        assert set(p['required_common_capabilities']) <= cap_ids
        assert 'C25_WIDE_CONVERT' not in p['required_common_capabilities']
        assert 'C24_LONG_SOFTMAX' not in p['required_common_capabilities']
        assert {o['id'] for o in p['conditional_capability_obligations']} == {'C25_WIDE_CONVERT', 'C24_LONG_SOFTMAX'}
        assert all(not o['model_lowering_proved_necessary'] and not o['dedicated_generic_unit_mandatory'] for o in p['conditional_capability_obligations'])
        assert p['runtime_generic_type_system_required'] is False
        assert p['program_binding']['complete_program_compiled'] is False
        assert p['program_binding']['complete_program_accepted'] is False
        assert p['program_binding']['resynthesize_controller_per_product'] is False
        assert p['program_binding']['runtime_program_upload'] is False
        assert p['program_binding']['unknown_model_automatically_accepted'] is False
        assert p['program_binding']['program_words'] is None
        assert p['program_binding']['ROM_offset'] is None
        assert p['program_binding']['accepted_parameter_extent'] is None
        assert p['program_binding']['all_product_programs_must_be_accepted_before_common_base_freeze'] is True
        assert p['source_export_boundary']['S'] == 2 and p['source_export_boundary']['cached_decode_validated'] is False
        expected = [e['id'] for e in obligations if e['model_id'] == p['model_id']]
        assert p['sample_obligation_ids'] == expected
        all_ids.extend(expected)
        src_layers = {t['layer_type_id']: t for t in f['layer_types'] if t['model_id'] == p['model_id']}
        for layer in p['layer_grammar_bindings']:
            orig = src_layers[layer['layer_type_id']]
            assert layer['source_normalization_sites'] == orig['normalization_sites']
            assert layer['source_attention'] == orig.get('attention')
            assert layer['source_recurrent_or_expert'] == (orig.get('gdn') or orig.get('ssm') or orig.get('moe'))
            assert layer['grammar_id'] in contract['finite_layer_grammars']
        assert 'ready_valid_latency_and_completion_errors' in p['runtime_variables']
        assert 'quantization_scale_if_data_dependent_scheme_is_accepted' in p['runtime_variables']
        if p['model_id'] == 'granite':
            assert 'top8_expert_ID_values' in p['runtime_variables'] and 'GRANITE_ALIAS' in p['unresolved_gate_ids']
        if p['model_id'] == 'llama':
            assert 'LLAMA_CHECKPOINT' in p['unresolved_gate_ids']
        if p['model_id'] in ('qwen35', 'falcon'):
            assert 'state_history_values' in p['runtime_variables'] and 'RECURRENT_NUMERIC' in p['unresolved_gate_ids']
    assert len(all_ids) == 96 and len(set(all_ids)) == 96
    for p in contract['compile_time_field_elision_candidates']:
        assert p['required_proof'] and p['must_retain']
        assert not p['automatically_elided_by_this_report']
    assert not contract['freeze_acceptance']['complete_programs_compiled']
    assert not contract['freeze_acceptance']['complete_programs_accepted']
    assert contract['freeze_acceptance']['all_products_before_base_freeze'] is True
    assert contract['freeze_acceptance']['program_length_estimates'] is None
    assert not contract['freeze_acceptance']['full_model_inference_accepted']
    for i in contract['provenance']['input_files']:
        assert sha(data_root / Path(i['repository_path']).name) == i['sha256']
    return {'model_bindings': 8, 'layer_types': 10, 'sample_obligations': 96,
            'conditional_elision_proofs': len(ELISION_PROOFS),
            'source_dimension_and_grammar_equality': True,
            'native_programs_compiled': 0, 'new_hardware_verification': False}


def make_report(c):
    rows = []
    detail = []
    for p in c['product_bindings']:
        d = p['source_dimensions']; a = d['attention']
        rows.append('| {0} | {1}/{2} | {3}/{4}/{5} | {6} | {7} |'.format(
          p['model_id'], d['H'], d['I'], a['query_heads'], a['kv_heads'], a['head_dim'],
          d['layers'], d['source_max_position_embeddings']))
        structure = ', '.join('{0}×{1}'.format(k, v) for k, v in p['source_layer_type_counts'].items())
        norms = '; '.join('{0}: {1}'.format(g['layer_type_id'],
           ', '.join('{0}({1}×{2})'.format(n['kind'], n['elements_per_group'], n['groups_per_token'])
                     for n in g['source_normalization_sites'])) for g in p['layer_grammar_bindings'])
        detail.append('### {0}：{1}\n\n- 有限层语法：{2}；完整层表在JSON，不生成任意层排列。\n'
          '- Norm范围：{3}。\n- 源算法/候选映射要求的共同能力：`{4}`，不是已编译的物理单元下界。\n'
          '- 宽转换与超过65535整行的处理单列条件义务，均未证明本产品必须有独立通用单元。\n'
          '- 永久绑定：{5}。\n- 运行时保留：`{6}`。\n'
          '- 共同控制器可复用，完整程序/ROM偏移/参数范围仍未编译接收；程序字数为null。\n'
          '- 产品阻塞门：`{7}`。\n'.format(p['model_id'], p['source_name'], structure, norms,
          ', '.join(p['required_common_capabilities']),
          '精确模型/层表、H/I/头与投影几何、Norm/激活/RoPE模式；整数参数、权重布局/身份及buffer路径须在程序接收时补齐',
          ', '.join(p['runtime_variables']), ', '.join(p['unresolved_gate_ids'])))
    proof_rows = '\n'.join('| {0} | {1} | {2} | {3} |'.format(p['id'],
        ', '.join(p['candidate_elided_fields']), p['required_proof'], ', '.join(p['must_retain']))
        for p in c['compile_time_field_elision_candidates'])
    capability_rows = '\n'.join('| {0} | {1} | {2} |'.format(k['id'], k['logical_location'], k['function'])
        for k in c['common_capability_catalog'])
    report = '''# 步骤1重研究：共同预制底座下的八产品永久绑定合同

本稿输入`e44c4f5f492b2ef0fef12846dd25c1b1ea637664`，仅在独立family草稿目录形成研究材料。任务Issue151、负责人Melodydt；本轮没有远端操作，没有改RTL/正式目录/旧文件/其他agent目录。来源是输入包family-spec、源索引和96条sample obligations，不重新执行模型或访问服务器。

## 1. 本次重新确定的前提

共同M1–M10底座必须包含全部受支持产品需要的有源计算、缓冲、控制、ROM与选择能力。M11/M12永久连接已预制的选择/参数端点，确定模型；**不能在定制某模型时重新综合它的控制器，也不通过启动装载控制程序补缺**。有限意味着明确八个现有样本和十层型，不意味着未来同名或未知模型自动可用。

系统有外存；本轮暂不研究其接口和调度，只保留将来闭合的依赖与边界。不再把旧P0的片上credit0当系统永久无外存；也不把外存当无限、零延迟或已实现的spill。完整模型存储/数据可见性仍待后续接收，当前S容量不是完整架构上限。

role/type/尺度/布局主要是编译期契约。目标是让软件把八个完整程序及参数映射到同一套有限控制能力，尽可能消除不必要的通用包头/解释器；不是先要求每条数据都携带旧稿的通用role、type、256bit handle或512bit task，再用通用运行时图引擎解释。是否删除某字段须有明确证明，不能删除真实握手、计数、状态或动态数据选择。

## 2. 真实样本域与“固定”的三个层次

| 样本ID | H/I | Q/KV/D（Attention分支） | 层数 | 源配置max_position |
|---|---|---|---:|---:|
''' + '\n'.join(rows) + '''

GDN另为key/query16头、value32头、Dk=Dv128；Falcon另为SSM32头、channel128、state256，不能把其Attention D套到状态分支。Gemma全局层为5/11/17/23/29，其余29层局部；Qwen3.5为[GDN,GDN,GDN,Global]×8。模型真实H/I/头数不缩小，源位置范围不改成硬件已支持范围。

| 层次 | 固定内容 | 不能误认为 |
|---|---|---|
| 共同底座固定 | 叶宏数量/几何/pin、共用顺序器与局部FSM、native-op译码、ROM读取、分支/循环/等待、转换/布局/缓冲/路由选择/驱动 | 为每个产品重新综合一套FSM后仍称同一底座 |
| 产品永久绑定 | 产品入口、精确层表与形状、模式、已接收的格式/尺度/常量、布局/route模板和允许参数域 | M11/M12能凭空新增计算、FIFO、寄存器、译码或CTS |
| 运行时变量 | token/长度/位置、合法prefill/decode分支、KV/state/history数值、MoE ID、等待/错误、计数和必要epoch | 模型固定就不再需要数据相关控制 |

当前仅形成四种有限层语法骨架：DENSE_ATTN_FFN、GDN_FFN、ATTN_MOE、ATTN_SSM_FFN。它们使用同一资源服务，结构选项由产品/层表永久决定；是可编译输入而不是已编译native程序，也不是四种超级指令已经覆盖整个模型。Attention与SSM具有并行数学语义，可以在单M上按固定合法顺序串行物化；不能让两个算法控制器直接并驱同一M/S。

## 3. 共同资源能力的并集

下表是八产品逻辑需求及全合法角色域条件义务的目录，**不是每项都对每个模型必需，也不是最终物理宏数、已实现的新模块或PPA结论**。当前一类一个七宏只是研究参照。预制冻结时必须接收实际能力/数量/路线；未用某能力的产品可以不调用或按已实现方式停用，不能后做有源修补。

| 能力ID | 逻辑归属 | 功能 |
|---|---|---|
''' + capability_rows + '''

M/N/E/G/R内部已有的算子不自动形成组合；所选路线若需要额外布局、NUM、状态版本或控制逻辑，仍须真实实现验收。C25是全合法角色域的条件宽转换义务，不是从八模型形状推导出的独立单元要求；优先复用M.op5量化出口、已证明位提取/重排、E13覆盖子集或专用分解，仍不足时才增加实际能力。C24也只在永久接收大于65535完整Softmax行时触发，不能把源config上限当已接收工作负载。两者在每产品JSON单列conditional，不计为已证明必需单元。外存接入有源边界需在真正冻结前确定，本轮不展开。

## 4. 逐产品绑定

以下逐项列出共同能力、永久参数和动态变量。H/I/头/层表与上游FamilySpec逐字段一致；source小图仍只有B1/S2/FP32/no-cache，没有完整程序/整数质量结论。

''' + '\n'.join(detail) + '''

### 需要在上述逐模型表中具体保留的差异

- Qwen2.5有三路QKV bias；Qwen3的Q宽2048而H1024，另有每头Q/K RMS；Llama没有Q/K头Norm，其图是重建配置/随机权重。
- Gemma是GELU_tanh、六处RMS0，局部window1024与全局层不同位置频率；不能用一份“普通RMS+SiLU”程序冒充。
- Phi是融合QKV与gate_up后Slice，RoPE仅96/128、其余32旁路；LongRoPE参数必须绑定源配置，不能用仅层内乘加图证明频率生成。
- Qwen3.5全局Q_gate宽8192，每头Q256+门256；Sigmoid门在PV后。GDN则qkv8192/z4096/beta32/a32、Conv8192×kernel4，无bias；状态[B,32,128,128]，先每head128 RMS后门乘。实际ONNX先Repeat16→32再L2，头映射floor(vhead/2)有Reshape/Tile证据；只计算16组L2是另需证明的优化。Q独立乘1/sqrt128，K不乘。
- Granite每token40选8，每专家I512，两个残差分支gain0.22、Attention multiplier0.015625；图没有shared expert。专家身份是动态数据，专家算法是固定循环，不应为每个动态ID编译一份新控制器。
- Falcon投影8736=Z4096+XBC4608+dt32，XBC再拆4096/256/256，B/C一组广播32头；Conv4608×kernel4有bias，R无bias口。状态[B,32,128,256]，先SiLU(Z)门乘再跨4096 RMS；K pre-RoPE scale与多处MuP不能合成一个万能系数。

## 5. 哪些role字段可消除，靠什么证明

静态role不等于没有控制状态。下表是条件化的软件证明义务；本轮没有完成这些编译证书，也没有自动删除字段。证明成立后可以选择更小的具体硬件编码，无需通用类型系统。

| 证明ID | 候选消除字段 | 必要证明 | 必须保留 |
|---|---|---|---|
''' + proof_rows + '''

例如，固定程序选择“M op5→E13→G”时，当前阶段和产品常量可以确定四S32的解释及shift，无需每包发送role/type/F。若M op5已夹取逻辑S16，也可采用已证明的位提取/重排，E13 shift0并非所有路线必选。一个E13响应的四S16低64可直接拆成两个G的32bit包，或以N count4消费；只有目的/存储布局要求紧凑八S16时才合并两半包。目的驱动的选择/保持、实际有效数和握手仍须实现，不预设一定有八元素合包器。硬件真正使用的opcode/shift/count没有因此消失。

N的STATS/EXP/REPLAY可由固定地址/阶段和原值不变性证书保证lineage，无需每包通用tensor ID；但实际长度可能变化，stats/EXP/replay计数、完整组屏障和写确认仍要存在。N busy也不是整组lease是否可切换的证明。

固定MoE TopK输入ID恰为0..39时，软件/形式证明可以避免重复的ID类型检查甚至冗余范围比较；实际TopK选出的8个ID、rank与probability及等待进度仍是运行时值，不能固定为8个专家。QwenGDN/Falcon即使模型固定，state内容、位置、候选/提交结果也不断变化。

若后续接受dense FFN动态量化或数据相关的因果重定标，scale以及必要的F/numeric_epoch会成为少量真实数值控制状态，不能应用“尺度永远固定”的删除证明。该条件变量在全部八产品表中保留，不默认只影响R模型。本轮尚无这些数值方案的完整接收结果。外存迟到响应/复位排空协议没有确定，故不能以本地单在途证明宣称全系统不需要任何tag或generation；也不在此引入强制通用tag头。

## 6. 完整程序的预制前接收门

每个产品都必须在**同一个共同底座冻结之前**提供并接收以下材料，不是只选一个样本通过，也不能先冻结底座后再为其他产品重综合controller：

1. 具体模型/config/权重与完整产品工作流身份；补清embedding、位置/mask、末Norm/LM head/采样等源图外边界。Llama图的随机参数和Granite别名不能被模糊处理。
2. 固定层语法的完整实例、源维度/合法运行范围、每边数值和布局、原生op/bitfield、资源唯一所有者与必要算法分解。
3. 用共同控制ISA/局部FSM真实编译出来的全部程序与永久参数；没有未解析NUM/转换/存储原语；ROM字数/地址/表域由实际编译结果测得，不估造program长度。
4. 资源/临时区/回放/状态生命周期与动态分支证明；外存边界后续需闭合请求/数据可见性/完成语义，不能凭“系统有外存”跳过。
5. 独立整数参考、组合功能、错误/取消/复位、活性与共用底座/永久选择的物理接受证据。单宏资格、source B1/S2和96条义务都不能代替。

当前JSON中八产品`complete_program_compiled=false`、`complete_program_accepted=false`，program_words/ROM_offset均null，完整已编译/已接收集合为空。若有一产品没有通过，应该阻止“支持全部八产品”的底座冻结结论，明确缩减受支持产品集合需另行评审；不能把它的profile标非法来隐藏缺口。未知模型不因落在某个品牌或大致形状范围就自动被接收。

## 7. 未知、阻塞与边界

具体产品门在JSON逐项索引。共同未知包括：每边整数格式/尺度/误差、完整产品程序和ROM容量、前后端模型工作流、外存数据完成依赖、新系统RTL/物理。GDN L2 epsilon未知，不能借RMS epsilon；R beta/decay/inject与状态单位及重定标未闭合；Falcon conv bias要保留宽数值路径；MoE宽归并/共同单位/gain待oracle。R跟踪候选仍未最终合格。

源config max_position只是原模型位置配置上限，不是已接收的硬件context上限；旧query1/context256是P0候选，不作为本稿永久参数。保留真实H/I/头/状态尺寸，容量不足是实现/映射缺口，不因当前S16KiB就永久排除系统有外存的模型，也不声称外存已补足。

## 8. 可复核检查与交付状态

同目录工具`build_family_binding_contract.py`从输入包三JSON生成本合同；`--check`只读核对8产品/10层型、真实维度/完整层表、Norm/Attention/R/MoE源特征逐字段等值、96义务逐产品无丢失、共享能力引用、8项条件消字段证明、永久绑定/无bootload/无产品重综合、外存范围与未编译状态，并检查输入SHA未漂移。它是研究一致性检查，不是native程序编译器、整数oracle或RTL测试。

工具不依赖本机草稿层级：`--input-root`默认当前目录，`--output-dir`默认工具所在目录；生成和`--check`均针对所选输出目录。整合到正式work目录后可在独立目录复算，避免覆盖正式文件，例如：

```text
python -X utf8 work/Melodydt/151/build_family_binding_contract.py --input-root . --output-dir work/Melodydt/151/recompute-family
python -X utf8 work/Melodydt/151/build_family_binding_contract.py --input-root . --output-dir work/Melodydt/151/recompute-family --check
```

上面是整合后复算入口，不冒充已在正式目录执行。产物只记录repository-relative输入路径和内容SHA，不嵌入输入/输出绝对目录；同字节输入应生成同字节JSON/报告。实际本轮运行入口仍在隔离drafts/family，输入为该任务integrated快照。

本轮只重新哈希三份本地输入JSON并复核19项源索引；没有远端操作，也未重哈希那19份原始源快照。源索引的旧验证是沿用来源，不冒充本轮模型复现。未执行推理、RTL/SystemC、服务器作业或EDA。正式整合、远端PR/状态和审查由主负责人执行，本独立稿不作这些变更。
'''
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-root', type=Path, default=Path('.'))
    ap.add_argument('--output-dir', type=Path, default=HERE,
                    help='Research output directory; --check reads here without writing.')
    ap.add_argument('--check', action='store_true', help='Read/check existing JSON only; do not write outputs.')
    a = ap.parse_args()
    path = a.output_dir / 'family-binding-contract.json'
    if a.check:
        result = validate(read_json(path), a.input_root)
    else:
        c = build(a.input_root)
        result = validate(c, a.input_root)
        a.output_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(c, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))
        (a.output_dir / 'family-report.md').write_bytes(make_report(c).encode('utf-8'))
    print(json.dumps({'check': result, 'output': str(path), 'sha256': sha(path),
                      'mode': 'check_only' if a.check else 'research_generation'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
