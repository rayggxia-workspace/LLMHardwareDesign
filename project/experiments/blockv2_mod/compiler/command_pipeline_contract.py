"""Required behavior for this revision; admission requires matching RTL evidence."""
SERVICE_PIPELINE={
 'revision':'command-pipeline/1',
 'activation_read_slots':2,'activation_write_slots':2,'weight_read_credits':32,
 'activation_prefetch_windows':1,'a_source_read_credits':2,
 'activation_stats_on_load':True,'quantization_read_words':32,'quantization_write_words':16,
 'quantization_response_slots':2,'quantization_pack_slots':2,
 'store_buffer_slots':2,'store_sram_read_credits':2,'store_ddr_write_credits':1,
 'dot_operand_cache_lines':2,
 'n_service_read_credits':4,'e_service_read_credits':4,
 'gather_activation_pipeline':True,'activation_scope_pipeline':True,
}
CAPABILITY_RTL={
 'activation_read_slots':'s128_ddr_range_load.sv','activation_write_slots':'s128_ddr_range_load.sv',
 'weight_read_credits':'weight_records.sv','activation_prefetch_windows':'projection_local_source.sv',
 'a_source_read_credits':'private_a_tile_abort_frontend.sv',
 'activation_stats_on_load':'projection_local_source.sv',
 **{k:'s32_a16_tile_quantizer.sv' for k in ('quantization_read_words','quantization_write_words','quantization_response_slots','quantization_pack_slots')},
 **{k:'s128_store_pipeline.sv' for k in ('store_buffer_slots','store_sram_read_credits','store_ddr_write_credits')},
 'dot_operand_cache_lines':'e32_dot_service_controller.sv',
 'n_service_read_credits':'n32_service_cluster.sv','e_service_read_credits':'e32_service_cluster.sv',
 'gather_activation_pipeline':'indexed_gather_service_controller.sv',
 'activation_scope_pipeline':'ddr_s128_load_scope.sv',
}
def validate_service_pipeline(hardware):
 if any(hardware.get('service_pipeline',{}).get(k)!=v for k,v in SERVICE_PIPELINE.items()):
  raise ValueError('hardware does not certify current command pipeline; rebuild base and plan')
 if hardware.get('base_rtl_contract',{}).get('service_pipeline')!=SERVICE_PIPELINE:
  raise ValueError('base and service pipeline contracts disagree')
