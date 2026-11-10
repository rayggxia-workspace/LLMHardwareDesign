# 接续 #247 的四轮研究

Issue [248](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/248)，负责人 YUZE-LU。
冻结父版本 PR243@9d987151ee687322c0ce52d69a0a14f2275bd52b。仅新增隔离目录，保留原 P/U 生产实现和冻结证据。

1. `prepare.py` 逐字节恢复 run23 输入，调用原 R4 生成链。`generate.py` 独立扩展：静态 W8 权重进入有限双 operand bank，DMA 写与 M 读共用各 bank 的单端口日历，不占普通 S。
2. `w8_stream_mac.sv` / `w8_weight_buffer.sv` / `w8_dot_candidate.sv` 实现 K16/N8、A8/A16、两槽 B 缓冲、512bit DMA 两拍填包；A8/S32 或 A16/S40 全 K 累加。是新叶宏候选，不替换已验收 M；输出尚未接原生 S 写回/局控。
3. 同资源比较 17.1/51.2/102.4 GB/s，另列 256B DMA beat 与第三 P 的新增资源。2通道每拍64B入口的聚合上限38.4GB/s不会因提高 DDR 参数自动消失。
4. `planner.py` 的贪心/DP 共用状态转移，选择 K/上下文/一个持久 A 对象；`SQ_PLAN` 由 SystemC 实际消费，容量扣账、冷/热搬运和保留描述符计费。精确性仅限声明的加性估计器，不声称全系统全局最优。

## 范围与验证

`run.py` 必须在 Slurm 分配节点执行 EDA。先验证独立整数 RTL，再要求关闭扩展时完整 RESULT 复现原 run23，然后运行各轮消融。`numeric.py` 是独立无界整数/RNE参考；`quality.py` 另做真实 checkpoint 的量化筛查，非线性及 KV 保持浮点，不能冒充整数整机生成。

模型的 SQ_ABITS 是静态权重 Dot 的接口候选。原图张量保留原格式；每个符合条件的不可变 A 对象经 U 两遍处理，生成新 A8/A16 对象，显式支付扫描、转换、写外存与 ACK；多个 Dot 复用这个新对象。动态 Attention Dot 和多行 prefill 保留旧路径。全 K 使用共同尺度，中间片不舍入。`w8_requantize4.sv` 独立验证 S64×正 S16 系数、移位、RNE 和饱和；尺度发现与系数逼近还未与整个模型联合验证。

计时模型仍用两个 K256 权重 tile 的 bank 日历及原命令尾费；RTL 是两个 K16 packet 槽。它们验证的是同一方向的有限缓冲候选，但**未做完整 P/DMA 周期校准**。16 KiB 模型预算仍为双 B tile 扣账；RTL 额外寄存器槽另计，不能宣称免费复用现有 SRAM。各文件头的范围以及正式报告中的覆盖表优先。

`planner.bundle()` 输出与执行文本共 binding ID 的研究 IR 和部分操作数端点需求；`complete_static_net_set=false`，尚无真实 pin 绑定、结果/控制/ACK 全网、母控/局控二进制 lowering。它不能直接交给物理后端部署。A8/A16 新 M、转换器、普通 S 和 DMA 的联合 RTL、整模型整数结果、物理面积/STA/P&R、DDR PHY 及能耗尚未取得资格。

M1–M10 必须包含新的 bank、选择器、转换与控制；M11/M12 只连接真实预留端点。P/U/C/F/J 仍为控制分组，未重新变成大硬框。基于旧条件模型的吞吐不能代表生产 RTL 已达到。

## 复跑入口

```powershell
python -B project/experiments/stream_quant_synthesis/planner.py
python -B project/experiments/stream_quant_synthesis/numeric.py
python -B project/experiments/stream_quant_synthesis/deploy.py 13 --out <新的本地任务输出目录>
```

部署器要求新的服务器目录，归档 HEAD 的 LF Git 源、保存 commit/SHA、Slurm 分配与运行回执。Windows CRLF 工作树不能直接跑旧版本的源码 SHA 锁；部署器用 `git -c core.autocrlf=false archive`。已有运行不覆盖。完整结果见 [四轮报告](../../../docs/experiments/issue-248-stream-quant-synthesis.md)。

纯证据核验不启动 EDA：`python -B work/YUZE-LU/248/verify.py`。新增运行完成后，用 `collect.py <tag> --jobs <真实作业号>` 回收并逐字节核验；用 `report.py --root work/YUZE-LU/248 --run <tag> --quality-run 08` 生成对照摘要及正确位宽的操作数需求。历史包保持原样，包括 run12 中早于修正的 coupled bundle；重新导出的 bundle 不改变任何已执行的 K/context/cache 文本。
