# 七顶层端口机械清单

由固定643c RTL的ANSI header解析；方向相对于宏。owner为集成契约，尚未实例化。

## M — block_v2_m

| 端口 | 方向 | 位宽 | 外侧/原生唯一驱动约束 | 源码行 |
|---|---|---:|---|---:|
| `clk` | input | 1 | FABRIC_CLOCK_RESET | 6 |
| `reset` | input | 1 | FABRIC_CLOCK_RESET | 6 |
| `a_valid` | input | 1 | S_LOADER | 7 |
| `a_ready` | output | 1 | NATIVE_M | 7 |
| `a_bank` | input | 1 | S_LOADER | 7 |
| `a_row` | input | 3 | S_LOADER | 8 |
| `a_tile` | input | 2 | S_LOADER | 8 |
| `a_wide` | input | 1 | S_LOADER | 8 |
| `a_data` | input | 128 | S_LOADER | 8 |
| `b_valid` | input | 1 | S_LOADER | 9 |
| `b_ready` | output | 1 | NATIVE_M | 9 |
| `b_bank` | input | 1 | S_LOADER | 9 |
| `b_tile` | input | 2 | S_LOADER | 9 |
| `b_wide` | input | 1 | S_LOADER | 10 |
| `b_half` | input | 1 | S_LOADER | 10 |
| `b_data` | input | 512 | S_LOADER | 10 |
| `cmd_valid` | input | 1 | M_CTRL | 11 |
| `cmd_ready` | output | 1 | NATIVE_M | 11 |
| `cmd_op` | input | 4 | M_CTRL | 11 |
| `cmd_index` | input | 6 | M_CTRL | 12 |
| `cmd_data` | input | 64 | M_CTRL | 12 |
| `rsp_valid` | output | 1 | NATIVE_M | 13 |
| `rsp_ready` | input | 1 | M_CTRL | 13 |
| `rsp_data` | output | 128 | NATIVE_M | 13 |
| `rsp_error` | output | 1 | NATIVE_M | 14 |
| `rsp_saturated` | output | 1 | NATIVE_M | 14 |
| `busy` | output | 1 | NATIVE_M | 14 |

## N — block_v2_n

| 端口 | 方向 | 位宽 | 外侧/原生唯一驱动约束 | 源码行 |
|---|---|---:|---|---:|
| `clk` | input | 1 | FABRIC_CLOCK_RESET | 4 |
| `reset` | input | 1 | FABRIC_CLOCK_RESET | 4 |
| `cmd_valid` | input | 1 | N_CTRL | 4 |
| `cmd_ready` | output | 1 | NATIVE_N | 4 |
| `cmd_op` | input | 4 | N_CTRL | 5 |
| `cmd_count` | input | 4 | N_CTRL | 5 |
| `cmd_param` | input | 32 | N_CTRL | 5 |
| `cmd_data` | input | 128 | N_CTRL | 6 |
| `cmd_aux` | input | 128 | N_CTRL | 6 |
| `rsp_valid` | output | 1 | NATIVE_N | 7 |
| `rsp_ready` | input | 1 | N_CTRL | 7 |
| `rsp_data` | output | 128 | NATIVE_N | 7 |
| `rsp_error` | output | 1 | NATIVE_N | 8 |
| `rsp_saturated` | output | 1 | NATIVE_N | 8 |
| `busy` | output | 1 | NATIVE_N | 8 |

## E — block_v2_e

