# 368 启动前绑定错误保留

Refs #121 / PR #122。stage脚本沿用V父任务类型，但allocation实际为R344；native_cohost_queue在任何测量任务claim前拒绝。FAILED/1，无node-queue-state。5原始文件SHA保留，不伪装通过。373为独立新运行，修正parent_task=revision300-route-r，七项实际通过。
