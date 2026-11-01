# Issue153：七宏SystemC完整文本执行及数值修复

沿用[Issue153](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/153)与同一[草稿PR154](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/154)，负责人/执行账号YUZE-LU，独立审查人待指定。分支task/153-systemc-llm-inference，基于未合并PR146；不自合并。

七种真实文本模型均完整执行，Llama依用户指示暂缓。最终r31原格式修正版5/7（与r23指标相同）通过预先声明的短输入数值门：Phi、Gemma、Qwen3、Qwen3.5、Falcon；Qwen2.5 logits/hidden失败，Granite token/greedy失败。r28统一N8权重候选仍5/7，负结果保留。新增两个短输入通过不替代原失败。

正式入口：[持续数值处理记录](../../../docs/SYSTEMC_NUMERICAL_REPAIR.md)、[历史逐步记录](../../../docs/SYSTEMC_LLM_INFERENCE_JOURNAL.md)、[运行说明](../../../project/systemc/llm/README.md)、[独立回执](../../../project/systemc/llm/results/continuation-r31/)。原始大权重/激活留服务器，由分配节点独立SHA审计绑定；执行时未提交源码按归档/成员SHA标识。

本地-Werror/UBSan6/6 CTest，真实七模型整组回归和独立审计完成；不改七宏/RTL/EDA/他人作业。下一步为Qwen2.5激活细尺度/补偿表示及Granite更保真专家权重/跨项累加，尚未实现，不称任务全部完成。Issue保持open/in_progress。

规则rayggxia-project-collab1.0.0、project_id llm-hardware-design。登记沿用旧management-hub PR5 pending证据本次未重核；无board.json/Projects工具，看板unverified/同步pending，处理人待指定。桌面侧聊附件此前thread not found，普通PR链接可访问。
