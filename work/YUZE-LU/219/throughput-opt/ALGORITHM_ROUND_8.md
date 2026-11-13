# 迭代8：整图tile数值、原生N修复和资源占用诊断

2026-11-09；Refs #219 / PR220，继续in_progress。算法约20%、完整KV、校准整机时间/能耗/token/s和最优适配对照均未完成。

## 新增的实际证据

- 不变tile配方增加C++有限S数值执行器。逐次128位S读写、有效位、最多8×8 S64上下文、packed/flag、
  E ASR15及三次M scatter都实际参与计算，独立逐项计数对照；68个边界/随机例通过，损坏基向量必须失败。
  C++只加快宿主仿真，不减少模型ticks，不是新增硬件或RTL证据。
- 完整Qwen2.5-3B、36层、embedding及LM head、B1/S2 prefill无KV，新tile贪心和选中DP两个计划各三输入逐位通过。
  每次包含253项tile Dot，HF L2仍为0.5265177% / 0.7250722% / 0.5591736%，两位置argmax及logits SHA保持。
  101484及101483均COMPLETED0:0，原件逐项回收SHA。**这两次使用历史NExp模板计成本，
  数值执行使用正确独立N参考，因此只能证明整数向量/tile行为，不能证明旧N原生命令语义。**
- 核对PR235发布的缺口后，确认原NExp的Stats(x)与所需exp(x-max(x,0))不同。现改为两次显式
  Stats(x)、Stats(0)，不假设能免费拼出[x,0]。原生N RTL三个初态各653例通过；高位污染、背压、
  负数及输出零扩展均检查。旧模板在x=-32768输出32768而参考为0，被负对照拒绝。
  101487 COMPLETED0:0；这是编译合同修复，不是硬件缺陷或性能优化。
- 独立检查器新增顺序/来源/常量检查，拒绝历史NExp IR；保存的向量程序必须重编译、重新调度。
  每输出新增一次真实读和Stats成本，所有基线共用。修正后的整图贪心数值101491已COMPLETED0:0，
  三输入仍逐位一致/HF误差及argmax保持，IR/计划SHA与重编译实际输出相符；搬运8,249,969,596条逻辑记录。
  新完整DP对照101489已COMPLETED0:0：贪心249,853,884,670，旧DP/条件DP均202,663,587,646，
  新策略相对较强同池旧DP额外0。其选中DP计划数值由attempt269 / Slurm101493补验，尚未给出终态资格。
- 最终源Windows与独立WSL/Linux各187项通过；服务器重编译源187项通过。项目结构检查通过。

## 算法对照：保持较强分母

新增可选整数资源价格下界，见[数学与边界](../../../../project/experiments/block_synthesis/WORK_PRICE_BOUND.md)。
它在每个前沿按已完成集合、当前日历、网并集及合法绑定重新计算剩余工作下界，不修改硬件或执行成本。
独立穷举、小图、多槽、大整数及复合绑定通过；150个随机诊断有57胜、16负、77平，仅作诊断。

修正NExp后的真实FFN：88原语、74服务、2033个顶层绑定（含孩子共2885个独立审计项），
九组、每S16KiB、18束上限、同候选及数值；各新计划逻辑搬运195,194,672条128位记录。

| 策略 | 模型ticks | 实际逻辑束数 |
| --- | ---: | ---: |
| 普通贪心 / HEFT式 | 5,924,911,296 | 10 |
| 旧DP / 条件尾部DP | 5,304,003,776 | 18 |
| 资源尾部贪心 / 价格贪心 | 4,397,032,640 | 18 |
| 资源尾部DP / 价格DP | 4,225,968,320 | 18 |

相对最强同池基线资源贪心，额外 **3.890449%**；不能取较弱的旧DP分母宣称20%。价格策略没有新增收益，耗时更高，保持可选。
这里是修正后原生成本/地址/计划审计，**该资源DP切片未单独完成数值回放**，不扩大为系统性能。

历史N成本的全图消融也没有复现切片收益：旧DP/条件DP202,642,188,094，资源/价格DP382,288,250,278，
后者还选择更多逻辑搬运。保留负结果，不改成默认。这些旧ticks只作为历史诊断；修正N后完整对照重新计算。
同池能力扩大、tile共同后端和C++宿主加速均不计入算法20%。

## 占用分析改变了下一步

修正后FFN选中计划中，两个虚拟外存通道的整服务预约接近或等于整个完成时间；这不是DRAM忙碌率。
三项tile给U0.E的预约合计3,658,163,392 ticks；E服务与其读写描述符合计685,824 ticks。
例如v202：预约1,221,178,304，但串行E段313,728（0.02569%）。

差额不是可直接扣除的时间。当前合同确实锁住整段M/E/S/LC/通道，编译器不能擅自复用其中任何资源。
下一轮应以实际ACK/数据生命周期为切分边界，把packed/flag持久对象、E临时槽、M上下文与选择一致性写进前沿；
再让其他服务在合法窗口进入。若采用整Dot的分阶段物化，额外外存临时区、重新初始化和搬运必须显式记账；
若采用逐tile事件前沿，活动任务/队列/循环PC必须有界，不能把K逐拍展开成不可运行搜索。
新动作族仍同时交给强基线，搜索收益独立计量。一般跨算子脏结果驻留、K打包及真实DMA仲裁尚未实现。

## 回执与恢复

[精确原件归档、源快照及SHA](results/column-tile-round8-final/manifest.json)，
[修正后完整DP终态补充](results/column-tile-round8-final/corrected-dp-manifest.json)。N配方及复跑见
[NEXP_CONTRACT.md](../../../../project/experiments/block_synthesis/NEXP_CONTRACT.md)。
首次宿主GLIBC不匹配用同容器wrapper修复；首次历史字段名失败和采集路径笔误保留，没有改硬件或删除检查。
100972早期冻结源已COMPLETED0:0（1h38m17s），不再报告运行；其历史N边界同上。

主要命令：

```text
python -m unittest discover -s project/experiments/block_synthesis -p "test_*.py"
python project/experiments/block_synthesis/recompile_ir.py OLD_IR NEW_DIRECTORY
python project/experiments/block_synthesis/tile_review.py NEW_DIRECTORY/ir.json NEW_REVIEW --registered-ir --wire-budget 18
python project/experiments/block_synthesis/reuse_validate.py --tile-worker WORKER IR PLAN CALIBRATION ACTIVATIONS LOGITS NEW_NUMERIC ORACLE
```

规则rayggxia-project-collab1.0.0；项目llm-hardware-design，负责人YUZE-LU，Issue219 in_progress；PR待独立审查，不自合并/关闭。
登记management-hub PR5实读open/未合并pending；缺board配置/Projects能力，看板unverified/同步pending，沿用Issue7交接。
没有新增完整MC/LC、DMA、系统RTL/物理、完整KV、整机SystemC、能耗、token/s或最优适配ASIC/FPGA通过结论。
