# 顶层共享 S 直供 A 的容量研究

Issue [247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)，负责人 Melodydt；沿现有 `task/242-r-load-bounds` / PR243。用户于 2026-11-10 选择共享 S → 每 P 独立有限 FIFO → A feeder 的速度方案，要求比较 32/48/96KiB。本实验独立于已经完成的四轮 RTL 迭代；生产 RTL 未扩容。

## 基线与范围

- 保留 R4 的四个完整场景：W8 decode/context512、W16 decode/context512、W8 decode/context2048、W8 prefill2。
- 固定旧评价体系的 S32/S96、300MHz、17.1GB/s、2P＋1U、每 Block 本地 S 16KiB、ctx8；本地 shared 与 ideal1R1W 端口层分别比较。
- pool0 必须逐字段复现 run23 的八条 R4 结果，仅允许附加新的共享池元数据。
- 32/48/96KiB 共享池通过有限请求与响应资源直接供给 A，不将命中数据写入本地 S 后再读。不免费广播，不增加 DDR 带宽，不把减少的字节直接换算为 token/s。
- 首版为静态矩阵输入的显式驻留前缀；全 A 可容纳时完整驻留，池外范围保留旧路径。跨算子保留、P/U 生产者直写共享池、透明扩展本地地址空间及共享广播均不在首版收益内。
- 共享池初始填充及写入、后续读取、仲裁、延迟、FIFO 背压与有限容量必须计费。两 P 同址读取也分别计费。

## 执行边界

按 `docs/REMOTE_RULES.md`，SystemC 编译和仿真仅在获授权的 Slurm 计算节点运行。服务器为 `yuzelu@10.129.166.172`，本人工作目录 `/public/home/yuzelu/Melodydt/issue247-area-speed/`，新实验使用独立 run 目录；既有 run01–23 不覆盖。提交后记录实际源码 commit、输入 SHA、工具版本、作业号、日志和输出 SHA。

条件模型结果不等于原生完整模型生成速度，也不证明新共享互连满足 300MHz。共享池 RTL、物理面积、时序、能耗和完整编译控制集成尚未实现或验收。容量面积预算只使用原 4KiB 1RW bank 的复制代理，不冒充共享池综合或布局结果。

运行与结果入口将在实际验证后补充；当前阶段为模型实现与审计，无新增 token/s 结果。
