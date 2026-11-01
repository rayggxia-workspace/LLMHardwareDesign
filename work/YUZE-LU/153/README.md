# Issue153：七宏SystemC完整文本执行及数值修复

沿用[Issue153](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/153)与同一[草稿PR154](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/154)，负责人/执行账号YUZE-LU，独立审查人待指定。分支task/153-systemc-llm-inference，基于未合并PR146；不自合并。

七种真实文本模型均完整执行，Llama依用户指示暂缓。同版r35全部通过冻结的短输入数值门，原Qwen2.5与Granite失败已闭合；旧r31/r32/r33负结果保留。动态SiLU、N8激活和专家权重双项累加均有显式精度/资源证据，不能据此宣称长上下文、普遍质量或物理验收。

正式入口：[持续数值处理记录](../../../docs/SYSTEMC_NUMERICAL_REPAIR.md)、[历史逐步记录](../../../docs/SYSTEMC_LLM_INFERENCE_JOURNAL.md)、[运行说明](../../../project/systemc/llm/README.md)、[独立回执](../../../project/systemc/llm/results/continuation-r35/)。原始大权重/激活留服务器，由分配节点独立SHA审计绑定；执行时未提交源码按归档/成员SHA标识。

本地-Werror/UBSan8/8 CTest，真实七模型整组回归、Qwen2.5/Granite额外输入和独立审计均通过；四种synthetic结构另存。r32/r33负结果及旧G断言审计失败保留。不改七宏/RTL/EDA/他人作业。下一步为独立审查及后续长上下文/更多输入/硬件格式预算，当前短输入通过不替代这些证据。Issue保持open/in_review，PR保持同一草稿、不自合并。

规则rayggxia-project-collab1.0.0、project_id llm-hardware-design。登记沿用旧management-hub PR5 pending证据本次未重核；无board.json/Projects工具，看板unverified/同步pending，处理人待指定。桌面侧聊附件此前thread not found，普通PR链接可访问。
