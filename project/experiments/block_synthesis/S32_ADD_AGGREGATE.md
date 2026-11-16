# 原生 S32 加法聚合：已验证的后端原型，未注册综合候选

Refs #219 / PR220，2026-11-09。这里扩充可执行方式，不是一次 DP 算法加速。
目前没有改变 `compile_graph`、DP、贪心、默认动作池或已发布计划。

## 为什么做这项检查

`streaming_ir.primitive_body(Add)` 的保守实现逐元素执行：每个输入先 `split32`，
再做三个 M partial，最后一次 S32 饱和读出。每次原生命令的输入/输出都显式经外存复制。
只更改就绪队列排序不能自动消除这些复制。

已有 M 支持多行。这里验证将 r 个互相独立的元素作为同一个 r×1 累加上下文，
共用 B=[1,0,…]。没有添加累加器、窄化原始数据、改变舍入或假定宏间旁路。
Add 的每个输入符号可以为 +1 或 -1，覆盖真实图里的减法组合。

对于任意 S32 x，原准备产生：

```
lo = signed16(x)
hi = x >> 16
flag = (lo < 0)
x = lo + (hi + flag) * 65536
```

每个输入三个分量各一次 feeder、Scale(sign, shift=0/16/16)、Execute。
只在第一项 clear，全部输入累完才饱和为 S32。不能逐输入饱和，否则取消相加会错。

## 可核查的数据和命令

`add_tile_recipe.commands` 给每条外部记录明确的对象/元素/输入/分量身份。
P.S[0:8] 放逐行分量，S[16:24] 放 B；先执行 16 次真实零包 LOAD 和一次常数 1 LOAD。
每片结束对 S[512+8*row] 等待真实写 ACK，再 STORE；最大地址范围 569 个 128 位记录，
小于 16 KiB 的 1024 条。没有让未初始化 padding 成为隐含零。

输入的准备分量是外存中的显式对象。本探针从这些记录开始，**不包含 split32 准备验收**。
完整绑定必须继续支付原来的 split32 命令和所有准备复制。有限准备临时区也是硬限制：
每片需要 `3 * inputs * rows` 条，原有 64 条区域下，四输入最多允许五行。

测得的边界时延只用于这个经过验证的 P/feeder 服务，不推断任意同字母实例的外围能力。
`aggregate_cost` 仅计算聚合及其真实 LOAD/STORE，明确返回 `preparation_included=False`。
它不是完整编译器 cost，也不是整机周期或物理 300 MHz 资格。

## 实际验证与复跑

`s32_add_probe.prepare` 先只读重验已有 column 证明，然后按 SHA 复制未修改的 P/M/S/feeder RTL、
原握手任务和指定 SRAM 银行模型。编译需原有 G 表 include：

```text
python s32_add_probe.py prepare QUALIFIED_COLUMN_PROOF SRAM_BANK NEW_PROBE
cd NEW_PROBE
iverilog -g2012 -Irtl/block_v2 -s tb_s32_add_probe -o probe.vvp -f compile.f
vvp probe.vvp +sinit=0 > simulate-0.log
vvp probe.vvp +sinit=1 > simulate-1.log
vvp probe.vvp +sinit=2 > simulate-2.log
python ORIGINAL_SOURCE/s32_add_probe.py analyse NEW_PROBE NEW_PROBE/simulate-0.log
```

三种银行初态各 384 例：rows1–8、输入2/3/5/17、正负溢出/取消相加/随机、三种符号模式。
检查原始 S64、最终 S32、实际 SRAM 写后读、A/B/宽读/写 ACK 数量及完成背压保持。
被动监测重建逐行 P 命令和 feeder 的固定服务时延及样本守恒。
另将第一例 S64 golden 翻一位，实际 vvp 必须退出失败且命中 `Add raw S64 mismatch`。

`replay` 用有限 SRAM、实际地址、feeder 快照、累加上下文和写 ACK 顺序解释生成命令。
70 组尺寸/尾片/符号与独立 Python 整数基准一致；成本按逐事件相加另行核对。
它不调用向量 sum 替代实际命令。仍不是完整系统或 split32 RTL 联调。

## 机会调查，不是加速结果

```text
python add_tile_survey.py CHECKED_IR CHECKED_PLAN ADD_PROOF NEW_REPORT
```

调查先独立验证旧计划和成本，确认 probe 来源与该硬件的 P 资格相同。
只看已选 M/E 实例上的 S32 Add，原 split32 工作全部按旧价计入，遍历有限临时区允许的1–8行。
真实 FFN 的23个 Add：串行成本总和 901,467,136 → 632,654,644 模型 ticks（少29.8194%），
逻辑128位搬运记录 30,448,128 → 21,465,991（少29.4998%）。
这些是 Add 子服务成本机会，**没有重调度，因此不是 FFN 完成时间，更不是算法20%**。
未接入整网数值、同池对照、控制程序、SystemC、物理或能耗验收。

## 接入前还必须补的合同

1. 用实际 SSA、索引和有限临时外存解析调试命令，计入全部准备及复制；每个候选记录资格来源。
2. 新聚合覆盖 P.S 工作窗口，必须在 DP/贪心前沿显式作只读缓存失效，并由独立检查器重建。
3. 原生成本、阶段资源、静态网、流量/利用率审计和有限 S 数值解释器同时支持，不能只改 ticks。
4. 先保留全部旧动作，再向强贪心、旧 DP、新 DP 提供同一完整动作池。单独报告共同后端收益。
5. 对新选中的 FFN/整网计划做自己的数值验证；旧计划通过不自动转移。

这还没有解决一般脏中间结果驻留。下一步要让前沿记录对象/分片、所在 S 窗口、有效时间、
是否已有外存副本及剩余消费者；保留、迁移、必要写回和丢弃都必须有实际服务支持。
外存访问能否消除，由地址、数值表示、S 容量/端口和 ACK 决定，不能以理想数据流图扣账。

另一个待验证方向：原 P 有 `cmd_pack16`，但已有 tile 探针将其绑0。
普通 width16 ReadFinal 仍是四个符号扩展 S32 槽，不能假装它自动密排八个 S16。
动态 K4 聚合/打包若采用此接口，需独立验证原生 gather、四列读出、pack、实际 S 写 ACK、
准备复用和全部搬运，不能将 host numpy 重排视为硬件能力。
