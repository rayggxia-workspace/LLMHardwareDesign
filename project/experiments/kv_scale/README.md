# Issue39：KV scale归约与bias边界

只在本机CPU复用Issue27已有Qwen3-0.6B层0/head0真实输入，不下载权重或启动其他机器。
`experiment.json`冻结候选；`core.py`执行整数路径，`oracle.py`只用独立Fraction算术核验。

```powershell
python -B scripts/check_project.py
python -B project/experiments/kv_scale/test_core.py
python -B project/experiments/kv_scale/run.py --output D:/Projects/Codex/kvscale-20261023/run01
python -B project/experiments/kv_scale/run.py --output D:/Projects/Codex/kvscale-20261023/run02
python -B project/experiments/kv_scale/audit.py D:/Projects/Codex/kvscale-20261023/run01 --replay D:/Projects/Codex/kvscale-20261023/run02
```

正式run要求工作区干净、输入归档SHA和源码commit字节匹配，拒绝覆盖已有输出。
上述两次正式运行来自源码a83e624a；最终交付后结果位于results/issue-39-run01/evidence.zip与index.json。
运行`python -B work/Liangruizhi/39/verify.py --extract D:/Projects/Codex/kvscale-20261023/delivery-replay`，
再以解压的run01作为audit.py参数复核；输入源审计用work/Liangruizhi/39/audit_inputs.py。
如从后续commit重新运行，新的source commit和SHA会据实记录，不冒充原a83e624a运行。
试开发必须`--development`且不能当正式证据。结果最终随Issue39归档交付，已有输入仍在Issue27归档。

Q/K/V量化、QK平衡、bias和M/r编译为离线浮点探索；之后dot/RQ/LUT/P/PV为整数参考，
不构成全整数在线模型或实际INT8速度。量化用本次完整块最大值，会读取未来块成员；
prefill因果mask没有消除这一scale来源的前视。因此不拿该实验的输出证明在线模型因果正确性或质量。
平衡用post-RoPE逐通道q乘2^g/k乘2^-g，真实dot保持；没有实现前端浮点到定点转换/动态求scale硬件，
额外转换与128个指数元数据显式记录，不把其误差变化归因于placement或声称新算法。

P7/P15和整型输出分别记误差；P7×V8用一个signed8乘法，P15×V8使用三个signed8部分乘法与宽加法，score重定标使用25个。
PV部分和逐步检查i32；不同块V scale在归约内移位对齐至i64，最后一次RNE除法和Sat16。
scale跨度>31或宽移位/求和越界拒绝。softmax显式4097×u32 ROM和逐概率64步恢复除法；
其ROM/算术并非目标底座已有硬件。软件循环时间不当作硬件周期。

transport是同一reducer及相同32KiB accumulator/2KiB staging、固定行微块、64B beat的边界服务账本，
不含完整LLM调度、权重搬运、矩阵时延或物理引脚/布线/时序证明，不能报告端到端加速。
整数bias为合成边界测试，不能称真实Qwen2量化bias已经验证；RQ33尚无RTL实现证据。
