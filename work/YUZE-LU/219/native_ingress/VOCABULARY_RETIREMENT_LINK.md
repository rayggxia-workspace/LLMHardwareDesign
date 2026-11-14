# Block V2 词表输出与解码交接

作业 `111132` 以现有 P scope 解码器和流式 A16 provider 的入口检查完整请求记录。5,396,848 次 P scope 调用全部通过入口检查，包含 4,830,840 次普通 K2048 调用、414,072 次 K11008 调用及 151,936 次词表 K2048 调用。检查假定输入已通过原始封包 CRC 校验，模拟入口的 job 和 epoch 取描述符声明的输入所有者。运行时还要提供对应 COPY/LOAD、结果 SRAM 确认和下游消费。该结果只证明请求的字段符合入口约束。

作业 `111141` 逐个绑定末尾的 128 个词表页。每页有 1,187 次 P0 CALL，每次在 P0 SRAM 从字地址 896 写 32 个字，对应 128 个 S32 logits。下一块会复用同一窗口，因此每次 CALL 的完成条件是 `tile_consumed`。完整读取一页的 151,936 个 logits 后，词表退出端才可以报告 `vocabulary_token_retired`。

链接器对照原始母控 CALL 地址、描述符 CRC、输入版本、连续列范围和 SRAM 窗口，同时把前 127 个词表页对应到后一解码步的 U0 Gather。最后一页交付最终 token。移除尾块、重复范围、越界 SRAM 窗口或中途修改版本的负例均被拒绝。

`retirement-link.json` 记录的是编译已知的依赖、数据量和地址。仍需在同一 Block V2 执行链上把 P0 实际结果接入退休单元，并通过有效的发送端把 token 提交至 U0 SRAM。Algo2 全量布线和 PR #260 的 P512/D128 同请求实测仍待验证。

- 入口报告 SHA-256 为 `1a8a1ab1c97f02fd7c7588555f5de48b69ab0bcae67b3334eef7900572decaa6`。
- 退休交接 SHA-256 为 `153a49e72d1248f27167cc4f057eb952d9160153269fa3f811ecad7f323d7346`。
- 远端工作目录为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/full-graph-zwl0Tr/merged-bmMd5X/native-request-6WI0tH/framework-r11-CatJ8r/p-native-audit-FMPaww`。
