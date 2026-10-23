# Issue39：本机KV量化归约与bias实验

2026-10-23（UTC+08:00），Liangruizhi；[Issue39](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/39) /
[PR40](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/40)，待审查合并。
正式源码`a83e624a10ecc3f012eff2f2f770c9f9842c3a76`；代码及冻结配置`project/experiments/kv_scale/`。

## 问题、输入与执行范围

在先架构筛选的Issue37之后，用户授权本机继续实验，并要求给师兄Codex文案。
本轮不下载权重、不运行大模型/GPU/服务器；不接管Issue32或整合师兄数据。
复用Issue27官方固定Qwen3-0.6B真实FP32 CPU捕获：层0，query head0、KV head0，post q/k norm和RoPE；
prefill32 Q[32,128]/KV[32,128]，teacher-forced最后decode48 Q[1,128]/KV[48,128]。
已有模型revision `c1899de289a04d12100db370d81485cdf75e47ca`，捕获源码`6ffb9417f0f01f614b733ce6c3ca9837906b3203`；
归档SHA `f760dec66344c11fe9c7f04f55d91f610157d7ad624f6d66faa6a9bbdb1f1588`，
原始NPZ SHA `58310ef9e33b4b701dfb83f38b92be633690fcc545af94bc2a9b38d0d0b082e7`。
原始token/权重/配置逐文件SHA沿捕获manifest保留，没有把旧FP32结果改写为INT8。

本次使用Python3.13.14/NumPy2.5.4、CPU Python整数参考；无需加载PyTorch或模型权重。
2捕获×3块长(8/16/32)×2概率(P7/P15)×2输入profile，共24组合。
direct采用Q逐行、K/V逐token块的离线2幂scale；balance在post-RoPE按通道q乘2^g、k乘2^-g，
g由当前完整捕获maxabs离线拟合、限制[-8,8]，未量化实数QK点积保持。

**证据边界**：块max和g使用当前完整张量，包含未来token；每个捕获独立拟合，
不是prefill→decode共用一套冻结scale的连续量化模型。因果mask并不能消除scale来源的前视。
因此本轮是整数实现/局部误差诊断，不是模型因果正确性、保留质量或全模型W8A8验证。
GQA其他query头尚未验证同一KV变换，g也不一定在RoPE配对通道相同，不能免费折进RoPE前投影。

## 数值合同及实际实现成本

| 路径 | 本次实际执行 | 实现与尚未证明的能力 |
| --- | --- | --- |
| Q/K/V | [-127,127] signed8，i8 dyadic exponent | offline float求scale/转换；在线生成与缓存更新硬件未实现 |
| QK | signed8 dot，逐步checked i32；score i16/f8 | M:u31/r0..63离线编译；一次RQ为25个signed8部分乘法、i64加移位/RNE/Sat16 |
| softmax | 显式mask、max、4097×u32 exp ROM，P7或P15 | 每概率u64恢复除法64步；ROM至少16388B，不是底座已有能力 |
| PV | P7×V8一个signed8乘法；P15×V8三个signed8部分乘法 | 每块部分和checked i32；不把P15视为普通W8A8单周期矩阵 |
| 块间V scale归约 | i32部分和按exponent在i64内对齐、求和，最后RNE除以127/32767和Sat16/f12 | scale跨度>31或宽移位/求和溢出拒绝；每输出64步除法，宽加/移位/暂存成本单列 |
| bias（合成） | checked i32 acc + i32 bias → i33，再M31乘/RNE/Sat8 | 33×31仍需25个8位部分乘积及i64归约；现有RQ32 RTL不支持33位输入，未新增RQ33 RTL/PPA |

所有精度/粒度、M/r、scale、输入/整数中间值、计数在归档内；mask后的零乘没有做跳过优化，
计数是当前参考算法的密集执行，不能当优化后的硬件最小周期。无wrap允许通过。
数值内核为整数；外围scale编译、balance转换及误差计算为浮点，不能宣称全整数在线模型。

## 实际结果与失败

以下为块长8、P15的局部head输出相对RMSE，参考为同捕获的FP64独立attention；
该FP64与保存的真实FP32 head输出在1e-4绝对/相对容忍内一致。

| 捕获 | direct | 同张量离线QK balance | 解释 |
| --- | ---: | ---: | --- |
| prefill32 | 42.5905% | 2.3120% | direct输入量化单项42.5922%，主要不是最终RQ误差 |
| decode48 | 15.2032% | 4.0788% | 不表示长序列误差或正式质量门槛通过 |

