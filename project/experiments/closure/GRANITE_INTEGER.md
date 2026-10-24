# Granite 真实输入整数路由（Issue72）

只读取granite_reference.py生成的冻结32层router输入/权重，不重跑或量化expert/整模型。每种typed参考各192个layer-case-profile，四候选(静态/动态激活×W8A8/W16A16)共768记录。另192个选择性宽路由。即使来源新参考失败也保留数值诊断标签，不能升级原Issue70 FAIL。

## 格式与算法

- 输入、权重分别对称S8/S16，范围[-127,127]、[-32767,32767]，RNE后显式饱和，零点0。权重per-output，激活是独立calibration.full的per-layer固定最大值，或当前row最大值。scale为2的整数幂，INT16 exponent，epoch0为此不可变payload格式，无未来数据/评价误差调参。
- 完整K1536 dot为INT64软件oracle。S8最坏24,774,144可INT32；S16最坏1,649,166,534,144需42个带符号位(41位幅度)，不能声称INT32。
- S16经符号×绝对值base128三digit表示，每digit在[-127,127]。3×3=9份全K S8 dot，每份INT32，然后7(i+j)位左移、宽合并。每个profile冻结first/last/最小FP64 margin三类行有实际9份dot见证，与软件宽dot逐位核对；其余dot仍明确为INT64 oracle，不称整个矩阵真实S8 lowering执行。
- per-output乘积unit不同，先对齐到该row最细的乘积power2 unit，再以整数实际比较全部40logits、重选top8。只有整数分数相等时expert ID升序。共同logit最多S64候选，溢出拒绝，未偷偷以FP比较。
- top8消费者：delta×log2(e)的Q30常数1549082005，RNE到base2 Q7，范围[-16,0]，2049项uint32 Q24 exp2 LUT，随后精确整数除法RNE生成uint16 Q0.15，独立舍入的和差分配给第一名，使总和32768。LUT源用离线FP64 compiler生成；运行时核不调用浮点exp/div。LUT8,196B，必须和输入/结果/控制一起占库存，不能假设免费。
- 共同logit宽乘常数可能需大于64位，逐记录报告保守带符号位要求；Q15除法分子40位、分母28位保守能力，比较/位移、9倍S8 products、宽重组、LUT、divider、格式转换都未RTL实现。这里仅给功能参考和操作/字节义务，无目标周期/PPA。

选择性宽路由从当前W8编码计算保守误差区间：对每out，以共同整数unit表达ceil((2 sum|Acode| + 2 sum|Wcode| + K)/4)再按weight exponent移位，且输入无饱和，只有所选最小下界严格大于未选最大上界才保留W8，否则当前row重算W16。它不读FP64误差、未来hidden或评价标签；W16仍可能不具可证间隔。成本始终付一次W8，再为fallback付9份S8产品及宽流水。FP64同输入只是离线检查数学保证和误差，不参与选择。

数据键：numeric.npz中layer{L}.b{8|16}.weight_code/weight_exp；{case}.{profile}.{L}.{mode}.b{bits}.input_code/input_exp/dot/common_logits/common_exp/ids/gate_q15/lut_index/input_saturated/certified_top8/error_bound_codes，S16另lowering_rows/lowering_partials。共享lut.exp2_q24。selective.fallback_w16/ids/gate_q15指向动态候选，不复制同一payload。same_input_fp64_logits/ids/gate是显式FP诊断桥。report记录与同输入FP64和来源模型IDs两类差异，不混淆hidden漂移与router数值误差。

~~~sh
python project/experiments/closure/granite_numeric.py --reference NEW_TYPED_REFERENCE --binding FROZEN_BINDING.json --out NEW_OUTPUT
~~~

binding包含commit与granite_numeric_sha256；来源model revision、artifact大小/SHA、源码SHA和原FAIL回链保持。只由root在服务器Slurm运行真实张量。本机只17个合成测试。integer_softmax未串入expert down/scale merge，本实验不能证明完整MoE整数消费者或应用质量。
