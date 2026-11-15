# Complete local RTL review index

Every local .sv/.svh is indexed. Pending is not approved. External dependencies are separately indexed.

| File | Status | Required action / evidence scope |
| --- | --- | --- |
| rtl/blockv2_mod_p0.sv | rejected_for_corrected_base | Old P wrapper: physical group boundary and hidden compute require replacement. |
| rtl/blockv2_mod_p_native_lc.sv | rejected_for_corrected_base | Old P hierarchy includes undeclared arithmetic; not current base. |
| rtl/blockv2_mod_u_native_lc.sv | rejected_for_corrected_base | Old U hierarchy includes undeclared arithmetic; not current base. |
| rtl/cfj/ucf_native_service.sv | excluded_historical_reference | Retain as historical control/ABI reference only. Current plan uses explicitly registered service implementations; no automatic ABI or endpoint equivalence. Architecture disposition only; historical functional validation not claimed. |
| rtl/control/e32_service_cluster.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/control/macro_service_dispatch.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/control/n32_service_cluster.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/control/native_e_owner_control.sv | structure_evidence_only | Current complete assembly elaboration/source hashes checked; full assembled execution remains unaccepted. |
| rtl/control/native_n_owner_control.sv | structure_evidence_only | Current complete assembly elaboration/source hashes checked; full assembled execution remains unaccepted. |
| rtl/control/native_nine_control_plane.sv | structure_evidence_only | Current complete assembly elaboration/source hashes checked; full assembled execution remains unaccepted. |
| rtl/control/native_p_owner_control.sv | structure_evidence_only | Current complete assembly elaboration/source hashes checked; full assembled execution remains unaccepted. |
| rtl/control/native_shared_memory_dma.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/control/native_shared_memory_plane.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/control/native_shared_read_dma.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/control/native_shared_read_plane.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/control/projection_service_cluster.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/macros/e_s32_mac_ap64.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/macros/e_s32_mac_native.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/macros/n_s32_mod.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/macros/n_s32_reduction_engine.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/native_selected_nine_assembly.sv | structure_evidence_only | Current complete assembly elaboration/source hashes checked; full assembled execution remains unaccepted. |
| rtl/native_vocabulary_product_terminal.sv | excluded_historical_reference | Wrapper dependency reaches unregistered arithmetic or rejected group/feed assembly; top-level absence of arithmetic is insufficient. Architecture disposition only; historical functional validation not claimed. |
| rtl/p_native_lc_coplacement.sv | rejected_for_corrected_base | Old group assembly: fixed supply wiring and wrong SRAM profile require replacement. |
| rtl/p_services/blockv2_mod_p_resident_services.sv | rejected_for_corrected_base | Embedded arithmetic must bind declared macros. |
| rtl/p_services/ddr_s128_load_scope.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/p_services/dot_s32_core.sv | excluded_historical_reference | Standalone dot/argmax or incompatible N arithmetic is not an extra free parent resource. Use registered E-MAC/N-mod or explicitly revise the inventory. Architecture disposition only; historical functional validation not claimed. |
| rtl/p_services/dot_s32_s128.sv | excluded_historical_reference | Standalone dot/argmax or incompatible N arithmetic is not an extra free parent resource. Use registered E-MAC/N-mod or explicitly revise the inventory. Architecture disposition only; historical functional validation not claimed. |
| rtl/p_services/dot_s32_stage64.sv | excluded_historical_reference | Finite transport/lease helper is not inherently a forbidden hard boundary, but has no registered current-plan binding and must not be auto-admitted. Architecture disposition only; historical functional validation not claimed. |
| rtl/p_services/dot_s80_checkpoint.sv | excluded_historical_reference | Finite transport/lease helper is not inherently a forbidden hard boundary, but has no registered current-plan binding and must not be auto-admitted. Architecture disposition only; historical functional validation not claimed. |
| rtl/p_services/ffn_down_store.sv | excluded_historical_reference | Legacy three-P or COPY protocol is not a fixed base path. Reuse needs explicit endpoints, registered holds/selectors and a selected product connection. Architecture disposition only; historical functional validation not claimed. |
| rtl/p_services/ffn_down_store_scope.sv | excluded_historical_reference | Legacy three-P or COPY protocol is not a fixed base path. Reuse needs explicit endpoints, registered holds/selectors and a selected product connection. Architecture disposition only; historical functional validation not claimed. |
| rtl/p_services/gated_s32_scope.sv | rejected_for_corrected_base | Embeds G32 inside service; use declared G32 via gated_s32_service_controller. |
| rtl/p_services/n_s32_softmax_s128.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/p_services/projection_bias_e32_s128.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/p_services/rope_e32_ap64.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/p_services/rope_e32_s128_commit.sv | rejected_for_corrected_base | Embeds E32; use RoPE control with selected existing E32. |
| rtl/p_services/s128_attention_core_scope.sv | rejected_for_corrected_base | Embeds dot/N32/E32; corrected plan must lease declared macro resources. |
| rtl/p_services/s128_ddr_range_load.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/p_services/s128_kv_row_transfer.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/p_services/s128_kv_store_scope.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/p_services/s128_rope_leased_row.sv | excluded_historical_reference | Wrapper dependency reaches unregistered arithmetic or rejected group/feed assembly; top-level absence of arithmetic is insufficient. Architecture disposition only; historical functional validation not claimed. |
| rtl/p_services/s128_rope_scope.sv | excluded_historical_reference | Wrapper dependency reaches unregistered arithmetic or rejected group/feed assembly; top-level absence of arithmetic is insufficient. Architecture disposition only; historical functional validation not claimed. |
| rtl/p_services/s32_add_scope.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/p_static_output_lease.sv | excluded_historical_reference | Finite transport/lease helper is not inherently a forbidden hard boundary, but has no registered current-plan binding and must not be auto-admitted. Architecture disposition only; historical functional validation not claimed. |
| rtl/projection/blockv2_mod_projection_feed.sv | rejected_for_corrected_base | Old U/P feed assembly; not selected by corrected graph frontend. |
| rtl/projection/copy_scale_header_rx.sv | excluded_historical_reference | Legacy three-P or COPY protocol is not a fixed base path. Reuse needs explicit endpoints, registered holds/selectors and a selected product connection. Architecture disposition only; historical functional validation not claimed. |
| rtl/projection/copy_scale_header_tx.sv | excluded_historical_reference | Legacy three-P or COPY protocol is not a fixed base path. Reuse needs explicit endpoints, registered holds/selectors and a selected product connection. Architecture disposition only; historical functional validation not claimed. |
| rtl/projection/early_copy_3p.sv | excluded_historical_reference | Legacy three-P or COPY protocol is not a fixed base path. Reuse needs explicit endpoints, registered holds/selectors and a selected product connection. Architecture disposition only; historical functional validation not claimed. |
| rtl/projection/early_copy_epoch_3p.sv | excluded_historical_reference | Legacy three-P or COPY protocol is not a fixed base path. Reuse needs explicit endpoints, registered holds/selectors and a selected product connection. Architecture disposition only; historical functional validation not claimed. |
| rtl/projection/ffn_k_window_sequencer.sv | excluded_historical_reference | Legacy three-P or COPY protocol is not a fixed base path. Reuse needs explicit endpoints, registered holds/selectors and a selected product connection. Architecture disposition only; historical functional validation not claimed. |
| rtl/projection/s32_a16_tile_quantizer.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/resources/e32_service_selector.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/resources/s128_serial_pair.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/resources/s128_service_selector.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/s128_vocabulary_retire.sv | excluded_historical_reference | Wrapper dependency reaches unregistered arithmetic or rejected group/feed assembly; top-level absence of arithmetic is insufficient. Architecture disposition only; historical functional validation not claimed. |
| rtl/s128_vocabulary_tile_consumer.sv | excluded_historical_reference | Wrapper dependency reaches unregistered arithmetic or rejected group/feed assembly; top-level absence of arithmetic is insufficient. Architecture disposition only; historical functional validation not claimed. |
| rtl/s32_token_argmax.sv | excluded_historical_reference | Standalone dot/argmax or incompatible N arithmetic is not an extra free parent resource. Use registered E-MAC/N-mod or explicitly revise the inventory. Architecture disposition only; historical functional validation not claimed. |
| rtl/services/add_s32_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/e32_dot_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/gated_s32_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/indexed_gather_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/n32_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/projection_local_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/projection_local_source.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/projection_stream_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/rms_apply_native_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/rms_apply_s32_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/rms_s32_service_controller.sv | rejected_for_corrected_base | Retired combined RMS; use N mod factor and E apply with selected data transfer. |
| rtl/services/rope_native_row.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/rope_native_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/services/rope_s32_service_controller.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/test_s128_vocabulary_retire.sv | excluded_historical_reference | Testbench contains a historical reduction and SRAM fixture; it cannot be a production implementation or current numerical evidence. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/block_v2_n.sv | excluded_historical_reference | Standalone dot/argmax or incompatible N arithmetic is not an extra free parent resource. Use registered E-MAC/N-mod or explicitly revise the inventory. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/block_v2_n_exp.svh | excluded_historical_reference | Standalone dot/argmax or incompatible N arithmetic is not an extra free parent resource. Use registered E-MAC/N-mod or explicitly revise the inventory. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/block_v2_n_group.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/u0/e_s32_ap64.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/u0/e_s32_native.sv | unit_evidence_only | Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted. |
| rtl/u0/s32_rms_apply_s128.sv | excluded_historical_reference | Retain as historical control/ABI reference only. Current plan uses explicitly registered service implementations; no automatic ABI or endpoint equivalence. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/s32_rms_factor_s128.sv | excluded_historical_reference | Retain as historical control/ABI reference only. Current plan uses explicitly registered service implementations; no automatic ABI or endpoint equivalence. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/s32_rms_range_scan.sv | excluded_historical_reference | Retain as historical control/ABI reference only. Current plan uses explicitly registered service implementations; no automatic ABI or endpoint equivalence. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/u_indexed_gather.sv | excluded_historical_reference | Retain as historical control/ABI reference only. Current plan uses explicitly registered service implementations; no automatic ABI or endpoint equivalence. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/u_n32_controlled_64.sv | excluded_historical_reference | Wrapper dependency reaches unregistered arithmetic or rejected group/feed assembly; top-level absence of arithmetic is insufficient. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/u_n32_legacy_dispatch.svh | excluded_historical_reference | Wrapper dependency reaches unregistered arithmetic or rejected group/feed assembly; top-level absence of arithmetic is insufficient. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/u_native_descriptor.sv | excluded_historical_reference | Retain as historical control/ABI reference only. Current plan uses explicitly registered service implementations; no automatic ABI or endpoint equivalence. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/u_projection_feed.sv | rejected_for_corrected_base | Old fixed U-to-P supply implementation; no implicit U/P product route permitted. |
| rtl/u0/u_resident_add.sv | rejected_for_corrected_base | Embeds E32 absent from U inventory; corrected Add selects declared E32 owner. |
| rtl/u0/u_resident_rms.sv | excluded_historical_reference | Wrapper dependency reaches unregistered arithmetic or rejected group/feed assembly; top-level absence of arithmetic is insufficient. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/u_resident_rms_core.sv | rejected_for_corrected_base | Embeds incompatible N and extra E32; use explicit N-mod and declared E32 stages. |
| rtl/u0/u_resident_store.sv | excluded_historical_reference | Retain as historical control/ABI reference only. Current plan uses explicitly registered service implementations; no automatic ABI or endpoint equivalence. Architecture disposition only; historical functional validation not claimed. |
| rtl/u0/wrapper.sv | excluded_historical_reference | Wrapper dependency reaches unregistered arithmetic or rejected group/feed assembly; top-level absence of arithmetic is insufficient. Architecture disposition only; historical functional validation not claimed. |