真实prefill K maxabs253.716、median abs0.766；decode K maxabs276.012、median abs0.764。
粗粒度scale受到少数通道大值影响；direct K8步长2或4，balance此样本降至1/16。
这只是定位与候选，尚无独立校准/评价、全层/GQA共享或在线转换代价验证；不得宣传为新量化算法或泛化收益。
P7在balance decode局部误差5.9435%，P15为4.0788%；概率精度与乘法成本耦合，不能只看KV存储。
合成长度512均匀行再次检出P7全部概率舍成0，P15保留非零值；本轮没有512长度真实模型推理。

- 24组合共**89280个整数值**与不导入目标内核的Fraction oracle相同；零溢出异常，
  饱和/截断计数按每例原样保存，零异常不代表任意输入不会溢出。
- **6个适用的真实K scale错误实现全部检出**；另外42个真实负例不适用，
  因scale相同不能构成反例。本次真实V scale均相同；不能称真实异V scale已经测过。
  独立合成V反例把不同scale错当相同，输出应9却得到2，已检出。
- bias合成边界显示INT32相加wrap会把正确127/-128变0；动态A scale下复用首行bias也检出错误。
  这是独立合同测试，不是Qwen2真实bias质量证据。
- 11项测试覆盖1055组独立RQ33边界/随机组合、800个不同scale PV输出、P7长行、
  8/16位乘法成本、宽溢出拒绝、错误scale及缓存追加改变旧token编码等；测试组数与比较值数分别记录。
- 独立来源审计检查**296448个量化输入值、540个scale指数**与原始FP32/精确dyadic关系，全部通过。

## 对Block边界的受控启发

同样一套数值函数与一份reducer资源，在V/PV侧完成跨块对齐再发i16结果，或将每块i32部分和＋scale
发到共享向量侧对齐。候选库存相同：一个reducer、32KiB accumulator、2KiB staging；按共同最大三行微块串行，
64B beat、8B packet header、i8 exponent、16B/cycle link，1RW staging每beat写/读一次。
12个(rows1/4/32 × KV块1/2/4/8)账本通过容量/打包检查，最大packet≤2048B。

单行d128的近端方案传最终结果320B；共享侧传1个部分和块576B、8块4608B。
对应**边界link服务**20cycle与36/288cycle，staging访问10与18/144个beat。
它不含完整矩阵/权重/其他边界、并行重叠、反馈时延或实际宏端口和物理路径，不是1.8/14.4倍端到端加速。
更大行微块可改善打包但受有限staging约束，不能只比较有效字节；所有宽状态暂存也应纳入库存。

这一结果支持把“部分和＋scale＋对齐归约”作为**共同评估的候选边界**；
不能仅把RQ移到矩阵旁边、忽略scale和wide reducer，便宣布划分完成。
制造前固定能力还需独立量化质量和真实端口/布线/时序证据；跨产品连接选择暂未据此最终冻结。

## 重放、版本与交付

从干净源码a83e624a执行run01/run02，五个科学结果文件逐字节一致；原始两个manifest及全部检查日志一起归档。
源码11个文件版本绑定、5科学文件SHA、24例覆盖和89280值独立重放通过；管理检查和git whitespace检查通过。
`project/experiments/kv_scale/results/issue-39-run01/index.json`记录压缩包/成员SHA，
`work/Liangruizhi/39/manifest.json`记录本次交付文件SHA。原始2.18MB整数payload保存在小型压缩包内，
没有新增权重、大trace或上传凭据。提取及离线核验：

```powershell
python -B work/Liangruizhi/39/verify.py --extract D:/Projects/Codex/kvscale-20261023/delivery-replay
python -B project/experiments/kv_scale/audit.py D:/Projects/Codex/kvscale-20261023/delivery-replay/run01
python -B work/Liangruizhi/39/audit_inputs.py D:/Projects/Codex/kvscale-20261023/delivery-replay/run01
```

本机本轮交付待审查/合并，非done；线上Issue/PR状态以读回为准。登记PR5 pending，
无board.json/Projects条目工具，看板unverified/同步pending，管理员/审查人待指定。
下一步不重复兄方GPU：可复制[实验文案](../handoffs/2026-10-23-gpu-codex-experiment-prompt.md)，
先续Qwen、条件Gemma、策略冻结后Phi；在线整数scale、独立质量/长状态及物理资格尚待补齐。
