# DAC 论文控制章节

基线为 [PR #251 的 `9abd46f5`](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/9abd46f5cbb4534bcfc614571ccd6d402ad11882)，任务见 [Issue #255](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/255) 和 [草稿 PR #256](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/256)。

- [英文正文与图注](control-section.md)解释为什么需要二级控制，以及如何用同一套指令描述不同模型的依赖关系。
- [逐图中文说明](figure-guide.zh.md)解释图 1(b) 的颜色和线型规则，以及图 2 的五类 Block 公共指令、各类服务和两种 FMA 计算流程。
- [图 1 底座与 P 局控](control-architecture.svg)逐个排列九个候选 Block。蓝色表示控制和指令，橙色表示描述符和数据。实线表示已核对的 RTL 接口，虚线表示候选绑定。
- [图 2 指令分类与拓扑映射](instruction-topologies.svg)统一呈现五类 Block 共有的 `L_EXEC/L_WAIT/L_END`，用 U 的两源与三源 FMA 说明额外数据路径、母控等待和局部描述符如何共同改变结果。
- [可编辑源图](control-figures.drawio)含两个页面，在 diagrams.net 打开即可移动形状、改文字、重新连接箭头。两张 SVG 保留矢量元素和可编辑文本。用 [出图脚本](draw_control.py)可重建 SVG、PNG 和 diagrams.net 源图。手工微调请直接保存源图并从编辑器导出。

## 固定版本证据

| 论文主张 | 来源 | 证据范围 |
| --- | --- | --- |
| NoPool 候选的五类九实例为 P×3、U×2、C×1、F×1、J×2 | [NoPool 合同 §1、§3](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/plans/w8a16-next-base-contract.md) | 这是候选部署清单。九组顶层联合验收尚未完成 |
| 单个 P 控制分组归属 M、G 和私有 S 各一。NoPool 绑定 K16×N8 的 M 和 G32_SILU，S 保留四银行 | [P 独立叶宏分组](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/pu_leaf_base/README.md#L18)、[G provider 绑定](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/w8a16_g/PROVIDERS.md#L14)、[S 银行组织](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/BLOCK_LOCAL_S_SRAM.md) | 三 P FFN 夹具实际采用三 M2、四份 16 KiB 私有 S（P×3、U×1）和一个共享 G32 服务 |
| MC v3 解码八条 64 位指令，CALL 和返回采用四个 128 位 flit，按身份匹配返回 | [MC 规格](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/mother_control_native/contract.json)、[MC 执行 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/mother_control_native/mc_native_controller.sv#L327-L396) | 图 2 使用已实现的调用与掩码语义构造母控片段 |
| P/U/C/F/J 的有界程序共用 L_EXEC、L_WAIT、L_END；L_EXEC 调用的服务随 Block 变化 | [五类生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cad3fa572d3cbf8515532df50868000806990b18/project/control_native_v1/images.py#L17-L62)、[五类 64 位 profile 证据](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/assets/five-leaf-bases/README.md#L40) | 公共子集允许统一说明。各自镜像、描述符和传输 profile 继续分别绑定 |
| U 的 E 原生 FMA 两源时输出 6，三源时输出 11，读取次数匹配源数 | [U 测试源码](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/pu_leaf_base/tb_u_native_entry.sv#L76-L94)、[U 试验回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/212/u-native-fix.md#L12-L19) | 数值和源数来自独立 U 原生入口。图中跨 Block 的输入连接和母控片段为候选部署 |
| 全局调度通过描述符引用传递服务参数。P 解码器校验描述符版本、长度及部署拓扑 | [LC 规格](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/native_lc_contract.json)、[P 描述符解码 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/block_local_native/p_scope128_decode.sv#L28-L104) | 兼容性取决于已注册服务、端口及可用物理路径 |
| 17 条静态 MC 指令构成 272 B 镜像。完整实例执行 64 轮，每轮三次 CALL | [FFN 程序生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_emit.py) | 镜像大小包含头和对齐。192 次 CALL 为展开计数 |
| 每个 P 的 LC 使用 352 B 镜像。实际执行 L_EXEC、L_WAIT、L_END，并取回 128 B 描述符 | [LC 镜像生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/make_lc_kernel.py)、[LC RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/rtl/lc_native_scope_controller.sv#L233-L276) | 三指令顺序为该已注册服务的内核。描述符通过两个 64 B DMA beat 获取 |
| 三个 P 实例均通过真实控制与共享 DMA 接口，两个供数实现各通过 36 组完整 FFN 对照 | [控制夹具](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_control_fixture.sv)、[实验与回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-three-p-ffn.md) | 固定镜像和搬运量时，提前发 EXEC 的供数实现节省 0.52–1.20% FFN 周期。实验采用确定性合成整数权重，夹具负责 K 分块搬运和外层阶段编排 |

[PR #180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180) 的覆盖和恢复实验另行引用，固定至其提交与具体测试。
