# 局控逻辑端口 v0.1

由contract.json生成；不是原生宏pin或已通过编译的RTL。

| group | pin | direction | bits | meaning |
|---|---|---|---:|---|
| clock | clk_i | input | 1 | rising-edge clock |
| clock | rst_ni | input | 1 | active-low local reset; synchronous observation after deassertion |
| cohort | release_valid_i | input | 1 | fresh provider/transport reset certificate |
| cohort | release_sequence_i | input | 32 | coordinator monotonic reset sequence; no wrap |
| cohort | release_epoch_i | input | 32 | lowest permitted job epoch |
| cohort | deploy_valid_i | input | 1 | all cohort targets prepared and bundle checked |
| cohort | deploy_generation_i | input | 32 | same deployment generation as local image |
| cohort | release_ready_o | output | 1 | accept certificate only in RESET_WAIT |
| cohort | poison_o | output | 1 | sticky request for coordinated reset |
| cohort | image_valid_o | output | 1 | local prepared plus matching cohort deployment |
| config | cfg_req_valid_i | input | 1 | one request |
| config | cfg_req_op_i | input | 3 | BEGIN0 WRITE16=1 READ16=2 VERIFY_PASS3 PREPARE4 ABORT5 |
| config | cfg_req_generation_i | input | 32 | new on BEGIN, matching afterwards |
| config | cfg_req_address_i | input | 14 | byte address; 16B aligned |
| config | cfg_req_data_i | input | 128 | 16 bytes; little endian |
| config | cfg_req_total_bytes_i | input | 16 | BEGIN complete image length, <=8320 |
| config | cfg_req_image_id_i | input | 32 | BEGIN program_image_id |
| config | cfg_req_topology_id_i | input | 32 | BEGIN topology_id |
| config | cfg_req_abi_id_i | input | 32 | BEGIN native ABI |
| config | cfg_req_capacity_id_i | input | 32 | BEGIN capacity profile |
| config | cfg_req_proof_i | input | 1 | trusted loader full digest/static checks passed; VERIFY_PASS only |
| config | cfg_rsp_ready_i | input | 1 | host consumed complete response |
| config | cfg_req_ready_o | output | 1 | one transaction at a time; no active task |
| config | cfg_rsp_valid_o | output | 1 | held response, after memory ACK when needed |
| config | cfg_rsp_status_o | output | 16 | existing ISA status codes |
| config | cfg_rsp_data_o | output | 128 | READ16 bytes, otherwise zero |
| config | cfg_rsp_generation_o | output | 32 | echo accepted request generation |
| program_memory | pm_req_ready_i | input | 1 | request accepted |
| program_memory | pm_rsp_valid_i | input | 1 | actual read/write completion, >=1 edge later |
| program_memory | pm_rsp_data_i | input | 128 | read word |
| program_memory | pm_rsp_error_i | input | 1 | memory error |
| program_memory | pm_req_valid_o | output | 1 | one held request |
| program_memory | pm_req_write_o | output | 1 | write only while loading |
| program_memory | pm_req_address_o | output | 14 | byte address, aligned16 |
| program_memory | pm_req_data_o | output | 128 | write data |
| program_memory | pm_rsp_ready_o | output | 1 | consume or quarantine response |
| task | task_valid_i | input | 1 | complete 64B task_message |
| task | task_packet_i | input | 512 | unchanged ISA record |
| task | task_credit_i | input | 1 | mother reserved a terminal return credit for CALL |
| task | task_ready_o | output | 1 | CALL admission or matching CANCEL; full packet acceptance |
| service | svc_req_ready_i | input | 1 | adapter accepted complete snapshotted service |
| service | svc_rsp_valid_i | input | 1 | registered service completion |
| service | svc_rsp_kind_i | input | 2 | EXEC0 RX1 TX2 |
| service | svc_rsp_token_i | input | 3 | local token |
| service | svc_rsp_sequence_i | input | 32 | service sequence |
| service | svc_rsp_job_i | input | 32 | current job |
| service | svc_rsp_epoch_i | input | 32 | current epoch |
| service | svc_rsp_task_sequence_i | input | 32 | current invocation |
| service | svc_rsp_status_i | input | 16 | OK0 or fixed error |
| service | svc_rsp_read_bytes_i | input | 32 | confirmed local reads |
| service | svc_rsp_write_bytes_i | input | 32 | confirmed stored bytes |
| service | svc_rsp_saturated_i | input | 1 | saturation fact |
| service | svc_req_valid_o | output | 1 | held adapter request |
| service | svc_req_kind_o | output | 2 | EXEC0 RX1 TX2; 3 reserved |
| service | svc_req_resource_o | output | 3 | M0 or S5 in first slice |
| service | svc_req_token_o | output | 3 | local token |
| service | svc_req_sequence_o | output | 32 | monotonic per task, no wrap |
| service | svc_req_job_o | output | 32 | current job |
| service | svc_req_epoch_o | output | 32 | current epoch |
| service | svc_req_task_sequence_o | output | 32 | current invocation |
| service | svc_req_descriptor_o | output | 1024 | execution128B or transfer64B zero-extended |
| service | svc_req_object_base_o | output | 64 | snapshotted S byte base; zero for M clear |
| service | svc_req_object_length_o | output | 32 | S window bytes |
| service | svc_req_object_version_o | output | 32 | object version |
| service | svc_rsp_ready_o | output | 1 | consume matching response or quarantine under reset/poison |
| return | event_ready_i | input | 1 | entire 64B packet accepted by mother, not first flit |
| return | event_valid_o | output | 1 | complete held event_message |
| return | event_packet_o | output | 512 | unchanged ISA record |
| rx_close | close_req_ready_i | input | 1 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_rsp_valid_i | input | 1 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_rsp_sequence_i | input | 32 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_rsp_job_i | input | 32 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_rsp_epoch_i | input | 32 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_rsp_task_sequence_i | input | 32 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_rsp_token_i | input | 3 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_rsp_status_i | input | 16 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_req_valid_o | output | 1 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_req_sequence_o | output | 32 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_req_job_o | output | 32 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_req_epoch_o | output | 32 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_req_task_sequence_o | output | 32 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_req_token_o | output | 3 | RX source-close coordination, matching current task/service; not stored ACK |
| rx_close | close_rsp_ready_o | output | 1 | RX source-close coordination, matching current task/service; not stored ACK |
| observation | life_o | output | 4 | lifecycle enum |
| observation | seq_o | output | 4 | sequencer enum |
| observation | trace_pc_o | output | 32 | architectural PC, instruction index |
| observation | trace_retire_o | output | 1 | instruction retires at this edge |
| observation | trace_opcode_o | output | 8 | retiring opcode |
| observation | trace_pm_owner_o | output | 2 | CFG0 FETCH1 DESCRIPTOR2; stored locally with request |
| observation | trace_ireg_valid_o | output | 1 | one instruction holding register |
| observation | trace_cancel_token_retire_o | output | 1 | cancel cleanup consumes completed/closed service without instruction retirement |
| observation | trace_cancel_object_drop_o | output | 1 | cancel cleanup releases object after obligations; full object checks remain R2 oracle |

payload寄存器预算下界：688B，不含控制元数据、valid位、适配器和物理实现。
