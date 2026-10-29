# V：回放选择与 Softmax 减法之间增加寄存

2026-10-30，Refs #121 / PR #122。仅修正唯一基础 V，不引入裕量版本。

[423最终原始结果](../../work/YUZE-LU/121/review-20261028/v-423-finish-diagnosis/README.md)的setup WS−0.0875939ns/TNS−1.35826ns、37违例与max_cap2不能接收；hold+0.0700393ns。第一max是function_sent[0]到function_unit.x1[13]，完整路径与实际input.v已映射，经过回放多路选择、S33减法和下限夹紧。旧424正常收尾，不取消或修改其已封存源。

新增function_fetch寄存：捕获两路原始S32操作数、两路有效mask、函数码、subtract标志及完整S32 maximum；下一拍才执行原样S33相减和−16 Q16.16下限夹紧，进入既有function_input寄存。函数单元本身的LUT、S45插值/RNE、三流水级和两lane II=1保持。每条有效数据携带自己的元数据；尤其奇数尾元素必须mask为原先的零，不能让无效lane参与减max并误触发正EXP错误。复位清除fetch/input valid，数据寄存不要求清零，仍用三初态及复位/背压回归验证。

新无停顿命令延迟预期：8元素函数由8改9拍，Softmax由137+10B+P改138+10B+P，N256为586拍；RMS/L2仍199+10B，N256为519拍。B=ceil(N/8)，P=ceil(N/2)；装载/消费/读回/阻塞另计。TopK/逐元素/统计/组级迭代不改。新独立期望已写入test_vector_latency.cpp，但尚待458实测，不称通过。所有数值位宽、饱和、舍入与完整域不改；norm_merge_rne/add128_grouped/rne纯算术函数保持原样。

458在c96以六个独立16CPU槽动态补位执行八个新源数值/映射/公共/扩展/组合/延迟/全宽算术检查；后续必须新测S回放/占用、重算模型有限预算并重做最终P&R/物理、电气、两DRC、三初态功能、LEC、六文件和全部接口/几何。max_cap2也必须实际修复，新增流水不等于电气已通过。M/S/T已通过的证据保持，R404继续原任务。
