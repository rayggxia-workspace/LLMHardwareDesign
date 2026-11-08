# 母控双格式实现与五类 Block 一致性验收

[Issue #223](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/223) · [PR #224](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/224)。负责人 YUZE-LU，2026-11-08 CST。工程门已通过，用户已明确授权合入 main；最终合并状态以 PR 在线回执为准，未代替独立审查人提交批准。与五类 Block 同处的[统一交付入口](assets/five-leaf-bases/README.md)。

母控采用 #180 的 `81663a1e6586602d2a02748db1c488d2d0ba0233`，负责派发任务、等待局控的真实完成、追踪 token 和处理取消/错误；不接管功能宏计算。新增母控自己的 16 KiB 程序 SRAM，使用四颗真实 256×128 bank，与各 Block 的私有 S 分开计价。没有把五类控制分组重新定义成组合硬宏。

## 验证顺序与结果

先完成 64 位物理、真实 Block 一致性和交付校验，再启动 128 位。128 位 gate 强制读入已合格的 64 位清单，并校验同一组六文件。

| 程序格式 | 镜像版本 | 母控 RTL | 母控最终物理网表 | 实际 Block/局控 RTL 组合 |
| --- | --- | --- | --- | --- |
| 64 bit | 2 | 54/54 | 54/54 | 69/69 |
| 128 bit | 1 | 54/54 | 54/54 | 69/69 |

次数均包含三种初始化/种子组合，原生功能范围为有限 profile，不是完整 ISA。功能回归不回标 SDF，提取后的 STA 独立判定时序。

母控原始 RTL 按镜像版本动态选择取指方式，128 位 PM 接口保持一致。两格式使用**同一份**已验收 ODB/V/DEF/SDC/SPEF/GDS，物理 cell 名保留 `mother_control_64`；没有另造一份 `_128` 电路或把旧功能结论直接算到新格式。硬件及来源锁逐字不变证明见[双格式来源](../../work/YUZE-LU/223/dual-format-hardware.json)。

| 同一物理实现的指标 | 结果 |
| --- | --- |
| 工艺与范围 | Nangate45 原生 M1–M10，TT 1.1 V、25°C，沿用 #158 银行表征边界 |
| 外框 | 1104 × 768 µm |
| 时钟 | 300 MHz；实际 SDC 3.3333 ns，比 3.333333333 ns 略严格 |
| 最差 setup / hold | +374.917 / +7.629 ps，含异步控制检查 |
| 最小电容 / 转换裕量 | +0.237484 fF / +0.045214321 ns，原 Liberty 上限不变 |
| RC、SRAM 周期/脉宽、PG、信号输入与放置 | 全部通过 |
| 最终 GDS 原版完整规则 | 0 项；规则 SHA-256 `4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147` |
| 接点 | 2446 个实际 M10 信号接点均在最终 GDS 中，不含全位 M11/M12 逃逸结论 |

I/O max/min 延迟为 0.5/0.05 ns，输入转换 0.05 ns、输出负载 5 fF，setup/hold uncertainty 0.05/0.02 ns。未设 false path、multicycle 或 case analysis。后续母控到局控的真实线负载与时钟预算仍需联合布局后核对。

fresh 路线检查的原始 14 个 M2/M3 同网标记**并非报告为 0**。每一标记的全部区域都被同一原网的实际 ODB 路由线段及最终 GDS 铜覆盖，逐项证明为几何重叠误报；原报告保留。多网间距、短路、缺线及其他类型不能这样接收。两项反向控制分别移除原网线段、移除实际 GDS 铜，均正确拒绝。原版完整 GDS 规则另行通过 0 项，未修改规则或作 waiver。

## Block 覆盖与控制版本

| 场景（两格式各执行） | 次数 | 实际范围 |
| --- | --- | --- |
| P | 3 | 原生 M/G/S 程序 |
| C、F、J 单块 | 各 3 | C/F G/E 服务；J 汇合/输出 |
| C 往返 | 15 | 当前 C 的 R 状态操作、存储往返、正常/背压/故障/背压伴故障/复位；U 为 #195 参考对端 |
| U 往返 | 15 | #221 当前 U 的 N/E 与传输，五种场景；C 为 #195 参考对端 |
| C/F 双向发送 | 9 | 当前 C 与 F，正常/背压/复位，强制两端同时提供 TX |
| U 双向、U 三源 FMA 双向 | 各 9 | 两份 #221 U，真实写确认、源保持、重复传输与复位 |

P/U 保留 #195 派生局控；64 位采用其已验收的紧凑取指适配。C/F/J 的 64 位采用 #180 `2a66b918…`（与本母控冻结源的 MC/LC/取指/消息端口代码一致），128 位采用原有 #195 派生原生 profile。消息端口 `mc_ports.svh` 与 #195 逐字相同，测试接入只修正互斥预处理分支的重复声明检查。不能将这些结果称为“所有 Block 已整体升级到最新版完整 ISA”。

U 绑定 #221 的已验收硬件提交 `17ba807d69dda5415b34e531af016ab47b8e17b0`，逐项核对 31 份硬件源；未覆盖对方工作目录或改其功能宏。本任务无需新增功能宏修改。

组合证据使用**母控最终网表 + 实际 Block/局控 RTL + 真实私有 SRAM**，局控程序存储仍为行为夹具。不是各 Block 最终网表组成的联合门级系统，也不是最新 C 与最新 U 的完整联合产品验收。母控最多两个驻留目标、八全局 token、每端单在途；九实例常驻控制、全芯片供电/CTS/布线和所有端点同时逃逸未验收。

## 交付与复核

完整索引：[acceptance-index.json](../../work/YUZE-LU/223/acceptance-index.json)。执行源、失败历史及 Slurm 作业见[执行记录](../../work/YUZE-LU/223/README.md)。物理门100281、64位最终网表100282、128位RTL/网表100299/100300，Block回归100283/100293/100297及100301。P&R/ECO每项10核，回归4核，完整审计6核，封包2核；不独占整节点。

服务器根目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-223-mother-backend/`。

| 包 | 相对服务器根目录 | SHA-256 | 内部文件 |
| --- | --- | --- | --- |
| 64 | `receipt-mother64-01/mother64-accepted.tar.gz` | `3cbbcda0c44270bc04135962378257b34533d3898b44806d5f7deb1852c5f5b5` | 3860 |
| 128 | `receipt-mother128-01/mother128-accepted.tar.gz` | `55eab9f6d3c6d2510e3875552d61e18357cd99608bc39e5c3fffa5d0d8a8ba2c` | 3148 |

本机分别回收到 `C:\Users\wine10\AppData\Local\LLMHardwareDesign\mc-backend\accepted64` 和 `accepted128`。包级及全部内部散列、原版规则、完整 DRC XML、六文件、程序版本和实际回归日志均通过流式校验，不解包执行内容。回执：[64位](../../work/YUZE-LU/223/mother64-local-verification.json)、[128位](../../work/YUZE-LU/223/mother128-local-verification.json)。128包另含已合格64位清单及本地回执，绑定相同物理实现。

复核入口为 `python -B project/experiments/mother_control_v1/verify64.py ARCHIVE SHA256 --receipt NEW_RECEIPT.json`，自动区分两格式。重跑命令及依赖见[实验说明](../../project/experiments/mother_control_v1/README.md)和[架构入口](../ARCHITECTURE.md)。登记沿用管理中心 PR5 pending；缺 `config/board.json`，Projects unverified、同步 pending，待管理员核验。独立审查人待指定，Issue 进入 in_review，不标 done。
