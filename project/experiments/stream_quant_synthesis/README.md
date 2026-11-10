# 接续 #247 的四轮研究

Issue [248](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/248)，负责人 YUZE-LU。
冻结父版本 PR243@9d987151ee687322c0ce52d69a0a14f2275bd52b。仅新增隔离目录，保留原 P/U 生产实现和冻结证据。

1. `prepare.py` 逐字节恢复 run23 输入，调用原 R4 生成链。`generate.py` 独立扩展：静态 W8 权重进入有限双 operand bank，DMA 写与 M 读共用各 bank 的单端口日历，不占普通 S。
2. `w8_stream_mac.sv` / `w8_weight_buffer.sv` / `w8_dot_candidate.sv` 实现 K16/N8、A8/A16、两槽 B 缓冲、512bit DMA 两拍填包；A8/S32 或 A16/S40 全 K 累加。是新叶宏候选，不替换已验收 M；输出尚未接原生 S 写回/局控。
3. 同资源比较 17.1/51.2/102.4 GB/s，另列 256B DMA beat 与第三 P 的新增资源。2通道每拍64B入口的聚合上限38.4GB/s不会因提高 DDR 参数自动消失。
4. `planner.py` 的贪心/DP 共用状态转移，选择 K/上下文/一个持久 A 对象；`SQ_PLAN` 由 SystemC 实际消费，容量扣账、冷/热搬运和保留描述符计费。精确性仅限声明的加性估计器，不声称全系统全局最优。

## 范围与验证

`run.py` 必须在 Slurm 分配节点执行 EDA。先验证独立整数 RTL，再要求关闭扩展时完整 RESULT 复现原 run23，然后运行各轮消融。`numeric.py` 是独立无界整数/RNE参考；`quality.py` 另做真实 checkpoint 的量化筛查，非线性及 KV 保持浮点，不能冒充整数整机生成。

模型的 SQ_ABITS 是静态权重 Dot 的接口候选；原 DDR/S 张量仍保留 S32，局部转换显式计费，不减半原 trace 字节。全 K 使用共同数值尺度，中间片不舍入。新转换器/接口的联合 RTL、整模型整数数值、物理面积/STA/P&R、DDR PHY 及能耗尚未取得资格。

M1–M10 必须包含新的 bank、选择器、转换与控制；M11/M12 只连接真实预留端点。P/U/C/F/J 仍为控制分组，未重新变成大硬框。基于旧条件模型的吞吐不能代表生产 RTL 已达到。

## 复跑入口

```powershell
python -B project/experiments/stream_quant_synthesis/planner.py
python -B project/experiments/stream_quant_synthesis/numeric.py
python -B project/experiments/stream_quant_synthesis/deploy.py 04 --out <新的本地任务输出目录>
```

部署器要求新的服务器目录，归档 HEAD 的 LF Git 源、保存 commit/SHA、Slurm 分配与运行回执。已有运行不覆盖。完整当前结果见后续 `docs/experiments/issue-248-stream-quant-synthesis.md`；尚未生成时该报告属于待交付项。
