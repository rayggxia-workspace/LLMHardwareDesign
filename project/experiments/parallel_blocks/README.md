# 独立并发 Block 实验

关联 [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)。本目录由并行会话维护；主线 `block_hierarchy/` 的 VECTOR、PG 修复和既有作业不修改。正式记录见 [并发试验记录](../../../docs/experiments/issue-7-parallel-blocks.md)。

四个独立 case：完整 llaccel v1 GEMM，以及 openTPU small 的 ACT、MXU、ACT＋MXU。后三项采用固定 D=32、MCOLS=2、ROWS=2、ACT_BLOCKS=32、ULANES=4、FIFO_DEPTH=64，保留原始 512＋128 bit ACT 读接口及其周期语义；合并包装按原 `otpu_slice` 连接信号，不加寄存器。它们是 O0-W／O1-W 的块实现准备，分开的两个块尚未重新组成顶层，因此暂不计算完整的分层收益。

源码使用远程只读 repo 的精确 `git archive`：llaccel `f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5`，openTPU `f237dab2f196855a59a083b1454786df8f01291f`。源码不改。openTPU 复用该 revision 的 ASIC RAM 映射和 **synthetic fakeram** 生成器，每个 case 只探测自己的 SRAM 类型，模型写入新 attempt。它不是已制造 SRAM，缺少真实 SRAM GDS／工艺签核，不能据模型得出量产面积或能耗结论。

```powershell
python project/experiments/parallel_blocks/submit.py --attempt parallel-blocks-01 --node node7
python project/experiments/parallel_blocks/monitor.py --attempt parallel-blocks-01
python project/experiments/parallel_blocks/submit_audit.py --attempt parallel-blocks-01
```

每次新 attempt 禁止覆盖，输出仅写入 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/<attempt>/`。一个 c64 Slurm allocation 申请 4 task × 16 CPU，四个 `srun --exclusive --cpu-bind=cores` step 各占 16 CPU，合计不超过分配的 64 核。任务名 `lyz-par4` 使用卢雨泽姓名缩写；不碰主线节点。所有作业 `--time=0`，提交后和计算开始时均核实 `TimeLimit=UNLIMITED`。

四路分别保存源与工具哈希、配置、stage 数据库／指标、日志、端口／RAM 清单和退出码；一路失败不取消其他路。批作业失败可能只有个别 step 失败，必须逐 case 判断。新产物哈希由计算节点生成，监视器仅采集轻量报告和已生成索引，不在登录节点运行物理工具或对大数据库重算哈希。

`submit_audit.py` 为同批次另建 `observer-v1/` 并提交一次性 `afterany` 审计；没有周期轮询。它在计算节点核对新产物哈希，保存每路执行及质量门槛（包括失败）到 `completion.json`。不重跑物理分析，不修改已提交 runner 或各 case 输入。监视器发现最终汇总与其计算节点 SHA 后，核对下载内容并保存在本地结果目录；摘要与原始 SHA 明确区分。

监视器将产物校验与物理预算门槛分别打印，四路旧终态的失败项为 `max_cap_zero`，不能只凭 `COMPLETED` 接受。最新快照新增各阶段电容违例数量、最终报告逐行电气违例、Slurm CPU／内存账单；`--verbose` 显示详细内容。冻结的 `completion.json` 保留原字节。本批四路均已结束，438 个产物条目校验通过，但仍有电容违例 49／2／12／41；详见正式记录的诊断与下一轮候选参数。候选参数尚未执行。

Nangate45：GEMM 3 ns／IO 0.6 ns，openTPU 2.5 ns／IO 0.5 ns；这是各自工程预算，不比较两个项目的绝对 PPA。35% 利用率、0.55 放置密度、原始数值及 lane 数保持固定。未提供完整外部驱动／负载或应用活动；本路线显式 `LEC_CHECK=0`，只推进物理工程，与主线仍运行的默认 LEC 分开。结构检查不代替回归或源 RTL 到物理网表等价。原始宽接口、完整控制和存储容量保留，未实施 128 bit 串行缓存方案。

本批 openTPU 将 IO delay 加到实际 clk，保留端口 hold 检查；历史完整 small 工程使用 virtual clock、端口 hold false-path 和 CTS latency hook。本批不复现该历史边界约束，因此不能直接用其已有 PPA 数字做前后收益比较。
