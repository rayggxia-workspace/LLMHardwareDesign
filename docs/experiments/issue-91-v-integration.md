# Issue91 V/S整合：容量与重读的结构证据

2026-10-25；任务[Issue91](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/91)，负责人Liangruizhi。首轮结论：**16KiB S可以容纳H2560完整I32 X/Y、256元素gamma tile、512B Vframe以及4KiB A-cache；不必为了放gamma而把X也分块重读。** 这约束了下一步电路设计，尚未证明新RTL周期、面积或数值通过。

源码冻结 `8fa5dde64dc26802087cd618d8a8d95bc8dd268a`，父85/PR89基线 `d60fac795ba6341df2e48804df564afd3e4e9818`；本机仅运行标准库纯结构/符号行检查，没有运行模型、真实张量、RTL、综合或服务器任务。实时读回PR89已推进到`eef976d3`、PR90到`3301e1b2`；本合同没有把它们的新成果归入本实验。旧84/85证据不改写，成员55/63范围不接管。

## 具体候选和计数

[合同](../V_S_INTEGRATION_CONTRACT_V1.md)给出地址、live-range、scale、命令、仲裁、错误恢复及新增库存。[分层验收表](../BLOCK_LIBRARY_ACCEPTANCE.md)明确六Block的现状与缺项。下列计数来自完整逐行枚举及不导入生成器的独立接收器：

| norm profile | 活跃S容量 | 外部读/写事务 | S读/写事务 | 外部payload | 原型5×128-bit wire |
| --- | ---: | ---: | ---: | ---: | ---: |
| H1536原full-gamma容量布局 | 16384 B | 768 / 384 | 1536 / 1152 | 18432 B | 92160 B |
| H1536 gamma256、保留Vframe/A | 11776 B | 768 / 384 | 1536 / 1152 | 18432 B | 92160 B |
| H2560 X常驻、gamma256、保留Vframe/A | 15872 B | 1280 / 640 | 2560 / 1920 | 30720 B | 153600 B |
| H2560 X/gamma都流式、tile1408、保留Vframe/A | 15872 B | 1920 / 640 | 2560 / 2560 | 40960 B | 204800 B |

H2560两个候选均为同一16KiB单1RW存储、同I32精度、同512B frame/4KiB A占用；X常驻省去第二遍的640条128-bit外部X读取及640条S写入，即10240 B有效数据、原型51200 B wire和10240 B S行流量。**这是计数差，不是端到端cycle/面积/能效收益。** 不把gamma按tile分别归一化，全H只计算一次den；不新增double-buffer。

共同基线是 **source X/G initially external**，包含输入staging、全行stats、输出计算和Y drain。若接回M且X已在S，需要单独改生产者/消费者基线；X流式对照可能必须先spill M结果，此成本不能遗漏，也不能把已有X加载再算成“节省”。原型wire不含epoch tags/descriptor/配置/程序/LUT/frame访问及软件pack；所有这些须在整合RTL计入。表中的frame仅保留容量，没有执行V程序。

H1536原fullX/fullgamma/A外加frame、H2560 fullX/fullgamma/frame两种非法布局被明确拒绝。合法的post-M frame覆盖仅在A租约释放后成立；原位Y在全行统计完成前禁止写。

## 验证证据

- `scripts/check_project.py` PASS；仅管理结构。
- 23个结构/协议语义单元检查 PASS：容量、对齐、活跃区重叠、非法免费frame、全行stats、错误gamma、有限response、完整consumer/egress、不能读未写数据、不能写A/guard、完成前后顺序等。
- 8布局（6合法/2预期拒绝）、4完整符号行trace，独立重建每条line的来源、生命期和闭式事务数量；18个代码/配置/旧实际源逐字节匹配原Git blob。
- 入仓副本再接收 PASS；四个交付负例实际拒绝：删除gamma-release后重签SHA、伪造计数字段为bool、伪造原源码SHA、添加未知“RTL_PASS”字段。未只依赖文件hash验收。最终归档时原Windows CRLF负例receipt与强制LF重放的逐字节断言失败，四个语义结果均一致；保留serialization-erratum.json及原Git版本，统一最终LF并更新索引，两个干净重放的receipt逐字节相同，trace/report和所有计数未改。
- [统一结果索引](../../project/experiments/v_integration/results/issue-91/index.json)、[报告](../../project/experiments/v_integration/results/issue-91/report.json)、[独立接收](../../project/experiments/v_integration/results/issue-91/receiver.json)、[实际命令/日志](../../work/Liangruizhi/91/execution.json)。report SHA-256：`145956d188d24b05b96fdd1c08008c3c5abc337c716e286ea9b0c1da898c1efc`。

以上是结构证据，接收器没有计算任何tensor值，也未验证ready/valid逐周期仲裁、RMW原子性、SFU算术、实际gamma控制RTL或PPA。把这些写成已实现属于证据越界。

## 对边界设计的决定

1. **先验证地址和生命周期，不增加SRAM。** H2560完整X/Y10KiB是可行候选；gamma1KiB/512B frame/4KiB A仍合法，保留512B空隙但不拿来暗加FIFO。
2. **通用V整合需要新增有价控制/byte非乘ALU。** 不能把旧8lane byte_alu旁挂后仍称只有8S8；共享M lane0需要新增可实施mux/模式。现有S32/SFU不免费支持A概率/KV或R更新，宽格式需分解/专用化和计费。
3. **程序和LUT分开。** 原1.93MB程序外存+16B取指cache，原128KiB ROM只存数据LUT。C0外置LUT会增加有限外部流量；C1片内ROM是不同库存候选，不进行伪同资源面积比较。
4. **下一实现只先做gamma streaming。** 保持精确整数norm合同，闭合H1536回归/H2560全行den、gamma credit与恢复。随后复用旧74真实gate/up，加SiLU→全512 scale→A8→真实M，8个delta来自RTL而非继续引用原捕获header，最后才做综合/电气与同资源周期比较。

本阶段Issue91本地可交付，远端发布/PR/看板由根会话统一处理；不合并、不done。没有新增模型或其它机器任务；所有未完成RTL/物理项保留在合同和交接。
