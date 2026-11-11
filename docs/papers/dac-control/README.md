# DAC 论文控制章节

基线为 [PR #251 的 `9abd46f5`](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/9abd46f5cbb4534bcfc614571ccd6d402ad11882)，任务见 [Issue #255](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/255) 和 [草稿 PR #256](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/256)。

- [英文正文与图注](control-section.md)解释为什么需要二级控制，以及如何用同一套指令描述不同模型的依赖关系。
- [图 1 二级调度](control-architecture.svg)展示母控处理 Block 间的调用和同步，局控及服务逻辑管理 Block 内的数据供给、子宏运算及写回。P 局控内的细节取自三 P FFN 范围服务。
- [图 2 拓扑映射](instruction-topologies.svg)并列展示串行链和双分支汇合。两种逻辑依赖用同一组 `G_CALL` 和 `G_WAIT` 表达。物理路径和端口由部署绑定。
- [出图脚本](draw_control.py)依赖 Matplotlib。在当前目录执行 `python draw_control.py` 可重建两张 SVG 及 PNG 预览。SVG 保留可编辑文本。

## 固定版本证据

| 论文主张 | 来源 | 证据范围 |
| --- | --- | --- |
| MC v3 执行 64 位指令，CALL 和返回采用四个 128 位 flit，按身份匹配返回 | [MC 规格](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/mother_control_native/contract.json)、[MC 执行 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/mother_control_native/mc_native_controller.sv#L327-L396) | 图 2 依照已实现的调用与 token 掩码语义构造教学示例 |
| 全局调度通过描述符引用传递服务参数。P 解码器校验描述符版本、长度及部署拓扑 | [LC 规格](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/native_lc_contract.json)、[P 描述符解码 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/block_local_native/p_scope128_decode.sv#L28-L104) | 兼容性取决于已注册服务、端口及可用物理路径 |
| 17 条静态 MC 指令构成 272 B 镜像。完整实例执行 64 轮，每轮三次 CALL | [FFN 程序生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_emit.py) | 镜像大小包含头和对齐。192 次 CALL 为展开计数 |
| 每个 P 的 LC 使用 352 B 镜像。实际执行 L_EXEC、L_WAIT、L_END，并取回 128 B 描述符 | [LC 镜像生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/make_lc_kernel.py)、[LC RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/rtl/lc_native_scope_controller.sv#L233-L276) | 三指令顺序为该已注册服务的内核。描述符通过两个 64 B DMA beat 获取 |
| 三个 P 实例均通过真实控制与共享 DMA 接口，两个供数实现各通过 36 组完整 FFN 对照 | [控制夹具](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_control_fixture.sv)、[实验与回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-three-p-ffn.md) | Qwen2.5-3B FFN 尺寸，确定性合成整数权重。夹具负责 K 分块搬运和外层 Gate/Up 与 Down 阶段编排 |

[PR #180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180) 的覆盖和恢复实验另行引用，固定至其提交与具体测试。本文中的跨模型拓扑为逻辑映射示意。实证范围为已绑定三 P FFN 夹具的 RTL 功能实验。
