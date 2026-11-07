# 母控独立物理实现（Issue #223）

先 _64，达到物理门并核对五类局控后，才推进 _128。当前是执行中的初版，不是已验收交付。

固定 #180 `81663a1e6586602d2a02748db1c488d2d0ba0233` 的原始 MC、紧凑取指和 PM RTL；来源散列见 `project/rtl/mother_control_v1/upstream-lock.json`。MC 限制为两个常驻目标、八 token、每端单在途任务。未扩大为九局控同时执行。五类 Block 的一致性要分别用真实原生局控及服务回放验证，有限 peer 冒烟不代替 Block 验证。U 的后续修复跟踪 #221，不覆写对方工作目录或旧验收包。

`mother_control_64` 组合一份母控和它自己的 16 KiB PM（四颗 #158/#200 同源 256×128 1RW SRAM bank）。不把 PM 当作 Block 的私有 S，不推断 FF 程序存储，复位不清 SRAM。原始 MC 的 128 位 PM/内部译码接口保留，镜像 v2 的指令为 64 位。

物理候选 1104×768、1160×800 µm，每项 10 核。使用原版 Nangate45、M1–M10、TT 1.1 V 25°C，周期 3.333333333 ns、I/O max/min 0.5/0.05 ns、转换 0.05 ns、输出 5 fF、setup/hold uncertainty 0.05/0.02 ns。完整 DRC 和提取后时序等必须全部通过，不用 false path 或 waiver 隐藏路径。

当前母控保留 2446 位完整原生信号接口；当前为四排 2 µm 原生 M10 接点，使用共同 4 µm 网格。它不是已经验证的 2 µm 全位 M11/M12 同时逃逸接口。接口宽度、粗金属接入和母控到局控的实际负载是后续连接合同的显式限制，不能把 native 通过写成最终联合产品通过。全芯片中的程序装载前端、互联及最终布局也另行核对。

`physical.sh RUN SOURCE` 在 Slurm c64/10 核数组 0–1 执行。`regression.sh OUT SOURCE` 在 4 核计算任务执行。SOURCE 的 `control180` 为锁定 #180 提交的 `project/control_*` 软件/原始测试参考，正式硬件输入均锁在本仓库。`regression.py` 在实际四-bank SRAM 上运行 v2 程序、真实装载/读回/部署、背压、两端并发、取消/排空和错误拒绝；初步 child 为有限 peer，结果必须明确标注。后续最终网表使用同一测试入口，不回标 SDF；提取 STA 独立判定时序。

失败候选、实际执行源和日志保持不可变；只在新目录重跑。大包存 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-223-mother-backend/`，Git 保存源、索引及散列。
