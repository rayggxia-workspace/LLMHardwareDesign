2026-11-01 21:41 CST：Issue153/同一[PR154](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/154)按①逻辑数据流→②host职责→③有限桥→④多token覆盖完成。本轮54次完整真实模型运行保留六个负例；最终同一f14程序七模型各9位置全Top1/独立greedy及冻结logits/hidden门通过。修复Qwen2.5矩阵N8、Gemma有效gamma、Falcon离线A_exp静态尺度，真实命令/元数据代价计入，R合同/七宏RTL不改。21次桥对照与r35完整二进制相同；最终七次原prompt/链路重查通过，独立6CPU审计重算依赖/寿命/事务/数值门/SHA。本地-Werror/UBSan及远端Release13/13，四synthetic×三模式字节一致。持续记录docs/SYSTEMC_INTERCONNECT_EXPERIMENTS.md步骤32–40与results/interconnect-final。未改RTL/EDA/他人任务；无长上下文、M11/M12、芯片性能或P&R验收，Llama暂缓。Issue提交独立审查open/in_review，PR仍draft基于未合并PR146，不自合并/不标done；登记沿用旧PR5 pending未重核，看板unverified/同步pending，无board.json/Projects工具，处理人/审查人待指定。

# Issue153：七宏SystemC完整文本执行及数值修复

沿用[Issue153](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/153)与同一[草稿PR154](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/154)，负责人/执行账号YUZE-LU，独立审查人待指定。分支task/153-systemc-llm-inference，基于未合并PR146；不自合并。

七种真实文本模型均完整执行，Llama依用户指示暂缓。同版r35全部通过冻结的短输入数值门，原Qwen2.5与Granite失败已闭合；旧r31/r32/r33负结果保留。动态SiLU、N8激活和专家权重双项累加均有显式精度/资源证据，不能据此宣称长上下文、普遍质量或物理验收。

正式入口：[持续数值处理记录](../../../docs/SYSTEMC_NUMERICAL_REPAIR.md)、[历史逐步记录](../../../docs/SYSTEMC_LLM_INFERENCE_JOURNAL.md)、[运行说明](../../../project/systemc/llm/README.md)、[独立回执](../../../project/systemc/llm/results/continuation-r35/)。原始大权重/激活留服务器，由分配节点独立SHA审计绑定；执行时未提交源码按归档/成员SHA标识。

本地-Werror/UBSan8/8 CTest，真实七模型整组回归、Qwen2.5/Granite额外输入和独立审计均通过；四种synthetic结构另存。r32/r33负结果及旧G断言审计失败保留。不改七宏/RTL/EDA/他人作业。下一步为独立审查及后续长上下文/更多输入/硬件格式预算，当前短输入通过不替代这些证据。Issue保持open/in_review，PR保持同一草稿、不自合并。

规则rayggxia-project-collab1.0.0、project_id llm-hardware-design。登记沿用旧management-hub PR5 pending证据本次未重核；无board.json/Projects工具，看板unverified/同步pending，处理人待指定。桌面侧聊附件此前thread not found，普通PR链接可访问。
