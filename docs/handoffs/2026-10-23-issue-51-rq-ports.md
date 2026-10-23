# Issue51 E2a与服务器并行交接

2026-10-23（UTC+08:00）。rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design。
负责人Liangruizhi（2663955430@qq.com，182389313已认证）。[Issue51](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/51)，
[PR52](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/52)，base PR49@6776470，task/51-rq-placement。
独立目录D:/Projects/LLMHardwareDesign-rqports；正式源码134838c71282f1a823cc99b3d857ebe3331b8d3b，交付head以PR读回为准。

用户新授权服务器并行，REMOTE_RULES已读，SSH只使用本人专用密钥认证、不读取/上传密钥内容。
服务器仅操作/public/home/yuzelu/RuizhiLiang/issue51-rq-ports-20261023/run01及run02，未修改他人目录或作业。
89936/89937均lrz-rqports、debug、8CPU/8worker、COMPLETED0:0，未占96核。正文[报告](../experiments/issue-51-rq-port-placement.md)。
原始回传包已下载核SHA，保留服务器文件/每case检查点。D盘记录D:/Projects/Codex/rq-ports-20261023。

## 已完成

8fixture数值/typed packet、1088 Fraction RQ、384服务组织、981312节点/80832packet依赖/资源/credit/容量审计，
8边界测试及6完整witness。本机/服务器最终384例cycles/busy/traffic/audit相等。
初版PE寄存器与MC分账声明有歧义，改成MC6KiB+PE2KiB、保持M总32KiB后复跑，结果不变；初版未删除。
192固定策略位置对中92近端快/100近端慢，最差单窗口退化不能视为硬件固有劣势。
48个各自取现有最佳窗口/调度的描述性对照，46近端快/2略慢，最好仅降0.5657%、最差增0.0650%。
没有依据固定不可绕过近端RQ；保留INT32内部完整K与typed bypass候选。不是全模型/RTL/PPA结果。

源码/命令[README](../../project/experiments/rq_ports/README.md)。正式结果local02/server-return02；
server-input02 SHA61ddf3b811aad874b55c23c5a62ab91979eabe82e8782cd6371890110eb723ec，
回传221411B SHA93c86dcebc5608f098c7edeec85b016f243b27885f7fb7c5eac2757e032af27d。
包索引project/experiments/rq_ports/results/issue-51-run01/index.json，含源码绑定/原始参数/结果/作业回执。
恢复先核最新AGENTS/Skill、Issue51/PR52和相关成员范围，再核包/解压新D盘路径，verify.py对local02与server02重放。

## 下一步与边界

E2b需真正的attention三遍score/PV反馈与M/A边界；bias33 RQ、R状态归属、物理实现各自仍pending。
不能把本次无bias整数linear和未校准服务当完成E2或应用质量。输入预打包/外存/浮点scale生成在边界外。
标准库服务搜索已经可以服务器并行；模型CPU迁移仍缺现代Python/Torch/Transformers环境与权重，不冒充已跑。
node27是Xeon8488C、约503.53GiB，flags含BF16/AMX/FP16；不证明OS许可、PyTorch内核可用或其他c96节点同配置。
下一步可在有界作业先核现代环境、已有小模型pilot和线程伸缩，再决定完整模型迁移；尚未开始此模型pilot。
师兄仍承担GPU专属吞吐/显存/真实GPU量化内核；已启动的采集先复用，不能在未知进度时要求全部重跑或停止。
Issue32数值包仍未获用户完成通知，未下载整合。Issue48/PR50由另一成员推进，不接管，合并共享ARCH章节时保留双方条目。

## 协作回执待办

规则rayggxia-project-collab1.0.0；本人进度与PR更新，审查/合并前in_review，不自行合并或done。
审查人待指定；登记management-hub PR5 pending。无board.json/Projects条目工具，实际看板unverified、同步pending。
具能力管理员待指定：核对受众/字段、复用或加入Issue51、Project ID=llm-hardware-design、In review/P1/assignee=Liangruizhi，
读回条目ID/字段/时间。不创建新看板或提升凭据权限。
