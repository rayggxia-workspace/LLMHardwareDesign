# A8设计、独立数学与TB静态交叉检查

检查对象为本目录A8 top、根A8_ABI、另一作者的 `a8_integer_reference.py`、冻结向量及 `block_w4_a8_tb.sv` / `a8-tb-contract.json`。本检查只读源码；没有执行RTL compile/simulation或外部PR批准。A8 top由本审阅者编写，数学/TB为另一作者，不能把作者对自身RTL自审写成独立外部审查。

发现并已由root采纳的两项ABI纠偏：PV A base原拟462不满足native loader四字对齐，改为prob464/pad465..467/output468；native M CLEAR为op6，MC_CLEAR=0只是本地阶段编号。当前ABI已修正，RTL不需要迁就错误opcode。其余本次检查未发现阻断问题。

数学oracle按独立公式重建1025项EXP，只解析native表作版本一致性检查，不以DUT输出作为期望。QK整数dot乘11585后RNE19、Softmax全组max/EXP/floor factor/RNE30和PV prob×V后RNE11与所选native路径相符。特别地，native EXP执行lo+RNE(delta*fraction,4)，oracle没有误用对lo+fraction合计的另一种tie parity。EXP32768保留U16位模式；PV的概率按非负S16 Fin14解释。两次op5的4×S32 carrier按低16抽取、first-half低4/second-half高4顺序正确。

TB预先声明8个数值向量及26个CASE，不从DUT日志抽取来定义预期覆盖。已静态检查：K key-major与V channel-major512-bit完整拼接；Q A128及prob A128；S loader配置与两个M投影格式/scale/descriptor；23普通S/19W4R、M10/N6/load2/T1；score/EXP/prob/padding/output逐stage实际写数据与ACK；N op3取score/op6取exact EXP；N响应保留时禁止PV提前启动；最后prob目的ACK与PV之间的门；真实native N op15、QK988c、PV988d错误与新帧恢复；abort/reset/held output/DONE+abort+ready和T release。

loader命令accept先把loads计数推进，后续真实A/B握手据此选择QK或PV期望，当前比较的边沿顺序正确。故障例关闭strict_native descriptor逐项断言但保留错误后无发布、存储及恢复断言，避免把故意非法命令当正常命令接受。normal_counts只用于完整成功帧，全suite取消事务不要求无条件计数相等。

限制：8向量/26CASE仍是待服务器Verilator执行的有限计划，不是RTL通过、全部输入或参数空间覆盖。该A8合法S8数值范围下score与最终值通常均在S16内，done_saturated检查不代表新增clip边界穷举。两状态/X、层级force、timing/reset注入和数组访问的实际Verilator兼容性须由root服务器真实compile/run及具体guard日志证明，不从旧ModelSim证据转移。无完整A、掩码/causal、RoPE/GQA、真实模型尺寸、外存或PPA资格。