| 端口 | 方向 | 位宽 | 外侧/原生唯一驱动约束 | 源码行 |
|---|---|---:|---|---:|
| `clk` | input | 1 | FABRIC_CLOCK_RESET | 6 |
| `reset` | input | 1 | FABRIC_CLOCK_RESET | 6 |
| `in_valid` | input | 1 | E_CTRL | 6 |
| `in_ready` | output | 1 | NATIVE_E | 6 |
| `in_op` | input | 4 | E_CTRL | 7 |
| `in_shift` | input | 5 | E_CTRL | 7 |
| `in_a` | input | 128 | E_CTRL | 8 |
| `in_b` | input | 128 | E_CTRL | 8 |
| `in_c` | input | 128 | E_CTRL | 8 |
| `out_valid` | output | 1 | NATIVE_E | 9 |
| `out_ready` | input | 1 | E_CTRL | 9 |
| `out_data` | output | 128 | NATIVE_E | 10 |
| `out_error` | output | 1 | NATIVE_E | 10 |
| `out_saturated` | output | 1 | NATIVE_E | 10 |

## G — block_v2_g

| 端口 | 方向 | 位宽 | 外侧/原生唯一驱动约束 | 源码行 |
|---|---|---:|---|---:|
| `clk` | input | 1 | FABRIC_CLOCK_RESET | 4 |
| `reset` | input | 1 | FABRIC_CLOCK_RESET | 4 |
| `in_valid` | input | 1 | G_CTRL | 4 |
| `in_ready` | output | 1 | NATIVE_G | 4 |
| `in_fn` | input | 3 | G_CTRL | 5 |
| `in_gated` | input | 1 | G_CTRL | 5 |
| `in_x` | input | 32 | G_CTRL | 6 |
| `in_gate` | input | 32 | G_CTRL | 6 |
| `out_valid` | output | 1 | NATIVE_G | 7 |
| `out_ready` | input | 1 | G_CTRL | 7 |
| `out_data` | output | 32 | NATIVE_G | 8 |
| `out_error` | output | 1 | NATIVE_G | 8 |
| `out_saturated` | output | 1 | NATIVE_G | 8 |

## R — block_v1_r

| 端口 | 方向 | 位宽 | 外侧/原生唯一驱动约束 | 源码行 |
|---|---|---:|---|---:|
| `clk` | input | 1 | FABRIC_CLOCK_RESET | 5 |
| `reset` | input | 1 | FABRIC_CLOCK_RESET | 5 |
| `cmd_valid` | input | 1 | R_CTRL | 5 |
| `cmd_ready` | output | 1 | NATIVE_R | 5 |
| `cmd_op` | input | 4 | R_CTRL | 6 |
| `cmd_index` | input | 10 | R_CTRL | 6 |
| `cmd_data` | input | 128 | R_CTRL | 6 |
| `rsp_valid` | output | 1 | NATIVE_R | 7 |
| `rsp_ready` | input | 1 | R_CTRL | 7 |
| `rsp_data` | output | 128 | NATIVE_R | 7 |
| `rsp_error` | output | 1 | NATIVE_R | 8 |
| `busy` | output | 1 | NATIVE_R | 8 |

## S — block_feed_s_macro

