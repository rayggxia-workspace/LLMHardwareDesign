# DAC 论文控制章节

基线为 [PR #251 的 `9abd46f5`](https://github.com/rayggxia-workspace/LLMHardwareDesign/commit/9abd46f5cbb4534bcfc614571ccd6d402ad11882)，任务见 [Issue #255](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/255)。这里收录英文正文、图注和矢量源图。图 1 采用已经接入真实母控、三套 P 局控和双通道 DMA 的 FFN RTL 夹具作为例子。

- [英文正文与图注](control-section.md)
- [母控、局控与指令流程矢量图](control-architecture.svg)
- [出图脚本](draw_control.py)，在该目录执行 `python draw_control.py` 可重建 SVG，并在本地导出 PNG 预览。依赖 Matplotlib，SVG 保留可编辑文本。

## 固定版本证据

| 论文主张 | 来源 | 证据范围 |
| --- | --- | --- |
| MC v3 执行 64 位指令，CALL 和返回采用四个 128 位 flit，按身份匹配返回 | [MC 规格](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/mother_control_native/contract.json)、[MC 执行 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/mother_control_native/mc_native_controller.sv#L327-L396) | 图展示三 P 的调用子集 |
| 17 条静态 MC 指令构成 272 B 镜像。完整实例执行 64 轮，每轮三次 CALL | [FFN 程序生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_emit.py) | 镜像大小包含头和对齐。192 次 CALL 为展开计数 |
| 每个 P 的 LC 使用 352 B 镜像。实际执行 L_EXEC、L_WAIT、L_END，并取回 128 B 描述符 | [LC 镜像生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/make_lc_kernel.py)、[LC RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/rtl/lc_native_scope_controller.sv#L233-L276) | 三指令顺序为该已注册服务的内核。描述符通过两个 64 B DMA beat 获取 |
| 三个 P 实例均通过真实控制与共享 DMA 接口，两个供数实现各通过 36 组完整 FFN 对照 | [控制夹具](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_control_fixture.sv)、[实验与回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-three-p-ffn.md) | Qwen2.5-3B FFN 尺寸，确定性合成整数权重。夹具负责 K 分块搬运和外层 Gate/Up 与 Down 阶段编排 |

[PR #180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180) 的覆盖和恢复实验另行引用，固定至其提交与具体测试。后续优先展开指令字段图，以及由日志支撑的 CALL、描述符获取、写确认与返回时序图。完整系统功能、能耗及联合物理验收以各自实验为准。
