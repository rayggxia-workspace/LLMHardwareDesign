# R256 与六宏的独立适配验收

本文件是接入前冻结快照的历史审计。后续已补齐R的RTL实例、适配器和控制连接，并完成组合功能检查，见[当前接入报告](../../../../docs/CONTROL_R256_INTEGRATION.md)。下述原始缺项与证据按原冻结输入保留。

日期：2026-11-03，中国标准时间。Refs #162；本侧聊独立核验，不修改主控制/R1024工作树，不合并。

**结论：R256→E 状态读回/格式转换 RTL 实测通过；现有七宏系统不具备完整验收条件，未通过系统验收。** 缺项是实际 R 实例、R 适配器、包含 R 的物理组合与互联证据，不是本轮发现 R256 单宏功能失败。

## 输入与边界

- 控制源码冻结为 `227981d20e47238a5aa2ffbe04a3ae2f3e152659`；当前主线程后续代码不被改写。本结果仅约束该冻结快照。
- R 来自已经本地完整实收的 issue166 attempt252 冻结包，不使用正在修改的 HEAD RTL。原包 SHA256 `5733b1c0c9ed45aba7d8fa9f3edfcd76bc04b8464f7aef3853edb3cc1d7cca55`；原资格及实收回执随本目录保存。
- [INPUT_BINDING.json](INPUT_BINDING.json)、[INPUTS.json](INPUTS.json)绑定全部 41 份输入，包括冻结 R 两文件、E 及其余六宏/控制源码。
- `pair_re.sv` 只为验证接线，没有增加寄存器：真实 R 128bit 流水读回直接连接真实 E 的 op13 输入，ready 反向连接。测试固定移位参数直至所有包消费完成。
- 不修改任一合格宏。测试执行 load/read，没有执行 R 算术命令；不声称覆盖整个递推算术、全局事务、全模型精度或跨宏物理时序。

## 实测结果

Slurm 95847，node14，24 CPU，单节点；12 核编译后由 24 个独立单线程进程动态取用例。共 384 组（32 移位×2 bank×2 背压模式×3 初始化），检查全部 64 个128bit包/每bank；两个bank均先装入完整256个S32元素。覆盖 S32 极值、正负边界及随机数据、R 读回顺序、R/E 有限队列产生的背压、E 舍入/饱和及标志、高64bit清零和末尾复位清除有效位。

| 检查 | 结果 |
|---|---|
| 实际 R→E RTL 数据/握手测试 | 384/384 通过 |
| 核对数据包 | 24,576 |
| 核对断言 | 1,813,248 |
| 故意将 oracle 移位6改为7 | 检出数值不匹配，负例正确拒绝 |
| 全部41输入执行后SHA复核 | 一致 |
| Slurm | COMPLETED 0:0，17秒，资源已自动释放 |
| 最大RSS | Slurm回报0，未得到可信峰值，不据此推断内存需求 |

[实际测试回执](evidence/results/RECEIPT.json)、[编译日志](evidence/results/build.log)、[负例日志](evidence/results/wrong-scale-negative.log)、[作业记录](evidence/SACCT.txt)。本地共实收392份文件，384份用例日志逐项与回执SHA一致，见[实收索引](LOCAL_RECEPTION.json)。原始工具输出和失败保留。

## 七宏系统拒收原因

[实际顶层检查](evidence/results/STRUCTURAL_ACCEPTANCE.json)直接从去注释后的冻结 `control_system.sv`提取六个已知宏的真实实例，结果为 M/N/E/G/S/T；没有 R。

1. 当前顶层没有 `r_stream_local` 或旧 `block_v1_r` 实例。
2. 当前源码没有实际 `control_adapter_r.sv`，尚未实现对应的任务发射、状态搬运和完成/错误交接。
3. 未提供绑定上述R冻结源的七宏物理顶层、实际M11/M12、全跨宏提取时序与联合交付。六宏或R单宏的合格证据不转授给七宏组合。

这些缺项使完整系统验收不能通过。本轮只接受R→E读回转换这一项RTL接口证据。S/T的128bit包宽相同只说明便于适配；M/N/G的位宽、数值尺度及吞吐仍须由实际适配/调度兑现。

## 继续验收所需输入

实现并冻结 R 适配器、接入实际控制派发与队列、S共享端口仲裁、状态换页和跨块全局提交；给出有状态逻辑的固定物理归属。用硬件执行代表任务，完成含R的最终单元组合与背压/错误/复位/换页验证。新增物理块全部验收后，以实际七宏拓扑完成M11/M12、PG、分布RC和300MHz全端点检查。

本轮交付为独立验收证据。需要补齐上述实际硬件后，再启动完整系统验收。

## 重跑

在新的独立远程目录展开 `INPUTS.json`列出的精确输入（R冻结源码保存在本目录），把本目录 INPUTS.json 复制为远程根目录 INPUTS.json；通过Slurm提交：

```bash
sbatch --nodelist=<允许且可用的一个c96节点> \
  --output=slurm-%j.log \
  work/YUZE-LU/162/r256-acceptance-20261103/run.sbatch "$PWD"
```

runner要求不少于24个已分配CPU，结果目录必须全新。该命令仅重跑本报告的RTL接口测试与系统缺项检查，不执行物理流程，不授予系统资格。

协作回执：rayggxia-project-collab 1.0.0；负责人YUZE-LU；`check_project.py`及输入Python语法检查通过，仅覆盖对应范围；登记沿用management-hub PR5 pending；本快照无config/board.json，看板unverified/同步pending，处理人待指定；Issue162仍为开放任务，本轮不改其状态或并行PR163。不自行合并，审查人待指定。
