# Issue153：七宏连接到LLM的阶段交付

- [Issue153](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/153)，执行/负责人YUZE-LU，保持开放、in_progress。
- [草稿PR154](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/154)，基于PR146的`task/145-systemc-seven-blocks`，待指定审查人；不合并自己PR。
- 本地工作树：`D:/Data/电路实验/LLMHardwareDesign-worktrees/issue-153-systemc-llm`；分支`task/153-systemc-llm-inference`。
- [逐步问题和解决记录](../../../docs/SYSTEMC_LLM_INFERENCE_JOURNAL.md)、[程序/命令](../../../project/systemc/llm/README.md)、[运行回执](../../../project/systemc/llm/results/)。真实权重和原始激活只保留本任务服务器目录，不进入Git。

实际：三种完整网络已有真实SystemC自回归执行。Qwen3/Granite本次三个新token吻合；Qwen2.5有量化分叉，不能写成精度通过。Qwen3.5仅R边界验证通过，不是完整网络。Gemma/Phi/Falcon/Llama及Qwen3.5整网的未完成项见覆盖表。

检查：GCC10.3/SystemC3.0.1的-Werror/UBSan、5/5 CTest；真实GDN的1060864条R事务在WSL/服务器输出和状态SHA相同；Python AST/JSON、Bash语法、管理检查、diff检查通过。无RTL、PDK或他人作业改动。最终源码SHA记录于results/source_manifest.json，运行程序/源码包及检查点SHA见各实际回执。

后续从Qwen2.5的第31个hidden边界与Qwen3最终norm的首位置偏差入手；先比较量化权重高精度参考，再决定是否需要分块尺度/宽中间表示。不能用旧错误theta恰好生成相同文本替代正确配置的验收。

协作：rayggxia-project-collab1.0.0；project_id llm-hardware-design。登记复用PR146的management-hub PR5 pending证据，本轮未重新核验；看板unverified/同步pending，缺config/board.json及Projects字段能力，处理人待指定。PR154实际已创建，但桌面侧聊attach_artifact返回thread not found，使用普通PR链接访问。PR未审查/未合并，八模型未全完成，不关闭Issue。
