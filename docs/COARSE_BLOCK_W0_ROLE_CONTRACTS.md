# W0：172个数据角色的可绑定接口合同

输入研究提交`bd7cb2f3060c61e5d28a2ece0653dd9336a024af`，叶源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本生成器仅做合同/证据锁定，不执行RTL、仿真或服务器任务，不联网；正式合同/文档按原Issue/PR统一交付。

本轮新增端点/typed view、有限shape domain、owner、source/operand/result三段生存期、接受/存储ACK/phase/job判据、逐条未知字段、责任W包与编译拒绝条件；不是把上轮角色状态改名。

## 范围与真实新增项

172个原键完整保留；每个`variant:edge_ID`的原role/format/sync/hops及JSON pointer、输入SHA保持可追溯。产品尺度、epsilon_raw、M read/op/shift、布局stride/尾字、运行时准入上限、实际buffer分配、MEM/NUM协议仍为null，必须补证后才能绑定。native已知Q14概率、UQ1.15 EXP、G Q10、R key/query Q14与UQ1.31系数单独记录，不反向把来源张量符号尺度写成已知。

当前适用性统计：`{"active_for_all_current_variant_layer_types": 153, "conditional_on_bound_model_layer_option": 14, "inactive_for_current_source_options": 5}`。5条inactive全部为A_gate从通用A继承的q25 bias/无QKnorm RoPE/Gemma postNorm选项：保留目录键并拒绝在当前Qwen3.5绑定中启用，不是硬件宏对永久禁止；未来family变更须另版本接收。conditional记录必须按具体层选择，不能把172条当一段顺序程序。

## 编译准入与完成规则

source response先由唯一owner分类，转入owned capture并存储ACK后才释放；gather必须先take当前S响应再请求另一S operand。M结果覆盖、N组原值/gamma/EXP、G两输入同token/head/rank、R候选/本地commit/完整root、T租约与MEM持久ACK各有独立生存期。任何native完成或fragment_last都不单独构成JOB_COMPLETE。

缺数值/布局/owner/容量/ACK/NUM/MEM binding时编译拒绝，不靠默认Q10/identity layout/无限存储放行。拒绝是当前mapping或实现未准入，不把原算法边改成语义非法。R op7接受后不可用op8回滚；D每head RMS后门乘，H门乘后跨4096 RMS；H第一残差由H_JOIN统一拥有；X IDs不是score，仍须selected-score gather和宽merge。

责任沿用island-sync-plan的W0..W11（八主线别名由根任务整合）：W1 capture/owner/storage；W3 E/G；W4 N phase；W5 A/F集成；W6布局/反馈/forkjoin；W7数值/NUM；W8 R/version；W9 X；W10 MEM；W2输出传输语义。人类负责人未擅自分配。

下一W1起点仅拟固定DOT8 shape/program/address、只变输入data，另做输入stored ACK/初始化、输出fragment/错误/排空与独立预期；不是172条整体解锁，不声称完整W1 ready。本轮所有full-role admission均false。

## 逐角色索引

详细dtype/shape/native端点/存储/未知字段在JSON同键。表中状态A=当前variant全域适用，C=按具体模型层选项，I=当前variant无适用source option。

