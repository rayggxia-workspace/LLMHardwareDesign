# 母控独立物理实现（Issue #223）

先 _64，达到物理门并核对五类局控后，才推进 _128。当前是执行中的初版，不是已验收交付。

固定 #180 `81663a1e6586602d2a02748db1c488d2d0ba0233` 的原始 MC、紧凑取指和 PM RTL；来源散列见 `project/rtl/mother_control_v1/upstream-lock.json`。MC 限制为两个常驻目标、八 token、每端单在途任务。未扩大为九局控同时执行。五类 Block 的一致性要分别用真实原生局控及服务回放验证，有限 peer 冒烟不代替 Block 验证。U 的后续修复跟踪 #221，不覆写对方工作目录或旧验收包。

`mother_control_64` 组合一份母控和它自己的 16 KiB PM（四颗 #158/#200 同源 256×128 1RW SRAM bank）。不把 PM 当作 Block 的私有 S，不推断 FF 程序存储，复位不清 SRAM。母控固定原生 ABI `0x01930001`，对应五类 Block；上游通用演示 ABI `0x00010001` 不作为本物理交付默认配置。原始 MC 的 128 位 PM/内部译码接口保留，镜像 v2 的指令为 64 位。

物理候选 1104×768、1160×800 µm，每项 10 核。使用原版 Nangate45、M1–M10、TT 1.1 V 25°C，周期 3.333333333 ns、I/O max/min 0.5/0.05 ns、转换 0.05 ns、输出 5 fF、setup/hold uncertainty 0.05/0.02 ns。完整 DRC 和提取后时序等必须全部通过，不用 false path 或 waiver 隐藏路径。

当前母控保留 2446 位完整原生信号接口；当前为六排 2 µm 原生 M10 接点，中心对齐 1.6 µm 原生轨道、间距 6.4 µm；原四排4 µm接点候选在端口附近出现间距冲突，旧结果不验收。它不是已经验证的 2 µm 全位 M11/M12 同时逃逸接口。接口宽度、粗金属接入和母控到局控的实际负载是后续连接合同的显式限制，不能把 native 通过写成最终联合产品通过。全芯片中的程序装载前端、互联及最终布局也另行核对。

`physical.sh RUN SOURCE` 在 Slurm c64/10 核数组 0–1 执行。`regression.sh OUT SOURCE` 在 4 核计算任务执行。SOURCE 的 `control180` 为锁定 #180 提交的 `project/control_*` 软件/原始测试参考，正式硬件输入均锁在本仓库。`regression.py` 在实际四-bank SRAM 上运行 v2 程序、真实装载/读回/部署、背压、两端并发、取消/排空和错误拒绝；初步 child 为有限 peer，结果必须明确标注。后续最终网表使用同一测试入口，不回标 SDF；提取 STA 独立判定时序。

失败候选、实际执行源和日志保持不可变；只在新目录重跑。大包存 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-223-mother-backend/`，Git 保存源、索引及散列。

`audit.sh OUT SOURCE CANDIDATE preflight|full` 执行独立原生STA、电气、PG、RC完整性、SRAM周期/脉宽及路线DRC；full再用未改的完整原版GDS规则检查。preflight不写物理通过结论。`gate.sh OUT SOURCE CANDIDATE`在实际6_final.v上重复54次功能回归，不标注SDF，提取STA单独验收。

`consistency.py`要求已通过full audit及gate回执，才接最终母控网表与实际Block/LC RTL。保留P/U旧局控语义，CFJ使用逐文件锁定的原紧凑源。测试覆盖任务及真实服务结果、确认/背压/故障/复位；LC程序存储沿用行为夹具，私有S是真实SRAM，因此不宣称五类全部最终门级系统或整芯片物理通过。尚未运行。


混合库审计必须先读Nangate标准单元库（fF），再读银行库（pF），与flow的UI单位一致；审计强制确认1e-15F单位，不能将SDC中的5.0读成5pF。原库上限保持原值，负裕量必失败。当前布局增加临时bank-front保留，扣除固定TAP占用；银行接收器合法放置后锁定512个实际buffer并释放临时保留，再进行其余修复。未增加底座尺寸。

`repair_notches.sh OUT SOURCE CANDIDATE ORIGINAL_DRC`只在全新目录克隆真实候选，对报告中单一原信号网的M2/M3窄缝增加合法宽度PATH，事先核对原线段/实际via几何及至少两个接触。随后重新finish/GDS/RC提取，必须另跑全部物理、功能与原版完整DRC门。修复脚本不产生通过资格；失败的矩形补线原型保持失败，不转移验收。
