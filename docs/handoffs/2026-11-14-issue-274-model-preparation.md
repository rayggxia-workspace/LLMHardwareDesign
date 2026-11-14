# #274 七模型短程吞吐交接

2026-11-15（Asia/Shanghai）。负责人 Melodydt，[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 进行中，[草稿 PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 交付。分支 `task/274-seven-model-short-throughput` 继承 PR #260 `55620f173f2ad540efade8a552c35e9dba0f43c0`。本机项目根是共享文件副本，任务路径 `work/Melodydt/274`。本地 Llama 下载缓存仅作复用，权重不放入 Git。

服务器 `yuzelu@10.129.166.172`，任务根 `/public/home/yuzelu/Melodydt/runs/issue-274`。六组历史权重、Llama 真实权重、七套 FP32 参考均核验。Qwen3 Gather（114290）、输入/头内 RMS（114376）、全层投影和词表权重打包（114340）均完成，归档散列已核对。第一次环境遗漏、修订复跑以及完整的命令、作业与结果位置见 [任务记录](../../work/Melodydt/274/README.md)。全部已提交作业均终态。

下一步由 Melodydt 串接 Gather 与 input RMS，绑定真实 QKV 权重和 16Q/8KV 布局，校验两位置 RoPE、KV 提交与回读，再接 O、FFN、残差和完整词表。需要可执行的整网短程部署、两次 token 退休和末层残差审计，七个模型当前均无 #260 同口径吞吐。登记 PR #5 待合并，看板缺有效配置，待具权限维护者。
