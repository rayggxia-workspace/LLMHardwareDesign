# DAC 论文控制章节

基线为 [PR #251 的 `9abd46f5`](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/9abd46f5cbb4534bcfc614571ccd6d402ad11882)，任务见 [Issue #255](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/255) 和 [草稿 PR #256](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/256)。

- [英文正文与图注](control-section.md)解释为什么需要二级控制，以及如何用同一套指令描述不同模型的依赖关系。
- [图 1 底座与 P 局控](control-architecture.svg)画出 NoPool 候选的 P×3、U×2、C×1、F×1、J×2，展开每个 P 内的 M、G32、四银行私有 S，以及母控和局控之间的消息连接。虚线标示产品数据路径及候选的 P 内 G32 服务绑定。
- [图 2 指令分类与拓扑映射](instruction-topologies.svg)按派发、同步、参数准备、程序流四类列出 native MC v3 的八条指令和 native P 局控内核的三条指令，展示描述符指针和等待掩码如何随两种依赖顺序推进。
- [出图脚本](draw_control.py)依赖 Matplotlib。在当前目录执行 `python draw_control.py` 可重建两张 SVG 及 PNG 预览。SVG 保留可编辑文本。

## 固定版本证据

| 论文主张 | 来源 | 证据范围 |
| --- | --- | --- |
| NoPool 候选的五类九实例为 P×3、U×2、C×1、F×1、J×2 | [NoPool 合同 §1、§3](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/plans/w8a16-next-base-contract.md) | 这是候选部署清单。九组顶层联合验收尚未完成 |
| 单个 P 控制分组归属 M、G 和私有 S 各一。NoPool 绑定 K16×N8 的 M 和 G32_SILU，S 保留四银行 | [P 独立叶宏分组](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/pu_leaf_base/README.md#L18)、[G provider 绑定](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/w8a16_g/PROVIDERS.md#L14)、[S 银行组织](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/BLOCK_LOCAL_S_SRAM.md) | 三 P FFN 夹具实际采用三 M2、四份 16 KiB 私有 S（P×3、U×1）和一个共享 G32 服务 |
| MC v3 解码八条 64 位指令，CALL 和返回采用四个 128 位 flit，按身份匹配返回 | [MC 规格](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/mother_control_native/contract.json)、[MC 执行 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/mother_control_native/mc_native_controller.sv#L327-L396) | 四类按正文的功能归类。图 2 两种顺序以已实现的调用与掩码语义构造 |
| 全局调度通过描述符引用传递服务参数。P 解码器校验描述符版本、长度及部署拓扑 | [LC 规格](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/native_lc_contract.json)、[P 描述符解码 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/block_local_native/p_scope128_decode.sv#L28-L104) | 兼容性取决于已注册服务、端口及可用物理路径 |
| 17 条静态 MC 指令构成 272 B 镜像。完整实例执行 64 轮，每轮三次 CALL | [FFN 程序生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_emit.py) | 镜像大小包含头和对齐。192 次 CALL 为展开计数 |
| 每个 P 的 LC 使用 352 B 镜像。实际执行 L_EXEC、L_WAIT、L_END，并取回 128 B 描述符 | [LC 镜像生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/make_lc_kernel.py)、[LC RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/rtl/lc_native_scope_controller.sv#L233-L276) | 三指令顺序为该已注册服务的内核。描述符通过两个 64 B DMA beat 获取 |
| 三个 P 实例均通过真实控制与共享 DMA 接口，两个供数实现各通过 36 组完整 FFN 对照 | [控制夹具](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_control_fixture.sv)、[实验与回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-three-p-ffn.md) | 固定镜像和搬运量时，提前发 EXEC 的供数实现节省 0.52–1.20% FFN 周期。实验采用确定性合成整数权重，夹具负责 K 分块搬运和外层阶段编排 |

[PR #180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180) 的覆盖和恢复实验另行引用，固定至其提交与具体测试。[五类叶宏图册](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/assets/five-leaf-bases/README.md)记录 P/U 和 C/F/J 各自的 64 位控制来源与 profile 边界。图 2 局控栏仅覆盖三 P 联合回归的 native P 内核。