| role UID | 端点 | shape | 状态 | 责任包 |
|---|---|---|---|---|
| A_plain:INPUT | EXT→N | ["B", "Sq", "H"] | A | W0,W1,W4,W5,W7,W10 |
| A_plain:WEIGHTS | MEM→M | selected projection matrices [K_in,N_out]; actual weight layout not inferred from notation | A | W0,W1,W5,W7,W10 |
| A_plain:GAMMA | PARAM→N | role-specific scalar/vector/mixed parameter records | A | W0,W1,W4,W5,W7,W10 |
| A_plain:CONSTANTS | PARAM→E | role-specific scalar/vector/mixed parameter records | A | W0,W1,W3,W5,W7,W10 |
| A_plain:TEMP_SPILL | S→MEM | the exact declared intermediate tensor range | A | W0,W1,W5,W6,W10 |
| A_plain:TEMP_RELOAD | MEM→S | the exact declared intermediate tensor range | A | W0,W1,W5,W6,W10 |
| A_plain:OUTPUT_DRAIN | T→EXT | output [B,Sq,H] over bounded fragments | A | W0,W1,W2,W5,W10 |
| A_plain:A_NORM_PROJ | N→M | ["B", "Sq", "H"] | A | W0,W1,W4,W5,W7 |
| A_plain:A_PROJ_BIAS | M→E | Q/K/V source projection widths/head axes per domain | C | W0,W1,W3,W5,W7 |
| A_plain:A_QKNORM | M→N | Q/K/V source projection widths/head axes per domain | C | W0,W1,W4,W5,W7 |
| A_plain:A_NORM_ROPE | N→E | Q/K/V source projection widths/head axes per domain | C | W0,W1,W3,W4,W5,W7 |
| A_plain:A_PLAIN_ROPE | M→E | Q/K/V source projection widths/head axes per domain | C | W0,W1,W3,W5,W7 |
| A_plain:A_BIAS_ROPE | E→E | Q/K/V source projection widths/head axes per domain | C | W0,W1,W3,W5,W6,W7 |
| A_plain:A_QK | E→M | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W3,W5,W7 |
| A_plain:A_KV_SAVE | M→MEM | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W5,W7,W10 |
| A_plain:A_K_SAVE | E→MEM | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W3,W5,W7,W10 |
| A_plain:A_KV_READ | MEM→M | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W5,W7,W10 |
| A_plain:A_SCORE | M→E | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W3,W5,W7 |
| A_plain:A_MASK | E→E | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W3,W5,W6,W7 |
| A_plain:A_STATS | E→N | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W3,W4,W5,W7 |
| A_plain:A_EXP | N→N | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W4,W5,W6,W7 |
| A_plain:A_PV | N→M | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W4,W5,W7 |
| A_plain:A_PV_WO | M→M | [B,Sq,Q_projection_width] context or per-head output Gate | A | W0,W1,W5,W6,W7 |
| A_plain:A_WO_POSTN | M→N | ["B", "Sq", "H"] | C | W0,W1,W4,W5,W7 |
| A_plain:A_POSTN_RES | N→E | ["B", "Sq", "H"] | C | W0,W1,W3,W4,W5,W7 |
| A_plain:A_WO_RES | M→E | ["B", "Sq", "H"] | C | W0,W1,W3,W5,W7 |
| A_plain:A_RES_STORE | E→T | output [B,Sq,H] over bounded fragments | A | W0,W1,W3,W5,W7 |
| A_gate:INPUT | EXT→N | ["B", "Sq", "H"] | A | W0,W1,W4,W5,W7,W10 |
| A_gate:WEIGHTS | MEM→M | selected projection matrices [K_in,N_out]; actual weight layout not inferred from notation | A | W0,W1,W5,W7,W10 |
| A_gate:GAMMA | PARAM→N | role-specific scalar/vector/mixed parameter records | A | W0,W1,W4,W5,W7,W10 |
| A_gate:CONSTANTS | PARAM→E | role-specific scalar/vector/mixed parameter records | A | W0,W1,W3,W5,W7,W10 |
| A_gate:TEMP_SPILL | S→MEM | the exact declared intermediate tensor range | A | W0,W1,W5,W6,W10 |
| A_gate:TEMP_RELOAD | MEM→S | the exact declared intermediate tensor range | A | W0,W1,W5,W6,W10 |
| A_gate:OUTPUT_DRAIN | T→EXT | output [B,Sq,H] over bounded fragments | A | W0,W1,W2,W5,W10 |
| A_gate:A_NORM_PROJ | N→M | ["B", "Sq", "H"] | A | W0,W1,W4,W5,W7 |
| A_gate:A_PROJ_BIAS | M→E | Q/K/V source projection widths/head axes per domain | I | W0,W1,W3,W5,W7 |
| A_gate:A_QKNORM | M→N | Q/K/V source projection widths/head axes per domain | A | W0,W1,W4,W5,W7 |
| A_gate:A_NORM_ROPE | N→E | Q/K/V source projection widths/head axes per domain | A | W0,W1,W3,W4,W5,W7 |
| A_gate:A_PLAIN_ROPE | M→E | Q/K/V source projection widths/head axes per domain | I | W0,W1,W3,W5,W7 |
| A_gate:A_BIAS_ROPE | E→E | Q/K/V source projection widths/head axes per domain | I | W0,W1,W3,W5,W6,W7 |
| A_gate:A_QK | E→M | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W3,W5,W7 |
| A_gate:A_KV_SAVE | M→MEM | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W5,W7,W10 |
| A_gate:A_K_SAVE | E→MEM | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W3,W5,W7,W10 |
| A_gate:A_KV_READ | MEM→M | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W5,W7,W10 |
| A_gate:A_SCORE | M→E | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W3,W5,W7 |
| A_gate:A_MASK | E→E | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W3,W5,W6,W7 |
| A_gate:A_STATS | E→N | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W3,W4,W5,W7 |
| A_gate:A_EXP | N→N | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W4,W5,W6,W7 |
| A_gate:A_PV | N→M | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W4,W5,W7 |
| A_gate:A_GATE_X | M→G | [B,Sq,Q_projection_width] context or per-head output Gate | A | W0,W1,W3,W5,W6,W7 |
| A_gate:A_GATE_LINEAR | M→G | [B,Sq,Q_projection_width] context or per-head output Gate | A | W0,W1,W3,W5,W6,W7 |
| A_gate:A_GATE_WO | G→M | [B,Sq,Q_projection_width] context or per-head output Gate | A | W0,W1,W3,W5,W7 |
| A_gate:A_WO_POSTN | M→N | ["B", "Sq", "H"] | I | W0,W1,W4,W5,W7 |
| A_gate:A_POSTN_RES | N→E | ["B", "Sq", "H"] | I | W0,W1,W3,W4,W5,W7 |
| A_gate:A_WO_RES | M→E | ["B", "Sq", "H"] | A | W0,W1,W3,W5,W7 |
| A_gate:A_RES_STORE | E→T | output [B,Sq,H] over bounded fragments | A | W0,W1,W3,W5,W7 |
| F:INPUT | EXT→N | ["B", "Sq", "H"] | A | W0,W1,W4,W5,W7,W10 |
| F:WEIGHTS | MEM→M | selected projection matrices [K_in,N_out]; actual weight layout not inferred from notation | A | W0,W1,W5,W7,W10 |
| F:GAMMA | PARAM→N | role-specific scalar/vector/mixed parameter records | A | W0,W1,W4,W5,W7,W10 |
| F:CONSTANTS | PARAM→E | role-specific scalar/vector/mixed parameter records | A | W0,W1,W3,W5,W7,W10 |
| F:TEMP_SPILL | S→MEM | the exact declared intermediate tensor range | A | W0,W1,W5,W6,W10 |
| F:TEMP_RELOAD | MEM→S | the exact declared intermediate tensor range | A | W0,W1,W5,W6,W10 |
| F:OUTPUT_DRAIN | T→EXT | output [B,Sq,H] over bounded fragments | A | W0,W1,W2,W5,W10 |
| F:F_NORM_PROJ | N→M | ["B", "Sq", "H"] | A | W0,W1,W4,W5,W7 |
| F:F_GATE | M→G | ["B", "Sq", "I"] | A | W0,W1,W3,W5,W6,W7 |
| F:F_UP | M→G | ["B", "Sq", "I"] | A | W0,W1,W3,W5,W6,W7 |
| F:F_FALCON_GATE_SCALE | M→E | ["B", "Sq", "I"] | C | W0,W1,W3,W5,W7 |
| F:F_SCALED_GATE | E→G | ["B", "Sq", "I"] | C | W0,W1,W3,W5,W6,W7 |
| F:F_MID | G→M | ["B", "Sq", "I"] | A | W0,W1,W3,W5,W7 |
| F:F_POSTN | M→N | ["B", "Sq", "H"] | C | W0,W1,W4,W5,W7 |
| F:F_NORM_RES | N→E | ["B", "Sq", "H"] | C | W0,W1,W3,W4,W5,W7 |
| F:F_DOWN_RES | M→E | ["B", "Sq", "H"] | C | W0,W1,W3,W5,W7 |
| F:F_GAIN_RES | E→E | ["B", "Sq", "H"] | C | W0,W1,W3,W5,W6,W7 |
| F:F_OUTPUT | E→T | output [B,Sq,H] over bounded fragments | A | W0,W1,W3,W5,W7 |
| D:INPUT | EXT→N | ["B", "Sq", "H"] | A | W0,W1,W4,W7,W10 |
| D:WEIGHTS | MEM→M | selected projection matrices [K_in,N_out]; actual weight layout not inferred from notation | A | W0,W1,W7,W10 |
| D:GAMMA | PARAM→N | role-specific scalar/vector/mixed parameter records | A | W0,W1,W4,W7,W10 |
| D:CONSTANTS | PARAM→E | role-specific scalar/vector/mixed parameter records | A | W0,W1,W3,W7,W10 |
| D:TEMP_SPILL | S→MEM | the exact declared intermediate tensor range | A | W0,W1,W6,W10 |
| D:TEMP_RELOAD | MEM→S | the exact declared intermediate tensor range | A | W0,W1,W6,W10 |
| D:OUTPUT_DRAIN | T→EXT | output [B,Sq,H] over bounded fragments | A | W0,W1,W2,W10 |
| D:R_NUM_PARAMETERS | PARAM→NUM | role-specific scalar/vector/mixed parameter records | A | W0,W1,W7,W10 |
| D:R_NORM_PROJ | N→M | ["B", "Sq", "H"] | A | W0,W1,W4,W7 |
| D:R_PROJECT_CONV | M→R | ["B", "Sq", 8192] | A | W0,W1,W7,W8 |
| D:R_HISTORY_IN | MEM→R | ["B", 8192, "history_depth"] | A | W0,W1,W7,W8,W10 |
| D:R_CONV_STORE | R→MEM | ["B", 8192, "history_depth"] | A | W0,W1,W7,W8,W10 |
| D:R_STATE_IN | MEM→R | ["B", 32, 128, 128] | A | W0,W1,W7,W8,W10 |
| D:R_STATE_LOOP | R→R | ["B", 32, 128, 128] | A | W0,W1,W6,W7,W8 |
| D:R_OUT_STORE | R→MEM | ["B", 32, 128, 128] | A | W0,W1,W7,W8,W10 |
| D:R_Z_GATE | M→G | ["B", "Sq", 4096] | A | W0,W1,W3,W6,W7 |
| D:R_DT_BIAS | M→E | ["B", "Sq", 32] | A | W0,W1,W3,W7 |
| D:R_DT_SOFTPLUS | E→G | ["B", "Sq", 32] | A | W0,W1,W3,W6,W7 |
| D:R_DT_NUM | G→NUM | ["B", "Sq", 32] | A | W0,W1,W3,W7 |
| D:R_COEFF | NUM→R | role-specific scalar/vector/mixed parameter records | A | W0,W1,W7,W8 |
| D:R_OUTPUT_PROJECT | G→M | ["B", "Sq", 4096] | A | W0,W1,W3,W7 |
| D:R_OUTPUT_RES | M→E | ["B", "Sq", "H"] | A | W0,W1,W3,W7 |
| D:D_CONV_SILU | R→G | ["B", "Sq", 8192] | A | W0,W1,W3,W6,W7,W8 |
| D:D_QK_REPEAT_L2 | G→N | ["B", "Sq", 32, 128] | A | W0,W1,W3,W4,W7 |
| D:D_Q_SCALE | N→E | ["B", "Sq", 32, 128] | A | W0,W1,W3,W4,W7 |
| D:D_QUERY | E→R | ["B", "Sq", 32, 128] | A | W0,W1,W3,W7,W8 |
| D:D_KEY | N→R | ["B", "Sq", 32, 128] | A | W0,W1,W4,W7,W8 |
| D:D_VALUE | G→R | ["B", "Sq", 4096] | A | W0,W1,W3,W7,W8 |
| D:D_BETA | M→G | ["B", "Sq", 32] | A | W0,W1,W3,W6,W7 |
| D:D_BETA_FORMAT | G→NUM | ["B", "Sq", 32] | A | W0,W1,W3,W7 |
| D:D_RMS | R→N | ["B", "Sq", 4096] | A | W0,W1,W4,W7,W8 |
| D:D_NORM_GATE | N→G | ["B", "Sq", 4096] | A | W0,W1,W3,W4,W6,W7 |
| D:D_FINAL | E→T | output [B,Sq,H] over bounded fragments | A | W0,W1,W3,W7 |
| H:INPUT | EXT→N | ["B", "Sq", "H"] | A | W0,W1,W4,W5,W7,W10 |
| H:WEIGHTS | MEM→M | selected projection matrices [K_in,N_out]; actual weight layout not inferred from notation | A | W0,W1,W5,W7,W10 |
| H:GAMMA | PARAM→N | role-specific scalar/vector/mixed parameter records | A | W0,W1,W4,W5,W7,W10 |
| H:CONSTANTS | PARAM→E | role-specific scalar/vector/mixed parameter records | A | W0,W1,W3,W5,W7,W10 |
| H:TEMP_SPILL | S→MEM | the exact declared intermediate tensor range | A | W0,W1,W5,W6,W10 |
| H:TEMP_RELOAD | MEM→S | the exact declared intermediate tensor range | A | W0,W1,W5,W6,W10 |
| H:OUTPUT_DRAIN | T→EXT | output [B,Sq,H] over bounded fragments | A | W0,W1,W2,W5,W10 |
| H:R_NUM_PARAMETERS | PARAM→NUM | role-specific scalar/vector/mixed parameter records | A | W0,W1,W5,W7,W10 |
| H:R_NORM_PROJ | N→M | ["B", "Sq", "H"] | A | W0,W1,W4,W5,W7 |
| H:R_PROJECT_CONV | E→R | ["B", "Sq", 4608] | A | W0,W1,W3,W5,W7,W8 |
| H:R_HISTORY_IN | MEM→R | ["B", 4608, "history_depth"] | A | W0,W1,W5,W7,W8,W10 |
| H:R_CONV_STORE | R→MEM | ["B", 4608, "history_depth"] | A | W0,W1,W5,W7,W8,W10 |
| H:R_STATE_IN | MEM→R | ["B", 32, 128, 256] | A | W0,W1,W5,W7,W8,W10 |
| H:R_STATE_LOOP | R→R | ["B", 32, 128, 256] | A | W0,W1,W5,W6,W7,W8 |
| H:R_OUT_STORE | R→MEM | ["B", 32, 128, 256] | A | W0,W1,W5,W7,W8,W10 |
| H:R_Z_GATE | E→G | ["B", "Sq", 4096] | A | W0,W1,W3,W5,W6,W7 |
| H:R_DT_BIAS | E→E | ["B", "Sq", 32] | A | W0,W1,W3,W5,W6,W7 |
| H:R_DT_SOFTPLUS | E→G | ["B", "Sq", 32] | A | W0,W1,W3,W5,W6,W7 |
| H:R_DT_NUM | G→NUM | ["B", "Sq", 32] | A | W0,W1,W3,W5,W7 |
| H:R_COEFF | NUM→R | role-specific scalar/vector/mixed parameter records | A | W0,W1,W5,W7,W8 |
| H:R_OUTPUT_PROJECT | N→M | ["B", "Sq", 4096] | A | W0,W1,W4,W5,W7 |
| H:R_OUTPUT_RES | M→E | ["B", "Sq", "H"] | A | W0,W1,W3,W5,W7 |
| H:H_MUP | M→E | ["B", "Sq", 8736] | A | W0,W1,W3,W5,W7 |
| H:H_CONV_BIAS | R→NUM | ["B", "Sq", 4608] | A | W0,W1,W5,W7,W8 |
| H:H_CONV_SILU | NUM→G | ["B", "Sq", 4608] | A | W0,W1,W3,W5,W6,W7,W8 |
| H:H_BC | G→R | ["B", "Sq", 1, 256] | A | W0,W1,W3,W5,W7,W8 |
| H:H_X_NUM | G→NUM | ["B", "Sq", 4096] | A | W0,W1,W3,W5,W7 |
| H:H_R_GATE | R→G | ["B", "Sq", 4096] | A | W0,W1,W3,W5,W6,W7,W8 |
| H:H_GATE_RMS | G→N | ["B", "Sq", 4096] | A | W0,W1,W3,W4,W5,W7 |
| H:H_SHARED_ATTN | N→M | ["B", "Sq", "H"] | A | W0,W1,W4,W5,W7 |
| H:H_K_SCALE_ROPE | M→E | Q/K/V source projection widths/head axes per domain | A | W0,W1,W3,W5,W7 |
| H:H_QK | E→M | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W3,W5,W7 |
| H:H_KV | MEM→M | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W5,W7,W10 |
| H:H_KV_NEXT | E→MEM | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W3,W5,W7,W10 |
| H:H_V_NEXT | M→MEM | Q[B,Qheads,Sq,D] and shared K/V[B,KVheads,T,D] as exact role | A | W0,W1,W5,W7,W10 |
| H:H_PV_WO | M→M | [B,Sq,Q_projection_width] context or per-head output Gate | A | W0,W1,W5,W6,W7 |
| H:H_JOIN | E→E | ["B", "Sq", "H"] | A | W0,W1,W3,W5,W6,W7 |
| H:H_FINAL | E→T | output [B,Sq,H] over bounded fragments | A | W0,W1,W3,W5,W7 |
| H:H_ATTN_SCORE | M→E | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W3,W5,W7 |
| H:H_ATTN_MASK | E→E | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W3,W5,W6,W7 |
| H:H_ATTN_STATS | E→N | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W3,W4,W5,W7 |
| H:H_ATTN_EXP | N→N | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W4,W5,W6,W7 |
| H:H_ATTN_PV | N→M | ["B", "Q_heads", "Sq", "T_accessible"] | A | W0,W1,W4,W5,W7 |
| X:INPUT | EXT→N | ["B", "Sq", "H"] | A | W0,W1,W4,W7,W9,W10 |
| X:WEIGHTS | MEM→M | selected projection matrices [K_in,N_out]; actual weight layout not inferred from notation | A | W0,W1,W7,W9,W10 |
| X:GAMMA | PARAM→N | role-specific scalar/vector/mixed parameter records | A | W0,W1,W4,W7,W9,W10 |
| X:CONSTANTS | PARAM→E | role-specific scalar/vector/mixed parameter records | A | W0,W1,W3,W7,W9,W10 |
| X:TEMP_SPILL | S→MEM | the exact declared intermediate tensor range | A | W0,W1,W6,W9,W10 |
| X:TEMP_RELOAD | MEM→S | the exact declared intermediate tensor range | A | W0,W1,W6,W9,W10 |
| X:OUTPUT_DRAIN | T→EXT | output [B,Sq,H] over bounded fragments | A | W0,W1,W2,W9,W10 |
| X:X_NUM_PARAMETERS | PARAM→NUM | role-specific scalar/vector/mixed parameter records | A | W0,W1,W7,W9,W10 |
| X:X_NORM | N→M | ["B", "Sq", "H"] | A | W0,W1,W4,W7,W9 |
| X:X_ROUTER | M→N | ["B", "Sq", 40] | A | W0,W1,W4,W7,W9 |
| X:X_IDS | N→IDX | ["B", "Sq", 8] | A | W0,W1,W4,W6,W7,W9 |
| X:X_SELECTED_LOGITS | M→N | ["B", "Sq", 8] | A | W0,W1,W4,W7,W9 |
| X:X_ROUTE_EXP | N→N | ["B", "Sq", 8] | A | W0,W1,W4,W6,W7,W9 |
| X:X_WEIGHTS | MEM→M | selected projection matrices [K_in,N_out]; actual weight layout not inferred from notation | A | W0,W1,W7,W9,W10 |
| X:X_GATE | M→G | ["B", "Sq", 8, 512] | A | W0,W1,W3,W6,W7,W9 |
| X:X_UP | M→G | ["B", "Sq", 8, 512] | A | W0,W1,W3,W6,W7,W9 |
| X:X_MID | G→M | ["B", "Sq", 8, 512] | A | W0,W1,W3,W7,W9 |
| X:X_RETURN | M→NUM | ["B", "Sq", 8, 1536] | A | W0,W1,W7,W9 |
| X:X_PROB | N→NUM | ["B", "Sq", 8] | A | W0,W1,W4,W7,W9 |
| X:X_ACC | NUM→NUM | ["B", "Sq", 8, 1536] | A | W0,W1,W6,W7,W9 |
| X:X_GAIN | NUM→E | ["B", "Sq", 1, 1536] | A | W0,W1,W3,W7,W9 |
| X:X_OUTPUT | E→T | output [B,Sq,H] over bounded fragments | A | W0,W1,W3,W7,W9 |

## 验证边界

875项研究结构/来源/保守拒绝义务检查通过；172无遗漏无新增、每条必要字段和原role/hops保持、product F未被填值、5条inactive保留、D/H与TopK身份保持。负例是合同拒绝义务，不是完整编译器或RTL执行测试；该边界在机器回执中保留。

主`w0-role-contracts.json`保存共享policy/shape domain/源锁和六分片SHA索引；`w0-role-contracts-<variant>.json`逐配置保存角色，每片不超过200000B。共享policy只是要求模板，不是令不同role共用同一个运行时参数值或buffer。

生成：`python -B -X utf8 build_w0_role_contracts.py --root <checkout> --output-dir <independent-dir>`；`--check`只读重算索引、六分片、检查回执与报告逐字节比较。`--report <path>`可将报告放在正式docs路径，其余JSON仍在output-dir。只需已提交输入JSON，无raw graph、网络或外部工具。输入和产物SHA在JSON/回执中；管理结构检查另记，不能替代接口/数值/RTL接收。