| 端口 | 方向 | 位宽 | 外侧/原生唯一驱动约束 | 源码行 |
|---|---|---:|---|---:|
| `clk` | input | 1 | FABRIC_CLOCK_RESET | 5 |
| `reset` | input | 1 | FABRIC_CLOCK_RESET | 5 |
| `req` | input | 1 | S_CTRL | 6 |
| `wr` | input | 1 | S_CTRL | 6 |
| `addr` | input | 10 | S_CTRL | 6 |
| `din` | input | 128 | S_CTRL | 6 |
| `ready` | output | 1 | NATIVE_S | 7 |
| `valid` | output | 1 | NATIVE_S | 7 |
| `take` | input | 1 | S_CTRL | 7 |
| `dout` | output | 128 | NATIVE_S | 7 |
| `load_valid` | input | 1 | S_CTRL | 8 |
| `load_ready` | output | 1 | NATIVE_S | 8 |
| `load_bank` | input | 1 | S_CTRL | 9 |
| `load_rows` | input | 4 | S_CTRL | 9 |
| `load_tiles` | input | 3 | S_CTRL | 9 |
| `load_a_wide` | input | 1 | S_CTRL | 10 |
| `load_b_wide` | input | 1 | S_CTRL | 10 |
| `load_reuse_b` | input | 1 | S_CTRL | 10 |
| `load_a_base` | input | 10 | S_CTRL | 11 |
| `load_b_base` | input | 10 | S_CTRL | 11 |
| `done_valid` | output | 1 | NATIVE_S | 12 |
| `done_take` | input | 1 | S_CTRL | 12 |
| `done_error` | output | 1 | NATIVE_S | 12 |
| `busy` | output | 1 | NATIVE_S | 12 |
| `a_valid` | output | 1 | NATIVE_S | 13 |
| `a_ready` | input | 1 | M_NATIVE_READY_OR_PREBUILT_EXPORT_SELECTION | 13 |
| `a_bank` | output | 1 | NATIVE_S | 13 |
| `a_row` | output | 3 | NATIVE_S | 14 |
| `a_tile` | output | 2 | NATIVE_S | 14 |
| `a_wide` | output | 1 | NATIVE_S | 15 |
| `a_data` | output | 128 | NATIVE_S | 15 |
| `b_valid` | output | 1 | NATIVE_S | 16 |
| `b_ready` | input | 1 | M_NATIVE_READY_OR_PREBUILT_EXPORT_SELECTION | 16 |
| `b_bank` | output | 1 | NATIVE_S | 16 |
| `b_tile` | output | 2 | NATIVE_S | 17 |
| `b_wide` | output | 1 | NATIVE_S | 17 |
| `b_half` | output | 1 | NATIVE_S | 17 |
| `b_data` | output | 512 | NATIVE_S | 17 |

## T — transaction6k

| 端口 | 方向 | 位宽 | 外侧/原生唯一驱动约束 | 源码行 |
|---|---|---:|---|---:|
| `clk` | input | 1 | FABRIC_CLOCK_RESET | 5 |
| `reset` | input | 1 | FABRIC_CLOCK_RESET | 5 |
| `begin_valid` | input | 1 | T_CTRL | 6 |
| `begin_ready` | output | 1 | NATIVE_T | 6 |
| `begin_owner` | input | 2 | T_CTRL | 7 |
| `begin_generation` | input | 32 | T_CTRL | 7 |
| `begin_words` | input | 10 | T_CTRL | 8 |
| `write_valid` | input | 1 | T_CTRL | 9 |
| `write_ready` | output | 1 | NATIVE_T | 9 |
| `write_index` | input | 10 | T_CTRL | 10 |
| `write_data` | input | 128 | T_CTRL | 10 |
| `commit_valid` | input | 1 | T_CTRL | 11 |
| `commit_ready` | output | 1 | NATIVE_T | 11 |
| `revoke_valid` | input | 1 | T_CTRL | 12 |
| `revoke_ready` | output | 1 | NATIVE_T | 12 |
| `read_valid` | output | 1 | NATIVE_T | 13 |
| `read_take` | input | 1 | T_CTRL | 13 |
| `read_index` | output | 10 | NATIVE_T | 14 |
| `read_data` | output | 128 | NATIVE_T | 14 |
| `read_last` | output | 1 | NATIVE_T | 15 |
| `owner` | output | 2 | NATIVE_T | 16 |
| `generation` | output | 32 | NATIVE_T | 16 |
| `word_count` | output | 10 | NATIVE_T | 17 |
| `release_valid` | input | 1 | T_CTRL | 18 |
| `release_ready` | output | 1 | NATIVE_T | 18 |
| `busy` | output | 1 | NATIVE_T | 19 |
| `sealed` | output | 1 | NATIVE_T | 19 |
| `committed` | output | 1 | NATIVE_T | 19 |
| `protocol_error` | output | 1 | NATIVE_T | 20 |
| `debug_state` | output | 3 | NATIVE_T | 20 |

